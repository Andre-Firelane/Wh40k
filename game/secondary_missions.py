"""Tactical Secondary Missions as a CARD DECK, for the human player only
(user-supplied, not the generic core rulebook: "Die Missionen sollen nur fuer
mich gelten, fuer den menschlichen Spieler. Die KI soll ihre Standard-Mission
erstmal behalten.").

WHAT THIS REPLACES
------------------
game/missions.py keeps the Primary ("Hold the Line") for everyone and keeps the
standard Secondary ("No Mercy") for whoever is NOT playing the deck. A player
listed in config.SECONDARY_MISSION_CARD_PLAYERS plays this deck INSTEAD of "No
Mercy" - that is a list-building declaration and is not derivable from what is
on the board, the same reasoning as config.SEER_COUNCIL_PLAYERS /
config.AWAKENED_DYNASTY_PLAYERS.

THE LOOP, AS THE USER DESCRIBED IT
----------------------------------
- At the start of your own Command phase you draw two cards into a hand that
  has no size limit ("Ich kann so viele secondary Missionen auf der Hand haben,
  wie ich moechte"). The draw is announced by a click-away overlay, then the
  cards join the strip on the left.
- Each card names its own scoring instant. When it is met you are ASKED whether
  to cash it in now - never scored automatically ("ich muss dann gefragt werden,
  ob ich diese Punkte jetzt einloesen moechte oder nicht, oder ob ich die Karte
  noch behalte, um vielleicht spaeter einzuloesen"). Cashing in discards the
  card; keeping it leaves it in hand for a later turn.
- At the end of your turn you may instead discard one card for +1 CP, capped at
  one bonus CP per battle round.
- At most MAX_SECONDARY_VP_PER_ROUND Secondary VP per battle round.

The deck holds each card ONCE per battle and is not reshuffled (user choice):
when it runs dry, no more cards are drawn.

WHY EVERY CHOICE IS A DecisionManager PROMPT
--------------------------------------------
The mission cards are drawn OVER the board (they are anchored at the left
panel's right edge, i.e. inside board_rect_screen, not inside left_panel_rect),
so a click on one falls through main.py's state-gated event chain to the board
branch and starts a camera pan. Making them clickable would mean a brand-new
branch ahead of that one - exactly the wiring trap CLAUDE.md records five times
under error class 15. So the strip stays a polled-hover, DRAW-ONLY view and
every decision goes through the DecisionManager overlay that already renders
every other choice in this game. It also means ai/agent_driver.py's generic
_maybe_resolve_decision() would answer these if the deck were ever handed to a
player it drives - no extra wiring needed.

ACTIONS: DELIBERATELY NOT BUILT YET
-----------------------------------
The user noted that some missions will need ACTIONS to complete. This engine
has no Actions system at all (see game/fall_back.py's own note), and neither
supplied card needs one - so nothing speculative is built here. A card's
`requires_action` field below is the named hook where that state will attach;
until a card sets it, it stays a documented gap rather than an unused system.
"""

import random

from game import config
from game.objectives import is_within_range_of_objective
from game.actions import ActionDefinition
from game.turn import PHASE_SHOOTING
# BATTLE_ROUNDS lives with the Primary because missions define game length.
# Beacon's "round 5" IS that last round, so it is read from there rather
# than written out again - the two would otherwise drift apart silently.
from game.missions import BATTLE_ROUNDS


def _other_player(player):
    # A local copy, matching this codebase's usual per-module small-helper
    # convention - game/missions.py and several other modules each keep their
    # own rather than sharing one.
    return "Player 2" if player == "Player 1" else "Player 1"

# A card's scoring instant. The two supplied cards differ, and the difference
# is printed on them: Centre Ground says "END OF YOUR TURN", Bring It Down says
# "END OF A TURN" - so Bring It Down is also checked when the OPPONENT's turn
# ends, and a kill made during their turn can score there.
TIMING_END_OF_YOUR_TURN = "end_of_your_turn"
TIMING_END_OF_ANY_TURN = "end_of_any_turn"
# Beacon's own, and the first that is not "every turn": user-expanded from the
# card's compressed "END OPP TURN - R5" badge to "END OF OPPONENTS TURN - ROUND
# 5". ONE instant in the whole battle - the end of the opponent's turn in the
# final battle round - so a Beacon is planted early and has to still be standing
# in the right place when the battle ends.
TIMING_END_OF_OPPONENT_TURN_FINAL_ROUND = "end_of_opponent_turn_final_round"
# What the strip shows on a card's collapsed bar. A card is checked ONLY at its
# own instant, so this - not a live "would it score right now" snapshot - is
# what a player needs to read off the bar.
TIMING_LABELS = {
    TIMING_END_OF_YOUR_TURN: "end of your turn",
    TIMING_END_OF_ANY_TURN: "end of a turn",
    TIMING_END_OF_OPPONENT_TURN_FINAL_ROUND: f"end of enemy turn, round {BATTLE_ROUNDS}",
}

# User-supplied cap: "Man kann nicht mehr als 15 Secondary Punkte pro Runde
# bekommen." Per BATTLE ROUND, matching the wording used for the CP cap in the
# same breath ("nicht mehr als einen zusaetzlichen Kommando-Punkt pro
# Schlachtrunde"). It CLAMPS rather than refuses - see cash_in().
MAX_SECONDARY_VP_PER_ROUND = 15

CARDS_DRAWN_PER_ROUND = 2

# Rule 03.04's Engagement Range and the objective range both live on the units
# they belong to; these two are Centre Ground's own printed numbers and belong
# to this card, not to any shared constant.
CENTRE_GROUND_FRIENDLY_RANGE_IN = 3.0
CENTRE_GROUND_CLEAR_NEAR_IN = 3.0   # the 3 VP tier
CENTRE_GROUND_CLEAR_FAR_IN = 6.0    # the 5 VP tier
CENTRE_GROUND_NEAR_VP = 3
CENTRE_GROUND_FAR_VP = 5

BRING_IT_DOWN_WOUNDS = 10       # "a Wounds characteristic of 10+"
BRING_IT_DOWN_VP_PER_MODEL = 5  # the TACTICAL half; the FIXED half's 4 VP is ignored per the user
BRING_IT_DOWN_MAX_VP = 5        # the card's own "MAX 5VP" stamp

GRIEVOUS_BLOW_STARTING_STRENGTH = 13  # "a Starting Strength of 13+"
GRIEVOUS_BLOW_VP_PER_UNIT = 5         # TACTICAL; the FIXED half prints 4 and is ignored per the user
GRIEVOUS_BLOW_MAX_VP = 5              # the card's own "MAX 5VP" stamp

# Assassination's two Tactical branches print the SAME value, so they are
# alternatives, not tiers - one number, not two.
ASSASSINATION_VP = 5

TEMPTING_TARGET_VP = 5

BEHIND_ENEMY_LINES_VP_PER_UNIT = 3  # TACTICAL; capped below, so one unit pays 3 and two or more pay 5
BEHIND_ENEMY_LINES_MAX_VP = 5

BURDEN_OF_TRUST_VP_PER_OBJECTIVE = 2  # TACTICAL; three guarded objectives are worth 6 and pay 5
BURDEN_OF_TRUST_MAX_VP = 5

OVERWHELMING_FORCE_VP_PER_UNIT = 3  # 3 VP each, capped at 5 - one unit pays 3, two or more pay 5
OVERWHELMING_FORCE_MAX_VP = 5

SECURE_NO_MANS_LAND_NEEDED = 2  # "two or more objectives within No Man's Land"
SECURE_NO_MANS_LAND_VP = 5

PLUNDER_VP = 5

NO_PRISONERS_VP_PER_UNIT = 2  # 2 VP each, capped at 5 - so two units pay 4 and three pay 5
NO_PRISONERS_MAX_VP = 5

OUTFLANK_EDGE_RANGE_IN = 6.0        # "within 6\" of one or more battlefield edges"
OUTFLANK_ONE_EDGE_VP = 3
OUTFLANK_OPPOSITE_EDGES_VP = 5

ENGAGE_CENTRE_EXCLUSION_IN = 6.0  # "not within 6\" of the battlefield centre"
ENGAGE_THREE_QUARTERS_VP = 3      # TACTICAL; the FIXED half prints 2 and is ignored per the user
ENGAGE_FOUR_QUARTERS_VP = 5       # TACTICAL; FIXED prints 4

FORWARD_POSITION_VP = 5

DEFEND_STRONGHOLD_CONTROL_VP = 3  # "You control your home objective"
DEFEND_STRONGHOLD_CLEAR_VP = 5    # "...and no enemy units are within your deployment zone"
DEFEND_STRONGHOLD_FROM_ROUND = 2  # the card's own "2ND ROUND ONWARD" band

# Display of Might's two bands share one condition and differ only in WHEN -
# holding No Man's Land through the enemy's turn is the harder half.
DISPLAY_OF_MIGHT_YOUR_TURN_VP = 2
DISPLAY_OF_MIGHT_OPPONENT_TURN_VP = 5

CLEANSE_ONE_VP = 2   # "One objective was cleansed this turn"
CLEANSE_MANY_VP = 5  # "Two or more objectives were cleansed this turn"

BEACON_OUTSIDE_DEPLOYMENT_VP = 3  # "on the battlefield and outside your deployment zone"
BEACON_OUTSIDE_TERRITORY_VP = 5   # "...and outside your territory" - user: territory = your half of the board


def board_centre():
    """The centre of the battlefield, in inches. Read from config at CALL time
    - maps.apply_to_config() writes the board dimensions at startup, so a
    module-level copy would be the pre-map board (see game/config.py's own note
    forbidding `from game.config import BOARD_WIDTH_IN`)."""
    return (config.BOARD_WIDTH_IN / 2.0, config.BOARD_HEIGHT_IN / 2.0)


def model_distance_to_point(model, x_in, y_in):
    """Base-EDGE distance from a model to a bare point, the same
    edge-not-centre convention game/squad.py's edge_distance() uses between two
    models. Kept local: this is its only consumer, and this repo's rule is to
    extract at the SECOND one, not in anticipation."""
    dx = model.x_in - x_in
    dy = model.y_in - y_in
    return max(0.0, (dx * dx + dy * dy) ** 0.5 - model.radius_in)


def objective_centre(objective):
    """The middle of an objective's terrain footprint, in inches. An Objective
    is a TerrainArea (13.01) made of axis-aligned features, so this is the
    centre of their common bounding box - the same `bounding_box` the renderer
    already draws the marker's outline from."""
    min_x, min_y, max_x, max_y = objective.terrain_area.bounding_box
    return ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)


def zone_distance(zone, x_in, y_in):
    """Distance from a point to the nearest edge of a deployment zone, 0 if
    inside it. The zone is one or more axis-aligned rects, so this is the
    smallest per-rect clamp distance."""
    best = None
    for x, y, w, h in zone.rects:
        dx = max(abs(x_in - x) - w / 2.0, 0.0)
        dy = max(abs(y_in - y) - h / 2.0, 0.0)
        dist = (dx * dx + dy * dy) ** 0.5
        if best is None or dist < best:
            best = dist
    return best if best is not None else float("inf")


def _zone_centre(zone):
    xs = [x for x, y, w, h in zone.rects]
    ys = [y for x, y, w, h in zone.rects]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def in_own_territory(ctx, x_in, y_in):
    """Whether a point is in `ctx.player`'s own half of the board.

    User's definition, supplied with the Beacon card: "Territory heisst einfach
    ausserhalb meiner Spielfeldhaelfte" - so territory is a HALF-BOARD, a much
    bigger area than the deployment zone inside it, which is why Beacon pays 5
    for leaving it and only 3 for leaving the zone.

    Which half is whose is DERIVED from where the two deployment zones sit
    rather than assumed: the split axis is whichever one separates them (all
    three shipped maps band the zones across the full width and split on y, but
    a future map could do the opposite), and your half is the side yours is
    on. Falls back to "everything is your territory" when the zones are unknown
    - that scores 0 rather than inventing a free 5 VP."""
    mine = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    theirs = [z for z in ctx.deployment_zones if z.owner == ctx.opponent]
    if not mine or not theirs:
        return True
    my_cx, my_cy = _zone_centre(mine[0])
    their_cx, their_cy = _zone_centre(theirs[0])
    centre_x, centre_y = board_centre()
    if abs(my_cy - their_cy) >= abs(my_cx - their_cx):
        return (y_in >= centre_y) if my_cy >= centre_y else (y_in <= centre_y)
    return (x_in >= centre_x) if my_cx >= centre_x else (x_in <= centre_x)


def no_mans_land_objectives(ctx):
    """The objectives in No Man's Land - i.e. inside NOBODY's deployment zone.

    That single test also delivers the card's "excl. home objectives" clause
    for free, and does it without reading names: every map here places its home
    objectives inside their owner's zone, so "not in a deployment zone" and
    "not a home objective" pick out the same set. Deriving it from geometry
    rather than from the string "Home" means a renamed or newly added objective
    is classified correctly on its own."""
    out = []
    for objective in ctx.objectives:
        cx, cy = objective_centre(objective)
        if not any(z.contains_point(cx, cy) for z in ctx.deployment_zones):
            out.append(objective)
    return out


