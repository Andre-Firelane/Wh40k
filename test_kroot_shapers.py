"""The three Kroot Shaper datasheets: Flesh, Trail and War Shaper.

One suite for three datasheets because they SHARE a stat line
(KrootShaperProfile), the same four core abilities and the same LEADER line -
so the thing most worth pinning is that they agree with each other, which three
separate suites could not express.

Real objects throughout: the real datasheets, the real FightController,
the real StratagemController and CommandPointManager, the real attach().
A/B probes accompany every ability claim - each is listed next to the check it
protects, and each was run and confirmed to break the suite.

  1. Stat line, base, keywords, points, loadouts, the one wargear swap
  2. Ritual Butchery       [SUSTAINED HITS 1] on the led unit's melee weapons
  3. Rites of Feasting     Feel No Pain 6+, upgraded to 5+ after a Fight kill
  4. War Leader            1 CP off a Stratagem targeting his unit
  5. Root of Honour        end Battle-shock on a KROOT unit within 12"
  6. What is deliberately NOT wired, and the source guards
"""

import copy

import testkit as tk
from game import ritual_butchery, rites_of_feasting
from game.attached_units import attach, can_attach
from game.battle_shock import BattleShockController
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.factions.tau_empire import (
    KROOT_CARNIVORES, KROOT_FLESH_SHAPER, KROOT_TRAIL_SHAPER, KROOT_WAR_SHAPER,
    WAR_SHAPER_DART_BOW_TO_BLADESTAVE,
)
from game.feel_no_pain import current_feel_no_pain
from game.root_of_honour import RootOfHonourController
from game.stratagems import Stratagem, StratagemController
from game.turn import TurnTracker
from game.units import KrootShaperProfile
from game.war_leader import WarLeaderDiscount

ck = tk.Checks("Kroot Shapers")

SHEETS = {
    "Kroot Flesh Shaper": KROOT_FLESH_SHAPER,
    "Kroot Trail Shaper": KROOT_TRAIL_SHAPER,
    "Kroot War Shaper": KROOT_WAR_SHAPER,
}


def shaper(sheet, owner="Player 1", choices=None):
    """Named the way main.py names squads - sprites._squad_key() matches the
    datasheet name as a SUBSTRING of the squad name, so a test squad named
    anything else finds different art than the real game would."""
    return tk.build(sheet, owner, name=f"1 {sheet.name} 1", choices=choices)


# --- 1. Stat line, keywords, points, loadouts -----------------------------
print("\n1. Stat line, keywords, points, loadouts")

for name, sheet in SHEETS.items():
    squad = shaper(sheet)
    model = squad.models[0]
    profile = model.profile
    ck.eq(f"{name}: one model", len(squad.models), 1)
    ck.eq(f"{name}: stat line",
          (profile.movement_in, profile.toughness, profile.armor_save, profile.wounds,
           profile.leadership, profile.oc),
          (7, 3, "6+", 3, "7+", 1))
    ck.eq(f"{name}: WS/BS off the weapon rows (all print 2+/4+)",
          (profile.weapon_skill, profile.ballistic_skill), ("2+", "4+"))
    # Printed 32mm, so this one is arithmetic rather than an assumption:
    # 32 / 2 / 25.4 = 0.6299...
    ck.true(f"{name}: 32mm base", abs(profile.base_radius_in - 32 / 2 / 25.4) < 0.001)
    ck.true(f"{name}: no invulnerable save printed", profile.invulnerable_save == "-")
    ck.true(f"{name}: CHARACTER + INFANTRY + KROOT",
            profile.character and profile.infantry and profile.kroot)
    ck.true(f"{name}: Infiltrators / Stealth / Scouts 7\" / Leader",
            profile.infiltrators and profile.stealth
            and profile.scouts == 7.0 and profile.leader)
    # Kroot are auxiliaries: the datasheets print neither, exactly like Kroot
    # Carnivores and unlike every Fire Warrior datasheet.
    ck.true(f"{name}: no For The Greater Good, no MARKERLIGHT",
            not profile.for_the_greater_good and not profile.markerlight)
    ck.true(f"{name}: SHAPER keyword", "SHAPER" in sheet.keywords)

# The shared base class is the point of the arrangement - three copies of one
# stat line would drift the first time one of them was corrected.
ck.true("all three subclass one shared stat line",
        all(issubclass(s.model_lines[0].profile_cls, KrootShaperProfile)
            for s in SHEETS.values()))

