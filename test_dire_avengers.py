"""Dire Avengers: datasheet data, Bladestorm, and the Shimmershield.

Two things get depth here because they are the new mechanics:

- Bladestorm is asserted through the REAL shooting resolution on identical
  scripted dice at two ranges, not by inspecting the flag - a granted
  [SUSTAINED HITS] that nothing reads would pass a flag check happily.
- The Shimmershield is the first wargear in this engine whose printed
  precondition is "another option was taken", so both halves are checked: it
  works after the swap that grants the pistol, and does nothing without it.
"""

import testkit as tk
from testkit import Checks, script

from game.factions import aeldari as ae
from game.bladestorm import BLADESTORM_SUSTAINED_HITS, squad_has_bladestorm
from game.invulnerable_save import effective_invulnerable_save
from game.sprites import _squad_key
from game.weapons import MELEE, RANGED

checks = Checks("Dire Avengers")
NAME = "1 Dire Avengers 1"
EXARCH_LINE = "Dire Avenger Exarch"


def avengers(composition_index=0, choices=None, gear=None, owner="Player 1"):
    return tk.build(ae.DIRE_AVENGERS, owner, name=NAME,
                    composition_index=composition_index, choices=choices, gear=gear)


def weapon_names(model):
    return sorted(w.name for w in model.weapons)


# --- 1. composition, statline, points --------------------------------------
print("--- 1. composition, statline, points ---")

small, big = avengers(0), avengers(1)
checks.eq("5-model unit", len(small.models), 5)
checks.eq("10-model unit", len(big.models), 10)
checks.eq("5 models cost 75", small.points, 75)
checks.eq("10 models cost 150", big.points, 150)
# Unlike Warp Spiders, this entry is not tiered by how many copies are fielded.
checks.eq("no army-copy tier", ae.DIRE_AVENGERS.points_for(1, unit_index=4), 150)

trooper = next(m for m in small.models if m.profile.name == "Dire Avenger")
exarch = next(m for m in small.models if m.profile.name == EXARCH_LINE)
checks.eq("M7\"", trooper.profile.movement_in, 7)
checks.eq("T3", trooper.profile.toughness, 3)
checks.eq("Sv4+", trooper.profile.armor_save, "4+")
checks.eq("W1 / Exarch W2", (trooper.profile.wounds, exarch.profile.wounds), (1, 2))
checks.eq("Ld6+", trooper.profile.leadership, "6+")
checks.eq("OC1", trooper.profile.oc, 1)
checks.eq("5+ invulnerable", trooper.profile.invulnerable_save, "5+")
checks.eq("28.5 mm base", round(trooper.profile.base_radius_in, 3), round(28.5 / 2 / 25.4, 3))
checks.true("INFANTRY", trooper.profile.infantry)
checks.true("Battle Focus", trooper.profile.battle_focus)
checks.true("Bladestorm", trooper.profile.bladestorm)
checks.true("the Exarch inherits Bladestorm", exarch.profile.bladestorm)
checks.eq("no Fleet of Foot", getattr(trooper.profile, "fleet_of_foot", False), False)
# No conditional melee improvement here, unlike Howling Banshees.
checks.eq("no melee-only invulnerable clause",
          getattr(trooper.profile, "invulnerable_save_vs_melee", None), None)
for kw in ("INFANTRY", "GRENADES", "ASPECT WARRIORS", "DIRE AVENGERS"):
    checks.true(f"keyword {kw}", kw in ae.DIRE_AVENGERS.keywords)


# --- 2. weapons ------------------------------------------------------------
print("--- 2. weapons ---")

checks.eq("every model has the same default loadout",
          weapon_names(trooper), ["Avenger Shuriken Catapult", "Close Combat Weapon"])
checks.eq("the Exarch's default is the same", weapon_names(exarch), weapon_names(trooper))

catapult = next(w for w in trooper.weapons if w.name == "Avenger Shuriken Catapult")
checks.eq("Avenger Shuriken Catapult 18\"/A4/S4/AP-1/D1",
          (catapult.range_in, catapult.attacks, catapult.strength, catapult.ap, catapult.damage),
          (18, 4, 4, -1, 1))
checks.true("[ASSAULT]", catapult.assault)
checks.eq("no [SUSTAINED HITS] printed on the weapon itself", catapult.sustained_hits, 0)
# Distinct from the Guardian Defenders' 18"/A2 row, which is why it is its own
# class rather than a reuse.
from game.weapons import ShurikenCatapultProfile  # noqa: E402
checks.eq("the plain Shuriken Catapult is A2, this one A4",
          (ShurikenCatapultProfile.attacks, catapult.attacks), (2, 4))

ccw = next(w for w in trooper.weapons if w.weapon_type == MELEE)
checks.eq("Close Combat Weapon is the A2/S3 Aeldari row",
          (ccw.attacks, ccw.strength, ccw.ap, ccw.damage), (2, 3, 0, 1))


