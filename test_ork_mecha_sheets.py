"""The three datasheets the Mecha Orks list needed (stage G1): Bigboss, Weirdboy
and Gunwagon, driven through the real controllers.

  1. the datasheets: keywords against the corpus, statlines, CORE fields, points,
     bases, sprites
  2. the weapons as printed - the Gunwagon's per-weapon BS4+, the Kannon's two
     profiles, the two same-named-but-different rows (Big Choppa, Crushin' Bulk)
  3. the Gunwagon's wargear: additions, the one-of Kannon swap, the priced Zzap Gun
  4. attachments (Bigboss and Weirdboy are SUPPORT) and the Gunwagon's transport
     line at 18.01 AND 18.02
  5. Sumfin' to Prove through a real FightController: melee only, component-wise
  6. the Weirdboy's Warpath through a real FightController: offered, [PSYCHIC],
     the automatic re-roll of wound 1s on the REAL wound roll, the Kill Rig's
     Warpath untouched, the shared psyker level
  7. Da Jump through a real DaJumpController: its gates, the roll, Strategic
     Reserves, Deep Strike at the real IngressController, once per army per
     battle round, and the button on the REAL ActionPanel
  8. Mobile Arsenal through a real ShootingController hit roll
  9. the AI: _handle_da_jump()'s four conditions
 10. wiring at the source

Run: python test_ork_mecha_sheets.py

Built on testkit.py (see its docstring for the headless-harness traps).
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import ast  # noqa: E402
import io  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import pygame  # noqa: E402

import testkit as tk  # noqa: E402
from testkit import DecisionManager, GameState, TurnTracker, build, line_up, script  # noqa: E402

from ai import agent_driver  # noqa: E402
from game import (  # noqa: E402
    activation_state, attached_units, config, da_jump, formations, maps, mobile_arsenal, psychic_roll, sprites,
    sumfin_to_prove, unstable_energies, warpath, weirdboy_warpath,
)
from game.attached_units import SUPPORT, attachment_role, can_attach  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.factions import orks  # noqa: E402
from game.factions.necrons import NECRON_WARRIORS  # noqa: E402
from game.factions.tau_empire import STRIKE_TEAM  # noqa: E402
from game.ingress import IngressController  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.proactive_stratagems import ProactiveStratagems  # noqa: E402
from game.setup import SetupController  # noqa: E402
from game.shooting import ShootingController  # noqa: E402
from game.transport import TransportController  # noqa: E402
from game.turn import PHASES, PHASE_FIGHT, PHASE_MOVEMENT  # noqa: E402
from game.weapons import MELEE, RANGED, printed_keywords  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
ORK, FOE = "Player 2", "Player 1"
MAP = maps.get("map2")
maps.apply_to_config(MAP)

pygame.init()
pygame.display.set_mode((1200, 900))

c = tk.Checks("Ork Mecha Orks sheets: Bigboss, Weirdboy, Gunwagon")


def read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8").read()


def corpus_keywords(sheet_name):
    text = read(os.path.join("rules", "orks", sheet_name + ".md"))
    match = re.search(r"^KEYWORDS: (.+)$", text, re.MULTILINE)
    return tuple(k.strip() for k in match.group(1).split(";")) if match else None


def tracker(phase, owner, battle_round=2):
    tt = TurnTracker()
    tt.started = True
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = owner
    tt.set_active(owner)
    tt.battle_round = battle_round
    return tt


def weapon(model, name):
    return next((w for w in model.weapons if w.name == name), None)


def profile_of(sheet):
    return sheet.model_lines[0].profile_cls


# ===========================================================================
print("\n1. the datasheets")
# ===========================================================================
_bb = build(orks.BIGBOSS, ORK, name="2 Bigboss 1")
_wb = build(orks.WEIRDBOY, ORK, name="2 Weirdboy 1")
_gw = build(orks.GUNWAGON, ORK, name="2 Gunwagon 1")
_pb, _pw, _pg = _bb.models[0].profile, _wb.models[0].profile, _gw.models[0].profile

for _sheet in (orks.BIGBOSS, orks.WEIRDBOY, orks.GUNWAGON):
    c.eq("%s: KEYWORDS match the printed line" % _sheet.name, tuple(_sheet.keywords), corpus_keywords(_sheet.name))

c.eq("Bigboss: M6 T5 Sv4+ W5 Ld7+ OC1, WS3+ BS5+, no invulnerable save",
     (_pb.movement_in, _pb.toughness, _pb.armor_save, _pb.wounds, _pb.leadership, _pb.oc,
      _pb.weapon_skill, _pb.ballistic_skill, _pb.invulnerable_save),
     (6, 5, "4+", 5, "7+", 1, "3+", "5+", "-"))
c.eq("Bigboss: CHARACTER INFANTRY SUPPORT, Sumfin' to Prove, Waaagh!",
     (_pb.character, _pb.infantry, _pb.support, _pb.leader, _pb.sumfin_to_prove, _pb.waaagh, _pb.orks),
     (True, True, True, False, True, True, True))
c.eq("Weirdboy: M6 T5 Sv5+ W4 Ld7+ OC1, WS3+",
     (_pw.movement_in, _pw.toughness, _pw.armor_save, _pw.wounds, _pw.leadership, _pw.oc, _pw.weapon_skill),
     (6, 5, "5+", 4, "7+", 1, "3+"))
c.eq("Weirdboy: CHARACTER INFANTRY PSYKER SUPPORT, psyker level 1, NOT BEAST SNAGGA",
     (_pw.character, _pw.infantry, _pw.psyker, _pw.support, _pw.psyker_level, _pw.beast_snagga),
     (True, True, True, True, 1, False))
c.eq("Weirdboy: Da Jump and HIS Warpath - not the Kill Rig's",
     (_pw.da_jump, _pw.weirdboy_warpath, _pw.warpath), (True, True, False))
c.true("Weirdboy: CORE Deadly Demise D3 is a real roll",
       _pw.deadly_demise_notation is not None and _pw.deadly_demise_notation.sides == 3)
c.eq("Gunwagon: M10 T12 Sv3+ W16 Ld7+ OC5, invulnerable 6+, WS3+ BS5+",
     (_pg.movement_in, _pg.toughness, _pg.armor_save, _pg.wounds, _pg.leadership, _pg.oc,
      _pg.invulnerable_save, _pg.weapon_skill, _pg.ballistic_skill),
     (10, 12, "3+", 16, "7+", 5, "6+", "3+", "5+"))
c.eq("Gunwagon: VEHICLE TRANSPORT, Damaged 6, Mobile Arsenal",
     (_pg.vehicle, _pg.transport, _pg.damaged_threshold, _pg.mobile_arsenal), (True, True, 6, True))
c.true("Gunwagon: CORE Deadly Demise D6 is a real roll",
       _pg.deadly_demise_notation is not None and _pg.deadly_demise_notation.sides == 6)
c.eq("Gunwagon: prints no Firing Deck and no Mobile Fortress (the Battlewagon's)",
     (_pg.firing_deck, _pg.ranged_damage_reduction), (0, 0))
c.eq("psyker levels: only the Weirdboy's (Unstable Energies)",
     [unstable_energies.psyker_level(s) for s in (_bb, _wb, _gw)], [0, 1, 0])

c.eq("points: Bigboss 50, Weirdboy 65", (_bb.points, _wb.points), (50, 65))
c.eq("points: Gunwagon 150 for the 1st and 2nd, 160 from the 3rd",
     [orks.GUNWAGON.points_for(unit_index=i) for i in (1, 2, 3, 4)], [150, 150, 160, 160])
c.eq("bases: Weirdboy the printed 50mm; Gunwagon the Battlewagon's 2.1\"; Bigboss 40mm (both print 'Use model')",
     (_pw.base_radius_in, _pg.base_radius_in, profile_of(orks.BATTLEWAGON).base_radius_in, _pb.base_radius_in),
     (0.98, 2.1, 2.1, 0.79))
for _squad, _file in ((_bb, "Bigboss.png"), (_wb, "Weirdboy.png"), (_gw, "Gunwagon.png"),
                      (build(orks.PAINBOY, ORK, name="2 Painboy 1"), "Painboy.png")):
    _sprite_key = sprites._squad_key(_squad.models[0])
    _path = (sprites._resolve_path(_sprite_key) if _sprite_key else None) or ""
    c.eq("sprite: %s draws %s" % (_squad.name, _file), os.path.basename(_path), _file)


# ===========================================================================
print("\n2. the weapons")
# ===========================================================================
c.eq("Bigboss carries a Big Choppa and a Slugga", sorted(w.name for w in _bb.models[0].weapons),
     ["Big Choppa", "Slugga"])
_bbc = weapon(_bb.models[0], "Big Choppa")
c.eq("Bigboss's Big Choppa: A5 S7 AP-2 D2 [PRECISION]",
     (_bbc.weapon_type, _bbc.attacks, _bbc.strength, _bbc.ap, _bbc.damage, _bbc.precision, _bbc.cleave),
     (MELEE, 5, 7, -2, 2, True, 0))
_nob_bc = weapon(build(orks.BOYZ, ORK, name="2 Boyz X", choices={"Nob": {orks.BOYZ_NOB_TO_BIG_CHOPPA: 1}})
                 .models[0], "Big Choppa")
c.true("...and NOT the Boyz Nob's Big Choppa (A4 AP-1 [CLEAVE 2]) - same name, other row",
       _nob_bc is not None and type(_nob_bc) is not type(_bbc)
       and (_nob_bc.attacks, _nob_bc.ap, _nob_bc.cleave) == (4, -1, 2))

c.eq("Weirdboy carries a Power Vomit and a Copper Staff", sorted(w.name for w in _wb.models[0].weapons),
     ["Copper Staff", "Power Vomit"])
_pv, _cs = weapon(_wb.models[0], "Power Vomit"), weapon(_wb.models[0], "Copper Staff")
c.eq("Power Vomit: 12\" A3 S5 AP-3 D2 [BLAST] [HAZARDOUS] [PSYCHIC] [TORRENT]",
     (_pv.weapon_type, _pv.range_in, _pv.attacks, _pv.strength, _pv.ap, _pv.damage,
      _pv.blast, _pv.hazardous, _pv.psychic, _pv.torrent),
     (RANGED, 12, 3, 5, -3, 2, 1, True, True, True))
c.eq("Copper Staff: A3 S8 AP-1 D2 [PSYCHIC]",
     (_cs.weapon_type, _cs.attacks, _cs.strength, _cs.ap, _cs.damage, _cs.psychic), (MELEE, 3, 8, -1, 2, True))

_gwm = _gw.models[0]
c.eq("Gunwagon default: Crushin' Bulk and a Kannon", sorted(w.name for w in _gwm.weapons),
     ["Crushin' Bulk", "Kannon - Frag"])
_frag = weapon(_gwm, "Kannon - Frag")
_shell = _frag.overcharge_profile
c.eq("Kannon - Frag: 36\" A4 BS4+ S5 AP0 D1 [BLAST 3] [RAPID FIRE 4]",
     (_frag.range_in, _frag.attacks, _frag.ballistic_skill, _frag.strength, _frag.ap, _frag.damage,
      _frag.blast, _frag.rapid_fire), (36, 4, "4+", 5, 0, 1, 3, 4))
_shell_dmg = getattr(_shell, "damage_notation", None)
c.eq("...its second profile Kannon - Shell: 36\" A2 BS4+ S10 AP-2 D D6+1 [RAPID FIRE 2]",
     (getattr(_shell, "name", None), getattr(_shell, "attacks", None), getattr(_shell, "ballistic_skill", None),
      getattr(_shell, "strength", None), getattr(_shell, "ap", None),
      getattr(_shell_dmg, "sides", None), getattr(_shell_dmg, "bonus", None), getattr(_shell, "rapid_fire", None)),
     ("Kannon - Shell", 2, "4+", 10, -2, 6, 1, 2))
_kk = orks.KillkannonProfile
c.eq("Killkannon: 24\" A4 BS4+ S6 AP-3 D2 [ANTI-INFANTRY 3+] [BLAST] [RAPID FIRE 4]",
     (_kk.range_in, _kk.attacks, _kk.ballistic_skill, _kk.strength, _kk.ap, _kk.damage, _kk.anti, _kk.blast,
      _kk.rapid_fire), (24, 4, "4+", 6, -3, 2, ("INFANTRY", 3), 1, 4))
_lb = orks.LobbaProfile
c.eq("Lobba: 48\" A3 BS4+ S5 AP0 D1 [BLAST 3] [INDIRECT FIRE] - not the Kill Rig's 'Eavy Lobba",
     (_lb.range_in, _lb.attacks, _lb.ballistic_skill, _lb.strength, _lb.damage, _lb.blast, _lb.indirect_fire,
      _lb is orks.EavyLobbaProfile), (48, 3, "4+", 5, 1, 3, True, False))
_zz = orks.ZzapGunProfile
c.eq("Zzap Gun: 36\" A2 BS4+ S8 AP-2 D4, anti and devastating vs MONSTER/VEHICLE, RF2, SH2",
     printed_keywords(_zz),
     ["ANTI-MONSTER/VEHICLE 4+", "DEVASTATING WOUNDS: MONSTER/VEHICLE", "RAPID FIRE 2", "SUSTAINED HITS 2"])
c.eq("...its numbers", (_zz.range_in, _zz.attacks, _zz.ballistic_skill, _zz.strength, _zz.ap, _zz.damage),
     (36, 2, "4+", 8, -2, 4))
_bulk = weapon(_gwm, "Crushin' Bulk")
_bw_bulk = weapon(build(orks.BATTLEWAGON, ORK, name="2 Battlewagon X").models[0], "Crushin' Bulk")
c.eq("the Gunwagon's Crushin' Bulk prints [CLEAVE 2], the Battlewagon's [CLEAVE 1]",
     (_bulk.cleave, _bw_bulk.cleave, (_bulk.attacks, _bulk.strength, _bulk.ap, _bulk.damage)),
     (2, 1, (6, 8, -2, 2)))
c.true("the Big Shoota row keeps the model's BS5+ (one class with the Battlewagon's)",
       orks.BigShootaS5Profile.ballistic_skill is None)


# ===========================================================================
print("\n3. the Gunwagon's wargear")
# ===========================================================================
def gunwagon(**options):
    return build(orks.GUNWAGON, ORK, name="2 Gunwagon W", choices={"Gunwagon": options})


_full = gunwagon(**{orks.GUNWAGON_ADD_WRECKIN_BALL: 1, orks.GUNWAGON_ADD_GRABBIN_KLAW: 1,
                    orks.GUNWAGON_ADD_LOBBA: 1, orks.GUNWAGON_ADD_BIG_SHOOTAS: 1,
                    orks.GUNWAGON_KANNON_TO_ZZAP_GUN: 1})
c.eq("the Mecha Orks build: Bulk, Wreckin' Ball, Grabbin' Klaw, Lobba, 4 Big Shootas, Zzap Gun",
     sorted(w.name for w in _full.models[0].weapons),
     sorted(["Crushin' Bulk", "Wreckin' Ball", "Grabbin' Klaw", "Lobba"] + ["Big Shoota"] * 4 + ["Zzap Gun"]))
c.eq("...priced 150 + 10 for the Zzap Gun (the app's 160 before its Enhancement)", _full.points, 160)
c.eq("a Killkannon costs nothing", gunwagon(**{orks.GUNWAGON_KANNON_TO_KILLKANNON: 1}).points, 150)
_both = gunwagon(**{orks.GUNWAGON_KANNON_TO_KILLKANNON: 1, orks.GUNWAGON_KANNON_TO_ZZAP_GUN: 1})
c.eq("\"one of the following\": asking for both swaps gives up ONE Kannon for ONE of them",
     sorted(w.name for w in _both.models[0].weapons if w.weapon_type == RANGED), ["Killkannon"])


# ===========================================================================
print("\n4. attachments and transport")
# ===========================================================================
c.eq("the Bigboss and the Weirdboy SUPPORT", (attachment_role(_bb), attachment_role(_wb)), (SUPPORT, SUPPORT))
c.eq("Bigboss + Boyz is legal",
     can_attach(build(orks.BIGBOSS, ORK, name="bb1"), build(orks.BOYZ, ORK, name="2 Boyz 1")), [])
_led = attached_units.attach(build(orks.WARBOSS, ORK, name="2 Warboss 1"), build(orks.BOYZ, ORK, name="2 Boyz 2"),
                             force=True)
c.eq("...beside a Warboss already leading them (rule 19.01)",
     can_attach(build(orks.BIGBOSS, ORK, name="bb2"), _led), [])
c.true("Bigboss + Beast Snagga Boyz is not",
       bool(can_attach(build(orks.BIGBOSS, ORK, name="bb3"), build(orks.BEAST_SNAGGA_BOYZ, ORK, name="2 BSB 1"))))
_bs_led = attached_units.attach(build(orks.BEASTBOSS, ORK, name="2 Beastboss 1"),
                                build(orks.BEAST_SNAGGA_BOYZ, ORK, name="2 BSB 2"), force=True)
c.eq("Weirdboy + Beast Snagga Boyz led by a Beastboss is legal",
     can_attach(build(orks.WEIRDBOY, ORK, name="wb1"), _bs_led), [])
c.eq("Weirdboy + Boyz is legal", can_attach(build(orks.WEIRDBOY, ORK, name="wb2"), build(orks.BOYZ, ORK, name="2 Boyz 3")), [])
c.true("Weirdboy + Meganobz is not",
       bool(can_attach(build(orks.WEIRDBOY, ORK, name="wb3"), build(orks.MEGANOBZ, ORK, name="2 Meganobz 1"))))


def fits(carrier_sheet, passenger):
    """(18.01 errors, 18.02 answer) for `passenger` boarding a fresh carrier."""
    st = GameState()
    token = build(carrier_sheet, ORK, name="2 %s T" % carrier_sheet.name).models[0]
    token.x_in, token.y_in = 20.0, 20.0
    spacing = 0.6
    line_up(passenger, x=20.0 - (len(passenger.models) - 1) * spacing / 2.0, y=23.0, spacing=spacing)
    st.add_token(token)
    for m in passenger.models:
        st.add_token(m)
    mc = MovementController(all_tokens=st.tokens)
    mc.moved_squad_ids.add(passenger)
    tc = TransportController(None, st, st.tokens, mc, None, None)
    return formations.embark_errors(passenger, token), tc.can_embark(passenger, token)


c.eq("Gunwagon: capacity 12 ORKS INFANTRY",
     (_pg.transport_capacity, _pg.transport_requires_infantry, _pg.transport_requires), (12, True, ("orks",)))
_mob = attached_units.attach(build(orks.BIGBOSS, ORK, name="2 Bigboss 2"),
                             attached_units.attach(build(orks.WARBOSS, ORK, name="2 Warboss 2"),
                                                   build(orks.BOYZ, ORK, name="2 Boyz 4"), force=True),
                             force=True)
c.eq("10 Boyz + Warboss + Bigboss (12) fit, at 18.01 and 18.02", fits(orks.GUNWAGON, _mob), ([], True))
c.eq("3 Meganobz (MEGA ARMOUR, 6 slots) fit", fits(orks.GUNWAGON, build(orks.MEGANOBZ, ORK, name="2 MN 1",
                                                                         composition_index=1)), ([], True))
_errs, _ok = fits(orks.GUNWAGON, build(orks.BOYZ, ORK, name="2 Boyz 20", composition_index=1))
c.true("20 Boyz are refused at both (20 > 12)", bool(_errs) and not _ok)
_errs, _ok = fits(orks.GUNWAGON, build(STRIKE_TEAM, ORK, name="2 ST 1"))
c.true("a non-ORKS unit is refused at both", bool(_errs) and not _ok)
_errs, _ok = fits(orks.KILL_RIG, attached_units.attach(build(orks.WEIRDBOY, ORK, name="2 Weirdboy 9"),
                                                       build(orks.BEAST_SNAGGA_BOYZ, ORK, name="2 BSB 9"),
                                                       force=True))
c.true("a Beast Snagga mob WITH its Weirdboy no longer fits a Kill Rig (he is not BEAST SNAGGA)",
       bool(_errs) and not _ok)


# ===========================================================================
print("\n5. Sumfin' to Prove")
# ===========================================================================
def sumfin(mods):
    return [m.amount for m in mods if m.source == sumfin_to_prove.SUMFIN_TO_PROVE_NAME]


_F = tk.fight_scene(orks.BOYZ, NECRON_WARRIORS, attacker_owner=ORK)
_boyz = _F["attacker"]
_FC = _F["fight"]
_FC.fighting_squad = _boyz
c.eq("(live) plain Boyz: no bonus", sumfin(_FC._hit_modifiers(_boyz.models[1], _F["target"])), [])
_bigboss_unit = build(orks.BIGBOSS, ORK, name="2 Bigboss 5")
line_up(_bigboss_unit, x=_boyz.models[-1].x_in + 1.0, y=_boyz.models[-1].y_in)
for _m in _bigboss_unit.models:
    _F["state"].add_token(_m)
_boyz = attached_units.attach(_bigboss_unit, _boyz, force=True)
_FC.fighting_squad = _boyz
_a_boy = next(m for m in _boyz.models if not m.profile.character)
c.eq("Boyz supported by a Bigboss: +1 to hit (-1 on the threshold) for a BOY's melee attack",
     sumfin(_FC._hit_modifiers(_a_boy, _F["target"])), [-1])
_S = tk.shooting_scene(orks.BIGBOSS, STRIKE_TEAM, attacker_owner=ORK, gap=8.0)
_S["shooting"].active_squad = _S["attacker"]
_ranged_group = {"pairs": [(_S["attacker"].models[0], weapon(_S["attacker"].models[0], "Slugga"))],
                 "target_squad": _S["target"]}
c.eq("...but NOT on a ranged attack - \"melee\" (the shooting side never asks)",
     sumfin(_S["shooting"]._hit_modifiers(_ranged_group)), [])
_the_bigboss = next((m for m in _boyz.models if m.profile.name == "Bigboss"), None)
if _the_bigboss is not None:
    _the_bigboss.current_wounds = 0
c.eq("the Bigboss destroyed: the mob loses it (rule 19.04)",
     (_the_bigboss is not None, sumfin(_FC._hit_modifiers(_a_boy, _F["target"]))), (True, []))

_T = tk.fight_scene(orks.BIGBOSS, orks.BOYZ, attacker_owner=ORK)
_T["fight"].select_to_fight(_T["attacker"])
if _T["fight"].target_squad is None:
    _T["fight"].choose_target_squad(_T["target"])
_key = next((k for k, label, *_r in _T["fight"].weapon_eligibility() if "Big Choppa" in str(label)), None)
script(*([2] * 5))
if _key is not None:
    _T["fight"].choose_weapon(_key)
c.eq("(live) the Bigboss's WS3+ Big Choppa hits on 2+ on the REAL Hit roll", _T["dice"].success_threshold, 2)


# ===========================================================================
print("\n6. the Weirdboy's Warpath")
# ===========================================================================
def wp_scene(attacker=None, auto=(), verdict=None, target_sheet=None):
    scene = tk.fight_scene(attacker or orks.WEIRDBOY, target_sheet or orks.BOYZ, attacker_owner=ORK)
    fc = scene["fight"]
    scene["turn"].battle_round = 2
    pr = psychic_roll.PsychicRollController(scene["dice"], scene["turn"], scene["log"])
    fc.warpath = warpath.WarpathController(pr, decision_manager=scene["decision"], game_log=scene["log"],
                                           auto_players=auto, verdict=verdict)
    fc.weirdboy_warpath = weirdboy_warpath.WeirdboyWarpathController(
        pr, decision_manager=scene["decision"], game_log=scene["log"], auto_players=auto, verdict=verdict)
    return SimpleNamespace(scene=scene, fc=fc, pr=pr, unit=scene["attacker"], target=scene["target"],
                           dice=scene["dice"], dm=scene["decision"], log=scene["log"])


W = wp_scene()
W.fc.select_to_fight(W.unit)
c.eq("selected to fight: the human is asked, Roll or Decline",
     (W.dm.player, tk.options_of(W.dm)), (ORK, [warpath.ROLL_LABEL, warpath.DECLINE_LABEL]))
c.true("...and the prompt names the Weirdboy's effect, not the Kill Rig's",
       "re-roll wound rolls of 1" in (W.dm.prompt or "") and "LETHAL HITS" not in (W.dm.prompt or ""))
script(5)
tk.pick_option(W.dm, "Make the psychic roll")
c.eq("yes: HIS grant is up (not the Kill Rig's) and the psychic D6 is on the table",
     (weirdboy_warpath.is_active(W.unit), warpath.is_active(W.unit), W.dice.is_pending,
      "Psychic roll: Warpath" in (W.dice.label or ""), unstable_energies.spent_this_round(W.unit, 2)),
     (True, False, True, True, 1))
_choppa_like = orks.PowerKlawProfile()
_adj = weirdboy_warpath.adjusted_weapon(_choppa_like, W.unit)
c.eq("a melee weapon gains [PSYCHIC] and NOT [LETHAL HITS]", (_adj.psychic, _adj.lethal_hits), (True, False))
c.eq("...on a copy - the weapon handed in is untouched", (_choppa_like.psychic, _adj is _choppa_like), (False, False))
c.true("...and a ranged weapon gets nothing",
       not weirdboy_warpath.adjusted_weapon(orks.SluggaProfile(), W.unit).psychic)
W.dice.acknowledge()
W.pr.on_dice_acknowledged()
c.eq("a 5: not shocked, grant kept", (W.unit.battle_shocked, weirdboy_warpath.is_active(W.unit)), (False, True))


def wound_step(active):
    """The Copper Staff's REAL wound roll with three 1s: what the step does next."""
    S = wp_scene(auto=(ORK,), verdict=lambda squad: active)
    script(6)
    S.fc.select_to_fight(S.unit)
    if S.dice.is_pending and "Psychic" in (S.dice.label or ""):
        S.dice.acknowledge()
        S.pr.on_dice_acknowledged()
    if S.fc.target_squad is None:
        S.fc.choose_target_squad(S.target)
    key = next((k for k, label, *_r in S.fc.weapon_eligibility() if "Copper Staff" in str(label)), None)
    if key is None:
        return None, None, None
    script(6, 6, 6)
    S.fc.choose_weapon(key)
    S.dice.acknowledge()
    script(1, 1, 1)
    S.fc.on_dice_acknowledged()
    wound_label = S.dice.label or ""
    script(4, 4, 4)
    S.dice.acknowledge()
    S.fc.on_dice_acknowledged()
    return S.fc.pending_step, S.dice.label or "", wound_label


