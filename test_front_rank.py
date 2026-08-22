"""Melee characters stand at the FRONT of their unit's formation.

Reported: "die ki stellt den warboss immer sehr weit hinten im squad auf. der
sollte ganz vorne im squad aufgestellt werden, damit er auch als ersten in den
nahkampf kommt. kann sonst nicht zuschlagen." - then, on the follow-up, "das
gilt fuer alle nahkampflastigen charaktere".

Measured on the reported mob (20 Boyz + Warboss + Painboy) before the fix: the
Warboss came out rank 7 of 22 and the Painboy rank 9. Every check below that
claims something improved runs A/B with game/front_rank.py neutralised, because
"the character is near the front" is also what an easy scene looks like.

Three places decide this and all three are covered: pre-game/reserve deployment
(game/formation_layout.py), stepping out of a transport
(ai/agent_driver.py's _disembark_pack_positions) and claiming an Engagement
Range slot on a charge or pile-in (_charge_per_model's phase 2).
"""

import math
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")

from testkit import Checks, build_squad, GameState

from ai import agent_driver
from game import attached_units, formation_layout, front_rank, maps
from game.factions import orks, tau_empire

c = Checks("front rank (melee characters lead)")

maps.apply_to_config(maps.get("map2"))


# ------------------------------------------------------------------ helpers

def mob(leader_sheet, body_sheet, owner="Player 2", **body_kw):
    body = build_squad(body_sheet, owner, **body_kw)
    leader = build_squad(leader_sheet, owner)
    attached_units.attach(leader, body)
    return body


def ranks(models, spots, forward):
    """Model names ordered front-most first along `forward`."""
    fx, fy = forward
    scored = sorted(
        ((x * fx + y * fy, m.profile.name) for m, (x, y) in zip(models, spots)),
        key=lambda pair: -pair[0],
    )
    return [name for _, name in scored]


def rank_of(name, order):
    return order.index(name) + 1


def without_front_rank(fn):
    """Run `fn` with the feature switched off, then restore it. This is the
    A/B: without it a passing check could simply mean the packer happened to
    put the character somewhere sensible."""
    saved = front_rank.front_rank_models
    front_rank.front_rank_models = lambda squad: []
    try:
        return fn()
    finally:
        front_rank.front_rank_models = saved


# =========================================================================
# 1. WHO counts as a melee character
# =========================================================================
# The classification is the load-bearing half: put a shooting character in the
# front rank and it dies for nothing.

CASES = [
    ("Warboss", orks.WARBOSS, orks.BOYZ, {"composition_index": 1}, True),
    ("Painboy", orks.PAINBOY, orks.BOYZ, {"composition_index": 1}, True),
    ("Warboss in Mega Armour", orks.WARBOSS_MEGA_ARMOUR, orks.MEGANOBZ, {}, True),
    ("Beastboss", orks.BEASTBOSS, orks.BEAST_SNAGGA_BOYZ, {}, True),
]
TAU_CASES = [
    ("Commander Farsight", tau_empire.COMMANDER_FARSIGHT, tau_empire.CRISIS_SUNFORGE, True),
    ("Cadre Fireblade", tau_empire.CADRE_FIREBLADE, tau_empire.BREACHER_TEAM, False),
    ("Commander in Coldstar Battlesuit", tau_empire.COMMANDER_IN_COLDSTAR_BATTLESUIT,
     tau_empire.CRISIS_STARSCYTHE, False),
]

for label, leader_sheet, body_sheet, kw, want in CASES:
    squad = mob(leader_sheet, body_sheet, **kw)
    model = next(m for m in squad.models if m.profile.name == label)
    c.eq(f"{label} counts as a melee character", front_rank.is_melee_character(model, squad), want)

for label, leader_sheet, body_sheet, want in TAU_CASES:
    squad = mob(leader_sheet, body_sheet, owner="Player 1")
    model = next(m for m in squad.models if m.profile.name == label)
    c.eq(f"{label} counts as a melee character: {want}",
         front_rank.is_melee_character(model, squad), want)

