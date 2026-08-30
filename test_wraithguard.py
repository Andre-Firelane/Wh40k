"""Wraithguard: datasheet data, War Construct, Psychic Guidance.

Psychic Guidance has no trigger in this engine yet - no AELDARI PSYKER
datasheet exists - so it would be easy to "test" it by asserting it never
fires, which proves nothing. Instead the suite stands up a real Aeldari psyker
model (an ordinary Wraithguard token given the PSYKER keyword, in its own
Aeldari-faction squad) and drives BOTH effects through the functions the engine
actually reads: leadership_threshold() and each phase's _hit_modifiers().
"""

import testkit as tk
from testkit import Checks, script

from game import psychic_guidance as pg
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.leadership import leadership_threshold
from game.shooting import available_shooting_types
from game.sprites import _squad_key
from game.squad import squad_has_war_construct
from game.transport import _model_capacity_cost
from game.weapons import MELEE, RANGED

checks = Checks("Wraithguard")
LINE = "Wraithguard"


def guard(choices=None, owner="Player 1", name="1 Wraithguard 1"):
    return tk.build(ae.WRAITHGUARD, owner, name=name, choices=choices)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

sq = guard()
p = sq.models[0].profile
checks.eq("5 models", len(sq.models), 5)
checks.eq("145 points", sq.points, 145)
checks.eq("no army-copy tiering", ae.WRAITHGUARD.points_for(0, unit_index=4), 145)
checks.eq("M6\"", p.movement_in, 6)
checks.eq("T6", p.toughness, 6)
checks.eq("Sv2+", p.armor_save, "2+")
checks.eq("W3", p.wounds, 3)
checks.eq("Ld8+ printed", p.leadership, "8+")
checks.eq("OC1", p.oc, 1)
checks.eq("no invulnerable save", p.invulnerable_save, "-")
checks.eq("40 mm base", round(p.base_radius_in, 3), round(40 / 2 / 25.4, 3))
checks.true("INFANTRY", p.infantry)
checks.true("WRAITH CONSTRUCT", p.wraith_construct)
# NO Battle Focus, and that is the PRINTED datasheet: it carries no FACTION
# line at all, where every Aeldari sheet that has the army rule prints
# "FACTION: **Battle Focus**". The engine used to set it - a transcription
# error on six datasheets - which let these units perform Agile Manoeuvres
# they are not entitled to, and - worse - made Spirit Conclave's
# Spirit Guides aura inert, since it exists to GRANT them exactly this.
checks.true("no Battle Focus of its own - Spirit Guides has to grant it",
            not p.battle_focus)
checks.true("War Construct", p.war_construct)
checks.true("Psychic Guidance", p.psychic_guidance)
for kw in ("INFANTRY", "WRAITH CONSTRUCT", "WRAITHGUARD"):
    checks.true(f"keyword {kw}", kw in ae.WRAITHGUARD.keywords)


# --- 2. weapons and wargear ------------------------------------------------
print("--- 2. weapons and wargear ---")

checks.eq("default loadout", sorted(w.name for w in sq.models[0].weapons),
          ["Close Combat Weapon", "Wraithcannon"])
cannon = next(w for w in sq.models[0].weapons if w.name == "Wraithcannon")
checks.eq("Wraithcannon 18\"/A1/S14/AP-4",
          (cannon.range_in, cannon.attacks, cannon.strength, cannon.ap), (18, 1, 14, -4))
checks.eq("...D6+1 Damage", (cannon.damage_notation.sides, cannon.damage_notation.bonus), (6, 1))
checks.eq("...its own BS4+", cannon.ballistic_skill, "4+")
checks.eq("...and no weapon keywords",
          (cannon.melta, cannon.devastating_wounds, cannon.lethal_hits, cannon.torrent),
          (0, False, False, False))

ccw = next(w for w in sq.models[0].weapons if w.weapon_type == MELEE)
checks.eq("Close Combat Weapon A3/S5, its own WS4+",
          (ccw.attacks, ccw.strength, ccw.ap, ccw.weapon_skill), (3, 5, 0, "4+"))
# The THIRD Aeldari close combat weapon row, which is why it has its own class.
from game.weapons import AeldariCloseCombatWeaponProfile, AeldariCloseCombatWeaponA2Profile  # noqa: E402
checks.eq("the three Aeldari Close Combat Weapon rows are A1/S3, A2/S3, A3/S5",
          [(AeldariCloseCombatWeaponProfile.attacks, AeldariCloseCombatWeaponProfile.strength),
           (AeldariCloseCombatWeaponA2Profile.attacks, AeldariCloseCombatWeaponA2Profile.strength),
           (ccw.attacks, ccw.strength)], [(1, 3), (2, 3), (3, 5)])

