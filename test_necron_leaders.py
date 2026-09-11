"""Stage 7 of the Necron datasheet backfill: the four characters that LEAD.

Royal Warden, Overlord with translocation shroud, Imotekh the Stormlord and
Trazyn the Infinite. Eight printed abilities, and SIX of them are twins of
something already built - so most of what this stage can get wrong is not the
new code, it is the ONE printed clause each twin does not share.

WHAT EACH SECTION IS FOR

  1. statlines, against the corpus. Three of the four agree and the fourth does
     not, which is why there is deliberately NO shared base here - the opposite
     decision to the C'tan batch one file over, and asserted as such.
  2. weapons and the collision sweep. Two names are SHARED with classes that
     already exist (the inverse of stage 3's fork), four are new, and the Staff
     of the Destroyer's two rows are NOT a firing-mode pair.
  3. points, bases and the LEADER table - measured through the real
     can_attach(), including the Royal Warden's missing Lychguard.
  4. Adaptive Strategy at BOTH of rule 09.07's gates, measured against the
     Triarch Praetorians in the same two calls: their Relentless Combatants
     lifts only one of them, so a copy of it would pass half this section.
  5. Engrammatic Logic at its four conditions, driven through the real
     controller.
  6. Translocation Shroud. The Advance half, the through-models half measured
     through clamp_move() and gated on the MOVE - and the through-TERRAIN half,
     which is a MEASURED no-op and is pinned as one rather than claimed.
  7. Grand Strategist and Lord of the Storm, both through real ledgers and real
     dice.
  8. Ancient Collector through the real sticky-objective sweep, and Surrogate
     Hosts asserted MISSING.
  9. the three extractions, each with its OTHER carrier still answering exactly
     as before - the load-bearing half of an extraction.
 10. wiring, the AI negative space, sprites - including the one name in this
     backfill the shadowing boilerplate cannot be copied for - and dormancy.
"""

import ast
import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((100, 100))

import testkit as tk
from testkit import Checks, script

from game import (adaptive_strategy, ancient_collector, attached_units,
                  command_phase_cp, end_battle_shock, fieldcraft,
                  lord_of_the_storm, move_exceptions, sprites,
                  translocation_shroud)
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.dice import DiceManager
from game.dice_notation import describe
from game.diviner_of_futures import DivinerOfFuturesController
from game.engrammatic_logic import EngrammaticLogicController
from game.factions import aeldari as ael
from game.factions import necrons as nec
from game.factions import orks as ork
from game.factions import tau_empire as tau
from game.factions.necrons_points import NECRONS_POINTS
from game.game_state import GameState
from game.grand_strategist import GrandStrategistController
from game.movement import MovementController
from game.objectives import Objective
from game.root_of_honour import RootOfHonourController
from game.terrain import DENSE, EXPOSED, Obstacle, TerrainArea
from game.turn import PHASE_MOVEMENT, TurnTracker
from game.units import (ImotekhTheStormlordProfile,
                        OverlordWithTranslocationShroudProfile,
                        RoyalWardenProfile, TrazynTheInfiniteProfile,
                        UnitProfile)
from game.weapons import (EmpathicObliteratorProfile, GauntletOfFireProfile,
                          NecronCloseCombatWeaponA4S5Profile,
                          OverlordsBladeProfile, RelicGaussBlasterProfile,
                          StaffOfTheDestroyerMeleeProfile,
                          StaffOfTheDestroyerRangedProfile)

c = Checks("Necron LEADERS")

D = nec.NECRONS.datasheets
WARDEN = D["Royal Warden"]
SHROUD = D["Overlord with translocation shroud"]
IMOTEKH = D["Imotekh The Stormlord"]
TRAZYN = D["Trazyn The Infinite"]
IMMORTALS = D["Immortals"]
LYCHGUARD = D["Lychguard"]
WARRIORS = D["Necron Warriors"]
OVERLORD = D["Overlord"]
HEXMARK = D["Hexmark Destroyer"]
PRAETORIANS = D["Triarch Praetorians"]

NEW = [WARDEN, SHROUD, IMOTEKH, TRAZYN]

PROFILES = {
    "Royal Warden": RoyalWardenProfile,
    "Overlord with translocation shroud": OverlordWithTranslocationShroudProfile,
    "Imotekh The Stormlord": ImotekhTheStormlordProfile,
    "Trazyn The Infinite": TrazynTheInfiniteProfile,
}


def build(sheet, owner="Player 2", n=1, **kw):
    """Named the way main.py names squads - see the sprite trap in
    game/sprites.py's _key_for_name()."""
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


def place(squad, x, y, spacing=1.4):
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + i * spacing, y
    return squad


def corpus(name):
    return io.open(os.path.join("rules", "necrons", name + ".md"),
                   encoding="utf-8").read()


def between(text, first, second):
    """The slice between two anchors, or "" if either is gone.

    find() and not index(): a pin that CRASHES when its anchor moves takes the
    whole suite down instead of going red, and then says nothing about which
    assurance broke."""
    a = text.find(first)
    if a < 0:
        return ""
    b = text.find(second, a + len(first))
    return text[a:b] if b > a else ""


def living(squad):
    return sum(1 for m in squad.models if not m.is_dead())


# --- 1. statlines ------------------------------------------------------------
print("--- 1. statlines ---")

STATS = {
    # name: (M, T, Sv, W, Ld, OC, InSv, base)
    # "-" is this engine's own sentinel for "no invulnerable save", not None.
    "Royal Warden": (5, 5, "3+", 4, "6+", 1, "-", 0.630),
    "Overlord with translocation shroud": (5, 5, "2+", 6, "6+", 1, "4+", 0.787),
    "Imotekh The Stormlord": (5, 5, "2+", 6, "6+", 1, "4+", 0.787),
    "Trazyn The Infinite": (5, 5, "2+", 6, "6+", 1, "4+", 0.492),
}
for name, want in sorted(STATS.items()):
    p = PROFILES[name]
    c.eq("%s: statline" % name,
         (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc,
          p.invulnerable_save, round(p.base_radius_in, 3)), want)
    c.true("%s: INFANTRY CHARACTER, and a Leader (24.22)" % name,
           p.infantry and p.character and p.leader)
    c.true("%s: carries the army rule" % name, p.reanimation_protocols)

