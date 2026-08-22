"""Kill Rig (Orks) - datasheet, transport restriction, and Spirit of Gork.

Run: python test_kill_rig.py

Built on testkit.py (see its docstring for the headless-harness traps it
exists to stop each new suite rediscovering).
"""

from testkit import (
    Checks, DecisionManager, GameState, Log, PHASES, PHASE_FIGHT, TurnTracker,
    build, fight_scene, line_up, options_of, pick_option, script,
)
from testkit import RecordingDice

from game import spirit_of_gork as sog
from game.factions.orks import (
    BEASTBOSS, BEAST_SNAGGA_BOYZ, BOYZ, GRETCHIN, KILL_RIG, MEGANOBZ, STORMBOYZ, TRUKK,
)
from game.factions.tau_empire import DEVILFISH, STRIKE_TEAM
from game.movement import MovementController
from game.transport import TransportController

c = Checks("Kill Rig")

# ---------------------------------------------------------------------------
# 1. Datasheet
# ---------------------------------------------------------------------------

rig_squad = build(KILL_RIG, name="Kill Rig 1")
c.eq("single-model datasheet", len(rig_squad.models), 1)
c.eq("points", rig_squad.points, 145)

rig = rig_squad.models[0]
p = rig.profile
# User: "kill rig und battle wagon sind zu groß. bitte so groß machen wie
# devilfish" - a deliberate cosmetic size, replacing the 2.68" the real
# 170x109mm oval works out to (see KillRigProfile's own note). Checked
# against the Devilfish's own value rather than a literal, so the two stay
# tied if that one ever moves.
c.eq("base radius (Devilfish-sized, per user)", round(p.base_radius_in, 2), 2.1)
c.eq("...and that IS the Devilfish's own value", round(p.base_radius_in, 2),
     round(build(DEVILFISH, name="DF").models[0].profile.base_radius_in, 2))
c.eq("move", p.movement_in, 10)
c.eq("toughness", p.toughness, 10)
c.eq("save", p.armor_save, "3+")
c.eq("wounds", p.wounds, 16)
c.eq("leadership", p.leadership, "7+")
c.eq("OC", p.oc, 5)
c.eq("weapon skill (the majority of its melee weapons)", p.weapon_skill, "3+")
c.eq("ballistic skill", p.ballistic_skill, "5+")
c.eq("MONSTER", p.monster, True)
c.eq("TRANSPORT", p.transport, True)
c.eq("PSYKER", p.psyker, True)
c.eq("BEAST SNAGGA", p.beast_snagga, True)
c.eq("Feel No Pain 6+", p.feel_no_pain, "6+")
c.eq("Damaged: 1-5 wounds remaining", p.damaged_threshold, 5)
c.true("Deadly Demise is a real D6 roll", p.deadly_demise_notation is not None)
c.eq("Waaagh!", p.waaagh, True)
c.eq("Spirit of Gork flag", p.spirit_of_gork, True)
c.eq("datasheet keywords", set(KILL_RIG.keywords),
     {"MONSTER", "TRANSPORT", "PSYKER", "BEAST SNAGGA", "KILL RIG"})

by_name = {w.name: w for w in rig.weapons}
c.eq("carries all six printed weapons", len(rig.weapons), 6)

lobba = by_name["'Eavy Lobba"]
c.eq("lobba range", lobba.range_in, 48)
c.eq("lobba strength", lobba.strength, 6)
c.eq("lobba damage", lobba.damage, 2)
c.eq("lobba has [BLAST]", lobba.blast, 1)
c.eq("lobba has [INDIRECT FIRE]", lobba.indirect_fire, True)
c.true("lobba Attacks is a real D6 roll", lobba.attacks_notation is not None)

stikka = by_name["Stikka Kannon"]
c.eq("stikka range", stikka.range_in, 12)
c.eq("stikka strength", stikka.strength, 12)
c.eq("stikka AP", stikka.ap, -2)
c.eq("stikka damage", stikka.damage, 3)
c.eq("stikka carries BOTH anti keywords at 2+", stikka.anti, (("MONSTER", 2), ("VEHICLE", 2)))

