"""Stage 6 of the Necron datasheet backfill: the other three C'tan.

Three datasheets that share almost everything and differ in exactly one ability
each - so the thing this stage has to get right is the AGREEMENT, not the
differences. A claim that four datasheets carry the same chassis cannot be made
by four separate copies of the numbers; it needs a base class that a drift has
to be written down to escape.

WHAT EACH SECTION IS FOR

  1. the chassis - every shared characteristic asserted against the CORPUS, and
     then asserted to come from the shared base rather than from four copies.
     The Void Dragon is in this sweep: it was reparented, so if that broke a
     single one of its values this section says so.
  2. weapons. The collision sweep came back EMPTY for this batch - the only one
     in the backfill with nothing to share and nothing to fork - so the
     assertion is that emptiness, measured over the corpus, plus the strike /
     sweep firing-mode pair and the two notation characteristics.
  3. points, base sizes and the attachment table. The Deceiver's base is a
     DECISION, so it is pinned against its sibling and against the printed
     40 mm the corpus really carries.
  4. Drain Life, driven end to end through a real DiceManager and a real rule
     06.02 allocation - the gate handful, the per-unit wound roll, and the
     wounds actually LANDING on a multi-model unit. That last one is the
     measure this engine has twice shipped wrong.
  5. Grand Illusion, at the clause a copy of its T'au twin would lose: "if your
     army INCLUDES this model" is not "if it is on the battlefield".
  6. Transdimensional Displacement - its three printed clauses at their three
     separate seams, each measured where the rule is decided rather than at the
     predicate.
  7. the three extractions, including the one that must be behaviour-neutral:
     Solid-image Projection is asserted to still answer exactly as before.
  8. wiring, the AI negative space, sprites and dormancy.
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

from game import (attached_units, awakened_dynasty, drain_life, grand_illusion,
                  mortal_wound_sweep, post_deployment_redeploy, sprites,
                  transdimensional_displacement)
from game import config
from game.decision import DecisionManager
from game.dice import DiceManager
from game.dice_notation import describe
from game.enh_solid_image_projection import SolidImageProjectionStep
from game.factions import necrons as nec
from game.factions.necrons_points import NECRONS_POINTS
from game.game_state import GameState
from game.ui.action_panel import ActionPanel
from game.movement import MovementController
from game.turn import PHASE_MOVEMENT, TurnTracker
from game.units import (CtanShardOfTheDeceiverProfile,
                        CtanShardOfTheNightbringerProfile,
                        CtanShardOfTheVoidDragonProfile, CtanShardProfile,
                        TranscendentCtanProfile)
from game.weapons import (CosmicInsanityProfile, CracklingTendrilsProfile,
                          GazeOfDeathProfile, GoldenFistsProfile,
                          ScytheOfTheNightbringerStrikeProfile,
                          ScytheOfTheNightbringerSweepProfile,
                          SeismicAssaultProfile)

c = Checks("Necron C'TAN")

D = nec.NECRONS.datasheets
NIGHTBRINGER = D["C'tan Shard of the Nightbringer"]
DECEIVER = D["C'tan Shard of the Deceiver"]
TRANSCENDENT = D["Transcendent C'tan"]
VOID_DRAGON = D["C'tan Shard of the Void Dragon"]
WARRIORS = D["Necron Warriors"]
IMMORTALS = D["Immortals"]

NEW = [NIGHTBRINGER, DECEIVER, TRANSCENDENT]
ALL_CTAN = [VOID_DRAGON] + NEW


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


# --- 1. the chassis ----------------------------------------------------------
print("--- 1. the chassis ---")

# Every shared characteristic, asserted against the PRINTED table rather than
# against a literal typed twice. All four corpus files carry the same row.
for sheet in ALL_CTAN:
    text = corpus(sheet.name)
    c.true("%s prints T11 Sv3+ W16 Ld6+ OC4 and a 4+ invulnerable" % sheet.name,
           "| 11 | 3+ | 16 | 6+ | 4 | 4+ |" in text)
    c.true("...and Feel No Pain 5+, Deep Strike and Deadly Demise D6 (%s)" % sheet.name,
           "Deadly Demise D6" in text and "Deep Strike" in text
           and "Feel No Pain 5+" in text)
    c.true("...and Necrodermis and Enslaved Star God (%s)" % sheet.name,
           "Necrodermis" in text and "Enslaved Star God" in text)

PROFILES = {
    "C'tan Shard of the Void Dragon": CtanShardOfTheVoidDragonProfile,
    "C'tan Shard of the Nightbringer": CtanShardOfTheNightbringerProfile,
    "C'tan Shard of the Deceiver": CtanShardOfTheDeceiverProfile,
    "Transcendent C'tan": TranscendentCtanProfile,
}
for name, prof in sorted(PROFILES.items()):
    c.eq("%s: the shared statline" % name,
         (prof.toughness, prof.armor_save, prof.wounds, prof.leadership, prof.oc,
          prof.invulnerable_save, prof.feel_no_pain),
         (11, "3+", 16, "6+", 4, "4+", "5+"))
    c.eq("%s: WS and BS are both 2+" % name,
         (prof.weapon_skill, prof.ballistic_skill), ("2+", "2+"))
    c.true("%s: MONSTER, CHARACTER, FLY, Deep Strike" % name,
           prof.monster and prof.character and prof.fly and prof.deep_strike)
    c.eq("%s: Necrodermis is a flat -1" % name, prof.damage_reduction, 1)
    c.true("%s: Enslaved Star God, the documented no-op" % name, prof.enslaved_star_god)
    c.eq("%s: Deadly Demise D6" % name, describe(prof.deadly_demise_notation), "D6")

# THE AGREEMENT IS STRUCTURAL, not four copies that happen to match today. A
# subclass that redefines one of the shared names would pass every line above
# and fail this one, which is the whole reason the base exists.
for name, prof in sorted(PROFILES.items()):
    c.true("%s inherits the shared chassis" % name, issubclass(prof, CtanShardProfile))
    own = set(vars(prof))
    c.eq("...and overrides nothing it shares (%s)" % name,
         sorted(own & {"toughness", "armor_save", "wounds", "leadership", "oc",
                       "invulnerable_save", "feel_no_pain", "weapon_skill",
                       "ballistic_skill", "monster", "character", "fly",
                       "deep_strike", "damage_reduction", "enslaved_star_god",
                       "deadly_demise", "deadly_demise_notation",
                       "reanimation_protocols"}),
         [])

# What they DO differ in - the four values the module docstring names.
c.eq("Move: the Void Dragon and the Nightbringer are 10\", the other two 8\"",
     [PROFILES[s.name].movement_in for s in ALL_CTAN], [10, 10, 8, 8])
c.eq("only the Transcendent C'tan is not an EPIC HERO",
     sorted(s.name for s in ALL_CTAN if not PROFILES[s.name].epic_hero),
     ["Transcendent C'tan"])
c.true("...and its keyword line says so too",
       "EPIC HERO" not in TRANSCENDENT.keywords and "EPIC HERO" in DECEIVER.keywords)
c.eq("only the Deceiver has STEALTH",
     sorted(s.name for s in ALL_CTAN if PROFILES[s.name].stealth),
     ["C'tan Shard of the Deceiver"])
c.eq("one ability each, and no two share one",
     [(PROFILES[s.name].matter_absorption, PROFILES[s.name].drain_life,
       PROFILES[s.name].grand_illusion,
       PROFILES[s.name].transdimensional_displacement) for s in ALL_CTAN],
     [(True, False, False, False), (False, True, False, False),
      (False, False, True, False), (False, False, False, True)])


# --- 2. weapons, and the collision sweep -------------------------------------
print("--- 2. weapons ---")


def row(w):
    return (w.range_in, w.attacks, w.strength, w.ap, w.damage)


c.eq("Gaze of Death", row(GazeOfDeathProfile), (18, 1, 12, -3, 9))
c.eq("...its Attacks are D3, not the placeholder",
     describe(GazeOfDeathProfile.attacks_notation), "D3")
c.eq("...and its Damage is D6+3", describe(GazeOfDeathProfile.damage_notation), "D6+3")
c.eq("Cosmic Insanity", row(CosmicInsanityProfile), (18, 6, 6, -2, 2))
c.eq("...and its three keywords", (CosmicInsanityProfile.anti,
                                   CosmicInsanityProfile.devastating_wounds,
                                   CosmicInsanityProfile.precision),
     (("CHARACTER", 4), True, True))
c.eq("Golden Fists", row(GoldenFistsProfile), (2, 8, 10, -3, 3))
c.eq("Seismic Assault", row(SeismicAssaultProfile), (12, 6, 8, -2, 2))
c.true("...[ASSAULT] and [SUSTAINED HITS 1]",
       SeismicAssaultProfile.assault and SeismicAssaultProfile.sustained_hits == 1)
c.eq("Crackling Tendrils", row(CracklingTendrilsProfile), (2, 8, 10, -3, 6))
c.eq("...its Damage is D6", describe(CracklingTendrilsProfile.damage_notation), "D6")

# The strike/sweep pair: ONE printed datasheet entry with two melee profiles,
# so a firing-mode pair rather than two weapons. Both halves asserted, because
# the failure mode is silent - two separate weapons would simply let rule 04.01
# be broken, with every characteristic still correct.
c.eq("Scythe - strike", row(ScytheOfTheNightbringerStrikeProfile), (2, 6, 14, -4, 8))
c.eq("...D6+2 damage and [DEVASTATING WOUNDS]",
     (describe(ScytheOfTheNightbringerStrikeProfile.damage_notation),
      ScytheOfTheNightbringerStrikeProfile.devastating_wounds), ("D6+2", True))
c.eq("Scythe - sweep", row(ScytheOfTheNightbringerSweepProfile), (2, 14, 8, -2, 2))
c.true("the two are a firing-mode PAIR",
       ScytheOfTheNightbringerStrikeProfile.overcharge_profile
       is ScytheOfTheNightbringerSweepProfile)
c.eq("...so only the strike mode is in the loadout",
     [w.name for w in build(NIGHTBRINGER).models[0].weapons],
     ["Gaze of Death", "Scythe of the Nightbringer - Strike"])

# THE COLLISION SWEEP, as a measurement over the corpus rather than a claim.
# Every weapon NAME these three print, against every weapon name printed by any
# other datasheet in the whole corpus. This batch is the only one in the
# backfill whose answer is "none", so it is the emptiness that gets asserted -
# and it is computed, so a fourth C'tan that shares a name makes it fail.
def printed_weapon_names(path):
    names, section = set(), None
    for line in io.open(path, encoding="utf-8"):
        if line.startswith("## "):
            section = line[3:].strip()
        if section in ("Ranged Weapons", "Melee Weapons") and line.startswith("| "):
            cell = line.strip().strip("|").split("|")[0].strip()
            if cell and cell not in ("Weapon",) and not cell.startswith("---"):
                names.add(cell.replace("’", "'"))
    return names


MINE = set()
for sheet in NEW:
    MINE |= printed_weapon_names(os.path.join("rules", "necrons", sheet.name + ".md"))
c.true("the three of them print seven weapon names", len(MINE) == 7)
elsewhere = set()
for folder in sorted(os.listdir("rules")):
    d = os.path.join("rules", folder)
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md") or fn[:-3] in [s.name for s in NEW]:
            continue
        elsewhere |= printed_weapon_names(os.path.join(d, fn))
c.true("the sweep really looked at the rest of the corpus", len(elsewhere) > 300)
c.eq("...and not one of the seven collides with anything", sorted(MINE & elsewhere), [])

# NO PER-WEAPON SKILL OVERRIDE anywhere in the batch: all four C'tan print 2+
# in every cell, so nothing here contradicts its wielder.
overrides = sorted(w.name for s in NEW for m in build(s).models for w in m.weapons
                   if w.ballistic_skill is not None or w.weapon_skill is not None)
c.eq("no C'tan weapon overrides a skill", overrides, [])


# --- 3. points, bases and attachment -----------------------------------------
print("--- 3. points, bases, attachment ---")

c.eq("the Nightbringer costs 360", build(NIGHTBRINGER).points, 360)
c.eq("the Deceiver costs 330", build(DECEIVER).points, 330)
c.eq("the Transcendent C'tan's first unit costs 340",
     tk.build_squad(TRANSCENDENT, "Player 2", name="x", unit_index=1).points, 340)
c.eq("...and its second 360 - the only C'tan a list may take twice",
     tk.build_squad(TRANSCENDENT, "Player 2", name="x", unit_index=2).points, 360)
c.true("all three are in the points table",
       all(s.name in NECRONS_POINTS for s in NEW))

# Bases. The two transcribed ones against the corpus; the DECISION against its
# sibling and against the number the corpus really prints, so the choice cannot
# be mistaken for a transcription later.
c.eq("the Nightbringer's 90 mm", round(CtanShardOfTheNightbringerProfile.base_radius_in, 3), 1.772)
c.true("...as printed", "90mm" in corpus(NIGHTBRINGER.name))
c.eq("the Transcendent C'tan's 60 mm", round(TranscendentCtanProfile.base_radius_in, 3), 1.181)
c.true("...as printed", "60mm" in corpus(TRANSCENDENT.name))
c.true("the Deceiver's datasheet really prints 40 mm", "40mm" in corpus(DECEIVER.name))
c.eq("...and it plays on the Void Dragon's base instead - a table-size decision",
     CtanShardOfTheDeceiverProfile.base_radius_in,
     CtanShardOfTheVoidDragonProfile.base_radius_in)
c.true("...which is bigger than the printed 40 mm, not a transcription of it",
       CtanShardOfTheDeceiverProfile.base_radius_in > 0.79)

# NONE of the three leads anything and nothing leads them - measured off the
# printed pages rather than inferred from an absent table entry.
for sheet in NEW:
    c.true("%s prints no Leader section" % sheet.name,
           "## Leader" not in corpus(sheet.name))
    c.true("...so it may not be attached to Immortals",
           attached_units.can_attach(build(sheet), build(IMMORTALS, composition_index=1)) != [])
    c.true("...nor to Necron Warriors",
           attached_units.can_attach(build(sheet), build(WARRIORS)) != [])


# --- 4. Drain Life -----------------------------------------------------------
print("--- 4. Drain Life ---")


def drain_scene(gate_values, wound_values, enemy_sheets=(WARRIORS,), distance=3.0):
    """A Nightbringer with enemy units placed `distance` inches away.

    Returns (controller, [enemy squads], log)."""
    state = GameState()
    log = tk.Log()
    bringer = place(build(NIGHTBRINGER, owner="Player 2"), 20.0, 20.0)
    enemies = []
    for i, sheet in enumerate(enemy_sheets):
        e = place(build(sheet, owner="Player 1", n=i + 1), 20.0, 20.0 + distance + i * 0.1)
        enemies.append(e)
    state.tokens = list(bringer.models) + [m for e in enemies for m in e.models]
    ctrl = drain_life.DrainLifeController(
        dice_manager=DiceManager(), game_log=log, game_state=state,
        auto_players=("Player 2",))
    script(*(list(gate_values) + list(wound_values)), default=1)
    return ctrl, bringer, enemies, log


c.eq("the ability is on the datasheet",
     drain_life.has_drain_life(build(NIGHTBRINGER)), True)
c.eq("...and on none of its siblings",
     [drain_life.has_drain_life(build(s)) for s in (DECEIVER, TRANSCENDENT, VOID_DRAGON)],
     [False, False, False])
c.eq("the printed numbers", (drain_life.DRAIN_LIFE_RANGE_IN,
                             drain_life.DRAIN_LIFE_THRESHOLD,
                             drain_life.DRAIN_LIFE_SIDES), (6.0, 4, 3))

ctrl, bringer, enemies, log = drain_scene([5], [2])
c.eq("one enemy unit in range is one candidate",
     [s.name for s in ctrl.candidates(bringer)], [enemies[0].name])
ctrl.resolve_end_of_fight_phase({bringer, enemies[0]})
c.true("the gate handful is rolled", ctrl.is_busy)
c.eq("...one die per candidate", len(ctrl.dice_manager.pending_values or []), 1)
ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()      # the gate: a 5 passes
c.true("a 4+ owes that unit its wounds", ctrl.is_busy)
ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()      # the D3: a 2

# THE MEASURE THAT MATTERS: the wounds LAND. Against a multi-model unit rule
# 06.02 parks the session on a choice, and this engine has twice shipped an
# ability whose wounds were rolled, logged and never applied - so this counts
# models lost, not dice thrown.
before = sum(1 for m in enemies[0].models if not m.is_dead())
while ctrl.pending_damage_choice:
    ctrl.choose_damage_model(ctrl.pending_damage_choice[0])
after = sum(1 for m in enemies[0].models if not m.is_dead())
c.eq("2 mortal wounds really killed 2 one-wound models", before - after, 2)
c.true("...and the sweep is finished", not ctrl.is_busy)

# A die below the threshold does nothing at all.
ctrl, bringer, enemies, log = drain_scene([3], [6])
ctrl.resolve_end_of_fight_phase({bringer, enemies[0]})
ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()
c.true("a 3 leaves the unit alone", not ctrl.is_busy)
c.eq("...and no model was lost",
     sum(1 for m in enemies[0].models if m.is_dead()), 0)
c.true("...and the log says which die belonged to which unit",
       any("rolled 3 for" in line and enemies[0].name in line for line in log.lines))

# Out of range is not a candidate at all - the 6" is measured, not assumed.
ctrl, bringer, enemies, log = drain_scene([6], [3], distance=9.0)
c.eq("an enemy 9\" away is out of the 6\" sweep",
     [s.name for s in ctrl.candidates(bringer)], [])
c.eq("...so nothing is offered", ctrl.resolve_end_of_fight_phase({bringer, enemies[0]}), False)

# A ONE-MODEL victim. This is the case that let two shipped abilities roll
# their wounds, log them and apply none of them for years: a single-model
# target never parks on a rule 06.02 choice, so the missing drain is invisible
# unless the sweep is asked to CONTINUE afterwards.
ctrl, bringer, enemies, log = drain_scene([6], [3], enemy_sheets=(D["Overlord"],))
full = enemies[0].models[0].current_wounds
ctrl.resolve_end_of_fight_phase({bringer, enemies[0]})
ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()      # the gate
ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()      # the D3
c.eq("3 mortal wounds land on a one-model unit with no click at all",
     full - enemies[0].models[0].current_wounds, 3)
c.true("...and the sweep closes itself", not ctrl.is_busy)
c.true("...with no allocation left open", ctrl.pending_damage_choice is None)

# TWO BEARERS owe a sweep at the same instant. The end-of-Fight-phase window
# belongs to neither player and DiceManager holds ONE roll at a time, so the
# second cannot simply start - it is queued, and is_busy has to stay true
# across the seam or the phase advances out from under it.
state = GameState()
b1 = place(build(NIGHTBRINGER, owner="Player 2", n=1), 20.0, 20.0)
b2 = place(build(NIGHTBRINGER, owner="Player 2", n=2), 40.0, 40.0)
e1 = place(build(WARRIORS, owner="Player 1", n=1), 20.0, 23.0)
e2 = place(build(WARRIORS, owner="Player 1", n=2), 40.0, 43.0)
state.tokens = [m for sq in (b1, b2, e1, e2) for m in sq.models]
two = drain_life.DrainLifeController(
    dice_manager=DiceManager(), game_log=tk.Log(), game_state=state,
    auto_players=("Player 2",))
script(6, 1, 6, 1, default=1)
two.resolve_end_of_fight_phase({b1, b2, e1, e2})
two.dice_manager.acknowledge(); two.on_dice_acknowledged()        # bearer 1's gate
two.dice_manager.acknowledge(); two.on_dice_acknowledged()        # bearer 1's D3
while two.pending_damage_choice:
    two.choose_damage_model(two.pending_damage_choice[0])
c.true("the SECOND bearer's sweep is still owed", two.is_busy)
c.true("...and it really started", bool(two.dice_manager.pending_values))
two.dice_manager.acknowledge(); two.on_dice_acknowledged()        # bearer 2's gate
two.dice_manager.acknowledge(); two.on_dice_acknowledged()        # bearer 2's D3
while two.pending_damage_choice:
    two.choose_damage_model(two.pending_damage_choice[0])
c.eq("both Nightbringers drained their own neighbour",
     [sum(1 for m in e.models if m.is_dead()) for e in (e1, e2)], [1, 1])
c.true("...and only then is the controller idle", not two.is_busy)

# TWO units, one gate roll each, and each with its own allocation afterwards.
ctrl, bringer, enemies, log = drain_scene([4, 5], [1, 1], enemy_sheets=(WARRIORS, IMMORTALS))
c.eq("two enemy units in range are two candidates", len(ctrl.candidates(bringer)), 2)
ctrl.resolve_end_of_fight_phase({bringer} | set(enemies))
c.eq("...and the gate is ONE handful of two dice",
     len(ctrl.dice_manager.pending_values or []), 2)
ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()
losses = []
for _ in range(2):
    if not ctrl.is_busy:
        break
    ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()
    while ctrl.pending_damage_choice:
        ctrl.choose_damage_model(ctrl.pending_damage_choice[0])
c.eq("both units lost a model", [sum(1 for m in e.models if m.is_dead()) for e in enemies], [1, 1])
c.true("...and the whole sweep is done", not ctrl.is_busy)


# --- 5. Grand Illusion -------------------------------------------------------
print("--- 5. Grand Illusion ---")


class _Pregame:
    """The three members PostDeploymentRedeployStep touches."""

    def __init__(self, owners):
        self._owners_list = list(owners)
        self._pending = {}
        self.state = None
        self.active_player = None

    def _owners(self):
        return list(self._owners_list)

    def _sync_turn_tracker(self):
        pass


def illusion_scene(deceiver_on_board=True):
    state = GameState()
    dec_sq = build(DECEIVER, owner="Player 2")
    warriors = place(build(WARRIORS, owner="Player 2"), 10.0, 10.0)
    state.tokens = list(warriors.models)
    if deceiver_on_board:
        state.tokens += list(place(dec_sq, 20.0, 20.0).models)
    else:
        state.reserves.append(dec_sq)
    step = grand_illusion.GrandIllusionStep(
        game_state=state, decision_manager=DecisionManager(), game_log=tk.Log(),
        auto_players=())
    return step, state, dec_sq, warriors


c.eq("the ability is on the datasheet",
     grand_illusion.has_grand_illusion(build(DECEIVER)), True)
c.eq("...and on none of its siblings",
     [grand_illusion.has_grand_illusion(build(s)) for s in (NIGHTBRINGER, TRANSCENDENT, VOID_DRAGON)],
     [False, False, False])

step, state, dec_sq, warriors = illusion_scene(deceiver_on_board=True)
c.true("a Deceiver on the board grants it", step.grants("Player 2"))
c.true("...and not to the other player", not step.grants("Player 1"))

# THE CLAUSE A COPY OF ITS T'AU TWIN WOULD LOSE. "If your army INCLUDES this
# model" is not "if this unit is on the battlefield" - the other redeploy
# ability in this engine (Prince of Corsairs) says the second, and its own
# docstring records that the reserve case is the one that quietly keeps
# working. Here the reserve case is CORRECT.
step, state, dec_sq, warriors = illusion_scene(deceiver_on_board=False)
c.true("a Deceiver in Strategic Reserves is not on the board",
       all(m not in state.tokens for m in dec_sq.models))
c.true("...and STILL grants Grand Illusion", step.grants("Player 2"))

# Three units, two destinations, the two-step board pick.
step, state, dec_sq, warriors = illusion_scene()
c.eq("up to three", step.remaining("Player 2"), 3)
c.eq("the maximum is the printed three", post_deployment_redeploy.MAX_UNITS, 3)
c.true("a NECRONS unit is an eligible target",
       warriors in step.eligible_targets("Player 2"))
c.true("...and the faction test is the datasheet's keyword",
       awakened_dynasty.is_necrons_unit(warriors))
# "three NECRONS units" is a real filter, so something that is NOT one has to
# be refused - and with an all-Necron board that clause can never be measured.
_ORK_BOYZ = __import__("game.factions.orks", fromlist=["x"]).ORKS.datasheets["Boyz"]
allies = place(tk.build(_ORK_BOYZ, "Player 2", name="2 Boyz 9"), 12.0, 14.0)
state.tokens += list(allies.models)
c.true("a non-NECRONS unit of the same player is refused",
       allies not in step.eligible_targets("Player 2"))
c.true("...while the NECRONS one beside it is still offered",
       warriors in step.eligible_targets("Player 2"))

pregame = _Pregame(["Player 2"])
c.true("the step takes over when there is something to ask",
       step.start(pregame, on_done=lambda: None))
opts = step.decision_manager.options
c.true("...with one option per unit plus a way out", len(opts) >= 2)
c.true("...and every unit option is TAGGED, so it is a board click",
       any(o.get("squad") is not None for o in opts))

# Answering "into Strategic Reserves" really moves the unit.
step, state, dec_sq, warriors = illusion_scene()
pregame = _Pregame(["Player 2"])
step.start(pregame, on_done=lambda: None)
step.choose("Player 2", warriors, post_deployment_redeploy.RESERVES)
step.decline("Player 2")
c.true("the redeployed unit left the board",
       all(m not in state.tokens for m in warriors.models))
c.true("...and is in Strategic Reserves", warriors in state.reserves)

# An owner that answers its own prompts declines outright - the same decision
# both of its siblings record, and for the same reason.
step, state, dec_sq, warriors = illusion_scene()
step.auto_players = ("Player 2",)
pregame = _Pregame(["Player 2"])
c.true("the AI does not redeploy", not step.start(pregame, on_done=lambda: None))
c.true("...and nothing moved", all(m in state.tokens for m in warriors.models))


# --- 6. Transdimensional Displacement ----------------------------------------
print("--- 6. Transdimensional Displacement ---")


def move_scene(sheet=TRANSCENDENT, enemy_at=None):
    state = GameState()
    tt = TurnTracker()
    tt.phase_index = [PHASE_MOVEMENT].index(PHASE_MOVEMENT)
    while tt.phase != PHASE_MOVEMENT:
        tt.advance_phase()
    tt.turn_owner = "Player 2"
    tt.set_active("Player 2")
    squad = place(build(sheet, owner="Player 2"), 20.0, 20.0)
    state.tokens = list(squad.models)
    enemy = None
    if enemy_at is not None:
        enemy = place(build(WARRIORS, owner="Player 1"), *enemy_at)
        state.tokens += list(enemy.models)
    mc = MovementController(obstacles=[], game_log=tk.Log(), player_name="Player 2",
                            dice_manager=DiceManager(), turn_tracker=tt,
                            all_tokens=state.tokens)
    mc.select(squad.models[0])
    mc.start_move()
    return mc, squad, enemy, state


c.eq("the ability is on the datasheet",
     transdimensional_displacement.has_ability(build(TRANSCENDENT)), True)
c.eq("...and on none of its siblings",
     [transdimensional_displacement.has_ability(build(s))
      for s in (NIGHTBRINGER, DECEIVER, VOID_DRAGON)], [False, False, False])
c.eq("the printed 8\"", transdimensional_displacement.TRANSDIMENSIONAL_MIN_ENEMY_DISTANCE_IN, 8.0)

mc, squad, _enemy, _state = move_scene()
c.true("it is offered when an Advance is legal", mc.can_transdimensional_displacement())
mc2, squad2, _e, _s = move_scene(sheet=NIGHTBRINGER)
c.true("...and not to a C'tan without it", not mc2.can_transdimensional_displacement())

# CLAUSE 1: no maximum distance. Measured against the ORDINARY Advance on the
# same chassis, so the assertion is about the ability rather than about a
# number that happens to be large.
mc, squad, _e, _s = move_scene()
plain_budget = mc.remaining_range[squad.models[0].id]
c.true("an ordinary Advance would be at most M + 6", plain_budget <= squad.models[0].profile.movement_in)
mc.start_transdimensional_displacement()
c.true("the displacement budget is far beyond any Advance",
       mc.remaining_range[squad.models[0].id] > plain_budget + 50)
c.true("...and no die was thrown for it", not mc.dice_manager.pending_values)
c.true("...but it still counts as this unit's Advance",
       mc.run_used and squad in mc.advance_bonus_by_squad)
c.true("...so a second one is not offered", not mc.can_transdimensional_displacement())

# CLAUSE 2: through all types of model - but NOT through terrain. Both halves,
# because a copy that reached for the FLY branch instead would pass the first
# and fail the second.
mc, squad, _e, _s = move_scene()
c.true("the models-only bypass is off before it is declared", not mc.displacing_this_move)
mc.start_transdimensional_displacement()
c.true("...and on afterwards", mc.displacing_this_move)
c.true("the bypass is asked per MODEL",
       transdimensional_displacement.model_has_ability(squad.models[0]))

# MEASURED THROUGH clamp_move(), not read out of the source. An enemy unit
# sits squarely between the C'tan and where it wants to go, and both runs ask
# for the SAME 6" - well inside an ordinary Advance - so the only thing the
# comparison can be about is the bypass.
def reach_through_enemy(displace):
    mc, squad, enemy, _s = move_scene(enemy_at=(20.0, 24.0))
    if displace:
        mc.start_transdimensional_displacement()
    else:
        script(6)
        mc.start_run()
        mc.dice_manager.acknowledge()
    token = squad.models[0]
    return mc.clamp_move(token, 20.0, 26.0)[1]


blocked = reach_through_enemy(displace=False)
through = reach_through_enemy(displace=True)
c.true("an ordinary Advance is stopped by the enemy base in the way", blocked < 23.0)
c.true("...and the displacement walks straight through it", through >= 25.9)

# But TERRAIN is not models: the printed text says "all types of MODEL" and
# says nothing about terrain features, so this is not the FLY branch.
src = io.open(os.path.join("game", "movement.py"), encoding="utf-8").read()
fly = src[src.index("if self.flying_this_move and token.profile.fly:"):]
c.true("...and it is NOT the FLY branch, which also ignores terrain",
       "transdimensional_displacement" not in fly[:fly.index("else:")])

# CLAUSE 3: more than 8" from every enemy unit, at CONFIRM.
mc, squad, enemy, _s = move_scene(enemy_at=(20.0, 24.0))
mc.start_transdimensional_displacement()
mc.confirm_move()
c.true("ending 4\" from an enemy unit is refused", bool(mc.errors))
c.true("...and the message names the ability, not a Scout move",
       any("Transdimensional Displacement" in e for e in mc.errors))
mc, squad, enemy, _s = move_scene(enemy_at=(20.0, 40.0))
mc.start_transdimensional_displacement()
mc.confirm_move()
c.eq("...while 20\" away is fine", mc.errors, [])

# The ordinary Advance on the same model is untouched by any of it.
mc, squad, _e, _s = move_scene()
script(4)
mc.start_run()
c.true("a plain Advance still rolls its D6", bool(mc.dice_manager.pending_values))
c.true("...and does not turn the bypass on", not mc.displacing_this_move)


# --- 7. the three extractions ------------------------------------------------
print("--- 7. the extractions ---")

# (a) post_deployment_redeploy: the T'au carrier must be BEHAVIOUR-UNCHANGED.
# That is the load-bearing half of an extraction - the new carrier working
# proves nothing about the one that was already shipped.
c.true("Solid-image Projection is now a subclass",
       issubclass(SolidImageProjectionStep, post_deployment_redeploy.PostDeploymentRedeployStep))
c.true("Grand Illusion is the second carrier",
       issubclass(grand_illusion.GrandIllusionStep,
                  post_deployment_redeploy.PostDeploymentRedeployStep))
c.eq("...and the two answer with their own printed faction",
     (SolidImageProjectionStep().label, grand_illusion.GrandIllusionStep().label),
     ("Solid-image Projection Unit", "Grand Illusion"))
import game.enh_solid_image_projection as _sip
c.eq("the T'au module still re-exports its three constants",
     (_sip.MAX_UNITS, _sip.REDEPLOY, _sip.RESERVES), (3, "redeploy", "reserves"))

# (b) mortal_wound_sweep: Drain Life is a subclass of the shared machine, and
# the machine is a subclass of the ONE-target base whose 06.02 plumbing it
# reuses rather than copies.
from game.mortal_wound_abilities import MortalWoundOfferController
c.true("Drain Life is a sweep",
       issubclass(drain_life.DrainLifeController,
                  mortal_wound_sweep.MortalWoundSweepController))
c.true("...and the sweep reuses the one-target base's 06.02 plumbing",
       issubclass(mortal_wound_sweep.MortalWoundSweepController, MortalWoundOfferController))
c.true("...rather than writing its own",
       "pending_damage_choice" not in io.open(
           os.path.join("game", "mortal_wound_sweep.py"), encoding="utf-8").read()
       .split("def _check_session_done")[0].split("class MortalWoundSweepController")[1])

# (c) Squad.check_min_enemy_distance: the Scout wrapper must answer EXACTLY as
# it did, since rule 24.32 is what it was written for.
victim = place(build(WARRIORS, owner="Player 2"), 20.0, 20.0)
foe = place(build(IMMORTALS, owner="Player 1"), 20.0, 24.0)
toks = list(victim.models) + list(foe.models)
c.true("the Scout wrapper still refuses at 4\"", bool(victim.check_scout_move_clearance(toks)))
c.true("...and says Scout move", "Scout move" in victim.check_scout_move_clearance(toks)[0])
c.true("...while the general form can say something else",
       "Displacement" in victim.check_min_enemy_distance(toks, 8.0, "a Displacement", "x")[0])
c.eq("...and a shorter distance lets the same board through",
     victim.check_min_enemy_distance(toks, 1.0, "a Displacement", "x"), [])


# --- 8. wiring, the AI, sprites, dormancy ------------------------------------
print("--- 8. wiring, AI, sprites, dormancy ---")

MAIN = io.open("main.py", encoding="utf-8").read()
_TREE = ast.parse(MAIN)
_LINES = MAIN.split("\n")
MAIN_CALLS = []
for node in ast.walk(_TREE):
    if isinstance(node, ast.Call):
        seg = "\n".join(_LINES[node.lineno - 1:node.end_lineno])
        MAIN_CALLS.append(" ".join(seg.split()))


def calls_in_main(needle):
    return [ca for ca in MAIN_CALLS if needle in ca]


for needle, why in [
    ("DrainLifeController(", "the controller is constructed"),
    ("drain_life_controller.resolve_end_of_fight_phase(",
     "...and fired at the end of the Fight phase"),
    ("drain_life_controller.on_dice_acknowledged()", "...and its dice are acknowledged"),
    ("drain_life_controller.choose_damage_model(", "...and its allocation is clickable"),
    ("GrandIllusionStep(", "the Grand Illusion step is constructed"),
]:
    c.true(why, bool(calls_in_main(needle)))
c.true("Drain Life is in the shared damage-pick list",
       "drain_life_controller," in MAIN)
c.true("...and its allocation is drawn",
       bool(calls_in_main("draw_damage_choice_highlight(board_surface, board, drain_life_controller")))
c.true("Grand Illusion joins the redeploy chain",
       bool(calls_in_main("_RedeployChain( _solid_image_step, prince_of_corsairs_step, grand_illusion_step)")))
# CONSTRUCTION ORDER (error class 23): main() is one long function and no suite
# runs it, so the only place this can be checked is the source.
c.true("...and the step is built before the chain that holds it",
       MAIN.find("grand_illusion_step = GrandIllusionStep(")
       < MAIN.find("pregame_controller.redeploy_step = _RedeployChain("))
c.true("the Drain Life controller is built before the phase hook reads it",
       MAIN.find("drain_life_controller = DrainLifeController(")
       < MAIN.find("drain_life_controller.resolve_end_of_fight_phase("))
# THE PANEL HAS TO DRAW IT. A source grep for the callback survives an
# `if False:` in front of the branch - the structural hole both stratagem
# audits found - so the real panel is rendered and its own button list read.
def panel_labels(sheet):
    mc, squad, _e, _s = move_scene(sheet=sheet)
    panel = ActionPanel()
    surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 640))
    panel._buttons = []
    panel._mouse_pos = (-1, -1)
    panel._mouse_down = False
    seen = []
    real = ActionPanel._draw_button

    def spy(self, surf, r, label, accent=None):
        seen.append(label)
        return real(self, surf, r, label, accent=accent)

    ActionPanel._draw_button = spy
    try:
        panel._draw_movement_ui(
            surface, pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 640),
            config.LEFT_PANEL_WIDTH - 20, mc, None)
    finally:
        ActionPanel._draw_button = real
    return seen, mc


labels, _mc = panel_labels(TRANSCENDENT)
c.true("the panel really draws the button", "Transdimensional Displacement" in labels)
c.true("...beside the ordinary Advance, not instead of it", "Advance" in labels)
c.true("...and the render reached the movement screen at all", len(labels) >= 2)
labels_other, _mc = panel_labels(NIGHTBRINGER)
c.true("a C'tan without the ability is offered only the ordinary Advance",
       "Transdimensional Displacement" not in labels_other and "Advance" in labels_other)

# THE AI NEGATIVE SPACE. Standing instruction for this backfill: no
# ai/agent_driver.py judgements. Asserted on the FULL datasheet and module
# names - the substring "C'tan" is already in that file three times, in
# pre-existing comments about charge geometry, and would report a false hit.
DRIVER = io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read()
c.true("the false-positive this sweep has to avoid really is there",
       DRIVER.count("C'tan") >= 1)
for name in ["C'tan Shard of the Nightbringer", "C'tan Shard of the Deceiver",
             "Transcendent C'tan", "drain_life", "grand_illusion",
             "transdimensional_displacement", "mortal_wound_sweep",
             "post_deployment_redeploy"]:
    c.eq("ai/agent_driver.py knows nothing about %s" % name, name in DRIVER, False)

# auto_players is taken at the OBJECT, not merely accepted as a keyword.
c.true("Drain Life gates on auto_players at the object",
       "Player 2" in drain_life.DrainLifeController(auto_players=("Player 2",)).auto_players)
c.true("...and so does the Grand Illusion step",
       "Player 2" in grand_illusion.GrandIllusionStep(auto_players=("Player 2",)).auto_players)

for sheet in NEW:
    c.true("%s draws its own art" % sheet.name,
           sprites.sprite_for(build(sheet, n=40).models[0]) is not None)

# SPRITE SHADOWING, measured in both directions - _key_for_name() returns the
# FIRST key that is a substring of the squad name.
_keys = list(sprites.SQUAD_SPRITE_KEYS)
for _new in [s.name for s in NEW]:
    c.eq("no existing key swallows %r" % _new,
         [k for k in _keys if k != _new and k in _new], [])
    c.eq("...and it swallows none", [k for k in _keys if k != _new and _new in k], [])

_roster = io.open(os.path.join("armies", "necrons.json"), encoding="utf-8").read()
for sheet in NEW:
    c.true("%s is dormant by roster" % sheet.name, sheet.name not in _roster)

c.finish()
