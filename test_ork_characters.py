"""The 2026-09 Ork codex's characters (stage E3b): Warboss, Warboss in Mega
Armour, Beastboss, Painboy.

Run: python test_ork_characters.py

Every ability through the real controller or seam that reads it:
  * Boss' Ammo Runt (game/boss_ammo_runt.py) through a real ShootingController -
    offered at start_shooting(), +1 to hit for the WARBOSS's group only, its own
    once-per-battle use beside the Boyz' Ammo Runts;
  * Might Is Right (game/might_is_right.py) through the real fight adjuster chain
    and the per-model attack key;
  * Dodge Dis! (game/dodge_dis.py) in BOTH _hit_modifiers(), gone with its Beastboss;
  * Intimidating Motivation / Keep Huntin'! (game/boss_motivation.py) - the two
    windows, the SHARED per-army budget and the separate one, the candidate filter,
    the board pick with a Cancel that spends nothing, the AI through the move
    hooks of a real MovementController, and the button on the real ActionPanel;
  * Krushin' Impetus (game/krushin_impetus.py) - one D6 per ENGAGED model, 3+ each
    a mortal wound, the 06.02 allocation drained to the last wound;
  * Crude Surgery / Catch Dat Red Bit (game/crude_surgery.py) on core rule
    02.02.04 (game/heal.py) - heal first, revive non-CHARACTERs, a human places the
    revived model, a unit off the board heals off the board, the Red Bit offered
    only when it can land.
Plus the datasheets, the extraction (reanimation_protocols re-exports game/heal.py),
the retirements, the AI's two answers and main.py's wiring at the source.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import ast                                                           # noqa: E402
import io                                                            # noqa: E402

import pygame                                                        # noqa: E402

import testkit as tk                                                 # noqa: E402
from testkit import (Checks, GameState, RecordingDice, build, fight_scene,  # noqa: E402
                     line_up, options_of, pick_option, script, shooting_scene)

from ai import agent_driver                                          # noqa: E402
from ai.agent_driver import (CATCH_DAT_RED_BIT_MIN_HEALABLE, boss_motivation_choice,  # noqa: E402
                             catch_dat_red_bit_verdict)
from game import (activation_state, boss_ammo_runt, boss_motivation, config,  # noqa: E402
                  crude_surgery, dodge_dis, heal, krushin_impetus, might_is_right,
                  ork_ammo_runts, reanimation_protocols, riled_up, setup as setup_mod,
                  unit_pick)
from game import squad as squad_mod                                  # noqa: E402
from game import weapons as weapons_mod                              # noqa: E402
from game.attached_units import attach, attachment_role, can_attach, LEADER, SUPPORT  # noqa: E402
from game.decision import DecisionManager                            # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.dice_notation import DiceNotation                          # noqa: E402
from game.factions import build_squad                                # noqa: E402
from game.factions import orks as ork                                # noqa: E402
from game.factions.tau_empire import STRIKE_TEAM                     # noqa: E402
from game.fight import _melee_attack_key                             # noqa: E402
from game.movement import MovementController                         # noqa: E402
from game.per_army_round_limit import PerArmyRoundLimit              # noqa: E402
from game.proactive_stratagems import ProactiveStratagems            # noqa: E402
from game.return_placement import ReturnPlacementController          # noqa: E402
from game.setup import SetupController                               # noqa: E402
from game.shooting import ShootingController, _attack_key            # noqa: E402
from game.token import Token                                         # noqa: E402
from game.turn import PHASES, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker  # noqa: E402
from game.ui.action_panel import ActionPanel                         # noqa: E402
from game.units import UnitProfile                                   # noqa: E402

c = Checks("Ork characters (2026-09 codex)")
HERE = os.path.dirname(os.path.abspath(__file__))
HUMAN, FOE = "Player 1", "Player 2"


def mods(modifiers, label):
    out = []
    for m in modifiers:
        text = next((getattr(m, a) for a in ("label", "reason", "source", "name")
                     if isinstance(getattr(m, a, None), str)), None)
        if text == label:
            out.append((m.amount, text))
    return out


def weapon_named(model, name):
    return next((w for w in model.weapons if w.name == name), None)


def bearer(squad, flag):
    return next((m for m in squad.models if getattr(m.profile, flag, False)), None)


def tracker(phase, owner=HUMAN, battle_round=2):
    tt = TurnTracker(first_player=owner)
    tt.started = True
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = owner
    tt.set_active(owner)
    tt.battle_round = battle_round
    return tt


def place(squad, x, y, spacing=2.1, per_row=6):
    for i, model in enumerate(squad.models):
        r, col = divmod(i, per_row)
        model.x_in, model.y_in = x + col * spacing, y + r * spacing
    return squad


# ===========================================================================
print("\n1. the four datasheets")
# ===========================================================================
_wb = build(ork.WARBOSS, HUMAN, name="1 Warboss 1")
_wbm = build(ork.WARBOSS_MEGA_ARMOUR, HUMAN, name="1 Warboss in Mega Armour 1")
_bb = build(ork.BEASTBOSS, HUMAN, name="1 Beastboss 1")
_pb = build(ork.PAINBOY, HUMAN, name="1 Painboy 1")

c.eq("Warboss loadout", sorted(w.name for w in _wb.models[0].weapons), ["Kustom Choppa", "Kustom Shoota"])
c.eq("Warboss in Mega Armour loadout", sorted(w.name for w in _wbm.models[0].weapons), ["'Uge Choppa", "Big Shoota"])
c.eq("Beastboss loadout", sorted(w.name for w in _bb.models[0].weapons),
     ["Beast Snagga Klaw and Beastchoppa", "Shoota"])
c.eq("Painboy loadout", sorted(w.name for w in _pb.models[0].weapons), ["'Urty Syringe", "Dok's Toolz"])
for _label, _opt, _want in (("Power Klaw", ork.WARBOSS_KUSTOM_CHOPPA_TO_POWER_KLAW, ["Kustom Shoota", "Power Klaw"]),
                            ("Kombi-rokkit", ork.WARBOSS_KUSTOM_SHOOTA_TO_KOMBI_ROKKIT,
                             ["Kombi-rokkit - Busta Rokkit", "Kustom Choppa"]),
                            ("Kombi-skorcha", ork.WARBOSS_KUSTOM_SHOOTA_TO_KOMBI_SKORCHA,
                             ["Kombi-skorcha - Shoota", "Kustom Choppa"])):
    _s = build(ork.WARBOSS, HUMAN, name="wb %s" % _label, choices={"Warboss": {_opt: 1}})
    c.eq("the Warboss's %s swap" % _label, sorted(w.name for w in _s.models[0].weapons), _want)
_klaw = weapon_named(build(ork.WARBOSS, HUMAN, name="wbk",
                           choices={"Warboss": {ork.WARBOSS_KUSTOM_CHOPPA_TO_POWER_KLAW: 1}}).models[0], "Power Klaw")
c.eq("...and his Power Klaw is HIS row (A6 S12), not the Nobs' A3 S10", (_klaw.attacks, _klaw.strength), (6, 12))

c.eq("points: Warboss 100", _wb.points, 100)
c.eq("points: Beastboss 85", _bb.points, 85)
c.eq("points: Painboy 45", _pb.points, 45)
c.eq("points: Warboss in Mega Armour 125, 125, then 140 for a third",
     [build_squad(ork.WARBOSS_MEGA_ARMOUR, HUMAN, name="w%d" % i, unit_index=i).points for i in (1, 2, 3)],
     [125, 125, 140])

_p = {s: s.models[0].profile for s in (_wb, _wbm, _bb, _pb)}
c.eq("Warboss statline M/T/W/Sv/InSv/WS/BS", tuple(getattr(_p[_wb], a) for a in
     ("movement_in", "toughness", "wounds", "armor_save", "invulnerable_save", "weapon_skill", "ballistic_skill")),
     (6, 6, 6, "4+", "5+", "2+", "5+"))
c.eq("Warboss in Mega Armour statline", tuple(getattr(_p[_wbm], a) for a in
     ("movement_in", "toughness", "wounds", "armor_save", "invulnerable_save", "weapon_skill", "ballistic_skill")),
     (5, 7, 7, "2+", "5+", "2+", "4+"))
c.eq("Beastboss statline (+FNP 6+)", tuple(getattr(_p[_bb], a) for a in
     ("movement_in", "toughness", "wounds", "armor_save", "invulnerable_save", "feel_no_pain")),
     (6, 6, 6, "4+", "5+", "6+"))
c.eq("Painboy statline", tuple(getattr(_p[_pb], a) for a in
     ("movement_in", "toughness", "wounds", "armor_save", "weapon_skill")), (6, 5, 3, "5+", "3+"))
c.eq("the Warboss keeps the user-supplied 50mm base - a NAMED deviation from the printed 40mm",
     _p[_wb].base_radius_in, 0.98)
c.eq("...which puts all three bosses on one base", {_p[_wbm].base_radius_in, _p[_bb].base_radius_in}, {0.98})
c.eq("the Painboy's printed 32mm", _p[_pb].base_radius_in, 0.63)

c.eq("the Warboss LEADS", attachment_role(_wb), LEADER)
c.eq("the Painboy SUPPORTS", attachment_role(_pb), SUPPORT)
c.eq("Warboss in Mega Armour + Meganobz is legal", can_attach(build(ork.WARBOSS_MEGA_ARMOUR, HUMAN, name="x"),
                                                              build(ork.MEGANOBZ, HUMAN, name="y")), [])
c.eq("Beastboss + Beast Snagga Boyz is legal", can_attach(build(ork.BEASTBOSS, HUMAN, name="x2"),
                                                           build(ork.BEAST_SNAGGA_BOYZ, HUMAN, name="y2")), [])
c.eq("Painboy + Boyz is legal", can_attach(build(ork.PAINBOY, HUMAN, name="x3"), build(ork.BOYZ, HUMAN, name="y3")), [])
c.true("the Warboss cannot lead Meganobz", bool(can_attach(build(ork.WARBOSS, HUMAN, name="x4"),
                                                          build(ork.MEGANOBZ, HUMAN, name="y4"))))

c.true("Warboss flags", all(getattr(_p[_wb], f) for f in ("boss_ammo_runt", "might_is_right", "intimidating_motivation")))
c.true("Warboss in Mega Armour flags", all(getattr(_p[_wbm], f) for f in ("krushin_impetus", "intimidating_motivation")))
c.true("...and NOT Might Is Right (not printed on his sheet)", not _p[_wbm].might_is_right)
c.true("Beastboss flags", all(getattr(_p[_bb], f) for f in ("keep_huntin", "dodge_dis")))
c.true("Painboy flags", all(getattr(_p[_pb], f) for f in ("crude_surgery", "catch_dat_red_bit")))
c.eq("the four sheets' printed keyword lines",
     [ork.WARBOSS.keywords, ork.WARBOSS_MEGA_ARMOUR.keywords, ork.BEASTBOSS.keywords, ork.PAINBOY.keywords],
     [("INFANTRY", "CHARACTER", "EXPLOSIVES", "WARBOSS"), ("INFANTRY", "CHARACTER", "MEGA ARMOUR", "WARBOSS"),
      ("INFANTRY", "BEAST SNAGGA", "CHARACTER", "WARBOSS"), ("INFANTRY", "CHARACTER")])


# ===========================================================================
print("\n2. Boss' Ammo Runt (Warboss)")
# ===========================================================================
def runt_scene(auto=False):
    scene = shooting_scene(ork.BOYZ, STRIKE_TEAM, attacker_owner=HUMAN, gap=10.0)
    state, boyz = scene["state"], scene["attacker"]
    boss = build(ork.WARBOSS, HUMAN, name="1 Warboss 1")
    led = attach(boss, boyz, game_state=state)
    line_up(led, y=20.0)
    for m in led.models:
        if m not in state.tokens:
            state.add_token(m)
    scene["attacker"] = led
    kw = dict(decision_manager=scene["decision"], turn_tracker=scene["turn"], game_log=scene["log"],
              auto_players=(HUMAN,) if auto else ())
    scene["boys_ctrl"] = ork_ammo_runts.AmmoRuntsController(**kw)
    scene["boss_ctrl"] = boss_ammo_runt.BossAmmoRuntController(**kw)
    scene["shooting"].ork_ammo_runts = scene["boys_ctrl"]
    scene["shooting"].boss_ammo_runt = scene["boss_ctrl"]
    return scene


_s = runt_scene()
_sc, _led, _t = _s["shooting"], _s["attacker"], _s["target"]
_boss = bearer(_led, "boss_ammo_runt")
_boy = next(m for m in _led.models if not m.profile.character and weapon_named(m, "Shoota"))
_sc.start_shooting(_led)
c.eq("selected to shoot, BOTH once-per-battle uses are offered, each its own prompt - the mob's first",
     options_of(_s["decision"]), ["Use Ammo Runts", "Save it for later"])
c.true("the mob's is first", pick_option(_s["decision"], "Save it for later"))
c.eq("...then the Warboss's own", options_of(_s["decision"]), ["Use Boss' Ammo Runt", "Save it for later"])
_bg = {"pairs": [(_boss, weapon_named(_boss, "Kustom Shoota"))], "target_squad": _t}
_yg = {"pairs": [(_boy, weapon_named(_boy, "Shoota"))], "target_squad": _t}
c.eq("before the answer: no bonus", mods(_sc._hit_modifiers(_bg), boss_ammo_runt.BOSS_AMMO_RUNT_NAME), [])
c.true("choosing it", pick_option(_s["decision"], "Use Boss' Ammo Runt"))
c.eq("the Warboss's group has +1 to hit through the real _hit_modifiers()",
     mods(_sc._hit_modifiers(_bg), boss_ammo_runt.BOSS_AMMO_RUNT_NAME), [(-1, "Boss' Ammo Runt")])
c.eq("...a Boy's group does NOT - 'this MODEL's ranged attacks'",
     mods(_sc._hit_modifiers(_yg), boss_ammo_runt.BOSS_AMMO_RUNT_NAME), [])
c.true("...and the mob's Ammo Runts is still unspent (per UNIT, a separate use)",
       not _led.ammo_runts_used and _led.boss_ammo_runt_used)
c.true("the attack key keeps the Warboss's group his own",
       _attack_key(_boss, weapon_named(_boss, "Kustom Shoota")) != _attack_key(_boy, weapon_named(_boss, "Kustom Shoota")))
c.eq("...False for every model that does not print it (no existing group splits)",
     boss_ammo_runt.attack_key(_boy), False)
boss_ammo_runt.reset_phase([_led])
c.eq("the grant ends with the phase", mods(_sc._hit_modifiers(_bg), "Boss' Ammo Runt"), [])
c.eq("...the spend survives", _s["boss_ctrl"].why_not(_led), "already used this battle")

_s = runt_scene(auto=True)
_s["shooting"].start_shooting(_s["attacker"])
c.true("the AI uses both at the first opportunity, no prompt",
       boss_ammo_runt.is_active(_s["attacker"]) and ork_ammo_runts.is_active(_s["attacker"])
       and not _s["decision"].is_pending)
_s = runt_scene()
_s["turn"].turn_owner = FOE
c.eq("not in the opponent's Shooting phase", _s["boss_ctrl"].why_not(_s["attacker"]), "not your Shooting phase")
c.eq("a mob without its Warboss has no Boss' Ammo Runt",
     boss_ammo_runt.BossAmmoRuntController().why_not(build(ork.BOYZ, HUMAN, name="plain")),
     "this unit has no Boss' Ammo Runt")


# ===========================================================================
print("\n3. Might Is Right (Warboss)")
# ===========================================================================
_f = fight_scene(ork.BOYZ, STRIKE_TEAM, attacker_owner=HUMAN)
_fc, _state = _f["fight"], _f["state"]
_led = attach(build(ork.WARBOSS, HUMAN, name="1 Warboss 1"), _f["attacker"], game_state=_state)
_fc.fighting_squad = _led
_boss = bearer(_led, "might_is_right")
_choppa = weapon_named(_boss, "Kustom Choppa")
_nob = next(m for m in _led.models if weapon_named(m, "Kustom Choppa") and not m.profile.character)
_nob_choppa = weapon_named(_nob, "Kustom Choppa")
_led.charged_this_turn = False
_plain = _fc._adjusted_weapon([(_boss, _choppa)], _f["target"])
c.eq("no charge this turn: A6 S7", (_plain.attacks, _plain.strength), (6, 7))
_led.charged_this_turn = True
_hot = _fc._adjusted_weapon([(_boss, _choppa)], _f["target"])
c.eq("after a charge move: +3 A, +2 S through the real fight chain (A9 S9)", (_hot.attacks, _hot.strength), (9, 9))
c.eq("...on a copy", (_choppa.attacks, _choppa.strength), (6, 7))
_nob_hot = _fc._adjusted_weapon([(_nob, _nob_choppa)], _f["target"])
c.eq("the Nob beside him gains nothing - 'this MODEL's melee attacks'",
     (_nob_hot.attacks, _nob_hot.strength), (_nob_choppa.attacks, _nob_choppa.strength))
c.true("ranged weapons gain nothing",
       might_is_right.adjusted_weapon(weapon_named(_boss, "Kustom Shoota"), _boss) is weapon_named(_boss, "Kustom Shoota"))
c.true("the melee attack key splits the Warboss from an otherwise identical row",
       _melee_attack_key(_boss, _nob_choppa) != _melee_attack_key(_nob, _nob_choppa))
_dice_weapon = weapons_mod.WarbossKustomChoppaProfile()
_dice_weapon.attacks_notation = DiceNotation(6, 1, 1)
_dice_weapon.strength_notation = DiceNotation(3, 2, 1)
_nd = might_is_right.adjusted_weapon(_dice_weapon, _boss)
c.eq("a dice notation takes the bonus on its flat part (D6+1 -> D6+4, D3+2 -> D3+4)",
     (_nd.attacks_notation.bonus, _nd.strength_notation.bonus), (4, 4))
_boss.current_wounds = 0
c.true("a dead Warboss grants nothing", might_is_right.adjusted_weapon(_choppa, _boss) is _choppa)
c.true("the pre-codex leader grant is gone", not hasattr(squad_mod, "squad_has_might_is_right"))


# ===========================================================================
print("\n4. Dodge Dis! (Beastboss)")
# ===========================================================================
_s = shooting_scene(ork.BEAST_SNAGGA_BOYZ, STRIKE_TEAM, attacker_owner=HUMAN, gap=10.0)
_sc, _bsb, _t = _s["shooting"], _s["attacker"], _s["target"]
_sc.active_squad = _bsb
_grp = {"pairs": [(_bsb.models[1], _bsb.models[1].weapons[0])], "target_squad": _t}
c.eq("Beast Snagga Boyz alone: no Dodge Dis!", mods(_sc._hit_modifiers(_grp), "Dodge Dis!"), [])
_led = attach(build(ork.BEASTBOSS, HUMAN, name="1 Beastboss 1"), _bsb, game_state=_s["state"])
_sc.active_squad = _led
c.eq("led by the Beastboss, a BOY's ranged attack has +1 to hit through the real shooting _hit_modifiers()",
     mods(_sc._hit_modifiers(_grp), "Dodge Dis!"), [(-1, "Dodge Dis!")])
_f = fight_scene(ork.BEAST_SNAGGA_BOYZ, STRIKE_TEAM, attacker_owner=HUMAN)
_fled = attach(build(ork.BEASTBOSS, HUMAN, name="1 Beastboss 2"), _f["attacker"], game_state=_f["state"])
_f["fight"].fighting_squad = _fled
c.eq("...and a melee attack too, through the real fight _hit_modifiers() ('attacks', both phases)",
     mods(_f["fight"]._hit_modifiers(_fled.models[1], _f["target"]), "Dodge Dis!"), [(-1, "Dodge Dis!")])
bearer(_fled, "dodge_dis").current_wounds = 0
c.eq("a mob whose Beastboss is dead loses it (19.04)", dodge_dis.hit_modifiers(_fled), [])
c.eq("an enemy attacking the Beastboss's unit gains nothing - read literally, the unit's OWN attacks",
     dodge_dis.hit_modifiers(_t), [])


# ===========================================================================
print("\n5. the per-army round limit")
# ===========================================================================
_lim = PerArmyRoundLimit("Test", "intimidating_motivation_round")
_a, _b = build(ork.BOYZ, HUMAN, name="lim a"), build(ork.BOYZ, HUMAN, name="lim b")
c.eq("unspent", _lim.is_spent(HUMAN, 2, [_a, _b]), False)
_lim.spend(HUMAN, 2, _a)
c.true("spent for that player, that round", _lim.is_spent(HUMAN, 2, [_a, _b]))
c.eq("...not for the other player", _lim.is_spent(FOE, 2, [_a, _b]), False)
c.eq("...and back next round", _lim.is_spent(HUMAN, 3, [_a, _b]), False)
_fresh = PerArmyRoundLimit("Test", "intimidating_motivation_round")
c.true("a fresh limit (a reloaded scene) reads the spend off the saved unit flag", _fresh.is_spent(HUMAN, 2, [_a, _b]))
c.eq("...and no round (battle not begun) is never spent", _fresh.is_spent(HUMAN, None, [_a]), False)


# ===========================================================================
print("\n6. Intimidating Motivation / Keep Huntin'!")
# ===========================================================================
def boss_board(phase=PHASE_MOVEMENT, owner=HUMAN, auto=(), choice=None, battle_round=2):
    st = GameState()
    tt = tracker(phase, owner, battle_round)
    boyz = place(attach(build(ork.WARBOSS, HUMAN, name="1 Warboss 1"),
                        build(ork.BOYZ, HUMAN, name="1 Boyz 1"), game_state=st), 10.0, 10.0)
    mega = place(attach(build(ork.WARBOSS_MEGA_ARMOUR, HUMAN, name="1 Warboss in Mega Armour 1"),
                        build(ork.MEGANOBZ, HUMAN, name="1 Meganobz 1"), game_state=st), 10.0, 20.0)
    bsb = place(attach(build(ork.BEASTBOSS, HUMAN, name="1 Beastboss 1"),
                       build(ork.BEAST_SNAGGA_BOYZ, HUMAN, name="1 Beast Snagga Boyz 1"), game_state=st), 30.0, 10.0)
    grots = place(build(ork.GRETCHIN, HUMAN, name="1 Gretchin 1"), 10.0, 14.5)
    far = place(build(ork.STORMBOYZ, HUMAN, name="1 Stormboyz 1"), 50.0, 40.0)
    # Two rows at y=2.0 and 4.1: clear of 03.04's Engagement Range from the
    # Warboss's mob (a mob in combat cannot make a Normal move at all).
    foe = place(build(ork.BOYZ, FOE, name="2 Boyz 1"), 10.0, 2.0)
    for sq in (boyz, mega, bsb, grots, far, foe):
        for m in sq.models:
            st.add_token(m)
    dm = DecisionManager()
    mover = MovementController([], tk.Log(), owner, DiceManager(), tt, st.tokens)
    kw = dict(turn_tracker=tt, movement_controller=mover, decision_manager=dm, game_log=tk.Log(),
              squads_provider=st.all_squads, all_tokens=st.tokens, auto_players=auto, choice=choice)
    im = boss_motivation.IntimidatingMotivationController(**kw)
    kh = boss_motivation.KeepHuntinController(**kw)
    return dict(state=st, turn=tt, boyz=boyz, mega=mega, bsb=bsb, grots=grots, far=far, foe=foe,
                decision=dm, mover=mover, im=im, kh=kh)


_b = boss_board()
_names = lambda squads: sorted(s.name for s in squads)  # noqa: E731
c.eq("Intimidating Motivation: every friendly ORKS unit within 6\" it would help - its OWN unit included",
     _names(_b["im"].candidates(_b["boyz"])), sorted([_b["boyz"].name, _b["grots"].name]))
c.true("...not the Stormboyz 40\" away, not the enemy Boyz", all(s not in _b["im"].candidates(_b["boyz"])
                                                               for s in (_b["far"], _b["foe"])))
c.eq("Keep Huntin'!: only BEAST SNAGGA units", _names(_b["kh"].candidates(_b["bsb"])), [_b["bsb"].name])
c.eq("Keep Huntin'! is not the Warboss's", _b["kh"].why_not(_b["boyz"]), "this unit has no Keep Huntin'!")
_kb = boss_board()
place(_kb["grots"], 30.0, 14.5)
c.true("(live) the Gretchin now stand within 6\" of the Beastboss's unit",
       _kb["bsb"].min_distance_to(_kb["grots"]) <= boss_motivation.BOSS_MOTIVATION_RANGE_IN)
c.true("...an ORKS unit Keep Huntin'! still does not take - it is not BEAST SNAGGA",
       _kb["grots"] not in _kb["kh"].candidates(_kb["bsb"]))
_b["grots"].riled_up_expires_turn = riled_up.until_start_of_your_next_turn(_b["turn"], HUMAN) + 5
c.true("a unit already riled up that long, and not battle-shocked, is not offered (Fehlerklasse 5)",
       _b["grots"] not in _b["im"].candidates(_b["boyz"]))
_b["grots"].battle_shocked = True
c.true("...but a battle-shocked one is, whatever its riled-up state", _b["grots"] in _b["im"].candidates(_b["boyz"]))
_b["grots"].battle_shocked = False
_b["grots"].riled_up_expires_turn = None

c.eq("START window open before the unit moves", _b["im"].why_not(_b["boyz"]), None)
_b["mover"].moved_squad_ids.add(_b["boyz"])
c.eq("after it has moved the start window is shut", _b["im"].why_not(_b["boyz"]),
     "only at the start or end of this unit's move")
_b["im"].on_move_finished(_b["boyz"], "normal")
c.eq("...and its END window opens when its move finishes", _b["im"].why_not(_b["boyz"]), None)
_b["im"].on_move_started(_b["far"])
c.eq("...until another unit begins a move", _b["im"].why_not(_b["boyz"]),
     "only at the start or end of this unit's move")
_b["mover"].moved_squad_ids.clear()

_b = boss_board()
_b["grots"].battle_shocked = True
c.true("a human with two candidates gets a prompt", _b["im"].use(_b["boyz"]) and _b["decision"].is_pending)
c.true("...a BOARD pick - every candidate tagged", unit_pick.pending(_b["decision"], _b["state"].tokens) is not None)
c.true("...with a Cancel", "Cancel" in options_of(_b["decision"]))
pick_option(_b["decision"], "Cancel")
c.true("Cancel spends nothing", not _b["im"].is_spent(HUMAN))
_b["im"].use(_b["boyz"])
c.true("choosing the Gretchin", pick_option(_b["decision"], _b["grots"].name))
_deadline = riled_up.until_start_of_your_next_turn(_b["turn"], HUMAN)
c.true("...unshocks them", not _b["grots"].battle_shocked)
c.eq("...riles them up until the start of your next turn", _b["grots"].riled_up_expires_turn, _deadline)
c.true("...and stamps it at once", _b["grots"].riled_up)
c.true("the budget is spent for the army this round", _b["im"].is_spent(HUMAN))
c.eq("the Warboss in Mega Armour SHARES it - one Intimidating Motivation per army",
     _b["im"].why_not(_b["mega"]), "already used this battle round")
c.eq("Keep Huntin'! is a separate budget", _b["kh"].why_not(_b["bsb"]), None)
_b["turn"].battle_round = 3
c.eq("...and Intimidating Motivation is back next battle round", _b["im"].why_not(_b["mega"]), None)

_b = boss_board(phase=PHASE_SHOOTING)
c.eq("not outside the Movement phase", _b["im"].why_not(_b["boyz"]), "not your Movement phase")
_b = boss_board(owner=FOE)
c.eq("not in the opponent's Movement phase", _b["im"].why_not(_b["boyz"]), "not your Movement phase")
_b = boss_board()
bearer(_b["boyz"], "intimidating_motivation").current_wounds = 0
c.eq("a dead Warboss motivates nobody", _b["im"].why_not(_b["boyz"]), "this unit has no Intimidating Motivation")

_b = boss_board()
_single = boss_motivation.KeepHuntinController(
    turn_tracker=_b["turn"], movement_controller=_b["mover"], decision_manager=_b["decision"],
    game_log=tk.Log(), squads_provider=_b["state"].all_squads, all_tokens=_b["state"].tokens)
c.true("one candidate is used outright, no prompt", _single.use(_b["bsb"]) and not _b["decision"].is_pending
       and _b["bsb"].riled_up)

# The AI, through a REAL MovementController's two hooks.
_b = boss_board(auto=(HUMAN,), choice=boss_motivation_choice)
_b["mover"].on_move_started.append(_b["im"].on_move_started)
_b["mover"].on_move_finished.append(_b["im"].on_move_finished)
_b["grots"].battle_shocked = True
_b["mover"].select(_b["boyz"].models[0])
_b["mover"].start_move()
c.true("(live) the real MovementController began the move", _b["mover"].state == "moving")
c.true("the AI used it at the START of the Warboss's move, through the hook, without a prompt",
       _b["im"].is_spent(HUMAN) and not _b["decision"].is_pending)
c.true("...on the battle-shocked unit first", not _b["grots"].battle_shocked and _b["grots"].riled_up)
_b2 = boss_board(auto=(HUMAN,), choice=lambda s, cands: None)
_b2["im"].on_move_started(_b2["boyz"])
c.true("a choice that holds it spends nothing", not _b2["im"].is_spent(HUMAN))
_b3 = boss_board(choice=boss_motivation_choice)
_b3["im"].on_move_started(_b3["boyz"])
c.true("a HUMAN is never answered by the hooks", not _b3["im"].is_spent(HUMAN) and not _b3["decision"].is_pending)


# ===========================================================================
print("\n7. the button, on the real ActionPanel")
# ===========================================================================
pygame.init()
pygame.display.set_mode((1200, 900))
_panel = ActionPanel()
_surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
_rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900)


def render(board, squad):
    registry = ProactiveStratagems()
    registry.add(board["im"])
    registry.add(board["kh"])
    mover = board["mover"]
    shooter = ShootingController(obstacles=[], game_log=tk.Log(), player_name=board["turn"].turn_owner,
                                 dice_manager=DiceManager(), turn_tracker=board["turn"],
                                 all_tokens=board["state"].tokens, decision_manager=DecisionManager())
    mover.select(squad.models[0])
    _surface.fill((0, 0, 0))
    _panel.draw(_surface, _rect, mover, shooter, dice_manager=DiceManager(), proactive_stratagems=registry)
    return [n for _r, n in _panel._stratagem_buttons], list(_panel._buttons), mover.selected_squad is squad


_b = boss_board()
_names_drawn, _btns, _ok = render(_b, _b["boyz"])
c.true("(live) the Warboss's unit was selected and the panel drew", _ok)
c.true("Intimidating Motivation is drawn for the Warboss's unit in its Movement phase",
       "Intimidating Motivation" in _names_drawn)
c.true("...Keep Huntin'! is not", "Keep Huntin'!" not in _names_drawn)
_names_drawn, _btns, _ok = render(_b, _b["bsb"])
c.true("Keep Huntin'! is drawn for the Beastboss's unit", _ok and "Keep Huntin'!" in _names_drawn)
_names_drawn, _btns, _ok = render(_b, _b["grots"])
c.true("nothing for a unit with no boss", _ok and not ({"Intimidating Motivation", "Keep Huntin'!"} & set(_names_drawn)))
_b = boss_board(phase=PHASE_SHOOTING)
_names_drawn, _btns, _ok = render(_b, _b["boyz"])
c.true("nothing in the Shooting phase", "Intimidating Motivation" not in _names_drawn)
_b = boss_board()
_b["im"].limit.spend(HUMAN, 2, _b["mega"])
_names_drawn, _btns, _ok = render(_b, _b["boyz"])
c.true("nothing once the army's use this round is spent - by the OTHER Warboss",
       "Intimidating Motivation" not in _names_drawn)
_b = boss_board()
_b["grots"].riled_up_expires_turn = riled_up.until_start_of_your_next_turn(_b["turn"], HUMAN) + 5
_b["boyz"].riled_up_expires_turn = _b["grots"].riled_up_expires_turn
_names_drawn, _btns, _ok = render(_b, _b["boyz"])
_rect_im = next((r for r, n in _panel._stratagem_buttons if n == "Intimidating Motivation"), None)
c.true("nothing when no unit in range would gain from it", _rect_im is None)
_b = boss_board()
render(_b, _b["boyz"])
_rect_im = next((r for r, n in _panel._stratagem_buttons if n == "Intimidating Motivation"), None)
_cb = next((cb for r, cb in _panel._buttons if r == _rect_im), None)
if _cb is not None:
    _cb()
c.true("the click really asks (two candidates -> the board pick)", _cb is not None and _b["decision"].is_pending)


# ===========================================================================
print("\n8. Krushin' Impetus (Warboss in Mega Armour)")
# ===========================================================================
def krush_scene(foes=(STRIKE_TEAM,), auto=(), far_models=0):
    st = GameState()
    led = line_up(attach(build(ork.WARBOSS_MEGA_ARMOUR, HUMAN, name="1 Warboss in Mega Armour 1"),
                         build(ork.MEGANOBZ, HUMAN, name="1 Meganobz 1"), game_state=st), x=10.0, y=20.0, spacing=2.0)
    for m in led.models[len(led.models) - far_models:] if far_models else ():
        m.y_in = 40.0
    enemies = []
    for i, sheet in enumerate(foes):
        unit = line_up(build(sheet, FOE, name="%s %d" % (sheet.name, i)), x=10.0 + i * 30.0, y=22.1, spacing=2.0)
        enemies.append(unit)
    for sq in [led] + enemies:
        for m in sq.models:
            st.add_token(m)
    dice, dm = RecordingDice(), DecisionManager()
    ctrl = krushin_impetus.KrushinImpetusController(dice_manager=dice, decision_manager=dm, game_log=tk.Log(),
                                                    game_state=st, auto_players=auto)
    return dict(state=st, led=led, foes=enemies, dice=dice, decision=dm, ctrl=ctrl)


def drain(ctrl):
    """Every mortal wound to its model - the target owner's pick each time."""
    guard = 0
    while ctrl.pending_damage_choice and guard < 50:
        ctrl.choose_damage_model(sorted(ctrl.pending_damage_choice, key=lambda m: m.id)[0])
        guard += 1
    return guard


