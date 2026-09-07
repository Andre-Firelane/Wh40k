"""GOLDEN MASTER for every shipped army list.

WHAT THIS IS FOR. `game/army_lists.py` is being converted from eight hand-written
builder functions into data files plus one generic builder. The contract of that
conversion is that NOTHING the builders produce may move - and "nothing" here is
much wider than points totals, because in this engine a SQUAD NAME IS A PRIMARY
KEY: `ai/agent_driver.py`'s plan orders address units by exact name,
`game/maps.py`'s partial rosters name them, `game/scene_io.py` keys saved scenes
on them, and attaching a character REWRITES that key
(attached_units.attached_unit_name(): "1 Breacher Team 1" becomes
"1 Breacher Team 1 + Cadre Fireblade").

So this fingerprints the built armies in far more detail than any suite here
does, and the whole test is one comparison against a committed baseline.

WHY A TEXT BASELINE AND NOT A HASH. A hash answers "something moved" and nothing
else. A migration that touches eight lists needs the answer to "WHAT moved", on
the first differing line, or the report sends the next investigation back to the
board - the same reason every diagnostic line in this repo carries the number
that is in dispute.

WHAT IS FINGERPRINTED, and why each one earns its place:

    register order      feeds main.py's `scene_units`, which feeds the Pre-game
                        declaration order and therefore deployment. Not a
                        cosmetic ordering.
    destination +       only pregame.EMBARK is ever used, and a passenger whose
    transport name      carrier is registered after it is a scene main.py
                        refuses (main.py's roster guard).
    squad name          the primary key, see above.
    points              catches a `unit_index` drift: the published list prices
                        e.g. a 3rd Ghostkeel higher than the first two, so a
                        changed build order can silently change a price.
    model count         catches a lost or doubled model line.
    per-model colour    leader colours differ from their bodyguard's in five of
                        the eight lists and EQUAL it in three, so "inherit the
                        unit's colour" would silently repaint a character in
                        exactly the lists where it is wrong.
    profile + weapons   the model identity game/scene_io.py itself matches on
                        (_profile_name/_weapon_names, imported rather than
                        re-spelled here - one definition).
    gear names          drones are FREE, so a wrong drone moves no points, no
                        weapon count and no total. Nothing else here can see it.
    components + roles  rule 19.01 provenance: which datasheets merged, and
                        which was the leader.
    enhancements        granted before the merge, and worth points.

USAGE
    python test_army_rosters.py            check against armies/baseline.txt
    python test_army_rosters.py --write    regenerate it (read the diff!)

After the conversion this stays as the permanent tool: changing an army list is
one line in a data file, then --write, then reading the diff.
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import army_lists, attached_units, enhancements, pregame  # noqa: E402
from game.scene_io import _profile_name, _weapon_names  # noqa: E402
from testkit import Checks  # noqa: E402

BASELINE = os.path.join("armies", "baseline.txt")

# Both owners, because every list builds for either player and the owner reaches
# the squad name (unit_name()'s leading digit) and nothing else. A list that
# built correctly for Player 1 only would be a real bug - mirror matches are a
# supported setup.
OWNERS = ("Player 1", "Player 2")


def _roles(squad):
    """"<datasheet>/<role>" per merged component (19.01), in merge order, or
    "-" for an ordinary unit that was never attached to."""
    parts = attached_units.components(squad)
    if not parts:
        return "-"
    return ", ".join(
        "%s/%s" % (getattr(c.datasheet, "name", "?"), (c.role or "?").lower())
        for c in parts
    )


def _model_key(model):
    """Everything about one model that a rebuild must reproduce."""
    return (
        _profile_name(model),
        tuple(_weapon_names(model)),
        tuple(sorted(getattr(model, "gear_names", None) or ())),
        tuple(getattr(model, "color", ()) or ()),
    )


def _model_lines(squad):
    """Identical models collapsed to one line with a count, in FIRST-APPEARANCE
    order rather than sorted: the order models sit in is itself load-bearing
    (models[0] is 19.02's representative and what many AI call sites read), so
    sorting would hide a reordering. Grouping only merges models that are
    indistinguishable, which cannot hide anything."""
    order = []
    counts = {}
    for model in squad.models:
        key = _model_key(model)
        if key not in counts:
            order.append(key)
            counts[key] = 0
        counts[key] += 1

    lines = []
    for profile, weapons, gear, color in order:
        key = (profile, weapons, gear, color)
        lines.append(
            "  %s x%d (%s) [%s] {%s}" % (
                profile,
                counts[key],
                ",".join(str(c) for c in color),
                ", ".join(weapons),
                ", ".join(gear),
            )
        )
    return lines


def _fingerprint(key, owner):
    """Build one list for one owner and describe exactly what came out.

    Built through ArmyList.build with a recording register - the same entry
    point main.py uses - so this measures the shipped path and not a
    reconstruction of it. `state=None` for the same reason preview_squads()
    passes it: attach() takes a game_state only to unregister the leader's
    squad from a board it was never put on.
    """
    registered = []

    def register(squad, destination=pregame.DEPLOY, transport=None):
        registered.append((squad, destination, transport))
        return squad

    army_lists.get(key).build(owner, register, state=None)

    out = ["### %s / %s" % (key, owner)]
    for squad, destination, transport in registered:
        if transport is None:
            where = "deploy"
        else:
            carrier = getattr(transport, "squad", None)
            where = "%s | via=%s" % (destination, getattr(carrier, "name", "?"))
        granted = enhancements.granted_names(squad) or ["-"]
        out.append("%s | %s | pts=%s | models=%d" % (
            squad.name, where, squad.points, len(squad.models)))
        out.append("  components: %s" % _roles(squad))
        out.extend(_model_lines(squad))
        out.append("  enhancements: %s" % ", ".join(granted))
    return out


def build_report():
    lines = []
    for key in [entry.key for entry in army_lists.ARMY_LISTS]:
        for owner in OWNERS:
            lines.extend(_fingerprint(key, owner))
            lines.append("")
    return lines


def main():
    lines = build_report()

    if "--write" in sys.argv:
        directory = os.path.dirname(BASELINE)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with io.open(BASELINE, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")
        print("wrote %s (%d lines)" % (BASELINE, len(lines)))
        return

    checks = Checks("army roster golden master")

    if not os.path.exists(BASELINE):
        checks.true("the baseline exists (run --write once to create it)", False)
        checks.finish()

    with io.open(BASELINE, encoding="utf-8") as handle:
        want = handle.read().splitlines()

    # One check per (list, owner) block rather than one for the whole file, so a
    # failure names the list that moved instead of just "the armies changed".
    blocks_got = _blocks(lines)
    blocks_want = _blocks(want)

    checks.eq("the baseline covers the same lists",
              sorted(blocks_want), sorted(blocks_got))

    for header in sorted(set(blocks_got) & set(blocks_want)):
        got, expected = blocks_got[header], blocks_want[header]
        if got == expected:
            checks.true(header, True)
            continue
        checks.eq("%s -- first differing line" % header,
                  _first_difference(got, expected)[0],
                  _first_difference(got, expected)[1])

    checks.finish()


def _blocks(lines):
    """{"### key / owner": [its lines]} - the report split at its headers."""
    blocks = {}
    current = None
    for line in lines:
        if line.startswith("### "):
            current = line
            blocks[current] = []
        elif current is not None:
            blocks[current].append(line)
    return blocks


def _first_difference(got, want):
    """The first line that differs, as a (got, want) pair. A trailing extra or
    missing line reports as a difference against "<missing>" rather than
    silently comparing nothing."""
    for index in range(max(len(got), len(want))):
        mine = got[index] if index < len(got) else "<missing>"
        theirs = want[index] if index < len(want) else "<missing>"
        if mine != theirs:
            return mine, theirs
    return "", ""


if __name__ == "__main__":
    main()
