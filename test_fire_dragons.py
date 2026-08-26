"""Fire Dragons: datasheet data, and Assured Destruction end to end.

Assured Destruction is three optional re-rolls at three different points of one
attack sequence, so it is tested through the REAL ShootingController rather
than against its predicate: an ability can pass applies() perfectly and still
never be offered, if it was chained into the wrong place. Each of the three is
shown to be offered, and each of its three conditions (MONSTER/VEHICLE, your
Shooting phase, the ability still alive in the unit) is isolated.
"""

import testkit as tk
from testkit import Checks, script

from game import assured_destruction as ad
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.sprites import _squad_key
from game.turn import PHASE_MOVEMENT, PHASE_SHOOTING
from game.weapons import MELEE, RANGED

checks = Checks("Fire Dragons")
EXARCH_LINE = "Fire Dragon Exarch"


def dragons(composition_index=0, choices=None, owner="Player 1"):
    return tk.build(ae.FIRE_DRAGONS, owner, name="1 Fire Dragons 1",
                    composition_index=composition_index, choices=choices)


def weapon_names(model):
    return sorted(w.name for w in model.weapons)


# --- 1. composition, statline, points --------------------------------------
print("--- 1. composition, statline, points ---")

small, big = dragons(0), dragons(1)
checks.eq("5-model unit", len(small.models), 5)
checks.eq("10-model unit", len(big.models), 10)
checks.eq("5 models cost 120", small.points, 120)
checks.eq("10 models cost 240", big.points, 240)
checks.eq("3rd+ unit of 5 costs 130", ae.FIRE_DRAGONS.points_for(0, unit_index=3), 130)
checks.eq("3rd+ unit of 10 costs 250", ae.FIRE_DRAGONS.points_for(1, unit_index=3), 250)

trooper = next(m for m in small.models if m.profile.name == "Fire Dragon")
exarch = next(m for m in small.models if m.profile.name == EXARCH_LINE)
checks.eq("M7\"", trooper.profile.movement_in, 7)
checks.eq("T3", trooper.profile.toughness, 3)
checks.eq("Sv3+", trooper.profile.armor_save, "3+")
checks.eq("W1 / Exarch W2", (trooper.profile.wounds, exarch.profile.wounds), (1, 2))
checks.eq("Ld6+", trooper.profile.leadership, "6+")
checks.eq("OC1", trooper.profile.oc, 1)
checks.eq("5+ invulnerable", trooper.profile.invulnerable_save, "5+")
checks.eq("28.5 mm base", round(trooper.profile.base_radius_in, 3), round(28.5 / 2 / 25.4, 3))
checks.true("INFANTRY", trooper.profile.infantry)
checks.true("Battle Focus", trooper.profile.battle_focus)
checks.true("Assured Destruction", trooper.profile.assured_destruction)
checks.true("the Exarch inherits it", exarch.profile.assured_destruction)
checks.eq("no Fleet of Foot", getattr(trooper.profile, "fleet_of_foot", False), False)
checks.eq("1 Aspect Shrine token at 5 models, 2 at 10",
          (small.aspect_shrine_tokens, big.aspect_shrine_tokens), (1, 2))
for kw in ("INFANTRY", "GRENADES", "ASPECT WARRIORS", "FIRE DRAGONS"):
    checks.true(f"keyword {kw}", kw in ae.FIRE_DRAGONS.keywords)


# --- 2. weapons ------------------------------------------------------------
print("--- 2. weapons ---")

checks.eq("trooper loadout", weapon_names(trooper), ["Close Combat Weapon", "Dragon Fusion Gun"])
checks.eq("Exarch loadout", weapon_names(exarch), ["Close Combat Weapon", "Exarch's Dragon Fusion Gun"])

gun = next(w for w in trooper.weapons if w.name == "Dragon Fusion Gun")
checks.eq("Dragon Fusion Gun 12\"/A1/S9/AP-4",
          (gun.range_in, gun.attacks, gun.strength, gun.ap), (12, 1, 9, -4))