wurr = by_name["Wurrtower"]
c.eq("wurrtower range", wurr.range_in, 24)
c.eq("wurrtower strength", wurr.strength, 12)
c.eq("wurrtower AP", wurr.ap, -3)
c.eq("wurrtower is [HAZARDOUS]", wurr.hazardous, True)
c.eq("wurrtower is [PSYCHIC]", wurr.psychic, True)
c.eq("wurrtower is [TORRENT]", wurr.torrent, True)
c.true("wurrtower Attacks is a real D3 roll", wurr.attacks_notation is not None)
c.true("wurrtower Damage is a real D6 roll", wurr.damage_notation is not None)
c.eq("wurrtower needs no BS override - [TORRENT] auto-hits", wurr.ballistic_skill, None)

butcha = by_name["Butcha Boyz"]
c.eq("butcha boyz attacks", butcha.attacks, 4)
c.eq("butcha boyz strength", butcha.strength, 5)
c.eq("butcha boyz has [EXTRA ATTACKS]", butcha.extra_attacks, True)
c.eq("butcha boyz anti", butcha.anti, (("MONSTER", 4), ("VEHICLE", 4)))

saw = by_name["Saw Blades"]
c.eq("saw blades attacks", saw.attacks, 6)
c.eq("saw blades strength", saw.strength, 10)
c.eq("saw blades AP", saw.ap, -2)
c.eq("saw blades needs no WS override", saw.weapon_skill, None)

horns = by_name["Savage Horns and Hooves"]
c.eq("horns attacks", horns.attacks, 4)
c.eq("horns strength", horns.strength, 8)
c.eq("horns damage", horns.damage, 3)
c.eq("horns overrides WS down to 4+", horns.weapon_skill, "4+")
c.eq("horns has [EXTRA ATTACKS]", horns.extra_attacks, True)
c.eq("horns has [LANCE]", horns.lance, True)

# Two of the three melee weapons are [EXTRA ATTACKS], so rule 04.01's
# "one melee weapon per activation" only ever contests the third.
c.eq("only one melee weapon competes under rule 04.01",
     sum(1 for w in rig.weapons if w.weapon_type == "melee" and not w.extra_attacks), 1)


# ---------------------------------------------------------------------------
# 2. Transport: "11 BEAST SNAGGA INFANTRY models"
# ---------------------------------------------------------------------------

def can_carry(passenger_sheet, name):
    """Drive the real TransportController eligibility, with the two
    unrelated preconditions (18.02's "must have moved this phase") satisfied
    so only the keyword/capacity half is under test."""
    state = GameState()
    rig_sq = build(KILL_RIG, name="Kill Rig T")
    pax = build(passenger_sheet, name=name)
    rig_sq.models[0].x_in, rig_sq.models[0].y_in = 20.0, 20.0
    line_up(pax, x=20.0, y=21.0, spacing=0.6)
    for squad in (rig_sq, pax):
        for m in squad.models:
            state.add_token(m)
    mc = MovementController(all_tokens=state.tokens)
    mc.moved_squad_ids.add(pax)
    tc = TransportController(
        setup_controller=None, game_state=state, all_tokens=state.tokens,
        movement_controller=mc, ingress_controller=None, dice_manager=None,
    )
    return tc.can_embark(pax, rig_sq.models[0])


c.eq("capacity", rig.profile.transport_capacity, 11)
c.eq("requires INFANTRY", rig.profile.transport_requires_infantry, True)
c.eq("requires BEAST SNAGGA", rig.profile.transport_requires, ("beast_snagga",))

