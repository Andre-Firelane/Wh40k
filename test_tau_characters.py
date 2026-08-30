"""The six remaining T'au character datasheets (Etappe 1b).

  Ethereal · Darkstrider · Firesight Team · Kroot Lone-Spear ·
  Commander in Enforcer Battlesuit · Commander Shadowsun

One suite because they are one batch of work with one set of shared risks -
every one of them is a single-model CHARACTER, four of them grant something
"while leading", and their abilities reuse five existing engine chains. What
is worth pinning is that each landed in the RIGHT chain, which is easiest to
state side by side.

Real objects throughout: the real datasheets, the real ShootingController and
FightController, the real save-threshold function, the real attach(). A/B
probes accompany every ability claim and are listed against the sections they
protect; each was run and confirmed to break this suite.

  1. Stat lines, bases, keywords, points, loadouts, wargear
  2. Failure Is Not an Option + Coordinated Leadership   (Ethereal)
  3. Structural Analyser                                 (Darkstrider)
  4. Precise Targeting                                   (Firesight Team)
  5. Advanced Scouting + Fire and Fade                   (Kroot Lone-Spear)
  6. Enforcer Commander + the support systems            (Enforcer)
  7. Agile Combatant + Hero of the Empire + drone        (Shadowsun)
  8. What is deliberately NOT wired, and the source guards
"""

import testkit as tk
from game import advanced_scouting as advanced_scouting_module
from game import fire_and_fade as fire_and_fade_module
from game import hero_of_the_empire as hero_module
from game import precise_targeting as precise_targeting_module
from game import reroll_scope, structural_analyser
from game.advanced_scouting import AdvancedScoutingController
from game.attached_units import attach, can_attach
from game.command_points import CommandPointManager
from game.coordinated_leadership import CoordinatedLeadershipController
from game.damage_resolution import save_thresholds
from game.decision import DecisionManager
from game.enforcer_commander import adjusted_ap
from game.factions.tau_empire import (
    BREACHER_TEAM, COMMANDER_IN_ENFORCER_BATTLESUIT, COMMANDER_SHADOWSUN, DARKSTRIDER,
    ENFORCER_BURST_TO_FUSION, ETHEREAL, FIRESIGHT_TEAM, KROOT_CARNIVORES, KROOT_LONE_SPEAR,
    LONE_SPEAR_LONG_GUN_TO_JAVELINS, PATHFINDER_TEAM, STRIKE_TEAM,
)
from game.feel_no_pain import current_feel_no_pain
from game.shooting import available_shooting_types
from game.squad import (
    squad_has_advanced_guardian_drone, squad_has_agile_combatant,
)
from game.turn import TurnTracker

ck = tk.Checks("T'au characters")

SHEETS = {
    "Ethereal": ETHEREAL,
    "Darkstrider": DARKSTRIDER,
    "Firesight Team": FIRESIGHT_TEAM,
    "Kroot Lone-Spear": KROOT_LONE_SPEAR,
    "Commander in Enforcer Battlesuit": COMMANDER_IN_ENFORCER_BATTLESUIT,
    "Commander Shadowsun": COMMANDER_SHADOWSUN,
}
MM = 25.4


def one(sheet, owner="Player 1", choices=None, gear=None):
    """Named the way main.py names squads - sprites._squad_key() matches the
    datasheet name as a SUBSTRING of the squad name."""
    return tk.build(sheet, owner, name=f"1 {sheet.name} 1", choices=choices, gear=gear)


def stats(sheet):
    p = one(sheet).models[0].profile
    return (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc)


# --- 1. Stat lines, bases, keywords, points, loadouts ---------------------
print("\n1. Stat lines, bases, keywords, points, loadouts")

for name, sheet in SHEETS.items():
    ck.eq(f"{name}: one model", len(one(sheet).models), 1)
    ck.true(f"{name}: CHARACTER", one(sheet).models[0].profile.character)

ck.eq("Ethereal stat line", stats(ETHEREAL), (6, 3, "5+", 3, "6+", 1))
ck.eq("Darkstrider stat line", stats(DARKSTRIDER), (7, 3, "4+", 3, "7+", 1))
ck.eq("Firesight Team stat line", stats(FIRESIGHT_TEAM), (6, 3, "4+", 4, "7+", 3))
ck.eq("Kroot Lone-Spear stat line", stats(KROOT_LONE_SPEAR), (12, 5, "5+", 6, "7+", 2))
ck.eq("Enforcer stat line", stats(COMMANDER_IN_ENFORCER_BATTLESUIT), (8, 5, "2+", 6, "7+", 2))
ck.eq("Shadowsun stat line", stats(COMMANDER_SHADOWSUN), (10, 4, "3+", 6, "6+", 1))

