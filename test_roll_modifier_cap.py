"""Hit and Wound roll modifiers are capped at +/-1 as a SUM, characteristic
modifiers are not, and no roll ever needs less than a 2 (game/modifiers.py).

User report: "wenn etwas +1 oder -1 auf hit oder wound gibt, dann kann diese
modifikation maximal 1 vom ursprungswert abweichen. es stackt also nicht.
beispiel: 3+ hit / -1 = 4+ hit / -2 = 4+ hit ... aber modifikatoren koennen
sich gegenseitig neutralisieren ... +1 und -2 = 4+ hit ... 1+ gibt es nicht
das beste moegliche ist immer 2+". And: "das betrifft hit und wound roll, aber
modifikationen auf werte zb. Ballistic Skill werden extra behandelt. Zb Cover".

Real engine objects throughout (testkit's scenes, real datasheets, scripted
dice). Sections:

  1. The arithmetic - the user's own examples, in ROLL terms.
  2. What the log and the dice panel say when the cap bites.
  3. A real hit roll in the Shooting phase, A/B on the SAME dice.
  4. A real hit roll in the Fight phase, A/B on the same dice.
  5. The AI's damage estimate folds the same way.
  6. Source guards: every Modifier in the engine is classified, and nobody
     sums Modifier amounts outside game/modifiers.py.
"""

import ast
import glob
import os
from collections import Counter

import testkit as tk
from testkit import script

from game import damage_estimate
from game.factions import orks as O
from game.factions import tau_empire as T
from game.modifiers import (
    BEST_THRESHOLD, CHARACTERISTIC, ROLL, ROLL_CAP_LABEL, Modifier,
    apply_modifiers, describe_modifiers, for_display, net_roll_modifier,
)

c = tk.Checks("roll modifier cap")
ROOT = os.path.dirname(os.path.abspath(__file__))


def to_hit(amount_in_roll_terms, source="x"):
    """A Hit/Wound ROLL modifier written the way the card prints it: +1 is
    "add 1 to the Hit roll". The engine's Modifier adjusts the THRESHOLD, so
    the sign flips."""
    return Modifier(-amount_in_roll_terms, source)


def char(amount_in_roll_terms, source="characteristic"):
    """"Improve (+1) / worsen (-1) the Ballistic Skill characteristic by 1"."""
    return Modifier(-amount_in_roll_terms, source, CHARACTERISTIC)


# --- 1. The arithmetic ------------------------------------------------------
print("\n1. The arithmetic - the user's examples")

c.eq("3+ with -1 to hit is 4+", apply_modifiers(3, [to_hit(-1)]), 4)
c.eq("3+ with -1 and -1 to hit is STILL 4+ (does not stack)",
     apply_modifiers(3, [to_hit(-1, "a"), to_hit(-1, "b")]), 4)
c.eq("3+ with +1 and -1 and -1 is 4+ (they cancel first, then the cap)",
     apply_modifiers(3, [to_hit(+1, "a"), to_hit(-1, "b"), to_hit(-1, "c")]), 4)
c.eq("3+ with +1 and -1 cancel to 3+",
     apply_modifiers(3, [to_hit(+1, "a"), to_hit(-1, "b")]), 3)
c.eq("3+ with +1 and +1 is 2+ - the best a 3+ can become",
     apply_modifiers(3, [to_hit(+1, "a"), to_hit(+1, "b")]), 2)
c.eq("3+ with -1 x3 is 4+ - the worst a 3+ can become through the roll",
     apply_modifiers(3, [to_hit(-1, "a"), to_hit(-1, "b"), to_hit(-1, "c")]), 4)
c.eq("+2 and -1 net +1: 4+ becomes 3+",
     apply_modifiers(4, [to_hit(+1, "a"), to_hit(+1, "b"), to_hit(-1, "c")]), 3)