checks.eq("its Damage is a rolled D6", gun.damage_notation.sides, 6)
checks.true("[ASSAULT]", gun.assault)
checks.eq("[MELTA 3]", gun.melta, 3)
# Distinct from Storm Guardians' Fusion Gun, which is why it is its own class.
from game.weapons import FusionGunProfile  # noqa: E402
checks.eq("the plain Fusion Gun is S8/[MELTA 2], this one S9/[MELTA 3]",
          (FusionGunProfile.strength, FusionGunProfile.melta, gun.strength, gun.melta), (8, 2, 9, 3))

ex_gun = next(w for w in exarch.weapons if w.name == "Exarch's Dragon Fusion Gun")
checks.eq("the Exarch's gun differs only in [MELTA 6]",
          (ex_gun.strength, ex_gun.ap, ex_gun.melta), (9, -4, 6))

ccw = next(w for w in trooper.weapons if w.weapon_type == MELEE)
checks.eq("Close Combat Weapon is the A2/S3 Aeldari row",
          (ccw.attacks, ccw.strength, ccw.ap, ccw.damage), (2, 3, 0, 1))


# --- 3. Exarch wargear -----------------------------------------------------
print("--- 3. Exarch wargear ---")

for option, expected in (
    (ae.FIRE_DRAGON_TO_BREATH_FLAMER, ["Close Combat Weapon", "Dragon's Breath Flamer"]),
    (ae.FIRE_DRAGON_TO_PISTOL_AND_AXE, ["Close Combat Weapon", "Dragon Axe", "Dragon Fusion Pistol"]),
    (ae.FIRE_DRAGON_TO_FIREPIKE, ["Close Combat Weapon", "Firepike"]),
):
    sq = dragons(choices={EXARCH_LINE: {option: 1}})
    checks.eq(f"{option}", weapon_names(sq.models[0]), expected)

flamer = next(w for w in dragons(choices={EXARCH_LINE: {ae.FIRE_DRAGON_TO_BREATH_FLAMER: 1}}).models[0].weapons
              if w.name == "Dragon's Breath Flamer")
checks.eq("Dragon's Breath Flamer rolls D6+2 attacks",
          (flamer.attacks_notation.sides, flamer.attacks_notation.bonus), (6, 2))
checks.true("...and auto-hits", flamer.torrent)
checks.true("...ignoring cover", flamer.ignores_cover)
checks.eq("no per-weapon BS override, since [TORRENT] makes one meaningless",
          flamer.ballistic_skill, None)

pike = next(w for w in dragons(choices={EXARCH_LINE: {ae.FIRE_DRAGON_TO_FIREPIKE: 1}}).models[0].weapons
            if w.name == "Firepike")
checks.eq("Firepike 18\"/S12", (pike.range_in, pike.strength), (18, 12))
axe = next(w for w in dragons(choices={EXARCH_LINE: {ae.FIRE_DRAGON_TO_PISTOL_AND_AXE: 1}}).models[0].weapons
           if w.name == "Dragon Axe")
checks.eq("Dragon Axe A3/S6/AP-4 with a rolled D6 Damage",
          (axe.attacks, axe.strength, axe.ap, axe.damage_notation.sides), (3, 6, -4, 6))

# "1 of the following": one Exarch, so a second choice finds nobody left.
sq = dragons(choices={EXARCH_LINE: {ae.FIRE_DRAGON_TO_BREATH_FLAMER: 1,
                                    ae.FIRE_DRAGON_TO_FIREPIKE: 1}})
checks.eq("two options chosen -> only the first applies",
          weapon_names(sq.models[0]), ["Close Combat Weapon", "Dragon's Breath Flamer"])


# --- 4. Assured Destruction: the predicate ---------------------------------
print("--- 4. Assured Destruction: the predicate ---")

vehicle = tk.build(tau.DEVILFISH, "Player 2", name="1 Devilfish 1")
infantry = tk.build(tau.STRIKE_TEAM, "Player 2", name="1 Strike Team 1")
shoot_turn = tk._tracker(PHASE_SHOOTING, "Player 1")

checks.true("a VEHICLE target in your own Shooting phase qualifies",
            ad.applies(small, vehicle, shoot_turn))