# Only two of the six print one, and both print 5+.
ck.eq("printed invulnerable saves",
      {n: one(s).models[0].profile.invulnerable_save for n, s in SHEETS.items()},
      {"Ethereal": "5+", "Darkstrider": "-", "Firesight Team": "-",
       "Kroot Lone-Spear": "-", "Commander in Enforcer Battlesuit": "-",
       "Commander Shadowsun": "5+"})

# Bases: arithmetic, not assumptions.
for name, sheet, mm in [("Ethereal", ETHEREAL, 40), ("Darkstrider", DARKSTRIDER, 32),
                        ("Firesight Team", FIRESIGHT_TEAM, 40),
                        ("Enforcer", COMMANDER_IN_ENFORCER_BATTLESUIT, 60),
                        ("Shadowsun", COMMANDER_SHADOWSUN, 50)]:
    ck.true(f"{name}: {mm}mm base",
            abs(one(sheet).models[0].profile.base_radius_in - mm / 2 / MM) < 0.002)
# The oval, converted the same way the Ghostkeel and Riptide already are.
ck.true("Kroot Lone-Spear: equal-area circle of the 90 x 52mm oval",
        abs(one(KROOT_LONE_SPEAR).models[0].profile.base_radius_in
            - (45 * 26) ** 0.5 / MM) < 0.002)

ck.eq("points",
      {n: one(s).points for n, s in SHEETS.items()},
      {"Ethereal": 50, "Darkstrider": 60, "Firesight Team": 55,
       "Kroot Lone-Spear": 80, "Commander in Enforcer Battlesuit": 80,
       "Commander Shadowsun": 100})

# Shadowsun is INFANTRY, not VEHICLE - the only Commander here that is, and
# what lets her have Infiltrators and Stealth at all.
_ss = one(COMMANDER_SHADOWSUN).models[0].profile
ck.true("Shadowsun is INFANTRY + FLY, not VEHICLE",
        _ss.infantry and _ss.fly and not _ss.vehicle)
_enf = one(COMMANDER_IN_ENFORCER_BATTLESUIT).models[0].profile
ck.true("the Enforcer is VEHICLE + WALKER + FLY", _enf.vehicle and _enf.walker and _enf.fly)
ck.true("Kroot Lone-Spear is MOUNTED and KROOT, not INFANTRY",
        one(KROOT_LONE_SPEAR).models[0].profile.mounted
        and one(KROOT_LONE_SPEAR).models[0].profile.kroot
        and not one(KROOT_LONE_SPEAR).models[0].profile.infantry)

# Loadouts, straight off the printed equipment lines.
ck.eq("Ethereal loadout", [w.name for w in one(ETHEREAL).models[0].weapons], ["Honour Stave"])
ck.eq("Darkstrider loadout",
      [w.name for w in one(DARKSTRIDER).models[0].weapons], ["Shade", "Close Combat Weapon"])
ck.eq("Shadowsun carries TWO high-energy fusion blasters",
      [w.name for w in one(COMMANDER_SHADOWSUN).models[0].weapons].count(
          "High-energy Fusion Blaster"), 2)

# The Shade's BS2+ overrides the profile's 4+ - the first T'au model whose two
# weapon rows disagree about skill.
_shade = next(w for w in one(DARKSTRIDER).models[0].weapons if w.name == "Shade")
ck.eq("the Shade carries its own BS2+ override", _shade.ballistic_skill, "2+")
ck.eq("...while the profile stays on the melee row's 4+",
      one(DARKSTRIDER).models[0].profile.ballistic_skill, "4+")

# Kalamandra's bite is [EXTRA ATTACKS], so 04.01's one-melee-weapon lock does
# not apply to it - the mount bites in addition to whatever the rider swings.
_bite = next(w for w in one(KROOT_LONE_SPEAR).models[0].weapons
             if w.name == "Kalamandra's Bite")
ck.true("Kalamandra's bite is [EXTRA ATTACKS]", _bite.extra_attacks)

# One weapon given up for TWO, one ranged and one melee.
_javelins = one(KROOT_LONE_SPEAR,
                choices={"Kroot Lone-Spear": {LONE_SPEAR_LONG_GUN_TO_JAVELINS: 1}})
