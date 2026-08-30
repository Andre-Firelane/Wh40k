"""The Death Lord's Chosen detachment rule: Deadly Vectors.

  "In your opponent's Command phase, roll 2D6 for each Afflicted enemy unit,
  subtracting 1 from the result if that unit is Below Half-strength. If the
  result is 6 or less, that enemy unit suffers D3 mortal wounds."

Etappe 2 of the Death Guard faction. Like Etappe 1's suite, the units here are
hand-built on a test-local profile - there is no Death Guard datasheet until
Etappe 3, and the rule does not need one.

Sections
  1. The detachment predicates
  2. The inverted threshold, and the Below-Half-strength modifier at its boundary
  3. "In your OPPONENT's Command phase" - both directions
  4. The queue, end to end through real dice
  5. Mortal wounds actually land, and the allocation is answerable
  6. Source guards on main.py
  7. A/B probes
"""
import inspect
import pathlib

from testkit import Checks, DecisionManager, GameState, Log, TurnTracker, script

from game import config, deadly_vectors, death_lords_chosen, nurgles_gift
from game.deadly_vectors import DeadlyVectorsController
from game.dice import DiceManager
from game.nurgles_gift import NurglesGiftController
from game.plagues import PlagueChoice
from game.squad import Squad, is_below_half_strength
from game.token import Token
from game.units import UnitProfile

c = Checks("Deadly Vectors (Death Lord's Chosen)")

DG = "Player 2"
FOE = "Player 1"


class PlagueMarineStandIn(UnitProfile):
    name = "Plague Marine Stand-in"
    nurgles_gift = True
    toughness = 6
    wounds = 2
    armor_save = "3+"
    base_radius_in = 0.63


class VictimProfile(UnitProfile):
    name = "Victim"
    toughness = 4
    wounds = 1
    armor_save = "6+"
    base_radius_in = 0.63


def squad_at(profile, owner, name, positions):
    models = [Token(x, y, profile.base_radius_in, (200, 200, 200), profile=profile)
              for x, y in positions]
    squad = Squad(name, models, owner=owner)
    for model in models:
        model.squad = squad
    return squad


class detachment_on:
    """config.DEATH_LORDS_CHOSEN_PLAYERS is a real global; restore it always."""

    def __init__(self, *players):
        self.players = players

    def __enter__(self):
        self._old = config.DEATH_LORDS_CHOSEN_PLAYERS
        config.DEATH_LORDS_CHOSEN_PLAYERS = tuple(self.players)
        return self

    def __exit__(self, *exc):
        config.DEATH_LORDS_CHOSEN_PLAYERS = self._old
        return False


def scene(victim_models=4, victim_alive=None, dg_at=(10.0, 10.0), foe_at=(14.0, 10.0)):
    """A Death Guard unit projecting its aura onto an enemy unit, with a real
    DiceManager and a refreshed Afflicted flag."""
    state = GameState()
    dg = squad_at(PlagueMarineStandIn, DG, "2 Plague Marines 1", [dg_at])
    foe = squad_at(VictimProfile, FOE, "1 Victim 1",
                   [(foe_at[0] + i * 1.4, foe_at[1]) for i in range(victim_models)])
    if victim_alive is not None:
        for model in foe.models[victim_alive:]:
            model.current_wounds = 0
        foe.models = foe.models[:victim_alive]   # as remove_dead_models() would leave it
    for squad in (dg, foe):
        for model in squad.models:
            state.add_token(model)
    tracker = TurnTracker()
    tracker.battle_round = 1
    NurglesGiftController(turn_tracker=tracker, plague_choice=PlagueChoice()).refresh(state.tokens)
    dice, log = DiceManager(), Log()
    ctrl = DeadlyVectorsController(dice_manager=dice, game_log=log, game_state=state)
    return {"state": state, "dg": dg, "foe": foe, "dice": dice, "log": log,
            "ctrl": ctrl, "turn": tracker,
            "squads": {t.squad for t in state.tokens if t.squad is not None}}


