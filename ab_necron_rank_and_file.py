"""A/B probes for Etappe 2 - Deathmarks, Flayed Ones, Cryptothralls, Tomb Blades.

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

SUITE = "test_necron_rank_and_file.py"
SHEETS = "test_necron_datasheets.py"

PROBES = [
    # --- Hyperspace Hunters -------------------------------------------------
    ("a CANCELLED ingress hands out a free volley",
     [("game/hyperspace_hunters.py",
       "        if self.ingress_controller is None:\n            return True\n"
       "        return squad in getattr(self.ingress_controller, \"ingressed_this_turn\", ())",
       "        return True")],
     [SUITE]),

    ("the 18\" range stops being measured",
     [("game/hyperspace_hunters.py",
       "            if not in_range(squad, arrival):\n                continue",
       "            pass")],
     [SUITE]),

    ("it fires in the hunter's OWN Movement phase too",
     [("game/hyperspace_hunters.py",
       "            if phase_owner is not None and squad.owner == phase_owner:\n"
       "                continue",
       "            pass")],
     [SUITE]),

    ("the \"must only target that enemy unit\" restriction is dropped",
     [("game/hyperspace_hunters.py",
       "            started = self.shooting_controller.start_reactive_shooting(\n"
       "                squad, restrict_to=arrival)",
       "            started = self.shooting_controller.start_reactive_shooting(squad)")],
     [SUITE]),

    # --- Flesh Hunger -------------------------------------------------------
    # The whole point of this rule is that the threshold is NOT a number. A
    # test that pinned a 6 or a 5 would pass with either of the next two.
    ("the crit threshold becomes a fixed 5 instead of the hit roll",
     [("game/crit_hit.py",
       "        if (_flesh_hunger_applies(model, target_squad)):\n"
       "            needed = hit_threshold",
       "        if (_flesh_hunger_applies(model, target_squad)):\n"
       "            needed = 5")],
     [SUITE]),

    ("...and Below Half-strength becomes at-or-below half",
     [("game/crit_hit.py",
       "    from game.squad import is_below_half_strength\n"
       "    return is_below_half_strength(target_squad)",
       "    from game.squad import is_at_half_strength\n"
       "    return is_at_half_strength(target_squad)")],
     [SUITE]),

    ("...and RANGED attacks get it as well",
     [("game/crit_hit.py",
       "        if (_flesh_hunger_applies(model, target_squad)):",
       "        pass\n    if True:\n        if (_flesh_hunger_applies(model, target_squad)):")],
     [SUITE]),

    # --- Bound Creation ------------------------------------------------------
    ("Bound Creation gives the 4+ to every model in the unit",
     [("game/cryptothralls.py",
       "    if not _model_is_cryptek(model, squad):\n        return \"-\"",
       "    pass")],
     [SUITE]),

    ("...and it never reaches the Feel No Pain chain",
     [("game/feel_no_pain.py",
       "    from game.cryptothralls import bound_creation_feel_no_pain\n"
       "    best = _better_threshold(best, bound_creation_feel_no_pain(model))",
       "    pass")],
     [SUITE]),

    # --- Systematic Vigour ----------------------------------------------------
    ("the 2+ becomes a 4+",
     [("game/cryptothralls.py",
       "SYSTEMATIC_VIGOUR_THRESHOLD = 2",
       "SYSTEMATIC_VIGOUR_THRESHOLD = 4")],
     [SUITE]),

    ("the \"has not fought this phase\" clause is dropped - the one its two "
     "siblings do not print",
     [("game/cryptothralls.py",
       "        return not self._has_fought(squad)",
       "        return True")],
     [SUITE]),

    ("a Necron Warrior is eligible too",
     [("game/cryptothralls.py",
       "        if not is_cryptothrall(model):\n            return False",
       "        pass")],
     [SUITE]),

    # --- Cryptek Retinue ------------------------------------------------------
    ("the retinue goes back to being a SUPPORT unit",
     [("game/attached_units.py",
       '    if all(getattr(m.profile, "cryptek_retinue", False) for m in squad.models):\n'
       "        return RETINUE",
       "    pass")],
     [SUITE]),

    ("any host will do - the CRYPTEK clause is dropped",
     [("game/cryptothralls.py",
       "    if not host_is_led_by_cryptek(host):\n"
       "        errors.append(\n"
       '            "%s is not being led by a CRYPTEK INFANTRY model." % host.name)',
       "    pass")],
     [SUITE]),

    ("a SECOND retinue may join the same host",
     [("game/cryptothralls.py",
       "    if already_joined and retinue not in already_joined:\n"
       "        errors.append(\n"
       '            "%s already has a CRYPTOTHRALLS unit joined to it." % host.name)',
       "    pass")],
     [SUITE]),

    ("the join offer falls back to Support Artillery",
     [("game/formations.py",
       "    if attached_units.attachment_role(joiner) == attached_units.RETINUE:\n"
       "        return CRYPTEK_RETINUE",
       "    pass")],
     [SUITE]),

    # --- Shieldvanes ----------------------------------------------------------
    # A TRADE, so each half is probed on its own: a fix that only carried the
    # good half would leave the unit with a 3+ save AND its printed 12".
    ("the save override never reaches damage_resolution",
     [("game/damage_resolution.py",
       "    _sv_override = tomb_blade_wargear.save_override(model)",
       "    _sv_override = None")],
     [SUITE]),

    ("the WORSE move is folded the usual better() way, so the 12\" survives",
     [("game/coldstar.py",
       "    _tb = tomb_blade_wargear.movement_override_in(model)\n"
       "    if _tb is not None:\n        base = _tb",
       "    _tb = tomb_blade_wargear.movement_override_in(model)\n"
       "    if _tb is not None:\n        base = max(base, _tb)")],
     [SUITE]),

    # --- Nebuloscope ----------------------------------------------------------
    ("[IGNORES COVER] is written onto the SHARED weapon class",
     [("game/tomb_blade_wargear.py",
       "    out = copy.copy(weapon)\n    out.ignores_cover = True\n    return out",
       "    weapon.ignores_cover = True\n    return weapon")],
     [SUITE]),

    ("...and melee weapons get it too",
     [("game/tomb_blade_wargear.py",
       '    if getattr(weapon, "weapon_type", None) != RANGED:\n        return weapon',
       "    pass")],
     [SUITE]),

    ("...and the grant never reaches the ranged adjuster chain",
     [("game/shooting.py",
       "        weapon = tomb_blade_wargear.adjusted_weapon(weapon, pairs[0][0])",
       "        pass")],
     [SUITE]),

    # --- Shadowloom -----------------------------------------------------------
    ("one shadowloom grants the UNIT Stealth - 24.33 read as any() not all()",
     [("game/squad.py",
       "    return attached_units.unit_has_ability(\n"
       "        squad, tomb_blade_wargear.model_has_stealth)",
       "    return any(tomb_blade_wargear.model_has_stealth(m)\n"
       "               for m in (squad.models or []))")],
     [SUITE]),

    # --- Evasion Engrams -------------------------------------------------------
    ("it borrows its neighbours' Engagement Range clause, which it does not print",
     [("game/evasion_engrams.py",
       "    return unit_has_evasion_engrams(squad)\n\n\nclass EvasionEngramsController",
       "    from game import engagement\n"
       "    return (unit_has_evasion_engrams(squad)\n"
       "            and not engagement.is_engaged(squad, all_tokens))\n\n\n"
       "class EvasionEngramsController")],
     [SUITE]),

    ("its move mode stops being waited on at a phase change",
     [("game/movement.py",
       '        "chronometron", "evasion_engrams",',
       '        "chronometron",')],
     [SUITE]),

    # --- the offering seams -----------------------------------------------------
    # "Gebaut, aber nie GEFUETTERT" is the class that has bitten this repo six
    # times, and no suite drives main(), so these probe the wiring directly.
    ("Evasion Engrams is never offered after shooting",
     [("main.py",
       "    shooting_controller.on_squad_finished_shooting.append("
       "evasion_engrams_controller.offer_after_shooting)",
       "    pass")],
     [SUITE]),

    ("Hyperspace Hunters is never fed by the ingress listener",
     [("main.py",
       "    ingress_controller.on_ingress_resolved.append(\n"
       "        lambda squad: hyperspace_hunters_controller.offer_on_arrival(\n"
       "            squad, turn_tracker.turn_owner))",
       "    pass")],
     [SUITE]),

    ("Systematic Vigour is never fed by the death sweep",
     [("main.py",
       "        systematic_vigour_controller.intercept_destroyed(_swept)",
       "        pass")],
     [SUITE]),

    ("...and never drained when the attacker finishes",
     [("main.py",
       "            systematic_vigour_controller.resolve_after_attacks(_fighter)",
       "            pass")],
     [SUITE]),

    ("Evasion Engrams' Confirm button never reaches its controller",
     [("main.py",
       "            evasion_engrams_controller=evasion_engrams_controller,",
       "")],
     [SUITE]),

    # --- weapons and sprites -----------------------------------------------------
    ("the twin gauss blaster loses [TWIN-LINKED]",
     [("game/weapons.py",
       '    name = "Twin gauss blaster"\n    twin_linked = True',
       '    name = "Twin gauss blaster"')],
     [SUITE]),

    ("the Deathmarks' art key is dropped",
     [("game/sprites.py",
       '    "Deathmarks": "Deathmarks",',
       "")],
     [SUITE, SHEETS]),
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