def _live_squads(tokens):
    """Every squad with at least one model still on the board. Derived from
    tokens rather than from a squad list so a wiped-out unit cannot linger -
    the same source main.py's own `{t.squad for t in state.tokens}` sets use."""
    return {t.squad for t in tokens if t.squad is not None and t.squad.models}


def _unit_within_of_point(squad, x_in, y_in, range_in):
    return any(model_distance_to_point(m, x_in, y_in) <= range_in for m in squad.models)


class MissionContext:
    """Everything a card's predicate is allowed to look at. A plain bag rather
    than passing five arguments around: a new card that needs one more fact
    adds a field here instead of changing every predicate's signature."""

    def __init__(self, player, tokens=(), turn_tracker=None, ending_player=None,
                 destroyed_this_turn=(), destroyed_squads_this_turn=(),
                 destroyed_characters_this_battle=(), all_squads=None,
                 objectives=(), deployment_zones=(), card_state=None,
                 battle_round=None, embarked_squads=(), hand=(), terrain_areas=(),
                 on_objective_at_turn_start=()):
        # The cards currently in hand. Two cards ask whether ANOTHER card is
        # "active" (Cleanse about Plunder and vice versa), which is the only
        # thing in this module that looks sideways at the rest of the hand.
        self.hand = list(hand)
        # Terrain areas (13.01) - Plunder's targets.
        self.terrain_areas = list(terrain_areas)
        # id(squad) for every enemy unit that was within range of an objective
        # at the START of this turn. A snapshot, because Overwhelming Force
        # asks about a moment that has passed by the time it scores - and about
        # units that no longer exist.
        self.on_objective_at_turn_start = set(on_objective_at_turn_start)
        # The battle round the ENDING TURN belonged to. Passed in rather than
        # read off turn_tracker: begin_end_of_turn() runs AFTER
        # TurnTracker.advance_phase(), which - when the second player's turn
        # ends - has already incremented battle_round. A card asking "is this
        # round 5" would then see 6 and never fire.
        self.battle_round = battle_round
        # Units inside a TRANSPORT (18.02). Neither on the board nor in
        # reserves; Beacon's setup explicitly offers them.
        self.embarked_squads = list(embarked_squads)
        # Board furniture, for cards that talk about places rather than kills.
        self.objectives = list(objectives)
        self.deployment_zones = list(deployment_zones)
        # The per-card scratchpad. A card that remembers something across the
        # battle (which objective is your tempting target, which unit is your
        # beacon) MUST keep it here and not on itself: the SecondaryMissionCard
        # objects are module-level singletons shared by every battle, and
        # writing state onto one is the shared-class-attribute trap this
        # codebase already documents for UnitProfile. The controller owns the
        # dict, keyed by card, so two battles cannot see each other's choices.
        self.card_state = {} if card_state is None else card_state
        self.player = player
        self.tokens = list(tokens)
        self.turn_tracker = turn_tracker
        self.ending_player = ending_player
        # Models destroyed since the last turn boundary, both sides. Cards that
        # say "destroyed this turn" read this; nothing else does.
        self.destroyed_this_turn = list(destroyed_this_turn)
        # Whole UNITS wiped out since the last turn boundary. A separate list,
        # not derived from the models above: "unit destroyed" is main.py's own
        # attached_units.unit_is_destroyed() judgement (19.01 merges a leader
        # into its bodyguard squad, so a half-dead unit is not a destroyed
        # one), and re-deriving it here would be a second opinion on a question
        # the engine already answers.
        self.destroyed_squads_this_turn = list(destroyed_squads_this_turn)
        # Enemy CHARACTER models destroyed at ANY point in the battle - a
        # longer lifetime than everything above, for Assassination's
        # "have been destroyed during the battle" clause.
        self.destroyed_characters_this_battle = list(destroyed_characters_this_battle)
        # Every unit still in the game, wherever it is - board, Strategic
        # Reserves (03.02) or embarked in a transport (18.02). `tokens` is the
        # BOARD only, so a card asking "are any left at all" must not use it:
        # a character sitting in reserves is not on the battlefield and is also
        # very much not destroyed. main.py supplies state.all_squads().
        self._all_squads = None if all_squads is None else list(all_squads)

    @property
    def opponent(self):
        return _other_player(self.player)

    def friendly_squads(self):
        return [sq for sq in _live_squads(self.tokens) if sq.owner == self.player]

    def enemy_squads(self):
        return [sq for sq in _live_squads(self.tokens) if sq.owner != self.player]

    def all_squads(self):
        """Board + reserves + embarked. Falls back to the board alone when no
        richer source was supplied (tests that only care about the board)."""
        if self._all_squads is None:
            return list(_live_squads(self.tokens))
        return [sq for sq in self._all_squads if sq is not None and sq.models]

    def living_enemy_models(self):
        return [m for sq in self.all_squads() if sq.owner != self.player for m in sq.models]


class SecondaryMissionCard:
    """One Tactical Secondary mission card.

    `score(ctx)` returns the VP this card would be worth RIGHT NOW, 0 meaning
    "not achieved". It is a pure function of the context - no side effects, no
    memory - so it can be asked repeatedly. It is asked ONLY at the card's own
    scoring instant: asking mid-turn answers a different question ("would this
    hold if the turn ended now") and rendering that as a fulfilment claim was a
    real reported bug - see offered_now().

    `when_drawn_may_redraw(ctx)` is the card's own "WHEN DRAWN" clause: True
    when the printed condition for discarding it right away is met. Only Bring
    It Down has one; the default is False.

    `requires_action` is the named hook for the Actions system that does not
    exist yet - see the module docstring. No card sets it.
    """

    def __init__(self, key, name, text, timing, score, when_drawn_may_redraw=None,
                 requires_action=False, on_draw=None, detail=None,
                 draw_choices=None, draw_prompt=None,
                 when_drawn_shuffles_back=False, action=None,
                 when_drawn_is_mandatory=False, min_battle_round=None):
        self.key = key
        self.name = name
        self.text = text
        self.timing = timing
        self._score = score
        self._when_drawn = when_drawn_may_redraw
        self.requires_action = requires_action
        # Optional "WHEN DRAWN" SETUP - distinct from when_drawn_may_redraw,
        # which is the "you may discard and draw again" clause. This one picks
        # something the card then remembers (a target objective, a beacon
        # unit); whatever it returns is stored in the controller's per-card
        # state, never on this shared singleton.
        self._on_draw = on_draw
        # Optional one-line description of that remembered choice, so the strip
        # and the draw notice can show WHICH objective/unit was picked. Without
        # it a card with setup state is unplayable - the printed text alone
        # never says which one it means.
        self._detail = detail
        # An INTERACTIVE WHEN DRAWN setup: returns [(label, value), ...] for the
        # player to pick from. Distinct from on_draw, which decides by itself.
        # Beacon is the player's own choice ("Choose one friendly unit"), so it
        # gets a prompt; A Tempting Target is the OPPONENT's and is decided
        # deterministically from the user's supplied rule.
        self._draw_choices = draw_choices
        self._draw_prompt = draw_prompt
        # Whether a declined-and-redrawn card goes back into the DECK
        # ("shuffle this card back", Behind Enemy Lines) or onto the discard
        # pile (Bring It Down, A Grievous Blow). The distinction is printed.
        self.when_drawn_shuffles_back = when_drawn_shuffles_back
        # The rule-16.01 ActionDefinition this card's scoring depends on, if
        # any. `requires_action` above says THAT it needs one; this is the one.
        self.action = action
        # Whether the WHEN DRAWN redraw clause is an INSTRUCTION rather than an
        # offer. Behind Enemy Lines prints "you may shuffle this card back";
        # Defend Stronghold prints the same sentence WITHOUT it. One gets a
        # prompt, the other just happens.
        self.when_drawn_is_mandatory = when_drawn_is_mandatory
        # A card that is not live until a given battle round ("2ND ROUND
        # ONWARD"). None = live from the start.
        self.min_battle_round = min_battle_round

    @property
    def timing_label(self):
        return TIMING_LABELS.get(self.timing, "")

    def scores_at(self, ctx):
        if (self.min_battle_round is not None and ctx.battle_round is not None
                and ctx.battle_round < self.min_battle_round):
            return False
        """Whether this card's own printed instant is the one that just
        happened. Centre Ground says "end of YOUR turn"; Bring It Down says
        "end of A turn" and so also fires when the opponent's turn ends."""
        if self.timing == TIMING_END_OF_OPPONENT_TURN_FINAL_ROUND:
            # Both halves matter, and the round is the one the ENDING TURN
            # belonged to - see MissionContext.battle_round, which main.py
            # supplies from before advance_phase(), since by the time this runs
            # the counter may already have rolled into the next round.
            return (ctx.ending_player == ctx.opponent
                    and ctx.battle_round == BATTLE_ROUNDS)
        if self.timing == TIMING_END_OF_ANY_TURN:
            return ctx.ending_player is not None
        return ctx.ending_player == ctx.player

    def score(self, ctx):
        return max(0, int(self._score(ctx)))

    def when_drawn_may_redraw(self, ctx):
        return bool(self._when_drawn(ctx)) if self._when_drawn is not None else False

    @property
    def has_setup(self):
        return self._on_draw is not None

    @property
    def has_interactive_setup(self):
        return self._draw_choices is not None

    def draw_choices(self, ctx):
        return list(self._draw_choices(ctx)) if self._draw_choices is not None else []

    @property
    def draw_prompt(self):
        return self._draw_prompt or f"{self.name}: choose."

    def on_draw(self, ctx):
        """Resolve this card's WHEN DRAWN setup. Returns whatever the card
        wants remembered, or None."""
        return self._on_draw(ctx) if self._on_draw is not None else None

    def detail(self, ctx):
        return self._detail(ctx) if self._detail is not None else None


# ------------------------------------------------------------- the two cards

def _centre_ground(ctx):
    """CENTRE GROUND, Tactical half.

    5 VP: a friendly unit within 3" of the battlefield centre and NO enemy unit
    within 6" of it. 3 VP: the same, but only "no enemy unit within 3"".

    The two tiers are nested - the 5 VP condition is strictly stricter - so the
    better one is tested first and the weaker one is the fallback.

    "excluding AIRCRAFT and battle-shocked units": battle-shock is
    squad.battle_shocked. AIRCRAFT is a documented NO-OP - this engine has no
    AIRCRAFT keyword at all, the same carve-out game/rapid_ingress.py already
    writes down for Rapid Ingress. The exclusion applies to the FRIENDLY side
    only; the card places no such qualifier on the enemy units it asks about.
    """
    centre_x, centre_y = board_centre()
    friendly = any(
        _unit_within_of_point(sq, centre_x, centre_y, CENTRE_GROUND_FRIENDLY_RANGE_IN)
        for sq in ctx.friendly_squads() if not sq.battle_shocked
    )
    if not friendly:
        return 0
    enemies = ctx.enemy_squads()
    if not any(_unit_within_of_point(sq, centre_x, centre_y, CENTRE_GROUND_CLEAR_FAR_IN) for sq in enemies):
        return CENTRE_GROUND_FAR_VP
    if not any(_unit_within_of_point(sq, centre_x, centre_y, CENTRE_GROUND_CLEAR_NEAR_IN) for sq in enemies):
        return CENTRE_GROUND_NEAR_VP
    return 0


def _big_enemy_models(ctx):
    """Enemy models on the battlefield with a Wounds characteristic of 10+ -
    the printed characteristic (profile.wounds), not the model's remaining
    wounds. A damaged Battlewagon is still a 10+ Wounds model."""
    return [
        t for t in ctx.tokens
        if t.squad is not None and t.profile is not None
        and t.squad.owner != ctx.player
        and t.profile.wounds >= BRING_IT_DOWN_WOUNDS
    ]


def _bring_it_down(ctx):
    """BRING IT DOWN, Tactical half: 5 VP for each enemy model with Wounds 10+
    destroyed this turn, MAX 5 VP.

    Written as the general per-model formula with the cap applied on top rather
    than as "5 if any" - the card prints both halves, and the FIXED variant
    (ignored here per the user) is the same formula with a different rate, so
    this reads correctly if it is ever added.

    Counts MODELS, not units: a Battlewagon squadron losing two hulls in one
    turn destroys two 10+ Wounds models, which is why main.py feeds this from
    the per-model death sweep rather than from record_destroyed_squad()."""
    killed = sum(
        1 for m in ctx.destroyed_this_turn
        if getattr(m, "profile", None) is not None
        and m.squad is not None and m.squad.owner != ctx.player
        and m.profile.wounds >= BRING_IT_DOWN_WOUNDS
    )
    return min(BRING_IT_DOWN_MAX_VP, killed * BRING_IT_DOWN_VP_PER_MODEL)


def _bring_it_down_when_drawn(ctx):
    """"WHEN DRAWN: If no enemy models with a Wounds characteristic of 10+ are
    on the battlefield, you may discard and draw a new Secondary Mission." """
    return not _big_enemy_models(ctx)


CENTRE_GROUND = SecondaryMissionCard(
    key="centre_ground",
    name="Centre Ground",
    text=(
        "End of your turn. 5VP if one or more friendly units (excl. AIRCRAFT and "
        "battle-shocked units) are within 3\" of the centre of the battlefield while no "
        "enemy units are within 6\" of that centre. 3VP if instead no enemy units are "
        "within 3\" of that centre."
    ),
    timing=TIMING_END_OF_YOUR_TURN,
    score=_centre_ground,
)