# --- 3. Exarch wargear -----------------------------------------------------
print("--- 3. Exarch wargear ---")

for option, expected in (
    (ae.DIRE_AVENGER_TO_DIRESWORD, ["Close Combat Weapon", "Diresword", "Shuriken Pistol"]),
    (ae.DIRE_AVENGER_TO_POWER_GLAIVE, ["Close Combat Weapon", "Power Glaive", "Shuriken Pistol"]),
    (ae.DIRE_AVENGER_SECOND_CATAPULT,
     ["Avenger Shuriken Catapult", "Avenger Shuriken Catapult", "Close Combat Weapon"]),
):
    sq = avengers(choices={EXARCH_LINE: {option: 1}})
    checks.eq(f"{option}", weapon_names(sq.models[0]), expected)

sq = avengers(choices={EXARCH_LINE: {ae.DIRE_AVENGER_TO_DIRESWORD: 1}})
sword = next(w for w in sq.models[0].weapons if w.name == "Diresword")
checks.eq("Diresword A4/S4/AP-2", (sword.attacks, sword.strength, sword.ap), (4, 4, -2))
sq = avengers(choices={EXARCH_LINE: {ae.DIRE_AVENGER_TO_POWER_GLAIVE: 1}})
glaive = next(w for w in sq.models[0].weapons if w.name == "Power Glaive")
checks.eq("Power Glaive A3/S5/AP-3", (glaive.attacks, glaive.strength, glaive.ap), (3, 5, -3))

# "one of the following" for the two swaps: one Exarch, so the second is trimmed.
sq = avengers(choices={EXARCH_LINE: {ae.DIRE_AVENGER_TO_DIRESWORD: 1,
                                     ae.DIRE_AVENGER_TO_POWER_GLAIVE: 1}})
checks.eq("both swaps chosen -> only the first applies",
          weapon_names(sq.models[0]), ["Close Combat Weapon", "Diresword", "Shuriken Pistol"])

# The second catapult is a pure ADDITION whose printed condition is "if the
# Exarch is still equipped with one" - taking a swap first removes it, and the
# addition then has nothing to duplicate.
sq = avengers(choices={EXARCH_LINE: {ae.DIRE_AVENGER_TO_DIRESWORD: 1,
                                     ae.DIRE_AVENGER_SECOND_CATAPULT: 1}})
checks.eq("a swap plus the second catapult does NOT re-add the catapult",
          weapon_names(sq.models[0]),
          ["Avenger Shuriken Catapult", "Close Combat Weapon", "Diresword", "Shuriken Pistol"])
checks.eq("only the Exarch is ever affected",
          weapon_names(sq.models[1]), ["Avenger Shuriken Catapult", "Close Combat Weapon"])


# --- 4. Shimmershield ------------------------------------------------------
print("--- 4. Shimmershield ---")

shielded = avengers(choices={EXARCH_LINE: {ae.DIRE_AVENGER_TO_DIRESWORD: 1}},
                    gear={EXARCH_LINE: [ae.DIRE_AVENGER_SHIMMERSHIELD]})
ex = shielded.models[0]
checks.eq("it replaces the Shuriken Pistol", weapon_names(ex), ["Close Combat Weapon", "Diresword"])
# Read through the function the Save roll asks, not the flag it was given.
checks.eq("the bearer has a 4+ invulnerable save", effective_invulnerable_save(ex), "4+")
checks.eq("its squadmates keep the printed 5+",
          effective_invulnerable_save(shielded.models[1]), "5+")

# Without the swap there is no pistol to give up, so the printed precondition
# fails and the item simply does nothing - the same trim an over-eager choice
# always gets.
bare = avengers(gear={EXARCH_LINE: [ae.DIRE_AVENGER_SHIMMERSHIELD]})
checks.eq("no swap -> the Exarch keeps its catapult",
          weapon_names(bare.models[0]), ["Avenger Shuriken Catapult", "Close Combat Weapon"])
checks.eq("no swap -> no 4+ invulnerable",
          effective_invulnerable_save(bare.models[0]), "5+")
# ...and that is the build_squad() guard doing it, not the Gear item: an
# unmet swap must not turn into a free addition either.
checks.eq("an unmet swap grants nothing at all",
          weapon_names(avengers(choices={EXARCH_LINE: {ae.DIRE_AVENGER_TO_DIRESWORD: 0}}).models[0]),
          ["Avenger Shuriken Catapult", "Close Combat Weapon"])


# --- 5. Bladestorm ---------------------------------------------------------
print("--- 5. Bladestorm ---")

checks.true("the unit has the ability", squad_has_bladestorm(small))
checks.eq("a unit without it does not",
          squad_has_bladestorm(tk.build(ae.HOWLING_BANSHEES, "Player 1",
                                        name="1 Howling Banshees 1")), False)


