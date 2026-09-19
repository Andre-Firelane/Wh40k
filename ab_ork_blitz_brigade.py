"""A/B probes for Blitz Brigade (Mecha Orks stage G4): Unstoppable Momentum (the
Advance that IS a 6, the charge re-roll), the two Enhancements (Targetin' Gizmos,
Boss Boomer), the two wired Stratagems (Keep It Runnin', Impending Krunch), the
shared mechanisms this stage extracted (game/end_of_fight_embark.py,
game/forced_shock_queue.py), main.py's wiring - and Readied Brawlers' named gap.

Same driver as ab_ork_green_tide.py: each probe restores one piece of a
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

TB = "test_ork_blitz_brigade.py"
TD = "test_detachments.py"
AE = "test_aeldari_detachment_stratagems.py"
TM = "test_ork_mecha_characters.py"

OR = os.path.join("game", "factions", "orks.py")
CF = os.path.join("game", "config.py")
BB = os.path.join("game", "blitz_brigade.py")
MV = os.path.join("game", "movement.py")
OB = os.path.join("ai", "observation.py")
MD = os.path.join("game", "more_dakka.py")
TG = os.path.join("game", "enh_targetin_gizmos.py")
BO = os.path.join("game", "enh_boss_boomer.py")
BM = os.path.join("game", "boss_motivation.py")
SH = os.path.join("game", "shooting.py")
KIR = os.path.join("game", "blitz_keep_it_runnin.py")
EFE = os.path.join("game", "end_of_fight_embark.py")
IK = os.path.join("game", "blitz_impending_krunch.py")
FSQ = os.path.join("game", "forced_shock_queue.py")
MAIN = "main.py"


# (label, [(path, anchor, replacement)], suites)
PROBES = [
    # ------------------------------------------------------------ the detachment
    ("detachment: no config setting",
     [(OR, '    setting="BLITZ_BRIGADE_PLAYERS",', "    setting=None," + MARK)], (TB, TD)),
    ("config: Blitz Brigade held by Player 2 by default",
     [(CF, "BLITZ_BRIGADE_PLAYERS = ()", 'BLITZ_BRIGADE_PLAYERS = ("Player 2",)' + MARK)], (TB,)),

    # ------------------------------------------------------- Unstoppable Momentum
    ("UM: any unit, not a WAGON",
     [(BB, "            and is_wagon_unit(squad))", "            and True)" + MARK)], (TB,)),
    ("UM: without the detachment",
     [(BB, '    return (squad is not None and fields_blitz_brigade(getattr(squad, "owner", None))',
       "    return (squad is not None and True" + MARK)], (TB,)),
    ("UM: the Advance is rolled after all",
     [(MV, "        elif blitz_brigade.advance_roll_is_fixed(self.selected_squad):", "        elif False:" + MARK)],
     (TB,)),
    ("UM: a flat 6 - the Advance modifiers skipped",
     [(MV, "            no_roll_bonus = (advance_total(self.selected_squad, [blitz_brigade.UNSTOPPABLE_MOMENTUM_ADVANCE],",
       "            no_roll_bonus = (blitz_brigade.UNSTOPPABLE_MOMENTUM_ADVANCE or advance_total(self.selected_squad, "
       "[blitz_brigade.UNSTOPPABLE_MOMENTUM_ADVANCE]," + MARK)], (TB,)),
    ("UM: the AI's observation still averages the Advance",
     [(OB, "    if blitz_brigade.advance_roll_is_fixed(squad):", "    if False:" + MARK)], (TB,)),
    ("UM: the charge re-roll never applies",
     [(BB, "        return applies(squad)", "        return False" + MARK)], (TB,)),
    ("main: the charge re-roll is never asked",
     [(MAIN, "                unstoppable_momentum_controller.maybe_offer_charge_reroll()", "                pass" + MARK)],
     (TB,)),

    # ---------------------------------------------------------- Targetin' Gizmos
    ("Gizmos: not a source of More Dakka",
     [(MD, "    return has_more_dakka(squad) or enh_targetin_gizmos.applies(squad, embarked_squads)",
       "    return has_more_dakka(squad)" + MARK)], (TB,)),
    ("Gizmos: any passenger will do, BIG MEK or not",
     [(TG, '            if not model.is_dead() and attached_units.model_has_datasheet_keyword(passenger, model, "BIG MEK"):',
       "            if not model.is_dead():" + MARK)], (TB,)),
    ("Gizmos: a dead Big Mek still counts",
     [(TG, '            if not model.is_dead() and attached_units.model_has_datasheet_keyword(passenger, model, "BIG MEK"):',
       '            if attached_units.model_has_datasheet_keyword(passenger, model, "BIG MEK"):' + MARK)], (TB,)),
    ("Gizmos: no Enhancement or detachment needed",
     [(TG, "    return (squad is not None and enhancements.is_active(squad, TARGETIN_GIZMOS)",
       "    return (squad is not None" + MARK)], (TB,)),
    ("shooting: the chain is not handed the embarked units",
     [(SH, "        weapon = more_dakka.adjusted_weapon(weapon, self.active_squad, self.embarked_squads())",
       "        weapon = more_dakka.adjusted_weapon(weapon, self.active_squad)" + MARK)], (TB, TM)),
    ("main: the ShootingController is never told who is embarked",
     [(MAIN, "    shooting_controller.embarked_squads_provider = lambda: state.embarked_squads",
       "    pass" + MARK)], (TB,)),

    # --------------------------------------------------------------- Boss Boomer
    ("Boomer: the WAGON is never a bearer",
     [(BM, "        return own + enh_boss_boomer.lent_models(squad, self._squads(), self.FLAG)",
       "        return own" + MARK)], (TB,)),
    ("Boomer: any model lends, WARBOSS or not",
     [(BO, '            if attached_units.model_has_datasheet_keyword(passenger, model, "WARBOSS"):',
       "            if True:" + MARK)], (TB,)),
    ("Boomer: a WARBOSS lends an ability he does not print",
     [(BO, "            if model.is_dead() or not getattr(model.profile, flag, False):",
       "            if model.is_dead():" + MARK)], (TB,)),
    ("Boomer: a dead Warboss still lends",
     [(BO, "            if model.is_dead() or not getattr(model.profile, flag, False):",
       "            if not getattr(model.profile, flag, False):" + MARK)], (TB,)),
    ("Boomer: no Enhancement or detachment needed",
     [(BO, "    if squad is None or not enhancements.is_active(squad, BOSS_BOOMER):", "    if squad is None:" + MARK)],
     (TB,)),
    ("Boomer: a Warboss anywhere lends, not only one aboard",
     [(BO, '        if id(getattr(passenger, "embarked_in", None)) not in own:', "        if False:" + MARK)], (TB,)),

    # ------------------------------------------------------------ Keep It Runnin'
    ("KIR: any ORKS unit, not ORKS INFANTRY",
     [(KIR, "            and ork_units.is_orks_infantry_unit(squad))", "            and ork_units.is_orks_unit(squad))" + MARK)],
     (TB,)),
    ("KIR: without the detachment",
     [(KIR, '    return (squad is not None and blitz_brigade.fields_blitz_brigade(getattr(squad, "owner", None))',
       "    return (squad is not None and True" + MARK)], (TB,)),
    ("KIR: within 12 inches instead of 6",
     [(KIR, "KEEP_IT_RUNNIN_RANGE_IN = 6.0", "KEEP_IT_RUNNIN_RANGE_IN = 12.0" + MARK)], (TB,)),
    ("embark: an engaged unit is offered",
     [(EFE, "        if engagement.is_engaged(squad, self.all_tokens):", "        if False:" + MARK)], (TB, AE)),
    ("embark: a unit that was not eligible to fight is offered",
     [(EFE, "        if not self.was_eligible_to_fight(squad):", "        if False:" + MARK)], (TB, AE)),
    ("embark: a nameless subclass is built",
     [(EFE, "        if not self.NAME:", "        if False:" + MARK)], (TB,)),
    ("main: Keep It Runnin' is never offered",
     [(MAIN, "            keep_it_runnin_controller.offer_at_end_of_fight_phase(" + NL
       + "                {t.squad for t in state.tokens if t.squad is not None})",
       "            pass" + MARK)], (TB,)),
    ("main: Keep It Runnin's window is never reset",
     [(MAIN, "        keep_it_runnin_controller.reset_phase()", "        pass" + MARK)], (TB,)),

    # ------------------------------------------------------------ Impending Krunch
    ("Krunch: in the opponent's Charge phase too",
     [(IK, "        if tt.phase != PHASE_CHARGE or squad.owner != tt.turn_owner:",
       "        if tt.phase != PHASE_CHARGE:" + MARK)], (TB,)),
    ("Krunch: outside the Charge phase too",
     [(IK, "        if tt.phase != PHASE_CHARGE or squad.owner != tt.turn_owner:",
       "        if squad.owner != tt.turn_owner:" + MARK)], (TB,)),
    ("Krunch: any unit, not a WAGON of Blitz Brigade",
     [(IK, "        if not blitz_brigade.applies(squad):", "        if False:" + MARK)], (TB,)),
    ("Krunch: offered when the charge engaged nothing",
     [(IK, "        if not self.targets_for(squad):", "        if False:" + MARK)], (TB,)),
    ("Krunch: offered again for the same charge move",
     [(IK, "        if key in self._offered:", "        if False:" + MARK)], (TB,)),
    ("Krunch: no -1",
     [(IK, "IMPENDING_KRUNCH_PENALTY = 1", "IMPENDING_KRUNCH_PENALTY = 0" + MARK)], (TB,)),
    ("Krunch: the AI buys it when everyone is already shocked",
     [(IK, "            if not worth_it(self.targets_for(squad)):", "            if False:" + MARK)], (TB,)),
    ("Krunch: the tests are queued but never started",
     [(IK, "        self.queue.drain()", "        pass" + MARK)], (TB,)),
    ("queue: a unit already waiting is queued twice",
     [(FSQ, "        if any(queued is target for queued, _p, _s, _m in self._queue):", "        if False:" + MARK)], (TB,)),
    ("main: Impending Krunch never hears a charge end",
     [(MAIN, "    charge_controller.on_charge_move_finished.append(" + NL
       + "        impending_krunch_controller.on_charge_move_finished)",
       "    pass" + MARK)], (TB,)),
    ("main: Impending Krunch's queue is never acknowledged",
     [(MAIN, "        impending_krunch_controller.on_dice_acknowledged()", "        pass" + MARK)], (TB,)),

    # --------------------------------------------------------- Readied Brawlers
    ("Readied Brawlers: the named gap dropped",
     [(BB, '    "Readied Brawlers": (', '    "_dropped": (' + MARK)], (TB,)),
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
