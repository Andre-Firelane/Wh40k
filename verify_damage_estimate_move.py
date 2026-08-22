"""Equivalence harness for the expected_wounds/expected_kills move out of
ai/observation.py into game/damage_estimate.py.

The move is meant to be behaviour-preserving: every threat number, trade
judgement, reserve landing score and melee weapon choice in the AI is built on
these two functions, so "I only moved it" has to be demonstrated rather than
asserted. Run with `--save` on the pre-move tree to record a baseline, then
without it afterwards to diff.

Covers every datasheet of both factions against every other, in both the
ranged and the melee direction, plus expected_wounds() on each individual
weapon - i.e. every code path the move touched.
"""

import json
import sys

from game.factions import build_squad
from game.factions import orks, tau_empire

BASELINE = "damage_estimate_baseline.json"


def _datasheets(module):
    seen = {}
    for name in dir(module):
        obj = getattr(module, name)
        if hasattr(obj, "model_lines") and hasattr(obj, "name") and name.isupper():
            seen.setdefault(obj.name, (name, obj))
    return [v for _, v in sorted(seen.items())]


def collect():
    from ai import observation

    squads = []
    for module, owner in ((tau_empire, "Player 1"), (orks, "Player 2")):
        for const_name, ds in _datasheets(module):
            try:
                squads.append((f"{module.__name__}.{const_name}", build_squad(ds, owner, name=const_name)))
            except Exception as exc:  # a datasheet needing choices we are not supplying
                squads.append((f"{module.__name__}.{const_name}", None))
                print(f"  (skipped {const_name}: {exc})")

    out = {"expected_kills": {}, "expected_wounds": {}}

    for a_name, attacker in squads:
        if attacker is None:
            continue
        for d_name, defender in squads:
            if defender is None:
                continue
            for melee in (False, True):
                key = f"{a_name}|{d_name}|{'melee' if melee else 'ranged'}"
                result = observation.expected_kills(attacker, defender, melee=melee)
                out["expected_kills"][key] = result

    # expected_wounds() on each individual weapon against each defender's soak
    # group - the single-weapon path rule 04.01's melee choice depends on.
    from game.damage_estimate import DefenderStats
    from game.squad import attached_unit_toughness

    for d_name, defender in squads:
        if defender is None:
            continue
        toughness = attached_unit_toughness(defender)
        soak = next((g for g in defender.allocation_groups() if g), defender.models)
        profile = DefenderStats(toughness, soak[0].profile)
        for a_name, attacker in squads:
            if attacker is None:
                continue
            for i, model in enumerate(attacker.models):
                for j, weapon in enumerate(model.weapons):
                    skill = model.profile.weapon_skill if getattr(weapon, "weapon_type", None) == "melee" else model.profile.ballistic_skill
                    key = f"{a_name}|{i}|{j}|{d_name}"
                    out["expected_wounds"][key] = round(
                        observation.expected_wounds(weapon, weapon.attacks, skill, profile), 10
                    )
    return out


def main():
    data = collect()
    n_kills = len(data["expected_kills"])
    n_wounds = len(data["expected_wounds"])
    if "--save" in sys.argv:
        with open(BASELINE, "w") as fh:
            json.dump(data, fh, indent=1, sort_keys=True)
        print(f"baseline saved: {n_kills} expected_kills entries, {n_wounds} expected_wounds entries")
        return 0

    with open(BASELINE) as fh:
        old = json.load(fh)

    failures = []
    for section in ("expected_kills", "expected_wounds"):
        keys = set(old[section]) | set(data[section])
        for key in sorted(keys):
            a, b = old[section].get(key, "<missing>"), data[section].get(key, "<missing>")
            if a != b:
                failures.append(f"{section}[{key}]: {a!r} -> {b!r}")

    print(f"compared {n_kills} expected_kills + {n_wounds} expected_wounds entries")
    if failures:
        print(f"FAIL: {len(failures)} differences")
        for line in failures[:20]:
            print("  " + line)
        return 1
    print("PASS: identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
