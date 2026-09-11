"""Tactical Secondary Mission cards (game/secondary_missions.py) - the human's
own mission deck.

What this suite pins, and why some of it looks surprising:

- Centre Ground has THREE outcomes, not two, and the middle one is the easy
  one to lose: 5 VP needs the centre clear to 6", 3 VP only to 3". Section 2
  measures a card at 4.44" from the centre, which is inside one band and
  outside the other - a test that only checked "enemy far" and "enemy close"
  would pass with the 3 VP tier deleted entirely.
- Bring It Down counts MODELS, not units, and scores at the end of *a* turn -
  including the opponent's. Both are printed on the card and both are pinned.
- Nothing is ever scored automatically. Section 5 asserts that an achieved
  card is worth 0 VP until the human answers a prompt, which is the whole
  point of the feature.
- The +1 CP for discarding is NOT re-implemented here: game/command_points.py
  already owned that cap. Section 6 pins that this module defers to it,
  including the case where another ability already spent the round's bonus.
"""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk  # noqa: E402
from game import config, secondary_missions as sm, unit_pick  # noqa: E402
from game.command_points import CommandPointManager  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game import missions  # noqa: E402
from game.missions import MissionController  # noqa: E402
from game.turn import PHASES, PHASE_SHOOTING, TurnTracker  # noqa: E402
from game.factions import aeldari as ae  # noqa: E402
from game.factions import orks as ork  # noqa: E402
from game import army_lists  # noqa: E402
from game.actions import ActionController  # noqa: E402
from game.objectives import is_within_range_of_objective  # noqa: E402

checks = tk.Checks("Secondary Missions")

# Every scenario below assumes the human is on the deck and the AI is not.
config.SECONDARY_MISSION_CARD_PLAYERS = ("Player 1",)
# Pinned so the centre is a known point regardless of which map ran last -
# board_centre() reads config at call time, which is the behaviour being used.
config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN = 60.0, 44.0
CENTRE_X, CENTRE_Y = sm.board_centre()


class FakeOverlay:
    def __init__(self):
        self.announced = []
        self.details = []

    def enqueue(self, player, cards, details=None):
        self.announced.append((player, [c.name for c in cards]))
        self.details.append(dict(details or {}))


def make(cards=None, seed=0, tokens=(), player="Player 1"):
    """A controller wired to real collaborators - the MissionController ledger
    and CommandPointManager cap are the actual ones, not stubs, because half of
    what this suite checks is that this module defers to them."""
    log = tk.Log()
    mission = MissionController(game_log=log)
    cp = CommandPointManager(game_log=log)
    decision = DecisionManager()
    turn = TurnTracker(game_log=tk.Log())
    overlay = FakeOverlay()
    ctrl = sm.SecondaryMissionController(
        player=player, mission_controller=mission, command_points=cp,
        decision_manager=decision, turn_tracker=turn, game_log=log,
        draw_overlay=overlay, cards=(list(cards) if cards is not None else None),
        rng=__import__("random").Random(seed),
    )
    box = list(tokens)
    ctrl.set_tokens_source(lambda: box)
    return ctrl, mission, cp, decision, turn, overlay, log, box


SCORING_PROMPT_MARK = "is complete"


def scoring_prompt_open(decision):
    """Whether the CURRENT prompt is a card's cash-in offer. Needed because
    the discard-for-CP offer follows every end-of-turn chain whenever the hand
    is non-empty and the round's bonus CP is unspent - so "is_pending" alone
    cannot tell "a card was offered" from "you were asked about discarding"."""
    return decision.is_pending and SCORING_PROMPT_MARK in (decision.prompt or "")


def decline_discard(decision):
    """Answer the trailing discard-for-CP offer with its decline option."""
    if decision.is_pending:
        tk.pick_option(decision, "Keep them all")


def squad_at(datasheet, owner, name, x, y, spacing=1.2):
    sq = tk.build(datasheet, owner=owner, name=name)
    for i, m in enumerate(sq.models):
        m.x_in, m.y_in = x + i * spacing, y
    return sq


# --- 1. the deck: draw two per round, once per round, until it runs dry ---
print("--- 1. the deck ---")

# A deck of exactly two PLAIN cards (no When Drawn clause) so this section
# tests deck mechanics alone. Deliberately NOT the shipped deck: a test that
# hard-codes "the deck holds N" goes stale the moment a card is added - which
# is exactly what happened when the deck grew from two cards to four.
plain_a = sm.SecondaryMissionCard("plain_a", "Plain A", "nothing.",
                                  sm.TIMING_END_OF_YOUR_TURN, lambda ctx: 0)
plain_b = sm.SecondaryMissionCard("plain_b", "Plain B", "nothing.",
                                  sm.TIMING_END_OF_YOUR_TURN, lambda ctx: 0)

ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[plain_a, plain_b])
drawn = ctrl.draw_at_command_phase("Player 1", 1)
checks.eq("round 1 draws two cards", len(drawn), sm.CARDS_DRAWN_PER_ROUND)
checks.eq("both land in hand", len(ctrl.hand), 2)
checks.eq("a two-card deck is now empty", len(ctrl.deck), 0)
checks.eq("the draw is announced once", len(overlay.announced), 1)
checks.eq("announced to the card player", overlay.announced[0][0], "Player 1")
checks.eq("announced cards are the drawn cards",
          sorted(overlay.announced[0][1]), sorted(c.name for c in drawn))

# Idempotent by battle round: main.py reaches draw_at_command_phase() from the
# Command-phase hook AND from both battle-start paths, and the battle's first
# Command phase is covered by both.
again = ctrl.draw_at_command_phase("Player 1", 1)
checks.eq("a second call in the same battle round draws nothing", len(again), 0)
checks.eq("hand is unchanged by it", len(ctrl.hand), 2)
checks.eq("no second announcement", len(overlay.announced), 1)

# User's choice: each card once per battle, no reshuffle.
checks.eq("a later round draws nothing from an empty deck",
          len(ctrl.draw_at_command_phase("Player 1", 2)), 0)
checks.true("the log says the deck is empty", log.has("deck is empty"))

# A four-card deck lasts two rounds, and never deals the same card twice.
four = [plain_a, plain_b,
        sm.SecondaryMissionCard("plain_c", "Plain C", "nothing.",
                                sm.TIMING_END_OF_YOUR_TURN, lambda ctx: 0),
        sm.SecondaryMissionCard("plain_d", "Plain D", "nothing.",
                                sm.TIMING_END_OF_YOUR_TURN, lambda ctx: 0)]
ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=four)
r1 = ctrl.draw_at_command_phase("Player 1", 1)
r2 = ctrl.draw_at_command_phase("Player 1", 2)
checks.eq("round 2 draws the remaining two", len(r2), 2)
checks.eq("round 3 draws nothing", len(ctrl.draw_at_command_phase("Player 1", 3)), 0)
checks.eq("no card was dealt twice",
          sorted(c.key for c in r1 + r2), sorted(c.key for c in four))

# The opponent never draws, even on their own Command phase.
ctrl2, _, _, _, _, _, _, _ = make(cards=[plain_a, plain_b])
checks.eq("the AI's Command phase draws nothing",
          len(ctrl2.draw_at_command_phase("Player 2", 1)), 0)
checks.eq("and nothing lands in the human's hand", len(ctrl2.hand), 0)

# The whole feature switches off cleanly - this is what the headless harnesses
# rely on, so it is asserted rather than assumed.
config.SECONDARY_MISSION_CARD_PLAYERS = ()
ctrl3, _, _, _, _, _, _, _ = make(cards=[plain_a, plain_b])
checks.eq("plays_cards is False when the config tuple is empty", ctrl3.plays_cards, False)
checks.eq("no cards are drawn at all", len(ctrl3.draw_at_command_phase("Player 1", 1)), 0)
config.SECONDARY_MISSION_CARD_PLAYERS = ("Player 1",)

# What actually ships, pinned by KEY so adding a card is a visible one-line
# change here rather than a silent one.
checks.eq("the shipped deck", [c.key for c in sm.ALL_CARDS],
          ["centre_ground", "bring_it_down", "a_grievous_blow", "assassination",
           "a_tempting_target", "beacon", "behind_enemy_lines",
           "cleanse", "defend_stronghold", "display_of_might",
           "engage_on_all_fronts", "forward_position", "no_prisoners", "outflank",
           "overwhelming_force", "plunder", "secure_no_mans_land"])
# Burden of Trust is built and tested (section 3g) but deliberately NOT dealt -
# user: "lass Burden of Trust erstmal weg". Pinned from both sides so putting it
# back is a visible one-line change rather than a silent one.
checks.eq("Burden of Trust is not in the shipped deck",
          any(c.key == "burden_of_trust" for c in sm.ALL_CARDS), False)
checks.true("...but the card itself still exists",
            sm.BURDEN_OF_TRUST.key == "burden_of_trust")
checks.eq("every card key is unique",
          len({c.key for c in sm.ALL_CARDS}), len(sm.ALL_CARDS))
for card in sm.ALL_CARDS:
    # Checked against the label table rather than a hand-listed tuple: a new
    # timing has to be given a human label anyway, so this cannot go stale.
    checks.true(f"{card.name} names a scoring instant", card.timing in sm.TIMING_LABELS)
    checks.true(f"{card.name}'s instant has a readable label", bool(card.timing_label))
    checks.true(f"{card.name} has printed text", bool(card.text.strip()))
    # Cleanse is the first card that needs rule 16.01; the rest still do not.
    checks.eq(f"{card.name}: requires_action matches whether it has an action",
              card.requires_action, card.action is not None)


# --- 2. Centre Ground: three bands, plus its two exclusions ---
print("--- 2. Centre Ground ---")


def centre_ground_vp(friendly_x, enemy_x, shocked=False, friendly_y=None):
    mine = squad_at(ae.RANGERS, "Player 1", "1 Rangers 1", friendly_x,
                    friendly_y if friendly_y is not None else CENTRE_Y)
    theirs = squad_at(ae.RANGERS, "Player 2", "2 Rangers 1", enemy_x, CENTRE_Y)
    mine.battle_shocked = shocked
    ctx = sm.MissionContext("Player 1", tokens=list(mine.models) + list(theirs.models))
    return sm._centre_ground(ctx)


# The distances are measured base-EDGE to the centre point, so the assertions
# below name the model x-offset and the band it lands in, not a round number.
checks.eq("friendly on the centre, enemy 20in away: 5 VP",
          centre_ground_vp(CENTRE_X, CENTRE_X + 20), sm.CENTRE_GROUND_FAR_VP)
checks.eq("enemy just outside 6in: still 5 VP",
          centre_ground_vp(CENTRE_X, CENTRE_X + 7), sm.CENTRE_GROUND_FAR_VP)
# THE BAND THAT SEPARATES THE TIERS: 4.44in from the centre is inside 6in and
# outside 3in, so the 5 VP tier fails and the 3 VP tier pays.
checks.eq("enemy between 3in and 6in: the 3 VP tier",
          centre_ground_vp(CENTRE_X, CENTRE_X + 5), sm.CENTRE_GROUND_NEAR_VP)
checks.eq("enemy inside 3in: nothing",
          centre_ground_vp(CENTRE_X, CENTRE_X + 2), 0)
checks.eq("a battle-shocked friendly unit does not hold the centre",
          centre_ground_vp(CENTRE_X, CENTRE_X + 20, shocked=True), 0)
checks.eq("no friendly unit within 3in of the centre: nothing",
          centre_ground_vp(CENTRE_X + 10, CENTRE_X + 30), 0)

# "End of YOUR turn" - the card is not checked when the opponent's turn ends.
card = sm.CENTRE_GROUND
checks.true("Centre Ground scores at the end of your own turn",
            card.scores_at(sm.MissionContext("Player 1", ending_player="Player 1")))
checks.eq("Centre Ground does NOT score at the end of the opponent's turn",
          card.scores_at(sm.MissionContext("Player 1", ending_player="Player 2")), False)


# --- 3. Bring It Down: models, not units; end of ANY turn ---
print("--- 3. Bring It Down ---")


def killed_models(datasheet, owner, count):
    sq = squad_at(datasheet, owner, f"{owner[-1]} kills 1", 10.0, 10.0)
    return sq.models[:count]


big = tk.build(ork.BATTLEWAGON, owner="Player 2", name="2 Battlewagon 1")
small = tk.build(ae.RANGERS, owner="Player 2", name="2 Rangers 1")
checks.true("the Battlewagon really is a 10+ Wounds model",
            big.models[0].profile.wounds >= sm.BRING_IT_DOWN_WOUNDS)
checks.true("a Ranger really is not", small.models[0].profile.wounds < sm.BRING_IT_DOWN_WOUNDS)


def bring_it_down_vp(dead):
    return sm._bring_it_down(sm.MissionContext("Player 1", destroyed_this_turn=dead))


checks.eq("no kills: nothing", bring_it_down_vp([]), 0)
checks.eq("one 10+ Wounds enemy model: 5 VP",
          bring_it_down_vp([big.models[0]]), sm.BRING_IT_DOWN_VP_PER_MODEL)
# The card's own MAX 5VP stamp - the formula is per model, the cap is on top.
two_big = tk.build(ork.BATTLEWAGON, owner="Player 2", name="2 Battlewagon 2")
checks.eq("two of them: still capped at 5 VP",
          bring_it_down_vp([big.models[0], two_big.models[0]]), sm.BRING_IT_DOWN_MAX_VP)
checks.eq("a 9-or-fewer Wounds model pays nothing",
          bring_it_down_vp([small.models[0]]), 0)
# Own losses never pay.
mine_big = tk.build(ork.BATTLEWAGON, owner="Player 1", name="1 Battlewagon 1")
checks.eq("losing your OWN 10+ Wounds model pays nothing",
          bring_it_down_vp([mine_big.models[0]]), 0)

checks.true("Bring It Down scores at the end of your own turn",
            sm.BRING_IT_DOWN.scores_at(sm.MissionContext("Player 1", ending_player="Player 1")))
checks.true("Bring It Down ALSO scores at the end of the opponent's turn",
            sm.BRING_IT_DOWN.scores_at(sm.MissionContext("Player 1", ending_player="Player 2")))

# WHEN DRAWN: only while no enemy 10+ Wounds model is on the battlefield.
ctx_empty = sm.MissionContext("Player 1", tokens=[])
ctx_big = sm.MissionContext("Player 1", tokens=list(big.models))
checks.true("When Drawn applies with no big enemy model on the table",
            sm.BRING_IT_DOWN.when_drawn_may_redraw(ctx_empty))
checks.eq("When Drawn does not apply with one on the table",
          sm.BRING_IT_DOWN.when_drawn_may_redraw(ctx_big), False)
checks.eq("Centre Ground has no When Drawn clause at all",
          sm.CENTRE_GROUND.when_drawn_may_redraw(ctx_empty), False)


# --- 3b. A Grievous Blow: UNITS of Starting Strength 13+ ---
print("--- 3b. A Grievous Blow ---")

# Built from the REAL army lists, not hand-made squads: "Starting Strength" is
# a property of how a list is composed, and the interesting cases (an attached
# unit crossing 13 only once its leaders are merged in, a roster with no
# qualifying unit at all) exist in the shipped lists and nowhere else.
necrons = army_lists.preview_squads("necrons", "Player 2")
tau_list = army_lists.preview_squads("tau", "Player 2")
big_unit = next(s for s in necrons if s.starting_model_count >= sm.GRIEVOUS_BLOW_STARTING_STRENGTH)
small_unit = next(s for s in necrons if s.starting_model_count < sm.GRIEVOUS_BLOW_STARTING_STRENGTH)
own_big = next(s for s in army_lists.preview_squads("orks", "Player 1")
               if s.starting_model_count >= sm.GRIEVOUS_BLOW_STARTING_STRENGTH)

checks.true("the Necron blob really is Starting Strength 13+",
            big_unit.starting_model_count >= sm.GRIEVOUS_BLOW_STARTING_STRENGTH)