print("   1+ does not exist")
c.eq("2+ with +1 to hit stays 2+, never 1+", apply_modifiers(2, [to_hit(+1)]), 2)
c.eq("the floor is the module's own constant", BEST_THRESHOLD, 2)
c.eq("2+ with an improved characteristic AND +1 to hit is still 2+",
     apply_modifiers(2, [char(+1), to_hit(+1)]), 2)
c.eq("3+ Guided (improve BS) plus the Guide (+1 to hit) is 2+, not 1+",
     apply_modifiers(3, [char(+1, "Guided"), to_hit(+1, "Guide")]), 2)

print("   characteristic modifiers are handled separately (Benefit of Cover)")
c.eq("3+ in cover (worsen BS) with no roll modifier is 4+",
     apply_modifiers(3, [char(-1, "Benefit of Cover")]), 4)
c.eq("3+ in cover with -1 and -1 to hit is 5+ - cover in full, the roll capped",
     apply_modifiers(3, [char(-1, "Benefit of Cover"), to_hit(-1, "a"), to_hit(-1, "b")]), 5)
c.eq("two characteristic changes are NOT capped: 3+ worsened twice is 5+",
     apply_modifiers(3, [char(-1, "a"), char(-1, "b")]), 5)
c.eq("a characteristic improvement does not cancel against the roll cap: "
     "3+ improved, with -1 -1 to hit, is 3+",
     apply_modifiers(3, [char(+1, "Guided"), to_hit(-1, "a"), to_hit(-1, "b")]), 3)
c.eq("net_roll_modifier ignores characteristic entries",
     net_roll_modifier([char(-1), char(-1), to_hit(+1)]), -1)

print("   the Wound roll obeys the same cap")
c.eq("S=T wounds on 4+; +1 +1 to wound (Doom, [LANCE]) is 3+",
     apply_modifiers(4, [to_hit(+1, "Doom"), to_hit(+1, "[LANCE]")]), 3)
c.eq("4+ with -1 -1 to wound (Protect, Guardian Drone) is 5+",
     apply_modifiers(4, [to_hit(-1, "Protect"), to_hit(-1, "Guardian Drone")]), 5)

print("   edges")
c.eq("no modifiers leaves the threshold alone", apply_modifiers(5, []), 5)
c.eq("a 6+ worsened stays 7+ (an unmodified 6 still succeeds in _resolve_roll)",
     apply_modifiers(6, [to_hit(-1)]), 7)
c.eq("a '-' characteristic stays None", apply_modifiers(None, [to_hit(+1)]), None)
try:
    Modifier(1, "typo", "charactersitic")
    c.true("a misspelt kind is refused", False)
except ValueError:
    c.true("a misspelt kind is refused", True)
c.eq("ROLL is the default kind", Modifier(1, "x").kind, ROLL)


# --- 2. Log and dice panel --------------------------------------------------
print("\n2. What the log and the panel say")

two_minus = [to_hit(-1, "Damaged"), to_hit(-1, "Suppressed")]
c.eq("the log names the cap when it bites",
     describe_modifiers(two_minus),
     "+1 (Damaged), +1 (Suppressed); roll modifiers +2 capped at +1")
c.eq("...and says nothing extra when it does not",
     describe_modifiers([to_hit(-1, "Damaged"), char(-1, "Benefit of Cover")]),
     "+1 (Damaged), +1 (Benefit of Cover)")
c.eq("the panel shows the correction as its LAST row, in player terms",
     for_display(two_minus),
     ((-1, "Damaged"), (-1, "Suppressed"), (+1, ROLL_CAP_LABEL)))
c.eq("...a helpful stack is corrected downwards",
     for_display([to_hit(+1, "Guide"), to_hit(+1, "[HEAVY]")]),
     ((+1, "Guide"), (+1, "[HEAVY]"), (-1, ROLL_CAP_LABEL)))
c.eq("...no row when a characteristic modifier is what exceeds one step",
     for_display([char(-1, "Benefit of Cover"), to_hit(-1, "Damaged")]),
     ((-1, "Benefit of Cover"), (-1, "Damaged")))