checks.eq("an INFANTRY target does not", ad.applies(small, infantry, shoot_turn), False)
checks.eq("nor does the Movement phase",
          ad.applies(small, vehicle, tk._tracker(PHASE_MOVEMENT, "Player 1")), False)
# "In YOUR Shooting phase" - which is what excludes a reactive Snap Shot
# (Fire Overwatch, 15.08/15.09) in the opponent's turn.
checks.eq("nor the opponent's Shooting phase",
          ad.applies(small, vehicle, tk._tracker(PHASE_SHOOTING, "Player 2")), False)
checks.eq("a unit without the ability never qualifies",
          ad.applies(tk.build(ae.DIRE_AVENGERS, "Player 1", name="1 Dire Avengers 1"),
                     vehicle, shoot_turn), False)
dead = dragons()
for model in dead.models:
    model.current_wounds = 0
checks.eq("nor a unit with no living model left to carry it",
          ad.applies(dead, vehicle, shoot_turn), False)


# --- 5. Assured Destruction: end to end ------------------------------------
print("--- 5. Assured Destruction: end to end ---")


def fire(target_sheet, faces, answers=(), gap=6.0, owner="Player 1"):
    """One Dragon Fusion Gun group (4 troopers, A1 each) against `target_sheet`,
    driven to a standstill. `sc["offers"]` is every prompt raised on the way,
    which is how a test can say WHICH step asked."""
    sc = tk.shooting_scene(ae.FIRE_DRAGONS, target_sheet, attacker_owner=owner, gap=gap)
    sc["shooting"].start_shooting(sc["attacker"])
    sc["shooting"].choose_target_squad(sc["target"])
    key = next(r[0] for r in sc["shooting"].weapon_eligibility()
               if r[1] == "Dragon Fusion Gun")
    script(*faces, default=4)
    sc["shooting"].choose_weapon(key)
    todo, offers = list(answers), []
    for _ in range(16):
        if sc["decision"].is_pending:
            offers.append(sc["decision"].prompt)
            tk.pick_option(sc["decision"], todo.pop(0) if todo else _decline(sc["decision"]))
        elif sc["dice"].is_pending:
            sc["dice"].acknowledge()
            sc["shooting"].on_dice_acknowledged()
        elif sc["shooting"].pending_damage_choice:
            sc["shooting"].choose_damage_model(sc["shooting"].pending_damage_choice[0])
        else:
            break
    sc["offers"] = offers
    return sc


def _decline(dm):
    """Whatever this prompt's "do nothing" option is called."""
    for label in ("Keep result", "Keep the roll", "Keep the Damage roll"):
        if any(o["label"].startswith(label) for o in dm.options):
            return label
    return dm.options[-1]["label"]


# 4 troopers, A1 each. Hit roll at BS3+: two hits, two misses, so the
# failures-only scope has something to throw. Then two wound dice at 5+
# against the Devilfish's T9, ONE of which fails - the wound offer is gated on
# there being a failure, so an all-wounds roll would (correctly) raise none.
# Then the save, which is academic (Sv3+ against AP-4 is a 7+, impossible),
# and finally the Damage roll: the script has to reach that far or the third
# offer can never be observed at all.
FACES = [4, 4, 1, 1] + [5, 1] + [1] + [3]

vs_vehicle = fire(tau.DEVILFISH, FACES)
vs_infantry = fire(tau.STRIKE_TEAM, FACES)


def steps(sc):
    out = []
    for prompt in sc["offers"]:
        if "Assured Destruction" not in prompt:
            continue
        for step in ("Hit roll", "Wound roll", "Damage roll"):
            if step in prompt:
                out.append(step)
                break
    return out


checks.eq("against a VEHICLE all three re-rolls are offered, in sequence",
          steps(vs_vehicle), ["Hit roll", "Wound roll", "Damage roll"])
checks.eq("against INFANTRY none of them are", steps(vs_infantry), [])

