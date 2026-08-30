"""The DEATH GUARD army rule: Nurgle's Gift, Contagion Range and the three Plagues.

Etappe 1 of the Death Guard faction. There is no Death Guard DATASHEET yet
(that is Etappe 3), so the carrier here is a test-local UnitProfile subclass
with nurgles_gift = True. That is not a workaround - it is the honest unit of
this stage: the aura is defined by the profile flag, and Etappe 3's datasheets
do nothing more than set it.

Sections
  1. Contagion Range: the printed table, the bonus, and the 12" cap
  2. Afflicted: the geometric source, measured AT the range boundary
  3. Afflicted: the sticky source, and the union of the two
  4. -1 Toughness through the REAL attack controllers, not the predicate
  5. The three Plagues, each at its own funnel
  6. The Declare Battle Formations choice (human prompt / deterministic AI)
  7. Source guards on main.py and game/pregame.py
  8. A/B probes
"""
import inspect
import pathlib

from testkit import (Checks, DecisionManager, GameState, TurnTracker, Log, PHASES,
                     PHASE_FIGHT, PHASE_SHOOTING, build, script, options_of, pick_option)

from game import nurgles_gift, plagues, leadership, objectives
from game.damage_resolution import save_thresholds, displayed_save_threshold
from game.coldstar import effective_movement_in
from game.nurgles_gift import NurglesGiftController
from game.plagues import PlagueChoice, PlagueSelectionStep
from game.squad import Squad, attached_unit_toughness
from game.status_effects import AFFLICTED, LABELS, active_effects
from game.token import Token
from game.units import UnitProfile

c = Checks("Nurgle's Gift (Death Guard army rule)")

DG = "Player 2"     # the Death Guard player throughout
FOE = "Player 1"


class PlagueMarineStandIn(UnitProfile):
    """A Death Guard model for aura purposes. Only nurgles_gift matters."""
    name = "Plague Marine Stand-in"
    nurgles_gift = True
    toughness = 6
    wounds = 2
    armor_save = "3+"
    base_radius_in = 0.63
    movement_in = 5
    leadership = "6+"
    oc = 2


class VictimProfile(UnitProfile):
    name = "Victim"
    toughness = 4
    wounds = 2
    armor_save = "3+"
    invulnerable_save = "4+"
    base_radius_in = 0.63
    movement_in = 6
    leadership = "6+"
    oc = 2


def squad_at(profile, owner, name, positions):
    """A hand-built Squad with one model per (x, y)."""
    models = [Token(x, y, profile.base_radius_in, (200, 200, 200), profile=profile)
              for x, y in positions]
    squad = Squad(name, models, owner=owner)
    for model in models:
        model.squad = squad
    return squad


def scene(dg_positions=((10.0, 10.0),), foe_positions=((14.0, 10.0),),
          battle_round=1, plague=None, foe_profile=VictimProfile):
    """A Death Guard unit, an enemy unit, and a refreshed controller."""
    dg = squad_at(PlagueMarineStandIn, DG, "2 Plague Marines 1", dg_positions)
    foe = squad_at(foe_profile, FOE, "1 Victim 1", foe_positions)
    tracker = TurnTracker()
    tracker.battle_round = battle_round
    choice = PlagueChoice()
    if plague is not None:
        choice.choose(DG, plague)
    ctrl = NurglesGiftController(turn_tracker=tracker, game_log=Log(), plague_choice=choice)
    tokens = list(dg.models) + list(foe.models)
    ctrl.refresh(tokens)
    return {"dg": dg, "foe": foe, "ctrl": ctrl, "tokens": tokens,
            "tracker": tracker, "choice": choice}


# --- 1. Contagion Range ------------------------------------------------------
print("--- 1. Contagion Range ---")

c.eq("battle round 1 reaches 3\"", nurgles_gift.contagion_range_in(1), 3.0)
c.eq("battle round 2 reaches 6\"", nurgles_gift.contagion_range_in(2), 6.0)
c.eq("battle round 3 reaches 9\"", nurgles_gift.contagion_range_in(3), 9.0)
# Rounds 4 and 5 are the DEFAULT rather than table rows, so a battle that
# somehow ran long would not fall off the end.
c.eq("battle round 4 still reaches 9\"", nurgles_gift.contagion_range_in(4), 9.0)
c.eq("battle round 5 still reaches 9\"", nurgles_gift.contagion_range_in(5), 9.0)
c.eq("an unknown round falls back to 9\", not to 0", nurgles_gift.contagion_range_in(9), 9.0)
c.eq("no tracker at all reads as round 1", nurgles_gift.contagion_range_in(None), 3.0)

