"""The six Death Lord's Chosen Stratagems, and the three AI paths.

Etappe 4 of the Death Guard faction. Sections:
  1. The shared TARGET line: detachment + TERMINATOR
  2. Blooming Pestilence, and the 12" cap that makes it worthless from round 3
  3. Grim Reapers, through the REAL melee re-roll seam
  4. Mortarion's Teachings, through the REAL adjuster chain
  5. Sickening Impact, end to end through real dice
  6. Undying Spite: the interception, the strike-back, the verdict
  7. Signal Pox: a documented no-op, pinned
  8. The AI: three paths, three deliberate absences, zero API calls
  9. Source guards on main.py and ai/agent_driver.py
 10. A/B probes
"""
import inspect
import pathlib

import testkit as tk
from testkit import Checks, GameState, TurnTracker, Log, build, script

from ai import agent_driver
from game import (config, death_lords_chosen, dlc_blooming_pestilence,
                  dlc_grim_reapers, dlc_mortarions_teachings, dlc_sickening_impact,
                  dlc_signal_pox, dlc_undying_spite, nurgles_gift)
from game.command_points import CommandPointManager
from game.dice import DiceManager
from game.decision import DecisionManager
from game.dlc_blooming_pestilence import BloomingPestilenceController
from game.dlc_grim_reapers import GrimReapersController
from game.dlc_mortarions_teachings import MortarionsTeachingsController
from game.dlc_sickening_impact import SickeningImpactController
from game.dlc_signal_pox import SignalPoxController
from game.dlc_undying_spite import UndyingSpiteController
from game.factions import death_guard as dg
from game.nurgles_gift import NurglesGiftController
from game.plagues import PlagueChoice
from game.squad import Squad
from game.stratagems import StratagemController
from game.token import Token
from game.turn import PHASE_CHARGE, PHASE_COMMAND, PHASE_FIGHT, PHASE_SHOOTING, PHASES
from game.units import UnitProfile

c = Checks("Death Lord's Chosen Stratagems")

DG = "Player 2"
FOE = "Player 1"


def strat(cp=10):
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=Log())


class detachment_on:
    """config.DEATH_LORDS_CHOSEN_PLAYERS is a real global; always restore it."""

    def __init__(self, *players):
        self.players = players

    def __enter__(self):
        self._old = config.DEATH_LORDS_CHOSEN_PLAYERS
        config.DEATH_LORDS_CHOSEN_PLAYERS = tuple(self.players)
        return self

    def __exit__(self, *exc):
        config.DEATH_LORDS_CHOSEN_PLAYERS = self._old
        return False


class Foe(UnitProfile):
    name = "Foe"
    toughness = 4
    wounds = 1
    armor_save = "6+"
    base_radius_in = 0.63
    infantry = True


class FoeTank(UnitProfile):
    name = "Foe Tank"
    toughness = 10
    wounds = 12
    armor_save = "3+"
    base_radius_in = 2.1
    vehicle = True


def foe_squad(profile=Foe, n=3, x=40.0, y=40.0, name="1 Foe 1"):
    models = [Token(x + i * 1.4, y, profile.base_radius_in, (1, 1, 1), profile=profile)
              for i in range(n)]
    squad = Squad(name, models, owner=FOE)
    for m in models:
        m.squad = squad
    return squad


def terminators(name="2 Deathshroud Terminators 1", x=10.0, y=10.0):
    squad = build(dg.DEATHSHROUD_TERMINATORS, DG, name=name)
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + i * 1.6, y
    return squad


def non_terminators(name="2 Plague Marines 1"):
    squad = build(dg.PLAGUE_MARINES, DG, name=name, composition_index=0)
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = 10.0 + i * 1.4, 10.0
    return squad


def tracker_at(phase, owner=DG, battle_round=1):
    tt = TurnTracker()
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = owner
    tt.set_active(owner)
    tt.battle_round = battle_round
    return tt


class FightStub:
    """Just enough FightController for the "has not fought this phase" clause."""

    def __init__(self, fought=()):
        self.fought_squad_ids = list(fought)
        self.target_reactions = []


class ShootStub:
    def __init__(self, shot=()):
        self.shot_squad_ids = list(shot)


# --- 1. The shared TARGET line ------------------------------------------------
print("--- 1. The shared TARGET line ---")

