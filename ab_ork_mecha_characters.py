"""A/B probes for the Mecha Orks characters (stage G2): the Big Mek in Mega Armour
(More Dakka, the Kustom Force Field, Fix Dat Armour Up), Ghazghkull Thraka (Da
Grand Warlord's Ladz, Makari, the Prophet aura), the army's Warlord (list load,
the builder, Da Boss), the cover-gate fix this stage made, and main.py's wiring.

Same driver as ab_ork_mecha_sheets.py: each probe restores one piece of a
plausible broken world AT THE SOURCE, runs the suite(s) that are supposed to catch
it, and puts the file back byte for byte. A probe that does NOT turn its suite red
is a finding about the TEST; one that CRASHES or HANGS a suite is a finding too.

EXCLUSIVE. This rewrites source files while it runs. No suite, measurement, edit
or commit may run beside it - and a parallel session must be told first. Every
replacement carries the marker AB-PROBE, so after a run

    git grep -n --untracked "AB-PROBE" -- . ":!ab_*.py" ":!CLAUDE*.md" ":!docs/*"

must come back empty. The driver hashes every probed file before the first probe
and after the last, and every suite run has a timeout.

game/factions/orks.py is CRLF: its anchors are single lines.

`--check` only verifies that every anchor is unique and the marker is absent,
writing nothing. `--only SUBSTRING` re-runs the probes whose label contains it.
"""

import hashlib
import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)
MARK = "  # AB-PROBE"
TIMEOUT_S = 300

def read(path):
    return io.open(path, encoding="utf-8", newline="").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def digest(path):
    return hashlib.sha1(read(path).encode("utf-8")).hexdigest()


def run(suite):
    """(passed, total, text); passed is None for a crash and "HANG" for a timeout."""
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    try:
        out = subprocess.run([sys.executable, suite], capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return "HANG", None, ""
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)

TK = "test_ork_mecha_characters.py"
EW = "test_event_chain_wiring.py"
WC = "test_weapon_characteristics.py"
AE = "test_aeldari_enhancements.py"
TT = "test_tau_characters.py"

WE = os.path.join("game", "weapons.py")
UN = os.path.join("game", "units.py")
OR = os.path.join("game", "factions", "orks.py")
PT = os.path.join("game", "factions", "orks_points.py")
SH = os.path.join("game", "shooting.py")
FI = os.path.join("game", "fight.py")
MD = os.path.join("game", "more_dakka.py")
KF = os.path.join("game", "kustom_force_field.py")
IS = os.path.join("game", "invulnerable_save.py")
FD = os.path.join("game", "fix_dat_armour_up.py")
WL = os.path.join("game", "warlord.py")
AIO = os.path.join("game", "army_io.py")
AR = os.path.join("game", "army_roster.py")
DB = os.path.join("game", "da_boss.py")
GL = os.path.join("game", "grand_warlords_ladz.py")
CLO = os.path.join("game", "conditional_lone_operative.py")
PR = os.path.join("game", "prophet_of_da_great_waaagh.py")
MK = os.path.join("game", "makari.py")
TR = os.path.join("game", "transport.py")
AG = os.path.join("ai", "agent_driver.py")
MAIN = "main.py"


