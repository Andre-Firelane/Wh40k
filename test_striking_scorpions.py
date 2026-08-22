"""Striking Scorpions (Aeldari) - the first Aspect Warriors datasheet, the
first two-size unit in this faction, and the first Aeldari unit whose core
abilities were all already implemented.

Two abilities are deliberately absent (Mandiblasters, Aspect Shrine token) -
only paraphrases of them were available, so nothing here asserts them. What IS
asserted is that they are absent, so adding them later cannot go unnoticed.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from collections import Counter

from game import battle_focus, sprites
from game.factions.aeldari import (
    EXARCH_TO_BITING_BLADE,
    EXARCH_TO_CHAINSABRES,
    STORM_GUARDIANS,
    STRIKING_SCORPIONS,
)
from game.squad import squad_has_infiltrators, squad_has_stealth
from game.units import StrikingScorpionExarchProfile, StrikingScorpionProfile
from game.weapons import MELEE, RANGED
from testkit import Checks, Log, build

checks = Checks("Striking Scorpions")

NAME = "1 Striking Scorpions 1"


def scorpions(size=0, choices=None, name=NAME):
    return build(STRIKING_SCORPIONS, "Player 1", name=name,
                 composition_index=size, choices=choices)


def weapons_of(squad):
    return Counter(w.name for m in squad.models for w in m.weapons)


# ------------------------------------------------------- 1. the datasheet

print("--- 1. datasheet ---")

small, big = scorpions(0), scorpions(1)
checks.eq("the 5-model build", len(small.models), 5)
checks.eq("costs 75", small.points, 75)
checks.eq("the 10-model build", len(big.models), 10)
checks.eq("costs 145", big.points, 145)
checks.eq("each build is 1 Exarch plus the rest",
          [sorted(Counter(m.profile.name for m in s.models).items()) for s in (small, big)],
          [[("Striking Scorpion", 4), ("Striking Scorpion Exarch", 1)],
           [("Striking Scorpion", 9), ("Striking Scorpion Exarch", 1)]])
for keyword in ("INFANTRY", "ASPECT WARRIORS", "STRIKING SCORPIONS"):
    checks.true(f"keyword {keyword}", keyword in STRIKING_SCORPIONS.keywords)

s, e = StrikingScorpionProfile, StrikingScorpionExarchProfile
checks.eq("Scorpion statline M/T/Sv/W/Ld/OC",
          (s.movement_in, s.toughness, s.armor_save, s.wounds, s.leadership, s.oc),
          (7, 3, "3+", 1, "6+", 1))
checks.eq("the Exarch differs only in wounds",
          (e.movement_in, e.toughness, e.armor_save, e.wounds, e.leadership, e.oc),
          (7, 3, "3+", 2, "6+", 1))
checks.true("and it is marked as the squad leader", e.squad_leader)
checks.eq("28.5mm base, like every Aeldari infantry model so far",
          s.base_radius_in, round(28.5 / 2 / 25.4, 3))
# Aspect Warriors are better armoured and steadier than Guardians - the numbers
# that actually differ, pinned so a copy-paste from the Guardian profile fails.
from game.units import GuardianDefenderProfile as _guardian
checks.eq("better save than a Guardian", (s.armor_save, _guardian.armor_save), ("3+", "4+"))
checks.eq("better leadership", (s.leadership, _guardian.leadership), ("6+", "7+"))
checks.eq("lower objective control", (s.oc, _guardian.oc), (1, 2))


# ---------------------------------------------------------- 2. the weapons

print("--- 2. weapons ---")

exarch = small.models[0]
trooper = small.models[1]
checks.eq("the Exarch's printed loadout is three weapons",
          sorted(w.name for w in exarch.weapons),
          ["Scorpion Chainsword", "Scorpion's Claw", "Shuriken Pistol"])
checks.eq("a trooper carries two",
          sorted(w.name for w in trooper.weapons),
          ["Scorpion Chainsword", "Shuriken Pistol"])

sword = next(w for w in trooper.weapons if w.name == "Scorpion Chainsword")
checks.eq("Scorpion Chainsword A/S/AP/D",
          (sword.attacks, sword.strength, sword.ap, sword.damage), (4, 4, -1, 1))
checks.eq("with [SUSTAINED HITS 1]", sword.sustained_hits, 1)

claw = next(w for w in exarch.weapons if w.name == "Scorpion's Claw")
checks.eq("Scorpion's Claw A/S/AP/D",
          (claw.attacks, claw.strength, claw.ap, claw.damage), (3, 8, -2, 2))
checks.eq("and no keywords", (claw.sustained_hits, claw.twin_linked), (0, False))

# The Shuriken Pistol is the one already built for Storm Guardians - the same
# printed row, so it is shared rather than duplicated.
pistol = next(w for w in trooper.weapons if w.name == "Shuriken Pistol")
checks.eq("Shuriken Pistol range/A/S/AP/D",
          (pistol.range_in, pistol.attacks, pistol.strength, pistol.ap, pistol.damage),
          (12, 1, 4, -1, 1))
checks.true("with [ASSAULT] and [PISTOL]", pistol.assault and pistol.pistol)


# --------------------------------------------- 3. the Exarch's two options

print("--- 3. Exarch wargear ---")

blade = scorpions(choices={"Striking Scorpion Exarch": {EXARCH_TO_BITING_BLADE: 1}})
checks.eq("Biting Blade option gives up all three printed weapons",
          sorted(w.name for w in blade.models[0].weapons),
          ["Biting Blade", "Shuriken Pistol"])
bb = next(w for w in blade.models[0].weapons if w.name == "Biting Blade")
checks.eq("Biting Blade A/S/AP/D", (bb.attacks, bb.strength, bb.ap, bb.damage), (4, 6, -3, 1))
checks.eq("with [SUSTAINED HITS 1]", bb.sustained_hits, 1)

sabres = scorpions(choices={"Striking Scorpion Exarch": {EXARCH_TO_CHAINSABRES: 1}})
sabre_weapons = [w for w in sabres.models[0].weapons if w.name == "Chainsabres"]
checks.eq("Chainsabres is ONE name with two profiles - a ranged and a melee row",
          sorted(w.weapon_type for w in sabre_weapons), sorted([MELEE, RANGED]))
ranged = next(w for w in sabre_weapons if w.weapon_type == RANGED)
melee = next(w for w in sabre_weapons if w.weapon_type == MELEE)
checks.eq("its ranged row matches a shuriken pistol plus [TWIN-LINKED]",
          (ranged.range_in, ranged.attacks, ranged.strength, ranged.ap, ranged.twin_linked),
          (12, 1, 4, -1, True))
checks.eq("its melee row is A5/S4/AP-1/D1",
          (melee.attacks, melee.strength, melee.ap, melee.damage), (5, 4, -1, 1))
checks.true("with [SUSTAINED HITS 1] and [TWIN-LINKED]",
            melee.sustained_hits == 1 and melee.twin_linked)
checks.eq("nothing of the printed loadout survives the swap",
          [w.name for w in sabres.models[0].weapons if w.name != "Chainsabres"], [])

# "One of the following" needs no code: the Exarch line holds a single model, so
# a second option finds nobody left to claim and is trimmed like any over-eager
# choice. This depends on the swap-collision fix - before it, both options
# started at model 0 and the Exarch would have ended up with everything.
both = scorpions(choices={"Striking Scorpion Exarch": {
    EXARCH_TO_BITING_BLADE: 1, EXARCH_TO_CHAINSABRES: 1}})
checks.eq("choosing both applies only the first - they are mutually exclusive",
          sorted(w.name for w in both.models[0].weapons),
          ["Biting Blade", "Shuriken Pistol"])
checks.eq("the troopers are untouched by an Exarch-only option",
          sorted(w.name for w in both.models[1].weapons),
          ["Scorpion Chainsword", "Shuriken Pistol"])

over = scorpions(1, choices={"Striking Scorpion Exarch": {EXARCH_TO_CHAINSABRES: 5}})
checks.eq("and an over-eager count is trimmed to the single Exarch",
          weapons_of(over)["Chainsabres"], 2)  # one ranged + one melee row on one model


# --------------------------------------------------------- 4. the abilities

print("--- 4. abilities ---")

checks.true("STEALTH (24.33) - already implemented, so only the flag was needed",
            squad_has_stealth(small))
checks.true("INFILTRATORS (24.20)", squad_has_infiltrators(small))
checks.eq("SCOUTS 7 inches (24.31/24.32)",
          {m.profile.scouts for m in small.models}, {7})
checks.true("and the army rule reaches it", battle_focus.has_battle_focus(small))
checks.eq("no Fleet of Foot, so Fade Back is not free",
          battle_focus.BattleFocusPool(players=("Player 1",), game_log=Log())
          .is_free(battle_focus.FADE_BACK, small), False)

# Stealth is what it is because game/shooting.py reads it as "unconditionally
# has the benefit of cover" - asserted through the shooting controller rather
# than through the flag, since the flag alone proves nothing.
from game.shooting import ShootingController
from testkit import DecisionManager, DiceManager, GameState
state = GameState()
for model in small.models:
    state.add_token(model)
sc = ShootingController(all_tokens=state.tokens, dice_manager=DiceManager(),
                        decision_manager=DecisionManager(), player_name="Player 2",
                        obstacles=[])
checks.true("the engine grants it cover with no terrain anywhere near",
            sc._compute_benefit_of_cover(small.models[0], small))

text = " ".join(STRIKING_SCORPIONS.abilities_text)
# The Aspect Shrine token used to be asserted as NOT IMPLEMENTED here, so that
# adding it would be a visible change. It has been (see game/aspect_shrine.py
# and test_aspect_shrine.py), so the assertion flipped rather than vanished.
checks.eq("the Aspect Shrine token is no longer recorded as missing",
          "NOT IMPLEMENTED" in text, False)
checks.eq("and the unit really holds one per 5 models",
          small.aspect_shrine_tokens, 1)
checks.eq("Mandiblasters is no longer recorded as missing",
          "Mandiblasters: NOT IMPLEMENTED" in text, False)


# -------------------------------------------------------- 4b. Mandiblasters

print("--- 4b. Mandiblasters ---")

# game/melee_crit.py became game/crit_hit.py when Lhykhis' Whispering Web
# needed the same threshold from the SHOOTING hit step - so the two
# melee-worded sources are now gated behind melee_only=True, which is what
# these checks have to pass.
from game import crit_hit

mand = scorpions()
trooper_m = mand.models[1]
checks.eq("before charging, melee crits need rule 05.02's 6",
          crit_hit.crit_hit_threshold(trooper_m, melee_only=True), 6)
mand.charged_this_turn = True
checks.eq("after a Charge move, an unmodified 5 is a Critical Hit",
          crit_hit.crit_hit_threshold(trooper_m, melee_only=True), 5)
checks.eq("the Exarch inherits the ability",
          crit_hit.crit_hit_threshold(mand.models[0], melee_only=True), 5)

# The pitfall this deliberately avoids: Squad.fights_first looks like the right
# "charged this turn" marker and is not - game/counteroffensive.py (15.12) sets
# it too, so a unit that never charged would have got the ability for free.
mand.charged_this_turn = False
mand.fights_first = True
checks.eq("fights_first alone does NOT trigger it", crit_hit.crit_hit_threshold(trooper_m, melee_only=True), 6)
mand.fights_first = False

no_ability = build(STORM_GUARDIANS, "Player 1", name="1 Storm Guardians 5")
no_ability.charged_this_turn = True
checks.eq("a unit without the ability is unaffected even after charging",
          crit_hit.crit_hit_threshold(no_ability.models[1], melee_only=True), 6)

# Wiring: game/fight.py's hit step must read the FOLDED function, not the old
# Ork-only one. Asserted by identity rather than by driving a whole fight here -
# the end-to-end path through the real hit resolution is already covered by
# test_unbridled_carnage.py, and both sources now go through this same hook, so
# proving fight.py holds this exact function proves the path.
import game.fight as _fight
checks.true("fight.py reads the folded melee crit threshold",
            _fight.crit_hit_threshold is crit_hit.crit_hit_threshold)
checks.eq("and the old module no longer defines its own copy",
          hasattr(__import__("game.unbridled_carnage", fromlist=["x"]),
                  "crit_hit_threshold"), False)


# ------------------------------------------------------------ 5. sprites

print("--- 5. sprites ---")

art = [os.path.basename(x) for x in sprites.portrait_paths(small, 4)]
checks.eq("one image for the whole unit - the Exarch has no art of its own",
          art, ["Striking Scorpion.png"])
checks.eq("and the Exarch uses it too",
          os.path.basename(sprites.sprite_for(exarch)), "Striking Scorpion.png")


# ---------------------------------------------------------- 6. A/B probe

print("--- 6. A/B probe ---")

saved = StrikingScorpionProfile.stealth
for cls in (StrikingScorpionProfile, StrikingScorpionExarchProfile):
    cls.stealth = False
probe = scorpions()
checks.eq("A/B: without the STEALTH flag the unit gets no free cover",
          sc._compute_benefit_of_cover(probe.models[0], probe), False)
for cls in (StrikingScorpionProfile, StrikingScorpionExarchProfile):
    cls.stealth = saved
checks.true("A/B: and it comes back when restored", squad_has_stealth(scorpions()))

checks.finish()