BRING_IT_DOWN = SecondaryMissionCard(
    key="bring_it_down",
    name="Bring It Down",
    text=(
        "End of a turn. 5VP for each enemy model with a Wounds characteristic of 10+ "
        "that is destroyed this turn (max 5VP). When drawn: if no enemy models with a "
        "Wounds characteristic of 10+ are on the battlefield, you may discard this and "
        "draw a new Secondary Mission."
    ),
    timing=TIMING_END_OF_ANY_TURN,
    score=_bring_it_down,
    when_drawn_may_redraw=_bring_it_down_when_drawn,
)

def _big_enemy_units(ctx):
    """Enemy units with a Starting Strength of 13+ still on the battlefield.

    Starting Strength is the unit's model count at the start of the battle
    (`squad.starting_model_count`), NOT its current one - a 20-model Boyz mob
    down to three models is still a Starting Strength 22 unit. For an attached
    unit (19.01) that count is re-derived from the merged components, so a
    Farseer + Warlock Conclave + Guardian Defenders unit counts as one unit of
    14, which is what makes it qualify."""
    return [
        sq for sq in ctx.enemy_squads()
        if sq.starting_model_count >= GRIEVOUS_BLOW_STARTING_STRENGTH
    ]


def _grievous_blow(ctx):
    """A GRIEVOUS BLOW, Tactical half: 5 VP for each enemy unit with a Starting
    Strength of 13+ destroyed this turn, MAX 5 VP.

    Counts UNITS, where Bring It Down counts MODELS - the two cards look alike
    and are deliberately fed from two different hooks in main.py's death sweep
    for exactly that reason."""
    killed = sum(
        1 for sq in ctx.destroyed_squads_this_turn
        if sq.owner != ctx.player
        and sq.starting_model_count >= GRIEVOUS_BLOW_STARTING_STRENGTH
    )
    return min(GRIEVOUS_BLOW_MAX_VP, killed * GRIEVOUS_BLOW_VP_PER_UNIT)


def _grievous_blow_when_drawn(ctx):
    """"WHEN DRAWN: If no enemy units with a Starting Strength of 13+ are on
    the battlefield, you may discard and draw a new Secondary Mission."

    Not a rare case: measured across the four army lists, the T'au roster has
    NO unit of Starting Strength 13+ at all, so against them this card is dead
    from the moment it is drawn - which is precisely what the clause exists
    for."""
    return not _big_enemy_units(ctx)


def _is_character(model):
    profile = getattr(model, "profile", None)
    return bool(profile is not None and getattr(profile, "character", False))


def _assassination(ctx):
    """ASSASSINATION, Tactical half: 5 VP if one or more enemy CHARACTER models
    were destroyed this turn, OR 5 VP if all enemy CHARACTER models have been
    destroyed during the battle.

    Both branches print the same 5 VP, so they are alternatives rather than
    tiers - the second is a catch-up clause for the turn AFTER you finished
    them off, when the first no longer applies.

    "All destroyed" is deliberately NOT "none on the battlefield": a character
    sitting in Strategic Reserves is off the board and very much alive, so the
    test is "no enemy CHARACTER model is left anywhere" (ctx.all_squads()
    covers board, reserves and transports) AND at least one was actually
    destroyed. Without that second half an opponent who never fielded a
    character at all would satisfy the clause vacuously, every single turn."""
    killed_this_turn = any(
        _is_character(m) for m in ctx.destroyed_this_turn
        if m.squad is not None and m.squad.owner != ctx.player
    )
    if killed_this_turn:
        return ASSASSINATION_VP
    ever_killed = bool(ctx.destroyed_characters_this_battle)
    none_left = not any(_is_character(m) for m in ctx.living_enemy_models())
    if ever_killed and none_left:
        return ASSASSINATION_VP
    return 0


def _tempting_target_on_draw(ctx):
    """"WHEN DRAWN: Your opponent selects one objective (excl. home objectives)
    within No Man's Land to be your tempting target."

    The opponent is the AI, and the user supplied the rule so it needs no API
    call: "Einfach deterministisch, eines der Objectives, die die KI
    kontrolliert. Wenn sie keins kontrolliert, dann das, was am weitesten weg
    von meiner Aufstellungszone ist."

    Both branches are a deliberately UNKIND choice, which is the point of the
    card - it names a place you do not already hold, or one as far from home as
    the board allows. Ties break on the objective's name so the same board
    always yields the same target (a card whose target flickers between two
    equally-good objectives would be unplayable)."""
    candidates = no_mans_land_objectives(ctx)
    if not candidates:
        return None
    held_by_opponent = [o for o in candidates if o.controlled_by == ctx.opponent]
    if held_by_opponent:
        return sorted(held_by_opponent, key=lambda o: o.name)[0]
    my_zones = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    if not my_zones:
        return sorted(candidates, key=lambda o: o.name)[0]

    def distance_from_home(objective):
        cx, cy = objective_centre(objective)
        return min(zone_distance(z, cx, cy) for z in my_zones)

    # -distance first, then name: max() alone would pick whichever of two
    # equidistant objectives happens to be listed first by the map.
    return sorted(candidates, key=lambda o: (-distance_from_home(o), o.name))[0]


def _tempting_target(ctx):
    """"You control your tempting target." - rule 14.02's controlled_by, read
    on the objective the opponent named when this card was drawn."""
    target = ctx.card_state.get("objective")
    if target is None:
        return 0
    return TEMPTING_TARGET_VP if target.controlled_by == ctx.player else 0


def _tempting_target_detail(ctx):
    target = ctx.card_state.get("objective")
    if target is None:
        return "No target - this map has no No Man's Land objective."
    holder = target.controlled_by or "nobody"
    return f"Target: {target.name} (held by {holder})"


A_TEMPTING_TARGET = SecondaryMissionCard(
    key="a_tempting_target",
    name="A Tempting Target",
    text=(
        "End of your turn. 5VP if you control your tempting target - one No Man's Land "
        "objective (excluding home objectives) chosen by your opponent when this card "
        "was drawn."
    ),
    timing=TIMING_END_OF_YOUR_TURN,
    score=_tempting_target,
    on_draw=_tempting_target_on_draw,
    detail=_tempting_target_detail,
)

# "north"/"south"/"west"/"east" are just labels for the four board edges; the
# board has no facing of its own. What matters is which two are OPPOSITE, and
# the card says it outright: "Opposite battlefield edges are the ones that run
# parallel to each other."
EDGE_NORTH, EDGE_SOUTH, EDGE_WEST, EDGE_EAST = "north", "south", "west", "east"
OPPOSITE_EDGE_PAIRS = ((EDGE_NORTH, EDGE_SOUTH), (EDGE_WEST, EDGE_EAST))


def model_distance_to_edges(model):
    """Base-EDGE distance from a model to each of the four board edges."""
    width, height = config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN
    r = model.radius_in
    return {
        EDGE_NORTH: max(0.0, model.y_in - r),
        EDGE_SOUTH: max(0.0, height - model.y_in - r),
        EDGE_WEST: max(0.0, model.x_in - r),
        EDGE_EAST: max(0.0, width - model.x_in - r),
    }


def unit_edges_within(squad, range_in=None):
    """Which board edges this unit is within `range_in` of.

    Unit-level and permissive, matching how Centre Ground reads the same
    "units ... are within X of Y" shape: ANY model close enough puts the unit
    at that edge. (Contrast Behind Enemy Lines' "wholly within", which is the
    strict form and says so.)"""
    if range_in is None:
        range_in = OUTFLANK_EDGE_RANGE_IN
    edges = set()
    for model in squad.models:
        for edge, distance in model_distance_to_edges(model).items():
            if distance <= range_in:
                edges.add(edge)
    return edges


def _outflank_units(ctx):
    """[(squad, edges, in_my_territory), ...] for every friendly unit that is
    at a board edge at all."""
    out = []
    for squad in ctx.friendly_squads():
        if squad.battle_shocked or not squad.models:
            continue
        edges = unit_edges_within(squad)
        if not edges:
            continue
        # "not within your territory" - read the same way Beacon's "outside
        # your territory" is: NO model of the unit inside your own half.
        inside = any(in_own_territory(ctx, m.x_in, m.y_in) for m in squad.models)
        out.append((squad, edges, inside))
    return out


def _outflank(ctx):
    """OUTFLANK.

    3 VP: one or more friendly units within 6" of one or more battlefield
    edges and not within your territory.

    5 VP: two or more friendly units within 6" of OPPOSITE battlefield edges,
    with at least one of those units not within your territory.

    Note what differs between the tiers, because it is easy to flatten: the
    3 VP tier needs THE unit out of your territory, while the 5 VP tier needs
    only ONE OF THE PAIR out of it. So the richer tier is not simply the
    poorer one twice - a unit pinned in your own half can still be half of it.
    """
    candidates = _outflank_units(ctx)
    for first_edge, second_edge in OPPOSITE_EDGE_PAIRS:
        at_first = [entry for entry in candidates if first_edge in entry[1]]
        at_second = [entry for entry in candidates if second_edge in entry[1]]
        for squad_a, _edges_a, inside_a in at_first:
            for squad_b, _edges_b, inside_b in at_second:
                if squad_a is squad_b:
                    continue  # "two or more units", not one unit on a narrow board
                if not inside_a or not inside_b:
                    return OUTFLANK_OPPOSITE_EDGES_VP
    if any(not inside for _squad, _edges, inside in candidates):
        return OUTFLANK_ONE_EDGE_VP
    return 0


def _outflank_detail(ctx):
    candidates = _outflank_units(ctx)
    outside = [sq.name for sq, _e, inside in candidates if not inside]
    if not candidates:
        return "No unit is within 6\" of a battlefield edge."
    return (f"At an edge: {len(candidates)} unit(s); outside your territory: "
            f"{', '.join(outside) if outside else 'none'}")


def _overwhelming_force(ctx):
    """OVERWHELMING FORCE: 3 VP for each enemy unit that STARTED THE TURN
    within range of one or more objectives and is destroyed, max 5.

    The qualifier is about where the unit was at the START of the turn, not
    where it died - so it cannot be read off the board when the card is
    scored, and it cannot be reconstructed afterwards either (the unit is
    gone). It needs a snapshot taken at the top of every turn; the controller
    keeps one and hands it over as `on_objective_at_turn_start`."""
    marked = ctx.on_objective_at_turn_start
    killed = sum(1 for sq in ctx.destroyed_squads_this_turn
                 if sq.owner != ctx.player and id(sq) in marked)
    return min(OVERWHELMING_FORCE_MAX_VP, killed * OVERWHELMING_FORCE_VP_PER_UNIT)


def _secure_no_mans_land(ctx):
    """SECURE NO MAN'S LAND: 5 VP for controlling two or more objectives within
    No Man's Land.

    "(excl. your home objective)" is belt and braces here: a home objective
    sits inside a deployment zone and so is never in No Man's Land to begin
    with. no_mans_land_objectives() already excludes every home objective by
    geometry, which is why this reads as one line."""
    held = sum(1 for o in no_mans_land_objectives(ctx) if o.controlled_by == ctx.player)
    return SECURE_NO_MANS_LAND_VP if held >= SECURE_NO_MANS_LAND_NEEDED else 0


def _secure_no_mans_land_detail(ctx):
    objectives = no_mans_land_objectives(ctx)
    held = [o.name for o in objectives if o.controlled_by == ctx.player]
    return (f"No Man's Land: holding {len(held)} of {len(objectives)} "
            f"(need {SECURE_NO_MANS_LAND_NEEDED})")


def plunderable_areas(ctx):
    """Terrain areas that are NOT within the card player's own territory.

    "One unit within a terrain area not within your territory" - the qualifier
    attaches to the terrain AREA, not to the unit: you plunder ground that is
    not yours. Measured at the area's centre, the same way an objective is
    classified as home or not."""
    out = []
    for area in ctx.terrain_areas:
        min_x, min_y, max_x, max_y = area.bounding_box
        cx, cy = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0
        if not in_own_territory(ctx, cx, cy):
            out.append(area)
    return out


def _area_label(area, index):
    min_x, min_y, max_x, max_y = area.bounding_box
    return f"Terrain area {index + 1} at ({(min_x + max_x) / 2:.0f}, {(min_y + max_y) / 2:.0f})"


def plunder_targets_for(squad, ctx):
    """The terrain areas this unit is standing in and may plunder."""
    return [(area, index) for index, area in enumerate(ctx.terrain_areas)
            if area in plunderable_areas(ctx)
            and any(area.overlaps_model(m) for m in squad.models)]


def plunder_units(squad, ctx):
    return squad.owner == ctx.player and bool(plunder_targets_for(squad, ctx))


def plunder_use_limit(started, squad, target, ctx):
    """"USE LIMIT: Once per turn." - one Plunder action in the whole turn, not
    one per unit. Contrast Cleanse, whose limit is unlimited-but-one-per-
    objective."""
    return not any(s.definition.key == "plunder" for s in started)


