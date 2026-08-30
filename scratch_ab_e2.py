"""A/B probes for Etappe 2 (the attack chains)."""
import io, os, shutil, subprocess, sys

BASE = 215
PROBES = [
    # --- Assassins' Eye ----------------------------------------------------
    ("Assassins' Eye: the AP is worsened instead of improved",
     "game/enh_assassins_eye.py",
     "    improved.ap = weapon.ap - ASSASSINS_EYE_AP_BONUS",
     "    improved.ap = weapon.ap + ASSASSINS_EYE_AP_BONUS"),
    ("Assassins' Eye: the CHARACTER condition is dropped",
     "game/enh_assassins_eye.py",
     "    return (enhancements.is_active(squad, ASSASSINS_EYE)\n            and target_is_character(target_squad))",
     "    return enhancements.is_active(squad, ASSASSINS_EYE)"),
    ("Assassins' Eye: it mutates the shared weapon",
     "game/enh_assassins_eye.py",
     "    improved = copy.copy(weapon)\n    improved.ap = weapon.ap - ASSASSINS_EYE_AP_BONUS\n    return improved",
     "    weapon.ap = weapon.ap - ASSASSINS_EYE_AP_BONUS\n    return weapon"),
    ("Assassins' Eye: it reaches melee weapons too",
     "game/enh_assassins_eye.py",
     '    if weapon is None or getattr(weapon, "weapon_type", None) != RANGED:\n        return weapon',
     "    if weapon is None:\n        return weapon"),
    ("Assassins' Eye: it never reaches the ranged chain",
     "game/shooting.py",
     "        weapon = enh_assassins_eye.adjusted_weapon(\n            weapon, self.active_squad, target_squad)",
     "        pass"),
    ("Assassins' Eye: the CHARACTER test reads one model, not the unit",
     "game/enh_assassins_eye.py",
     "    return attached_units.unit_has_keyword(\n        target_squad, lambda m: getattr(m.profile, \"character\", False))",
     "    return getattr(target_squad.models[0].profile, \"character\", False)"),
    # --- the three psychic-weapon ones -------------------------------------
    ("Psychic Destroyer: it reaches a MELEE psychic weapon",
     "game/enh_psychic_weapons.py",
     "    if _is_ranged_psychic(weapon) and _bearer_has(model, PSYCHIC_DESTROYER):",
     "    if _is_psychic(weapon) and _bearer_has(model, PSYCHIC_DESTROYER):"),
    ("Psychic Destroyer: it reaches a non-psychic gun",
     "game/enh_psychic_weapons.py",
     '    return _is_psychic(weapon) and getattr(weapon, "weapon_type", None) == RANGED',
     '    return getattr(weapon, "weapon_type", None) == RANGED'),
    # The bug an earlier version of this module really had: a rolled Damage
    # skipped outright, which is inert on four of its five likeliest bearers.
    ("Psychic Destroyer: a ROLLED Damage is skipped",
     "game/enh_psychic_weapons.py",
     "        if weapon.damage_notation is not None:\n            out.damage_notation = DiceNotation(\n                weapon.damage_notation.sides,\n                weapon.damage_notation.bonus + PSYCHIC_DESTROYER_DAMAGE)",
     "        pass"),
    ("Psychic Destroyer: the bonus lands on the DIE, not the bonus",
     "game/enh_psychic_weapons.py",
     "                weapon.damage_notation.sides,\n                weapon.damage_notation.bonus + PSYCHIC_DESTROYER_DAMAGE)",
     "                weapon.damage_notation.sides + PSYCHIC_DESTROYER_DAMAGE,\n                weapon.damage_notation.bonus)"),
    ("Psychic Destroyer: the preview value stops moving with the notation",
     "game/enh_psychic_weapons.py",
     "        out.damage = weapon.damage + PSYCHIC_DESTROYER_DAMAGE",
     "        out.damage = weapon.damage"),
    ("Seersight Strike: it narrows to RANGED, which its card does not say",
     "game/enh_psychic_weapons.py",
     "    if not _is_psychic(weapon) or not _bearer_has(model, SEERSIGHT_STRIKE):",
     "    if not _is_ranged_psychic(weapon) or not _bearer_has(model, SEERSIGHT_STRIKE):"),
    ("Seersight Strike: the granted pair REPLACES the printed entries",
     "game/enh_psychic_weapons.py",
     "    entries = printed if isinstance(printed[0], tuple) else (printed,)\n    return tuple(entries) + tuple(extra)",
     "    return tuple(extra)"),
    ("Seersight Strike: the thresholds slip to 3+",
     "game/enh_psychic_weapons.py",
     'SEERSIGHT_STRIKE_ANTI = (("MONSTER", 2), ("VEHICLE", 2))',
     'SEERSIGHT_STRIKE_ANTI = (("MONSTER", 3), ("VEHICLE", 3))'),
    ("Stone of Eldritch Fury: the range bonus never reaches weapon_range",
     "game/weapon_range.py",
     "            + enh_psychic_weapons.range_bonus_in(model, weapon))",
     "            + 0.0)"),
    ("Stone of Eldritch Fury: it is 6\" like its three neighbours",
     "game/enh_psychic_weapons.py",
     "STONE_OF_ELDRITCH_FURY_RANGE_IN = 12.0",
     "STONE_OF_ELDRITCH_FURY_RANGE_IN = 6.0"),
    ("psychic weapons: the adjuster never reaches the chain",
     "game/shooting.py",
     "        weapon = enh_psychic_weapons.adjusted_weapon(weapon, pairs[0][0] if pairs else None)",
     "        pass"),
    ("psychic weapons: the attack key drops its term",
     "game/shooting.py",
     "            enh_psychic_weapons.attack_key(model))",
     "            )"),
    # --- Aspect of Murder --------------------------------------------------
    ("Aspect of Murder: it reaches ranged weapons too",
     "game/enh_aspect_of_murder.py",
     '    if getattr(weapon, "weapon_type", None) == RANGED:\n        return weapon              # "MELEE weapons", as printed',
     "    if False:\n        return weapon"),
    ("Aspect of Murder: the [PRECISION] grant is dropped",
     "game/enh_aspect_of_murder.py",
     "    out.precision = True",
     "    pass"),
    ("Aspect of Murder: the Damage bonus is dropped",
     "game/enh_aspect_of_murder.py",
     "    out.damage = weapon.damage + ASPECT_OF_MURDER_DAMAGE",
     "    pass"),
    ("Aspect of Murder: a ROLLED Damage is skipped",
     "game/enh_aspect_of_murder.py",
     "    if weapon.damage_notation is not None:\n        out.damage_notation = DiceNotation(\n            weapon.damage_notation.sides,\n            weapon.damage_notation.bonus + ASPECT_OF_MURDER_DAMAGE)",
     "    pass"),
    ("Aspect of Murder: it mutates the shared weapon",
     "game/enh_aspect_of_murder.py",
     "    out = copy.copy(weapon)",
     "    out = weapon"),
    ("Aspect of Murder: it never reaches the melee chain",
     "game/fight.py",
     "        weapon = enh_aspect_of_murder.adjusted_weapon(weapon, pairs[0][0] if pairs else None)",
     "        pass"),
    ("Aspect of Murder: the melee attack key drops its term",
     "game/fight.py",
     "            enh_aspect_of_murder.attack_key(model))",
     "            )"),
    # --- the rename and the split ------------------------------------------
    ("split: crit_ap stops re-exporting",
     "game/crit_ap.py",
     "from game.critical_wound_split import (  # noqa: F401\n    adjusted_weapon, applies, label, sources)",
     "adjusted_weapon = applies = label = sources = None"),
    ("split: the RANGED test goes back to the front door",
     "game/critical_wound_split.py",
     "    if weapon is None:\n        return []",
     "    if weapon is None or weapon.weapon_type != RANGED:\n        return []"),
    ("split: Stave of Kurnous is dropped as a source",
     "game/critical_wound_split.py",
     "    if enh_stave_of_kurnous.applies(squad):\n        out.append(STAVE_OF_KURNOUS)",
     "    if False:\n        out.append(STAVE_OF_KURNOUS)"),
    ("split: its [PRECISION] grant is dropped",
     "game/critical_wound_split.py",
     "        elif source == STAVE_OF_KURNOUS:\n            adjusted = enh_stave_of_kurnous.adjusted_weapon(adjusted)",
     "        elif source == STAVE_OF_KURNOUS:\n            pass"),
    ("split: the melee twin never computes the split",
     "game/fight.py",
     "        self._pending_crit_split = (crits - self._devastating_crits) if _split else 0",
     "        self._pending_crit_split = 0"),
    ("split: the melee crits stay in the normal save",
     "game/fight.py",
     "        normal_wounds = (wounds - self._devastating_crits - self._pending_crit_split\n                         + self._lethal_hits_auto_wounds)",
     "        normal_wounds = wounds - self._devastating_crits + self._lethal_hits_auto_wounds"),
    # NOTE: this probe is the one that was left applied when git checkout wiped
    # the file - it is why the rescued .pyc carries `elif False:` here. Anchored
    # on the elif line alone now, so an intervening comment cannot stale it.
    ("split: the melee sub-step is never dispatched",
     "game/fight.py",
     "        elif self._pending_crit_split > 0:\n            # Every wound in this roll was critical",
     "        elif False:\n            # Every wound in this roll was critical"),
    ("split: the precision question uses the group's weapon, not the split one",
     "game/fight.py",
     "            if self._precision_choice_needed(split_weapon, target_squad):",
     "            if self._precision_choice_needed(weapon, target_squad):"),
    # --- Stave of Kurnous's own clauses ------------------------------------
    ("Stave of Kurnous: the TITANIC exclusion is dropped",
     "game/enh_stave_of_kurnous.py",
     "    return wraith_construct.is_non_titanic_wraith_construct(squad)",
     "    return wraith_construct.is_wraith_construct_unit(squad)"),
    ("Stave of Kurnous: it mutates the shared weapon",
     "game/enh_stave_of_kurnous.py",
     "    granted = copy.copy(weapon)\n    granted.precision = True\n    return granted",
     "    weapon.precision = True\n    return weapon"),
    ("Stave of Kurnous: main.py stops driving its Command phase",
     "main.py",
     "            stave_of_kurnous_controller.begin_command_phase(turn_tracker.turn_owner)",
     "            pass"),
]

SUITE = "test_aeldari_enhancements.py"


def run():
    for root, dirs, _ in os.walk("."):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True)
    for line in (out.stdout + out.stderr).splitlines():
        if "checks passed" in line:
            return int(line.split("/")[0].strip())
    return -1


bad = []
for label, path, old, new in PROBES:
    src = io.open(path, encoding="utf-8").read()
    if src.count(old) != 1:
        print("NO ANCHOR  %-4s %s" % (src.count(old), label))
        bad.append(label)
        continue
    io.open(path, "w", encoding="utf-8", newline="\n").write(src.replace(old, new, 1))
    try:
        got = run()
    finally:
        io.open(path, "w", encoding="utf-8", newline="\n").write(src)
    bites = -1 < got < BASE
    tag = "bites" if bites else ("CRASH" if got == -1 else "NO BITE")
    print("%-9s %d/%d  %s" % (tag, got, BASE, label))
    if not bites:
        bad.append(label)

print("\nprobes: %d, all biting: %s" % (len(PROBES), not bad))
for b in bad:
    print("  !", b)
