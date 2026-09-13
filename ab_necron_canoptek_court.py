"""A/B probes for the Canoptek Court: its rule, four Enhancements, six Stratagems,
and the engine seams the detachment needed.

Each probe restores one piece of a plausible broken world AT THE SOURCE, runs the
suite(s) that are supposed to catch it, and puts the file back byte for byte. A
probe that does NOT turn its suite red is a finding about the TEST; a probe that
makes the suite CRASH is a finding too ("a probe has to make it RED, not crash
it" - learnt more than twenty times in this repo). Either way this file exits
non-zero.

EXCLUSIVE. This rewrites source files while it runs. No suite, measurement, edit
or commit may run beside it - a commit that lands mid-probe captures the probed
world (error class 20). Every replacement carries the marker AB-PROBE, so after a
run

    git grep -n "AB-PROBE" -- . ":!ab_*.py"

over the working tree and over HEAD must both come back empty. The driver also
hashes every probed file before the first probe and after the last, and fails if
any differs.

SHARED SEAMS ARE PROBED AGAINST EVERY SUITE THAT OWNS THEM: a change to a module
read by two suites has to redden both, or the one that stayed green is not
measuring its half.
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

COURT = "test_necron_canoptek_court.py"
UI = "test_necron_detachment_ui.py"
WIRING = "test_event_chain_wiring.py"
CANOPTEK = "test_necron_canoptek.py"

PM = os.path.join("game", "court_power_matrix.py")
SH = os.path.join("game", "shooting.py")
FI = os.path.join("game", "fight.py")
ND = os.path.join("game", "necron_detachments.py")
CU = os.path.join("game", "court_curse_of_the_cryptek.py")
CY = os.path.join("game", "court_cynosure_of_eradication.py")
SP = os.path.join("game", "court_solar_pulse.py")
CT = os.path.join("game", "court_countertemporal_shift.py")
RS = os.path.join("game", "court_reactive_subroutines.py")
FA = os.path.join("game", "court_suboptimal_facade.py")
TW = os.path.join("game", "enh_metalodermal_tesla_weave.py")
FU = os.path.join("game", "enh_hyperphasic_fulcrum.py")
AU = os.path.join("game", "enh_autodivinator.py")
SQ = os.path.join("game", "squad.py")
CPM = os.path.join("game", "command_points.py")
SEC = os.path.join("game", "secondary_missions.py")
RP = os.path.join("game", "reanimation_protocols.py")
MV = os.path.join("game", "movement.py")
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
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


# (label, [(path, anchor, replacement)], suites)
PROBES = [
    # ------------------------------------------------------ the Power Matrix
    ("'at least half' read as a strict majority",
     [(PM, "    return held * 2 >= len(objectives)",
       "    return held * 2 > len(objectives)" + MARK)], (COURT,)),
    ("half of ZERO objectives counts as holding the region",
     [(PM, lines("    if not objectives:", "        return False", "    held = sum("),
       lines("    if not objectives:" + MARK, "        return True", "    held = sum("))], (COURT,)),
    ("'wholly within your zone' tests only the base's centre",
     [(PM, "    in_own = any(z.contains_circle(x, y, r) for z in mine)",
       "    in_own = any(z.contains_point(x, y) for z in mine)" + MARK)], (COURT, UI)),
    ("own zone + No Man's Land: a base may reach into the enemy zone",
     [(PM, "        return bool(mine) and all(z.distance_to_point(x, y) >= r - EDGE_TOLERANCE_IN",
       "        return bool(mine) and all(z.distance_to_point(x, y) >= 0.0 - EDGE_TOLERANCE_IN" + MARK)],
     (COURT,)),
    ("the start-of-phase latch never expires",
     [(PM, "        if latched is not None and latched[0] == self._phase_key():",
       "        if latched is not None:" + MARK)], (COURT,)),
    ("a CRYPTEK/CANOPTEK unit counts without the detachment",
     [(PM, '    if squad is None or not has_detachment(getattr(squad, "owner", None)):',
       "    if squad is None:" + MARK)], (COURT, UI)),

    # ------------------------------------------------ the re-roll, both phases
    ("shooting never offers the whole Hit roll in the matrix",
     [(SH, "        if court_power_matrix.offers_full_reroll(self.active_squad, self.power_matrix):",
       "        if False:" + MARK)], (COURT,)),
    ("shooting loses the automatic Hit-roll-of-1 re-roll",
     [(SH, "        matrix_ones = court_power_matrix.applies(self.active_squad)",
       "        matrix_ones = False" + MARK)], (COURT,)),
    ("fight never offers the whole Hit roll in the matrix",
     [(FI, "        if court_power_matrix.offers_full_reroll(self.fighting_squad, self.power_matrix):",
       "        if False:" + MARK)], (COURT,)),
    ("fight loses the automatic Hit-roll-of-1 re-roll",
     [(FI, "        if ones and court_power_matrix.applies(self.fighting_squad):",
       "        if False:" + MARK)], (COURT,)),
    ("the per-model CRYPTEK/CANOPTEK term leaves the attack key",
     [(ND, "    return (model_is_cryptek(squad, model), model_is_canoptek(squad, model))",
       "    return (False, False)" + MARK)], (COURT,)),

    # ------------------------------------------------------- Enhancements
    ("Hyperphasic Fulcrum no longer needs the bearer to be leading",
     [(FU, lines("    if not attached_units.is_attached_unit(squad):", "        return False", ""),
       lines("    pass" + MARK, ""))], (COURT,)),
    ("Hyperphasic Fulcrum never reaches the shooting wound step",
     [(SH, "        elif enh_hyperphasic_fulcrum.applies(self.active_squad, self.power_matrix):",
       "        elif False:" + MARK)], (COURT,)),
    ("Hyperphasic Fulcrum never reaches the fight wound step",
     [(FI, "        elif ones and enh_hyperphasic_fulcrum.applies(self.fighting_squad, self.power_matrix):",
       "        elif False:" + MARK)], (COURT,)),
    ("Dimensional Sanctum stops granting Infiltrators",
     [(SQ, lines("    from game import enh_dimensional_sanctum",
                 "    return enh_dimensional_sanctum.grants_infiltrators(squad)"),
       "    return False" + MARK)], (COURT,)),
    ("the Autodivinator answers a MISSION CP as well",
     [(AU, "        if source != command_points_module.SOURCE_ABILITY or amount <= 0:",
       "        if amount <= 0:" + MARK)], (COURT,)),
    ("the Autodivinator rolls past the bonus-CP cap",
     [(AU, "                if self.command_points.bonus_cp_remaining(opponent, battle_round) <= 0:",
       "                if False:" + MARK)], (COURT,)),
    ("the Autodivinator pays on a 1",
     [(AU, "AUTODIVINATOR_THRESHOLD = 2", "AUTODIVINATOR_THRESHOLD = 1" + MARK)], (COURT,)),
    ("the Tesla Weave's 6 rolls a D3 instead of 3 flat",
     [(TW, lines("    if band_roll >= TESLA_WEAVE_FLAT_ON:", "        return TESLA_WEAVE_FLAT_WOUNDS", ""),
       lines("    pass" + MARK, ""))], (COURT,)),
    ("the Tesla Weave fires more than once per phase",
     [(TW, "        self._fired_this_phase.add(id(bearer))", "        pass" + MARK)], (COURT,)),
    ("the Tesla Weave's allocation never checks itself done (a one-model target parks)",
     [(TW, lines("        )", "        self._check_mortal_wounds_done()", "", "    @property"),
       lines("        )", "        pass" + MARK, "", "    @property"))], (COURT,)),
    ("the Tesla Weave can no longer take a model click",
     [(TW, "    def choose_damage_model(self, model):",
       "    def choose_damage_model_gone(self, model):" + MARK)], (WIRING, COURT)),

    # ---------------------------------------------------- gain_cp's source
    ("gain_cp() accepts any source",
     [(CPM, lines("        if source not in SOURCES:",
                  '            raise ValueError(f"gain_cp(): source must be one of {SOURCES}, not {source!r}")',
                  ""),
       lines("        pass" + MARK, ""))], (COURT,)),
    ("listeners hear a grant the cap swallowed",
     [(CPM, lines("        if granted <= 0:", "            self._log("),
       lines("        if granted <= 0:",
             "            for listener in list(self.on_cp_gained):" + MARK,
             "                listener(player, 0, source=source, battle_round=battle_round, reason=reason)",
             "            self._log("))], (COURT,)),
    ("the Secondary Mission discard claims to be an ABILITY grant",
     [(SEC, "                source=SOURCE_MISSION,",
       "                source=SOURCE_ABILITY," + MARK)], (COURT,)),

    # ------------------------------------------------ Curse of the Cryptek
    ("a death between activations waits instead of answering the last attacker",
     [(CU, lines("        if killer_squad is None and self._last_attacker is not None:",
                 "            return self._offer(squad, self._last_attacker)", ""),
       lines("        pass" + MARK, ""))], (COURT,)),
    ("a death with no killer is never drained",
     [(CU, "        mine = [sq for sq, k in self._owed if k is None or k is attacker]",
       "        mine = [sq for sq, k in self._owed if k is attacker]" + MARK)], (COURT,)),
    ("the Curse reads the UNIT's keywords instead of the attacking MODEL's",
     [(CU, "        return necron_detachments.model_is_canoptek(attacking_squad, attacking_model)",
       "        return necron_detachments.is_canoptek_unit(attacking_squad)" + MARK)], (COURT,)),
    ("the Curse is offered in YOUR Shooting phase too",
     [(CU, "        return tt.phase == PHASE_SHOOTING and tt.turn_owner == attacker.owner",
       "        return tt.phase == PHASE_SHOOTING" + MARK)], (COURT,)),
    ("the marks end with the phase instead of the battle",
     [(CU, lines("        self._last_attacker = None", "        self._asked = set()", ""),
       lines("        self._last_attacker = None", "        self._asked = set()",
             "        self._marks = {}" + MARK, ""))], (COURT,)),
    ("the shooting Hit roll never hears the Curse",
     [(SH, "self.curse_of_the_cryptek.hit_modifiers(", "(lambda *a, **k: [])(" + MARK)], (COURT,)),
    ("the shooting Wound roll never hears the Curse",
     [(SH, "self.curse_of_the_cryptek.wound_modifiers(", "(lambda *a, **k: [])(" + MARK)], (COURT,)),
    ("the fight Hit roll never hears the Curse",
     [(FI, "self.curse_of_the_cryptek.hit_modifiers(", "(lambda *a, **k: [])(" + MARK)], (COURT,)),

    # ------------------------------------------------ Cynosure of Eradication
    ("Cynosure gains an owner clause for the Fight phase it does not print",
     [(CY, lines("        if tt.phase == PHASE_FIGHT:", "            fc = self.fight_controller"),
       lines("        if tt.phase == PHASE_FIGHT:",
             "            if tt.turn_owner != squad.owner:" + MARK,
             "                return False",
             "            fc = self.fight_controller"))], (UI,)),
    ("Cynosure forgets 'the START of your Shooting phase'",
     [(CY, "            return sc.active_squad is None and not sc.shot_squad_ids",
       "            return True" + MARK)], (UI, COURT)),
    ("Cynosure forgets 'the start of the Fight phase'",
     [(CY, "            return fc.state == fight_module.NOT_STARTED and not fc.fought_squad_ids",
       "            return True" + MARK)], (UI,)),
    ("Cynosure no longer needs the unit wholly within the matrix",
     [(CY, lines("        if not court_power_matrix.unit_wholly_within(squad, self.power_matrix):",
                 "            return False", ""),
       lines("        pass" + MARK, ""))], (UI,)),
    ("Cynosure's grant outlives the phase",
     [(CY, "            squad.court_cynosure_active = False", "            pass" + MARK)], (UI,)),
    ("Cynosure grants weapons of models that are neither CRYPTEK nor CANOPTEK",
     [(CY, lines("    if not model_qualifies(squad, model):", "        return weapon", ""),
       lines("    pass" + MARK, ""))], (COURT,)),
    ("the shooting weapon chain never reads Cynosure",
     [(SH, "        weapon = court_cynosure_of_eradication.adjusted_weapon(",
       "        weapon = (lambda w, *a, **k: w)(" + MARK)], (COURT,)),
    ("the fight weapon chain never reads Cynosure",
     [(FI, "        weapon = court_cynosure_of_eradication.adjusted_weapon(",
       "        weapon = (lambda w, *a, **k: w)(" + MARK)], (COURT,)),

    # --------------------------------------------------------- Solar Pulse
    ("Solar Pulse forgets that its WHEN says YOUR Shooting phase",
     [(SP, "        if tt.phase != PHASE_SHOOTING or tt.turn_owner != squad.owner:",
       "        if tt.phase != PHASE_SHOOTING:" + MARK)], (UI,)),
    ("Solar Pulse forgets 'the START of' the phase",
     [(SP, "        if sc is None or sc.active_squad is not None or sc.shot_squad_ids:",
       "        if sc is None:" + MARK)], (UI,)),
    ("Solar Pulse stops gating on the detachment",
     [(SP, lines("        if not necron_detachments.has_detachment(squad.owner, SETTING):",
                 "            return False", "        if squad.owner in self._pulsed:"),
       lines("        pass" + MARK, "        if squad.owner in self._pulsed:"))], (UI,)),
    ("Solar Pulse's pulse outlives the phase",
     [(SP, "        self._pulsed.clear()", "        pass" + MARK)], (UI,)),
    ("the objective prompt loses its Cancel",
     [(SP, '            + [("Cancel", lambda: None)],', "            ," + MARK)], (UI,)),
    ("Solar Pulse ignores cover for any shooter, NECRONS or not",
     [(SP, lines("        if not necron_detachments.is_necrons_unit(shooting_squad):",
                 "            return False", ""),
       lines("        pass" + MARK, ""))], (COURT,)),
    ("the shooting cover funnel never asks Solar Pulse",
     [(SH, "                and self.solar_pulse.ignores_cover(self.active_squad, target_squad))",
       "                and False)" + MARK)], (COURT,)),

    # ------------------------------------------------ Reactive Subroutines
    ("Reactive Subroutines answers a Charge or a Scout move too",
     [(RS, lines("        if kind is not None and kind not in QUALIFYING_KINDS:", "            return False", ""),
       lines("        pass" + MARK, ""))], (COURT,)),
    ("Reactive Subroutines is offered to an ENGAGED unit",
     [(RS, lines("        if squad.is_engaged(self._tokens()):", "            return False", ""),
       lines("        pass" + MARK, ""))], (COURT,)),
    ("Reactive Subroutines forgets its 8\"",
     [(RS, lines("        if not self._within(squad, mover, REACTIVE_SUBROUTINES_TRIGGER_RANGE_IN):",
                 "            return False", ""),
       lines("        pass" + MARK, ""))], (COURT,)),
    ("its move mode is missing from REACTIVE_MOVE_MODES",
     [(MV, '"court_reactive_subroutines"})', "})" + MARK)], (WIRING,)),
    ("the AI destination hands the mover a {'x','y'} dict again (the bug the suite found)",
     [(AG, '    return (leg["x"], leg["y"]) if leg is not None else goal',
       "    return leg if leg is not None else goal" + MARK)], (COURT,)),

    # ------------------------------------------------ Countertemporal Shift
    ("Countertemporal Shift is offered against an attacker already within 18\"",
     [(CT, lines("        if attacker.min_distance_to(target) <= COUNTERTEMPORAL_SHIFT_RANGE_IN:",
                 "            return False", ""),
       lines("        pass" + MARK, ""))], (COURT,)),
    ("Countertemporal Shift is offered in YOUR Shooting phase",
     [(CT, "        if tt is None or tt.phase != PHASE_SHOOTING or tt.turn_owner != attacker.owner:",
       "        if tt is None or tt.phase != PHASE_SHOOTING:" + MARK)], (COURT,)),

    # ----------------------------------------------------- Suboptimal Facade
    ("the Facade never hands the charge back",
     [(FA, lines("    def _finish(self):", "        resume, self._resume = self._resume, None",
                 "        if resume is not None:", "            resume()"),
       lines("    def _finish(self):", "        self._resume = None" + MARK))], (COURT,)),
    ("the Facade no longer needs the target wholly within the matrix",
     [(FA, lines("        if not court_power_matrix.unit_wholly_within(target_squad, self.power_matrix):",
                 "            return False", ""),
       lines("        pass" + MARK, ""))], (COURT,)),
    ("the Facade is offered for a unit with nothing to recover",
     [(FA, lines("        if reanimation_protocols.recoverable_wounds(target_squad) <= 0:",
                 "            return False", ""),
       lines("        pass" + MARK, ""))], (COURT,)),

    # ------------------------------------- the one door into reanimate()
    ("activate() stops applying the Reanimation boost",
     [(RP, "        wounds += boost.extra_wounds(squad, all_tokens, log=log)",
       "        pass" + MARK)], (CANOPTEK,)),

    # --------------------------------------------------------- main.py
    ("main.py never stamps the Power Matrix at the start of a phase",
     [(MAIN, "        power_matrix_controller.stamp_at_start_of_phase()",
       "        if False: power_matrix_controller.stamp_at_start_of_phase()" + MARK)], (COURT,)),
    ("main.py never offers the Curse after shooting",
     [(MAIN, "        curse_of_the_cryptek_controller.maybe_offer(shooter_squad)",
       "        if False: curse_of_the_cryptek_controller.maybe_offer(shooter_squad)" + MARK)], (COURT,)),
    ("main.py's death sweep never feeds the Curse",
     [(MAIN, "            curse_of_the_cryptek_controller.notify_model_destroyed(",
       "            False and curse_of_the_cryptek_controller.notify_model_destroyed(" + MARK)], (COURT,)),
    ("main.py never acknowledges the Tesla Weave's dice",
     [(MAIN, "        metalodermal_tesla_weave_controller.on_dice_acknowledged()",
       "        if False: metalodermal_tesla_weave_controller.on_dice_acknowledged()" + MARK)],
     (COURT, WIRING)),
    ("the Facade leaves the charge-declaration chain",
     [(MAIN, lines("        metalodermal_tesla_weave_controller.maybe_offer,",
                   "        suboptimal_facade_controller.maybe_offer,", "    ])"),
       lines("        metalodermal_tesla_weave_controller.maybe_offer," + MARK, "    ])"))], (COURT,)),
    ("on_move_finished is REBOUND again (the listener-dropping scar)",
     [(MAIN, "    movement_controller.on_move_finished.append(reactive_subroutines_controller.on_move_finished)",
       "    movement_controller.on_move_finished = [reactive_subroutines_controller.on_move_finished]" + MARK)],
     (WIRING,)),
    ("main.py never registers the Autodivinator as a CP listener",
     [(MAIN, "    command_points.on_cp_gained.append(autodivinator_controller.on_cp_gained)",
       "    if False: command_points.on_cp_gained.append(autodivinator_controller.on_cp_gained)" + MARK)],
     (COURT,)),
    ("the ShootingController never gets Solar Pulse",
     [(MAIN, "    shooting_controller.solar_pulse = solar_pulse_controller",
       "    shooting_controller.solar_pulse = None" + MARK)], (COURT,)),
    ("Cynosure is built but never put on the panel registry",
     [(MAIN, "    cynosure_controller = proactive_stratagems.add(CynosureOfEradicationController(",
       "    cynosure_controller = (CynosureOfEradicationController(" + MARK)], (UI, COURT)),
    ("main.py never ends Solar Pulse at the phase boundary",
     [(MAIN, "        solar_pulse_controller.reset_phase()",
       "        if False: solar_pulse_controller.reset_phase()" + MARK)], (COURT,)),
]


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    probes = [p for p in PROBES if not only or any(o.lower() in p[0].lower() for o in only)]

    touched = sorted({path for _l, edits, _s in probes for path, _a, _r in edits})
    before = {path: digest(path) for path in touched}

    # Refuse a replacement text that is already in the file: restoring is by
    # writing the saved original back, but the post-run `git grep AB-PROBE`
    # check only means something if the marker cannot pre-exist.
    for path in touched:
        if "AB-PROBE" in read(path):
            print("REFUSED: %s already contains the AB-PROBE marker" % path)
            raise SystemExit(2)

    suites = sorted({s for _l, _e, ss in probes for s in ss})
    base = {}
    for suite in suites:
        got, total, text = run(suite)
        if got is None:
            print("BASELINE DID NOT RUN for %s:%s%s" % (suite, NL, text[-2000:]))
            raise SystemExit(2)
        base[suite] = total - got
        print("baseline %-34s %s/%s (%d red)" % (suite, got, total, total - got))
    print()

    bad = 0
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
                bad += 1
                continue
            for suite in probe_suites:
                runs += 1
                got, tot, out = run(suite)
                if got is None:
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
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
