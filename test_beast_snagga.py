"""Beast Snagga Boyz (Orks) - datasheet, weapons, and the Monster Hunters
Hit-roll re-roll in BOTH phases.

Run: python test_beast_snagga.py

Uses real build_squad() datasheets and real ShootingController/
FightController/DecisionManager/DiceManager objects; only the dice are
scripted, and only where the point of the check is what the numbers do.

The A/B checks matter most here: a "the re-roll happened" assertion proves
nothing on its own, because a re-roll that silently did nothing and a
re-roll that was never offered look the same from the outside. So every
Monster Hunters check is paired with the same scripted dice against a target
that is NOT a MONSTER/VEHICLE, or against a unit without the ability.
"""

import sys

from game import monster_hunters
from game.decision import DecisionManager
from game.dice import DiceManager
from game.dice_notation import describe as describe_dice_notation
from game.factions import build_squad
from game.factions.orks import BEAST_SNAGGA_BOYZ, BEAST_SNAGGA_BOYZ_THUMP_GUN, BOYZ, DEFF_DREAD, GRETCHIN
from game.factions.tau_empire import DEVILFISH, STRIKE_TEAM
from game.squad import is_monster_or_vehicle_unit

FAILURES = []
CHECKS = [0]


def check(label, got, want):
    CHECKS[0] += 1
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def check_true(label, got):
    check(label, bool(got), True)


def build(datasheet, owner="Player 2", choices=None, name=None, x=0.0, y=0.0):
    return build_squad(datasheet, owner, choices=choices, name=name or datasheet.name, x_in=x, y_in=y)


# ---------------------------------------------------------------------------
# 1. Datasheet: stat line, keywords, points, weapons
# ---------------------------------------------------------------------------

squad = build(BEAST_SNAGGA_BOYZ)
check("unit size", len(squad.models), 10)
check("points (10 models)", squad.points, 90)

nob = squad.models[0]
boy = squad.models[1]
check("nob is the leader model", nob.profile.squad_leader, True)
check("nob wounds", nob.profile.wounds, 2)
check("boy wounds", boy.profile.wounds, 1)
for label, p in (("nob", nob.profile), ("boy", boy.profile)):
    check(f"{label} move", p.movement_in, 6)
    check(f"{label} toughness", p.toughness, 5)
    check(f"{label} save", p.armor_save, "5+")
    check(f"{label} leadership", p.leadership, "7+")
    check(f"{label} OC", p.oc, 2)
    check(f"{label} WS", p.weapon_skill, "3+")
    check(f"{label} BS", p.ballistic_skill, "5+")
    check(f"{label} base radius (32mm)", round(p.base_radius_in, 2), 0.63)
    check(f"{label} INFANTRY", p.infantry, True)
    check(f"{label} Feel No Pain 6+", p.feel_no_pain, "6+")
    check(f"{label} Monster Hunters", p.monster_hunters, True)
    check(f"{label} Waaagh!", p.waaagh, True)
    check(f"{label} Orks faction flag", p.orks, True)
    # Keywords line has no GRENADES and no BEASTS - see the profile's note.
    check(f"{label} no GRENADES keyword", p.grenades, False)
    check(f"{label} no BEASTS keyword", p.beasts, False)

check("datasheet keywords", set(BEAST_SNAGGA_BOYZ.keywords),
      {"BATTLELINE", "INFANTRY", "MOB", "BEAST SNAGGA", "BEAST SNAGGA BOYZ"})

# Weapons: the printed numbers, and specifically the ones that differ from
# the same-named Ork weapons this file already had.
power_snappa = next(w for w in nob.weapons if w.name == "Power Snappa")
check("power snappa attacks", power_snappa.attacks, 4)
check("power snappa strength", power_snappa.strength, 7)
check("power snappa AP", power_snappa.ap, -1)
check("power snappa damage", power_snappa.damage, 2)

choppa = next(w for w in boy.weapons if w.name == "Choppa")
check("beast snagga choppa attacks", choppa.attacks, 3)
check("beast snagga choppa strength (S5, not Boyz' S4)", choppa.strength, 5)
check("beast snagga choppa AP", choppa.ap, -1)
check("beast snagga choppa damage", choppa.damage, 1)

slugga = next(w for w in boy.weapons if w.name == "Slugga")
check("slugga range", slugga.range_in, 12)
check("slugga strength", slugga.strength, 4)
check("slugga is a Pistol", slugga.pistol, True)