checks.true("and the comparison unit really is not",
            small_unit.starting_model_count < sm.GRIEVOUS_BLOW_STARTING_STRENGTH)


def grievous_vp(destroyed=()):
    return sm._grievous_blow(sm.MissionContext("Player 1", destroyed_squads_this_turn=destroyed))


checks.eq("nothing destroyed: nothing", grievous_vp(), 0)
checks.eq("a small enemy unit pays nothing", grievous_vp([small_unit]), 0)
checks.eq("one 13+ enemy unit: 5 VP", grievous_vp([big_unit]), sm.GRIEVOUS_BLOW_VP_PER_UNIT)
checks.eq("two of them: still capped at 5 VP",
          grievous_vp([big_unit, big_unit]), sm.GRIEVOUS_BLOW_MAX_VP)
checks.eq("losing your OWN 13+ unit pays nothing", grievous_vp([own_big]), 0)

# Starting Strength, not current strength - a mob down to two models is still
# a Starting Strength 13+ unit when it finally dies.
survivors = big_unit.models[:2]
kept, big_unit.models = big_unit.models, survivors
checks.eq("a nearly-wiped 13+ unit still counts when it dies",
          grievous_vp([big_unit]), sm.GRIEVOUS_BLOW_VP_PER_UNIT)
big_unit.models = kept

# It counts UNITS where Bring It Down counts MODELS - the two cards look alike
# and are fed from two different hooks, so they are pinned against each other.
checks.eq("Bring It Down scores nothing for a destroyed 13+ unit per se",
          sm._bring_it_down(sm.MissionContext("Player 1", destroyed_this_turn=[])), 0)
checks.eq("A Grievous Blow scores nothing for a destroyed 10+ Wounds model per se",
          grievous_vp([]), 0)

checks.true("A Grievous Blow scores at the end of a turn - either player's",
            sm.A_GRIEVOUS_BLOW.scores_at(sm.MissionContext("Player 1", ending_player="Player 2")))

# WHEN DRAWN. Measured: the T'au roster has NO unit of Starting Strength 13+
# at all, so against them the clause is not an edge case but the normal state.
checks.eq("no 13+ unit in the whole T'au list",
          [s.name for s in tau_list if s.starting_model_count >= sm.GRIEVOUS_BLOW_STARTING_STRENGTH], [])
tau_models = [m for s in tau_list for m in s.models]
necron_models = [m for s in necrons for m in s.models]
checks.true("against T'au the When Drawn clause applies",
            sm.A_GRIEVOUS_BLOW.when_drawn_may_redraw(
                sm.MissionContext("Player 1", tokens=tau_models)))
checks.eq("against Necrons it does not",
          sm.A_GRIEVOUS_BLOW.when_drawn_may_redraw(
              sm.MissionContext("Player 1", tokens=necron_models)), False)


# --- 3c. Assassination: enemy CHARACTER models ---
print("--- 3c. Assassination ---")

lychguard = next(s for s in necrons if "Lychguard" in s.name)
enemy_character = next(m for m in lychguard.models if m.profile.character)
enemy_grunt = next(m for m in lychguard.models if not m.profile.character)
no_character_squads = [s for s in necrons if not any(m.profile.character for m in s.models)]


def assassination_vp(**kw):
    return sm._assassination(sm.MissionContext("Player 1", **kw))


checks.true("the Overlord really carries the CHARACTER keyword", enemy_character.profile.character)
checks.eq("and a Lychguard really does not", enemy_grunt.profile.character, False)

checks.eq("nothing destroyed: nothing", assassination_vp(all_squads=necrons), 0)
checks.eq("one enemy CHARACTER destroyed this turn: 5 VP",
          assassination_vp(destroyed_this_turn=[enemy_character], all_squads=necrons),
          sm.ASSASSINATION_VP)
checks.eq("a non-character death pays nothing",
          assassination_vp(destroyed_this_turn=[enemy_grunt], all_squads=necrons), 0)

# The second branch: killed in an EARLIER turn, none left now.
checks.eq("all enemy CHARACTERs dead during the battle: 5 VP",
          assassination_vp(destroyed_characters_this_battle=[enemy_character],
                           all_squads=no_character_squads),
          sm.ASSASSINATION_VP)
checks.eq("...but not while one is still alive",
          assassination_vp(destroyed_characters_this_battle=[enemy_character],
                           all_squads=necrons), 0)
# Vacuous truth guard: an opponent who never fielded a character must not
# satisfy "all of them have been destroyed" every single turn.
checks.eq("an opponent who never had a CHARACTER pays nothing",
          assassination_vp(all_squads=no_character_squads), 0)


class _OffBoardSquad:
    """Stands in for a unit in Strategic Reserves or inside a transport - it
    has models and an owner but is not on the board."""

    def __init__(self, owner, models):
        self.owner, self.models = owner, models


# THE TRAP: "all destroyed" is not "none on the battlefield". A character in
# reserves is off the board and very much alive. Measured both ways, because
# reading the board alone silently awards the 5 VP.
reserved = _OffBoardSquad("Player 2", [enemy_character])
checks.eq("a CHARACTER waiting in reserves blocks the all-destroyed branch",
          assassination_vp(destroyed_characters_this_battle=[enemy_grunt],
                           all_squads=no_character_squads + [reserved]), 0)
checks.eq("...whereas ignoring reserves would have wrongly paid out",
          assassination_vp(destroyed_characters_this_battle=[enemy_grunt],
                           all_squads=no_character_squads),
          sm.ASSASSINATION_VP)

checks.true("Assassination scores at the end of a turn - either player's",
            sm.ASSASSINATION.scores_at(sm.MissionContext("Player 1", ending_player="Player 2")))
checks.eq("it has no When Drawn clause",
          sm.ASSASSINATION.when_drawn_may_redraw(sm.MissionContext("Player 1")), False)

# Your own losses never pay, either branch.
own_necrons = army_lists.preview_squads("necrons", "Player 1")
own_character = next(m for s in own_necrons for m in s.models if m.profile.character)
checks.eq("losing your OWN character pays nothing",
          assassination_vp(destroyed_this_turn=[own_character], all_squads=necrons), 0)

# The feed: record_destroyed_model() is what remembers a character for the
# whole battle, and it must not remember friendly ones.
ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[sm.ASSASSINATION])
ctrl.record_destroyed_model(enemy_character)
ctrl.record_destroyed_model(own_character)
ctrl.record_destroyed_model(enemy_grunt)
checks.eq("only the ENEMY character is remembered for the battle",
          len(ctrl._destroyed_characters_this_battle), 1)
ctrl.hand = [sm.ASSASSINATION]
ctrl.begin_end_of_turn("Player 2")
checks.true("and it opens the prompt at the end of a turn", decision.is_pending)
tk.pick_option(decision, "Score 5")
checks.eq("paying 5 VP", mission.secondary_points.get("Player 1", 0), sm.ASSASSINATION_VP)
checks.true("the battle-long list SURVIVES the turn boundary",
            len(ctrl._destroyed_characters_this_battle) == 1)

# The unit feed dedupes: the death sweep can reach an emptied squad again.
ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[sm.A_GRIEVOUS_BLOW])
ctrl.record_destroyed_squad(big_unit)
ctrl.record_destroyed_squad(big_unit)
checks.eq("one destroyed unit is recorded once, not twice",
          len(ctrl._destroyed_squads_this_turn), 1)
ctrl.hand = [sm.A_GRIEVOUS_BLOW]
ctrl.begin_end_of_turn("Player 1")
checks.true("it opens the prompt", decision.is_pending)
tk.pick_option(decision, "Score 5")
checks.eq("for 5 VP, not 10", mission.secondary_points.get("Player 1", 0),
          sm.GRIEVOUS_BLOW_VP_PER_UNIT)
checks.eq("the per-turn unit list clears at the boundary",
          len(ctrl._destroyed_squads_this_turn), 0)

# --- 3d. A Tempting Target: the opponent names an objective ---
print("--- 3d. A Tempting Target ---")

# Built on a REAL map: the card is entirely about board geometry (which
# objectives sit in No Man's Land, how far each is from your own deployment
# zone), and hand-made rectangles would only test the arithmetic, not the
# classification the maps actually produce.
from game import maps  # noqa: E402
from game.game_state import GameState  # noqa: E402

_map = maps.MAPS["map2"]
maps.apply_to_config(_map)
board = GameState()
_map.build(board)


def board_ctx(**kw):
    return sm.MissionContext("Player 1", objectives=board.objectives,
                             deployment_zones=board.deployment_zones, **kw)


nml = sm.no_mans_land_objectives(board_ctx())
home = [o for o in board.objectives if o not in nml]
checks.eq("map2 has three No Man's Land objectives", len(nml), 3)
checks.eq("and two home objectives", len(home), 2)
# The classification is geometric, not by name - but on every shipped map the
# two agree, which is what makes the geometric test safe. Pinned so a future
# map that breaks the coincidence shows up here.
checks.eq("every excluded objective is in fact a home objective",
          sorted(o.name for o in home), ["P1 Home Objective", "P2 Home Objective"])
for objective in nml:
    cx, cy = sm.objective_centre(objective)
    checks.eq(f"{objective.name} is in nobody's deployment zone",
              any(z.contains_point(cx, cy) for z in board.deployment_zones), False)

# Rule the user supplied: "eines der Objectives, die die KI kontrolliert. Wenn
# sie keins kontrolliert, dann das, was am weitesten weg von meiner
# Aufstellungszone ist."
p1_zone = next(z for z in board.deployment_zones if z.owner == "Player 1")


def distance_from_my_zone(objective):
    return sm.zone_distance(p1_zone, *sm.objective_centre(objective))


for objective in board.objectives:
    objective.controlled_by = None

farthest = max(nml, key=distance_from_my_zone)
nearest = min(nml, key=distance_from_my_zone)
checks.true("the farthest and nearest No Man's Land objectives are different",
            farthest is not nearest)
picked = sm._tempting_target_on_draw(board_ctx())
checks.eq("with nothing controlled it picks the one farthest from my zone",
          picked.name, farthest.name)
checks.true("which really is farther than the nearest one",
            distance_from_my_zone(picked) > distance_from_my_zone(nearest))

# ...and an objective the AI controls wins even when it is the NEAREST one -
# otherwise the first branch would be indistinguishable from the second.
nearest.controlled_by = "Player 2"
picked = sm._tempting_target_on_draw(board_ctx())
checks.eq("an objective the AI controls is chosen instead", picked.name, nearest.name)
checks.true("even though it is the nearest to my zone",
            distance_from_my_zone(picked) < distance_from_my_zone(farthest))

# One I control is NOT a tempting target - only the opponent's.
nearest.controlled_by = "Player 1"
checks.eq("an objective I control is not chosen",
          sm._tempting_target_on_draw(board_ctx()).name, farthest.name)

# A home objective the AI controls is out of scope entirely.
for objective in board.objectives:
    objective.controlled_by = None
next(o for o in home if o.name == "P2 Home Objective").controlled_by = "Player 2"
checks.eq("a home objective is never chosen, even when the AI holds it",
          sm._tempting_target_on_draw(board_ctx()).name, farthest.name)

# Scoring: 14.02's controlled_by on the remembered objective.
for objective in board.objectives:
    objective.controlled_by = None
target = farthest
state = {"objective": target}
checks.eq("nobody holds the target: nothing",
          sm._tempting_target(board_ctx(card_state=state)), 0)
target.controlled_by = "Player 2"
checks.eq("the AI holds it: nothing", sm._tempting_target(board_ctx(card_state=state)), 0)
target.controlled_by = "Player 1"
checks.eq("I hold it: 5 VP", sm._tempting_target(board_ctx(card_state=state)),
          sm.TEMPTING_TARGET_VP)
checks.eq("a card with no target scores nothing",
          sm._tempting_target(board_ctx(card_state={})), 0)
checks.true("A Tempting Target scores at the end of YOUR turn",
            sm.A_TEMPTING_TARGET.scores_at(sm.MissionContext("Player 1", ending_player="Player 1")))
checks.eq("not at the end of the opponent's",
          sm.A_TEMPTING_TARGET.scores_at(sm.MissionContext("Player 1", ending_player="Player 2")), False)

# The choice is made ONCE, at draw time, and remembered - not re-chosen later
# when the board has moved on.
for objective in board.objectives:
    objective.controlled_by = None
ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[sm.A_TEMPTING_TARGET])
ctrl.set_objectives_source(lambda: board.objectives)
ctrl.set_zones_source(lambda: board.deployment_zones)
ctrl.draw_at_command_phase("Player 1", 1)
chosen = ctrl.card_state["a_tempting_target"]["objective"]
checks.true("the draw stores a target", chosen is not None)
checks.eq("the log names it", log.has(chosen.name), True)
# Now let the AI take a different one; the target must not move.
other = next(o for o in nml if o is not chosen)
other.controlled_by = "Player 2"
checks.eq("the target does not change when the board does",
          ctrl.card_state["a_tempting_target"]["objective"].name, chosen.name)

# The strip and the notice must be able to say WHICH objective, or the card is
# unplayable - its printed text only ever says "your tempting target".
detail = ctrl.detail_for(sm.A_TEMPTING_TARGET)
checks.true("a detail line is offered for the card", bool(detail))
checks.true("and it names the objective", chosen.name in detail)
checks.eq("a card without setup offers no detail line",
          ctrl.detail_for(sm.CENTRE_GROUND), None)

# Per-card state is per CARD, not shared - the cards are module singletons, so
# a controller that stored state on them would leak between battles.
ctrl2, _, _, _, _, _, _, _ = make(cards=[sm.A_TEMPTING_TARGET])
ctrl2.set_objectives_source(lambda: board.objectives)
ctrl2.set_zones_source(lambda: board.deployment_zones)
checks.eq("a fresh controller starts with no card state", ctrl2.card_state, {})
checks.eq("and the card object itself carries none",
          hasattr(sm.A_TEMPTING_TARGET, "objective"), False)

# End to end through the real prompt chain.
for objective in board.objectives:
    objective.controlled_by = None
ctrl.card_state["a_tempting_target"]["objective"].controlled_by = "Player 1"
ctrl.begin_end_of_turn("Player 1")
checks.true("holding the target opens the prompt at the end of your turn",
            scoring_prompt_open(decision))
tk.pick_option(decision, "Score 5")
checks.eq("and pays 5 VP", mission.secondary_points.get("Player 1", 0), sm.TEMPTING_TARGET_VP)

# A map with no No Man's Land objective at all must not crash the draw.
empty_ctx = sm.MissionContext("Player 1", objectives=[], deployment_zones=[])
checks.eq("no candidates: no target", sm._tempting_target_on_draw(empty_ctx), None)
checks.true("and the detail line says so",
            "No target" in sm._tempting_target_detail(sm.MissionContext("Player 1", card_state={})))

# --- 3e. Beacon: a unit you plant, checked once at the very end ---
print("--- 3e. Beacon ---")

from game.turn import PHASES  # noqa: E402
from game.missions import BATTLE_ROUNDS  # noqa: E402

# map2 again: P1 deploys in y 32..44, so its half is y >= 22 and the enemy half
# is y < 22. Every distance below is named by the band it lands in.
maps.apply_to_config(_map)
p1_zone = next(z for z in board.deployment_zones if z.owner == "Player 1")


def beacon_unit_at(y, name="1 Rangers 1"):
    squad = tk.build(ae.RANGERS, owner="Player 1", name=name)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = 20 + i * 1.2, y
    return squad


def beacon_ctx(squad, on_board=True, **kw):
    return sm.MissionContext(
        "Player 1", tokens=(list(squad.models) if on_board else []),
        objectives=board.objectives, deployment_zones=board.deployment_zones,
        card_state={"objective": squad}, **kw)