_k = krush_scene()
_engaged = krushin_impetus.dice_for(_k["led"], _k["foes"][0])
c.eq("every model of the attached unit is engaged: one D6 each (Warboss + 2 Meganobz)", _engaged, 3)
_alive_before = sum(1 for m in _k["foes"][0].models if not m.is_dead())
script(3, 2, 6)
c.true("ending a charge move rolls", _k["ctrl"].on_charge_move_finished(_k["led"]))
c.eq("...one die per engaged model, named Krushin' Impetus", (_k["dice"].rolled[-1][0], len(_k["dice"].rolled[-1][1])),
     ("Krushin' Impetus", 3))
_k["dice"].acknowledge()
_k["ctrl"].on_dice_acknowledged()
c.true("a multi-model target parks the 06.02 allocation for its owner", bool(_k["ctrl"].pending_damage_choice))
drain(_k["ctrl"])
c.eq("each 3+ is ONE mortal wound, all of them landed (3, 6 -> 2)",
     _alive_before - sum(1 for m in _k["foes"][0].models if not m.is_dead()), 2)
c.true("...and nothing is left open", _k["ctrl"].pending_damage_choice is None and not _k["ctrl"].is_busy)

_k = krush_scene(far_models=2)
c.eq("only the models THEMSELVES engaged roll", krushin_impetus.dice_for(_k["led"], _k["foes"][0]), 1)
_k = krush_scene(foes=(STRIKE_TEAM, STRIKE_TEAM))
for _i, _m in enumerate(_k["foes"][1].models):
    _m.x_in = _k["led"].models[-1].x_in + 0.1 * _i
