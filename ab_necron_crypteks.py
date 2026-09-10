"""A/B probes for Etappe 1 - the Necron Crypteks.

Each probe restores ONE printed clause to a pre-fix state AT THE SOURCE and
must make the suite that covers it go red. A probe that does not bite is a
finding about the TEST, not an all-clear.

Run these ALONE. A probe rewrites the file it probes and restores it in a
`finally`; a suite, measurement or commit started alongside one reads the
mutated tree (see the probe-runs-are-exclusive note, and commit 412dc4a).
"""
import io
import os
import re
import shutil
import subprocess
import sys

SUITE = "test_necron_crypteks.py"

PROBES = [
    # --- Timesplinter Mantle ------------------------------------------------
    ("the melee -1 never reaches the fight chain",
     [("game/fight.py",
       "        modifiers.extend(timesplinter_mantle.hit_modifiers(target_squad))",
       "        pass")],
     [SUITE]),

    # The obvious probe here would remove an extra Stealth source from
    # squad_has_stealth(). There is none to remove: one WAS written, this
    # driver reported NO BITE for it, and the measurement showed 19.04's
    # component-wise unit_has_ability() already answers True on its own. The
    # redundant source was deleted and the finding written into both
    # docstrings. What is probed instead is the reading the mantle's own
    # predicate uses, immediately below.

    ("the mantle is read with unit_wide_ability instead of 19.03 pooling",
     [("game/timesplinter_mantle.py",
       "    return unit_has_keyword(squad, lambda m: getattr(m.profile, \"timesplinter_mantle\", False))",
       "    return all(getattr(m.profile, \"timesplinter_mantle\", False)\n"
       "               for m in (squad.models or []))")],
     [SUITE]),

    # --- Chronometron -------------------------------------------------------
    ("the printed Engagement Range condition is dropped",
     [("game/chronometron.py",
       "    return unit_has_chronometron(squad) and not engagement.is_engaged(squad, all_tokens)",
       "    return unit_has_chronometron(squad)")],
     [SUITE]),

    ("its move mode stops being waited on at a phase change",
     [("game/movement.py",
       '        "retro_thrusters", "retro_thrusters_fall_back",\n        "chronometron",',
       '        "retro_thrusters", "retro_thrusters_fall_back",')],
     [SUITE]),

    # --- the Psychomancer ---------------------------------------------------
    ("the -1 on the Battle-Shock test is dropped",
     [("game/psychomancer.py",
       "BATTLE_SHOCK_PENALTY = 1",
       "BATTLE_SHOCK_PENALTY = 0")],
     [SUITE]),

    ("Nightmare Shroud stops checking Starting Strength",
     [("game/psychomancer.py",
       "                              NIGHTMARE_SHROUD_RANGE_IN, extra=below_starting_strength)",
       "                              NIGHTMARE_SHROUD_RANGE_IN)")],
     [SUITE]),

    ("Nightmare Shroud fires in its OWN Command phase too",
     [("game/psychomancer.py",
       "            if not has_nightmare_shroud(squad) or squad.owner == command_phase_player:",
       "            if not has_nightmare_shroud(squad):")],
     [SUITE]),

    ("Harbinger of Despair loses its once-per-turn ledger",
     [("game/psychomancer.py",
       "        return (has_harbinger(squad) and id(squad) not in self._used_this_turn\n"
       "                and bool(self.candidates(squad)))",
       "        return has_harbinger(squad) and bool(self.candidates(squad))")],
     [SUITE]),

    ("Harbinger offers in the opponent's phase as well",
     [("game/psychomancer.py",
       "            if squad.owner != phase_owner or not self.can_use(squad):",
       "            if not self.can_use(squad):")],
     [SUITE]),

    # --- Master Chronomancer -------------------------------------------------
    ("the 4+ never reaches the invulnerable chain",
     [("game/invulnerable_save.py",
       '    from game import attached_units\n'
       '    if attached_units.leader_ability(squad, "master_chronomancer"):\n'
       '        save = _better(save, MASTER_CHRONOMANCER_INVULNERABLE_SAVE)',
       "    pass")],
     [SUITE]),

    ("...and it is granted without LEADING anything",
     [("game/invulnerable_save.py",
       '    if attached_units.leader_ability(squad, "master_chronomancer"):',
       '    if squad is not None and any(getattr(m.profile, "master_chronomancer", False)\n'
       '                                 for m in (squad.models or [])):')],
     [SUITE]),

    # --- The Stars Are Right -------------------------------------------------
    ("\"triple\" becomes \"+2\" - the arithmetic a flag-only test cannot see",
     [("game/the_stars_are_right.py",
       "    out.attacks = weapon.attacks * MULTIPLIER\n"
       "    out.strength = weapon.strength * MULTIPLIER",
       "    out.attacks = weapon.attacks + 2\n"
       "    out.strength = weapon.strength + 2")],
     [SUITE]),

    ("every successful Wound stops being a Critical Wound",
     [("game/the_stars_are_right.py",
       "    return min(default_crit, wound_threshold)",
       "    return default_crit")],
     [SUITE]),

    ("...and the grant is allowed to make an [ANTI-X] threshold WORSE",
     [("game/the_stars_are_right.py",
       "    return min(default_crit, wound_threshold)",
       "    return wound_threshold")],
     [SUITE]),

    ("it stops naming the weapon, so any melee weapon is tripled",
     [("game/the_stars_are_right.py",
       "    if not isinstance(weapon, StaffOfTomorrowProfile):\n        return weapon\n",
       "")],
     [SUITE]),

    ("the once-per-battle ledger is cleared by the phase reset",
     [("game/the_stars_are_right.py",
       "                if getattr(model, \"stars_are_right_active\", False):\n"
       "                    model.stars_are_right_active = False",
       "                if getattr(model, \"stars_are_right_active\", False):\n"
       "                    model.stars_are_right_active = False\n"
       "        self._used = set()")],
     [SUITE]),

    # WHICH MODEL the crit half is asked about. An earlier version of this
    # probe only widened the early-out above the call and reported NO BITE -
    # correctly, because the module re-checks the model itself, so that
    # early-out is redundant defence rather than the gate. What can really go
    # wrong is asking about the WRONG model, which is what this does: the
    # squad's first model instead of the attacking group's.
    ("the crit half asks about the unit's first model, not the attacker",
     [("game/fight.py",
       # The same line appears in _crit_note(), so the anchor carries the one
       # that follows it in _wound_crit() to stay unique.
       '        model = self.current_group["pairs"][0][0] if self.current_group else None\n'
       "        if not the_stars_are_right.is_active(model):",
       "        model = (self.fighting_squad.models[0]\n"
       "                 if self.fighting_squad and self.fighting_squad.models else None)\n"
       "        if not the_stars_are_right.is_active(model):")],
     [SUITE]),

    # --- the 19.01 role correction -------------------------------------------
    ("the Crypteks go back to carrying the Leader role",
     [("game/units.py",
       "class ChronomancerProfile(UnitProfile):",
       "class ChronomancerProfile(UnitProfile):\n    leader = True\n    support = False")],
     [SUITE]),

    # --- the offering seams ---------------------------------------------------
    # "Gebaut, aber nie GEFUETTERT" is the class that has bitten this repo six
    # times, and no suite drives main(), so these probe the wiring directly.
    ("Chronometron is never offered after shooting",
     [("main.py",
       "    shooting_controller.on_squad_finished_shooting.append("
       "chronometron_controller.offer_after_shooting)",
       "    pass")],
     [SUITE]),

    ("Nightmare Shroud's queue is never drained",
     [("main.py",
       "                        nightmare_shroud_controller.on_dice_acknowledged()",
       "                        pass")],
     [SUITE]),

    ("Chronometron's Confirm button never reaches its controller",
     [("main.py",
       "            chronometron_controller=chronometron_controller,",
       "")],
     [SUITE]),

    ("The Stars Are Right is never offered",
     [("main.py",
       "            the_stars_are_right_controller.offer_at_start_of_fight_phase(\n"
       "                {t.squad for t in state.tokens if t.squad is not None})",
       "            pass")],
     [SUITE]),

    # --- sprites --------------------------------------------------------------
    ("Orikan's art key is dropped, so he falls back to no art",
     [("game/sprites.py",
       '    "Orikan The Diviner": "Orikan the Diviner",',
       "")],
     [SUITE]),
]