# The stat line looks identical to Boyz' but the Choppa does not - the check
# that the reuse was correctly NOT made.
boyz_choppa = next(w for w in build(BOYZ).models[1].weapons if w.name == "Choppa")
check("Boyz' own Choppa is still S4", boyz_choppa.strength, 4)
check_true("the two Choppas are different classes", type(choppa) is not type(boyz_choppa))

# ---------------------------------------------------------------------------
# 2. Thump gun wargear option
# ---------------------------------------------------------------------------

THUMP = {"Beast Snagga Boy": {BEAST_SNAGGA_BOYZ_THUMP_GUN: 1}}
tg_squad = build(BEAST_SNAGGA_BOYZ, choices=THUMP)
gunner = [m for m in tg_squad.models if any(w.name == "Thump Gun" for w in m.weapons)]
check("exactly one thump gun carrier", len(gunner), 1)
gunner = gunner[0]
check("gunner weapons", sorted(w.name for w in gunner.weapons), ["Close Combat Weapon", "Thump Gun"])
check_true("gunner gave up its Slugga", not any(w.name == "Slugga" for w in gunner.weapons))
check_true("gunner gave up its Choppa", not any(w.name == "Choppa" for w in gunner.weapons))
check("gunner keeps the datasheet stat line", gunner.profile.toughness, 5)
check("thump gun swap is free", tg_squad.points, 90)

thump = next(w for w in gunner.weapons if w.name == "Thump Gun")
check("thump gun range", thump.range_in, 18)
check("thump gun strength", thump.strength, 6)
check("thump gun AP", thump.ap, 0)
check("thump gun damage", thump.damage, 2)
check("thump gun has [BLAST]", thump.blast, 1)
check_true("thump gun Attacks is a real D3 roll", thump.attacks_notation is not None)
check("thump gun Attacks notation", describe_dice_notation(thump.attacks_notation), "D3")

ccw = next(w for w in gunner.weapons if w.name == "Close Combat Weapon")
check("gunner close combat weapon attacks", ccw.attacks, 2)
check("gunner close combat weapon strength (S5)", ccw.strength, 5)
check("gunner close combat weapon AP", ccw.ap, 0)

# The cap: over-eager choices are trimmed, same convention as every other
# datasheet's own options.
greedy = build(BEAST_SNAGGA_BOYZ, choices={"Beast Snagga Boy": {BEAST_SNAGGA_BOYZ_THUMP_GUN: 5}})
check("over-eager thump gun choice trimmed to 1",
      sum(1 for m in greedy.models if any(w.name == "Thump Gun" for w in m.weapons)), 1)
check("the Nob's line cannot take the thump gun",
      sum(1 for m in build(BEAST_SNAGGA_BOYZ, choices={"Beast Snagga Nob": {BEAST_SNAGGA_BOYZ_THUMP_GUN: 1}}).models
          if any(w.name == "Thump Gun" for w in m.weapons)), 0)

# The multi-weapon `replaces` this option introduced must not have changed
# how single-weapon options behave.
from game.factions.orks import BOYZ_BIG_CHOPPA_TO_POWER_KLAW  # noqa: E402
klaw_boyz = build(BOYZ, choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}})
klaw_nob = klaw_boyz.models[0]
check("single-weapon swap still drops only its own weapon",
      sorted(w.name for w in klaw_nob.weapons), ["Power Klaw", "Slugga"])

# ---------------------------------------------------------------------------
# 3. Monster Hunters: the applies() predicate
# ---------------------------------------------------------------------------

vehicle = build(DEVILFISH, owner="Player 1", name="Devilfish")
infantry = build(STRIKE_TEAM, owner="Player 1", name="Strike Team")
plain_boyz = build(BOYZ, name="Boyz")

check_true("target predicate agrees the Devilfish is a VEHICLE unit", is_monster_or_vehicle_unit(vehicle))
check("Monster Hunters vs a VEHICLE", monster_hunters.applies(squad, vehicle), True)
check("Monster Hunters vs INFANTRY", monster_hunters.applies(squad, infantry), False)
check("a unit without the ability gets nothing", monster_hunters.applies(plain_boyz, vehicle), False)
check("no attacker", monster_hunters.applies(None, vehicle), False)
check("no target", monster_hunters.applies(squad, None), False)