# The user's definition of territory, checked directly: "Territory heisst
# einfach ausserhalb meiner Spielfeldhaelfte."
empty = sm.MissionContext("Player 1", deployment_zones=board.deployment_zones)
checks.true("my own deployment zone is in my territory", sm.in_own_territory(empty, 20, 38))
checks.true("so is my side of the centre line", sm.in_own_territory(empty, 20, 26))
checks.eq("the enemy half is not", sm.in_own_territory(empty, 20, 18), False)
checks.eq("nor the enemy deployment zone", sm.in_own_territory(empty, 20, 5), False)
# Derived from the zones, not assumed - the same call for the OTHER player must
# come out mirrored, or the derivation is really a hard-coded side.
theirs = sm.MissionContext("Player 2", deployment_zones=board.deployment_zones)
checks.true("Player 2's territory is the other half", sm.in_own_territory(theirs, 20, 5))
checks.eq("and excludes Player 1's half", sm.in_own_territory(theirs, 20, 38), False)

# The three bands of the card, plus the "on the battlefield" gate.
checks.eq("inside my deployment zone: nothing",
          sm._beacon(beacon_ctx(beacon_unit_at(38))), 0)
checks.eq("out of the zone but still my half: 3 VP",
          sm._beacon(beacon_ctx(beacon_unit_at(26))), sm.BEACON_OUTSIDE_DEPLOYMENT_VP)
checks.eq("in the enemy half: 5 VP",
          sm._beacon(beacon_ctx(beacon_unit_at(18))), sm.BEACON_OUTSIDE_TERRITORY_VP)
checks.eq("deep in the enemy deployment zone: still 5 VP",
          sm._beacon(beacon_ctx(beacon_unit_at(5))), sm.BEACON_OUTSIDE_TERRITORY_VP)
checks.eq("a beacon that is not on the battlefield scores nothing",
          sm._beacon(beacon_ctx(beacon_unit_at(18), on_board=False)), 0)
checks.eq("and no beacon at all scores nothing",
          sm._beacon(sm.MissionContext("Player 1", card_state={})), 0)

# "Outside" means the WHOLE unit has left - one model still inside is enough to
# fail. Built by dragging a single model back over the line.
straddling = beacon_unit_at(26)
straddling.models[0].y_in = 38.0  # back inside the deployment zone
checks.eq("one model still inside the zone loses the 3 VP",
          sm._beacon(beacon_ctx(straddling)), 0)
straddling = beacon_unit_at(18)
straddling.models[0].y_in = 26.0  # back over the centre line, still out of the zone
checks.eq("one model back in my half drops it from 5 VP to 3 VP",
          sm._beacon(beacon_ctx(straddling)), sm.BEACON_OUTSIDE_DEPLOYMENT_VP)

# TIMING. "END OF OPPONENTS TURN - ROUND 5" is ONE instant in the battle.
for ending, rnd, want in [
    ("Player 2", BATTLE_ROUNDS, True),
    ("Player 1", BATTLE_ROUNDS, False),      # your own turn, wrong half of the pair
    ("Player 2", BATTLE_ROUNDS - 1, False),  # right player, wrong round
    ("Player 2", BATTLE_ROUNDS + 1, False),  # the rolled-over counter, see below
]:
    checks.eq(f"scores_at(ending={ending}, round={rnd})",
              sm.BEACON.scores_at(sm.MissionContext("Player 1", ending_player=ending,
                                                    battle_round=rnd)), want)

# THE TRAP the battle_round argument exists for: begin_end_of_turn() runs AFTER
# TurnTracker.advance_phase(), and when the SECOND player of a round finishes,
# that call has already incremented the counter. Reading turn_tracker directly
# at that instant would see round 6 and the card could never fire.
# Measured on a MID-battle round, where the rollover is still real: the final
# round no longer rolls over at all (rule 07.01 ends the battle there instead,
# see test_battle_end.py), so the hazard has to be shown where it still exists.
rollover = TurnTracker(first_player="Player 1", game_log=tk.Log())
rollover.battle_round = BATTLE_ROUNDS - 2
rollover.turn_index_in_round = 1
rollover.active_player = rollover.turn_owner = "Player 2"
rollover.phase_index = len(PHASES) - 1
round_before = rollover.battle_round
rollover.advance_phase()
checks.eq("advance_phase() really does roll the counter over at a turn's end",
          rollover.battle_round, round_before + 1)
checks.true("so the live counter and the ending turn's round disagree",
            rollover.battle_round != round_before)

# ...and at the FINAL round the counter now stays put, because the battle ends
# there. Both readings agree at that instant - but the argument is still the
# right one to pass, and the rounds above are why.
final = TurnTracker(first_player="Player 1", game_log=tk.Log())
final.battle_round = BATTLE_ROUNDS
final.turn_index_in_round = 1
final.active_player = final.turn_owner = "Player 2"
final.phase_index = len(PHASES) - 1
final.advance_phase()
checks.true("the final round ends the battle", final.battle_over)
checks.eq("...and leaves the counter on it", final.battle_round, BATTLE_ROUNDS)
checks.eq("the round the ending turn belonged to is the one that scores",
          sm.BEACON.scores_at(sm.MissionContext("Player 1", ending_player="Player 2",
                                                battle_round=BATTLE_ROUNDS)), True)
checks.eq("a round before the last does not",
          sm.BEACON.scores_at(sm.MissionContext("Player 1", ending_player="Player 2",
                                                battle_round=BATTLE_ROUNDS - 1)), False)

# The interactive WHEN DRAWN setup: the player picks, from board units plus
# embarked ones, and NOT from Strategic Reserves.
on_board = beacon_unit_at(38, name="1 Rangers 1")
in_transport = tk.build(ae.RANGERS, owner="Player 1", name="1 Fire Dragons 1")
in_reserve = tk.build(ae.RANGERS, owner="Player 1", name="1 Warp Spiders 1")
enemy = tk.build(ae.RANGERS, owner="Player 2", name="2 Rangers 1")
for i, model in enumerate(enemy.models):
    model.x_in, model.y_in = 20 + i * 1.2, 5

ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[sm.BEACON])
box.extend(list(on_board.models) + list(enemy.models))
ctrl.set_zones_source(lambda: board.deployment_zones)
ctrl.set_objectives_source(lambda: board.objectives)
ctrl.set_embarked_source(lambda: [in_transport])
ctrl.draw_at_command_phase("Player 1", 1)

checks.true("drawing Beacon asks the player to choose", decision.is_pending)
labels = tk.options_of(decision)
checks.true("a unit on the battlefield is offered", "1 Rangers 1" in labels)
checks.true("so is one embarked in a transport", "1 Fire Dragons 1" in labels)
checks.eq("a unit in Strategic Reserves is NOT offered",
          "1 Warp Spiders 1" in labels, False)
checks.eq("nor is an enemy unit", "2 Rangers 1" in labels, False)
checks.eq("nothing is announced until the choice is made", len(overlay.announced), 0)

tk.pick_option(decision, "1 Rangers 1")
checks.eq("the chosen unit is remembered",
          ctrl.card_state["beacon"]["objective"].name, "1 Rangers 1")
checks.eq("and the draw is announced afterwards", len(overlay.announced), 1)
detail = ctrl.detail_for(sm.BEACON)
checks.true("the strip can name the beacon", detail and "1 Rangers 1" in detail)
checks.true("the announcement carries it too",
            "1 Rangers 1" in overlay.details[0].get("beacon", ""))

# End to end at the real instant, through the prompt chain.
for model in on_board.models:
    model.y_in = 18.0  # into the enemy half
ctrl.begin_end_of_turn("Player 2", battle_round=BATTLE_ROUNDS)
checks.true("at the end of the enemy's final turn the card is offered",
            scoring_prompt_open(decision))
tk.pick_option(decision, "Score 5")
checks.eq("paying its 5 VP tier",
          mission.secondary_points.get("Player 1", 0), sm.BEACON_OUTSIDE_TERRITORY_VP)

# ...and NOT at any other turn end, however well placed the beacon is.
ctrl2, mission2, _, decision2, _, _, _, box2 = make(cards=[sm.BEACON])
box2.extend(list(on_board.models))
ctrl2.set_zones_source(lambda: board.deployment_zones)
ctrl2.hand = [sm.BEACON]
ctrl2.card_state["beacon"] = {"objective": on_board}
ctrl2.begin_end_of_turn("Player 2", battle_round=BATTLE_ROUNDS - 1)
checks.eq("an earlier round offers nothing", scoring_prompt_open(decision2), False)
ctrl2.begin_end_of_turn("Player 1", battle_round=BATTLE_ROUNDS)
checks.eq("nor does your OWN final turn", scoring_prompt_open(decision2), False)

# A card with nothing to choose records the miss instead of hanging.
ctrl3, _, _, decision3, _, overlay3, log3, box3 = make(cards=[sm.BEACON])
ctrl3.set_zones_source(lambda: board.deployment_zones)
ctrl3.draw_at_command_phase("Player 1", 1)
checks.eq("with no eligible unit nothing is asked", decision3.is_pending, False)
checks.eq("the miss is recorded", ctrl3.card_state["beacon"]["objective"], None)
checks.true("and logged", log3.has("nothing eligible"))
checks.eq("the card then scores nothing", sm.BEACON.score(
    sm.MissionContext("Player 1", card_state={"objective": None})), 0)

# --- 3f. Behind Enemy Lines: units WHOLLY in the enemy zone ---
print("--- 3f. Behind Enemy Lines ---")

enemy_zone = next(z for z in board.deployment_zones if z.owner == "Player 2")  # map2: y 0..12


def bel_unit(y, name, models=None):
    squad = tk.build(ae.RANGERS, owner="Player 1", name=name)
    if models is not None:
        squad.models[:] = squad.models[:models]
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = 20 + i * 1.5, y
    return squad


def bel_vp(units, battle_round=None):
    tokens = [m for u in units for m in u.models]
    return sm._behind_enemy_lines(sm.MissionContext(
        "Player 1", tokens=tokens, deployment_zones=board.deployment_zones,
        battle_round=battle_round))


checks.eq("no units: nothing", bel_vp([]), 0)
checks.eq("a unit at home: nothing", bel_vp([bel_unit(30, "1 Rangers 1")]), 0)
checks.eq("one unit in the enemy zone: 3 VP",
          bel_vp([bel_unit(6, "1 Rangers 1")]), sm.BEHIND_ENEMY_LINES_VP_PER_UNIT)
# 3 VP each capped at 5, so the second unit adds 2 and the third adds nothing.
checks.eq("two units: capped at 5 VP",
          bel_vp([bel_unit(6, "1 Rangers 1"), bel_unit(8, "1 Rangers 2")]),
          sm.BEHIND_ENEMY_LINES_MAX_VP)
checks.eq("three units: still 5 VP",
          bel_vp([bel_unit(6, "1 Rangers 1"), bel_unit(8, "1 Rangers 2"),
                  bel_unit(4, "1 Rangers 3")]), sm.BEHIND_ENEMY_LINES_MAX_VP)

# "WHOLLY within" - one model left behind loses the whole unit's 3 VP. This is
# rule 03.01's own contains_circle test (the BASE has to be inside), not a
# centre-point test, so a model on the zone's edge does not squeak in either.
straggler = bel_unit(6, "1 Rangers 9")
straggler.models[0].y_in = 30.0
checks.eq("one model left behind: nothing", bel_vp([straggler]), 0)
edge = bel_unit(6, "1 Rangers 8")
edge.models[0].y_in = enemy_zone.rects[0][1] + enemy_zone.rects[0][3] / 2.0  # centre exactly on the edge
checks.eq("a model whose base straddles the zone edge does not count",
          bel_vp([edge]), 0)

shocked = bel_unit(6, "1 Rangers 7")
shocked.battle_shocked = True
checks.eq("a battle-shocked unit is excluded", bel_vp([shocked]), 0)

# Its When Drawn clause is about the ROUND, not the enemy army.
checks.true("the redraw applies in battle round 1", bel_vp and
            sm.BEHIND_ENEMY_LINES.when_drawn_may_redraw(
                sm.MissionContext("Player 1", battle_round=1)))
checks.eq("but not in battle round 2",
          sm.BEHIND_ENEMY_LINES.when_drawn_may_redraw(
              sm.MissionContext("Player 1", battle_round=2)), False)
checks.true("Behind Enemy Lines scores at the end of YOUR turn",
            sm.BEHIND_ENEMY_LINES.scores_at(
                sm.MissionContext("Player 1", ending_player="Player 1")))

# SHUFFLED BACK, not discarded - and the replacement must be a DIFFERENT card.
# Drawing before returning it is what guarantees that; returning it first lets
# a small deck hand the same card straight back, and the clause silently does
# nothing.
bel_ctrl, _, _, bel_dec, _, _, bel_log, bel_box = make(
    cards=[sm.BEHIND_ENEMY_LINES, sm.CENTRE_GROUND, sm.ASSASSINATION, sm.BRING_IT_DOWN])
bel_ctrl.set_zones_source(lambda: board.deployment_zones)
bel_ctrl.set_objectives_source(lambda: board.objectives)
bel_ctrl.draw_at_command_phase("Player 1", 1)
checks.true("drawing it in round 1 offers the redraw", bel_dec.is_pending)
tk.pick_option(bel_dec, "Discard and redraw")
while bel_dec.is_pending:
    tk.pick_option(bel_dec, "Keep it")
checks.true("it goes back into the DECK",
            any(c.key == "behind_enemy_lines" for c in bel_ctrl.deck))
checks.eq("not onto the discard pile",
          any(c.key == "behind_enemy_lines" for c in bel_ctrl.discarded), False)
checks.eq("and not left in hand",
          any(c.key == "behind_enemy_lines" for c in bel_ctrl.hand), False)
checks.eq("the replacement is a different card",
          any(c.key == "behind_enemy_lines" for c in bel_ctrl.hand), False)
checks.eq("the hand still holds two cards", len(bel_ctrl.hand), 2)
checks.true("the log says shuffled, not discarded", bel_log.has("shuffles"))

# The contrast, on the same machinery: Bring It Down's clause DISCARDS.
bid_ctrl, _, _, bid_dec, _, _, _, _ = make(
    cards=[sm.BRING_IT_DOWN, sm.CENTRE_GROUND, sm.ASSASSINATION])
bid_ctrl.draw_at_command_phase("Player 1", 1)
if bid_dec.is_pending:
    tk.pick_option(bid_dec, "Discard and redraw")
    while bid_dec.is_pending:
        tk.pick_option(bid_dec, "Keep it")
    checks.true("Bring It Down is discarded, not shuffled back",
                any(c.key == "bring_it_down" for c in bid_ctrl.discarded))
    checks.eq("...and does not rejoin the deck",
              any(c.key == "bring_it_down" for c in bid_ctrl.deck), False)


# --- 3g. Burden of Trust: guarded objectives ---
print("--- 3g. Burden of Trust ---")

central = next(o for o in board.objectives if o.name == "Central Objective")


def guard_on(objective, name, offset=0.0):
    ox, oy = sm.objective_centre(objective)
    squad = tk.build(ae.RANGERS, owner="Player 1", name=name)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = ox + i * 1.2, oy + offset
    return squad


def burden_vp(pairs, controlled_by="Player 1"):
    for objective in board.objectives:
        objective.controlled_by = None
    guards, units = {}, []
    for objective, squad in pairs:
        objective.controlled_by = controlled_by
        guards[id(objective)] = squad
        units.append(squad)
    tokens = [m for u in units for m in u.models]
    return sm._burden_of_trust(sm.MissionContext(
        "Player 1", tokens=tokens, objectives=board.objectives,
        deployment_zones=board.deployment_zones, card_state={"guards": guards}))


three = board.objectives[:3]
checks.eq("nothing guarded: nothing", burden_vp([]), 0)
checks.eq("one guarded objective: 2 VP",
          burden_vp([(three[0], guard_on(three[0], "1 A"))]),
          sm.BURDEN_OF_TRUST_VP_PER_OBJECTIVE)
checks.eq("two: 4 VP",
          burden_vp([(three[0], guard_on(three[0], "1 A")),
                     (three[1], guard_on(three[1], "1 B"))]),
          2 * sm.BURDEN_OF_TRUST_VP_PER_OBJECTIVE)