def _plunder(ctx):
    """PLUNDER: 5 VP if a terrain area was plundered this turn. One action per
    turn, so this is a yes/no rather than a count."""
    return PLUNDER_VP if ctx.card_state.get("plundered_this_turn") else 0


def _plunder_detail(ctx):
    plundered = ctx.card_state.get("plundered_this_turn") or ()
    if plundered:
        return "A terrain area was plundered this turn."
    return "Nothing plundered this turn. Start the action in your Shooting phase."


def _has_card_in_hand(ctx, key):
    return any(card.key == key for card in ctx.hand)


def _plunder_when_drawn(ctx):
    """"WHEN DRAWN: If you have Cleanse active, you may shuffle this card back
    and draw a new Secondary Mission." - and Cleanse prints the mirror of it.
    Both are live now that both cards exist."""
    return _has_card_in_hand(ctx, "cleanse")


def _no_prisoners(ctx):
    """NO PRISONERS: 2 VP for each enemy unit destroyed this turn, max 5.

    Counts UNITS, so it is fed from the same per-unit hook A Grievous Blow
    uses - that card is the same shape with a Starting Strength filter on top.
    Two units pay 4 and three pay 5, not 6."""
    killed = sum(1 for sq in ctx.destroyed_squads_this_turn if sq.owner != ctx.player)
    return min(NO_PRISONERS_MAX_VP, killed * NO_PRISONERS_VP_PER_UNIT)


def table_quarters():
    """The four table quarters, as (min_x, min_y, max_x, max_y) in inches.

    Split at the battlefield centre on both axes - the plain reading of "table
    quarter", and the only one that works on all three boards here (44x60
    portrait, 60x44 landscape, 30x30 square) without special cases."""
    centre_x, centre_y = board_centre()
    width, height = config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN
    return [
        (0.0, 0.0, centre_x, centre_y),          # NW
        (centre_x, 0.0, width, centre_y),        # NE
        (0.0, centre_y, centre_x, height),       # SW
        (centre_x, centre_y, width, height),     # SE
    ]


def _model_wholly_in_rect(model, rect):
    min_x, min_y, max_x, max_y = rect
    r = model.radius_in
    return (min_x <= model.x_in - r and model.x_in + r <= max_x
            and min_y <= model.y_in - r and model.y_in + r <= max_y)


def unit_has_presence_in(squad, rect, ctx):
    """Engage on All Fronts' own definition of "presence":

        "You have a presence in a table quarter if one or more friendly units
        (excl. AIRCRAFT & battle-shocked) are wholly within it and not within
        6" of the battlefield centre."

    Two conditions on the SAME unit, and the second is the one that makes the
    card hard: a unit parked on the middle of the board sits in a quarter but
    is too close to the centre to count, so spreading out is not enough - you
    have to spread out AWAY from the middle.

    "Wholly within it" is measured per model base, so a unit straddling a
    centre line is in neither quarter."""
    if squad.battle_shocked or not squad.models:
        return False
    if not all(_model_wholly_in_rect(m, rect) for m in squad.models):
        return False
    centre_x, centre_y = board_centre()
    return all(model_distance_to_point(m, centre_x, centre_y) > ENGAGE_CENTRE_EXCLUSION_IN
               for m in squad.models)


def quarters_with_presence(ctx):
    quarters = table_quarters()
    friendly = ctx.friendly_squads()
    return [rect for rect in quarters
            if any(unit_has_presence_in(sq, rect, ctx) for sq in friendly)]


def _engage_on_all_fronts(ctx):
    """ENGAGE ON ALL FRONTS, Tactical half: 3 VP for a presence in three table
    quarters, 5 VP for four."""
    count = len(quarters_with_presence(ctx))
    if count >= 4:
        return ENGAGE_FOUR_QUARTERS_VP
    if count >= 3:
        return ENGAGE_THREE_QUARTERS_VP
    return 0


def _engage_detail(ctx):
    count = len(quarters_with_presence(ctx))
    return f"Presence in {count} of 4 table quarters (3 pays 3 VP, 4 pays 5 VP)"


def expansion_objective_for(ctx, player):
    """A player's EXPANSION OBJECTIVE: the objective nearest their deployment
    zone, home objectives excluded.

    User-supplied definition: "das Objektiv, was an meiner Aufstellungszone am
    naechsten ist, ausser natuerlich das Home-Objektiv."

    Home objectives are excluded by GEOMETRY (they sit inside a deployment
    zone, so their distance would be 0 and one would always win) - the same
    test no_mans_land_objectives() uses, which is why that function supplies
    the candidates here rather than a second name-based filter.

    Ties break on the name so the same board always yields the same objective;
    a card whose target flickers between two equally-near objectives would be
    unplayable."""
    zones = [z for z in ctx.deployment_zones if z.owner == player]
    candidates = no_mans_land_objectives(ctx)
    if not zones or not candidates:
        return None

    def distance(objective):
        cx, cy = objective_centre(objective)
        return min(zone_distance(z, cx, cy) for z in zones)

    return sorted(candidates, key=lambda o: (distance(o), o.name))[0]


def expansion_objectives(ctx):
    """BOTH players' expansion objectives - one each, deduplicated.

    Forward Position says "EACH expansion objective", so it needs the whole
    set, not just the card player's own. On the two full-size boards that is a
    symmetric pair (map1 Southwest/Northeast, map2 East/West - each the nearest
    to its own owner's zone); on map3, whose only non-home objective is the
    central one, both players' nearest is the SAME objective and the set has
    one member."""
    out = []
    for player in (ctx.player, ctx.opponent):
        objective = expansion_objective_for(ctx, player)
        if objective is not None and not any(o is objective for o in out):
            out.append(objective)
    return out


def enemy_home_objective(ctx):
    """The OPPONENT's home objective - own_home_objective() from the other
    side, so the two cannot disagree about what "home" means."""
    theirs = [z for z in ctx.deployment_zones if z.owner == ctx.opponent]
    for objective in ctx.objectives:
        cx, cy = objective_centre(objective)
        if any(z.contains_point(cx, cy) for z in theirs):
            return objective
    return None


def _forward_position(ctx):
    """FORWARD POSITION: "You control your opponent's home objective and/or
    each expansion objective."

    "and/or" makes the two alternatives, not a pair to be added: either one
    alone pays the single 5 VP. "EACH expansion objective" is all of them, not
    any one - which is what stops the card being trivial on a board with two
    of them."""
    enemy_home = enemy_home_objective(ctx)
    if enemy_home is not None and enemy_home.controlled_by == ctx.player:
        return FORWARD_POSITION_VP
    expansions = expansion_objectives(ctx)
    if expansions and all(o.controlled_by == ctx.player for o in expansions):
        return FORWARD_POSITION_VP
    return 0


def _forward_position_detail(ctx):
    enemy_home = enemy_home_objective(ctx)
    parts = []
    if enemy_home is not None:
        parts.append(f"{enemy_home.name} (enemy home)")
    parts += [o.name for o in expansion_objectives(ctx)]
    return "Either: " + " OR all of: ".join([parts[0], ", ".join(parts[1:])]) if len(parts) > 1 \
        else ("Target: " + parts[0] if parts else "No qualifying objective on this map.")


def own_home_objective(ctx):
    """The card player's OWN home objective: the one inside their deployment
    zone. Derived from geometry, like every other objective classification
    here, so a renamed objective still resolves."""
    mine = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    for objective in ctx.objectives:
        cx, cy = objective_centre(objective)
        if any(z.contains_point(cx, cy) for z in mine):
            return objective
    return None


def unit_wholly_in_no_mans_land(squad, ctx):
    """Every model's whole BASE outside BOTH deployment zones.

    "Wholly within No Man's Land" is the mirror of Behind Enemy Lines' "wholly
    within your opponent's deployment zone", so it gets the same strictness
    from the other side: a base that so much as touches either zone is not in
    No Man's Land. zone_distance() returns 0 inside a zone, so "> radius" reads
    as "the whole base clears it"."""
    zones = list(ctx.deployment_zones)
    if not zones or not squad.models:
        return False
    return all(zone_distance(z, m.x_in, m.y_in) > m.radius_in
               for m in squad.models for z in zones)


def _counts_for_display_of_might(squads, ctx):
    return sum(1 for sq in squads
               if not sq.battle_shocked and unit_wholly_in_no_mans_land(sq, ctx))


def _display_of_might(ctx):
    """DISPLAY OF MIGHT: more friendly than enemy units (excl. AIRCRAFT and
    battle-shocked) wholly within No Man's Land.

    The first card whose VALUE depends on WHICH instant it is scored at, not on
    how well the condition is met: 2 VP at the end of your own turn, 5 VP at
    the end of your opponent's. Same condition, two prices - holding No Man's
    Land through the enemy's turn is the harder half, and that is the whole
    design of the card.

    The "(excl. AIRCRAFT & battle-shocked)" parenthetical is printed after
    "enemy units" but is applied to BOTH counts: it reads as a qualifier on
    what counts as a unit for this card, and the sibling cards phrase the same
    exclusion against their own units. Applying it to both is also the
    stricter reading, so it cannot hand out VP the card did not intend."""
    friendly = _counts_for_display_of_might(ctx.friendly_squads(), ctx)
    enemy = _counts_for_display_of_might(ctx.enemy_squads(), ctx)
    if friendly <= enemy:
        return 0
    if ctx.ending_player == ctx.player:
        return DISPLAY_OF_MIGHT_YOUR_TURN_VP
    return DISPLAY_OF_MIGHT_OPPONENT_TURN_VP


def _display_of_might_detail(ctx):
    friendly = _counts_for_display_of_might(ctx.friendly_squads(), ctx)
    enemy = _counts_for_display_of_might(ctx.enemy_squads(), ctx)
    return f"No Man's Land: {friendly} of yours vs {enemy} enemy (2 VP your turn, 5 VP theirs)"


def _defend_stronghold(ctx):
    """DEFEND STRONGHOLD: 3 VP for controlling your home objective, 5 VP if no
    enemy units are in your deployment zone as well.

    "no enemy units are WITHIN your deployment zone" - not "wholly within".
    A single enemy model with a toe inside breaks it, which is the opposite
    strictness from Behind Enemy Lines' "wholly within" and is why the two use
    different tests."""
    home = own_home_objective(ctx)
    if home is None or home.controlled_by != ctx.player:
        return 0
    my_zones = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    intruder = any(
        zone_distance(z, m.x_in, m.y_in) <= m.radius_in
        for sq in ctx.enemy_squads() for m in sq.models for z in my_zones
    )
    return (DEFEND_STRONGHOLD_CONTROL_VP if intruder
            else DEFEND_STRONGHOLD_CLEAR_VP)


def _defend_stronghold_when_drawn(ctx):
    """"WHEN DRAWN: During the first battle round, shuffle this card back and
    draw a new Secondary Mission."

    Note what is NOT there: no "you may". Behind Enemy Lines prints the same
    sentence WITH it, so that one is an offer and this one is an instruction -
    see SecondaryMissionCard.when_drawn_is_mandatory."""
    return ctx.battle_round is not None and ctx.battle_round < DEFEND_STRONGHOLD_FROM_ROUND


def _defend_stronghold_detail(ctx):
    home = own_home_objective(ctx)
    if home is None:
        return "This map has no home objective for you."
    holder = home.controlled_by or "nobody"
    return f"Your home objective: {home.name} (held by {holder})"


def _non_home_objectives(ctx):
    """Every objective except the card player's OWN home one.

    Cleanse says "excl. your home objective" - singular and possessive, so the
    ENEMY's home objective is a legal target. Derived from geometry like
    no_mans_land_objectives(): a home objective is one inside its owner's
    deployment zone, so "mine" is one inside MY zone."""
    mine = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    out = []
    for objective in ctx.objectives:
        cx, cy = objective_centre(objective)
        if not any(z.contains_point(cx, cy) for z in mine):
            out.append(objective)
    return out


def cleanse_units(squad, ctx):
    """Cleanse's UNITS line: "One friendly unit within range of an objective
    (excl. your home objective)"."""
    if squad.owner != ctx.player:
        return False
    return bool(cleanse_targets_for(squad, ctx))


def cleanse_targets_for(squad, ctx):
    """The objectives this unit could Cleanse - within range, and not the
    player's own home objective."""
    return [o for o in _non_home_objectives(ctx)
            if is_within_range_of_objective(squad, [o])]


def cleanse_use_limit(started, squad, target, ctx):
    """"Unlimited. Each unit must be within range of a different objective."

    Unlimited in COUNT, but no two units may work the same objective - so the
    limit is really a uniqueness rule on the TARGET, not a cap on the number
    of actions."""
    if target is None:
        return False
    return not any(s.target is target for s in started if not s.broken)


def cleanse_completes(state, ctx):
    """"End of your turn, if that unit controls that objective."

    "That unit controls" is read as the unit being within range of the
    objective AND its owner holding it (14.02) - the same live pair Burden of
    Trust's guards use, and the same reading that makes "controls" mean
    something a single unit can be responsible for."""
    objective = state.target
    if objective is None or not state.squad.models:
        return False
    if objective.controlled_by != state.squad.owner:
        return False
    return is_within_range_of_objective(state.squad, [objective])