# --- 1. The detachment predicates -------------------------------------------
print("--- 1. Predicates ---")

s = scene()
with detachment_on(DG):
    c.true("the Death Guard player has the detachment", death_lords_chosen.has_detachment(DG))
    c.true("the opponent does not", not death_lords_chosen.has_detachment(FOE))
    c.eq("detachment_players() lists it", death_lords_chosen.detachment_players(), [DG])
    c.true("a Death Guard unit passes the shared TARGET line",
           death_lords_chosen.stratagem_target_ok(s["dg"]))
    c.true("...but only for its own player",
           not death_lords_chosen.stratagem_target_ok(s["dg"], player=FOE))
    c.true("an enemy unit never does",
           not death_lords_chosen.stratagem_target_ok(s["foe"]))
with detachment_on():
    c.true("with the detachment unset, nothing targets",
           not death_lords_chosen.stratagem_target_ok(s["dg"]))
    c.eq("...and no player holds it", death_lords_chosen.detachment_players(), [])

c.true("is_death_guard_unit() recognises a hand-built carrier by its army rule",
       death_lords_chosen.is_death_guard_unit(s["dg"]))
c.true("...and not the enemy", not death_lords_chosen.is_death_guard_unit(s["foe"]))
# The fallback is only for a squad with NO datasheet - a real datasheet must
# win, or a future non-Death-Guard unit carrying the flag would be mislabelled.
s["dg"].datasheet = type("Sheet", (), {"keywords": ("INFANTRY",), "faction": None})()
c.true("a squad WITH a datasheet is judged on its faction, not on the fallback",
       not death_lords_chosen.is_death_guard_unit(s["dg"]))
s["dg"].datasheet = None

# Signal Pox's keyword is deliberately unreachable for this roster.
c.true("no hand-built unit is a LORD OF VIRULENCE",
       not death_lords_chosen.is_lord_of_virulence_unit(s["dg"]))
c.true("nor a TERMINATOR without the datasheet keyword",
       not death_lords_chosen.is_terminator_unit(s["dg"]))
s["dg"].datasheet = type("Sheet", (), {"keywords": ("INFANTRY", "TERMINATOR"), "faction": None})()
c.true("the TERMINATOR test reads the DATASHEET keyword",
       death_lords_chosen.is_terminator_unit(s["dg"]))
s["dg"].datasheet = None


# --- 2. The inverted threshold and the modifier ------------------------------
print("--- 2. Threshold and modifier ---")

full = scene(victim_models=4, victim_alive=4)
c.true("a full-strength unit is not Below Half-strength",
       not is_below_half_strength(full["foe"]))
c.eq("...so no penalty", deadly_vectors.result_penalty(full["foe"])[0], 0)

# "Below Half-strength" is STRICTLY less than half - the Appendix term, NOT
# is_at_half_strength()'s at-or-below. 2 of 4 is exactly half, so it does NOT
# qualify; 1 of 4 does. That boundary is the only place the two definitions
# differ, which is why it is measured here and nowhere else.
half = scene(victim_models=4, victim_alive=2)
below = scene(victim_models=4, victim_alive=1)
c.true("exactly half is NOT Below Half-strength", not is_below_half_strength(half["foe"]))
c.eq("...so still no penalty", deadly_vectors.result_penalty(half["foe"])[0], 0)
c.true("one of four IS Below Half-strength", is_below_half_strength(below["foe"]))
c.eq("...and takes the -1", deadly_vectors.result_penalty(below["foe"])[0], 1)
c.eq("the penalty names its reason for the log",
     deadly_vectors.result_penalty(below["foe"])[1], "Below Half-strength")

# "If the result is 6 or less" - an INVERTED threshold. Low rolls hurt.
c.eq("the threshold is 6 or less", deadly_vectors.DEADLY_VECTORS_MAX_RESULT, 6)
c.true("a 6 triggers", deadly_vectors.triggers(6, full["foe"]))
c.true("a 7 does not", not deadly_vectors.triggers(7, full["foe"]))
c.true("a 2 triggers - LOW is dangerous here, not high",
       deadly_vectors.triggers(2, full["foe"]))
