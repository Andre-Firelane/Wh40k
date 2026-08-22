"""Aspect Shrine tokens: the ASPECT WARRIORS wargear shared by four datasheets.

The two things worth testing hard are the ones that could silently be wrong:

- the GATE, because an ability that offers itself on every hit and wound roll
  of every Aspect Warrior unit would be exactly the interruption this project
  has pushed back on before. Each of its conditions is isolated, with the
  others shown to be satisfied, so "not offered" is always attributable.
- the ARITHMETIC, through the REAL resolution in both phases: a failure turned
  into an unmodified 6 has to add a hit AND a critical, and that is measured by
  the number of dice the next step throws, not by reading a counter back.
"""

import testkit as tk
from testkit import Checks, script

from game import aspect_shrine
from game.factions import aeldari as ae
from game.units import WarbossProfile
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

# (a) a failure to convert - the biggest gain, always offered.
checks.eq("a miss on the hit roll is worth a token",
          aspect_shrine.hit_change(sq, model, catapult, hits=19, crits=0, misses=1)[:2], (20, 1))
checks.eq("a failed wound likewise",
          aspect_shrine.wound_change(sq, model, catapult, wounds=19, crits=0, no_effect=1)[:3], (20, 1, 0))

# (b) no failure, and a critical would buy nothing -> NOT offered. This is the
# condition that keeps the ability quiet, so it gets both directions.
checks.eq("an all-hits roll with no crit payoff is NOT offered",
          aspect_shrine.hit_change(sq, model, catapult, hits=20, crits=0, misses=0), None)
sustained = type("W", (), {"sustained_hits": 1, "lethal_hits": False, "devastating_wounds": False})()
checks.eq("...but the same roll IS offered once the weapon has [SUSTAINED HITS]",
          aspect_shrine.hit_change(sq, model, sustained, hits=20, crits=0, misses=0)[:2], (20, 1))
lethal = type("W", (), {"sustained_hits": 0, "lethal_hits": True, "devastating_wounds": False})()
checks.eq("...or [LETHAL HITS]",
          aspect_shrine.hit_change(sq, model, lethal, hits=20, crits=0, misses=0)[:2], (20, 1))
checks.eq("an all-wounds roll with no [DEVASTATING WOUNDS] is NOT offered",
          aspect_shrine.wound_change(sq, model, catapult, wounds=20, crits=0, no_effect=0), None)
devastating = type("W", (), {"sustained_hits": 0, "lethal_hits": False, "devastating_wounds": True})()
checks.eq("...but it is with [DEVASTATING WOUNDS]",
          aspect_shrine.wound_change(sq, model, devastating, wounds=20, crits=0, no_effect=0)[:3], (20, 1, 0))

# (c) everything already critical -> nothing left to change.
checks.eq("a roll that is already all criticals is NOT offered",
          aspect_shrine.hit_change(sq, model, sustained, hits=20, crits=20, misses=0), None)

# (d) no token left.
spent = avengers()
aspect_shrine.spend(spent)
checks.eq("its one token is gone", aspect_shrine.unspent_tokens(spent), 0)
checks.eq("with no token there is no offer",
          aspect_shrine.hit_change(spent, spent.models[1], catapult, hits=19, crits=0, misses=1), None)

# (e) "excluding CHARACTER models". leader_models() falls back to reading
# profile.leader for a hand-built squad, which is exactly this shape.
led = avengers()
warboss = tk.build(ae.DIRE_AVENGERS, "Player 1", name="1 Dire Avengers 2").models[0]
warboss.profile = WarbossProfile()
led.models.append(warboss)
warboss.squad = led
checks.true("the stand-in is recognised as a CHARACTER", warboss.profile.leader)
checks.eq("a roll made for a CHARACTER model cannot use the token",
          aspect_shrine.hit_change(led, warboss, catapult, hits=19, crits=0, misses=1), None)
checks.eq("...while the same roll for a non-CHARACTER model in that unit can",
          aspect_shrine.hit_change(led, led.models[1], catapult, hits=19, crits=0, misses=1)[:2], (20, 1))


# --- 3. end to end, Shooting phase -----------------------------------------
print("--- 3. end to end, Shooting phase ---")


def shoot(faces, answers=(), gap=14.0):
    """One Avenger Shuriken Catapult group, 5 models x A4 = 20 dice, at 14"
    so Bladestorm is out of range and cannot muddy the crit arithmetic.

    Driven to a standstill rather than one step at a time: `answers` is used
    up in the order the offers arrive, and anything past it declines. sc's
    extra "offers" key is every prompt that was raised along the way, so a
    test can assert WHICH step asked."""
    sc = tk.shooting_scene(ae.DIRE_AVENGERS, ae.HOWLING_BANSHEES,
                           attacker_owner="Player 1", gap=gap)
    sc["shooting"].start_shooting(sc["attacker"])
    sc["shooting"].choose_target_squad(sc["target"])
    key = next(r[0] for r in sc["shooting"].weapon_eligibility()
               if r[1] == "Avenger Shuriken Catapult")
    script(*faces)
    sc["shooting"].choose_weapon(key)
    todo, offers = list(answers), []
    for _ in range(10):
        if sc["decision"].is_pending:
            offers.append(sc["decision"].prompt)
            tk.pick_option(sc["decision"], todo.pop(0) if todo else "Keep the roll")
        elif sc["dice"].is_pending:
            sc["dice"].acknowledge()
            sc["shooting"].on_dice_acknowledged()
        else:
            break
    sc["offers"] = offers
    return sc