ck.eq("Lone-Spear swap: long gun out, both javelins in",
      sorted(w.name for w in _javelins.models[0].weapons),
      ["Blast Javelin", "Close Combat Weapon", "Hunting Javelin", "Kalamandra's Bite"])

_fusion = one(COMMANDER_IN_ENFORCER_BATTLESUIT,
              choices={"Commander in Enforcer Battlesuit": {ENFORCER_BURST_TO_FUSION: 1}})
ck.eq("Enforcer swap: burst cannon -> fusion blaster",
      sorted(w.name for w in _fusion.models[0].weapons),
      ["Battlesuit Fists", "Fusion Blaster"])
ck.eq("the burst-cannon menu offers all six weapon swaps",
      len(COMMANDER_IN_ENFORCER_BATTLESUIT.wargear_options), 6)
ck.eq("Shadowsun has no wargear options at all",
      len(COMMANDER_SHADOWSUN.wargear_options), 0)

# LEADER pairings, read off the points list by can_attach() (a list of REASONS
# it is NOT allowed - empty means allowed).
ck.eq("the Ethereal can lead a Strike Team",
      can_attach(one(ETHEREAL), one(STRIKE_TEAM)), [])
ck.eq("...and a Breacher Team", can_attach(one(ETHEREAL), one(BREACHER_TEAM)), [])
ck.eq("Darkstrider can lead a Pathfinder Team",
      can_attach(one(DARKSTRIDER), one(PATHFINDER_TEAM)), [])
ck.true("Darkstrider cannot lead a Strike Team (not on his printed line)",
        bool(can_attach(one(DARKSTRIDER), one(STRIKE_TEAM))))
# Three of the six lead nobody: two are LONE OPERATIVEs, one is a Marksman.
for name in ("Firesight Team", "Kroot Lone-Spear", "Commander Shadowsun"):
    ck.true(f"{name} has no Leader ability",
            not one(SHEETS[name]).models[0].profile.leader)
    ck.eq(f"{name} is a LONE OPERATIVE" if name != "Firesight Team"
          else "Firesight Team is a LONE OPERATIVE",
          one(SHEETS[name]).models[0].profile.lone_operative, 12.0)


# --- 2. Ethereal ----------------------------------------------------------
# A/B: the FNP fold removed -> 3 fail; the CP roll's threshold inverted -> 2.
print("\n2. Ethereal: Failure Is Not an Option, Coordinated Leadership")


def led(leader_sheet, body_sheet=STRIKE_TEAM, owner="Player 1"):
    body = one(body_sheet, owner=owner)
    attach(one(leader_sheet, owner=owner), body)
    return body


_eth_unit = led(ETHEREAL)
_body = next(m for m in _eth_unit.models
             if not getattr(m.profile, "failure_is_not_an_option", False))
ck.eq("a led unit has Feel No Pain 5+", current_feel_no_pain(_body), "5+")
ck.eq("an unled unit has none", current_feel_no_pain(one(STRIKE_TEAM).models[0]), "-")
for _m in _eth_unit.models:
    if getattr(_m.profile, "failure_is_not_an_option", False):
        _m.current_wounds = 0
ck.eq("a dead Ethereal stops conferring it", current_feel_no_pain(_body), "-")

_cp = CommandPointManager()
_cl_tt = TurnTracker(first_player="Player 1")
_cl = CoordinatedLeadershipController(command_points=_cp, turn_tracker=_cl_tt)
_eth = one(ETHEREAL)
ck.eq("it queues one roll per Ethereal",
      len(_cl.eligible_squads([_eth, one(STRIKE_TEAM)], "Player 1")), 1)
def roll_leadership(face, cp=None):
    """Drive one Coordinated Leadership roll end to end through a REAL
    DiceManager, so the D6 is genuinely thrown and acknowledged rather than
    the resolution being poked directly."""
    cp = cp if cp is not None else CommandPointManager()
    dice = tk.RecordingDice()
    ctrl = CoordinatedLeadershipController(
        dice_manager=dice, command_points=cp, turn_tracker=_cl_tt)
    tk.script(face)
    started = ctrl.begin_command_phase([one(ETHEREAL)], "Player 1")
    if started and dice.is_pending:
        dice.acknowledge()
        ctrl.on_dice_acknowledged()
    tk.script()
    return cp, dice, ctrl


# The printed threshold, measured at both sides of it.
_cp4, _dice4, _ = roll_leadership(4)
ck.eq("a 4 gains 1 CP", _cp4.cp["Player 1"], 1)
ck.eq("...and it really was a D6 labelled as itself",
      _dice4.last_roll[0], "Coordinated Leadership")
