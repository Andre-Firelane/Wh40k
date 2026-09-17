"""Ork vehicles (2026-09 codex, stage E3d): Warbikers, Deffkoptas, Trukk,
Battlewagon and Deff Dread - the datasheets, their transport rules and every
engine-wired ability, driven through the real controllers.

  1. the five datasheets: points tiers, keyword lines against the corpus, the
     base sizes (with the two named deviations), profile flags
  2. multi-profile weapons and the wargear menus, with the named limitations
  3. transport: the Trukk's and the Battlewagon's printed capacity lines, at
     18.01 (Declare Battle Formations) AND 18.02 (mid-battle)
  4. High-speed Carnage through FightController's adjuster chain
  5. Deff from Above through ShootingController's hit modifiers
  6. Dread 'Ard and Mobile Fortress through a real DamageAllocationSession, and
     Damaged 6
  7. Aerial Manoover at the end-of-opponent's-Fight-phase seam
  8. Pilin' Out: the three triggers, the passenger queue behind a REAL
     disembark placement, the per-phase decline memo, the AI path
  9. the AI's two deterministic policies
 10. wiring at the source and the retirements

Run: python test_ork_vehicles.py

Built on testkit.py (see its docstring for the headless-harness traps).
"""

import ast
import io
import math
import os
import re
from types import SimpleNamespace

import testkit as tk
from testkit import DecisionManager, DiceManager, GameState, TurnTracker, build, line_up, script

from ai import agent_driver
from game import aerial_manoover, deff_from_above, formations, high_speed_carnage, maps, pilin_out
from game import strategic_reserves
from game.damage_resolution import DamageAllocationSession
from game.factions import orks
from game.factions.necrons import NECRON_WARRIORS
from game.factions.tau_empire import STRIKE_TEAM
from game.modifiers import describe_modifiers
from game.movement import MovementController
from game.setup import PLACING, SetupController
from game.shooting import _damaged_modifier
from game.transport import COMBAT, RAPID, TransportController
from game.turn import PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASES
from game.weapons import MELEE, RANGED, WeaponProfile
from game import weapon_profiles

ROOT = os.path.dirname(os.path.abspath(__file__))
ORK, FOE = "Player 1", "Player 2"
MAP = maps.get("map2")
maps.apply_to_config(MAP)

c = tk.Checks("Ork vehicles (2026-09 codex)")


def read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8").read()


def corpus_keywords(sheet_name):
    text = read(os.path.join("rules", "orks", sheet_name + ".md"))
    match = re.search(r"^KEYWORDS: (.+)$", text, re.MULTILINE)
    return tuple(k.strip() for k in match.group(1).split(";")) if match else None


def weapons_of(model):
    return sorted(w.name for w in model.weapons)


def weapon_named(model, needle):
    return next((w for w in model.weapons if needle.lower() in w.name.lower()), None)


def tracker(phase, owner, battle_round=2):
    tt = TurnTracker()
    tt.started = True
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = owner
    tt.set_active(owner)
    tt.battle_round = battle_round
    return tt


# ===========================================================================
print("\n1. the five datasheets")
# ===========================================================================
SHEETS = {
    "Warbikers": orks.WARBIKERS, "Deffkoptas": orks.DEFFKOPTAS, "Trukk": orks.TRUKK,
    "Battlewagon": orks.BATTLEWAGON, "Deff Dread": orks.DEFF_DREAD,
}
for name, sheet in SHEETS.items():
    c.eq("%s's KEYWORDS match the printed line" % name, tuple(sheet.keywords), corpus_keywords(name))

POINTS = [
    ("Warbikers x3", orks.WARBIKERS, 0, 1, 75), ("Warbikers x6", orks.WARBIKERS, 1, 1, 140),
    ("...a 5th unit costs the same (one tier)", orks.WARBIKERS, 0, 5, 75),
    ("Deffkoptas x3", orks.DEFFKOPTAS, 0, 1, 80), ("Deffkoptas x6", orks.DEFFKOPTAS, 1, 2, 160),
    ("...3rd unit of 3", orks.DEFFKOPTAS, 0, 3, 90), ("...3rd unit of 6", orks.DEFFKOPTAS, 1, 3, 170),
    ("Trukk", orks.TRUKK, 0, 3, 60), ("...4th Trukk", orks.TRUKK, 0, 4, 70),
    ("Battlewagon", orks.BATTLEWAGON, 0, 2, 150), ("...3rd Battlewagon", orks.BATTLEWAGON, 0, 3, 160),
    ("Deff Dread", orks.DEFF_DREAD, 0, 2, 130), ("...3rd Deff Dread", orks.DEFF_DREAD, 0, 3, 140),
]
for label, sheet, comp, unit_index, want in POINTS:
    c.eq("points: " + label, sheet.points_for(composition_index=comp, unit_index=unit_index), want)

bikes = build(orks.WARBIKERS, ORK, name="1 Warbikers 1")
koptas = build(orks.DEFFKOPTAS, ORK, name="1 Deffkoptas 1")
trukk = build(orks.TRUKK, ORK, name="1 Trukk 1")
wagon = build(orks.BATTLEWAGON, ORK, name="1 Battlewagon 1")
dread = build(orks.DEFF_DREAD, ORK, name="1 Deff Dread 1")