ck.eq("Flesh Shaper points", shaper(KROOT_FLESH_SHAPER).points, 45)
ck.eq("Trail Shaper points", shaper(KROOT_TRAIL_SHAPER).points, 50)
ck.eq("War Shaper points", shaper(KROOT_WAR_SHAPER).points, 60)

ck.eq("Flesh Shaper loadout",
      sorted(w.name for w in shaper(KROOT_FLESH_SHAPER).models[0].weapons),
      ["Kroot Scattergun", "Twin Ritualistic Blades"])
ck.eq("Trail Shaper loadout",
      sorted(w.name for w in shaper(KROOT_TRAIL_SHAPER).models[0].weapons),
      ["Kroot Rifle", "Shaper's Blade"])
ck.eq("War Shaper loadout",
      sorted(w.name for w in shaper(KROOT_WAR_SHAPER).models[0].weapons),
      ["Dart-bow and Tri-blade", "Kroot Pistol", "Shaper's Blade"])

# The Shaper's blade is ONE class shared by two datasheets, not a copy each.
ck.eq("Shaper's blade is the same class on both datasheets",
      type(next(w for w in shaper(KROOT_TRAIL_SHAPER).models[0].weapons
                if w.name == "Shaper's Blade")),
      type(next(w for w in shaper(KROOT_WAR_SHAPER).models[0].weapons
                if w.name == "Shaper's Blade")))

# Weapon numbers, straight off the printed rows.
_scatter = next(w for w in shaper(KROOT_FLESH_SHAPER).models[0].weapons
                if w.name == "Kroot Scattergun")
ck.eq("Kroot scattergun 12\" A2 S4 AP0 D1 [ASSAULT]",
      (_scatter.range_in, _scatter.attacks, _scatter.strength, _scatter.ap,
       _scatter.damage, _scatter.assault), (12, 2, 4, 0, 1, True))
_blades = next(w for w in shaper(KROOT_FLESH_SHAPER).models[0].weapons
               if w.name == "Twin Ritualistic Blades")
ck.eq("Twin ritualistic blades A4 S5 AP-1 D1 [TWIN-LINKED]",
      (_blades.attacks, _blades.strength, _blades.ap, _blades.damage,
       _blades.twin_linked), (4, 5, -1, 1, True))
_dartbow = next(w for w in shaper(KROOT_WAR_SHAPER).models[0].weapons
                if w.name == "Dart-bow and Tri-blade")
ck.eq("Dart-bow 24\" S4 AP0 D2, ANTI-INFANTRY 3+",
      (_dartbow.range_in, _dartbow.strength, _dartbow.ap, _dartbow.damage,
       _dartbow.anti), (24, 4, 0, 2, ("INFANTRY", 3)))
# Printed "D3+1" Attacks, so `attacks` is only the preview and the real count
# is rolled - the notation is what the engine actually uses.
ck.true("Dart-bow Attacks is a D3+1 notation, not a fixed number",
        _dartbow.attacks_notation is not None)
ck.true("Dart-bow prints [ASSAULT] and [HEAVY] together",
        _dartbow.assault and _dartbow.heavy)

# The one wargear option on any of the three: a RANGED weapon traded for a
# MELEE one, which leaves him with only the Kroot pistol at range.
_swapped = shaper(KROOT_WAR_SHAPER,
                  choices={"Kroot War Shaper": {WAR_SHAPER_DART_BOW_TO_BLADESTAVE: 1}})
ck.eq("War Shaper swap: dart-bow out, bladestave in",
      sorted(w.name for w in _swapped.models[0].weapons),
      ["Bladestave and Prey-hook", "Kroot Pistol", "Shaper's Blade"])
_bladestave = next(w for w in _swapped.models[0].weapons
                   if w.name == "Bladestave and Prey-hook")
ck.eq("Bladestave A4 S5 AP-1 D2 [LETHAL HITS]",
      (_bladestave.attacks, _bladestave.strength, _bladestave.ap,
       _bladestave.damage, _bladestave.lethal_hits), (4, 5, -1, 2, True))
ck.eq("the other two have no wargear options at all",
      [len(KROOT_FLESH_SHAPER.wargear_options), len(KROOT_TRAIL_SHAPER.wargear_options)],
      [0, 0])
ck.eq("no Shaper takes drones (they are Kroot)",
      [len(s.gear_options) for s in SHEETS.values()], [0, 0, 0])

