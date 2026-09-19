"""A/B probes for Green Tide (Mecha Orks stage G3): Mob-handed Brutality, the two
Enhancements (Ferocious Show-off, 'Ardboyz), the three Stratagems (Unbridled
Carnage, 'Ere We Go, Mob Mentality), the AI's handlers, main.py's wiring - and the
two engine fixes this stage made: the melee Attacks COUNT reads the adjusted
weapon, and the Save characteristic has one reader (game/save_characteristic.py).

Same driver as ab_ork_mecha_characters.py: each probe restores one piece of a
plausible broken world AT THE SOURCE, runs the suite(s) that are supposed to catch
it, and puts the file back byte for byte. A probe that does NOT turn its suite red
is a finding about the TEST; one that CRASHES or HANGS a suite is a finding too.

EXCLUSIVE. This rewrites source files while it runs. No suite, measurement, edit
or commit may run beside it - and a parallel session must be told first. Every
replacement carries the marker AB-PROBE, so after a run

    git grep -n --untracked "AB-PROBE" -- . ":!ab_*.py" ":!CLAUDE*.md" ":!docs/*"

must come back empty. The driver hashes every probed file before the first probe
and after the last, and every suite run has a timeout.

game/factions/orks.py, game/damage_estimate.py and game/movement.py are CRLF:
their anchors are single lines.

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

TG = "test_ork_green_tide.py"
UI = "test_ork_green_tide_ui.py"
EW = "test_event_chain_wiring.py"
TD = "test_detachments.py"

OR = os.path.join("game", "factions", "orks.py")
CF = os.path.join("game", "config.py")
GTM = os.path.join("game", "green_tide.py")
UC = os.path.join("game", "green_tide_unbridled_carnage.py")
EWG = os.path.join("game", "green_tide_ere_we_go.py")
MM = os.path.join("game", "green_tide_mob_mentality.py")
FSO = os.path.join("game", "enh_ferocious_show_off.py")
ARD = os.path.join("game", "enh_ardboyz.py")
EN = os.path.join("game", "enhancements.py")
SVC = os.path.join("game", "save_characteristic.py")
DR = os.path.join("game", "damage_resolution.py")
DE = os.path.join("game", "damage_estimate.py")
SQ = os.path.join("game", "squad.py")
OB = os.path.join("ai", "observation.py")
AG = os.path.join("ai", "agent_driver.py")
DC = os.path.join("game", "ui", "unit_datacard.py")
FI = os.path.join("game", "fight.py")
RB = os.path.join("game", "roll_bonus.py")
MV = os.path.join("game", "movement.py")
BS = os.path.join("game", "battle_shock.py")
IB = os.path.join("game", "insane_bravery.py")
AU = os.path.join("game", "attached_units.py")
DN = os.path.join("game", "dice_notation.py")
AS = os.path.join("game", "activation_state.py")
MAIN = "main.py"


# (label, [(path, anchor, replacement)], suites)
PROBES = [
    # ------------------------------------------------------------ the detachment
    ("detachment: no config setting",
     [(OR, '    setting="GREEN_TIDE_PLAYERS",', "    setting=None," + MARK)], (TG, TD)),
    ("config: Green Tide held by Player 2 by default",
     [(CF, "GREEN_TIDE_PLAYERS = ()", 'GREEN_TIDE_PLAYERS = ("Player 2",)' + MARK)], (TG,)),

    # ----------------------------------------------------- Mob-handed Brutality
    ("MHB: Sustained Hits for every ORKS unit, not just BOYZ",
     [(GTM, "            and is_boyz_unit(squad))", "            and is_orks_unit(squad))" + MARK)], (TG,)),
    ("MHB: Sustained Hits without the detachment",
     [(GTM, '    return (squad is not None and fields_green_tide(getattr(squad, "owner", None))',
       "    return (squad is not None and True" + MARK)], (TG,)),
    ("MHB: Lethal Hits without a charge",
     [(GTM, '    if not getattr(squad, "charged_this_turn", False) or not is_orks_infantry_unit(squad):',
       "    if not is_orks_infantry_unit(squad):" + MARK)], (TG,)),
    ("MHB: Lethal Hits against a VEHICLE too",
     [(GTM, "    return NON_MONSTER_VEHICLE_TARGETS.matches(target_squad)", "    return True" + MARK)], (TG,)),
    ("MHB: downgrades Sustained Hits 2",
     [(GTM, "            and (weapon.sustained_hits or 0) < MOB_HANDED_SUSTAINED_HITS):", "            and True):" + MARK)],
     (TG,)),
    ("MHB: touches a dice-notation Sustained Hits",
     [(GTM, '            and getattr(weapon, "sustained_hits_notation", None) is None', "            and True" + MARK)],
     (TG,)),
    ("MHB: gone from the fight chain",
     [(FI, "        weapon = green_tide.adjusted_weapon(" + NL
       + "            weapon, self.fighting_squad," + NL
       + "            target_squad if target_squad is not None else self.target_squad)",
       "        pass" + MARK)], (TG,)),

    # ------------------------------------------------- the Attacks count fix
    ("count: the fixed Attacks sum reads the raw pairs again",
     [(FI, "        total_attacks = sum(damaged_attacks.attacks_for(m, attacks_weapon) for m, _w in pairs)",
       "        total_attacks = sum(damaged_attacks.attacks_for(m, w) for m, w in pairs)" + MARK)], (TG, EW)),
    ("count: the dice-notation Attacks roll reads the raw weapon again",
     [(FI, "                attacks_weapon.attacks_notation, count=len(pairs), dice_manager=self.dice_manager,",
       "                weapon.attacks_notation, count=len(pairs), dice_manager=self.dice_manager," + MARK)], (EW,)),

    # ------------------------------------------------------ Ferocious Show-off
    ("FSO: +2 A whatever the unit size",
     [(FSO, '    if green_tide.living_model_count(getattr(model, "squad", None)) >= FEROCIOUS_SHOW_OFF_MOB_SIZE:',
       "    if True:" + MARK)], (TG,)),
    ("FSO: bearer read off the flag - no detachment, no death check",
     [(FSO, "    return model is not None and enhancements.model_is_active(model, FEROCIOUS_SHOW_OFF)",
       '    return model is not None and getattr(model.profile, "ferocious_show_off", False)' + MARK)], (TG,)),
    ("FSO: the notation keeps its flat part",
     [(FSO, '    boosted.attacks_notation = dice_notation.plus(getattr(weapon, "attacks_notation", None), bonus)',
       "    pass" + MARK)], (TG,)),
    ("FSO: gone from the fight chain",
     [(FI, "        weapon = enh_ferocious_show_off.adjusted_weapon(weapon, pairs[0][0] if pairs else None)",
       "        pass" + MARK)], (TG,)),
    ("FSO: gone from _melee_attack_key()",
     [(FI, "            enh_ferocious_show_off.attack_key(model),", "            None," + MARK)], (TG,)),
    ("FSO: bearer line drops INFANTRY",
     [(EN, '     _orks_infantry_character, "ORKS INFANTRY model only")',
       '     _orks_character, "ORKS INFANTRY model only")' + MARK)], (TG,)),

    # --------------------------------------------------------------- 'Ardboyz
    ("Ardboyz: not unit-level",
     [(EN, '     _boyz_unit, "BOYZ unit only", unit_level=True)', '     _boyz_unit, "BOYZ unit only")' + MARK)], (TG,)),
    ("Ardboyz: Beast Snagga Boyz may take it",
     [(EN, '    return _unit_is(squad, ("Boyz",))', '    return _unit_is(squad, ("Boyz", "Beast Snagga Boyz"))' + MARK)],
     (TG,)),
    ("Ardboyz: read off the flag - no detachment, no living source",
     [(ARD, "    return squad is not None and enhancements.is_active(squad, ARDBOYZ)",
       '    return squad is not None and any(getattr(m.profile, "ardboyz", False) for m in squad.models)' + MARK)],
     (TG,)),
    ("save characteristic: 'Ardboyz not asked",
     [(SVC, "    for source in (tomb_blade_wargear.save_override, enh_ardboyz.save_override):",
       "    for source in (tomb_blade_wargear.save_override,):" + MARK)], (TG,)),
    ("reader 1: the save roll reads the profile",
     [(DR, "    sv = parse_threshold(save_characteristic.armour_save(model))",
       "    sv = parse_threshold(model.profile.armor_save)" + MARK)], (TG, EW)),
    ("reader 2: defender_soak() reads the profile",
     [(DE, "                          armor_save=save_characteristic.armour_save(soak_group[0])),",
       "                          armor_save=None)," + MARK)], (TG,)),
    ("reader 3: observation reads the profile",
     [(OB, '        "save": save_characteristic.armour_save(squad.models[0]),',
       '        "save": squad.models[0].profile.armor_save,' + MARK)], (TG, EW)),
    ("reader 3b: observation's attached characters read the profile",
     [(OB, '            "save": save_characteristic.armour_save(m),', '            "save": m.profile.armor_save,' + MARK)],
     (TG, EW)),
    ("reader 4: the matchup hint reads the profile",
     [(AG, '    return f"T{profile.toughness}, Sv{save_characteristic.armour_save(target.models[0])}{keyword}"',
       '    return f"T{profile.toughness}, Sv{profile.armor_save}{keyword}"' + MARK)], (TG, EW)),
    ("reader 5: the datacard prints the profile",
     [(DC, "                token.current_wounds, armor_save=save_characteristic.armour_save(token)),",
       "                token.current_wounds, armor_save=None)," + MARK)], (TG,)),
    ("reader 6: the allocation key reads the profile",
     [(SQ, "            key = (model.profile.wounds, save_characteristic.armour_save(model))",
       "            key = (model.profile.wounds, model.profile.armor_save)" + MARK)], (TG, EW)),
    ("reader 6b: the allocation weakness reads the profile",
     [(SQ, "    save_threshold = parse_threshold(save_characteristic.armour_save(models[0])) or 7  # no save = weakest",
       "    save_threshold = parse_threshold(models[0].profile.armor_save) or 7" + MARK)], (EW,)),

    # ------------------------------------------------------- Unbridled Carnage
    ("UC: no charge needed",
     [(UC, '            and bool(getattr(squad, "charged_this_turn", False)))', "            and True)" + MARK)], (TG, UI)),
    ("UC: any ORKS unit, not BOYZ",
     [(UC, "            and green_tide.is_boyz_unit(squad)", "            and green_tide.is_orks_unit(squad)" + MARK)],
     (TG,)),
    ("UC: any phase",
     [(UC, "        if self.turn_tracker.phase != PHASE_FIGHT:", "        if False:" + MARK)], (TG, UI)),
    ("UC: offered to a unit that fought or is fighting",
     [(UC, '        if squad in getattr(fc, "fought_squad_ids", ()) or getattr(fc, "fighting_squad", None) is squad:',
       "        if False:" + MARK)], (UI,)),
    ("UC: the grant never lands",
     [(UC, "            squad.unbridled_carnage_active = True", "            pass" + MARK)], (TG, UI)),
    ("UC: +0 A",
     [(UC, "    boosted.attacks = weapon.attacks + UNBRIDLED_CARNAGE_ATTACKS", "    boosted.attacks = weapon.attacks" + MARK)],
     (TG,)),
    ("UC: no detachment gate",
     [(UC, '    return (squad is not None and green_tide.fields_green_tide(getattr(squad, "owner", None))',
       "    return (squad is not None and True" + MARK)], (TG, UI)),
    ("UC: the grant never ends",
     [(UC, "            squad.unbridled_carnage_active = False", "            pass" + MARK)], (TG, UI)),
    ("UC: gone from the fight chain",
     [(FI, "        weapon = green_tide_unbridled_carnage.adjusted_weapon(weapon, self.fighting_squad)",
       "        pass" + MARK)], (TG,)),

    # --------------------------------------------------------------- 'Ere We Go
    ("EWG: the Advance roll does not get it",
     [(RB, "    ere_we_go = green_tide_ere_we_go.advance_bonus(squad)", "    ere_we_go = 0" + MARK)], (TG,)),
    ("EWG: movement reads the Advance+Charge list again",
     [(MV, "    terms = list(roll_bonus_advance_sources(squad, all_tokens))",
       '    terms = list(__import__("game.roll_bonus", fromlist=["sources"]).sources(squad, all_tokens))' + MARK)],
     (TG,)),
    ("EWG: leaks into the Charge roll",
     [(RB, "    return bloody_handed.roll_bonus(squad, all_tokens)",
       '    return bloody_handed.roll_bonus(squad, all_tokens) + __import__("game.green_tide_ere_we_go", '
       'fromlist=["x"]).advance_bonus(squad)' + MARK)], (TG,)),
    ("EWG: any ORKS unit",
     [(EWG, "            and green_tide.is_beast_snagga_boyz_or_boyz_unit(squad))",
       "            and green_tide.is_orks_unit(squad))" + MARK)], (TG,)),
    ("EWG: offered after the unit moved",
     [(EWG, '            if squad in getattr(self.movement_controller, "moved_squad_ids", ()):', "            if False:" + MARK)],
     (TG, UI)),
    ("EWG: offered after the unit Advanced",
     [(EWG, '            if squad in getattr(self.movement_controller, "advanced_squad_ids", ()):',
       "            if False:" + MARK)], (TG,)),
    ("EWG: the opponent's Movement phase too",
     [(EWG, "        if squad.owner != self.turn_tracker.turn_owner:", "        if False:" + MARK)], (TG, UI)),
    ("EWG: the grant never lands",
     [(EWG, "            squad.ere_we_go_active = True", "            pass" + MARK)], (TG, UI)),

    # ----------------------------------------------------------- Mob Mentality
    ("MM: no 13+ models",
     [(MM, "            and green_tide.living_model_count(squad) >= MOB_MENTALITY_MIN_MODELS)", "            and True)" + MARK)],
     (TG, UI)),
    ("MM: no 12 inch range",
     [(MM, "                if mob.min_distance_to(other) > MOB_MENTALITY_RANGE_IN:", "                if False:" + MARK)],
     (TG,)),
    ("MM: no visibility",
     [(MM, "                if self.visible is not None and not self.visible(mob, other):", "                if False:" + MARK)],
     (TG,)),
    ("MM: a unit that owes no roll is offered",
     [(MM, "            if auto_passes(other) or not self.owes_roll(other):", "            if auto_passes(other):" + MARK)],
     (TG, UI)),
    ("MM: offered after the step began",
     [(MM, "        if self.step_has_begun(squad.owner):", "        if False:" + MARK)], (TG, UI)),
    ("MM: an opponent's roll closes the window",
     [(MM, '        return any(getattr(s, "owner", None) == player for s in bsc.rolled_squad_ids)',
       "        return bool(bsc.rolled_squad_ids)" + MARK)], (TG,)),
    ("MM: the opponent's Command phase too",
     [(MM, "        if tt.phase != PHASE_COMMAND or squad.owner != tt.turn_owner:",
       "        if tt.phase != PHASE_COMMAND:" + MARK)], (TG, UI)),
    ("MM: never asks - pays for the first candidate",
     [(MM, "        if len(options) == 1 or self.decision_manager is None:", "        if True:" + MARK)], (TG, UI)),
    ("MM: the grant never lands",
     [(MM, "        other.mob_mentality_active = True", "        pass" + MARK)], (TG, UI)),
    ("MM: the grant goes to the TARGET instead of the pick",
     [(MM, "        other = self._chosen", "        other = targets[0] if targets else None" + MARK)], (TG, UI)),
    ("battle-shock: the 08.03 roll is not automatic",
     [(BS, "        if source is not None:" + NL + "            self.force_pass(squad, source=source)",
       "        if False:" + MARK + NL + "            self.force_pass(squad, source=source)")], (TG,)),
    ("battle-shock: a forced roll is not automatic",
     [(BS, "        self._auto_success = auto_success_source(squad)", "        self._auto_success = None" + MARK)], (TG,)),
    ("battle-shock: the acknowledgement grades the dice anyway",
     [(BS, "        if automatic is not None or leadership_success(rolls, squad, self.all_tokens, penalty):",
       "        if leadership_success(rolls, squad, self.all_tokens, penalty):" + MARK)], (TG,)),
    ("battle-shock: Mob Mentality is not a source",
     [(BS, "    if green_tide_mob_mentality.auto_passes(squad):", "    if False:" + MARK)], (TG,)),
    ("Insane Bravery: offered over Mob Mentality",
     [(IB, "        if already is not None:", "        if False:" + MARK)], (TG,)),

    # ------------------------------------------------------------------- the AI
    ("AI: Mob Mentality never asked",
     [(AG, "            acted = _handle_mob_mentality(player, all_tokens, mob_mentality_controller, game_log=game_log)",
       "            acted = False" + MARK)], (TG,)),
    ("AI: Mob Mentality for a unit that would pass anyway",
     [(AG, "            if fail < MOB_MENTALITY_MIN_FAIL_CHANCE:", "            if True:" + MARK)], (TG,)),
    ("AI: Unbridled Carnage never asked",
     [(AG, "    if _handle_unbridled_carnage(player, all_tokens, fight_controller, unbridled_carnage_controller, game_log):",
       "    if False:" + MARK)], (TG,)),
    ("AI: 'Ere We Go never bought at the Advance decision",
     [(AG, "                _buy_ere_we_go(player, squad, ere_we_go_controller, game_log)", "                pass" + MARK)],
     (TG,)),
    ("AI: 'Ere We Go bought for the other player's unit",
     [(AG, "    if ere_we_go_controller is None or squad is None or squad.owner != player:",
       "    if ere_we_go_controller is None or squad is None:" + MARK)], (TG,)),

    # ---------------------------------------------------------------- main.py
    ("main: Unbridled Carnage not on the registry",
     [(MAIN, "    unbridled_carnage_controller = proactive_stratagems.add(UnbridledCarnageController(",
       "    unbridled_carnage_controller = (UnbridledCarnageController(" + MARK)], (TG, UI)),
    ("main: Mob Mentality not reset at the phase boundary",
     [(MAIN, "        mob_mentality_controller.reset_phase(_horde_squads)", "        pass" + MARK)], (TG,)),
    ("main: Mob Mentality not handed to the AI",
     [(MAIN, "            mob_mentality_controller=mob_mentality_controller,", "            " + MARK)], (TG,)),
    ("main: Mob Mentality without the line-of-sight test",
     [(MAIN, "        visible=lambda observer, other: any(" + NL
       + "            line_of_sight.has_line_of_sight(a, b, state.obstacles, state.tokens, state.terrain_areas)" + NL
       + "            for a in observer.models if not a.is_dead()" + NL
       + "            for b in other.models if not b.is_dead())))",
       "        visible=None))" + MARK)], (TG,)),

    # ------------------------------------------------------------ extractions
    ("unit_datasheet_names(): the components dropped",
     [(AU, '    sheets += [getattr(c, "datasheet", None) for c in getattr(squad, "attached_components", None) or ()]',
       "    pass" + MARK)], (TG,)),
    ("dice_notation.plus(): drops the dice count",
     [(DN, "    return notation._replace(bonus=notation.bonus + bonus)",
       "    return DiceNotation(notation.sides, notation.bonus + bonus)" + MARK)], (TG,)),
    ("save list: Mob Mentality's grant not saved",
     [(AS, '    "mob_mentality_active",', "   " + MARK)], (TG,)),
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