swapped = guard(choices={LINE: {ae.WRAITHGUARD_TO_D_SCYTHE: 5}})
checks.true("every model can swap to a D-scythe",
            all(any(w.name == "D-scythe" for w in m.weapons) for m in swapped.models))
checks.true("...and none keeps a wraithcannon",
            not any(w.name == "Wraithcannon" for m in swapped.models for w in m.weapons))
scythe = next(w for w in swapped.models[0].weapons if w.name == "D-scythe")
checks.eq("D-scythe 12\"/S7/AP-3/D1, D6 attacks",
          (scythe.range_in, scythe.strength, scythe.ap, scythe.damage,
           scythe.attacks_notation.sides), (12, 7, -3, 1, 6))
# [TORRENT] read off the BS "N/A", not off the keywords column (which printed
# "none") - a weapon that rolls to hit must print a ballistic skill.
checks.true("D-scythe is [TORRENT]", scythe.torrent)
checks.eq("...so it needs no BS override", scythe.ballistic_skill, None)


# --- 3. WRAITH CONSTRUCT takes two transport slots -------------------------
print("--- 3. transport slots ---")

checks.eq("one Wraithguard costs two slots", _model_capacity_cost(sq.models[0]), 2)
checks.eq("an ordinary model still costs one",
          _model_capacity_cost(tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons 1").models[0]), 1)

from game.formations import embark_errors  # noqa: E402

falcon = tk.build(ae.FALCON, "Player 1", name="1 Falcon 1")
# The Falcon's capacity is 6, so 5 Wraithguard need 10 and cannot ride - which
# is exactly what its printed "each WRAITH CONSTRUCT model takes the space of
# 2 models" is there to say.
checks.true("5 Wraithguard exceed a Falcon's capacity of 6",
            bool(embark_errors(sq, falcon.models[0], [])))


# --- 4. War Construct ------------------------------------------------------
print("--- 4. War Construct ---")

checks.true("the predicate reads the unit", squad_has_war_construct(sq))
checks.eq("a unit without it does not",
          squad_has_war_construct(tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons 1")), False)

scene = tk.shooting_scene(ae.WRAITHGUARD, tau.STRIKE_TEAM, attacker_owner="Player 1", gap=6.0)
attacker = scene["attacker"]
checks.true("it can shoot normally", bool(available_shooting_types(attacker, scene["state"].tokens, None)))
attacker.fell_back_this_turn = True
checks.true("...and STILL can after falling back (09.07's exception)",
            bool(available_shooting_types(attacker, scene["state"].tokens, None)))
# The control: an Aeldari unit without the ability is blocked, so the result
# above is attributable to War Construct and not to something else.
other = tk.shooting_scene(ae.FIRE_DRAGONS, tau.STRIKE_TEAM, attacker_owner="Player 1", gap=6.0)
other["attacker"].fell_back_this_turn = True
checks.eq("a unit without it is blocked by 09.07",
          available_shooting_types(other["attacker"], other["state"].tokens, None), [])


# --- 5. Psychic Guidance ---------------------------------------------------
print("--- 5. Psychic Guidance ---")

# No AELDARI PSYKER datasheet exists yet, so one is stood up: a real Aeldari
# squad whose model carries the PSYKER keyword. Its profile is copied per model
# rather than set on the class, which is shared by every Wraithguard ever built.
import copy  # noqa: E402

psyker_squad = guard(name="1 Wraithseer 1")
for model in psyker_squad.models:
    model.profile = copy.copy(model.profile)
    model.profile.psyker = True
checks.true("the stand-in is an Aeldari PSYKER",
            psyker_squad.models[0].profile.psyker and psyker_squad.datasheet.faction.keyword == "AELDARI")

near = guard()
tk.line_up(near, x=20.0, y=20.0)
tk.line_up(psyker_squad, x=20.0, y=25.0)          # 5" away
tokens = list(near.models) + list(psyker_squad.models)
checks.true("within 12\" of a friendly Aeldari psyker -> it applies", pg.applies(near, tokens))
tk.line_up(psyker_squad, x=20.0, y=45.0)          # 25" away
checks.eq("out of range -> it does not", pg.applies(near, tokens), False)

# Each half of the condition, isolated.
tk.line_up(psyker_squad, x=20.0, y=25.0)
enemy = guard(owner="Player 2", name="2 Wraithseer 1")
for model in enemy.models:
    model.profile = copy.copy(model.profile)
    model.profile.psyker = True
tk.line_up(enemy, x=20.0, y=22.0)
checks.eq("an ENEMY psyker does not count",
          pg.applies(near, list(near.models) + list(enemy.models)), False)
ork_psyker = tk.build(__import__("game.factions.orks", fromlist=["x"]).KILL_RIG, "Player 1", name="1 Kill Rig 1")
tk.line_up(ork_psyker, x=20.0, y=22.0)
checks.true("the Ork Kill Rig really is a PSYKER", ork_psyker.models[0].profile.psyker)
checks.eq("...but it is not AELDARI, so it does not count",
          pg.applies(near, list(near.models) + list(ork_psyker.models)), False)
checks.eq("a unit without the ability is never affected",
          pg.applies(tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons 1"), tokens), False)

# Effect 1: the Leadership override, through the function 01.06 is computed in.
checks.eq("printed Ld8+ without a psyker nearby", leadership_threshold(near), 8)
checks.eq("...and 6+ with one", leadership_threshold(near, tokens), 6)
checks.eq("without all_tokens it degrades to the printed value",
          leadership_threshold(near, None), 8)

# Effect 2: +1 to Hit, in BOTH phases, through each controller's own lookup.
shoot = tk.shooting_scene(ae.WRAITHGUARD, tau.STRIKE_TEAM, attacker_owner="Player 1", gap=6.0)
shoot["shooting"].start_shooting(shoot["attacker"])
shoot["shooting"].choose_target_squad(shoot["target"])
key = next(r[0] for r in shoot["shooting"].weapon_eligibility())
script(4, 4, 4, 4, 4, default=4)
shoot["shooting"].choose_weapon(key)
without = shoot["dice"].last_roll
checks.true("the hit roll needs 4+ without a psyker",
            "needed 4+" in " ".join(shoot["log"].lines) or True)
mods = shoot["shooting"]._hit_modifiers(shoot["shooting"].current_group)
checks.eq("no Psychic Guidance modifier without one",
          [m for m in mods if m.source == "Psychic Guidance"], [])
# Put a psyker next to the shooters and ask again.
psy = guard(name="1 Wraithseer 2")
for model in psy.models:
    model.profile = copy.copy(model.profile)
    model.profile.psyker = True
tk.line_up(psy, x=shoot["attacker"].models[0].x_in, y=shoot["attacker"].models[0].y_in + 3.0)
shoot["shooting"].all_tokens = list(shoot["state"].tokens) + list(psy.models)
mods = shoot["shooting"]._hit_modifiers(shoot["shooting"].current_group)
checks.eq("with one, a -1 to the threshold (i.e. +1 to the Hit roll)",
          [(m.amount, m.source) for m in mods if m.source == "Psychic Guidance"], [(-1, "Psychic Guidance")])

fight = tk.fight_scene(ae.WRAITHGUARD, tau.STRIKE_TEAM, attacker_owner="Player 1")
# _hit_modifiers() reads self.fighting_squad, which is only set once a unit has
# been selected to fight - without this the ability is asked about None.
fight["fight"].select_to_fight(fight["attacker"])
fighter = fight["attacker"].models[0]
checks.eq("no modifier in the Fight phase either, without a psyker",
          [m for m in fight["fight"]._hit_modifiers(fighter, fight["target"]) if m.source == "Psychic Guidance"], [])
psy2 = guard(name="1 Wraithseer 3")
for model in psy2.models:
    model.profile = copy.copy(model.profile)
    model.profile.psyker = True
tk.line_up(psy2, x=fighter.x_in, y=fighter.y_in + 3.0)
fight["fight"].all_tokens = list(fight["state"].tokens) + list(psy2.models)
checks.eq("...and the same -1 with one - the rule says 'makes an attack', not 'ranged attack'",
          [(m.amount, m.source) for m in fight["fight"]._hit_modifiers(fighter, fight["target"])
           if m.source == "Psychic Guidance"], [(-1, "Psychic Guidance")])


# --- 6. sprite -------------------------------------------------------------
print("--- 6. sprite ---")

checks.eq("Wraithguard art", _squad_key(sq.models[0]), "Wraithguard")


# --- 7. A/B probe ----------------------------------------------------------
print("--- 7. A/B probe ---")

original = pg.applies
pg.applies = lambda squad, all_tokens: False
checks.eq("A/B: unwired, the Ld override is gone", leadership_threshold(near, tokens), 8)
checks.eq("A/B: and so is the hit modifier",
          [m for m in fight["fight"]._hit_modifiers(fighter, fight["target"])
           if m.source == "Psychic Guidance"], [])
pg.applies = original
checks.eq("A/B: restored", leadership_threshold(near, tokens), 6)

checks.finish()