# Against the PRINTED page, not against the table above.
for sheet in NEW:
    text = corpus(sheet.name)
    p = PROFILES[sheet.name]
    row = "| 5\" | 5 | %s | %s | 6+ | 1 |" % (p.armor_save, p.wounds)
    c.true("%s prints %s" % (sheet.name, row.strip()), row in text)
    c.true("...and CORE: Leader (%s)" % sheet.name, "**Leader**" in text)
    if p.invulnerable_save != "-":
        c.true("...and an INSV column of %s" % p.invulnerable_save,
               "| 1 | %s |" % p.invulnerable_save in text)
    else:
        c.true("...and NO INSV column at all", "| INSV |" not in text)

# THREE AGREE AND ONE DOES NOT, which is why there is no shared base here. The
# C'tan batch got one; this batch would need the odd member to override three
# of the shared names, and four honest copies say more than that.
c.eq("only the Royal Warden lacks an invulnerable save",
     sorted(n for n, p in PROFILES.items() if p.invulnerable_save == "-"),
     ["Royal Warden"])
c.eq("...and only he is not NOBLE",
     sorted(n for n, p in PROFILES.items() if not p.noble), ["Royal Warden"])
c.eq("two of the four are EPIC HEROes",
     sorted(n for n, p in PROFILES.items() if p.epic_hero),
     ["Imotekh The Stormlord", "Trazyn The Infinite"])
c.true("...so all four derive straight from UnitProfile, sharing no base",
       all(p.__bases__ == (UnitProfile,) for p in PROFILES.values()))

# Every printed keyword these four carry, read off the corpus rather than the
# table that encodes it.
for sheet in NEW:
    kw = between(corpus(sheet.name), "KEYWORDS:", "FACTION KEYWORDS:")
    for word in ("INFANTRY", "CHARACTER"):
        c.true("%s prints %s" % (sheet.name, word), word in kw)
    c.eq("...and EPIC HERO iff the profile says so (%s)" % sheet.name,
         "EPIC HERO" in kw, PROFILES[sheet.name].epic_hero)
    c.eq("...and NOBLE iff the profile says so (%s)" % sheet.name,
         "NOBLE" in kw, PROFILES[sheet.name].noble)


# --- 2. weapons ---------------------------------------------------------------
print("--- 2. weapons ---")


def row(w):
    return (w.range_in, w.attacks, w.strength, w.ap, w.damage)


c.eq("Relic Gauss Blaster", row(RelicGaussBlasterProfile), (24, 2, 5, -1, 2))
c.true("...[LETHAL HITS] and [RAPID FIRE 2]",
       RelicGaussBlasterProfile.lethal_hits and RelicGaussBlasterProfile.rapid_fire == 2)
c.eq("Gauntlet of Fire", (GauntletOfFireProfile.range_in, GauntletOfFireProfile.strength,
                          GauntletOfFireProfile.ap, GauntletOfFireProfile.damage),
     (12, 5, -1, 1))
c.eq("...its Attacks are D6", describe(GauntletOfFireProfile.attacks_notation), "D6")
c.true("...BS \"N/A\" on the printed row is [TORRENT], plus [IGNORES COVER]",
       GauntletOfFireProfile.torrent and GauntletOfFireProfile.ignores_cover)
c.true("...and it carries no skill override to contradict its wielder",
       GauntletOfFireProfile.ballistic_skill is None)
c.eq("Empathic Obliterator", (EmpathicObliteratorProfile.range_in,
                              EmpathicObliteratorProfile.attacks,
                              EmpathicObliteratorProfile.strength,
                              EmpathicObliteratorProfile.ap), (2, 4, 7, 0))
c.eq("...its Damage is D3", describe(EmpathicObliteratorProfile.damage_notation), "D3")
c.eq("...and its [SUSTAINED HITS] is D3 too",
     describe(EmpathicObliteratorProfile.sustained_hits_notation), "D3")

# THE TWO SHARES. Stage 3 had to FORK "Close combat weapon" three ways; this is
# the inverse error, and cloning here would be it. Asserted as class IDENTITY,
# which a copy carrying the same numbers would fail.
c.true("the Royal Warden's Close Combat Weapon IS the Hexmark's class",
       any(type(w) is NecronCloseCombatWeaponA4S5Profile
           for w in build(WARDEN).models[0].weapons))
c.true("...and the Hexmark really carries that same class",
       any(type(w) is NecronCloseCombatWeaponA4S5Profile
           for w in build(HEXMARK).models[0].weapons))
c.eq("...while their WS comes off their own profiles, not off the shared weapon",
     (RoyalWardenProfile.weapon_skill, build(HEXMARK).models[0].profile.weapon_skill,
      NecronCloseCombatWeaponA4S5Profile.weapon_skill), ("3+", "3+", None))
c.true("the shroud Overlord's blade IS the Overlord's class",
       any(type(w) is OverlordsBladeProfile for w in build(SHROUD).models[0].weapons))
c.true("...the very same class the plain Overlord carries",
       any(type(w) is OverlordsBladeProfile for w in build(OVERLORD).models[0].weapons))

# THE STAFF OF THE DESTROYER: one name, two rows, and NOT a firing-mode pair.
# Pinned against each other rather than against literals - a copy would pass
# either read on its own.
c.eq("Staff of the Destroyer - ranged", row(StaffOfTheDestroyerRangedProfile), (18, 3, 6, -3, 2))
c.eq("Staff of the Destroyer - melee", row(StaffOfTheDestroyerMeleeProfile), (2, 4, 6, -3, 2))
c.eq("...they print the SAME name",
     (StaffOfTheDestroyerRangedProfile.name, StaffOfTheDestroyerMeleeProfile.name),
     ("Staff of the Destroyer", "Staff of the Destroyer"))