dead_squad = build(BEAST_SNAGGA_BOYZ)
for m in dead_squad.models:
    m.current_wounds = 0
check("ability dies with the models (19.04)", monster_hunters.applies(dead_squad, vehicle), False)
dead_squad.models[3].current_wounds = 1
check("one survivor is enough (19.04)", monster_hunters.applies(dead_squad, vehicle), True)


# ---------------------------------------------------------------------------
# 4. Monster Hunters in the SHOOTING phase, end to end
# ---------------------------------------------------------------------------

from game import dice as dice_mod  # noqa: E402

_scripted = []
_default = [1]  # what an unscripted die shows - 1 = a miss, so only the scripted dice matter


def _scripted_randint(low, high):
    return _scripted.pop(0) if _scripted else _default[0]


dice_mod.random.randint = _scripted_randint


class ScriptedDice(DiceManager):
    """Real DiceManager on top of the patched randint above (this engine
    generates its faces there, so that - not an overridden roll() - is where
    a test has to script them). Records what each roll actually asked for,
    so a check can assert on the dice the ENGINE threw rather than on values
    the test injected."""

    def __init__(self, script):
        super().__init__()
        _scripted[:] = list(script)
        self.rolled = []

    def roll(self, count, sides=6, **kwargs):
        values = super().roll(count, sides, **kwargs)
        self.rolled.append((kwargs.get("label", ""), list(self.pending_values or values or [])))
        return values


def find_option(dm, needle):
    if not dm.is_pending:
        return None
    for opt in dm.options:
        if needle.lower() in opt["label"].lower():
            return opt
    return None


from game.shooting import ShootingController  # noqa: E402
from game.turn import PHASE_SHOOTING, TurnTracker  # noqa: E402


def run_shooting(attacker, target, script, answer):
    """One weapon group's hit step, driven through the real controller.

    `answer` picks an option by substring - "failed", "whole", "keep" - or
    None to expect no prompt at all. Returns (prompt_seen, handled, dice,
    option_labels)."""
    dice = ScriptedDice([])   # nothing to throw unless the offer is taken
    dm = DecisionManager()
    tracker = TurnTracker("Player 2")
    while tracker.phase != PHASE_SHOOTING:
        tracker.advance_phase()
    sc = ShootingController(
        dice_manager=dice, turn_tracker=tracker, decision_manager=dm,
        all_tokens=list(attacker.models) + list(target.models), obstacles=[],
    )
    sc.active_squad = attacker
    weapon = next(w for w in attacker.models[0].weapons if w.weapon_type == "ranged")
    threshold = 5
    label = "Slugga"
    # Drive just the hit step: the roll's outcome, then the tail under test.
    rolls = list(script)
    results = ["critical" if r >= 6 else ("hit" if r >= threshold else "fail") for r in rolls]
    hits = sum(1 for r in results if r != "fail")
    crits = sum(1 for r in results if r == "critical")
    rerollable = (hits, crits, len(rolls))
    sc._hit_reroll_used = False
    seen = {"handled": None}
    sc._handle_hit_results = lambda h, c, w, t, l: seen.__setitem__("handled", (h, c))
    sc._finish_hit_roll(hits, crits, weapon, target, label, rerollable, threshold)
    prompt = dm.is_pending
    labels = [o["label"] for o in dm.options] if prompt else []
    if prompt and answer:
        opt = find_option(dm, answer)
        if opt is not None:
            dm.choose(dm.options.index(opt))
    return prompt, seen["handled"], dice, labels


# Five dice, three misses (BS5+): 2, 3, 5, 6, 1 -> 2 hits (one critical).
SCRIPT = [2, 3, 5, 6, 1]

prompt, handled, _, labels = run_shooting(squad, vehicle, list(SCRIPT), answer="keep")
check("shooting: prompt offered against a VEHICLE", prompt, True)
check("shooting: keeping the result keeps the 2 hits", handled, (2, 1))

# Both scopes must be offered, per the user instruction - neither dominates
# the other, so the player picks.
check("prompt offers all three options", len(labels), 3)
check_true("failures-only option is offered", any("failed hit rolls" in l for l in labels))
check_true("whole-roll option is offered", any("whole Hit roll" in l for l in labels))
check_true("keep option is offered", any("Keep result" in l for l in labels))
check_true("failures-only names the 3 failed dice", any("failed hit rolls (3 dice)" in l for l in labels))
check_true("whole-roll names all 5 dice", any("whole Hit roll (5 dice)" in l for l in labels))

