"""Aspect Shrine tokens: the ASPECT WARRIORS wargear shared by four datasheets.

The token is now spent from the LEFT PANEL against the roll on the table, not
answered in a prompt after it - user: "momentan werde ich bei aeldari jedes mal
gefragt, ob ich aspect shrine tokens verwenden will... nach jedem wurf. kann
das nicht eine option im linken panel sein, statt eines overlays? command
reroll funktioniert ja auch so." So the things worth testing hard are:

- the GATE, because a button that buys nothing is a button that lies about
  what it is for. Each of its conditions is isolated, with the others shown to
  be satisfied, so "not offered" is always attributable.
- the EFFECT, through the REAL resolution in both phases. It is no longer
  counter arithmetic: the chosen DIE becomes a 6 and the ordinary resolution
  reads it, so what gets measured is how many dice the next step throws.
- the FLOW, because "click the button, then pick the die" is what was asked
  for and it is the part a unit test of the ability alone cannot see.
"""

import testkit as tk
from testkit import Checks, script

from game import aspect_shrine, unmodified_six
from game.factions import aeldari as ae
from game.units import WarbossProfile
from game.unmodified_six_controller import UnmodifiedSixController
from game.weapons import RANGED

checks = Checks("Aspect Shrine tokens")

ASPECT_SHEETS = (ae.STRIKING_SCORPIONS, ae.HOWLING_BANSHEES, ae.WARP_SPIDERS, ae.DIRE_AVENGERS)


def avengers(owner="Player 1", composition_index=0):
    return tk.build(ae.DIRE_AVENGERS, owner, name="1 Dire Avengers 1",
                    composition_index=composition_index)


# --- 1. where the tokens come from -----------------------------------------
print("--- 1. where the tokens come from ---")

for sheet in ASPECT_SHEETS:
    for idx, size, want in ((0, 5, 1), (1, 10, 2)):
        sq = tk.build(sheet, "Player 1", name=f"1 {sheet.name} 1", composition_index=idx)
        checks.eq(f"{sheet.name} at {size} models holds {want} token(s)",
                  (len(sq.models), sq.aspect_shrine_tokens), (size, want))