_step_on, _label_on, _wound_on = wound_step(True)
_step_off, _label_off, _wound_off = wound_step(False)
c.true("(live) the wound roll was really thrown with three 1s", "Wound" in (_wound_on or "") and "Wound" in (_wound_off or ""))
c.eq("with Warpath: the three wound 1s are re-rolled as their own visible step",
     (_step_on, "Warpath (Weirdboy)" in _label_on and "re-roll of 1s" in _label_on), ("wound_reroll_ones", True))
c.true("without it: no re-roll step", _step_off != "wound_reroll_ones" and "re-roll of 1s" not in _label_off)

_rig = wp_scene(attacker=orks.KILL_RIG, auto=(ORK,), verdict=lambda squad: True)
_rig.fc.select_to_fight(_rig.unit)
c.eq("a Kill Rig still gets ITS Warpath and never the Weirdboy's",
     (warpath.is_active(_rig.unit), weirdboy_warpath.is_active(_rig.unit)), (True, False))
c.true("...and its fight asks for no wound 1s re-roll", not weirdboy_warpath.rerolls_wound_ones(_rig.unit))
_plain = wp_scene(attacker=orks.BOYZ)
_plain.fc.select_to_fight(_plain.unit)
c.true("not offered to a unit without a Weirdboy", not _plain.dm.is_pending)

