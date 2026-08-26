"""Baharroth - the fourth Phoenix Lord here, and the one whose signature
ability turned out to be two mechanisms this engine already had.

CLOUDSTRIDER, half for half:
  * "remove it from the battlefield and place it into Strategic Reserves" is
    game/strategic_reserves.py's withdraw - the third consumer, after the
    Starflare Ignition System and Unshrouded Truth;
  * "set up anywhere more than 6" horizontally away from all enemy models, but
    until the end of the turn it is not eligible to declare a charge" is
    sentence for sentence The Shortened Blade, so it arms the same override.

Which is why the checks below go through the REAL IngressController and the
REAL GameState rather than reading the ability's own flags back.

CRY OF THE WIND is the odd one: "a successful unmodified Hit roll scores a
Critical Hit" is not a fixed number, it is whatever the attack needs to hit.
"""

import testkit as tk
from game import attached_units as au
from game import cloudstrider
from game.crit_hit import crit_hit_threshold
from game.factions import aeldari as ae
from game.factions import orks as ork
from game.units import BaharrothProfile

checks = tk.Checks("Baharroth")


def baharroth(name="1 Baharroth 1"):
    return tk.build(ae.BAHARROTH, "Player 1", name=name)


def hawks(name="1 Swooping Hawks 1"):
    return tk.build(ae.SWOOPING_HAWKS, "Player 1", name=name)


# --- 1. statline, weapons, points ------------------------------------------
print("--- 1. statline, weapons, points ---")

lord = baharroth()
checks.eq("one model", len(lord.models), 1)
checks.eq("125 pts", lord.points, 125)

p = BaharrothProfile()
checks.eq("M14\"", p.movement_in, 14)
checks.eq("T3", p.toughness, 3)
checks.eq("Sv2+", p.armor_save, "2+")
checks.eq("W5", p.wounds, 5)
checks.eq("Ld6+", p.leadership, "6+")
checks.eq("OC1", p.oc, 1)
checks.eq("WS2+ / BS2+", (p.weapon_skill, p.ballistic_skill), ("2+", "2+"))
checks.eq("4+ invulnerable save", p.invulnerable_save, "4+")
checks.eq("40 mm base -> 0.787\"", p.base_radius_in, round(40 / 2 / 25.4, 3))
checks.true("INFANTRY", p.infantry)
checks.true("JUMP PACK + FLY", p.jump_pack and p.fly)
checks.true("CORE: Deep Strike", p.deep_strike)
checks.true("CORE: Leader", p.leader)
checks.true("Battle Focus", p.battle_focus)
checks.true("EPIC HERO on the keyword line", "EPIC HERO" in ae.BAHARROTH.keywords)
checks.true("PHOENIX LORD too", "PHOENIX LORD" in ae.BAHARROTH.keywords)

# Deep Strike against the other three Phoenix Lords. Written first as "the
# first Phoenix Lord here with it" - which the check immediately disproved:
# Lhykhis has it too. Kept as a comparison rather than a claim, which is the
# point of measuring it instead of asserting it.
ds = {other.name: tk.build(other, "Player 1", name="1 %s 1" % other.name).models[0].profile.deep_strike
      for other in (ae.ASURMEN, ae.JAIN_ZAR, ae.LHYKHIS)}
checks.eq("Asurmen has no Deep Strike", ds["Asurmen"], False)
checks.eq("...nor Jain Zar", ds["Jain Zar"], False)
checks.eq("...but Lhykhis does, so he is not the first", ds["Lhykhis"], True)

fury = next(w for w in lord.models[0].weapons if w.name == "Fury of the Tempest")
checks.eq("Fury of the Tempest: 24\"/A4/S6/AP-1/D2",
          (fury.range_in, fury.attacks, fury.strength, fury.ap, fury.damage), (24, 4, 6, -1, 2))
checks.true("...[ASSAULT] + [LETHAL HITS]", fury.assault and fury.lethal_hits)
blade = next(w for w in lord.models[0].weapons if w.name == "Shining Blade")
checks.eq("Shining Blade: A6/S5/AP-2/D2",
          (blade.attacks, blade.strength, blade.ap, blade.damage), (6, 5, -2, 2))
checks.eq("...[SUSTAINED HITS 1]", blade.sustained_hits, 1)
checks.eq("no wargear options", list(ae.BAHARROTH.wargear_options), [])


# --- 2. LEADER --------------------------------------------------------------
print("--- 2. LEADER ---")