# One per FIVE models, so a unit is never entitled to more than that.
checks.eq("a non-Aspect-Warrior unit holds none",
          tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 1").aspect_shrine_tokens, 0)

# Read off STARTING strength: tokens are bought when the list is written, so
# losing models must not lose them.
sq = avengers(composition_index=1)
for model in sq.models[:6]:
    model.current_wounds = 0
sq.models[:] = [m for m in sq.models if not m.is_dead()]
checks.eq("down to 4 models, the 10-model unit keeps both tokens",
          (len(sq.models), aspect_shrine.tokens_for(sq)), (4, 2))
checks.eq("and both are still unspent", aspect_shrine.unspent_tokens(sq), 2)


# --- 2. the gate -----------------------------------------------------------
print("--- 2. the gate ---")

sq = avengers()
model = sq.models[1]          # a plain Dire Avenger, not the Exarch
catapult = next(w for w in model.weapons if w.weapon_type == RANGED)
checks.eq("the catapult has no crit-triggered ability of its own",
          (catapult.sustained_hits, catapult.lethal_hits, catapult.devastating_wounds), (0, False, False))

# The gate splits cleanly in two, and they are tested apart because they fail
# apart: game/unmodified_six.py answers "is a die worth changing" from the
# roll, and each ability answers "may this unit change one" from its resource.

# (a) a failure to convert - the biggest gain, always worth it.
checks.eq("a miss on the roll is worth a token",
          unmodified_six.gain(failures=1, successes=19, crits=0, crit_matters=False), "failure")

# (b) no failure, and a critical would buy nothing -> nothing to offer. This
# is the condition that keeps the button honest, so it gets both directions.
checks.eq("an all-hits roll with no crit payoff is NOT worth it",
          unmodified_six.gain(failures=0, successes=20, crits=0, crit_matters=False), None)
checks.eq("...but the same roll IS once a critical buys something",
          unmodified_six.gain(failures=0, successes=20, crits=0, crit_matters=True), "success")

# ...and what "buys something" means, per step, off the real weapon fields.
sustained = type("W", (), {"sustained_hits": 1, "lethal_hits": False, "devastating_wounds": False})()
lethal = type("W", (), {"sustained_hits": 0, "lethal_hits": True, "devastating_wounds": False})()
devastating = type("W", (), {"sustained_hits": 0, "lethal_hits": False, "devastating_wounds": True})()
checks.eq("[SUSTAINED HITS] makes a critical HIT matter",
          unmodified_six.crit_matters_on_hit(sustained), True)
checks.eq("...so does [LETHAL HITS]", unmodified_six.crit_matters_on_hit(lethal), True)
checks.eq("the plain catapult's does not", unmodified_six.crit_matters_on_hit(catapult), False)
checks.eq("[DEVASTATING WOUNDS] makes a critical WOUND matter",
          unmodified_six.crit_matters_on_wound(devastating), True)
checks.eq("the plain catapult's does not", unmodified_six.crit_matters_on_wound(catapult), False)
# The two steps ask DIFFERENT questions - a weapon can matter on one and not
# the other, and reading one for the other would be a silent bug.
checks.eq("[SUSTAINED HITS] does nothing for a critical wound",
          unmodified_six.crit_matters_on_wound(sustained), False)
checks.eq("[DEVASTATING WOUNDS] does nothing for a critical hit",
          unmodified_six.crit_matters_on_hit(devastating), False)

# (c) everything already critical -> nothing left to change.
checks.eq("a roll that is already all criticals is NOT worth it",
          unmodified_six.gain(failures=0, successes=20, crits=20, crit_matters=True), None)

# (d) the resource half. No token left.
checks.true("a fresh unit may use its token", aspect_shrine.usable(sq, model))
spent = avengers()
aspect_shrine.spend(spent)
checks.eq("its one token is gone", aspect_shrine.unspent_tokens(spent), 0)
checks.eq("with no token there is no offer", aspect_shrine.usable(spent, spent.models[1]), False)

# (e) "excluding CHARACTER models". leader_models() falls back to reading
# profile.leader for a hand-built squad, which is exactly this shape.
led = avengers()
warboss = tk.build(ae.DIRE_AVENGERS, "Player 1", name="1 Dire Avengers 2").models[0]
warboss.profile = WarbossProfile()
led.models.append(warboss)
warboss.squad = led
checks.true("the stand-in is recognised as a CHARACTER", warboss.profile.leader)
checks.eq("a roll made for a CHARACTER model cannot use the token",
          aspect_shrine.usable(led, warboss), False)
checks.true("...while the same roll for a non-CHARACTER model in that unit can",
            aspect_shrine.usable(led, led.models[1]))

# (f) the button says what is left, because with a per-battle resource that is
# the whole decision.
checks.true("the button names the ability and the count",
            "Aspect Shrine" in aspect_shrine.button_label(sq)
            and "1 token" in aspect_shrine.button_label(sq))


# --- 3. end to end, Shooting phase -----------------------------------------
print("--- 3. end to end, Shooting phase ---")


def shoot(faces, gap=14.0):
    """One Avenger Shuriken Catapult group, 5 models x A4 = 20 dice, at 14"
    so Bladestorm is out of range and cannot muddy the crit arithmetic.

    Stops at the pending HIT roll - which is exactly where the panel now
    offers the button, so this is the state under test."""
    sc = tk.shooting_scene(ae.DIRE_AVENGERS, ae.HOWLING_BANSHEES,
                           attacker_owner="Player 1", gap=gap)
    sc["shooting"].start_shooting(sc["attacker"])
    sc["shooting"].choose_target_squad(sc["target"])
    key = next(r[0] for r in sc["shooting"].weapon_eligibility()
               if r[1] == "Avenger Shuriken Catapult")
    script(*faces)
    sc["shooting"].choose_weapon(key)
    sc["ctrl"] = UnmodifiedSixController(
        sc["dice"], attack_controllers=(sc["shooting"],), game_log=sc["log"])
    return sc


def drain(sc, answers=()):
    """Run the activation to a standstill, answering any prompt that is left."""
    todo = list(answers)
    for _ in range(12):
        if sc["decision"].is_pending:
            tk.pick_option(sc["decision"], todo.pop(0) if todo else "Keep")
        elif sc["dice"].is_pending:
            sc["dice"].acknowledge()
            sc["shooting"].on_dice_acknowledged()
        else:
            break
    return sc


# 19 hits and one miss on a 3+, then every wound die fails so the wound step
# offers nothing of its own and the hit step stays isolated.
HIT_FACES = [4] * 19 + [1]

offered = shoot(HIT_FACES)
sources = offered["ctrl"].available_sources()
checks.eq("the miss makes the button appear", [s.__name__ for s, _sq, _m in sources],
          ["game.aspect_shrine"])
checks.eq("...on the HIT roll", offered["dice"].label.startswith("Hit Roll"), True)
checks.eq("...and the gate says which die is worth it", offered["ctrl"].worth_changing(catapult), "failure")
# NOT a prompt any more - that is the entire report.
checks.eq("nothing is asked in an overlay", offered["decision"].is_pending, False)

# The flow the user asked for: click the button, then pick the die.
picked = shoot(HIT_FACES)
picked["ctrl"].start(aspect_shrine)
checks.true("clicking the button starts die selection", picked["ctrl"].selecting_die)
checks.eq("...and no token is spent yet", aspect_shrine.unspent_tokens(picked["attacker"]), 1)
miss_index = next(i for i, v in enumerate(picked["dice"].pending_values) if v == 1)
picked["ctrl"].choose_die(miss_index)
checks.eq("picking the die ends selection", picked["ctrl"].selecting_die, False)
checks.eq("...the die is now an unmodified 6",
          picked["dice"].pending_values[miss_index], unmodified_six.UNMODIFIED_SIX)
checks.eq("...the token is spent", aspect_shrine.unspent_tokens(picked["attacker"]), 0)
checks.true("...and it is logged",
            any("unmodified 6" in line for line in picked["log"].lines))

# The die the player picks is THEIRS to pick: a plain hit is a legal choice
# even though the gate found a miss.
other = shoot(HIT_FACES)
other["ctrl"].start(aspect_shrine)
hit_index = next(i for i, v in enumerate(other["dice"].pending_values) if v == 4)
other["ctrl"].choose_die(hit_index)
checks.eq("a hit can be chosen instead of the miss",
          other["dice"].pending_values[hit_index], unmodified_six.UNMODIFIED_SIX)
checks.eq("...and the miss is untouched", other["dice"].pending_values[miss_index], 1)


def wound_dice(sc):
    """How many dice the WOUND roll threw - one per hit, so this is the
    engine's own count of the hits the step produced."""
    return next(len(v) for label, v in sc["dice"].rolled if label.startswith("Wound Roll"))


kept = drain(shoot(HIT_FACES))
spent_sc = shoot(HIT_FACES)
spent_sc["ctrl"].start(aspect_shrine)
spent_sc["ctrl"].choose_die(miss_index)
drain(spent_sc)
checks.eq("declined: 19 hits go to the wound step", wound_dice(kept), 19)
checks.eq("spent: the miss became a hit, so 20 do", wound_dice(spent_sc), 20)
checks.eq("declining costs no token", aspect_shrine.unspent_tokens(kept["attacker"]), 1)
checks.eq("spending costs exactly one", aspect_shrine.unspent_tokens(spent_sc["attacker"]), 0)

# The critical half comes for free now, because the DIE is a 6 rather than a
# counter being nudged - so anything that reads the roll sees it.
checks.true("the changed die reads as a critical",
            spent_sc["dice"].is_critical(unmodified_six.UNMODIFIED_SIX))

# The wound step is its own offer with its own dice. All 20 hits, then 19
# wounds and one failure on a 3+.
WOUND_FACES = [4] * 20 + [3] * 19 + [1]
w = shoot(WOUND_FACES)
checks.eq("an all-hits roll offers nothing at the HIT step",
          w["ctrl"].available_sources(), [])
w["dice"].acknowledge()
w["shooting"].on_dice_acknowledged()
checks.eq("...but the wound step does", [s.__name__ for s, _sq, _m in w["ctrl"].available_sources()],
          ["game.aspect_shrine"])
checks.eq("...and it really is the Wound roll", w["dice"].label.startswith("Wound Roll"), True)


def save_dice(sc):
    return next(len(v) for label, v in sc["dice"].rolled if label.startswith("Save Roll"))


w_kept = drain(shoot(WOUND_FACES))
w_spent = shoot(WOUND_FACES)
w_spent["dice"].acknowledge()
w_spent["shooting"].on_dice_acknowledged()
w_spent["ctrl"].start(aspect_shrine)
w_spent["ctrl"].choose_die(
    next(i for i, v in enumerate(w_spent["dice"].pending_values) if v == 1))
drain(w_spent)
checks.eq("declined: 19 wounds reach the save", save_dice(w_kept), 19)
checks.eq("spent: the failed wound became one, so 20 do", save_dice(w_spent), 20)

# A die that is ALREADY a 6 is never offered - it would buy nothing.
all_sixes = shoot([6] * 20)
checks.eq("a roll of all 6s offers nothing", all_sixes["ctrl"].available_sources(), [])
checks.eq("...because no die is changeable", all_sixes["ctrl"]._changeable_indices(), [])


# --- 4. end to end, Fight phase --------------------------------------------
print("--- 4. end to end, Fight phase ---")

fs = tk.fight_scene(ae.HOWLING_BANSHEES, ae.DIRE_AVENGERS, attacker_owner="Player 1")
fc = fs["fight"]
fc.select_to_fight(fs["attacker"])
if fc.state == "choosing_target":
    fc.choose_target_squad(fs["target"])
groups = fc.weapon_eligibility()
checks.true("the Banshees have a melee group to swing", bool(groups))
# 5 models x A2 = 10 Banshee Blade dice at WS2+, so a 1 is the only miss -
# nine hits and one of them, which is what makes the token worth spending
# (the Banshee Blade has no crit-triggered ability, so with no miss there
# would correctly be nothing to buy).
script(*([4] * 9 + [1]), default=1)
fc.choose_weapon(groups[0][0])
fight_ctrl = UnmodifiedSixController(fs["dice"], attack_controllers=(fc,), game_log=fs["log"])
checks.eq("the same button appears in the Fight phase",
          [s.__name__ for s, _sq, _m in fight_ctrl.available_sources()], ["game.aspect_shrine"])
checks.eq("...and still nothing is asked in an overlay", fs["decision"].is_pending, False)
fight_ctrl.start(aspect_shrine)
fight_ctrl.choose_die(next(i for i, v in enumerate(fs["dice"].pending_values) if v == 1))
checks.eq("the token is spent", aspect_shrine.unspent_tokens(fs["attacker"]), 0)
checks.true("and it is logged",
            any("unmodified 6" in line for line in fs["log"].lines))
checks.eq("...and the button is gone once it is spent", fight_ctrl.available_sources(), [])


# --- 5. once per battle, per token -----------------------------------------
print("--- 5. once per battle, per token ---")

big = avengers(composition_index=1)
checks.eq("a 10-model unit starts with 2", aspect_shrine.unspent_tokens(big), 2)
aspect_shrine.spend(big)
checks.eq("one spent leaves one", aspect_shrine.unspent_tokens(big), 1)
checks.true("and it can still be used", aspect_shrine.usable(big, big.models[1]))
aspect_shrine.spend(big)
checks.eq("both spent leaves none", aspect_shrine.unspent_tokens(big), 0)
checks.eq("and no further offer", aspect_shrine.usable(big, big.models[1]), False)
# Nothing refreshes them: they are per BATTLE, not per phase or per turn.
checks.eq("the spend count only ever grows", big.aspect_shrine_tokens_used, 2)

# Two tokens on the SAME roll is now possible, where the old prompt deliberately
# asked only once per group per step. Nothing about the rule forbade it - each
# token is its own "you can change the result of one roll" - and with a button
# the reason not to (re-prompting) is gone.
two = shoot(HIT_FACES)
two["attacker"].aspect_shrine_tokens = 2
first, second = [i for i, v in enumerate(two["dice"].pending_values) if v == 4][:2]
two["ctrl"].start(aspect_shrine)
two["ctrl"].choose_die(first)
checks.eq("one token spent", aspect_shrine.unspent_tokens(two["attacker"]), 1)
checks.true("the button is still offered for the second",
            two["ctrl"].can_use(aspect_shrine))
two["ctrl"].start(aspect_shrine)
two["ctrl"].choose_die(second)
checks.eq("both dice are now 6s",
          (two["dice"].pending_values[first], two["dice"].pending_values[second]), (6, 6))
checks.eq("both tokens spent", aspect_shrine.unspent_tokens(two["attacker"]), 0)


# --- 6. A/B probe ----------------------------------------------------------
print("--- 6. A/B probe ---")

original = aspect_shrine.unspent_tokens
aspect_shrine.unspent_tokens = lambda squad: 0
blind = shoot(HIT_FACES)
checks.eq("A/B: with no tokens the button never appears", blind["ctrl"].available_sources(), [])
aspect_shrine.unspent_tokens = original
restored = shoot(HIT_FACES)
checks.true("A/B: restored", bool(restored["ctrl"].available_sources()))

checks.finish()
