"""A/B probes for Support Artillery's Declare Battle Formations decision, at
the SOURCE.

Two things were missing and both are new here, so both owe proof that the suite
would notice them going away again:

  * the JOIN decision itself - the rule and the merge mechanism have existed
    since the platforms were built, but nothing ever OFFERED the choice;
  * the printed transport ban at rule 18.01 - can_embark() has enforced it
    mid-battle all along, and the pre-game declaration did not, so the two
    readers of one sentence disagreed.

Each probe restores one piece of a plausible broken world and reruns the suite.
A probe that does NOT go red is a finding about the test, not a clean bill of
health.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)
FORM = os.path.join("game", "formations.py")
PRE = os.path.join("game", "pregame.py")
PANEL = os.path.join("game", "ui", "action_panel.py")
ATTACH = os.path.join("game", "attached_units.py")
SUITE = "test_support_weapon_platforms.py"


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


PROBES = [
    # THE WHOLE DECISION GONE. eligible_join_targets() answers "nothing is a
    # legal host" - the world before this change, in which the platform's only
    # answers were Deploy and Reserves. The panel then draws no Join button
    # either, so this is the one probe that has to move the most lines.
    ("no unit is ever a legal join target", FORM,
     "    return [\n        unit for unit in army\n"
     "        if not support_join_errors(platform, unit, joins.get(id(unit), ()),\n"
     "                                   destinations.get(id(unit)))\n    ]",
     "    return []",
     SUITE),

    # THE PAIRING IGNORED. Any unit will do - the world in which "may join
    # Guardian Defenders" passes while Storm Guardians are offered too, which
    # is exactly what the counter-cases in section 6 exist to catch.
    ("support_join_errors() skips can_attach()", FORM,
     "    errors = list(attached_units.can_attach(platform, target))",
     "    errors = []",
     SUITE),

    # THE ONE-PER-UNIT LIMIT. "A unit cannot have more than one SUPPORT WEAPON
    # model joined to it" - printed, and the only line that stops two D-cannons
    # stacking into one Guardian block.
    ("the one-platform-per-unit limit removed", FORM,
     "    if len(already_joined) >= MAX_SUPPORT_WEAPONS_PER_UNIT and platform not in already_joined:",
     "    if False:",
     SUITE),

    # THE ROLE GATE. Without it every unit in the army is a "platform" and the
    # panel offers Join buttons to the Guardians themselves.
    ("is_support_platform() says yes to everything", FORM,
     "    return (squad is not None and getattr(squad, \"models\", None)\n"
     "            and attached_units.attachment_role(squad) == attached_units.SUPPORT)",
     "    return True",
     SUITE),

    # THE TRANSPORT BAN, HALF ONE. The pre-fix world exactly: 18.01 does not
    # know the platform cannot embark, so the screen offers it a Wave Serpent.
    ("18.01 forgets the platform cannot embark", FORM,
     "    if any(getattr(m.profile, \"cannot_embark\", False) for m in squad.models):\n"
     "        errors.append(f\"{squad.name} cannot embark within a TRANSPORT.\")",
     "    pass",
     SUITE),

    # THE TRANSPORT BAN, HALF TWO. "AND ANY UNIT IT IS JOINED TO" - the half
    # that only exists in the window between the two declarations.
    ("the joined host may still embark", FORM,
     "    for platform in joining or ():",
     "    for platform in ():",
     SUITE),

    # ...and its mirror, from the joining side.
    ("a unit going into a transport is still a legal host", FORM,
     "    if target_destination == \"embark\":",
     "    if False:",
     SUITE),

    # THE RESOLUTION. Declarations recorded, nothing merged - the shape of
    # every "built but never fed" failure this repo has met: the buttons draw,
    # the click lands, and the platform still deploys on its own.
    ("finish_formations_for() never resolves a join", PRE,
     "            merged = attached_units.attach(squad, target, game_state=self.game_state)",
     "            merged = target",
     SUITE),

    # THE ABSORBED SQUAD LEFT IN THE ARMY. It has no models any more, so every
    # later pass has to remember to skip it - and _pending would list it.
    ("the absorbed platform stays in army()", PRE,
     "        self._all_units[owner] = [\n            s for s in self._all_units.get(owner, ())\n"
     "            if getattr(s, \"absorbed_into\", None) is None\n        ]",
     "        pass",
     SUITE),

    # THE TARGETLESS DECLARATION ACCEPTED. "Join, nobody" stored as an answer -
    # the unit looks declared and nothing can ever resolve it.
    ("declare(JOIN) without a target is accepted", PRE,
     "        if destination == JOIN and join_target is None:\n            return",
     "        pass",
     SUITE),

    # THE BUTTONS NOT DRAWN. The predicate is right, the panel never asks -
    # which is the failure mode a predicate-only test cannot see.
    ("the panel draws no Join buttons", PANEL,
     "                self._buttons.append((join_rect, _declare(pregame.JOIN, join_target=target)))",
     "                pass",
     SUITE),

    # THE BUTTON DRAWN BUT DEAD. Drawn and not wired - the variant that looks
    # finished in a screenshot.
    ("the Join button is drawn but records nothing", PANEL,
     "                pregame_controller.declare(squad, destination, transport_token=transport,\n"
     "                                           join_target=join_target)",
     "                pregame_controller.declare(squad, destination, transport_token=transport)",
     SUITE),

    # THE WORDING. A SUPPORT unit does not LEAD anything; the message became
    # player-facing the day the offer existed, and it is the reason a Guardian
    # unit is missing from the list.
    ("can_attach() says 'lead' to a SUPPORT unit", ATTACH,
     "        verb = \"join\" if attachment_role(leader_squad) == SUPPORT else \"lead\"",
     "        verb = \"lead\"",
     SUITE),
]

got, total, text = run(SUITE)
if got is None:
    print("BASELINE DID NOT RUN:" + NL + text[-2000:])
    raise SystemExit(2)
BASE = got
print("baseline %-42s %s/%s" % (SUITE, got, total))
print()

bad = 0
for label, path, new, old, suite in PROBES:
    src = read(path)
    if src.count(new) != 1:
        print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(new)))
        bad += 1
        continue
    try:
        write(path, src.replace(new, old))
        got, tot, out = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < BASE:
            verdict, detail = "BITES", "%s/%s" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < BASE:
            for line in out.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:150])
                    break
    finally:
        write(path, src)

print()
print("%d probe(s) did not bite" % bad if bad else "every probe bites")
raise SystemExit(1 if bad else 0)