# The rank and file are never promoted, however hard they hit - the rule is
# about characters, and a mob cannot all be in the front rank anyway.
squad = mob(orks.WARBOSS, orks.BOYZ, composition_index=1)
boy = next(m for m in squad.models if m.profile.name == "Boy")
c.eq("a rank-and-file model is not a character", front_rank.is_melee_character(boy, squad), False)
c.true("...even though it is melee-focused in its own right", front_rank.is_melee_focused(boy))

# An unattached character leads nobody, so there is no formation to lead from.
lone = build_squad(orks.WARBOSS, "Player 2")
c.eq("a character standing on its own is not promoted anywhere",
     front_rank.front_rank_models(lone), [])

# Hardest hitter first, so two characters do not depend on attach order.
squad = mob(orks.WARBOSS, orks.BOYZ, composition_index=1)
attached_units.attach(build_squad(orks.PAINBOY, "Player 2"), squad)
c.eq("with two characters the bigger threat leads",
     [m.profile.name for m in front_rank.front_rank_models(squad)], ["Warboss", "Painboy"])

# The measured separation the 1.0 threshold sits in - if a datasheet change
# ever narrows it, this is where it shows up rather than in a live game.
farsight = mob(tau_empire.COMMANDER_FARSIGHT, tau_empire.CRISIS_SUNFORGE, owner="Player 1")
fs = next(m for m in farsight.models if m.profile.name == "Commander Farsight")
fireblade = mob(tau_empire.CADRE_FIREBLADE, tau_empire.BREACHER_TEAM, owner="Player 1")
fb = next(m for m in fireblade.models if m.profile.name == "Cadre Fireblade")
fs_ratio = front_rank.model_output(fs, True) / front_rank.model_output(fs, False)
fb_ratio = front_rank.model_output(fb, True) / front_rank.model_output(fb, False)
c.true(f"the threshold sits in a gap, not on a cliff ({fb_ratio:.2f} .. {fs_ratio:.2f})",
       fb_ratio < 0.75 < 1.5 < fs_ratio)


# =========================================================================
# 2. DEPLOYMENT - the reported case
# =========================================================================
# game/formation_layout.py packs the block; base_angle is the direction it
# GROWS, i.e. away from the enemy, so forward is the other way.

BASE_ANGLE = math.pi / 2
FORWARD = (math.cos(BASE_ANGLE + math.pi), math.sin(BASE_ANGLE + math.pi))


def packed(squad):
    return formation_layout.pack_positions(squad, 24.0, 30.0, base_angle=BASE_ANGLE)


reported = mob(orks.WARBOSS, orks.BOYZ, composition_index=1)
attached_units.attach(build_squad(orks.PAINBOY, "Player 2"), reported)
c.eq("the reported mob really is 22 models", len(reported.models), 22)

order = ranks(reported.models, packed(reported), FORWARD)
before = without_front_rank(lambda: ranks(reported.models, packed(reported), FORWARD))

c.eq(f"A/B: the Warboss used to be buried mid-block (rank {rank_of('Warboss', before)} of 22)",
     rank_of("Warboss", before) > 5, True)
c.eq(f"A/B: so was the Painboy (rank {rank_of('Painboy', before)} of 22)",
     rank_of("Painboy", before) > 5, True)
c.true(f"the Warboss now deploys in the front rank (rank {rank_of('Warboss', order)} of 22)",
       rank_of("Warboss", order) == 1)
c.true(f"the Painboy right behind him (rank {rank_of('Painboy', order)} of 22)",
       rank_of("Painboy", order) <= 3)

# The block is still a legal formation - this is the part a reordering could
# quietly break, and rule 09.02 is checked by confirm_setup() at every caller.
spots = packed(reported)
for model, (x, y) in zip(reported.models, spots):
    model.x_in, model.y_in = x, y
c.eq("the promoted formation is still one coherent group (rule 09.02)",
     reported.check_coherency(), [])
worst = min(
    ((spots[i][0] - spots[j][0]) ** 2 + (spots[i][1] - spots[j][1]) ** 2) ** 0.5
    - reported.models[i].radius_in - reported.models[j].radius_in
    for i in range(len(spots)) for j in range(i + 1, len(spots))
)
c.true(f"no two models overlap (closest edges {worst:.2f}\")", worst > 0)