# LEADER, read off the points list's own `leads` table by can_attach().
# can_attach() returns a list of REASONS it is not allowed - empty means
# allowed - so these read inverted on purpose.
for name, sheet in SHEETS.items():
    ck.eq(f"{name} can lead Kroot Carnivores",
          can_attach(shaper(sheet), shaper(KROOT_CARNIVORES)), [])
ck.true("a Shaper cannot lead another Shaper (both are leader units)",
        bool(can_attach(shaper(KROOT_FLESH_SHAPER), shaper(KROOT_WAR_SHAPER))))
# KROOT FARSTALKERS is named on all three LEADER lines. It had no datasheet
# when this suite was written, and the pin said so - which is exactly why
# building it (Etappe 2) turned this line red rather than passing unnoticed.
# The pairing now works in both directions, so that is what is asserted.
from game.factions.tau_empire import KROOT_FARSTALKERS  # noqa: E402
ck.true("Kroot Farstalkers is on all three LEADER lines",
        all("Kroot Farstalkers" in s.points.leads for s in SHEETS.values()))
for name, sheet in SHEETS.items():
    ck.eq(f"{name} can lead Kroot Farstalkers",
          can_attach(shaper(sheet), shaper(KROOT_FARSTALKERS)), [])


# --- 2. Ritual Butchery ---------------------------------------------------
# A/B: game/fight.py's chain entry removed -> 4 of these fail.
print("\n2. Ritual Butchery ([SUSTAINED HITS 1] while leading)")


def led_carnivores(shaper_sheet):
    """A real attached unit (19.01): attach() MERGES the Shaper's model into
    the Carnivores' squad and throws the leader squad away."""
    body = shaper(KROOT_CARNIVORES, owner="Player 1")
    lead = shaper(shaper_sheet, owner="Player 1")
    attach(lead, body)
    return body


_led = led_carnivores(KROOT_FLESH_SHAPER)
_lone = shaper(KROOT_CARNIVORES, owner="Player 1")
_melee = next(w for w in _lone.models[0].weapons if w.weapon_type == "melee")

ck.eq("led: melee weapon gains [SUSTAINED HITS 1]",
      ritual_butchery.adjusted_weapon(_melee, _led).sustained_hits, 1)
ck.eq("unled: melee weapon unchanged",
      ritual_butchery.adjusted_weapon(_melee, _lone).sustained_hits, 0)
ck.true("the shared weapon instance is never mutated (a copy is returned)",
        _melee.sustained_hits == 0
        and ritual_butchery.adjusted_weapon(_melee, _led) is not _melee)

# Never downgrades: "have the [SUSTAINED HITS 1] ability" grants it, it does
# not set the value. Nothing in the Kroot loadouts prints a higher X, which is
# exactly why this is asserted rather than left to chance.
_better = copy.copy(_melee)
_better.sustained_hits = 2
ck.eq("a weapon already printing [SUSTAINED HITS 2] keeps its 2",
      ritual_butchery.adjusted_weapon(_better, _led).sustained_hits, 2)

ck.true("a dead Shaper stops conferring it",
        (lambda: [setattr(m, "current_wounds", 0) for m in _led.models
                  if getattr(m.profile, "ritual_butchery", False)]
         and ritual_butchery.adjusted_weapon(_melee, _led).sustained_hits == 0)())

# End to end through the REAL FightController: the keyword has to reach the
# weapon the attack actually swings, not just the predicate.
_scene = tk.fight_scene(KROOT_CARNIVORES, KROOT_CARNIVORES, attacker_owner="Player 2")
_lead2 = shaper(KROOT_FLESH_SHAPER, owner="Player 2")
attach(_lead2, _scene["attacker"])
# The chain reads self.fighting_squad, which begin_fight_step() leaves unset
# until a unit is actually selected - so it is set here rather than driving a
# whole activation, which would test the activation and not the chain.
_scene["fight"].fighting_squad = _scene["attacker"]
_pairs = [(m, next(w for w in m.weapons if w.weapon_type == "melee"))
          for m in _scene["attacker"].models if not m.is_dead()]
_adjusted = _scene["fight"]._adjusted_weapon(_pairs)
ck.eq("FightController._adjusted_weapon() applies it", _adjusted.sustained_hits, 1)
_scene["fight"].fighting_squad = _scene["target"]
_target_pairs = [(m, next(w for w in m.weapons if w.weapon_type == "melee"))
                 for m in _scene["target"].models if not m.is_dead()]