# With nothing failed there is nothing to re-roll failures-wise, so that
# option is dropped rather than offered as a no-op.
_, _, _, all_hit_labels = run_shooting(squad, vehicle, [5, 5, 6], answer="keep")
check("no failures -> no failures-only option", len(all_hit_labels), 2)
check_true("but the whole roll can still be thrown",
           any("whole Hit roll (3 dice)" in l for l in all_hit_labels))

prompt_ab, handled_ab, _, _ = run_shooting(squad, infantry, list(SCRIPT), answer=None)
check("shooting A/B: no prompt against INFANTRY", prompt_ab, False)
check("shooting A/B: same dice still resolve to 2 hits", handled_ab, (2, 1))

prompt_nb, handled_nb, _, _ = run_shooting(plain_boyz, vehicle, list(SCRIPT), answer=None)
check("shooting A/B: no prompt for a unit without the ability", prompt_nb, False)


# ---------------------------------------------------------------------------
# 5. The re-roll actually replaces the roll (and can lose hits)
# ---------------------------------------------------------------------------

def run_reroll(attacker, target, first, second, scope="whole"):
    """Take the offer; `second` is what the re-rolled dice come up as.
    `scope` picks which of the two re-roll options is taken."""
    dice = ScriptedDice(list(second))
    dm = DecisionManager()
    tracker = TurnTracker("Player 2")
    while tracker.phase != PHASE_SHOOTING:
        tracker.advance_phase()
    sc = ShootingController(
        dice_manager=dice, turn_tracker=tracker, decision_manager=dm,
        all_tokens=list(attacker.models) + list(target.models), obstacles=[],
    )
    sc.active_squad = attacker
    weapon = next(w for w in attacker.models[0].weapons if w.weapon_type == "ranged")
    threshold = 5
    results = ["critical" if r >= 6 else ("hit" if r >= threshold else "fail") for r in first]
    hits = sum(1 for r in results if r != "fail")
    crits = sum(1 for r in results if r == "critical")
    sc._hit_reroll_used = False
    seen = {"handled": None}
    sc._handle_hit_results = lambda h, c, w, t, l: seen.__setitem__("handled", (h, c))
    sc._finish_hit_roll(hits, crits, weapon, target, "Slugga", (hits, crits, len(first)), threshold)
    opt = find_option(dm, scope)
    if opt is None:
        # No offer at all - a real regression. Report it as a failed check
        # rather than crashing, so the rest of the suite still runs.
        check("re-roll was offered at all (prerequisite of this section)", False, True)
        return sc, dm, dice, seen
    dm.choose(dm.options.index(opt))
    # The re-roll is a real, visible dice step - resolve it the way
    # main.py's own acknowledge chain does.
    sc.group = {"weapon_key": None, "weapon_label": "Slugga", "pairs": [(attacker.models[0], weapon)],
                "target_squad": target}
    return sc, dm, dice, seen


# a) the WHOLE roll: all five dice go, and nothing is carried over.
sc, dm, dice, seen = run_reroll(squad, vehicle, SCRIPT, [6, 6, 6, 6, 6], scope="whole")
last_roll = dice.rolled[-1] if dice.rolled else ("", [])
check("whole-roll option throws every re-rollable die", last_roll[1], [6, 6, 6, 6, 6])
check_true("re-roll label names the ability", "Monster Hunters" in last_roll[0])
check_true("whole-roll label says so", "re-rolling all" in last_roll[0])
check("re-roll marks its dice as spent", sc.pending_step, "hit_monster_hunters_reroll")
check("whole roll carries nothing over", (sc._pending_hit_reroll["hits"], sc._pending_hit_reroll["crits"]), (0, 0))
check("whole roll is flagged as such", sc._pending_hit_reroll["full"], True)

# The offer is once per weapon group.
check("offer is one-shot per group", sc._hit_reroll_used, True)

