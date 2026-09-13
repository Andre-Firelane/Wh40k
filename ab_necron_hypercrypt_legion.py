"""A/B probes for the Hypercrypt Legion: its rule, four Enhancements, six
Stratagems, and the engine seams the detachment needed.

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

SHARED SEAMS ARE PROBED AGAINST EVERY SUITE THAT OWNS THEM.
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

HC = "test_necron_hypercrypt_legion.py"
UI = "test_necron_detachment_ui.py"
WIRING = "test_event_chain_wiring.py"
TITANS = "test_necron_titans.py"
REROLL = "test_reroll_scope.py"
RIDE = "test_aeldari_detachment_rules.py"

BS = os.path.join("game", "battle_size.py")
EOW = os.path.join("game", "end_of_turn_withdrawal.py")
HP = os.path.join("game", "hypercrypt_hyperphasing.py")
OV = os.path.join("game", "enh_dimensional_overseer.py")
TY = os.path.join("game", "enh_arisen_tyrant.py")
OF = os.path.join("game", "enh_osteoclave_fulcrum.py")
QD = os.path.join("game", "hypercrypt_quantum_deflection.py")
ED = os.path.join("game", "hypercrypt_entropic_damping.py")
RC = os.path.join("game", "hypercrypt_reanimation_crypts.py")
CP = os.path.join("game", "hypercrypt_cosmic_precision.py")
DC = os.path.join("game", "hypercrypt_dimensional_corridor.py")
HR = os.path.join("game", "hypercrypt_hyperphasic_recall.py")
ING = os.path.join("game", "ingress.py")
EG = os.path.join("game", "eternity_gate.py")
CH = os.path.join("game", "charge.py")
FI = os.path.join("game", "fight.py")
SH = os.path.join("game", "shooting.py")
MV = os.path.join("game", "movement.py")
RP = os.path.join("game", "reanimation_protocols.py")
RS = os.path.join("game", "reroll_scope.py")
INV = os.path.join("game", "invulnerable_save.py")
AP = os.path.join("game", "ui", "action_panel.py")
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


def gone(*anchor_lines):
    """Replace a guard of the form `if ...:` / `    return ...` with `pass`,
    keeping the anchor's own indentation."""
    indent = anchor_lines[0][:len(anchor_lines[0]) - len(anchor_lines[0].lstrip())]
    return lines(*anchor_lines), indent + "pass" + MARK


