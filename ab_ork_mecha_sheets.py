"""A/B probes for the Mecha Orks sheets (stage G1): Bigboss, Weirdboy, Gunwagon -
their datasheet lines, weapons, wargear and sprites, Sumfin' to Prove, the
Weirdboy's Warpath (and the parametrised game/warpath.py it rides on), Da Jump,
Mobile Arsenal, the AI's Da Jump handler and main.py's wiring.

Each probe restores one piece of a plausible broken world AT THE SOURCE, runs the
suite(s) that are supposed to catch it, and puts the file back byte for byte. A
probe that does NOT turn its suite red is a finding about the TEST; a probe that
makes the suite CRASH or HANG is a finding too. Either way this file exits
non-zero.

EXCLUSIVE. This rewrites source files while it runs. No suite, measurement, edit
or commit may run beside it. Every replacement carries the marker AB-PROBE, so
after a run

    git grep -n --untracked "AB-PROBE" -- . ":!ab_*.py" ":!CLAUDE*.md" ":!docs/*"

must come back empty (--untracked: new modules are untracked until the commit).
The driver also hashes every probed file before the first probe and after the
last, and fails if any differs. Every suite run has a timeout - a probe that
hangs a suite is reported, not waited on.

game/factions/orks.py is CRLF: its anchors are single lines.

`--check` only verifies that every anchor is unique and the marker is absent,
writing nothing - safe to run beside anything. `--only SUBSTRING` re-runs the
probes whose label contains it.
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

TK = "test_ork_mecha_sheets.py"
WC = "test_weapon_characteristics.py"

WE = os.path.join("game", "weapons.py")
UN = os.path.join("game", "units.py")
OR = os.path.join("game", "factions", "orks.py")
PT = os.path.join("game", "factions", "orks_points.py")
SP = os.path.join("game", "sprites.py")
FI = os.path.join("game", "fight.py")
SH = os.path.join("game", "shooting.py")
IN = os.path.join("game", "ingress.py")
DJ = os.path.join("game", "da_jump.py")
WW = os.path.join("game", "weirdboy_warpath.py")
WP = os.path.join("game", "warpath.py")
MA = os.path.join("game", "mobile_arsenal.py")
ST = os.path.join("game", "sumfin_to_prove.py")
AS = os.path.join("game", "activation_state.py")
AG = os.path.join("ai", "agent_driver.py")
MAIN = "main.py"


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


# (label, [(path, anchor, replacement)], suites)
PROBES = [
    # ------------------------------------------------------------- datasheets
    ("Bigboss: the pre-codex 55 points",
     [(PT, '    "Bigboss": flat_points({1: 50}, supports=("Boyz", "Breaka Boyz", "Nobz")),',
       '    "Bigboss": flat_points({1: 55}, supports=("Boyz", "Breaka Boyz", "Nobz")),' + MARK)], (TK,)),
    ("Bigboss: prints no Sumfin' to Prove",
     [(UN, "    sumfin_to_prove = True  # Sumfin' to Prove - see game/sumfin_to_prove.py",
       "    sumfin_to_prove = False" + MARK)], (TK,)),
    ("Bigboss: the Boyz Nob's Big Choppa",
     [(OR, "_BIGBOSS_LOADOUT = [BigbossBigChoppaProfile, SluggaProfile]",
       "_BIGBOSS_LOADOUT = [BigChoppaProfile, SluggaProfile]" + MARK)], (TK, WC)),
    ("Weirdboy: BEAST SNAGGA",
     [(UN, '    weirdboy_warpath = True  # "Warpath (psychic level 1)" - see game/weirdboy_warpath.py',
       "    weirdboy_warpath = True" + NL + "    beast_snagga = True" + MARK)], (TK,)),
    ("Weirdboy: psyker level 0",
     [(UN, '    psyker_level = 1  # "Waaagh! Energy (psyker level 1)" - see game/unstable_energies.py',
       "    psyker_level = 0" + MARK)], (TK,)),
    ("Weirdboy: the pre-codex LEAD list (Boyz, Breaka Boyz)",
     [(PT, '    "Weirdboy": flat_points({1: 65}, supports=("Beast Snagga Boyz", "Boyz")),',
       '    "Weirdboy": flat_points({1: 65}, supports=("Boyz", "Breaka Boyz")),' + MARK)], (TK,)),
    ("Weirdboy: the Kill Rig's Warpath flag",
     [(UN, '    weirdboy_warpath = True  # "Warpath (psychic level 1)" - see game/weirdboy_warpath.py',
       "    warpath = True" + MARK)], (TK,)),
    ("Gunwagon: the Battlewagon's capacity of 22",
     [(UN, '    transport_capacity = 12  # "a transport capacity of 12 ORKS INFANTRY models"',
       "    transport_capacity = 22" + MARK)], (TK,)),
    ("Gunwagon: a Firing Deck like the Battlewagon",
     [(UN, "    mobile_arsenal = True  # Mobile Arsenal - see game/mobile_arsenal.py",
       "    mobile_arsenal = True" + NL + "    firing_deck = 11" + MARK)], (TK,)),
    ("Gunwagon: prints no Mobile Arsenal",
     [(UN, "    mobile_arsenal = True  # Mobile Arsenal - see game/mobile_arsenal.py",
       "    mobile_arsenal = False" + MARK)], (TK,)),

    # ---------------------------------------------------------------- weapons
    ("Crushin' Bulk: the Battlewagon's [CLEAVE 1]",
     [(WE, '    so a subclass that changes that one keyword."""' + NL + "    cleave = 2",
       '    so a subclass that changes that one keyword."""' + NL + "    cleave = 1" + MARK)], (TK, WC)),
    ("Zzap Gun: no [DEVASTATING WOUNDS: MONSTER/VEHICLE]",
     [(WE, '    conditional_keywords = (("devastating_wounds", True, MONSTER_OR_VEHICLE_TARGETS),)',
       "    pass" + MARK)], (TK, WC)),
    ("Kannon: no Shell profile",
     [(WE, "    overcharge_profile = KannonShellProfile", "    pass" + MARK)], (TK,)),
    ("Killkannon: [ANTI-INFANTRY 4+]",
     [(WE, '    anti = ("INFANTRY", 3)  # [ANTI-INFANTRY 3+], rule 24.03',
       '    anti = ("INFANTRY", 4)' + MARK)], (TK, WC)),
    ("Lobba: the Kill Rig's [BLAST 2]",
     [(WE, "    blast = 3" + NL + "    indirect_fire = True  # [INDIRECT FIRE], rule 10.07",
       "    blast = 2" + NL + "    indirect_fire = True" + MARK)], (TK, WC)),

    # ---------------------------------------------------------------- wargear
    ("Gunwagon: the Zzap Gun is free",
     [(OR, '                      points=ORKS_POINTS["Gunwagon"].wargear["Zzap Gun"]),',
       "                      )," + MARK)], (TK,)),
    ("Gunwagon: the Killkannon is an addition, not a swap",
     [(OR, '        WargearOption("Gunwagon", replaces=KannonFragProfile, with_weapons=[KillkannonProfile], max_models=1,',
       '        WargearOption("Gunwagon", replaces=None, with_weapons=[KillkannonProfile], max_models=1,' + MARK)],
     (TK,)),

    # ---------------------------------------------------------------- sprites
    ("sprites: the Weirdboy draws Wurrboy.png",
     [(SP, '    "Weirdboy": "Weirdboy",', '    "Weirdboy": "Wurrboy",' + MARK)], (TK,)),
    ("sprites: the Painboy has no art",
     [(SP, '    "Painboy": "Painboy",', MARK)], (TK,)),

    # -------------------------------------------------------- Sumfin' to Prove
    ("fight: Sumfin' to Prove is not read",
     [(FI, "        modifiers.extend(sumfin_to_prove.hit_modifiers(self.fighting_squad))", "        pass" + MARK)],
     (TK,)),
    ("Sumfin' to Prove: a penalty",
     [(ST, "    return [Modifier(-SUMFIN_TO_PROVE_HIT_BONUS, SUMFIN_TO_PROVE_NAME)]",
       "    return [Modifier(SUMFIN_TO_PROVE_HIT_BONUS, SUMFIN_TO_PROVE_NAME)]" + MARK)], (TK,)),
    ("Sumfin' to Prove: a dead Bigboss still confers it",
     [(ST, '    return squad is not None and bool(unit_wide_ability(squad, "sumfin_to_prove"))',
       '    return squad is not None and any(m.profile.sumfin_to_prove for m in squad.models)' + MARK)], (TK,)),
    ("shooting: Sumfin' to Prove on ranged attacks too",
     [(SH, "        modifiers.extend(dodge_dis.hit_modifiers(self.active_squad))",
       "        modifiers.extend(dodge_dis.hit_modifiers(self.active_squad)); modifiers.extend("
       "__import__('game.sumfin_to_prove', fromlist=['x']).hit_modifiers(self.active_squad))" + MARK)], (TK,)),

    # ------------------------------------------------------ Weirdboy's Warpath
    ("Weirdboy Warpath: no [PSYCHIC]",
     [(WW, "    granted.psychic = True", "    pass" + MARK)], (TK,)),
    ("Weirdboy Warpath: ranged weapons too",
     [(WW, '    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE or not is_active(squad):',
       "    if weapon is None or not is_active(squad):" + MARK)], (TK,)),
    ("Weirdboy Warpath: no wound 1s re-roll",
     [(WW, "    return is_active(squad)", "    return False" + MARK)], (TK,)),
    ("Weirdboy Warpath: grants the Kill Rig's flag",
     [(WW, '    ACTIVE_FLAG = "weirdboy_warpath_active"', '    ACTIVE_FLAG = "warpath_active"' + MARK)], (TK,)),
    ("Weirdboy Warpath: asks the Kill Rig's ability",
     [(WW, '    ABILITY_FLAG = "weirdboy_warpath"', '    ABILITY_FLAG = "warpath"' + MARK)], (TK,)),
    ("Weirdboy Warpath: reset_phase keeps the grant",
     [(WW, "            squad.weirdboy_warpath_active = False", "            pass" + MARK)], (TK,)),
    ("warpath.py: use() always sets the Kill Rig's grant",
     [(WP, "        setattr(squad, self.ACTIVE_FLAG, True)", "        squad.warpath_active = True" + MARK)],
     (TK,)),
    ("warpath.py: the prompt always describes the Kill Rig's effect",
     [(WP, "            % (squad.name, WARPATH_NAME, WARPATH_PSYCHIC_LEVEL, self.EFFECT_TEXT),",
       "            % (squad.name, WARPATH_NAME, WARPATH_PSYCHIC_LEVEL, WarpathController.EFFECT_TEXT)," + MARK)],
     (TK,)),
    ("warpath.py: the ability flag is not asked",
     [(WP, "        return squad is not None and bool(unit_wide_ability(squad, self.ABILITY_FLAG))",
       "        return squad is not None" + MARK)], (TK,)),
    ("fight: the Weirdboy's Warpath is not offered",
     [(FI, "            self.weirdboy_warpath.offer(squad)", "            pass" + MARK)], (TK,)),
    ("fight: the Weirdboy's Warpath is not in the chain",
     [(FI, "        weapon = weirdboy_warpath.adjusted_weapon(weapon, self.fighting_squad)", "        pass" + MARK)],
     (TK,)),
    ("fight: the wound 1s are not re-rolled",
     [(FI, "        elif ones and weirdboy_warpath.rerolls_wound_ones(self.fighting_squad):",
       "        elif False:" + MARK)], (TK,)),

    # ---------------------------------------------------------------- Da Jump
    ("Da Jump: in the opponent's Movement phase too",
     [(DJ, "        if tt is None or tt.phase != PHASE_MOVEMENT or tt.turn_owner != squad.owner:",
       "        if tt is None or tt.phase != PHASE_MOVEMENT:" + MARK)], (TK,)),
    ("Da Jump: in any phase",
     [(DJ, "        if tt is None or tt.phase != PHASE_MOVEMENT or tt.turn_owner != squad.owner:",
       "        if tt is None or tt.turn_owner != squad.owner:" + MARK)], (TK,)),
    ("Da Jump: an embarked unit may jump",
     [(DJ, "        if st is None or squad in st.reserves or squad in st.embarked_squads:",
       "        if st is None or squad in st.reserves:" + MARK)], (TK,)),
    ("Da Jump: mid-move",
     [(DJ, "        if any(m.id in starts for m in squad.models):", "        if False:" + MARK)], (TK,)),
    ("Da Jump: no once-per-army limit",
     [(DJ, "        if self.limit.is_spent(squad.owner, self._battle_round(), pool):", "        if False:" + MARK)],
     (TK,)),
    ("Da Jump: the spend is not written",
     [(DJ, "        self.limit.spend(squad.owner, self._battle_round(), squad)", "        pass" + MARK)], (TK,)),
    ("Da Jump: no Deep Strike",
     [(DJ, "        squad.da_jump_deep_strike = True", "        pass" + MARK)], (TK,)),
    ("Da Jump: not into Strategic Reserves",
     [(DJ, "        withdraw_to_reserves(" + NL, "        (lambda *a, **k: None)(" + MARK + NL)], (TK,)),
    ("Da Jump: the psychic roll's gates are not asked",
     [(DJ, "        return self.psychic_roll.why_not(squad, DA_JUMP_PSYCHIC_LEVEL)", "        return None" + MARK)],
     (TK,)),
    ("Da Jump: no psychic roll",
     [(DJ, "        if not self.psychic_roll.roll(squad, DA_JUMP_NAME, DA_JUMP_PSYCHIC_LEVEL):",
       "        if False:" + MARK)], (TK,)),
    ("Da Jump: the pick stays on the jumped unit",
     [(DJ, "            mc.select(None)", "            pass" + MARK)], (TK,)),
    ("Da Jump: every unit has it",
     [(DJ, '    return squad is not None and bool(unit_wide_ability(squad, "da_jump"))',
       "    return squad is not None" + MARK)], (TK,)),
    ("Da Jump: the grant reads False",
     [(DJ, '    return squad is not None and bool(getattr(squad, "da_jump_deep_strike", False))',
       "    return False" + MARK)], (TK,)),
    ("ingress: Da Jump's Deep Strike is not read",
     [(IN, "        if da_jump.grants_deep_strike(squad):", "        if False:" + MARK)], (TK,)),
    ("save: Da Jump's round is not kept",
     [(AS, '    "da_jump_round",', MARK)], (TK,)),

    # --------------------------------------------------------- Mobile Arsenal
    ("Mobile Arsenal: on a reactive activation too",
     [(MA, "    return not reactive and has_ability(squad)", "    return has_ability(squad)" + MARK)], (TK,)),
    ("Mobile Arsenal: every unit has it",
     [(MA, '    return squad is not None and bool(unit_wide_ability(squad, "mobile_arsenal"))',
       "    return squad is not None" + MARK)], (TK,)),
    ("shooting: Mobile Arsenal is not in the automatic 1s",
     [(SH, "            or arsenal_ones" + NL, MARK + NL)], (TK,)),

    # ---------------------------------------------------------------- main.py
    ("main.py: no Weirdboy Warpath on the FightController",
     [(MAIN, "        weirdboy_warpath=WeirdboyWarpathController(",
       "        unused_weirdboy_warpath=WeirdboyWarpathController(" + MARK)], (TK,)),
    ("main.py: the Weirdboy's Warpath outlives its phase",
     [(MAIN, "        weirdboy_warpath.reset_phase({t.squad for t in state.tokens if t.squad is not None})",
       "        pass" + MARK)], (TK,)),
    ("main.py: Da Jump is not on the registry",
     [(MAIN, "    da_jump_controller = proactive_stratagems.add(DaJumpController(",
       "    da_jump_controller = (lambda controller: controller)(DaJumpController(" + MARK)], (TK,)),
    ("main.py: the AI is not handed Da Jump",
     [(MAIN, "            da_jump_controller=da_jump_controller,", "            " + MARK)], (TK,)),

    # --------------------------------------------------------------------- AI
    ("AI: Da Jump in battle round 1",
     [(AG, '    if tt is None or (getattr(tt, "battle_round", 0) or 0) < INGRESS_MIN_BATTLE_ROUND:',
       "    if tt is None:" + MARK)], (TK,)),
    ("AI: Da Jump for a unit that has moved",
     [(AG, "        if not movement_controller.can_make_move(squad):", "        if False:" + MARK)], (TK,)),
    ("AI: Da Jump off an objective",
     [(AG, '        if is_within_range_of_objective(squad, getattr(state, "objectives", None) or []):',
       "        if False:" + MARK)], (TK,)),
    ("AI: Da Jump when the enemy is in reach on foot",
     [(AG, "        if gap is None or gap <= observation.advance_reach_in(squad) + CHARGE_RANGE_IN:",
       "        if gap is None:" + MARK)], (TK,)),
    ("AI: the Movement handler never asks Da Jump",
     [(AG, "    if _handle_da_jump(player, state, movement_controller, da_jump_controller, game_log):",
       "    if False:" + MARK)], (TK,)),
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