c.eq("Warbikers: 1 Biker Nob + 2 Warbikers", [m.profile.name for m in bikes.models],
     ["Biker Nob", "Warbiker", "Warbiker"])
c.eq("...the Biker Nob alone has W4 and a 6+ invulnerable save",
     [(m.profile.wounds, m.profile.invulnerable_save) for m in bikes.models],
     [(4, "6+"), (3, "-"), (3, "-")])
c.eq("...and is the unit's leader model", [m.profile.squad_leader for m in bikes.models], [True, False, False])
c.true("Deffkoptas are NO LONGER a VEHICLE (MOUNTED since the codex)",
       not koptas.models[0].profile.vehicle and koptas.models[0].profile.mounted)
c.eq("...FLY and Deep Strike", (koptas.models[0].profile.fly, koptas.models[0].profile.deep_strike), (True, True))

# Bases. The two 75x42mm ovals keep the bikes' 0.98" - a NAMED DEVIATION: the
# oval's equal-area circle is ~1.10".
_oval = math.sqrt(75 * 42) / 2 / 25.4
c.true("the printed 75x42mm oval's equal-area radius is ~1.10\"", abs(_oval - 1.10) < 0.01)
c.eq("Warbikers and Deffkoptas stay on 0.98\" (named deviation)",
     (bikes.models[0].profile.base_radius_in, koptas.models[0].profile.base_radius_in), (0.98, 0.98))
c.eq("the Deff Dread's printed 60mm", round(dread.models[0].profile.base_radius_in, 2), round(30 / 25.4, 2))
c.eq("Trukk and Battlewagon print 'Use model' - table-size decisions",
     (trukk.models[0].profile.base_radius_in, wagon.models[0].profile.base_radius_in), (1.4, 2.1))

_w = wagon.models[0].profile
c.eq("Battlewagon: T11 Sv3+ W16 OC5, Damaged 6, Firing Deck 11",
     (_w.toughness, _w.armor_save, _w.wounds, _w.oc, _w.damaged_threshold, _w.firing_deck),
     (11, "3+", 16, 5, 6, 11))
c.true("...Deadly Demise D6 is a real roll", _w.deadly_demise_notation is not None)
c.eq("...Mobile Fortress is the RANGED-only reduction", (_w.ranged_damage_reduction, _w.damage_reduction), (1, 0))
_d = dread.models[0].profile
c.eq("Deff Dread: M8 T9 Sv2+ W8 OC3, WALKER, Deadly Demise 1, Dread 'Ard -1 D",
     (_d.movement_in, _d.toughness, _d.armor_save, _d.wounds, _d.oc, _d.walker, _d.deadly_demise, _d.damage_reduction),
     (8, 9, "2+", 8, 3, True, 1, 1))
_t = trukk.models[0].profile
c.eq("Trukk: M12 T8 Sv4+ W10, Firing Deck 12, Pilin' Out",
     (_t.movement_in, _t.toughness, _t.armor_save, _t.wounds, _t.firing_deck, _t.pilin_out), (12, 8, "4+", 10, 12, True))
c.true("...Deadly Demise D3 is a real roll", _t.deadly_demise_notation is not None)


# ===========================================================================
print("\n2. weapons and wargear")
# ===========================================================================
nob = bikes.models[0]
kombi = weapon_named(nob, "Kombi-rokkit")
c.eq("the Biker Nob's Dual Kombi-rokkit is a two-profile weapon",
     [p.name for p in weapon_profiles.profiles(kombi)],
     ["Dual Kombi-rokkit - Dakkagun", "Dual Kombi-rokkit - Busta Rokkit"])
c.true("...both profiles [ASSAULT]", all(p.assault for p in weapon_profiles.profiles(kombi)))
_rokkit = weapon_named(koptas.models[0], "Rokkit Launcha")
c.eq("a Deffkopta's Rokkit Launcha: Blasta -> Busta",
     [(p.name, p.strength, bool(p.lethal_hits)) for p in weapon_profiles.profiles(_rokkit)],
     [("Rokkit Launcha - Blasta", 4, False), ("Rokkit Launcha - Busta", 10, True)])
_dread_rokkit = build(orks.DEFF_DREAD, ORK, name="dr", choices={"Deff Dread": {
    orks.DEFF_DREAD_BIG_SHOOTA_TO_ROKKIT_LAUNCHA: 1}}).models[0]
c.eq("...while the Deff Dread's Busta prints no [LETHAL HITS]",
     [bool(p.lethal_hits) for p in weapon_profiles.profiles(weapon_named(_dread_rokkit, "Rokkit"))],
     [False, False])
c.eq("the Deffkopta Choppa overrides WS to the printed 4+ (the model carries 3+)",
     (weapon_named(koptas.models[0], "Choppa").weapon_skill, koptas.models[0].profile.weapon_skill), ("4+", "3+"))