_cp3, _, _ = roll_leadership(3)
ck.eq("a 3 gains nothing", _cp3.cp["Player 1"], 0)
_cp6, _, _ = roll_leadership(6)
ck.eq("a 6 gains 1 CP", _cp6.cp["Player 1"], 1)

_cl3 = CoordinatedLeadershipController(command_points=CommandPointManager(),
                                       turn_tracker=_cl_tt)
ck.true("a unit without the ability queues nothing",
        not _cl3.begin_command_phase([one(STRIKE_TEAM)], "Player 1"))

# Hover Drone: two real characteristic changes, and its own menu group so it
# cannot eat one of the two drone slots.
_hover = one(ETHEREAL, gear={"Ethereal": ["Hover Drone"]})
ck.true("the Hover Drone grants FLY and M10\"",
        _hover.models[0].profile.fly and _hover.models[0].profile.movement_in == 10)
ck.true("a plain Ethereal has neither",
        not one(ETHEREAL).models[0].profile.fly
        and one(ETHEREAL).models[0].profile.movement_in == 6)
_both = one(ETHEREAL, gear={"Ethereal": ["Hover Drone", "Gun Drone", "Gun Drone"]})
ck.true("the hover drone does not eat a drone slot (both menus fill)",
        _both.models[0].profile.fly
        and [w.name for w in _both.models[0].weapons].count("Twin Pulse Carbine") == 2)


# --- 3. Darkstrider -------------------------------------------------------
# A/B: the _wound_modifiers entry removed -> 2 fail; the sign flipped -> 1.
print("\n3. Darkstrider: Structural Analyser")

_ds_unit = led(DARKSTRIDER, PATHFINDER_TEAM)
ck.true("it applies while he leads", structural_analyser.applies(_ds_unit))
ck.true("not to an unled unit", not structural_analyser.applies(one(PATHFINDER_TEAM)))
# "add 1 to the Wound roll" is a BONUS, and this file's convention is that a
# positive modifier WORSENS the threshold - so the amount must be negative.
ck.eq("the modifier is negative (a bonus, per game/modifiers.py's convention)",
      structural_analyser.STRUCTURAL_ANALYSER_WOUND_MODIFIER, -1)

_scene = tk.shooting_scene(PATHFINDER_TEAM, KROOT_CARNIVORES, attacker_owner="Player 2")
# _wound_modifiers() reads self.active_squad, which only a started activation
# sets - assigned here rather than driving a whole shooting sequence, which
# would be testing the sequence and not the chain.
_scene["shooting"].active_squad = _scene["attacker"]
_plain_mods = _scene["shooting"]._wound_modifiers(_scene["target"])
attach(one(DARKSTRIDER, owner="Player 2"), _scene["attacker"])
_led_mods = _scene["shooting"]._wound_modifiers(_scene["target"])
ck.eq("ShootingController._wound_modifiers() picks it up",
      len(_led_mods) - len(_plain_mods), 1)
ck.true("...with the right label",
        any(m.source == structural_analyser.STRUCTURAL_ANALYSER_LABEL for m in _led_mods))
for _m in _ds_unit.models:
    if getattr(_m.profile, "structural_analyser", False):
        _m.current_wounds = 0
ck.true("a dead Darkstrider stops conferring it", not structural_analyser.applies(_ds_unit))


# --- 4. Firesight Team ----------------------------------------------------
# A/B: the _hit_reroll_reason entry removed -> 2 fail.
print("\n4. Firesight Team: Precise Targeting")


class _FakeGreaterGood:
    def __init__(self, spotted=()):
        self._spotted = set(id(s) for s in spotted)

    def is_spotted(self, squad):
        return id(squad) in self._spotted


_fs = one(FIRESIGHT_TEAM)
_prey = one(KROOT_CARNIVORES, owner="Player 2")
ck.true("no Spotted mark, no re-roll",
        not precise_targeting_module.applies(_fs, _prey, _FakeGreaterGood()))
ck.true("a Spotted target grants it",
        precise_targeting_module.applies(_fs, _prey, _FakeGreaterGood([_prey])))
ck.true("another unit gets nothing from the same mark",
        not precise_targeting_module.applies(one(STRIKE_TEAM), _prey,
                                             _FakeGreaterGood([_prey])))
ck.true("no GreaterGoodController at all is simply no re-roll",
        not precise_targeting_module.applies(_fs, _prey, None))