# Every other attached unit in both armies, same treatment.
for label, leader_sheet, body_sheet, kw, _ in CASES[2:]:
    squad = mob(leader_sheet, body_sheet, **kw)
    got = ranks(squad.models, packed(squad), FORWARD)
    c.eq(f"{label} deploys at the very front", rank_of(label, got), 1)

farsight = mob(tau_empire.COMMANDER_FARSIGHT, tau_empire.CRISIS_SUNFORGE, owner="Player 1")
got = ranks(farsight.models, packed(farsight), FORWARD)
c.eq("Commander Farsight deploys at the very front", rank_of("Commander Farsight", got), 1)

# ...and a shooting character is deliberately left where the packer put it.
fireblade = mob(tau_empire.CADRE_FIREBLADE, tau_empire.BREACHER_TEAM, owner="Player 1")
got = ranks(fireblade.models, packed(fireblade), FORWARD)
was = without_front_rank(lambda: ranks(fireblade.models, packed(fireblade), FORWARD))
c.eq("a shooting character is NOT pushed into the front rank",
     rank_of("Cadre Fireblade", got), rank_of("Cadre Fireblade", was))

# A unit with no character at all must come out bit-for-bit unchanged - this
# is what keeps the change off every other unit on the board.
plain = build_squad(orks.BOYZ, "Player 2", composition_index=1)
c.eq("a unit with no character is packed exactly as before",
     packed(plain), without_front_rank(lambda: packed(plain)))


# =========================================================================
# 3. DISEMBARKING - same rule, different packer
# =========================================================================
# ai/agent_driver.py has its own ring geometry here, and its base_angle points
# AT the enemy rather than away, so forward is base_angle itself.

def disembark_scene():
    cargo = mob(orks.WARBOSS, orks.BOYZ, composition_index=1)
    attached_units.attach(build_squad(orks.PAINBOY, "Player 2"), cargo)
    wagon = build_squad(orks.BATTLEWAGON, "Player 2")
    hull = wagon.models[0]
    hull.x_in, hull.y_in = 20.0, 15.0
    enemy = build_squad(orks.BOYZ, "Player 1")
    for i, model in enumerate(enemy.models):
        model.x_in, model.y_in = 14.0 + i * 1.5, 34.0
    return cargo, hull, [hull] + list(enemy.models)


def disembark_order():
    cargo, hull, tokens = disembark_scene()
    spots = agent_driver._disembark_pack_positions(cargo, hull, 3.0, tokens, setup_controller=None)
    return ranks(cargo.models, spots, (0.0, 1.0))  # the enemy is due north


after = disembark_order()
prior = without_front_rank(disembark_order)
c.eq(f"A/B: the Painboy used to step out LAST (rank {rank_of('Painboy', prior)} of 22)",
     rank_of("Painboy", prior) > 15, True)
c.true(f"the Painboy now steps out in the front rank (rank {rank_of('Painboy', after)} of 22)",
       rank_of("Painboy", after) <= 4)
c.true(f"the Warboss steps out in the front rank (rank {rank_of('Warboss', after)} of 22)",
       rank_of("Warboss", after) <= 4)


# =========================================================================
# 4. the fragility guard
# =========================================================================
# Putting a wider base at the tip of a block costs it neighbours, and the
# disembark clump work exists precisely to keep single points of failure out of
# a formation. So the front-rank layout is only taken when it is no worse.

square = [(0.0, 0.0), (1.5, 0.0), (0.0, 1.5), (1.5, 1.5)]
chain = [(0.0, 0.0), (2.4, 0.0), (4.8, 0.0), (7.2, 0.0)]
c.eq("bridge_count: a tight block has no single point of failure",
     formation_layout.bridge_count([(x, y, 0.63) for x, y in square]), 0)
c.true("bridge_count: a chain is all single points of failure",
       formation_layout.bridge_count([(x, y, 0.63) for x, y in chain]) == 3)
c.eq("bridge_count: a disconnected placement cannot be measured",
     formation_layout.bridge_count([(0.0, 0.0, 0.63), (40.0, 40.0, 0.63)]), None)