c.eq("Beast Snagga Boyz may embark", can_carry(BEAST_SNAGGA_BOYZ, "BSB 1"), True)
c.eq("Beastboss may embark (BEAST SNAGGA INFANTRY too)", can_carry(BEASTBOSS, "Boss 1"), True)
c.eq("plain Boyz may NOT - INFANTRY, but not BEAST SNAGGA", can_carry(BOYZ, "Boyz 1"), False)
c.eq("Gretchin may not either", can_carry(GRETCHIN, "Grots 1"), False)
c.eq("a Trukk may not (not INFANTRY, and a TRANSPORT itself)", can_carry(TRUKK, "Trukk 1"), False)

# A/B: with the new requirement neutralised, plain Boyz WOULD fit - so the
# rejection above is really the BEAST SNAGGA half and not something else.
_saved = type(rig.profile).transport_requires
type(rig.profile).transport_requires = ()
c.eq("A/B: without the BEAST SNAGGA requirement, Boyz would fit",
     can_carry(BOYZ, "Boyz 2"), True)
type(rig.profile).transport_requires = _saved
c.eq("...and the requirement is back on", can_carry(BOYZ, "Boyz 3"), False)


# ---------------------------------------------------------------------------
# 3. Spirit of Gork: targeting and the strongest-unit rule
# ---------------------------------------------------------------------------

def gork_scene(distances, auto=True, owner="Player 2", comps=None):
    """A Kill Rig plus one friendly unit per (sheet, distance, name) entry.
    `comps` maps a unit name to a composition_index for the larger builds."""
    comps = comps or {}
    state = GameState()
    rig_sq = build(KILL_RIG, owner, name="Kill Rig 1")
    rig_sq.models[0].x_in, rig_sq.models[0].y_in = 20.0, 20.0
    state.add_token(rig_sq.models[0])
    friends = []
    for i, (sheet, dist, nm) in enumerate(distances):
        sq = build(sheet, owner, name=nm, composition_index=comps.get(nm, 0))
        line_up(sq, x=20.0 + i * 0.1, y=20.0 + dist, spacing=1.0)
        for m in sq.models:
            state.add_token(m)
        friends.append(sq)
    log, dice, dec = Log(), RecordingDice(), DecisionManager()
    ctrl = sog.SpiritOfGorkController(
        dice_manager=dice, decision_manager=dec, game_log=log,
        all_tokens=state.tokens, auto_players=("Player 2",) if auto else (),
    )
    return dict(state=state, rig=rig_sq, friends=friends, ctrl=ctrl,
                dice=dice, decision=dec, log=log)


# The Kill Rig itself is 145 pts and its own unit IS eligible (the rule does
# not exclude it), so a friend only wins the ranking by costing more - hence
# the 6-model Meganobz build (180 pts) rather than a cheap mob.
near = gork_scene([
    (BEAST_SNAGGA_BOYZ, 5.0, "BSB near"),      # 90 pts
    (STORMBOYZ, 8.0, "Stormboyz near"),        # 65 pts (5-model build)
    (GRETCHIN, 30.0, "Grots far"),             # out of range
])
targets = near["ctrl"].eligible_targets(near["rig"])
names = sorted(t.name for t in targets)
c.true("units within 12\" are eligible", "BSB near" in names and "Stormboyz near" in names)
c.true("a unit 30\" away is not", "Grots far" not in names)
c.true("the Kill Rig's own unit is eligible too (the rule does not exclude it)",
       "Kill Rig 1" in names)

# Ranking with no caster given: the Kill Rig's own 145 pts wins outright.
c.eq("raw ranking still puts the priciest first",
     near["ctrl"].strongest(targets).name, "Kill Rig 1")
# But the AI is told to prefer the strongest OTHER unit (user instruction),
# so with a caster given it skips itself even though it is worth more.
c.eq("the AI prefers the strongest OTHER unit over itself",
     near["ctrl"].strongest(targets, caster=near["rig"]).name, "BSB near")
# ...and falls back to itself when nothing else is eligible.
alone = gork_scene([])
alone_targets = alone["ctrl"].eligible_targets(alone["rig"])
c.eq("with no other unit in range, only itself is eligible",
     [t.name for t in alone_targets], ["Kill Rig 1"])