ck.eq("...and not to the unled squad on the other side",
      _scene["fight"]._adjusted_weapon(_target_pairs).sustained_hits, 0)


# --- 3. Rites of Feasting -------------------------------------------------
# A/B: the fold removed from game/feel_no_pain.py -> 4 of these fail.
print("\n3. Rites of Feasting (Feel No Pain 6+, then 5+)")

_feast = led_carnivores(KROOT_FLESH_SHAPER)
_body_model = next(m for m in _feast.models
                   if not getattr(m.profile, "rites_of_feasting", False))
ck.eq("led unit has Feel No Pain 6+", current_feel_no_pain(_body_model), "6+")
ck.eq("unled unit has none",
      current_feel_no_pain(shaper(KROOT_CARNIVORES).models[0]), "-")

_tt = TurnTracker(first_player="Player 1")
while _tt.phase != "Fight":
    _tt.advance_phase()
ck.true("a Fight-phase kill is recorded",
        rites_of_feasting.record_fight_phase_kill(_feast, _tt))
ck.eq("and upgrades the unit to Feel No Pain 5+",
      current_feel_no_pain(_body_model), "5+")

# "in the Fight phase" - a kill in any other phase does not count, which the
# module checks itself rather than trusting the call site.
_shoot_feast = led_carnivores(KROOT_FLESH_SHAPER)
_shoot_tt = TurnTracker(first_player="Player 1")
while _shoot_tt.phase != "Shooting":
    _shoot_tt.advance_phase()
ck.true("a Shooting-phase kill does NOT count",
        not rites_of_feasting.record_fight_phase_kill(_shoot_feast, _shoot_tt))
ck.eq("so that unit is still on 6+",
      current_feel_no_pain(
          next(m for m in _shoot_feast.models
               if not getattr(m.profile, "rites_of_feasting", False))), "6+")

# "until the end of the battle" - no phase or turn boundary clears it.
for _ in range(12):
    _tt.advance_phase()
ck.eq("the 5+ survives every phase and turn boundary",
      current_feel_no_pain(_body_model), "5+")

# The flag is on the UNIT, so it outlives the Shaper - but it confers nothing
# on its own, because the leader check comes first.
for _m in _feast.models:
    if getattr(_m.profile, "rites_of_feasting", False):
        _m.current_wounds = 0
ck.eq("with the Shaper dead the unit has no Feel No Pain at all",
      current_feel_no_pain(_body_model), "-")
ck.true("but the feast is still on record",
        rites_of_feasting.has_feasted(_feast))

# Never worse than printed: this is the fold's whole job, and 6+ is the worst
# threshold any source grants, so it is the one that would expose a bad fold.
_printed5 = shaper(KROOT_CARNIVORES, owner="Player 1")
_printed5.models[0].profile = type(
    "Printed5", (type(_printed5.models[0].profile),), {"feel_no_pain": "5+"})
_lead5 = shaper(KROOT_FLESH_SHAPER, owner="Player 1")
attach(_lead5, _printed5)
ck.eq("a model printing 5+ is not dragged down to the granted 6+",
      current_feel_no_pain(_printed5.models[0]), "5+")


# --- 4. War Leader --------------------------------------------------------
# A/B: the discount unregistered in main.py -> the source guard fails;
# available_discount() forced to 0 -> 4 of these fail.
print("\n4. War Leader (1 CP off a Stratagem targeting his unit)")

_wl_tt = TurnTracker(first_player="Player 1")
_cp = CommandPointManager()
_cp.gain_core_cp(5)
_strat_ctrl = StratagemController(command_points=_cp)
_discount = WarLeaderDiscount(turn_tracker=_wl_tt)
_strat_ctrl.cost_discounts.append(_discount)
_two_cp = Stratagem("Test Stratagem", 2, effect=lambda *a, **k: None)

_wl_unit = led_carnivores(KROOT_WAR_SHAPER)
_plain = shaper(KROOT_CARNIVORES, owner="Player 1")

ck.eq("a Stratagem targeting his unit costs 1 CP less",
      _strat_ctrl._cost_for("Player 1", _two_cp, [_wl_unit], 0), 1)
ck.eq("targeting any other unit costs full price",
      _strat_ctrl._cost_for("Player 1", _two_cp, [_plain], 0), 2)
ck.eq("asking the price does not spend the entitlement",
      _strat_ctrl._cost_for("Player 1", _two_cp, [_wl_unit], 0), 1)