def clear_cache():
    """The documented __pycache__ race: these probes rewrite and restore inside
    the same second, so a stale .pyc reports the PREVIOUS run's result."""
    for root, dirs, _ in os.walk("."):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)


def run(suite):
    if not os.path.exists(suite):
        return None, None
    clear_cache()
    out = subprocess.run([sys.executable, suite], capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    m = re.search(r"(\d+)/(\d+) checks passed", out.stdout + out.stderr)
    if not m:
        return None, None          # crashed - counts as red
    return int(m.group(1)), int(m.group(2))


baselines = {}
for _, _, suites in PROBES:
    for s in suites:
        if s not in baselines:
            baselines[s] = run(s)
print("baselines:")
for s, (g, t) in baselines.items():
    print("   %-40s %s" % (s, "MISSING" if g is None else "%d/%d" % (g, t)))
print()

bad = []
for label, edits, suites in PROBES:
    originals = {}
    ok = True
    for path, old, new in edits:
        src = io.open(path, encoding="utf-8").read()
        if src.count(old) != 1:
            print("NO ANCHOR (%d)  %s" % (src.count(old), label))
            ok = False
            break
        originals[path] = src
        io.open(path, "w", encoding="utf-8", newline="\n").write(src.replace(old, new, 1))
    if not ok:
        for p, s in originals.items():
            io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        bad.append(label)
        continue
    try:
        verdicts = []
        for s in suites:
            base = baselines.get(s, (None, None))[0]
            got, tot = run(s)
            if base is None:
                verdicts.append((s, "NO SUITE", ""))
            elif got is None:
                verdicts.append((s, "BITES", "(crashed - counts as red)"))
            elif got < base:
                verdicts.append((s, "BITES", "%d/%d" % (got, tot)))
            else:
                verdicts.append((s, "NO BITE", "%d/%d" % (got, tot)))
    finally:
        for p, s in originals.items():
            io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    bit = any(v == "BITES" for _, v, _ in verdicts)
    detail = "  ".join("%s %s" % (v, d) for _s, v, d in verdicts)
    print("%-9s %-62s %s" % ("bites" if bit else "NO BITE", label[:62], detail))
    if not bit:
        bad.append(label)

clear_cache()
print("\nprobes: %d, all biting: %s" % (len(PROBES), not bad))
for b in bad:
    print("  !", b)
raise SystemExit(1 if bad else 0)