# b) FAILURES ONLY on the same roll: only the 3 misses go, and the 2 hits
# already rolled are kept - the difference that makes it a real choice.
sc_f, _, dice_f, _ = run_reroll(squad, vehicle, SCRIPT, [6, 6, 6], scope="failed")
fail_roll = dice_f.rolled[-1] if dice_f.rolled else ("", [])
check("failures-only throws just the 3 misses", len(fail_roll[1]), 3)
check_true("failures-only label says so", "re-rolling 3 failed" in fail_roll[0])
check("failures-only keeps the 2 hits already rolled",
      (sc_f._pending_hit_reroll["hits"], sc_f._pending_hit_reroll["crits"]), (2, 1))
check("failures-only is not flagged as a full re-roll", sc_f._pending_hit_reroll["full"], False)


# ---------------------------------------------------------------------------
# 6. Monster Hunters in the FIGHT phase
# ---------------------------------------------------------------------------

from game.fight import FightController  # noqa: E402
from game.turn import PHASE_FIGHT  # noqa: E402


def run_fight(attacker, target, first, answer):
    dice = ScriptedDice([])
    dm = DecisionManager()
    tracker = TurnTracker("Player 2")
    while tracker.phase != PHASE_FIGHT:
        tracker.advance_phase()
    fc = FightController(
        dice_manager=dice, turn_tracker=tracker, decision_manager=dm,
        all_tokens=list(attacker.models) + list(target.models),
    )
    fc.fighting_squad = attacker
    weapon = next(w for w in attacker.models[0].weapons if w.weapon_type == "melee")
    threshold = 3
    results = ["critical" if r >= 6 else ("hit" if r >= threshold else "fail") for r in first]
    hits = sum(1 for r in results if r != "fail")
    crits = sum(1 for r in results if r == "critical")
    fc._hit_reroll_used = False
    seen = {"handled": None}
    fc._handle_hit_results = lambda h, c, w, t, l: seen.__setitem__("handled", (h, c))
    fc._finish_hit_roll(hits, crits, weapon, target, "Choppa", (hits, crits, len(first)), threshold)
    prompt = dm.is_pending
    labels = [o["label"] for o in dm.options] if prompt else []
    if prompt and answer:
        opt = find_option(dm, answer)
        if opt is not None:
            dm.choose(dm.options.index(opt))
    return prompt, seen["handled"], dice, labels


walker = build(DEFF_DREAD, owner="Player 1", name="Deff Dread")
grots = build(GRETCHIN, owner="Player 1", name="Gretchin")

MELEE_SCRIPT = [1, 2, 4, 6, 3]  # WS3+: 3 hits, one critical

prompt, handled, _, flabels = run_fight(squad, walker, MELEE_SCRIPT, answer="keep")
check("fight: prompt offered against a VEHICLE (\"makes an attack\", not ranged)", prompt, True)
check("fight: keeping the result keeps the 3 hits", handled, (3, 1))
check("fight: both scopes offered here too", len(flabels), 3)
check_true("fight: failures-only names the 2 misses", any("failed hit rolls (2 dice)" in l for l in flabels))
check_true("fight: whole-roll names all 5", any("whole Hit roll (5 dice)" in l for l in flabels))

prompt_ab, handled_ab, _, _ = run_fight(squad, grots, MELEE_SCRIPT, answer=None)
check("fight A/B: no prompt against non-MONSTER/VEHICLE", prompt_ab, False)
check("fight A/B: same dice still resolve to 3 hits", handled_ab, (3, 1))

prompt_nb, _, _, _ = run_fight(plain_boyz, walker, MELEE_SCRIPT, answer=None)
check("fight A/B: no prompt for a unit without the ability", prompt_nb, False)

_, _, fdice, _ = run_fight(squad, walker, MELEE_SCRIPT, answer="whole")
f_last = fdice.rolled[-1] if fdice.rolled else ("", [])
check("fight: whole-roll option throws all 5", len(f_last[1]), 5)
check_true("fight: re-roll label names the ability", "Monster Hunters" in f_last[0])

_, _, fdice2, _ = run_fight(squad, walker, MELEE_SCRIPT, answer="failed")
f_last2 = fdice2.rolled[-1] if fdice2.rolled else ("", [])
check("fight: failures-only option throws just the 2 misses", len(f_last2[1]), 2)


# ---------------------------------------------------------------------------
# 7. A die is never re-rolled twice
# ---------------------------------------------------------------------------

dice = ScriptedDice([])
dm = DecisionManager()
tracker = TurnTracker("Player 2")
while tracker.phase != PHASE_SHOOTING:
    tracker.advance_phase()