# 2 VP each caps at 5, so the third guarded objective is worth 1, not 2.
checks.eq("three: capped at 5 VP, not 6",
          burden_vp([(three[0], guard_on(three[0], "1 A")),
                     (three[1], guard_on(three[1], "1 B")),
                     (three[2], guard_on(three[2], "1 C"))]),
          sm.BURDEN_OF_TRUST_MAX_VP)

# BOTH halves of "guarded" are live, and either one failing drops it.
checks.eq("a guard 20in from its objective does not count",
          burden_vp([(central, guard_on(central, "1 A", offset=20.0))]), 0)
checks.eq("in range but the enemy controls it: does not count",
          burden_vp([(central, guard_on(central, "1 A"))], controlled_by="Player 2"), 0)
checks.eq("in range but NOBODY controls it: does not count",
          burden_vp([(central, guard_on(central, "1 A"))], controlled_by=None), 0)

wiped = guard_on(central, "1 A")
wiped.models[:] = []
checks.eq("a wiped-out guard does not count", burden_vp([(central, wiped)]), 0)

checks.true("Burden of Trust scores at the same instant as Beacon",
            sm.BURDEN_OF_TRUST.timing == sm.BEACON.timing)
checks.true("...i.e. the end of the enemy's final turn",
            sm.BURDEN_OF_TRUST.scores_at(sm.MissionContext(
                "Player 1", ending_player="Player 2", battle_round=BATTLE_ROUNDS)))

# The assignment window, through the real prompt chain.
for objective in board.objectives:
    objective.controlled_by = "Player 1"
on_centre = guard_on(central, "1 Rangers 1")
elsewhere = guard_on(central, "1 Rangers ELSEWHERE")
for _m in elsewhere.models:
    _m.x_in += 40  # nowhere near any objective
bot_ctrl, bot_mission, _, bot_dec, _, _, bot_log, bot_box = make(cards=[sm.BURDEN_OF_TRUST])
bot_box.extend(list(on_centre.models) + list(elsewhere.models))
bot_ctrl.set_objectives_source(lambda: board.objectives)
bot_ctrl.set_zones_source(lambda: board.deployment_zones)
bot_ctrl.draw_at_command_phase("Player 1", 1)

checks.true("drawing it opens the guard gate", bot_dec.is_pending)
checks.true("the gate offers declining",
            any("unguarded" in lbl.lower() for lbl in tk.options_of(bot_dec)))
tk.pick_option(bot_dec, "Assign guards")
# The guard is picked by CLICKING THE UNIT ON THE BOARD, not from a list of
# names (user: "ich muss auf der Map mein Einheit anklicken"). Since every such
# prompt in the game works this way now, the chain hands its requests to the
# ordinary DecisionManager with the options tagged, and game/unit_pick.py is
# what turns one into a click. Each names the objective it is about - that is
# the whole reason the request carries a `subject`.
asked = []
while unit_pick.pending(bot_dec, bot_box) is not None:
    pick = unit_pick.pending(bot_dec, bot_box)
    asked.append(pick.subject)
    checks.true(f"the request names an objective ({pick.subject})",
                any(o.name == pick.subject for o in board.objectives))
    checks.true("it says what to do", "click" in pick.prompt.lower())
    # Only units actually IN RANGE are eligible - a guard has to be in range to
    # count for anything, so offering one that is not would be a choice the
    # card cannot honour.
    for squad in pick.squads:
        checks.true(f"{squad.name} really is in range of {pick.subject}",
                    is_within_range_of_objective(
                        squad, [o for o in board.objectives if o.name == pick.subject]))
    if any(sq is on_centre for sq in pick.squads):
        # A click on an INELIGIBLE unit is ignored, not guessed at.
        checks.eq("clicking a unit that is not eligible does nothing",
                  pick.pick(elsewhere), False)
        checks.true("...and the request is still open", bot_dec.is_pending)
        checks.true("clicking the eligible one takes", pick.pick(on_centre))
    else:
        pick.choose(pick.skip_options[0][1])
checks.true("at least one objective was asked about", bool(asked))
checks.eq("only objectives with a unit in range are asked about",
          all(any(is_within_range_of_objective(sq, [o for o in board.objectives if o.name == name])
                  for sq in [on_centre]) for name in asked), True)
checks.eq("one guard was assigned",
          len(bot_ctrl.card_state["burden_of_trust"]["guards"]), 1)
detail = bot_ctrl.detail_for(sm.BURDEN_OF_TRUST)
checks.true("the detail names the objective and its guard",
            detail and central.name in detail and "1 Rangers 1" in detail)
checks.eq("and it scores",
          sm.BURDEN_OF_TRUST.score(bot_ctrl._context(card=sm.BURDEN_OF_TRUST)),
          sm.BURDEN_OF_TRUST_VP_PER_OBJECTIVE)
checks.eq("the controller is idle once the chain is done", bot_ctrl.is_busy, False)
checks.eq("...and nothing is left pending anywhere", bot_dec.is_pending, False)

# "Until your next turn": the assignment LAPSES and is offered again at the
# start of each of your turns. That is what makes the card a burden - you have
# to commit units every turn, and only the standing at the very end pays.
bot_ctrl.start_of_turn("Player 1")
checks.eq("the start of your next turn clears last turn's guards",
          bot_ctrl.card_state["burden_of_trust"]["guards"], {})
checks.true("and offers them again", bot_dec.is_pending)
checks.true("the offer names the card", "Burden of Trust" in (bot_dec.prompt or ""))
tk.pick_option(bot_dec, "Leave them unguarded")
checks.eq("declining leaves nothing guarded that turn",
          sm.BURDEN_OF_TRUST.score(bot_ctrl._context(card=sm.BURDEN_OF_TRUST)), 0)

# Guards do NOT accumulate across turns - the printed duration is explicit,
# so a fresh assignment REPLACES the old set rather than adding to it.
bot_ctrl.start_of_turn("Player 1")
tk.pick_option(bot_dec, "Assign guards")
while unit_pick.pending(bot_dec, bot_box) is not None:
    pick = unit_pick.pending(bot_dec, bot_box)
    if any(sq is on_centre for sq in pick.squads):
        pick.pick(on_centre)
    else:
        pick.choose(pick.skip_options[0][1])
checks.eq("a new turn's assignment replaces the old set, it does not add to it",
          len(bot_ctrl.card_state["burden_of_trust"]["guards"]), 1)

# Not at the start of the OPPONENT's turn, and not when the card is not held.
bot_ctrl.start_of_turn("Player 2")
checks.eq("the enemy's turn opens no guard window",
          bot_dec.is_pending, False)
empty_ctrl, _, _, empty_dec, _, _, _, _ = make(cards=[sm.CENTRE_GROUND])
empty_ctrl.set_objectives_source(lambda: board.objectives)
empty_ctrl.hand = [sm.CENTRE_GROUND]
empty_ctrl.start_of_turn("Player 1")
checks.eq("no Burden of Trust in hand, no window", empty_dec.is_pending, False)

# "while that unit stays in range and you control it" is checked LIVE at the
# scoring instant - a guard that walks away or loses its objective stops
# counting without any bookkeeping.
checks.eq("a standing guard scores",
          sm.BURDEN_OF_TRUST.score(bot_ctrl._context(card=sm.BURDEN_OF_TRUST)),
          sm.BURDEN_OF_TRUST_VP_PER_OBJECTIVE)
for _m in on_centre.models:
    _m.x_in += 30
checks.eq("...but not once it has wandered off",
          sm.BURDEN_OF_TRUST.score(bot_ctrl._context(card=sm.BURDEN_OF_TRUST)), 0)
for _m in on_centre.models:
    _m.x_in -= 30
central.controlled_by = "Player 2"
checks.eq("...nor once the enemy has taken the objective",
          sm.BURDEN_OF_TRUST.score(bot_ctrl._context(card=sm.BURDEN_OF_TRUST)), 0)
central.controlled_by = "Player 1"

# Settled at the end of the battle, not before.
bot_ctrl.begin_end_of_turn("Player 2", battle_round=BATTLE_ROUNDS - 1)
checks.eq("an earlier round settles nothing", scoring_prompt_open(bot_dec), False)
bot_ctrl.begin_end_of_turn("Player 2", battle_round=BATTLE_ROUNDS)
checks.true("the end of the enemy's final turn does", scoring_prompt_open(bot_dec))
tk.pick_option(bot_dec, "Score")
checks.eq("paying for the one guarded objective",
          bot_mission.secondary_points.get("Player 1", 0),
          sm.BURDEN_OF_TRUST_VP_PER_OBJECTIVE)


# --- 3h. Defend Stronghold: hold your own corner ---
print("--- 3h. Defend Stronghold ---")

my_zone = next(z for z in board.deployment_zones if z.owner == "Player 1")  # map2: y 32..44
MY_HOME = sm.own_home_objective(sm.MissionContext(
    "Player 1", objectives=board.objectives, deployment_zones=board.deployment_zones))
checks.eq("my home objective is found by geometry", MY_HOME.name, "P1 Home Objective")
# The other player's home objective must NOT be mine - the clause is possessive.
checks.eq("and Player 2's is theirs, not mine",
          sm.own_home_objective(sm.MissionContext(
              "Player 2", objectives=board.objectives,
              deployment_zones=board.deployment_zones)).name, "P2 Home Objective")


def stronghold_unit(y, name, owner="Player 1"):
    squad = tk.build(ae.RANGERS, owner=owner, name=name)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = 20 + i * 1.5, y
    return squad


def stronghold_vp(holder, enemy_y=None):
    MY_HOME.controlled_by = holder
    units = [stronghold_unit(38, "1 Rangers 1")]
    if enemy_y is not None:
        units.append(stronghold_unit(enemy_y, "2 Rangers 1", owner="Player 2"))
    tokens = [m for u in units for m in u.models]
    return sm._defend_stronghold(sm.MissionContext(
        "Player 1", tokens=tokens, objectives=board.objectives,
        deployment_zones=board.deployment_zones))


checks.eq("nobody holds my home objective: nothing", stronghold_vp(None), 0)
checks.eq("the enemy holds it: nothing", stronghold_vp("Player 2"), 0)
checks.eq("I hold it and my zone is clear: 5 VP",
          stronghold_vp("Player 1"), sm.DEFEND_STRONGHOLD_CLEAR_VP)
checks.eq("I hold it but an enemy is in my zone: only 3 VP",
          stronghold_vp("Player 1", enemy_y=38), sm.DEFEND_STRONGHOLD_CONTROL_VP)
checks.eq("an enemy outside my zone does not cost the 5 VP",
          stronghold_vp("Player 1", enemy_y=26), sm.DEFEND_STRONGHOLD_CLEAR_VP)

# "no enemy units are WITHIN your deployment zone" - NOT "wholly within". One
# model with a toe inside breaks it, which is the opposite strictness from
# Behind Enemy Lines' "wholly within" and is why the two use different tests.
edge_y = my_zone.rects[0][1] - my_zone.rects[0][3] / 2.0  # the zone's near edge
MY_HOME.controlled_by = "Player 1"
toe = stronghold_unit(0, "2 Rangers TOE", owner="Player 2")
for model in toe.models:
    model.x_in, model.y_in = 20.0, edge_y - model.radius_in / 2.0  # base straddles the edge
mine = stronghold_unit(38, "1 Rangers 1")
straddle_ctx = sm.MissionContext(
    "Player 1", tokens=list(mine.models) + list(toe.models),
    objectives=board.objectives, deployment_zones=board.deployment_zones)
checks.eq("an enemy base merely TOUCHING my zone already costs the 5 VP",
          sm._defend_stronghold(straddle_ctx), sm.DEFEND_STRONGHOLD_CONTROL_VP)

# Timing: same single instant as Beacon, plus its own "2ND ROUND ONWARD" band.
checks.true("it scores at the end of the enemy's final turn",
            sm.DEFEND_STRONGHOLD.scores_at(sm.MissionContext(
                "Player 1", ending_player="Player 2", battle_round=BATTLE_ROUNDS)))
checks.eq("never in the first battle round",
          sm.DEFEND_STRONGHOLD.scores_at(sm.MissionContext(
              "Player 1", ending_player="Player 2", battle_round=1)), False)
checks.eq("its band starts at round 2", sm.DEFEND_STRONGHOLD.min_battle_round,
          sm.DEFEND_STRONGHOLD_FROM_ROUND)

# THE distinction from Behind Enemy Lines: that card prints "you may shuffle
# this card back", this one prints "shuffle this card back". One is an offer,
# the other an instruction.
checks.true("Defend Stronghold's clause is MANDATORY",
            sm.DEFEND_STRONGHOLD.when_drawn_is_mandatory)
checks.eq("Behind Enemy Lines' is not",
          sm.BEHIND_ENEMY_LINES.when_drawn_is_mandatory, False)
checks.true("the clause applies in round 1",
            sm.DEFEND_STRONGHOLD.when_drawn_may_redraw(
                sm.MissionContext("Player 1", battle_round=1)))
checks.eq("and not from round 2",
          sm.DEFEND_STRONGHOLD.when_drawn_may_redraw(
              sm.MissionContext("Player 1", battle_round=2)), False)

# ...and it really resolves WITHOUT a prompt.
ds_ctrl, _, _, ds_dec, _, _, ds_log, _ = make(
    cards=[sm.DEFEND_STRONGHOLD, sm.CENTRE_GROUND, sm.ASSASSINATION, sm.BRING_IT_DOWN])
ds_ctrl.draw_at_command_phase("Player 1", 1)
checks.eq("drawing it in round 1 asks NOTHING", ds_dec.is_pending, False)
checks.eq("it is not in hand", any(c.key == "defend_stronghold" for c in ds_ctrl.hand), False)
checks.true("it went back into the deck",
            any(c.key == "defend_stronghold" for c in ds_ctrl.deck))
checks.eq("not onto the discard pile",
          any(c.key == "defend_stronghold" for c in ds_ctrl.discarded), False)
checks.true("and the log says shuffled", ds_log.has("shuffles Defend Stronghold"))
checks.eq("the hand still ends up with two cards", len(ds_ctrl.hand), 2)

# From round 2 it simply stays.
ds2, _, _, ds2_dec, _, _, _, _ = make(cards=[sm.DEFEND_STRONGHOLD, sm.CENTRE_GROUND])
ds2.draw_at_command_phase("Player 1", 2)
checks.true("from round 2 it stays in hand",
            any(c.key == "defend_stronghold" for c in ds2.hand))
checks.eq("and asks nothing", ds2_dec.is_pending, False)


# --- 3i. Display of Might: outnumber them in No Man's Land ---
print("--- 3i. Display of Might ---")

# map2: my zone is y 32..44, theirs y 0..12, so No Man's Land is y 12..32.
def might_vp(friendly_ys, enemy_ys, ending_player, shocked=()):
    units = []
    for i, y in enumerate(friendly_ys):
        squad = stronghold_unit(y, f"1 Rangers {i}")
        if i in shocked:
            squad.battle_shocked = True
        units.append(squad)
    for i, y in enumerate(enemy_ys):
        units.append(stronghold_unit(y, f"2 Rangers {i}", owner="Player 2"))
    tokens = [m for u in units for m in u.models]
    return sm._display_of_might(sm.MissionContext(
        "Player 1", tokens=tokens, objectives=board.objectives,
        deployment_zones=board.deployment_zones, ending_player=ending_player))


checks.eq("nobody in No Man's Land: nothing", might_vp([], [], "Player 1"), 0)
# The two bands: same condition, different price. This is the first card whose
# VALUE depends on WHICH instant it is scored at.
checks.eq("outnumbering them at the end of YOUR turn: 2 VP",
          might_vp([22], [], "Player 1"), sm.DISPLAY_OF_MIGHT_YOUR_TURN_VP)
checks.eq("the same board at the end of THEIR turn: 5 VP",
          might_vp([22], [], "Player 2"), sm.DISPLAY_OF_MIGHT_OPPONENT_TURN_VP)
checks.true("the enemy-turn band really is the richer one",
            sm.DISPLAY_OF_MIGHT_OPPONENT_TURN_VP > sm.DISPLAY_OF_MIGHT_YOUR_TURN_VP)