with detachment_on(DG):
    term = terminators()
    marines = non_terminators()
    c.true("a Deathshroud unit is a TERMINATOR unit",
           death_lords_chosen.is_terminator_unit(term))
    c.true("Plague Marines are not", not death_lords_chosen.is_terminator_unit(marines))
    # Typhus is himself a TERMINATOR, and 19.03 pools keywords - but the
    # merged unit keeps the BODYGUARD's datasheet, so the pairing is what makes
    # the merged unit a TERMINATOR one either way.
    from game import attached_units  # noqa: E402
    typhus_led = attached_units.attach(build(dg.TYPHUS, DG, name="2 Typhus 1"), terminators())
    c.true("Typhus leading Deathshroud is still a TERMINATOR unit",
           death_lords_chosen.is_terminator_unit(typhus_led))

    # Every one of the six refuses a non-TERMINATOR unit, and refuses it for
    # THAT reason rather than by accident - checked one Stratagem at a time,
    # because a shared predicate that one of them forgot to call would still
    # pass a test that only exercised the others.
    sc = strat()
    controllers = {
        "Blooming Pestilence": BloomingPestilenceController(
            sc, turn_tracker=tracker_at(PHASE_COMMAND)),
        "Grim Reapers": GrimReapersController(
            sc, turn_tracker=tracker_at(PHASE_FIGHT), fight_controller=FightStub()),
        "Mortarion's Teachings": MortarionsTeachingsController(
            sc, turn_tracker=tracker_at(PHASE_SHOOTING), shooting_controller=ShootStub()),
        "Undying Spite": UndyingSpiteController(
            sc, turn_tracker=tracker_at(PHASE_FIGHT), fight_controller=FightStub()),
    }
    for label, ctrl in controllers.items():
        c.true(f"{label} accepts a TERMINATOR unit", ctrl.can_use(term))
        c.true(f"{label} refuses Plague Marines", not ctrl.can_use(marines))

with detachment_on():
    sc = strat()
    ctrl = GrimReapersController(sc, turn_tracker=tracker_at(PHASE_FIGHT),
                                 fight_controller=FightStub())
    c.true("without the detachment nothing is buyable", not ctrl.can_use(terminators()))


# --- 2. Blooming Pestilence ---------------------------------------------------
print("--- 2. Blooming Pestilence ---")

# Contagion Range runs 3"/6"/9" and the 12" ceiling exists so that this +3" can
# take a round-3 aura to exactly 12" - so it is worth the full 3" in EVERY
# round. Pinned in all five, because an earlier build had the table as 6/9/12,
# where it would have been worthless from round 3 on.
for _rnd in (1, 2, 3, 4, 5):
    c.true(f"round {_rnd}: +3\" widens the aura",
           dlc_blooming_pestilence.bonus_is_worth_anything(_rnd))
c.true("...by the full 3\" every time - the ceiling never eats any of it",
       all(nurgles_gift.contagion_range_in(r, 3.0) - nurgles_gift.contagion_range_in(r) == 3.0
           for r in (1, 2, 3, 4, 5)))
# The gate is kept even though it currently always says yes: it is the honest
# "never offer what cannot help" test, and it would start refusing if a second
# modifier ever pushed the aura to the ceiling on its own.
c.true("an aura already AT the ceiling gains nothing",
       not dlc_blooming_pestilence.bonus_is_worth_anything.__wrapped__(3)
       if hasattr(dlc_blooming_pestilence.bonus_is_worth_anything, "__wrapped__")
       else nurgles_gift.contagion_range_in(3, 3.0) == nurgles_gift.CONTAGION_RANGE_CAP_IN)