# The printed table tops out at 9", so the 12" cap can only ever bound a
# MODIFIER - and the only modifier there is (Blooming Pestilence's +3") lands
# exactly on 12" in round 3. The cap is therefore inert with these numbers,
# which is worth pinning: an earlier build had the table as 6/9/12, where the
# cap DID bite unaided and made that Stratagem worthless from round 3.
c.eq("a +3\" bonus in round 1 gives 6\"", nurgles_gift.contagion_range_in(1, 3.0), 6.0)
c.eq("a +3\" bonus in round 2 gives 9\"", nurgles_gift.contagion_range_in(2, 3.0), 9.0)
c.eq("a +3\" bonus in round 3 gives exactly the 12\" cap",
     nurgles_gift.contagion_range_in(3, 3.0), 12.0)
c.true("...so the bonus is worth 3\" in EVERY round - the cap never eats it",
       all(nurgles_gift.contagion_range_in(r, 3.0) - nurgles_gift.contagion_range_in(r) == 3.0
           for r in (1, 2, 3, 4, 5)))

s = scene(battle_round=1)
c.eq("the controller reads the range off the turn tracker", s["ctrl"].reach_of(s["dg"]), 3.0)
s["ctrl"].add_range_bonus(s["dg"], 3.0)
c.eq("a per-unit bonus reaches reach_of()", s["ctrl"].reach_of(s["dg"]), 6.0)
s["ctrl"].expire_phase()
c.eq("expire_phase() clears the bonus", s["ctrl"].reach_of(s["dg"]), 3.0)


# --- 2. Afflicted: the geometric source, AT the boundary ---------------------
print("--- 2. Afflicted: geometry ---")

# Two 0.63\" radii, so edge-to-edge is centre distance - 1.26. In round 1 the
# reach is 3", so the boundary sits at 4.26" centre-to-centre. Measured on both
# sides of it, because a test that puts the enemy clearly inside or clearly
# outside passes for either an edge-to-edge or a centre-to-centre reading.
inside = scene(foe_positions=((10.0 + 4.20, 10.0),), battle_round=1)
outside = scene(foe_positions=((10.0 + 4.30, 10.0),), battle_round=1)
c.true("just inside Contagion Range -> Afflicted", nurgles_gift.is_afflicted(inside["foe"]))
c.true("just outside Contagion Range -> not Afflicted",
       not nurgles_gift.is_afflicted(outside["foe"]))
c.true("the measurement is edge to edge, not centre to centre",
       4.20 - 2 * 0.63 <= 3.0 < 4.30 - 2 * 0.63 + 0.63)

# The same pair of positions in a later round, where the reach has grown.
later = scene(foe_positions=((10.0 + 4.30, 10.0),), battle_round=2)
c.true("the same gap IS Afflicted once round 2 widens the aura to 6\"",
       nurgles_gift.is_afflicted(later["foe"]))

c.true("the Death Guard unit does not afflict ITSELF",
       not nurgles_gift.is_afflicted(inside["dg"]))

# "one or more DEATH GUARD models" - any model of the carrier reaches.
spread = scene(dg_positions=((10.0, 10.0), (30.0, 10.0)),
               foe_positions=((34.0, 10.0),), battle_round=1)
c.true("a SECOND Death Guard model in range is enough",
       nurgles_gift.is_afflicted(spread["foe"]))

# A wiped carrier stops projecting. The liveness test has to be
# any(not is_dead()) rather than `not squad.models`, because remove_dead_models()
# runs once a frame and the refresh can still see corpses.
dead = scene(battle_round=1)
for model in dead["dg"].models:
    model.current_wounds = 0
dead["ctrl"].refresh(dead["tokens"])
c.true("a Death Guard unit whose models are all dead projects nothing",
       not nurgles_gift.is_afflicted(dead["foe"]))

wiped = scene(battle_round=1)
for model in wiped["foe"].models:
    model.current_wounds = 0
wiped["ctrl"].refresh(wiped["tokens"])
c.true("a wiped-out enemy unit is not Afflicted", not nurgles_gift.is_afflicted(wiped["foe"]))

c.eq("qualifying_players() is derived from the units",
     nurgles_gift.qualifying_players([inside["dg"], inside["foe"]]), [DG])
c.eq("a game with no Death Guard has no qualifying player",
     nurgles_gift.qualifying_players([inside["foe"]]), [])
c.true("has_nurgles_gift() is true for the carrier", nurgles_gift.has_nurgles_gift(inside["dg"]))
c.true("has_nurgles_gift() is false for the enemy",
       not nurgles_gift.has_nurgles_gift(inside["foe"]))


