"""A/B probes for the ONE AI switch - each restores a piece of the pre-fix
world AT THE SOURCE and re-runs the suite that should notice.

Three reports came out of one game, and all three are the same root: "AI mode"
was only ever auto-play, and auto-play only ever gated ai/agent_driver.py's
frame tick.

  1. "Protokoll of undying legions wurde wieder automatisch ausgefuehrt,
     obwohl KI Modus aus war"          -> the ~83 auto_players gates
  2. "rapid ingress ... konnte aber danach keine einheit platzieren"
                                        -> a separate defect the same game found
  3. "ohne angeschalteten KI-Modus geht es ... nicht weiter. es gibt keinen
     knopf ... fuer attacker/defender"  -> the pre-game's singular human

A probe that does not bite is a finding about the TEST, not proof of the fix
(error class 24).

    python ab_ai_mode_switch.py
"""

import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
_TALLY = re.compile(r"(\d+)/(\d+) checks passed|passed (\d+), failed (\d+)")


def run(suite):
    proc = subprocess.run([sys.executable, os.path.join(ROOT, suite)], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    hits = _TALLY.findall(proc.stdout or "")
    if not hits:
        return (0, 0)
    passed, total, p2, f2 = hits[-1]
    if passed:
        return (int(passed), int(total))
    return (int(p2), int(p2) + int(f2))


# (label, suite, file, [(old, new)])
PROBES = [
    ("the gates hold a FROZEN copy again - the reported bug",
     "test_ai_mode.py", "game/ai_mode.py",
     [("    if isinstance(auto_players, AutoAnswerPlayers):\n        return auto_players\n"
       "    return AutoAnswerPlayers(auto_players)",
       "    if isinstance(auto_players, AutoAnswerPlayers):\n        return auto_players\n"
       "    view = AutoAnswerPlayers(auto_players)\n"
       "    view.__class__ = type('Frozen', (AutoAnswerPlayers,), {\n"
       "        '__contains__': lambda s, p: p in s.members})\n"
       "    return view")]),

    ("main() hands the gates a plain tuple again",
     "test_ai_mode.py", "main.py",
     [("    ai_players = ai_mode.players(p for p in sorted(armies) if p in config.AI_PLAYERS)",
       "    ai_players = tuple(p for p in sorted(armies) if p in config.AI_PLAYERS)")]),

    ("Shift+A flips a local flag again, reaching nothing else",
     "test_ai_mode.py", "main.py",
     [('                    _set_ai_mode(ai_mode.toggle(), "Shift+A")',
       '                    ai_mode.set_enabled(not ai_mode.enabled())')]),

    ("the switch is drawn only while it is ON",
     "test_ai_busy_badge.py", "main.py",
     [("        ai_toggle_rect = draw_ai_mode_toggle(",
       "        ai_toggle_rect = ai_mode.enabled() and draw_ai_mode_toggle(")]),

    # The honest pre-fix world is NO branch, not a dead one: an earlier version
    # of this probe wrote `and False and ...` and did not bite, because the pin
    # only asked whether the text was there. Deleting it is what "the switch is
    # a light, not a control" actually looked like.
    ("the board switch has no click branch at all",
     "test_ai_mode.py", "main.py",
     [("            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1\n"
       "                    and not army_rules_overlay.is_pending\n"
       "                    and ai_toggle_rect is not None\n"
       "                    and ai_toggle_rect.collidepoint(event.pos)):\n"
       '                _set_ai_mode(not ai_mode.enabled(), "AI toggle")\n'
       "                continue\n",
       "")]),

    ("a carried Rapid Ingress card expires again (report 2)",
     "test_line_drag.py", "main.py",
     [("                or (turn_tracker.phase != PHASE_MOVEMENT\n"
       "                    and picked_reserve_squad is not rapid_ingress_controller.pending_squad)):",
       "                or turn_tracker.phase != PHASE_MOVEMENT):")]),

    ("the pre-game believes in ONE human again (report 3)",
     "test_pregame.py", "game/ui/action_panel.py",
     [("        pending_owners = pregame_controller.humans_with_undeclared_units()\n"
       "        owner = pending_owners[0] if pending_owners else pregame_controller.first_human()",
       "        pending_owners = []\n"
       "        owner = pregame_controller.first_human()")]),

    ("...and its roll-off asks for one name rather than a set",
     "test_pregame.py", "game/pregame.py",
     [("        return [o for o in self._owners()\n"
       "                if o in self.human_players and self.undeclared_units(o)]",
       "        return [o for o in self._owners()[:1]\n"
       "                if o in self.human_players and self.undeclared_units(o)]")]),
]


def main():
    base = {}
    for _label, suite, _f, _e in PROBES:
        if suite not in base:
            base[suite] = run(suite)
            print("BASELINE %-28s %d/%d" % (suite, *base[suite]))
    if any(p != t for p, t in base.values()):
        print("\n  baseline not green - fix that first")
        return 1

    bites = 0
    for label, suite, path, edits in PROBES:
        full = os.path.join(ROOT, path)
        original = io.open(full, encoding="utf-8").read()
        patched = original
        for old, new in edits:
            if patched.count(old) != 1:
                print("!! %s: anchor matched %d times in %s"
                      % (label, patched.count(old), path))
                patched = None
                break
            patched = patched.replace(old, new)
        if patched is None:
            continue
        io.open(full, "w", encoding="utf-8", newline="\n").write(patched)
        try:
            got = run(suite)
        finally:
            io.open(full, "w", encoding="utf-8", newline="\n").write(original)
        fell = base[suite][0] - got[0]
        bites += 1 if fell > 0 else 0
        print("\n%s %s" % ("+ BITES" if fell > 0 else "! NO BITE", label))
        print("      %-28s %d/%d (was %d)" % (suite, got[0], got[1], base[suite][0]))
        if fell <= 0:
            print("      a finding about the TEST, not proof of the fix")

    print("\n%d/%d probes bite" % (bites, len(PROBES)))
    for suite, was in base.items():
        now = run(suite)
        print("restored %-28s %d/%d" % (suite, *now))
        if now != was:
            return 1
    return 0 if bites == len(PROBES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