# (label, [(path, anchor, replacement)], suites)
PROBES = [
    # ------------------------------------------------------ the cover gate fix
    ("cover split: handed the printed weapon again",
     [(SH, "        if self._cover_ignored_for_group(self._adjusted_weapon(pairs, target_squad), target_squad):",
       "        if self._cover_ignored_for_group(pairs[0][1], target_squad):" + MARK)], (EW,)),
    ("hit modifiers: the cover test handed the printed weapon again",
     [(SH, '        if (not self._cover_ignored_for_group(self._adjusted_weapon(group["pairs"], target_squad), target_squad)',
       "        if (not self._cover_ignored_for_group(weapon, target_squad)" + MARK)], (TK, EW)),

    # --------------------------------------------------------------- More Dakka
    ("shooting: More Dakka is not in the chain",
     [(SH, "        weapon = more_dakka.adjusted_weapon(weapon, self.active_squad, self.embarked_squads())",
       "        pass" + MARK)], (TK,)),
    ("More Dakka: no [IGNORES COVER]",
     [(MD, "        granted.ignores_cover = True", "        pass" + MARK)], (TK,)),
    ("More Dakka: no [SUSTAINED HITS 1]",
     [(MD, "        granted.sustained_hits = MORE_DAKKA_SUSTAINED_HITS", "        pass" + MARK)], (TK,)),
    ("More Dakka: [SUSTAINED HITS 1] without being riled up",
     [(MD, "    add_sustained = (riled_up.is_riled_up(squad)", "    add_sustained = (True" + MARK)], (TK,)),
    ("More Dakka: melee weapons too",
     [(MD, '    if (weapon is None or getattr(weapon, "weapon_type", None) != RANGED',
       "    if (weapon is None" + MARK)], (TK,)),
    ("More Dakka: a dead Big Mek still confers it",
     [(MD, '    return squad is not None and bool(unit_wide_ability(squad, "more_dakka"))',
       "    return squad is not None and any(m.profile.more_dakka for m in squad.models)" + MARK)], (TK,)),

    # ------------------------------------------------------ Kustom Force Field
    ("InSv: the Kustom Force Field is not asked",
     [(IS, "        save = _better(save, kustom_force_field.ranged_invulnerable_save(model))", "        pass" + MARK)],
     (TK,)),
    ("InSv: the Kustom Force Field against melee too",
     [(IS, '        save = _better(save, getattr(model.profile, "invulnerable_save_vs_melee", None))',
       '        save = _better(save, getattr(model.profile, "invulnerable_save_vs_melee", None)); '
       'save = _better(save, __import__("game.kustom_force_field", fromlist=["x"]).ranged_invulnerable_save(model))'
       + MARK)], (TK,)),
    ("Kustom Force Field: a dead bearer still shields",
     [(KF, '    return attached_units.unit_has_ability(squad, lambda m: getattr(m, "kustom_force_field", False))',
       '    return any(getattr(m, "kustom_force_field", False) for m in squad.models)' + MARK)], (TK,)),
    ("Kustom Force Field: the gear marks nothing",
     [(OR, "    token.kustom_force_field = True", "    pass" + MARK)], (TK,)),

    # ------------------------------------------------------- Fix Dat Armour Up
    ("Fix Dat: offered again after use",
     [(FD, '    if not has_ability(squad) or getattr(squad, "fix_dat_armour_up_used", False):',
       "    if not has_ability(squad):" + MARK)], (TK,)),
    ("Fix Dat: offered with nothing to heal",
     [(FD, "    return heal_rule.healable_wounds(squad) > 0", "    return True" + MARK)], (TK,)),
    ("Fix Dat: the use is not spent",
     [(FD, "        squad.fix_dat_armour_up_used = True", "        pass" + MARK)], (TK,)),
    ("Fix Dat: the AI is prompted like a human",
     [(FD, "            if squad.owner in self.auto_players or self.decision_manager is None:",
       "            if self.decision_manager is None:" + MARK)], (TK,)),
    ("Fix Dat: the AI verdict is not asked",
     [(FD, "                if self.verdict is None or self.verdict(squad):", "                if True:" + MARK)], (TK,)),
    ("AI: Fix Dat on a scratch",
     [(AG, "    return squad is not None and heal_rule.healable_wounds(squad) >= FIX_DAT_ARMOUR_UP_MIN_HEALABLE",
       "    return squad is not None" + MARK)], (TK,)),
    ("main.py: Fix Dat is never begun",
     [(MAIN, "            fix_dat_armour_up_controller.begin_command_phase(state.all_squads(), turn_tracker.turn_owner)",
       "            pass" + MARK)], (TK,)),
    ("main.py: Fix Dat has no placer",
     [(MAIN, "    fix_dat_armour_up_controller.placer = return_placement_controller", "    pass" + MARK)], (TK,)),

    # ----------------------------------------------------------------- Warlord
    ("Warlord: two may be named",
     [(WL, "    if len(named) > 1:", "    if False:" + MARK)], (TK,)),
    ("Warlord: a non-CHARACTER may be named",
     [(WL, "        if not is_character_entry(spec):", "        if False:" + MARK)], (TK,)),
    ("Warlord: a C'tan may be named",
     [(WL, "        if may_not_be_warlord(spec):", "        if False:" + MARK)], (TK,)),
    ("Warlord: a Supreme Commander is not made the Warlord",
     [(WL, "            spec.warlord = True", "            pass" + MARK)], (TK,)),
    ("Warlord: another Warlord beside a Supreme Commander is accepted",
     [(WL, "        if named and named[0][0] is not spec:", "        if False:" + MARK)], (TK,)),
    ("army_io: the Warlord rules are not run",
     [(AIO, "        warlord.validate_roster(roster, problems)", "        pass" + MARK)], (TK,)),
    ("army_io: a leader's warlord flag is dropped",
     [(AIO, "                                  warlord=led.warlord))", "                                  ))" + MARK)],
     (TK,)),
    ("builder: the whole unit is marked (Menhirs too)",
     [(AR, "    for model in characters or squad.models:", "    for model in squad.models:" + MARK)], (TK,)),
    ("builder: a leader Warlord is not marked",
     [(AR, "                _mark_warlord(leader_squad)", "                pass" + MARK)], (TK,)),
    ("The Silent King is no Supreme Commander",
     [(UN, '    supreme_commander = True        # "Supreme Commander" - the unit\'s Warlord is Szarekh, enforced at list load (game/warlord.py)',
       "    supreme_commander = False" + MARK)], (TK,)),
    ("Shadowsun is no Supreme Commander",
     [(UN, '    # WARLORD") is enforced when a list is loaded - see game/warlord.py.' + NL + "    supreme_commander = True",
       '    # WARLORD") is enforced when a list is loaded - see game/warlord.py.' + NL + "    supreme_commander = False" + MARK)],
     (TK, TT)),

    # ------------------------------------------------------------------ Da Boss
    ("Da Boss: any Warlord pays",
     [(DB, '    if model is None or not getattr(model.profile, "da_boss", False):', "    if model is None:" + MARK)],
     (TK,)),
    ("Da Boss: pays twice in a round",
     [(DB, '            if getattr(model.squad, "da_boss_round", None) == battle_round:', "            if False:" + MARK)],
     (TK,)),
    ("Da Boss: the paid round is not stamped",
     [(DB, "            model.squad.da_boss_round = battle_round", "            pass" + MARK)], (TK,)),
    ("Warlord: a dead Warlord still counts",
     [(WL, "    return model if model is not None and not model.is_dead() else None", "    return model" + MARK)],
     (TK,)),
    ("main.py: Da Boss is not paid at the battle's start",
     [(MAIN, '''        # Da Boss: "at the start of the battle round" - round 1's CP here.''' + NL
       + "        da_boss_rule_controller.sync_battle_round(turn_tracker.battle_round)",
       '''        # Da Boss: "at the start of the battle round" - round 1's CP here.''' + NL + "        pass" + MARK)],
     (TK,)),

    # ------------------------------------------------ Da Grand Warlord's Ladz
    ("Ladz: any friendly unit counts (a VEHICLE too)",
     [(GL, "        if _is_orks_infantry(other) and squad.min_distance_to(other) <= GRAND_WARLORDS_LADZ_RANGE_IN:",
       "        if squad.min_distance_to(other) <= GRAND_WARLORDS_LADZ_RANGE_IN:" + MARK)], (TK,)),
    ("Ladz: enemy units count",
     [(GL, "        if other.owner != squad.owner:", "        if False:" + MARK)], (TK,)),
    ("Ladz: 6 inches",
     [(GL, "GRAND_WARLORDS_LADZ_RANGE_IN = 3.0", "GRAND_WARLORDS_LADZ_RANGE_IN = 6.0" + MARK)], (TK,)),
    ("Ladz: his own unit counts",
     [(GL, "        if other is None or other is squad or id(other) in seen or token.is_dead():",
       "        if other is None or id(other) in seen or token.is_dead():" + MARK)], (TK,)),
    ("Ladz: not registered as a conditional Lone Operative",
     [(CLO, "    (grand_warlords_ladz.grants_lone_operative," + NL
       + "     grand_warlords_ladz.GRAND_WARLORDS_LADZ_LONE_OPERATIVE_RANGE_IN),", MARK)], (TK, AE)),

    # ------------------------------------------------------------------ Prophet
    ("fight: the Prophet's +1 to hit is not read",
     [(FI, "        modifiers.extend(prophet_of_da_great_waaagh.hit_modifiers(self.fighting_squad, self.all_tokens))",
       "        pass" + MARK)], (TK,)),
    ("fight: the Prophet's +1 to wound is not read",
     [(FI, "        modifiers.extend(prophet_of_da_great_waaagh.wound_modifiers(self.fighting_squad, self.all_tokens))",
       "        pass" + MARK)], (TK,)),
    ("Prophet: 8 inches",
     [(PR, "PROPHET_RANGE_IN = 6.0", "PROPHET_RANGE_IN = 8.0" + MARK)], (TK,)),
    ("Prophet: an enemy Ghazghkull's aura counts",
     [(PR, '            and getattr(getattr(t, "squad", None), "owner", None) == owner]', "            ]" + MARK)],
     (TK,)),
    ("Prophet: a penalty to wound",
     [(PR, '    """+1 to wound (-1 on the threshold) for a melee attack inside the aura."""' + NL
       + "    return [Modifier(-1, PROPHET_NAME)]",
       '    """+1 to wound (-1 on the threshold) for a melee attack inside the aura."""' + NL
       + "    return [Modifier(1, PROPHET_NAME)]" + MARK)], (TK,)),
    ("Prophet: non-ORKS units count",
     [(PR, '    if not any(getattr(m.profile, "orks", False) for m in models):', "    if False:" + MARK)], (TK,)),

    # ------------------------------------------------------------------- Makari
    ("Makari: five units in any round",
     [(MK, '        return max(0, getattr(self.turn_tracker, "battle_round", 0) or 0)', "        return 5" + MARK)], (TK,)),
    ("Makari: the use is not spent",
     [(MK, "            bearer.makari_used = True", "            pass" + MARK)], (TK,)),
    ("Makari: not once per battle",
     [(MK, "        if self.is_used(squad.owner, squad):", "        if False:" + MARK)], (TK,)),
    ("Makari: units already riled up past the deadline are offered",
     [(MK, "            if current is not None and current >= deadline:", "            if False:" + MARK)], (TK,)),
    ("Makari: in any phase",
     [(MK, "        if tt.phase != PHASE_MOVEMENT or squad.owner != tt.turn_owner:",
       "        if squad.owner != tt.turn_owner:" + MARK)], (TK,)),
    ("Makari: pressing the button already spends it",
     [(MK, "        self._picking = (squad, [])", "        self._picking = (squad, []); squad.makari_used = True" + MARK)],
     (TK,)),
    ("main.py: Makari is not on the registry",
     [(MAIN, "    makari_controller = proactive_stratagems.add(MakariController(",
       "    makari_controller = (lambda controller: controller)(MakariController(" + MARK)], (TK,)),
    ("main.py: the AI is not handed Makari",
     [(MAIN, "            makari_controller=makari_controller,", "            " + MARK)], (TK,)),
    ("AI: Makari as soon as one unit gains",
     [(AG, "    if len(scored) < min(limit, MAKARI_MIN_UNITS):", "    if not scored:" + MARK)], (TK,)),
    ("AI: Makari on the units furthest from the enemy",
     [(AG, "    picked = [squad for _gap, _name, squad in sorted(scored)[:limit]]",
       "    picked = [squad for _gap, _name, squad in sorted(scored, reverse=True)[:limit]]" + MARK)], (TK,)),
    ("AI: the Movement handler never asks Makari",
     [(AG, "    if _handle_makari(player, all_tokens, makari_controller, game_log):", "    if False:" + MARK)], (TK,)),

    # ---------------------------------------------------------------- transport
    ("transport: Ghazghkull costs one slot",
     [(TR, '    if getattr(model.profile, "ghazghkull_thraka", False):', "    if False:" + MARK)], (TK,)),
    ("Trukk: carries Ghazghkull",
     [(UN, '    transport_excludes = ("jump_pack", "ghazghkull_thraka")  # "cannot transport GHAZGHKULL THRAKA/JUMP PACK models"',
       '    transport_excludes = ("jump_pack",)' + MARK)], (TK,)),

    # ------------------------------------------------------ datasheets, weapons
    ("Ghazghkull: no 'Eadbutt",
     [(OR, "_GHAZGHKULL_LOADOUT = [MorksRoarAimedProfile, AdamantineEadbuttProfile, GorksKlawProfile]",
       "_GHAZGHKULL_LOADOUT = [MorksRoarAimedProfile, GorksKlawProfile]" + MARK)], (TK,)),
    ("'Eadbutt: no [EXTRA ATTACKS]",
     [(WE, "    devastating_wounds = True" + NL + "    extra_attacks = True" + NL + "    precision = True",
       "    devastating_wounds = True" + NL + "    precision = True" + MARK)], (TK, WC)),
    ("Gork's Klaw: [CLEAVE 1]",
     [(WE, "    cleave = 2" + NL + "    devastating_wounds = True",
       "    cleave = 1" + NL + "    devastating_wounds = True" + MARK)], (TK, WC)),
    ("Mork's Roar: no Point Blank profile",
     [(WE, "    overcharge_profile = MorksRoarPointBlankProfile", "    pass" + MARK)], (TK,)),
    ("Big Mek: the app's 80 points",
     [(PT, '    "Big Mek in Mega Armour": flat_points({1: 90}, leads=("Meganobz", "Mek Gunz")),',
       '    "Big Mek in Mega Armour": flat_points({1: 80}, leads=("Meganobz", "Mek Gunz")),' + MARK)], (TK,)),
    ("Ghazghkull: the app's 235 points",
     [(PT, '    "Ghazghkull Thraka": flat_points({1: 300}),', '    "Ghazghkull Thraka": flat_points({1: 235}),' + MARK)],
     (TK,)),
]