_fs_scene = tk.shooting_scene(FIRESIGHT_TEAM, KROOT_CARNIVORES, attacker_owner="Player 2")
_fs_scene["shooting"].active_squad = _fs_scene["attacker"]
_fs_scene["shooting"].greater_good = _FakeGreaterGood([_fs_scene["target"]])
ck.eq("ShootingController._hit_reroll_reason() names it",
      _fs_scene["shooting"]._hit_reroll_reason(_fs_scene["target"]),
      precise_targeting_module.PRECISE_TARGETING_LABEL)

# Ordinary failures-or-whole shape: registering it in reroll_scope would offer
# a ones-only re-roll the printed text never grants.
ck.true("it is NOT a ones-or-whole source",
        not reroll_scope.is_ones_or_whole(precise_targeting_module.PRECISE_TARGETING_LABEL))


# --- 5. Kroot Lone-Spear --------------------------------------------------
# A/B: record_hit() made unconditional -> 2 fail; the "another" test dropped
# -> 1; the Engagement Range condition dropped -> 2.
print("\n5. Kroot Lone-Spear: Advanced Scouting, Fire and Fade")

_ls = one(KROOT_LONE_SPEAR)
_kroot = one(KROOT_CARNIVORES)
_victim = one(KROOT_CARNIVORES, owner="Player 2")
_as = AdvancedScoutingController()

ck.true("nothing is marked to begin with", not _as.is_marked(_victim))
ck.true("a unit WITHOUT the ability marks nothing",
        not _as.record_hit(_kroot, _victim))
ck.true("the Lone-Spear's hit marks the target", _as.record_hit(_ls, _victim))
ck.true("another KROOT unit may re-roll against it", _as.applies(_kroot, _victim))
# "another KROOT model" - he does not re-roll his own later attacks.
ck.true("but the Lone-Spear himself may not", not _as.applies(_ls, _victim))
ck.true("a non-KROOT unit gets nothing",
        not _as.applies(one(STRIKE_TEAM), _victim))
ck.true("an enemy unit gets nothing",
        not _as.applies(one(KROOT_CARNIVORES, owner="Player 2"), _victim))
ck.true("an unmarked unit grants nothing",
        not _as.applies(_kroot, one(KROOT_CARNIVORES, owner="Player 2")))
_as.reset_turn()
ck.true("the mark lasts only until the end of the turn", not _as.applies(_kroot, _victim))

# Fire and Fade: the printed Engagement Range condition is the half Tactical
# Acumen does not have.
_ff_scene = tk.shooting_scene(KROOT_LONE_SPEAR, KROOT_CARNIVORES,
                              attacker_owner="Player 2", gap=12.0)
ck.true("out of Engagement Range, it can be used",
        fire_and_fade_module.can_use(_ff_scene["attacker"], _ff_scene["state"].tokens))
tk.line_up(_ff_scene["target"], y=20.5)
ck.true("engaged, it cannot",
        not fire_and_fade_module.can_use(_ff_scene["attacker"], _ff_scene["state"].tokens))
ck.true("a unit without the ability never can",
        not fire_and_fade_module.can_use(one(STRIKE_TEAM), []))
ck.eq("the printed distance is a flat 6\"", fire_and_fade_module.FIRE_AND_FADE_MOVE_IN, 6.0)


# --- 6. Commander in Enforcer Battlesuit ----------------------------------
# A/B: the save_thresholds() entry removed -> 3 fail; the min(0, ...) clamp
# dropped -> 1.
print("\n6. Enforcer: Enforcer Commander, support systems")

from game.factions.tau_empire import CRISIS_STARSCYTHE  # noqa: E402
_crisis = one(CRISIS_STARSCYTHE, owner="Player 1")
attach(one(COMMANDER_IN_ENFORCER_BATTLESUIT, owner="Player 1"), _crisis)
_target_model = _crisis.models[0]
_ap2 = next(w for w in one(DARKSTRIDER).models[0].weapons if w.name == "Shade")


class _Ranged:
    weapon_type = "ranged"
    ap = -2


class _Melee:
    weapon_type = "melee"
    ap = -2


class _RangedAp0:
    weapon_type = "ranged"
    ap = 0


ck.eq("a ranged AP-2 attack becomes AP-1 against the led unit",
      adjusted_ap(-2, _target_model, _Ranged()), -1)
ck.eq("a MELEE AP-2 attack is untouched (the text says ranged)",
      adjusted_ap(-2, _target_model, _Melee()), -2)
ck.eq("AP0 cannot become a bonus to the target's save",
      adjusted_ap(0, _target_model, _RangedAp0()), 0)
