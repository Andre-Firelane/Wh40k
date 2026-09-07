"""Rule 15.11, Heroic Intervention (Core Stratagem, 1 CP).

WHY THIS SUITE EXISTS AT ALL: there was no test for 15.11 - a grep for
"heroic_intervention" across test_*.py came back empty - and it was reported as
a bug ("ich habe heroic intervention benutzt mit dem avatar, aber die cp
scheinen nicht abgezogen geworden zu sein"). That is the same shape as rule
15.12's Counteroffensive, which shipped a 2 CP no-op precisely because nothing
drove it: a Stratagem whose fields all LOOK right from inside its own
controller.

So the CP ledger is driven end to end here - real StratagemController, real
CommandPointManager, real ChargeController - rather than asserted on a stub,
because "the cost was charged" and "the cost was charged to the right player,
exactly once, and only when the offer was accepted" are different claims and
only the second one is worth guarding.

THE OTHER HALF is active_player. This Stratagem runs OUTSIDE the reacting
player's own phase, so offer() flips turn_tracker.active_player to them and
EVERY exit path has to flip it back - decline, and the charge concluding. A
path that forgets leaves the reactor active for the rest of the battle, and
game/command_reroll.py bills CP against whoever is active, so the NEXT
Command Re-roll would be charged to the wrong player. That is the failure mode
closest to the report, so it is measured on every exit.
"""

import testkit as tk
from testkit import Checks, GameState, TurnTracker, build_squad
from game import heroic_intervention
from game.charge import ChargeController
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import aeldari, necrons
from game.heroic_intervention import HeroicInterventionController
from game.movement import MovementController
from game.stratagems import StratagemController
from game.turn import PHASE_CHARGE, PHASES

c = Checks("Heroic Intervention (rule 15.11)")

HUMAN, AI = "Player 1", "Player 2"


def scene(cp=3, gap=5.0, reactor_sheet=aeldari.AVATAR_OF_KHAINE):
    """The reported board: the AI's Charge phase has just ended and the human's
    Avatar stands unengaged within 6" of an enemy unit.

    gap is measured centre to centre, so the default 5.0" leaves 2.8" of EDGE
    distance past the Avatar's 1.575" base - outside rule 03.04's 2"
    Engagement Range (an engaged unit is not eligible) and inside 15.11's 6".
    Both bounds are asserted in section 1 rather than trusted."""
    state = GameState()
    avatar = build_squad(reactor_sheet, HUMAN, name="1 Avatar of Khaine 1")
    foe = build_squad(necrons.IMMORTALS, AI, name="2 Immortals 2")
    tk.line_up(avatar, x=20.0, y=20.0)
    tk.line_up(foe, x=20.0, y=20.0 + gap)
    for squad in (avatar, foe):
        for model in squad.models:
            state.add_token(model)

    turn = TurnTracker(first_player=AI)
    turn.phase_index = PHASES.index(PHASE_CHARGE)
    turn.turn_owner = AI
    turn.set_active(AI)

    pool = CommandPointManager(game_log=tk.Log())
    for player in pool.cp:
        pool.cp[player] = cp
    log, dice, dec = tk.Log(), DiceManager(), DecisionManager()
    pool.game_log = log
    strat = StratagemController(command_points=pool, game_log=log)
    move = MovementController(obstacles=[], all_tokens=state.tokens,
                              turn_tracker=turn, game_log=log, dice_manager=dice)
    charge = ChargeController(
        game_log=log, dice_manager=dice, turn_tracker=turn,
        all_tokens=state.tokens, movement_controller=move,
    )
    ctrl = HeroicInterventionController(
        strat, charge, move, dec, all_tokens=state.tokens, turn_tracker=turn,
        game_log=log,
    )
    return dict(state=state, avatar=avatar, foe=foe, turn=turn, pool=pool,
                strat=strat, charge=charge, move=move, dec=dec, ctrl=ctrl,
                log=log, dice=dice)


# --- 1. the offer itself -----------------------------------------------------
print("--- 1. the offer ---")

s = scene()
# The scene's own two bounds, asserted rather than trusted: the docstring's
# arithmetic is what makes every other check in this file mean something, and
# a gap that quietly drifted inside Engagement Range would make section 1 fail
# for a reason that has nothing to do with rule 15.11.
c.true("the reactor is NOT engaged (03.04) - it would be ineligible",
       not s["avatar"].is_engaged(s["state"].tokens))
c.true("...and IS within the Stratagem's 6 inches",
       s["avatar"].min_distance_to(s["foe"]) <= 6.0)
s["ctrl"].offer(AI, s["dec"])
c.true("an eligible unit within 6 inches produces an offer", s["dec"].is_pending)
c.eq("...addressed to the OPPONENT of whoever's phase just ended",
     s["dec"].player, HUMAN)
labels = tk.options_of(s["dec"])
c.true("...naming the unit and its price",
       any("Avatar" in label and "1 CP" in label for label in labels))
c.true("...with a Decline", any("Decline" in label for label in labels))
c.eq("the reacting player is made active for the window",
     s["turn"].active_player, HUMAN)
c.eq("nothing is charged just for being offered", s["pool"].cp[HUMAN], 3)

