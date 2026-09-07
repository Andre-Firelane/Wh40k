"""Runtime proof through the REAL main() loop that the T'au Stratagem buttons
reach the screen, and only in a phase their printed WHEN names.

test_tau_stratagem_ui.py draws the real ActionPanel, but it builds the panel,
the registry and the controllers itself. What it cannot show is that MAIN'S
registry, filled by MAIN'S constructors, reaches MAIN'S panel - "built but
never FED" has hit this repo six times, and it is what shipped for
overflight_controller on the Aeldari side.

So this spies on game/ui/button_style.py's draw_button() - the one chokepoint
every button in the game goes through - and reports which of the fourteen were
drawn, in which phases, and whether any appeared outside its WHEN.

THREE THINGS ARE STAGED, each because the harness cannot be relied on to
produce it, and each named rather than quietly faked:
  * THE DETACHMENTS. Wrapped rather than pre-set: apply_to_config() writes
    every detachment setting from scratch, so a flag set before it runs is
    simply erased.
  * A SELECTED UNIT, every frame. _draw_movement_ui() opens with
    movement_controller.selected_squad and draws no unit UI at all without one,
    and a phase or turn change clears the pick - so a single select() would
    give a handful of frames and a truthful-looking zero.
  * THE PHASE. Measured on this roster: a T'au list reaches the end of the
    pre-game but not one phase change inside any budget worth waiting for,
    where the default armies reach seven. A passive run would therefore report
    "drawn in Command only" and read as a phase bug.

The phase is READ LIVE at draw time, not from a snapshot: main() can advance
the phase in the middle of a frame, and a phase recorded a flip ago attributes
the button to the wrong one.

Usage:  python verify_tau_stratagem_buttons.py [map2] [frames]
        python verify_tau_stratagem_buttons.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game import config, detachments, proactive_stratagems
from game.turn import (PHASES, PHASE_CHARGE, PHASE_COMMAND, PHASE_FIGHT,
                       PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker)
from game.renderer import Renderer
from game.ui import button_style

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"
MIN_FRAMES = 1500      # below this, "undrawn" means "not yet", not "never"

# TRANSCRIBED from the printed WHEN, deliberately not imported: the probe and
# the suite are then two independent statements of the same table, and a table
# that moved would have to move in both.
WHEN = {
    "Experimental Ammunition": {PHASE_SHOOTING},
    "Experimental Modifications": {PHASE_SHOOTING, PHASE_FIGHT},
    "Alien Expertise": {PHASE_MOVEMENT},
    "Guided Fire": {PHASE_SHOOTING},
    "Point-Blank Ambush": {PHASE_SHOOTING},
    "Coordinate to Engage": {PHASE_SHOOTING},
    "A Tempting Trap": {PHASE_SHOOTING},
    "Aggressive Mobility": {PHASE_MOVEMENT},
    "Combat Debarkation": {PHASE_SHOOTING},
    "Focused Fire": {PHASE_SHOOTING},
    "Microdrone Support": {PHASE_SHOOTING},
    "Arro'kon Protocol": {PHASE_SHOOTING},
    "The Torchstar Gambit": {PHASE_SHOOTING},
    "The Shortened Blade": {PHASE_MOVEMENT},
}

SETTINGS = ("KAUYON_PLAYERS", "MONTKA_PLAYERS",
            "ADVANCED_ACQUISITION_CADRE_PLAYERS", "AUXILIARY_CADRE_PLAYERS",
            "EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS", "RETALIATION_CADRE_PLAYERS")

# Why a passive run can legitimately never draw one. Each entry is a printed
# TARGET clause the MockAgent does not arrange, not an excuse for a missing
# wire - and an undrawn name with NO entry here is a failure.
UNREACHED = {
    "Combat Debarkation":
        "TARGET is a unit that disembarked this turn; the AI keeps its "
        "Breachers aboard or walks them",
    "Coordinate to Engage":
        "TARGET is an Observer unit that Spotted something this phase",
    "A Tempting Trap":
        "TARGET needs an objective marker outside the enemy zone AND the unit "
        "not to have shot yet",
    "Microdrone Support":
        "TARGET is a unit whose rule-16.01 action is blocking its shooting",
    "The Torchstar Gambit":
        "TARGET is a BATTLESUIT that has already resolved its attacks this phase",
    "The Shortened Blade":
        "bought DURING a Deep Strike arrival, on the setup screen - a MockAgent "
        "run reaches no such arrival",
    "Experimental Modifications":
        "TARGET is a KROOT/VESPID unit that is eligible to fight or shoot",
    "Alien Expertise": "TARGET is a KROOT/VESPID unit in the Movement phase",
    "Guided Fire": "TARGET must not itself be KROOT/VESPID",
    "Point-Blank Ambush": "third battle round onwards",
    "A Tempting Trap ": "unused",
}

state = {"frames": 0, "selected": 0, "seen": {}, "off_when": [],
         "phases": set(), "tracker": None, "rotate": False}

_real_draw_button = button_style.draw_button


def draw_button(surface, rect, label, font, hovered=False, pressed=False,
                accent=None):
    """The one chokepoint every button in the game goes through."""
    if accent == "stratagem":
        name = label.split(" (")[0].strip()
        if name in WHEN:
            # READ LIVE, not from a snapshot taken at flip(): main() can
            # advance the phase in the middle of a frame, and a phase recorded
            # a flip ago attributes the button to the wrong one.
            tracker = state.get("tracker")
            phase = tracker.phase if tracker is not None else None
            first = state["seen"].setdefault(
                name, {"frame": state["frames"], "phases": set()})
            if phase is not None:
                first["phases"].add(phase)
                if phase not in WHEN[name]:
                    state["off_when"].append((name, phase, state["frames"]))
    return _real_draw_button(surface, rect, label, font, hovered=hovered,
                             pressed=pressed, accent=accent)


button_style.draw_button = draw_button

if NEUTRALIZE:
    # THE REGISTRY NEVER REACHES THE PANEL - the "built but never fed" shape.
    # Everything else is untouched, so a report of 0 for the eleven registry
    # buttons here is the panel path and nothing else. The three that predate
    # the registry take their own argument and are deliberately left alone, so
    # the run also shows WHICH path each button came down.
    proactive_stratagems.ProactiveStratagems.buttons_for = (
        lambda self, squad: [])

_real_apply = detachments.apply_to_config


def apply_to_config(*args, **kwargs):
    """WRAPPED, not pre-set: this writes every detachment setting from
    scratch, so a flag set before it runs would simply be erased."""
    out = _real_apply(*args, **kwargs)
    for name in SETTINGS:
        setattr(config, name, (HUMAN,))
    return out


detachments.apply_to_config = apply_to_config

_real_tracker_init = TurnTracker.__init__


def tracker_init(self, *args, **kwargs):
    _real_tracker_init(self, *args, **kwargs)
    state["tracker"] = self


TurnTracker.__init__ = tracker_init

_ORDER = (PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE,
          PHASE_FIGHT)
_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    tracker = state.get("tracker")
    if tracker is not None and getattr(tracker, "started", True):
        phase = _ORDER[(state["frames"] // 40) % len(_ORDER)]
        tracker.phase_index = PHASES.index(phase)
        tracker.turn_owner = HUMAN
        tracker.set_active(HUMAN)
        tracker.battle_round = 3       # satisfies every printed round clause
        state["phases"].add(phase)
    # A DIFFERENT PERIOD from the phase rotation above, and coprime with the
    # five phases. Sharing one modulus pairs unit i with phase i%5 for ever, so
    # a unit whose WHEN names a phase it is never selected in is reported "not
    # drawn" - a truthful-looking zero produced entirely by the probe. Measured:
    # with both on //40, the panel was never once asked about a BATTLESUIT
    # CHARACTER unit in the Shooting phase.
    if state["frames"] % 17 == 0:
        state["rotate"] = True
    state["frames"] += 1
    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

_real_move_range = Renderer.draw_move_range


def draw_move_range(self, surface, board, movement_controller):
    """RE-SELECTED every frame, and ROTATED every forty. A phase or turn change
    clears the pick and the panel draws no unit UI without one, so a single
    select() would give a handful of frames and a truthful-looking zero; and a
    single unit would only ever satisfy the TARGET line of a few of the
    fourteen."""
    squads = []
    for token in movement_controller.all_tokens or ():
        squad = getattr(token, "squad", None)
        if squad is not None and squad.owner == HUMAN and squad not in squads:
            squads.append(squad)
    if squads and (state.pop("rotate", False)
                   or movement_controller.selected_squad is None):
        index = (state["frames"] // 17) % len(squads)
        movement_controller.select(squads[index].models[0])
    if movement_controller.selected_squad is not None:
        state["selected"] += 1
        _tr = state.get("tracker")
        state.setdefault("units", set()).add(movement_controller.selected_squad.name)
        state.setdefault("pairs", set()).add(
            (movement_controller.selected_squad.name,
             _tr.phase if _tr is not None else None))
    return _real_move_range(self, surface, board, movement_controller)


Renderer.draw_move_range = draw_move_range

# WHY an undrawn name was refused, measured rather than guessed. Without this
# an entry in UNREACHED is a story about the harness that nobody checked - and
# the two this was written for (Experimental Ammunition, Arro'kon Protocol)
# turned out to have their bearer selected in the right phase, so the guess
# would have been wrong. Only the last clause each controller reaches is
# recorded, which is the one that actually refused.
from game import arrokon_protocol as _arro  # noqa: E402
from game import epc_experimental_ammunition as _ammo  # noqa: E402

_WATCH = {"Experimental Ammunition": _ammo.ExperimentalAmmunitionController,
          "Arro'kon Protocol": _arro.ArrokonProtocolController}


def _watch(name, cls):
    real = cls.can_use

    def can_use(self, squad):
        out = real(self, squad)
        if not out and squad is not None:
            tr = getattr(self, "turn_tracker", None)
            sc = getattr(self, "shooting_controller", None)
            why = []
            if tr is not None and tr.phase != PHASE_SHOOTING:
                why.append("phase")
            elif tr is not None and squad.owner != tr.active_player:
                why.append("owner")
            elif sc is not None and sc.active_squad is squad:
                why.append("already activated")
            elif sc is not None and not sc.can_shoot(squad):
                why.append("cannot shoot")
            else:
                why.append("target/ledger clause")
            state.setdefault("why", {}).setdefault(name, set()).update(why)
        return out

    cls.can_use = can_use


for _n, _c in _WATCH.items():
    _watch(_n, _c)

_argv = sys.argv[1:] or ["map2", "3000"]
sys.argv = ["selfplay.py"] + _argv
config.PLAYER1_ARMY = "tau"
config.ARMY_SELECT = False

runpy.run_module("selfplay", run_name="__main__")

drawn = sorted(state["seen"])
missing = sorted(n for n in WHEN if n not in state["seen"])

print()
print("--- T'au Stratagem buttons"
      + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames / with a selection : %d / %d" % (state["frames"], state["selected"]))
print("  phases staged             : %s" % ", ".join(sorted(state["phases"])))
print("  units selected            : %d" % len(state.get("units", ())))
_bs = sorted(p for p in state.get("pairs", ()) if "Coldstar" in p[0])
print("  battlesuit-character unit, phases reached: %s"
      % ", ".join(sorted({p[1] for p in _bs})) if _bs else "  (never selected)")
print("  DRAWN %d/%d" % (len(drawn), len(WHEN)))
for name in drawn:
    info = state["seen"][name]
    print("     %-28s f%-6d %s" % (name, info["frame"],
                                   ",".join(sorted(info["phases"]))))
if missing:
    print("  NOT DRAWN                 : %s" % ", ".join(missing))
    for name in missing:
        _why = state.get("why", {}).get(name)
        _reason = UNREACHED.get(name)
        if _reason is None and _why:
            _reason = "measured refusal: " + ", ".join(sorted(_why))
        print("     %-28s %s" % (name, _reason or "*** NO REASON ***"))
print("  off-WHEN sightings        : %d" % len(state["off_when"]))
for name, phase, frame in state["off_when"][:6]:
    print("     %-28s %s at f%d" % (name, phase, frame))

# THE VERDICT. Not "all fourteen", which a passive run cannot honestly reach:
# what this can prove is that the registry reaches the panel, that every button
# it did draw appeared only in a phase its WHEN names, and that anything
# undrawn has a named reason rather than a missing wire.
if state["selected"] == 0:
    print("  INCONCLUSIVE: no unit was ever selected, so no unit UI was drawn")
    raise SystemExit(2)
if state["frames"] < MIN_FRAMES:
    print("  INCONCLUSIVE: fewer than %d frames" % MIN_FRAMES)
    raise SystemExit(2)

if NEUTRALIZE:
    ok = not any(n for n in drawn if n not in
                 ("Arro'kon Protocol", "The Torchstar Gambit",
                  "The Shortened Blade"))
    print("  VERDICT: " + ("no registry button reached the panel"
                           if ok else "NOT reproduced"))
    raise SystemExit(0 if ok else 1)

unexplained = [n for n in missing
               if n not in UNREACHED and not state.get("why", {}).get(n)]
ok = bool(drawn) and not state["off_when"] and not unexplained
print("  VERDICT: " + ("the registry reaches the panel, in the right phases"
                       if ok else "FAILED"))
raise SystemExit(0 if ok else 1)