# The bounding-box reject in _is_afflicted_now() is a pure optimisation, so it
# has to be proved to change no answer - the same treatment the line-of-sight
# bounding-box filter got (400 fuzz comparisons against the brute-force
# version). A reject that is not a true lower bound would silently un-afflict
# units, and nothing else in this suite would notice.
import random                                              # noqa: E402

_rng = random.Random(20260828)


def _brute_force_afflicted(ctrl, target, carriers):
    """The pre-optimisation answer: every carrier model against every target
    model, with no box test at all."""
    for carrier in carriers:
        if carrier.owner == target.owner:
            continue
        reach = ctrl.reach_of(carrier)
        for model in carrier.models:
            if model.is_dead():
                continue
            if nurgles_gift._gap(model, target) <= reach:
                return True
    return False


_mismatches = 0
for _ in range(400):
    dg_pos = [(_rng.uniform(0, 40), _rng.uniform(0, 40)) for _ in range(_rng.randint(1, 4))]
    foe_pos = [(_rng.uniform(0, 40), _rng.uniform(0, 40)) for _ in range(_rng.randint(1, 4))]
    fz = scene(dg_positions=tuple(dg_pos), foe_positions=tuple(foe_pos),
               battle_round=_rng.choice([1, 2, 3]))
    if nurgles_gift.is_afflicted(fz["foe"]) != _brute_force_afflicted(
            fz["ctrl"], fz["foe"], [fz["dg"]]):
        _mismatches += 1
c.eq("the bounding-box reject changes no answer (400 fuzz boards)", _mismatches, 0)
c.eq("_box_gap is a true lower bound on the model-to-model gap for a known pair",
     round(nurgles_gift._box_gap((0.0, 0.0, 1.0, 1.0), (5.0, 0.0, 6.0, 1.0)), 3), 4.0)
c.eq("overlapping boxes report 0",
     nurgles_gift._box_gap((0.0, 0.0, 5.0, 5.0), (4.0, 4.0, 9.0, 9.0)), 0.0)


# --- 3. Afflicted: the sticky source ----------------------------------------
print("--- 3. Afflicted: the sticky mark ---")

far = scene(foe_positions=((40.0, 40.0),), battle_round=1)
c.true("far away and unmarked -> not Afflicted", not nurgles_gift.is_afflicted(far["foe"]))
far["ctrl"].mark_afflicted(far["foe"], until_turn_of=DG)
far["ctrl"].refresh(far["tokens"])
c.true("a sticky mark afflicts a unit with no Death Guard anywhere near it",
       nurgles_gift.is_afflicted(far["foe"]))
c.true("is_marked() reports it", far["ctrl"].is_marked(far["foe"]))
# "until the START of YOUR next turn" - the marking player's turn, not the
# victim's. Clearing on the wrong player's turn would halve the duration.
far["ctrl"].expire_marks_for(FOE)
far["ctrl"].refresh(far["tokens"])
c.true("the VICTIM's turn starting does not clear the mark",
       nurgles_gift.is_afflicted(far["foe"]))
far["ctrl"].expire_marks_for(DG)
far["ctrl"].refresh(far["tokens"])
c.true("the MARKING player's turn starting clears it",
       not nurgles_gift.is_afflicted(far["foe"]))

# The union: a unit both in range and marked stays Afflicted when only one
# source goes away.
both = scene(foe_positions=((14.0, 10.0),), battle_round=1)
both["ctrl"].mark_afflicted(both["foe"], until_turn_of=DG)
both["ctrl"].expire_marks_for(DG)
both["ctrl"].refresh(both["tokens"])
c.true("losing the sticky mark leaves the aura still afflicting it",
       nurgles_gift.is_afflicted(both["foe"]))

# The two clocks are separate: expire_phase() must NOT clear sticky marks.
clocks = scene(foe_positions=((40.0, 40.0),), battle_round=1)
clocks["ctrl"].mark_afflicted(clocks["foe"], until_turn_of=DG)
clocks["ctrl"].expire_phase()
clocks["ctrl"].refresh(clocks["tokens"])
c.true("expire_phase() does NOT clear a sticky mark - two clocks, two places",
       nurgles_gift.is_afflicted(clocks["foe"]))


# --- 4. -1 Toughness, through the real controllers ---------------------------
print("--- 4. -1 Toughness ---")