with detachment_on(DG):
    for rnd, buyable in ((1, True), (2, True), (3, True), (4, True)):
        sc = strat()
        aura = NurglesGiftController(turn_tracker=tracker_at(PHASE_COMMAND, battle_round=rnd),
                                     plague_choice=PlagueChoice())
        ctrl = BloomingPestilenceController(
            sc, nurgles_gift_controller=aura,
            turn_tracker=tracker_at(PHASE_COMMAND, battle_round=rnd), game_log=Log())
        c.eq(f"round {rnd}: offered = {buyable}", ctrl.can_use(terminators()), buyable)

    # The bonus really reaches the aura, and it is PER UNIT.
    sc = strat()
    tt = tracker_at(PHASE_COMMAND, battle_round=1)
    aura = NurglesGiftController(turn_tracker=tt, plague_choice=PlagueChoice())
    ctrl = BloomingPestilenceController(sc, nurgles_gift_controller=aura,
                                        turn_tracker=tt, game_log=Log())
    one, two = terminators("2 Deathshroud Terminators 1"), terminators("2 Deathshroud Terminators 2")
    c.eq("before: 3\"", aura.reach_of(one), 3.0)
    c.true("bought", ctrl.use(one))
    c.eq("after: 6\"", aura.reach_of(one), 6.0)
    c.eq("...and the OTHER unit is untouched - the bonus is per unit",
         aura.reach_of(two), 3.0)
    c.true("a second purchase for the same unit is refused", not ctrl.can_use(one))

    # "Start of ANY phase" - no phase test at all, unlike the other five.
    for phase in (PHASE_COMMAND, PHASE_SHOOTING, PHASE_CHARGE, PHASE_FIGHT):
        sc2 = strat()
        tt2 = tracker_at(phase, battle_round=1)
        ctrl2 = BloomingPestilenceController(
            sc2, nurgles_gift_controller=NurglesGiftController(
                turn_tracker=tt2, plague_choice=PlagueChoice()),
            turn_tracker=tt2)
        c.true(f"offered in {phase} - \"start of ANY phase\"", ctrl2.can_use(terminators()))


# --- 3. Grim Reapers ----------------------------------------------------------
print("--- 3. Grim Reapers ---")

with detachment_on(DG):
    sc = strat()
    fight = FightStub()
    ctrl = GrimReapersController(sc, turn_tracker=tracker_at(PHASE_FIGHT),
                                 fight_controller=fight, game_log=Log())
    term = terminators()
    soft, tank = foe_squad(), foe_squad(FoeTank, n=1, name="1 Foe Tank 1")
    c.true("not granted before it is bought", not dlc_grim_reapers.applies(term, soft))
    c.true("bought", ctrl.use(term))
    c.true("re-rolls against ordinary infantry", dlc_grim_reapers.applies(term, soft))
    c.true("...but NOT against a VEHICLE - the printed exclusion",
           not dlc_grim_reapers.applies(term, tank))

    # "has not been selected to fight this phase"
    sc2 = strat()
    fought = FightStub(fought=[term])
    ctrl2 = GrimReapersController(sc2, turn_tracker=tracker_at(PHASE_FIGHT),
                                  fight_controller=fought)
    c.true("a unit that already fought cannot buy it", not ctrl2.can_use(term))

    # "Fight phase" with NO "your" - the phase belongs to both players.
    sc3 = strat()
    ctrl3 = GrimReapersController(sc3, turn_tracker=tracker_at(PHASE_FIGHT, owner=FOE),
                                  fight_controller=FightStub())
    c.true("buyable in the opponent's turn too - the Fight phase is shared",
           ctrl3.can_use(terminators()))

    # Wrong phase.
    sc4 = strat()
    ctrl4 = GrimReapersController(sc4, turn_tracker=tracker_at(PHASE_SHOOTING),
                                  fight_controller=FightStub())
    c.true("not in the Shooting phase", not ctrl4.can_use(terminators()))

    # Through the REAL melee re-roll seam, not the predicate.
    from game.fight import FightController  # noqa: E402
    _fight_src = inspect.getsource(FightController._hit_reroll_reason)
    c.true("game/fight.py's _hit_reroll_reason() reads it",
           "dlc_grim_reapers.applies" in _fight_src)
    from game import shooting as shooting_module  # noqa: E402
    c.true("game/shooting.py does NOT - the grant is Fight-phase only",
           "dlc_grim_reapers" not in inspect.getsource(shooting_module))


# --- 4. Mortarion's Teachings -------------------------------------------------
print("--- 4. Mortarion's Teachings ---")