ck.eq("an unled unit is untouched",
      adjusted_ap(-2, one(CRISIS_STARSCYTHE).models[0], _Ranged()), -2)
# End to end through the function the save roll and the dice panel BOTH read.
_sv, _insv, _ap = save_thresholds(_target_model, _Ranged())
ck.eq("save_thresholds() applies it", _ap, -1)

# The three support systems, each wired to a field another datasheet already
# uses - so nothing new is enforced, only newly reachable.
_shield = one(COMMANDER_IN_ENFORCER_BATTLESUIT,
              gear={"Commander in Enforcer Battlesuit": ["Shield Generator"]})
ck.eq("Shield Generator grants a 4+ invulnerable save",
      _shield.models[0].profile.invulnerable_save, "4+")
_wss = one(COMMANDER_IN_ENFORCER_BATTLESUIT,
           gear={"Commander in Enforcer Battlesuit": ["Weapon Support System"]})
ck.true("Weapon Support System sets ignores_hit_modifiers",
        _wss.models[0].profile.ignores_hit_modifiers)
_bss = one(COMMANDER_IN_ENFORCER_BATTLESUIT,
           gear={"Commander in Enforcer Battlesuit": ["Battlesuit Support System"]})
ck.true("Battlesuit Support System sets its own flag",
        _bss.models[0].profile.battlesuit_support_system)
ck.true("a plain Enforcer has none of the three",
        one(COMMANDER_IN_ENFORCER_BATTLESUIT).models[0].profile.invulnerable_save == "-"
        and not one(COMMANDER_IN_ENFORCER_BATTLESUIT).models[0].profile.ignores_hit_modifiers)
# Second menu adds a weapon, and the drone menu is independent of it.
_extra = one(COMMANDER_IN_ENFORCER_BATTLESUIT,
             gear={"Commander in Enforcer Battlesuit": ["Fusion Blaster", "Fusion Blaster",
                                                       "Gun Drone", "Gun Drone"]})
ck.eq("the support menu can add duplicate guns",
      [w.name for w in _extra.models[0].weapons].count("Fusion Blaster"), 2)
ck.eq("...without eating the drone slots",
      [w.name for w in _extra.models[0].weapons].count("Twin Pulse Carbine"), 2)


# --- 7. Commander Shadowsun -----------------------------------------------
# A/B: the Fall Back gate entry removed -> 2 fail; the aura's automatic-1s
# entry removed -> 2; the drone's wound entry removed -> 2.
print("\n7. Shadowsun: Agile Combatant, Hero of the Empire, Advanced Guardian Drone")

_ss_squad = one(COMMANDER_SHADOWSUN)
ck.true("Agile Combatant is recognised", squad_has_agile_combatant(_ss_squad))
ck.true("a Strike Team is not", not squad_has_agile_combatant(one(STRIKE_TEAM)))
_ss_squad.fell_back_this_turn = True
ck.true("she can still shoot after Falling Back",
        bool(available_shooting_types(_ss_squad, [], None)))
_fell = one(STRIKE_TEAM)
_fell.fell_back_this_turn = True
ck.eq("a unit without any such ability cannot",
      available_shooting_types(_fell, [], None), [])

# The aura: a property of where SHE stands, not of the attacking unit.
_aura_target = one(STRIKE_TEAM)
tk.line_up(_aura_target, x=20.0, y=20.0)
tk.line_up(_ss_squad, x=22.0, y=20.0)
_tokens = list(_aura_target.models) + list(_ss_squad.models)
ck.true("a friendly T'AU EMPIRE unit within 6\" is in the aura",
        hero_module.applies(_aura_target, _tokens))
tk.line_up(_ss_squad, x=60.0, y=20.0)
ck.true("beyond 6\" it is not", not hero_module.applies(_aura_target, _tokens))
tk.line_up(_ss_squad, x=22.0, y=20.0)
# Kroot are deliberately NOT T'AU EMPIRE on their own datasheets' authority.
_kroot_near = one(KROOT_CARNIVORES)
tk.line_up(_kroot_near, x=20.0, y=20.0)
ck.true("a KROOT unit gets nothing from it",
        not hero_module.applies(_kroot_near, list(_kroot_near.models) + list(_ss_squad.models)))
# An enemy unit standing next to her gets nothing either.
_enemy = one(STRIKE_TEAM, owner="Player 2")
tk.line_up(_enemy, x=20.0, y=20.0)
ck.true("an enemy unit gets nothing",
        not hero_module.applies(_enemy, list(_enemy.models) + list(_ss_squad.models)))