radius = lambda i: 0.63
solid = {i: xy for i, xy in enumerate(square)}
strung = {i: xy for i, xy in enumerate(chain)}
c.eq("a candidate that seats fewer models is refused",
     formation_layout.no_worse_than({0: (0.0, 0.0)}, solid, radius), False)
c.eq("a candidate that is more fragile is refused",
     formation_layout.no_worse_than(strung, solid, radius), False)
c.eq("a candidate that is no worse is taken",
     formation_layout.no_worse_than(solid, solid, radius), True)
c.eq("a candidate that is not one group at all is refused",
     formation_layout.no_worse_than({0: (0.0, 0.0), 1: (40.0, 40.0)}, solid, radius), False)


# =========================================================================
# 5. CHARGING - who claims an Engagement Range slot first
# =========================================================================
# Rule 12.05: only models within Engagement Range fight. Slots are handed out
# in the order _charge_per_model()'s phase 2 walks its models, so a character
# who is NOT the nearest model gets whatever the mob left over. Driven through
# the real charge here rather than through a reimplementation of the sort.

from game import config
from game.movement import MovementController
from game.turn import PHASES, PHASE_CHARGE, TurnTracker


def charge_scene():
    """A 10-Boyz mob with its Warboss deliberately placed in the BACK rank,
    charging a tight enemy block that has room for only some of them."""
    attacker = mob(orks.WARBOSS, orks.BOYZ, composition_index=0)
    defender = build_squad(orks.GRETCHIN, "Player 1")
    defender.models = defender.models[:3]
    for i, model in enumerate(defender.models):
        model.x_in, model.y_in = 21.0 + i * 1.4, 31.0

    body = [m for m in attacker.models if m.profile.name != "Warboss"]
    boss = next(m for m in attacker.models if m.profile.name == "Warboss")
    for i, model in enumerate(body):
        model.x_in, model.y_in = 19.5 + (i % 5) * 1.5, 26.0 - (i // 5) * 1.6
    boss.x_in, boss.y_in = 21.5, 22.8  # behind both ranks

    tokens = list(attacker.models) + list(defender.models)
    state = GameState()
    state.tokens = tokens
    turn = TurnTracker(first_player="Player 2")
    turn.phase_index = PHASES.index(PHASE_CHARGE)
    mc = MovementController(obstacles=[], player_name="Player 2", turn_tracker=turn,
                            all_tokens=tokens, board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    return attacker, defender, boss, mc


def engaged(attacker, defender):
    return [
        m for m in attacker.models
        if any(((m.x_in - e.x_in) ** 2 + (m.y_in - e.y_in) ** 2) ** 0.5
               - m.radius_in - e.radius_in <= 2.0 for e in defender.models)
    ]


def run_charge():
    attacker, defender, boss, mc = charge_scene()
    mc.select(attacker.models[0])
    mc.start_charge_move(9.0, [defender])
    agent_driver._charge_per_model(mc, attacker, defender, 9.0)
    fighting = engaged(attacker, defender)
    swings = sum(front_rank.model_output(m, melee=True) for m in fighting)
    return boss in fighting, len(fighting), swings, attacker.check_coherency()


boss_fights, count, swings, coherency = run_charge()
was_fighting, was_count, was_swings, _ = without_front_rank(run_charge)

c.true("the mob really cannot get all of itself into Engagement Range "
       f"({count} of 11 models)", count < 11)
c.eq("A/B: without the priority the rear-rank Warboss does not reach the fight",
     was_fighting, False)
c.eq("the melee character gets into Engagement Range (rule 12.05)", boss_fights, True)
c.eq("...and the charge is still a legal formation (rule 09.02)", coherency, [])
# Measured in DAMAGE, not bodies. The Warboss has a bigger base, so squeezing
# him in can cost a Boy his slot - which is the trade the whole change is
# about: one Warboss swinging is worth several Boyz not swinging, and counting
# bodies would call that a regression.
c.true(f"the mob hits harder for it ({was_count} bodies/{was_swings:.1f} damage -> "
       f"{count}/{swings:.1f})", swings > was_swings)

c.finish()
