"""Runtime proof through the REAL main() loop that the Aeldari Stratagem
buttons are drawn, and drawn in the phases their printed WHEN names.

test_aeldari_stratagem_ui.py renders the panel itself, with a registry it
builds itself. That answers "would the panel draw this?" and cannot answer
"does the running game hand it a registry at all?" - which is exactly the
defect that shipped for overflight_controller twice, and the class CLAUDE.md
records as "built but never FED" seven times over.

So this drives selfplay.py's real main() loop and spies on the ONE chokepoint
every button in the game goes through, game/ui/button_style.py's draw_button.
No PNGs: what is measured is the label, the rect and the frame it appeared on.

FOUR FACTS A PASSIVE RUN CANNOT PRODUCE, each staged with its reason:

  1. THE DETACHMENT. Six of the eight are unreachable from any shipped list
     (game/army_lists.py declares two, and game/detachments.py writes every
     other setting blank), so nothing would ever be usable. detachments.
     apply_to_config is WRAPPED rather than config being written directly -
     that function rewrites every setting from scratch and would erase a
     pre-set flag.
  2. A SELECTED UNIT, re-selected EVERY frame. _draw_movement_ui() keys on
     movement_controller.selected_squad and on nothing else, and every phase
     and turn change clears the pick.
  3. THE PHASE. Measured on this harness, a run gets a couple of phase
     advances in a few thousand frames, so Shooting and Fight are effectively
     unreachable - a passive counter would report zero and look like a pass.
     The live TurnTracker's phase_index is parked from a display.flip hook,
     the trick verify_wall_of_mirrors.py uses for the same reason.
  4. Nothing else. The panel, the registry, every can_use(), the CP ledger and
     draw_button itself are the real ones.

BUDGET: 4000 frames, measured rather than guessed. The last two of the
thirteen only come up once their bearer's own clause happens to hold - Seer's
Eye first appears at frame 1481 and Wind of Blades at 2041 - so a shorter run
reports them as undrawn, which is indistinguishable from a real gap. Below
MIN_FRAMES this says INCONCLUSIVE instead of failing.

Usage:  python verify_aeldari_stratagem_buttons.py [map2] [frames]
        python verify_aeldari_stratagem_buttons.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game import detachments, proactive_stratagems
from game.renderer import Renderer
from game.turn import (PHASES, PHASE_CHARGE, PHASE_COMMAND, PHASE_FIGHT,
                       PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker)
from game.ui import button_style

HUMAN = "Player 1"

#: Below this, "undrawn" means "not yet", not "never" - see the docstring.
MIN_FRAMES = 3000

#: The nineteen panel Stratagems, with the phases their printed WHEN names.
#: Transcribed here rather than imported so the probe and the suite are two
#: independent statements of the same table.
WHEN = {
    "Presentiment of Dread": {PHASE_COMMAND},
    "Fate Inescapable": {PHASE_SHOOTING},
    "Unshrouded Truth": {PHASE_MOVEMENT},
    "Soulsight": {PHASE_SHOOTING},
    "Warding Salvoes": {PHASE_SHOOTING, PHASE_FIGHT},
    "Time to Strike": {PHASE_MOVEMENT},
    "Blades of Asuryan": {PHASE_SHOOTING},
    "Wind of Blades": {PHASE_MOVEMENT},
    "Focused Firepower": {PHASE_SHOOTING},
    "Death from on High": {PHASE_SHOOTING, PHASE_FIGHT},
    "Daring Riders": {PHASE_MOVEMENT},
    "Blitzing Firepower": {PHASE_SHOOTING},
    "Seer's Eye": {PHASE_SHOOTING, PHASE_FIGHT},
    "Blades from Beyond": {PHASE_FIGHT},
    "Soul Bridge": {PHASE_COMMAND},
    "Spirit Token": {PHASE_MOVEMENT},
    "Warrior Focus": {PHASE_SHOOTING, PHASE_FIGHT},
    "Doom Inescapable": {PHASE_SHOOTING},
    "Preternatural Precision": {PHASE_SHOOTING},
}

#: Every Aeldari detachment setting, switched on together. A real army could
#: not field all eight at once (3 DP), but this measures the PANEL, and a
#: detachment nobody fields draws nothing at all to measure.
SETTINGS = ("SEER_COUNCIL_PLAYERS", "ARMOURED_WARHOST_PLAYERS",
            "PATH_OF_THE_OUTCAST_PLAYERS", "GUARDIAN_BATTLEHOST_PLAYERS",
            "ASPECT_HOST_PLAYERS", "WARHOST_PLAYERS",
            "WINDRIDER_HOST_PLAYERS", "SPIRIT_CONCLAVE_PLAYERS")

#: Why a Stratagem can go undrawn in a passive run even though its wiring is
#: perfect: its printed TARGET clause names a board state this harness never
#: reaches. Each is a fact about the ROSTER or the moment, measured rather than
#: assumed, and each is covered by test_aeldari_stratagem_ui.py, which stages
#: the target itself. A name that turns up here WITHOUT a reason is the finding
#: this probe exists for.
UNREACHED = {
    "Blades from Beyond":
        "WRAITHBLADES only, and the shipped Aeldari roster fields none",
    "Soulsight":
        "TARGET is the unit that is mid-shooting-activation right now",
    "Daring Riders":
        "TARGET is a unit still in Strategic Reserves",
    "Death from on High":
        "TARGET is a unit that arrived from Reserves THIS turn",
    "Spirit Token":
        "TARGET is a unit standing on an objective it controls",
    "Presentiment of Dread":
        "needs an enemy within 18in of a bearer AND visible, in the Command phase",
}

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

state = {"frames": 0, "selected": 0, "phases": set(), "seen": {}, "off_when": []}


# --- 1. the detachment ------------------------------------------------------
_real_apply = detachments.apply_to_config


def apply_to_config(*args, **kwargs):
    """WRAPPED, not pre-set: this function writes every detachment setting from
    scratch, so a flag set before it runs would simply be erased."""
    out = _real_apply(*args, **kwargs)
    from game import config
    for name in SETTINGS:
        setattr(config, name, (HUMAN,))
    return out


detachments.apply_to_config = apply_to_config


# --- 2. a selected unit, every frame ---------------------------------------
_real_move_range = Renderer.draw_move_range


def draw_move_range(self, surface, board, movement_controller):
    """RE-SELECTED every frame. A phase or turn change clears the pick, and the
    panel draws no unit UI at all without one - so a single select() would give
    a handful of frames and a truthful-looking zero."""
    if movement_controller.selected_squad is None:
        for token in movement_controller.all_tokens or ():
            squad = getattr(token, "squad", None)
            if squad is not None and squad.owner == HUMAN:
                movement_controller.select(squad.models[0])
                if movement_controller.selected_squad is not None:
                    break
    if movement_controller.selected_squad is not None:
        state["selected"] += 1
        state["squad"] = movement_controller.selected_squad.name
    return _real_move_range(self, surface, board, movement_controller)


Renderer.draw_move_range = draw_move_range


# --- 3. the phase -----------------------------------------------------------
_real_tracker_init = TurnTracker.__init__


def tracker_init(self, *args, **kwargs):
    _real_tracker_init(self, *args, **kwargs)
    state["tracker"] = self


TurnTracker.__init__ = tracker_init

#: Cycled rather than held: each of the five has to be visited so the four
#: negatives per Stratagem mean something. Every unit of the human's army is
#: also cycled through, because a Stratagem's bearer clause names keywords.
_ORDER = (PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE, PHASE_FIGHT)
_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    tracker = state.get("tracker")
    if tracker is not None:
        phase = _ORDER[(state["frames"] // 40) % len(_ORDER)]
        tracker.phase_index = PHASES.index(phase)
        tracker.turn_owner = HUMAN
        tracker.set_active(HUMAN)
        state["phases"].add(phase)
        state["phase_now"] = phase
    # Let the selection rotate too, so every bearer keyword gets a turn.
    if state["frames"] % 40 == 0:
        state["rotate"] = True
    state["frames"] += 1
    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

# The selection rotation, driven by the same counter.
_seen_squads = []


def _rotate(movement_controller):
    if not state.pop("rotate", False):
        return
    squads = []
    for token in movement_controller.all_tokens or ():
        squad = getattr(token, "squad", None)
        if squad is not None and squad.owner == HUMAN and squad not in squads:
            squads.append(squad)
    if not squads:
        return
    index = (state["frames"] // 40) % len(squads)
    movement_controller.select(squads[index].models[0])


_real_move_range_2 = Renderer.draw_move_range


def draw_move_range_rotating(self, surface, board, movement_controller):
    _rotate(movement_controller)
    return _real_move_range_2(self, surface, board, movement_controller)


Renderer.draw_move_range = draw_move_range_rotating


# --- the spy ----------------------------------------------------------------
_real_draw_button = button_style.draw_button


def draw_button(surface, rect, label, font, hovered=False, pressed=False, accent=None):
    """The one chokepoint every button in the game goes through."""
    if accent == "stratagem":
        name = label.split(" (")[0].strip()
        if name in WHEN:
            # READ LIVE, not from a snapshot taken at flip(): main() can
            # advance the phase in the middle of a frame, and a phase recorded
            # a flip ago would attribute the button to the wrong one - which is
            # how the first run of this probe reported 139 phantom off-WHEN
            # sightings.
            tracker = state.get("tracker")
            phase = tracker.phase if tracker is not None else None
            first = state["seen"].setdefault(name, {"frame": state["frames"],
                                                    "rect": tuple(rect),
                                                    "phases": set()})
            if phase is not None:
                first["phases"].add(phase)
                if phase not in WHEN[name]:
                    state["off_when"].append((name, phase, state["frames"]))
    return _real_draw_button(surface, rect, label, font,
                             hovered=hovered, pressed=pressed, accent=accent)


button_style.draw_button = draw_button


# --- the pre-fix world ------------------------------------------------------
if NEUTRALIZE:
    # THE REGISTRY NEVER REACHES THE PANEL - the "built but never fed" shape,
    # and literally what shipped for overflight_controller. Everything else is
    # untouched, so a report of 0/19 here is the panel path and nothing else.
    proactive_stratagems.ProactiveStratagems.buttons_for = (
        lambda self, squad: [])


_args = [a for a in sys.argv[1:]] or ["map2", "4000"]
sys.argv = ["selfplay.py"] + _args
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- Aeldari Stratagem buttons" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames / with a selection : %d / %d" % (state["frames"], state["selected"]))
print("  phases staged             : %s" % ", ".join(sorted(state["phases"])))
if not state["selected"]:
    print("  no unit was ever selected - INCONCLUSIVE")
    raise SystemExit(2)
if len(state["phases"]) < len(_ORDER):
    print("  not every phase was staged - INCONCLUSIVE")
    raise SystemExit(2)

print("  DRAWN %d/%d" % (len(state["seen"]), len(WHEN)))
for name in sorted(state["seen"]):
    got = state["seen"][name]
    print("     %-26s f%-6d %-28s rect=%s"
          % (name, got["frame"], ",".join(sorted(got["phases"])), got["rect"]))
missing = sorted(set(WHEN) - set(state["seen"]))
print("  NOT DRAWN                 : %s" % (", ".join(missing) if missing else "(none)"))
for name in missing:
    print("     %-26s %s" % (name, UNREACHED.get(name, "NO KNOWN REASON - investigate")))
unexplained = [n for n in missing if n not in UNREACHED]
print("  off-WHEN sightings        : %d%s"
      % (len(state["off_when"]),
         "" if not state["off_when"] else "  <- a label in a phase its WHEN does not name"))
for row in state["off_when"][:5]:
    print("     %s in %s at frame %d" % row)

# THE VERDICT. Not "all nineteen", which a passive run cannot honestly reach:
# what this probe can prove is that the registry reaches the panel, that every
# button it does draw appears only in a phase its WHEN names, and that anything
# undrawn has a named reason rather than a missing wire.
print()
if state["frames"] < MIN_FRAMES and not NEUTRALIZE:
    print("  only %d frames - below the measured %d this needs, so an undrawn "
          "button here means 'not yet'. INCONCLUSIVE."
          % (state["frames"], MIN_FRAMES))
    raise SystemExit(2)
if unexplained:
    print("  FAIL: drawn nowhere and with no known reason: %s" % ", ".join(unexplained))
    raise SystemExit(1)
if state["off_when"]:
    print("  FAIL: %d button(s) drawn outside their printed WHEN" % len(state["off_when"]))
    raise SystemExit(1)
if not state["seen"]:
    print("  FAIL: the registry never reached the panel - not one button was drawn")
    raise SystemExit(1)
print("  OK: %d/%d drawn, every one inside its printed WHEN, %d explained by "
      "their TARGET clause" % (len(state["seen"]), len(WHEN), len(missing)))