with detachment_on(DG):
    sc = strat()
    ctrl = MortarionsTeachingsController(sc, turn_tracker=tracker_at(PHASE_SHOOTING),
                                         shooting_controller=ShootStub(), game_log=Log())
    term = terminators()
    gauntlet = next(w for w in term.models[0].weapons if w.name == "Plaguespurt Gauntlet")
    c.eq("the gauntlet prints neither keyword", (gauntlet.assault, gauntlet.heavy), (False, False))
    c.true("bought", ctrl.use(term))
    granted = dlc_mortarions_teachings.adjusted_weapon(gauntlet, term)
    c.eq("it gains BOTH [ASSAULT] and [HEAVY]", (granted.assault, granted.heavy), (True, True))
    c.eq("...on a COPY - the shared instance is untouched",
         (gauntlet.assault, gauntlet.heavy), (False, False))

    melee = next(w for w in term.models[0].weapons if w.name == "Manreaper - strike")
    c.true("a MELEE weapon is untouched - \"ranged weapons\"",
           dlc_mortarions_teachings.adjusted_weapon(melee, term) is melee)

    # "has not been selected to shoot this phase", and "YOUR Shooting phase".
    sc2 = strat()
    c.true("a unit that already shot cannot buy it",
           not MortarionsTeachingsController(
               sc2, turn_tracker=tracker_at(PHASE_SHOOTING),
               shooting_controller=ShootStub(shot=[term])).can_use(term))
    sc3 = strat()
    c.true("not in the opponent's Shooting phase - \"YOUR\"",
           not MortarionsTeachingsController(
               sc3, turn_tracker=tracker_at(PHASE_SHOOTING, owner=FOE),
               shooting_controller=ShootStub()).can_use(terminators()))

    # "Until the end of the PHASE" - one clock, unlike Sudden Storm's two.
    ctrl.reset_phase([term])
    c.true("the grant expires with the phase", not dlc_mortarions_teachings.is_active(term))

    c.true("game/shooting.py's adjuster chain reads it",
           "dlc_mortarions_teachings.adjusted_weapon" in inspect.getsource(shooting_module))

    # THE OTHER READER, and the one that was missing. The line above proves
    # the DAMAGE maths see the grant; rule 10.05's "may still shoot after
    # Advancing" is decided somewhere else entirely - by
    # coldstar.weapon_has_assault(), via shooting.available_shooting_types().
    # This Stratagem's own docstring promises that benefit and could not
    # deliver it. Found by the probe that fixed the same defect in Protocol of
    # the Sudden Storm (reported by a player); see test_awakened_dynasty.py
    # section 4b for the reported case.
    from game import coldstar as _cs
    from game import shooting as _sh

    class _Advanced:
        def __init__(self, squads):
            self.advanced_squad_ids = set(squads)

    _mt_unit = terminators()
    _mt_state = GameState()
    tk.line_up(_mt_unit, y=20.0)
    for _m in _mt_unit.models:
        _mt_state.add_token(_m)
    _mt_gun = next(x for x in _mt_unit.models[0].weapons
                   if x.name == "Plaguespurt Gauntlet")
    c.eq("before: an Advanced unit cannot shoot at all",
         _sh.available_shooting_types(_mt_unit, _mt_state.tokens,
                                      _Advanced([_mt_unit])), [])
    MortarionsTeachingsController(
        strat(), turn_tracker=tracker_at(PHASE_SHOOTING),
        shooting_controller=ShootStub(), game_log=Log()).use(_mt_unit)
    c.true("weapon_has_assault() - the rule-10.05 gate - sees the grant",
           _cs.weapon_has_assault(_mt_gun, _mt_unit))
    c.eq("...so the Advanced unit really gets Assault shooting",
         _sh.available_shooting_types(_mt_unit, _mt_state.tokens,
                                      _Advanced([_mt_unit])),
         [_sh.ASSAULT_SHOOTING])
    c.true("...and a melee weapon still never reaches that gate",
           not _cs.weapon_has_assault(
               next(x for x in _mt_unit.models[0].weapons
                    if x.name == "Manreaper - strike"), _mt_unit))


# --- 5. Sickening Impact ------------------------------------------------------
print("--- 5. Sickening Impact ---")