# She is T'AU EMPIRE herself, so she benefits from her own aura.
ck.true("she is inside her own aura",
        hero_module.applies(_ss_squad, list(_ss_squad.models)))

ck.true("the Advanced Guardian Drone is recognised",
        squad_has_advanced_guardian_drone(_ss_squad))
ck.true("a Strike Team has no such drone",
        not squad_has_advanced_guardian_drone(one(STRIKE_TEAM)))
_ss_scene = tk.shooting_scene(STRIKE_TEAM, COMMANDER_SHADOWSUN, attacker_owner="Player 2")
_ss_scene["shooting"].active_squad = _ss_scene["attacker"]
ck.true("it reaches _wound_modifiers() as a malus",
        any(m.source == "Advanced Guardian Drone"
            for m in _ss_scene["shooting"]._wound_modifiers(_ss_scene["target"])))
_plain_scene = tk.shooting_scene(STRIKE_TEAM, STRIKE_TEAM, attacker_owner="Player 2")
_plain_scene["shooting"].active_squad = _plain_scene["attacker"]
ck.true("...and not against anyone else",
        not any(m.source == "Advanced Guardian Drone"
                for m in _plain_scene["shooting"]._wound_modifiers(_plain_scene["target"])))


# --- 8. Deliberately not wired, and the source guards ---------------------
print("\n8. Deliberately not wired, and the source guards")

_ds_text = " ".join(DARKSTRIDER.abilities_text)
ck.true("Jammer Array is recorded as not engine-wired",
        "Jammer Array" in _ds_text and "NOT ENGINE-WIRED" in _ds_text)
_ss_text = " ".join(COMMANDER_SHADOWSUN.abilities_text)
ck.true("the Command-link Drone is recorded as not engine-wired",
        "Command-link Drone" in _ss_text and "NOT ENGINE-WIRED" in _ss_text)
ck.true("Supreme Commander is recorded as a no-op",
        "Supreme Commander" in _ss_text and "NO-OP" in _ss_text)
_enf_text = " ".join(COMMANDER_IN_ENFORCER_BATTLESUIT.abilities_text)
ck.true("the Battlesuit Support System's second clause is recorded as unenforced",
        "NOT ENFORCED" in _enf_text)
ck.true("no profile flag pretends Jammer Array is implemented",
        not hasattr(DARKSTRIDER.model_lines[0].profile_cls, "jammer_array"))
ck.true("no profile flag pretends the Command-link Drone is implemented",
        not hasattr(COMMANDER_SHADOWSUN.model_lines[0].profile_cls, "command_link_drone"))

# ART ARRIVED - this block pinned the ABSENCE until it did. Asserted at the
# MODEL, never at the mapping table: sprites.sprite_for() loads the file, so a
# key naming a file that is not on disk fails here.
from game import sprites  # noqa: E402
for name, sheet in SHEETS.items():
    ck.true(f"{name}: has art", sprites.sprite_for(one(sheet).models[0]) is not None)
# Three of the six files are spelled differently from the datasheet, and the
# FOLDER wins - the same decision "Ghostkheel", "Skyray" and "Vespid" record.
# Written out per file so a later rename is a visible change.
ck.eq("Darkstrider takes the folder's two-word spelling",
      sprites._squad_key(one(DARKSTRIDER).models[0]), "Dark Strider")
ck.eq("Firesight Team takes the folder's \"Tau \" prefix",
      sprites._squad_key(one(FIRESIGHT_TEAM).models[0]), "Tau Firesight Team")
# The Kroot Lone-Spear is a CHARACTER too, but unlike the three Shapers it has
# art of its own, so it keeps it rather than sharing the Flesh Shaper's.
ck.eq("the Lone-Spear keeps his own art, not the Shapers' shared one",
      sprites._squad_key(one(KROOT_LONE_SPEAR).models[0]), "Kroot Lone-Spear")

_main = open("main.py", encoding="utf-8").read()
ck.true("Coordinated Leadership is constructed in main.py",
        "coordinated_leadership_controller = CoordinatedLeadershipController(" in _main)
ck.true("...queued at the end of the Command phase",
        "coordinated_leadership_controller.begin_command_phase(" in _main)
ck.true("...and its roll is acknowledged",
        "coordinated_leadership_controller.on_dice_acknowledged()" in _main)
ck.true("Fire and Fade is offered after shooting",
        "on_squad_finished_shooting.append(fire_and_fade_controller.offer_after_shooting)" in _main)