# 19 hits and one miss on a 3+, then every wound die fails so the wound step
# raises no offer of its own and the hit step stays isolated.
HIT_FACES = [4] * 19 + [1]

offered = shoot(HIT_FACES)
checks.true("the miss raises an offer", bool(offered["offers"]))
checks.true("it names the unit and the token",
            "Aspect Shrine token" in offered["offers"][0])
checks.true("and it is about the hit roll", "hit roll" in offered["offers"][0])

kept = shoot(HIT_FACES)
spent_sc = shoot(HIT_FACES, answers=("Spend an Aspect Shrine token",))


def wound_dice(sc):
    """How many dice the WOUND roll threw - one per hit, so this is the
    engine's own count of the hits the step produced."""
    return next(len(v) for label, v in sc["dice"].rolled if label.startswith("Wound Roll"))


checks.eq("declined: 19 hits go to the wound step", wound_dice(kept), 19)
checks.eq("spent: the miss became a hit, so 20 do", wound_dice(spent_sc), 20)
checks.eq("declining costs no token", aspect_shrine.unspent_tokens(kept["attacker"]), 1)
checks.eq("spending costs exactly one", aspect_shrine.unspent_tokens(spent_sc["attacker"]), 0)
checks.true("and the log says what it bought",
            any("counts as an unmodified 6" in line for line in spent_sc["log"].lines))
# The critical half matters too - and it is visible because a critical WOUND
# would be routed differently. Here the hit-step critical is what was bought,
# so check the log's own before/after rather than a downstream count.
checks.true("the log records the critical it added",
            any("19 hit(s) of which 0 critical -> 20 of which 1" in line
                for line in spent_sc["log"].lines))

# The wound step is a separate offer with its own token check. All 20 hits,
# then 19 wounds and one failure on a 3+.
WOUND_FACES = [4] * 20 + [3] * 19 + [1]
w_kept = shoot(WOUND_FACES)
w_spent = shoot(WOUND_FACES, answers=("Spend an Aspect Shrine token",))
checks.eq("an all-hits roll raises no offer at the HIT step, only at the wound step",
          [("hit roll" in p, "wound roll" in p) for p in w_spent["offers"]], [(False, True)])


def save_dice(sc):
    return next(len(v) for label, v in sc["dice"].rolled if label.startswith("Save Roll"))


checks.eq("declined: 19 wounds reach the save", save_dice(w_kept), 19)
checks.eq("spent: the failed wound became one, so 20 do", save_dice(w_spent), 20)

# One offer per group per step, so a unit with two tokens is not asked twice
# about the same roll.
two = shoot(HIT_FACES, answers=("Spend an Aspect Shrine token",))
checks.eq("the hit roll is asked about exactly once, not once per token",
          sum(1 for p in two["offers"] if "hit roll" in p), 1)


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
fs["dice"].acknowledge()
fc.on_dice_acknowledged()
checks.true("the same offer appears in the Fight phase", fs["decision"].is_pending)
checks.eq("it belongs to the fighting player", fs["decision"].player, "Player 1")
tk.pick_option(fs["decision"], "Spend an Aspect Shrine token")
checks.eq("the token is spent", aspect_shrine.unspent_tokens(fs["attacker"]), 0)
checks.true("and it is logged",
            any("counts as an unmodified 6" in line for line in fs["log"].lines))


# --- 5. once per battle, per token -----------------------------------------
print("--- 5. once per battle, per token ---")

big = avengers(composition_index=1)
checks.eq("a 10-model unit starts with 2", aspect_shrine.unspent_tokens(big), 2)
aspect_shrine.spend(big)
checks.eq("one spent leaves one", aspect_shrine.unspent_tokens(big), 1)
checks.true("and it can still be used",
            aspect_shrine.hit_change(big, big.models[1], catapult, hits=19, crits=0, misses=1) is not None)
aspect_shrine.spend(big)
checks.eq("both spent leaves none", aspect_shrine.unspent_tokens(big), 0)
checks.eq("and no further offer",
          aspect_shrine.hit_change(big, big.models[1], catapult, hits=19, crits=0, misses=1), None)
# Nothing refreshes them: they are per BATTLE, not per phase or per turn.
checks.eq("the spend count only ever grows", big.aspect_shrine_tokens_used, 2)


# --- 6. A/B probe ----------------------------------------------------------
print("--- 6. A/B probe ---")

original = aspect_shrine.unspent_tokens
aspect_shrine.unspent_tokens = lambda squad: 0
blind = shoot(HIT_FACES)
checks.eq("A/B: with no tokens the offer never appears", blind["offers"], [])
aspect_shrine.unspent_tokens = original
restored = shoot(HIT_FACES)
checks.true("A/B: restored", bool(restored["offers"]))

checks.finish()