# "MORE friendly than enemy" - equal is not more.
checks.eq("1 against 1 is not more", might_vp([22], [20], "Player 2"), 0)
checks.eq("2 against 1 is", might_vp([22, 24], [20], "Player 2"),
          sm.DISPLAY_OF_MIGHT_OPPONENT_TURN_VP)
checks.eq("1 against 2 is not", might_vp([22], [20, 18], "Player 2"), 0)

# The exclusion applies to BOTH sides - a battle-shocked unit of mine stops
# counting for me, which is the stricter reading of a parenthetical printed
# after "enemy units".
checks.eq("a battle-shocked unit of mine does not count",
          might_vp([22], [], "Player 2", shocked={0}), 0)
checks.eq("...but a battle-shocked ENEMY does not count either, so I win again",
          might_vp([22, 24], [20], "Player 2", shocked=set()),
          sm.DISPLAY_OF_MIGHT_OPPONENT_TURN_VP)

# "WHOLLY within No Man's Land": one model back in either deployment zone and
# the unit stops counting. Both zones tested - it is the whole of No Man's Land,
# not just "out of mine".
partly_home = stronghold_unit(22, "1 Rangers P")
partly_home.models[0].y_in = 38.0  # back in MY zone
checks.eq("one model back in my own zone: the unit does not count",
          sm._display_of_might(sm.MissionContext(
              "Player 1", tokens=list(partly_home.models), objectives=board.objectives,
              deployment_zones=board.deployment_zones, ending_player="Player 2")), 0)
partly_enemy = stronghold_unit(22, "1 Rangers Q")
partly_enemy.models[0].y_in = 6.0  # into THEIR zone
checks.eq("one model in the enemy zone: also does not count",
          sm._display_of_might(sm.MissionContext(
              "Player 1", tokens=list(partly_enemy.models), objectives=board.objectives,
              deployment_zones=board.deployment_zones, ending_player="Player 2")), 0)
# A base merely touching a zone edge is not wholly within No Man's Land.
touching = stronghold_unit(22, "1 Rangers T")
for model in touching.models:
    model.y_in = my_zone.rects[0][1] - my_zone.rects[0][3] / 2.0 - model.radius_in / 2.0
checks.eq("a base touching the zone edge is not wholly in No Man's Land",
          sm._display_of_might(sm.MissionContext(
              "Player 1", tokens=list(touching.models), objectives=board.objectives,
              deployment_zones=board.deployment_zones, ending_player="Player 2")), 0)

checks.true("Display of Might scores at the end of a turn - either player's",
            sm.DISPLAY_OF_MIGHT.scores_at(sm.MissionContext(
                "Player 1", ending_player="Player 2")))
checks.true("...including your own",
            sm.DISPLAY_OF_MIGHT.scores_at(sm.MissionContext(
                "Player 1", ending_player="Player 1")))
checks.eq("it has no When Drawn clause",
          sm.DISPLAY_OF_MIGHT.when_drawn_may_redraw(sm.MissionContext("Player 1")), False)

# End to end: the same board pays differently depending on whose turn ended.
for ending, want in (("Player 1", sm.DISPLAY_OF_MIGHT_YOUR_TURN_VP),
                     ("Player 2", sm.DISPLAY_OF_MIGHT_OPPONENT_TURN_VP)):
    dm_ctrl, dm_mission, _, dm_dec, _, _, _, dm_box = make(cards=[sm.DISPLAY_OF_MIGHT])
    holder = stronghold_unit(22, "1 Rangers NML")
    dm_box.extend(holder.models)
    dm_ctrl.set_zones_source(lambda: board.deployment_zones)
    dm_ctrl.set_objectives_source(lambda: board.objectives)
    dm_ctrl.hand = [sm.DISPLAY_OF_MIGHT]
    dm_ctrl.begin_end_of_turn(ending, battle_round=2)
    checks.true(f"a prompt opens at the end of {ending}'s turn", scoring_prompt_open(dm_dec))
    tk.pick_option(dm_dec, "Score")
    checks.eq(f"...paying {want} VP", dm_mission.secondary_points.get("Player 1", 0), want)

# --- 3j. Engage on All Fronts: presence in the table quarters ---
print("--- 3j. Engage on All Fronts ---")

maps.apply_to_config(_map)
BOARD_CX, BOARD_CY = sm.board_centre()
QUARTERS = sm.table_quarters()

checks.eq("the board splits into four quarters", len(QUARTERS), 4)
checks.eq("they cover the whole board",
          sum((qx1 - qx0) * (qy1 - qy0) for qx0, qy0, qx1, qy1 in QUARTERS),
          config.BOARD_WIDTH_IN * config.BOARD_HEIGHT_IN)
# Split at the centre on both axes - so every quarter has one corner at the
# battlefield centre.
checks.true("every quarter touches the battlefield centre",
            all(BOARD_CX in (qx0, qx1) and BOARD_CY in (qy0, qy1)
                for qx0, qy0, qx1, qy1 in QUARTERS))


def corner_unit(x, y, name, owner="Player 1"):
    squad = tk.build(ae.RANGERS, owner=owner, name=name)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = x + i * 1.2, y
    return squad


def engage_ctx(units):
    return sm.MissionContext(
        "Player 1", tokens=[m for u in units for m in u.models],
        objectives=board.objectives, deployment_zones=board.deployment_zones)


# One unit deep in each quarter's outer corner - far from the centre, so the
# 6" exclusion cannot be what decides these.
CORNERS = [(8, 8), (45, 8), (8, 34), (45, 34)]


def engage_vp(corner_count):
    units = [corner_unit(x, y, f"1 Rangers {i}")
             for i, (x, y) in enumerate(CORNERS[:corner_count])]
    return sm._engage_on_all_fronts(engage_ctx(units))


checks.eq("no units: nothing", engage_vp(0), 0)
checks.eq("one quarter: nothing", engage_vp(1), 0)
checks.eq("two quarters: still nothing", engage_vp(2), 0)
checks.eq("THREE quarters: 3 VP", engage_vp(3), sm.ENGAGE_THREE_QUARTERS_VP)
checks.eq("four quarters: 5 VP", engage_vp(4), sm.ENGAGE_FOUR_QUARTERS_VP)

# The 6" centre exclusion is the clause that makes the card hard: a unit can be
# wholly inside a quarter and still not count. Measured on both sides of the
# line, in the SAME quarter, so only the distance differs.
nw = QUARTERS[0]
near_centre = corner_unit(BOARD_CX - 3.0, BOARD_CY - 3.0, "1 Rangers NEAR")
far_centre = corner_unit(BOARD_CX - 12.0, BOARD_CY - 12.0, "1 Rangers FAR")
checks.true("a unit far from the centre gives presence",
            sm.unit_has_presence_in(far_centre, nw, engage_ctx([far_centre])))
checks.eq("a unit inside 6\" of the centre does NOT, same quarter",
          sm.unit_has_presence_in(near_centre, nw, engage_ctx([near_centre])), False)
# ...and that really is what the exclusion constant says.
nearest = min(sm.model_distance_to_point(m, BOARD_CX, BOARD_CY) for m in near_centre.models)
checks.true("the near unit really is inside the exclusion",
            nearest <= sm.ENGAGE_CENTRE_EXCLUSION_IN)
furthest_near = min(sm.model_distance_to_point(m, BOARD_CX, BOARD_CY) for m in far_centre.models)
checks.true("and the far one really is outside it",
            furthest_near > sm.ENGAGE_CENTRE_EXCLUSION_IN)

# "WHOLLY within it" - a unit straddling a centre line is in NEITHER quarter,
# not in one of them.
straddling = corner_unit(BOARD_CX - 0.5, 8, "1 Rangers STRADDLE")
checks.eq("a unit across a centre line counts for no quarter",
          len(sm.quarters_with_presence(engage_ctx([straddling]))), 0)

shocked = corner_unit(8, 8, "1 Rangers SHOCKED")
shocked.battle_shocked = True
checks.eq("a battle-shocked unit gives no presence",
          len(sm.quarters_with_presence(engage_ctx([shocked]))), 0)

# Enemy units are irrelevant to this card - it asks only about yours.
enemy_everywhere = [corner_unit(x, y, f"2 Rangers {i}", owner="Player 2")
                    for i, (x, y) in enumerate(CORNERS)]
mine_three = [corner_unit(x, y, f"1 Rangers {i}") for i, (x, y) in enumerate(CORNERS[:3])]
checks.eq("enemy presence neither helps nor hurts",
          sm._engage_on_all_fronts(engage_ctx(mine_three + enemy_everywhere)),
          sm.ENGAGE_THREE_QUARTERS_VP)

checks.true("Engage on All Fronts scores at the end of YOUR turn",
            sm.ENGAGE_ON_ALL_FRONTS.scores_at(
                sm.MissionContext("Player 1", ending_player="Player 1")))
checks.eq("it has no When Drawn clause",
          sm.ENGAGE_ON_ALL_FRONTS.when_drawn_may_redraw(sm.MissionContext("Player 1")), False)

# The quarters follow the BOARD, so a differently-shaped map gets different
# ones - checked because table_quarters() reads config at call time.
maps.apply_to_config(maps.MAPS["map1"])
portrait = sm.table_quarters()
checks.true("a portrait board yields differently-shaped quarters",
            portrait != QUARTERS)
maps.apply_to_config(_map)


# --- 3k. Forward Position: take their ground ---
print("--- 3k. Forward Position ---")

fp_ctx = sm.MissionContext("Player 1", objectives=board.objectives,
                           deployment_zones=board.deployment_zones)
ENEMY_HOME = sm.enemy_home_objective(fp_ctx)
EXPANSIONS = sm.expansion_objectives(fp_ctx)

checks.eq("the enemy home objective is theirs, not mine",
          ENEMY_HOME.name, "P2 Home Objective")
checks.true("...and it is the mirror of my own",
            ENEMY_HOME is not sm.own_home_objective(fp_ctx))
# User's definition: "das Objektiv, was an meiner Aufstellungszone am naechsten
# ist, ausser natuerlich das Home-Objektiv." One per player, so Forward
# Position's "EACH expansion objective" is the pair.
checks.eq("the expansion objectives on map2",
          sorted(o.name for o in EXPANSIONS), ["Objective East", "Objective West"])
checks.eq("nor is either home objective one",
          any("Home" in o.name for o in EXPANSIONS), False)
# Each player's is the one nearest THEIR zone, and on a symmetric board that
# makes them different objectives - measured rather than assumed, since a
# definition that handed both players the same objective would quietly turn
# "each" into "one".
mine_exp = sm.expansion_objective_for(fp_ctx, "Player 1")
theirs_exp = sm.expansion_objective_for(fp_ctx, "Player 2")
checks.eq("my expansion objective on map2", mine_exp.name, "Objective East")
checks.eq("theirs is the other flank", theirs_exp.name, "Objective West")
checks.true("so they are different objectives", mine_exp is not theirs_exp)


def _zone_gap(objective, player):
    zones = [z for z in board.deployment_zones if z.owner == player]
    ox, oy = sm.objective_centre(objective)
    return min(sm.zone_distance(z, ox, oy) for z in zones)


# It really is the NEAREST, not merely a flanking one: every other candidate
# has to be further from my zone.
for other in sm.no_mans_land_objectives(fp_ctx):
    if other is mine_exp:
        continue
    checks.true(f"{other.name} is further from my zone than my expansion objective",
                _zone_gap(other, "Player 1") > _zone_gap(mine_exp, "Player 1"))
checks.eq("the central objective is not the nearest on map2",
          any("Central" in o.name for o in EXPANSIONS), False)


def forward_vp(held):
    for objective in board.objectives:
        objective.controlled_by = None
    for objective in held:
        objective.controlled_by = "Player 1"
    return sm._forward_position(fp_ctx)


checks.eq("nothing held: nothing", forward_vp([]), 0)
# "and/or" makes these alternatives - either alone pays the single 5 VP.
checks.eq("their home objective alone: 5 VP", forward_vp([ENEMY_HOME]), sm.FORWARD_POSITION_VP)
checks.eq("ALL the expansion objectives: 5 VP", forward_vp(EXPANSIONS), sm.FORWARD_POSITION_VP)
checks.eq("both at once is still 5 VP - one box, not two",
          forward_vp([ENEMY_HOME] + EXPANSIONS), sm.FORWARD_POSITION_VP)
# "EACH expansion objective" is all of them, which is what stops the card being
# trivial on a board with two.
checks.eq("only ONE expansion objective: nothing", forward_vp(EXPANSIONS[:1]), 0)
checks.eq("my own home objective does not count",
          forward_vp([sm.own_home_objective(fp_ctx)]), 0)
checks.eq("nor does the central objective",
          forward_vp([o for o in board.objectives if "Central" in o.name]), 0)
# An objective the ENEMY holds is not one I control.
for objective in board.objectives:
    objective.controlled_by = None
ENEMY_HOME.controlled_by = "Player 2"
checks.eq("their home objective held by THEM pays nothing", sm._forward_position(fp_ctx), 0)

checks.true("Forward Position scores at the end of YOUR turn",
            sm.FORWARD_POSITION.scores_at(
                sm.MissionContext("Player 1", ending_player="Player 1")))
# Its When Drawn clause is Behind Enemy Lines': round 1, optional, shuffles back.
checks.true("its clause applies in round 1",
            sm.FORWARD_POSITION.when_drawn_may_redraw(
                sm.MissionContext("Player 1", battle_round=1)))
checks.eq("and not later",
          sm.FORWARD_POSITION.when_drawn_may_redraw(
              sm.MissionContext("Player 1", battle_round=2)), False)
checks.true("it shuffles back rather than discarding",
            sm.FORWARD_POSITION.when_drawn_shuffles_back)
checks.eq("and it is OPTIONAL - the card says 'you may'",
          sm.FORWARD_POSITION.when_drawn_is_mandatory, False)

# map3 deploys in opposite CORNERS, and that is where ranking by the
# conservative zone distance goes wrong: it measures to the nearest constraint
# LINE, which ties an objective 4.5" away with one 10.6" away and then breaks
# the tie on the name. Each player must get the one on their own side.
maps.apply_to_config(maps.MAPS["map3"])
corner = GameState()
maps.MAPS["map3"].build(corner)
corner_ctx = sm.MissionContext("Player 1", objectives=corner.objectives,
                               deployment_zones=corner.deployment_zones)
checks.eq("map3: Player 1's expansion objective is the one on their side",
          sm.expansion_objective_for(corner_ctx, "Player 1").name, "Objective West")
checks.eq("map3: Player 2's is the mirror of it",
          sm.expansion_objective_for(corner_ctx, "Player 2").name, "Objective East")
checks.eq("map3's expansion set therefore has two members",
          len(sm.expansion_objectives(corner_ctx)), 2)

# The set has to DEDUPLICATE when both players' nearest is the same objective,
# or "each expansion objective" would demand the same one twice. That case used
# to be supplied by the old 30"x30" board, whose only non-home objective was
# the central one; that board is gone, so it is built here rather than borrowed
# from whichever map happens to have it.
_one = [o for o in corner.objectives if o.name in ("P1 Home Objective", "P2 Home Objective")]
_one.append([o for o in corner.objectives if o.name == "Objective East"][0])
_one_ctx = sm.MissionContext("Player 1", objectives=_one,
                             deployment_zones=corner.deployment_zones)
checks.eq("with one non-home objective, both players' nearest is the same",
          sm.expansion_objective_for(_one_ctx, "Player 1").name,
          sm.expansion_objective_for(_one_ctx, "Player 2").name)
checks.eq("...and the set collapses to a single member",
          len(sm.expansion_objectives(_one_ctx)), 1)
checks.true("both players' nearest really is the same objective",
            sm.expansion_objective_for(_one_ctx, "Player 1")
            is sm.expansion_objective_for(_one_ctx, "Player 2"))
one_enemy_home = sm.enemy_home_objective(_one_ctx)
checks.true("it also has an enemy home objective", one_enemy_home is not None)
for o in _one:
    o.controlled_by = None