c.eq("...so it falls back to buffing itself",
     alone["ctrl"].strongest(alone_targets, caster=alone["rig"]).name, "Kill Rig 1")
richer = gork_scene([(MEGANOBZ, 5.0, "Meganobz near")], comps={"Meganobz near": 1})
c.eq("a friend worth more than the caster wins the ranking",
     richer["ctrl"].strongest(richer["ctrl"].eligible_targets(richer["rig"])).name,
     "Meganobz near")

# Enemies are never eligible, however close.
enemy = gork_scene([(BEAST_SNAGGA_BOYZ, 4.0, "Mine")])
foe = build(STRIKE_TEAM, "Player 1", name="Theirs")
line_up(foe, x=20.0, y=22.0)
for m in foe.models:
    enemy["state"].add_token(m)
c.true("an enemy unit within 12\" is not eligible",
       "Theirs" not in [t.name for t in enemy["ctrl"].eligible_targets(enemy["rig"])])

# A non-ORKS friendly unit is not eligible either ("friendly ORKS unit").
mixed = gork_scene([(BEAST_SNAGGA_BOYZ, 4.0, "Orky")])
tau = build(STRIKE_TEAM, "Player 2", name="Not Orky")
line_up(tau, x=20.0, y=23.0)
for m in tau.models:
    mixed["state"].add_token(m)
c.true("a friendly non-ORKS unit is not eligible",
       "Not Orky" not in [t.name for t in mixed["ctrl"].eligible_targets(mixed["rig"])])

# points=None must not crash the ranking.
class _NoPoints:
    pass


unpriced = build(BEAST_SNAGGA_BOYZ, name="Unpriced")
unpriced.points = None
priced = build(BEAST_SNAGGA_BOYZ, name="Priced")
c.eq("a unit with no published points sorts last",
     near["ctrl"].strongest([unpriced, priced]).name, "Priced")


# ---------------------------------------------------------------------------
# 4. Spirit of Gork: the AI resolves it deterministically, no prompt
# ---------------------------------------------------------------------------

# Both friends cost LESS than the Kill Rig's own 145 pts on purpose: a pick
# that ranked the caster in would take the rig itself here, so this scene
# actually discriminates the "strongest OTHER unit" rule.
auto = gork_scene([(BEAST_SNAGGA_BOYZ, 5.0, "Strong"),   # 90 pts
                   (STORMBOYZ, 6.0, "Weak")],            # 65 pts
                  auto=True)
script(4)  # a 2-5 result
took = auto["ctrl"].start_of_fight_phase([auto["rig"]])
c.eq("the AI takes the dice without being asked", took, True)
c.eq("...and raises NO prompt", auto["decision"].is_pending, False)
auto["dice"].acknowledge()
auto["ctrl"].on_dice_acknowledged()
strong = next(f for f in auto["friends"] if f.name == "Strong")
weak = next(f for f in auto["friends"] if f.name == "Weak")
c.eq("the strongest OTHER unit got the buff", strong.spirit_of_gork_strength, True)
c.eq("the Kill Rig did not buff itself while a friend was eligible",
     auto["rig"].spirit_of_gork_strength, False)
c.eq("the weaker one did not", getattr(weak, "spirit_of_gork_strength", False), False)
c.eq("a 2-5 grants no [LETHAL HITS]", getattr(strong, "spirit_of_gork_lethal", False), False)
c.true("and it is logged", auto["log"].has("Spirit of Gork"))

# A 6 grants both halves.
six = gork_scene([(MEGANOBZ, 5.0, "Strong")], auto=True, comps={"Strong": 1})
script(6)
six["ctrl"].start_of_fight_phase([six["rig"]])
six["dice"].acknowledge()
six["ctrl"].on_dice_acknowledged()
tgt = six["friends"][0]
c.eq("a 6 grants +1 Strength", tgt.spirit_of_gork_strength, True)
c.eq("...and [LETHAL HITS]", tgt.spirit_of_gork_lethal, True)