c.eq("two engaged enemy units are both candidates", len(krushin_impetus.targets(_k["led"], _k["state"].tokens)), 2)
script(6, 6, 6)
_k["ctrl"].on_charge_move_finished(_k["led"])
c.true("a human picks WHICH on the board, with no decline", _k["decision"].is_pending
       and unit_pick.pending(_k["decision"], _k["state"].tokens) is not None
       and not any(lab in ("Decline", "Cancel") for lab in options_of(_k["decision"])))
_k = krush_scene(foes=(STRIKE_TEAM, STRIKE_TEAM), auto=(HUMAN,))
for _i, _m in enumerate(_k["foes"][1].models):
    _m.x_in = _k["led"].models[-1].x_in + 0.1 * _i
script(6, 6, 6)
_k["ctrl"].on_charge_move_finished(_k["led"])
c.true("the AI picks without a prompt", not _k["decision"].is_pending and bool(_k["dice"].rolled))
_k = krush_scene()
for _m in _k["foes"][0].models:
    _m.y_in = 40.0
c.eq("a charge that fell short finds nothing", _k["ctrl"].on_charge_move_finished(_k["led"]), False)
_k = krush_scene()
bearer(_k["led"], "krushin_impetus").current_wounds = 0
c.eq("a mob whose Warboss is dead has no Krushin' Impetus", krushin_impetus.has_ability(_k["led"]), False)