c.eq("Deffkoptas: one Kustom Mega-blasta per 3 models",
     [sum(1 for m in build(orks.DEFFKOPTAS, ORK, name="k%d" % comp, composition_index=comp,
                           choices={"Deffkopta": {orks.DEFFKOPTAS_KUSTOM_MEGA_BLASTA: 6}}).models
          if weapon_named(m, "Kustom Mega-blasta")) for comp in (0, 1)], [1, 2])

_t2 = build(orks.TRUKK, ORK, name="t2", choices={"Trukk": {
    orks.TRUKK_DUAL_BIG_SHOOTA_TO_ROKKIT_LAUNCHA: 1, orks.TRUKK_ADD_BUZZSAW: 1}}).models[0]
c.eq("Trukk: Rokkit Launcha for the Dual Big Shoota, a Buzzsaw beside the Spiked Ram",
     weapons_of(_t2), ["Buzzsaw", "Rokkit Launcha - Blasta", "Spiked Ram"])
_t3 = build(orks.TRUKK, ORK, name="t3", choices={"Trukk": {
    orks.TRUKK_ADD_BUZZSAW: 1, orks.TRUKK_ADD_GRABBIN_KLAW: 1}}).models[0]
c.eq("KNOWN LIMITATION: 'one of' the two additions is not exclusive",
     weapons_of(_t3), ["Buzzsaw", "Dual Big Shoota", "Grabbin' Klaw", "Spiked Ram"])

_d2 = build(orks.DEFF_DREAD, ORK, name="d2", choices={"Deff Dread": {
    orks.DEFF_DREAD_BIG_SHOOTA_TO_EXTRA_KLAW: 1, orks.DEFF_DREAD_SKORCHA_TO_BIG_SHOOTA: 1}}).models[0]
c.eq("Deff Dread: both swaps at once, the Big Shoota swap applied first",
     weapons_of(_d2), ["Big Shoota", "Dread Klaws", "Extra Klaw"])
_w2 = build(orks.BATTLEWAGON, ORK, name="w2", choices={"Battlewagon": {
    orks.BATTLEWAGON_ADD_BIG_SHOOTAS: 1, orks.BATTLEWAGON_ADD_WRECKIN_BALL: 1, orks.BATTLEWAGON_ADD_GRABBIN_KLAW: 1}})
c.eq("Battlewagon: all three additions beside the Crushin' Bulk",
     weapons_of(_w2.models[0]), ["Big Shoota"] * 4 + ["Crushin' Bulk", "Grabbin' Klaw", "Wreckin' Ball"])
c.eq("...and every one of them free", _w2.points, 150)
c.true("KNOWN LIMITATION: 'up to 4 Big Shoota' is offered as the four at once",
       orks.BATTLEWAGON_ADD_BIG_SHOOTAS == "+ 4x Big Shoota")


# ===========================================================================
print("\n3. transport")
# ===========================================================================
def fits(passenger, transport_squad, **kw):
    """(18.01 errors, 18.02 answer) for `passenger` boarding `transport_squad`."""
    st = GameState()
    token = transport_squad.models[0]
    token.x_in, token.y_in = 20.0, 20.0
    spacing = 0.6
    line_up(passenger, x=20.0 - (len(passenger.models) - 1) * spacing / 2.0, y=21.0, spacing=spacing)
    for sq in (transport_squad, passenger):
        for m in sq.models:
            st.add_token(m)
    mc = MovementController(all_tokens=st.tokens)
    mc.moved_squad_ids.add(passenger)
    tc = TransportController(None, st, st.tokens, mc, None, None)
    return formations.embark_errors(passenger, token), tc.can_embark(passenger, token)


_boyz10 = lambda n: build(orks.BOYZ, ORK, name=n)
c.eq("a Trukk takes 10 Boyz, at 18.01 and at 18.02", fits(_boyz10("b1"), build(orks.TRUKK, ORK, name="T1")), ([], True))
_errs, _ok = fits(build(orks.STORMBOYZ, ORK, name="s1"), build(orks.TRUKK, ORK, name="T2"))
c.true("...refuses JUMP PACK Stormboyz at both", bool(_errs) and not _ok)
_errs, _ok = fits(build(STRIKE_TEAM, ORK, name="st"), build(orks.TRUKK, ORK, name="T3"))
c.true("...refuses a non-ORKS INFANTRY unit at both", bool(_errs) and not _ok)
c.eq("...takes 6 Meganobz (MEGA ARMOUR 2 each = 12)",
     fits(build(orks.MEGANOBZ, ORK, name="m6", composition_index=3), build(orks.TRUKK, ORK, name="T4")), ([], True))
_errs, _ok = fits(build(orks.WARBIKERS, ORK, name="wb"), build(orks.TRUKK, ORK, name="T5"))
c.true("...and refuses MOUNTED Warbikers (not INFANTRY)", bool(_errs) and not _ok)
c.eq("a Battlewagon takes 10 JUMP PACK Stormboyz (20 of 22)",
     fits(build(orks.STORMBOYZ, ORK, name="s2", composition_index=1), build(orks.BATTLEWAGON, ORK, name="W1")), ([], True))