# A 1 backfires onto the Kill Rig, via a second D3 roll.
one = gork_scene([(MEGANOBZ, 5.0, "Strong")], auto=True, comps={"Strong": 1})
script(1, 3)  # the D6 comes up 1, then the D3 comes up 3
one["ctrl"].start_of_fight_phase([one["rig"]])
one["dice"].acknowledge()
one["ctrl"].on_dice_acknowledged()          # resolves the D6, starts the D3
c.true("a 1 starts a second (D3) roll", one["ctrl"].is_busy)
c.eq("the second roll is a D3", one["dice"].last_roll[1] and one["dice"].sides, 3)
one["dice"].acknowledge()
one["ctrl"].on_dice_acknowledged()          # resolves the D3
c.eq("the Kill Rig took the mortal wounds", one["rig"].models[0].current_wounds, 16 - 3)
c.eq("and the target got nothing",
     getattr(one["friends"][0], "spirit_of_gork_strength", False), False)
c.true("the backlash is logged", one["log"].has("backlash"))

# Once per phase per Kill Rig.
again = gork_scene([(MEGANOBZ, 5.0, "Strong")], auto=True, comps={"Strong": 1})
script(4)
again["ctrl"].start_of_fight_phase([again["rig"]])
again["dice"].acknowledge()
again["ctrl"].on_dice_acknowledged()
c.eq("a second call in the same phase does nothing",
     again["ctrl"].start_of_fight_phase([again["rig"]]), False)

# "Until the end of the phase".
target_squad = again["friends"][0]
c.eq("the buff is up", target_squad.spirit_of_gork_strength, True)
again["ctrl"].reset_phase([target_squad])
c.eq("reset_phase clears it", target_squad.spirit_of_gork_strength, False)
c.eq("...and re-arms the once-per-phase counter",
     again["ctrl"].start_of_fight_phase([again["rig"]]), True)


# ---------------------------------------------------------------------------
# 5. A human is asked instead
# ---------------------------------------------------------------------------

human = gork_scene([(MEGANOBZ, 5.0, "Strong"), (STORMBOYZ, 6.0, "Weak")],
                   auto=False, owner="Player 1", comps={"Strong": 1})
human["ctrl"].auto_players = set()
took = human["ctrl"].start_of_fight_phase([human["rig"]])
labels = options_of(human["decision"])
c.eq("a human gets a prompt", human["decision"].is_pending, True)
c.true("every eligible unit is offered", any("Strong" in l for l in labels) and any("Weak" in l for l in labels))
c.true("declining is possible - the rule says \"can\"", any("Decline" in l for l in labels))
c.true("the strongest is listed first", labels[0].endswith("Strong"))
c.eq("no dice are thrown until a choice is made", len(human["dice"].rolled), 0)
script(4)
pick_option(human["decision"], "Strong")
c.eq("choosing rolls the D6", len(human["dice"].rolled), 1)
human["dice"].acknowledge()
human["ctrl"].on_dice_acknowledged()
c.eq("and the chosen unit is buffed",
     next(f for f in human["friends"] if f.name == "Strong").spirit_of_gork_strength, True)

declined = gork_scene([(MEGANOBZ, 5.0, "Strong")], auto=False, owner="Player 1", comps={"Strong": 1})
declined["ctrl"].auto_players = set()
declined["ctrl"].start_of_fight_phase([declined["rig"]])
pick_option(declined["decision"], "Decline")
c.eq("declining throws nothing", len(declined["dice"].rolled), 0)
c.eq("...and grants nothing",
     getattr(declined["friends"][0], "spirit_of_gork_strength", False), False)


# ---------------------------------------------------------------------------
# 6. The effect, end to end through the real fight chain
#
# The observable has to be a real outcome, not a label: Beast Snagga Choppas
# are S5, the target (Boyz) is T5, so unbuffed they wound on 4+ and buffed
# (S6) on 3+. Scripting every wound die as a 3 therefore separates the two
# completely - 0 wounds without the buff, all of them with it.
# ---------------------------------------------------------------------------