# ===========================================================================
print("\n9. Crude Surgery / Catch Dat Red Bit (Painboy)")
# ===========================================================================
def surgery_scene(dead_boys=2, doc_wounds_lost=1, owner=HUMAN, auto=(), verdict=None, on_board=True,
                  with_placer=True, dice=True):
    st = GameState()
    mob = place(attach(build(ork.PAINBOY, owner, name="1 Painboy 1"),
                       build(ork.BOYZ, owner, name="1 Boyz 1"), game_state=st), 10.0, 10.0, spacing=1.5)
    if on_board:
        for m in mob.models:
            st.add_token(m)
    doc = bearer(mob, "crude_surgery")
    doc.current_wounds -= doc_wounds_lost
    boys = [m for m in mob.models if not m.profile.character and m.profile.name == "Boy"]
    for m in boys[:dead_boys]:
        m.current_wounds = 0
    if on_board:
        st.remove_dead_models()
    else:
        for m in boys[:dead_boys]:
            mob.models.remove(m)
            mob.destroyed_models.append(m)
    setup = SetupController(st, all_tokens=st.tokens, board_width_in=60.0, board_height_in=44.0)
    placer = ReturnPlacementController(setup_controller=setup, game_state=st, auto_players=auto) if with_placer else None
    dm = DecisionManager()
    rd = RecordingDice() if dice else None
    ctrl = crude_surgery.CrudeSurgeryController(dice_manager=rd, decision_manager=dm, game_log=tk.Log(),
                                                game_state=st, auto_players=auto, placer=placer, verdict=verdict)
    return dict(state=st, mob=mob, doc=doc, setup=setup, placer=placer, decision=dm, dice=rd, ctrl=ctrl)