_errs, _ok = fits(build(STRIKE_TEAM, ORK, name="st2"), build(orks.BATTLEWAGON, ORK, name="W2"))
c.true("...and refuses a non-ORKS unit", bool(_errs) and not _ok)


# ===========================================================================
print("\n4. High-speed Carnage (Warbikers)")
# ===========================================================================
S = tk.fight_scene(orks.WARBIKERS, NECRON_WARRIORS, attacker_owner=ORK)
A, FC = S["attacker"], S["fight"]
FC.fighting_squad = A
_choppa_pairs = [(m, weapon_named(m, "Choppa")) for m in A.models if m.profile.name == "Warbiker"]
_nob_pairs = [(A.models[0], weapon_named(A.models[0], "Kustom Choppa"))]
c.eq("(live) not charged: the Choppa is S5 D1", (FC._adjusted_weapon(_choppa_pairs).strength,
                                                 FC._adjusted_weapon(_choppa_pairs).damage), (5, 1))
A.charged_this_turn = True
c.eq("charged: +1 S and +1 D through FightController's chain",
     (FC._adjusted_weapon(_choppa_pairs).strength, FC._adjusted_weapon(_choppa_pairs).damage), (6, 2))
c.eq("...the Biker Nob's Kustom Choppa too (S5 D2 -> S6 D3)",
     (FC._adjusted_weapon(_nob_pairs).strength, FC._adjusted_weapon(_nob_pairs).damage), (6, 3))
c.eq("...the shared instance is never mutated", (_choppa_pairs[0][1].strength, _choppa_pairs[0][1].damage), (5, 1))
_kombi = weapon_named(A.models[0], "Kombi")
c.true("a RANGED weapon is untouched", high_speed_carnage.adjusted_weapon(_kombi, A) is _kombi)


class _NotatedBlade(WeaponProfile):
    name = "Notated Blade"
    weapon_type = MELEE
    strength = 5
    damage = 3


from game.dice_notation import D3  # noqa: E402
_nb = _NotatedBlade()
_nb.damage_notation = D3()
c.eq("a dice-notation Damage takes the +1 on its bonus (D3 -> D3+1)",
     high_speed_carnage.adjusted_weapon(_nb, A).damage_notation.bonus, 1)
S2 = tk.fight_scene(orks.DEFFKOPTAS, NECRON_WARRIORS, attacker_owner=ORK)
S2["attacker"].charged_this_turn = True
S2["fight"].fighting_squad = S2["attacker"]
_kp = [(m, weapon_named(m, "Spinnin")) for m in S2["attacker"].models]
c.eq("a unit without the ability that charged is unchanged", S2["fight"]._adjusted_weapon(_kp).strength, 5)


# ===========================================================================
print("\n5. Deff from Above (Deffkoptas)")
# ===========================================================================
S = tk.shooting_scene(orks.DEFFKOPTAS, STRIKE_TEAM, attacker_owner=ORK, gap=12.0)
A, SC = S["attacker"], S["shooting"]
SC.active_squad = A
_group = {"pairs": [(m, weapon_named(m, "Rokkit")) for m in A.models], "target_squad": S["target"]}


def dfa_in(shooting):
    return "Deff from Above" in describe_modifiers(shooting._hit_modifiers(_group))


SC.ingress_controller = SimpleNamespace(ingressed_this_turn=set())
c.true("(live) not ingressed: no bonus", not dfa_in(SC))
SC.ingress_controller.ingressed_this_turn.add(A)
c.true("ingressed this turn: +1 to hit (-1 on the threshold)", dfa_in(SC))
c.eq("...as a -1 Modifier", [m.amount for m in SC._hit_modifiers(_group) if m.source == "Deff from Above"], [-1])
SC._reactive = True
c.true("...but not in a reactive shot (\"In YOUR Shooting phase\")", not dfa_in(SC))
SC._reactive = False
SC.ingress_controller = None
c.true("no ingress controller at all answers nothing", not dfa_in(SC))
_bk = build(orks.WARBIKERS, ORK, name="bk")
c.true("a unit without the ability that ingressed gets nothing",
       not deff_from_above.applies(_bk, SimpleNamespace(ingressed_this_turn={_bk})))
c.true("\"made an ingress move this turn\" is IngressController.ingressed_this_turn, written on confirm",
       "self.ingressed_this_turn.add(squad)" in read("game/ingress.py"))


# ===========================================================================
print("\n6. Dread 'Ard, Mobile Fortress, Damaged 6")
# ===========================================================================
class _Gun(WeaponProfile):
    name = "Test Gun"
    weapon_type = RANGED
    range_in = 24
    strength = 12
    ap = -4
    damage = 3


class _Axe(_Gun):
    name = "Test Axe"
    weapon_type = MELEE


def landed(squad, weapon, rolls=(1,)):
    model = squad.models[0]
    before = model.current_wounds
    session = DamageAllocationSession(list(rolls), weapon, squad)
    while session.pending_choice is not None:
        session.choose_model(session.pending_choice[0])
    return before - model.current_wounds