_bsb = build(orks.BEAST_SNAGGA_BOYZ, ORK, name="2 BSB 7")
_wb7 = build(orks.WEIRDBOY, ORK, name="2 Weirdboy 7")
_mob7 = attached_units.attach(_wb7, _bsb, force=True)
_ctrl7 = weirdboy_warpath.WeirdboyWarpathController(
    psychic_roll.PsychicRollController(tk.RecordingDice(), tracker(PHASE_FIGHT, ORK), tk.Log()))
c.true("a Beast Snagga mob he supports has it (19.04 component-wise)", _ctrl7.can_use(_mob7))
unstable_energies.spend(_mob7, 1, 2)
c.true("...not once Da Jump spent the psyker level this round (one shared budget)", not _ctrl7.can_use(_mob7))
_the_weirdboy = next((m for m in _mob7.models if m.profile.name == "Weirdboy"), None)
if _the_weirdboy is not None:
    _the_weirdboy.current_wounds = 0
_mob7.unstable_energies_round = None
c.true("...and not once the Weirdboy is destroyed", _the_weirdboy is not None and not _ctrl7.can_use(_mob7))
W = wp_scene(auto=(ORK,), verdict=lambda squad: True)
W.fc.select_to_fight(W.unit)
weirdboy_warpath.reset_phase([W.unit])
c.true("reset_phase ends the grant", not weirdboy_warpath.is_active(W.unit))