_s = surgery_scene(dead_boys=1, doc_wounds_lost=0)
_alive = len(_s["mob"].models)
c.eq("healable: one dead Boy (1 wound) and nothing damaged", heal.healable_wounds(_s["mob"]), 1)
_s["ctrl"].begin_command_phase([_s["mob"]], HUMAN)
c.true("3 or fewer to heal: no Red Bit question", not _s["decision"].is_pending)
c.eq("...the Boy is revived", len(_s["mob"].models), _alive + 1)
c.eq("...and a HUMAN places him (rule 01.02.03)", _s["setup"].state, setup_mod.PLACING)

_s = surgery_scene(dead_boys=1, doc_wounds_lost=2, auto=(HUMAN,))
_s["ctrl"].begin_command_phase([_s["mob"]], HUMAN)
c.eq("healing comes FIRST: the Painboy is topped up (2 of the 3) ...", _s["doc"].current_wounds, 3)
c.eq("...and the last wound stands the Boy up", [m for m in _s["mob"].destroyed_models
                                                  if m not in _s["mob"].models], [])
c.eq("...the AI's model lands outright", _s["setup"].state, setup_mod.IDLE)

_s = surgery_scene(dead_boys=4, doc_wounds_lost=0)
c.true("more than 3 to heal: Catch Dat Red Bit is asked", _s["ctrl"].begin_command_phase([_s["mob"]], HUMAN)
       and _s["decision"].is_pending)
