"""Do the dice panel's re-roll buttons replace click-then-overlay, in the REAL main() loop?

User: "Momentan akzeptiert man das Wuerfelergebnis durch ein Klick irgendwo hin.
Besser waere: Unten im Panel Buttons je nach Situation: Wurf akzeptieren / 1en
wiederholen (wenns geht) / alles wiederholen (wenns geht) / Fehlschlaege
wiederholen (wenns geht). Dann poppen nicht so viele Overlays hintereinander auf."

WHY THIS NEEDS THE REAL LOOP. test_roll_choice.py proves the preview equals the
offer on a real ShootingController. What only main() can show is the wiring
around it: that the RollChoiceView reaches the controller, that the panel is
DRAWN with the choice main() computes, that a real click on a drawn button is
routed to the button and not read as "accept", that a click anywhere is ignored
while a re-roll is on offer - and that no "Keep result" prompt is ever raised.

WHAT IS STAGED, AND WHY, each fact named:
  1. The shot. A MockAgent run does not reach "Player 1 shoots with a re-roll
     source" in a fixed frame budget (this repo's documented harness limit), so
     the hit roll is started through the LIVE ShootingController's
     _begin_resolution() - current_group and the roll are the controller's own.
  2. The re-roll sources: Monster Hunters, the controller's own ordinary
     "failures or whole roll" source, answered by stubbing _hit_reroll_reason -
     no shipped Player 1 unit carries one - and Forward Observers' AUTOMATIC
     re-roll of 1s next to it. That pairing is the user report "bei rerolls,
     sollte es keine reroll option geben": the optional re-roll used to be
     asked on the 1s re-roll. It is asked on the roll as thrown now, and the
     re-roll that follows a press carries no re-roll button.
  3. Three dice set to 1, so there is something to re-roll (a hot roll with no
     misses would offer nothing and read like a failure of the thing measured).
  4. A prompt the battle left open is answered (its last option) first - this
     harness answers no human prompt outside the pre-game, so one is open on
     nearly every frame, and the panel is never offered a choice under it.
  5. A click-away notice that comes up while waiting is dismissed (handing the
     turn to the shooter raises the turn banner, which suppresses the panel).
  6. The panel's slide/tumble clocks are wall-clock; they are rewound so the
     result reveals within a frame or two.
Everything after that is the game: main() draws the panel, real
MOUSEBUTTONDOWN events go through main()'s own event chain.

Usage:  python verify_dice_panel_buttons.py [map2] [--neutralize]
        --neutralize restores the pre-fix world (no choice on the panel, no
        answer riding on the roll) and MUST report: no buttons, a click anywhere
        accepts the roll, and a "Keep result" prompt opens afterwards.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import runpy

import pygame

MAP = "map2"
NEUTRALIZE = "--neutralize" in sys.argv
for arg in sys.argv[1:]:
    if arg.startswith("map"):
        MAP = arg

from game import config, dlc_grim_reapers, roll_choice   # noqa: E402
from game.decision import DecisionManager                # noqa: E402

config.ARMY_SELECT = False
config.MAP_SELECT = False
config.MAP = MAP

STAGE_AT = 250
FRAMES = 2500
WAIT_LIMIT = 240        # frames to wait for the reveal before calling it a failure

if NEUTRALIZE:
    # The pre-fix world, at the source: the panel is never handed a choice, and
    # no offer site ever takes an answer from the roll.
    roll_choice.RollChoiceView.pending = lambda self, dice_manager, human_players: None
    roll_choice.take = lambda dice_manager, keyed_options: False

SEEN = {
    "staged": False, "error": None, "shooter": None, "target": None, "weapon": None,
    "buttons": [], "keep_prompts": 0, "overlay_frames": 0,
    "anywhere": None, "press": None, "done": False, "refused": {},
}

_real_request = DecisionManager.request


def spy_request(self, player, prompt, options, **kwargs):
    if SEEN["staged"] and any("Keep" in str(o[0]) for o in options if isinstance(o, (tuple, list))):
        SEEN["keep_prompts"] += 1
    return _real_request(self, player, prompt, options, **kwargs)


DecisionManager.request = spy_request

# The left column must not draw a Stratagem or ability dice button any more:
# "buttons für fähigkeiten und stratagems sollen doch mit in das würfel panel
# rein, statt links in die spalte."
from game.ui.action_panel import ActionPanel  # noqa: E402

SEEN["left_ability_labels"] = 0
_real_left_button = ActionPanel._draw_button
_ABILITY_WORDS = ("Command Re-roll", "Aspect Shrine", "Branching Fates", "Targeting Array", "Crystal Matrix")


def spy_left_button(self, surface, rect, label, **kwargs):
    if SEEN["staged"] and any(word in str(label) for word in _ABILITY_WORDS):
        SEEN["left_ability_labels"] += 1
    return _real_left_button(self, surface, rect, label, **kwargs)


ActionPanel._draw_button = spy_left_button


def _on_board(state, squad):
    tokens = {id(t) for t in state.tokens}
    return any(id(m) in tokens and not m.is_dead() for m in squad.models)


def stage(loc):
    """Start a real human hit roll with a re-roll source, or return False to
    try again next frame."""
    dm, dec, sc = loc["dice_manager"], loc["decision_manager"], loc["shooting_controller"]
    pregame = loc.get("pregame_controller")
    # A HUMAN prompt left open by the battle (selfplay answers none outside the
    # pre-game - measured: open on 2251 of 2500 frames) would keep the panel
    # from ever being offered a choice. Answered with its last option, the way
    # verify_dcannon_damage_reroll.py empties the queue before it measures.
    if pregame is None or not pregame.is_active:
        for _ in range(20):
            if not dec.is_pending:
                break
            dec.choose(len(dec.options) - 1)
    for reason, busy in (("pre-game still running", pregame is not None and pregame.is_active),
                         ("a roll is on the table", dm.is_pending),
                         ("a decision is open", dec.is_pending),
                         ("a notice is up", bool(loc["_front_notice"]()))):
        if busy:
            SEEN["refused"][reason] = SEEN["refused"].get(reason, 0) + 1
            return False
    humans = loc["human_players"]
    state = loc["state"]
    squads = sorted(state.all_squads(), key=lambda s: s.name)
    # The weapon that throws the MOST dice: with one die "re-roll failures"
    # and "re-roll all" are the same die, and the measurement could not tell
    # the two buttons apart.
    shooter = weapon = None
    best = 0
    for squad in squads:
        if squad.owner not in humans or not _on_board(state, squad):
            continue
        for model in squad.models:
            for w in model.weapons:
                if not (getattr(w, "range_in", 0) and w.range_in > 0 and not getattr(w, "torrent", False)
                        and getattr(w, "attacks_notation", None) is None):
                    continue
                dice = sum(getattr(w2, "attacks", 1) or 1 for m2 in squad.models for w2 in m2.weapons
                           if w2.name == w.name and not m2.is_dead())
                if dice > best:
                    best, shooter, weapon = dice, squad, w
    target = next((s for s in squads if s.owner not in humans and _on_board(state, s)), None)
    if shooter is None or target is None:
        SEEN["error"] = "no human shooter or no enemy on the board"
        SEEN["staged"] = True
        return True
    pairs = [(m, w) for m in shooter.models for w in m.weapons
             if w.name == weapon.name and not m.is_dead()]
    tt = loc["turn_tracker"]
    tt.turn_owner = shooter.owner
    tt.set_active(shooter.owner)
    sc.cancel()
    sc.active_squad = shooter
    sc._hit_reroll_reason = lambda _target: dlc_grim_reapers.GRIM_REAPERS_LABEL
    sc._forward_observers_applies = lambda _target: True
    sc._begin_resolution("verify", weapon.name, pairs, target)
    SEEN.update(staged=True, shooter=shooter.name, target=target.name,
                weapon="%s x%d" % (weapon.name, len(pairs)))
    if sc.pending_step != "hit" or not dm.is_pending:
        SEEN["error"] = "the staged shot did not reach a hit roll (step %r)" % sc.pending_step
        return True
    SEEN["forced"] = min(3, len(dm.pending_values))
    for i in range(SEEN["forced"]):
        dm.set_die(i, 1)
    SEEN["dice"] = len(dm.pending_values)
    SEEN["misses"] = sum(1 for v in dm.pending_values if not dm.is_success(v))
    return True


def drive():
    frames = {"n": 0}
    script = {"phase": "stage", "waited": 0, "sent": None}
    real_flip = pygame.display.flip

    def flip(*args, **kwargs):
        frames["n"] += 1
        frame = sys._getframe(1)
        while frame is not None and frame.f_code.co_name != "main":
            frame = frame.f_back
        if frame is None or SEEN["done"]:
            return real_flip(*args, **kwargs)
        loc = frame.f_locals
        dm, dec, sc = loc["dice_manager"], loc["decision_manager"], loc["shooting_controller"]
        panel = loc["dice_panel"]
        if loc["decision_overlay"] is not None and dec.is_pending and SEEN["staged"]:
            SEEN["overlay_frames"] += 1

        if script["phase"] == "stage" and frames["n"] >= STAGE_AT:
            if stage(loc):
                if SEEN["error"]:
                    SEEN["done"] = True
                    return real_flip(*args, **kwargs)
                script["phase"] = "wait"
                inner = pygame.event.get

                def pump(*a, **kw):
                    events = inner(*a, **kw)
                    if SEEN["done"]:
                        return events
                    # REPLACE the frame's events: selfplay presses the first
                    # drawn dice button itself every frame, which would answer
                    # exactly what is being measured.
                    sent, script["sent"] = script["sent"], None
                    if sent is None:
                        return []
                    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=sent)]

                pygame.event.get = pump
        elif script["phase"] == "wait":
            script["waited"] += 1
            # A notice raised while we wait (handing the turn to the shooter
            # raises the turn banner) suppresses the panel, and the pump no
            # longer lets selfplay click it away - so it is dismissed here.
            notice = loc["_front_notice"]()
            if notice is not None and hasattr(notice, "dismiss"):
                notice.dismiss()
            if panel._anim_start is not None:
                panel._anim_start -= 10
            if panel._flicker_start is not None:
                panel._flicker_start -= 10
            revealed = getattr(panel, "_phase", None) == "shown" or bool(panel._button_rects)
            if panel._button_rects or (NEUTRALIZE and revealed and script["waited"] > 8):
                SEEN["buttons"] = [(o.key, o.count) for o, _r in panel._button_rects]
                SEEN["ability_buttons"] = [o.label for o, _r in getattr(panel, "_action_rects", [])]
                SEEN["command_reroll_usable"] = loc["command_reroll_controller"].can_use()
                board, backdrop = loc["board_rect_screen"], panel.last_backdrop_rect
                spot = (board.left + 30, board.bottom - 30)
                if backdrop is not None and backdrop.collidepoint(spot):
                    spot = (board.right - 30, board.bottom - 30)
                script["sent"] = spot
                script["phase"] = "anywhere"
            elif script["waited"] > WAIT_LIMIT:
                notice = loc["_front_notice"]()
                SEEN["error"] = ("the dice panel never revealed the roll (roll pending=%s, panel phase=%r, "
                                 "step=%r, decision=%r, notice=%s, choice=%s)"
                                 % (dm.is_pending, getattr(panel, "_phase", None), sc.pending_step,
                                    dec.prompt if dec.is_pending else None,
                                    type(notice).__name__ if notice else None,
                                    loc["_frame_roll_choice"]()))
                SEEN["done"] = True
        elif script["phase"] == "anywhere" and script["sent"] is None:
            SEEN["anywhere"] = {"roll_still_pending": dm.is_pending, "step": sc.pending_step,
                                "prompt_open": dec.is_pending, "keep_prompts": SEEN["keep_prompts"]}
            failures = next((r for o, r in panel._button_rects if o.key == roll_choice.FAILURES), None)
            if NEUTRALIZE or failures is None:
                SEEN["done"] = True
            else:
                script["sent"] = failures.center
                script["phase"] = "press"
        elif script["phase"] == "press" and script["sent"] is None:
            SEEN["press"] = {"step": sc.pending_step, "prompt_open": dec.is_pending,
                             "rerolled_dice": len(dm.pending_values or ()),
                             "already_rerolled": len(dm.already_rerolled),
                             "keep_prompts": SEEN["keep_prompts"]}
            script["phase"] = "reroll"
            script["waited"] = 0
        elif script["phase"] == "reroll":
            # The RE-ROLL the press threw: once it reveals, what does its panel
            # offer? "man darf rerolls nicht rerollen" - nothing but Accept.
            script["waited"] += 1
            notice = loc["_front_notice"]()
            if notice is not None and hasattr(notice, "dismiss"):
                notice.dismiss()
            if panel._anim_start is not None:
                panel._anim_start -= 10
            if panel._flicker_start is not None:
                panel._flicker_start -= 10
            if dm.is_pending and getattr(panel, "_phase", None) == "shown" and panel._button_rects:
                SEEN["reroll"] = {"step": sc.pending_step,
                                  "buttons": [(o.key, o.count) for o, _r in panel._button_rects]}
                SEEN["done"] = True
            elif script["waited"] > WAIT_LIMIT:
                SEEN["reroll"] = {"step": sc.pending_step, "buttons": None, "timed_out": True}
                SEEN["done"] = True
        return real_flip(*args, **kwargs)

    pygame.display.flip = flip
    sys.argv = ["selfplay.py", MAP, str(FRAMES)]
    try:
        runpy.run_module("selfplay", run_name="__main__")
    except SystemExit:
        pass
    finally:
        pygame.display.flip = real_flip


drive()

print("\n" + "=" * 74)
print("mode:", "NEUTRALIZED (pre-fix world)" if NEUTRALIZE else "fixed")
print("=" * 74)
if not SEEN["staged"]:
    print("FAILED: never staged a hit roll - this measured nothing")
    print("refused on frames:", SEEN["refused"])
    raise SystemExit(1)
if SEEN["error"]:
    print("FAILED:", SEEN["error"])
    raise SystemExit(1)
print("shooter / weapon / target  : %s / %s / %s" % (SEEN["shooter"], SEEN["weapon"], SEEN["target"]))
print("dice on the table          : %s (%s set to 1, %s miss in all)"
      % (SEEN.get("dice"), SEEN.get("forced"), SEEN.get("misses")))
print("buttons drawn              : %s" % (SEEN["buttons"] or "none"))
print("after a click ANYWHERE     : %s" % SEEN["anywhere"])
print("after pressing FAILURES    : %s" % SEEN["press"])
print("the re-roll's own panel    : %s" % SEEN.get("reroll"))
print("ability buttons (dice panel): %s (Command Re-roll usable: %s)"
      % (SEEN.get("ability_buttons"), SEEN.get("command_reroll_usable")))
print("ability buttons (left panel): %d drawn" % SEEN["left_ability_labels"])
print("'Keep result' prompts      : %d" % SEEN["keep_prompts"])
print("frames a decision was open : %d" % SEEN["overlay_frames"])

anywhere = SEEN["anywhere"] or {}
if NEUTRALIZE:
    # The lone Accept button is part of the new panel in both worlds; what the
    # pre-fix world lacks is every RE-ROLL button.
    ok = (not any(k != roll_choice.ACCEPT for k, _c in SEEN["buttons"])
          and not anywhere.get("roll_still_pending", True) and SEEN["keep_prompts"] >= 1)
    print("\n" + ("PASS - reproduced: no re-roll buttons, the click accepted, then a prompt opened"
                  if ok else "FAIL - the pre-fix world was not restored"))
else:
    press = SEEN["press"] or {}
    keys = [k for k, _c in SEEN["buttons"]]
    ok = (keys[:1] == [roll_choice.ACCEPT] and roll_choice.FAILURES in keys
          and anywhere.get("roll_still_pending") and anywhere.get("step") == "hit"
          and press.get("step") == "hit_optional_reroll"
          and press.get("rerolled_dice") == SEEN.get("misses")
          and dict(SEEN["buttons"]).get(roll_choice.FAILURES) == SEEN.get("misses")
          and dict(SEEN["buttons"]).get(roll_choice.WHOLE) == SEEN.get("dice")
          and not press.get("prompt_open") and SEEN["keep_prompts"] == 0)
    reroll = SEEN.get("reroll") or {}
    reroll_keys = [k for k, _c in (reroll.get("buttons") or [])]
    ok_reroll = (reroll.get("step") == "hit_optional_reroll" and reroll_keys == [roll_choice.ACCEPT])
    ok_abilities = (SEEN["left_ability_labels"] == 0
                    and (not SEEN.get("command_reroll_usable")
                         or "Command Re-roll (1 CP)" in (SEEN.get("ability_buttons") or [])))
    print("re-roll carries no re-roll button : %s" % ok_reroll)
    print("ability buttons on the dice panel : %s" % ok_abilities)
    ok = ok and ok_reroll and ok_abilities
    print("\n" + ("PASS - buttons drawn, a click anywhere ignored, the press re-rolled without a prompt, "
                  "the re-roll offered no re-roll, and the ability buttons live on the dice panel"
                  if ok else "FAIL"))
sys.exit(0 if ok else 1)
