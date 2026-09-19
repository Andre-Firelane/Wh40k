"""Blitz Brigade - the second of the Mecha Orks list's three detachments (stage
G4) - driven through the real controllers.

  1. the detachment: registration, DP, setting, the corpus, WAGON's carriers
  2. Unstoppable Momentum, the Advance: a WAGON's Advance IS a 6 - no die thrown
     (so no re-roll is ever offered), the Advance modifiers still land on it,
     and the AI's observation is told the 6
  3. Unstoppable Momentum, the charge re-roll: the THIRD carrier of
     game/charge_reroll.py, on a real ChargeController mid-roll
  4. Targetin' Gizmos: More Dakka's second source, on a real ShootingController
     - [IGNORES COVER] at the chain AND the cover gate, [SUSTAINED HITS 1] only
     while riled up, and only while a BIG MEK rides inside
  5. Boss Boomer: the WAGON becomes a bearer of the embarked WARBOSS's ability -
     measured on the real controllers AND drawn on the real ActionPanel
  6. Keep It Runnin': the third printing of the end-of-Fight embark
     (game/end_of_fight_embark.py) - offered, picked, paid, embarked; every
     clause as a negative; the AI declines
  7. Impending Krunch: offered at the end of a WAGON's charge move (through a
     real ChargeController's confirm), paid, each engaged enemy tests at -1
     through the shared queue; the AI's rule
  8. READIED BRAWLERS IS NOT WIRED - the named gap, pinned (user decision)
  9. the extractions (end_of_fight_embark, forced_shock_queue, ork_units)
 10. wiring at the source

Run: python test_ork_blitz_brigade.py
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

from ai import observation  # noqa: E402
from game import (  # noqa: E402
    attached_units, blitz_brigade as bb, blitz_impending_krunch as krunch, blitz_keep_it_runnin as kir,
    config, detachments, end_of_fight_embark, enh_boss_boomer, enh_targetin_gizmos as gizmos,
    enhancements as E, force_dispositions, forced_shock_queue, maps, mobbed, more_dakka, ork_units,
    riled_up, rules_text, skyborne_sanctuary,
)
from game.battle_shock import BattleShockController  # noqa: E402
from game.boss_motivation import IntimidatingMotivationController, KeepHuntinController  # noqa: E402
from game.charge import ChargeController  # noqa: E402
from game.command_points import CommandPointManager  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.factions import necrons  # noqa: E402
from game.factions import orks as ork  # noqa: E402
from game.factions import tau_empire as tau  # noqa: E402
from game.fight import FightController  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.proactive_stratagems import ProactiveStratagems  # noqa: E402
from game.shooting import ShootingController  # noqa: E402
from game.stratagems import StratagemController  # noqa: E402
from game.transport import TransportController  # noqa: E402
from game.turn import PHASES, PHASE_CHARGE, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker  # noqa: E402
from game.ui.action_panel import ActionPanel  # noqa: E402
from game.weapons import RANGED  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
ORK, FOE = "Player 2", "Player 1"
# War Horde off in both: config holds it for Player 2 by default, and nothing
# here should pass or fail because of it.
BB = dict(BLITZ_BRIGADE_PLAYERS=(ORK,), WAR_HORDE_PLAYERS=())
NO_BB = dict(BLITZ_BRIGADE_PLAYERS=(), WAR_HORDE_PLAYERS=())

pygame.init()
pygame.display.set_mode((1200, 900))
maps.apply_to_config(maps.get("map2"))

c = tk.Checks("Ork Blitz Brigade (Mecha Orks G4)")


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


def place(squad, x, y, spacing=1.3, per_row=5):
    for i, model in enumerate(squad.models):
        r, col = divmod(i, per_row)
        model.x_in, model.y_in = x + col * spacing, y + r * spacing
    return squad


def embark(state, squad, carrier):
    """Put `squad` inside `carrier` the way TransportController.embark() leaves
    it: off the token list, on the embarked list, embarked_in set."""
    for model in squad.models:
        if model in state.tokens:
            state.tokens.remove(model)
    squad.embarked_in = carrier.models[0]
    state.embarked_squads.append(squad)
    return squad


# ===========================================================================
print("\n1. the detachment")
# ===========================================================================
_bd = ork.ORKS.detachments.get("Blitz Brigade")
c.true("Blitz Brigade is an Ork detachment", _bd is not None)
c.eq("...1 DP, Take and Hold", (getattr(_bd, "points", None), getattr(_bd, "force_dispositions", None)),
     (1, (force_dispositions.TAKE_AND_HOLD,)))
c.eq("...its rule is Unstoppable Momentum", getattr(_bd, "rule_name", None), bb.UNSTOPPABLE_MOMENTUM)
c.eq("...setting BLITZ_BRIGADE_PLAYERS, empty by default", (getattr(_bd, "setting", None), config.BLITZ_BRIGADE_PLAYERS),
     (bb.SETTING, ()))
c.true("...which detachments.apply_to_config() writes", bb.SETTING in detachments.all_settings())
_md = read(os.path.join("rules", "orks", "detachments", "Blitz Brigade.md"))
c.eq("the corpus prints three Stratagems",
     sorted(s.name for s in rules_text.detachment_stratagems("ORKS", "Blitz Brigade")),
     ["IMPENDING KRUNCH", "KEEP IT RUNNIN'", "READIED BRAWLERS"])
c.eq("both Enhancements are engine-wired at the printed points",
     [(s.name, s.points, s.unit_level) for s in E.for_detachment("Blitz Brigade")],
     [("Targetin' Gizmos", 10, True), ("Boss Boomer", 10, True)])
c.true("...as the corpus prints them", "### Targetin' Gizmos - 10 pts" in _md and "### Boss Boomer - 10 pts" in _md)
_wagons = sorted(n for n, ds in ork.ORKS.datasheets.items() if "WAGON" in (ds.keywords or ()))
c.eq("WAGON is printed by exactly the Battlewagon, the Gunwagon and the Kill Rig",
     _wagons, ["Battlewagon", "Gunwagon", "Kill Rig"])
c.true("...and read as a datasheet keyword: a Battlewagon is one, a Trukk is not",
       bb.is_wagon_unit(tk.build(ork.BATTLEWAGON, ORK)) and not bb.is_wagon_unit(tk.build(ork.TRUKK, ORK)))


# ===========================================================================
print("\n2. Unstoppable Momentum: the Advance is a 6")
# ===========================================================================
def advance_rig(sheet, owner=ORK):
    st = GameState()
    squad = place(tk.build(sheet, owner, name="%s %s 1" % (owner[-1], sheet.name)), 20.0, 20.0)
    for m in squad.models:
        st.add_token(m)
    tt = turn_at(PHASE_MOVEMENT, owner)
    dm = tk.RecordingDice()
    mc = MovementController(obstacles=st.obstacles, turn_tracker=tt, all_tokens=st.tokens, dice_manager=dm)
    mc.select(squad.models[0])
    mc.start_move()
    before = mc.remaining_range.get(squad.models[0].id)
    return squad, mc, dm, before


with settings_as(**BB):
    _w, _mc, _dm, _r0 = advance_rig(ork.BATTLEWAGON)
    _mc.start_run()
    c.eq("a Battlewagon's Advance adds exactly 6\"", round(_mc.remaining_range[_w.models[0].id] - _r0, 3), 6.0)
    c.eq("...and no die is thrown - nothing a re-roll could buy", _dm.rolled, [])
    c.eq("...nothing is pending", _dm.is_pending, False)
    _w2, _mc2, _dm2, _r2 = advance_rig(ork.GUNWAGON)
    _w2.shaken_until_turn = 99
    _mc2.start_run()
    c.eq("a 6 is a ROLL: Mont'ka's shaken -2 still lands on it (6 - 2 = 4)",
         round(_mc2.remaining_range[_w2.models[0].id] - _r2, 3), 4.0)
    _t, _mct, _dmt, _rt = advance_rig(ork.TRUKK)
    tk.script(2)
    _mct.start_run()
    c.eq("a Trukk is no WAGON: it rolls its die", [len(v) for _l, v in _dmt.rolled], [1])
    _obs_w = observation.advance_reach_in(tk.build(ork.BATTLEWAGON, ORK))
    _obs_t = observation.advance_reach_in(tk.build(ork.TRUKK, ORK))
    _mw = tk.build(ork.BATTLEWAGON, ORK).models[0].profile.movement_in
    c.eq("the AI's observation is told the 6 for a WAGON (M + 6)", round(_obs_w, 3), round(_mw + 6.0, 3))
    c.eq("...and the average for anyone else (M + 3.5)",
         round(_obs_t, 3), round(tk.build(ork.TRUKK, ORK).models[0].profile.movement_in + 3.5, 3))

with settings_as(**NO_BB):
    _w, _mc, _dm, _r0 = advance_rig(ork.BATTLEWAGON)
    tk.script(1)
    _mc.start_run()
    c.eq("WITHOUT Blitz Brigade the Battlewagon rolls", [len(v) for _l, v in _dm.rolled], [1])


# ===========================================================================
print("\n3. Unstoppable Momentum: the charge re-roll")
# ===========================================================================
def charge_scene(sheet, gap=9.0, auto=()):
    state = GameState()
    charger = place(tk.build(sheet, ORK, name="2 %s 1" % sheet.name), 20.0, 20.0)
    enemy = place(tk.build(necrons.NECRON_WARRIORS, FOE, name="1 Necron Warriors 1"), 20.0,
                  20.0 + gap + charger.models[0].radius_in)
    for s in (charger, enemy):
        for m in s.models:
            state.add_token(m)
    tt = turn_at(PHASE_CHARGE, ORK)
    log, dice, dec = tk.Log(), tk.RecordingDice(), DecisionManager()
    cc = ChargeController(game_log=log, dice_manager=dice, turn_tracker=tt, all_tokens=state.tokens)
    rc = bb.UnstoppableMomentumChargeRerollController(
        dice_manager=dice, decision_manager=dec, charge_controller=cc, game_log=log, auto_players=auto)
    return SimpleNamespace(state=state, charger=charger, enemy=enemy, cc=cc, rc=rc, dice=dice, dec=dec, log=log)


with settings_as(**BB):
    sc = charge_scene(ork.BATTLEWAGON, auto=(ORK,))
    tk.script(1, 2)
    sc.cc.declare_charge(sc.charger)
    c.true("the scene is a failed charge that a 12 would reach",
           not sc.cc.targets_reachable_with(3) and bool(sc.cc.targets_reachable_with(12)))
    c.true("the AI re-rolls the failed charge - free", sc.rc.maybe_offer_charge_reroll())
    c.eq("...in full", sc.dice.already_rerolled, {0, 1})
    c.true("...and the log names Unstoppable Momentum",
           any(bb.UNSTOPPABLE_MOMENTUM in line for line in sc.log.lines))
    sc = charge_scene(ork.BATTLEWAGON)
    tk.script(1, 2)
    sc.cc.declare_charge(sc.charger)
    c.true("a human is asked", sc.rc.maybe_offer_charge_reroll() and sc.dec.is_pending)
    sc = charge_scene(ork.TRUKK, auto=(ORK,))
    tk.script(1, 2)
    sc.cc.declare_charge(sc.charger)
    c.eq("a Trukk gets no re-roll", sc.rc.maybe_offer_charge_reroll(), False)

with settings_as(**NO_BB):
    sc = charge_scene(ork.BATTLEWAGON, auto=(ORK,))
    tk.script(1, 2)
    sc.cc.declare_charge(sc.charger)
    c.eq("WITHOUT Blitz Brigade no re-roll", sc.rc.maybe_offer_charge_reroll(), False)


# ===========================================================================
print("\n4. Targetin' Gizmos")
# ===========================================================================
c.true("a Gunwagon may take it", safe_grant(tk.build(ork.GUNWAGON, ORK), gizmos.TARGETIN_GIZMOS))
c.eq("...a Trukk may not (no WAGON)", safe_grant(tk.build(ork.TRUKK, ORK), gizmos.TARGETIN_GIZMOS), False)
c.eq("...nor a Big Mek (a WAGON unit only)",
     safe_grant(tk.build(ork.BIG_MEK_MEGA_ARMOUR, ORK), gizmos.TARGETIN_GIZMOS), False)


def gizmo_scene(passenger="bigmek", enh=True, provider=True):
    sc = tk.shooting_scene(ork.GUNWAGON, tau.STRIKE_TEAM, attacker_owner=ORK, gap=12.0)
    wagon, st = sc["attacker"], sc["state"]
    if enh:
        safe_grant(wagon, gizmos.TARGETIN_GIZMOS)
    if passenger == "bigmek":
        mob = attached_units.attach(tk.build(ork.BIG_MEK_MEGA_ARMOUR, ORK, name="2 Big Mek 1"),
                                    tk.build(ork.MEGANOBZ, ORK, name="2 Meganobz 1"))
        embark(st, mob, wagon)
    elif passenger == "meganobz":
        embark(st, tk.build(ork.MEGANOBZ, ORK, name="2 Meganobz 1"), wagon)
    shooter = sc["shooting"]
    if provider:
        shooter.embarked_squads_provider = lambda: st.embarked_squads
    shooter.active_squad = wagon
    gun = next(w for w in wagon.models[0].weapons if w.weapon_type == RANGED)
    return sc, wagon, shooter, gun


with settings_as(**BB):
    sc, wagon, shooter, gun = gizmo_scene()
    adj = shooter._adjusted_weapon([(wagon.models[0], gun)], sc["target"])
    c.true("with a Big Mek aboard: the Gunwagon's gun has [IGNORES COVER]", adj.ignores_cover)
    c.eq("...but no [SUSTAINED HITS 1] while not riled up", adj.sustained_hits, gun.sustained_hits)
    _real = shooter._has_benefit_of_cover
    shooter._has_benefit_of_cover = lambda shooter_model, target_squad: True
    try:
        mods = [m.source for m in shooter._hit_modifiers({"pairs": [(wagon.models[0], gun)],
                                                         "target_squad": sc["target"]})]
    finally:
        shooter._has_benefit_of_cover = _real
    c.eq("...and the COVER GATE sees it: no Benefit of Cover on the Hit roll", "Benefit of Cover" in mods, False)
    riled_up.grant(wagon, 99, None)
    c.eq("riled up: [SUSTAINED HITS 1] too",
         shooter._adjusted_weapon([(wagon.models[0], gun)], sc["target"]).sustained_hits, max(1, gun.sustained_hits))
    sc, wagon, shooter, gun = gizmo_scene(passenger="meganobz")
    c.eq("Meganobz without their Big Mek aboard: nothing (the model must be a BIG MEK)",
         shooter._adjusted_weapon([(wagon.models[0], gun)], sc["target"]).ignores_cover, bool(gun.ignores_cover))
    sc, wagon, shooter, gun = gizmo_scene(passenger=None)
    c.eq("nobody aboard: nothing", shooter._adjusted_weapon([(wagon.models[0], gun)], sc["target"]).ignores_cover,
         bool(gun.ignores_cover))
    sc, wagon, shooter, gun = gizmo_scene(enh=False)
    c.eq("a Big Mek aboard but no Enhancement: nothing",
         shooter._adjusted_weapon([(wagon.models[0], gun)], sc["target"]).ignores_cover, bool(gun.ignores_cover))
    sc, wagon, shooter, gun = gizmo_scene(provider=False)
    c.eq("a controller that is not told who is embarked under-reports (never over)",
         shooter._adjusted_weapon([(wagon.models[0], gun)], sc["target"]).ignores_cover, bool(gun.ignores_cover))
    sc, wagon, shooter, gun = gizmo_scene()
    for m in sc["state"].embarked_squads[0].models:
        if m.profile.character:
            m.current_wounds = 0
    c.eq("the Big Mek dead: nothing", shooter._adjusted_weapon([(wagon.models[0], gun)], sc["target"]).ignores_cover,
         bool(gun.ignores_cover))

with settings_as(**NO_BB):
    sc, wagon, shooter, gun = gizmo_scene()
    c.eq("WITHOUT Blitz Brigade: nothing", shooter._adjusted_weapon([(wagon.models[0], gun)], sc["target"]).ignores_cover,
         bool(gun.ignores_cover))


# ===========================================================================
print("\n5. Boss Boomer")
# ===========================================================================
def boomer_scene(boss_sheet=ork.WARBOSS, enh=True, aboard=True, phase=PHASE_MOVEMENT):
    st = GameState()
    wagon = place(tk.build(ork.BATTLEWAGON, ORK, name="2 Battlewagon 1"), 20.0, 20.0)
    if enh:
        safe_grant(wagon, enh_boss_boomer.BOSS_BOOMER)
    friend = place(tk.build(ork.BEAST_SNAGGA_BOYZ, ORK, name="2 Beast Snagga Boyz 1"), 20.0, 25.0)
    friend.battle_shocked = True
    for s in (wagon, friend):
        for m in s.models:
            st.add_token(m)
    boss = tk.build(boss_sheet, ORK, name="2 %s 1" % boss_sheet.name)
    if aboard:
        embark(st, boss, wagon)
    else:
        place(boss, 40.0, 40.0)
        for m in boss.models:
            st.add_token(m)
    tt = turn_at(phase, ORK)
    squads = [wagon, friend, boss]
    ctrls = dict(
        im=IntimidatingMotivationController(turn_tracker=tt, squads_provider=lambda: squads,
                                            all_tokens=st.tokens, game_log=tk.Log()),
        kh=KeepHuntinController(turn_tracker=tt, squads_provider=lambda: squads,
                                all_tokens=st.tokens, game_log=tk.Log()))
    return SimpleNamespace(state=st, wagon=wagon, friend=friend, boss=boss, tt=tt, **ctrls)


c.true("a Battlewagon may take it", safe_grant(tk.build(ork.BATTLEWAGON, ORK), enh_boss_boomer.BOSS_BOOMER))
c.eq("...a Warboss may not", safe_grant(tk.build(ork.WARBOSS, ORK), enh_boss_boomer.BOSS_BOOMER), False)

with settings_as(**BB):
    r = boomer_scene()
    c.true("a Warboss aboard: the WAGON has Intimidating Motivation", r.im.can_use(r.wagon))
    c.eq("...lent by that Warboss", [m.squad for m in r.im.bearer_models(r.wagon)], [r.boss])
    c.eq("...not Keep Huntin'! (he does not print it)", r.kh.can_use(r.wagon), False)
    c.true("...its targets are measured from the WAGON (the Boyz 5\" from it)",
           r.friend in r.im.candidates(r.wagon))
    c.true("used from the WAGON on them: un-shocked and riled up",
           r.im.apply(r.wagon, r.friend) and not r.friend.battle_shocked and riled_up.is_riled_up(r.friend))
    c.true("...spending the ability's once-per-round use", r.im.is_spent(ORK))
    r = boomer_scene(boss_sheet=ork.BEASTBOSS)
    c.true("a Beastboss aboard: Keep Huntin'!", r.kh.can_use(r.wagon))
    c.eq("...and not Intimidating Motivation", r.im.can_use(r.wagon), False)
    r = boomer_scene(boss_sheet=ork.GHAZGHKULL_THRAKA)
    c.eq("Ghazghkull aboard: a WARBOSS who prints neither lends nothing",
         (r.im.can_use(r.wagon), r.kh.can_use(r.wagon)), (False, False))
    # "that WARBOSS model's" ability: every built sheet that prints Intimidating
    # Motivation IS a WARBOSS, so the clause is measured on a stand-in - a Boy
    # whose own profile INSTANCE is given the ability.
    r = boomer_scene(boss_sheet=ork.BOYZ)
    r.boss.models[0].profile.intimidating_motivation = True
    c.eq("a model that is NOT a WARBOSS lends nothing, even printing the ability (stand-in)",
         r.im.can_use(r.wagon), False)
    r = boomer_scene(aboard=False)
    c.eq("the Warboss on the board, not aboard: nothing", r.im.can_use(r.wagon), False)
    r = boomer_scene(enh=False)
    c.eq("aboard, but no Enhancement: nothing", r.im.can_use(r.wagon), False)
    r = boomer_scene()
    r.boss.models[0].current_wounds = 0
    c.eq("the Warboss dead: nothing", r.im.can_use(r.wagon), False)

with settings_as(**NO_BB):
    r = boomer_scene()
    c.eq("WITHOUT Blitz Brigade: nothing", r.im.can_use(r.wagon), False)

# The real ActionPanel: the lent ability is DRAWN for the WAGON.
_panel = ActionPanel()
_labels = []
_real_button = ActionPanel._draw_button


def _spy(self, surface, rect, label, *a, **kw):
    _labels.append(label)
    return _real_button(self, surface, rect, label, *a, **kw)


ActionPanel._draw_button = _spy


def drawn_for(r, phase=PHASE_MOVEMENT):
    reg = ProactiveStratagems()
    reg.add(r.im)
    reg.add(r.kh)
    tracker = turn_at(phase, ORK)
    r.im.turn_tracker = r.kh.turn_tracker = tracker
    mover = MovementController([], tk.Log(), ORK, DiceManager(), tracker, r.state.tokens)
    shooter = ShootingController(obstacles=[], game_log=tk.Log(), player_name=ORK, dice_manager=DiceManager(),
                                 turn_tracker=tracker, all_tokens=r.state.tokens, decision_manager=DecisionManager())
    _labels.clear()
    mover.select(r.wagon.models[0])
    surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
    _panel.draw(surface, pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900), mover, shooter,
                dice_manager=DiceManager(), proactive_stratagems=reg)
    return [n for _r, n in _panel._stratagem_buttons], mover.selected_squad is r.wagon


with settings_as(**BB):
    _names, _live = drawn_for(boomer_scene())
    c.true("(live) the panel drew the WAGON's screen", _live)
    c.true("the real ActionPanel DRAWS Intimidating Motivation for the WAGON", "Intimidating Motivation" in _names)
    for _phase in (PHASE_SHOOTING, PHASE_CHARGE, PHASE_FIGHT):
        _n, _l = drawn_for(boomer_scene(), _phase)
        c.eq("...not in the %s phase" % _phase, "Intimidating Motivation" in _n, False)
    _names, _live = drawn_for(boomer_scene(enh=False))
    c.eq("...and not for a WAGON without Boss Boomer", "Intimidating Motivation" in _names, False)
with settings_as(**NO_BB):
    _names, _live = drawn_for(boomer_scene())
    c.eq("...nor without the detachment (the gate AT THE PANEL)", "Intimidating Motivation" in _names, False)
ActionPanel._draw_button = _real_button


# ===========================================================================
print("\n6. Keep It Runnin'")
# ===========================================================================
def kir_scene(gap=3.0, engaged=False, eligible=True, sheet=ork.BOYZ, carrier=ork.BATTLEWAGON,
              auto=(), cp=10, both=False):
    st = GameState()
    wagon = place(tk.build(carrier, ORK, name="2 %s 1" % carrier.name), 20.0, 20.0)
    mob = place(tk.build(sheet, ORK, name="2 %s 1" % sheet.name), 18.0,
                20.0 + wagon.models[0].radius_in + gap, spacing=1.0)
    squads = [wagon, mob]
    foe = None
    if engaged:
        foe = place(tk.build(tau.STRIKE_TEAM, FOE, name="1 Strike Team 1"), 18.0,
                    mob.models[-1].y_in + 1.5, spacing=1.0)
        squads.append(foe)
    for s in squads:
        for m in s.models:
            st.add_token(m)
    tt = turn_at(PHASE_FIGHT, ORK)
    mover = SimpleNamespace(moved_squad_ids=set())
    tc = TransportController(None, st, st.tokens, mover, None, None, game_log=tk.Log(), turn_tracker=tt)
    fc = FightController(all_tokens=st.tokens, turn_tracker=tt, game_log=tk.Log())
    if eligible:
        fc.engaged_at_start = {mob}
    dec = DecisionManager()
    sc = strat(cp)
    ctrl = kir.KeepItRunninController(sc, transport_controller=tc, fight_controller=fc, game_state=st,
                                      all_tokens=st.tokens, turn_tracker=tt, decision_manager=dec,
                                      game_log=tk.Log(), auto_players=auto)
    return SimpleNamespace(state=st, wagon=wagon, mob=mob, foe=foe, tc=tc, fc=fc, dec=dec, sc=sc, ctrl=ctrl,
                           squads={s for s in squads})


with settings_as(**BB):
    r = kir_scene()
    c.true("offered at the end of the Fight phase for an unengaged Boyz mob 3\" from a Battlewagon",
           r.ctrl.offer_at_end_of_fight_phase(r.squads) and r.dec.is_pending)
    c.true("...naming the mob", any(r.mob.name in o["label"] for o in r.dec.options))
    _cp = r.sc.command_points.cp[ORK]
    tk.pick_option(r.dec, r.mob.name)
    c.eq("picked (one transport, no second question): 1CP", _cp - r.sc.command_points.cp[ORK], 1)
    c.true("...and the mob is embarked within the Battlewagon", r.mob.embarked_in is r.wagon.models[0])
    c.true("...off the board", not any(m in r.state.tokens for m in r.mob.models))
    for _label, _kw in (("engaged", dict(engaged=True)), ("not eligible to fight this phase", dict(eligible=False)),
                        ("7\" away (not wholly within 6\")", dict(gap=7.0)),
                        ("with 0CP", dict(cp=0)),
                        ("Boyz next to a Kill Rig (it carries BEAST SNAGGA only)", dict(carrier=ork.KILL_RIG))):
        r = kir_scene(**_kw)
        c.eq("NOT offered: %s" % _label, r.ctrl.offer_at_end_of_fight_phase(r.squads), False)
    r = kir_scene(sheet=ork.BEAST_SNAGGA_BOYZ, carrier=ork.KILL_RIG)
    c.true("...while Beast Snagga Boyz may board a Kill Rig (its own ban is can_embark()'s)",
           r.ctrl.offer_at_end_of_fight_phase(r.squads))
    r = kir_scene(sheet=ork.DEFFKOPTAS)
    c.eq("NOT offered: Deffkoptas are no ORKS INFANTRY", r.ctrl.offer_at_end_of_fight_phase(r.squads), False)
    # Every Ork TRANSPORT bans non-INFANTRY itself, which would answer the line
    # above on its own. So the TARGET's own INFANTRY clause is measured against a
    # stand-in: this Battlewagon's profile INSTANCE loses its INFANTRY ban.
    r = kir_scene(sheet=ork.DEFFKOPTAS)
    r.wagon.models[0].profile.transport_requires_infantry = False
    c.true("(the stand-in Battlewagon would take the Deffkoptas)",
           bool(r.tc.can_embark(r.mob, r.wagon.models[0], require_move=False, range_in=6.0)))
    c.eq("...and Keep It Runnin' still refuses them - its own ORKS INFANTRY clause",
         r.ctrl.offer_at_end_of_fight_phase(r.squads), False)
    r = kir_scene(auto=(ORK,))
    c.eq("the AI is not asked and declines (named)", (r.ctrl.offer_at_end_of_fight_phase(r.squads), r.dec.is_pending),
         (False, False))
    r = kir_scene()
    r.ctrl.turn_tracker = turn_at(PHASE_MOVEMENT, FOE)
    c.true("\"End of THE Fight phase\": offered whoever's turn it was (no owner test)",
           r.ctrl.offer_at_end_of_fight_phase(r.squads))
    r = kir_scene()
    c.eq("without the offer's window it cannot be bought (no live phase test)", r.ctrl.can_use(r.mob), False)

with settings_as(**NO_BB):
    r = kir_scene()
    c.eq("WITHOUT Blitz Brigade: not offered", r.ctrl.offer_at_end_of_fight_phase(r.squads), False)


# ===========================================================================
print("\n7. Impending Krunch")
# ===========================================================================
def krunch_scene(owner_turn=ORK, phase=PHASE_CHARGE, carrier=ork.BATTLEWAGON, engaged=True, auto=(), cp=10,
                 shocked=False):
    st = GameState()
    wagon = place(tk.build(carrier, ORK, name="2 %s 1" % carrier.name), 20.0, 20.0)
    foe = place(tk.build(tau.STRIKE_TEAM, FOE, name="1 Strike Team 1"), 17.0,
                20.0 + wagon.models[0].radius_in + (1.2 if engaged else 8.0), spacing=1.0)
    foe2 = place(tk.build(tau.BREACHER_TEAM, FOE, name="1 Breacher Team 1"), 17.0,
                 20.0 - wagon.models[0].radius_in - (1.2 if engaged else 8.0) - 1.0, spacing=1.0)
    for s in (wagon, foe, foe2):
        for m in s.models:
            st.add_token(m)
    foe.battle_shocked = foe2.battle_shocked = shocked
    tt = turn_at(phase, owner_turn)
    dice = tk.RecordingDice()
    bsc = BattleShockController(game_log=tk.Log(), dice_manager=dice, turn_tracker=tt, all_tokens=st.tokens)
    dec = DecisionManager()
    sc = strat(cp)
    ctrl = krunch.ImpendingKrunchController(sc, battle_shock_controller=bsc, turn_tracker=tt,
                                            decision_manager=dec, all_tokens=st.tokens, game_log=tk.Log(),
                                            auto_players=auto)
    return SimpleNamespace(state=st, wagon=wagon, foe=foe, foe2=foe2, tt=tt, dice=dice, bsc=bsc, dec=dec, sc=sc,
                           ctrl=ctrl)


with settings_as(**BB):
    r = krunch_scene()
    c.eq("the premise: both enemy units are engaged with the Battlewagon",
         [s.name for s in r.ctrl.targets_for(r.wagon)], sorted([r.foe.name, r.foe2.name]))
    # Through a REAL ChargeController: confirm_charge_move() fires the hook.
    _cc = ChargeController(game_log=tk.Log(), dice_manager=DiceManager(), turn_tracker=r.tt, all_tokens=r.state.tokens)
    _cc.movement_controller = SimpleNamespace(confirm_move=lambda: None, errors=[])
    _cc.on_charge_move_finished.append(r.ctrl.on_charge_move_finished)
    _cc.active_squad, _cc.charge_targets, _cc.max_distance = r.wagon, [r.foe], 7
    _cc.confirm_charge_move()
    c.true("a real ChargeController's confirm_charge_move() raises the offer", r.dec.is_pending)
    c.true("...Use / Decline", [o["label"] for o in r.dec.options] == [krunch.USE_LABEL, krunch.DECLINE_LABEL])
    _cp = r.sc.command_points.cp[ORK]
    tk.script(1, 1, 1, 1)
    tk.pick_option(r.dec, krunch.USE_LABEL)
    c.eq("Use: 1CP", _cp - r.sc.command_points.cp[ORK], 1)
    c.true("...the first engaged unit tests at once, at -1",
           r.dice.rolled and "Impending Krunch" in r.dice.rolled[-1][0] and "-1" in r.dice.rolled[-1][0])
    r.dice.acknowledge()
    r.bsc.on_dice_acknowledged()
    r.ctrl.on_dice_acknowledged()
    c.eq("...the acknowledgement releases the second", len(r.dice.rolled), 2)
    r.dice.acknowledge()
    r.bsc.on_dice_acknowledged()
    r.ctrl.on_dice_acknowledged()
    c.true("...a 2 fails: both are battle-shocked", r.foe.battle_shocked and r.foe2.battle_shocked)
    c.eq("...and the queue is empty", r.ctrl.is_busy, False)
    c.eq("offered ONCE per charge move", r.ctrl.on_charge_move_finished(r.wagon), False)

    for _label, _kw in (("in the OPPONENT's Charge phase (a Heroic Intervention)", dict(owner_turn=FOE)),
                        ("outside the Charge phase", dict(phase=PHASE_FIGHT)),
                        ("for a Trukk (no WAGON)", dict(carrier=ork.TRUKK)),
                        ("when the charge engaged nothing", dict(engaged=False)),
                        ("with 0CP", dict(cp=0))):
        r = krunch_scene(**_kw)
        c.eq("NOT offered: %s" % _label, r.ctrl.on_charge_move_finished(r.wagon), False)
    r = krunch_scene()
    c.true("offered again for a fresh charge", r.ctrl.on_charge_move_finished(r.wagon))
    tk.pick_option(r.dec, krunch.DECLINE_LABEL)
    c.eq("Decline costs nothing", r.sc.command_points.cp[ORK], 10)
    # After a Decline nothing else refuses (no CP spent, 15.01 untouched), so
    # this is where "asked once per charge move" is measurable.
    c.eq("...and the same charge move is not asked about twice", r.ctrl.on_charge_move_finished(r.wagon), False)

    r = krunch_scene(auto=(ORK,))
    tk.script(1, 1, 1, 1)
    c.true("the AI buys it when an engaged enemy is not yet shocked", r.ctrl.on_charge_move_finished(r.wagon))
    c.eq("...without a prompt", r.dec.is_pending, False)
    r = krunch_scene(auto=(ORK,), shocked=True)
    c.eq("...and not when every engaged enemy is already shocked (a pass would CURE them)",
         r.ctrl.on_charge_move_finished(r.wagon), False)

with settings_as(**NO_BB):
    r = krunch_scene()
    c.eq("WITHOUT Blitz Brigade: not offered", r.ctrl.on_charge_move_finished(r.wagon), False)


# ===========================================================================
print("\n8. Readied Brawlers is NOT wired - the named gap")
# ===========================================================================
c.true("the corpus prints it", "### READIED BRAWLERS - 1CP" in _md)
c.true("...its EFFECT is the 'assault disembark move'", "**assault disembark move**" in _md)
c.eq("game/blitz_brigade.py names it as NOT wired, with the user's decision",
     sorted(bb.NOT_WIRED), ["Readied Brawlers"])
_why = bb.NOT_WIRED.get("Readied Brawlers") or ""
c.true("...the reason names the missing move type and the user decision",
       "assault disembark move" in _why and "user decision" in _why)
_mentions = sorted(f for f in os.listdir(os.path.join(ROOT, "game")) if f.endswith(".py")
                   and "Readied Brawlers" in read(os.path.join("game", f)))
c.eq("no engine module but the detachment rule mentions it (no half-built controller)", _mentions, ["blitz_brigade.py"])
c.eq("...and no module or main.py builds an 'assault disembark'",
     [f for f in os.listdir(os.path.join(ROOT, "game")) if f.endswith(".py")
      and "assault_disembark" in read(os.path.join("game", f))] + (["main.py"] if "assault_disembark" in read("main.py") else []),
     [])


# ===========================================================================
print("\n9. the extractions")
# ===========================================================================
c.true("Skyborne Sanctuary and Keep It Runnin' are the same mechanism",
       issubclass(skyborne_sanctuary.SkyborneSanctuaryController, end_of_fight_embark.EndOfFightEmbarkController)
       and issubclass(kir.KeepItRunninController, end_of_fight_embark.EndOfFightEmbarkController))
c.eq("...differing in their knobs", (kir.KeepItRunninController.NAME, kir.KeepItRunninController.RANGE_IN,
                                     skyborne_sanctuary.SkyborneSanctuaryController.NAME),
     ("Keep It Runnin'", 6.0, "Skyborne Sanctuary"))
try:
    end_of_fight_embark.EndOfFightEmbarkController(strat())
    _nameless = False
except TypeError:
    _nameless = True
c.true("...the base class refuses to be built nameless", _nameless)
c.true("Mobbed and Impending Krunch share game/forced_shock_queue.py",
       isinstance(mobbed.MobbedController().queue, forced_shock_queue.ForcedShockQueue)
       and isinstance(krunch.ImpendingKrunchController(strat()).queue, forced_shock_queue.ForcedShockQueue))
from game import green_tide, war_horde  # noqa: E402
c.true("game/ork_units.py answers ORKS / ORKS INFANTRY for all three detachments",
       war_horde.is_orks_unit is ork_units.is_orks_unit and green_tide.is_orks_unit is ork_units.is_orks_unit
       and green_tide.is_orks_infantry_unit is ork_units.is_orks_infantry_unit)
_q = forced_shock_queue.ForcedShockQueue(None)
_t = tk.build(ork.BOYZ, FOE)
c.eq("the queue refuses a unit already waiting", (_q.enqueue(_t, 1, "x"), _q.enqueue(_t, 1, "x")), (True, False))


# ===========================================================================
print("\n10. wiring at the source")
# ===========================================================================
MAIN = read("main.py")
TREE = ast.parse(MAIN)


def calls(text):
    return [n for n in ast.walk(TREE) if isinstance(n, ast.Call) and ast.unparse(n) == text]


c.eq("main.py asks Unstoppable Momentum's charge re-roll at the acknowledgement",
     len(calls("unstoppable_momentum_controller.maybe_offer_charge_reroll()")), 1)
c.true("...after the other two carriers",
       MAIN.find("phaeron_blades_controller.maybe_offer_charge_reroll()")
       < MAIN.find("unstoppable_momentum_controller.maybe_offer_charge_reroll()"))
c.true("...and puts it on the dice panel's roll choices",
       "        unstoppable_momentum_controller,\n" in MAIN)
c.true("hands the ShootingController the embarked units",
       "shooting_controller.embarked_squads_provider = lambda: state.embarked_squads" in MAIN)
c.eq("appends Impending Krunch to the charge-end hook",
     len(calls("charge_controller.on_charge_move_finished.append(impending_krunch_controller.on_charge_move_finished)")), 1)
c.eq("...and releases its queue on every acknowledgement",
     len(calls("impending_krunch_controller.on_dice_acknowledged()")), 1)
c.eq("resets Keep It Runnin's window and offers it at the end of the Fight phase",
     (len(calls("keep_it_runnin_controller.reset_phase()")),
      len([n for n in ast.walk(TREE) if isinstance(n, ast.Call)
           and ast.unparse(n.func) == "keep_it_runnin_controller.offer_at_end_of_fight_phase"])), (1, 1))
_mv = read(os.path.join("game", "movement.py"))
c.true("MovementController.start_run() asks Unstoppable Momentum", "blitz_brigade.advance_roll_is_fixed(self.selected_squad)" in _mv)
c.true("More Dakka's grant asks Targetin' Gizmos", "enh_targetin_gizmos.applies(squad, embarked_squads)"
       in read(os.path.join("game", "more_dakka.py")))
c.true("Boss Motivation's bearers ask Boss Boomer", "enh_boss_boomer.lent_models(squad, self._squads(), self.FLAG)"
       in read(os.path.join("game", "boss_motivation.py")))

c.finish()