# The -1 makes a weakened unit EASIER to hurt, not harder.
c.true("a 7 DOES trigger against a Below-Half-strength unit (7-1=6)",
       deadly_vectors.triggers(7, below["foe"]))
c.true("...but an 8 still does not (8-1=7)", not deadly_vectors.triggers(8, below["foe"]))
c.true("the modifier makes a weakened unit MORE vulnerable, not less",
       deadly_vectors.triggers(7, below["foe"]) and not deadly_vectors.triggers(7, full["foe"]))


# --- 3. "In your OPPONENT's Command phase" -----------------------------------
print("--- 3. Whose Command phase ---")

with detachment_on(DG):
    own = scene()
    c.true("nothing happens in the Death Guard player's OWN Command phase",
           not own["ctrl"].begin_opponent_command_phase(own["squads"], phase_owner=DG))
    c.true("...and the controller stays idle", not own["ctrl"].is_busy)

    opp = scene()
    script(4, 1)
    c.true("it fires in the OPPONENT's Command phase",
           opp["ctrl"].begin_opponent_command_phase(opp["squads"], phase_owner=FOE))
    c.true("...and it rolled for the Afflicted enemy unit",
           "Deadly Vectors" in (opp["dice"].label or ""))
    c.eq("2D6", len(opp["dice"].last_values or []), 2)
    c.true("the threshold rides in the LABEL, since success_threshold would colour it backwards",
           "6 or less" in (opp["dice"].label or ""))
    c.eq("...and success_threshold is deliberately unset", opp["dice"].success_threshold, None)
    c.eq("the dice panel names the unit as Afflicted, not as a Target",
         opp["dice"].subject_label, "Afflicted")

    # Only AFFLICTED units are rolled for.
    far = scene(foe_at=(60.0, 60.0))
    c.true("the enemy unit out of Contagion Range is not Afflicted",
           not nurgles_gift.is_afflicted(far["foe"]))
    c.true("...so nothing is rolled for it",
           not far["ctrl"].begin_opponent_command_phase(far["squads"], phase_owner=FOE))

with detachment_on():
    none = scene()
    c.true("without the detachment nobody rolls at all",
           not none["ctrl"].begin_opponent_command_phase(none["squads"], phase_owner=FOE))

# targets_for() is relative to the DEATH GUARD player, which is what makes a
# mirror match resolve each side against the other rather than against itself.
tgt = scene()
c.eq("targets_for() finds the enemy unit",
     [s.name for s in tgt["ctrl"].targets_for(tgt["squads"], DG)], ["1 Victim 1"])
c.eq("...and from the other side, the Death Guard unit instead",
     [s.name for s in tgt["ctrl"].targets_for(tgt["squads"], FOE)], [])


# --- 4. The queue, end to end -----------------------------------------------
print("--- 4. The queue ---")


def run(ctrl, dice, limit=40):
    for _ in range(limit):
        if not dice.pending_values:
            break
        dice.acknowledge()
        ctrl.on_dice_acknowledged()


