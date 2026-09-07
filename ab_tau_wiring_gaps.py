"""A/B probes for the three main.py wiring gaps found by the T'au audit.

Each probe restores one piece of the pre-fix world AT THE SOURCE, runs the
suite that should notice, and puts it back. A probe that does NOT go red is a
finding about the TEST, not a clean bill of health - so this exits non-zero if
any survives.

THE THREE GAPS
  F1  Four controllers owned a pending_damage_choice, had a click branch, drew
      their eligible models and blocked the phase - and were absent from
      _any_pending_damage_choice(), the snapshot that pauses the AI for one
      frame so the render can show the casualty before it acts again. Three
      lists answer that one question in main.py and all three disagreed;
      nothing was watching this one.
  F2  Twelve move modes are opened outside the moving unit's own Movement
      phase by eleven modules, and _has_unresolved_declaration() had no
      movement_controller term at all - so "Next Phase" orphaned a paid-for
      move. Two owners were waited on already, both for an unrelated reason.
  F4  Retro-thrusters' Fall Back half delegated to start_fall_back_move(),
      which is gated on the Movement phase - so at the end of the Fight phase
      where the ability fires it returned early, no move opened, and the line
      after it set a move_mode anyway. A mode with no move behind it, which is
      also why F2's gate term needs its state test.

The last probe is the one that matters most for F2: everything else stays green
without the gate term, because the set and the sweep are both intact and only
the READER is missing - the "gebaut, aber nie GEFUETTERT" shape.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)
MAIN = "main.py"
MOVEMENT = os.path.join("game", "movement.py")
ENHANCEMENTS = os.path.join("game", "enhancements.py")
WALL = os.path.join("game", "kauyon_wall_of_mirrors.py")
WIRING = "test_event_chain_wiring.py"
AELDARI_ENH = "test_aeldari_enhancements.py"
SUITES = (WIRING, AELDARI_ENH)


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite):
    # The probes rewrite modules within the same second - the documented
    # __pycache__ race that has produced phantom failures in this repo.
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


# --- F1 ---------------------------------------------------------------------
_F1 = ("                ishas_fury_controller, grenade_pack_controller," + NL
       + "                grav_inhibitor_controller, flickerjump_controller," + NL)
_F1_ONE = ("                ishas_fury_controller, grenade_pack_controller," + NL
           + "                grav_inhibitor_controller," + NL)

# --- F2 ---------------------------------------------------------------------
_F2_TERM = ("            or (movement_controller.state == movement.MOVING" + NL
            + "                and movement_controller.move_mode" + NL
            + "                in movement.MovementController.OUT_OF_PHASE_MOVE_MODES)")
_F2_TERM_OFF = "            or False  # gate term removed by ab_tau_wiring_gaps.py"
_F2_TERM_NO_STATE = ("            or (movement_controller.move_mode" + NL
                     + "                in movement.MovementController.OUT_OF_PHASE_MOVE_MODES)")

_F2_SET = '        "torchstar", "tactical_acumen", "fire_and_fade",'
_F2_SET_NO_TORCHSTAR = '        "tactical_acumen", "fire_and_fade",'
_F2_SET_DEAD = ('        "torchstar", "tactical_acumen", "fire_and_fade", "no_such_move",')

_REACTIVE = ('    REACTIVE_MOVE_MODES = frozenset({"battle_focus", "path_of_the_outcast",' + NL
             + '                                     "raid_and_run", "overflight", "higher_duty"})')
_REACTIVE_SHORT = ('    REACTIVE_MOVE_MODES = frozenset({"battle_focus", "path_of_the_outcast",' + NL
                   + '                                     "overflight", "higher_duty"})')

# An unresolvable move_mode: the sweep must REPORT it rather than quietly
# measuring one mode fewer, which would make every difference below pass.
_OPAQUE_SRC = '        self.movement_controller.start_post_shooting_move('
_OPAQUE = _OPAQUE_SRC

# --- F4 ---------------------------------------------------------------------
_F4 = ("            self._begin_move(effective_movement_in)" + NL
       + '            self.move_mode = "retro_thrusters_fall_back"' + NL
       + "            self.desperate_escape_this_move = False")
_F4_OFF = ('            self.start_fall_back_move("ordered_retreat")' + NL
           + '            self.move_mode = "retro_thrusters_fall_back"')


PROBES = [
    # F1
    ("F1: the four controllers never pause the AI (the shipped world)",
     [(MAIN, _F1, "")], WIRING),
    ("F1: only ONE of the four is left out - a partial regression",
     [(MAIN, _F1, _F1_ONE)], WIRING),

    # F2 - the reader. THE probe for this fix.
    ("F2: the phase gate never reads the move-mode set (built, never fed)",
     [(MAIN, _F2_TERM, _F2_TERM_OFF)], WIRING),
    ("F2: the gate reads the set but drops its state test (a stale mode "
     "would deadlock the phase)",
     [(MAIN, _F2_TERM, _F2_TERM_NO_STATE)], WIRING),

    # F2 - the set, both directions.
    ("F2: torchstar dropped from the set (the originally reported move)",
     [(MOVEMENT, _F2_SET, _F2_SET_NO_TORCHSTAR)], WIRING),
    ("F2: a dead entry in the set that nothing opens",
     [(MOVEMENT, _F2_SET, _F2_SET_DEAD)], WIRING),

    # F2 - the twice-reported reactive contract. TWO probes, because
    # OUT_OF_PHASE_MOVE_MODES is derived as a union WITH REACTIVE_MOVE_MODES:
    # dropping a mode from the reactive set alone removes it from both, so the
    # out-of-phase difference fires first and the contract check is never shown
    # to be live. The second probe puts the mode back into the explicit half so
    # ONLY the contract check can fail - which is what proves the line that
    # exists to prevent a third "the AI just carried on" report.
    ("F2: raid_and_run dropped from REACTIVE_MOVE_MODES (reported twice)",
     [(MOVEMENT, _REACTIVE, _REACTIVE_SHORT)], WIRING),
    ("F2: ...and isolated, so only the reactive contract can notice",
     [(MOVEMENT, _REACTIVE, _REACTIVE_SHORT),
      (MOVEMENT, _F2_SET, '        "raid_and_run",' + NL + _F2_SET)], WIRING),

    # F4 - and note it is measured against the ALIEN suite, because that is
    # where the pin on "_begin_move is the one shared entry" lives. A fix that
    # only the T'au side notices would be exactly the drift this catches.
    ("F4: Retro-thrusters' Fall Back half goes back through the phase gate",
     [(MOVEMENT, _F4, _F4_OFF)], AELDARI_ENH),

    # --- The three PREVENTATIVE guards (sections 14-16) -------------------
    # These are green today by construction; each probe is what shows the
    # guard would actually catch the failure it was written for, rather than
    # passing because it measures nothing.

    # 14: a Stratagem controller that asks for a panel button and is never
    # registered - the "built but never fed" shape, for the panel path.
    ("14: a panel Stratagem is built but never registered",
     [(MAIN,
       "    guided_fire_controller = proactive_stratagems.add(GuidedFireController(",
       "    guided_fire_controller = (GuidedFireController(")], WIRING),

    # 15: an end-of-phase offer deciding eligibility from the live clock -
    # the exact shape of six bugs across two factions.
    # A STRING literal, not PHASE_FIGHT: that name is not imported in this
    # module, so the constant form makes section 1b (free names) go red first
    # and section 15 is never shown to be the thing that noticed. Measured -
    # the first version of this probe bit for exactly that wrong reason.
    ("15: an end-of-phase offer reads the live clock again",
     [(WALL,
       "        if not self._window.is_open(squad.owner):",
       '        if self.turn_tracker.phase != "Fight":')], WIRING),

    # 16: an Enhancement whose UnitProfile field nothing reads - bought, paid
    # for, shown on the datacard, and inert.
    ("16: an Enhancement's flag is read by nothing",
     [(ENHANCEMENTS,
       '_add("Internal Grenade Racks", 20, _RETALIATION, "internal_grenade_racks",',
       '_add("Internal Grenade Racks", 20, _RETALIATION, "internal_grenade_racks_x",')],
     WIRING),

    # The whole pre-fix world.
    ("the whole pre-fix world: F1 out, F2's gate term out, F4 back",
     [(MAIN, _F1, ""), (MAIN, _F2_TERM, _F2_TERM_OFF), (MOVEMENT, _F4, _F4_OFF)],
     WIRING),
]


BASE = {}
for _suite in SUITES:
    got, total, text = run(_suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:%s%s" % (_suite, NL, text[-2000:]))
        raise SystemExit(2)
    BASE[_suite] = got
    print("baseline %-34s %s/%s" % (_suite, got, total))
print()

bad = 0
for label, edits, suite in PROBES:
    originals = {path: read(path) for path, _, _ in edits}
    ok = True
    for path, new, old in edits:
        src = read(path)
        if src.count(new) != 1:
            print("  SKIP     %s: anchor not unique in %s (%d)"
                  % (label, path, src.count(new)))
            ok = False
            break
        write(path, src.replace(new, old))
    try:
        if not ok:
            bad += 1
            continue
        got, tot, out = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < BASE[suite]:
            verdict, detail = "BITES", "%s/%s" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < BASE[suite]:
            for line in out.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:104])
                    break
    finally:
        for path, text in originals.items():
            write(path, text)

print()
print("%d probe(s) did not bite" % bad if bad else "every probe bit")
raise SystemExit(1 if bad else 0)