def hits_at(gap, faces):
    """Fire one Avenger Shuriken Catapult group at `gap` inches and report the
    hit line the engine logged. The catapult is 18", so half range is 9"."""
    sc = tk.shooting_scene(ae.DIRE_AVENGERS, ae.HOWLING_BANSHEES,
                           attacker_owner="Player 1", gap=gap)
    attacker = sc["attacker"]
    sc["shooting"].start_shooting(attacker)
    sc["shooting"].choose_target_squad(sc["target"])
    # weapon_eligibility() rows are (key, label, eligible, total, overcharge);
    # the key itself is an _attack_key tuple, so match on the LABEL.
    key = next(row[0] for row in sc["shooting"].weapon_eligibility()
               if row[1] == "Avenger Shuriken Catapult")
    script(*faces)
    sc["shooting"].choose_weapon(key)
    sc["dice"].acknowledge()
    sc["shooting"].on_dice_acknowledged()
    # Dire Avengers hold an Aspect Shrine token, and inside half range
    # Bladestorm has just given the weapon [SUSTAINED HITS] - which is exactly
    # what makes a critical hit worth buying, so the token is offered here.
    # Declined: this helper is measuring Bladestorm, not the token (which has
    # its own suite). That the offer appears at all is asserted below.
    if sc["decision"].is_pending:
        tk.pick_option(sc["decision"], "Keep the roll")
    return sc


# 5 models x A4 = 20 dice. Two natural 6s in the script, everything else a 4
# (a hit at BS3+ but not a critical), so [SUSTAINED HITS 1] is worth exactly
# two extra hits when it applies.
FACES = [6, 6] + [4] * 18


def hit_line(sc):
    return next(line for line in sc["log"].lines if "hit roll" in line)


near = hits_at(6.0, FACES)     # 6" apart - inside the 9" half range
far = hits_at(14.0, FACES)     # 14" apart - inside 18", outside half range
checks.true("within half range, [SUSTAINED HITS] fires",
            any("[SUSTAINED HITS] adds 2 extra hit(s)" in line for line in near["log"].lines))
checks.eq("beyond half range it does not",
          any("[SUSTAINED HITS]" in line for line in far["log"].lines), False)
# The same HIT dice in both (rolled[0]), so any difference downstream is the
# ability and nothing else. rolled[-1] is the WOUND roll by this point, and its
# size is the clearest end-to-end evidence there is: 20 hits become 22 wound
# dice inside half range, and stay 20 outside it.
checks.eq("identical hit dice were rolled in both",
          near["dice"].rolled[0][1], far["dice"].rolled[0][1])
checks.eq("20 hits -> 22 wound dice within half range", len(near["dice"].rolled[-1][1]), 22)
checks.eq("and only 20 beyond it", len(far["dice"].rolled[-1][1]), 20)

# The grant is a copy: the shared class-level profile must never be mutated.
from game.weapons import AvengerShurikenCatapultProfile  # noqa: E402
checks.eq("the shared class-level profile was never mutated",
          AvengerShurikenCatapultProfile.sustained_hits, 0)
checks.eq("BLADESTORM grants exactly 1", BLADESTORM_SUSTAINED_HITS, 1)

# ...and the two abilities interlock in a way worth pinning down: the token is
# only worth spending on a hit roll when a critical buys something, so at close
# range (Bladestorm active) the button is offered and beyond half range it is
# not. Read through the real UnmodifiedSixController, which is what the left
# panel draws its buttons off - and this is the case that proves the
# controller reads the ADJUSTED weapon: Bladestorm's [SUSTAINED HITS] is a
# conditional grant, so the printed profile would say "nothing to buy" in
# exactly the situation where there is.
from game.unmodified_six_controller import UnmodifiedSixController  # noqa: E402
from game import aspect_shrine  # noqa: E402

near_offer = tk.shooting_scene(ae.DIRE_AVENGERS, ae.HOWLING_BANSHEES, attacker_owner="Player 1", gap=6.0)
far_offer = tk.shooting_scene(ae.DIRE_AVENGERS, ae.HOWLING_BANSHEES, attacker_owner="Player 1", gap=14.0)
for scene, expected, label in ((near_offer, True, "within"), (far_offer, False, "beyond")):
    scene["shooting"].start_shooting(scene["attacker"])
    scene["shooting"].choose_target_squad(scene["target"])
    k = next(r[0] for r in scene["shooting"].weapon_eligibility()
             if r[1] == "Avenger Shuriken Catapult")
    script(*FACES)
    scene["shooting"].choose_weapon(k)
    ctrl = UnmodifiedSixController(scene["dice"], attack_controllers=(scene["shooting"],))
    offered = [src.__name__ for src, _sq, _m in ctrl.available_sources()]
    checks.eq(f"an all-hits roll {label} half range offers the token: {expected}",
              offered == ["game.aspect_shrine"], expected)
    # ...and it is Bladestorm's grant doing it, not something else: the gate
    # says "success" (a plain hit worth turning critical) rather than
    # "failure", because this roll has no misses at all.
    if expected:
        _sq, _m, adjusted = scene["shooting"].unmodified_six_context()
        checks.eq("...because the adjusted weapon has [SUSTAINED HITS]",
                  bool(adjusted.sustained_hits), True)
        checks.eq("...and the gate calls it a plain-success upgrade",
                  ctrl.worth_changing(adjusted), "success")
    checks.eq(f"...and nothing is asked in an overlay ({label})",
              scene["decision"].is_pending, False)

