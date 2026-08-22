"""Pick game/stim_injectors.py's MIN_EXPECTED_WOUNDS_SAVED from the data
rather than from a guess, and report what it costs.

The gate exists so a stratagem whose WHEN fires on every enemy target
selection does not interrupt the game constantly. Two things have to be true
for the threshold to be defensible:

  * it separates chip damage from real threats, and
  * it does not hang on any single datasheet - i.e. it sits in a GAP in the
    distribution, not in the middle of a cluster.

Measures every attacker in both factions against every BATTLESUIT unit it
could legally target (the stratagem's own TARGET clause), in both the ranged
and the melee direction, and prints the sorted distribution either side of the
threshold plus which datasheets sit closest to it.
"""

import sys

from game.factions import build_squad
from game.factions import orks, tau_empire
from game.stim_injectors import MIN_EXPECTED_WOUNDS_SAVED, expected_wounds_saved, is_battlesuit_unit


def _datasheets(module):
    seen = {}
    for name in dir(module):
        obj = getattr(module, name)
        if hasattr(obj, "model_lines") and hasattr(obj, "name") and name.isupper():
            seen.setdefault(obj.name, (name, obj))
    return [v for _, v in sorted(seen.items())]


def build_all():
    out = []
    for module, owner in ((tau_empire, "Player 1"), (orks, "Player 2")):
        for const_name, ds in _datasheets(module):
            try:
                out.append((const_name, build_squad(ds, owner, name=const_name)))
            except Exception:
                pass
    return out


def main():
    squads = build_all()
    targets = [(n, s) for n, s in squads if is_battlesuit_unit(s)]
    print(f"{len(squads)} datasheets built; {len(targets)} of them are BATTLESUIT units "
          f"(the only legal targets of this stratagem):")
    for n, _ in targets:
        print(f"    {n}")

    rows = []
    for a_name, attacker in squads:
        for t_name, target in targets:
            if attacker is target:
                continue
            for melee in (False, True):
                saved = expected_wounds_saved(attacker, target, melee=melee)
                if saved <= 0.0:
                    continue  # no weapons of that kind at all - never an offer regardless
                rows.append((saved, a_name, t_name, "melee" if melee else "ranged"))

    rows.sort()
    below = [r for r in rows if r[0] < MIN_EXPECTED_WOUNDS_SAVED]
    above = [r for r in rows if r[0] >= MIN_EXPECTED_WOUNDS_SAVED]

    print(f"\n{len(rows)} attacker-vs-BATTLESUIT matchups with any relevant weapon.")
    print(f"threshold MIN_EXPECTED_WOUNDS_SAVED = {MIN_EXPECTED_WOUNDS_SAVED}")
    print(f"  suppressed (pointless): {len(below):4d}  ({100.0 * len(below) / max(1, len(rows)):.0f}%)")
    print(f"  offered   (worthwhile): {len(above):4d}  ({100.0 * len(above) / max(1, len(rows)):.0f}%)")

    print("\nthe gap the threshold sits in - 8 matchups either side:")
    for saved, a, t, kind in below[-8:]:
        print(f"   suppressed  {saved:6.3f}   {a} -> {t} ({kind})")
    print(f"  {'-' * 12} threshold {MIN_EXPECTED_WOUNDS_SAVED} {'-' * 12}")
    for saved, a, t, kind in above[:8]:
        print(f"   offered     {saved:6.3f}   {a} -> {t} ({kind})")

    if below and above:
        gap = above[0][0] - below[-1][0]
        print(f"\nnearest values straddling it: {below[-1][0]:.3f} / {above[0][0]:.3f}  (gap {gap:.3f})")

    print("\nworst offenders (would always be offered):")
    for saved, a, t, kind in rows[-6:]:
        print(f"   {saved:6.3f}   {a} -> {t} ({kind})")

    # A threshold that lands mid-cluster is fragile: a single datasheet change
    # would flip matchups across it. Report how sensitive the split is.
    for probe in (0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
        n = sum(1 for r in rows if r[0] >= probe)
        print(f"  at {probe:.2f}: {n:4d} offered ({100.0 * n / max(1, len(rows)):.0f}%)")

    # The number that actually matters for playability: can each BATTLESUIT
    # unit EVER be protected? A threshold that never fires for the toughest
    # unit in the army has quietly deleted the stratagem for that unit.
    print("\nper target unit - can it ever be protected?")
    for t_name, target in targets:
        mine = [r for r in rows if r[2] == t_name]
        if not mine:
            continue
        offered = [r for r in mine if r[0] >= MIN_EXPECTED_WOUNDS_SAVED]
        best = max(r[0] for r in mine)
        wounds = sum(m.profile.wounds for m in target.models)
        print(f"   {t_name:36s} {len(offered):3d}/{len(mine):3d} attacks offer   "
              f"best {best:.3f}   (unit has {wounds} wounds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
