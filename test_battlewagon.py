"""Battlewagon (Orks) - datasheet, 'Ard Case, transport capacity, and
Ramshackle but Rugged. Plus the sprite mapping for every new Ork unit.

Run: python test_battlewagon.py

Built on testkit.py (see its docstring for the headless-harness traps).
"""

import os

from testkit import Checks, GameState, build, line_up, script

from game import ramshackle
from game.damage_resolution import DamageAllocationSession
from game.factions.orks import (
    BATTLEWAGON, BATTLEWAGON_ARD_CASE, BEAST_SNAGGA_BOYZ, BEASTBOSS, BOYZ, FLASH_GITZ,
    GRETCHIN, KILL_RIG, MEGANOBZ, STORMBOYZ, TRUKK, WARBOSS, WARBOSS_MEGA_ARMOUR,
)
from game.movement import MovementController
from game.transport import TransportController, _model_capacity_cost
from game.weapons import BigShootaProfile, WreckinBallProfile

c = Checks("Battlewagon")

# ---------------------------------------------------------------------------
# 1. Datasheet
# ---------------------------------------------------------------------------

squad = build(BATTLEWAGON, name="Battlewagon 1")
c.eq("single-model datasheet", len(squad.models), 1)
c.eq("points", squad.points, 145)

wagon = squad.models[0]
p = wagon.profile
# "base size wie kill rig", and the Kill Rig is in turn Devilfish-sized on
# user request ("kill rig und battle wagon sind zu groß") - so both halves
# are checked, the literal and the tie to the Kill Rig's own value.
c.eq("base radius (same as Kill Rig)", round(p.base_radius_in, 2), 2.1)
c.eq("...and that IS the Kill Rig's own value",
     round(p.base_radius_in, 2), round(build(KILL_RIG, name="KR").models[0].profile.base_radius_in, 2))
c.eq("move", p.movement_in, 10)
c.eq("toughness", p.toughness, 10)
c.eq("save", p.armor_save, "3+")
c.eq("invulnerable save", p.invulnerable_save, "6+")
c.eq("wounds", p.wounds, 16)
c.eq("leadership", p.leadership, "7+")
c.eq("OC", p.oc, 5)
c.eq("weapon skill (its only default weapon's own)", p.weapon_skill, "4+")
c.eq("ballistic skill", p.ballistic_skill, "5+")
c.eq("VEHICLE", p.vehicle, True)
c.eq("TRANSPORT", p.transport, True)
c.eq("not a MONSTER (unlike the Kill Rig it shares a stat line with)", p.monster, False)
c.eq("Damaged: 1-5 wounds remaining", p.damaged_threshold, 5)
c.true("Deadly Demise is a real D6 roll", p.deadly_demise_notation is not None)
c.eq("Firing Deck 11", p.firing_deck, 11)
c.eq("Ramshackle but Rugged flag", p.ramshackle_but_rugged, True)
c.eq("Waaagh!", p.waaagh, True)
c.eq("datasheet keywords", set(BATTLEWAGON.keywords), {"VEHICLE", "TRANSPORT", "BATTLEWAGON"})

c.eq("only one default weapon", len(wagon.weapons), 1)
tracks = wagon.weapons[0]
c.eq("tracks and wheels", tracks.name, "Tracks and Wheels")
c.eq("tracks attacks", tracks.attacks, 6)
c.eq("tracks strength", tracks.strength, 8)
c.eq("tracks AP", tracks.ap, 0)
c.eq("tracks damage", tracks.damage, 1)
c.eq("tracks needs no WS override (matches the model's 4+)", tracks.weapon_skill, None)

# Unselected Profiles: two are reused unchanged, three are new classes.
from game.weapons import DeffRollaProfile, GrabbinKlawProfile, LobbaProfile  # noqa: E402

big_shoota, wreckin = BigShootaProfile(), WreckinBallProfile()
c.eq("Big shoota reuses the Trukk's class", (big_shoota.range_in, big_shoota.attacks, big_shoota.strength,
                                             big_shoota.rapid_fire), (36, 3, 5, 2))
c.eq("Wreckin' ball reuses the Trukk's class too",
     (wreckin.attacks, wreckin.strength, wreckin.ap, wreckin.extra_attacks), (1, 10, 0, True))