c.eq("Battlewagon: a ranged D3 attack lands 2 (Mobile Fortress)", landed(build(orks.BATTLEWAGON, ORK, name="b1"), _Gun()), 2)
c.eq("...a MELEE D3 attack lands all 3", landed(build(orks.BATTLEWAGON, ORK, name="b2"), _Axe()), 3)
c.eq("Deff Dread: a ranged D3 attack lands 2 (Dread 'Ard)", landed(build(orks.DEFF_DREAD, ORK, name="d1"), _Gun()), 2)
c.eq("...and a melee one too - 'Attacks that target this unit'", landed(build(orks.DEFF_DREAD, ORK, name="d2x"), _Axe()), 2)
_one = _Gun()
_one.damage = 1
c.eq("a Damage 1 attack is never reduced below 1", landed(build(orks.DEFF_DREAD, ORK, name="d3"), _one), 1)
c.eq("a Trukk has no reduction", landed(build(orks.TRUKK, ORK, name="tt"), _Gun()), 3)
_logged = []
_s = DamageAllocationSession([1], _Gun(), build(orks.BATTLEWAGON, ORK, name="b3"), log=_logged.append)
c.true("the log names the printed ability", any("Mobile Fortress" in line for line in _logged))

_bw = build(orks.BATTLEWAGON, ORK, name="dam").models[0]
_bw.current_wounds = 7
c.eq("Damaged 6: nothing at 7 wounds", _damaged_modifier(_bw), [])
_bw.current_wounds = 6
c.eq("...-1 to hit at 6", [(m.amount, m.source) for m in _damaged_modifier(_bw)], [(1, "Damaged")])


# ===========================================================================
print("\n7. Aerial Manoover (Deffkoptas)")
# ===========================================================================
def am_scene(auto=(), choose=None, battle_round=2, foe_gap=20.0, second=False):
    st = GameState()
    tt = tracker(PHASE_COMMAND, ORK, battle_round=battle_round)
    kop = line_up(build(orks.DEFFKOPTAS, ORK, name="1 Deffkoptas 1"), y=10.0)
    squads = [kop]
    if second:
        squads.append(line_up(build(orks.DEFFKOPTAS, ORK, name="1 Deffkoptas 2"), y=4.0))
    foe = line_up(build(STRIKE_TEAM, FOE, name="2 Strike Team 1"), y=10.0 + foe_gap)
    for sq in squads + [foe]:
        for m in sq.models:
            st.add_token(m)
    dm, log = DecisionManager(), tk.Log()
    ctrl = aerial_manoover.AerialManooverController(decision_manager=dm, game_state=st, game_log=log,
                                                    turn_tracker=tt, auto_players=auto, choose=choose)
    return SimpleNamespace(st=st, tt=tt, kop=kop, squads=squads, foe=foe, dm=dm, log=log, ctrl=ctrl)


def all_squads(sc):
    return {t.squad for t in sc.st.tokens if t.squad is not None}


E = am_scene()
c.true("offered at the end of the OPPONENT's Fight phase", E.ctrl.offer_at_end_of_fight_phase(all_squads(E), FOE))
c.eq("...one prompt for the unit", (E.dm.is_pending, E.dm.player), (True, ORK))
c.eq("...with the two answers", [o["label"] for o in E.dm.options or []], ["Go into Strategic Reserves", "Stay on the battlefield"])
E.dm.choose(0)
c.true("answered yes: in Strategic Reserves", E.kop in E.st.reserves and not any(m in E.st.tokens for m in E.kop.models))
c.true("...and logged under its printed name", E.log.has("uses Aerial Manoover"))

E = am_scene()
c.true("not at the end of its OWN Fight phase", not E.ctrl.offer_at_end_of_fight_phase(all_squads(E), ORK))
E = am_scene(foe_gap=1.2)
c.true("not while engaged (03.04)", not E.ctrl.can_use(E.kop))
for _m in E.foe.models:
    _m.current_wounds = 0
c.true("...but a unit engaged only with the dead is unengaged", E.ctrl.can_use(E.kop))
E = am_scene(battle_round=4)
E.tt.turn_index_in_round = 0
c.true("never when rule 20.03 would destroy it in the same call", not E.ctrl.can_use(E.kop))
E.tt.turn_index_in_round = 1
c.true("...the round-4 turn it CAN come back from is fine", E.ctrl.can_use(E.kop))
E.tt.battle_over = True
c.true("...and never after the battle's last turn", not E.ctrl.can_use(E.kop))
E = am_scene(second=True)
E.ctrl.offer_at_end_of_fight_phase(all_squads(E), FOE)
c.eq("two units: one prompt at a time", len(E.dm._queue), 1)
E.dm.choose(1)
c.true("...the decline asks the next", E.dm.is_pending and "Deffkoptas 2" in E.dm.prompt)
_seen = []
E = am_scene(auto=(ORK,), choose=lambda eligible: (_seen.append([s.name for s in eligible]) or eligible[:1]))
E.ctrl.offer_at_end_of_fight_phase(all_squads(E), FOE)
c.eq("the AI gets the eligible units and no prompt", (_seen, E.dm.is_pending), ([["1 Deffkoptas 1"]], False))
c.true("...and what it picks is withdrawn", E.kop in E.st.reserves)
E = am_scene(auto=(ORK,), choose=lambda eligible: [])
E.ctrl.offer_at_end_of_fight_phase(all_squads(E), FOE)
c.true("...an empty pick withdraws nothing", E.kop not in E.st.reserves)