# (label, [(path, anchor, replacement)], suites)
PROBES = [
    # ------------------------------------------------------------ battle size
    ("an unknown battle size reads as itself, not Strike Force",
     [(BS, "    return key if key in BATTLE_SIZES else DEFAULT_BATTLE_SIZE",
       "    return key" + MARK)], (HC,)),

    # ------------------------------------------------------------ Hyperphasing
    ("Hyperphasing's cap ignores the battle size",
     [(HP, "    return battle_size_module.lookup(UNITS_BY_BATTLE_SIZE, battle_size)",
       "    return UNITS_BY_BATTLE_SIZE[battle_size_module.STRIKE_FORCE]" + MARK)], (HC,)),
    ("the Dimensional Overseer adds nothing to the cap",
     [(HP, "                + enh_dimensional_overseer.extra_units(player, self.game_state))",
       "                + 0)" + MARK)], (HC,)),
    # The module's embarked_in filter was measured redundant and removed (an
    # embarked unit is in neither container); what can really go wrong is reading
    # a THIRD container, which is what this probe does.
    ("the Dimensional Overseer counts an EMBARKED bearer",
     [(OV, '    for squad in getattr(game_state, "reserves", ()) or ():',
       '    for squad in list(getattr(game_state, "reserves", ()) or ())'
       ' + list(getattr(game_state, "embarked_squads", ()) or ()):' + MARK)], (HC,)),
    ("the Dimensional Overseer counts only a bearer on the battlefield",
     [(OV, *gone("    for squad in getattr(game_state, \"reserves\", ()) or ():",
                 "        if squad not in squads:",
                 "            squads.append(squad)"))], (HC,)),
    ("a doomed withdrawal is still offered (round 3's destruction)",
     [(HP, lines("        if withdrawal_is_doomed(self.turn_tracker):", "            return False",
                 '        if getattr(squad, "embarked_in", None) is not None:'),
       lines("        pass" + MARK, '        if getattr(squad, "embarked_in", None) is not None:'))], (HC,)),
    ("doomed read one round early",
     [(HP, '"battle_round", 0) == RESERVES_DESTROYED_AFTER_ROUND + 1',
       '"battle_round", 0) == RESERVES_DESTROYED_AFTER_ROUND' + MARK)], (HC,)),
    ("an embarked unit may be hyperphased",
     [(HP, lines('        if getattr(squad, "embarked_in", None) is not None:', "            return False",
                 "        tokens = "),
       lines("        pass" + MARK, "        tokens = "))], (HC,)),
    ("the withdrawal cap is not re-read before each prompt",
     [(EOW, lines('        if self.remaining(getattr(squad, "owner", None)) <= 0:', "            return False"),
       "        pass" + MARK)], (HC, RIDE)),
    ("the withdrawal takes a unit within Engagement Range",
     [(EOW, "        return not self.is_engaged(squad)", "        return True" + MARK)], (HC, RIDE)),
    ("the AI's withdrawal policy is never consulted",
     [(EOW, "        if self.choose is not None:", "        if False:" + MARK)], (HC,)),
    ("an AI owner is prompted like a human",
     [(EOW, "            (s for s in others if s.owner not in self.auto_players),",
       "            (s for s in others)," + MARK)], (HC,)),

    # ------------------------------------------------------- relaxed arrival
    ("the opponent's zone is banned again for a relaxed arrival (the 20.04 disagreement)",
     [(ING, lines("        if self._uses_relaxed_arrival(squad):",
                  '            # "can be set up ANYWHERE on the battlefield that is more than 6"'),
       lines("        if False:" + MARK,
             '            # "can be set up ANYWHERE on the battlefield that is more than 6"'))], (HC,)),
    ("the AI's landing sweep ignores a relaxed arrival",
     [(AG, "    if ingress_controller._has_deep_strike(squad) or ingress_controller._uses_relaxed_arrival(squad):",
       "    if ingress_controller._has_deep_strike(squad):" + MARK)], (HC,)),

    # ------------------------------------------------------- the gate's lock
    ("the Eternity Gate rides the shared lock again",
     [(EG, "        passenger.eternity_gate_charge_locked = True",
       "        passenger.charge_locked_until_end_of_turn = True" + MARK)], (HC, TITANS)),
    ("rule 11.02 ignores the gate's lock",
     # game/charge.py has CRLF line endings, so the anchor stays on one line.
     [(CH, "        if squad.eternity_gate_charge_locked:", "        if False:" + MARK)], (HC,)),
    ("the gate's Monolith always counts as having started on the battlefield",
     [(EG, lines("        passenger.eternity_gate_bearer_started_on_board = not bool(",
                 '            getattr(monolith_squad, "set_up_this_turn", False))'),
       "        passenger.eternity_gate_bearer_started_on_board = True" + MARK)], (HC,)),
    ("the ingress Confirm never records a gate arrival",
     [(ING, lines("            if self.eternity_gate_squad is squad:",
                  "                self.gate_arrivals_this_turn.add(squad)"),
       lines("            if False:" + MARK, "                self.gate_arrivals_this_turn.add(squad)"))], (HC,)),
    ("gate arrivals outlive the turn",
     [(ING, lines("        self.ingressed_this_turn = set()", "        self.gate_arrivals_this_turn = set()", "",
                  "    def can_ingress"),
       lines("        self.ingressed_this_turn = set()" + MARK, "", "    def can_ingress"))], (HC,)),
    ("main.py never clears the gate's lock at the end of a turn",
     [(MAIN, "                _gate_squad.eternity_gate_charge_locked = False",
       "                pass" + MARK)], (HC,)),

    # ------------------------------------------------------ the fight ledger
    ("the fight ledger re-takes its count at every hit",
     [(FI, "            self._living_when_first_hit.setdefault(id(target_squad), _living_count(target_squad))",
       "            self._living_when_first_hit[id(target_squad)] = _living_count(target_squad)" + MARK)], (HC,)),
    ("the fight ledger survives into the next activation",
     [(FI, lines("        # _actually_finish_current_fight() and still has to read it.",
                 "        self._living_when_first_hit = {}"),
       lines("        # _actually_finish_current_fight() and still has to read it.", "        pass" + MARK))],
     (HC,)),

    # --------------------------------------------------- off-board reanimation
    ("an off-board revive stands the model on the battlefield",
     [(RP, lines("    if off_board:", "        revived = []"),
       lines("    if False:" + MARK, "        revived = []"))], (HC,)),
    ("the boosts are asked for a unit in Reserves",
     [(RP, "    if boost is not None and not off_board:", "    if boost is not None:" + MARK)], (HC,)),

    # ------------------------------------------------------------ Enhancements
    ("Arisen Tyrant offers the whole roll whether or not the unit was set up",
     [(TY, '    return applies(squad) and bool(getattr(squad, "set_up_this_turn", False))',
       "    return applies(squad)" + MARK)], (HC,)),
    ("shooting never names Arisen Tyrant's whole roll",
     [(SH, "        if enh_arisen_tyrant.offers_full_reroll(self.active_squad):",
       "        if False:" + MARK)], (HC,)),
    ("shooting loses Arisen Tyrant's 1s",
     [(SH, "        tyrant_ones = enh_arisen_tyrant.applies(self.active_squad)",
       "        tyrant_ones = False" + MARK)], (HC,)),
    ("fight never names Arisen Tyrant's whole roll",
     [(FI, "        if enh_arisen_tyrant.offers_full_reroll(self.fighting_squad):",
       "        if False:" + MARK)], (HC,)),
    ("fight loses Arisen Tyrant's 1s",
     [(FI, "        if ones and enh_arisen_tyrant.applies(self.fighting_squad):",
       "        if False:" + MARK)], (HC,)),
    ("Arisen Tyrant leaves the ones-or-whole set",
     [(RS, "    ARISEN_TYRANT_LABEL,                # Hypercrypt Legion Enhancement (hit)",
       "    # ARISEN_TYRANT_LABEL" + MARK)], (HC, REROLL)),
    ("the Transfer Node's Advance is rolled",
     [(MV, "        elif enh_hyperspatial_transfer_node.skips_advance_roll(self.selected_squad):",
       "        elif False:" + MARK)], (HC,)),
    ("Osteoclave Fulcrum grants the bearer alone",
     [(OF, lines("        for model in models:", "            model.profile.deep_strike = True"),
       lines("        for model in models[-1:]:" + MARK, "            model.profile.deep_strike = True"))], (HC,)),
    ("Osteoclave Fulcrum is granted twice",
     [(OF, lines('        if all(getattr(m.profile, "deep_strike", False) for m in models):', "            continue"),
       "        pass" + MARK)], (HC,)),
    ("main.py never applies Osteoclave Fulcrum at Declare Battle Formations",
     [(MAIN, lines("        enh_osteoclave_fulcrum.apply_all(",
                   "            _all_squads(state, pregame_controller), game_log=game_log)"),
       lines("        False and enh_osteoclave_fulcrum.apply_all(" + MARK,
             "            _all_squads(state, pregame_controller), game_log=game_log)"))], (HC,)),

    # ------------------------------------------------------ Quantum Deflection
    ("Quantum Deflection is offered in YOUR Shooting phase",
     [(QD, "        return tt.phase == PHASE_SHOOTING and tt.turn_owner == attacker.owner",
       "        return tt.phase == PHASE_SHOOTING" + MARK)], (HC,)),
    ("Quantum Deflection forgets 'or the Fight phase'",
     [(QD, '            return tt.phase == PHASE_FIGHT          # "the Fight phase" - nobody\'s',
       "            return False" + MARK)], (HC,)),
    ("Quantum Deflection is offered when the save buys nothing",
     [(QD, "        if is_active(target) or not grant_changes_anything(target, melee):",
       "        if is_active(target):" + MARK)], (HC,)),
    ("the invulnerable save fold never reads Quantum Deflection",
     [(INV, "    save = _better(save, hypercrypt_quantum_deflection.invulnerable_save_for(squad))",
       "    pass" + MARK)], (HC,)),
    ("Quantum Deflection's save outlives the phase",
     [(QD, "            squad.quantum_deflection_active = False", "            pass" + MARK)], (HC,)),
    ("the AI buys Quantum Deflection whatever the AP",
     [(QD, "            if worth_for_ai(attacker, target, melee):", "            if True:" + MARK)], (HC,)),
    ("Quantum Deflection leaves the fight reaction tuple",
     [(MAIN, lines("        repair_barge_controller, quantum_deflection_controller,", "    )"),
       lines("        repair_barge_controller," + MARK, "    )"))], (HC,)),
    ("Entropic Damping joins the fight reaction tuple",
     [(MAIN, lines("        repair_barge_controller, quantum_deflection_controller,", "    )"),
       lines("        repair_barge_controller, quantum_deflection_controller, entropic_damping_controller," + MARK,
             "    )"))], (HC,)),

    # -------------------------------------------------------- Entropic Damping
    ("Entropic Damping flags the TARGET instead of the attacker",
     [(ED, "        attacker.entropic_damping_hazardous = True",
       "        [setattr(t, 'entropic_damping_hazardous', True) for t in targets or ()]" + MARK)], (HC,)),
    ("Entropic Damping mutates the model's own weapon",
     [(ED, "    granted = copy.copy(weapon)", "    granted = weapon" + MARK)], (HC,)),
    ("Entropic Damping forgets its 18\"",
     [(ED, lines("        if attacker.min_distance_to(target) > ENTROPIC_DAMPING_RANGE_IN:", "            return False"),
       "        pass" + MARK)], (HC,)),
    ("Entropic Damping is offered in melee",
     [(ED, lines("        if melee:", '            return False               # "your opponent\'s SHOOTING phase"'),
       "        pass" + MARK)], (HC,)),
    ("Entropic Damping is offered for a model that is no TITANIC",
     [(ED, lines("        if not titanic.is_titanic_unit(target):", "            return False"),
       "        pass" + MARK)], (HC,)),
    ("shooting's weapon chain never reads Entropic Damping",
     [(SH, "        weapon = hypercrypt_entropic_damping.adjusted_weapon(weapon, self.active_squad)",
       "        pass" + MARK)], (HC,)),

    # ------------------------------------------------------ Reanimation Crypts
    ("Reanimation Crypts is offered in the opponent's Command phase",
     [(RC, "        if tt.phase != PHASE_COMMAND or tt.turn_owner != squad.owner:",
       "        if tt.phase != PHASE_COMMAND:" + MARK)], (HC,)),
    ("Reanimation Crypts is offered with nothing in Reserves to recover",
     [(RC, lines("        if not recovering_units(self.game_state, squad.owner):", "            return False"),
       "        pass" + MARK)], (HC, UI)),
    # NOT against the UI suite: after a purchase rule 15.01's ledger already
    # takes the button away, so the panel cannot see is_busy at all (measured:
    # no bite there). The Hypercrypt suite's phase-gate check is the reader.
    ("Reanimation Crypts is never busy while its dice are out",
     [(RC, "        return self._current is not None or bool(self._queue)", "        return False" + MARK)],
     (HC,)),
    ("Reanimation Crypts rolls for the first unit only",
     [(RC, lines("        self._apply(squad, rolled)", "        self._roll_next()", "        return True"),
       lines("        self._apply(squad, rolled)" + MARK, "        return True"))], (HC,)),
    ("Reanimation Crypts bypasses the one door into reanimate()",
     [(RC, "        wounds, spent, revived = reanimation_protocols.activate(",
       "        wounds, spent, revived = (lambda *a, **k: (0, 0, []))(" + MARK)], (HC, UI)),
    ("main.py never acknowledges Reanimation Crypts' dice",
     [(MAIN, "        reanimation_crypts_controller.on_dice_acknowledged()",
       "        if False: reanimation_crypts_controller.on_dice_acknowledged()" + MARK)], (HC, WIRING)),
    # NOT against test_event_chain_wiring.py: its section 10 guards gate ->
    # resolvable, never resolvable -> gate, so a term dropped from the gate is
    # invisible to it (measured: no bite there).
    ("the phase gate forgets Reanimation Crypts",
     [(MAIN, "            or reanimation_crypts_controller.is_busy", "            or False" + MARK)], (HC,)),

    # -------------------------------------------------------- Cosmic Precision
    ("Cosmic Precision moves to the unit screen",
     [(CP, "    PANEL_SCREEN = ARRIVAL_SCREEN", "    PANEL_SCREEN = None" + MARK)], (UI,)),
    ("the Set Up screen never draws arrival buttons",
     [(AP, "squad, screen=ARRIVAL_SCREEN):", 'squad, screen="nowhere"):' + MARK)], (UI,)),
    ("the dispatch never hands the registry to the Set Up screen",
     [(AP, lines("                                return_placement_controller=return_placement_controller,",
                 "                                proactive_stratagems=proactive_stratagems)"),
       "                                return_placement_controller=return_placement_controller)" + MARK)],
     (UI, HC)),
    ("the Shortened Blade's 'is active' line is drawn beside Cosmic Precision's note",
     [(AP, "              and not arrival_notes):", "              and True):" + MARK)], (UI,)),
    ("Cosmic Precision is offered before the unit arrives",
     [(CP, "        if require_arriving and not ic.is_ingressing(squad):", "        if False:" + MARK)], (HC,)),
    ("Cosmic Precision is offered to a MONSTER",
     [(CP, lines("        if is_monster_unit(squad):", "            return False"), "        pass" + MARK)], (HC, UI)),
    ("Cosmic Precision is offered through the Eternity Gate",
     [(CP, lines("        if ic.eternity_gate_squad is squad:",
                 "            return False     # the gate's rule is asked first and would win"),
       "        pass" + MARK)], (HC, UI)),
    ("Cosmic Precision is offered in the opponent's Movement phase",
     [(CP, "        if tt.phase != PHASE_MOVEMENT or tt.turn_owner != squad.owner:",
       "        if tt.phase != PHASE_MOVEMENT:" + MARK)], (HC, UI)),
    ("Cosmic Precision forgets its RESTRICTIONS",
     [(CP, "        squad.charge_locked_until_end_of_turn = True", "        pass" + MARK)], (HC, UI)),
    ("Cosmic Precision arms no relaxed arrival",
     [(CP, "        self.ingress_controller.relaxed_arrival_squad = squad", "        pass" + MARK)], (HC, UI)),

    # ---------------------------------------------------- Dimensional Corridor
    ("Dimensional Corridor lifts the SHARED lock too",
     [(DC, lines("            squad.eternity_gate_charge_locked = False", "            if self.game_log is not None:"),
       lines("            squad.eternity_gate_charge_locked = False",
             "            squad.charge_locked_until_end_of_turn = False" + MARK,
             "            if self.game_log is not None:"))], (HC,)),
    ("Dimensional Corridor's question leaves the lock lifted",
     [(DC, lines("        finally:", "            squad.eternity_gate_charge_locked = before"),
       lines("        finally:", "            pass" + MARK))], (HC, UI)),
    ("Dimensional Corridor is offered without an arrival through the gate",
     [(DC, '        if squad not in getattr(ic, "gate_arrivals_this_turn", ()):', "        if False:" + MARK)],
     (HC, UI)),
    ("Dimensional Corridor's Monolith need not have started on the battlefield",
     [(DC, lines('        if not getattr(squad, "eternity_gate_bearer_started_on_board", False):',
                 "            return False"), "        pass" + MARK)], (HC,)),
    ("Dimensional Corridor is offered when lifting the lock buys nothing",
     [(DC, lines("        if not self.eligible_once_lifted(squad):", "            return False"),
       "        pass" + MARK)], (HC, UI)),
    ("Dimensional Corridor is offered in the opponent's Charge phase",
     [(DC, "        if tt.phase != PHASE_CHARGE or tt.turn_owner != squad.owner:",
       "        if tt.phase != PHASE_CHARGE:" + MARK)], (HC,)),

    # ------------------------------------------------------ Hyperphasic Recall
    ("'wholly within 6\"' read as plain 'within'",
     [(HR, "    return gap + radius_in - monolith_model.radius_in <= HYPERPHASIC_RECALL_RANGE_IN + _EPSILON",
       "    return gap - radius_in - monolith_model.radius_in <= HYPERPHASIC_RECALL_RANGE_IN + _EPSILON" + MARK)],
     (HC,)),
    ("the set-up does not wait for the death sweep",
     [(HR, lines('            if any(m.is_dead() for m in getattr(squad, "models", ()) or ()):',
                 "                return False        # the sweep has not taken the corpses yet"),
       "            pass" + MARK)], (HC,)),
    ("Hyperphasic Recall is offered in YOUR Shooting phase",
     [(HR, "        return tt.phase == PHASE_SHOOTING and tt.turn_owner == attacker.owner",
       "        return tt.phase == PHASE_SHOOTING" + MARK)], (HC,)),
    ("the Recall validator ignores Engagement Range",
     [(HR, lines("                        <= ENGAGEMENT_RANGE_IN):", "                    return False"),
       lines("                        <= ENGAGEMENT_RANGE_IN):", "                    pass" + MARK))], (HC,)),
    # The offer's own "no Monolith" early-out was measured redundant and removed
    # (monoliths_with_room reads monoliths_for). What really decides it is the
    # MONOLITH keyword question, so that is what this probe takes away.
    ("Hyperphasic Recall is offered with no MONOLITH on the battlefield",
     [(HR, "            if attached_units.model_has_datasheet_keyword(squad, m, MONOLITH_KEYWORD)]",
       "            if True]" + MARK)], (HC,)),
    ("a cancelled Recall leaves the unit off the battlefield",
     [(HR, lines("            if model not in tokens:", "                tokens.append(model)"),
       lines("            if False:" + MARK, "                tokens.append(model)"))], (HC,)),
    ("Hyperphasic Recall asks about the same attack twice",
     [(HR, lines("            if key in self._asked:", "                continue"), "            pass" + MARK)], (HC,)),
    ("main.py never resolves the deferred Recall set-up",
     [(MAIN, "        hyperphasic_recall_controller.resolve_deferred()",
       "        if False: hyperphasic_recall_controller.resolve_deferred()" + MARK)], (HC,)),
    ("main.py's fight hook hands Hyperphasic Recall the SHOOTING ledger",
     [(MAIN, "                _fighter, fight_controller.models_lost_this_activation)",
       "                _fighter, shooting_controller.models_lost_this_activation)" + MARK)], (HC,)),

    # -------------------------------------------------------------------- AI
    ("the AI's Hyperphasing ignores round 3's destruction and the arrival floor",
     [(AG, lines("    if (hypercrypt_hyperphasing.withdrawal_is_doomed(turn_tracker)",
                 "            or hypercrypt_hyperphasing.misses_next_arrival(turn_tracker)):",
                 "        return []"), "    pass" + MARK)], (HC,)),
    ("the AI pulls a garrison off its objective",
     [(AG, lines("        if held and is_within_range_of_objective(squad, held):", "            continue"),
       "        pass" + MARK)], (HC,)),
    ("the AI's Recall verdict always says yes",
     [(AG, "    return remaining > 0 and _expected_incoming_wounds(state, squad) >= remaining",
       "    return True" + MARK)], (HC,)),
    ("the AI buys Reanimation Crypts for a single wound",
     [(AG, "REANIMATION_CRYPTS_MIN_RECOVERABLE = 2", "REANIMATION_CRYPTS_MIN_RECOVERABLE = 1" + MARK)], (HC,)),
    ("the AI spends 2CP of Dimensional Corridor on a shooting unit",
     [(AG, lines("    if _shooting_specialist_charge_block(squad) is not None:", "        return None",
                 "    gaps = "),
       lines("    pass" + MARK, "    gaps = "))], (HC,)),
    ("the AI buys Cosmic Precision for a tie-break",
     [(AG, "    return tuple(relaxed_score[:2]) < tuple(plain_score[:2])",
       "    return tuple(relaxed_score) < tuple(plain_score)" + MARK)], (HC,)),
    ("the AI never asks Dimensional Corridor in its Charge phase",
     [(AG, lines("        acted = _handle_dimensional_corridor(player, all_tokens, dimensional_corridor_controller,",
                 "                                             game_log=game_log)"),
       "        acted = False" + MARK)], (HC,)),

    # --------------------------------------------------------------- main.py
    ("Hyperphasing is built without the AI's policy",
     [(MAIN, "        choose=lambda eligible, cap: hyperphasing_choice(state, turn_tracker, eligible, cap))",
       "        choose=None)" + MARK)], (HC,)),
    ("main.py never offers Hyperphasing",
     [(MAIN, lines("            hyperphasing_controller.offer_at_end_of_turn(",
                   "                {t.squad for t in state.tokens if t.squad is not None}, ending_player)"),
       lines("            False and hyperphasing_controller.offer_at_end_of_turn(" + MARK,
             "                {t.squad for t in state.tokens if t.squad is not None}, ending_player)"))], (HC,)),
    ("Cosmic Precision is built but never put on the registry",
     [(MAIN, "    cosmic_precision_controller = proactive_stratagems.add(CosmicPrecisionController(",
       "    cosmic_precision_controller = (CosmicPrecisionController(" + MARK)], (HC, UI)),
    ("Reanimation Crypts is never handed the shared boost",
     [(MAIN, "    reanimation_crypts_controller.boost = reanimation_boost",
       "    reanimation_crypts_controller.boost = None" + MARK)], (HC,)),
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