# ===========================================================================
print("\n7. Da Jump")
# ===========================================================================
def dj_scene(phase=PHASE_MOVEMENT, owner=ORK, battle_round=2, mob=True):
    st = GameState()
    tt = tracker(phase, owner, battle_round)
    weird = build(orks.WEIRDBOY, ORK, name="2 Weirdboy 1")
    unit = attached_units.attach(weird, build(orks.BOYZ, ORK, name="2 Boyz 1"), force=True) if mob else weird
    line_up(unit, x=12.0, y=10.0, spacing=1.2)
    for m in unit.models:
        st.add_token(m)
    foe = build(STRIKE_TEAM, FOE, name="1 Strike Team 1")
    line_up(foe, x=12.0, y=40.0)
    for m in foe.models:
        st.add_token(m)
    dice, log = tk.RecordingDice(), tk.Log()
    pr = psychic_roll.PsychicRollController(dice, tt, log)
    mc = MovementController([], tk.Log(), owner, DiceManager(), tt, st.tokens)
    ctrl = da_jump.DaJumpController(pr, game_state=st, movement_controller=mc, turn_tracker=tt,
                                    game_log=log, squads_provider=st.all_squads)
    setup = SetupController(st, obstacles=[], all_tokens=st.tokens,
                            board_width_in=MAP.width_in, board_height_in=MAP.height_in)
    ingress = IngressController(setup, st, st.tokens, game_log=log, turn_tracker=tt,
                                board_width_in=MAP.width_in, board_height_in=MAP.height_in)
    return SimpleNamespace(st=st, tt=tt, unit=unit, foe=foe, dice=dice, log=log, pr=pr, mc=mc, ctrl=ctrl,
                           ingress=ingress)