c.eq("...and none for an additive roll's (delta, source) pairs (a Charge roll)",
     for_display([(1, "a"), (1, "b")], lower_is_better=False), ((1, "a"), (1, "b")))


# --- 3. The Shooting phase --------------------------------------------------
print("\n3. A real hit roll in the Shooting phase")

# A Ghostkeel (BS 4+) with 1-4 wounds left takes its own printed "Damaged:
# subtract 1 from the Hit roll"; a target under Lightning-Fast Reactions
# adds "subtract 1 from the Hit roll" from the defender's side. Two -1s.
def shoot(target_sheet, damaged, lfr, dice):
    scene = tk.shooting_scene(T.GHOSTKEEL_BATTLESUIT, target_sheet, gap=10.0)
    sc, dm = scene["shooting"], scene["dice"]
    if damaged:
        scene["attacker"].models[0].current_wounds = 4
    scene["target"].lightning_fast_reactions_active = lfr
    sc.start_shooting(scene["attacker"])
    sc.choose_target_squad(scene["target"])
    key = next(e[0] for e in sc.weapon_eligibility() if e[1] == "Fusion Collider")
    script(*dice)
    sc.choose_weapon(key)
    threshold, shown = dm.success_threshold, dm.shown_modifiers
    label = scene["dice"].last_roll[0]
    values = list(dm.pending_values or ())
    script(default=1)
    dm.acknowledge()
    sc.on_dice_acknowledged()
    line = scene["log"].find("Fusion Collider hit roll")
    return dict(threshold=threshold, shown=shown, label=label, values=values, line=line)


plain = shoot(T.STRIKE_TEAM, damaged=False, lfr=False, dice=(5, 5))
c.eq("baseline: an undamaged Ghostkeel hits the Strike Team on its BS 4+", plain["threshold"], 4)

one = shoot(T.STRIKE_TEAM, damaged=True, lfr=False, dice=(5, 5))
c.eq("one -1 (Damaged): 5+", one["threshold"], 5)

both = shoot(T.STRIKE_TEAM, damaged=True, lfr=True, dice=(5, 5))
c.eq("the reported case, two -1s (Damaged + Lightning-Fast Reactions): STILL 5+ "
     "(was 6+ before the cap)", both["threshold"], 5)
c.eq("the dice really were the scripted 5s", both["values"], [5, 5])
c.true("...and both 5s HIT - under the old 6+ they missed", "2 hit(s)" in both["line"])
c.true("the log line says why: base 4+, both sources, and the cap",
       "needed 5+: base 4+, +1 (Damaged), +1 (Lightning-Fast Reactions); "
       "roll modifiers +2 capped at +1" in both["line"])
c.true("the dice label carries the same explanation", "capped at +1" in both["label"])
c.eq("the panel lists both maluses and the correction",
     both["shown"],
     ((-1, "Damaged"), (-1, "Lightning-Fast Reactions"), (+1, ROLL_CAP_LABEL)))

# Kroot Carnivores have the Benefit of Cover here - a CHARACTERISTIC change,
# which the user named as handled separately. It applies in full on top.
kroot = shoot(T.KROOT_CARNIVORES, damaged=True, lfr=True, dice=(5, 5))
c.true("the Kroot really are in cover (else this proves nothing)",
       any(src == "Benefit of Cover" for _d, src in kroot["shown"]))
c.eq("cover (worsen BS, +1) PLUS the capped roll (+1): 4+ becomes 6+", kroot["threshold"], 6)
c.true("...so the same 5s now miss", "0 hit(s)" in kroot["line"])


# --- 4. The Fight phase -----------------------------------------------------
print("\n4. A real hit roll in the Fight phase")