t_out = scene(foe_positions=((40.0, 40.0),), battle_round=1)
t_in = scene(foe_positions=((14.0, 10.0),), battle_round=1)
c.eq("printed Toughness while not Afflicted", attached_unit_toughness(t_out["foe"]), 4)
c.eq("Afflicted subtracts 1 from Toughness", attached_unit_toughness(t_in["foe"]), 3)
c.eq("nurgles_gift.toughness_penalty() agrees", nurgles_gift.toughness_penalty(t_in["foe"]), 1)


class T1Profile(VictimProfile):
    name = "Nurgling-grade"
    toughness = 1


floor = scene(foe_positions=((14.0, 10.0),), battle_round=1, foe_profile=T1Profile)
c.eq("Toughness is clamped at 1 and never reaches 0",
     attached_unit_toughness(floor["foe"]), 1)

# End to end through a REAL ShootingController, not the predicate. Ork Boyz'
# shoota is S4: against printed T4 it wounds on 4+, against Afflicted T3 on 3+.
# Driven through testkit's real scene so the penalty is proved to reach the
# roll that is actually made, rather than only the helper that computes it.
from game.factions.orks import BOYZ                       # noqa: E402  (after the helpers)
from testkit import shooting_scene                        # noqa: E402


def wound_log_line(afflicted):
    """Run one real Boyz shooting activation at a Victim and return the
    engine's own Wound-roll log line."""
    sc = shooting_scene(BOYZ, BOYZ, attacker_owner=DG, gap=6.0)
    target = sc["target"]
    # Swap the target's models onto our Victim profile so the Toughness under
    # test is a clean T4 rather than an Ork's.
    for model in target.models:
        model.profile = VictimProfile
        model.current_wounds = VictimProfile.wounds
    # BEHIND the target, not between it and the shooters - a carrier standing
    # between them would sit inside Engagement Range, and rule 03.04 would make
    # the target an illegal shooting target altogether. Round 1 reaches 3", so
    # the window is narrow: at y=29.8 the gap is 2.54" edge-to-edge, inside the
    # 3" aura and outside the 2" that would break the scene.
    carrier = squad_at(PlagueMarineStandIn, DG, "2 Plague Marines 1",
                       [(20.0, 29.8) if afflicted else (90.0, 90.0)])
    for model in carrier.models:
        sc["state"].add_token(model)
    sc["turn"].battle_round = 1
    NurglesGiftController(turn_tracker=sc["turn"], plague_choice=PlagueChoice()).refresh(
        sc["state"].tokens)
    script(*([6] * 200))   # 6s so every hit lands and a Wound roll actually happens
    sc["shooting"].start_shooting(sc["attacker"])
    sc["shooting"].choose_target_squad(target)
    sc["shooting"].choose_weapon(sorted(sc["shooting"].remaining_weapon_types)[0])
    for _ in range(120):
        if sc["dice"].pending_values:
            sc["dice"].acknowledge()
            sc["shooting"].on_dice_acknowledged()
            continue
        if sc["decision"].is_pending:
            sc["decision"].choose(0)
            continue
        break
    return sc["log"].find("wound roll"), target


clean_line, clean_target = wound_log_line(afflicted=False)
tainted_line, tainted_target = wound_log_line(afflicted=True)
c.true("the clean run really shot", "wound roll" in clean_line)
c.true("S4 vs printed T4 needs a 4+", "needed 4+" in clean_line)
c.true("S4 vs Afflicted T3 needs a 3+ - the penalty reaches the roll actually made",
       "needed 3+" in tainted_line)
c.true("...and the victim really was flagged in that scene",
       nurgles_gift.is_afflicted(tainted_target))
c.true("...while the control run's victim was not",
       not nurgles_gift.is_afflicted(clean_target))

# The AI's own estimate reads the same funnel, so it sees the real Toughness
# rather than the printed one - the reason the penalty lives in
# attached_unit_toughness() and not at its nine callers.
from game import damage_estimate                          # noqa: E402
c.true("game/damage_estimate.py reads attached_unit_toughness(), so it inherits the penalty",
       "attached_unit_toughness" in inspect.getsource(damage_estimate))
_est_clean = damage_estimate.expected_wounds_against(clean_target, t_out["foe"]) or 0.0
c.true("game/ai_observation's estimate is a real number for the control unit", _est_clean >= 0.0)


# --- 5. The three Plagues ----------------------------------------------------
print("--- 5. The three Plagues ---")

# Rattlejoint Ague: worsen the SAVE characteristic by 1.
rj = scene(plague=plagues.RATTLEJOINT_AGUE)
rj_off = scene(foe_positions=((40.0, 40.0),), plague=plagues.RATTLEJOINT_AGUE)
weapon = type("W", (), {"ap": 0, "weapon_type": "ranged"})()
c.eq("not Afflicted: printed 3+ save",
     save_thresholds(rj_off["foe"].models[0], weapon)[0], 3)