one_enemy_home.controlled_by = "Player 1"
checks.eq("the card scores off their home objective there",
          sm._forward_position(_one_ctx), sm.FORWARD_POSITION_VP)
one_enemy_home.controlled_by = None
sm.expansion_objectives(_one_ctx)[0].controlled_by = "Player 1"
checks.eq("...and off the lone expansion objective too",
          sm._forward_position(_one_ctx), sm.FORWARD_POSITION_VP)
for o in corner.objectives:
    o.controlled_by = None
maps.apply_to_config(_map)

# End to end through the prompt chain.
for objective in board.objectives:
    objective.controlled_by = None
ENEMY_HOME.controlled_by = "Player 1"
fp_ctrl, fp_mission, _, fp_dec, _, _, _, _ = make(cards=[sm.FORWARD_POSITION])
fp_ctrl.set_objectives_source(lambda: board.objectives)
fp_ctrl.set_zones_source(lambda: board.deployment_zones)
fp_ctrl.hand = [sm.FORWARD_POSITION]
fp_ctrl.begin_end_of_turn("Player 1", battle_round=3)
checks.true("holding their home objective opens the prompt", scoring_prompt_open(fp_dec))
tk.pick_option(fp_dec, "Score 5")
checks.eq("paying 5 VP", fp_mission.secondary_points.get("Player 1", 0), sm.FORWARD_POSITION_VP)

# --- 3l. No Prisoners and Outflank ---
print("--- 3l. No Prisoners / Outflank ---")


def edge_unit(name, positions, owner="Player 1"):
    """A unit with one model per given (x, y) - so a scene can put ONE model
    somewhere and the rest elsewhere, which is the whole point of section 3m."""
    squad = tk.build(ae.RANGERS, owner=owner, name=name)
    squad.models[:] = squad.models[:len(positions)]
    for model, (x, y) in zip(squad.models, positions):
        model.x_in, model.y_in = x, y
    return squad


def spatial_ctx(units, **kw):
    return sm.MissionContext(
        "Player 1", tokens=[m for u in units for m in u.models],
        objectives=board.objectives, deployment_zones=board.deployment_zones, **kw)


# No Prisoners: 2 VP per enemy UNIT destroyed this turn, capped at 5. Fed from
# the same per-unit hook A Grievous Blow uses - that card is this one with a
# Starting Strength filter on top.
dead = [edge_unit(f"2 Rangers {i}", [(10, 10)], owner="Player 2") for i in range(3)]
for count, want in ((0, 0), (1, 2), (2, 4), (3, 5)):
    checks.eq(f"{count} enemy unit(s) destroyed",
              sm._no_prisoners(spatial_ctx([], destroyed_squads_this_turn=dead[:count])), want)
checks.eq("three pays 5, not 6 - the cap bites",
          sm._no_prisoners(spatial_ctx([], destroyed_squads_this_turn=dead)),
          sm.NO_PRISONERS_MAX_VP)
checks.eq("losing your OWN unit pays nothing",
          sm._no_prisoners(spatial_ctx([], destroyed_squads_this_turn=[
              edge_unit("1 Rangers 9", [(10, 10)])])), 0)
checks.true("No Prisoners scores at the end of a turn - either player's",
            sm.NO_PRISONERS.scores_at(sm.MissionContext("Player 1", ending_player="Player 2")))

# Outflank. map2: board 60x44, my half is y >= 22, so y < 22 is outside my
# territory. Edges are N y=0, S y=44, W x=0, E x=60.
checks.eq("opposite edges are the parallel pairs", sm.OPPOSITE_EDGE_PAIRS,
          (("north", "south"), ("west", "east")))

near_edge_away = edge_unit("1 A", [(30, 3), (30, 15), (32, 15)])   # at N edge, all outside my half
checks.eq("one unit at an edge and outside your territory: 3 VP",
          sm._outflank(spatial_ctx([near_edge_away])), sm.OUTFLANK_ONE_EDGE_VP)

in_my_half = edge_unit("1 A", [(30, 41), (32, 41)])               # at S edge, inside my half
checks.eq("an edge unit inside your own territory pays nothing",
          sm._outflank(spatial_ctx([in_my_half])), 0)

middle = edge_unit("1 A", [(30, 15)])                              # outside my half, no edge
checks.eq("a unit away from every edge pays nothing",
          sm._outflank(spatial_ctx([middle])), 0)

# The 5 VP tier needs OPPOSITE edges - two units on the same edge is not it.
same_edge = [edge_unit("1 A", [(20, 3)]), edge_unit("1 B", [(40, 3)])]
checks.eq("two units on the SAME edge is not the 5 VP tier",
          sm._outflank(spatial_ctx(same_edge)), sm.OUTFLANK_ONE_EDGE_VP)
adjacent = [edge_unit("1 A", [(30, 3)]), edge_unit("1 B", [(3, 15)])]  # north + west
checks.eq("two units on ADJACENT edges is not either",
          sm._outflank(spatial_ctx(adjacent)), sm.OUTFLANK_ONE_EDGE_VP)
opposite = [edge_unit("1 A", [(30, 3)]), edge_unit("1 B", [(30, 41)])]  # north + south
checks.eq("north and south: 5 VP", sm._outflank(spatial_ctx(opposite)),
          sm.OUTFLANK_OPPOSITE_EDGES_VP)
west_east = [edge_unit("1 A", [(3, 15)]), edge_unit("1 B", [(57, 15)])]
checks.eq("west and east: 5 VP too", sm._outflank(spatial_ctx(west_east)),
          sm.OUTFLANK_OPPOSITE_EDGES_VP)

# THE difference between the tiers, and it is easy to flatten: the 3 VP tier
# needs THE unit out of your territory; the 5 VP tier needs only ONE OF THE
# PAIR out of it. So a unit pinned in your own half can still be half of the
# richer tier.
one_out = [edge_unit("1 A", [(30, 3)]),        # north, outside my half
           edge_unit("1 B", [(30, 41)])]       # south, INSIDE my half
checks.eq("only one of the pair needs to be outside your territory",
          sm._outflank(spatial_ctx(one_out)), sm.OUTFLANK_OPPOSITE_EDGES_VP)
both_in = [edge_unit("1 A", [(3, 30)]), edge_unit("1 B", [(57, 30)])]  # both inside my half
checks.eq("...but BOTH inside it pays nothing at all",
          sm._outflank(spatial_ctx(both_in)), 0)

shocked_edge = edge_unit("1 A", [(30, 3)])
shocked_edge.battle_shocked = True
checks.eq("a battle-shocked unit at the edge does not count",
          sm._outflank(spatial_ctx([shocked_edge])), 0)
checks.true("Outflank scores at the end of YOUR turn",
            sm.OUTFLANK.scores_at(sm.MissionContext("Player 1", ending_player="Player 1")))


# --- 3m. WITHIN vs WHOLLY WITHIN, across every card that uses either ---
print("--- 3m. within vs wholly within ---")

# User: "Wo du wirklich vorsichtig sein musst, ist in der Unterscheidung
# zwischen Within und Wholly Within. Within: da reicht, wenn ich nur den
# kleinen Zeh mit einem Modell reinhalte. Wholly within dagegen muss die
# Einheit wirklich vollstaendig drin sein."
#
# Every clause below is exercised at the SAME boundary case - a unit with one
# model on one side of a line and the rest on the other - so the two readings
# give visibly different answers. A card that quietly used the wrong one would
# pass every "unit clearly inside / clearly outside" test ever written.
CENTRE_X, CENTRE_Y = sm.board_centre()
MY_ZONE = next(z for z in board.deployment_zones if z.owner == "Player 1")
ENEMY_ZONE = next(z for z in board.deployment_zones if z.owner == "Player 2")

# --- WITHIN: one model inside is ENOUGH ---
toe_on_centre = edge_unit("1 A", [(CENTRE_X, CENTRE_Y), (50, 40), (52, 40)])
checks.eq("Centre Ground: ONE model on the centre holds it",
          sm._centre_ground(spatial_ctx([toe_on_centre])), sm.CENTRE_GROUND_FAR_VP)

my_home = sm.own_home_objective(spatial_ctx([]))
my_home.controlled_by = "Player 1"
holder = edge_unit("1 M", [(30, 38)])
zone_edge_y = MY_ZONE.rects[0][1] - MY_ZONE.rects[0][3] / 2.0
one_toe_in = edge_unit("2 T", [(20, zone_edge_y + 0.1), (20, 5), (22, 5)], owner="Player 2")
checks.eq("Defend Stronghold: ONE enemy model in your zone costs the 5 VP",
          sm._defend_stronghold(spatial_ctx([holder, one_toe_in])),
          sm.DEFEND_STRONGHOLD_CONTROL_VP)
all_out = edge_unit("2 T", [(20, 5), (22, 5), (24, 5)], owner="Player 2")
checks.eq("...and with none of them inside it pays 5",
          sm._defend_stronghold(spatial_ctx([holder, all_out])),
          sm.DEFEND_STRONGHOLD_CLEAR_VP)

edge_toe = edge_unit("1 A", [(30, 3), (30, 15), (32, 15)])
checks.eq("Outflank: ONE model within 6\" of an edge puts the unit there",
          sm._outflank(spatial_ctx([edge_toe])), sm.OUTFLANK_ONE_EDGE_VP)

# --- WHOLLY WITHIN: one model outside spoils it ---
almost = edge_unit("1 A", [(20, 6), (22, 6), (24, 38)])
checks.eq("Behind Enemy Lines: ONE model left behind loses the unit's 3 VP",
          sm._behind_enemy_lines(spatial_ctx([almost])), 0)
fully = edge_unit("1 A", [(20, 6), (22, 6), (24, 6)])
checks.eq("...with every model inside, it pays",
          sm._behind_enemy_lines(spatial_ctx([fully])), sm.BEHIND_ENEMY_LINES_VP_PER_UNIT)

nml_almost = edge_unit("1 A", [(20, 20), (22, 20), (24, 38)])
checks.eq("Display of Might: ONE model back in your zone and the unit stops counting",
          sm._display_of_might(spatial_ctx([nml_almost], ending_player="Player 2")), 0)
nml_fully = edge_unit("1 A", [(20, 20), (22, 20), (24, 20)])
checks.eq("...wholly in No Man's Land, it counts",
          sm._display_of_might(spatial_ctx([nml_fully], ending_player="Player 2")),
          sm.DISPLAY_OF_MIGHT_OPPONENT_TURN_VP)

quarter = sm.table_quarters()[0]
across_line = edge_unit("1 A", [(8, 8), (10, 8), (CENTRE_X + 2, 8)])
checks.eq("Engage on All Fronts: ONE model over the centre line kills the presence",
          sm.unit_has_presence_in(across_line, quarter, spatial_ctx([across_line])), False)
inside_quarter = edge_unit("1 A", [(8, 8), (10, 8), (12, 8)])
checks.true("...wholly inside the quarter, there is a presence",
            sm.unit_has_presence_in(inside_quarter, quarter, spatial_ctx([inside_quarter])))

# --- NOT WITHIN / OUTSIDE: one model inside spoils it, the mirror of WITHIN ---
near_centre_toe = edge_unit("1 A", [(8, 8), (10, 8), (CENTRE_X - 4, CENTRE_Y - 4)])
checks.eq("Engage: ONE model inside 6\" of the centre kills the presence",
          sm.unit_has_presence_in(near_centre_toe, quarter, spatial_ctx([near_centre_toe])),
          False)

beacon_toe = edge_unit("1 B", [(20, 18), (22, 18), (24, 26)])
checks.eq("Beacon: ONE model back in your half drops 5 VP to 3",
          sm._beacon(spatial_ctx([beacon_toe], card_state={"objective": beacon_toe})),
          sm.BEACON_OUTSIDE_DEPLOYMENT_VP)
beacon_clear = edge_unit("1 B", [(20, 18), (22, 18), (24, 18)])
checks.eq("...wholly across, it is 5",
          sm._beacon(spatial_ctx([beacon_clear], card_state={"objective": beacon_clear})),
          sm.BEACON_OUTSIDE_TERRITORY_VP)

outflank_toe = edge_unit("1 A", [(30, 3), (30, 15), (32, 30)])
checks.eq("Outflank: ONE model back in your territory and the 3 VP is gone",
          sm._outflank(spatial_ctx([outflank_toe])), 0)

# ...and the asymmetry inside Outflank itself: the 5 VP tier only needs ONE of
# the pair out of your territory, so a unit that fails the 3 VP test on its own
# can still be half of the 5 VP one.
pinned = edge_unit("1 B", [(30, 41), (32, 30)])   # at the S edge, a model in my half
free = edge_unit("1 A", [(30, 3)])                 # at the N edge, outside my half
checks.eq("the pinned unit alone pays nothing", sm._outflank(spatial_ctx([pinned])), 0)
checks.eq("but paired across opposite edges it is still 5 VP",
          sm._outflank(spatial_ctx([pinned, free])), sm.OUTFLANK_OPPOSITE_EDGES_VP)

# --- 3n. Overwhelming Force, Secure No Man's Land, Plunder ---
print("--- 3n. the last three ---")

CENTRAL_OBJ = next(o for o in board.objectives if o.name == "Central Objective")


def obj_unit(objective, name, owner="Player 2"):
    ox, oy = sm.objective_centre(objective)
    squad = tk.build(ae.RANGERS, owner=owner, name=name)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = ox + i * 1.2, oy
    return squad


# OVERWHELMING FORCE: the qualifier is about where the unit was at the START of
# the turn, which is a fact that cannot be read off the board when the card
# scores - the unit is dead by then. It needs the controller's snapshot.
on_objective = [obj_unit(CENTRAL_OBJ, f"2 Rangers {i}") for i in range(3)]
elsewhere = tk.build(ae.RANGERS, owner="Player 2", name="2 Rangers FAR")
for i, model in enumerate(elsewhere.models):
    model.x_in, model.y_in = 3 + i * 1.2, 3
marked = {id(sq) for sq in on_objective}


def force_vp(destroyed, snapshot=None):
    return sm._overwhelming_force(sm.MissionContext(
        "Player 1", objectives=board.objectives, deployment_zones=board.deployment_zones,
        destroyed_squads_this_turn=destroyed,
        on_objective_at_turn_start=(marked if snapshot is None else snapshot)))


for count, want in ((0, 0), (1, 3), (2, 5), (3, 5)):
    checks.eq(f"{count} marked enemy unit(s) destroyed", force_vp(on_objective[:count]), want)
checks.eq("two pay 5, not 6 - the cap bites", force_vp(on_objective[:2]),
          sm.OVERWHELMING_FORCE_MAX_VP)
# THE clause: a unit destroyed while nowhere near an objective pays nothing,
# even though it is an enemy unit destroyed this turn.
checks.eq("a unit that did not start the turn on an objective pays nothing",
          force_vp([elsewhere]), 0)
checks.eq("...and an empty snapshot pays nothing at all",
          force_vp(on_objective, snapshot=set()), 0)
own = tk.build(ae.RANGERS, owner="Player 1", name="1 Rangers 9")
checks.eq("losing your OWN unit pays nothing",
          force_vp([own], snapshot={id(own)}), 0)
checks.true("Overwhelming Force scores at the end of a turn - either player's",
            sm.OVERWHELMING_FORCE.scores_at(
                sm.MissionContext("Player 1", ending_player="Player 2")))

# The snapshot itself: taken from the live board, enemies only.
of_ctrl, _, _, _, _, _, _, of_box = make(cards=[sm.OVERWHELMING_FORCE])
mine_on_obj = obj_unit(CENTRAL_OBJ, "1 Rangers ON", owner="Player 1")
of_box.extend(list(on_objective[0].models) + list(elsewhere.models) + list(mine_on_obj.models))
of_ctrl.set_objectives_source(lambda: board.objectives)
of_ctrl.set_zones_source(lambda: board.deployment_zones)
of_ctrl.snapshot_turn_start()
snapshot = of_ctrl._on_objective_at_turn_start
checks.true("the snapshot catches an enemy unit on an objective",
            id(on_objective[0]) in snapshot)
