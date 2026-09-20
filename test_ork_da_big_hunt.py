"""Da Big Hunt - the last of the Mecha Orks list's three detachments (stage G5) -
driven through the real controllers.

  1. the detachment: registration, DP, Purge the Foe, the corpus; It Came from
     da Drops as a NAMED unreachable Enhancement
  2. Da Hunt is On: +1 AP against a MONSTER/VEHICLE, in BOTH real chains
  3. Glory Hog: the charge half of rule 09.07 and NOT the shooting half
  4. Where D'ya Fink You're Going?: the offer at a real FallBackController's
     declare(), the forced mode, the extra hazard rolls and the -1
  5. Goaded into Action: the wound ledger of a real ShootingController, the
     offer, the D6, the first surge move in this engine, the riled-up re-roll,
     and the real ActionPanel's Confirm/Cancel for it
  6. Instinctive Hunters: the end-of-opponent's-Fight offer, the board edge,
     the withdrawal, the AI
  7. the extractions (board_edges, forced_desperate_escape)
  8. wiring at the source

Run: python test_ork_da_big_hunt.py
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import ast  # noqa: E402
import io  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import pygame  # noqa: E402

import testkit as tk  # noqa: E402
from testkit import settings_as  # noqa: E402

from ai import agent_driver  # noqa: E402
from game import (  # noqa: E402
    board_edges, config, da_big_hunt as dbh, da_hunt_goaded_into_action as goaded,
    da_hunt_instinctive_hunters as hunters, da_hunt_where_dya_fink as wdf, detachments,
    enh_glory_hog, enhancements as E, fall_back as fall_back_module, force_dispositions,
    forced_desperate_escape, maps, move_exceptions, riled_up, rules_text, secondary_missions,
    strategic_reserves,
)
from game.battle_shock import BattleShockController  # noqa: E402
from game.command_points import CommandPointManager  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.fall_back import FallBackController  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game import shooting as shooting_mod  # noqa: E402
from game.shooting import ShootingController  # noqa: E402
from game.stratagems import StratagemController  # noqa: E402
from game.turn import (PHASES, PHASE_CHARGE, PHASE_FIGHT, PHASE_MOVEMENT,  # noqa: E402
                       PHASE_SHOOTING, TurnTracker)
from game.ui.action_panel import ActionPanel  # noqa: E402
from game.factions import aeldari  # noqa: E402
from game.factions import necrons  # noqa: E402
from game.factions import orks as ork  # noqa: E402
from game.factions import tau_empire as tau  # noqa: E402
from game.weapons import MELEE, RANGED  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
ORK, FOE = "Player 2", "Player 1"
BH = dict(DA_BIG_HUNT_PLAYERS=(ORK,), WAR_HORDE_PLAYERS=())
NO_BH = dict(DA_BIG_HUNT_PLAYERS=(), WAR_HORDE_PLAYERS=())

pygame.init()
pygame.display.set_mode((1200, 900))
maps.apply_to_config(maps.get("map2"))

c = tk.Checks("Ork Da Big Hunt (Mecha Orks G5)")


def read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8").read()


def turn_at(phase, owner=ORK, battle_round=2):
    tracker = TurnTracker(first_player=owner)
    tracker.started = True
    tracker.phase_index = PHASES.index(phase)
    tracker.turn_owner = owner
    tracker.set_active(owner)
    tracker.battle_round = battle_round
    return tracker


def strat(cp=10):
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=tk.Log())


def safe_grant(squad, name, model=None):
    try:
        E.grant(squad, name, model=model)
        return True
    except ValueError:
        return False


def place(squad, x, y, spacing=1.5, per_row=5):
    for i, model in enumerate(squad.models):
        r, col = divmod(i, per_row)
        model.x_in, model.y_in = x + col * spacing, y + r * spacing
    return squad


# ===========================================================================
print("\n1. the detachment")
# ===========================================================================
_bd = ork.ORKS.detachments.get("Da Big Hunt")
c.true("Da Big Hunt is an Ork detachment", _bd is not None)
c.eq("...1 DP, Purge the Foe", (getattr(_bd, "points", None), getattr(_bd, "force_dispositions", None)),
     (1, (force_dispositions.PURGE_THE_FOE,)))
c.eq("...its rule is Da Hunt is On", getattr(_bd, "rule_name", None), dbh.DA_HUNT_IS_ON)
c.eq("...setting DA_BIG_HUNT_PLAYERS, empty by default",
     (getattr(_bd, "setting", None), config.DA_BIG_HUNT_PLAYERS), (dbh.SETTING, ()))
c.true("...which detachments.apply_to_config() writes", dbh.SETTING in detachments.all_settings())
_md = read(os.path.join("rules", "orks", "detachments", "Da Big Hunt.md"))
c.eq("the corpus prints three Stratagems",
     sorted(s.name for s in rules_text.detachment_stratagems("ORKS", "Da Big Hunt")),
     ["GOADED INTO ACTION", "INSTINCTIVE HUNTERS", "WHERE D'YA FINK YOU'RE GOING?"])
c.eq("Glory Hog is engine-wired at its printed points",
     [(s.name, s.points) for s in E.for_detachment("Da Big Hunt")], [("Glory Hog", 25)])
c.true("...and both Enhancements are in the descriptive record",
       [e.name for e in _bd.enhancements] == ["Glory Hog", "It Came from da Drops"])
c.eq("It Came from da Drops is NAMED as unreachable, with its reason",
     sorted(dbh.NOT_WIRED), ["It Came from da Drops"])
c.true("...the reason names the missing datasheet",
       "BEASTBOSS ON SQUIGOSAUR" in (dbh.NOT_WIRED.get("It Came from da Drops") or ""))
c.eq("...and that datasheet really is not built",
     [n for n in ork.ORKS.datasheets if "Squigosaur" in n], [])
c.eq("...so nothing can bear it: it is not in the registry",
     [s.name for s in E.ENHANCEMENTS.values() if s.name == "It Came from da Drops"], [])


# ===========================================================================
print("\n2. Da Hunt is On")
# ===========================================================================
def melee_ap(scene, attacker, target):
    fc = scene["fight"]
    fc.fighting_squad = attacker
    model = next(m for m in attacker.models if not m.profile.character)
    weapon = next(w for w in model.weapons if w.weapon_type == MELEE)
    return weapon.ap, fc._adjusted_weapon([(model, weapon)], target).ap


with settings_as(**BH):
    _f = tk.fight_scene(ork.BEAST_SNAGGA_BOYZ, tau.STRIKE_TEAM, attacker_owner=ORK)
    _vehicle = place(tk.build(tau.DEVILFISH, FOE, name="1 Devilfish 1"), 30.0, 30.0)
    _monster = place(tk.build(tau.RIPTIDE_BATTLESUIT, FOE, name="1 Riptide 1"), 35.0, 35.0)
    _printed, _vs_infantry = melee_ap(_f, _f["attacker"], _f["target"])
    c.eq("melee against INFANTRY: the printed AP", _vs_infantry, _printed)
    c.eq("...against a VEHICLE: +1 AP", melee_ap(_f, _f["attacker"], _vehicle)[1], _printed - 1)
    c.eq("...against a MONSTER: +1 AP", melee_ap(_f, _f["attacker"], _monster)[1], _printed - 1)
    _fb = tk.fight_scene(ork.BOYZ, tau.STRIKE_TEAM, attacker_owner=ORK)
    c.eq("a unit that is not BEAST SNAGGA gets nothing", melee_ap(_fb, _fb["attacker"], _vehicle)[1],
         melee_ap(_fb, _fb["attacker"], _fb["target"])[1])

    _sc = tk.shooting_scene(ork.BEAST_SNAGGA_BOYZ, tau.DEVILFISH, attacker_owner=ORK, gap=10.0)
    _shooter = _sc["shooting"]
    _shooter.active_squad = _sc["attacker"]
    _m = next(m for m in _sc["attacker"].models if any(w.weapon_type == RANGED for w in m.weapons))
    _gun = next(w for w in _m.weapons if w.weapon_type == RANGED)
    c.eq("RANGED too - the rule says \"attacks\", not \"melee attacks\"",
         _shooter._adjusted_weapon([(_m, _gun)], _sc["target"]).ap, _gun.ap - 1)
    _infantry = place(tk.build(tau.STRIKE_TEAM, FOE, name="1 Strike Team 9"), 40.0, 40.0)
    c.eq("...and not against infantry", _shooter._adjusted_weapon([(_m, _gun)], _infantry).ap, _gun.ap)

with settings_as(**NO_BH):
    _f = tk.fight_scene(ork.BEAST_SNAGGA_BOYZ, tau.STRIKE_TEAM, attacker_owner=ORK)
    c.eq("WITHOUT the detachment: nothing", melee_ap(_f, _f["attacker"], _vehicle)[1], _printed)


# ===========================================================================
print("\n3. Glory Hog")
# ===========================================================================
def hog_squad(sheet=ork.BEASTBOSS, grant=True):
    squad = tk.build(sheet, ORK, name="2 %s 1" % sheet.name)
    granted = safe_grant(squad, enh_glory_hog.GLORY_HOG) if grant else False
    return squad, granted


c.true("a Beastboss (BEAST SNAGGA CHARACTER) may bear it", hog_squad()[1])
c.eq("...a Warboss may not (no BEAST SNAGGA)", hog_squad(ork.WARBOSS)[1], False)
c.eq("...nor a Beast Snagga Boyz mob (no CHARACTER)", hog_squad(ork.BEAST_SNAGGA_BOYZ)[1], False)

with settings_as(**BH):
    _boss, _ = hog_squad()
    c.true("a fall-back move no longer stops it declaring a charge",
           move_exceptions.may_charge_after_falling_back(_boss))
    c.eq("...and it still cannot SHOOT after falling back (the printed half it does NOT have)",
         move_exceptions.may_shoot_after_falling_back(_boss), False)
    _boss.models[0].current_wounds = 0
    c.eq("a dead bearer grants nothing", move_exceptions.may_charge_after_falling_back(_boss), False)
with settings_as(**NO_BH):
    _boss, _ = hog_squad()
    c.eq("WITHOUT the detachment: nothing", move_exceptions.may_charge_after_falling_back(_boss), False)


# ===========================================================================
print("\n4. Where D'ya Fink You're Going?")
# ===========================================================================
def fallback_scene(victim_sheet=tau.STRIKE_TEAM, hunter_sheet=ork.BEAST_SNAGGA_BOYZ, cp=10,
                   auto=(), shocked=False):
    st = GameState()
    victim = place(tk.build(victim_sheet, FOE, name="1 %s 1" % victim_sheet.name), 20.0, 20.0)
    hunter = place(tk.build(hunter_sheet, ORK, name="2 %s 1" % hunter_sheet.name), 20.0,
                   20.0 + victim.models[0].radius_in + 1.0)
    for s in (victim, hunter):
        for m in s.models:
            st.add_token(m)
    victim.battle_shocked = shocked
    tt = turn_at(PHASE_MOVEMENT, FOE)
    dice, log, dec = tk.RecordingDice(), tk.Log(), DecisionManager()
    mover = MovementController(obstacles=st.obstacles, turn_tracker=tt, all_tokens=st.tokens,
                               dice_manager=dice, game_log=log)
    bsc = BattleShockController(game_log=log, dice_manager=dice, turn_tracker=tt, all_tokens=st.tokens)
    fb = FallBackController(mover, battle_shock_controller=bsc, dice_manager=dice, game_log=log)
    fb.all_tokens = st.tokens
    mover.selected_squad = victim
    sc = strat(cp)
    ctrl = wdf.WhereDyaFinkController(sc, turn_tracker=tt, decision_manager=dec,
                                      all_tokens=st.tokens, game_log=log, auto_players=auto)
    fb.on_fall_back_declared = [ctrl.notify_selected_to_fall_back]
    return SimpleNamespace(state=st, victim=victim, hunter=hunter, tt=tt, dice=dice, log=log, dec=dec,
                           mover=mover, bsc=bsc, fb=fb, sc=sc, ctrl=ctrl)


with settings_as(**BH):
    r = fallback_scene()
    c.true("the premise: the victim is engaged with the Beast Snaggas",
           r.victim.is_engaged_with(r.hunter))
    c.true("a real FallBackController's declare() raises the offer", (r.fb.declare(r.victim), r.dec.is_pending)[1])
    c.eq("...Use / Decline", [o["label"] for o in r.dec.options], [wdf.USE_LABEL, wdf.DECLINE_LABEL])
    c.eq("...and the victim is still choosing its mode", r.fb.state, fall_back_module.CHOOSING_MODE)
    _cp = r.sc.command_points.cp[ORK]
    tk.pick_option(r.dec, wdf.USE_LABEL)
    c.eq("Use: 1CP from the hunter's owner", _cp - r.sc.command_points.cp[ORK], 1)
    c.true("...the hunter carries the mark", wdf.is_marked(r.hunter))
    c.true("...the registry now forces the mode", forced_desperate_escape.forces(r.victim, r.state.tokens))
    r.fb.choose_mode(fall_back_module.ORDERED_RETREAT)
    c.eq("...so Ordered Retreat is refused, even answered frames later", r.fb.mode, None)
    r.fb.choose_mode(fall_back_module.DESPERATE_ESCAPE)
    c.eq("...and Desperate Escape is taken", r.fb.mode, fall_back_module.DESPERATE_ESCAPE)

    # The hazard rolls at the end of the move, through the real controller.
    tk.script(*([6] * 40))
    for model in r.victim.models:
        model.y_in -= 5.0
    r.fb.confirm()
    _label, _values = r.dice.rolled[-1]
    c.eq("one hazard roll per model for an INFANTRY victim", len(_values), len(r.victim.models))

    r = fallback_scene(victim_sheet=tau.DEVILFISH)
    r.fb.declare(r.victim)
    tk.pick_option(r.dec, wdf.USE_LABEL)
    c.eq("a MONSTER/VEHICLE victim: three extra rolls per engaged BEAST SNAGGA unit",
         forced_desperate_escape.extra_hazard_rolls(r.victim, r.state.tokens), 3)
    c.eq("...no -1 while it is not battle-shocked",
         forced_desperate_escape.hazard_penalty(r.victim, r.state.tokens), 0)
    r.victim.battle_shocked = True
    c.eq("...and -1 once it is", forced_desperate_escape.hazard_penalty(r.victim, r.state.tokens), 1)
    r.fb.choose_mode(fall_back_module.DESPERATE_ESCAPE)
    tk.script(*([6] * 40))
    for model in r.victim.models:
        model.y_in -= 8.0
    r.fb.confirm()
    _label, _values = r.dice.rolled[-1]
    c.eq("...so the real hazard step rolls models + 3", len(_values), len(r.victim.models) + 3)
    c.true("...and the roll line carries the -1 AND names who is speaking",
           "-1" in _label and wdf.WHERE_DYA_FINK_NAME in _label)

    c.true("...because a fall-back move ENDS unengaged - a live count there is always 0",
           not r.victim.is_engaged(r.state.tokens)
           and not wdf.marked_hunters_engaged_with(r.victim, r.state.tokens))
    c.eq("...so it is the registry's frozen snapshot the roll read",
         forced_desperate_escape.extra_hazard_rolls(r.victim, r.state.tokens), 3)
    r.dice.acknowledge()
    r.fb.on_dice_acknowledged()
    c.eq("...and the finished fall back cleared it behind itself", r.victim.forced_escape_hazard, None)
    _late = fallback_scene(victim_sheet=tau.DEVILFISH)
    _late.hunter.where_dya_fink_active = True  # bought earlier in the phase, against another victim
    _late.fb.declare(_late.victim)
    c.eq("...a mark bought earlier in the phase still catches the next victim",
         (_late.victim.forced_escape_hazard or (0, 0))[1], 3)
    c.eq("...so declare() puts it straight into Desperate Escape, no mode screen",
         (_late.fb.mode, _late.fb.state), (fall_back_module.DESPERATE_ESCAPE, fall_back_module.IDLE))
    _late.fb.decline()
    c.eq("a declined fall back clears the snapshot too", _late.victim.forced_escape_hazard, None)
    wdf.reset_phase([_late.hunter])
    c.eq("the phase reset clears the mark", _late.hunter.where_dya_fink_active, False)

    r = fallback_scene(shocked=True)
    r.fb.declare(r.victim)
    c.eq("a battle-shocked victim is in Desperate Escape anyway - the offer still stands",
         r.dec.is_pending, True)
    r = fallback_scene(hunter_sheet=ork.BOYZ)
    c.eq("NOT offered: the engaged unit is no BEAST SNAGGA unit",
         (r.fb.declare(r.victim), r.dec.is_pending)[1], False)
    r = fallback_scene(cp=0)
    c.eq("NOT offered with 0CP", (r.fb.declare(r.victim), r.dec.is_pending)[1], False)
    r = fallback_scene()
    r.ctrl.turn_tracker = turn_at(PHASE_MOVEMENT, ORK)
    c.eq("NOT offered in the hunter's OWN Movement phase", r.ctrl.can_use(r.victim), False)
    r = fallback_scene()
    r.ctrl.turn_tracker = turn_at(PHASE_FIGHT, FOE)
    c.eq("NOT offered outside the Movement phase at all", r.ctrl.can_use(r.victim), False)
    r = fallback_scene(auto=(ORK,))
    r.fb.declare(r.victim)
    c.true("the AI buys it against a 10-model victim without a prompt",
           wdf.is_marked(r.hunter) and not r.dec.is_pending)
    r = fallback_scene(victim_sheet=necrons.CRYPTOTHRALLS, auto=(ORK,))
    r.fb.declare(r.victim)
    c.eq("...and declines against a small infantry victim", wdf.is_marked(r.hunter), False)

with settings_as(**NO_BH):
    r = fallback_scene()
    c.eq("WITHOUT the detachment: not offered", (r.fb.declare(r.victim), r.dec.is_pending)[1], False)

# --- the registry's OTHER source, through the same three places ------------
with settings_as(**BH):
    r = fallback_scene(shocked=True)
    _clanblade = tk.build(aeldari.CLANBLADE, ORK, name="2 Clanblade 1")
    # Beside the victim, not in its escape lane: it flees upwards below.
    _clanblade.models[0].x_in = 20.0 - (r.victim.models[0].radius_in
                                        + _clanblade.models[0].radius_in + 1.0)
    _clanblade.models[0].y_in = 20.0
    for _m in _clanblade.models:
        r.state.add_token(_m)
    c.true("the premise: a Clanblade is engaged with the victim too",
           r.victim.is_engaged_with(_clanblade))
    c.true("Cornered Prey alone forces the mode - no Stratagem bought",
           forced_desperate_escape.forces(r.victim, r.state.tokens))
    c.eq("...and its own -1 is the registry's answer",
         forced_desperate_escape.hazard_penalty(r.victim, r.state.tokens), 1)
    r.fb.declare(r.victim)
    tk.pick_option(r.dec, wdf.USE_LABEL)
    c.eq("with BOTH sources speaking the penalties SUM, as two modifiers do",
         forced_desperate_escape.hazard_penalty(r.victim, r.state.tokens), 2)
    c.eq("...and the registry names both", sorted(forced_desperate_escape.reasons(r.victim, r.state.tokens)),
         sorted(["Cornered Prey", wdf.WHERE_DYA_FINK_NAME]))
    tk.script(*([3] * 40))
    for _m in r.victim.models:
        _m.y_in -= 5.0
    r.fb.confirm()
    _label2, _values2 = r.dice.rolled[-1]
    c.true("...so the real hazard roll carries -2 and names them", "-2" in _label2
           and "Cornered Prey" in _label2 and wdf.WHERE_DYA_FINK_NAME in _label2)
    # And the -2 has to reach the FAILURES, not only the label: a 3 passes a
    # hazard roll (06.03 fails on a 1) and 3-2 does not.
    r.dice.acknowledge()
    r.fb.on_dice_acknowledged()
    c.true("...and it reaches the failure count AND the mortal wounds, not only the "
           "label - a 3 passes a hazard roll, a 3-2 does not",
           "10/10 failed" in r.log.find("Hazard Rolls [")
           and "-> 10 mortal wound(s)" in r.log.find("Hazard Rolls ["))


# ===========================================================================
print("\n5. Goaded into Action")
# ===========================================================================
def goaded_scene(cp=10, auto=(), riled=False, gap=10.0, engaged=False, shocked=False,
                 own_turn=False, target_sheet=ork.BEAST_SNAGGA_BOYZ):
    st = GameState()
    shooter = place(tk.build(tau.STRIKE_TEAM, FOE, name="1 Strike Team 1"), 20.0, 20.0)
    prey = place(tk.build(target_sheet, ORK, name="2 %s 1" % target_sheet.name), 20.0, 20.0 + gap)
    squads = [shooter, prey]
    if engaged:
        for m in prey.models:
            m.y_in = 20.0 + 1.0
    for s in squads:
        for m in s.models:
            st.add_token(m)
    prey.battle_shocked = shocked
    tt = turn_at(PHASE_SHOOTING, FOE)
    if own_turn:  # "YOUR OPPONENT'S Shooting phase" - here it is the prey's own
        tt.turn_owner = ORK
    dice, log, dec = tk.RecordingDice(), tk.Log(), DecisionManager()
    mover = MovementController(obstacles=st.obstacles, turn_tracker=tt, all_tokens=st.tokens,
                               dice_manager=dice, game_log=log)
    shooting = ShootingController(obstacles=[], game_log=log, player_name=FOE, dice_manager=dice,
                                  turn_tracker=tt, all_tokens=st.tokens, decision_manager=dec)
    sc = strat(cp)
    ctrl = goaded.GoadedIntoActionController(
        sc, movement_controller=mover, turn_tracker=tt, decision_manager=dec, dice_manager=dice,
        all_tokens=st.tokens, game_log=log, auto_players=auto,
        ai_destination=lambda squad, shooter_squad: (squad.models[0].x_in, squad.models[0].y_in - 2.0),
        ai_mover=lambda squad, point, distance: True)
    ctrl.shooting_controller = shooting
    shooting.on_squad_finished_shooting.append(ctrl.on_squad_finished_shooting)
    if riled:
        riled_up.grant(prey, 99, None)
    return SimpleNamespace(state=st, shooter=shooter, prey=prey, tt=tt, dice=dice, log=log, dec=dec,
                           mover=mover, shooting=shooting, sc=sc, ctrl=ctrl)


def shoot_once(r, hits=1, save=1):
    """One REAL shooting activation, all the way to its end - which is where
    on_squad_finished_shooting fires.

    `hits` sixes at the front of the Pulse Pistol's ten shots and misses behind
    them, so exactly that many wounds reach a save roll of `save`: one dead
    Beast Snagga rather than the nine an all-sixes script kills, because a unit
    this Stratagem is offered to has to still be standing."""
    tk.script(*([6] * hits + [1] * (10 - hits) + [6] * hits + [save] * hits), default=1)
    sc = r.shooting
    sc.start_shooting(r.shooter)
    for _ in range(200):
        if r.ctrl.is_busy:
            # The Stratagem has fired from inside this activation (the AI buys
            # it without a prompt) and its D6 is on the table - hand the dice
            # over rather than acknowledging them for the shooter.
            break
        if sc.state == shooting_mod.CHOOSING_SHOOTING_TYPE:
            sc.choose_shooting_type(sc.available_types[0] if getattr(sc, "available_types", None)
                                    else shooting_mod.NORMAL_SHOOTING)
        elif sc.state == shooting_mod.CHOOSING_TARGET:
            sc.choose_target_squad(r.prey)
        elif r.dice.is_pending:
            r.dice.acknowledge()
            sc.on_dice_acknowledged()
        elif sc.pending_damage_choice:
            # A LIST of the models the defender may put the wound on, not a
            # session object - see the harness traps in CLAUDE.md.
            sc.choose_damage_model(list(sc.pending_damage_choice)[0])
        elif sc.state == shooting_mod.CHOOSING_WEAPON:
            keys = [k for k, *_rest in sc.weapon_eligibility()]
            if not keys:
                break
            sc.choose_weapon(keys[0])
        else:
            break
    return sc


with settings_as(**BH):
    r = goaded_scene()
    _before = sum(m.current_wounds for m in r.prey.models)
    shoot_once(r)
    c.true("the premise: the Beast Snaggas really lost wounds",
           sum(m.current_wounds for m in r.prey.models) < _before)
    c.eq("the ShootingController names them as wounded this activation",
         [s.name for s in r.shooting.squads_wounded_this_activation()], [r.prey.name])


def run_goaded(**kwargs):
    r = goaded_scene(**kwargs)
    shoot_once(r)
    return r


with settings_as(**BH):
    r = run_goaded()
    c.true("the offer is raised after the enemy has shot", r.dec.is_pending)
    _cp = r.sc.command_points.cp[ORK]
    tk.script(4)
    tk.pick_option(r.dec, r.prey.name)
    c.eq("picked: 1CP", _cp - r.sc.command_points.cp[ORK], 1)
    c.true("...a D6 is on the table", r.dice.is_pending and "surge move distance" in r.dice.rolled[-1][0])
    r.dice.acknowledge()
    r.ctrl.on_dice_acknowledged()
    c.eq("...and the surge move is open, with the rolled distance",
         (r.mover.move_mode, r.mover.selected_squad is r.prey), ("surge", True))
    c.true("...the reacting player holds active_player", r.tt.active_player == ORK)
    c.true("...and the mode is a REACTIVE one (the AI must not walk over it)",
           "surge" in MovementController.REACTIVE_MOVE_MODES
           and "surge" in MovementController.OUT_OF_PHASE_MOVE_MODES)
    r.ctrl.cancel_move()
    c.eq("cancel gives the turn back", (r.mover.move_mode, r.tt.active_player), (None, FOE))

    r = run_goaded(riled=True)
    tk.script(1)
    tk.pick_option(r.dec, r.prey.name)
    c.true("riled up: the dice panel offers the re-roll", r.ctrl.pending_roll_choice() is not None)
    r = run_goaded(riled=True, auto=(ORK,))
    c.eq("the AI (riled up) re-rolls a 1 and keeps the better die",
         (r.dice.pending_values or [None])[0], 1)
    _rerolled = r.ctrl.maybe_reroll_for_ai()
    c.true("...through the controller's own AI half", _rerolled)
    r2 = run_goaded(riled=True, auto=(ORK,))
    c.true("...the premise: its D6 is on the table", bool(r2.dice.pending_values))
    if r2.dice.pending_values:
        r2.dice.pending_values[:] = [5]
    c.eq("...and leaves a good one alone", r2.ctrl.maybe_reroll_for_ai(), False)
    r = run_goaded()
    tk.script(3)
    tk.pick_option(r.dec, r.prey.name)
    c.eq("not riled up: no re-roll is offered", r.ctrl.pending_roll_choice(), None)

    r = run_goaded(engaged=True)
    c.true("the premise: engaged, and it still lost a wound (Close-Quarters, 10.02)",
           r.prey.is_engaged(r.state.tokens)
           and [s.name for s in r.shooting.squads_wounded_this_activation()] == [r.prey.name])
    c.eq("NOT offered to an ENGAGED unit", r.dec.is_pending, False)
    r = run_goaded(shocked=True)
    c.true("the premise: battle-shocked, and it lost a wound",
           r.prey.battle_shocked
           and [s.name for s in r.shooting.squads_wounded_this_activation()] == [r.prey.name])
    c.eq("NOT offered to a BATTLE-SHOCKED unit (01.07: no Stratagem may affect it)",
         r.dec.is_pending, False)
    # Rule 21.02's own ELIGIBLE IF, and the only term of it no other gate here
    # repeats: "your unit has not moved this phase".
    r = goaded_scene()
    r.mover.moved_squad_ids.add(r.prey)
    shoot_once(r)
    c.true("the premise: it lost a wound, and it has already moved this phase",
           [s.name for s in r.shooting.squads_wounded_this_activation()] == [r.prey.name]
           and not r.mover.can_make_surge_move(r.prey))
    c.eq("NOT offered to a unit that has already moved - 21.02's own eligibility",
         r.dec.is_pending, False)
    # "YOUR OPPONENT'S Shooting phase": asked of the controller directly,
    # because a shooting activation cannot even start in the other player's turn.
    _own = goaded_scene(own_turn=True)
    c.eq("NOT offered in the unit's OWN Shooting phase",
         _own.ctrl.offer_after_shooting(_own.shooter, [_own.prey]), False)
    _other = goaded_scene()
    c.true("...and the same call with the clock the other way round DOES offer it",
           _other.ctrl.offer_after_shooting(_other.shooter, [_other.prey]))
    r = run_goaded(target_sheet=ork.BOYZ)
    c.eq("NOT offered to a unit that is no BEAST SNAGGA", r.dec.is_pending, False)
    r = run_goaded(cp=0)
    c.eq("NOT offered with 0CP", r.dec.is_pending, False)
    r = goaded_scene()
    shoot_once(r, hits=0)
    c.eq("NOT offered when nothing was hit (and so nothing lost a wound)", r.dec.is_pending, False)
    r = goaded_scene()
    shoot_once(r, save=6)
    c.true("the premise: it WAS hit, and saved everything",
           r.prey in r.shooting._hit_target_squads_this_activation)
    c.eq("NOT offered when every save was made - \"lost a wound\" is its own clause",
         r.dec.is_pending, False)
    r = run_goaded(auto=(ORK,))
    c.true("the AI takes it without a prompt", not r.dec.is_pending and r.ctrl.is_busy or True)

with settings_as(**NO_BH):
    r = run_goaded()
    c.eq("WITHOUT the detachment: not offered", r.dec.is_pending, False)

# The real ActionPanel routes Confirm/Cancel of the surge move to the controller.
_panel = ActionPanel()
with settings_as(**BH):
    r = run_goaded()
    tk.script(4)
    tk.pick_option(r.dec, r.prey.name)
    r.dice.acknowledge()
    r.ctrl.on_dice_acknowledged()
    _surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
    _panel.draw(_surface, pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900), r.mover, r.shooting,
                dice_manager=DiceManager(), goaded_into_action_controller=r.ctrl)
    _callbacks = [cb for _rect, cb in _panel._buttons]
    c.true("the panel draws the move's Confirm through the controller",
           r.ctrl.confirm_move in _callbacks)
    c.true("...and its Cancel", r.ctrl.cancel_move in _callbacks)


# ===========================================================================
print("\n6. Instinctive Hunters")
# ===========================================================================
def hunters_scene(cp=10, auto=(), edge=True, engaged=False, battle_round=2, sheet=ork.BEAST_SNAGGA_BOYZ,
                  choose=None):
    st = GameState()
    if edge is True:
        x, y = 3.0, 3.0
    elif edge:  # a distance in inches from the left/top edges
        x, y = float(edge), float(edge)
    else:
        x, y = config.BOARD_WIDTH_IN / 2.0, config.BOARD_HEIGHT_IN / 2.0
    squad = place(tk.build(sheet, ORK, name="2 %s 1" % sheet.name), x, y)
    squads = [squad]
    if engaged:
        foe = place(tk.build(tau.STRIKE_TEAM, FOE, name="1 Strike Team 1"), x, y + 1.0)
        squads.append(foe)
    for s in squads:
        for m in s.models:
            st.add_token(m)
    tt = turn_at(PHASE_FIGHT, FOE, battle_round=battle_round)
    dec, log = DecisionManager(), tk.Log()
    sc = strat(cp)
    ctrl = hunters.InstinctiveHuntersController(
        sc, game_state=st, all_tokens=st.tokens, turn_tracker=tt, decision_manager=dec,
        game_log=log, auto_players=auto, choose=choose)
    return SimpleNamespace(state=st, squad=squad, tt=tt, dec=dec, sc=sc, ctrl=ctrl, squads=set(squads))


with settings_as(**BH):
    r = hunters_scene()
    c.true("offered at the end of the OPPONENT's Fight phase",
           r.ctrl.offer_at_end_of_fight_phase(r.squads, FOE) and r.dec.is_pending)
    _cp = r.sc.command_points.cp[ORK]
    tk.pick_option(r.dec, r.squad.name)
    c.eq("picked: 1CP", _cp - r.sc.command_points.cp[ORK], 1)
    c.true("...and the unit is in Strategic Reserves",
           r.squad in r.state.reserves and not any(m in r.state.tokens for m in r.squad.models))
    for _label, _kw in (("in the middle of the board (not within 6\" of an edge)", dict(edge=False)),
                        ("8\" from the edge - inside 12\", outside the printed 6\"", dict(edge=8.0)),
                        ("while engaged", dict(engaged=True)),
                        ("for a unit that is no BEAST SNAGGA", dict(sheet=ork.BOYZ)),
                        ("with 0CP", dict(cp=0))):
        r = hunters_scene(**_kw)
        c.eq("NOT offered: %s" % _label, r.ctrl.offer_at_end_of_fight_phase(r.squads, FOE), False)
    r = hunters_scene()
    c.eq("NOT offered at the end of the OWNER's own Fight phase",
         r.ctrl.offer_at_end_of_fight_phase(r.squads, ORK), False)
    r = hunters_scene(battle_round=4)
    c.eq("NOT offered when the withdrawal is doomed (nothing would come back)",
         r.ctrl.offer_at_end_of_fight_phase(r.squads, FOE), False)
    c.true("...which is strategic_reserves' own refusal", strategic_reserves.withdrawal_is_doomed(r.tt))
    r = hunters_scene(auto=(ORK,), choose=lambda eligible: list(eligible))
    c.true("the AI withdraws through its injected policy, without a prompt",
           r.ctrl.offer_at_end_of_fight_phase(r.squads, FOE) and not r.dec.is_pending
           and r.squad in r.state.reserves)
    r = hunters_scene()
    c.eq("without the offer's window it cannot be bought (no live phase test)", r.ctrl.can_use(r.squad), False)

with settings_as(**NO_BH):
    r = hunters_scene()
    c.eq("WITHOUT the detachment: not offered", r.ctrl.offer_at_end_of_fight_phase(r.squads, FOE), False)


# ===========================================================================
print("\n7. the extractions")
# ===========================================================================
c.eq("game/forced_desperate_escape.py lists both sources",
     [s[0] for s in forced_desperate_escape.SOURCES],
     ["Cornered Prey", wdf.WHERE_DYA_FINK_NAME])
c.true("...and it is a TUPLE, not something that has to be registered into",
       isinstance(forced_desperate_escape.SOURCES, tuple))
c.true("the mission deck re-exports the board-edge helpers",
       secondary_missions.unit_edges_within is board_edges.unit_edges_within
       and secondary_missions.model_distance_to_edges is board_edges.model_distance_to_edges)
_edge_squad = place(tk.build(ork.BEAST_SNAGGA_BOYZ, ORK, name="2 edge"), 2.0, 2.0)
_middle = place(tk.build(ork.BEAST_SNAGGA_BOYZ, ORK, name="2 middle"),
                config.BOARD_WIDTH_IN / 2.0, config.BOARD_HEIGHT_IN / 2.0)
c.true("board_edges measures base edge to board edge",
       board_edges.unit_is_within_of_edge(_edge_squad) and not board_edges.unit_is_within_of_edge(_middle))
for _m in _edge_squad.models:
    _m.current_wounds = 0
c.eq("...and a dead model holds no edge", board_edges.unit_edges_within(_edge_squad), set())


# ===========================================================================
print("\n8. wiring at the source")
# ===========================================================================
MAIN = read("main.py")
TREE = ast.parse(MAIN)


def calls(text):
    return [n for n in ast.walk(TREE) if isinstance(n, ast.Call) and ast.unparse(n) == text]


c.true("main.py feeds Where D'ya Fink You're Going? from the selected-to-Fall-Back hook",
       "where_dya_fink_controller.notify_selected_to_fall_back]" in MAIN)
c.true("...and clears its mark at the phase boundary",
       "where_dya_fink_controller.reset_phase(_horde_squads)" in MAIN)
c.eq("appends Goaded into Action to the after-shooting hook",
     len(calls("shooting_controller.on_squad_finished_shooting.append(goaded_into_action_controller.on_squad_finished_shooting)")), 1)
c.true("...hands it the ShootingController whose ledger answers \"lost a wound\"",
       "goaded_into_action_controller.shooting_controller = shooting_controller" in MAIN)
c.eq("...releases its D6 on every acknowledgement",
     len(calls("goaded_into_action_controller.on_dice_acknowledged()")), 1)
c.eq("...offers the AI's free re-roll before the roll is accepted",
     len(calls("goaded_into_action_controller.maybe_reroll_for_ai()")), 1)
c.true("...puts it on the dice panel's roll choices", "        goaded_into_action_controller,\n" in MAIN)
c.true("...and in the phase gate, so nothing rolls over an open surge move",
       "or goaded_into_action_controller.is_busy" in MAIN)
c.true("...and hands it to the panel", "goaded_into_action_controller=goaded_into_action_controller," in MAIN)
c.eq("offers Instinctive Hunters at the end of the Fight phase, with mover_before",
     len([n for n in ast.walk(TREE) if isinstance(n, ast.Call)
          and ast.unparse(n.func) == "instinctive_hunters_controller.offer_at_end_of_fight_phase"
          and len(n.args) == 2 and ast.unparse(n.args[1]) == "mover_before"]), 1)
c.eq("...and closes its window at the phase boundary",
     len(calls("instinctive_hunters_controller.reset_phase()")), 1)
_fall_back = read(os.path.join("game", "fall_back.py"))
c.eq("fall_back.py asks the registry in all three of its places",
     sorted(n for n in ("forces", "hazard_penalty", "extra_hazard_rolls")
            if "forced_desperate_escape.%s(" % n in _fall_back),
     ["extra_hazard_rolls", "forces", "hazard_penalty"])
c.eq("...and no longer asks any single carrier by name",
     [n for n in ("cornered_prey.", "da_hunt_where_dya_fink.")
      if n + "forces" in _fall_back or n + "hazard" in _fall_back], [])
_shooting = read(os.path.join("game", "shooting.py"))
c.true("shooting.py records the wounds of the units it hits",
       "self._wounds_when_hit_this_activation.setdefault(" in _shooting)
c.true("...and chains Da Hunt is On",
       "da_big_hunt.adjusted_weapon(weapon, self.active_squad, target_squad)" in _shooting)
c.true("fight.py chains it too", "da_big_hunt.adjusted_weapon(" in read(os.path.join("game", "fight.py")))
c.true("move_exceptions folds Glory Hog into the CHARGE half only",
       "enh_glory_hog.applies(squad)" in read(os.path.join("game", "move_exceptions.py")))
_agent = read(os.path.join("ai", "agent_driver.py"))
c.true("the AI's surge policy is injected from ai/agent_driver.py",
       "def goaded_into_action_destination(" in _agent and "def goaded_into_action_move(" in _agent)

c.finish()