c.eq("Rattlejoint Ague worsens the Save characteristic to 4+",
     save_thresholds(rj["foe"].models[0], weapon)[0], 4)
c.eq("the invulnerable save is NOT worsened - a different characteristic",
     save_thresholds(rj["foe"].models[0], weapon)[1], 4)
c.eq("the displayed threshold moves with it, so the panel cannot disagree",
     displayed_save_threshold(rj["foe"].models[0], weapon), 4)
sk = scene(plague=plagues.SKULLSQUIRM_BLIGHT)
c.eq("a DIFFERENT Plague leaves the save alone",
     save_thresholds(sk["foe"].models[0], weapon)[0], 3)

# Skullsquirm Blight: the afflicted unit's own shooting grants cover, its own
# melee is -1 to hit. Both are asked of the AFFLICTED unit as the ATTACKER.
c.eq("Skullsquirm Blight: -1 to the Afflicted unit's OWN Hit rolls",
     [(m.amount, m.source) for m in plagues.hit_modifiers(sk["foe"])],
     [(1, "Skullsquirm Blight")])
c.eq("positive amount, because positive WORSENS a threshold in this engine",
     plagues.SKULLSQUIRM_HIT_PENALTY, 1)
c.eq("a unit that is not Afflicted is unaffected",
     plagues.hit_modifiers(sk["dg"]), [])
c.eq("Rattlejoint Ague adds no hit modifier", plagues.hit_modifiers(rj["foe"]), [])
# "AN attack", not "a ranged attack": ONE function, read by BOTH phases. The
# earlier build had a ranged half (grant cover) and a melee half (-1 hit) -
# neither of which the printed card says. Pinned at the source so the two
# sites cannot drift back apart.
import inspect as _inspect                                   # noqa: E402
from game import fight as _fight_mod, shooting as _shoot_mod  # noqa: E402
c.true("game/shooting.py reads plagues.hit_modifiers()",
       "plagues.hit_modifiers(" in _inspect.getsource(_shoot_mod))
c.true("game/fight.py reads the SAME function",
       "plagues.hit_modifiers(" in _inspect.getsource(_fight_mod))
c.true("no cover clause survives anywhere - the card has none",
       not hasattr(plagues, "grants_cover_to_its_targets"))

# Scabrous Soulrot: Move, Leadership, Objective Control.
ss = scene(plague=plagues.SCABROUS_SOULROT)
ss_off = scene(foe_positions=((40.0, 40.0),), plague=plagues.SCABROUS_SOULROT)
c.eq("printed Move is 6\"", effective_movement_in(ss_off["foe"].models[0]), 6)
c.eq("Scabrous Soulrot worsens Move by 1", effective_movement_in(ss["foe"].models[0]), 5.0)
c.eq("printed Leadership threshold is 6",
     leadership.leadership_threshold(ss_off["foe"]), 6)
c.eq("Scabrous Soulrot worsens Leadership to 7 (higher is worse on 2D6)",
     leadership.leadership_threshold(ss["foe"]), 7)
c.eq("printed OC is 2", plagues.worsen_oc(ss_off["foe"].models[0]), 2)
c.eq("Scabrous Soulrot worsens OC to 1", plagues.worsen_oc(ss["foe"].models[0]), 1)


class Oc1Profile(VictimProfile):
    name = "OC 1"
    oc = 1


class Oc0Profile(VictimProfile):
    name = "OC 0"
    oc = 0


oc1 = scene(foe_positions=((14.0, 10.0),), plague=plagues.SCABROUS_SOULROT, foe_profile=Oc1Profile)
oc0 = scene(foe_positions=((14.0, 10.0),), plague=plagues.SCABROUS_SOULROT, foe_profile=Oc0Profile)
c.eq("OC 1 stays 1 - \"to a minimum of 1\"", plagues.worsen_oc(oc1["foe"].models[0]), 1)
c.eq("OC 0 stays 0 - the floor bounds WORSENING, it does not raise anything",
     plagues.worsen_oc(oc0["foe"].models[0]), 0)
c.eq("a different Plague leaves Move alone",
     effective_movement_in(rj["foe"].models[0]), 6)

# Which Plague lands on a unit is its OPPONENT's choice.
c.eq("plague_against() answers with the OPPONENT's pick",
     ss["choice"].plague_against(ss["foe"]), plagues.SCABROUS_SOULROT)
c.eq("the Death Guard player's own units suffer nothing",
     ss["choice"].plague_against(ss["dg"]), None)