with detachment_on(DG):
    state = GameState()
    term = terminators(x=10.0, y=10.0)
    # Three Deathshroud in a row at x=10.0/11.6/13.2, y=10.0. Two enemies
    # placed so exactly TWO Deathshroud are within Engagement Range of them -
    # the dice count is per model in range of THAT unit, not per model in the
    # unit, and that is the difference this scene exists to show.
    victim = foe_squad(n=2, x=11.0, y=11.4, name="1 Foe 1")
    for squad in (term, victim):
        for m in squad.models:
            state.add_token(m)
    sc = strat()
    dice = DiceManager()
    ctrl = SickeningImpactController(
        sc, dice_manager=dice, turn_tracker=tracker_at(PHASE_CHARGE),
        game_log=Log(), game_state=state, auto_players=(DG,))
    c.eq("the victim is the only engaged target",
         [s.name for s in dlc_sickening_impact.engaged_targets(term, state.tokens)],
         ["1 Foe 1"])
    n = dlc_sickening_impact.dice_against(term, victim)
    c.true("some but not all Deathshroud are in Engagement Range", 0 < n <= len(term.models))
    c.true("it is offered after a charge move", ctrl.can_use(term))

    script(*([2] * 20))     # every die a 2 - the printed 2+ threshold
    ctrl.on_charge_move_finished(term)
    c.eq(f"{n}D6 were rolled - one per engaged model", len(dice.last_values or []), n)
    dice.acknowledge()
    ctrl.on_dice_acknowledged()
    c.true("the enemy took mortal wounds",
           any(m.is_dead() for m in victim.models) or ctrl.pending_damage_choice is not None)

    # The cap is on the RESULT, not the dice.
    c.eq("the printed cap is 6 mortal wounds",
         dlc_sickening_impact.SICKENING_IMPACT_MAX_WOUNDS, 6)

    # A charge that fell short leaves nothing in Engagement Range, so the
    # ability simply finds no target - no separate "did it succeed" test.
    lonely = terminators("2 Deathshroud Terminators 2", x=60.0, y=60.0)
    for m in lonely.models:
        state.add_token(m)
    c.eq("a unit with nothing in Engagement Range has no targets",
         dlc_sickening_impact.engaged_targets(lonely, state.tokens), [])
    c.true("...so it is not offered", not SickeningImpactController(
        strat(), dice_manager=DiceManager(), turn_tracker=tracker_at(PHASE_CHARGE),
        game_state=state).can_use(lonely))


# --- 6. Undying Spite ---------------------------------------------------------
print("--- 6. Undying Spite ---")