# ===========================================================================
print("\n8. Pilin' Out (Trukk)")
# ===========================================================================
def po_scene(auto=(), choose=None, phase=PHASE_MOVEMENT, turn_owner=FOE, foe_y=None, painboy=True):
    st = GameState()
    tt = tracker(phase, turn_owner)
    trk = build(orks.TRUKK, ORK, name="1 Trukk 1")
    token = trk.models[0]
    token.x_in, token.y_in = 30.0, 22.0
    st.add_token(token)
    boyz = build(orks.BOYZ, ORK, name="1 Boyz 1")
    passengers = [boyz]
    if painboy:
        passengers.append(build(orks.PAINBOY, ORK, name="1 Painboy 1"))
    for p in passengers:
        p.embarked_in = token
        st.embarked_squads.append(p)
    foe = build(STRIKE_TEAM, FOE, name="2 Strike Team 1")
    # 30.0/22.0 with the Trukk's 1.4" hull; a Strike Team model's 0.63" base.
    line_up(foe, x=28.0, y=foe_y if foe_y is not None else 30.0)
    for m in foe.models:
        st.add_token(m)
    setup = SetupController(st, obstacles=[], all_tokens=st.tokens,
                            board_width_in=MAP.width_in, board_height_in=MAP.height_in)
    mc = MovementController([], tk.Log(), turn_owner, DiceManager(), tt, st.tokens)
    dice = DiceManager()
    tc = TransportController(setup, st, st.tokens, mc, None, dice, turn_tracker=tt,
                             board_width_in=MAP.width_in, board_height_in=MAP.height_in)
    dm, log = DecisionManager(), tk.Log()
    ctrl = pilin_out.PilinOutController(tc, game_state=st, turn_tracker=tt, decision_manager=dm,
                                        game_log=log, auto_players=auto, choose=choose)
    tc.on_disembark_resolved.append(ctrl.on_disembark_resolved)
    return SimpleNamespace(st=st, tt=tt, trk=trk, token=token, boyz=boyz, passengers=passengers, foe=foe,
                           setup=setup, mc=mc, tc=tc, dm=dm, log=log, ctrl=ctrl, dice=dice)


def place_south(P, squad):
    """Lay the placement's models out legally in the half-ring south of the
    Trukk (away from the foe), inside the rapid 3"."""
    token = P.token
    placed = []
    for model in squad.models:
        done = False
        ring = token.radius_in + model.radius_in + 0.15
        while not done and ring <= token.radius_in + model.radius_in + 3.0:
            steps = max(6, int(math.pi * ring / (2 * model.radius_in + 0.1)))
            for i in range(steps + 1):
                ang = math.pi + math.pi * i / steps
                x, y = token.x_in + ring * math.cos(ang), token.y_in + ring * math.sin(ang)
                if all(math.hypot(x - px, y - py) >= 2 * model.radius_in + 0.1 for px, py in placed):
                    model.x_in, model.y_in = x, y
                    placed.append((x, y))
                    done = True
                    break
            ring += 2 * model.radius_in + 0.1
    return len(placed) == len(squad.models)


def edge(a, b):
    return math.hypot(a.x_in - b.x_in, a.y_in - b.y_in) - a.radius_in - b.radius_in


P = po_scene()
c.true("(live) the foe stands within 8\" of the Trukk", min(edge(P.token, m) for m in P.foe.models) <= 8.0)
c.true("an enemy's move ending in range in ITS Movement phase asks the Trukk's owner",
       P.ctrl.on_move_finished(P.foe, "normal"))
c.eq("...one prompt, to the Ork player, for the first passenger by name",
     (P.dm.player, "1 Boyz 1" in (P.dm.prompt or ""), len(P.dm._queue)), (ORK, True, 1))
c.eq("...Disembark or Stay put", [o["label"] for o in P.dm.options or []], ["Disembark (rapid disembark)", "Stay put"])
P.dm.choose(0)
c.eq("yes: a RAPID disembark placement opens (the printed mode, not determine_mode())",
     (P.setup.state, P.tc.disembark_mode, P.tc.is_disembarking(P.boyz)), (PLACING, RAPID, True))
c.true("...and the NEXT passenger is not asked while it is open", not P.dm.is_pending)
c.true("(live) the models can be laid out legally", place_south(P, P.boyz))
P.tc.confirm_disembark()
c.eq("confirmed: on the battlefield, no errors", (P.setup.errors if P.setup.state == PLACING else [],
                                                  P.boyz.embarked_in), ([], None))