c.true("Wreckin' ball's WS4+ matches this model, so it needs no override",
       wreckin.weapon_skill is None)

lobba = LobbaProfile()
c.eq("lobba range", lobba.range_in, 48)
c.eq("lobba strength", lobba.strength, 5)
c.eq("lobba damage", lobba.damage, 1)
c.eq("lobba has [BLAST]", lobba.blast, 1)
c.eq("lobba has [INDIRECT FIRE]", lobba.indirect_fire, True)
c.true("lobba Attacks is a real D6 roll", lobba.attacks_notation is not None)
# NOT the Kill Rig's 'Eavy lobba, despite the related name.
from game.weapons import EavyLobbaProfile  # noqa: E402
eavy = EavyLobbaProfile()
c.true("it is a different class from the Kill Rig's 'Eavy lobba", type(lobba) is not type(eavy))
c.eq("...which is S6/D2 where this is S5/D1", (eavy.strength, eavy.damage), (6, 2))

klaw = GrabbinKlawProfile()
c.eq("grabbin' klaw", (klaw.attacks, klaw.strength, klaw.ap, klaw.damage), (2, 8, -2, 2))
c.eq("grabbin' klaw has [EXTRA ATTACKS]", klaw.extra_attacks, True)
c.eq("grabbin' klaw overrides WS to a BETTER 3+", klaw.weapon_skill, "3+")

rolla = DeffRollaProfile()
c.eq("deff rolla", (rolla.attacks, rolla.strength, rolla.ap, rolla.damage), (6, 9, -1, 2))
c.eq("deff rolla overrides WS to a BETTER 3+", rolla.weapon_skill, "3+")
c.eq("deff rolla has no [EXTRA ATTACKS]", rolla.extra_attacks, False)


# ---------------------------------------------------------------------------
# 2. 'Ard Case
# ---------------------------------------------------------------------------

ARD = {"Battlewagon": [BATTLEWAGON_ARD_CASE]}
cased = build(BATTLEWAGON, name="Battlewagon 2", gear=ARD)
cw = cased.models[0]
c.eq("'Ard Case adds 2 Toughness", cw.profile.toughness, 12)
c.eq("...and removes Firing Deck", cw.profile.firing_deck, 0)
c.eq("...and costs 15 points", cased.points, 160)
c.eq("a Battlewagon without it is unchanged", (wagon.profile.toughness, wagon.profile.firing_deck), (10, 11))
c.eq("...and cheaper", squad.points, 145)
c.eq("the price comes from the published list, not a literal here",
     cased.points - squad.points, 15)

# The effect mutates only this token's own profile instance.
third = build(BATTLEWAGON, name="Battlewagon 3")
c.eq("a later Battlewagon is unaffected by an earlier one's 'Ard Case",
     (third.models[0].profile.toughness, third.models[0].profile.firing_deck), (10, 11))

# Only one slot, so asking twice is trimmed rather than stacking to +4.
greedy = build(BATTLEWAGON, name="Battlewagon 4",
               gear={"Battlewagon": [BATTLEWAGON_ARD_CASE, BATTLEWAGON_ARD_CASE]})
c.eq("a second 'Ard Case is trimmed", greedy.models[0].profile.toughness, 12)
c.eq("...and not charged twice", greedy.points, 160)

# Gear pricing is new - every existing free item must still be free.
from game.factions.tau_empire import STRIKE_TEAM  # noqa: E402
plain_st = build(STRIKE_TEAM, "Player 1", name="ST 1")
droned = build(STRIKE_TEAM, "Player 1", name="ST 2", gear={"Fire Warrior Shas'ui": ["Shield Drone"]})
c.eq("a free gear item still costs nothing", droned.points, plain_st.points)


# ---------------------------------------------------------------------------
# 3. Transport capacity
# ---------------------------------------------------------------------------

c.eq("capacity", p.transport_capacity, 22)
c.eq("requires INFANTRY", p.transport_requires_infantry, True)
c.eq("no BEAST SNAGGA-style requirement (any ORKS INFANTRY)", p.transport_requires, ())

