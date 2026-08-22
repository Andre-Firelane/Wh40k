"""Commander Farsight datasheet: stat line, the Dawn Blade's two modes, and
his two abilities (Way of the Short Blade, Puretide's Teachings). Also covers
the two follow-ups that came with him - the Twin Lance's corrected base size
and its per-model sprites.

Real objects throughout (build_squad() off the real datasheets, real
ShootingController/FightController/StratagemController/CommandPointManager/
TurnTracker), no mocks of the things under test. Every ability claim carries
an A/B.
"""

import pygame

from game import attached_units, sprites
from game.command_points import CommandPointManager
from game.factions import build_squad
from game.factions.tau_empire import (
    COMMANDER_FARSIGHT, CRISIS_STARSCYTHE, CRISIS_SUNFORGE, KROOT_CARNIVORES, THE_TWIN_LANCE,
)
from game.puretide import PURETIDE_DISCOUNT_CP, PuretideController, unit_has_puretide
from game.shooting import NORMAL_SHOOTING, ShootingController
from game.stratagems import Stratagem, StratagemController
from game.turn import TurnTracker
from game.units import ColdstarCommanderProfile, CommanderFarsightProfile, RiLantarProfile
from game.way_of_the_short_blade import SHORT_BLADE_RANGE_IN, applies, wound_modifiers

pygame.init()
pygame.display.set_mode((100, 100))

PASS = []
FAIL = []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))


def make_farsight(x=20.0, y=20.0):
    s = build_squad(COMMANDER_FARSIGHT, "Player 1", name="1 Commander Farsight 1", x_in=x, y_in=y)
    s.models[0].x_in, s.models[0].y_in = x, y
    return s


def make_crisis(x=20.0, y=22.5, datasheet=CRISIS_SUNFORGE, name="1 Crisis Sunforge Battlesuits 1"):
    s = build_squad(datasheet, "Player 1", name=name, x_in=x, y_in=y)
    for i, m in enumerate(s.models):
        m.x_in, m.y_in = x + i * 2.4, y
    return s