checks.eq("he leads Swooping Hawks", au.can_attach(baharroth(), hawks()), [])
merged = au.attach(baharroth(), hawks())
checks.eq("...merging to 6 models", len(merged.models), 6)
checks.true("he may lead NOTHING else in this army",
            bool(au.can_attach(baharroth(name="1 Baharroth 2"),
                               tk.build(ae.DIRE_AVENGERS, "Player 1", name="1 Dire Avengers 1"))))
# ...and the count of Grenade Pack Flyover dice tells the two components apart.
from game import grenade_pack_flyover as gpf  # noqa: E402

checks.eq("a merged unit rolls one die per SWOOPING HAWKS model, not per model",
          (gpf.dice_count(merged), len(merged.models)), (5, 6))


# --- 3. Cloudstrider, half one: back into Strategic Reserves ----------------
print("--- 3. Cloudstrider: the withdraw ---")

from game.decision import DecisionManager  # noqa: E402
from game.game_state import GameState  # noqa: E402


def withdraw_scene(led=True, enemy_gap=10.0):
    state = GameState()
    squad = hawks()
    if led:
        squad = au.attach(baharroth(), squad)
    enemy = tk.build(ork.BOYZ, "Player 2", name="2 Boyz 1")
    tk.line_up(squad, y=20.0)
    tk.line_up(enemy, y=20.0 + enemy_gap)
    for s in (squad, enemy):
        for m in s.models:
            state.add_token(m)
    log, dec = tk.Log(), DecisionManager()
    ctrl = cloudstrider.CloudstriderController(
        game_state=state, decision_manager=dec, game_log=log,
    )
    return dict(state=state, squad=squad, enemy=enemy, ctrl=ctrl, decision=dec, log=log)


checks.true("the profile carries it", p.cloudstrider)
led = withdraw_scene(led=True)
checks.true("a unit he leads can withdraw",
            cloudstrider.can_withdraw(led["squad"], led["state"]))
# "While this model is LEADING a unit" - so an unled unit gets nothing, and
# that is read through leader_ability() rather than a unit-wide test.
alone = withdraw_scene(led=False)
checks.eq("...an unled Swooping Hawks unit cannot",
          cloudstrider.can_withdraw(alone["squad"], alone["state"]), False)
solo = baharroth()
checks.eq("...and neither can Baharroth standing on his own",
          cloudstrider.applies(solo), False)
# "if that unit is not within Engagement Range of one or more enemy units"
stuck = withdraw_scene(led=True, enemy_gap=1.0)
checks.eq("...nor one within Engagement Range",
          cloudstrider.can_withdraw(stuck["squad"], stuck["state"]), False)
checks.true("...and the reason says so",
            "Engagement Range" in (cloudstrider.refusal_reason(stuck["squad"], stuck["state"]) or ""))

# The move itself, through the real GameState.
go = withdraw_scene(led=True)
go["squad"].ingress_locked = True          # a stale lock from an earlier arrival
checks.true("the unit starts on the board",
            any(t.squad is go["squad"] for t in go["state"].tokens))
checks.true("withdrawing succeeds", go["ctrl"].withdraw(go["squad"]))
checks.eq("...its models leave the board",
          [t for t in go["state"].tokens if t.squad is go["squad"]], [])
checks.true("...and it is in Strategic Reserves", go["squad"] in go["state"].reserves)
checks.eq("...with the stale ingress lock cleared", go["squad"].ingress_locked, False)
checks.eq("...and it cannot withdraw twice",
          cloudstrider.can_withdraw(go["squad"], go["state"]), False)

# The offer at the end of the opponent's turn belongs to the reacting player.
offer = withdraw_scene(led=True)
offer["ctrl"].offer_at_end_of_turn("Player 2")
checks.true("the end of the opponent's turn raises the offer", offer["decision"].is_pending)
checks.eq("...owned by the reacting player", offer["decision"].player, "Player 1")
checks.true("...with a way to decline", any("Stay" in l for l in tk.options_of(offer["decision"])))
tk.pick_option(offer["decision"], "Stay")
checks.eq("declining leaves it on the board", offer["squad"] in offer["state"].reserves, False)
# ...and it is NOT offered at the end of its own player's turn.
own = withdraw_scene(led=True)
own["ctrl"].offer_at_end_of_turn("Player 1")
checks.eq("nothing is offered at the end of its OWN turn", own["decision"].is_pending, False)


# --- 4. Cloudstrider, half two: the 6" arrival ------------------------------
print("--- 4. Cloudstrider: the arrival ---")