c.eq("...with its two answers", options_of(_s["decision"]),
     [crude_surgery.USE_RED_BIT_LABEL, crude_surgery.SAVE_RED_BIT_LABEL])
c.true("...and it holds the phase meanwhile", _s["ctrl"].is_busy)
_before = len(_s["mob"].models)
script(2)
pick_option(_s["decision"], "Catch Dat Red Bit")
c.eq("using it rolls a visible D3", (_s["dice"].rolled[-1][0].startswith("Catch Dat Red Bit"),
                                     len(_s["dice"].rolled[-1][1])), (True, 1))
c.true("...spent once per battle, on the unit", _s["mob"].catch_dat_red_bit_used)
_s["dice"].acknowledge()
c.true("(its acknowledgement is taken)", _s["ctrl"].on_dice_acknowledged())
c.eq("3 + 2 wounds healed: four Boys stand up (the fifth wound has no one left to heal)",
     len(_s["mob"].models) - _before, 4)
c.true("...and it is done", not _s["ctrl"].is_busy)

_s = surgery_scene(dead_boys=4, doc_wounds_lost=0)
_s["ctrl"].begin_command_phase([_s["mob"]], HUMAN)
_before = len(_s["mob"].models)
pick_option(_s["decision"], "Save it for later")
c.eq("saving it heals the 3", len(_s["mob"].models) - _before, 3)
c.true("...and spends nothing", not _s["mob"].catch_dat_red_bit_used)
_s["mob"].catch_dat_red_bit_used = True
c.eq("once spent it is never offered again", crude_surgery.red_bit_offerable(_s["mob"]), False)

_s = surgery_scene(dead_boys=6, doc_wounds_lost=0, auto=(HUMAN,), verdict=catch_dat_red_bit_verdict)
script(1)
_s["ctrl"].begin_command_phase([_s["mob"]], HUMAN)
c.true("the AI (6 to heal) rolls the Red Bit without a prompt",
       not _s["decision"].is_pending and _s["mob"].catch_dat_red_bit_used)