c.eq("...and differ in exactly Attacks and [DEVASTATING WOUNDS]",
     (StaffOfTheDestroyerMeleeProfile.attacks - StaffOfTheDestroyerRangedProfile.attacks,
      StaffOfTheDestroyerMeleeProfile.devastating_wounds,
      StaffOfTheDestroyerRangedProfile.devastating_wounds), (1, True, False))
c.true("NEITHER is the other's overcharge_profile - he carries both at once",
       StaffOfTheDestroyerRangedProfile.overcharge_profile is None
       and StaffOfTheDestroyerMeleeProfile.overcharge_profile is None)
c.eq("...so all three of his weapons are in the loadout",
     sorted(w.name for w in build(IMOTEKH).models[0].weapons),
     ["Gauntlet of Fire", "Staff of the Destroyer", "Staff of the Destroyer"])

# NO PER-WEAPON SKILL OVERRIDE in this batch: every row agrees with its wielder.
overrides = sorted(w.name for s in NEW for m in build(s).models for w in m.weapons
                   if w.ballistic_skill is not None or w.weapon_skill is not None)
c.eq("no weapon in this batch overrides a skill", overrides, [])


# --- 3. points, bases, attachment ---------------------------------------------
print("--- 3. points, bases, attachment ---")

for sheet, cost in [(WARDEN, 50), (SHROUD, 90), (IMOTEKH, 100), (TRAZYN, 65)]:
    c.eq("%s costs %d" % (sheet.name, cost), build(sheet).points, cost)
    c.true("...and the corpus prints that number",
           "| 1 model | %d |" % cost in corpus(sheet.name))
c.true("all four are in the points table", all(s.name in NECRONS_POINTS for s in NEW))
for sheet in NEW:
    mm = {"Royal Warden": "32mm", "Overlord with translocation shroud": "40mm",
          "Imotekh The Stormlord": "40mm", "Trazyn The Infinite": "25mm"}[sheet.name]
    c.true("%s prints a %s base" % (sheet.name, mm), mm in corpus(sheet.name))

# THE LEADER TABLE, through the REAL can_attach() rather than at the table -
# `[]` means legal.
PAIRINGS = {
    "Royal Warden": {"Immortals": True, "Lychguard": False, "Necron Warriors": True},
    "Overlord with translocation shroud": {"Immortals": True, "Lychguard": True, "Necron Warriors": True},
    "Imotekh The Stormlord": {"Immortals": True, "Lychguard": True, "Necron Warriors": True},
    "Trazyn The Infinite": {"Immortals": True, "Lychguard": True, "Necron Warriors": True},
}
for leader_name, wants in sorted(PAIRINGS.items()):
    for body_name, legal in sorted(wants.items()):
        reasons = attached_units.can_attach(build(D[leader_name]), build(D[body_name]))
        c.eq("%s -> %s" % (leader_name, body_name), reasons == [], legal)

# THE ONE THAT DIFFERS, said out loud and read off the printed page rather than
# off the table that encodes it.
_warden_leader = between(corpus(WARDEN.name), "## Leader", "## Keywords")
c.true("the Royal Warden's printed Leader section names IMMORTALS",
       "IMMORTALS" in _warden_leader)
c.true("...and NECRON WARRIORS", "NECRON WARRIORS" in _warden_leader)
c.true("...and NOT LYCHGUARD - the single word that separates him from the other three",
       "LYCHGUARD" not in _warden_leader)
for other in (SHROUD, IMOTEKH, TRAZYN):
    c.true("...while %s's does" % other.name,
           "LYCHGUARD" in between(corpus(other.name), "## Leader", "## Keywords"))

# Rule 19.01 in both directions: the merge really forms ONE unit.
_merged = build(WARRIORS)
_before = living(_merged)
attached_units.attach(build(WARDEN), _merged)
c.eq("attaching him adds his model to the bodyguard unit", living(_merged) - _before, 1)
c.true("...and it is one attached unit (19.01)",
       attached_units.is_attached_unit(_merged))


# --- 4. Adaptive Strategy -----------------------------------------------------
print("--- 4. Adaptive Strategy ---")

_warden_unit = build(WARDEN)
_plain = build(WARRIORS)
c.true("the ability is on the Royal Warden",
       adaptive_strategy.squad_has_adaptive_strategy(_warden_unit))
c.true("...and not on a unit without him",
       not adaptive_strategy.squad_has_adaptive_strategy(_plain))

# BOTH of rule 09.07's bans, measured at the two gates that enforce them.
c.true("he lifts the SHOOTING ban", move_exceptions.may_shoot_after_falling_back(_warden_unit))
c.true("...and the CHARGE ban", move_exceptions.may_charge_after_falling_back(_warden_unit))
c.true("a plain Necron unit lifts neither",
       not move_exceptions.may_shoot_after_falling_back(_plain)
       and not move_exceptions.may_charge_after_falling_back(_plain))

# THE COMPARISON THAT MAKES THIS SECTION WORTH HAVING: the Triarch Praetorians
# print the same sentence MINUS the shooting half, so a copy of their
# Relentless Combatants would pass the charge line above and fail the first.
_praets = build(PRAETORIANS)
c.eq("the Praetorians lift only the CHARGE ban",
     (move_exceptions.may_shoot_after_falling_back(_praets),
      move_exceptions.may_charge_after_falling_back(_praets)), (False, True))
c.true("...and their printed text really says only \"declare a charge\"",
       "eligible to declare a charge" in corpus("Triarch Praetorians")
       and "eligible to shoot and declare a charge" not in corpus("Triarch Praetorians"))
