"""A/B probes for the Orks army rules (2026-09 codex): Waaagh!, riled up, War
Cry, the Advance re-roll, Unstable Energies - and the retired `waaagh=`
threading's replacement seams.

Each probe restores one piece of a plausible broken world AT THE SOURCE, runs the
suite(s) that are supposed to catch it, and puts the file back byte for byte. A
probe that does NOT turn its suite red is a finding about the TEST; a probe that
makes the suite CRASH is a finding too. Either way this file exits non-zero.

EXCLUSIVE. This rewrites source files while it runs. No suite, measurement, edit
or commit may run beside it - a commit that lands mid-probe captures the probed
world (error class 20). Every replacement carries the marker AB-PROBE, so after a
run

    git grep -n "AB-PROBE" -- . ":!ab_*.py" ":!CLAUDE*.md"

must come back empty. The driver also hashes every probed file before the first
probe and after the last, and fails if any differs.

`--check` only verifies that every anchor is unique and the marker is absent,
writing nothing - safe to run beside anything.

SHARED SEAMS ARE PROBED AGAINST EVERY SUITE THAT OWNS THEM: the [ASSAULT] gate
against test_event_chain_wiring.py section 7 as well, the Advance re-roll's claim
against the Autarch's suite, the save registrations against the scene-activation
completeness guard.
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
TIMEOUT_S = 900

T = "test_ork_army_rules.py"
WIRING = "test_event_chain_wiring.py"
AUTARCH = "test_autarchs_and_maugan_ra.py"
SCENE = "test_scene_activation.py"
ADVANCE = "test_advance_usage.py"

RU = os.path.join("game", "riled_up.py")
WC = os.path.join("game", "war_cry.py")
WA = os.path.join("game", "waaagh.py")
ARO = os.path.join("game", "advance_reroll_offer.py")
UE = os.path.join("game", "unstable_energies.py")
UNITS = os.path.join("game", "units.py")
ACT = os.path.join("game", "activation_state.py")
COLD = os.path.join("game", "coldstar.py")
MOVEX = os.path.join("game", "move_exceptions.py")
SH = os.path.join("game", "shooting.py")
INV = os.path.join("game", "invulnerable_save.py")
AG = os.path.join("ai", "agent_driver.py")
OBS = os.path.join("ai", "observation.py")
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
    try:
        out = subprocess.run([sys.executable, suite], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return None, None, "HUNG: no result within %ds" % TIMEOUT_S
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


# (label, [(path, anchor, replacement)], suites)
PROBES = [
    # --------------------------------------------------------------- riled up
    ("the turn serial ignores which turn of the round it is",
     [(RU, "    return (battle_round - 1) * 2 + index",
       "    return (battle_round - 1) * 2" + MARK)], (T,)),
    ("'until the start of your next turn' is a flat +2 from either turn",
     [(RU, "    return serial + (2 if owner == player else 1)",
       "    return serial + 2" + MARK)], (T,)),
    ("grant() accepts a unit without the Waaagh! ability",
     [(RU, "    if squad is None or not has_ability(squad):",
       "    if squad is None:" + MARK)], (T,)),
    ("a second, shorter grant shortens the first",
     [(RU, "                                   else max(current, expires_turn))",
       "                                   else expires_turn)" + MARK)], (T,)),
    ("an expired deadline is kept rather than cleared",
     [(RU, "            squad.riled_up_expires_turn = None",
       "            pass" + MARK)], (T,)),
    ("riled up lasts one turn too long",
     [(RU, "serial < deadline and has_ability(squad)",
       "serial <= deadline and has_ability(squad)" + MARK)], (T,)),
    ("refresh() stamps a deadline on a unit without the ability",
     [(RU, "serial < deadline and has_ability(squad)",
       "serial < deadline" + MARK)], (T,)),
    ("grant() waits for the next phase instead of stamping at once",
     [(RU, "        refresh((squad,), turn_tracker)",
       "        pass" + MARK)], (T,)),
    ("the [ASSAULT] grant mutates the shared weapon instance",
     [(RU, "    granted = copy.copy(weapon)",
       "    granted = weapon" + MARK)], (T,)),

    # ------------------------------------------------ the three effects' readers
    ("the Advance-shooting gate does not ask riled up (the adjuster chain still grants)",
     [(COLD, "            or riled_up.grants_assault(squad))",
       "            or False)" + MARK)], (T, WIRING)),
    ("the shooting adjuster chain does not grant [ASSAULT]",
     [(SH, "        weapon = riled_up.adjusted_weapon(weapon, self.active_squad)",
       "        pass" + MARK)], (T,)),
    ("the Save roll never sees the 5+ invulnerable save",
     [(INV, "        save = _better(save, riled_up.RILED_UP_INVULNERABLE_SAVE)",
       "        pass" + MARK)], (T,)),
    ("an Advance still stops a riled-up unit's charge",
     [(MOVEX, "            or riled_up.is_riled_up(squad)",
       "            or False" + MARK)], (T,)),

    # ---------------------------------------------------------------- War Cry
    ("War Cry is only offered in its owner's own Command phase ('your', not 'the')",
     [(WC, "        order = sorted(PLAYERS, key=lambda p: (p != owner, p))",
       "        order = [owner]" + MARK)], (T,)),
    ("an EMPTY orks_players reads as 'unknown' (truthiness)",
     [(WC, "        if self.orks_players is not None and player not in self.orks_players:",
       "        if self.orks_players and player not in self.orks_players:" + MARK)], (T,)),
    ("any army may use War Cry",
     [(WC, "        if self.orks_players is not None and player not in self.orks_players:",
       "        if False:" + MARK)], (T,)),
    ("War Cry is not once per battle",
     [(WC, lines("        if self.is_used(player):", "            return False"),
       "        pass" + MARK)], (T,)),
    ("the spend is not read back off the units (lost across a load)",
     [(WC, '        return any(getattr(s, "war_cry_called", False)',
       '        return False and any(getattr(s, "war_cry_called", False)' + MARK)], (T,)),
    ("the spend is never written onto the units",
     [(WC, "                squad.war_cry_called = True",
       "                pass" + MARK)], (T,)),
    ("War Cry lasts 'until the start of your next turn' instead",
     [(WC, "        deadline = riled_up.until_end_of_next_turn(tracker)",
       "        deadline = riled_up.until_start_of_your_next_turn(tracker, player)" + MARK)], (T,)),
    ("the AI is prompted instead of answering through its verdict",
     [(WC, "            if player in self.auto_players:",
       "            if False:" + MARK)], (T,)),
    ("the Decline option is not a red decline",
     [(WC, 'DECLINE_LABEL = "Decline"',
       'DECLINE_LABEL = "Maybe later"' + MARK)], (T,)),
    ("on_used is never called (the AI's notice overlay stays silent)",
     [(WC, "            self.on_used(player)",
       "            pass" + MARK)], (T,)),

    # ------------------------------------------------- who has the ability
    ("one Ork datasheet loses its Waaagh! flag",
     # The Gretchin's line - the one profile that prints its FACTION rule as
     # "Rules: Waaagh!". Its earlier anchor went with the pre-codex Battlewagon
     # comment in stage E3d.
     [(UNITS, '    waaagh = True  # "Rules: Waaagh!"',
       "    waaagh = False" + MARK)], (T,)),
    ("the Waaagh! flag leaks onto every profile",
     [(UNITS, '    psyker_level = 0  # the Orks army rule Unstable Energies: how many psychic levels '
              'this PSYKER may use per battle round ("psyker level N" in its abilities) - read by '
              'game/unstable_energies.py',
       '    psyker_level = 0' + NL + "    waaagh = True" + MARK)], (T,)),
    ("the Kill Rig loses its printed psyker level",
     [(UNITS, '    psyker_level = 1  # "Wurrboy (psyker level 1)" - the Unstable Energies budget, '
              'see game/unstable_energies.py',
       "    psyker_level = 0" + MARK)], (T,)),

    # ------------------------------------------------------ the Advance re-roll
    ("every unit may re-roll its Advance, not only Waaagh! units",
     [(WA, "        return has_waaagh(squad)",
       "        return True" + MARK)], (T,)),
    ("the AI keeps every Advance roll",
     [(ARO, "            if values[0] >= ADVANCE_REROLL_FLOOR:",
       "            if values[0] >= 1:" + MARK)], (T,)),
    ("the offer is not claimed once per roll (the reported loop)",
     [(ARO, lines("        if not self.dice_manager.claim_reroll_offer(self.LABEL):", "            return False"),
       "        pass" + MARK)], (T, AUTARCH)),

    # ------------------------------------------------------ Unstable Energies
    ("the psyker budget is never exceeded - because it is never checked",
     [(UE, "    return spent_this_round(squad, battle_round) + psychic_level <= level",
       "    return True" + MARK)], (T,)),
    ("a new battle round does not start the count again",
     [(UE, lines('    if getattr(squad, "unstable_energies_round", None) != battle_round:', "        return 0"),
       "    pass" + MARK)], (T,)),

    # ---------------------------------------------------------------- saving
    ("the riled-up deadline is not saved",
     [(ACT, '    "riled_up_expires_turn",', "    # AB-PROBE")], (T, SCENE)),
    ("the War Cry spend is not saved",
     [(ACT, '    "war_cry_called",', "    # AB-PROBE")], (T, SCENE)),

    # ------------------------------------------------------ the AI's verdict
    # The policy is the CLOCK and nothing else (restored 2026-09-21), so there
    # are two ways to break it and both are here: the wrong round, and losing
    # the "own Command phase" half. The three probes that used to stand here
    # (the round-3 fallback, the 18" enemy-turn reach, the 40% share) went with
    # the reach heuristic they measured - it is what called War Cry in round 1.
    ("War Cry is called a round early (back to round 1)",
     [(AG, "WAR_CRY_ROUND = 2", "WAR_CRY_ROUND = 1" + MARK)], (T,)),
    ("the verdict also fires in the OPPONENT's Command phase",
     [(AG, lines("    if turn_tracker.turn_owner != player:", "        return False"),
       "    pass" + MARK)], (T,)),
    ("the AI's charge planning forgets that riled up keeps the charge",
     [(AG, "        waaagh_charge_ok = riled_up.is_riled_up(squad)",
       "        waaagh_charge_ok = False" + MARK)], (ADVANCE,)),

    # ----------------------------------------------------- what the planner reads
    ("a non-Ork army is told about War Cry",
     [(OBS, "    if orks is not None and player not in orks:",
       "    if False:" + MARK)], (T,)),
    ("a riled-up unit's summary does not say so",
     [(OBS, "    if riled_up.is_riled_up(squad):",
       "    if False:" + MARK)], (T,)),

    # ---------------------------------------------------------- main.py wiring
    ("riled up is not re-stamped at the start of a phase",
     [(MAIN, lines("        # anything this phase can read it, and before War Cry's offer below.",
                   "        riled_up.refresh(state.all_squads(), turn_tracker)"),
       lines("        # anything this phase can read it, and before War Cry's offer below.",
             "        pass" + MARK))], (T,)),
    ("riled up is not re-stamped after a load",
     [(MAIN, lines("        # at the next phase change.",
                   "        riled_up.refresh(state.all_squads(), turn_tracker)"),
       lines("        # at the next phase change.", "        pass" + MARK))], (T,)),
    ("War Cry is never offered after the battle's first Command phase",
     [(MAIN, lines("            # army that has not used it, the phase owner first. game/war_cry.py.",
                   "            war_cry_controller.offer_at_start_of_command_phase(turn_tracker)"),
       lines("            # army that has not used it, the phase owner first. game/war_cry.py.",
             "            False and war_cry_controller.offer_at_start_of_command_phase(turn_tracker)" + MARK))],
     (T,)),
    ("a resumed snapshot is offered War Cry again",
     [(MAIN, "        if not resuming:", "        if True:" + MARK)], (T,)),
    ("the load path does not resume",
     [(MAIN, '        begin_battle((loaded.get("turn") or {}).get("turn_owner") or "Player 1", resuming=True)',
       '        begin_battle((loaded.get("turn") or {}).get("turn_owner") or "Player 1", resuming=False)'
       + MARK)], (T,)),
    ("the Advance re-roll is never offered before acknowledge()",
     [(MAIN, "            waaagh_advance_reroll_controller.maybe_offer_advance_reroll(_adv_squad)",
       "            False and waaagh_advance_reroll_controller.maybe_offer_advance_reroll(_adv_squad)" + MARK)],
     (T,)),
    ("the dice panel never shows the Re-roll Advance button",
     [(MAIN, "        lambda: waaagh_advance_reroll_controller.pending_roll_choice(movement_controller.selected_squad),",
       "        lambda: None," + MARK)], (T,)),
    ("War Cry is never told whose army rule it is",
     [(MAIN, "    war_cry_controller.orks_players = waaagh_module.qualifying_players(",
       "    war_cry_controller.orks_players = None and waaagh_module.qualifying_players(" + MARK)], (T,)),
    ("the AI's War Cry verdict is never injected",
     [(MAIN, "        verdict=lambda player, tracker: war_cry_verdict(player, tracker, state.tokens))",
       "        verdict=None)" + MARK)], (T,)),
    ("take_one_action() is not handed the War Cry controller",
     [(MAIN, "war_cry_controller=war_cry_controller, arrokon_controller=arrokon_controller,",
       "arrokon_controller=arrokon_controller," + MARK)], (T,)),
]


def main():
    check_only = "--check" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    probes = [p for p in PROBES if not only or any(o.lower() in p[0].lower() for o in only)]

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
        if got is None:
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
                if got is None:
                    verdict = "CRASH"
                    detail = "suite crashed or hung - a probe must turn it RED, not crash it"
                    bad += 1
                    tail = [ln for ln in out.splitlines() if ln.strip()][-1:]
                elif tot - got > base[suite]:
                    verdict = "BITES"
                    detail = "%s/%s (%d red)" % (got, tot, tot - got)
                    tail = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("FAIL")][:1]
                else:
                    verdict = "NO BITE"
                    detail = "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
                    bad += 1
                    tail = []
                print("  %-8s %s [%s]: %s" % (verdict, label, suite, detail), flush=True)
                for ln in tail:
                    print("             " + ln[:110], flush=True)
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