# Boyz (WS 3+) into a Strike Team that is Forewarned ("subtract 1 from the Hit
# roll and subtract 1 from the Wound roll") and under Lightning-Fast Reactions
# (whose WHEN names both attack phases).
def fight(flags, dice):
    scene = tk.fight_scene(O.BOYZ, T.STRIKE_TEAM, attacker_owner="Player 2")
    for flag in flags:
        setattr(scene["target"], flag, True)
    fc, dm = scene["fight"], scene["dice"]
    script(*dice)
    fc.select_to_fight(scene["attacker"])
    if not dm.pending_values and fc.remaining_weapon_types:
        fc.choose_weapon(sorted(fc.remaining_weapon_types)[0])
    threshold, kind = dm.success_threshold, dm.roll_kind
    script(default=4)
    dm.acknowledge()
    fc.on_dice_acknowledged()
    return dict(threshold=threshold, kind=kind, line=scene["log"].find("hit roll"),
                wound_threshold=dm.success_threshold if dm.roll_kind == "wound" else None)


f_plain = fight((), dice=[4] * 4)
c.eq("baseline: the Boyz hit on their WS 3+", f_plain["threshold"], 3)
c.eq("...and it is the hit roll being read", f_plain["kind"], "hit")
f_one = fight(("forewarned_active",), dice=[4] * 4)
c.eq("Forewarned alone: 4+", f_one["threshold"], 4)
f_both = fight(("forewarned_active", "lightning_fast_reactions_active"), dice=[4] * 4)
c.eq("Forewarned + Lightning-Fast Reactions: STILL 4+ (was 5+ before the cap)",
     f_both["threshold"], 4)
c.true("...so four scripted 4s are four hits", "4 hit(s)" in f_both["line"])
c.true("...and the log says the cap bit", "roll modifiers +2 capped at +1" in f_both["line"])
c.eq("the wound roll has only Forewarned's -1 and is uncapped by it: S5 vs T3 3+ -> 4+",
     f_both["wound_threshold"], 4)


# --- 5. The AI's estimate ---------------------------------------------------
print("\n5. The damage estimate folds the same way")

_real = damage_estimate.tank_hunters_modifiers
try:
    damage_estimate.tank_hunters_modifiers = lambda *a, **k: [to_hit(+1, "a"), to_hit(+1, "b")]
    shooter = tk.build(T.GHOSTKEEL_BATTLESUIT).models[0]
    c.eq("two +1s reach attack_modifiers() as one step on each roll",
         damage_estimate.attack_modifiers(shooter, tk.build(T.STRIKE_TEAM), melee=True), (-1, -1))
finally:
    damage_estimate.tank_hunters_modifiers = _real


# --- 6. Source guards ---------------------------------------------------------
print("\n6. Source guards")