checks.eq("...and not one far from every objective", id(elsewhere) in snapshot, False)
checks.eq("...and not your OWN units", id(mine_on_obj) in snapshot, False)
# Retaken each turn, so last turn's positions cannot linger.
for model in on_objective[0].models:
    model.x_in += 40
of_ctrl.snapshot_turn_start()
checks.eq("a unit that has moved off is not in the next turn's snapshot",
          id(on_objective[0]) in of_ctrl._on_objective_at_turn_start, False)
for model in on_objective[0].models:
    model.x_in -= 40


# SECURE NO MAN'S LAND: two or more No Man's Land objectives.
NML = sm.no_mans_land_objectives(sm.MissionContext(
    "Player 1", objectives=board.objectives, deployment_zones=board.deployment_zones))
checks.true("map2 has at least two No Man's Land objectives", len(NML) >= 2)


def secure_vp(held):
    for objective in board.objectives:
        objective.controlled_by = None
    for objective in held:
        objective.controlled_by = "Player 1"
    return sm._secure_no_mans_land(sm.MissionContext(
        "Player 1", objectives=board.objectives, deployment_zones=board.deployment_zones))


checks.eq("none held: nothing", secure_vp([]), 0)
checks.eq("one held: still nothing", secure_vp(NML[:1]), 0)
checks.eq("two held: 5 VP", secure_vp(NML[:2]), sm.SECURE_NO_MANS_LAND_VP)
checks.eq("three held: still 5 VP - one box", secure_vp(NML), sm.SECURE_NO_MANS_LAND_VP)
# "(excl. your home objective)" is belt and braces - a home objective is never
# in No Man's Land anyway - but holding BOTH home objectives must not pay.
homes = [o for o in board.objectives if o not in NML]
checks.eq("both home objectives held pays nothing", secure_vp(homes), 0)
# An objective the enemy holds is not one I control.
for objective in board.objectives:
    objective.controlled_by = "Player 2"
checks.eq("the enemy holding them pays nothing",
          sm._secure_no_mans_land(sm.MissionContext(
              "Player 1", objectives=board.objectives,
              deployment_zones=board.deployment_zones)), 0)
for objective in board.objectives:
    objective.controlled_by = None


# PLUNDER: an OBJECTIVE ACTION that completes IMMEDIATELY.
plunder_ctx = sm.MissionContext(
    "Player 1", objectives=board.objectives, deployment_zones=board.deployment_zones,
    terrain_areas=board.terrain_areas)
PLUNDERABLE = sm.plunderable_areas(plunder_ctx)
checks.true("some terrain areas lie outside my territory", bool(PLUNDERABLE))
checks.true("...but not all of them", len(PLUNDERABLE) < len(board.terrain_areas))
# "a terrain area NOT WITHIN YOUR TERRITORY" - the qualifier attaches to the
# AREA, not to the unit: you plunder ground that is not yours.
for area in PLUNDERABLE:
    min_x, min_y, max_x, max_y = area.bounding_box
    checks.eq("a plunderable area's centre is outside my half",
              sm.in_own_territory(plunder_ctx, (min_x + max_x) / 2, (min_y + max_y) / 2), False)


def unit_in_area(area, name):
    min_x, min_y, max_x, max_y = area.bounding_box
    squad = tk.build(ae.RANGERS, owner="Player 1", name=name)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = (min_x + max_x) / 2 + i * 0.9, (min_y + max_y) / 2
    return squad


in_theirs = unit_in_area(PLUNDERABLE[0], "1 Rangers A")
plunder_scene = sm.MissionContext(
    "Player 1", tokens=list(in_theirs.models), objectives=board.objectives,
    deployment_zones=board.deployment_zones, terrain_areas=board.terrain_areas)
checks.true("a unit in such an area satisfies the UNITS line",
            sm.plunder_units(in_theirs, plunder_scene))
mine_side = [a for a in board.terrain_areas if a not in PLUNDERABLE]
if mine_side:
    in_mine = unit_in_area(mine_side[0], "1 Rangers B")
    checks.eq("a unit in a terrain area in MY territory does not",
              sm.plunder_units(in_mine, sm.MissionContext(
                  "Player 1", tokens=list(in_mine.models), objectives=board.objectives,
                  deployment_zones=board.deployment_zones,
                  terrain_areas=board.terrain_areas)), False)
open_ground = tk.build(ae.RANGERS, owner="Player 1", name="1 Rangers C")
for i, model in enumerate(open_ground.models):
    model.x_in, model.y_in = 30 + i * 1.2, 15
checks.eq("a unit standing in no terrain area at all does not either",
          sm.plunder_units(open_ground, sm.MissionContext(
              "Player 1", tokens=list(open_ground.models), objectives=board.objectives,
              deployment_zones=board.deployment_zones,
              terrain_areas=board.terrain_areas)), False)

checks.true("Plunder completes immediately", sm.PLUNDER_ACTION.completes_immediately)
checks.eq("Cleanse does not", sm.CLEANSE_ACTION.completes_immediately, False)

# End to end, and the point of "COMPLETES: Immediately": a later move cannot
# take it back, where a Cleanse in the same position would be cancelled.
pl_ctrl, pl_mission, _, pl_dec, _, _, _, pl_box = make(cards=[sm.PLUNDER])
pl_box.extend(in_theirs.models)
pl_ctrl.set_objectives_source(lambda: board.objectives)
pl_ctrl.set_zones_source(lambda: board.deployment_zones)
pl_ctrl.set_terrain_source(lambda: board.terrain_areas)
pl_actions = ActionController(tokens_source=lambda: list(in_theirs.models), game_log=tk.Log())
pl_ctrl.set_action_controller(pl_actions)
pl_ctrl.hand = [sm.PLUNDER]
_pl_turn = TurnTracker(game_log=tk.Log())
_pl_turn.phase_index = PHASES.index(PHASE_SHOOTING)
_pl_turn.turn_owner = "Player 1"
pl_ctrl.turn_tracker = _pl_turn
# Offered as PANEL BUTTONS for the selected unit, not as a prompt - so the
# label names the action and the target, and no decision is opened.
pl_offers = pl_ctrl.available_actions_for(in_theirs)
checks.true("the unit is offered the action", bool(pl_offers))
checks.true("every offer names Plunder, not Cleanse",
            all("Plunder" in label and "leanse" not in label
                for label, _a, _t in pl_offers))
checks.eq("nothing is asked", pl_dec.is_pending, False)
_label, _action, _target = pl_offers[0]
pl_ctrl.start_action(_action, in_theirs, _target)
state = pl_actions.states[0]
checks.true("it is finished the moment it starts", state.completed)
checks.true("its locks apply all the same", pl_actions.blocks_shooting(in_theirs))
checks.true("...including the charge", pl_actions.blocks_charge(in_theirs))
# 16.01's move-cancellation cannot reach a completed action.
pl_actions.notify_move(in_theirs, None)
checks.true("a later move marks it broken", state.broken)
checks.true("...but it stays completed", state.completed)
checks.eq("...and still counts at the end of the turn",
          len(pl_actions.resolve_end_of_turn("Player 1", pl_ctrl._context())), 1)
pl_ctrl.begin_end_of_turn("Player 1", battle_round=2)
checks.true("which opens the scoring prompt", scoring_prompt_open(pl_dec))
tk.pick_option(pl_dec, "Score 5")
checks.eq("paying 5 VP", pl_mission.secondary_points.get("Player 1", 0), sm.PLUNDER_VP)

# USE LIMIT: once per TURN, not once per unit - unlike Cleanse's
# unlimited-but-one-per-objective.
checks.eq("a second Plunder action in the same turn is refused",
          sm.plunder_use_limit(pl_actions.states, in_theirs, PLUNDERABLE[0],
                               pl_ctrl._context()), False)
checks.true("...whereas Cleanse only forbids the SAME objective twice",
            sm.cleanse_use_limit([], in_theirs, CENTRAL_OBJ, plunder_scene))

# The two Objective Action cards each offer to step aside for the other.
def hand_ctx(cards):
    return sm.MissionContext("Player 1", hand=cards)


checks.true("Cleanse's clause is live now that Plunder exists",
            sm.CLEANSE.when_drawn_may_redraw(hand_ctx([sm.PLUNDER])))
checks.eq("...and inert without it",
          sm.CLEANSE.when_drawn_may_redraw(hand_ctx([sm.CENTRE_GROUND])), False)
checks.true("Plunder prints the mirror clause",
            sm.PLUNDER.when_drawn_may_redraw(hand_ctx([sm.CLEANSE])))
checks.eq("...also inert without it",
          sm.PLUNDER.when_drawn_may_redraw(hand_ctx([sm.CENTRE_GROUND])), False)
checks.true("both shuffle back rather than discarding",
            sm.PLUNDER.when_drawn_shuffles_back and sm.CLEANSE.when_drawn_shuffles_back)

# --- 4. the When Drawn redraw offer ---
print("--- 4. When Drawn redraw ---")

# Three cards so that drawing two still leaves something to redraw INTO - with
# the shipped two-card deck the offer can never fire, which is itself pinned
# below.
filler = sm.SecondaryMissionCard("filler", "Filler", "nothing.",
                                 sm.TIMING_END_OF_YOUR_TURN, lambda ctx: 0)
ctrl, mission, cp, decision, turn, overlay, log, box = make(
    cards=[sm.BRING_IT_DOWN, filler, sm.CENTRE_GROUND])
ctrl.draw_at_command_phase("Player 1", 1)
checks.true("with no big enemy on the table the redraw is offered", decision.is_pending)
checks.eq("nothing is announced until the offer is answered", len(overlay.announced), 0)
labels = tk.options_of(decision)
checks.true("the offer names discarding and redrawing",
            any("redraw" in lbl.lower() for lbl in labels))
tk.pick_option(decision, "Discard and redraw")
checks.eq("Bring It Down left the hand",
          any(c.key == "bring_it_down" for c in ctrl.hand), False)
checks.eq("a replacement was drawn in its place", len(ctrl.hand), 2)
checks.eq("the announcement finally lands, once", len(overlay.announced), 1)

# Keeping it is the other half of the same offer.
ctrl, mission, cp, decision, turn, overlay, log, box = make(
    cards=[sm.BRING_IT_DOWN, filler, sm.CENTRE_GROUND])
ctrl.draw_at_command_phase("Player 1", 1)
tk.pick_option(decision, "Keep it")
checks.true("keeping it leaves Bring It Down in hand",
            any(c.key == "bring_it_down" for c in ctrl.hand))
checks.eq("and the pair is announced", len(overlay.announced), 1)

# The offer is WITHHELD when there is nothing to draw into - "discard and draw
# a new Secondary Mission" cannot be honoured with an empty deck, and this
# engine does not offer what it will not deliver.
ctrl, mission, cp, decision, turn, overlay, log, box = make(
    cards=[sm.BRING_IT_DOWN, sm.CENTRE_GROUND])
ctrl.draw_at_command_phase("Player 1", 1)
checks.eq("with the deck emptied by the draw, no redraw is offered",
          decision.is_pending, False)
checks.eq("the pair is announced immediately", len(overlay.announced), 1)

# ...and withheld when a big enemy model IS on the table.
ctrl, mission, cp, decision, turn, overlay, log, box = make(
    cards=[sm.BRING_IT_DOWN, filler, sm.CENTRE_GROUND])
box.extend(big.models)
ctrl.draw_at_command_phase("Player 1", 1)
checks.eq("with a 10+ Wounds enemy on the table, no redraw is offered",
          decision.is_pending, False)


# --- 5. scoring is never automatic ---
print("--- 5. cashing a card in ---")


def achieved_scene(cards=None):
    """A board where Centre Ground is met: a friendly unit on the centre and
    the nearest enemy far away."""
    ctrl, mission, cp, decision, turn, overlay, log, box = make(
        cards=cards if cards is not None else [sm.CENTRE_GROUND])
    mine = squad_at(ae.RANGERS, "Player 1", "1 Rangers 1", CENTRE_X, CENTRE_Y)
    theirs = squad_at(ae.RANGERS, "Player 2", "2 Rangers 1", CENTRE_X + 20, CENTRE_Y)
    box.extend(list(mine.models) + list(theirs.models))
    ctrl.hand = [sm.CENTRE_GROUND] if cards is None else list(cards)
    return ctrl, mission, cp, decision, turn, overlay, log


ctrl, mission, cp, decision, turn, overlay, log = achieved_scene()
ready = ctrl.achieved()
checks.eq("the card reads as achieved", len(ready), 1)
checks.eq("worth its 5 VP tier", ready[0][1], sm.CENTRE_GROUND_FAR_VP)

ctrl.begin_end_of_turn("Player 1")
checks.true("a prompt is opened", decision.is_pending)
checks.eq("NOTHING is scored before it is answered",
          mission.secondary_points.get("Player 1", 0), 0)
checks.true("the card is still in hand", sm.CENTRE_GROUND in ctrl.hand)
checks.true("the controller reports itself busy", ctrl.is_busy)
checks.true("the prompt offers keeping the card",
            any("keep" in lbl.lower() for lbl in tk.options_of(decision)))

tk.pick_option(decision, "Keep the card")
checks.eq("keeping it scores nothing", mission.secondary_points.get("Player 1", 0), 0)
checks.true("and leaves it in hand for a later turn", sm.CENTRE_GROUND in ctrl.hand)
# Keeping a card leaves it discardable, so the chain ends on the +1 CP offer.
checks.true("the discard-for-CP offer follows the scoring choice", decision.is_pending)
decline_discard(decision)
checks.eq("declining both leaves the controller idle", ctrl.is_busy, False)

# The same card, cashed in on a later turn - "oder ob ich die Karte noch
# behalte, um vielleicht spaeter einzuloesen".
ctrl.begin_end_of_turn("Player 1")
tk.pick_option(decision, "Score 5 VP")
decline_discard(decision)
checks.eq("cashing it in credits the ledger",
          mission.secondary_points.get("Player 1", 0), sm.CENTRE_GROUND_FAR_VP)
checks.eq("the card leaves the hand", len(ctrl.hand), 0)
checks.true("and is on the discard pile", sm.CENTRE_GROUND in ctrl.discarded)
checks.eq("mission totals pick it up",
          mission.total_points("Player 1"), sm.CENTRE_GROUND_FAR_VP)
checks.eq("the controller is no longer busy", ctrl.is_busy, False)

# An unachieved card is not offered at all.
ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[sm.CENTRE_GROUND])
ctrl.hand = [sm.CENTRE_GROUND]
ctrl.begin_end_of_turn("Player 1")
checks.eq("an unachieved card opens no scoring prompt", scoring_prompt_open(decision), False)

# Bring It Down, end to end, at the end of the OPPONENT's turn.
ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[sm.BRING_IT_DOWN])
ctrl.hand = [sm.BRING_IT_DOWN]
ctrl.record_destroyed_model(big.models[0])
ctrl.begin_end_of_turn("Player 2")
checks.true("a kill made during the opponent's turn is offered at its end",
            decision.is_pending)
tk.pick_option(decision, "Score 5")
checks.eq("and pays 5 VP", mission.secondary_points.get("Player 1", 0),
          sm.BRING_IT_DOWN_VP_PER_MODEL)
checks.eq("no discard offer follows the OPPONENT's turn end", decision.is_pending, False)
checks.eq("the destroyed-model list is cleared at the turn boundary",
          len(ctrl._destroyed_this_turn), 0)

# ...so the same kill cannot pay twice on the next turn.
ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[sm.BRING_IT_DOWN])
ctrl.hand = [sm.BRING_IT_DOWN]
ctrl.record_destroyed_model(big.models[0])
ctrl.begin_end_of_turn("Player 2")
tk.pick_option(decision, "Keep the card")
decline_discard(decision)
ctrl.begin_end_of_turn("Player 1")
checks.eq("a kill from a previous turn no longer counts", scoring_prompt_open(decision), False)


