"""Does a SECOND Vespid unit really get its own Airborne Agility offer?

User: "ich habe 2 vespiden, aber die rueckkehr in reserve wurde mir immer nur
von einem der beiden squads angeboten."

test_tau_kroot_and_vespid.py pins the controller's behaviour, but this repo has
been bitten enough times by "built, wired in a test, never actually fed" that
the claim is worth making against the controller main() itself builds. So this
drives selfplay's REAL main() loop with `tau_recon` - the one shipped list that
fields TWO Vespid Stingwings units, which is the reported army shape - reaches
into main()'s own frame for the LIVE AirborneAgilityController and the LIVE
DecisionManager, and drains the queue the way a player clicking would.

WHAT IS STAGED, AND WHY - three things, each with its reason:

  1. The two units are moved clear of enemy models (the corner DERIVED from
     where the enemy actually stands, not hard-coded - a fixed corner put them
     into Player 2's own deployment edge the first time this ran, and both
     came back ineligible for the right reason).
  2. The offer is fired by hand for a turn end. A MockAgent run does not
     reliably produce "both Vespid units standing free at the end of the
     opponent's turn" inside a fixed frame budget - this repo's documented
     harness limit - and a passive counter would report 0 and read like a pass.
  3. A FRESH DecisionManager for the duration. The chain only shows its second
     prompt once the first is ANSWERED, and the running game very nearly always
     has a prompt of its own at the front of the live queue (measured: it does
     here) - answering that on the player's behalf would change the game being
     measured. Only the mailbox is swapped.

Everything else - the controller main() built, its eligibility test, the chain
in game/per_unit_offer.py - is the real thing.

Usage:  python verify_airborne_agility_offers.py [map2] [--neutralize]
        --neutralize restores the pre-fix loop (one prompt, then return) and
        MUST report a single offer.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import runpy

MAP = "map2"
NEUTRALIZE = "--neutralize" in sys.argv
for arg in sys.argv[1:]:
    if arg.startswith("map"):
        MAP = arg

from game import config                              # noqa: E402

config.PLAYER1_ARMY = "tau_recon"    # the one shipped list with TWO Vespid units
config.PLAYER2_ARMY = "necrons"
config.ARMY_SELECT = False
config.MAP_SELECT = False
config.MAP = MAP

RESULTS = {}


def _human(locals_):
    ai = set(locals_["ai_players"])
    for player in sorted(locals_["armies"]):
        if player not in ai:
            return player
    return None


def _old_offer(controller, squads, ending_player):
    """The pre-fix loop, verbatim in shape: prompt the first eligible unit and
    return, so the second is never asked."""
    for squad in sorted((s for s in squads if s.owner != ending_player),
                        key=lambda s: (str(s.owner), s.name)):
        if not controller.can_use(squad):
            continue
        if squad.owner in controller.auto_players or controller.decision_manager is None:
            return False
        controller.decision_manager.request(
            squad.owner,
            "%s: Airborne Agility - leave the battlefield and go into "
            "Strategic Reserves?" % squad.name,
            [("Go into Strategic Reserves", lambda s=squad: controller.use(s)),
             ("Stay on the battlefield", lambda: None)])
        return True
    return False


def inspect(locals_):
    human = _human(locals_)
    state = locals_["state"]
    controller = locals_["airborne_agility_controller"]

    RESULTS["human"] = human
    RESULTS["controller_is_live"] = controller.game_state is state

    vespids = [s for s in state.all_squads()
               if s.owner == human and "Vespid" in s.name]
    RESULTS["vespid_units"] = [s.name for s in vespids]
    if len(vespids) < 2:
        RESULTS["error"] = "the list did not field two Vespid units"
        return

    # STAGED: put them on the board, well clear of every enemy model, so the
    # printed condition ("not within Engagement Range") is satisfied for both.
    # The corner is DERIVED from where the enemy actually stands rather than
    # hard-coded - map2 gives Player 2 the low-y edge, and a fixed corner put
    # them straight into the enemy line the first time this ran.
    enemies = [t for t in state.tokens
               if t.squad is not None and t.squad.owner != human]
    far_y = (config.BOARD_HEIGHT_IN - 4.0
             if sum(t.y_in for t in enemies) / max(1, len(enemies))
             < config.BOARD_HEIGHT_IN / 2.0 else 4.0)
    on_board = {id(t.squad) for t in state.tokens if t.squad is not None}
    for index, squad in enumerate(vespids):
        if id(squad) not in on_board:
            for model in squad.models:
                state.add_token(model)
        for slot, model in enumerate(squad.models):
            model.x_in = 4.0 + slot * 1.3
            model.y_in = far_y - index * 9.0
    RESULTS["nearest_enemy_in"] = round(min(
        ((m.x_in - t.x_in) ** 2 + (m.y_in - t.y_in) ** 2) ** 0.5
        for s in vespids for m in s.models for t in enemies), 1)

    RESULTS["eligible"] = [s.name for s in controller.eligible_squads(vespids, human)]

    if NEUTRALIZE:
        controller.offer_at_end_of_turn = (
            lambda squads, ending_player: _old_offer(controller, squads, ending_player))

    # The opponent's turn ending is what opens this window.
    opponent = next(p for p in locals_["armies"] if p != human)
    squads = {t.squad for t in state.tokens if t.squad is not None}

    # THE ONE SUBSTITUTION, and it is deliberate: a FRESH DecisionManager for
    # the duration of the measurement. The chain has to be ANSWERED to show its
    # second prompt (that is the whole mechanism), and the running game almost
    # always has a prompt of its own at the front of the live queue - answering
    # that one on the player's behalf would change the game being measured.
    # The controller, its eligibility test and game/per_unit_offer.py's chain
    # are the real ones; only the mailbox is ours.
    from game.decision import DecisionManager
    probe = DecisionManager()
    real = controller.decision_manager
    controller.decision_manager = probe
    RESULTS["live_manager_was_busy"] = locals_["decision_manager"].is_pending
    try:
        controller.offer_at_end_of_turn(squads, opponent)
        prompts = []
        while probe.is_pending and len(prompts) < 8:
            prompts.append(probe.prompt)
            labels = [o["label"] for o in probe.options]
            probe.choose(labels.index("Stay on the battlefield"))
    finally:
        controller.decision_manager = real
    RESULTS["prompts"] = prompts
    RESULTS["reserves"] = [s.name for s in state.reserves]


def drive(frames=260, at=200):
    import pygame
    fired = []
    count = {"n": 0}
    real_flip = pygame.display.flip

    def flip(*args, **kwargs):
        count["n"] += 1
        if count["n"] == at and not fired:
            fired.append(True)
            frame = sys._getframe(1)
            while frame is not None and frame.f_code.co_name != "main":
                frame = frame.f_back
            if frame is None:
                raise SystemExit("could not reach main()'s frame")
            inspect(frame.f_locals)
        return real_flip(*args, **kwargs)

    pygame.display.flip = flip
    sys.argv = ["selfplay.py", MAP, str(frames)]
    try:
        runpy.run_module("selfplay", run_name="__main__")
    except SystemExit:
        pass
    finally:
        pygame.display.flip = real_flip
    return bool(fired)


if not drive():
    print("FAILED: never reached main()'s frame")
    raise SystemExit(1)

print("\n" + "=" * 74)
print("mode:", "NEUTRALIZED (pre-fix loop)" if NEUTRALIZE else "fixed")
print("=" * 74)
if "error" in RESULTS:
    print("FAILED:", RESULTS["error"])
    raise SystemExit(1)

print("human player            : %s" % RESULTS["human"])
print("controller is main()'s  : %s" % RESULTS["controller_is_live"])
print("Vespid units in the list: %s" % ", ".join(RESULTS["vespid_units"]))
print("nearest enemy model     : %.1f in" % RESULTS["nearest_enemy_in"])
print("live queue busy meanwhile: %s" % RESULTS["live_manager_was_busy"])
print("eligible to withdraw    : %s" % ", ".join(RESULTS["eligible"]))
print("prompts raised at ONE turn end: %d" % len(RESULTS["prompts"]))
for prompt in RESULTS["prompts"]:
    print("   %s" % prompt)
print("units withdrawn (all declined): %s" % (RESULTS["reserves"] or "none"))

ok = (RESULTS["controller_is_live"]
      and len(RESULTS["eligible"]) == 2
      and len(RESULTS["prompts"]) == 2)
print()
if NEUTRALIZE:
    if len(RESULTS["prompts"]) <= 1:
        print("PASS: the pre-fix loop offers only one unit - the report, reproduced.")
        raise SystemExit(0)
    print("FAILED: the neutralized world still offered %d" % len(RESULTS["prompts"]))
    raise SystemExit(1)
print("PASS: both Vespid units are offered" if ok
      else "FAILED: expected two eligible units and two prompts")
raise SystemExit(0 if ok else 1)