def make_kroot(x=26.0, y=20.0, owner="Player 2", name="1 Kroot Carnivores 1"):
    s = build_squad(KROOT_CARNIVORES, owner, name=name, x_in=x, y_in=y)
    for i, m in enumerate(s.models):
        m.x_in, m.y_in = x + (i % 5) * 1.2, y + (i // 5) * 1.2
    return s


# --- 1. Stat line, weapons, points ---------------------------------------
print("\n1. Stat line / weapons / points")

squad = make_farsight()
model = squad.models[0]
p = model.profile
stats = (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc, p.weapon_skill, p.ballistic_skill)
check('M10" T5 Sv2+ W8 Ld6+ OC2, WS2+/BS2+', stats == (10, 5, "2+", 8, "6+", 2, "2+", "2+"), str(stats))
check("Invulnerable Save (4+)", p.invulnerable_save == "4+")
check("single model", len(squad.models) == 1)
check("CHARACTER + VEHICLE/WALKER/FLY/BATTLESUIT", p.character and p.vehicle and p.walker and p.fly and p.battlesuit)
check("Deep Strike + For The Greater Good + Leader", p.deep_strike and p.for_the_greater_good and p.leader)
check("60mm base, same as the Coldstar Commander (user-supplied)",
      p.base_radius_in == ColdstarCommanderProfile.base_radius_in == 1.18)
check("points: flat 70 (EPIC HERO, no per-copy tiering)",
      COMMANDER_FARSIGHT.points_for(0, unit_index=1) == 70 and COMMANDER_FARSIGHT.points_for(0, unit_index=4) == 70)

rifle = next(w for w in model.weapons if w.name == "High-intensity Plasma Rifle")
check('High-intensity plasma rifle 24"/A2/S8/AP-3/D3',
      (rifle.range_in, rifle.attacks, rifle.strength, rifle.ap, rifle.damage) == (24, 2, 8, -3, 3))
check("it defers BS to the model (both are 2+)", rifle.ballistic_skill is None)

strike = next(w for w in model.weapons if w.name == "Dawn Blade - Strike")
sweep = next(w for w in model.weapons if w.name == "Dawn Blade - Sweep")
check("Dawn Blade - strike A4/S10/AP-2/D3",
      (strike.attacks, strike.strength, strike.ap, strike.damage) == (4, 10, -2, 3))
check("Dawn Blade - sweep A8/S6/AP-1/D1",
      (sweep.attacks, sweep.strength, sweep.ap, sweep.damage) == (8, 6, -1, 1))
check("both defer WS to the model (all are 2+)",
      strike.weapon_skill is None and sweep.weapon_skill is None)
check("both are melee, neither is [EXTRA ATTACKS] - so 04.01 makes them mutually exclusive",
      strike.weapon_type == "melee" and sweep.weapon_type == "melee"
      and not strike.extra_attacks and not sweep.extra_attacks)
check("melee profiles carry a melee range, not the RANGED default of 24\"",
      strike.range_in == 2 and sweep.range_in == 2)
check("Independent Power is recorded on the datasheet even though it is unenforceable",
      any("Independent Power" in t for t in COMMANDER_FARSIGHT.abilities_text))


# --- 2. Way of the Short Blade -------------------------------------------
print("\n2. Way of the Short Blade")

lone = make_farsight()
kroot = make_kroot(x=26.0, y=20.0)
check("A/B: a LONE Farsight leads nobody, so the ability does not apply",
      not applies(lone, kroot))

bodyguard = make_crisis()
farsight = make_farsight()
attached_units.attach(farsight, bodyguard)
led = bodyguard
check("test setup: Farsight really is attached", attached_units.is_attached_unit(led))
check("the led unit's models include Farsight",
      any(m.profile.way_of_the_short_blade for m in led.models))

near = make_kroot(x=26.0, y=20.0, name="1 Kroot Carnivores 1")
gap_near = led.min_distance_to(near)
check(f"test geometry: the near target is inside 9\" ({gap_near:.2f}\")", gap_near <= SHORT_BLADE_RANGE_IN)
check("A/B: within 9\" the ability applies", applies(led, near))
mods = wound_modifiers(led, near)
check("it is a +1 to the Wound roll (a -1 on the threshold)",
      len(mods) == 1 and mods[0].amount == -1, str([(m.amount, m.source) for m in mods]))

far = make_kroot(x=40.0, y=20.0, name="1 Kroot Carnivores 2")
check(f"A/B: beyond 9\" it does not ({led.min_distance_to(far):.2f}\")", not applies(led, far))
check("...and yields no modifier", wound_modifiers(led, far) == [])

plain = make_crisis(name="1 Crisis Starscythe Battlesuits 1", datasheet=CRISIS_STARSCYTHE)
check("A/B: an unled unit of the same distance gets nothing", not applies(plain, near))


def shooting_wound_mods(attacker, target):
    tokens = list(attacker.models) + list(target.models)
    sc = ShootingController(all_tokens=tokens, player_name="Player 1")
    sc.shooting_type = NORMAL_SHOOTING
    sc.active_squad = attacker
    return sc._wound_modifiers(target)


led_mods = shooting_wound_mods(led, near)
plain_mods = shooting_wound_mods(plain, near)
check("end-to-end: the real shooting _wound_modifiers() carries it",
      any(m.source == "Way of the Short Blade" for m in led_mods), str([m.source for m in led_mods]))
check("A/B: and does not for an unled unit",
      not any(m.source == "Way of the Short Blade" for m in plain_mods))

import inspect
from game import fight as fight_module
check('it is hooked into the FIGHT phase too ("makes an attack", not "ranged attack")',
      "way_of_the_short_blade" in inspect.getsource(fight_module))

# 19.04's grace window: the ability stops once its source model is gone.
for m in led.models:
    if m.profile.way_of_the_short_blade:
        m.current_wounds = 0
check("the ability dies with Farsight himself", not applies(led, near))


# --- 3. Puretide's Teachings ---------------------------------------------
print("\n3. Puretide's Teachings")

tt = TurnTracker()
tt.start_battle("Player 1")
cp = CommandPointManager()
cp.cp["Player 1"] = 10
log_lines = []


class _Log:
    def add(self, text, **kw):
        log_lines.append(text)


puretide = PuretideController(turn_tracker=tt, game_log=_Log())
sc = StratagemController(command_points=cp, game_log=_Log())
sc.cost_discounts.append(puretide)

target_with = make_crisis()
farsight2 = make_farsight()
attached_units.attach(farsight2, target_with)
target_without = make_crisis(name="1 Crisis Starscythe Battlesuits 2", datasheet=CRISIS_STARSCYTHE)

check("unit_has_puretide sees the attached Farsight", unit_has_puretide(target_with))
check("A/B: and not a unit without him", not unit_has_puretide(target_without))

strat = Stratagem(name="Test Stratagem", cp_cost=2, effect=lambda c, p, t: None)
check("A/B: no discount for a unit without the ability",
      sc._cost_for("Player 1", strat, [target_without], 0) == 2)
check(f"a unit with it costs {PURETIDE_DISCOUNT_CP}CP less",
      sc._cost_for("Player 1", strat, [target_with], 0) == 2 - PURETIDE_DISCOUNT_CP)
check("asking the price does NOT spend the once-per-round use",
      puretide.available("Player 1"))

before = cp.cp["Player 1"]
sc.use("Player 1", strat, [target_with])
check("using it actually spends the reduced cost", before - cp.cp["Player 1"] == 2 - PURETIDE_DISCOUNT_CP,
      f"{before} -> {cp.cp['Player 1']}")
check("...and it is logged", any("Puretide" in l for l in log_lines))
check("the once-per-round use is now spent", not puretide.available("Player 1"))

strat2 = Stratagem(name="Second Stratagem", cp_cost=2, effect=lambda c, p, t: None)
check("A/B: a second Stratagem this round pays full price",
      sc._cost_for("Player 1", strat2, [target_with], 0) == 2)
tt.advance_phase()
check("still spent within the same battle round", not puretide.available("Player 1"))
while tt.battle_round == 1:
    tt.advance_phase()
check("a new battle round refreshes it", puretide.available("Player 1"))
check("A/B: and the discount is back", sc._cost_for("Player 1", strat2, [target_with], 0) == 1)

check("the other player's use is tracked separately", puretide.available("Player 2"))

# Affordability: the discount is applied to the COST, not refunded after -
# so exactly-enough CP is enough.
cp.cp["Player 2"] = 1
sc2 = StratagemController(command_points=cp)
sc2.cost_discounts.append(puretide)
p2_target = build_squad(CRISIS_SUNFORGE, "Player 2", name="2 Crisis Sunforge Battlesuits 1", x_in=40, y_in=40)
fs2 = build_squad(COMMANDER_FARSIGHT, "Player 2", name="2 Commander Farsight 1", x_in=40, y_in=40)
attached_units.attach(fs2, p2_target)
check("A/B: 1 CP is not enough for a 2CP Stratagem without the discount",
      not StratagemController(command_points=cp).can_use("Player 2", strat, [target_without]))
check("but IS enough with it - the discount lowers the price, it is not a refund",
      sc2.can_use("Player 2", strat, [p2_target]))


# --- 4. Follow-ups: Twin Lance base size and per-model sprites ------------
print("\n4. Follow-ups (Twin Lance)")

check("Twin Lance now uses the Coldstar's 60mm base (was 0.98\")",
      RiLantarProfile.base_radius_in == ColdstarCommanderProfile.base_radius_in == 1.18)

lance = build_squad(THE_TWIN_LANCE, "Player 1", name="1 The Twin Lance 1", x_in=20, y_in=20)
paths = {m.profile.name: (sprites.sprite_for(m) or "").replace("\\", "/").rsplit("/", 1)[-1] for m in lance.models}
check("Ri'Lantar gets the Fusion art", paths.get("Ri'Lantar") == "Twin Blade Fusion.png", str(paths))
check("Ri'Locai gets the Ion art", paths.get("Ri'Locai") == "Twin Blade Ion.png", str(paths))
check("A/B: the two models genuinely resolve to DIFFERENT images",
      paths.get("Ri'Lantar") != paths.get("Ri'Locai"))
check("the panel listing shows both", len(sprites.portrait_paths(lance, 2)) == 2)
check("Farsight's own art resolves", (sprites.sprite_for(make_farsight().models[0]) or "").endswith("Commander Farsight.png"))

riptide_squad = build_squad(
    __import__("game.factions.tau_empire", fromlist=["RIPTIDE_BATTLESUIT"]).RIPTIDE_BATTLESUIT,
    "Player 1", name="1 Riptide Battlesuit 1", x_in=20, y_in=20,
)
check("regression: an ordinary squad still resolves by squad name",
      (sprites.sprite_for(riptide_squad.models[0]) or "").endswith("Riptide.png"))

print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print("  -", f)
    raise SystemExit(1)