# The hit offer is a genuine two-way choice, as it already is for Monster
# Hunters - so "failures only" and "the whole roll" are both on the table.
hit_prompt_scene = tk.shooting_scene(ae.FIRE_DRAGONS, tau.DEVILFISH, attacker_owner="Player 1", gap=6.0)
hit_prompt_scene["shooting"].start_shooting(hit_prompt_scene["attacker"])
hit_prompt_scene["shooting"].choose_target_squad(hit_prompt_scene["target"])
k = next(r[0] for r in hit_prompt_scene["shooting"].weapon_eligibility() if r[1] == "Dragon Fusion Gun")
script(*FACES)
hit_prompt_scene["shooting"].choose_weapon(k)
hit_prompt_scene["dice"].acknowledge()
hit_prompt_scene["shooting"].on_dice_acknowledged()
labels = [o["label"] for o in hit_prompt_scene["decision"].options]
checks.true("the hit offer names the ability", "Assured Destruction" in hit_prompt_scene["decision"].prompt)
checks.true("...offers the failures-only scope",
            any(lbl.startswith("Re-roll failed hit rolls") for lbl in labels))
checks.true("...offers the whole roll",
            any(lbl.startswith("Re-roll the whole Hit roll") for lbl in labels))
checks.true("...and a way to decline", any(lbl == "Keep result" for lbl in labels))

# Taking the failures-only re-roll actually throws exactly the failed dice.
taken = fire(tau.DEVILFISH, [4, 4, 1, 1] + [4, 4] + [5, 1] + [1] + [3],
             answers=("Re-roll failed hit rolls (2 dice)",))
checks.true("the re-roll is logged with the ability's name",
            any("Assured Destruction" in line and "re-roll" in line.lower()
                for line in taken["log"].lines))
reroll_sizes = [len(v) for label, v in taken["dice"].rolled if label.startswith("Hit Roll")]
checks.eq("the first hit roll was 4 dice and the re-roll exactly its 2 failures",
          reroll_sizes, [4, 2])

# The wound half re-rolls the WHOLE roll, like Breach and Clear and Sunforge -
# and offers the failures-only subset of it too.
checks.true("the wound offer also names the ability",
            any("Assured Destruction" in p and "Wound roll" in p for p in vs_vehicle["offers"]))
checks.true("and the damage offer too",
            any("Assured Destruction" in p and "Damage roll" in p for p in vs_vehicle["offers"]))


# --- 6. sprites ------------------------------------------------------------
print("--- 6. sprites ---")

for model in (trooper, exarch):
    checks.eq(f"{model.profile.name} art", _squad_key(model), "Fire Dragons")


# --- 7. A/B probe ----------------------------------------------------------
print("--- 7. A/B probe ---")

original = ad.applies
ad.applies = lambda *a, **kw: False
blind = fire(tau.DEVILFISH, FACES)
checks.eq("A/B: unwired, a VEHICLE target gets no offer at all", steps(blind), [])
ad.applies = original
restored = fire(tau.DEVILFISH, FACES)
checks.eq("A/B: restored", steps(restored), ["Hit roll", "Wound roll", "Damage roll"])

print("--- the Exarch is marked as the squad leader ---")
import testkit as _tk_leader  # noqa: E402
from game.factions.aeldari import FIRE_DRAGONS as _sheet_for_leader  # noqa: E402
from game.units import FireDragonExarchProfile as _ExarchProfile  # noqa: E402

# User report: "bei warp spider und avengers kann ich den exarch nicht
# unterscheiden". There is no separate Exarch art for this datasheet, so the
# leader ring/label the renderer draws for squad_leader models is the ONLY
# thing that tells it apart - and the flag was simply never set here (the
# Striking Scorpion and Howling Banshee Exarchs already had it).
checks.true("the Exarch is flagged squad_leader", _ExarchProfile.squad_leader)
_exarch_squad = _tk_leader.build(_sheet_for_leader, "Player 1", name="1 FIRE_DRAGONS L1")
_leaders = [m for m in _exarch_squad.models if m.profile.squad_leader]
checks.eq("exactly one model in the unit carries it", len(_leaders), 1)
checks.eq("and it is the Exarch", _leaders[0].profile.name, "Fire Dragon Exarch")


checks.finish()