# "EFFECT: That objective is cleansed by your army." - deliberately no
# callback. Completing the action IS the effect: ActionController's
# resolve_end_of_turn() returns the completed states, and the objectives named
# by those states are exactly the cleansed ones. A side-channel that appended
# to some list would be a second record of the same fact, free to disagree with
# the first.
CLEANSE_EFFECT = None


def _cleanse(ctx):
    """CLEANSE, Tactical half: 2 VP if one objective was cleansed this turn,
    5 VP if two or more were."""
    count = len(ctx.card_state.get("cleansed_this_turn") or ())
    if count >= 2:
        return CLEANSE_MANY_VP
    if count == 1:
        return CLEANSE_ONE_VP
    return 0


def _cleanse_when_drawn(ctx):
    """"WHEN DRAWN: If you have Plunder active, you may shuffle this card back
    and draw a new Secondary Mission."

    "Active" = in hand. This was a documented no-op while Plunder did not
    exist; it is live now, and Plunder prints the mirror of it - each offers
    to step aside for the other, so a hand never has to carry both Objective
    Action cards at once."""
    return _has_card_in_hand(ctx, "plunder")


def _cleanse_detail(ctx):
    cleansed = ctx.card_state.get("cleansed_this_turn") or ()
    if not cleansed:
        return "Nothing cleansed this turn. Start the action in your Shooting phase."
    return "Cleansed this turn: " + ", ".join(o.name for o in cleansed)


def _behind_enemy_lines(ctx):
    """BEHIND ENEMY LINES, Tactical half: 3 VP for each friendly unit (excl.
    AIRCRAFT and battle-shocked) WHOLLY within your opponent's deployment zone,
    max 5 VP.

    "Wholly within" is rule 03.01's own phrase and gets 03.01's own test:
    every model's whole BASE inside the zone (DeploymentZone.contains_circle),
    not just its centre. Reused rather than re-derived - deployment already
    owns that definition.

    Because 3 VP each caps at 5, one unit pays 3 and two or more pay 5. Written
    as the per-unit formula with the cap on top so the numbers stay readable
    against the printed card."""
    enemy_zones = [z for z in ctx.deployment_zones if z.owner == ctx.opponent]
    if not enemy_zones:
        return 0
    qualifying = 0
    for squad in ctx.friendly_squads():
        if squad.battle_shocked:
            continue
        if all(any(z.contains_circle(m.x_in, m.y_in, m.radius_in) for z in enemy_zones)
               for m in squad.models):
            qualifying += 1
    return min(BEHIND_ENEMY_LINES_MAX_VP, qualifying * BEHIND_ENEMY_LINES_VP_PER_UNIT)


def _behind_enemy_lines_when_drawn(ctx):
    """"WHEN DRAWN: During the first battle round, you may shuffle this card
    back and draw a new Secondary Mission."

    The only condition is the ROUND - unlike Bring It Down and A Grievous Blow,
    whose clauses ask about the enemy army. Nothing about the board makes this
    card dead; it is simply a slow one, and the clause exists so a round-1 draw
    is not a wasted card."""
    return ctx.battle_round == 1


def _guard_assignments(ctx):
    """[(objective, squad), ...] currently on duty for Burden of Trust."""
    guards = ctx.card_state.get("guards") or {}
    out = []
    for objective in ctx.objectives:
        squad = guards.get(id(objective))
        if squad is not None:
            out.append((objective, squad))
    return out


def objective_is_guarded(ctx, objective, squad):
    """"it counts as guarded while that unit stays in range and you control
    it" - both halves, checked live.

    "In range" is the engine's existing "within range of an objective marker"
    (game/objectives.py's 3", the same number rule 12.08 uses); "you control
    it" is 14.02's controlled_by. A guard that has wandered off, been wiped
    out, or whose objective has been taken stops counting on its own - there is
    no separate bookkeeping to go stale."""
    if squad is None or not squad.models:
        return False
    if objective.controlled_by != ctx.player:
        return False
    return is_within_range_of_objective(squad, [objective])


def _burden_of_trust(ctx):
    """BURDEN OF TRUST, Tactical half: 2 VP for each objective guarded by your
    army, max 5 VP. Three guarded objectives are worth 6 and pay 5."""
    guarded = sum(1 for objective, squad in _guard_assignments(ctx)
                  if objective_is_guarded(ctx, objective, squad))
    return min(BURDEN_OF_TRUST_MAX_VP, guarded * BURDEN_OF_TRUST_VP_PER_OBJECTIVE)


def _burden_of_trust_detail(ctx):
    pairs = _guard_assignments(ctx)
    if not pairs:
        return "No objectives guarded."
    parts = []
    for objective, squad in pairs:
        mark = "OK" if objective_is_guarded(ctx, objective, squad) else "lapsed"
        parts.append(f"{objective.name}: {squad.name} ({mark})")
    return "Guards - " + "; ".join(parts)


def _beacon_candidates(ctx):
    """"Choose one friendly unit on the battlefield (or embarked in a
    TRANSPORT) as your beacon unit."

    Board units plus embarked ones - and deliberately NOT units in Strategic
    Reserves, which the card does not offer. Sorted by name so the option list
    is stable between frames."""
    on_board = [sq for sq in _live_squads(ctx.tokens) if sq.owner == ctx.player]
    embarked = [sq for sq in ctx.embarked_squads
                if sq is not None and sq.models and sq.owner == ctx.player]
    seen, out = set(), []
    for squad in on_board + embarked:
        if id(squad) not in seen:
            seen.add(id(squad))
            out.append(squad)
    return sorted(out, key=lambda sq: sq.name)


def _beacon(ctx):
    """BEACON, Tactical half: 3 VP if your beacon unit is on the battlefield
    and outside your deployment zone, 5 VP if it is outside your territory.

    The 5 VP condition is strictly stricter (your territory contains your
    deployment zone), so the better tier is tested first, exactly like Centre
    Ground's two bands.

    "On the battlefield" is load-bearing on both branches: a beacon still
    sitting inside its transport, or destroyed, scores nothing at all - which
    is checked here by asking the BOARD (ctx.tokens), not the all-squads list
    that includes transports and reserves.

    "Outside" a region means NO model of the unit is inside it - the unit as a
    whole has to have left, not merely poked a toe out."""
    beacon = ctx.card_state.get("objective")
    if beacon is None:
        return 0
    on_board = {id(sq) for sq in _live_squads(ctx.tokens)}
    if id(beacon) not in on_board or not beacon.models:
        return 0
    my_zones = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    if not any(in_own_territory(ctx, m.x_in, m.y_in) for m in beacon.models):
        return BEACON_OUTSIDE_TERRITORY_VP
    if not any(z.contains_point(m.x_in, m.y_in) for z in my_zones for m in beacon.models):
        return BEACON_OUTSIDE_DEPLOYMENT_VP
    return 0


def _beacon_detail(ctx):
    beacon = ctx.card_state.get("objective")
    if beacon is None:
        return "No beacon unit chosen."
    return f"Beacon: {beacon.name}"


BEACON = SecondaryMissionCard(
    key="beacon",
    name="Beacon",
    text=(
        "End of your opponent's turn in the final battle round. 3VP if your beacon unit "
        "is on the battlefield and outside your deployment zone, or 5VP if it is outside "
        "your territory (your half of the battlefield). The beacon unit is chosen when "
        "this card is drawn."
    ),
    timing=TIMING_END_OF_OPPONENT_TURN_FINAL_ROUND,
    score=_beacon,
    draw_choices=lambda ctx: [(sq.name, sq) for sq in _beacon_candidates(ctx)],
    draw_prompt="Beacon: choose one of your units on the battlefield (or embarked) "
                "as your beacon unit.",
    detail=_beacon_detail,
)

NO_PRISONERS = SecondaryMissionCard(
    key="no_prisoners",
    name="No Prisoners",
    text=(
        "End of a turn. 2VP for each enemy unit destroyed this turn (max 5VP)."
    ),
    timing=TIMING_END_OF_ANY_TURN,
    score=_no_prisoners,
)

OUTFLANK = SecondaryMissionCard(
    key="outflank",
    name="Outflank",
    text=(
        "End of your turn. 3VP if one or more friendly units (excl. AIRCRAFT and "
        "battle-shocked) are within 6\" of one or more battlefield edges and not within "
        "your territory, or 5VP if two or more such units are within 6\" of OPPOSITE "
        "battlefield edges with at least one of them not within your territory. Opposite "
        "edges are the ones that run parallel to each other."
    ),
    timing=TIMING_END_OF_YOUR_TURN,
    score=_outflank,
    detail=_outflank_detail,
)

ENGAGE_ON_ALL_FRONTS = SecondaryMissionCard(
    key="engage_on_all_fronts",
    name="Engage on All Fronts",
    text=(
        "End of your turn. 3VP for a presence in three table quarters, or 5VP in four. "
        "You have a presence in a table quarter if one or more friendly units (excl. "
        "AIRCRAFT and battle-shocked) are wholly within it and not within 6\" of the "
        "battlefield centre."
    ),
    # The card prints no timing badge - its slot carries FIXED / TACTICAL
    # instead, where every other card here carries the instant. Confirmed by
    # the user: "engage on all fronts triggered am Ende des Zuges", i.e. the
    # same end-of-your-turn instant every other board-state Tactical card in
    # this deck uses.
    timing=TIMING_END_OF_YOUR_TURN,
    score=_engage_on_all_fronts,
    detail=_engage_detail,
)

FORWARD_POSITION = SecondaryMissionCard(
    key="forward_position",
    name="Forward Position",
    text=(
        "End of your turn. 5VP if you control your opponent's home objective and/or "
        "each expansion objective (the objective nearest each player's own deployment "
        "zone, home objectives aside). When drawn during the first battle round you may "
        "shuffle this card back and draw a new Secondary Mission."
    ),
    timing=TIMING_END_OF_YOUR_TURN,
    score=_forward_position,
    when_drawn_may_redraw=_behind_enemy_lines_when_drawn,  # same clause, same wording
    when_drawn_shuffles_back=True,
    detail=_forward_position_detail,
)

DEFEND_STRONGHOLD = SecondaryMissionCard(
    key="defend_stronghold",
    name="Defend Stronghold",
    text=(
        "From the second battle round, at the end of your opponent's turn in the final "
        "battle round. 3VP if you control your home objective, or 5VP if you control it "
        "and no enemy units are within your deployment zone. When drawn during the first "
        "battle round it is shuffled back and a new Secondary Mission is drawn."
    ),
    timing=TIMING_END_OF_OPPONENT_TURN_FINAL_ROUND,
    score=_defend_stronghold,
    when_drawn_may_redraw=_defend_stronghold_when_drawn,
    when_drawn_shuffles_back=True,
    # No "you may" on this card's clause, unlike Behind Enemy Lines' - so it is
    # resolved without asking.
    when_drawn_is_mandatory=True,
    min_battle_round=DEFEND_STRONGHOLD_FROM_ROUND,
    detail=_defend_stronghold_detail,
)

DISPLAY_OF_MIGHT = SecondaryMissionCard(
    key="display_of_might",
    name="Display of Might",
    text=(
        "End of a turn. 2VP at the end of your own turn, or 5VP at the end of your "
        "opponent's turn, if there are more friendly units than enemy units (excl. "
        "AIRCRAFT and battle-shocked) wholly within No Man's Land."
    ),
    timing=TIMING_END_OF_ANY_TURN,
    score=_display_of_might,
    detail=_display_of_might_detail,
)

PLUNDER_ACTION = ActionDefinition(
    key="plunder",
    name="Plunder",
    starts=PHASE_SHOOTING,           # "STARTS: Your Shooting phase."
    units=plunder_units,
    # "COMPLETES: Immediately" - so there is no later condition to test, and
    # nothing that happens afterwards can take it back.
    completes=lambda state, ctx: True,
    completes_immediately=True,
    effect=None,                     # completing IS the effect; see CLEANSE_EFFECT
    use_limit=plunder_use_limit,
    target_options=lambda squad, ctx: [
        (_area_label(area, index), area) for area, index in plunder_targets_for(squad, ctx)
    ],
)

PLUNDER = SecondaryMissionCard(
    key="plunder",
    name="Plunder",
    text=(
        "End of your turn. 5VP if a terrain area was plundered this turn. Plunder is an "
        "OBJECTIVE ACTION started once per turn in your Shooting phase by a unit standing "
        "in a terrain area outside your own territory; it completes immediately."
    ),
    timing=TIMING_END_OF_YOUR_TURN,
    score=_plunder,
    when_drawn_may_redraw=_plunder_when_drawn,
    when_drawn_shuffles_back=True,
    detail=_plunder_detail,
    requires_action=True,
    action=PLUNDER_ACTION,
)

OVERWHELMING_FORCE = SecondaryMissionCard(
    key="overwhelming_force",
    name="Overwhelming Force",
    text=(
        "End of a turn. 3VP for each enemy unit that started the turn within range of one "
        "or more objectives and is destroyed this turn (max 5VP)."
    ),
    timing=TIMING_END_OF_ANY_TURN,
    score=_overwhelming_force,
)

SECURE_NO_MANS_LAND = SecondaryMissionCard(
    key="secure_no_mans_land",
    name="Secure No Man's Land",
    text=(
        "End of your turn. 5VP if you control two or more objectives within No Man's Land "
        "(excluding your home objective)."
    ),
    timing=TIMING_END_OF_YOUR_TURN,
    score=_secure_no_mans_land,
    detail=_secure_no_mans_land_detail,
)