c.true("...while the Royal Warden's says both",
       "eligible to shoot and declare a charge" in corpus(WARDEN.name))

# Rule 19.03 pooling: merged into a bodyguard unit he carries the whole unit.
_led = build(WARRIORS)
attached_units.attach(build(WARDEN), _led)
c.true("merged into Necron Warriors he carries the whole unit (19.03)",
       move_exceptions.may_shoot_after_falling_back(_led)
       and move_exceptions.may_charge_after_falling_back(_led))


# --- 5. Engrammatic Logic -----------------------------------------------------
print("--- 5. Engrammatic Logic ---")


def logic_scene(distance=6.0, shocked=True, owner="Player 2", auto=True):
    warden = place(build(WARDEN, owner=owner), 20.0, 20.0)
    victim = place(build(WARRIORS, owner=owner), 20.0, 20.0 + distance)
    victim.battle_shocked = shocked
    ctrl = EngrammaticLogicController(
        decision_manager=DecisionManager(), game_log=tk.Log(),
        all_squads=lambda: [warden, victim],
        auto_players=(owner,) if auto else ())
    return ctrl, warden, victim


ctrl, warden, victim = logic_scene()
c.true("it is offered", ctrl.can_use(warden))
c.true("...and an auto_players owner resolves it with no prompt", ctrl.offer(warden))
c.true("...and it worked", not victim.battle_shocked)

# ONCE PER BATTLE, per MODEL, reset by nothing.
c.true("a second use is refused", not ctrl.can_use(warden))
victim.battle_shocked = True
c.true("...even against a freshly shocked unit", not ctrl.can_use(warden))

# NOT BATTLE-SHOCKED is filtered, so the once-per-battle use is never burnt for
# nothing (standing rule: never offer what buys nothing).
ctrl, warden, victim = logic_scene(shocked=False)
c.eq("an unshocked unit is not a target", ctrl.eligible_targets(warden.models[0]), [])
c.true("...so nothing is offered", not ctrl.can_use(warden))

# 12", edge to edge, measured from the MODEL.
ctrl, warden, victim = logic_scene(distance=20.0)
c.eq("a unit 20\" away is out of range", ctrl.eligible_targets(warden.models[0]), [])
c.eq("the shared 12\"", EngrammaticLogicController.range_in, 12.0)

# THE KEYWORD. A non-Necron unit of the SAME player is refused - and on an
# all-Necron board that clause could never be measured at all.
warden = place(build(WARDEN), 20.0, 20.0)
allies = place(tk.build(ork.ORKS.datasheets["Boyz"], "Player 2", name="2 Boyz 9"), 20.0, 23.0)
allies.battle_shocked = True
ctrl = EngrammaticLogicController(all_squads=lambda: [warden, allies],
                                  auto_players=("Player 2",))
c.eq("a Battle-shocked ORK unit of the same player is not a target",
     ctrl.eligible_targets(warden.models[0]), [])

# ANY PHASE, including the opponent's - offer_at_start_of_phase() defaults to
# every owner on the table rather than to one side.
ctrl, warden, victim = logic_scene()
c.true("it is offered without naming a player",
       ctrl.offer_at_start_of_phase([warden, victim]))

# A HUMAN is asked; the AI is not. Both halves, because a rule that answers for
# the player is a failure this repo has shipped before.
ctrl, warden, victim = logic_scene(auto=False)
c.true("a human owner gets a prompt", ctrl.offer(warden))
c.true("...and nothing has happened yet", victim.battle_shocked)
c.true("...the options name the unit",
       any("Necron Warriors" in o["label"] for o in ctrl.decision_manager.options))
tk.pick_option(ctrl.decision_manager, "Free")
c.true("...and answering it frees them", not victim.battle_shocked)


# --- 6. Translocation Shroud --------------------------------------------------
print("--- 6. Translocation Shroud ---")

_shroud_unit = build(SHROUD)
c.true("the ability is on the shroud Overlord",
       translocation_shroud.squad_has_shroud(_shroud_unit))
c.true("...and not on the plain one",
       not translocation_shroud.squad_has_shroud(build(OVERLORD)))
c.eq("the printed +6\"", translocation_shroud.TRANSLOCATION_SHROUD_BONUS_IN, 6.0)
c.eq("the printed move modes", translocation_shroud.TRANSLOCATION_SHROUD_MOVE_MODES,
     (None, "fall_back"))


def move_scene(sheet=SHROUD, enemy_at=None, wall=False, owner="Player 2"):
    tt = TurnTracker()
    while tt.phase != PHASE_MOVEMENT:
        tt.advance_phase()
    tt.turn_owner = owner
    tt.set_active(owner)
    squad = place(build(sheet, owner=owner), 20.0, 20.0)
    tokens = list(squad.models)
    if enemy_at is not None:
        foe = "Player 1" if owner == "Player 2" else "Player 2"
        tokens += list(place(build(WARRIORS, owner=foe), *enemy_at).models)
    obstacles = [Obstacle(20.0, 24.0, 6.0, 1.0, category=DENSE)] if wall else []
    mc = MovementController(obstacles=obstacles, game_log=tk.Log(), player_name=owner,
                            dice_manager=DiceManager(), turn_tracker=tt,
                            all_tokens=tokens)
    mc.select(squad.models[0])
    mc.start_move()
    return mc, squad


# HALF ONE: the Advance is REPLACED, not added to.
mc, squad = move_scene()
before = mc.remaining_range[squad.models[0].id]
script(1)   # a 1 would be the worst possible D6 - and no die is thrown at all
mc.start_run()
c.true("no Advance die is thrown", not mc.dice_manager.pending_values)
c.eq("...and a flat 6\" is added instead",
     round(mc.remaining_range[squad.models[0].id] - before, 3), 6.0)