_s = surgery_scene(dead_boys=4, doc_wounds_lost=0, auto=(HUMAN,), verdict=catch_dat_red_bit_verdict)
_s["ctrl"].begin_command_phase([_s["mob"]], HUMAN)
c.true("...but holds it on 4", not _s["mob"].catch_dat_red_bit_used)

_s = surgery_scene(dead_boys=2, doc_wounds_lost=0, on_board=False)
_before = len(_s["mob"].models)
_s["ctrl"].begin_command_phase([_s["mob"]], HUMAN)
c.eq("a unit OFF the board heals too - both Boys rejoin the unit", len(_s["mob"].models) - _before, 2)
c.true("...without a token on the battlefield", not any(m in _s["state"].tokens for m in _s["mob"].models))
c.eq("...and nothing is opened to place them", _s["setup"].state, setup_mod.IDLE)

_s = surgery_scene(dead_boys=2)
_s["doc"].current_wounds = 0
c.eq("a dead Painboy heals nobody", _s["ctrl"].begin_command_phase([_s["mob"]], HUMAN), False)
_s = surgery_scene(dead_boys=0, doc_wounds_lost=0)
c.eq("a unit with nothing to heal is skipped", _s["ctrl"].begin_command_phase([_s["mob"]], HUMAN), False)
_s = surgery_scene(dead_boys=2, owner=HUMAN)
c.eq("only the Command phase's own player", _s["ctrl"].begin_command_phase([_s["mob"]], FOE), False)
_s = surgery_scene(dead_boys=0, doc_wounds_lost=0)
_s["doc"].current_wounds = 0
_s["state"].remove_dead_models()
c.eq("CHARACTER models are never revived (02.02.04) - a Painboy cannot raise himself",
     heal.revivable_models(_s["mob"]), [])


# ===========================================================================
print("\n10. the extraction: core rule 02.02.04 lives in game/heal.py")
# ===========================================================================
for _name, _orig in (("revivable_models", "revivable_models"), ("recoverable_wounds", "healable_wounds"),
                     ("placement_validator", "placement_validator")):
    c.true("reanimation_protocols.%s IS heal.%s (one definition)" % (_name, _orig),
           getattr(reanimation_protocols, _name) is getattr(heal, _orig))
_rp_src = io.open(os.path.join(HERE, "game", "reanimation_protocols.py"), encoding="utf-8").read()
_rp_tree = ast.parse(_rp_src)
_reanimate = next(n for n in ast.walk(_rp_tree) if isinstance(n, ast.FunctionDef) and n.name == "reanimate")
c.true("reanimate() delegates to heal.heal()",
       any(isinstance(n, ast.Call) and ast.unparse(n.func) == "heal_rule.heal" for n in ast.walk(_reanimate)))


# ===========================================================================
print("\n11. the AI's two answers")
# ===========================================================================
_x = build(ork.BOYZ, HUMAN, name="x")
_y = build(ork.MEGANOBZ, HUMAN, name="y")
_z = build(ork.GRETCHIN, HUMAN, name="z")
_z.battle_shocked = True
c.eq("the boss motivation takes the battle-shocked unit first", boss_motivation_choice(None, [_x, _y, _z]), _z)
_z.battle_shocked = False
c.eq("...otherwise the most valuable one", boss_motivation_choice(None, [_x, _y, _z]).name,
     max((_x, _y, _z), key=lambda s: s.points).name)
c.eq("...and with nothing to choose from, nothing", boss_motivation_choice(None, []), None)
_s = surgery_scene(dead_boys=CATCH_DAT_RED_BIT_MIN_HEALABLE, doc_wounds_lost=0)
c.true("Catch Dat Red Bit at %d to heal" % CATCH_DAT_RED_BIT_MIN_HEALABLE, catch_dat_red_bit_verdict(_s["mob"]))
_s = surgery_scene(dead_boys=CATCH_DAT_RED_BIT_MIN_HEALABLE - 1, doc_wounds_lost=0)
c.eq("...not below it", catch_dat_red_bit_verdict(_s["mob"]), False)


class _FellThrough(Exception):
    pass


def _ai_owned_krush():
    """A human's Krushin' Impetus on the AI's multi-model unit: the rule 06.02
    pick is the AI's (FOE's) to make."""
    k = krush_scene()
    script(3, 3, 3)
    k["ctrl"].on_charge_move_finished(k["led"])
    k["dice"].acknowledge()
    k["ctrl"].on_dice_acknowledged()
    return k


def _one_ai_action(**kwargs):
    """_take_one_action() down to its own-allocation step; the next step is
    replaced with a sentinel, so 'fell through' is a result, not a crash."""
    real = agent_driver._maybe_resolve_decision
    agent_driver._maybe_resolve_decision = lambda *a, **k: (_ for _ in ()).throw(_FellThrough())
    try:
        agent_driver._take_one_action(None, None, None, None, None, None, None, None, None, None,
                                      None, None, None, player=FOE, **kwargs)
        return "resolved"
    except _FellThrough:
        return "fell through"
    finally:
        agent_driver._maybe_resolve_decision = real


_k = _ai_owned_krush()
c.true("a human's Krushin' Impetus on an AI mob leaves the pick with the AI",
       bool(_k["ctrl"].pending_damage_choice)
       and _k["ctrl"].pending_damage_choice[0].squad.owner == FOE)
_alive_before = sum(1 for m in _k["foes"][0].models if not m.is_dead())
c.eq("the AI answers it from the shared list main.py passes",
     _one_ai_action(damage_choice_controllers=(_k["ctrl"],)), "resolved")
c.true("...every wound lands and nothing is left open",
       _k["ctrl"].pending_damage_choice is None
       and _alive_before - sum(1 for m in _k["foes"][0].models if not m.is_dead()) == 3)
_k = _ai_owned_krush()
c.eq("without that list the AI walks past it (the measured stall)", _one_ai_action(), "fell through")
c.true("...and the allocation is still open", bool(_k["ctrl"].pending_damage_choice))


# ===========================================================================
print("\n12. retired")
# ===========================================================================
for _mod in ("ferocious_rage", "doks_toolz", "hold_still", "grot_orderly"):
    c.true("game/%s.py is gone" % _mod, not os.path.exists(os.path.join(HERE, "game", "%s.py" % _mod)))
for _cls in ("AttackSquigProfile", "KombiWeaponProfile", "TwinSluggaProfile", "WarbossBigChoppaProfile",
             "BeastSnaggaKlawProfile", "BeastchoppaProfile"):
    c.true("weapons.%s is gone" % _cls, not hasattr(weapons_mod, _cls))
c.true("Token carries no grot_orderly field", "grot_orderly" not in Token.__dataclass_fields__)
for _flag in ("ferocious_rage", "doks_toolz"):
    c.true("UnitProfile carries no %s flag" % _flag, not hasattr(UnitProfile, _flag))