ck.true("the Advanced Scouting ledger reaches ShootingController",
        "advanced_scouting=advanced_scouting_controller" in _main)
ck.true("...and is cleared at end of turn",
        "advanced_scouting_controller.reset_turn()" in _main)
ck.true("Fire and Fade's Confirm is routed to its own controller",
        "fire_and_fade_controller=fire_and_fade_controller," in _main)

_shooting_src = open("game/shooting.py", encoding="utf-8").read()
ck.true("Structural Analyser is in the shooting wound chain",
        "structural_analyser_module.applies(self.active_squad)" in _shooting_src)
_fight_src = open("game/fight.py", encoding="utf-8").read()
ck.true("...and NOT in the melee one (the text says 'a ranged attack')",
        "structural_analyser" not in _fight_src)
ck.true("Advanced Scouting IS in both (its text says 'an attack')",
        "advanced_scouting" in _fight_src and "advanced_scouting" in _shooting_src)
# The regression caught this and this suite did not: FightController READ
# self.advanced_scouting before it had the attribute, which every melee hit
# roll in the game then crashed on. A read needs a constructor slot AND a
# caller that fills it - so both halves are pinned, and the controller is
# actually built rather than only grepped for.
ck.true("FightController takes the ledger as a constructor argument",
        "advanced_scouting=None," in _fight_src
        and "self.advanced_scouting = advanced_scouting" in _fight_src)
ck.true("...and main.py actually passes it",
        "advanced_scouting=advanced_scouting_controller," in _main)
_melee_scene = tk.fight_scene(KROOT_CARNIVORES, KROOT_CARNIVORES, attacker_owner="Player 2")
_melee_scene["fight"].fighting_squad = _melee_scene["attacker"]
ck.true("a FightController built without one does not explode on a hit roll",
        _melee_scene["fight"]._hit_reroll_reason(_melee_scene["target"]) is None)
_marked_scene = tk.fight_scene(KROOT_CARNIVORES, KROOT_CARNIVORES, attacker_owner="Player 2")
_marked_scene["fight"].fighting_squad = _marked_scene["attacker"]
_ledger = AdvancedScoutingController()
_ledger.record_hit(one(KROOT_LONE_SPEAR, owner="Player 2"), _marked_scene["target"])
_marked_scene["fight"].advanced_scouting = _ledger
ck.eq("a marked target grants the melee re-roll too",
      _marked_scene["fight"]._hit_reroll_reason(_marked_scene["target"]),
      advanced_scouting_module.ADVANCED_SCOUTING_LABEL)
ck.true("Precise Targeting is shooting-only (Spotted cannot survive into melee)",
        "precise_targeting" in _shooting_src and "precise_targeting" not in _fight_src)
ck.true("the mark is recorded from the HIT step, not target selection",
        "self.advanced_scouting.record_hit(self.active_squad, target_squad)" in _shooting_src)
# Hero of the Empire needed BOTH of these, and finding that out is the reason
# they exist: an A/B probe that deleted "or hero_aura" from the disjunction
# left this suite fully green, because everything above tests the predicate and
# nothing tested that the predicate reaches the hit step. Per CLAUDE.md's
# Fehlerklasse 24 a guard has to pin the CALL EXPRESSION, not just a name - so
# both the lookup and its use in the automatic-1s disjunction are pinned.
ck.true("Hero of the Empire's aura is looked up in the hit step",
        "hero_aura = hero_of_the_empire_module.applies(self.active_squad, self.all_tokens)"
        in _shooting_src)
ck.true("...and actually joins the automatic-1s sources",
        "or hero_aura" in _shooting_src)
ck.true("...and names itself when it is the reason",
        "ones_reason = hero_of_the_empire_module.HERO_OF_THE_EMPIRE_LABEL" in _shooting_src)
ck.true("it re-rolls the HIT roll only - not the wound one, unlike Forward "
        "Observers, which it otherwise resembles",
        _shooting_src.count("hero_of_the_empire_module.applies") == 1)

_panel = open("game/ui/action_panel.py", encoding="utf-8").read()
ck.true("the panel routes the fire_and_fade move mode",
        "fire_and_fade.FIRE_AND_FADE_MOVE_MODE" in _panel)
ck.true("the panel parameter is keyword-appended, never positional",
        "fire_and_fade_controller=None," in _panel)
_movement = open("game/movement.py", encoding="utf-8").read()
ck.true("fire_and_fade is excluded from the Movement-phase move bookkeeping",
        '"tactical_acumen", "fire_and_fade",' in _movement)

ck.finish()