# --- 6. the 15 VP per battle round cap ---
print("--- 6. the 15 VP cap ---")

ctrl, mission, cp, decision, turn, overlay, log = achieved_scene()
ctrl.sync_battle_round(1)
checks.eq("a fresh round has the full allowance",
          ctrl.remaining_vp_this_round(), sm.MAX_SECONDARY_VP_PER_ROUND)
ctrl._scored_vp_this_round = 12
checks.eq("with 12 already scored, 3 are left", ctrl.remaining_vp_this_round(), 3)
ctrl.begin_end_of_turn("Player 1")
labels = tk.options_of(decision)
checks.true("the prompt offers the CLAMPED amount, not the card's face value",
            any("Score 3 VP" in lbl for lbl in labels))
checks.true("and says why it is short", any("cap" in lbl.lower() for lbl in labels))
tk.pick_option(decision, "Score 3 VP")
checks.eq("only 3 VP land", mission.secondary_points.get("Player 1", 0), 3)
checks.eq("the round's allowance is now spent", ctrl.remaining_vp_this_round(), 0)

# Fully capped: the card is not offered at all rather than offered for 0.
ctrl, mission, cp, decision, turn, overlay, log = achieved_scene()
ctrl.sync_battle_round(1)
ctrl._scored_vp_this_round = sm.MAX_SECONDARY_VP_PER_ROUND
ctrl.begin_end_of_turn("Player 1")
checks.eq("a fully-capped round offers no scoring prompt", scoring_prompt_open(decision), False)
checks.true("the card stays in hand", sm.CENTRE_GROUND in ctrl.hand)
checks.true("and the log says why", log.has("cap"))

# The allowance resets with the battle round - sync_battle_round() is
# idempotent, so it is called on every phase change.
ctrl.sync_battle_round(1)
checks.eq("re-syncing the SAME round does not reset the ledger",
          ctrl.remaining_vp_this_round(), 0)
ctrl.sync_battle_round(2)
checks.eq("the next battle round restores the full allowance",
          ctrl.remaining_vp_this_round(), sm.MAX_SECONDARY_VP_PER_ROUND)


# --- 7. discarding a card for +1 CP ---
print("--- 7. discard for CP ---")

ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[sm.CENTRE_GROUND])
ctrl.hand = [sm.CENTRE_GROUND]
before = cp.cp.get("Player 1", 0)
ctrl.begin_end_of_turn("Player 1")
checks.true("the discard offer opens at the end of your own turn", decision.is_pending)
checks.true("it lists the card by name",
            any("Centre Ground" in lbl for lbl in tk.options_of(decision)))
checks.true("and a way to decline",
            any("keep them all" in lbl.lower() for lbl in tk.options_of(decision)))
tk.pick_option(decision, "Discard Centre Ground")
checks.eq("exactly 1 CP is granted", cp.cp.get("Player 1", 0) - before, 1)
checks.eq("the card leaves the hand", len(ctrl.hand), 0)

# The cap is CommandPointManager's, shared with every other bonus-CP source -
# so a second discard in the same battle round pays nothing, and is therefore
# not offered at all.
ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[sm.CENTRE_GROUND])
ctrl.hand = [sm.CENTRE_GROUND, sm.BRING_IT_DOWN]
cp.gain_cp("Player 1", turn.battle_round, amount=1, reason="some other ability")
before = cp.cp.get("Player 1", 0)
ctrl.begin_end_of_turn("Player 1")
checks.eq("with the round's bonus CP already spent elsewhere, nothing is offered",
          decision.is_pending, False)
checks.eq("both cards stay in hand", len(ctrl.hand), 2)
# And if it is forced through anyway, it grants 0 rather than a second CP.
checks.eq("a forced discard grants 0 CP", ctrl.discard_for_cp(sm.CENTRE_GROUND), 0)
checks.eq("no CP appeared", cp.cp.get("Player 1", 0) - before, 0)

# Not at the end of the OPPONENT's turn - "am Ende meiner Runde".
ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[sm.CENTRE_GROUND])
ctrl.hand = [sm.CENTRE_GROUND]
ctrl.begin_end_of_turn("Player 2")
checks.eq("no discard offer at the end of the opponent's turn", decision.is_pending, False)

# An empty hand offers nothing.
ctrl, mission, cp, decision, turn, overlay, log, box = make(cards=[sm.CENTRE_GROUND])
ctrl.begin_end_of_turn("Player 1")
checks.eq("an empty hand offers nothing", decision.is_pending, False)

# CommandPointManager's own new query, in both directions.
cp2 = CommandPointManager()
checks.eq("a fresh round has bonus CP available", cp2.bonus_cp_remaining("Player 1", 1), 1)
checks.eq("asking does not itself spend anything", cp2.bonus_cp_remaining("Player 1", 1), 1)
cp2.gain_cp("Player 1", 1, amount=1, reason="test")
checks.eq("after a grant, none is left", cp2.bonus_cp_remaining("Player 1", 1), 0)
checks.eq("the next battle round has it again", cp2.bonus_cp_remaining("Player 1", 2), 1)


# --- 8. "No Mercy" belongs to the AI now ---
print("--- 8. No Mercy is the AI's ---")

mission = MissionController(game_log=tk.Log())
victim_p1 = tk.build(ae.RANGERS, owner="Player 1", name="1 Rangers 9")
victim_p2 = tk.build(ae.RANGERS, owner="Player 2", name="2 Rangers 9")
mission.record_destroyed_squad(victim_p2)   # credits Player 1
mission.record_destroyed_squad(victim_p1)   # credits Player 2
checks.eq("Player 1 scores no No Mercy points - they play the deck",
          mission.score_secondary_end_of_turn("Player 1"), 0)
checks.eq("their Secondary ledger is untouched by it",
          mission.secondary_points.get("Player 1", 0), 0)
# One kill, at the standard Secondary's own rate - pinned against the CONSTANT,
# which has been retuned once (1 -> 3, user: "secondary gibt 3 statt 1").
checks.eq("Player 2 still scores No Mercy normally",
          mission.score_secondary_end_of_turn("Player 2"),
          missions.SECONDARY_POINTS_PER_KILL)
checks.true("plays_secondary_cards reflects the config",
            mission.plays_secondary_cards("Player 1"))
checks.eq("and the AI is not on it", mission.plays_secondary_cards("Player 2"), False)
# add_secondary_points() is the one door card VP comes through.
checks.eq("add_secondary_points credits the shared ledger",
          mission.add_secondary_points("Player 1", 4), 4)
checks.eq("it lands in secondary_points", mission.secondary_points.get("Player 1", 0), 4)
checks.eq("a zero/negative amount is refused", mission.add_secondary_points("Player 1", 0), 0)
# The trio GameStatusPanel and test_faction_badges.py duck-type must survive.
for attr in ("primary_points", "secondary_points", "total_points"):
    checks.true(f"MissionController still exposes {attr}", hasattr(mission, attr))


# --- 9. A/B probes: the whole pre-fix world, not one line ---
print("--- 9. A/B probes ---")

# 9a. Without the 15 VP cap, the over-cap card pays its full face value.
saved_cap = sm.MAX_SECONDARY_VP_PER_ROUND
try:
    sm.MAX_SECONDARY_VP_PER_ROUND = 10 ** 6
    ctrl, mission, cp, decision, turn, overlay, log = achieved_scene()
    ctrl.sync_battle_round(1)
    ctrl._scored_vp_this_round = 12
    ctrl.begin_end_of_turn("Player 1")
    tk.pick_option(decision, "Score")
    decline_discard(decision)
    checks.eq("A/B: with the cap removed the full 5 VP lands (it was clamped to 3)",
              mission.secondary_points.get("Player 1", 0), sm.CENTRE_GROUND_FAR_VP)
finally:
    sm.MAX_SECONDARY_VP_PER_ROUND = saved_cap

# 9b. Without the per-round draw guard, the same round draws again and again.
ctrl, mission, cp, decision, turn, overlay, log, box = make(
    cards=[sm.CENTRE_GROUND, filler, sm.BRING_IT_DOWN, filler])
ctrl.draw_at_command_phase("Player 1", 1)
ctrl._drawn_round = None  # neutralise the guard
ctrl.draw_at_command_phase("Player 1", 1)
checks.eq("A/B: without the round guard the deck is drained in one round",
          len(ctrl.hand), 4)


# --- 10. wiring: the hooks really exist in main.py ---
print("--- 10. wiring ---")

main_src = io.open("main.py", encoding="utf-8").read()

checks.eq("main.py builds the controller exactly once",
          main_src.count("secondary_mission_controller = SecondaryMissionController("), 1)
checks.eq("it is given a live token source, once",
          main_src.count("secondary_mission_controller.set_tokens_source("), 1)
checks.eq("the draw overlay is attached, once",
          main_src.count("secondary_mission_controller.draw_overlay = mission_draw_overlay"), 1)
checks.eq("and buffered announcements are flushed",
          main_src.count("secondary_mission_controller.flush_announcements()"), 1)

# The end-of-turn call has to sit in the block that only runs when a turn is
# actually ending - sliced out first so a match elsewhere cannot give a false
# green.
end_of_turn_block = main_src[main_src.index("if ending_player is not None:"):]
end_of_turn_block = end_of_turn_block[:end_of_turn_block.index("if turn_tracker.phase == PHASE_COMMAND:")]
checks.true("the end-of-turn step runs in the end-of-turn block",
            "secondary_mission_controller.begin_end_of_turn(" in end_of_turn_block)
# It must be handed the round the ENDING TURN belonged to, not the live counter:
# advance_phase() has already run by then and may have rolled it over, which
# would stop Beacon ("round 5") from ever firing.
checks.true("and given the pre-advance battle round",
            "battle_round=battle_round_before" in end_of_turn_block)

command_block = main_src[main_src.index("if turn_tracker.phase == PHASE_COMMAND:"):]
command_block = command_block[:command_block.index("if turn_tracker.phase == PHASE_MOVEMENT:")]
checks.true("the draw runs in the Command-phase block",
            "secondary_mission_controller.draw_at_command_phase(" in command_block)
checks.true("driven by turn_owner, not active_player",
            "draw_at_command_phase(\n                turn_tracker.turn_owner" in command_block)

checks.eq("the round ledger is synced on every phase change, and at both battle starts",
          main_src.count("secondary_mission_controller.sync_battle_round("), 3)
checks.eq("both battle-start paths draw round 1's cards",
          main_src.count("secondary_mission_controller.draw_at_command_phase("), 3)

checks.true("every removed model is reported",
            "secondary_mission_controller.record_destroyed_model(dead)" in main_src)
checks.true("an open mission prompt blocks the phase from advancing",
            "or secondary_mission_controller.is_busy" in main_src)

# The strip is handed BOTH mission systems now: this deck for the hand, and the
# Force Disposition Primary for the card at the top of it. Checked as two
# separate needles rather than as one exact multi-line call - that is what this
# was, and it went red the moment a second argument arrived, which is a guard
# failing on formatting instead of on meaning.
checks.eq("the strip is handed the deck",
          main_src.count("mission_cards_overlay.draw(screen, left_panel_rect, mission_controller,"), 1)
checks.true("...and the Primary controller alongside it",
            "primary_controller=primary_mission_controller)" in main_src)
# NOT drawn directly any more: it goes through main.py's _front_notice(), so
# only the front-most modal is ever on screen. test_one_modal_at_a_time.py
# owns that rule; here we only pin that this notice takes part in it.
checks.eq("the draw notice is never drawn unconditionally",
          main_src.count("mission_draw_overlay.draw(screen)"), 0)
front_helper = main_src[main_src.index("def _front_notice():"):]
front_helper = front_helper[:front_helper.index("def advance_turn_phase():")]
checks.true("it is listed among the one-at-a-time modals",
            "mission_draw_overlay" in front_helper)
checks.eq("and dismissed by a click", main_src.count("mission_draw_overlay.dismiss()"), 1)
# It must gate the AI everywhere the sibling notices do, or auto-play runs on
# underneath a notice nobody has read.
checks.eq("the AI is gated on it at every site the Stratagem notice gates",
          main_src.count("not mission_draw_overlay.is_pending"),
          main_src.count("not stratagem_notice_overlay.is_pending"))

# The six headless harnesses must switch the deck off - they answer no prompt
# belonging to the human outside the pre-game, so leaving it on stalls them.
for harness in ("smoke_pregame.py", "smoke_log_input.py", "smoke_setup_screens.py",
                "smoke_measure_tool.py", "smoke_end_turn_warning.py", "selfplay.py"):
    src = io.open(harness, encoding="utf-8").read()
    checks.eq(f"{harness} turns the Secondary Mission deck off",
              src.count("config.SECONDARY_MISSION_CARD_PLAYERS = ()"), 1)


# --- 11. every card with a detail says which KIND of detail it is ---------
print("--- 11. detail: remembered choice or live readout ---")
# A SET DIFFERENCE at the source, not a list of card names. The strip's
# collapsed bar may show a REMEMBERED CHOICE (A Tempting Target's objective)
# and must never show a LIVE READOUT ("presence in 2 of 4 table quarters") -
# a bar claiming a live score was the first version of that strip and was
# reported as wrong. A behaviour test cannot see the twelfth card, because it
# does not exist yet; this line does.
_all_cards = [v for v in vars(sm).values() if isinstance(v, sm.SecondaryMissionCard)]
checks.true("the sweep actually found the cards", len(_all_cards) >= 17)

_with_detail = [c for c in _all_cards if c.detail(sm.MissionContext(
    "Player 1", card_state={})) is not None or c._detail is not None]
_remembered = [c for c in _all_cards if c._subject is not None]
_live = [c for c in _all_cards if c.detail_is_live]

checks.eq("every card with a detail declares which kind it is",
          sorted(c.key for c in _with_detail
                 if c._subject is None and not c.detail_is_live), [])
checks.eq("and none claims to be both",
          sorted(c.key for c in _remembered if c.detail_is_live), [])
checks.eq("a card with no detail declares neither",
          sorted(c.key for c in _all_cards
                 if c._detail is None and (c._subject is not None or c.detail_is_live)), [])
# Vacuity guards: the two halves have to be non-empty, or the set difference
# above is satisfied by a file in which nothing is classified at all.
checks.true("there really are remembered-choice cards", len(_remembered) >= 4)
checks.true("...and live-readout cards", len(_live) >= 7)
checks.eq("the two halves account for every detail-carrying card",
          len(_remembered) + len(_live), len(_with_detail))

# THE load-bearing property, and the reason `subject` is a separate field
# rather than a shortened `detail`: it must not move when the board does.
# Without this the guard above passes on a subject that simply returns the
# whole live sentence.
_probe_obj = next(o for o in board.objectives if o.controlled_by is None)
_probe = sm.SecondaryMissionController(player="Player 1")
_probe.set_tokens_source(lambda: [])
_probe.set_objectives_source(lambda: board.objectives)
_probe.set_zones_source(lambda: board.deployment_zones)
_probe.card_state.setdefault("a_tempting_target", {})["objective"] = _probe_obj
_probe.card_state.setdefault("beacon", {})["objective"] = _probe_obj

_moved = []
for _card in _remembered:
    if _card.key not in ("a_tempting_target", "beacon"):
        continue  # the two this probe can stage; the other two need a guard/home objective
    _probe_obj.controlled_by = None
    _before_subject = _probe.subject_for(_card)
    _before_detail = _probe.detail_for(_card)
    _probe_obj.controlled_by = "Player 2"
    checks.eq(f"{_card.key}: the subject does not move when control flips",
              _probe.subject_for(_card), _before_subject)
    if _probe.detail_for(_card) != _before_detail:
        _moved.append(_card.key)
_probe_obj.controlled_by = None
# ...and at least one of them HAS a live half, or "the subject did not move"
# is satisfied by a card whose detail never moves either - which proves
# nothing about the split. Measured: A Tempting Target and Defend Stronghold
# print "(held by X)", Beacon and Burden of Trust do not.
checks.eq("...on a card whose detail genuinely does move", _moved, ["a_tempting_target"])

checks.finish()