with detachment_on(DG):
    # 2D6 = 6 -> triggers; D3 = 2 -> two mortal wounds. ONE model, so the
    # allocation has nothing to pause on and the queue can be seen to drain -
    # the multi-model case (which DOES pause, correctly) is section 5's.
    hit = scene(victim_models=1)
    script(3, 3, 2, *([6] * 20))
    hit["ctrl"].begin_opponent_command_phase(hit["squads"], phase_owner=FOE)
    run(hit["ctrl"], hit["dice"])
    c.true("a total of 6 triggers the rule",
           "Deadly Vectors: 1 Victim 1 rolled 6" in hit["log"].find("rolled 6"))
    c.true("...and mortal wounds are announced",
           "suffers 2 mortal wound(s)" in hit["log"].find("mortal wound(s)"))
    c.true("the queue finished", not hit["ctrl"].is_busy)

    miss = scene(victim_models=4)
    script(6, 6, *([6] * 20))
    miss["ctrl"].begin_opponent_command_phase(miss["squads"], phase_owner=FOE)
    run(miss["ctrl"], miss["dice"])
    c.true("a total of 12 does nothing", "no effect" in miss["log"].find("no effect"))
    c.eq("...and no model was hurt",
         [m.current_wounds for m in miss["foe"].models], [1, 1, 1, 1])
    c.true("the queue finished", not miss["ctrl"].is_busy)

    # A second Afflicted enemy unit gets its own labelled roll - it is a QUEUE.
    two = scene(victim_models=1)
    # Round 1 reaches only 3", so the second victim has to sit inside that -
    # at (16, 12) it was 5.06" away and simply not Afflicted.
    second = squad_at(VictimProfile, FOE, "1 Victim 2", [(12.0, 12.5)])
    for model in second.models:
        two["state"].add_token(model)
    NurglesGiftController(turn_tracker=two["turn"],
                          plague_choice=PlagueChoice()).refresh(two["state"].tokens)
    squads = {t.squad for t in two["state"].tokens if t.squad is not None}
    script(6, 6, 6, 6, *([6] * 20))   # both miss, so the queue is the only thing under test
    two["ctrl"].begin_opponent_command_phase(squads, phase_owner=FOE)
    run(two["ctrl"], two["dice"])
    c.eq("both Afflicted units were rolled for",
         two["log"].lines.__str__().count("no effect"), 2)
    c.true("the queue drained", not two["ctrl"].is_busy)


# --- 5. Mortal wounds land ---------------------------------------------------
print("--- 5. Mortal wounds land ---")

with detachment_on(DG):
    # One model, so the allocation has no choice to pause on and resolves
    # straight through - the isolated case that proves the damage is real.
    solo = scene(victim_models=1)
    script(2, 2, 3, *([6] * 20))
    solo["ctrl"].begin_opponent_command_phase(solo["squads"], phase_owner=FOE)
    run(solo["ctrl"], solo["dice"])
    c.true("the single model was destroyed by 3 mortal wounds",
           solo["foe"].models[0].is_dead())
    c.true("the queue finished", not solo["ctrl"].is_busy)

    # A multi-model target pauses on the defender's choice. That is the COMMON
    # case here, so the controller has to expose it under the name main.py's
    # event chain keys on, or the queue would stall with nothing able to answer.
    multi = scene(victim_models=4)
    script(2, 2, 2, *([6] * 20))
    multi["ctrl"].begin_opponent_command_phase(multi["squads"], phase_owner=FOE)
    run(multi["ctrl"], multi["dice"])
    c.true("the allocation is waiting for the defender",
           multi["ctrl"].pending_damage_choice is not None)
    c.true("...and it is busy until answered", multi["ctrl"].is_busy)
    _choice = multi["ctrl"].pending_damage_choice or ()
    chosen = _choice[0] if _choice else None
    if chosen is not None:
        multi["ctrl"].choose_damage_model(chosen)
    c.true("the chosen model took a mortal wound", chosen is not None and chosen.is_dead())
    for _ in range(10):
        _next = multi["ctrl"].pending_damage_choice
        if not _next:
            break
        multi["ctrl"].choose_damage_model(_next[0])
    c.eq("two mortal wounds killed two of the four models",
         sum(1 for m in multi["foe"].models if m.is_dead()), 2)
    c.true("the queue finished once the allocation did", not multi["ctrl"].is_busy)

c.eq("pending_damage_choice is a property, spelled as main.py's chain expects",
     isinstance(inspect.getattr_static(DeadlyVectorsController, "pending_damage_choice"),
                property), True)
c.true("choose_damage_model exists under that exact name",
       callable(getattr(DeadlyVectorsController, "choose_damage_model", None)))
c.eq("the controller takes no agent - the rule is not optional and asks nothing",
     "agent" in inspect.signature(DeadlyVectorsController.__init__).parameters, False)
c.eq("...and no decision_manager either, for the same reason",
     "decision_manager" in inspect.signature(DeadlyVectorsController.__init__).parameters,
     False)


