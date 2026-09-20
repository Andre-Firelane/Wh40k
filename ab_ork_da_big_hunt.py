"""A/B probes for Da Big Hunt (Mecha Orks stage G5): Da Hunt is On in both
adjuster chains, Glory Hog, the three Stratagems (Where D'ya Fink You're Going?,
Goaded into Action, Instinctive Hunters), the two mechanisms this stage
extracted (game/forced_desperate_escape.py, game/board_edges.py), the surge gate
this stage had to fix, main.py's wiring - and It Came from da Drops' named gap.

Same driver as ab_ork_blitz_brigade.py: each probe restores one piece of a
plausible broken world AT THE SOURCE, runs the suite(s) that are supposed to catch
it, and puts the file back byte for byte. A probe that does NOT turn its suite red
is a finding about the TEST; one that CRASHES or HANGS a suite is a finding too.

EXCLUSIVE. This rewrites source files while it runs. No suite, measurement, edit
or commit may run beside it - and a parallel session must be told first. Every
replacement carries the marker AB-PROBE, so after a run

    git grep -n --untracked "AB-PROBE" -- . ":!ab_*.py" ":!CLAUDE*.md" ":!docs/*"

must come back empty. The driver hashes every probed file before the first probe
and after the last, and every suite run has a timeout.

game/factions/orks.py, game/movement.py and game/squad.py are CRLF: their
anchors are single lines.

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


TH = "test_ork_da_big_hunt.py"
TD = "test_detachments.py"
TX = "test_exodites.py"          # Cornered Prey, the registry's other source
TS = "test_secondary_missions.py"  # the board-edge helpers' first reader
TW = "test_event_chain_wiring.py"

OR = os.path.join("game", "factions", "orks.py")
CF = os.path.join("game", "config.py")
BH = os.path.join("game", "da_big_hunt.py")
GH = os.path.join("game", "enh_glory_hog.py")
EN = os.path.join("game", "enhancements.py")
MX = os.path.join("game", "move_exceptions.py")
FD = os.path.join("game", "forced_desperate_escape.py")
FB = os.path.join("game", "fall_back.py")
HZ = os.path.join("game", "hazard.py")
WD = os.path.join("game", "da_hunt_where_dya_fink.py")
GI = os.path.join("game", "da_hunt_goaded_into_action.py")
IH = os.path.join("game", "da_hunt_instinctive_hunters.py")
BE = os.path.join("game", "board_edges.py")
MV = os.path.join("game", "movement.py")
SH = os.path.join("game", "shooting.py")
FT = os.path.join("game", "fight.py")
AP = os.path.join("game", "ui", "action_panel.py")
AG = os.path.join("ai", "agent_driver.py")
MAIN = "main.py"


# (label, [(path, anchor, replacement)], suites)
PROBES = [
    # ------------------------------------------------------------ the detachment
    ("detachment: no config setting",
     [(OR, '    setting="DA_BIG_HUNT_PLAYERS",', "    setting=None," + MARK)], (TH, TD)),
    ("config: Da Big Hunt held by Player 2 by default",
     [(CF, "DA_BIG_HUNT_PLAYERS = ()", 'DA_BIG_HUNT_PLAYERS = ("Player 2",)' + MARK)], (TH,)),

    # ------------------------------------------------------------ Da Hunt is On
    ("rule: any unit, not a BEAST SNAGGA one",
     [(BH, "    return is_beast_snagga_unit(squad) and is_monster_or_vehicle_unit(target_squad)",
       "    return is_monster_or_vehicle_unit(target_squad)" + MARK)], (TH,)),
    ("rule: any target, not only MONSTER/VEHICLE",
     [(BH, "    return is_beast_snagga_unit(squad) and is_monster_or_vehicle_unit(target_squad)",
       "    return is_beast_snagga_unit(squad)" + MARK)], (TH,)),
    ("rule: without the detachment",
     [(BH, "    if not fields_da_big_hunt(getattr(squad, \"owner\", None)):",
       "    if False:" + MARK)], (TH,)),
    ("rule: -1 AP instead of +1",
     [(BH, "    sharpened.ap = weapon.ap - DA_HUNT_IS_ON_AP", "    sharpened.ap = weapon.ap + DA_HUNT_IS_ON_AP" + MARK)],
     (TH,)),
    ("rule: the shared WeaponProfile is mutated instead of copied",
     [(BH, "    sharpened = copy.copy(weapon)", "    sharpened = weapon" + MARK)], (TH,)),
    ("shooting: the chain has no Da Hunt is On link",
     [(SH, "        weapon = da_big_hunt.adjusted_weapon(weapon, self.active_squad, target_squad)",
       "        pass" + MARK)], (TH,)),
    ("fight: the chain has no Da Hunt is On link",
     [(FT, "        weapon = da_big_hunt.adjusted_weapon(" + NL
       + "            weapon, self.fighting_squad," + NL
       + "            target_squad if target_squad is not None else self.target_squad)",
       "        pass" + MARK)], (TH,)),
    ("gap: It Came from da Drops dropped instead of named",
     [(BH, '    "It Came from da Drops": (', '    "_dropped": (' + MARK)], (TH,)),

    # ---------------------------------------------------------------- Glory Hog
    ("Glory Hog: no Enhancement needed",
     [(GH, "    return squad is not None and enhancements.is_active(squad, GLORY_HOG)",
       "    return squad is not None" + MARK)], (TH,)),
    ("Glory Hog: any ORKS CHARACTER may bear it, BEAST SNAGGA or not",
     [(EN, '     _beast_snagga_character, "BEAST SNAGGA model only")',
       '     _orks_character, "BEAST SNAGGA model only")' + MARK)], (TH,)),
    ("Glory Hog: folded into the SHOOTING half as well",
     [(MX, "def may_shoot_after_falling_back(squad):",
       "def may_shoot_after_falling_back(squad):" + NL
       + "    if enh_glory_hog.applies(squad):" + NL
       + "        return True" + MARK)], (TH,)),
    ("Glory Hog: not folded into the charge half at all",
     [(MX, "            or enh_glory_hog.applies(squad)", "            or False" + MARK)], (TH,)),

    # ------------------------------------------- Where D'ya Fink You're Going?
    ("WDF: offered in the owner's own Movement phase too",
     [(WD, "        if tt.phase != PHASE_MOVEMENT or victim.owner != tt.turn_owner:",
       "        if tt.phase != PHASE_MOVEMENT:" + MARK)], (TH,)),
    ("WDF: offered in any phase",
     [(WD, "        if tt.phase != PHASE_MOVEMENT or victim.owner != tt.turn_owner:",
       "        if victim.owner != tt.turn_owner:" + MARK)], (TH,)),
    ("WDF: any engaged unit marks, BEAST SNAGGA or not",
     [(WD, "            if not da_big_hunt.fields_da_big_hunt(other.owner) or not da_big_hunt.is_beast_snagga_unit(other):",
       "            if False:" + MARK)], (TH,)),
    ("WDF: the mark is never set",
     [(WD, "        hunter.where_dya_fink_active = True", "        pass" + MARK)], (TH,)),
    ("WDF: nothing is frozen at the purchase - the late-buy case",
     [(WD, "            forced_desperate_escape.snapshot(victim, self.all_tokens)",
       "            pass" + MARK)], (TH,)),
    ("WDF: three extra rolls for an INFANTRY victim too",
     [(WD, "    if not is_monster_or_vehicle_unit(victim):" + NL + "        return 0" + NL
       + "    return WHERE_DYA_FINK_EXTRA_ROLLS * len(marked_hunters_engaged_with(victim, all_tokens))",
       "    return WHERE_DYA_FINK_EXTRA_ROLLS * len(marked_hunters_engaged_with(victim, all_tokens))" + MARK)],
     (TH,)),
    ("WDF: one extra roll per unit instead of three",
     [(WD, "WHERE_DYA_FINK_EXTRA_ROLLS = 3", "WHERE_DYA_FINK_EXTRA_ROLLS = 1" + MARK)], (TH,)),
    ("WDF: the -1 applies to a victim that is not battle-shocked",
     [(WD, '    if not getattr(victim, "battle_shocked", False):' + NL + "        return 0",
       "    if False:" + NL + "        return 0" + MARK)], (TH,)),
    ("WDF: the mark outlives its phase",
     [(WD, "        if getattr(squad, \"where_dya_fink_active\", False):" + NL
       + "            squad.where_dya_fink_active = False",
       "        if False:" + NL + "            squad.where_dya_fink_active = False" + MARK)], (TH,)),
    ("WDF: the AI buys it against anything",
     [(WD, "            if not self.worth_it(victim):" + NL + "                return False",
       "            if False:" + NL + "                return False" + MARK)], (TH,)),

    # ----------------------------------------------- the desperate-escape registry
    ("registry: Where D'ya Fink is not a source",
     [(FD, "    (da_hunt_where_dya_fink.WHERE_DYA_FINK_NAME,", "    (\"_dropped\"," + MARK)], (TH,)),
    ("registry: Cornered Prey is not a source",
     [(FD, "    (cornered_prey.CORNERED_PREY_LABEL,", "    (\"_dropped\"," + MARK)], (TH,)),
    ("registry: the sources do not sum",
     [(FD, "def _live_penalty(squad, all_tokens):" + NL
       + "    return sum(fn(squad, all_tokens) for _label, _f, fn, _x in SOURCES if fn is not None)",
       "def _live_penalty(squad, all_tokens):" + NL
       + "    return max([fn(squad, all_tokens) for _label, _f, fn, _x in SOURCES if fn is not None] or [0])" + MARK)],
     (TH,)),
    ("fall_back: the mode is not forced at declare()",
     [(FB, "        if squad.battle_shocked or forced_desperate_escape.forces(",
       "        if squad.battle_shocked or False and forced_desperate_escape.forces(" + MARK)], (TH, TX)),
    ("fall_back: Ordered Retreat is allowed anyway",
     [(FB, "        if mode == ORDERED_RETREAT and forced_desperate_escape.forces(",
       "        if False and forced_desperate_escape.forces(" + MARK)], (TH, TX)),
    ("fall_back: the extra hazard rolls are not rolled",
     [(FB, "                squad, len(squad.models) + forced_desperate_escape.extra_hazard_rolls(squad, tokens),",
       "                squad, len(squad.models)," + MARK)], (TH,)),
    ("fall_back: the hazard rolls take no penalty",
     [(FB, "                penalty=forced_desperate_escape.hazard_penalty(squad, tokens),",
       "                penalty=0," + MARK)], (TH,)),
    ("fall_back: nothing is frozen when the mode is chosen",
     [(FB, "        forced_desperate_escape.snapshot(self.acting_squad, self._all_tokens())",
       "        pass" + MARK)], (TH,)),
    ("registry: the frozen snapshot is ignored at the roll",
     [(FD, "    return max(_live_penalty(squad, all_tokens), _frozen(squad)[0])",
       "    return _live_penalty(squad, all_tokens)" + MARK)], (TH,)),
    ("registry: the frozen extra rolls are ignored at the roll",
     [(FD, "    return max(_live_extra_rolls(squad, all_tokens), _frozen(squad)[1])",
       "    return _live_extra_rolls(squad, all_tokens)" + MARK)], (TH,)),
    ("registry: a finished fall back keeps its snapshot",
     [(FD, '    if squad is not None and getattr(squad, "forced_escape_hazard", None):' + NL
       + "        squad.forced_escape_hazard = None", "    pass" + MARK)], (TH,)),
    ("hazard: the roll line does not name the modifier",
     [(FB, '                penalty_label=" and ".join(forced_desperate_escape.reasons(squad, tokens)))',
       '                penalty_label="")' + MARK)], (TH,)),
    ("hazard: the penalty does not reach the MORTAL WOUNDS",
     [(HZ, "        total = hazard_mortal_wounds(self.squad, rolls, self.penalty)",
       "        total = hazard_mortal_wounds(self.squad, rolls)" + MARK)], (TH,)),
    ("hazard: the penalty does not reach the failure count",
     [(HZ, "            f\"Hazard Rolls {rolls}: {hazard_failures(rolls, self.penalty)}/{len(rolls)} failed{self._note} -> {total} mortal wound(s).\"",
       "            f\"Hazard Rolls {rolls}: {hazard_failures(rolls)}/{len(rolls)} failed{self._note} -> {total} mortal wound(s).\"" + MARK)],
     (TH,)),

    # ------------------------------------------------------- Goaded into Action
    ("Goaded: offered to every unit on the board, not the ones that lost a wound",
     [(GI, "        wounded = set(wounded or ())",
       '        wounded = {getattr(t, "squad", None) for t in self.all_tokens}' + MARK)], (TH,)),
    # BOTH readings of "unengaged" at once: the printed TARGET clause here and
    # rule 21.02's own ELIGIBLE IF in the MovementController. Either alone
    # leaves the other refusing, which is what belt and braces means.
    ("Goaded: offered to an ENGAGED unit",
     [(GI, "        if is_engaged(squad, self.all_tokens):", "        if False:" + MARK),
      # CRLF file: one-line anchor. An early return opens 21.02's own gate.
      (MV, "        if squad.battle_shocked:",
       "        return True" + MARK + NL + "        if squad.battle_shocked:")], (TH,)),
    ("Goaded: 21.02's own eligibility is never asked",
     [(GI, "        if self.movement_controller is not None and not self.movement_controller.can_make_surge_move(squad):",
       "        if False:" + MARK)], (TH,)),
    ("Goaded: any unit, not a BEAST SNAGGA one of this detachment",
     [(GI, "        if not da_big_hunt.fields_da_big_hunt(squad.owner) or not da_big_hunt.is_beast_snagga_unit(squad):",
       "        if False:" + MARK)], (TH,)),
    ("Goaded: offered in the unit's OWN Shooting phase",
     [(GI, "        if tt.phase != PHASE_SHOOTING or squad is None or squad.owner == tt.turn_owner:",
       "        if tt.phase != PHASE_SHOOTING or squad is None:" + MARK)], (TH,)),
    ("Goaded: the surge move is never opened",
     [(GI, "        mc.start_surge_move(squad, float(distance), closest_enemy_squad(squad, self.all_tokens))",
       "        pass" + MARK)], (TH,)),
    ("Goaded: active_player is not held by the reacting player",
     [(GI, "            self.turn_tracker.set_active(squad.owner)", "            pass" + MARK)], (TH,)),
    ("Goaded: the re-roll is offered to a unit that is not riled up",
     [(GI, "                or not riled_up.is_riled_up(squad) or not dm.rerollable_indices()",
       "                or not dm.rerollable_indices()" + MARK)], (TH,)),
    ("Goaded: the AI re-rolls a good die too",
     [(GI, "        if dm.pending_values[0] > 2:" + NL + "            return False",
       "        if False:" + NL + "            return False" + MARK)], (TH,)),
    ("Goaded: the wound ledger is never written",
     [(SH, "            self._wounds_when_hit_this_activation.setdefault(" + NL
       + "                id(target_squad), _squad_wound_total(target_squad))",
       "            pass" + MARK)], (TH,)),
    ("Goaded: the ledger answers \"hit\" instead of \"lost a wound\"",
     [(SH, "             if _squad_wound_total(squad) < self._wounds_when_hit_this_activation.get(id(squad), 0)),",
       "             if True)," + MARK)], (TH,)),
    # CRLF file: the ANCHOR is one line (the replacement may span several -
    # only the match has to survive the line endings).
    ("movement: a surge needs the Movement phase again",
     [(MV, '        what the printed line actually says."""',
       '        what the printed line actually says."""' + NL
       + "        if not self.can_move(squad):" + NL
       + "            return False" + MARK)], (TH,)),
    ("movement: \"surge\" is not a reactive mode",
     [(MV, '                                     "surge"})', "                                     })" + MARK)],
     (TH, TW)),
    ("panel: the surge move's Confirm is not routed to the controller",
     [(AP, "            elif is_surge and goaded_into_action_controller is not None:" + NL
       + "                # Da Big Hunt's Goaded into Action owns the only surge move in",
       "            elif False:" + NL
       + "                # Da Big Hunt's Goaded into Action owns the only surge move in" + MARK)], (TH,)),
    ("panel: its Cancel is not routed to the controller",
     [(AP, "            elif is_surge and goaded_into_action_controller is not None:" + NL
       + "                cancel_callback = goaded_into_action_controller.cancel_move",
       "            elif False:" + NL
       + "                cancel_callback = goaded_into_action_controller.cancel_move" + MARK)], (TH,)),

    # -------------------------------------------------------- Instinctive Hunters
    ("Hunters: no edge needed",
     [(IH, "        if not board_edges.unit_is_within_of_edge(squad, INSTINCTIVE_HUNTERS_EDGE_RANGE_IN):",
       "        if False:" + MARK)], (TH,)),
    ("Hunters: 12 inches from the edge instead of 6",
     [(IH, "INSTINCTIVE_HUNTERS_EDGE_RANGE_IN = 6.0", "INSTINCTIVE_HUNTERS_EDGE_RANGE_IN = 12.0" + MARK)], (TH,)),
    ("Hunters: an engaged unit is offered",
     [(IH, "        if engagement.is_engaged(squad, self.all_tokens):", "        if False:" + MARK)], (TH,)),
    ("Hunters: offered when the withdrawal is doomed",
     [(IH, "        if withdrawal_is_doomed(self.turn_tracker):", "        if False:" + MARK)], (TH,)),
    ("Hunters: any unit, not a BEAST SNAGGA one of this detachment",
     [(IH, "        if not da_big_hunt.fields_da_big_hunt(squad.owner) or not da_big_hunt.is_beast_snagga_unit(squad):",
       "        if False:" + MARK)], (TH,)),
    ("Hunters: the window is a live clock read",
     [(IH, "        if not self._window.is_open(squad.owner):", "        if False:" + MARK)], (TH,)),
    ("Hunters: the owner of the ending Fight phase is asked too",
     [(IH, "        for player in sorted({s.owner for s in squads if s is not None and s.owner != mover_before}):",
       "        for player in sorted({s.owner for s in squads if s is not None}):" + MARK)], (TH,)),
    ("Hunters: nothing is withdrawn",
     [(IH, "        return withdraw_to_reserves(", "        return True or withdraw_to_reserves(" + MARK)], (TH,)),

    # ----------------------------------------------------------- board_edges
    ("edges: a dead model still holds an edge",
     [(BE, "        if model.is_dead():", "        if False:" + MARK)], (TH,)),
    ("edges: the mission deck keeps its own copy",
     [(BE, "DEFAULT_EDGE_RANGE_IN = 6.0", "DEFAULT_EDGE_RANGE_IN = 0.0" + MARK)], (TH, TS)),

    # ------------------------------------------------------------- main.py
    ("main: Where D'ya Fink never hears a fall back declared",
     [(MAIN, "        where_dya_fink_controller.notify_selected_to_fall_back]",
       "        ]" + MARK)], (TH,)),
    ("main: its mark is never cleared",
     [(MAIN, "        where_dya_fink_controller.reset_phase(_horde_squads)", "        pass" + MARK)], (TH,)),
    # The ordering bug this stage shipped for one run: the reset written ABOVE
    # the line that builds the set it is handed. main() dies with
    # UnboundLocalError at the first phase change; section 32 of the wiring
    # guard is what now says so in two seconds.
    ("main: the phase reset is handed a set built further down",
     [(MAIN, NL + "        where_dya_fink_controller.reset_phase(_horde_squads)", "" + MARK),
      (MAIN, "        instinctive_hunters_controller.reset_phase()",
       "        instinctive_hunters_controller.reset_phase()" + NL
       + "        where_dya_fink_controller.reset_phase(_horde_squads)")], (TW,)),
    ("main: Goaded into Action never hears a unit finish shooting",
     [(MAIN, "    shooting_controller.on_squad_finished_shooting.append(" + NL
       + "        goaded_into_action_controller.on_squad_finished_shooting)", "    pass" + MARK)], (TH,)),
    ("main: it is never handed the ShootingController's ledger",
     [(MAIN, "    goaded_into_action_controller.shooting_controller = shooting_controller",
       "    pass" + MARK)], (TH,)),
    ("main: its D6 is never acknowledged",
     [(MAIN, "        goaded_into_action_controller.on_dice_acknowledged()", "        pass" + MARK)], (TH,)),
    ("main: the AI's riled-up re-roll is never offered",
     [(MAIN, "        goaded_into_action_controller.maybe_reroll_for_ai()", "        pass" + MARK)], (TH,)),
    ("main: the phase gate does not wait for an open surge move",
     [(MAIN, "            or goaded_into_action_controller.is_busy", "            or False" + MARK)], (TH,)),
    ("main: the panel is not handed the controller",
     [(MAIN, "            goaded_into_action_controller=goaded_into_action_controller,",
       "            goaded_into_action_controller=None," + MARK)], (TH,)),
    ("main: Instinctive Hunters is never offered",
     [(MAIN, "            instinctive_hunters_controller.offer_at_end_of_fight_phase(" + NL
       + "                {t.squad for t in state.tokens if t.squad is not None}, mover_before)",
       "            pass" + MARK)], (TH,)),
    ("main: its offer reads the live clock instead of mover_before",
     [(MAIN, "            instinctive_hunters_controller.offer_at_end_of_fight_phase(" + NL
       + "                {t.squad for t in state.tokens if t.squad is not None}, mover_before)",
       "            instinctive_hunters_controller.offer_at_end_of_fight_phase(" + NL
       + "                {t.squad for t in state.tokens if t.squad is not None}, turn_tracker.turn_owner)" + MARK)],
     (TH,)),
    ("main: its window is never closed",
     [(MAIN, "        instinctive_hunters_controller.reset_phase()", "        pass" + MARK)], (TH,)),
    ("agent_driver: the AI has no surge destination",
     [(AG, "def goaded_into_action_destination(state, squad, shooter):",
       "def _unused_goaded_into_action_destination(state, squad, shooter):" + MARK)], (TH,)),
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