c.true("...counted as this unit's Advance", mc.run_used and squad in mc.advance_bonus_by_squad)
# The plain Overlord in the same seat still rolls.
mc, squad = move_scene(sheet=OVERLORD)
script(3)
mc.start_run()
c.true("a plain Overlord still rolls its D6", bool(mc.dice_manager.pending_values))


# HALF TWO: through MODELS, measured through clamp_move(). Both runs ask for the
# same 5", well inside an ordinary move, so the only thing the comparison can be
# about is the bypass. The enemy sits 4" away - outside Engagement Range, so
# neither mover is stuck on a Fall Back - and squarely on the path.
def reach(sheet, mode=None, enemy_at=(20.0, 24.0), wall=False, owner="Player 2"):
    mc, squad = move_scene(sheet=sheet, enemy_at=enemy_at, wall=wall, owner=owner)
    mc.move_mode = mode
    return mc.clamp_move(squad.models[0], 20.0, 25.0)[1]


c.true("an enemy base in the way stops a plain Overlord", reach(OVERLORD) < 23.0)
c.true("...and the shroud walks straight through it", reach(SHROUD) >= 24.9)

# GATED ON THE MOVE. Charge, Pile In and Consolidate are not on the printed
# list, so the bypass is off for them - the half a flag-only reading loses.
c.true("...but NOT during a charge", reach(SHROUD, mode="charge") < 23.0)
c.true("...nor a pile in", reach(SHROUD, mode="pile_in") < 23.0)
c.true("...nor a consolidation", reach(SHROUD, mode="consolidate") < 23.0)
c.true("...while a Fall Back is on the printed list", reach(SHROUD, mode="fall_back") >= 24.9)
c.true("the predicate answers the same way on its own",
       translocation_shroud.crosses_everything(None, _shroud_unit.models[0])
       and translocation_shroud.crosses_everything("fall_back", _shroud_unit.models[0])
       and not translocation_shroud.crosses_everything("charge", _shroud_unit.models[0]))

# THE TERRAIN HALF IS A MEASURED NO-OP, and is written down as one rather than
# claimed to work. Rule 13.06 already lets INFANTRY move through Dense terrain,
# and every unit this Overlord can lead is INFANTRY too - so the clause cannot
# buy him a single inch on any rostered board. It is built with the qualifier
# anyway (the printed text names terrain) and pinned from BOTH sides. The board
# here is PLAYER 1's, because the wall-crossing house rule would let any
# Player 2 model through and the comparison would measure that instead.
_plain_wall = reach(OVERLORD, enemy_at=None, wall=True, owner="Player 1")
_shroud_wall = reach(SHROUD, enemy_at=None, wall=True, owner="Player 1")
c.true("a Dense wall does not stop a plain INFANTRY Overlord either (13.06)",
       _plain_wall >= 24.9)
c.eq("...so the shroud measures exactly the same through it",
     round(_shroud_wall, 3), round(_plain_wall, 3))
c.true("...and the reason is the KEYWORD, not the ability",
       OverlordWithTranslocationShroudProfile.can_move_through_dense_terrain)
c.true("...while the printed text does name terrain features",
       "through models and **terrain features**" in corpus(SHROUD.name))

# "IT CANNOT FINISH A MOVE ON TOP OF ANOTHER MODEL OR ITS BASE" needs no code -
# this engine enforces that for everyone - but the clause is covered by this
# rather than by nothing.
mc, squad = move_scene(enemy_at=(20.0, 24.0))
squad.models[0].x_in, squad.models[0].y_in = 20.0, 24.0
c.true("ending on top of an enemy model is still refused",
       bool(squad.check_model_overlap(mc.all_tokens)))


# --- 7. Grand Strategist and Lord of the Storm --------------------------------
print("--- 7. Grand Strategist, Lord of the Storm ---")

_tt = TurnTracker()
_imo = place(build(IMOTEKH), 20.0, 20.0)


def strategist(cp=None, models=None):
    return GrandStrategistController(
        command_points=cp if cp is not None else CommandPointManager(),
        all_tokens=list(models if models is not None else _imo.models),
        turn_tracker=_tt, game_log=tk.Log())


_cp = CommandPointManager()
_gs = strategist(_cp)
c.eq("Grand Strategist grants 1 CP", _gs.start_of_command_phase("Player 2"), 1)
c.eq("...to the right player", _cp.cp["Player 2"], 1)
c.eq("...and nothing to the other side", _gs.start_of_command_phase("Player 1"), 0)

# THE CAP IS SHARED, not per ability - the house rule allows one bonus CP per
# battle round from ALL such abilities together. Measured through a real ledger.
_gs2 = strategist()
c.eq("first grant lands", _gs2.start_of_command_phase("Player 2"), 1)
c.eq("...a second in the same round is capped away", _gs2.start_of_command_phase("Player 2"), 0)

c.true("Grand Strategist and Diviner of Futures share one machine",
       issubclass(GrandStrategistController, command_phase_cp.CommandPhaseCpController)
       and issubclass(DivinerOfFuturesController, command_phase_cp.CommandPhaseCpController))
c.eq("...and differ in exactly the flag and the reason",
     (GrandStrategistController.flag, DivinerOfFuturesController.flag),
     ("grand_strategist", "diviner_of_futures"))

# "ON THE BATTLEFIELD" is the token list: a dead bearer grants nothing.
_dead = place(build(IMOTEKH, n=2), 20.0, 20.0)
for m in _dead.models:
    m.current_wounds = 0
c.eq("a dead Imotekh grants nothing",
     strategist(models=_dead.models).start_of_command_phase("Player 2"), 0)


def storm_scene(gate_values, wound_values, enemies=1, distance=6.0, auto=True):
    state = GameState()
    imo = place(build(IMOTEKH, owner="Player 2"), 20.0, 20.0)
    foes = [place(build(WARRIORS, owner="Player 1", n=i + 1),
                  20.0, 20.0 + distance + i * 0.1) for i in range(enemies)]
    state.tokens = list(imo.models) + [m for f in foes for m in f.models]
    ctrl = lord_of_the_storm.LordOfTheStormController(
        dice_manager=DiceManager(), game_log=tk.Log(), game_state=state,
        decision_manager=DecisionManager(),
        auto_players=("Player 2",) if auto else ())
    script(*(list(gate_values) + list(wound_values)), default=1)
    return ctrl, imo, foes