# EVERY Modifier construction in the engine, keyed (file, label) - a string
# label by its text, anything else by its source expression. Two lists, and
# the SUM of them must be exactly what the code constructs:
#
#   * a NEW Modifier fails here until someone has read the printed text and
#     put it on one of the lists - "add/subtract 1 to/from the Hit/Wound roll"
#     or "+1 to hit rolls" is ROLL; "improve/worsen the Ballistic Skill /
#     Weapon Skill characteristic" is CHARACTERISTIC and must pass that kind;
#   * a REMOVED one leaves a stale entry, which fails too, so the lists stay a
#     true statement about the code.
CHARACTERISTIC_SITES = [
    ("game/shooting.py", "Benefit of Cover"),                                    # 13.08
    ("game/shooting.py", "Close-Quarters (non-[CLOSE-QUARTERS] weapon)"),        # 10.06
    ("game/shooting.py", "Close-Quarters (target not engaged with this unit)"),  # 10.06
    ("game/shooting.py", "For the Greater Good (Guided)"),
    ("game/shooting.py", "Target Uploaded"),
    ("game/shooting.py", "Coordinate to Engage"),
    ("game/shooting.py", "Psychic Guidance"),  # the Wraithlord's half
    ("game/fight.py", "Psychic Guidance"),     # the Wraithlord's half
]
ROLL_SITES = [
    ("game/armour_hunter.py", "ARMOUR_HUNTER_LABEL"),
    ("game/awakened_dynasty.py", "COMMAND_PROTOCOLS_LABEL"),
    ("game/beastscent.py", "BEASTSCENT_NAME"),
    ("game/boss_ammo_runt.py", "BOSS_AMMO_RUNT_NAME"),
    ("game/court_curse_of_the_cryptek.py", "CURSE_OF_THE_CRYPTEK_NAME"),  # hit
    ("game/court_curse_of_the_cryptek.py", "CURSE_OF_THE_CRYPTEK_NAME"),  # wound
    ("game/damage_estimate.py", "Guardian Drone"),
    ("game/defend_at_all_costs.py", "DEFEND_AT_ALL_COSTS_LABEL"),
    ("game/deff_from_above.py", "DEFF_FROM_ABOVE_NAME"),
    ("game/destroyer_hive.py", "DESTROYER_HIVE_LABEL"),
    ("game/dodge_dis.py", "DODGE_DIS_NAME"),
    ("game/enh_precision_patient_hunter.py", "LABEL"),
    ("game/enh_precision_patient_hunter.py", "f'{LABEL} (round {WOUND_BONUS_FROM_ROUND}+)'"),
    ("game/fight.py", "Psychic Guidance"),  # the Wraithguard's half
    ("game/fight.py", "corsair_abilities.PIRATICAL_HERO_LABEL"),
    ("game/fight.py", "Forewarned"),  # hit
    ("game/fight.py", "Forewarned"),  # wound
    ("game/fight.py", "Guide"),
    ("game/fight.py", "Suppressed"),
    ("game/fight.py", "enh_mirage_field.MIRAGE_FIELD_LABEL"),
    ("game/fight.py", "Protect"),
    ("game/fight.py", "Doom"),
    ("game/fight.py", "[LANCE] (charged)"),
    ("game/fight.py", "misfortune_module.MISFORTUNE_LABEL"),
    ("game/guardian_shield_nodes.py", "SHIELD_NODES_NAME"),
    ("game/harassment_swarm.py", "HARASSMENT_SWARM_LABEL"),
    ("game/krumpin_time.py", "KRUMPIN_TIME_NAME"),
    ("game/ork_ammo_runts.py", "AMMO_RUNTS_NAME"),
    ("game/plagues.py", "Skullsquirm Blight"),
    ("game/prophet_of_da_great_waaagh.py", "PROPHET_NAME"),  # "+1 to hit rolls"
    ("game/prophet_of_da_great_waaagh.py", "PROPHET_NAME"),  # "+1 to wound rolls"
    ("game/shepherds_of_the_dead.py", "VENGEFUL_DEAD_LABEL"),  # hit
    ("game/shepherds_of_the_dead.py", "VENGEFUL_DEAD_LABEL"),  # wound
    ("game/shooting.py", "Damaged"),  # the model's own tier
    ("game/shooting.py", "Damaged"),  # The Silent King's unit-wide tier
    ("game/shooting.py", "Psychic Guidance"),  # the Wraithguard's half
    ("game/shooting.py", "corsair_abilities.PIRATICAL_HERO_LABEL"),
    ("game/shooting.py", "Guide"),
    ("game/shooting.py", "Suppressed"),
    ("game/shooting.py", "[HEAVY] (stationary)"),
    ("game/shooting.py", "enh_mirage_field.MIRAGE_FIELD_LABEL"),
    ("game/shooting.py", "enh_guiding_presence.GUIDING_PRESENCE_LABEL"),
    ("game/shooting.py", "Guardian Drone"),
    ("game/shooting.py", "misfortune_module.MISFORTUNE_LABEL"),
    ("game/shooting.py", "Advanced Guardian Drone"),
    ("game/shooting.py", "Protect"),
    ("game/shooting.py", "Doom"),
    ("game/shooting.py", "structural_analyser_module.STRUCTURAL_ANALYSER_LABEL"),
    ("game/shooting.py", "enh_shimmerstone.SHIMMERSTONE_LABEL"),
    ("game/shooting.py", "kauyon_tempting_trap.TEMPTING_TRAP_NAME"),
    ("game/squad.py", "Tank Hunters (MONSTER/VEHICLE)"),
    ("game/strength_over_toughness.py", "shield.label"),
    ("game/sumfin_to_prove.py", "SUMFIN_TO_PROVE_NAME"),
    ("game/timesplinter_mantle.py", "LABEL"),
    ("game/warhost_lightning_fast_reactions.py", "LIGHTNING_FAST_REACTIONS_NAME"),
    ("game/way_of_the_short_blade.py", "Way of the Short Blade"),
]