# Nothing in range -> no offer at all, so an empty Decline-only prompt never
# flashes and active_player is never touched.
far = scene(gap=30.0)
far["ctrl"].offer(AI, far["dec"])
c.true("no eligible unit -> no prompt", not far["dec"].is_pending)
c.eq("...and active_player is left alone", far["turn"].active_player, AI)

# A player who cannot pay is not offered a Stratagem they cannot buy.
broke = scene(cp=0)
broke["ctrl"].offer(AI, broke["dec"])
c.true("0 CP -> no offer (the engine must not offer what cannot be chosen)",
       not broke["dec"].is_pending)


# --- 2. THE REPORTED CLAIM: the CP ledger ------------------------------------
print("--- 2. the CP ledger ---")

s = scene()
before = s["pool"].cp[HUMAN]
s["ctrl"].offer(AI, s["dec"])
c.true("accepted the offer", tk.pick_option(s["dec"], "Heroic Intervention:"))
c.eq("accepting costs exactly 1 CP - the reported claim",
     s["pool"].cp[HUMAN], before - 1)
c.eq("...charged to the REACTOR, not to whoever's phase it is",
     s["pool"].cp[AI], before)
c.eq("...and the ledger says so exactly once",
     len([line for line in s["log"].lines if line == "Player 1 spends 1 CP."]), 1)
c.true("...and the Stratagem is recorded as used",
       s["log"].has("Player 1 uses Heroic Intervention."))
c.eq("the cost constant is the printed 1 CP",
     heroic_intervention.HEROIC_INTERVENTION_CP_COST, 1)

# The mode prompt is a SECOND decision opened from inside the first one's own
# resolution. It must not charge again.
c.true("a mode decision follows immediately", s["dec"].is_pending)
mode_labels = tk.options_of(s["dec"])
c.true("...offering both printed modes",
       any("Leap to Defend" in label for label in mode_labels)
       and any("Into the Fray" in label for label in mode_labels))
mid = s["pool"].cp[HUMAN]
tk.pick_option(s["dec"], "Into the Fray")
c.eq("choosing a mode does NOT charge a second time", s["pool"].cp[HUMAN], mid)
c.eq("...and the whole Stratagem still cost 1 CP in total",
     s["pool"].cp[HUMAN], before - 1)

# Declining is free.
d = scene()
d["ctrl"].offer(AI, d["dec"])
c.true("declined", tk.pick_option(d["dec"], "Decline"))
c.eq("declining costs nothing", d["pool"].cp[HUMAN], 3)
c.eq("...and hands the turn back to whoever's phase it was",
     d["turn"].active_player, AI)

# Rule 15.01: once per phase.
t = scene(cp=5)
t["ctrl"].offer(AI, t["dec"])
tk.pick_option(t["dec"], "Heroic Intervention:")
tk.pick_option(t["dec"], "Into the Fray")
t["ctrl"].offer(AI, t["dec"])
c.true("it cannot be bought twice in the same phase (rule 15.01)",
       not t["dec"].is_pending)
c.eq("...and no second CP is taken", t["pool"].cp[HUMAN], 4)


# --- 3. active_player is restored on every exit ------------------------------
print("--- 3. active_player is restored ---")

# The decline path is measured above. The other exit is the charge concluding,
# which is what a real game takes - and which command_reroll.py's billing
# depends on.
s = scene()
s["ctrl"].offer(AI, s["dec"])
tk.pick_option(s["dec"], "Heroic Intervention:")
tk.pick_option(s["dec"], "Into the Fray")
c.eq("the reactor stays active while their charge resolves",
     s["turn"].active_player, HUMAN)
s["ctrl"]._on_charge_finished()
c.eq("...and the phase's owner is active again once it ends",
     s["turn"].active_player, AI)
c.true("...with the board selection released",
       s["move"].selected_squad is None)

# The third exit: the charge is declared but never made (a roll too short to
# reach anything, then Cancel). Rule 11.02 resolves the charge either way, so
# this path has to hand active_player back too - and it is the one a player
# actually hits, because a 2D6 that falls short is the common outcome.
f = scene()
f["ctrl"].offer(AI, f["dec"])
tk.pick_option(f["dec"], "Heroic Intervention:")
tk.pick_option(f["dec"], "Into the Fray")
c.eq("a declared-but-unmade charge starts with the reactor active",
     f["turn"].active_player, HUMAN)
f["charge"].decline_charge_move()
c.eq("...and giving up on it still restores the phase owner",
     f["turn"].active_player, AI)
c.eq("...at no extra CP - the 1 CP was already paid",
     f["pool"].cp[HUMAN], 2)


# --- 4. the TARGET line ------------------------------------------------------
print("--- 4. the TARGET line ---")

# "a VEHICLE unit only qualifies if it is also CHARACTER or WALKER."
v = scene(reactor_sheet=aeldari.FALCON)
v["ctrl"].offer(AI, v["dec"])
c.true("a plain VEHICLE unit is not eligible", not v["dec"].is_pending)
c.eq("...and is not charged, obviously", v["pool"].cp[HUMAN], 3)

# The Avatar used above is the positive control for the same clause: a MONSTER,
# not a VEHICLE, so it passes - which is what makes the negative meaningful.
c.true("the Avatar used above is not a VEHICLE (so section 1 proves something)",
       not all(m.profile.vehicle for m in scene()["avatar"].models))

c.finish()