boy = build(BOYZ, name="B").models[1]
meganob = build(MEGANOBZ, name="M").models[0]
stormboy = build(STORMBOYZ, name="S").models[1]
c.eq("an ordinary INFANTRY model costs 1", _model_capacity_cost(boy), 1)
c.eq("a MEGA ARMOUR model costs 2", _model_capacity_cost(meganob), 2)
c.eq("a JUMP PACK model costs 2 as well (this datasheet's own line)",
     _model_capacity_cost(stormboy), 2)
c.true("...and Stormboyz really are the JUMP PACK unit", stormboy.profile.jump_pack)


def can_carry(passenger_sheet, name, transport_sheet=BATTLEWAGON, comp=0):
    state = GameState()
    tr = build(transport_sheet, name="Transport")
    pax = build(passenger_sheet, name=name, composition_index=comp)
    tr.models[0].x_in, tr.models[0].y_in = 20.0, 20.0
    # Centred on the transport, not started at it: can_embark also enforces
    # rule 18.02's "every model within 3in of the hull", so a row that runs
    # off in one direction puts the tail model out of range for a big enough
    # passenger count - which is a fact about this harness's geometry, not
    # about the keyword eligibility these checks are actually asking about.
    # (An 11-model Gretchin row did exactly that once the Kill Rig's and
    # Battlewagon's bases shrank to the Devilfish's 2.1" - the smaller hull
    # reaches less far, so the same row no longer fit.) Centring halves the
    # worst-case distance and keeps every passenger size in range.
    spacing = 0.6
    line_up(pax, x=20.0 - (len(pax.models) - 1) * spacing / 2.0, y=21.0, spacing=spacing)
    for sq in (tr, pax):
        for m in sq.models:
            state.add_token(m)
    mc = MovementController(all_tokens=state.tokens)
    mc.moved_squad_ids.add(pax)
    tc = TransportController(
        setup_controller=None, game_state=state, all_tokens=state.tokens,
        movement_controller=mc, ingress_controller=None, dice_manager=None,
    )
    return tc.can_embark(pax, tr.models[0])


c.eq("Boyz may embark", can_carry(BOYZ, "Boyz 1"), True)
c.eq("Gretchin may embark", can_carry(GRETCHIN, "Grots 1"), True)
c.eq("Beast Snagga Boyz may embark (ORKS INFANTRY)", can_carry(BEAST_SNAGGA_BOYZ, "BSB 1"), True)
c.eq("Stormboyz may embark - unlike a Trukk, which refuses JUMP PACK",
     can_carry(STORMBOYZ, "Storm 1"), True)
c.eq("...and a Trukk still refuses them", can_carry(STORMBOYZ, "Storm 2", TRUKK), False)
c.eq("a Trukk may not embark (a TRANSPORT itself)", can_carry(TRUKK, "Trukk 1"), False)

# 10 Stormboyz at 2 slots each = 20, inside 22; the 6-model Meganobz build is
# 12, also inside. A Trukk's 12 could not take the Stormboyz even if it
# accepted them - which is what makes the doubled cost observable.
c.eq("10 JUMP PACK models (20 slots) fit in 22", can_carry(STORMBOYZ, "Storm 3", comp=1), True)
c.eq("6 MEGA ARMOUR models (12 slots) fit too", can_carry(MEGANOBZ, "Mega 1", comp=1), True)


# ---------------------------------------------------------------------------
# 4. Ramshackle but Rugged
# ---------------------------------------------------------------------------

c.eq("AP-2 is worsened to AP-1", ramshackle.adjusted_ap(-2, wagon), -1)
c.eq("AP-1 is worsened to AP0", ramshackle.adjusted_ap(-1, wagon), 0)
c.eq("AP0 stays AP0 - worsening never becomes a bonus", ramshackle.adjusted_ap(0, wagon), 0)
c.eq("AP-4 is worsened to AP-3", ramshackle.adjusted_ap(-4, wagon), -3)
c.eq("a model without the ability is untouched", ramshackle.adjusted_ap(-2, boy), -2)
c.eq("no model at all degrades quietly", ramshackle.adjusted_ap(-2, None), -2)
c.eq("unit predicate", ramshackle.unit_has_ramshackle(squad), True)
c.eq("...and is False for anyone else", ramshackle.unit_has_ramshackle(build(BOYZ, name="B2")), False)

dead = build(BATTLEWAGON, name="Wreck")
dead.models[0].current_wounds = 0
c.eq("the ability dies with the model (19.04)", ramshackle.unit_has_ramshackle(dead), False)