def swing_choppas(strength_buff, lethal_buff, wound_face):
    scene = fight_scene(BEAST_SNAGGA_BOYZ, BOYZ)
    scene["attacker"].spirit_of_gork_strength = strength_buff
    scene["attacker"].spirit_of_gork_lethal = lethal_buff
    fc = scene["fight"]
    fc.select_to_fight(scene["attacker"])
    if fc.state == "choosing_target":
        fc.choose_target_squad(scene["target"])
    key = next(k for k, *rest in fc.weapon_eligibility() if "Choppa" in str(rest[0]))
    script(*([6] * 40))          # every hit roll succeeds
    fc.choose_weapon(key)
    fc.dice_manager.acknowledge()
    script(*([wound_face] * 40))  # now the wound roll
    fc.on_dice_acknowledged()
    fc.dice_manager.acknowledge()
    fc.on_dice_acknowledged()
    return scene


def wounds_in(scene):
    line = scene["log"].find("wound roll")
    try:
        return int(line.split(": ", 1)[1].split(" wound(s)")[0])
    except (IndexError, ValueError):
        return None


plain = swing_choppas(False, False, 3)
buffed = swing_choppas(True, False, 3)
c.eq("without the buff, S5 vs T5 needs a 4+ - threes fail", wounds_in(plain), 0)
c.true("with +1 Strength the same threes wound", (wounds_in(buffed) or 0) > 0)
c.true("both runs really reached the wound step",
       plain["log"].has("wound roll") and buffed["log"].has("wound roll"))

# [LETHAL HITS] (24.23) turns a critical HIT straight into a wound, skipping
# the wound roll for it entirely. With every hit critical that is a total
# difference: without the keyword the engine rolls to wound (and all 1s
# produce nothing), with it there is no wound roll left to make.
lethal = swing_choppas(True, True, 1)
no_lethal = swing_choppas(True, False, 1)
c.true("without [LETHAL HITS] a wound roll happens...", no_lethal["log"].has("wound roll"))
c.eq("...and all 1s produce nothing", wounds_in(no_lethal), 0)
c.eq("with [LETHAL HITS] the critical hits skip the wound roll entirely",
     lethal["log"].has("wound roll"), False)


# The adjuster itself, directly - no mutation of the shared instance.
boy = build(BEAST_SNAGGA_BOYZ, name="Adj").models[1]
choppa = next(w for w in boy.weapons if w.weapon_type == "melee")
base_strength = choppa.strength


class _Flagged:
    spirit_of_gork_strength = True
    spirit_of_gork_lethal = True


boosted = sog.spirit_of_gork_adjusted_weapon(choppa, _Flagged())
c.eq("+1 Strength", boosted.strength, base_strength + 1)
c.eq("[LETHAL HITS] granted", boosted.lethal_hits, True)
c.eq("the base instance is untouched", choppa.strength, base_strength)
c.eq("...including its keyword", choppa.lethal_hits, False)

wurrtower = next(w for w in build(KILL_RIG, name="R").models[0].weapons if w.name == "Wurrtower")
c.true("MELEE only - a ranged weapon is returned untouched",
       sog.spirit_of_gork_adjusted_weapon(wurrtower, _Flagged()) is wurrtower)


class _Unflagged:
    spirit_of_gork_strength = False
    spirit_of_gork_lethal = False


c.true("no buff -> the weapon is returned untouched",
       sog.spirit_of_gork_adjusted_weapon(choppa, _Unflagged()) is choppa)

# 19.04: the caster's ability dies with it.
dead_rig = build(KILL_RIG, name="Dead Rig")
dead_rig.models[0].current_wounds = 0
c.eq("a destroyed Kill Rig casts nothing", sog.unit_has_spirit_of_gork(dead_rig), False)
c.eq("...and offers no targets",
     sog.SpiritOfGorkController(all_tokens=[]).eligible_targets(dead_rig), [])

c.finish()