c.true("...its charge is locked for the rest of this turn (18.04)", P.boyz.charge_locked_until_end_of_turn)
c.true("...logged under its printed name", P.log.has("Pilin' Out"))
c.true("...and the second passenger is asked once the first has resolved",
       P.dm.is_pending and "1 Painboy 1" in P.dm.prompt)
P.dm.choose(1)
c.true("Stay put: the Painboy stays aboard", P.passengers[1].embarked_in is P.token and not P.dm.is_pending)
P.ctrl.on_move_finished(P.foe, "advance")
c.true("...and is not asked again this Movement phase", not P.dm.is_pending)
P.ctrl.reset_movement_phase()
P.ctrl.on_move_finished(P.foe, "normal")
c.true("...until the next one", P.dm.is_pending and "1 Painboy 1" in P.dm.prompt)

P = po_scene(painboy=False)
P.ctrl.on_move_finished(P.foe, "normal")
P.dm.choose(0)
P.tc.cancel_disembark()
c.true("a CANCELLED placement puts the unit back aboard", P.boyz.embarked_in is P.token)
P.ctrl.on_move_finished(P.foe, "normal")
c.true("...and counts as the answer for this phase", not P.dm.is_pending and P.setup.state != PLACING)

# An ENEMY unit whose move ends in range in the ORK player's turn - a reactive
# move - is the case the owner test exists for; the Orks' own units are never
# a trigger anyway (transports_in_range() skips a same-owner Trukk).
P = po_scene(turn_owner=ORK)
c.true("not in the Trukk owner's OWN Movement phase, even for an enemy move in range",
       not P.ctrl.on_move_finished(P.foe, "normal") and not P.dm.is_pending)
P = po_scene(phase=PHASE_SHOOTING)
c.true("not in the opponent's Shooting phase", not P.ctrl.on_move_finished(P.foe, "normal"))
P = po_scene(foe_y=33.0)
c.true("(live) the foe now stands more than 8\" away", min(edge(P.token, m) for m in P.foe.models) > 8.0)
c.true("...and nothing is offered", not P.ctrl.on_move_finished(P.foe, "normal") and not P.dm.is_pending)
_plain_transport = build(orks.BATTLEWAGON, ORK, name="1 Battlewagon 9").models[0]
c.true("a TRANSPORT without the ability is not a Pilin' Out Trukk", not pilin_out.has_ability(_plain_transport))

# The three triggers.
P = po_scene()
_mover = MovementController([], tk.Log(), FOE, DiceManager(), P.tt, P.st.tokens)
_mover.on_move_finished.append(P.ctrl.on_move_finished)
_mover.select(P.foe.models[0])
_mover.start_move()
for _m in P.foe.models:
    _m.x_in += 0.5
_mover.confirm_move()
c.eq("(live) the real move was accepted", _mover.errors, [])
c.true("a REAL confirmed Normal move triggers it through the hook", P.dm.is_pending)
P = po_scene()
c.true("an arrival (ingress) on the board triggers it", P.ctrl.on_ingress_resolved(P.foe) and P.dm.is_pending)
P = po_scene()
for _m in P.foe.models:
    P.st.tokens.remove(_m)
c.true("...a cancelled arrival (not on the board) does not", not P.ctrl.on_ingress_resolved(P.foe))
P = po_scene()
c.true("an enemy's confirmed Disembark Move triggers it", P.ctrl.on_disembark_resolved(P.foe, True) and P.dm.is_pending)

# The resolved hook fires only once a Combat disembark's hazard roll is done.
P = po_scene(painboy=False)
_heard = []
P.tc.on_disembark_resolved.append(lambda sq, ok: _heard.append((sq.name, ok)))
P.tc.start_disembark(P.boyz, mode=COMBAT)
place_south(P, P.boyz)
script(*([6] * 10))
P.tc.confirm_disembark()
c.eq("a Combat disembark is not resolved while its hazard roll is open", _heard, [])
P.dice.acknowledge()
P.tc.on_dice_acknowledged()
c.eq("...and fires once the roll is done", _heard, [("1 Boyz 1", True)])

# The AI.
_asked = []
P = po_scene(auto=(ORK,), choose=lambda t, p, m: (_asked.append((t.squad.name, p.name, m.name)) or p.name == "1 Painboy 1"))
P.ctrl.on_move_finished(P.foe, "normal")
c.eq("the AI is asked per passenger with (transport, passenger, mover)",
     _asked, [("1 Trukk 1", "1 Boyz 1", "2 Strike Team 1"), ("1 Trukk 1", "1 Painboy 1", "2 Strike Team 1")])
c.eq("...a no stays aboard, a yes opens the placement with no prompt",
     (P.boyz.embarked_in is P.token, P.tc.is_disembarking(P.passengers[1]), P.dm.is_pending), (True, True, False))


# ===========================================================================
print("\n9. the AI's policies")
# ===========================================================================
_st = GameState()
_kop = line_up(build(orks.DEFFKOPTAS, ORK, name="1 Deffkoptas 1"), y=5.0)
for _m in _kop.models:
    _st.add_token(_m)