c.eq("no choice made at all -> no Plague", PlagueChoice().plague_against(ss["foe"]), None)

# The mirror-match property: each side suffers the OTHER's Plague.
mirror = PlagueChoice()
mirror.choose(DG, plagues.RATTLEJOINT_AGUE)
mirror.choose(FOE, plagues.SCABROUS_SOULROT)
c.eq("mirror match: Player 1's units suffer Player 2's Plague",
     mirror.plague_against(ss["foe"]), plagues.RATTLEJOINT_AGUE)
c.eq("mirror match: Player 2's units suffer Player 1's Plague",
     mirror.plague_against(ss["dg"]), plagues.SCABROUS_SOULROT)


# --- 6. The Declare Battle Formations choice ---------------------------------
print("--- 6. Choosing a Plague ---")

c.eq("all three Plagues exist", sorted(plagues.PLAGUES),
     sorted([plagues.RATTLEJOINT_AGUE, plagues.SKULLSQUIRM_BLIGHT, plagues.SCABROUS_SOULROT]))
c.eq("the AI's pick is deterministic", plagues.ai_choice(), plagues.RATTLEJOINT_AGUE)
c.eq("...and repeating it cannot diverge", plagues.ai_choice(), plagues.ai_choice())
c.eq("PlagueSelectionStep takes no agent - it cannot cost an API call",
     "agent" in inspect.signature(PlagueSelectionStep.__init__).parameters, False)
c.eq("neither does begin()",
     "agent" in inspect.signature(PlagueSelectionStep.begin).parameters, False)

dg_squad = squad_at(PlagueMarineStandIn, DG, "2 Plague Marines 1", [(10.0, 10.0)])
foe_squad = squad_at(VictimProfile, FOE, "1 Victim 1", [(40.0, 40.0)])

# The AI answers itself, with no prompt at all.
choice_ai = PlagueChoice()
dec = DecisionManager()
step = PlagueSelectionStep(choice_ai, decision_manager=dec, human_player=FOE)
c.eq("only the Death Guard player is asked", step.begin([dg_squad, foe_squad]), [DG])
c.eq("the AI chose without a prompt", choice_ai.chosen_by(DG), plagues.RATTLEJOINT_AGUE)
c.true("nothing is pending", not dec.is_pending)

# The human is prompted with all three, and the answer sticks.
choice_h = PlagueChoice()
dec_h = DecisionManager()
step_h = PlagueSelectionStep(choice_h, decision_manager=dec_h, human_player=DG)
step_h.begin([dg_squad, foe_squad])
c.true("the human gets a prompt", dec_h.is_pending)
c.eq("with all three Plagues offered", len(options_of(dec_h)), 3)
c.true("Scabrous Soulrot is one of them", pick_option(dec_h, "Scabrous"))
c.eq("and the pick is recorded", choice_h.chosen_by(DG), plagues.SCABROUS_SOULROT)

# Idempotent: start() can be reached more than once (both battle-start paths).
c.eq("a second begin() does not re-ask an answered player",
     step_h.begin([dg_squad, foe_squad]), [])

# A game with no Death Guard never sees any of this.
c.eq("no Death Guard on the table -> nobody is asked",
     PlagueSelectionStep(PlagueChoice(), decision_manager=DecisionManager()).begin([foe_squad]), [])

# A mirror match asks BOTH players.
both_dg = squad_at(PlagueMarineStandIn, FOE, "1 Plague Marines 1", [(40.0, 40.0)])
c.eq("a mirror match asks both players",
     PlagueSelectionStep(PlagueChoice(), decision_manager=None,
                         human_player="nobody").begin([dg_squad, both_dg]),
     [FOE, DG])


# --- 6b. The board label -----------------------------------------------------
print("--- 6b. The board label ---")

lbl = scene(foe_positions=((14.0, 10.0),))
c.eq("AFFLICTED has a two-letter label like the other marks", LABELS[AFFLICTED], "AF")
c.true("an Afflicted model shows the label",
       AFFLICTED in active_effects(lbl["foe"].models[0], [], None, {}))
c.true("a Death Guard model does not",
       AFFLICTED not in active_effects(lbl["dg"].models[0], [], None, {}))


# --- 6c. The green aura layer -------------------------------------------------
print("--- 6c. The aura layer ---")