D = dj_scene()
c.true("(live) your Movement phase, battle round 2: the Weirdboy's mob may jump", D.ctrl.can_use(D.unit))
c.true("...the plain Strike Team may not", not D.ctrl.can_use(D.foe))
_rig_dj = build(orks.KILL_RIG, ORK, name="2 Kill Rig DJ")
_rig_dj.models[0].x_in, _rig_dj.models[0].y_in = 40.0, 12.0
D.st.add_token(_rig_dj.models[0])
c.true("...(live) the Kill Rig beside it could make a psychic roll", D.pr.can_roll(_rig_dj))
c.true("...and still has no Da Jump - the ability gate holds, not the psyker level", not D.ctrl.can_use(_rig_dj))
_middle = (MAP.width_in / 2.0, 22.0)
c.true("(live) before the jump a mid-board landing is NOT legal for it (no Deep Strike: 6\" of an edge)",
       not D.ingress._has_deep_strike(D.unit) and not D.ingress.position_valid(D.unit, D.unit.models[0], *_middle))
D.mc.select(D.unit.models[0])
script(4)
c.true("use: rolls and jumps", D.ctrl.use(D.unit))
c.eq("...a visible psychic D6 is on the table, the level spent",
     (D.dice.is_pending, "Psychic roll: Da Jump" in (D.dice.label or ""),
      unstable_energies.spent_this_round(D.unit, 2)), (True, True, 1))