CLEANSE_ACTION = ActionDefinition(
    key="cleanse",
    name="Cleanse",
    starts=PHASE_SHOOTING,          # "STARTS: Your Shooting phase."
    units=cleanse_units,
    completes=cleanse_completes,
    effect=CLEANSE_EFFECT,
    use_limit=cleanse_use_limit,
    target_options=lambda squad, ctx: [(o.name, o) for o in cleanse_targets_for(squad, ctx)],
)

CLEANSE = SecondaryMissionCard(
    key="cleanse",
    name="Cleanse",
    text=(
        "End of your turn. 2VP if one objective was cleansed this turn, or 5VP if two or "
        "more were. Cleanse is an OBJECTIVE ACTION started in your Shooting phase by a "
        "unit within range of an objective other than your home objective; it completes "
        "at the end of your turn if that unit still controls that objective."
    ),
    timing=TIMING_END_OF_YOUR_TURN,
    score=_cleanse,
    when_drawn_may_redraw=_cleanse_when_drawn,
    when_drawn_shuffles_back=True,
    detail=_cleanse_detail,
    # The first card that needs rule 16.01 at all - see game/actions.py.
    requires_action=True,
    action=CLEANSE_ACTION,
)

BEHIND_ENEMY_LINES = SecondaryMissionCard(
    key="behind_enemy_lines",
    name="Behind Enemy Lines",
    text=(
        "End of your turn. 3VP for each friendly unit (excl. AIRCRAFT and battle-shocked) "
        "wholly within your opponent's deployment zone (max 5VP). When drawn: during the "
        "first battle round you may shuffle this card back and draw a new Secondary "
        "Mission."
    ),
    timing=TIMING_END_OF_YOUR_TURN,
    score=_behind_enemy_lines,
    when_drawn_may_redraw=_behind_enemy_lines_when_drawn,
    # "SHUFFLE this card back", not "discard" - it returns to the deck and can
    # be drawn again later. The other two redraw clauses discard.
    when_drawn_shuffles_back=True,
)

BURDEN_OF_TRUST = SecondaryMissionCard(
    key="burden_of_trust",
    name="Burden of Trust",
    text=(
        "End of your opponent's turn in the final battle round. 2VP for each objective "
        "guarded by your army (max 5VP). When drawn and at the start of each of your "
        "turns you may pick one friendly unit to guard each objective; it counts as "
        "guarded until your next turn, while that unit stays in range and you control it."
    ),
    timing=TIMING_END_OF_OPPONENT_TURN_FINAL_ROUND,
    score=_burden_of_trust,
    detail=_burden_of_trust_detail,
)

A_GRIEVOUS_BLOW = SecondaryMissionCard(
    key="a_grievous_blow",
    name="A Grievous Blow",
    text=(
        "End of a turn. 5VP for each enemy unit with a Starting Strength of 13+ that is "
        "destroyed this turn (max 5VP). When drawn: if no enemy units with a Starting "
        "Strength of 13+ are on the battlefield, you may discard this and draw a new "
        "Secondary Mission."
    ),
    timing=TIMING_END_OF_ANY_TURN,
    score=_grievous_blow,
    when_drawn_may_redraw=_grievous_blow_when_drawn,
)

ASSASSINATION = SecondaryMissionCard(
    key="assassination",
    name="Assassination",
    text=(
        "End of a turn. 5VP if one or more enemy CHARACTER models were destroyed this "
        "turn, or 5VP if all enemy CHARACTER models have been destroyed during the "
        "battle."
    ),
    timing=TIMING_END_OF_ANY_TURN,
    score=_assassination,
)

# The deck, in a fixed listed order - shuffled per battle by the controller.
# A new card is one entry here plus its predicate above; nothing else changes.
#
# BURDEN_OF_TRUST is deliberately NOT in this list. User: "lass Burden of Trust
# erstmal weg" - the card's own economy did not sit right (you re-commit guards
# every turn, but only the standing at the end of the battle pays, so four of
# the five commitments are invisible). Everything it needs is still here and
# still tested - the card object, its guard assignment window, the board-click
# picking it introduced - so putting it back is adding one name below.
ALL_CARDS = [CENTRE_GROUND, BRING_IT_DOWN, A_GRIEVOUS_BLOW, ASSASSINATION,
             A_TEMPTING_TARGET, BEACON, BEHIND_ENEMY_LINES, CLEANSE,
             DEFEND_STRONGHOLD, DISPLAY_OF_MIGHT, ENGAGE_ON_ALL_FRONTS,
             FORWARD_POSITION, NO_PRISONERS, OUTFLANK, OVERWHELMING_FORCE,
             PLUNDER, SECURE_NO_MANS_LAND]


def deck_players():
    """Which players run the card deck instead of the standard Secondary.
    Read from config at call time (never imported by value), so the headless
    harnesses' `config.SECONDARY_MISSION_CARD_PLAYERS = ()` really takes."""
    return tuple(config.SECONDARY_MISSION_CARD_PLAYERS)