def main():
    sys.stdout.reconfigure(line_buffering=True)
    check_only = "--check" in sys.argv
    probes = PROBES
    if "--only" in sys.argv:
        needle = sys.argv[sys.argv.index("--only") + 1]
        probes = [p for p in PROBES if needle in p[0]]
        if not probes:
            print("no probe label contains %r" % needle)
            raise SystemExit(2)
    touched = sorted({path for _l, edits, _s in probes for path, _a, _r in edits})
    for path in touched:
        if "AB-PROBE" in read(path):
            print("REFUSED: %s already contains the AB-PROBE marker" % path)
            raise SystemExit(2)
    bad_anchor = 0
    for label, edits, _suites in probes:
        for path, anchor, _replacement in edits:
            n = read(path).count(anchor)
            if n != 1:
                print("  ANCHOR x%d  %s (%s)" % (n, label, path))
                bad_anchor += 1
    if check_only:
        print("%d probe(s), %d anchor problem(s)" % (len(probes), bad_anchor))
        raise SystemExit(1 if bad_anchor else 0)

    before = {path: digest(path) for path in touched}
    suites = sorted({s for _l, _e, ss in probes for s in ss})
    base = {}
    for suite in suites:
        got, total, text = run(suite)
        if got is None or got == "HANG":
            print("BASELINE DID NOT RUN for %s:%s%s" % (suite, NL, text[-2000:]))
            raise SystemExit(2)
        base[suite] = total - got
        print("baseline %-36s %s/%s (%d red)" % (suite, got, total, total - got))
    print()

    bad = bad_anchor
    runs = 0
    for label, edits, probe_suites in probes:
        originals = {path: read(path) for path, _a, _r in edits}
        ok = True
        for path, anchor, replacement in edits:
            src = read(path)
            if src.count(anchor) != 1:
                print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(anchor)))
                ok = False
                bad += 1
                break
            write(path, src.replace(anchor, replacement))
        try:
            if not ok:
                continue
            for suite in probe_suites:
                runs += 1
                got, tot, out = run(suite)
                if got == "HANG":
                    verdict, detail, tail = "HANG", "suite timed out after %ds" % TIMEOUT_S, []
                    bad += 1
                elif got is None:
                    verdict = "CRASH"
                    detail = "suite crashed - a probe must turn it RED, not crash it"
                    bad += 1
                    tail = [ln for ln in out.splitlines() if ln.strip()][-1:]
                elif tot - got > base[suite]:
                    verdict = "BITES"
                    detail = "%s/%s (%d red)" % (got, tot, tot - got)
                    tail = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("FAIL:")][:1]
                else:
                    verdict = "NO BITE"
                    detail = "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
                    bad += 1
                    tail = []
                print("  %-8s %s [%s]: %s" % (verdict, label, suite, detail))
                for ln in tail:
                    print("             " + ln[:110])
        finally:
            for path, text in originals.items():
                write(path, text)

    after = {path: digest(path) for path in touched}
    drift = [p for p in touched if before[p] != after[p]]
    print()
    if drift:
        print("RESTORE FAILED for: %s" % ", ".join(drift))
        bad += 1
    print("%d probe(s), %d suite run(s)" % (len(probes), runs))
    print("%d probe run(s) did not bite" % bad if bad else "every probe bit")
    print("exit")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
