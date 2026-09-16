"""A/B probes for the 2026-09 Ork characters (stage E3b): Boss' Ammo Runt, Might
Is Right, Dodge Dis!, Intimidating Motivation / Keep Huntin'!, Krushin' Impetus,
Crude Surgery / Catch Dat Red Bit, the core-rule heal extraction (game/heal.py),
the AI's two answers, and main.py's wiring.

Each probe restores one piece of a plausible broken world AT THE SOURCE, runs the
suite(s) that are supposed to catch it, and puts the file back byte for byte. A
probe that does NOT turn its suite red is a finding about the TEST; a probe that
makes the suite CRASH or HANG is a finding too. Either way this file exits
non-zero.

EXCLUSIVE. This rewrites source files while it runs. No suite, measurement, edit
or commit may run beside it. Every replacement carries the marker AB-PROBE, so
after a run

    git grep -n "AB-PROBE" -- . ":!ab_*.py" ":!CLAUDE*.md"

must come back empty. The driver also hashes every probed file before the first
probe and after the last, and fails if any differs. Every suite run has a
timeout - a probe that hangs a suite is reported, not waited on.

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

TC = "test_ork_characters.py"
WIRING = "test_event_chain_wiring.py"
REANIM = "test_reanimation_protocols.py"
SCENE = "test_scene_activation.py"

BAR = os.path.join("game", "boss_ammo_runt.py")
MIR = os.path.join("game", "might_is_right.py")
DD = os.path.join("game", "dodge_dis.py")
BM = os.path.join("game", "boss_motivation.py")
KI = os.path.join("game", "krushin_impetus.py")
CS = os.path.join("game", "crude_surgery.py")
HEAL = os.path.join("game", "heal.py")
SH = os.path.join("game", "shooting.py")
FI = os.path.join("game", "fight.py")
ACT = os.path.join("game", "activation_state.py")
AG = os.path.join("ai", "agent_driver.py")
MAIN = "main.py"


def lines(*parts):
    return NL.join(parts)


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
    # ------------------------------------------------------- Boss' Ammo Runt
    ("Boss' Ammo Runt: never offered when selected to shoot",
     [(SH, "            self.boss_ammo_runt.offer(squad)", "            pass" + MARK)], (TC,)),
    ("Boss' Ammo Runt: the bonus is not in the Shooting hit modifiers",
     [(SH, "        modifiers.extend(boss_ammo_runt.hit_modifiers(shooter_model, self.active_squad))",
       "        pass" + MARK)], (TC,)),
    ("Boss' Ammo Runt: not in the attack key (one representative answers for the mob)",
     [(SH, "            boss_ammo_runt.attack_key(model),", "            False," + MARK)], (TC,)),
    ("Boss' Ammo Runt: the bonus reaches the whole unit, not 'this model'",
     [(BAR, "    if not is_active(squad) or not attack_key(model):", "    if not is_active(squad):" + MARK)], (TC,)),
    ("Boss' Ammo Runt: shares the mob's Ammo Runts spend",
     [(BAR, '    USED_ATTR = "boss_ammo_runt_used"', '    USED_ATTR = "ammo_runts_used"' + MARK)], (TC,)),
    ("Boss' Ammo Runt: the spend is not saved",
     [(ACT, '    "boss_ammo_runt_used",', '    # "boss_ammo_runt_used",' + MARK)], (TC,)),
    ("main: ShootingController is not handed Boss' Ammo Runt",
     [(MAIN, "        boss_ammo_runt=boss_ammo_runt_controller,", "        " + MARK.strip())], (TC,)),

    # -------------------------------------------------------- Might Is Right
    ("Might Is Right: not in the fight adjuster chain",
     [(FI, "        weapon = might_is_right.adjusted_weapon(weapon, pairs[0][0] if pairs else None)",
       "        pass" + MARK)], (TC,)),
    ("Might Is Right: not in the melee attack key",
     [(FI, "            might_is_right.attack_key(model),", "            False," + MARK)], (TC,)),
    ("Might Is Right: without the charge-move condition",
     [(MIR, '    return is_bearer(model) and bool(getattr(getattr(model, "squad", None), "charged_this_turn", False))',
       "    return is_bearer(model)" + MARK)], (TC,)),
    ("Might Is Right: +2 A instead of +3",
     [(MIR, "MIGHT_IS_RIGHT_ATTACKS = 3", "MIGHT_IS_RIGHT_ATTACKS = 2" + MARK)], (TC,)),
    ("Might Is Right: a dice Strength keeps its old bonus",
     [(MIR, "        boosted.strength_notation = _plus(weapon.strength_notation, MIGHT_IS_RIGHT_STRENGTH)",
       "        pass" + MARK)], (TC,)),
    ("Might Is Right: a dead Warboss still grants it",
     [(MIR, lines("    return bool(model is not None and not model.is_dead()",
                  '                and getattr(model.profile, "might_is_right", False))'),
       '    return bool(model is not None and getattr(model.profile, "might_is_right", False))' + MARK)], (TC,)),

    # ------------------------------------------------------------ Dodge Dis!
    ("Dodge Dis!: not in the Shooting hit modifiers",
     [(SH, "        modifiers.extend(dodge_dis.hit_modifiers(self.active_squad))", "        pass" + MARK)], (TC,)),
    ("Dodge Dis!: not in the Fight hit modifiers",
     [(FI, "        modifiers.extend(dodge_dis.hit_modifiers(self.fighting_squad))", "        pass" + MARK)], (TC,)),
    ("Dodge Dis!: any model rather than rule 19.04 (a dead Beastboss still grants it)",
     [(DD, '    return squad is not None and bool(unit_wide_ability(squad, "dodge_dis"))',
       '    return squad is not None and any(getattr(m.profile, "dodge_dis", False) for m in squad.models)'
       + MARK)], (TC,)),

    # --------------------------------------------------- the boss motivations
    ("Boss motivation: the window is always open",
     [(BM, lines("        if squad is self._just_moved:", "            return True"),
       "        return True" + MARK)], (TC,)),
    ("Boss motivation: another unit's move does not close the END window",
     [(BM, lines("        self._just_moved = None", "        return self._auto(squad, ignore_window=True)"),
       "        return self._auto(squad, ignore_window=True)" + MARK)], (TC,)),
    ("Boss motivation: Keep Huntin'! spends Intimidating Motivation's budget",
     [(BM, '    LIMIT_FLAG = "keep_huntin_round"', '    LIMIT_FLAG = "intimidating_motivation_round"' + MARK)], (TC,)),
    ("Boss motivation: the target stays battle-shocked",
     [(BM, "        target.battle_shocked = False", "        pass" + MARK)], (TC,)),
    ("Boss motivation: riled up one turn too long",
     [(BM, "        return riled_up.until_start_of_your_next_turn(self.turn_tracker, player)",
       "        return riled_up.until_start_of_your_next_turn(self.turn_tracker, player) + 1" + MARK)], (TC,)),
    ("Boss motivation: a unit it would not help is offered anyway",
     [(BM, "    def benefits(self, target, player):",
       "    def benefits(self, target, player):" + NL + "        return True" + MARK)], (TC,)),
    ("Boss motivation: 60\" instead of 6\"",
     [(BM, "BOSS_MOTIVATION_RANGE_IN = 6.0", "BOSS_MOTIVATION_RANGE_IN = 60.0" + MARK)], (TC,)),
    ("Boss motivation: Keep Huntin'! takes any ORKS unit",
     [(BM, '        return any(getattr(m.profile, "beast_snagga", False) for m in _alive(squad))',
       '        return any(getattr(m.profile, "orks", False) for m in _alive(squad))' + MARK)], (TC,)),
    ("Boss motivation: no Cancel on the board pick",
     [(BM, '        options.append(("Cancel", lambda: None))', "        pass" + MARK)], (TC,)),
    ("Boss motivation: the options are not tagged (a list, not a board pick)",
     [(BM, '        options = [("%s: %s" % (self.NAME, t.name), (lambda t=t: self.apply(squad, t)), t)',
       '        options = [("%s: %s" % (self.NAME, t.name), (lambda t=t: self.apply(squad, t)))' + MARK)], (TC,)),
    ("Boss motivation: the hooks answer for a human too",
     [(BM, "        if squad is None or squad.owner not in self.auto_players or self.choice is None:",
       "        if squad is None or self.choice is None:" + MARK)], (TC,)),
    ("AI: the boss motivation does not prefer a battle-shocked unit",
     [(AG, '    return sorted(candidates, key=lambda s: (not getattr(s, "battle_shocked", False),',
       "    return sorted(candidates, key=lambda s: (False," + MARK)], (TC,)),
    ("main: the boss motivations are not on the registry",
     [(MAIN, lines("    proactive_stratagems.add(intimidating_motivation_controller)",
                   "    proactive_stratagems.add(keep_huntin_controller)"), "    pass" + MARK)], (TC, WIRING)),
    ("main: Intimidating Motivation does not hear a move begin",
     [(MAIN, "    movement_controller.on_move_started.append(intimidating_motivation_controller.on_move_started)",
       "    pass" + MARK)], (TC,)),

    # ------------------------------------------------------- Krushin' Impetus
    ("Krushin' Impetus: one die per model, engaged or not",
     [(KI, "    return sum(1 for m in _alive(squad) if gap_to(m, target) <= ENGAGEMENT_RANGE_IN)",
       "    return len(_alive(squad))" + MARK)], (TC,)),
    ("Krushin' Impetus: 4+ instead of 3+",
     [(KI, "KRUSHIN_IMPETUS_THRESHOLD = 3", "KRUSHIN_IMPETUS_THRESHOLD = 4" + MARK)], (TC,)),
    ("Krushin' Impetus: the mortal wounds are never allocated",
     [(KI, '        self._inflict(ctx["target"], wounds)', "        pass" + MARK)], (TC,)),
    ("Krushin' Impetus: a human does not pick the target",
     [(KI, "        if len(candidates) == 1 or squad.owner in self.auto_players or self.decision_manager is None:",
       "        if True:" + MARK)], (TC,)),
    ("main: Krushin' Impetus does not hear the charge move end",
     [(MAIN, lines("    charge_controller.on_charge_move_finished.append(",
                   "        krushin_impetus_controller.on_charge_move_finished)"), "    pass" + MARK)], (TC,)),
    ("main: Krushin' Impetus' allocation is never drawn",
     [(MAIN, "        renderer.draw_damage_choice_highlight(board_surface, board, "
             "krushin_impetus_controller.pending_damage_choice)", "        pass" + MARK)], (TC, WIRING)),

    # ------------------------------------------- Crude Surgery / core-rule heal
    ("Heal: destroyed models revived before the damaged ones are topped up",
     [(HEAL, lines("    while remaining > 0:", "        damaged = "),
       lines("    while False:" + MARK, "        damaged = "))], (TC, REANIM)),
    ("Heal: CHARACTER models revived",
     [(HEAL, '                  if not getattr(m.profile, "character", False)]', "                  ]" + MARK)],
     (TC, REANIM)),
    ("Crude Surgery: Catch Dat Red Bit asked with 3 or fewer to heal",
     [(CS, "            and heal_rule.healable_wounds(squad) > CRUDE_SURGERY_WOUNDS)",
       "            and heal_rule.healable_wounds(squad) > 0)" + MARK)], (TC,)),
    ("Crude Surgery: Catch Dat Red Bit never spent",
     [(CS, "        squad.catch_dat_red_bit_used = True", "        pass" + MARK)], (TC,)),
    ("Crude Surgery: the D3 is not added",
     [(CS, "        self._heal(squad, CRUDE_SURGERY_WOUNDS + rolled, bonus=rolled)",
       "        self._heal(squad, CRUDE_SURGERY_WOUNDS, bonus=rolled)" + MARK)], (TC,)),
    ("Crude Surgery: a unit off the board is healed as if on it",
     [(CS, "        off_board = not self._on_board(squad)", "        off_board = False" + MARK)], (TC,)),
    ("Crude Surgery: the engine places a human's revived models",
     [(CS, "        placer = None if off_board else self.placer", "        placer = None" + MARK)], (TC,)),
    ("Crude Surgery: the AI ignores its verdict",
     [(CS, "                if self.verdict is None or self.verdict(squad):", "                if True:" + MARK)], (TC,)),
    ("Crude Surgery: the spend is not saved",
     [(ACT, '    "catch_dat_red_bit_used",', '    # "catch_dat_red_bit_used",' + MARK)], (TC,)),
    ("AI: Catch Dat Red Bit on 3 to heal",
     [(AG, "CATCH_DAT_RED_BIT_MIN_HEALABLE = 5", "CATCH_DAT_RED_BIT_MIN_HEALABLE = 3" + MARK)], (TC,)),
    ("AI: the shared damage-choice list is taken but never folded in",
     [(AG, "    for extra in damage_choice_controllers or ():", "    for extra in ():" + MARK)], (TC, WIRING)),
    ("main: take_one_action() is not handed the shared damage-choice list",
     [(MAIN, "            damage_choice_controllers=damage_choice_controllers,",
       "            " + MARK.strip())], (WIRING,)),
    ("main: Crude Surgery is never begun",
     [(MAIN, "            crude_surgery_controller.begin_command_phase(state.all_squads(), turn_tracker.turn_owner)",
       "            pass" + MARK)], (TC,)),
    ("main: Catch Dat Red Bit's D3 is never acknowledged",
     [(MAIN, "        crude_surgery_controller.on_dice_acknowledged()", "        pass" + MARK)], (TC, WIRING)),
]


def main():
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
                sys.stdout.flush()
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
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