_discount.consume("Player 1", _two_cp, [_wl_unit])
ck.eq("once used, the same battle round pays full price",
      _strat_ctrl._cost_for("Player 1", _two_cp, [_wl_unit], 0), 2)
_wl_tt.battle_round += 1
ck.eq("a new battle round restores it",
      _strat_ctrl._cost_for("Player 1", _two_cp, [_wl_unit], 0), 1)

# "one unit from your army with this ability" - per ARMY, so two War Shapers
# share one entitlement rather than getting one each.
_second = led_carnivores(KROOT_WAR_SHAPER)
_discount.consume("Player 1", _two_cp, [_wl_unit])
ck.eq("a second War Shaper does not get his own use",
      _strat_ctrl._cost_for("Player 1", _two_cp, [_second], 0), 2)

for _m in _wl_unit.models:
    if getattr(_m.profile, "war_leader", False):
        _m.current_wounds = 0
_wl_tt.battle_round += 1
ck.eq("a dead War Shaper confers no discount",
      _strat_ctrl._cost_for("Player 1", _two_cp, [_wl_unit], 0), 2)


# --- 5. Root of Honour ----------------------------------------------------
# A/B: the offer call removed from main.py -> the source guard fails;
# the battle_shocked filter removed -> 2 of these fail.
print("\n5. Root of Honour (end Battle-shock on a KROOT unit within 12\")")

_roh_shaper = led_carnivores(KROOT_WAR_SHAPER)
_victim = shaper(KROOT_CARNIVORES, owner="Player 1")
tk.line_up(_roh_shaper, x=20.0, y=20.0)
tk.line_up(_victim, x=24.0, y=20.0)
_all = [_roh_shaper, _victim]
_dec = DecisionManager()
_roh = RootOfHonourController(decision_manager=_dec, all_squads=lambda: _all)

ck.true("nothing to do while no unit is Battle-shocked", not _roh.can_use(_roh_shaper))
_victim.battle_shocked = True
ck.true("a shocked KROOT unit in range makes it usable", _roh.can_use(_roh_shaper))

ck.true("it asks rather than firing on its own", _roh.offer(_roh_shaper))
ck.true("Decline is an option", "Decline" in tk.options_of(_dec))
ck.true("the shocked unit is offered by name",
        any(_victim.name in label for label in tk.options_of(_dec)))
tk.pick_option(_dec, _victim.name)
ck.true("the unit is no longer Battle-shocked", not _victim.battle_shocked)

_victim.battle_shocked = True
ck.true("once per battle: it cannot be used again", not _roh.can_use(_roh_shaper))

# Out of range, and a non-KROOT unit, are two separate reasons to be ineligible.
_roh2 = RootOfHonourController(decision_manager=DecisionManager(), all_squads=lambda: _all)
tk.line_up(_victim, x=60.0, y=20.0)
ck.true("a shocked unit beyond 12\" is not eligible", not _roh2.can_use(_roh_shaper))
tk.line_up(_victim, x=24.0, y=20.0)
ck.true("back in range, eligible again", _roh2.can_use(_roh_shaper))