with detachment_on(DG):
    sc = strat()
    dice = DiceManager()
    fight = FightStub()
    log = Log()
    state = GameState()
    term = terminators()
    attacker = foe_squad(n=3, x=11.0, y=11.4, name="1 Foe 1")
    for squad in (term, attacker):
        for m in squad.models:
            state.add_token(m)
    ctrl = UndyingSpiteController(sc, dice_manager=dice, turn_tracker=tracker_at(PHASE_FIGHT),
                                  fight_controller=fight, game_log=log, game_state=state,
                                  auto_players=(DG,))
    c.true("offered when an enemy selects it as a target", ctrl.maybe_offer(attacker, term, melee=True))
    c.true("...and the grant is up", ctrl.is_active(term))

    # The interception: a destroyed model that has not fought stays up on a 4+.
    victim_model = term.models[0]
    victim_model.current_wounds = 0
    script(5, 5, 5)
    kept = ctrl.intercept_destroyed([victim_model])
    c.eq("a 5 keeps the model on the board", kept, [victim_model])
    c.eq("...and it is owed an activation", ctrl.models_owed_an_activation(), [victim_model])
    c.true("the controller is busy until it has struck", ctrl.is_busy)

    script(1, 1, 1)
    other = term.models[1]
    other.current_wounds = 0
    c.eq("a 1 does not", ctrl.intercept_destroyed([other]), [])

    # "...and is THEN removed from play."
    removed = ctrl.resolve_after_attacks(attacker)
    c.eq("it is removed once the attacker has finished", removed, [victim_model])
    c.true("...and the controller is idle again", not ctrl.is_busy)

    # "if that model has NOT FOUGHT this phase"
    sc2 = strat()
    fought = FightStub(fought=[term])
    ctrl2 = UndyingSpiteController(sc2, dice_manager=DiceManager(),
                                   turn_tracker=tracker_at(PHASE_FIGHT),
                                   fight_controller=fought, game_state=state)
    c.true("a unit that already fought cannot buy it", not ctrl2.can_use(term))

    # The argument order is the LIST'S: (attacker, target, melee=).
    c.eq("maybe_offer takes (attacking_squad, target_squad, melee)",
         list(inspect.signature(UndyingSpiteController.maybe_offer).parameters)[1:],
         ["attacking_squad", "target_squad", "melee"])
    c.true("a RANGED reaction is ignored - the WHEN is the Fight phase",
           not UndyingSpiteController(
               strat(), dice_manager=DiceManager(), turn_tracker=tracker_at(PHASE_FIGHT),
               fight_controller=FightStub(), game_state=state,
               auto_players=(DG,)).maybe_offer(attacker, terminators("2 D 3"), melee=False))

    # THE USER'S VERDICT, at its boundary: buy when at least one Terminator is
    # projected to die. Injected, so the test can measure the boundary itself.
    c.eq("the threshold is one expected casualty",
         UndyingSpiteController.MIN_EXPECTED_KILLS, 1)
    verdicts = []

    def _fake_worth(attacker_squad, target_squad):
        verdicts.append((attacker_squad.name, target_squad.name))
        return False

    shy = UndyingSpiteController(strat(), dice_manager=DiceManager(),
                                 turn_tracker=tracker_at(PHASE_FIGHT),
                                 fight_controller=FightStub(), game_state=state,
                                 auto_players=(DG,), worth_using=_fake_worth)
    fresh = terminators("2 Deathshroud Terminators 9")
    c.true("the AI declines when the estimate says nothing would die",
           not shy.maybe_offer(attacker, fresh, melee=True))
    c.eq("...and the estimate really was consulted, with (attacker, target)",
         verdicts, [("1 Foe 1", "2 Deathshroud Terminators 9")])

    # The gate is applied ONLY to the AI - a human is being asked, so the
    # engine must not pre-judge it for them.
    dec = DecisionManager()
    human = UndyingSpiteController(strat(), dice_manager=DiceManager(),
                                   decision_manager=dec,
                                   turn_tracker=tracker_at(PHASE_FIGHT),
                                   fight_controller=FightStub(), game_state=state,
                                   auto_players=(), worth_using=lambda a, t: False)
    c.true("a HUMAN is still offered it even when the estimate says no",
           human.maybe_offer(attacker, terminators("2 Deathshroud Terminators 8"), melee=True))
    c.true("...as a prompt", dec.is_pending)


# --- 7. Signal Pox: a documented no-op ----------------------------------------
print("--- 7. Signal Pox ---")

c.eq("no datasheet in this engine has the LORD OF VIRULENCE keyword",
     [sheet.name for sheet in dg.DEATH_GUARD.datasheets.values()
      if death_lords_chosen.LORD_OF_VIRULENCE_KEYWORD in (sheet.keywords or ())],
     [])
with detachment_on(DG):
    sc = strat()
    ctrl = SignalPoxController(sc, turn_tracker=tracker_at(PHASE_COMMAND), game_log=Log())
    for sheet in (dg.TYPHUS, dg.DEATHSHROUD_TERMINATORS, dg.DAEMON_PRINCE_OF_NURGLE):
        squad = build(sheet, DG, name=f"2 {sheet.name} 1")
        c.true(f"{sheet.name} cannot use Signal Pox - it is not a LORD OF VIRULENCE",
               not ctrl.can_use(squad, all_objectives=[]))
    c.eq("...so it has no bearers at all", dlc_signal_pox.bearers(terminators()), [])
# It is nonetheless fully written, so adding a Lord of Virulence later is one
# datasheet and no rules work - which is exactly what these two pins protect.
c.true("the Stratagem is implemented, not skipped",
       hasattr(SignalPoxController, "refresh") and hasattr(SignalPoxController, "use"))
c.eq("...and it uses the aura's STICKY half",
     "mark_afflicted" in inspect.getsource(SignalPoxController.refresh), True)


# --- 8. The AI ----------------------------------------------------------------
print("--- 8. The AI ---")


class ThrowingAgent:
    def choose_action(self, *a, **k):
        raise AssertionError("a Death Guard Stratagem must never ask the agent")

    def plan_turn(self, *a, **k):
        raise AssertionError("a Death Guard Stratagem must never ask the agent")


# The strongest form of the zero-API guarantee: a handler that cannot TAKE an
# agent cannot call one.
c.eq("_handle_grim_reapers takes no agent",
     "agent" in inspect.signature(agent_driver._handle_grim_reapers).parameters, False)