c.eq("the printed numbers",
     (lord_of_the_storm.LORD_OF_THE_STORM_RANGE_IN,
      lord_of_the_storm.LORD_OF_THE_STORM_THRESHOLD,
      lord_of_the_storm.LORD_OF_THE_STORM_BIG_ROLL,
      lord_of_the_storm.LORD_OF_THE_STORM_BIG_BONUS), (12.0, 2, 6, 3))

# TWO BANDS - the knob a single-band ability would never have needed.
_solo = lord_of_the_storm.LordOfTheStormController()
c.eq("a 2 pays a plain D3", describe(_solo.wounds_for(2)), "D3")
c.eq("...a 5 pays a plain D3 too", describe(_solo.wounds_for(5)), "D3")
c.eq("...and a 6 pays D3+3", describe(_solo.wounds_for(6)), "D3+3")

ctrl, imo, foes = storm_scene([6], [1])   # the big band, then a D3 of 1 -> 4 wounds
c.eq("every enemy unit within 12\" is a candidate", len(ctrl.candidates(imo)), 1)
c.true("the offer fires at the end of ITS OWN Command phase",
       ctrl.offer_at_end_of_command_phase({imo, foes[0]}, "Player 2"))
c.true("...the gate handful is rolled", ctrl.is_busy)
c.eq("...one die per candidate", len(ctrl.dice_manager.pending_values or []), 1)
ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()   # the gate: a 6
ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()   # the D3: a 1
_before = living(foes[0])
while ctrl.pending_damage_choice:
    ctrl.choose_damage_model(ctrl.pending_damage_choice[0])
c.eq("a 6 really killed four one-wound models (D3=1, +3)", _before - living(foes[0]), 4)
c.true("...and the sweep is finished", not ctrl.is_busy)

# A 1 does nothing at all - the threshold is 2, not 4.
ctrl, imo, foes = storm_scene([1], [6])
ctrl.offer_at_end_of_command_phase({imo, foes[0]}, "Player 2")
ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()
c.true("a 1 leaves the unit alone", not ctrl.is_busy)
c.eq("...and no model was lost", sum(1 for m in foes[0].models if m.is_dead()), 0)

# ONCE PER BATTLE, and it is spent whether or not it hurt anything.
c.true("a second use is refused", not ctrl.can_use(imo))
c.eq("...and offering again does nothing",
     ctrl.offer_at_end_of_command_phase({imo, foes[0]}, "Player 2"), False)

# 12", not the Nightbringer's 6".
ctrl, imo, foes = storm_scene([6], [1], distance=10.0)
c.eq("an enemy 10\" away is still in the 12\" sweep", len(ctrl.candidates(imo)), 1)
ctrl, imo, foes = storm_scene([6], [1], distance=20.0)
c.eq("...and 20\" away is not", len(ctrl.candidates(imo)), 0)
c.true("...so nothing is offered at all",
       not ctrl.offer_at_end_of_command_phase({imo, foes[0]}, "Player 2"))

# "AT THE END OF YOUR COMMAND PHASE" takes a SIDE, unlike Drain Life.
ctrl, imo, foes = storm_scene([6], [1])
c.eq("the other player's Command phase offers nothing",
     ctrl.offer_at_end_of_command_phase({imo, foes[0]}, "Player 1"), False)

# TWO enemy units means two dice in ONE handful and two separate allocations.
ctrl, imo, foes = storm_scene([6, 6], [1, 1], enemies=2)
ctrl.offer_at_end_of_command_phase({imo, foes[0], foes[1]}, "Player 2")
c.eq("two candidates means two gate dice", len(ctrl.dice_manager.pending_values or []), 2)
_start = [living(f) for f in foes]
for _ in range(12):
    if ctrl.dice_manager.pending_values:
        ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()
    while ctrl.pending_damage_choice:
        ctrl.choose_damage_model(ctrl.pending_damage_choice[0])
    if not ctrl.is_busy:
        break
c.eq("...and both units really lose models",
     [s - living(f) for s, f in zip(_start, foes)], [4, 4])

# A HUMAN is asked first.
ctrl, imo, foes = storm_scene([6], [1], auto=False)
c.true("a human owner gets a prompt",
       ctrl.offer_at_end_of_command_phase({imo, foes[0]}, "Player 2"))
c.true("...and no die has been thrown yet", not ctrl.is_busy)


# --- 8. Ancient Collector, and Surrogate Hosts --------------------------------
print("--- 8. Ancient Collector, Surrogate Hosts ---")

_area = TerrainArea([Obstacle(30.0, 30.0, 6.0, 6.0, category=EXPOSED)])
_obj = Objective(_area, name="Test Objective")


def collector_scene(attached=True):
    """A Trazyn on an objective, with control DERIVED from the board the way
    main.py's advance_turn_phase() derives it - not written in by hand."""
    _obj.controlled_by = None
    _obj.secured_by = None
    trazyn = build(TRAZYN)
    if attached:
        unit = build(WARRIORS)
        attached_units.attach(trazyn, unit)
    else:
        unit = trazyn
    place(unit, 30.0, 30.0, spacing=0.4)
    _obj.update_control(list(unit.models))
    return unit


_unit = collector_scene(attached=True)
c.eq("standing on it, he controls it (14.02)", _obj.controlled_by, "Player 2")
c.true("while LEADING a unit the ability applies", ancient_collector.applies(_unit))
fieldcraft.apply_fieldcraft([_obj], list(_unit.models), "Player 2")
c.eq("...and the objective is Secured (rule 14.03)", _obj.secured_by, "Player 2")