from game.factions.tau_empire import STRIKE_TEAM  # noqa: E402
_not_kroot = tk.build(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
tk.line_up(_not_kroot, x=24.0, y=22.0)
_not_kroot.battle_shocked = True
_victim.battle_shocked = False
_roh3 = RootOfHonourController(decision_manager=DecisionManager(),
                               all_squads=lambda: [_roh_shaper, _not_kroot])
ck.true("a shocked NON-Kroot unit is not eligible", not _roh3.can_use(_roh_shaper))

# An enemy unit is not "friendly", however close and however shocked.
_enemy = shaper(KROOT_CARNIVORES, owner="Player 2")
tk.line_up(_enemy, x=24.0, y=20.0)
_enemy.battle_shocked = True
_roh4 = RootOfHonourController(decision_manager=DecisionManager(),
                               all_squads=lambda: [_roh_shaper, _enemy])
ck.true("an enemy unit is not eligible", not _roh4.can_use(_roh_shaper))

# The AI answers it deterministically - no DecisionManager, no API call.
_ai_shaper = led_carnivores(KROOT_WAR_SHAPER)
_ai_shaper.owner = "Player 2"
for _m in _ai_shaper.models:
    _m.owner = "Player 2"
_ai_victim = shaper(KROOT_CARNIVORES, owner="Player 2")
tk.line_up(_ai_shaper, x=20.0, y=20.0)
tk.line_up(_ai_victim, x=24.0, y=20.0)
_ai_victim.battle_shocked = True
_ai_dec = DecisionManager()
_ai_roh = RootOfHonourController(decision_manager=_ai_dec, auto_players=("Player 2",),
                                 all_squads=lambda: [_ai_shaper, _ai_victim])
ck.true("the AI resolves it without a prompt", _ai_roh.offer(_ai_shaper))
ck.true("...and asked nothing", not _ai_dec.is_pending)
ck.true("...and it worked", not _ai_victim.battle_shocked)

# It writes the SAME flag the Battle-shock test itself writes - not a private
# second one that the rest of the engine would never read.
_shock_tt = TurnTracker(first_player="Player 1")
_shock_ctrl = BattleShockController(turn_tracker=_shock_tt)
_shock_src = open("game/battle_shock.py", encoding="utf-8").read()
_roh_src = open("game/root_of_honour.py", encoding="utf-8").read()
ck.true("Root of Honour clears the same Squad.battle_shocked flag "
        "BattleShockController sets",
        "battle_shocked = False" in _shock_src
        and "battle_shocked = False" in _roh_src)


# --- 6. Deliberately not wired, and the source guards ---------------------
print("\n6. Deliberately not wired, and the source guards")

_trail_text = " ".join(KROOT_TRAIL_SHAPER.abilities_text)
ck.true("Trail Finding is recorded as not engine-wired",
        "Trail Finding" in _trail_text and "NOT ENGINE-WIRED" in _trail_text)
ck.true("Kroot Ambush is recorded as not engine-wired",
        "Kroot Ambush" in _trail_text and _trail_text.count("NOT ENGINE-WIRED") == 2)
ck.true("no profile flag pretends either is implemented",
        not hasattr(KROOT_TRAIL_SHAPER.model_lines[0].profile_cls, "trail_finding")
        and not hasattr(KROOT_TRAIL_SHAPER.model_lines[0].profile_cls, "kroot_ambush"))

# ART ARRIVED. This block pinned the ABSENCE until it did - which is what made
# adding it a visible change rather than a silent one. Asserted at the MODEL,
# never at the mapping table: sprites.sprite_for() actually loads the file, so
# a key pointing at a filename that is not on disk fails here, where a look at
# the map would not see it.
#
# User instruction: "fuer alle Kroot characters Kroot Flesh Shaper.png" - so
# all three Shapers share one image.
from game import sprites  # noqa: E402
for name, sheet in SHEETS.items():
    squad = shaper(sheet)
    ck.true(f"{name}: has art", sprites.sprite_for(squad.models[0]) is not None)
    ck.eq(f"{name}: uses the Flesh Shaper image",
          sprites._squad_key(squad.models[0]), "Kroot Flesh Shaper")
# ...and specifically that it is not accidentally borrowing Kroot Carnivores'.
ck.true("Kroot Carnivores' key is not a substring of any Shaper's squad name",
        all("Kroot Carnivores" not in f"1 {n} 1" for n in SHEETS))

_main = open("main.py", encoding="utf-8").read()
ck.true("War Leader is registered as a cost discount in main.py",
        "cost_discounts.append(\n        WarLeaderDiscount(" in _main
        or "WarLeaderDiscount(turn_tracker=turn_tracker" in _main)
ck.true("Root of Honour is constructed in main.py",
        "root_of_honour_controller = RootOfHonourController(" in _main)
ck.true("...and actually offered at every phase boundary",
        "root_of_honour_controller.offer_at_start_of_phase(" in _main)
ck.true("Rites of Feasting is fed from the death sweep",
        "rites_of_feasting.record_fight_phase_kill(" in _main)
_fight_src = open("game/fight.py", encoding="utf-8").read()
ck.true("Ritual Butchery is in FightController's adjuster chain",
        "ritual_butchery.adjusted_weapon(weapon, self.fighting_squad)" in _fight_src)
_shooting_src = open("game/shooting.py", encoding="utf-8").read()
ck.true("...and NOT in the shooting chain (it is melee-only)",
        "ritual_butchery" not in _shooting_src)
_fnp_src = open("game/feel_no_pain.py", encoding="utf-8").read()
ck.true("Rites of Feasting is folded into current_feel_no_pain()",
        "rites_of_feasting_feel_no_pain(model)" in _fnp_src)

ck.finish()