c.eq("...the WHOLE attached unit is in Strategic Reserves and off the board",
     (D.unit in D.st.reserves, any(m in D.st.tokens for m in D.unit.models)), (True, False))
c.eq("...with Deep Strike, the round of its spend written on it",
     (da_jump.grants_deep_strike(D.unit), D.unit.da_jump_round), (True, 2))
c.true("...and the panel's pick no longer points at it", D.mc.selected_squad is not D.unit)
D.dice.acknowledge()
D.pr.on_dice_acknowledged()
c.eq("a 4: not battle-shocked", D.unit.battle_shocked, False)
c.true("(live IngressController) it may arrive this same phase in battle round 2", D.ingress.can_ingress(D.unit))
c.true("...WITH Deep Strike (rule 24.09)", D.ingress._has_deep_strike(D.unit) and D.ingress.deep_striking(D.unit))
c.true("...so a mid-board landing more than 8\" from the enemy is legal now",
       D.ingress.position_valid(D.unit, D.unit.models[0], *_middle))
c.true("...but not one within 8\" of it",
       not D.ingress.position_valid(D.unit, D.unit.models[0], D.foe.models[0].x_in, D.foe.models[0].y_in - 4.0))
c.true("in reserves it cannot jump again", not D.ctrl.can_use(D.unit))

D = dj_scene()
script(1)
D.ctrl.use(D.unit)
D.dice.acknowledge()
D.pr.on_dice_acknowledged()
c.eq("a 1: battle-shocked - and STILL in reserves with Deep Strike (the effect lands on every roll)",
     (D.unit.battle_shocked, D.unit in D.st.reserves, da_jump.grants_deep_strike(D.unit)), (True, True, True))