# THE ONE CLAUSE A COPY OF FIELDCRAFT WOULD LOSE: "while this model is LEADING".
_alone = collector_scene(attached=False)
c.eq("a Trazyn standing on his own still controls it", _obj.controlled_by, "Player 2")
c.true("...but he is not leading anything", not ancient_collector.applies(_alone))
fieldcraft.apply_fieldcraft([_obj], list(_alone.models), "Player 2")
c.eq("...so he secures nothing", _obj.secured_by, None)
c.true("...and Fieldcraft itself is not on his datasheet",
       not fieldcraft.squad_has_fieldcraft(_alone))

# It reuses rule 14.03 rather than a second sticky scheme: once Secured, the
# objective survives having no models in range at all.
_unit = collector_scene(attached=True)
fieldcraft.apply_fieldcraft([_obj], list(_unit.models), "Player 2")
for m in _unit.models:
    m.x_in, m.y_in = 5.0, 5.0
_obj.update_control(list(_unit.models))
c.eq("Secured keeps control with nobody in range", _obj.controlled_by, "Player 2")

# SURROGATE HOSTS IS NOT WIRED, and is asserted missing so adding it is visible.
c.true("Trazyn's datasheet records it as NOT ENGINE-WIRED",
       any("Surrogate Hosts" in t and "NOT ENGINE-WIRED" in t
           for t in TRAZYN.abilities_text))
c.true("...and no profile flag pretends otherwise",
       not hasattr(TrazynTheInfiniteProfile, "surrogate_hosts"))
c.true("...while the printed text really is on his page",
       "Surrogate Hosts" in corpus(TRAZYN.name))


# --- 9. the three extractions -------------------------------------------------
print("--- 9. the extractions ---")

# (a) end_battle_shock: the KROOT carrier must be BEHAVIOUR-UNCHANGED. That is
# the load-bearing half - the new carrier working proves nothing about the one
# already shipped.
c.true("both are subclasses of one machine",
       issubclass(RootOfHonourController, end_battle_shock.EndBattleShockController)
       and issubclass(EngrammaticLogicController, end_battle_shock.EndBattleShockController))
c.eq("...and differ in exactly the two flags",
     (RootOfHonourController.bearer_flag, RootOfHonourController.target_flag,
      EngrammaticLogicController.bearer_flag, EngrammaticLogicController.target_flag),
     ("root_of_honour", "kroot", "engrammatic_logic", "reanimation_protocols"))

_T = tau.TAU_EMPIRE.datasheets
_shaper = place(tk.build(_T["Kroot War Shaper"], "Player 2", name="2 Kroot War Shaper 1"),
                20.0, 20.0)
_kroot = place(tk.build(_T["Kroot Carnivores"], "Player 2", name="2 Kroot Carnivores 1"),
               20.0, 23.0)
_kroot.battle_shocked = True
_roh = RootOfHonourController(all_squads=lambda: [_shaper, _kroot],
                              auto_players=("Player 2",), game_log=tk.Log())
c.true("Root of Honour still frees a KROOT unit", _roh.offer(_shaper))
c.true("...and it worked", not _kroot.battle_shocked)
c.eq("the shared 12\"", end_battle_shock.BATTLE_SHOCK_RELIEF_RANGE_IN, 12.0)
import game.root_of_honour as _roh_mod
c.eq("...still re-exported under its old name", _roh_mod.ROOT_OF_HONOUR_RANGE_IN, 12.0)
# And a NECRONS unit is not a KROOT one, through the same controller.
_nec_unit = place(build(WARRIORS), 20.0, 22.0)
_nec_unit.battle_shocked = True
_roh2 = RootOfHonourController(all_squads=lambda: [_shaper, _nec_unit],
                               auto_players=("Player 2",))
c.eq("...and it will not free a NECRONS unit",
     _roh2.eligible_targets(_shaper.models[0]), [])

# (b) command_phase_cp: Eldrad still gains his CP.
_eld = place(tk.build(ael.AELDARI.datasheets["Eldrad Ulthran"], "Player 1",
                      name="1 Eldrad Ulthran 1"), 20.0, 20.0)
_cp3 = CommandPointManager()
c.eq("Diviner of Futures still grants 1 CP",
     DivinerOfFuturesController(command_points=_cp3, all_tokens=list(_eld.models),
                                turn_tracker=TurnTracker()).start_of_command_phase("Player 1"), 1)
import game.diviner_of_futures as _dov
c.eq("...and its old constant is re-exported", _dov.DIVINER_OF_FUTURES_CP, 1)
c.eq("...as is its bearer helper",
     len(_dov.bearers_on_battlefield("Player 1", list(_eld.models))), 1)

# (c) the fieldcraft sweep: its original carrier still secures.
_obj.controlled_by = None
_obj.secured_by = None
_kroot2 = place(tk.build(_T["Kroot Carnivores"], "Player 2", name="2 Kroot Carnivores 2"),
                30.0, 30.0, spacing=0.4)
_obj.update_control(list(_kroot2.models))
fieldcraft.apply_fieldcraft([_obj], list(_kroot2.models), "Player 2")
c.eq("Fieldcraft itself still secures", _obj.secured_by, "Player 2")


# --- 10. wiring, AI, sprites, dormancy ----------------------------------------
print("--- 10. wiring, AI, sprites, dormancy ---")

MAIN = io.open("main.py", encoding="utf-8").read()
_TREE = ast.parse(MAIN)
_LINES = MAIN.split("\n")
MAIN_CALLS = []
MAIN_STATEMENTS = []


def _text_of(node):
    return " ".join("\n".join(_LINES[node.lineno - 1:node.end_lineno]).split())