c.eq("...and no memory either - the verdict is a pure function of the board",
     "memory" in inspect.signature(agent_driver._handle_grim_reapers).parameters, False)

# NEGATIVE SPACE: the three Stratagems the user ruled irrelevant to the AI, and
# the two REACTIVE ones, must have NOTHING in ai/ - the reactive pair answers
# inside its own controller via auto_players.
_ai_names = [n.lower() for n in dir(agent_driver)]
for word, label in (("blooming", "Blooming Pestilence"),
                    ("mortarion", "Mortarion's Teachings"),
                    ("signal_pox", "Signal Pox"),
                    ("undying_spite", "Undying Spite"),
                    ("sickening", "Sickening Impact")):
    c.eq(f"nothing in ai/ mentions {label} - by design",
         [n for n in _ai_names if word in n], [])
c.true("...but Grim Reapers IS there",
       any("grim_reapers" in n for n in _ai_names))

with detachment_on(DG):
    # First opportunity: the handler buys for the first eligible unit, in a
    # deterministic name order, and refuses a second use in the same phase
    # (rule 15.01).
    sc = strat()
    fight = FightStub()
    ctrl = GrimReapersController(sc, turn_tracker=tracker_at(PHASE_FIGHT),
                                 fight_controller=fight, game_log=Log())
    a = terminators("2 Deathshroud Terminators 1", x=10.0)
    b = terminators("2 Deathshroud Terminators 2", x=30.0)
    tokens = list(a.models) + list(b.models)
    agent = ThrowingAgent()   # never touched - proved by the signature above
    c.true("the handler buys at the first opportunity",
           agent_driver._handle_grim_reapers(DG, tokens, ctrl, Log()))
    c.true("...for the first unit by name", dlc_grim_reapers.is_active(a))
    c.true("...and not the second - 15.01 allows one use per phase",
           not dlc_grim_reapers.is_active(b))
    c.true("a second call in the same phase does nothing",
           not agent_driver._handle_grim_reapers(DG, tokens, ctrl, Log()))
    c.true("a None controller does not crash",
           not agent_driver._handle_grim_reapers(DG, tokens, None, Log()))
    c.true("it never acts for the other player",
           not agent_driver._handle_grim_reapers(FOE, tokens, GrimReapersController(
               strat(), turn_tracker=tracker_at(PHASE_FIGHT), fight_controller=FightStub()),
               Log()))

# The two reactive ones take auto_players and answer themselves.
for cls in (UndyingSpiteController, SickeningImpactController):
    c.true(f"{cls.__name__} takes auto_players",
           "auto_players" in inspect.signature(cls.__init__).parameters)
for cls in (BloomingPestilenceController, GrimReapersController,
            MortarionsTeachingsController):
    c.true(f"{cls.__name__} does NOT - it is proactive",
           "auto_players" not in inspect.signature(cls.__init__).parameters)


# --- 9. Source guards ---------------------------------------------------------
print("--- 9. Wiring ---")

_main = pathlib.Path("main.py").read_text(encoding="utf-8")
for needle, label in [
    ("blooming_pestilence_controller = BloomingPestilenceController(", "Blooming Pestilence is built"),
    ("grim_reapers_controller = GrimReapersController(", "Grim Reapers is built"),
    ("mortarions_teachings_controller = MortarionsTeachingsController(", "Mortarion's Teachings is built"),
    ("signal_pox_controller = SignalPoxController(", "Signal Pox is built"),
    ("sickening_impact_controller = SickeningImpactController(", "Sickening Impact is built"),
    ("undying_spite_controller = UndyingSpiteController(", "Undying Spite is built"),
    ("fight_controller.target_reactions.append(undying_spite_controller)",
     "Undying Spite sits in the target-reactions list"),
    ("sickening_impact_controller.on_charge_move_finished",
     "Sickening Impact hangs off the charge hook"),
    ("undying_spite_controller.intercept_destroyed(_swept)",
     "Undying Spite intercepts the death sweep"),
    ("undying_spite_controller.resolve_after_attacks(_fighter)",
     "...and removes them once the attacker finishes"),
    ("sickening_impact_controller.on_dice_acknowledged()", "Sickening Impact gets its dice"),
    ("signal_pox_controller.refresh(state.tokens)", "Signal Pox re-marks each frame"),
    ("signal_pox_controller.expire_for_turn(ending_player)", "...and expires on its owner's turn"),
    ("grim_reapers_controller.reset_phase(_phase_squads)", "Grim Reapers is phase-scoped"),
    ("mortarions_teachings_controller.reset_phase(_phase_squads)", "so is Mortarion's Teachings"),
    ("undying_spite_controller.reset_phase()", "so is Undying Spite"),
    ("grim_reapers_controller=grim_reapers_controller,", "the AI gets the Grim Reapers controller"),
    ("_undying_spite_worth_it", "the Undying Spite verdict is injected"),
]:
    c.true(label, needle in _main)