class _Weapon:
    """An AP-2, Damage-1 attack - enough to matter against a 3+ save."""
    ap = -2
    damage = 1
    damage_notation = None
    name = "Test Gun"
    weapon_type = "ranged"


def saves_made(target_squad, rolls):
    """Run the real allocation session and report how many saves held."""
    session = DamageAllocationSession(list(rolls), _Weapon(), target_squad)
    while session.pending_choice is not None:
        session.choose_model(session.pending_choice[0])
    return session.saved, session.failed


# Sv3+ against AP-2 needs a 5+; Ramshackle makes it AP-1, so a 4+. A roll of
# exactly 4 is therefore the whole difference.
target = build(BATTLEWAGON, name="Under Fire")
saved, failed = saves_made(target, [4, 4, 4])
c.eq("three 4s all save behind Ramshackle (AP-2 -> AP-1 vs Sv3+)", (saved, failed), (3, 0))

# A/B: the same rolls against a model without the ability must fail.
plain_target = build(KILL_RIG, name="No Ramshackle")  # also Sv3+, T10, 16W
c.eq("the same rolls against an identical Sv3+ model without it all fail",
     saves_made(plain_target, [4, 4, 4]), (0, 3))
c.true("...and that comparison is fair - both are Sv3+",
       target.models[0].profile.armor_save == plain_target.models[0].profile.armor_save)

# A 3 fails either way (3 + (-1) = 2, below 3+), so the ability is not a
# blanket immunity.
c.eq("a roll of 3 still fails even with Ramshackle", saves_made(build(BATTLEWAGON, name="U2"), [3]), (0, 1))


# ---------------------------------------------------------------------------
# 5. Sprites for every new Ork unit
# ---------------------------------------------------------------------------

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((10, 10))
from game import attached_units, sprites  # noqa: E402

EXPECTED = {
    BEAST_SNAGGA_BOYZ: {"Beast Snagga Boy": "Beast Boy", "Beast Snagga Nob": "Beast Boy Nob"},
    BEASTBOSS: {"Beastboss": "Ork Beast Boss"},
    KILL_RIG: {"Kill Rig": "Ork Kill Rig"},
    FLASH_GITZ: {"Kaptin": "Flash GItz", "Flash Git": "Flash GItz"},
    BATTLEWAGON: {"Battlewagon": "Ork Battle Wagon"},
    # Regression: the units these new keys could collide with by substring.
    BOYZ: {"Boss Nob": "Ork Boy", "Boy": "Ork Boy"},
    WARBOSS: {"Warboss": "Ork Warboss"},
    WARBOSS_MEGA_ARMOUR: {"Warboss in Mega Armour": "Ork Warboss in Megaarmor"},
}

for sheet, expected in EXPECTED.items():
    sq = build(sheet, name=f"2 {sheet.name} 1")
    got = {m.profile.name: sprites._squad_key(m) for m in sq.models}
    c.eq(f"sprite keys for {sheet.name}", got, expected)
    for model in sq.models:
        c.true(f"{sheet.name}/{model.profile.name} art actually loads",
               sprites.sprite_for(model) is not None)

# "Beast Snagga Boyz" contains "Boyz" - the ordering hazard this file warns
# about for Warboss. Check it head-on rather than trusting the dict order.
keys = list(sprites.SQUAD_SPRITE_KEYS)
c.true("the Beast Snagga entry is ordered before the plain Boyz one",
       keys.index("Beast Snagga Boyz") < keys.index("Boyz"))

# And inside an attached unit, where one squad has two datasheets.
boss_sq = build(BEASTBOSS, name="2 Beastboss 1")
mob = build(BEAST_SNAGGA_BOYZ, name="2 Beast Snagga Boyz 1")
attached_units.attach(boss_sq, mob)
attached = {m.profile.name: sprites._squad_key(m) for m in mob.models}
c.eq("an attached Beastboss keeps its own art", attached.get("Beastboss"), "Ork Beast Boss")
c.eq("...and the mob keeps its own", attached.get("Beast Snagga Boy"), "Beast Boy")
c.eq("...and the Nob keeps its own", attached.get("Beast Snagga Nob"), "Beast Boy Nob")

c.finish()