D = dj_scene(battle_round=1)
script(3)
D.ctrl.use(D.unit)
c.true("in battle round 1 it jumps, but cannot arrive before round 2 (rule 20.03)",
       D.unit in D.st.reserves and not D.ingress.can_ingress(D.unit))

for _label, _kw, _mutate in (
        ("not in the opponent's Movement phase", dict(owner=FOE), None),
        ("not outside the Movement phase", dict(phase=PHASE_FIGHT), None),
        ("not while battle-shocked", {}, lambda s: setattr(s.unit, "battle_shocked", True)),
        ("not once its psyker level is spent this round (Warpath)", {},
         lambda s: unstable_energies.spend(s.unit, 1, 2)),
        ("not while another roll is on the table", {},
         lambda s: s.dice.roll(count=1, sides=6, label="Hit Roll: something")),
        ("not mid-move", {}, lambda s: s.mc.move_start.update({s.unit.models[0].id: (0.0, 0.0)})),
        ("not while embarked", {}, lambda s: s.st.embarked_squads.append(s.unit)),
):
    D = dj_scene(**_kw)
    if _mutate is not None:
        _mutate(D)
    c.true("Da Jump: %s" % _label, not D.ctrl.can_use(D.unit))

D = dj_scene()
_second = build(orks.WEIRDBOY, ORK, name="2 Weirdboy 2")
line_up(_second, x=30.0, y=10.0)
for _m in _second.models:
    D.st.add_token(_m)
c.true("(live) a second Weirdboy may jump before the first has", D.ctrl.can_use(_second))
script(4)
D.ctrl.use(D.unit)
D.dice.acknowledge()
D.pr.on_dice_acknowledged()
c.true("\"once per army, per battle round\": after the first jump the second may not",
       "already used" in (D.ctrl.why_not(_second) or ""))
_fresh = da_jump.DaJumpController(D.pr, game_state=D.st, movement_controller=D.mc, turn_tracker=D.tt,
                                  game_log=D.log, squads_provider=D.st.all_squads)
c.true("...read off the unit that spent it, so a new controller (a loaded save) agrees",
       "already used" in (_fresh.why_not(_second) or ""))
D.tt.battle_round = 3
c.true("...and it is back next battle round", _fresh.can_use(_second))
c.true("its three flags are saved (SQUAD_FLAGS)",
       {"weirdboy_warpath_active", "da_jump_deep_strike", "da_jump_round"} <= set(activation_state.SQUAD_FLAGS))

# --- the REAL ActionPanel ---------------------------------------------------
from game.ui.action_panel import ActionPanel  # noqa: E402

_panel = ActionPanel()
_surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
_rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900)
_reached = []
_real_movement_ui = ActionPanel._draw_movement_ui


def _spy_movement_ui(self, *a, **kw):
    _reached.append(True)
    return _real_movement_ui(self, *a, **kw)


ActionPanel._draw_movement_ui = _spy_movement_ui


def render(scene, registry=None):
    """Draw the real panel with the scene's unit selected; (names, buttons, reached)."""
    registry = registry if registry is not None else ProactiveStratagems([scene.ctrl])
    shooter = ShootingController(obstacles=[], game_log=tk.Log(), player_name=scene.tt.turn_owner,
                                 dice_manager=DiceManager(), turn_tracker=scene.tt,
                                 all_tokens=scene.st.tokens, decision_manager=DecisionManager())
    _reached.clear()
    _surface.fill((0, 0, 0))
    scene.mc.select(scene.unit.models[0])
    _panel.draw(_surface, _rect, scene.mc, shooter, dice_manager=DiceManager(), proactive_stratagems=registry)
    return ([n for _, n in _panel._stratagem_buttons], list(_panel._buttons),
            scene.mc.selected_squad is scene.unit and bool(_reached))


D = dj_scene()
_names, _buttons, _ok = render(D, registry=ProactiveStratagems())
c.true("(liveness) the unit screen was drawn with the mob selected", _ok)
c.true("...and an EMPTY registry draws no Da Jump", da_jump.DA_JUMP_NAME not in _names)
for _phase in PHASES:
    D = dj_scene(phase=_phase)
    _names, _buttons, _ok = render(D)
    c.eq("the real panel draws Da Jump in your %s: %s" % (_phase, _phase == PHASE_MOVEMENT),
         (_ok or _phase != PHASE_MOVEMENT, da_jump.DA_JUMP_NAME in _names), (True, _phase == PHASE_MOVEMENT))
D = dj_scene(mob=False)
D.unit = D.foe
D.foe.owner = ORK
_names, _buttons, _ok = render(D)
c.true("...never for a unit without a Weirdboy", _ok and da_jump.DA_JUMP_NAME not in _names)
D = dj_scene()
_names, _buttons, _ok = render(D)
_rect_dj = next((r for r, n in _panel._stratagem_buttons if n == da_jump.DA_JUMP_NAME), None)
_cb = next((cb for r, cb in _buttons if r == _rect_dj), None)
script(4)
if _cb is not None:
    _cb()
c.eq("pressing the drawn button really jumps (roll on the table, unit in reserves)",
     (_cb is not None, D.dice.is_pending, D.unit in D.st.reserves), (True, True, True))


# ===========================================================================
print("\n8. Mobile Arsenal")
# ===========================================================================
def arsenal_scene(attacker=orks.GUNWAGON, reactive=False):
    tk.script(1, 1, 5, default=5)
    scene = tk.shooting_scene(attacker, STRIKE_TEAM, attacker_owner=ORK, gap=12.0)
    sc = scene["shooting"]
    sc.start_shooting(scene["attacker"])
    sc._reactive = reactive
    sc.choose_target_squad(scene["target"])
    key = next((k for k, *rest in sc.weapon_eligibility() if "Kannon" in str(rest[0])), None)
    if key is None:
        return scene, sc, None
    sc.choose_weapon(key)
    scene["dice"].acknowledge()
    sc.on_dice_acknowledged()
    return scene, sc, key