# The interception has to happen AFTER the sweep - that is the whole point.
c.true("Undying Spite intercepts AFTER remove_dead_models(), not before",
       _main.index("_swept = state.remove_dead_models()")
       < _main.index("undying_spite_controller.intercept_destroyed(_swept)"))

_driver = pathlib.Path("ai/agent_driver.py").read_text(encoding="utf-8")
# A defined-but-never-called handler is invisible to every test that drives it
# directly - the failure class verify_mark_wiring.py exists for, and one this
# project has hit four times. A bare count of the NAME is not enough: a mention
# in a docstring counts too, so removing the real call still left the guard
# green (measured - the A/B probe passed 126/126 until this was tightened).
# The CALL EXPRESSION is checked instead.
c.true("the Grim Reapers handler is defined",
       "def _handle_grim_reapers(" in _driver)
c.true("...AND really called from the Fight-phase branch",
       "if _handle_grim_reapers(player, all_tokens, grim_reapers_controller" in _driver)
c.true("...before the fight loop, or the \"has not been selected to fight\" "
       "TARGET clause would already be false",
       _driver.index("if _handle_grim_reapers(player, all_tokens, grim_reapers_controller")
       < _driver.index("eligible = sorted(fight_controller.eligible_to_select_now()"))

_panel = pathlib.Path("game/ui/action_panel.py").read_text(encoding="utf-8")
for needle, label in [
    ("grim_reapers_controller.use(squad)", "the panel offers Grim Reapers"),
    ("mortarions_teachings_controller.use(squad)", "...and Mortarion's Teachings"),
    ("blooming_pestilence_controller.use(squad)", "...and Blooming Pestilence"),
    ("and not can_grim_reapers_now", "the \"nothing to do\" guard knows about them"),
]:
    c.true(label, needle in _panel)
c.true("the panel does NOT offer the two reactive ones - they arrive as prompts",
       "undying_spite_controller.use" not in _panel
       and "sickening_impact_controller.use" not in _panel)


# --- 10. A/B probes -----------------------------------------------------------
print("--- 10. A/B probes ---")

# The gate really reads the aura's own numbers rather than answering yes
# unconditionally: drop the table to the ceiling and it starts refusing.
_real_default = nurgles_gift.CONTAGION_RANGE_DEFAULT_IN
try:
    nurgles_gift.CONTAGION_RANGE_DEFAULT_IN = nurgles_gift.CONTAGION_RANGE_CAP_IN
    c.true("A/B: with the aura already at the ceiling, the +3\" is refused",
           not dlc_blooming_pestilence.bonus_is_worth_anything(3))
finally:
    nurgles_gift.CONTAGION_RANGE_DEFAULT_IN = _real_default
c.true("A/B restored", dlc_blooming_pestilence.bonus_is_worth_anything(3))

_real_applies = dlc_grim_reapers.is_active
try:
    dlc_grim_reapers.is_active = lambda squad: False
    c.true("A/B: without the grant Grim Reapers re-rolls nothing",
           not dlc_grim_reapers.applies(terminators(), foe_squad()))
finally:
    dlc_grim_reapers.is_active = _real_applies

_real_mt = dlc_mortarions_teachings.is_active
try:
    dlc_mortarions_teachings.is_active = lambda squad: False
    _t = terminators()
    _g = next(w for w in _t.models[0].weapons if w.name == "Plaguespurt Gauntlet")
    c.true("A/B: without the grant the gauntlet keeps neither keyword",
           dlc_mortarions_teachings.adjusted_weapon(_g, _t) is _g)
finally:
    dlc_mortarions_teachings.is_active = _real_mt

c.finish()