sc = ShootingController(
    dice_manager=dice, turn_tracker=tracker, decision_manager=dm,
    all_tokens=list(squad.models) + list(vehicle.models), obstacles=[],
)
sc.active_squad = squad
weapon = next(w for w in squad.models[0].weapons if w.weapon_type == "ranged")
sc._hit_reroll_used = False
sc._handle_hit_results = lambda *a: None
# Nothing left that may be thrown again -> no offer, even against a VEHICLE.
sc._finish_hit_roll(2, 1, weapon, vehicle, "Slugga", (2, 1, 0), 5)
check("no offer when every die already used its re-roll", dm.is_pending, False)

# And the offer only ever throws the free share.
sc2 = ShootingController(
    dice_manager=ScriptedDice([]), turn_tracker=tracker, decision_manager=DecisionManager(),
    all_tokens=list(squad.models) + list(vehicle.models), obstacles=[],
)
sc2.active_squad = squad
sc2._hit_reroll_used = False
sc2._handle_hit_results = lambda *a: None
sc2._finish_hit_roll(3, 1, weapon, vehicle, "Slugga", (1, 0, 2), 5)
opt = find_option(sc2.decision_manager, "whole")
check_true("whole-roll offer names the free dice count only",
           opt is not None and "(2 dice)" in opt["label"])
if opt is not None:
    sc2.decision_manager.choose(sc2.decision_manager.options.index(opt))
carried = sc2._pending_hit_reroll or {}
check("only the free share is thrown",
      len(sc2.dice_manager.rolled[-1][1]) if sc2.dice_manager.rolled else None, 2)
check("hits on already-spent dice are carried over", carried.get("hits"), 2)
check("crits on already-spent dice are carried over", carried.get("crits"), 1)


# ---------------------------------------------------------------------------
# 8. END TO END through the real dice chain (Fight phase)
#
# Sections 4-7 drive the hit-roll tail directly, which is precise but stops
# short of proving the re-roll actually resolves. This one runs a whole
# weapon group through the real controller - select, target, swing, take the
# offer, acknowledge the second roll - and reads the outcome off the log the
# controller itself wrote.
# ---------------------------------------------------------------------------

from game.command_points import CommandPointManager  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.turn import PHASES  # noqa: E402

class CollectingLog:
    def __init__(self):
        self.lines = []

    def add(self, message, file_only=False):
        self.lines.append(message)


def fight_scene(attacker_sheet, target_sheet):
    st = GameState()
    attacker = build_squad(attacker_sheet, "Player 2", name="Beast Snagga Boyz 1")
    target = build_squad(target_sheet, "Player 1", name="Deff Dread 1")
    for i, m in enumerate(attacker.models):
        m.x_in, m.y_in = 20.0 + i * 1.4, 20.0
    for i, m in enumerate(target.models):
        m.x_in, m.y_in = 20.0 + i * 1.4, 21.2  # inside Engagement Range
    for sq in (attacker, target):
        for m in sq.models:
            st.add_token(m)
    tt = TurnTracker()
    tt.phase_index = PHASES.index(PHASE_FIGHT)
    tt.turn_owner = "Player 2"
    tt.set_active("Player 2")
    log = CollectingLog()
    dice, dec = DiceManager(), DecisionManager()
    fc = FightController(dice_manager=dice, turn_tracker=tt, all_tokens=st.tokens,
                         decision_manager=dec, game_log=log)
    fc.game_log = log
    fc.begin_fight_step()
    return dict(attacker=attacker, target=target, dice=dice, dec=dec, fight=fc, log=log)


def swing(scene, first_roll, answer, second_roll=()):
    """One weapon group, all the way through. `answer` is 'reroll'/'keep'."""
    fc, dice, dec = scene["fight"], scene["dice"], scene["dec"]
    fc.select_to_fight(scene["attacker"])
    if fc.state == "choosing_target":
        fc.choose_target_squad(scene["target"])
    groups = fc.weapon_eligibility()
    _scripted[:] = list(first_roll)
    fc.choose_weapon(groups[0][0])
    rolled = list(dice.pending_values)
    _scripted[:] = []           # every wound/save die fails - only hits matter here
    dice.acknowledge()
    fc.on_dice_acknowledged()
    prompted = dec.is_pending
    opt = None
    if prompted:
        opt = next((o for o in dec.options if answer in o["label"].lower()), None)
    if prompted and opt is not None:
        _scripted[:] = list(second_roll)
        dec.choose(dec.options.index(opt))
        if answer != "keep":
            dice.acknowledge()
            fc.on_dice_acknowledged()
    return rolled, prompted