_tt = tracker(PHASE_COMMAND, ORK, battle_round=2)
c.eq("Aerial Manoover: a stranded unit (nothing to shoot, charge or take) is repositioned",
     agent_driver.aerial_manoover_choice(_st, _tt, [_kop]), [_kop])
_tt.battle_round = 1
c.eq("...never before its owner can arrive (round 1)", agent_driver.aerial_manoover_choice(_st, _tt, [_kop]), [])
_tt.battle_round, _tt.battle_over = 3, True
c.eq("...never when the withdrawal is doomed", agent_driver.aerial_manoover_choice(_st, _tt, [_kop]), [])
c.true("strategic_reserves owns the doomed predicate the controller reads",
       aerial_manoover.withdrawal_is_doomed is strategic_reserves.withdrawal_is_doomed)

_st2 = GameState()
_trk = build(orks.TRUKK, ORK, name="1 Trukk 1")
_trk.models[0].x_in, _trk.models[0].y_in = 30.0, 22.0
_st2.add_token(_trk.models[0])
_foe = line_up(build(STRIKE_TEAM, FOE, name="2 Strike Team 1"), x=28.0, y=32.0)
for _m in _foe.models:
    _st2.add_token(_m)
_pax = build(orks.BOYZ, ORK, name="1 Boyz 1")
c.true("Pilin' Out: a Trukk expected to survive keeps its passengers",
       not agent_driver.pilin_out_verdict(_st2, _trk.models[0], _pax, _foe))
_trk.models[0].current_wounds = 1
c.true("...one expected to be destroyed lets them out", agent_driver.pilin_out_verdict(_st2, _trk.models[0], _pax, _foe))


# ===========================================================================
print("\n10. wiring and retirements")
# ===========================================================================
MAIN = read("main.py")
TREE = ast.parse(MAIN)


def calls(tree, text):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
            and ast.unparse(n.value) == text]


for _hook in ("movement_controller.on_move_finished.append(pilin_out_controller.on_move_finished)",
              "ingress_controller.on_ingress_resolved.append(pilin_out_controller.on_ingress_resolved)",
              "transport_controller.on_disembark_resolved.append(pilin_out_controller.on_disembark_resolved)",
              "pilin_out_controller.reset_movement_phase()"):
    c.eq("main.py runs %s" % _hook, len(calls(TREE, _hook)), 1)
c.true("the AI's Pilin' Out verdict is injected", "pilin_out_verdict(" in MAIN)
c.true("...and the Aerial Manoover policy", "aerial_manoover_choice(state, turn_tracker, eligible)" in MAIN)
_offer = "aerial_manoover_controller.offer_at_end_of_fight_phase({t.squad for t in state.tokens if t.squad is not None}, mover_before)"
c.eq("Aerial Manoover is offered at the end-of-Fight seam with mover_before", len(calls(TREE, _offer)), 1)

# The end-of-turn flag sweep runs over EVERY unit: a Pilin' Out lock set in the
# opponent's turn must not run on through the Boyz' own.
_sweeps = [n for n in ast.walk(TREE) if isinstance(n, ast.For) and ast.unparse(n.iter) == "state.all_squads()"
           and any(isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "squad.charge_locked_until_end_of_turn"
                   for s in n.body)]
c.eq("the charge-lock reset sweeps state.all_squads()", len(_sweeps), 1)
c.true("...and clears disembarked_from_this_turn with it",
       bool(_sweeps) and any(ast.unparse(s) == "squad.disembarked_from_this_turn = None" for s in _sweeps[0].body))
c.true("no loop over ending_squads resets the charge lock any more",
       not any(isinstance(n, ast.For) and ast.unparse(n.iter) == "ending_squads"
               and "charge_locked_until_end_of_turn" in ast.unparse(n) for n in ast.walk(TREE)))

c.true("High-speed Carnage sits in FightController's adjuster chain",
       "high_speed_carnage.adjusted_weapon(" in read("game/fight.py"))
c.true("Deff from Above sits in ShootingController's hit modifiers",
       any(ast.unparse(n) == "deff_from_above.hit_modifiers(self.active_squad, self.ingress_controller, "
                             "reactive=self._reactive)"
           for n in ast.walk(ast.parse(read("game/shooting.py"))) if isinstance(n, ast.Call)))
c.eq("main.py hands the shooting controller its ingress controller",
     sum(1 for n in ast.walk(TREE) if isinstance(n, ast.Assign)
         and ast.unparse(n) == "shooting_controller.ingress_controller = ingress_controller"), 1)

from game import units as _units  # noqa: E402
for _flag in ("drive_by_dakka", "grot_riggers", "ramshackle_but_rugged", "ard_case"):
    c.true("no profile carries the retired %s flag" % _flag,
           not any(getattr(v, _flag, False) for v in vars(_units).values() if isinstance(v, type)))
for _mod in ("drive_by_dakka.py", "grot_riggers.py", "ramshackle.py"):
    c.true("game/%s is gone" % _mod, not os.path.exists(os.path.join(ROOT, "game", _mod)))

c.finish()