c.true("WeaponProfile carries no hold_still flag", not hasattr(weapons_mod.WeaponProfile, "hold_still"))
for _flag in ("boss_ammo_runt_used", "boss_ammo_runt_active", "intimidating_motivation_round",
              "keep_huntin_round", "catch_dat_red_bit_used"):
    c.true("%s survives a save (activation_state.SQUAD_FLAGS)" % _flag, _flag in activation_state.SQUAD_FLAGS)
    c.true("...and every Squad starts with it", hasattr(build(ork.BOYZ, HUMAN, name="f"), _flag))


# ===========================================================================
print("\n13. wiring, at the source")
# ===========================================================================
def read(rel):
    return io.open(os.path.join(HERE, rel), encoding="utf-8").read()


def body_calls(rel, name, cls=None):
    """unparse() of every call that is a WHOLE STATEMENT or an argument of one in
    `name`'s body, reachable - a call behind `if False:` or `False and` does not
    count."""
    tree = ast.parse(read(rel))
    scope = tree if cls is None else next((n for n in ast.walk(tree)
                                           if isinstance(n, ast.ClassDef) and n.name == cls), None)
    fn = next((n for n in ast.walk(scope) if isinstance(n, ast.FunctionDef) and n.name == name), None) \
        if scope is not None else None
    out = set()
    if fn is None:
        return out

    def walk(node):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Constant) and not node.test.value:
            for child in node.orelse:
                walk(child)
            return
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And) and any(
                isinstance(v, ast.Constant) and not v.value for v in node.values):
            return
        if isinstance(node, ast.Call):
            out.add(ast.unparse(node))
        for child in ast.iter_child_nodes(node):
            walk(child)

    for stmt in fn.body:
        walk(stmt)
    return out


for _rel, _cls, _fn, _call in (
        ("game/shooting.py", "ShootingController", "start_shooting", "self.boss_ammo_runt.offer(squad)"),
        ("game/shooting.py", "ShootingController", "_hit_modifiers",
         "boss_ammo_runt.hit_modifiers(shooter_model, self.active_squad)"),
        ("game/shooting.py", "ShootingController", "_hit_modifiers", "dodge_dis.hit_modifiers(self.active_squad)"),
        ("game/shooting.py", None, "_attack_key", "boss_ammo_runt.attack_key(model)"),
        ("game/fight.py", "FightController", "_adjusted_weapon",
         "might_is_right.adjusted_weapon(weapon, pairs[0][0] if pairs else None)"),
        ("game/fight.py", "FightController", "_hit_modifiers", "dodge_dis.hit_modifiers(self.fighting_squad)"),
        ("game/fight.py", None, "_melee_attack_key", "might_is_right.attack_key(model)")):
    c.true("%s %s() reaches %s" % (_rel, _fn, _call), _call in body_calls(_rel, _fn, _cls))

MAIN = read("main.py")
MAIN_TREE = ast.parse(MAIN)
_main_fn = next(n for n in MAIN_TREE.body if isinstance(n, ast.FunctionDef) and n.name == "main")
_statements = {ast.unparse(n.value) for n in ast.walk(_main_fn)
               if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)}


def ctor(cls):
    call = next((n for n in ast.walk(_main_fn) if isinstance(n, ast.Call) and ast.unparse(n.func) == cls), None)
    return {kw.arg: ast.unparse(kw.value) for kw in call.keywords} if call is not None else None


for _cls, _want in (("BossAmmoRuntController", {"auto_players": "ai_players"}),
                    ("IntimidatingMotivationController", {"auto_players": "ai_players",
                                                          "choice": "boss_motivation_choice",
                                                          "movement_controller": "movement_controller"}),
                    ("KeepHuntinController", {"auto_players": "ai_players", "choice": "boss_motivation_choice"}),
                    ("KrushinImpetusController", {"auto_players": "ai_players", "target_pick": "_best_damage_target"}),
                    ("CrudeSurgeryController", {"auto_players": "ai_players", "verdict": "catch_dat_red_bit_verdict"})):
    _kw = ctor(_cls)
    c.true("main() builds %s" % _cls, _kw is not None)
    for _k, _v in _want.items():
        c.eq("...with %s=%s" % (_k, _v), (_kw or {}).get(_k), _v)
c.eq("ShootingController gets the Boss' Ammo Runt controller",
     (ctor("ShootingController") or {}).get("boss_ammo_runt"), "boss_ammo_runt_controller")
for _stmt in ("proactive_stratagems.add(intimidating_motivation_controller)",
              "proactive_stratagems.add(keep_huntin_controller)",
              "movement_controller.on_move_started.append(intimidating_motivation_controller.on_move_started)",
              "movement_controller.on_move_finished.append(intimidating_motivation_controller.on_move_finished)",
              "movement_controller.on_move_started.append(keep_huntin_controller.on_move_started)",
              "movement_controller.on_move_finished.append(keep_huntin_controller.on_move_finished)",
              "charge_controller.on_charge_move_finished.append(krushin_impetus_controller.on_charge_move_finished)",
              "krushin_impetus_controller.on_dice_acknowledged()",
              "crude_surgery_controller.on_dice_acknowledged()",
              "boss_ammo_runt.reset_phase({t.squad for t in state.tokens if t.squad is not None})",
              "intimidating_motivation_controller.reset_phase()",
              "keep_huntin_controller.reset_phase()",
              "renderer.draw_damage_choice_highlight(board_surface, board, krushin_impetus_controller.pending_damage_choice)",
              "krushin_impetus_controller.choose_damage_model(clicked)"):
    c.true("main() runs %s" % _stmt, _stmt in _statements)
c.true("main() hands Crude Surgery the return placer",
       "crude_surgery_controller.placer = return_placement_controller" in MAIN)
_cmd = [n for n in ast.walk(_main_fn) if isinstance(n, ast.If)
        and ast.unparse(n.test) == "turn_tracker.phase == PHASE_COMMAND"]
_surgery = [s for block in _cmd for s in ast.walk(ast.Module(body=block.body, type_ignores=[]))
            if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
            and ast.unparse(s.value.func) == "crude_surgery_controller.begin_command_phase"]
c.eq("Crude Surgery begins in the start-of-Command-phase block, once", len(_surgery), 1)
c.true("...for the phase's own turn owner, across every unit wherever it is",
       bool(_surgery) and ast.unparse(_surgery[0].value) ==
       "crude_surgery_controller.begin_command_phase(state.all_squads(), turn_tracker.turn_owner)")
_tuple = next((n for n in ast.walk(_main_fn) if isinstance(n, ast.Assign)
               and any(ast.unparse(t) == "damage_choice_controllers" for t in n.targets)), None)
c.true("Krushin' Impetus is in the damage-choice list (AI pause, panel)",
       _tuple is not None and "krushin_impetus_controller" in ast.unparse(_tuple.value))
_gate = next((n for n in ast.walk(_main_fn) if isinstance(n, ast.FunctionDef)
              and n.name == "_has_unresolved_declaration"), None)
c.true("...and its open allocation holds the phase",
       _gate is not None and "krushin_impetus_controller.pending_damage_choice is not None" in ast.unparse(_gate))
c.true("the Grot Orderly is no longer built", "GrotOrderlyController" not in MAIN and "grot_orderly" not in MAIN)

c.finish()