def _counts_from(text, sep):
    # The failures-only line reads "N additional hit(s)", the others just
    # "N hit(s)" - take the leading number either way.
    try:
        after = text.split(sep, 1)[1]
        return int(after.split()[0]), int(after.split("of which ")[1].split(" critical")[0])
    except (IndexError, ValueError):
        return None, None


def hit_counts(log):
    """(hits, crits) after whichever re-roll scope was taken.

    The controller writes one line per throw, so the two scopes combine
    differently: a WHOLE re-roll discards the first line (its own line is
    the result), while a FAILURES-ONLY re-roll adds to it. Note the whole-
    roll line does not print the hits carried over from dice that were held
    back - in these scenarios nothing is held back, so the line is the whole
    story; sections 5 and 7 check the carry-over directly instead."""
    base = next((l for l in log.lines if "hit roll" in l and "re-rolled" not in l), "")
    whole = next((l for l in log.lines if "re-rolled the whole Hit roll" in l), "")
    partial = next((l for l in log.lines if "re-rolled failed hit rolls" in l), "")
    if whole:
        return _counts_from(whole, "-> ")
    b_hits, b_crits = _counts_from(base, ": ")
    if not partial or b_hits is None:
        return b_hits, b_crits
    p_hits, p_crits = _counts_from(partial, "-> ")
    if p_hits is None:
        return b_hits, b_crits
    return b_hits + p_hits, b_crits + p_crits


# Beast Snagga Boyz are WS3+. First roll: two misses and one hit.
sc_keep = fight_scene(BEAST_SNAGGA_BOYZ, DEFF_DREAD)
rolled, prompted = swing(sc_keep, [1, 2, 4], answer="keep", second_roll=[])
check("e2e: the real chain offers the re-roll against a VEHICLE", prompted, True)
check("e2e: keeping the result keeps 1 hit", hit_counts(sc_keep["log"])[0], 1)

sc_rr = fight_scene(BEAST_SNAGGA_BOYZ, DEFF_DREAD)
_, prompted = swing(sc_rr, [1, 2, 4], answer="whole", second_roll=[6, 6, 6])
check("e2e: the re-roll resolves through the real chain", prompted, True)
rr_line = next((l for l in sc_rr["log"].lines if "re-rolled the whole Hit roll" in l), "")
check_true("e2e: log says the previous roll is discarded", "previous roll is discarded" in rr_line)
check_true("e2e: log names Monster Hunters", "Monster Hunters" in rr_line)
rr_hits, rr_crits = hit_counts(sc_rr["log"])
check("e2e: 1 hit becomes 3 after re-rolling into three 6s", rr_hits, 3)
check("e2e: all three are Critical Hits", rr_crits, 3)

# The other scope, same starting roll: the 3 misses go, the 1 hit stays.
sc_f = fight_scene(BEAST_SNAGGA_BOYZ, DEFF_DREAD)
swing(sc_f, [1, 2, 4], answer="failed", second_roll=[6, 6, 6])
f_line = next((l for l in sc_f["log"].lines if "re-rolled failed hit rolls" in l), "")
check_true("e2e: failures-only logs as an addition, not a discard",
           f_line and "additional hit(s)" in f_line and "discarded" not in f_line)
f_hits, f_crits = hit_counts(sc_f["log"])
check("e2e: failures-only keeps the original hit and adds 3 more", f_hits, 4)
check("e2e: and the 3 new sixes are all critical", f_crits, 3)

# A/B on the same dice against a target the ability does not cover.
sc_ab = fight_scene(BEAST_SNAGGA_BOYZ, GRETCHIN)
_, prompted_ab = swing(sc_ab, [1, 2, 4], answer="keep", second_roll=[])
check("e2e A/B: no offer against a non-MONSTER/VEHICLE target", prompted_ab, False)
check("e2e A/B: the same dice still give 1 hit", hit_counts(sc_ab["log"])[0], 1)

# ---------------------------------------------------------------------------

print(f"{CHECKS[0] - len(FAILURES)}/{CHECKS[0]} checks passed")
for f in FAILURES:
    print("  FAIL:", f)
sys.exit(1 if FAILURES else 0)