class SecondaryMissionController:
    """The deck, the hand, and every prompt the two of them generate.

    Deliberately ONE controller rather than one per card: the interesting state
    (which cards are left, what is in hand, how much of this round's 15 VP is
    spent, whether this round's bonus CP is still available) is shared across
    all cards, and every prompt is a choice BETWEEN cards. A per-card
    controller would have to ask this object everything anyway.
    """

    def __init__(self, player="Player 1", mission_controller=None, command_points=None,
                 decision_manager=None, turn_tracker=None, game_log=None,
                 draw_overlay=None, cards=None, rng=None):
        self.player = player
        self.mission_controller = mission_controller
        self.command_points = command_points
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.draw_overlay = draw_overlay
        self._rng = rng if rng is not None else random.Random()
        # Shuffled once, here: the battle's deck order is fixed from the start,
        # which is what makes "each card once per battle" checkable.
        self.deck = list(cards if cards is not None else ALL_CARDS)
        self._rng.shuffle(self.deck)
        self.hand = []
        self.discarded = []
        self._unannounced = []  # draws made before draw_overlay existed - see _announce()
        # Per-card scratchpad, keyed by card KEY - see MissionContext.card_state
        # for why it lives here and not on the card objects.
        self.card_state = {}
        # An open "click one of your units on the board" request, or None.
        # {"prompt", "subject", "eligible", "on_pick", "on_skip", "skip_label"}
        # - see request_unit_pick(). This is the one thing in this module the
        # player answers on the BOARD rather than in the decision overlay.
        self.pending_pick = None
        # Which battle round the two cards were last drawn in. The draw hook is
        # reachable from three call sites (the two battle-start paths and every
        # Command phase), so it has to be idempotent by round, not by call.
        self._drawn_round = None
        # The 15 VP/round ledger, lazily reset by sync_battle_round().
        self._scored_round = None
        self._scored_vp_this_round = 0
        # Models destroyed since the last turn boundary - see MissionContext.
        self._destroyed_this_turn = []
        # Whole units wiped out since the last turn boundary, plus the ids
        # already recorded so one unit cannot be counted twice (main.py's death
        # sweep can reach the same emptied squad on several models in a frame,
        # exactly as MissionController.record_destroyed_squad() guards against).
        self._destroyed_squads_this_turn = []
        self._destroyed_squad_ids = set()
        # Enemy CHARACTER models destroyed at any point in the battle. NOT
        # cleared at a turn boundary - Assassination's second branch asks about
        # the whole battle.
        self._destroyed_characters_this_battle = []
        # Overwhelming Force's snapshot - see snapshot_turn_start().
        self._on_objective_at_turn_start = set()
        # Prompt chain state, see begin_end_of_turn()/_ask_next().
        self._pending_scoring = []
        self._asking = False
        # The (card, vp) whose cash-in prompt is on screen right now, or None.
        # Read by offered_now() so the strip can mark exactly the card being
        # asked about - and nothing else.
        self._current_offer = None

    # ------------------------------------------------------------- plumbing

    @property
    def plays_cards(self):
        """False when this player is not on the deck at all (the headless
        harnesses set the config tuple empty), which makes every hook below a
        no-op without main.py needing a condition at each call site."""
        return self.player in deck_players()

    # ------------------------------------------------- click-a-unit picking

    def request_unit_pick(self, prompt, subject, eligible, on_pick,
                          on_skip=None, skip_label="Skip"):
        """Ask the player to pick one of their units by CLICKING IT ON THE
        BOARD, rather than choosing a name from the decision overlay.

        User, about Burden of Trust: "Bei Burden of Trust muss immer links in
        der Spalte das Objective genannt werden, um das es gerade geht, und ich
        muss auf der Map mein Einheit anklicken."

        `subject` is what the left panel names as the thing being decided (the
        objective) - the whole reason this exists is that a bare "pick a unit"
        prompt does not say which objective it is for.

        `eligible` is the set of squads a click may resolve to; a click on
        anything else is ignored rather than guessed at."""
        self.pending_pick = {
            "prompt": prompt,
            "subject": subject,
            "eligible": list(eligible),
            "on_pick": on_pick,
            "on_skip": on_skip,
            "skip_label": skip_label,
        }

    def pick_is_eligible(self, squad):
        pick = self.pending_pick
        return bool(pick) and any(sq is squad for sq in pick["eligible"])

    def choose_picked_unit(self, squad):
        """Resolve an open pick with the clicked squad. Ignores a click on
        anything not eligible - returns whether it took."""
        pick = self.pending_pick
        if not pick or not self.pick_is_eligible(squad):
            return False
        self.pending_pick = None
        pick["on_pick"](squad)
        return True

    def skip_pick(self):
        """The panel's own button: decline this one and move on."""
        pick = self.pending_pick
        if not pick:
            return
        self.pending_pick = None
        if pick["on_skip"] is not None:
            pick["on_skip"]()

    @property
    def is_busy(self):
        """True while this controller still owes the human a prompt. Read by
        main.py's _has_unresolved_declaration() so the phase cannot advance out
        from under an open mission decision."""
        return self._asking or bool(self._pending_scoring) or self.pending_pick is not None

    def sync_battle_round(self, battle_round):
        """Idempotent per-battle-round reset of the 15 VP ledger. Called on
        EVERY phase change, exactly like battle_focus_pool.sync_battle_round()
        - that is what guarantees the reset never depends on catching one exact
        moment."""
        if self._scored_round == battle_round:
            return
        self._scored_round = battle_round
        self._scored_vp_this_round = 0

    def remaining_vp_this_round(self, battle_round=None):
        if battle_round is not None:
            self.sync_battle_round(battle_round)
        return max(0, MAX_SECONDARY_VP_PER_ROUND - self._scored_vp_this_round)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _context(self, ending_player=None, card=None, battle_round=None):
        return MissionContext(
            self.player, tokens=self._tokens(), turn_tracker=self.turn_tracker,
            ending_player=ending_player, destroyed_this_turn=self._destroyed_this_turn,
            objectives=(list(self._objectives_source()) if self._objectives_source else []),
            deployment_zones=(list(self._zones_source()) if self._zones_source else []),
            card_state=(self.card_state.setdefault(card.key, {}) if card is not None else None),
            battle_round=battle_round,
            embarked_squads=(list(self._embarked_source()) if self._embarked_source else []),
            hand=list(self.hand),
            terrain_areas=(list(self._terrain_source()) if self._terrain_source else []),
            on_objective_at_turn_start=self._on_objective_at_turn_start,
            destroyed_squads_this_turn=self._destroyed_squads_this_turn,
            destroyed_characters_this_battle=self._destroyed_characters_this_battle,
            all_squads=self._squads(),
        )

    # Tokens are supplied as a CALLABLE, not a snapshot list: the board changes
    # under this controller between the moment it is built and every moment it
    # is asked, and a stale list would score against a board that no longer
    # exists. Same reasoning as game/path_of_the_outcast.py's all_squads.
    _tokens_source = None

    def set_tokens_source(self, source):
        self._tokens_source = source

    def _tokens(self):
        if self._tokens_source is None:
            return []
        return list(self._tokens_source())

    # Board + reserves + embarked (state.all_squads()). Separate from the token
    # source because they answer different questions: "what is on the
    # battlefield" versus "what is still in the game at all". Assassination
    # needs the second and would be wrong with the first.
    _squads_source = None

    def set_squads_source(self, source):
        self._squads_source = source

    # Board furniture, for cards that talk about places. Same
    # callable-not-snapshot reasoning as the two sources above: control of an
    # objective changes at every phase boundary.
    _objectives_source = None
    _zones_source = None

    def set_objectives_source(self, source):
        self._objectives_source = source

    def set_zones_source(self, source):
        self._zones_source = source

    # Units inside a transport (18.02). Beacon offers them alongside the board
    # units; reserves are deliberately NOT offered, and the three sources above
    # cannot tell an embarked squad from a reserved one on their own.
    _embarked_source = None

    def set_embarked_source(self, source):
        self._embarked_source = source

    # Terrain areas (13.01), for Plunder.
    _terrain_source = None

    def set_terrain_source(self, source):
        self._terrain_source = source

    # Rule 16.01's ActionController (game/actions.py). Held rather than owned:
    # actions are a general mechanic, not a mission one - shooting and charge
    # eligibility read the same controller, and a future non-mission action
    # would share it.
    action_controller = None

    def set_action_controller(self, controller):
        self.action_controller = controller

    def _squads(self):
        if self._squads_source is None:
            return None
        return list(self._squads_source())

    # ----------------------------------------------------------- the deck

    # ------------------------------------------- Burden of Trust's guards

    def snapshot_turn_start(self):
        """Record which enemy units are within range of an objective RIGHT NOW.

        Overwhelming Force asks about units that "started the turn within range
        of one or more objectives" - a fact about a moment that has already
        passed when the card scores, and about units that by then no longer
        exist. It cannot be reconstructed later, so it is taken at the top of
        every turn (either player's: the card scores at the end of A turn).

        Cheap and unconditional: a set of ids, taken even when the card is not
        in hand, because whether it is drawn NEXT round is not knowable now."""
        objectives = list(self._objectives_source()) if self._objectives_source else []
        if not objectives:
            self._on_objective_at_turn_start = set()
            return
        self._on_objective_at_turn_start = {
            id(sq) for sq in _live_squads(self._tokens())
            if sq.owner != self.player and is_within_range_of_objective(sq, objectives)
        }

    def start_of_turn(self, turn_owner):
        """"WHEN DRAWN / START OF YOUR TURN: For each objective, you may pick
        one friendly unit to guard it."

        Two triggers, one window. The assignments last "until your next turn",
        so this both CLEARS last turn's and offers new ones - a guard is not
        something you set once and forget, which is what makes the card a
        burden: every turn you have to commit units again, and only the
        standing at the very end pays.

        (User confirmed this reading after a look at the card: "Am Start des
        Zuges musst du jedes Mal eine neue Einheit bestimmen ... und am Ende
        wird abgerechnet.")"""
        if not self.plays_cards or turn_owner != self.player:
            return
        card = next((c for c in self.hand if c.key == BURDEN_OF_TRUST.key), None)
        if card is None:
            return
        # "Until your next turn" is up: last turn's guards lapse now, before
        # anything new is offered. They do NOT accumulate across turns - the
        # printed duration is explicit about that.
        self.card_state.setdefault(card.key, {})["guards"] = {}
        self._offer_guard_gate(card)

    def _offer_guard_gate(self, card):
        """The one yes/no gate in front of the per-objective chain. Shared by
        the WHEN DRAWN window and the start-of-turn one - the card gives them
        the same wording, so they get the same code.

        A gate rather than walking straight into one prompt per objective:
        map2 has five, "you may pick one friendly unit to guard it" is
        optional per objective anyway, and this window opens at the start of
        every one of your turns. Declining leaves everything unguarded that
        turn, which is a legal answer."""
        if self.decision_manager is None:
            return
        ctx = self._context(card=card)
        if not ctx.objectives or not self._guard_candidates(ctx):
            return
        self.decision_manager.request(
            self.player,
            f"{card.name}: assign a unit to guard each objective this turn?",
            [
                ("Assign guards", lambda c=card: self._assign_guard_next(c, 0)),
                ("Leave them unguarded", lambda: None),
            ],
        )

    @staticmethod
    def _guard_candidates(ctx):
        return sorted((sq for sq in _live_squads(ctx.tokens) if sq.owner == ctx.player),
                      key=lambda sq: sq.name)

    def _assign_guard_next(self, card, index):
        """One objective at a time, and the unit is picked by CLICKING IT ON
        THE BOARD (user's request) rather than from a list of names.

        The objective travels with the request as its `subject`, because that
        is the whole point: "muss immer links in der Spalte das Objective
        genannt werden, um das es gerade geht". Only units actually IN RANGE
        are eligible - a guard has to be in range to count for anything, so a
        click on one that is not would be a choice the card cannot honour.
        """
        ctx = self._context(card=card)
        objectives = list(ctx.objectives)
        while index < len(objectives):
            objective = objectives[index]
            eligible = [sq for sq in self._guard_candidates(ctx)
                        if is_within_range_of_objective(sq, [objective])]
            if not eligible:
                index += 1
                continue
            self.request_unit_pick(
                prompt=f"{card.name}: click the unit that guards this objective.",
                subject=objective.name,
                eligible=eligible,
                on_pick=(lambda squad, c=card, o=objective, i=index:
                         self._take_guard(c, o, squad, i)),
                on_skip=(lambda c=card, i=index: self._assign_guard_next(c, i + 1)),
                skip_label="No guard here",
            )
            return
        self.pending_pick = None

    def _take_guard(self, card, objective, squad, index):
        guards = self.card_state.setdefault(card.key, {}).setdefault("guards", {})
        guards[id(objective)] = squad
        self._log(f"{self.player}: {card.name} - {squad.name} guards {objective.name}.")
        self._assign_guard_next(card, index + 1)

    # ------------------------------------------------- rule 16.01 actions

    def offer_actions_at_shooting_phase(self, turn_owner):
        """"STARTS: Your Shooting phase." Offer every action a held card brings,
        to every unit 16.01 lets start it.

        Behind one yes/no gate, like Burden of Trust's guards and for the same
        reason: starting an action costs the unit its shooting AND its charge
        this turn, so it is a real decision, but being asked about every
        eligible unit every Shooting phase when you did not want to would be
        worse than the card is worth."""
        if not self.plays_cards or turn_owner != self.player:
            return
        if self.decision_manager is None or self.action_controller is None:
            return
        for card in self.hand:
            if card.action is None or card.action.starts != PHASE_SHOOTING:
                continue
            ctx = self._context(card=card)
            if not self._action_candidates(card.action, ctx):
                continue
            self.decision_manager.request(
                self.player,
                f"{card.name}: start the {card.action.name} action this Shooting phase? "
                "(a unit that does loses its shooting and its charge this turn)",
                [
                    ("Start the action", lambda a=card.action: self._offer_action_next(a, 0)),
                    ("Not this turn", lambda: None),
                ],
            )
            return

    def _action_candidates(self, action, ctx):
        squads = sorted((sq for sq in _live_squads(ctx.tokens) if sq.owner == self.player),
                        key=lambda sq: sq.name)
        out = []
        for squad in squads:
            ok, _reason = self.action_controller.can_start(action, squad, ctx)
            if ok and action.target_options(squad, ctx):
                out.append(squad)
        return out

    def _offer_action_next(self, action, index):
        """One prompt per eligible unit, chained. Re-derived each time rather
        than snapshotted: starting an action changes who is still eligible
        (USE LIMIT: "each unit must be within range of a DIFFERENT
        objective"), so a list built up front would offer a target that has
        just been taken."""
        card = next((c for c in self.hand if c.action is action), None)
        if card is None or self.decision_manager is None:
            return
        ctx = self._context(card=card)
        candidates = self._action_candidates(action, ctx)
        if index >= len(candidates):
            return
        squad = candidates[index]
        targets = [(label, target) for label, target in action.target_options(squad, ctx)
                   if action.use_limit_allows(self.action_controller.states, squad, target, ctx)]
        if not targets:
            self._offer_action_next(action, index + 1)
            return
        self.decision_manager.request(
            self.player,
            # The action names itself - hard-coding one action's verb here made
            # Plunder ask which objective a unit "cleanses".
            f"{action.name}: which target does {squad.name} use for {action.name}?",
            [
                (label, lambda a=action, sq=squad, t=target, i=index:
                    self._take_action_target(a, sq, t, i))
                for label, target in targets
            ] + [(f"{squad.name} does not act",
                  lambda a=action, i=index: self._offer_action_next(a, i + 1))],
        )

    def _take_action_target(self, action, squad, target, index):
        self.action_controller.start(action, squad, target, self._context())
        # index, not index + 1: starting an action removes this unit from the
        # candidate list, so the next eligible one has slid down into its slot.
        self._offer_action_next(action, index)

    def _resolve_actions(self, ending_player):
        """Complete this turn's actions and hand each card what it needs.

        Runs BEFORE the cards are scored - Cleanse's whole VP comes from what
        completed at this instant."""
        if self.action_controller is None:
            return
        completed = self.action_controller.resolve_end_of_turn(ending_player, self._context())
        for card in list(self.hand) + list(self.discarded):
            if card.action is None:
                continue
            done = [state.target for state in completed
                    if state.definition is card.action and state.target is not None]
            # Each action card reads its own completions under its own name -
            # the word is the card's, not the framework's.
            slot = "plundered_this_turn" if card.action.key == "plunder" else "cleansed_this_turn"
            self.card_state.setdefault(card.key, {})[slot] = done

    def record_destroyed_model(self, model):
        """Fed from main.py's dead-model sweep, once per removed model. Cards
        that say "destroyed this turn" read the list this builds; it is cleared
        at each turn boundary by begin_end_of_turn().

        An enemy CHARACTER model is ALSO remembered for the whole battle, for
        Assassination's "have been destroyed during the battle" branch - noted
        here, in the sweep, because that is the only moment the model is still
        identifiable as a character before it leaves the board."""
        if not self.plays_cards:
            return
        self._destroyed_this_turn.append(model)
        squad = getattr(model, "squad", None)
        if squad is not None and squad.owner != self.player and _is_character(model):
            self._destroyed_characters_this_battle.append(model)

    def record_destroyed_squad(self, squad):
        """Fed from the SAME sweep, but from main.py's own
        attached_units.unit_is_destroyed() branch - a whole unit being wiped
        out, not one model dying. A Grievous Blow counts units where Bring It
        Down counts models, so the two need separate feeds; deriving one from
        the other would be a second opinion on a question the engine already
        answers (19.01 merges a leader into its squad, so "all its models are
        gone" is not a judgement this module should be making).

        Idempotent per squad by identity: the sweep can reach an
        already-emptied squad again on the next dead model in the same frame,
        exactly as MissionController.record_destroyed_squad() guards against."""
        if not self.plays_cards or squad is None:
            return
        if id(squad) in self._destroyed_squad_ids:
            return
        self._destroyed_squad_ids.add(id(squad))
        self._destroyed_squads_this_turn.append(squad)

    def draw_at_command_phase(self, turn_owner, battle_round):
        """"Am Anfang jeder Runde zieht man zwei neue Missionen" - resolved as
        the start of this player's OWN Command phase, which happens exactly
        once per battle round.

        Idempotent by battle round: main.py reaches this from the two
        battle-start paths as well as from every Command phase, and the very
        first Command phase is covered by both."""
        if not self.plays_cards or turn_owner != self.player:
            return []
        if self._drawn_round == battle_round:
            return []
        self._drawn_round = battle_round
        drawn = [c for c in (self._draw_one() for _ in range(CARDS_DRAWN_PER_ROUND)) if c is not None]
        if not drawn:
            self._log(f"{self.player}: the Secondary Mission deck is empty - no cards drawn.")
            return []
        for card in drawn:
            self._log(f"{self.player} draws Secondary Mission: {card.name}.")
        # The "WHEN DRAWN" clauses resolve BEFORE the notice overlay is shown,
        # so the overlay announces the final pair rather than one the human is
        # about to throw away. _offer_redraws() enqueues the overlay itself once
        # it is done, which is also the only path when there is nothing to ask.
        self._offer_redraws(list(drawn), battle_round=battle_round)
        return drawn

    def _draw_one(self):
        """One card off the top, or None. The deck is NOT reshuffled when empty
        (user choice: each card once per battle)."""
        if not self.deck:
            return None
        card = self.deck.pop(0)
        self.hand.append(card)
        self._run_setup(card)
        return card

    def _run_setup(self, card):
        """Resolve a card's WHEN DRAWN setup, if it has one, and remember the
        result in this card's own slot of self.card_state.

        Runs at the moment of the draw, which is what the card says - A
        Tempting Target's objective is chosen from the board as it stands
        then, not re-chosen later when it would be easier or harder."""
        if not card.has_setup:
            return
        chosen = card.on_draw(self._context(card=card))
        state = self.card_state.setdefault(card.key, {})
        state["objective"] = chosen
        detail = self.detail_for(card)
        if detail:
            self._log(f"{self.player}: {card.name} - {detail}")

    def _offer_redraws(self, pending, announced=None, battle_round=None):
        """Walk the just-drawn cards, asking about each one whose own WHEN
        DRAWN clause applies, then announce the final set.

        The offer is withheld when the deck is empty: "discard and draw a new
        Secondary Mission" cannot be honoured with nothing to draw, and this
        engine does not offer what it will not deliver (CLAUDE.md error class
        5). With the current two-card deck that is the normal case - drawing
        two empties it - so the clause is built but will rarely fire."""
        announced = list(announced if announced is not None else [])
        while pending:
            card = pending.pop(0)
            ctx = self._context(card=card, battle_round=battle_round)
            if self.deck and card.when_drawn_may_redraw(ctx) and card.when_drawn_is_mandatory:
                # No "you may" on this card's clause - it is an instruction, so
                # it resolves without a prompt. Defend Stronghold is the only
                # one so far; Behind Enemy Lines prints the same sentence WITH
                # "you may" and is offered below.
                self._redraw(card, pending, announced, battle_round)
                return
            if (self.decision_manager is not None and self.deck
                    and card.when_drawn_may_redraw(ctx)):
                self.decision_manager.request(
                    self.player,
                    f"{card.name} was drawn, but its When Drawn clause applies. "
                    "Discard it and draw a new Secondary Mission?",
                    [
                        ("Discard and redraw", lambda c=card, p=list(pending), a=list(announced):
                            self._redraw(c, p, a, battle_round)),
                        ("Keep it", lambda c=card, p=list(pending), a=list(announced):
                            self._offer_redraws(p, a + [c], battle_round)),
                    ],
                )
                return
            announced.append(card)
        # Redraws settled - now the cards that need the PLAYER to pick
        # something (Beacon's beacon unit). Kept as a second pass rather than
        # folded into the loop above so a card cannot be set up and then
        # redrawn away, wasting the choice.
        self._setup_next(announced)

    def _setup_next(self, announced):
        """Ask about each drawn card with an interactive WHEN DRAWN setup, one
        at a time, then announce the final set.

        Chained through the callbacks like the redraw offer above and the
        end-of-turn scoring chain: DecisionManager is a queue, but each prompt's
        option list has to be built from the board AS IT IS when that prompt is
        answered, not all up front."""
        announced = list(announced)
        for index, card in enumerate(announced):
            if not card.has_interactive_setup:
                continue
            if self.card_state.get(card.key, {}).get("objective") is not None:
                continue  # already chosen in an earlier pass of this chain
            ctx = self._context(card=card)
            options = card.draw_choices(ctx)
            if not options or self.decision_manager is None:
                # Nothing to choose from (no units on the board yet). Record the
                # miss rather than silently leaving a card that can never score.
                self.card_state.setdefault(card.key, {})["objective"] = None
                self._log(f"{self.player}: {card.name} - nothing eligible to choose.")
                continue
            rest = announced
            self.decision_manager.request(
                self.player, card.draw_prompt,
                [
                    (label, lambda c=card, v=value, a=rest: self._take_setup_choice(c, v, a))
                    for label, value in options
                ],
            )
            return
        self._announce(announced)
        # "WHEN DRAWN / START OF YOUR TURN" - the same window, so a freshly
        # drawn Burden of Trust gets its guards offered right away. Announced
        # FIRST on purpose: the draw notice outranks decisions in main.py's
        # event chain, so the player sees WHICH cards arrived, dismisses that,
        # and only then is asked about guards.
        for card in announced:
            if card.key == BURDEN_OF_TRUST.key:
                self._offer_guard_gate(card)
                break

    def _take_setup_choice(self, card, value, announced):
        self.card_state.setdefault(card.key, {})["objective"] = value
        detail = self.detail_for(card)
        if detail:
            self._log(f"{self.player}: {card.name} - {detail}")
        self._setup_next(announced)

    def _redraw(self, card, pending, announced, battle_round=None):
        """Resolve a WHEN DRAWN redraw: the card leaves the hand and a
        replacement is drawn.

        Two disposals, and the cards print the difference: Bring It Down and A
        Grievous Blow are DISCARDED, Behind Enemy Lines is SHUFFLED BACK into
        the deck and can come round again.

        ORDER MATTERS for the shuffle-back case. The replacement is drawn
        FIRST, and only then does the returned card rejoin the deck - because
        "draw a NEW Secondary Mission" is exactly what putting it back before
        drawing fails to guarantee. Measured: with a small deck, shuffling
        first hands the same card straight back and the whole clause becomes a
        no-op that looks like a bug."""
        if card in self.hand:
            self.hand.remove(card)
        replacement = self._draw_one()
        if card.when_drawn_shuffles_back:
            self.deck.append(card)
            self._rng.shuffle(self.deck)
            self._log(f"{self.player} shuffles {card.name} back into the deck and draws again.")
        else:
            self.discarded.append(card)
            self._log(f"{self.player} discards {card.name} (When Drawn) and draws again.")
        if replacement is not None:
            self._log(f"{self.player} draws Secondary Mission: {replacement.name}.")
            pending = list(pending) + [replacement]
        self._offer_redraws(pending, announced, battle_round)

    def _announce(self, cards):
        """Hand the drawn cards to the click-away notice - or buffer them if it
        does not exist yet.

        The buffer is not hypothetical: on the legacy instant-scene path
        (config.PREGAME_DEPLOYMENT off) main.py starts the battle - and so
        draws round 1's cards - hundreds of lines before the UI is built, so
        the overlay is genuinely still None at that point. Without the buffer
        that one announcement would silently vanish and the very first draw of
        the game would be the only one the player never sees. main.py calls
        flush_announcements() right after attaching the overlay."""
        if not cards:
            return
        if self.draw_overlay is None:
            self._unannounced.append(list(cards))
            return
        self.draw_overlay.enqueue(self.player, cards, self._details_for(cards))

    def _details_for(self, cards):
        out = {}
        for card in cards:
            detail = self.detail_for(card)
            if detail:
                out[card.key] = detail
        return out

    def flush_announcements(self):
        """Announce anything drawn before draw_overlay was attached. Safe to
        call at any time; a no-op once the buffer is empty."""
        if self.draw_overlay is None:
            return
        pending, self._unannounced = self._unannounced, []
        for cards in pending:
            self.draw_overlay.enqueue(self.player, cards, self._details_for(cards))

    def _discard(self, card):
        if card in self.hand:
            self.hand.remove(card)
        self.discarded.append(card)

    # ------------------------------------------------------- scoring / prompts

    def offered_now(self):
        """The cards whose cash-in prompt is open right now, as {id(card): vp}.

        This - NOT achieved() - is what the strip marks as READY. A card is
        "erfuellt" only at its own printed instant, and asking achieved()
        without an ending_player answers a different question ("would the
        condition hold if the turn ended now"), which the strip used to render
        as a fulfilment claim. User: "mir ist aufgefallen, dass ich gerade
        Center Ground mitten im Zug schon erfuellt habe... Center Ground wird
        erst am Ende meines Zuges erfuellt." Marking a mid-turn snapshot as
        complete was exactly that mistake - Centre Ground is measured at the
        end of your turn, and until then holding the centre is a position, not
        a score."""
        offered = {}
        if self._current_offer is not None:
            card, vp = self._current_offer
            offered[id(card)] = vp
        for card, vp in self._pending_scoring:
            offered.setdefault(id(card), vp)
        return offered

    def achieved(self, ending_player=None, battle_round=None):
        """[(card, vp), ...] for every hand card whose printed instant is the
        one that just happened AND whose condition is met.

        `ending_player=None` skips the timing filter, i.e. asks "is the
        condition met" rather than "does this score now" - only useful to a
        caller that already knows it is standing at a scoring instant. The
        strip deliberately does NOT use it; see offered_now()."""
        if not self.plays_cards:
            return []
        out = []
        for card in self.hand:
            # A context PER CARD, not one shared across the hand: card_state is
            # the card's own scratchpad, and handing every card the same dict
            # would let A Tempting Target read the Beacon's choice.
            ctx = self._context(ending_player=ending_player, card=card,
                                battle_round=battle_round)
            if ending_player is not None and not card.scores_at(ctx):
                continue
            vp = card.score(ctx)
            if vp > 0:
                out.append((card, vp))
        return out

    def detail_for(self, card):
        """The one-line description of whatever this card remembered at draw
        time ("Target: Central Objective"), or None. Shown by the strip and the
        draw notice - a card with setup state is unplayable without it, since
        its printed text never says WHICH objective or unit it means.

        Deliberately NOT wrapped in a try/except: this runs every frame from
        the strip, and a bare except there would swallow a real defect forever
        (it already hid one during development - a mis-applied edit left the
        strip showing no detail at all, and the silent guard turned that into
        "the feature just does nothing"). Cards keep their own detail functions
        total instead, reading state with .get()."""
        return card.detail(self._context(card=card))

    def begin_end_of_turn(self, ending_player, battle_round=None):
        """The end-of-turn step: offer every achieved card, one at a time, then
        the single discard-for-CP offer.

        The VP amounts are computed EAGERLY, here, before anything is asked -
        the prompts resolve asynchronously (the human may take several frames,
        and turn_tracker has already flipped by the time this runs, exactly as
        starflare_controller.offer() does at the same instant), so the board
        they were measured against must not be re-read later. That also lets
        _destroyed_this_turn be cleared right now, before the next turn starts
        filling it."""
        if not self.plays_cards:
            self._destroyed_this_turn = []
            self._destroyed_squads_this_turn = []
            return
        # Actions first: Cleanse completes at exactly this instant, and its
        # card's VP is a count of what completed.
        self._resolve_actions(ending_player)
        self._pending_scoring = list(
            self.achieved(ending_player=ending_player, battle_round=battle_round))
        self._destroyed_this_turn = []
        # The per-TURN unit list clears with it; _destroyed_squad_ids does NOT,
        # since it is only there to stop one unit being recorded twice and a
        # destroyed unit never comes back.
        self._destroyed_squads_this_turn = []
        self._ask_next(ending_player)

    def _ask_next(self, ending_player):
        """One prompt per achieved card, chained: both options call back into
        here, so the queue drains in order and the discard-for-CP offer only
        opens once every scoring choice has been answered (a card cashed in is
        gone and must not still be listed as discardable)."""
        while self._pending_scoring:
            card, vp = self._pending_scoring.pop(0)
            if card not in self.hand:
                continue  # already discarded by an earlier answer in this same chain
            granted = min(vp, self.remaining_vp_this_round())
            if granted <= 0:
                self._log(
                    f"{self.player}: {card.name} is complete, but this battle round's "
                    f"{MAX_SECONDARY_VP_PER_ROUND} VP Secondary cap is already reached - not offered."
                )
                continue
            if self.decision_manager is None:
                continue
            capped = " (this round's 15 VP cap)" if granted < vp else ""
            self._asking = True
            self._current_offer = (card, granted)
            self.decision_manager.request(
                self.player,
                f"{card.name} is complete. Score {granted} VP now and discard the card, "
                "or keep it for a later turn?",
                [
                    (f"Score {granted} VP{capped}",
                     lambda c=card, g=granted, e=ending_player: self._cash_in(c, g, e)),
                    ("Keep the card",
                     lambda e=ending_player: self._keep(e)),
                ],
            )
            return
        self._asking = False
        self._current_offer = None
        self._offer_discard_for_cp(ending_player)

    def _cash_in(self, card, vp, ending_player):
        self._current_offer = None
        self.cash_in(card, vp)
        self._ask_next(ending_player)

    def _keep(self, ending_player):
        self._current_offer = None
        self._ask_next(ending_player)

    def cash_in(self, card, vp):
        """Credit the VP through game/missions.py's own ledger - the same
        secondary_points dict GameStatusPanel already reads - and discard the
        card. Clamped to what is left of this battle round's 15 VP rather than
        refused, so a partially-capped card still pays what it can."""
        granted = max(0, min(int(vp), self.remaining_vp_this_round()))
        if granted <= 0:
            return 0
        self._scored_vp_this_round += granted
        if self.mission_controller is not None:
            self.mission_controller.add_secondary_points(self.player, granted)
        self._discard(card)
        self._log(f"{self.player} scores {granted} Secondary point(s) ({card.name}).")
        return granted

    # --------------------------------------------------- discard for +1 CP

    def _bonus_cp_available(self):
        """Whether a discard would actually pay. The cap is shared across every
        bonus-CP source in the game (Thievin' Scavengers, Diviner of Futures,
        ...), so this asks CommandPointManager rather than keeping a second
        count of its own."""
        if self.command_points is None or self.turn_tracker is None:
            return False
        return self.command_points.bonus_cp_remaining(self.player, self.turn_tracker.battle_round) > 0

    def _offer_discard_for_cp(self, ending_player):
        """"Ich kann mich aber auch dazu entscheiden, am Ende meiner Runde eine
        secondary Mission abzuwerfen und bekomme dann einen zusaetzlichen
        Kommando-Punkt."

        Only at the end of the card player's OWN turn, and only while this
        round's bonus CP is still unspent - offering a discard that would grant
        0 CP is exactly the "don't offer what you don't want chosen" mistake.
        ONE decision listing every hand card plus a decline, the same
        option-per-candidate shape game/neocapacitor_shields.py uses."""
        if ending_player != self.player or not self.hand:
            return
        if self.decision_manager is None or not self._bonus_cp_available():
            return
        options = [
            (f"Discard {card.name} for +1 CP", lambda c=card: self.discard_for_cp(c))
            for card in self.hand
        ]
        options.append(("Keep them all", lambda: None))
        self.decision_manager.request(
            self.player,
            "End of your turn: discard one Secondary Mission for +1 CP? "
            "(at most 1 bonus CP per battle round)",
            options,
        )

    def discard_for_cp(self, card):
        """Discard one card for +1 CP. gain_cp() owns the per-round cap, so
        this neither re-implements nor second-guesses it - it just reports what
        actually landed."""
        if card not in self.hand:
            return 0
        battle_round = self.turn_tracker.battle_round if self.turn_tracker is not None else None
        granted = 0
        if self.command_points is not None:
            granted = self.command_points.gain_cp(
                self.player, battle_round, amount=1, reason=f"discarded {card.name}",
            )
        self._discard(card)
        self._log(f"{self.player} discards Secondary Mission {card.name} for {granted} CP.")
        return granted