# --- 6. Source guards --------------------------------------------------------
print("--- 6. Wiring ---")

_main = pathlib.Path("main.py").read_text(encoding="utf-8")
for needle, label in [
    ("deadly_vectors_controller = DeadlyVectorsController(", "main.py builds the controller"),
    ("deadly_vectors_controller.begin_opponent_command_phase(", "main.py fires it at a Command phase"),
    ("deadly_vectors_controller.on_dice_acknowledged()", "main.py feeds it dice acknowledgements"),
    ("deadly_vectors_controller.is_busy", "main.py blocks the phase change while the queue drains"),
    ("deadly_vectors_controller.choose_damage_model(clicked)", "main.py routes the allocation click"),
    ("renderer.draw_damage_choice_highlight(board_surface, board, deadly_vectors_controller.pending_damage_choice)",
     "main.py highlights the models the defender may pick"),
]:
    c.true(label, needle in _main)

# It has to fire at the START of a Command phase, not the end: Reanimation
# Protocols drains its own dice queue at the END of the same phase, and two
# queues on one seam would fight over DiceManager.pending_values.
_dv_at = _main.find("deadly_vectors_controller.begin_opponent_command_phase(")
_reanim_at = _main.find("reanimation_controller.begin_command_phase(")
c.true("it fires on the START-of-Command-phase seam, not the end-of-phase one",
       "if turn_tracker.phase == PHASE_COMMAND:" in _main
       and 0 <= _dv_at < _reanim_at)
c.true("it is handed turn_tracker.turn_owner, so 'your opponent' resolves itself",
       "turn_tracker.turn_owner,\n            )" in _main)

_dv = pathlib.Path("game/deadly_vectors.py").read_text(encoding="utf-8")
# Checked on the IMPORT line, not on the whole file: the module docstring names
# is_at_half_strength() precisely to say it is the wrong one, so a naive
# substring search over the source finds the word it is warning about.
_driver = pathlib.Path("ai/agent_driver.py").read_text(encoding="utf-8")
# The rule needs no AI HANDLER (it is not optional and asks nothing), but its
# mortal wounds land on the OPPONENT - so when the AI is the victim, its own
# allocation choice has to be answerable. _resolve_own_damage_choice() is the
# only thing that ever does that for Player 2's models; without the controller
# in that list, main.py's phase gate would hold on a choice nobody could
# answer. Same deadlock deadly_demise_controller was added there to prevent.
_driver_list = _driver[_driver.find("    controllers = ["):]
c.true("the AI can resolve its own Deadly Vectors allocation",
       "deadly_vectors_controller," in _driver_list[:_driver_list.find("]")])
c.true("main.py passes the controller to take_one_action()",
       "deadly_vectors_controller=deadly_vectors_controller," in _main)
c.eq("...and it is passed BY KEYWORD, since that call is positional up front",
     _main.count("deadly_vectors_controller=deadly_vectors_controller,"), 1)

_dv_imports = [line for line in _dv.splitlines() if line.startswith("from game.squad import")]
c.eq("the module imports is_below_half_strength and not is_at_half_strength",
     _dv_imports, ["from game.squad import is_below_half_strength"])


# --- 7. A/B probes -----------------------------------------------------------
print("--- 7. A/B probes ---")

_real = deadly_vectors.result_penalty
try:
    deadly_vectors.result_penalty = lambda squad: (0, None)
    c.eq("A/B: with no Below-Half-strength modifier a 7 stops triggering",
         deadly_vectors.triggers(7, below["foe"]), False)
finally:
    deadly_vectors.result_penalty = _real
c.eq("A/B restored", deadly_vectors.triggers(7, below["foe"]), True)

# The at-or-below misreading: it would fire the rule one model too early.
from game.squad import is_at_half_strength                 # noqa: E402
c.true("A/B: is_at_half_strength() would WRONGLY penalise a unit at exactly half",
       is_at_half_strength(half["foe"]) and not is_below_half_strength(half["foe"]))

c.finish()