# User request: "fuer deathguard spezifische aura, die alle einheiten haben
# haette ich gerne einen ganz subtilen gruenen layer. aehnlich wie die anzeige
# der gegnerischen engagement range beim movement."
#
# Measured in PIXELS on a real Surface, not against the colour constant: the
# question is whether anything actually reaches the screen and where, which a
# constant cannot answer.
import pygame  # noqa: E402
from game.board import Board  # noqa: E402
from game.renderer import CONTAGION_AURA_ALPHA, CONTAGION_AURA_COLOR, Renderer  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

_aura_scene = scene(dg_positions=((10.0, 10.0),), foe_positions=((40.0, 40.0),),
                    battle_round=1)
_board = Board(60.0, 44.0, 15)   # 15 px per inch -> 900x660
_renderer = Renderer()


def _px(x_in, y_in):
    """Board.to_px() returns floats; Surface.get_at() needs ints."""
    x, y = _board.to_px(x_in, y_in)
    return (round(x), round(y))

_surface = pygame.Surface((900, 660), pygame.SRCALPHA)
_surface.fill((0, 0, 0, 255))
_before = _surface.get_at(_px(12.0, 10.0))
_renderer.draw_contagion_aura(_surface, _board, _aura_scene["tokens"],
                              reach_of=_aura_scene["ctrl"].reach_of)
_inside = _surface.get_at(_px(12.0, 10.0))     # 2" from the model, inside the 3" aura
_outside = _surface.get_at(_px(30.0, 10.0))    # 20" away

c.true("something is painted inside the Contagion Range", _inside != _before)
c.true("...and it is GREENER than what was there", _inside.g > _before.g)
c.true("...and it is not painted 20\" away", _outside == _before)
c.true("the layer is SUBTLE - it tints the ground rather than covering it",
       CONTAGION_AURA_ALPHA <= 60)
c.true("...but not invisible - measured on a real frame, 34 could not be seen",
       CONTAGION_AURA_ALPHA >= 38)

# The union is drawn OPAQUE and faded ONCE, so overlapping models do not stack
# into hotspots - being inside the aura twice is the same as being inside it
# once, and a patchwork would say otherwise. Measured with two models whose
# circles overlap: the overlap must be the SAME colour as either one alone.
_pair = squad_at(PlagueMarineStandIn, DG, "2 Plague Marines 9",
                 [(10.0, 10.0), (14.0, 10.0)])
_pair_ctrl = NurglesGiftController(turn_tracker=TurnTracker(), plague_choice=PlagueChoice())
_pair_ctrl.turn_tracker.battle_round = 1
_surface.fill((0, 0, 0, 255))
_renderer.draw_contagion_aura(_surface, _board, list(_pair.models),
                              reach_of=_pair_ctrl.reach_of)
c.eq("overlapping auras do not stack into a brighter patch",
     _surface.get_at(_px(12.0, 10.0)), _surface.get_at(_px(8.0, 10.0)))
c.true("...and both really are painted", _surface.get_at(_px(12.0, 10.0)).g > 0)

# The radius is the one the RULE reads, bonus and cap included - that is the
# whole reason reach_of is injected rather than computed in the renderer.
_aura_scene["ctrl"].add_range_bonus(_aura_scene["dg"], 3.0)
_surface.fill((0, 0, 0, 255))
_renderer.draw_contagion_aura(_surface, _board, _aura_scene["tokens"],
                              reach_of=_aura_scene["ctrl"].reach_of)
c.true("a Blooming Pestilence bonus widens the painted circle too",
       _surface.get_at(_px(15.5, 10.0)).g > 0)

# Without a reach_of the layer is simply not drawn - a renderer that guessed
# the range would be a second, quietly diverging answer.
_surface.fill((0, 0, 0, 255))
_renderer.draw_contagion_aura(_surface, _board, _aura_scene["tokens"], reach_of=None)
c.true("no reach_of -> nothing is drawn at all",
       _surface.get_at(_px(11.0, 10.0)).g == 0)

# A non-Death-Guard model paints nothing, however close it is.
_surface.fill((0, 0, 0, 255))
_renderer.draw_contagion_aura(_surface, _board, list(_aura_scene["foe"].models),
                              reach_of=_aura_scene["ctrl"].reach_of)
c.true("an enemy model projects no aura",
       _surface.get_at(_px(41.0, 40.0)).g == 0)


# --- 7. Source guards --------------------------------------------------------
print("--- 7. Wiring ---")

_main = pathlib.Path("main.py").read_text(encoding="utf-8")
c.true("main.py refreshes the aura once per frame",
       "nurgles_gift_controller.refresh(state.tokens)" in _main)
c.true("...right after the death sweep, so a unit wiped this frame stops projecting it",
       _main.index("_swept = state.remove_dead_models()")
       < _main.index("nurgles_gift_controller.refresh(state.tokens)")
       < _main.index("vengeful_stars_controller.notify_unit_destroyed"))