def _sources():
    paths = glob.glob(os.path.join(ROOT, "game", "**", "*.py"), recursive=True)
    paths += glob.glob(os.path.join(ROOT, "ai", "**", "*.py"), recursive=True)
    paths.append(os.path.join(ROOT, "main.py"))
    for path in sorted(paths):
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        if rel == "game/modifiers.py":
            continue
        with open(path, encoding="utf-8") as handle:
            yield rel, ast.parse(handle.read())


def _kind_of(call):
    node = call.args[2] if len(call.args) > 2 else next(
        (k.value for k in call.keywords if k.arg == "kind"), None)
    if node is None:
        return ROLL
    text = ast.unparse(node)
    if text.endswith("CHARACTERISTIC"):
        return CHARACTERISTIC
    if text.endswith("ROLL"):
        return ROLL
    return f"<unreadable kind {text}>"


def _label_of(call):
    node = call.args[1] if len(call.args) > 1 else next(
        (k.value for k in call.keywords if k.arg == "source"), None)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ast.unparse(node) if node is not None else "<no label>"


found = Counter()
where = {}
amount_sums = []
for rel, tree in _sources():
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "id", getattr(node.func, "attr", None)) == "Modifier"):
            key = (rel, _label_of(node), _kind_of(node))
            found[key] += 1
            where.setdefault(key, node.lineno)
        # A Modifier's amount may be COMPARED (the ignore-modifier filters keep
        # the `m.amount <= 0` ones) but never added up: a hand-rolled sum is
        # exactly the fold this module replaces, and it would skip the cap.
        # `self.amount` is some other class's own field (Feel No Pain, CP).
        if (isinstance(node, ast.Attribute) and node.attr == "amount"
                and not (isinstance(node.value, ast.Name) and node.value.id == "self")
                and not isinstance(parents.get(node), ast.Compare)):
            amount_sums.append(f"{rel}:{node.lineno}")

expected = Counter([(f, l, CHARACTERISTIC) for f, l in CHARACTERISTIC_SITES]
                   + [(f, l, ROLL) for f, l in ROLL_SITES])
unlisted = found - expected
stale = expected - found
c.eq("every Modifier construction is classified - a new one needs its printed "
     "text read: ROLL ('... to the Hit/Wound roll') or CHARACTERISTIC "
     "('improve/worsen the ... characteristic', pass CHARACTERISTIC)",
     sorted(f"{f}:{where.get((f, l, k), '?')} {l!r} as {k}" for (f, l, k) in unlisted), [])
c.eq("...and no listed site is gone or has changed kind", sorted(stale), [])
# 54 at the cap's own stage, +2 for Ghazghkull's Prophet of da Great Waaagh!
# (Mecha Orks G2: "+1 to hit rolls", "+1 to wound rolls").
c.eq("the lists hold 8 characteristic and 56 roll sites",
     (len(CHARACTERISTIC_SITES), len(ROLL_SITES)), (8, 56))
c.eq("nobody reads a Modifier's amount except to COMPARE it (no hand-rolled sums)",
     amount_sums, [])

c.finish()