for node in ast.walk(_TREE):
    if isinstance(node, ast.Call):
        MAIN_CALLS.append(_text_of(node))
    # A call that IS a whole statement - i.e. one that really runs when the
    # branch it sits in runs. A plain substring, or even a Call node, survives
    # `False and <call>` and `if False:` alike, which is the shape this repo
    # has been caught by half a dozen times.
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        MAIN_STATEMENTS.append(_text_of(node.value))


def calls_in_main(needle):
    return [ca for ca in MAIN_CALLS if needle in ca]


def statements_in_main(needle):
    return [ca for ca in MAIN_STATEMENTS if needle in ca]


# CONSTRUCTED: these are assignments, so the call is not a statement of its own.
for needle, why in [
    ("EngrammaticLogicController(", "Engrammatic Logic is constructed"),
    ("GrandStrategistController(", "Grand Strategist is constructed"),
    ("LordOfTheStormController(", "Lord of the Storm is constructed"),
]:
    c.true(why, bool(calls_in_main(needle)))

# FED: each of these has to be a statement that really executes.
for needle, why in [
    ("engrammatic_logic_controller.offer_at_start_of_phase(", "...and Engrammatic Logic is offered every phase"),
    ("grand_strategist_controller.start_of_command_phase(", "...and Grand Strategist is fired at the start of the Command phase"),
    ("lord_of_the_storm_controller.offer_at_end_of_command_phase(", "...and Lord of the Storm is offered at the end of it"),
    ("lord_of_the_storm_controller.on_dice_acknowledged()", "...and its dice are acknowledged"),
    ("lord_of_the_storm_controller.choose_damage_model(", "...and its allocation is clickable"),
    ("draw_damage_choice_highlight(board_surface, board, lord_of_the_storm_controller",
     "...and its allocation is drawn"),
]:
    c.true(why, bool(statements_in_main(needle)))
c.true("Lord of the Storm is in the shared damage-pick list",
       "lord_of_the_storm_controller," in MAIN)

# CONSTRUCTION ORDER (error class 23) - main() is one long function and no
# suite runs it, so the source is the only place this can be checked.
for first, second, why in [
    ("engrammatic_logic_controller = EngrammaticLogicController(",
     "engrammatic_logic_controller.offer_at_start_of_phase(",
     "Engrammatic Logic is built before it is offered"),
    ("grand_strategist_controller = GrandStrategistController(",
     "grand_strategist_controller.start_of_command_phase(",
     "Grand Strategist is built before it is fired"),
    ("lord_of_the_storm_controller = LordOfTheStormController(",
     "lord_of_the_storm_controller.offer_at_end_of_command_phase(",
     "Lord of the Storm is built before it is offered"),
]:
    a, b = MAIN.find(first), MAIN.find(second)
    c.true(why, 0 <= a < b)

# The end-of-Command-phase offer must use the player captured BEFORE
# advance_phase() flipped the clock - the seam guarded by section 8 of
# test_event_chain_wiring.py.
_lots_call = (calls_in_main("lord_of_the_storm_controller.offer_at_end_of_command_phase(") or [""])[0]
c.true("...and it is offered to mover_before, not to the flipped turn_owner",
       "mover_before" in _lots_call and "turn_tracker.turn_owner" not in _lots_call)

DRIVER = io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read()
for name in ["Royal Warden", "Overlord with translocation shroud",
             "Imotekh", "Trazyn",
             "adaptive_strategy", "engrammatic_logic", "translocation_shroud",
             "grand_strategist", "lord_of_the_storm", "ancient_collector",
             "end_battle_shock", "command_phase_cp"]:
    c.eq("ai/agent_driver.py knows nothing about %s" % name, name in DRIVER, False)

c.true("Engrammatic Logic gates on auto_players at the object",
       "Player 2" in EngrammaticLogicController(auto_players=("Player 2",)).auto_players)
c.true("...and so does Lord of the Storm",
       "Player 2" in lord_of_the_storm.LordOfTheStormController(
           auto_players=("Player 2",)).auto_players)

for sheet in (WARDEN, IMOTEKH, TRAZYN):
    c.true("%s draws its own art" % sheet.name,
           sprites.sprite_for(build(sheet, n=40).models[0]) is not None)

# THE ONE NAME IN THIS BACKFILL THE SHADOWING BOILERPLATE CANNOT BE COPIED FOR.
# "Overlord" is already a key AND is a substring of "Overlord with translocation
# shroud", so _key_for_name() would hand him the plain Overlord's picture
# whatever the table said. That is a stated DECISION, so what is asserted here
# is what he RESOLVES TO - not that nothing swallows him.
_keys = list(sprites.SQUAD_SPRITE_KEYS)
c.eq("the shroud Overlord really is swallowed by the shorter key",
     [k for k in _keys if k != SHROUD.name and k in SHROUD.name], ["Overlord"])
# index() and [] would CRASH when the entry is gone, which takes the whole
# suite down instead of naming what broke - the lesson this repo has paid for
# often enough to have a rule about.
c.true("...so the table names him explicitly, ABOVE it",
       SHROUD.name in _keys and "Overlord" in _keys
       and _keys.index(SHROUD.name) < _keys.index("Overlord"))
c.eq("...and both resolve to the plain Overlord's file",
     (sprites.SQUAD_SPRITE_KEYS.get(SHROUD.name), sprites.SQUAD_SPRITE_KEYS.get("Overlord")),
     ("Necron Overlord", "Necron Overlord"))
c.true("...which really loads", sprites.sprite_for(build(SHROUD, n=40).models[0]) is not None)
for _new in [WARDEN.name, IMOTEKH.name, TRAZYN.name]:
    c.eq("no existing key swallows %r" % _new,
         [k for k in _keys if k != _new and k in _new], [])
    c.eq("...and it swallows none", [k for k in _keys if k != _new and _new in k], [])

_roster = io.open(os.path.join("armies", "necrons.json"), encoding="utf-8").read()
for sheet in NEW:
    c.true("%s is dormant by roster" % sheet.name, sheet.name not in _roster)

c.finish()
