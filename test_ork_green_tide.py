"""Green Tide - the first of the Mecha Orks list's three detachments (stage G3) -
driven through the real controllers.

  1. the detachment: registration, DP, Force Disposition, setting, the corpus
  2. Mob-handed Brutality through the real FightController chain: [SUSTAINED HITS
     1] for BOYZ (a Warboss-led mob too, Beast Snagga Boyz not), [LETHAL HITS]
     after a charge for any ORKS INFANTRY unit - against a non-MONSTER/VEHICLE
     target only
  3. THE ATTACKS COUNT (the fix this stage made): a +A grant in the fight chain
     reaches the number of Hit dice thrown - Might Is Right and Rokkit Charge,
     measured through a real activation
  4. Ferocious Show-off: the bearer line, +1 A / +2 A at 11+ models, per bearer
  5. 'Ardboyz: the unit line, 4+ Sv at every reader of the Save characteristic
     (game/save_characteristic.py, the extraction this stage made) - and the
     Tomb Blades' Shieldvanes reaching the ones it never did
  6. Unbridled Carnage: WHEN/TARGET, +1 A in the chain AND in the dice
  7. 'Ere We Go: WHEN/TARGET, +2 on the Advance roll, never on a Charge roll
  8. Mob Mentality: WHEN/TARGET, the pick, the auto-successful rolls at all three
     roll entries, Insane Bravery refused
  9. the AI's three handlers
 10. the two small extractions (datasheet names, dice-notation plus)
 11. wiring at the source

The panel matrix is test_ork_green_tide_ui.py.

Run: python test_ork_green_tide.py
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

from ai import agent_driver, observation  # noqa: E402
from game import (  # noqa: E402
    activation_state, attached_units, config, damage_estimate, detachments, dice_notation,
    enh_ardboyz, enh_ferocious_show_off as fso, enhancements as E, force_dispositions, green_tide,
    green_tide_ere_we_go as ewg, green_tide_mob_mentality as mm, green_tide_unbridled_carnage as uc,
    movement, roll_bonus, rules_text, save_characteristic,
)
from game.battle_shock import BattleShockController  # noqa: E402
from game.command_points import CommandPointManager  # noqa: E402
from game.damage_resolution import save_thresholds  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.factions import necrons  # noqa: E402
from game.factions import orks as ork  # noqa: E402
from game.factions import tau_empire as tau  # noqa: E402
from game.fight import _melee_attack_groups  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.insane_bravery import InsaneBraveryController  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.stratagems import StratagemController  # noqa: E402
from game.turn import PHASES, PHASE_COMMAND, PHASE_FIGHT, PHASE_MOVEMENT, TurnTracker  # noqa: E402
from game.ui.unit_datacard import UnitDatacardOverlay  # noqa: E402
from game.weapons import MELEE, RANGED  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
ORK, FOE = "Player 2", "Player 1"
# War Horde is OFF in both: its Get Stuck In gives every ORKS unit [SUSTAINED
# HITS 1], and config holds it for Player 2 by default - left on, it would
# satisfy every Sustained Hits check below whether Green Tide worked or not.
GT = dict(GREEN_TIDE_PLAYERS=(ORK,), WAR_HORDE_PLAYERS=())
NO_GT = dict(GREEN_TIDE_PLAYERS=(), WAR_HORDE_PLAYERS=())

pygame.init()
pygame.display.set_mode((1200, 900))

c = tk.Checks("Ork Green Tide (Mecha Orks G3)")


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


def melee(model, name):
    return next((w for w in model.weapons if w.weapon_type == MELEE and w.name == name), None)


def kill(squad, n):
    for model in [m for m in squad.models if not m.is_dead()][:n]:
        model.current_wounds = 0


def boyz(owner=ORK, big=True, name=None):
    return tk.build(ork.BOYZ, owner, name=name or "%s Boyz 1" % owner[-1], composition_index=1 if big else 0)


def led_by(char_sheet, mob, enhancement=None):
    char = tk.build(char_sheet, mob.owner, name="%s %s 1" % (mob.owner[-1], char_sheet.name))
    if enhancement:
        E.grant(char, enhancement)
    return attached_units.attach(char, mob)


# ===========================================================================
print("\n1. the detachment")
# ===========================================================================
_gt = ork.ORKS.detachments.get("Green Tide")
c.true("Green Tide is an Ork detachment", _gt is not None)
c.eq("...costs 1 DP", getattr(_gt, "points", None), 1)
c.eq("...permits Take and Hold", getattr(_gt, "force_dispositions", None), (force_dispositions.TAKE_AND_HOLD,))
c.eq("...its rule is Mob-handed Brutality", getattr(_gt, "rule_name", None), "Mob-handed Brutality")
c.eq("...and its setting is GREEN_TIDE_PLAYERS", getattr(_gt, "setting", None), green_tide.SETTING)
c.true("the setting is one detachments.apply_to_config() writes", green_tide.SETTING in detachments.all_settings())
c.eq("nobody holds it by default", config.GREEN_TIDE_PLAYERS, ())
_md = read(os.path.join("rules", "orks", "detachments", "Green Tide.md"))
for _line in ("Friendly BOYZ units’ melee attacks have [Sustained Hits 1].",
              "that unit’s melee attacks have [Lethal Hits: non-Monster/Vehicle]."):
    c.true("the corpus prints: %s" % _line[:50], _line in _md)
c.eq("the corpus holds its three Stratagems",
     sorted(s.name for s in rules_text.detachment_stratagems("ORKS", "Green Tide")),
     ["'ERE WE GO", "MOB MENTALITY", "UNBRIDLED CARNAGE"])
c.eq("both Enhancements are engine-wired, at the printed points",
     [(s.name, s.points, s.detachment) for s in E.for_detachment("Green Tide")],
     [("Ferocious Show-off", 15, "Green Tide"), ("'Ardboyz", 25, "Green Tide")])
c.eq("...and match the descriptive records",
     [(e.name, e.points) for e in _gt.enhancements], [("Ferocious Show-off", 15), ("'Ardboyz", 25)])
c.true("the corpus prints both at those points",
       "### Ferocious Show-off - 15 pts" in _md and "### 'Ardboyz - 25 pts" in _md)


# ===========================================================================
print("\n2. Mob-handed Brutality")
# ===========================================================================
def mhb_scene(attacker_sheet=ork.BOYZ, target_sheet=tau.STRIKE_TEAM):
    f = tk.fight_scene(attacker_sheet, target_sheet, attacker_owner=ORK)
    f["fight"].fighting_squad = f["attacker"]
    return f


def adjusted(f, model, weapon, target=None):
    return f["fight"]._adjusted_weapon([(model, weapon)], target if target is not None else f["target"])


with settings_as(**GT):
    _f = mhb_scene()
    _boy = next(m for m in _f["attacker"].models if melee(m, "Choppa"))
    _choppa = melee(_boy, "Choppa")
    c.eq("a Boy's Choppa has no Sustained Hits printed", _choppa.sustained_hits, 0)
    c.eq("with Green Tide it has [SUSTAINED HITS 1] through the real fight chain",
         adjusted(_f, _boy, _choppa).sustained_hits, 1)
    c.eq("...on a copy", _choppa.sustained_hits, 0)
    _shoota = next(w for w in _boy.weapons if w.weapon_type == RANGED)
    c.true("ranged weapons are untouched", green_tide.adjusted_weapon(_shoota, _f["attacker"], _f["target"]) is _shoota)
    c.eq("no charge this turn: no [LETHAL HITS] (Tide of Muscle and the rule both wait for one)",
         adjusted(_f, _boy, _choppa).lethal_hits, False)

    _led = led_by(ork.WARBOSS, boyz(name="2 Boyz 9"))
    _boss = next(m for m in _led.models if m.profile.character)
    _bc = melee(_boss, "Kustom Choppa") or next(w for w in _boss.weapons if w.weapon_type == MELEE)
    c.eq("a Warboss leading the mob swings with [SUSTAINED HITS 1] too (19.03 - the unit is a BOYZ unit)",
         green_tide.adjusted_weapon(_bc, _led, _f["target"]).sustained_hits, 1)
    c.true("...because the attached unit is a BOYZ unit", green_tide.is_boyz_unit(_led))

    _bsb = mhb_scene(ork.BEAST_SNAGGA_BOYZ)
    _bb = next(m for m in _bsb["attacker"].models if not m.profile.character)
    _bw = next(w for w in _bb.weapons if w.weapon_type == MELEE)
    c.eq("Beast Snagga Boyz are NOT Boyz: no Sustained Hits", adjusted(_bsb, _bb, _bw).sustained_hits,
         _bw.sustained_hits)
    _bsb["attacker"].charged_this_turn = True
    c.eq("...but as ORKS INFANTRY that charged they have [LETHAL HITS] against infantry",
         adjusted(_bsb, _bb, _bw).lethal_hits, True)
    _wagon = tk.build(tau.DEVILFISH, FOE, name="1 Devilfish 1")
    c.eq("...and NOT against a VEHICLE (the condition is the target's)",
         adjusted(_bsb, _bb, _bw, target=_wagon).lethal_hits, bool(_bw.lethal_hits))
    c.eq("...and not with no target in hand", green_tide.adjusted_weapon(_bw, _bsb["attacker"], None).lethal_hits,
         bool(_bw.lethal_hits))
    _bsb["attacker"].charged_this_turn = False
    c.eq("...and not in a turn it did not charge", adjusted(_bsb, _bb, _bw).lethal_hits, bool(_bw.lethal_hits))

    import copy as _copy
    _s2 = _copy.copy(_choppa)
    _s2.sustained_hits = 2
    c.eq("never a downgrade: a [SUSTAINED HITS 2] weapon keeps its 2",
         green_tide.adjusted_weapon(_s2, _f["attacker"], _f["target"]).sustained_hits, 2)
    _sd = _copy.copy(_choppa)
    _sd.sustained_hits_notation = dice_notation.D3()
    c.true("...and a dice-notation value is left alone (the weapon comes back untouched)",
           green_tide.adjusted_weapon(_sd, _f["attacker"], _f["target"]) is _sd)

with settings_as(**NO_GT):
    _f = mhb_scene()
    _boy = next(m for m in _f["attacker"].models if melee(m, "Choppa"))
    c.eq("WITHOUT Green Tide: no Sustained Hits", adjusted(_f, _boy, melee(_boy, "Choppa")).sustained_hits, 0)
    _f["attacker"].charged_this_turn = True
    _bsb = mhb_scene(ork.BEAST_SNAGGA_BOYZ)
    _bsb["attacker"].charged_this_turn = True
    _bb = next(m for m in _bsb["attacker"].models if not m.profile.character)
    _bw = next(w for w in _bb.weapons if w.weapon_type == MELEE)
    c.eq("...and no charge-turn [LETHAL HITS]", adjusted(_bsb, _bb, _bw).lethal_hits, bool(_bw.lethal_hits))


# ===========================================================================
print("\n3. the Attacks COUNT reads the adjusted weapon")
# ===========================================================================
def hit_dice(f, pick):
    """Drive one real activation to its first Hit roll; the number of dice."""
    fc = f["fight"]
    fc.select_to_fight(f["attacker"])
    if fc.target_squad is None:
        fc.choose_target_squad(f["target"])
    if fc.current_group is None:
        groups = _melee_attack_groups(fc.fighting_squad, fc._used_other_melee_weapon, fc.one_shot_used)
        key = next((k for k, *_ in fc.weapon_eligibility() if pick(groups.get(k, []))), None)
        if key is None:
            return None
        fc.choose_weapon(key)
    hits = [v for label, v in f["dice"].rolled if label.startswith("Hit Roll")]
    return len(hits[-1]) if hits else None


def boss_group(pairs):
    return bool(pairs) and pairs[0][0].profile.character and pairs[0][1].weapon_type == MELEE


def warboss_dice(charged):
    tk.script(*([4] * 300))
    f = tk.fight_scene(ork.WARBOSS, tau.STRIKE_TEAM, attacker_owner=ORK)
    f["attacker"].charged_this_turn = charged
    return hit_dice(f, boss_group)


_calm, _hot = warboss_dice(False), warboss_dice(True)
c.true("the measurement is live (%s Hit dice uncharged)" % _calm, _calm is not None and _calm > 0)
c.eq("Might Is Right's +3 A reaches the dice: a charged Warboss throws 3 more (%s vs %s)" % (_hot, _calm),
     (_hot or 0) - (_calm or 0), 3)


def stormboyz_dice(charged):
    tk.script(*([4] * 300))
    f = tk.fight_scene(ork.STORMBOYZ, tau.STRIKE_TEAM, attacker_owner=ORK)
    f["attacker"].rokkit_charge_active = charged
    return hit_dice(f, lambda pairs: bool(pairs) and pairs[0][1].name == "Choppa"), f


_sc, _sf = stormboyz_dice(False)
_sh, _ = stormboyz_dice(True)
_n = sum(1 for m in _sf["attacker"].models if melee(m, "Choppa"))
c.eq("Rokkit Charge's +1 A reaches the dice: one more per Stormboy (%s vs %s, %d models)" % (_sh, _sc, _n),
     (_sh or 0) - (_sc or 0), _n)


# ===========================================================================
print("\n4. Ferocious Show-off")
# ===========================================================================
def safe_grant(squad, name):
    """E.grant() as a bool - a probe that breaks the bearer line must turn this
    file RED, not crash it."""
    try:
        E.grant(squad, name)
        return True
    except ValueError:
        return False


def grant_ok(sheet, name, owner=ORK, **kw):
    return safe_grant(tk.build(sheet, owner, name="x", **kw), name)


c.true("a Warboss (ORKS INFANTRY CHARACTER) may bear it", grant_ok(ork.WARBOSS, fso.FEROCIOUS_SHOW_OFF))
c.true("...and a Big Mek in Mega Armour", grant_ok(ork.BIG_MEK_MEGA_ARMOUR, fso.FEROCIOUS_SHOW_OFF))
c.eq("...a Boyz mob cannot (no CHARACTER - the model rule)", grant_ok(ork.BOYZ, fso.FEROCIOUS_SHOW_OFF), False)
c.eq("...nor a Kill Rig", grant_ok(ork.KILL_RIG, fso.FEROCIOUS_SHOW_OFF), False)
# No built Ork sheet is a CHARACTER without INFANTRY, so the INFANTRY clause is
# measured on a stand-in: a Warboss whose own profile INSTANCE loses the keyword.
_nonfoot = tk.build(ork.WARBOSS, ORK, name="x")
_nonfoot.models[0].profile.infantry = False
c.eq("...nor an ORKS CHARACTER that is not INFANTRY (a stand-in Warboss)",
     safe_grant(_nonfoot, fso.FEROCIOUS_SHOW_OFF), False)

with settings_as(**GT):
    _mob = boyz(name="2 Boyz 5")
    _led = led_by(ork.WARBOSS, _mob, fso.FEROCIOUS_SHOW_OFF)
    _boss = next(m for m in _led.models if m.profile.character)
    _nob = next(m for m in _led.models if not m.profile.character and melee(m, "Kustom Choppa"))
    c.eq("21 models: +2 A", fso.attacks_bonus(_boss), 2)
    _bw = next(w for w in _boss.weapons if w.weapon_type == MELEE)
    c.eq("...on the bearer's melee weapon", fso.adjusted_weapon(_bw, _boss).attacks, _bw.attacks + 2)
    c.eq("...not on anyone else", fso.attacks_bonus(_nob), 0)
    c.true("...and the bearer is his own attack group (_melee_attack_key)",
           fso.attack_key(_boss) and not fso.attack_key(_nob))
    from game.fight import _melee_attack_key
    _twin = next(m for m in led_by(ork.WARBOSS, boyz(name="2 Boyz 8")).models if m.profile.character)
    _tw = next(w for w in _twin.weapons if w.weapon_type == MELEE and w.name == _bw.name)
    c.true("...measured at the key itself: a bearer and a plain Warboss with the same weapon do not share a group",
           _melee_attack_key(_boss, _bw) != _melee_attack_key(_twin, _tw))
    c.true("ranged weapons are untouched",
           all(fso.adjusted_weapon(w, _boss) is w for w in _boss.weapons if w.weapon_type == RANGED))
    kill(_led, 11)
    c.eq("down to 10 living models: +1 A (the two bullets are alternatives)", fso.attacks_bonus(_boss), 1)
    _dn = tk.build(ork.BOYZ, ORK, name="dummy").models[0].weapons[0]
    _dn = __import__("copy").copy(_dn)
    _dn.weapon_type, _dn.attacks_notation = MELEE, dice_notation.D6(1)
    c.eq("a dice-notation Attacks takes it on the flat part (D6+1 -> D6+2)",
         fso.adjusted_weapon(_dn, _boss).attacks_notation, dice_notation.D6(2))
    _boss.current_wounds = 0
    c.eq("a dead bearer grants nothing", fso.attacks_bonus(_boss), 0)

with settings_as(**NO_GT):
    _mob = boyz(name="2 Boyz 6")
    _led = led_by(ork.WARBOSS, _mob, fso.FEROCIOUS_SHOW_OFF)
    _boss = next(m for m in _led.models if m.profile.character)
    c.eq("without Green Tide the bearer gains nothing", fso.attacks_bonus(_boss), 0)

with settings_as(**GT):
    def show_off_dice(with_enh):
        tk.script(*([4] * 300))
        f = tk.fight_scene(ork.BOYZ, tau.STRIKE_TEAM, attacker_owner=ORK, attacker_choices=None)
        mob = f["attacker"]
        boss = tk.build(ork.WARBOSS, ORK, name="2 Warboss 7")
        if with_enh:
            E.grant(boss, fso.FEROCIOUS_SHOW_OFF)
        led = attached_units.attach(boss, mob, game_state=f["state"])
        char = next(m for m in led.models if m.profile.character)
        char.x_in, char.y_in = led.models[0].x_in, led.models[0].y_in
        f["state"].add_token(char)
        f["attacker"] = led
        return hit_dice(f, boss_group)
    _plain, _shown = show_off_dice(False), show_off_dice(True)
    c.eq("through a real activation the bearer throws 2 more Hit dice (10 Boyz and him: 11 models, +2 A)",
         (_shown or 0) - (_plain or 0), 2)


# ===========================================================================
print("\n5. 'Ardboyz and the Save characteristic")
# ===========================================================================
c.true("a Boyz unit may take it", grant_ok(ork.BOYZ, enh_ardboyz.ARDBOYZ))
c.eq("...Beast Snagga Boyz may not (not BOYZ)", grant_ok(ork.BEAST_SNAGGA_BOYZ, enh_ardboyz.ARDBOYZ), False)
c.eq("...nor a Warboss", grant_ok(ork.WARBOSS, enh_ardboyz.ARDBOYZ), False)

_pts = boyz(name="2 Boyz 11")
_before = _pts.points
safe_grant(_pts, enh_ardboyz.ARDBOYZ)
c.eq("it costs 25 points", _pts.points - _before, 25)
c.true("...and marks every Boy (a unit-level Enhancement)",
       all(getattr(m.profile, "ardboyz", False) for m in _pts.models))


def ard_mob():
    mob = boyz(name="2 Boyz 12", big=False)
    safe_grant(mob, enh_ardboyz.ARDBOYZ)
    return led_by(ork.PAINBOY, mob)


with settings_as(**GT):
    _led = ard_mob()
    _boy = next(m for m in _led.models if not m.profile.character)
    _doc = next(m for m in _led.models if m.profile.character)
    c.eq("the printed Sv is 5+ (Boy and Painboy)", (_boy.profile.armor_save, _doc.profile.armor_save), ("5+", "5+"))
    c.eq("save_characteristic: every model of the attached unit has 4+ (19.04)",
         sorted({save_characteristic.armour_save(m) for m in _led.models}), ["4+"])
    _gun = tau.STRIKE_TEAM
    _w = next(w for w in tk.build(tau.STRIKE_TEAM, FOE).models[0].weapons if w.weapon_type == RANGED)
    c.eq("reader 1 - the save roll: threshold 4", save_thresholds(_boy, _w)[0], 4)
    c.eq("reader 2 - the AI estimate (defender_soak)", damage_estimate.defender_soak(_led)[0].armor_save, "4+")
    _obs = observation.defensive_profile(_led)
    c.eq("reader 3 - the AI observation", _obs["save"], "4+")
    c.eq("...including the attached character", [a["save"] for a in _obs.get("attached_characters", [])], ["4+"])
    c.true("reader 4 - the AI's matchup hint", "Sv4+" in agent_driver._target_profile_hint(_led))
    _rows = dict(UnitDatacardOverlay().card_parts(_boy)["stat_rows"])
    c.eq("reader 5 - the datacard", _rows.get("Sv"), "4+")
    with settings_as(**NO_GT):
        _groups_printed = len(_led.allocation_groups())
    c.eq("reader 6 - the allocation order: the whole unit moved to 4+ together, so no group splits",
         len(_led.allocation_groups()), _groups_printed)
    kill(_led, sum(1 for m in _led.models if not m.profile.character))
    c.eq("the mob destroyed, the Painboy is back to 5+ (the source is gone)",
         save_characteristic.armour_save(_doc), "5+")

with settings_as(**NO_GT):
    _led = ard_mob()
    c.eq("WITHOUT Green Tide the unit keeps its printed 5+",
         sorted({save_characteristic.armour_save(m) for m in _led.models}), ["5+"])

# The Tomb Blades' Shieldvanes - the first override, now at every reader.
_tb = tk.build(necrons.TOMB_BLADES, FOE, name="1 Tomb Blades 1", composition_index=1)
_vane = _tb.models[0]
_vane.shieldvanes = True
c.eq("Shieldvanes: the bearer's Save characteristic is 3+", save_characteristic.armour_save(_vane), "3+")
c.eq("...the datacard shows it (it used to print the profile's)",
     dict(UnitDatacardOverlay().card_parts(_vane)["stat_rows"]).get("Sv"), "3+")
c.eq("...and the allocation order puts the bearer in a group of its own",
     sorted(len(g) for g in _tb.allocation_groups()), sorted([1, len(_tb.models) - 1]))


# ===========================================================================
print("\n6. Unbridled Carnage")
# ===========================================================================
def uc_rig(owner=ORK, phase=PHASE_FIGHT, cp=10, charged=True, sheet=ork.BOYZ):
    f = tk.fight_scene(sheet, tau.STRIKE_TEAM, attacker_owner=owner)
    f["attacker"].charged_this_turn = charged
    ctrl = uc.UnbridledCarnageController(strat(cp), turn_tracker=turn_at(phase, owner),
                                         fight_controller=f["fight"], game_log=tk.Log())
    return f, ctrl


with settings_as(**GT):
    _f, _u = uc_rig()
    c.true("offered for a charged Boyz mob in the Fight phase", _u.can_use(_f["attacker"]))
    c.eq("...not for one that did not charge", uc_rig(charged=False)[1].can_use(uc_rig(charged=False)[0]["attacker"]), False)
    _fb, _ub = uc_rig(sheet=ork.BEAST_SNAGGA_BOYZ)
    c.eq("...not for Beast Snagga Boyz (TARGET: that BOYZ unit)", _ub.can_use(_fb["attacker"]), False)
    _fm, _um = uc_rig(phase=PHASE_MOVEMENT)
    c.eq("...not outside the Fight phase", _um.can_use(_fm["attacker"]), False)
    _fo, _uo = uc_rig()
    _uo.turn_tracker = turn_at(PHASE_FIGHT, FOE)
    c.true("...but in the OPPONENT's Fight phase too ('Fight phase', no 'your')", _uo.can_use(_fo["attacker"]))
    _fc0, _uc0 = uc_rig(cp=0)
    c.eq("...not without the CP", _uc0.can_use(_fc0["attacker"]), False)
    _f2, _u2 = uc_rig()
    _f2["fight"].fought_squad_ids.add(_f2["attacker"])
    c.eq("...not once the unit has fought", _u2.can_use(_f2["attacker"]), False)

    _f, _u = uc_rig()
    _boy = next(m for m in _f["attacker"].models if melee(m, "Choppa"))
    _before = _u.stratagem_controller.command_points.cp[ORK]
    c.true("bought", _u.use(_f["attacker"]))
    c.eq("...for 1CP", _before - _u.stratagem_controller.command_points.cp[ORK], 1)
    c.true("...the unit carries the grant", uc.is_active(_f["attacker"]))
    _f["fight"].fighting_squad = _f["attacker"]
    c.eq("+1 A in the real fight chain", adjusted(_f, _boy, melee(_boy, "Choppa")).attacks,
         melee(_boy, "Choppa").attacks + 1)
    c.eq("...and not offered again", _u.can_use(_f["attacker"]), False)
    uc.reset_phase([_f["attacker"]])
    c.eq("reset_phase() ends it", uc.is_active(_f["attacker"]), False)

    def carnage_dice(bought):
        tk.script(*([4] * 300))
        f, ctrl = uc_rig()
        if bought:
            ctrl.use(f["attacker"])
        return hit_dice(f, lambda pairs: bool(pairs) and pairs[0][1].name == "Choppa"), f
    _p, _pf = carnage_dice(False)
    _q, _ = carnage_dice(True)
    _boys = sum(1 for m in _pf["attacker"].models if melee(m, "Choppa"))
    c.eq("through a real activation: one more Hit die per Choppa Boy (%s vs %s)" % (_q, _p), (_q or 0) - (_p or 0), _boys)
    c.true("the AI's estimate of the extra attacks is positive",
           uc.expected_extra_wounds(_pf["attacker"], _pf["target"]) > 0)

with settings_as(**NO_GT):
    _f, _u = uc_rig()
    c.eq("WITHOUT Green Tide it is not offered", _u.can_use(_f["attacker"]), False)


# ===========================================================================
print("\n7. 'Ere We Go")
# ===========================================================================
def ewg_rig(sheet=ork.BOYZ, owner=ORK, phase=PHASE_MOVEMENT, cp=10):
    st = GameState()
    squad = tk.line_up(tk.build(sheet, owner, name="%s %s 1" % (owner[-1], sheet.name)), y=20.0)
    for m in squad.models:
        st.add_token(m)
    tt = turn_at(phase, owner)
    dm = DiceManager()
    mc = MovementController(obstacles=st.obstacles, turn_tracker=tt, all_tokens=st.tokens, dice_manager=dm)
    ctrl = ewg.EreWeGoController(strat(cp), turn_tracker=tt, movement_controller=mc, game_log=tk.Log())
    return squad, mc, ctrl, dm


with settings_as(**GT):
    _s, _mc, _e, _dm = ewg_rig()
    c.true("offered for a Boyz unit in your Movement phase", _e.can_use(_s))
    _sb, _mcb, _eb, _ = ewg_rig(ork.BEAST_SNAGGA_BOYZ)
    c.true("...and for Beast Snagga Boyz (BEAST SNAGGA BOYZ/BOYZ)", _eb.can_use(_sb))
    _sw, _mcw, _ew, _ = ewg_rig(ork.WARBIKERS)
    c.eq("...not for Warbikers", _ew.can_use(_sw), False)
    _so, _mco, _eo, _ = ewg_rig()
    _eo.turn_tracker = turn_at(PHASE_MOVEMENT, FOE)
    c.eq("...not in the opponent's Movement phase", _eo.can_use(_so), False)
    _sm, _mcm, _em, _ = ewg_rig()
    _mcm.moved_squad_ids.add(_sm)
    c.eq("...not once the unit has moved", _em.can_use(_sm), False)
    _sa, _mca, _ea, _ = ewg_rig()
    _mca.advanced_squad_ids.add(_sa)
    c.eq("...not once it has Advanced", _ea.can_use(_sa), False)

    _s, _mc, _e, _dm = ewg_rig()
    c.eq("before: no Advance term", movement.advance_roll_modifiers(_s), [])
    c.true("bought", _e.use(_s))
    c.eq("the Advance roll gains +2 ('Ere We Go)", movement.advance_roll_modifiers(_s), [("'Ere We Go", 2)])
    c.eq("advance_total(): a 3 becomes 5", movement.advance_total(_s, [3]), 5)
    c.eq("...and NOTHING on a Charge roll (roll_bonus.sources(), the Charge side)", roll_bonus.sources(_s), [])
    c.eq("...nor in advance_and_charge_bonus()", roll_bonus.advance_and_charge_bonus(_s), 0)
    tk.script(3)
    _mc.select(_s.models[0])
    _mc.start_move()
    _range0 = _mc.remaining_range.get(_s.models[0].id)
    _mc.start_run()
    _range1 = _mc.remaining_range.get(_s.models[0].id)
    c.eq("a real MovementController Advance with a scripted 3 adds 5\"",
         round((_range1 or 0) - (_range0 or 0), 3), 5.0)
    ewg.reset_phase([_s])
    c.eq("reset_phase() ends it", movement.advance_roll_modifiers(_s), [])

with settings_as(**NO_GT):
    _s, _mc, _e, _dm = ewg_rig()
    c.eq("WITHOUT Green Tide it is not offered", _e.can_use(_s), False)


# ===========================================================================
print("\n8. Mob Mentality")
# ===========================================================================
def mm_rig(owner=ORK, phase=PHASE_COMMAND, cp=10, gap=6.0, far_gap=30.0, visible=None, big=True):
    st = GameState()
    mob = tk.line_up(boyz(owner, big=big, name="%s Boyz 1" % owner[-1]), x=10.0, y=20.0, spacing=1.2)
    near = tk.line_up(tk.build(ork.BEAST_SNAGGA_BOYZ, owner, name="%s Beast Snagga Boyz 1" % owner[-1]),
                      x=10.0, y=20.0 + gap, spacing=1.2)
    far = tk.line_up(tk.build(ork.BEAST_SNAGGA_BOYZ, owner, name="%s Beast Snagga Boyz 2" % owner[-1]),
                     x=10.0, y=20.0 + far_gap, spacing=1.2)
    for squad in (mob, near, far):
        for m in squad.models:
            st.add_token(m)
    kill(near, 6)
    kill(far, 6)
    # "Below half strength" counts squad.models, which only the per-frame death
    # sweep shortens - so the scene runs it, as a frame would.
    st.remove_dead_models()
    tt = turn_at(phase, owner)
    dice = tk.RecordingDice()
    log = tk.Log()
    bsc = BattleShockController(game_log=log, dice_manager=dice, turn_tracker=tt, all_tokens=st.tokens)
    dec = tk.DecisionManager()
    sc = strat(cp)
    ctrl = mm.MobMentalityController(sc, battle_shock_controller=bsc, turn_tracker=tt, decision_manager=dec,
                                     all_tokens=st.tokens, game_log=log, visible=visible)
    return SimpleNamespace(state=st, mob=mob, near=near, far=far, tt=tt, dice=dice, log=log, bsc=bsc,
                           dec=dec, sc=sc, ctrl=ctrl)


with settings_as(**GT):
    r = mm_rig()
    c.true("the unit below half strength owes a roll (the premise)", r.bsc.can_roll(r.near))
    c.true("offered on a 20-model Boyz mob at the start of your Command phase", r.ctrl.can_use(r.mob))
    c.eq("candidates: the unit in 12\" that owes a roll - not the one 30\" away, not the mob (owes none)",
         [s.name for s in r.ctrl.candidates(r.mob)], [r.near.name])
    c.eq("...not on a 10-model mob (13+ models)", mm_rig(big=False).ctrl.can_use(mm_rig(big=False).mob), False)
    _r = mm_rig(phase=PHASE_MOVEMENT)
    c.eq("...not outside the Command phase", _r.ctrl.can_use(_r.mob), False)
    _r = mm_rig()
    _r.ctrl.turn_tracker = turn_at(PHASE_COMMAND, FOE)
    c.eq("...not in the opponent's Command phase", _r.ctrl.can_use(_r.mob), False)
    _r = mm_rig(gap=20.0)
    c.eq("...not when nothing in 12\" owes a roll (it would buy nothing)", _r.ctrl.can_use(_r.mob), False)
    _r = mm_rig(visible=lambda a, b: False)
    c.eq("...not when the unit is not VISIBLE to the mob", _r.ctrl.can_use(_r.mob), False)
    _r = mm_rig(cp=0)
    c.eq("...not without the CP", _r.ctrl.can_use(_r.mob), False)
    _r = mm_rig()
    _r.bsc.rolled_squad_ids.add(_r.far)
    c.eq("...not once the Battle-shock step has begun (a roll of yours made)", _r.ctrl.can_use(_r.mob), False)
    _r = mm_rig()
    _r.bsc.rolled_squad_ids.add(tk.build(ork.BOYZ, FOE, name="1 Boyz 99"))
    c.true("...an OPPONENT's roll does not close it", _r.ctrl.can_use(_r.mob))

    # A sole candidate is taken without a prompt, and paid for.
    r = mm_rig()
    _cp = r.sc.command_points.cp[ORK]
    c.true("pressed with one candidate", r.ctrl.use(r.mob))
    c.eq("...no prompt", r.dec.is_pending, False)
    c.eq("...1CP", _cp - r.sc.command_points.cp[ORK], 1)
    c.true("...and the candidate's rolls auto-pass", mm.auto_passes(r.near))
    c.eq("...not the mob's (TARGET and beneficiary differ)", mm.auto_passes(r.mob), False)
    c.true("rule 15.01 marks the MOB as the target", (ORK, r.mob) in r.sc.targeted_this_phase)

    # The 08.03 roll: no dice, a pass.
    r.near.battle_shocked = True
    r.bsc.start_roll(r.near)
    c.eq("the 08.03 roll throws no dice", r.dice.rolled, [])
    c.eq("...and passes: no longer battle-shocked", r.near.battle_shocked, False)
    c.true("...it counts as this phase's roll", r.near in r.bsc.rolled_squad_ids)
    c.true("...and the log names Mob Mentality", any("Mob Mentality" in line for line in r.log.lines))

    # A forced roll: the dice are thrown (six callers wait for them) and graded a pass.
    r = mm_rig()
    r.ctrl.use(r.mob)
    tk.script(1, 1)
    c.true("a forced roll still STARTS (its caller waits for the acknowledgement)",
           r.bsc.start_forced_roll(r.near, "Nightmare Shroud", penalty=1))
    c.true("...shown as automatically successful", "automatically successful (Mob Mentality)" in r.dice.rolled[-1][0])
    r.dice.acknowledge()
    r.bsc.on_dice_acknowledged()
    c.eq("...and a roll of 1+1 passes", r.near.battle_shocked, False)

    # Two candidates: a prompt; the pick pays; Cancel costs nothing.
    r = mm_rig()
    kill(r.mob, 11)
    r.state.remove_dead_models()
    c.eq("the mob itself owes a roll now (below half) - but it is below 13 models too",
         r.ctrl.can_use(r.mob), False)
    r = mm_rig()
    _third = tk.line_up(tk.build(ork.BOYZ, ORK, name="2 Boyz 3"), x=20.0, y=24.0, spacing=1.2)
    for m in _third.models:
        r.state.add_token(m)
    kill(_third, 6)
    r.state.remove_dead_models()
    c.eq("two candidates", [s.name for s in r.ctrl.candidates(r.mob)], sorted([r.near.name, _third.name]))
    _cp = r.sc.command_points.cp[ORK]
    r.ctrl.use(r.mob)
    c.true("...a prompt opens", r.dec.is_pending)
    c.eq("...and nothing is paid yet", r.sc.command_points.cp[ORK], _cp)
    tk.pick_option(r.dec, "Mob Mentality: %s" % _third.name)
    c.eq("the pick pays", _cp - r.sc.command_points.cp[ORK], 1)
    c.true("...and covers the picked unit", mm.auto_passes(_third) and not mm.auto_passes(r.near))
    r2 = mm_rig()
    _t2 = tk.line_up(tk.build(ork.BOYZ, ORK, name="2 Boyz 4"), x=20.0, y=24.0, spacing=1.2)
    for m in _t2.models:
        r2.state.add_token(m)
    kill(_t2, 6)
    r2.state.remove_dead_models()
    _cp = r2.sc.command_points.cp[ORK]
    r2.ctrl.use(r2.mob)
    tk.pick_option(r2.dec, mm.CANCEL_LABEL)
    c.eq("Cancel costs nothing", r2.sc.command_points.cp[ORK], _cp)
    c.true("...and the button is back", r2.ctrl.can_use(r2.mob))

    # Insane Bravery would buy nothing.
    r = mm_rig()
    ib = InsaneBraveryController(r.sc, r.bsc, turn_tracker=r.tt)
    c.true("Insane Bravery is offered before (the counter-proof)", ib.can_use(r.near))
    r.ctrl.use(r.mob)
    ok, why = ib.why_not(r.near)
    c.eq("...and refused after, naming Mob Mentality", (ok, "Mob Mentality" in (why or "")), (False, True))
    mm.reset_phase([r.near])
    c.eq("reset_phase() ends it", mm.auto_passes(r.near), False)

with settings_as(**NO_GT):
    r = mm_rig()
    c.eq("WITHOUT Green Tide it is not offered", r.ctrl.can_use(r.mob), False)


# ===========================================================================
print("\n9. the AI")
# ===========================================================================
with settings_as(**GT):
    r = mm_rig()
    _tokens = r.state.tokens
    c.true("Mob Mentality: the AI buys it for the unit that would fail",
           agent_driver._handle_mob_mentality(ORK, _tokens, r.ctrl, game_log=tk.Log()))
    c.true("...and covers it", mm.auto_passes(r.near))
    r = mm_rig(gap=20.0)
    c.eq("...not when nothing in reach owes a roll",
         agent_driver._handle_mob_mentality(ORK, r.state.tokens, r.ctrl), False)
    c.eq("...and never with no controller", agent_driver._handle_mob_mentality(ORK, [], None), False)

    _f, _u = uc_rig()
    c.true("Unbridled Carnage: the AI buys it for a charged, engaged Boyz mob",
           agent_driver._handle_unbridled_carnage(ORK, _f["state"].tokens, _f["fight"], _u, game_log=tk.Log()))
    c.true("...the grant is up", uc.is_active(_f["attacker"]))
    _f, _u = uc_rig(charged=False)
    c.eq("...not for a mob that did not charge",
         agent_driver._handle_unbridled_carnage(ORK, _f["state"].tokens, _f["fight"], _u), False)

    _s, _mc, _e, _dm = ewg_rig()
    c.true("'Ere We Go: bought for a Boyz unit the AI decided to Advance with",
           agent_driver._buy_ere_we_go(ORK, _s, _e, game_log=tk.Log()))
    c.eq("...not twice", agent_driver._buy_ere_we_go(ORK, _s, _e), False)
    _sw, _mcw, _ew, _ = ewg_rig(ork.WARBIKERS)
    c.eq("...not for Warbikers", agent_driver._buy_ere_we_go(ORK, _sw, _ew), False)
    _so, _mco, _eo, _ = ewg_rig()
    c.eq("...not for the other player's unit (a fresh board, so only the owner test refuses)",
         agent_driver._buy_ere_we_go(FOE, _so, _eo), False)
    c.true("...while the owner may (the counter-proof)", agent_driver._buy_ere_we_go(ORK, _so, _eo))
    c.eq("the fail chance of Ld 7+ is 15/36", round(agent_driver._battle_shock_fail_chance(r.near, []), 4),
         round(15 / 36, 4))


# ===========================================================================
print("\n10. the two small extractions")
# ===========================================================================
_led = led_by(ork.WARBOSS, boyz(name="2 Boyz 20"))
c.eq("unit_datasheet_names(): the mob and its leader", attached_units.unit_datasheet_names(_led), ["Boyz", "Warboss"])
c.true("unit_is_datasheet()", attached_units.unit_is_datasheet(_led, ("Boyz",))
       and not attached_units.unit_is_datasheet(_led, ("Beast Snagga Boyz",)))
c.eq("a hand-built squad with no datasheet has none",
     attached_units.unit_datasheet_names(SimpleNamespace(datasheet=None, attached_components=())), [])
c.eq("dice_notation.plus() keeps the dice count (2D6+1 -> 2D6+3)",
     dice_notation.plus(dice_notation.D6(1, dice=2), 2), dice_notation.D6(3, dice=2))
c.eq("...and None stays None", dice_notation.plus(None, 1), None)
for _mod in ("enhancements", "far_reaching_doom"):
    c.true("game/%s.py asks the extraction" % _mod, "attached_units.unit_" in read(os.path.join("game", _mod + ".py")))
for _mod in ("rokkit_charge", "high_speed_carnage", "might_is_right", "psychic_communion"):
    c.true("game/%s.py asks dice_notation.plus()" % _mod, "dice_notation.plus(" in read(os.path.join("game", _mod + ".py")))


# ===========================================================================
print("\n11. wiring at the source")
# ===========================================================================
MAIN = read("main.py")
TREE = ast.parse(MAIN)
_registered = {ast.unparse(n.args[0].func) for n in ast.walk(TREE)
               if isinstance(n, ast.Call) and ast.unparse(n.func) == "proactive_stratagems.add"
               and n.args and isinstance(n.args[0], ast.Call)}
for _cls in ("UnbridledCarnageController", "EreWeGoController", "MobMentalityController"):
    c.true("main.py registers %s on the panel registry" % _cls, _cls in _registered)
for _name in ("unbridled_carnage_controller", "ere_we_go_controller", "mob_mentality_controller"):
    c.true("...resets %s at the phase boundary" % _name, "%s.reset_phase(_horde_squads)" % _name in MAIN)
    c.eq("...and hands it to the AI", sum(1 for n in ast.walk(TREE) if isinstance(n, ast.keyword)
                                        and n.arg == _name and ast.unparse(n.value) == _name), 1)
_mmc = next((n for n in ast.walk(TREE) if isinstance(n, ast.Call)
             and ast.unparse(n.func) == "MobMentalityController"), None)
_vis = next((k.value for k in (_mmc.keywords if _mmc is not None else []) if k.arg == "visible"), None)
c.true("Mob Mentality gets the real line-of-sight test (a lambda over has_line_of_sight)",
       isinstance(_vis, ast.Lambda) and "line_of_sight.has_line_of_sight(" in ast.unparse(_vis))
_fight = read(os.path.join("game", "fight.py"))
for _call in ("green_tide.adjusted_weapon(", "green_tide_unbridled_carnage.adjusted_weapon(weapon, self.fighting_squad)",
              "enh_ferocious_show_off.adjusted_weapon(weapon, pairs[0][0] if pairs else None)",
              "enh_ferocious_show_off.attack_key(model)"):
    c.true("fight.py: %s" % _call, _call in _fight)
c.true("movement.py folds the Advance-only bonus",
       "roll_bonus_advance_sources(squad, all_tokens)" in read(os.path.join("game", "movement.py")))
c.true("charge.py does NOT (it reads sources())", "advance_sources" not in read(os.path.join("game", "charge.py")))
_bs = read(os.path.join("game", "battle_shock.py"))
c.eq("battle_shock.py asks auto_success_source() at its roll entries (start_roll + the shared dice start)",
     _bs.count("= auto_success_source(squad)"), 2)
c.true("Insane Bravery asks it too", "auto_success_source(squad)" in read(os.path.join("game", "insane_bravery.py")))
_agent = read(os.path.join("ai", "agent_driver.py"))
c.true("the AI asks Mob Mentality BEFORE its first Battle-shock roll",
       0 <= _agent.find("acted = _handle_mob_mentality(") < _agent.find("acted = _handle_battle_shock("))
c.true("...buys 'Ere We Go at the Advance decision", "_buy_ere_we_go(player, squad, ere_we_go_controller, game_log)" in _agent)
c.true("...and Unbridled Carnage in the Fight handler",
       "_handle_unbridled_carnage(player, all_tokens, fight_controller, unbridled_carnage_controller, game_log)" in _agent)
c.true("the three grants are saved (SQUAD_FLAGS)",
       {"unbridled_carnage_active", "ere_we_go_active", "mob_mentality_active"} <= set(activation_state.SQUAD_FLAGS))

c.finish()