_scene, _sc, _key = arsenal_scene()
c.true("(live) the Gunwagon's Kannon rolled to hit", _key is not None)
c.eq("its hit 1s are re-rolled as their own visible step, named Mobile Arsenal",
     (_sc.pending_step, "Mobile Arsenal" in (_scene["dice"].label or "")), ("hit_reroll_ones", True))
_scene, _sc, _key = arsenal_scene(reactive=True)
c.true("NOT on a reactive activation - \"in your Shooting phase\"", _sc.pending_step != "hit_reroll_ones")
c.true("a unit without it re-rolls nothing",
       not mobile_arsenal.applies(build(orks.BATTLEWAGON, ORK, name="2 Battlewagon 9")))


# ===========================================================================
print("\n9. the AI")
# ===========================================================================
class _Area:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def distance_to_model(self, model):
        return max(0.0, math.hypot(model.x_in - self.x, model.y_in - self.y) - model.radius_in)


def ai_jump(battle_round=2, foe_y=40.0, objective=None, moved=False):
    D = dj_scene(battle_round=battle_round)
    for m in D.foe.models:
        m.y_in = foe_y
    if objective is not None:
        D.st.objectives = [SimpleNamespace(terrain_area=_Area(*objective), name="obj",
                                           update_control=lambda tokens: None)]
    if moved:
        D.mc.moved_squad_ids.add(D.unit)
    log = tk.Log()
    script(4)
    acted = agent_driver._handle_da_jump(ORK, D.st, D.mc, D.ctrl, log)
    return acted, D, log


_acted, _D, _log = ai_jump()
c.eq("AI, round 2, the nearest enemy ~30\" away (beyond an Advance and a charge): jumps",
     (_acted, _D.unit in _D.st.reserves, _log.has("[da jump]")), (True, True, True))
c.true("AI: not in battle round 1 (it could not come back this phase)", not ai_jump(battle_round=1)[0])
c.true("AI: not when the enemy is within an Advance plus a charge", not ai_jump(foe_y=22.0)[0])
c.true("AI: not a unit standing within range of an objective", not ai_jump(objective=(12.0, 10.0))[0])
c.true("AI: not a unit that has already moved", not ai_jump(moved=True)[0])
c.true("AI: no controller, nothing", not agent_driver._handle_da_jump(ORK, _D.st, _D.mc, None, None))


# ===========================================================================
print("\n10. wiring at the source")
# ===========================================================================
MAIN = read("main.py")
TREE = ast.parse(MAIN)


def calls(tree, text):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n) == text]


_ww = [n for n in ast.walk(TREE) if isinstance(n, ast.keyword) and n.arg == "weirdboy_warpath"
       and isinstance(n.value, ast.Call) and ast.unparse(n.value.func) == "WeirdboyWarpathController"]
c.eq("main.py hands FightController a WeirdboyWarpathController", len(_ww), 1)
c.true("...on main()'s psychic roll, with the AI's verdict injected",
       bool(_ww) and ast.unparse(_ww[0].value.args[0]) == "psychic_roll_controller"
       and any(k.arg == "verdict" and "warpath_verdict(state, squad)" in ast.unparse(k.value)
               for k in _ww[0].value.keywords))
c.eq("...clears it with the per-phase grants",
     len(calls(TREE, "weirdboy_warpath.reset_phase({t.squad for t in state.tokens if t.squad is not None})")), 1)
_dj = [n for n in ast.walk(TREE) if isinstance(n, ast.Call) and ast.unparse(n.func) == "proactive_stratagems.add"
       and n.args and isinstance(n.args[0], ast.Call) and ast.unparse(n.args[0].func) == "DaJumpController"]
c.eq("...registers Da Jump on the panel registry", len(_dj), 1)
c.true("...on main()'s psychic roll",
       bool(_dj) and ast.unparse(_dj[0].args[0].args[0]) == "psychic_roll_controller")
c.eq("...and hands it to the AI",
     sum(1 for n in ast.walk(TREE) if isinstance(n, ast.keyword) and n.arg == "da_jump_controller"
         and ast.unparse(n.value) == "da_jump_controller"), 1)
_fight = read(os.path.join("game", "fight.py"))
c.true("FightController offers the Weirdboy's Warpath at selection", "self.weirdboy_warpath.offer(squad)" in _fight)
c.true("...chains its [PSYCHIC]", "weirdboy_warpath.adjusted_weapon(weapon, self.fighting_squad)" in _fight)
c.true("...re-rolls its wound 1s", "weirdboy_warpath.rerolls_wound_ones(self.fighting_squad)" in _fight)
c.true("...and reads Sumfin' to Prove", "sumfin_to_prove.hit_modifiers(self.fighting_squad)" in _fight)
c.true("ShootingController reads Mobile Arsenal (never reactive)",
       "mobile_arsenal.applies(self.active_squad, reactive=self._reactive)" in read(os.path.join("game", "shooting.py")))
c.true("ShootingController does NOT read Sumfin' to Prove",
       "sumfin_to_prove" not in read(os.path.join("game", "shooting.py")))
c.true("IngressController reads Da Jump's Deep Strike",
       "da_jump.grants_deep_strike(squad)" in read(os.path.join("game", "ingress.py")))
_agent = read(os.path.join("ai", "agent_driver.py"))
c.true("the AI's Movement handler asks Da Jump before its Ingress step",
       0 <= _agent.find("if _handle_da_jump(player, state, movement_controller, da_jump_controller, game_log):")
       < _agent.find("    # Rule 20.04 (Ingress move): deploy any of player's own strategic-"))

c.finish()