from game.ingress import IngressController, SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN  # noqa: E402
from game.setup import SetupController  # noqa: E402

arm = withdraw_scene(led=True)
setup = SetupController(arm["state"], [], arm["log"])
ing = IngressController(setup, arm["state"], arm["state"].tokens, game_log=arm["log"])
ctrl = cloudstrider.CloudstriderController(
    game_state=arm["state"], decision_manager=arm["decision"],
    ingress_controller=ing, game_log=arm["log"],
)
checks.eq("before arming, the arrival is nobody's", ing.relaxed_arrival_squad, None)
checks.true("arming succeeds for a unit he leads", ctrl.arm_arrival(arm["squad"]))
checks.eq("...and it is THE same override The Shortened Blade uses",
          ing.relaxed_arrival_squad, arm["squad"])
checks.eq("...at the same 6\"", cloudstrider.CLOUDSTRIDER_MIN_ENEMY_DISTANCE_IN,
          SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN)
# "but until the end of the turn, it is not eligible to declare a charge" -
# UNCONDITIONAL, so it is set when the ability is used rather than on confirm.
checks.true("...and the charge lock is set immediately",
            arm["squad"].charge_locked_until_end_of_turn)
# An unled unit gets nothing.
plain = withdraw_scene(led=False)
plain_ing = IngressController(SetupController(plain["state"], [], plain["log"]),
                              plain["state"], plain["state"].tokens, game_log=plain["log"])
plain_ctrl = cloudstrider.CloudstriderController(
    game_state=plain["state"], ingress_controller=plain_ing, game_log=plain["log"])
checks.eq("an unled unit cannot arm it", plain_ctrl.arm_arrival(plain["squad"]), False)
checks.eq("...and takes no charge lock", plain["squad"].charge_locked_until_end_of_turn, False)


# --- 5. Cry of the Wind -----------------------------------------------------
print("--- 5. Cry of the Wind ---")

# "A successful unmodified Hit roll scores a Critical Hit" - so the crit
# threshold IS the hit threshold, not a fixed number. Measured through the real
# crit_hit_threshold().
model = baharroth().models[0]
checks.true("the profile carries it", p.cry_of_the_wind)
checks.eq("before being set up, the ordinary 6 applies (05.02)",
          crit_hit_threshold(model, hit_threshold=2), 6)
model.cry_of_the_wind_active = True
checks.eq("...after being set up, ANY successful roll is critical",
          crit_hit_threshold(model, hit_threshold=2), 2)
checks.eq("...and it follows the threshold rather than being a fixed number",
          crit_hit_threshold(model, hit_threshold=4), 4)
# Without a threshold to hand (the dice-panel label) it falls back to his BS.
checks.eq("with no threshold given it falls back to his printed BS",
          crit_hit_threshold(model), 2)
# RANGED only.
checks.eq("it does NOT reach a melee attack",
          crit_hit_threshold(model, hit_threshold=2, melee_only=True), 6)
# It never makes the threshold worse.
model_bad = baharroth().models[0]
model_bad.cry_of_the_wind_active = True
checks.eq("a worse hit threshold cannot raise the crit threshold above 6",
          crit_hit_threshold(model_bad, hit_threshold=8), 6)
# ...and nothing else has it.
other = tk.build(ork.BOYZ, "Player 2", name="2 Boyz 2").models[0]
other.cry_of_the_wind_active = True
checks.eq("a model without the printed ability is unaffected even if flagged",
          crit_hit_threshold(other, hit_threshold=2), 6)


# --- 6. A/B probe -----------------------------------------------------------
print("--- 6. A/B probe ---")

original = cloudstrider.applies
cloudstrider.applies = lambda squad: False
probe = withdraw_scene(led=True)
checks.eq("A/B: unwired, a led unit cannot withdraw",
          cloudstrider.can_withdraw(probe["squad"], probe["state"]), False)
cloudstrider.applies = original
restored = withdraw_scene(led=True)
checks.true("A/B: restored", cloudstrider.can_withdraw(restored["squad"], restored["state"]))


# --- 7. sprite --------------------------------------------------------------
print("--- 7. sprite ---")

from game import sprites  # noqa: E402

# Art arrived after the datasheet was built. Checked at the model, not at the
# mapping table: a key that resolves to no file on disk is exactly the failure
# this is here to catch.
checks.true("Baharroth resolves a sprite", sprites.sprite_for(lord.models[0]))
checks.true("...and it is his own file",
            "Baharroth" in (sprites.sprite_for(lord.models[0]) or ""))


checks.finish()