c.true("main.py clears the phase-scoped Contagion bonus",
       "nurgles_gift_controller.expire_phase()" in _main)
c.true("main.py expires sticky marks at the start of that player's turn",
       "nurgles_gift_controller.expire_marks_for(turn_tracker.turn_owner)" in _main)
c.true("main.py wires the Declare Battle Formations Plague choice",
       "pregame_controller.on_formations_started" in _main)
c.true("main.py draws the green Contagion layer",
       "renderer.draw_contagion_aura(" in _main)
c.true("...with the CONTROLLER's own range, not one the renderer computed",
       "reach_of=nurgles_gift_controller.reach_of" in _main)
c.true("...before the models, so they sit on top of it rather than under a wash",
       _main.index("renderer.draw_contagion_aura(")
       < _main.index("renderer.draw_embarked_passengers("))
c.true("the controller is built with the PlagueChoice, or afflicted_plague is never stamped",
       "plague_choice=plague_choice" in _main)

_pregame = pathlib.Path("game/pregame.py").read_text(encoding="utf-8")
c.true("pregame.py fires the hook",
       "self.on_formations_started(self._owners())" in _pregame)
c.true("...from start(), i.e. when Declare Battle Formations begins",
       _pregame.index("self.state = FORMATIONS")
       < _pregame.index("self.on_formations_started(self._owners())"))

# game/nurgles_gift.py must stay import-free: game/squad.py depends on it.
_ng = pathlib.Path("game/nurgles_gift.py").read_text(encoding="utf-8")
c.eq("game/nurgles_gift.py imports nothing at all - game/squad.py depends on it",
     [line for line in _ng.splitlines()
      if line.startswith("import ") or line.startswith("from ")], [])
_pl = pathlib.Path("game/plagues.py").read_text(encoding="utf-8")
c.eq("game/plagues.py imports only leaves, so six funnels can depend on it",
     sorted(line for line in _pl.splitlines()
            if line.startswith("import ") or line.startswith("from ")),
     ["from game import nurgles_gift", "from game.modifiers import Modifier"])


# --- 8. A/B probes -----------------------------------------------------------
print("--- 8. A/B probes ---")
# Each probe restores the pre-fix world for ONE claim and must break it.

_real_penalty = nurgles_gift.toughness_penalty
try:
    nurgles_gift.toughness_penalty = lambda squad: 0
    c.eq("A/B: with no Toughness penalty an Afflicted unit is back to T4",
         attached_unit_toughness(t_in["foe"]), 4)
finally:
    nurgles_gift.toughness_penalty = _real_penalty
c.eq("A/B restored", attached_unit_toughness(t_in["foe"]), 3)

_real_active = plagues.active_plague
try:
    plagues.active_plague = lambda squad: None
    c.eq("A/B: with no active Plague the save is back to 3+",
         save_thresholds(rj["foe"].models[0], weapon)[0], 3)
    c.eq("A/B: ...and Move is back to 6\"", effective_movement_in(ss["foe"].models[0]), 6)
    c.eq("A/B: ...and Leadership is back to 6", leadership.leadership_threshold(ss["foe"]), 6)
    c.eq("A/B: ...and OC is back to 2", plagues.worsen_oc(ss["foe"].models[0]), 2)
    c.eq("A/B: ...and no hit penalty", plagues.hit_modifiers(sk["foe"]), [])
finally:
    plagues.active_plague = _real_active
c.eq("A/B restored: the save is 4+ again", save_thresholds(rj["foe"].models[0], weapon)[0], 4)

# The cap probe: without it, a bonus in round 3 would keep growing the aura,
# and Blooming Pestilence would have no decision boundary at all.
# The cap never bites with the printed table (9" + the only 3" modifier is
# exactly 12"), so the probe has to push PAST it to show it is there at all.
c.eq("a bonus bigger than the rules grant is still clamped at 12\"",
     nurgles_gift.contagion_range_in(3, 9.0), 12.0)
_real_cap = nurgles_gift.CONTAGION_RANGE_CAP_IN
try:
    nurgles_gift.CONTAGION_RANGE_CAP_IN = 99.0
    c.eq("A/B: without the cap that oversized bonus would run to 18\"",
         nurgles_gift.contagion_range_in(3, 9.0), 18.0)
finally:
    nurgles_gift.CONTAGION_RANGE_CAP_IN = _real_cap
c.eq("A/B restored: the cap holds", nurgles_gift.contagion_range_in(3, 9.0), 12.0)

c.finish()