# Half range is per WEAPON, not per unit: the Exarch's 12" Shuriken Pistol
# halves to 6", not to the catapult's 9".
from game.bladestorm import bladestorm_adjusted_weapon  # noqa: E402
from game.weapons import ShurikenPistolProfile  # noqa: E402

sc = tk.shooting_scene(ae.DIRE_AVENGERS, ae.HOWLING_BANSHEES, attacker_owner="Player 1", gap=8.0)
shooter = sc["attacker"].models[0]
pistol = ShurikenPistolProfile()
cat = next(w for w in shooter.weapons if w.name == "Avenger Shuriken Catapult")
checks.eq("at 8\" the 18\" catapult IS inside its half range",
          bladestorm_adjusted_weapon(cat, [(shooter, cat)], sc["target"]).sustained_hits, 1)
checks.eq("at the same 8\" a 12\" pistol is NOT",
          bladestorm_adjusted_weapon(pistol, [(shooter, pistol)], sc["target"]).sustained_hits, 0)
# Ranged only, exactly as printed.
melee = next(w for w in shooter.weapons if w.weapon_type == MELEE)
checks.eq("melee weapons are never granted it",
          bladestorm_adjusted_weapon(melee, [(shooter, melee)], sc["target"]).sustained_hits, 0)


# --- 6. sprites ------------------------------------------------------------
print("--- 6. sprites ---")

for model in (trooper, exarch):
    checks.eq(f"{model.profile.name} art", _squad_key(model), "Dire Avengers")


# --- 7. A/B probes ---------------------------------------------------------
print("--- 7. A/B probes ---")

import game.bladestorm as bs  # noqa: E402
import game.shooting as shooting_mod  # noqa: E402

original = shooting_mod.bladestorm_adjusted_weapon
shooting_mod.bladestorm_adjusted_weapon = lambda weapon, pairs, target: weapon
probe = hits_at(6.0, FACES)
checks.eq("A/B: unwired, the close-range shot gets no extra hits",
          any("[SUSTAINED HITS]" in line for line in probe["log"].lines), False)
shooting_mod.bladestorm_adjusted_weapon = original
probe2 = hits_at(6.0, FACES)
checks.true("A/B: restored",
            any("[SUSTAINED HITS] adds 2 extra hit(s)" in line for line in probe2["log"].lines))

import game.invulnerable_save as inv_mod  # noqa: E402

saved = inv_mod.SHIMMERSHIELD_INVULNERABLE_SAVE
inv_mod.SHIMMERSHIELD_INVULNERABLE_SAVE = None
checks.eq("A/B: without the grant the bearer is back to 5+",
          effective_invulnerable_save(shielded.models[0]), "5+")
inv_mod.SHIMMERSHIELD_INVULNERABLE_SAVE = saved
checks.eq("A/B: restored", effective_invulnerable_save(shielded.models[0]), "4+")

print("--- the Exarch is marked as the squad leader ---")
import testkit as _tk_leader  # noqa: E402
from game.factions.aeldari import DIRE_AVENGERS as _sheet_for_leader  # noqa: E402
from game.units import DireAvengerExarchProfile as _ExarchProfile  # noqa: E402

# User report: "bei warp spider und avengers kann ich den exarch nicht
# unterscheiden". There is no separate Exarch art for this datasheet, so the
# leader ring/label the renderer draws for squad_leader models is the ONLY
# thing that tells it apart - and the flag was simply never set here (the
# Striking Scorpion and Howling Banshee Exarchs already had it).
checks.true("the Exarch is flagged squad_leader", _ExarchProfile.squad_leader)
_exarch_squad = _tk_leader.build(_sheet_for_leader, "Player 1", name="1 DIRE_AVENGERS L1")
_leaders = [m for m in _exarch_squad.models if m.profile.squad_leader]
checks.eq("exactly one model in the unit carries it", len(_leaders), 1)
checks.eq("and it is the Exarch", _leaders[0].profile.name, "Dire Avenger Exarch")


checks.finish()
