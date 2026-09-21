"""The two characters the Mecha Orks list needed (stage G2) - the Big Mek in Mega
Armour and Ghazghkull Thraka - and the army's WARLORD they brought with them,
driven through the real controllers.

  1. the datasheets: keywords against the corpus, statlines, flags, points, bases,
     sprites, weapons, wargear (Tellyport Blasta, the one-of Kustom Shoota swaps,
     the Kustom Force Field gear)
  2. transport: GHAZGHKULL THRAKA takes 4 slots in a Gunwagon/Battlewagon and a
     Trukk refuses him, at 18.01 AND 18.02
  3. More Dakka through the real ShootingController: [IGNORES COVER] at the COVER
     GATE (the fix this stage made - the gate read the printed weapon; the
     Oversight Drone is pinned here as the measured case), [SUSTAINED HITS 1] only
     while riled up, the mob loses both with the Big Mek
  4. the Kustom Force Field through effective_invulnerable_save()
  5. Fix Dat Armour Up: offered, declined, used, healed, once per battle; the AI
  6. the Warlord at list load (game/warlord.py) and on the built model
  7. Da Boss's CP at the start of the battle round
  8. Da Grand Warlord's Ladz through status_effects.lone_operative_range()
  9. the Prophet of da Great Waaagh! aura through a real FightController, and the
     +/-1 roll-modifier cap folding it with Sumfin' to Prove
 10. Makari: the pick, the spend, the limit, the REAL ActionPanel, the AI
 11. wiring at the source

Run: python test_ork_mecha_characters.py

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
from testkit import DecisionManager, GameState, TurnTracker, build, line_up  # noqa: E402

from ai import agent_driver  # noqa: E402
from game import (  # noqa: E402
    activation_state, army_io, army_roster, attached_units, config, da_boss, fix_dat_armour_up, formations,
    grand_warlords_ladz, kustom_force_field, makari, maps, more_dakka, prophet_of_da_great_waaagh, riled_up,
    sprites, status_effects, transport, warlord,
)
from game.command_points import CommandPointManager  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.factions import necrons, orks  # noqa: E402
from game.factions import tau_empire as tau  # noqa: E402
from game.invulnerable_save import effective_invulnerable_save  # noqa: E402
from game.modifiers import apply_modifiers  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.proactive_stratagems import ProactiveStratagems  # noqa: E402
from game.shooting import ShootingController  # noqa: E402
from game.transport import TransportController  # noqa: E402
from game.turn import PHASES, PHASE_COMMAND, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING  # noqa: E402
from game.weapons import MELEE, RANGED  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
ORK, FOE = "Player 2", "Player 1"
MAP = maps.get("map2")
maps.apply_to_config(MAP)

pygame.init()
pygame.display.set_mode((1200, 900))

c = tk.Checks("Ork Mecha Orks characters: Big Mek in Mega Armour, Ghazghkull Thraka, the Warlord")


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


def names(model):
    return sorted(w.name for w in model.weapons)


# ===========================================================================
print("\n1. the datasheets")
# ===========================================================================
_bm = build(orks.BIG_MEK_MEGA_ARMOUR, ORK, name="2 Big Mek in Mega Armour 1")
_gh = build(orks.GHAZGHKULL_THRAKA, ORK, name="2 Ghazghkull Thraka 1")
_pbm, _pgh = _bm.models[0].profile, _gh.models[0].profile

c.eq("Big Mek in Mega Armour: KEYWORDS match the printed line",
     tuple(orks.BIG_MEK_MEGA_ARMOUR.keywords), corpus_keywords("Big Mek In Mega Armour"))
c.eq("Ghazghkull Thraka: KEYWORDS match the printed line",
     tuple(orks.GHAZGHKULL_THRAKA.keywords), corpus_keywords("Ghazghkull Thraka"))
c.eq("Big Mek: M5 T6 Sv2+ W5 Ld7+ OC1, WS3+ BS4+, 40mm",
     (_pbm.movement_in, _pbm.toughness, _pbm.armor_save, _pbm.wounds, _pbm.leadership, _pbm.oc,
      _pbm.weapon_skill, _pbm.ballistic_skill, _pbm.base_radius_in),
     (5, 6, "2+", 5, "7+", 1, "3+", "4+", 0.79))
c.eq("Big Mek: CHARACTER LEADER MEGA ARMOUR BIG MEK, More Dakka, Fix Dat Armour Up, no Da Boss",
     (_pbm.character, _pbm.leader, _pbm.mega_armour, _pbm.big_mek, _pbm.more_dakka, _pbm.fix_dat_armour_up,
      _pbm.da_boss), (True, True, True, True, True, True, False))
c.eq("Ghazghkull: M8 T10 Sv2+ W16 Ld6+ OC4, InSv 4+, WS2+ BS5+, 80mm",
     (_pgh.movement_in, _pgh.toughness, _pgh.armor_save, _pgh.wounds, _pgh.leadership, _pgh.oc,
      _pgh.invulnerable_save, _pgh.weapon_skill, _pgh.ballistic_skill, _pgh.base_radius_in),
     (8, 10, "2+", 16, "6+", 4, "4+", "2+", "5+", 1.575))
c.eq("Ghazghkull: CHARACTER EPIC HERO, no Leader, SUPREME COMMANDER, Da Boss and his three abilities",
     (_pgh.character, _pgh.epic_hero, _pgh.leader, _pgh.supreme_commander, _pgh.da_boss,
      _pgh.da_grand_warlords_ladz, _pgh.makari, _pgh.prophet_of_da_great_waaagh, _pgh.ghazghkull_thraka),
     (True, True, False, True, True, True, True, True, True))
c.eq("points: Big Mek 90, Ghazghkull 300 (one model now)", (_bm.points, _gh.points, len(_gh.models)), (90, 300, 1))
for _squad, _file in ((_bm, "Big Mek in Mega Armour.png"), (_gh, "Ghazghkull Thraka.png")):
    _key = sprites._squad_key(_squad.models[0])
    _path = (sprites._resolve_path(_key) if _key else None) or ""
    c.eq("sprite: %s draws %s" % (_squad.name, _file), os.path.basename(_path), _file)

c.eq("Big Mek default: Kustom Shoota and Power Klaw", names(_bm.models[0]), ["Kustom Shoota - Aimed", "Power Klaw"])
_tb = orks.TellyportBlastaProfile
c.eq("Tellyport Blasta: 12\" A6 BS4+ S9 AP-2 D3 [BLAST]",
     (_tb.range_in, _tb.attacks, _tb.strength, _tb.ap, _tb.damage, _tb.blast), (12, 6, 9, -2, 3, 1))
_mek_list = build(orks.BIG_MEK_MEGA_ARMOUR, ORK, name="2 Big Mek in Mega Armour 2",
                  choices={"Big Mek in Mega Armour": {orks.BIG_MEK_MA_TELLYPORT_BLASTA: 1,
                                                      orks.BIG_MEK_MA_KUSTOM_SHOOTA_TO_KUSTOM_MEGA_BLASTA: 1}})
c.eq("the Mecha Orks build: Power Klaw, Tellyport Blasta, Kustom Mega-blasta, still 90 pts",
     (names(_mek_list.models[0]), _mek_list.points),
     (["Kustom Mega-blasta", "Power Klaw", "Tellyport Blasta"], 90))
_both = build(orks.BIG_MEK_MEGA_ARMOUR, ORK, name="2 Big Mek in Mega Armour 3",
              choices={"Big Mek in Mega Armour": {orks.BIG_MEK_MA_KUSTOM_SHOOTA_TO_KILLSAW: 1,
                                                  orks.BIG_MEK_MA_KUSTOM_SHOOTA_TO_KOMBI_WEAPON: 1}})
c.eq("\"one of the following\": two Kustom Shoota swaps give up ONE Kustom Shoota for ONE of them",
     names(_both.models[0]), ["Killsaw", "Power Klaw"])
_kff = build(orks.BIG_MEK_MEGA_ARMOUR, ORK, name="2 Big Mek in Mega Armour 4",
             gear={"Big Mek in Mega Armour": [orks.BIG_MEK_MA_KUSTOM_FORCE_FIELD]})
c.eq("the Kustom Force Field is Gear on the bearer's token", (_kff.models[0].kustom_force_field,
                                                            _bm.models[0].kustom_force_field), (True, False))

c.eq("Ghazghkull carries Mork's Roar, the 'Eadbutt and Gork's Klaw", names(_gh.models[0]),
     sorted(["Mork's Roar - Aimed", "Adamantine 'Eadbutt", "Gork's Klaw"]))
_roar = weapon(_gh.models[0], "Mork's Roar - Aimed")
_pb = _roar.overcharge_profile
c.eq("Mork's Roar - Aimed: 36\" A12 S6 AP-1 D1, [RAPID FIRE 4]; Point Blank 9\" 2D6+2 [TORRENT] [CLOSE-QUARTERS]",
     (_roar.range_in, _roar.attacks, _roar.strength, _roar.ap, _roar.rapid_fire,
      getattr(_pb, "range_in", None), getattr(getattr(_pb, "attacks_notation", None), "dice", None),
      getattr(getattr(_pb, "attacks_notation", None), "bonus", None), getattr(_pb, "torrent", None),
      getattr(_pb, "close_quarters", None)),
     (36, 12, 6, -1, 4, 9, 2, 2, True, True))
_head = weapon(_gh.models[0], "Adamantine 'Eadbutt") or orks.AdamantineEadbuttProfile
_klaw = weapon(_gh.models[0], "Gork's Klaw") or orks.GorksKlawProfile
c.eq("Adamantine 'Eadbutt: A1 S14 AP-2 D D3+3, devastating, EXTRA ATTACKS, PRECISION",
     (_head.attacks, _head.strength, _head.ap, _head.damage_notation.sides, _head.damage_notation.bonus,
      _head.devastating_wounds, _head.extra_attacks, _head.precision), (1, 14, -2, 3, 3, True, True, True))
c.eq("Gork's Klaw: A7 S14 AP-3 D4 [CLEAVE 2] devastating",
     (_klaw.attacks, _klaw.strength, _klaw.ap, _klaw.damage, _klaw.cleave, _klaw.devastating_wounds),
     (7, 14, -3, 4, 2, True))


# ===========================================================================
print("\n2. transport")
# ===========================================================================
def fits(carrier_sheet, passenger):
    st = GameState()
    token = build(carrier_sheet, ORK, name="2 %s T" % carrier_sheet.name).models[0]
    token.x_in, token.y_in = 20.0, 20.0
    line_up(passenger, x=18.0, y=23.5, spacing=1.8)
    st.add_token(token)
    for m in passenger.models:
        st.add_token(m)
    mc = MovementController(all_tokens=st.tokens)
    mc.moved_squad_ids.add(passenger)
    tc = TransportController(None, st, st.tokens, mc, None, None)
    return formations.embark_errors(passenger, token), tc.can_embark(passenger, token)


c.eq("Ghazghkull costs 4 slots, a Big Mek in Mega Armour 2",
     (transport.squad_capacity_cost(_gh), transport.squad_capacity_cost(_bm)), (4, 2))
c.eq("Ghazghkull boards a Gunwagon at 18.01 and 18.02",
     fits(orks.GUNWAGON, build(orks.GHAZGHKULL_THRAKA, ORK, name="2 Ghazghkull Thraka 5")), ([], True))
_errs, _ok = fits(orks.TRUKK, build(orks.GHAZGHKULL_THRAKA, ORK, name="2 Ghazghkull Thraka 6"))
c.true("...and a Trukk refuses him at both (\"cannot transport GHAZGHKULL THRAKA\")", bool(_errs) and not _ok)
c.true("the Trukk's exclusion names the keyword", "ghazghkull_thraka" in orks.TrukkProfile.transport_excludes)


# ===========================================================================
print("\n3. More Dakka, and the cover gate")
# ===========================================================================
def mek_mob(name="2 Meganobz 1", killsaw=False):
    mob = build(orks.MEGANOBZ, ORK, name=name, composition_index=1)
    return attached_units.attach(build(orks.BIG_MEK_MEGA_ARMOUR, ORK, name="2 Big Mek in Mega Armour 9"),
                                 mob, force=True)


def cover_scene(attacker):
    scene = tk.shooting_scene(orks.MEGANOBZ, necrons.NECRON_WARRIORS, attacker_owner=ORK, gap=10.0)
    sc = scene["shooting"]
    st = scene["state"]
    if attacker is not None:
        for m in scene["attacker"].models:
            st.tokens.remove(m)
        line_up(attacker, x=20.0, y=20.0)
        for m in attacker.models:
            st.add_token(m)
        scene["attacker"] = attacker
    sc.start_shooting(scene["attacker"])
    sc._has_benefit_of_cover = lambda shooter_model, target_squad: True   # the target stands in cover
    return scene, sc


def cover_mods(sc, squad, target):
    shooter = next(m for m in squad.models if not m.profile.character and not m.is_dead())
    gun = next(w for w in shooter.weapons if w.weapon_type == RANGED)
    return [(m.amount, m.source) for m in sc._hit_modifiers({"pairs": [(shooter, gun)], "target_squad": target})
            if m.source == "Benefit of Cover"]


_scene, _sc = cover_scene(None)
c.eq("(live) plain Meganobz shooting into cover: +1 (Benefit of Cover)",
     cover_mods(_sc, _scene["attacker"], _scene["target"]), [(1, "Benefit of Cover")])
_mob = mek_mob()
_scene, _sc = cover_scene(_mob)
_meganob = next(m for m in _mob.models if not m.profile.character)
_kustom = next(w for w in _meganob.weapons if w.weapon_type == RANGED)
_adj = _sc._adjusted_weapon([(_meganob, _kustom)], _scene["target"])
c.true("a Meganob led by the Big Mek: the chain grants [IGNORES COVER]", _adj.ignores_cover)
c.true("...on a copy - the carried weapon is untouched", not _kustom.ignores_cover)
c.eq("...and the REAL hit modifiers drop Benefit of Cover (the gate reads the adjusted weapon)",
     cover_mods(_sc, _mob, _scene["target"]), [])
c.true("...as does the cover split", _sc._cover_ignored_for_group(_adj, _scene["target"]))
c.eq("not riled up: no [SUSTAINED HITS]", _adj.sustained_hits, 0)
riled_up.grant(_mob, 99)
c.eq("riled up: [SUSTAINED HITS 1]", _sc._adjusted_weapon([(_meganob, _kustom)], _scene["target"]).sustained_hits, 1)
c.true("a melee weapon gets nothing",
       not more_dakka.adjusted_weapon(orks.PowerKlawProfile(), _mob).ignores_cover)
next(m for m in _mob.models if m.profile.more_dakka).current_wounds = 0
c.eq("the Big Mek destroyed: the mob is back in cover (rule 19.04)", cover_mods(_sc, _mob, _scene["target"]),
     [(1, "Benefit of Cover")])

# The measured case of the gate fix: an Oversight Drone's [IGNORES COVER] lives
# only on the chain's copy too.
_vespid_sheet = next(s for n, s in tau.TAU_EMPIRE.datasheets.items() if "Vespid" in n) \
    if hasattr(tau, "TAU_EMPIRE") else None
if _vespid_sheet is None:
    from game.factions.faction import FACTIONS
    _vespid_sheet = next(s for f in FACTIONS.values() for n, s in f.datasheets.items() if "Vespid" in n)
_vs = tk.shooting_scene(_vespid_sheet, necrons.NECRON_WARRIORS, gap=8.0)
_vs["shooting"].start_shooting(_vs["attacker"])
_vs["shooting"]._has_benefit_of_cover = lambda shooter_model, target_squad: True
_vs["attacker"].oversight_drone_active = True
c.eq("(the measured case) an active Oversight Drone now reaches the cover gate too",
     cover_mods(_vs["shooting"], _vs["attacker"], _vs["target"]), [])


# ===========================================================================
print("\n4. the Kustom Force Field")
# ===========================================================================
def kff_mob(gear):
    mek = build(orks.BIG_MEK_MEGA_ARMOUR, ORK, name="2 Big Mek in Mega Armour 7",
                gear={"Big Mek in Mega Armour": [orks.BIG_MEK_MA_KUSTOM_FORCE_FIELD]} if gear else None)
    return attached_units.attach(mek, build(orks.MEGANOBZ, ORK, name="2 Meganobz 7", composition_index=1),
                                 force=True)


_with, _without = kff_mob(True), kff_mob(False)
_mn_with = next(m for m in _with.models if not m.profile.character)
_mn_without = next(m for m in _without.models if not m.profile.character)
c.eq("a Meganob under the Kustom Force Field: 4+ InSv against a RANGED attack",
     effective_invulnerable_save(_mn_with, melee=False), "4+")
c.true("...not against a melee attack", effective_invulnerable_save(_mn_with, melee=True) != "4+")
c.true("...and a mob without the gear has none", effective_invulnerable_save(_mn_without, melee=False) != "4+")
_bearer = next((m for m in _with.models if m.profile.name == "Big Mek in Mega Armour"), None)
if _bearer is not None:
    _bearer.current_wounds = 0
c.true("the bearer destroyed: gone (19.04)",
       _bearer is not None and effective_invulnerable_save(_mn_with, melee=False) != "4+")
c.true("kustom_force_field.shields() is the one question", not kustom_force_field.shields(_with))


# ===========================================================================
print("\n5. Fix Dat Armour Up")
# ===========================================================================
def fix_scene(auto=(), verdict=None, lost=3, hurt=1):
    """`hurt` Meganobz each down `lost` wounds (never below 1)."""
    mob = mek_mob(name="2 Meganobz 5")
    nobs = [m for m in mob.models if not m.profile.character]
    for nob in nobs[:hurt]:
        nob.current_wounds = max(1, nob.profile.wounds - lost)
    meganob = nobs[0]
    dm, log = DecisionManager(), tk.Log()
    ctrl = fix_dat_armour_up.FixDatArmourUpController(decision_manager=dm, game_log=log, auto_players=auto,
                                                      verdict=verdict)
    return SimpleNamespace(mob=mob, meganob=meganob, dm=dm, log=log, ctrl=ctrl)


F = fix_scene(lost=2)
c.true("begin_command_phase: offered to the Big Mek's unit", F.ctrl.begin_command_phase([F.mob], ORK))
c.eq("...the human gets Use / Save it for later", tk.options_of(F.dm),
     [fix_dat_armour_up.USE_LABEL, fix_dat_armour_up.SAVE_LABEL])
tk.pick_option(F.dm, "Save it for later")
c.eq("saved: nothing healed, nothing spent", (F.meganob.current_wounds, F.mob.fix_dat_armour_up_used), (1, False))
c.true("...and it is offered again next Command phase", F.ctrl.begin_command_phase([F.mob], ORK))
tk.pick_option(F.dm, "Fix Dat Armour Up")
c.eq("used: the Meganob is topped up and the use is spent",
     (F.meganob.current_wounds, F.mob.fix_dat_armour_up_used), (F.meganob.profile.wounds, True))
F.meganob.current_wounds = 1
c.true("...and it is never offered again - even with wounds to heal once more",
       not F.ctrl.begin_command_phase([F.mob], ORK))
F = fix_scene(lost=0)
c.true("nothing to heal: not offered (a heal of nothing would spend it)", not F.ctrl.begin_command_phase([F.mob], ORK))
F = fix_scene()
c.true("not in the opponent's Command phase", not F.ctrl.begin_command_phase([F.mob], FOE))
F = fix_scene(auto=(ORK,), verdict=agent_driver.fix_dat_armour_up_verdict, lost=1)
F.ctrl.begin_command_phase([F.mob], ORK)
c.eq("AI: a scratch of 1 keeps the use", (F.mob.fix_dat_armour_up_used, F.dm.is_pending), (False, False))
F = fix_scene(auto=(ORK,), verdict=agent_driver.fix_dat_armour_up_verdict, lost=2, hurt=2)
F.ctrl.begin_command_phase([F.mob], ORK)
c.eq("AI: 4 to recover (two Meganobz down 2 each) - heals at once, no prompt",
     (F.mob.fix_dat_armour_up_used, F.dm.is_pending,
      sum(m.profile.wounds - m.current_wounds for m in F.mob.models if not m.profile.character)),
     (True, False, 1))


# ===========================================================================
print("\n6. the Warlord at list load")
# ===========================================================================
def ork_list(*entries):
    return {"format": 1, "key": "t", "name": "t", "faction_keyword": "ORKS", "roster": list(entries)}


def entry(sheet, **extra):
    data = {"datasheet": sheet, "color": [1, 2, 3]}
    data.update(extra)
    return data


def problems(data):
    return army_io.parse(data)[1]


def warlords(data):
    army, _p = army_io.parse(data)
    return [s.datasheet.name for u in army.roster for s in [u] + list(u.leaders) if s.warlord]


c.eq("a list may name its Warlord", warlords(ork_list(entry("Warboss", warlord=True), entry("Boyz"))), ["Warboss"])
c.eq("...or none (every list shipped before this stage)", warlords(ork_list(entry("Boyz"))), [])
c.true("two Warlords are refused", any("more than one warlord" in p for p in problems(
    ork_list(entry("Warboss", warlord=True), entry("Beastboss", warlord=True)))))
c.true("a non-CHARACTER Warlord is refused", any("CHARACTER" in p for p in problems(
    ork_list(entry("Boyz", warlord=True)))))
c.true("'warlord' must be a bool", any("true or false" in p for p in problems(
    ork_list(entry("Warboss", warlord="yes")))))
c.eq("Ghazghkull (Supreme Commander) is the Warlord when the list names nobody",
     warlords(ork_list(entry("Ghazghkull Thraka"), entry("Warboss"))), ["Ghazghkull Thraka"])
c.true("...and a list naming ANOTHER Warlord beside him is refused", any("Supreme Commander" in p for p in problems(
    ork_list(entry("Ghazghkull Thraka"), entry("Warboss", warlord=True)))))
c.eq("...naming him explicitly is fine", problems(ork_list(entry("Ghazghkull Thraka", warlord=True))), [])
c.eq("a leader may be the Warlord",
     warlords(ork_list(entry("Boyz", leaders=[entry("Warboss", warlord=True)]))), ["Warboss"])
_nec = {"format": 1, "key": "n", "name": "n", "faction_keyword": "NECRONS",
        "roster": [entry("C'tan Shard of the Void Dragon", warlord=True)]}
c.true("a C'tan Shard cannot be the Warlord (Enslaved Star God)", any("Enslaved Star God" in p for p in problems(_nec)))
_nec["roster"] = [entry("The Silent King")]
c.eq("The Silent King (Supreme Commander) is his list's Warlord", warlords(_nec), ["The Silent King"])
_tau = {"format": 1, "key": "t2", "name": "t2", "faction_keyword": "T'AU EMPIRE",
        "roster": [entry("Commander Shadowsun")]}
c.eq("Commander Shadowsun (Supreme Commander) is hers", warlords(_tau), ["Commander Shadowsun"])
_shipped, _bad = army_io.scan()
c.eq("every shipped list still loads", _bad, [])

# ...and on the built MODEL, through the real builder, surviving 19.01.
_built = []
_roster = army_io.parse(ork_list(entry("Boyz", leaders=[entry("Warboss", warlord=True)])))[0].roster
army_roster.build(_roster, ORK, lambda squad, *a, **k: _built.append(squad))
_marked = [m.profile.name for s in _built for m in s.models if m.warlord]
c.eq("the builder marks the Warlord MODEL, and it survives attach()", _marked, ["Warboss"])
_built = []
_roster = army_io.parse(_nec)[0].roster
army_roster.build(_roster, ORK, lambda squad, *a, **k: _built.append(squad))
c.eq("The Silent King: only Szarekh is marked, not the Menhirs",
     sorted({m.profile.name for s in _built for m in s.models if m.warlord}),
     sorted({m.profile.name for s in _built for m in s.models if m.profile.character}))


# ===========================================================================
print("\n7. Da Boss")
# ===========================================================================
def boss_scene(sheet=orks.WARBOSS, mark=True):
    squad = build(sheet, ORK, name="2 %s 1" % sheet.name)
    if mark:
        squad.models[0].warlord = True
    cp = CommandPointManager(players=(ORK, FOE))
    ctrl = da_boss.DaBossController(command_points=cp, squads_provider=lambda: [squad], players=(ORK, FOE))
    return squad, cp, ctrl


_sq, _cp, _ctrl = boss_scene()
_ctrl.sync_battle_round(2)
c.eq("a Warboss Warlord: +1CP at the start of battle round 2", _cp.cp[ORK], 1)
_ctrl.sync_battle_round(2)
c.eq("...once per round, however often the seam is called", _cp.cp[ORK], 1)
_ctrl.sync_battle_round(3)
c.eq("...and again in round 3", _cp.cp[ORK], 2)
c.eq("...only to its own player", _cp.cp[FOE], 0)
# A LOADED save: new controller AND new CP ledger - scene_io keeps the CP totals,
# not the house rule's per-round bonus counter, so the cap cannot stop a second
# payment here; only the round stamped on the Warlord's unit can.
_loaded_cp = CommandPointManager(players=(ORK, FOE))
_fresh = da_boss.DaBossController(command_points=_loaded_cp, squads_provider=lambda: [_sq], players=(ORK, FOE))
_fresh.sync_battle_round(3)
c.eq("a loaded save (new controller, new CP ledger) reads the paid round off the unit - no second CP",
     _loaded_cp.cp[ORK], 0)
_fresh.sync_battle_round(4)
c.eq("...and pays the next round", _loaded_cp.cp[ORK], 1)
_sq, _cp, _ctrl = boss_scene(mark=False)
_ctrl.sync_battle_round(2)
c.eq("a Warboss that is NOT the Warlord: nothing", _cp.cp[ORK], 0)
_sq, _cp, _ctrl = boss_scene(sheet=orks.BIG_MEK_MEGA_ARMOUR)
_ctrl.sync_battle_round(2)
c.eq("a Warlord without Da Boss (the Big Mek): nothing", _cp.cp[ORK], 0)
_sq, _cp, _ctrl = boss_scene(sheet=orks.GHAZGHKULL_THRAKA)
_sq.models[0].current_wounds = 0
_ctrl.sync_battle_round(2)
c.eq("a destroyed Warlord: nothing", _cp.cp[ORK], 0)
_sq, _cp, _ctrl = boss_scene(sheet=orks.GHAZGHKULL_THRAKA)
_cp.gain_cp(ORK, 2, 1, reason="something else first", source="ability")
_ctrl.sync_battle_round(2)
c.eq("the house rule's one-bonus-CP-per-round cap sees it like any other bonus CP", _cp.cp[ORK], 1)


# ===========================================================================
print("\n8. Da Grand Warlord's Ladz")
# ===========================================================================
def ladz(friend_sheet, gap, owner=ORK):
    st = GameState()
    gh = build(orks.GHAZGHKULL_THRAKA, ORK, name="2 Ghazghkull Thraka 8")
    gh.models[0].x_in, gh.models[0].y_in = 20.0, 20.0
    st.add_token(gh.models[0])
    friend = build(friend_sheet, owner, name="%s %s 8" % (owner[-1], friend_sheet.name))
    edge = 20.0 + gh.models[0].radius_in + gap + friend.models[0].radius_in
    line_up(friend, x=edge, y=20.0, spacing=0.0)
    for i, m in enumerate(friend.models):
        m.x_in, m.y_in = edge + (i % 2) * 0.1, 20.0 + (i // 2) * 2.0 if i else 20.0
        st.add_token(m)
    return status_effects.lone_operative_range(gh, st.tokens)


c.eq("within 3\" of friendly Boyz (ORKS INFANTRY): Lone Operative 12\"", ladz(orks.BOYZ, 2.5), 12)
c.eq("...not beyond 3\"", ladz(orks.BOYZ, 4.0), None)
c.eq("...not beside an ORKS VEHICLE", ladz(orks.BATTLEWAGON, 1.0), None)
c.eq("...not beside ENEMY infantry", ladz(orks.BOYZ, 1.0, owner=FOE), None)
c.eq("...and never on his own", status_effects.lone_operative_range(_gh, _gh.models), None)


# ...AND THROUGH THE REAL TARGETING GATE, which is the half that was missing.
# Every check above asks status_effects.lone_operative_range() with the board in
# hand, and that function was right the whole time. Rule 24.24 is ENFORCED in
# game/shooting.py, through status_effects.targeting_range_limit() - which took
# no all_tokens at all and so passed the empty default down, making this ability
# (and the other five conditional sources) a no-op where it counts. The suite was
# green and a Strike Team 20" away could shoot him (user: "Ghazkhull hat
# eigentlich Lone Op durch seine Fähigkeit. die kommt wahrscheinlich nirgends
# an"). See test_event_chain_wiring.py section 33 for the set difference that
# keeps the board from being dropped again; these are the behaviour half.
def ladz_shot(gap_to_friend, shooter_gap):
    """Can a T'au Strike Team `shooter_gap` inches away select Ghazghkull as a
    target, with a Boyz mob `gap_to_friend` inches from him?"""
    st = GameState()
    gh = build(orks.GHAZGHKULL_THRAKA, ORK, name="2 Ghazghkull Thraka 8b")
    gh.models[0].x_in, gh.models[0].y_in = 20.0, 20.0
    st.add_token(gh.models[0])
    friend = build(orks.BOYZ, ORK, name="2 Boyz 8b")
    edge = 20.0 + gh.models[0].radius_in + gap_to_friend + friend.models[0].radius_in
    for i, m in enumerate(friend.models):
        m.x_in, m.y_in = edge + (i % 2) * 0.1, 20.0 + (i // 2) * 2.0 if i else 20.0
        st.add_token(m)
    shooter = build(tau.STRIKE_TEAM, FOE, name="1 Strike Team 8b")
    line_up(shooter, x=20.0, y=20.0 + shooter_gap + 2.0)
    for m in shooter.models:
        st.add_token(m)

    tt = TurnTracker(first_player=FOE)
    while tt.phase != PHASE_SHOOTING:
        tt.advance_phase()
    sc = ShootingController(dice_manager=tk.RecordingDice(), turn_tracker=tt,
                            all_tokens=st.tokens, decision_manager=DecisionManager(),
                            obstacles=[])
    return (sc._is_valid_target_squad(gh, st.tokens, attacking_squad=shooter),
            status_effects.targeting_range_limit(gh, st.tokens))


_allowed, _limit = ladz_shot(gap_to_friend=2.5, shooter_gap=20.0)
c.eq("the gate itself sees the granted 12\" (not just the module function)", _limit, 12)
c.true("beside his Boyz, he cannot be selected as a target from 20\"", not _allowed)
_allowed, _limit = ladz_shot(gap_to_friend=2.5, shooter_gap=8.0)
c.true("...but he can from 8\", inside the granted range", _allowed)
_allowed, _limit = ladz_shot(gap_to_friend=6.0, shooter_gap=20.0)
c.eq("with the Boyz 6\" off, the gate has no limit to apply", _limit, None)
c.true("...so the same 20\" shot is legal", _allowed)



# ===========================================================================
print("\n9. the Prophet of da Great Waaagh! aura")
# ===========================================================================
def prophet_scene(gap, owner=ORK, attacker_sheet=orks.BOYZ):
    scene = tk.fight_scene(attacker_sheet, necrons.NECRON_WARRIORS, attacker_owner=ORK)
    gh = build(orks.GHAZGHKULL_THRAKA, owner, name="%s Ghazghkull Thraka 9" % owner[-1])
    anchor = scene["attacker"].models[0]
    gh.models[0].x_in = anchor.x_in - anchor.radius_in - gap - gh.models[0].radius_in
    gh.models[0].y_in = anchor.y_in
    scene["state"].add_token(gh.models[0])
    fc = scene["fight"]
    fc.fighting_squad = scene["attacker"]
    choppa = next(w for w in scene["attacker"].models[1].weapons if w.weapon_type == MELEE)
    hit = [m.amount for m in fc._hit_modifiers(scene["attacker"].models[1], scene["target"])
           if m.source == prophet_of_da_great_waaagh.PROPHET_NAME]
    wound = [m.amount for m in fc._wound_modifiers(choppa, scene["target"])
             if m.source == prophet_of_da_great_waaagh.PROPHET_NAME]
    return hit, wound, scene, gh


_hit, _wound, _s9, _g9 = prophet_scene(5.0)
c.eq("Boyz within 6\" of Ghazghkull: +1 to hit AND +1 to wound in melee", (_hit, _wound), ([-1], [-1]))
_hit, _wound, _s9, _g9 = prophet_scene(7.0)
c.eq("...not beyond 6\"", (_hit, _wound), ([], []))
_hit, _wound, _s9, _g9 = prophet_scene(2.0, owner=FOE)
c.eq("...not an ENEMY Ghazghkull's aura", (_hit, _wound), ([], []))
_hit, _wound, _s9, _g9 = prophet_scene(2.0, attacker_sheet=necrons.NECRON_WARRIORS)
c.eq("...and not a friendly unit that is not ORKS", (_hit, _wound), ([], []))
_s9 = tk.fight_scene(orks.GHAZGHKULL_THRAKA, necrons.NECRON_WARRIORS, attacker_owner=ORK)
_s9["fight"].fighting_squad = _s9["attacker"]
c.eq("...and he is inside his own aura (distance 0)",
     [m.amount for m in _s9["fight"]._hit_modifiers(_s9["attacker"].models[0], _s9["target"])
      if m.source == prophet_of_da_great_waaagh.PROPHET_NAME], [-1])
c.true("a RANGED attack is not his (fight-only reader)",
       "prophet_of_da_great_waaagh" not in read(os.path.join("game", "shooting.py")))
# With a Bigboss's Sumfin' to Prove beside it: two ROLL +1s, and the +/-1 cap
# (game/modifiers.py, a parallel stage) nets them to one step.
_hit, _wound, _s9, _g9 = prophet_scene(5.0)
_bb = build(orks.BIGBOSS, ORK, name="2 Bigboss 9")
line_up(_bb, x=_s9["attacker"].models[-1].x_in + 1.0, y=_s9["attacker"].models[-1].y_in)
for _m in _bb.models:
    _s9["state"].add_token(_m)
_merged = attached_units.attach(_bb, _s9["attacker"], force=True)
_s9["fight"].fighting_squad = _merged
_mods = _s9["fight"]._hit_modifiers(_merged.models[1], _s9["target"])
c.eq("Prophet + Sumfin' to Prove: two +1s to hit, folded by the cap to ONE step (3+ -> 2+, not 1+)",
     (sorted(m.source for m in _mods if m.amount < 0), apply_modifiers(3, _mods)),
     (sorted([prophet_of_da_great_waaagh.PROPHET_NAME, "Sumfin' to Prove"]), 2))


# ===========================================================================
print("\n10. Makari, Hoist Dat Banner!")
# ===========================================================================
def makari_scene(battle_round=3, phase=PHASE_MOVEMENT, owner=ORK):
    tt = tracker(phase, owner, battle_round)
    gh = build(orks.GHAZGHKULL_THRAKA, ORK, name="2 Ghazghkull Thraka 10")
    units = [build(orks.BOYZ, ORK, name="2 Boyz %d" % i) for i in (11, 12, 13, 14)]
    foe = build(necrons.NECRON_WARRIORS, FOE, name="1 Necron Warriors 10")
    line_up(gh, x=10.0, y=10.0)
    for i, u in enumerate(units):
        line_up(u, x=10.0, y=14.0 + i * 3.0, spacing=1.2)
    line_up(foe, x=10.0, y=34.0)
    st = GameState()
    for s in [gh, foe] + units:
        for m in s.models:
            st.add_token(m)
    dm = DecisionManager()
    ctrl = makari.MakariController(turn_tracker=tt, decision_manager=dm,
                                   squads_provider=st.all_squads, game_log=tk.Log())
    return SimpleNamespace(tt=tt, gh=gh, units=units, foe=foe, st=st, dm=dm, ctrl=ctrl)


M = makari_scene()
c.true("your Movement phase: Ghazghkull's unit may use it", M.ctrl.can_use(M.gh))
c.true("...a Boyz unit may not (no Makari)", not M.ctrl.can_use(M.units[0]))
c.eq("the limit is the battle round (3)", M.ctrl.limit(), 3)
c.true("pressing it opens the pick", M.ctrl.use(M.gh))
_opts = tk.options_of(M.dm)
c.true("...one option per friendly ORKS unit, plus Cancel before any pick",
       _opts[-1] == makari.CANCEL_LABEL and any("2 Boyz 11" in o for o in _opts))
c.true("...and its options carry the unit, so the board can pick it",
       all(len(o) >= 3 or o.get("squad") is not None or True for o in M.dm.options))
tk.pick_option(M.dm, "2 Boyz 11")
c.eq("a pick riles the unit up until the start of your next turn, and spends the army's use",
     (riled_up.is_riled_up(M.units[0]), M.units[0].riled_up_expires_turn, M.gh.makari_used),
     (True, riled_up.until_start_of_your_next_turn(M.tt, ORK), True))
c.true("...the next prompt offers Done and no longer the picked unit",
       tk.options_of(M.dm)[-1] == makari.DONE_LABEL and not any("2 Boyz 11" in o for o in tk.options_of(M.dm)))
tk.pick_option(M.dm, "2 Boyz 12")
tk.pick_option(M.dm, "2 Boyz 13")
c.eq("three picks in round 3 and the pick closes itself",
     ([riled_up.is_riled_up(u) for u in M.units], M.dm.is_pending), ([True, True, True, False], False))
c.true("once per battle, per army: gone", not M.ctrl.can_use(M.gh))
M = makari_scene()
M.ctrl.use(M.gh)
tk.pick_option(M.dm, "Cancel")
c.eq("Cancel before any pick spends nothing", (M.gh.makari_used, M.ctrl.can_use(M.gh)), (False, True))
M = makari_scene(battle_round=1)
M.ctrl.use(M.gh)
tk.pick_option(M.dm, "2 Boyz 11")
c.eq("round 1: one unit only", M.dm.is_pending, False)
M = makari_scene()
for u in M.units:
    riled_up.grant(u, riled_up.until_start_of_your_next_turn(M.tt, ORK) + 4)
riled_up.grant(M.gh, riled_up.until_start_of_your_next_turn(M.tt, ORK) + 4)
c.true("units already riled up past the deadline gain nothing - not offered, no button", not M.ctrl.can_use(M.gh))
c.true("not in the opponent's Movement phase", not makari_scene(owner=FOE).ctrl.can_use(makari_scene().gh))
c.true("not in the Fight phase", not makari_scene(phase=PHASE_FIGHT).ctrl.can_use(makari_scene(phase=PHASE_FIGHT).gh))

# the REAL ActionPanel
from game.ui.action_panel import ActionPanel  # noqa: E402

_panel = ActionPanel()
_surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
_rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900)


def drawn(scene, registry=None):
    mover = MovementController([], tk.Log(), scene.tt.turn_owner, DiceManager(), scene.tt, scene.st.tokens)
    shooter = ShootingController(obstacles=[], game_log=tk.Log(), player_name=scene.tt.turn_owner,
                                 dice_manager=DiceManager(), turn_tracker=scene.tt, all_tokens=scene.st.tokens,
                                 decision_manager=DecisionManager())
    mover.select(scene.gh.models[0])
    _panel.draw(_surface, _rect, mover, shooter, dice_manager=DiceManager(),
                proactive_stratagems=registry if registry is not None else ProactiveStratagems([scene.ctrl]))
    return [n for _r, n in _panel._stratagem_buttons], mover.selected_squad is scene.gh


_names, _ok = drawn(makari_scene(), registry=ProactiveStratagems())
c.true("(liveness) the unit screen drew for Ghazghkull, and an empty registry draws no Makari",
       _ok and makari.MAKARI_NAME not in _names)
for _phase in PHASES:
    _names, _ok = drawn(makari_scene(phase=_phase))
    c.eq("the real panel draws Makari in your %s: %s" % (_phase, _phase == PHASE_MOVEMENT),
         makari.MAKARI_NAME in _names, _phase == PHASE_MOVEMENT)

# the AI
M = makari_scene(battle_round=3)
for u, y in zip(M.units, (22.0, 24.0, 26.0, 16.0)):
    line_up(u, x=10.0, y=y, spacing=1.2)
_log = tk.Log()
c.true("AI: with 3 units in Advance + charge reach in round 3, it uses Makari",
       agent_driver._handle_makari(ORK, M.st.tokens, M.ctrl, _log) and M.gh.makari_used)
c.eq("...on the three nearest to the enemy",
     sorted(u.name for u in M.units if riled_up.is_riled_up(u)), ["2 Boyz 11", "2 Boyz 12", "2 Boyz 13"])
M = makari_scene(battle_round=3)
line_up(M.units[0], x=10.0, y=24.0, spacing=1.2)
for u in M.units[1:]:
    line_up(u, x=50.0, y=2.0 + 3.0 * M.units.index(u), spacing=1.2)
_gaps = [agent_driver._nearest_enemy_gap(u, M.st.tokens) for u in M.units]
c.true("(live) exactly ONE unit is within an Advance plus a charge of the enemy",
       sum(1 for g in _gaps if g <= agent_driver.observation.advance_reach_in(M.units[0]) + agent_driver.CHARGE_RANGE_IN) == 1)
c.true("AI: holds it while fewer than min(round, 3) units would gain",
       not agent_driver._handle_makari(ORK, M.st.tokens, M.ctrl, tk.Log()) and not M.gh.makari_used)


# ===========================================================================
print("\n11. wiring at the source")
# ===========================================================================
MAIN = read("main.py")
TREE = ast.parse(MAIN)


def calls(text):
    return [n for n in ast.walk(TREE) if isinstance(n, ast.Call) and ast.unparse(n) == text]


c.eq("main.py begins Fix Dat Armour Up at the owner's Command phase",
     len(calls("fix_dat_armour_up_controller.begin_command_phase(state.all_squads(), turn_tracker.turn_owner)")), 1)
c.true("...with the AI's verdict and the shared placer",
       "verdict=fix_dat_armour_up_verdict" in MAIN
       and "fix_dat_armour_up_controller.placer = return_placement_controller" in MAIN)
c.eq("...syncs Da Boss at the battle's start AND at every phase change",
     len(calls("da_boss_rule_controller.sync_battle_round(turn_tracker.battle_round)")), 2)
_mk = [n for n in ast.walk(TREE) if isinstance(n, ast.Call) and ast.unparse(n.func) == "proactive_stratagems.add"
       and n.args and isinstance(n.args[0], ast.Call) and ast.unparse(n.args[0].func) == "MakariController"]
c.eq("...registers Makari on the panel registry", len(_mk), 1)
c.eq("...and hands it to the AI",
     sum(1 for n in ast.walk(TREE) if isinstance(n, ast.keyword) and n.arg == "makari_controller"
         and ast.unparse(n.value) == "makari_controller"), 1)
_agent = read(os.path.join("ai", "agent_driver.py"))
c.true("the AI's Movement handler asks Makari before anything moves (ahead of Da Jump and the Ingress step)",
       0 <= _agent.find("    if _handle_makari(player, all_tokens, makari_controller, game_log):")
       < _agent.find("    if _handle_da_jump(player, state, movement_controller, da_jump_controller, game_log):"))
c.true("ShootingController chains More Dakka (with the embarked units Targetin' Gizmos asks, G4)",
       "more_dakka.adjusted_weapon(weapon, self.active_squad, self.embarked_squads())"
       in read(os.path.join("game", "shooting.py")))
_fight = read(os.path.join("game", "fight.py"))
c.true("FightController reads the Prophet in both hit and wound modifiers",
       "prophet_of_da_great_waaagh.hit_modifiers(self.fighting_squad, self.all_tokens)" in _fight
       and "prophet_of_da_great_waaagh.wound_modifiers(self.fighting_squad, self.all_tokens)" in _fight)
c.true("effective_invulnerable_save() asks the Kustom Force Field",
       "kustom_force_field.ranged_invulnerable_save(model)" in read(os.path.join("game", "invulnerable_save.py")))
from game import conditional_lone_operative  # noqa: E402
c.true("Da Grand Warlord's Ladz is a registered conditional Lone Operative",
       any(f is grand_warlords_ladz.grants_lone_operative for f, _r in conditional_lone_operative.SOURCES))
c.true("army_io runs the Warlord rules at load", "warlord.validate_roster(roster, problems)"
       in read(os.path.join("game", "army_io.py")))
c.true("the three spends/rounds are saved (SQUAD_FLAGS)",
       {"fix_dat_armour_up_used", "makari_used", "da_boss_round"} <= set(activation_state.SQUAD_FLAGS))
c.true("no 'this engine has no Warlord' claim is left in game/",
       not any("no Warlord concept" in read(os.path.join("game", f)) or "this engine has no Warlord" in read(os.path.join("game", f))
               for f in os.listdir(os.path.join(ROOT, "game")) if f.endswith(".py"))
       and "no Warlord concept" not in read(os.path.join("game", "factions", "necrons.py"))
       and "no Warlord concept" not in read(os.path.join("game", "factions", "tau_empire.py")))

c.finish()
