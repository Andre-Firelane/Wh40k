"""PRIMARY MISSIONS, one per FORCE DISPOSITION (user-supplied cards).

WHAT THIS REPLACES
------------------
game/missions.py keeps "Hold the Line" - 3 VP per objective controlled at the
start of your own Command phase - for whoever is NOT playing one of these. A
player listed in config.PRIMARY_MISSION_CARD_PLAYERS plays the mission their
army list's Force Disposition names INSTEAD.

Scope, from the user: "die ki soll weiterhin ihre standard primar mission
haben. die primary missions hier sind nur fuer spieler1."

HOW A PLAYER GETS ONE
---------------------
Every detachment permits exactly one Force Disposition (transcribed onto
Detachment.force_disposition from the detachment's own Wahapedia heading, and
mirrored into rules/*/detachments/*.md). A list picks one of the dispositions
its detachments grant and writes it down; game/detachments.py's validate()
checks the pick. The disposition then names the mission, one to one - which is
why this registry is keyed on the disposition and not on a mission name.

WHY THIS IS NOT A SecondaryMissionCard
--------------------------------------
A Secondary is one card with ONE scoring instant, cashed in ONCE, out of a hand
you choose from. A Primary is one card you hold all battle, with SEVERAL
independent scoring boxes - different instants, different battle-round bands -
each of which pays every single time its instant comes round and its condition
holds. Those are different objects, and squeezing the second into the first
would have meant five cards' worth of boxes pretending to be one timing.

AUTOMATIC, NO PROMPTS
---------------------
The Secondary deck asks before scoring, because there a card is a resource you
might rather keep for a better turn. A Primary offers no such choice: there is
exactly one card, you cannot discard it, and every box is a fixed condition. So
these score silently. That is also why the headless harnesses need no opt-out
from this system, unlike the Secondary deck - nothing here can stall on a
question nobody answers.

NO VP CAP
---------
User's decision, asked explicitly. The cards print none, so none is invented.
Note the AI's "Hold the Line" has no cap either, so neither side is capped.

THE OPPONENT IS ASSUMED TO BE TAKE AND HOLD
-------------------------------------------
All five supplied cards print "OPPONENT: TAKE AND HOLD" at the bottom - they
are the deck for a game whose other player is playing Take and Hold (user: "wir
gehen davon aus, dass spieler 2 immer take and hold hat"), and Battlefield
Dominance's footer says "TAKE AND HOLD - MIRROR" because there both are. The
engine does not enforce it; announce() logs when the other player's declared
disposition is something else, so a violated assumption shows up in the log
rather than quietly mispricing a card.
"""

from game import force_dispositions
from game.actions import ActionDefinition
from game.mission_context import (
    MissionContext,
    _live_squads,
    _non_home_objectives,
    _other_player,
    central_objectives,
    own_home_objective,
    quarters_with_presence,
)
from game.objectives import is_within_range_of_objective
from game.turn import PHASE_SHOOTING

# ------------------------------------------------------------------ timings
# When a scoring box is checked. Each is a real instant main.py already has a
# seam for; a box is asked at its own instant and at no other.
#
# "END OF YOUR TURN" - the `if ending_player is not None` block.
TIMING_END_OF_YOUR_TURN = "end_of_your_turn"
# "END OF CMD PHASE" - the `if phase_before == PHASE_COMMAND` block, for the
# player whose Command phase just ended. Note this is a DIFFERENT instant from
# the one "Hold the Line" uses, which is the START of the Command phase: Battle
# Shock is resolved in between and changes OC, which changes who controls what.
TIMING_END_OF_COMMAND_PHASE = "end_of_command_phase"
# "END OF BATTLE / FINAL SCORING" - once, from _check_battle_end(), before the
# result overlay reads the ledger.
TIMING_END_OF_BATTLE = "end_of_battle"

TIMING_LABELS = {
    TIMING_END_OF_YOUR_TURN: "end of your turn",
    TIMING_END_OF_COMMAND_PHASE: "end of your Command phase",
    TIMING_END_OF_BATTLE: "end of the battle",
}


class ScoringBox:
    """One printed scoring box: an instant, a battle-round band, and what it
    pays.

    `score(ctx)` is a pure function of the context, like a Secondary card's -
    no side effects, no memory - so it can be asked repeatedly. It is asked
    ONLY at this box's own instant.

    `min_round`/`max_round` are the printed band ("2ND ROUND ONWARD",
    "ROUNDS 1-2"), inclusive on both ends. None means unbounded that way; a box
    printing "ANY BATTLE ROUND" has neither.

    `vp` is what this box PAYS, as a short string for the card's scoring table
    (user: "vielleicht eine kleine tablle / Was | Wann | VP"). A string and not
    a number because half these boxes do not pay a flat amount - "3 or 6",
    "1 per unit", "3 per obj, +2" - and `score(ctx)` cannot answer it either:
    it needs a live board, while the card has to state its rate before anything
    has happened. REQUIRED, with no default: a box that forgot it would render
    a blank cell, which reads as "pays nothing".

    Every one is built from the same module constant its score function reads,
    so the printed rate and the paid rate cannot drift apart.
    """

    def __init__(self, key, timing, score, label, vp, min_round=None, max_round=None):
        self.key = key
        self.timing = timing
        self._score = score
        self.label = label
        self.vp = vp
        self.min_round = min_round
        self.max_round = max_round

    @property
    def round_label(self):
        if self.min_round and self.max_round:
            return "rounds %d-%d" % (self.min_round, self.max_round)
        if self.min_round:
            return "round %d onward" % self.min_round
        if self.max_round:
            return "up to round %d" % self.max_round
        return "any battle round"

    def in_round_band(self, battle_round):
        """Unknown round (None) counts as IN the band. Every caller in main.py
        supplies one; a test driving a box directly should not have to."""
        if battle_round is None:
            return True
        if self.min_round is not None and battle_round < self.min_round:
            return False
        if self.max_round is not None and battle_round > self.max_round:
            return False
        return True

    def score(self, ctx):
        return max(0, int(self._score(ctx)))


class PrimaryMission:
    """One Primary Mission card: the boxes on its front, plus the Objective
    Action on its back if it has one."""

    def __init__(self, key, name, force_disposition, text, boxes, action=None):
        self.key = key
        self.name = name
        self.force_disposition = force_disposition
        self.text = text
        self.boxes = list(boxes)
        # The rule-16.01 ActionDefinition this card's scoring depends on, if
        # any - the card's printed reverse side. Two of the five have one.
        self.action = action

    def boxes_at(self, timing):
        return [b for b in self.boxes if b.timing == timing]

    @property
    def disposition_label(self):
        return force_dispositions.label(self.force_disposition)

    def scoring_rows(self):
        """The card's scoring boxes as (WHAT, WHEN, VP) triples - the little
        table the strip draws.

        User: "koenntest du hier absaetze unten einbauen, was wieviele punkte
        gibt? und vielleicht punkte und text tabellarisch trennen? so im
        fliesstext ist die information sehr unuebersichtlich. vielleicht eine
        kleine tablle / Was | Wann | VP".

        Split out of info_rows() rather than growing it to three columns,
        because the two are different KINDS of row: DISPOSITION and ACTION are
        one-off facts about the card, these are the repeated rate card. Mixing
        them meant every scoring box shared a column layout with a sentence
        about an Objective Action, and the VP - the column the user actually
        asked for - had nowhere to go that lined up.

        WHAT is the box's own printed label, not a summary of its condition:
        the condition is the printed prose below, and paraphrasing it into a
        cell is exactly the "selbst generierte variante" that was just removed
        from the unit datacard."""
        return [(box.label,
                 "%s, %s" % (TIMING_LABELS.get(box.timing, ""), box.round_label),
                 box.vp)
                for box in self.boxes]

    def info_rows(self):
        """The one-off facts about this card, as (LABEL, value) pairs - what
        disposition it belongs to, and its Objective Action if it has one. The
        per-box rate card is scoring_rows().

        Pairs rather than padded strings for a measured reason: these were
        "%-12s" padded, which only lines up in a monospace font, and
        config.FONT_NAME is pygame's proportional default."""
        rows = [("DISPOSITION", self.disposition_label)]
        if self.action is not None:
            completes = ("completes immediately" if self.action.completes_immediately
                         else "completes at the end of your turn")
            rows.append(("ACTION", "%s, started in your %s phase; %s; the unit "
                                   "cannot shoot or charge this turn"
                                   % (self.action.name, self.action.starts, completes)))
        return rows

    def info_lines(self):
        """Every row of both tables flattened to strings, for callers that only
        want to read the text. Built FROM the two row builders so they cannot
        disagree - and it still covers the scoring boxes, which is what a
        caller asking "what does this card say" means."""
        lines = [f"{label}  {value}" for label, value in self.info_rows()]
        return lines + [f"{what}  {when}  {vp}VP" for what, when, vp in self.scoring_rows()]


# ------------------------------------------------------------ shared reading
# Every one of the five cards talks about controlling objectives, and four of
# them say "(excluding your home objective)". These two are that sentence.

def controlled_objectives(ctx):
    return [o for o in ctx.objectives if o.controlled_by == ctx.player]


def controlled_non_home_objectives(ctx):
    """"...(excluding your home objective)" - singular and possessive on every
    card that prints it, so the OPPONENT's home objective still counts. Reuses
    _non_home_objectives(), which derives "mine" from the deployment zones
    rather than from the string "Home"."""
    return [o for o in _non_home_objectives(ctx) if o.controlled_by == ctx.player]


def enemy_units_destroyed_this_turn(ctx):
    return [sq for sq in ctx.destroyed_squads_this_turn if sq.owner != ctx.player]


# ------------------------------------------------- BATTLEFIELD DOMINANCE (T&H)
BATTLEFIELD_DOMINANCE_MORE_VP = 2
BATTLEFIELD_DOMINANCE_PER_OBJECTIVE_VP = 3
BATTLEFIELD_DOMINANCE_HOME_BONUS_VP = 2
SECOND_ROUND_ONWARD = 2  # the "2ND ROUND ONWARD" band every card here prints


def _dominance_more_objectives(ctx):
    """"Rounds 1-2, end of your turn: you control more objectives than your
    opponent." MORE, so a tie pays nothing - own test line, because "at least
    as many" is the easy misreading."""
    mine = len(controlled_objectives(ctx))
    theirs = sum(1 for o in ctx.objectives if o.controlled_by == ctx.opponent)
    return BATTLEFIELD_DOMINANCE_MORE_VP if mine > theirs else 0


def _dominance_control(ctx):
    """"For each objective you control: 3 VP. + CUMULATIVE: for each of those
    objectives (excluding your home objective), if you control your home
    objective: +2 VP."

    CUMULATIVE means the +2 is added on top of the 3, not instead of it. Note
    the asymmetry in one sentence: the 3 VP counts EVERY objective including
    your home, the +2 counts every one EXCEPT it - so holding your home turns
    each forward objective into 5 while the home itself stays worth 3."""
    base = len(controlled_objectives(ctx)) * BATTLEFIELD_DOMINANCE_PER_OBJECTIVE_VP
    home = own_home_objective(ctx)
    if home is None or home.controlled_by != ctx.player:
        return base
    forward = len(controlled_non_home_objectives(ctx))
    return base + forward * BATTLEFIELD_DOMINANCE_HOME_BONUS_VP


BATTLEFIELD_DOMINANCE = PrimaryMission(
    key="battlefield_dominance",
    name="Battlefield Dominance",
    force_disposition=force_dispositions.TAKE_AND_HOLD,
    text=(
        "Rounds 1-2, at the end of your turn: 2VP if you control more objectives than "
        "your opponent. From the second battle round, at the end of your Command phase: "
        "3VP for each objective you control, plus a cumulative 2VP for each of those "
        "objectives other than your home objective if you control your home objective."
    ),
    boxes=[
        ScoringBox("more_objectives", TIMING_END_OF_YOUR_TURN, _dominance_more_objectives,
                   "MORE OBJ", "%d" % BATTLEFIELD_DOMINANCE_MORE_VP, max_round=2),
        ScoringBox("control", TIMING_END_OF_COMMAND_PHASE, _dominance_control,
                   "CONTROL",
                   "%d/obj, +%d" % (BATTLEFIELD_DOMINANCE_PER_OBJECTIVE_VP,
                                    BATTLEFIELD_DOMINANCE_HOME_BONUS_VP),
                   min_round=SECOND_ROUND_ONWARD),
    ],
)


# ------------------------------------------- RECONNAISSANCE SWEEP (RECON)
RECON_THREE_QUARTERS_VP = 3
RECON_FOUR_QUARTERS_VP = 6
RECON_PER_KILL_VP = 1
RECON_OBJECTIVE_VP = 3


def _recon_quarters(ctx):
    """"Three or more friendly units are wholly within three different table
    quarters, and not within 6" of the centre of the battlefield: 3VP. OR four
    or more units in four different quarters: 6VP."

    OR, so these are ALTERNATIVES and not tiers that add - four quarters pays
    6, never 9. Own test line, because the card next door (Secure Asset) prints
    two rows in one band that DO add.

    Counting quarters is the same thing as counting units here, and that is not
    a shortcut: unit_has_presence_in() requires every model's base to be wholly
    inside one quarter, so a unit can supply presence in at most one. Presence
    in three quarters therefore means three DIFFERENT units, which is exactly
    what the card asks for.

    The 6"-from-centre clause is word for word Engage on All Fronts', which is
    why both read the same helper and the same CENTRE_EXCLUSION_IN."""
    quarters = len(quarters_with_presence(ctx))
    if quarters >= 4:
        return RECON_FOUR_QUARTERS_VP
    if quarters >= 3:
        return RECON_THREE_QUARTERS_VP
    return 0


def _recon_kills(ctx):
    """"For each enemy unit destroyed this turn: 1VP." No cap printed."""
    return len(enemy_units_destroyed_this_turn(ctx)) * RECON_PER_KILL_VP


def _recon_objective(ctx):
    return RECON_OBJECTIVE_VP if controlled_non_home_objectives(ctx) else 0


RECONNAISSANCE_SWEEP = PrimaryMission(
    key="reconnaissance_sweep",
    name="Reconnaissance Sweep",
    force_disposition=force_dispositions.RECONNAISSANCE,
    text=(
        "End of your turn: 3VP if three or more friendly units are wholly within three "
        "different table quarters and not within 6\" of the centre of the battlefield, or "
        "6VP for four or more units in four different quarters. Also at the end of your "
        "turn, 1VP for each enemy unit destroyed this turn. From the second battle round, "
        "at the end of your Command phase: 3VP if you control one or more objectives "
        "other than your home objective."
    ),
    boxes=[
        ScoringBox("quarters", TIMING_END_OF_YOUR_TURN, _recon_quarters, "SPREAD",
                   "%d or %d" % (RECON_THREE_QUARTERS_VP, RECON_FOUR_QUARTERS_VP)),
        ScoringBox("kills", TIMING_END_OF_YOUR_TURN, _recon_kills, "KILLS",
                   "%d/unit" % RECON_PER_KILL_VP),
        ScoringBox("objective", TIMING_END_OF_COMMAND_PHASE, _recon_objective,
                   "OBJECTIVE", "%d" % RECON_OBJECTIVE_VP,
                   min_round=SECOND_ROUND_ONWARD),
    ],
)


# ---------------------------------------------- UNSTOPPABLE FORCE (PURGE)
UNSTOPPABLE_KILL_VP = 3
UNSTOPPABLE_PER_OBJECTIVE_VP = 4
UNSTOPPABLE_GAINED_VP = 3
UNSTOPPABLE_CENTRAL_VP = 5


def _unstoppable_kills(ctx):
    """"One or more enemy units were destroyed this turn: 3VP." A yes/no, not a
    count - contrast Reconnaissance Sweep's per-unit box."""
    return UNSTOPPABLE_KILL_VP if enemy_units_destroyed_this_turn(ctx) else 0


def _unstoppable_objectives(ctx):
    return len(controlled_non_home_objectives(ctx)) * UNSTOPPABLE_PER_OBJECTIVE_VP


def _unstoppable_gained(ctx):
    """"You control one or more objectives you did not control at the start of
    the turn (excluding your home objective): 3VP."

    Reads the turn-start snapshot rather than the board, because control at the
    start of the turn is unrecoverable by the time this scores - the whole
    point of taking it. An objective held throughout pays nothing; this box is
    for ground TAKEN."""
    return (UNSTOPPABLE_GAINED_VP
            if any(id(o) not in ctx.objectives_controlled_at_turn_start
                   for o in controlled_non_home_objectives(ctx))
            else 0)


def _unstoppable_central(ctx):
    """"End of battle: you control one or more central objectives: 5VP." See
    mission_context.central_objectives() for what "central" means and why it
    cannot be the objective NAMED "Central"."""
    return (UNSTOPPABLE_CENTRAL_VP
            if any(o.controlled_by == ctx.player for o in central_objectives(ctx))
            else 0)


UNSTOPPABLE_FORCE = PrimaryMission(
    key="unstoppable_force",
    name="Unstoppable Force",
    force_disposition=force_dispositions.PURGE_THE_FOE,
    text=(
        "End of your turn: 3VP if one or more enemy units were destroyed this turn. From "
        "the second battle round, at the end of your Command phase: 4VP for each "
        "objective you control other than your home objective; and at the end of your "
        "turn, 3VP if you control one or more objectives (other than your home "
        "objective) that you did not control at the start of the turn. At the end of the "
        "battle: 5VP if you control one or more central objectives."
    ),
    boxes=[
        ScoringBox("kills", TIMING_END_OF_YOUR_TURN, _unstoppable_kills, "KILLS",
                   "%d" % UNSTOPPABLE_KILL_VP),
        ScoringBox("objectives", TIMING_END_OF_COMMAND_PHASE, _unstoppable_objectives,
                   "OBJECTIVES", "%d/obj" % UNSTOPPABLE_PER_OBJECTIVE_VP,
                   min_round=SECOND_ROUND_ONWARD),
        ScoringBox("gained", TIMING_END_OF_YOUR_TURN, _unstoppable_gained,
                   "GAINED", "%d" % UNSTOPPABLE_GAINED_VP,
                   min_round=SECOND_ROUND_ONWARD),
        ScoringBox("central", TIMING_END_OF_BATTLE, _unstoppable_central, "CENTRAL",
                   "%d" % UNSTOPPABLE_CENTRAL_VP),
    ],
)


# --------------------------------------------- SECURE ASSET (PRIORITY ASSETS)
SECURE_ASSET_SECURED_VP = 4
SECURE_ASSET_KILL_VP = 2
SECURE_ASSET_ONE_OBJECTIVE_VP = 4
SECURE_ASSET_THREE_OBJECTIVES_VP = 4
SECURE_ASSET_THREE_NEEDED = 3
SECURE_ASSET_SLOT = "secured_this_turn"


def secure_asset_units(squad, ctx):
    """"UNITS: One friendly unit within range of an objective (excluding your
    home objective)." Word for word Cleanse's UNITS line."""
    if squad.owner != ctx.player:
        return False
    return bool(secure_asset_targets_for(squad, ctx))


def secure_asset_targets_for(squad, ctx):
    return [o for o in _non_home_objectives(ctx)
            if is_within_range_of_objective(squad, [o])]


def secure_asset_use_limit(started, squad, target, ctx):
    """"USE LIMIT: Once per turn." - one Secure Asset action in the whole turn,
    not one per unit. Plunder's form, NOT Cleanse's, even though the rest of
    this action is Cleanse: Cleanse is unlimited-but-one-per-objective."""
    return not any(s.definition.key == "secure_asset" for s in started)


def secure_asset_completes(state, ctx):
    """"COMPLETES: End of your turn, if your unit controls that objective."

    Same pair Cleanse and Burden of Trust's guards read: the unit still within
    range AND its owner holding the objective (14.02). That is the reading
    under which "your unit controls it" is something a single unit can be
    responsible for."""
    objective = state.target
    if objective is None or not state.squad.models:
        return False
    if objective.controlled_by != state.squad.owner:
        return False
    return is_within_range_of_objective(state.squad, [objective])


SECURE_ASSET_ACTION = ActionDefinition(
    key="secure_asset",
    result_slot=SECURE_ASSET_SLOT,
    name="Secure Asset",
    starts=PHASE_SHOOTING,           # "STARTS: Your Shooting phase."
    units=secure_asset_units,
    completes=secure_asset_completes,
    # "EFFECT: Your unit secures the asset." - deliberately no callback, the
    # same reasoning Cleanse writes out: completing the action IS the effect,
    # and resolve_end_of_turn() already reports which ones completed. A second
    # record of the same fact is a second record free to disagree.
    effect=None,
    use_limit=secure_asset_use_limit,
    target_options=lambda squad, ctx: [(o.name, o) for o in secure_asset_targets_for(squad, ctx)],
)


def _secure_asset_secured(ctx):
    """"A friendly unit secured the asset this turn: 4VP." One action per turn,
    so this is a yes/no rather than a count."""
    return SECURE_ASSET_SECURED_VP if ctx.card_state.get(SECURE_ASSET_SLOT) else 0


def _secure_asset_kill(ctx):
    """"At least one enemy unit that started the turn within range of one or
    more central objectives was destroyed: 2VP."

    Reads the turn-start snapshot: by the time this scores the unit is off the
    board and where it stood is gone with it."""
    marked = ctx.on_central_objective_at_turn_start
    return (SECURE_ASSET_KILL_VP
            if any(id(sq) in marked for sq in enemy_units_destroyed_this_turn(ctx))
            else 0)


def _secure_asset_one_objective(ctx):
    return SECURE_ASSET_ONE_OBJECTIVE_VP if controlled_non_home_objectives(ctx) else 0


def _secure_asset_three_objectives(ctx):
    """"You control three or more objectives: 4VP."

    NO "(excluding your home objective)" on this row, where the row directly
    above it has one - so your home objective counts towards the three. The two
    rows sit in the same printed band and look alike; the difference is one
    parenthesis and it is worth its own test line.

    They also STACK: both are separate rows of the same "2ND ROUND ONWARD / END
    OF CMD PHASE" band, so holding three including your home pays 4 + 4."""
    return (SECURE_ASSET_THREE_OBJECTIVES_VP
            if len(controlled_objectives(ctx)) >= SECURE_ASSET_THREE_NEEDED else 0)


SECURE_ASSET = PrimaryMission(
    key="secure_asset",
    name="Secure Asset",
    force_disposition=force_dispositions.PRIORITY_ASSETS,
    text=(
        "End of your turn: 4VP if a friendly unit secured the asset this turn, and 2VP if "
        "at least one enemy unit that started the turn within range of a central objective "
        "was destroyed. From the second battle round, at the end of your Command phase: "
        "4VP if you control one or more objectives other than your home objective, and a "
        "further 4VP if you control three or more objectives. Secure Asset is an OBJECTIVE "
        "ACTION started once per turn in your Shooting phase by a unit within range of an "
        "objective other than your home objective; it completes at the end of your turn if "
        "that unit controls that objective."
    ),
    boxes=[
        ScoringBox("secured", TIMING_END_OF_YOUR_TURN, _secure_asset_secured, "SECURED",
                   "%d" % SECURE_ASSET_SECURED_VP),
        ScoringBox("kill", TIMING_END_OF_YOUR_TURN, _secure_asset_kill, "KILL",
                   "%d" % SECURE_ASSET_KILL_VP),
        ScoringBox("one_objective", TIMING_END_OF_COMMAND_PHASE, _secure_asset_one_objective,
                   "OBJECTIVE", "%d" % SECURE_ASSET_ONE_OBJECTIVE_VP,
                   min_round=SECOND_ROUND_ONWARD),
        ScoringBox("three_objectives", TIMING_END_OF_COMMAND_PHASE,
                   _secure_asset_three_objectives, "THREE OBJ",
                   "+%d" % SECURE_ASSET_THREE_OBJECTIVES_VP,
                   min_round=SECOND_ROUND_ONWARD),
    ],
    action=SECURE_ASSET_ACTION,
)


# ------------------------------------------------- DEATH TRAP (DISRUPTION)
DEATH_TRAP_PER_AREA_VP = 2
DEATH_TRAP_OBJECTIVE_AREA_BONUS_VP = 3
DEATH_TRAP_KILL_VP = 3
DEATH_TRAP_OBJECTIVE_VP = 4
# Two slots, two lifetimes, and keeping them apart is the whole of Death Trap's
# bookkeeping. "trapped" is the set of areas trapped SO FAR IN THE BATTLE - the
# action's UNITS line says "that is not yet trapped", so it must outlive the
# turn. "trapped_this_turn" is what the 2 VP box counts, and is cleared at each
# turn end after scoring. Folding them into one would either let the same area
# be trapped every turn for 2 VP a go, or make the second turn's traps invisible.
DEATH_TRAP_SLOT = "trapped_this_turn"
DEATH_TRAP_ALL_SLOT = "trapped"


def trapped_areas(ctx):
    """The terrain areas trapped so far this battle, in the order they were
    trapped. Kept in the mission's own state rather than on the TerrainArea
    (which carries no state at all) and rather than derived from the completed
    ActionStates the way Plunder does it - ActionController.reset_for_turn()
    empties those every turn, and being trapped outlives the turn."""
    return list((ctx.card_state.get(DEATH_TRAP_ALL_SLOT) or {}).values())


def area_is_trapped(ctx, area):
    return id(area) in (ctx.card_state.get(DEATH_TRAP_ALL_SLOT) or {})


def area_is_an_objective(ctx, area):
    """Whether this terrain area carries an objective marker.

    Identity, not geometry: GameState.add_objective() hands the Objective the
    very TerrainArea it registered in state.terrain_areas, so the two lists
    share objects."""
    return any(o.terrain_area is area for o in ctx.objectives)


def _area_outside_own_deployment_zone(ctx, area):
    """"...a terrain area outside your deployment zone". Measured at the area's
    bounding-box centre, the same way plunderable_areas() and every objective
    classification in this codebase measure an area's location."""
    min_x, min_y, max_x, max_y = area.bounding_box
    cx, cy = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0
    mine = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    return not any(z.contains_point(cx, cy) for z in mine)


def booby_trap_targets_for(squad, ctx):
    """The terrain areas this unit could trap.

    The printed UNITS line is: "One friendly unit within range of an objective
    (excluding your home objective), OR within a terrain area outside your
    deployment zone that is not yet trapped."

    Two branches, and BOTH name a terrain area, which is what makes the EFFECT
    ("that terrain area is trapped") well defined and gives the +3 VP clause
    ("for each of those terrain areas that is an objective") something to bite
    on: an objective IS a terrain area here. So branch one contributes the
    terrain areas of the non-home objectives the unit is within range of, and
    branch two the areas outside your own deployment zone the unit is standing
    in. Already-trapped areas drop out of both - trapping one twice is what
    "not yet trapped" forbids, and it would pay 2 VP a turn for standing still.
    """
    if squad.owner != ctx.player:
        return []
    out = []
    for objective in _non_home_objectives(ctx):
        if is_within_range_of_objective(squad, [objective]):
            out.append(objective.terrain_area)
    for area in ctx.terrain_areas:
        if not _area_outside_own_deployment_zone(ctx, area):
            continue
        if any(area.overlaps_model(m) for m in squad.models):
            out.append(area)
    seen, unique = set(), []
    for area in out:
        if id(area) in seen or area_is_trapped(ctx, area):
            continue
        seen.add(id(area))
        unique.append(area)
    return unique


def booby_trap_units(squad, ctx):
    return bool(booby_trap_targets_for(squad, ctx))


def booby_trap_use_limit(started, squad, target, ctx):
    """"USE LIMIT: Unlimited. Each unit initiating this action this phase must
    be within a different terrain area."

    So the limit is a uniqueness rule on the TARGET, not a cap on the number of
    actions - Cleanse's shape rather than Plunder's, even though the rest of
    this action is Plunder's. "This phase" and "this turn" are the same window
    here (the action only starts in your Shooting phase, of which there is one
    per turn), which is why reading ActionController's per-TURN state list is
    faithful; a second Shooting phase in a turn would need this revisited."""
    if target is None:
        return False
    return not any(s.target is target for s in started if not s.broken)


def _booby_trap_effect(state, ctx):
    """"EFFECT: That terrain area is trapped - place one of your operation
    markers within that terrain area."

    Unlike Cleanse and Plunder this action DOES have a callback, because being
    trapped is a lasting fact about the board rather than a fact about this
    turn's completions. It runs the instant the action starts (the action
    completes immediately), so a later unit this same phase already sees the
    area as trapped."""
    area = state.target
    if area is None:
        return
    ctx.card_state.setdefault(DEATH_TRAP_ALL_SLOT, {})[id(area)] = area
    ctx.card_state.setdefault(DEATH_TRAP_SLOT, []).append(area)


BOOBY_TRAP_ACTION = ActionDefinition(
    key="booby_trap",
    result_slot="booby_trapped_this_turn",  # unused: the effect records it directly
    name="Booby Trap",
    starts=PHASE_SHOOTING,           # "STARTS: Your Shooting phase."
    units=booby_trap_units,
    completes=lambda state, ctx: True,   # "COMPLETES: Immediately."
    completes_immediately=True,
    effect=_booby_trap_effect,
    use_limit=booby_trap_use_limit,
    target_options=lambda squad, ctx: [
        (_area_label(ctx, area), area) for area in booby_trap_targets_for(squad, ctx)
    ],
)


def _area_label(ctx, area):
    """A terrain area has no name of its own, so one is built from what it is
    and where it is. Naming the objective when there is one matters: those are
    the areas worth 5 VP instead of 2."""
    for objective in ctx.objectives:
        if objective.terrain_area is area:
            return objective.name
    cx, cy = _area_centre(area)
    return "Terrain area at (%.0f, %.0f)" % (cx, cy)


def _area_centre(area):
    min_x, min_y, max_x, max_y = area.bounding_box
    return ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)


def _death_trap_traps(ctx):
    """"For each terrain area trapped this turn: 2VP. + CUMULATIVE: for each of
    those terrain areas that is an objective: +3VP."

    CUMULATIVE again, so an objective area pays 5 and a plain one 2."""
    total = 0
    for area in (ctx.card_state.get(DEATH_TRAP_SLOT) or ()):
        total += DEATH_TRAP_PER_AREA_VP
        if area_is_an_objective(ctx, area):
            total += DEATH_TRAP_OBJECTIVE_AREA_BONUS_VP
    return total


def _death_trap_kill(ctx):
    """"At least one enemy unit that started the turn in a terrain area has
    been destroyed, provided that terrain area is trapped: 3VP."

    Both halves come from different places on purpose: WHERE the unit stood is
    the turn-start snapshot (it is dead now), while WHETHER that area is
    trapped is read live, because an area trapped on an earlier turn is still
    trapped now - "is trapped", present tense, with no "this turn"."""
    trapped = ctx.card_state.get(DEATH_TRAP_ALL_SLOT) or {}
    if not trapped:
        return 0
    for squad in enemy_units_destroyed_this_turn(ctx):
        for area_id in ctx.in_terrain_at_turn_start.get(id(squad), ()):
            if area_id in trapped:
                return DEATH_TRAP_KILL_VP
    return 0


def _death_trap_objective(ctx):
    return DEATH_TRAP_OBJECTIVE_VP if controlled_non_home_objectives(ctx) else 0


DEATH_TRAP = PrimaryMission(
    key="death_trap",
    name="Death Trap",
    force_disposition=force_dispositions.DISRUPTION,
    text=(
        "End of your turn: 2VP for each terrain area trapped this turn, plus a cumulative "
        "3VP for each of those terrain areas that is an objective; and 3VP if at least one "
        "enemy unit that started the turn in a trapped terrain area was destroyed. From the "
        "second battle round, at the end of your Command phase: 4VP if you control one or "
        "more objectives other than your home objective. Booby Trap is an OBJECTIVE ACTION "
        "started in your Shooting phase by a unit within range of an objective other than "
        "your home objective, or standing in an untrapped terrain area outside your "
        "deployment zone; it completes immediately and traps that terrain area for the rest "
        "of the battle."
    ),
    boxes=[
        ScoringBox("traps", TIMING_END_OF_YOUR_TURN, _death_trap_traps, "TRAPS",
                   "%d/area, +%d" % (DEATH_TRAP_PER_AREA_VP,
                                     DEATH_TRAP_OBJECTIVE_AREA_BONUS_VP)),
        ScoringBox("kill", TIMING_END_OF_YOUR_TURN, _death_trap_kill, "KILL",
                   "%d" % DEATH_TRAP_KILL_VP),
        ScoringBox("objective", TIMING_END_OF_COMMAND_PHASE, _death_trap_objective,
                   "OBJECTIVE", "%d" % DEATH_TRAP_OBJECTIVE_VP,
                   min_round=SECOND_ROUND_ONWARD),
    ],
    action=BOOBY_TRAP_ACTION,
)


# ---------------------------------------------------------------- registry
# One mission per Force Disposition, keyed on it - the disposition IS the
# choice, and there is nothing else to look a mission up by. A sixth cannot
# appear without moving test_primary_missions.py's count.
ALL_MISSIONS = [BATTLEFIELD_DOMINANCE, RECONNAISSANCE_SWEEP, UNSTOPPABLE_FORCE,
                SECURE_ASSET, DEATH_TRAP]

BY_DISPOSITION = {mission.force_disposition: mission for mission in ALL_MISSIONS}


def mission_for(disposition):
    """The Primary Mission a Force Disposition names, or None for an unknown
    one. None rather than raising: this is read on the render path (the mission
    strip), where a stale setting should show no card rather than kill a frame.
    game/detachments.py's validate() is what makes a bad disposition loud."""
    return BY_DISPOSITION.get(disposition)


def card_players():
    """Who plays a Force Disposition Primary instead of "Hold the Line". Read
    from config at CALL time, never imported by value, so a harness that
    empties the tuple really turns it off."""
    from game import config
    return tuple(config.PRIMARY_MISSION_CARD_PLAYERS)


class PrimaryMissionController:
    """Runs ONE player's Force Disposition Primary Mission.

    Shaped like SecondaryMissionController next door - the same lazily-read
    `set_*_source()` callables, the same per-mission scratchpad, the same "no-op
    entirely when this player is not playing one" property - with the
    differences that follow from a Primary not being a card game: there is no
    deck, no hand, no discard, and no prompt. Its boxes simply score at their
    own instants.
    """

    def __init__(self, player="Player 1", mission_controller=None, turn_tracker=None,
                 game_log=None, mission=None, action_controller=None):
        self.player = player
        self.mission_controller = mission_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.action_controller = action_controller
        # Normally resolved from the army list's declared disposition (see the
        # `mission` property); passed in directly by tests, which have no army
        # list and should not have to build one to score a box.
        self._mission_override = mission
        # The mission's own scratchpad - what Death Trap has trapped, whether
        # Secure Asset's action completed. Owned HERE and handed to predicates
        # as ctx.card_state, never written onto the PrimaryMission objects:
        # those are module-level singletons shared by every battle, which is the
        # shared-class-attribute trap this codebase documents for UnitProfile
        # and for SecondaryMissionCard.
        self.card_state = {}
        self.points = 0                # this player's running Primary VP, for the strip
        self._destroyed_squads_this_turn = []
        self._destroyed_squad_ids = set()
        self._on_central_objective_at_turn_start = set()
        self._in_terrain_at_turn_start = {}
        self._objectives_controlled_at_turn_start = set()
        self._battle_scored = False    # the end-of-battle boxes pay once
        self._announced = False
        self._tokens_source = None
        self._squads_source = None
        self._objectives_source = None
        self._zones_source = None
        self._terrain_source = None

    # ------------------------------------------------------------- sources

    def set_tokens_source(self, source):
        self._tokens_source = source

    def set_squads_source(self, source):
        self._squads_source = source

    def set_objectives_source(self, source):
        self._objectives_source = source

    def set_zones_source(self, source):
        self._zones_source = source

    def set_terrain_source(self, source):
        self._terrain_source = source

    def set_action_controller(self, controller):
        self.action_controller = controller

    def _tokens(self):
        return list(self._tokens_source()) if self._tokens_source else []

    def _objectives(self):
        return list(self._objectives_source()) if self._objectives_source else []

    def _zones(self):
        return list(self._zones_source()) if self._zones_source else []

    def _terrain(self):
        return list(self._terrain_source()) if self._terrain_source else []

    # ------------------------------------------------------------- identity

    @property
    def plays_card(self):
        return self.player in card_players()

    @property
    def mission(self):
        """This player's Primary, from the Force Disposition their army list
        declares. Looked up on every read rather than cached, so choosing a
        different list really changes the mission; the army_lists import is
        function-local because that module pulls in every faction and this one
        is read from the render path."""
        if self._mission_override is not None:
            return self._mission_override
        from game import army_lists
        return mission_for(army_lists.force_disposition_for(self.player))

    # -------------------------------------------------------------- context

    def _context(self, ending_player=None, battle_round=None):
        return MissionContext(
            self.player,
            tokens=self._tokens(),
            turn_tracker=self.turn_tracker,
            ending_player=ending_player,
            destroyed_squads_this_turn=list(self._destroyed_squads_this_turn),
            all_squads=(self._squads_source() if self._squads_source else None),
            objectives=self._objectives(),
            deployment_zones=self._zones(),
            terrain_areas=self._terrain(),
            card_state=self.card_state,
            battle_round=battle_round,
            on_central_objective_at_turn_start=self._on_central_objective_at_turn_start,
            in_terrain_at_turn_start=self._in_terrain_at_turn_start,
            objectives_controlled_at_turn_start=self._objectives_controlled_at_turn_start,
        )

    # ----------------------------------------------------------- turn start

    def snapshot_turn_start(self):
        """Record the three facts about THIS instant that three boxes ask about
        later, when they are no longer recoverable.

        Taken at the top of EVERY turn, either player's, and unconditionally:
        two of the three are about enemy units that will be dead by scoring
        time, and whether any box needs them is not knowable now. Same shape
        and the same reason as SecondaryMissionController.snapshot_turn_start()
        (Overwhelming Force)."""
        if not self.plays_card:
            return
        ctx = self._context()
        enemies = [sq for sq in _live_squads(ctx.tokens) if sq.owner != self.player]

        central = central_objectives(ctx)
        self._on_central_objective_at_turn_start = {
            id(sq) for sq in enemies
            if central and is_within_range_of_objective(sq, central)
        }

        areas = self._terrain()
        in_terrain = {}
        for squad in enemies:
            standing_in = frozenset(
                id(area) for area in areas
                if any(area.overlaps_model(m) for m in squad.models))
            if standing_in:
                in_terrain[id(squad)] = standing_in
        self._in_terrain_at_turn_start = in_terrain

        self._objectives_controlled_at_turn_start = {
            id(o) for o in ctx.objectives if o.controlled_by == self.player
        }

    def record_destroyed_squad(self, squad):
        """Fed from main.py's dead-model sweep, from its own
        attached_units.unit_is_destroyed() branch - the same feed
        MissionController and the Secondary deck take. Idempotent per squad by
        identity, because the sweep reaches an already-emptied squad again on
        the next dead model in the same frame.

        There is deliberately no record_destroyed_model() twin: not one of the
        sixteen boxes counts MODELS. Bring It Down needed one; nothing here
        does, and an unused feed is a wire that rots."""
        if not self.plays_card or squad is None:
            return
        if id(squad) in self._destroyed_squad_ids:
            return
        self._destroyed_squad_ids.add(id(squad))
        self._destroyed_squads_this_turn.append(squad)

    # ---------------------------------------------------------- rule 16.01

    def available_actions_for(self, squad):
        """[(label, action, target), ...] - what this unit could start now.

        Same contract and same gates as
        SecondaryMissionController.available_actions_for(): the left panel
        turns each into a button beside the unit's other options."""
        mission = self.mission
        if (not self.plays_card or squad is None or self.action_controller is None
                or mission is None or mission.action is None):
            return []
        turn_tracker = self.turn_tracker
        if turn_tracker is not None and turn_tracker.turn_owner != self.player:
            return []
        action = mission.action
        if turn_tracker is not None and turn_tracker.phase != action.starts:
            return []          # the action's own STARTS line
        ctx = self._context()
        ok, _reason = self.action_controller.can_start(action, squad, ctx)
        if not ok:
            return []
        return [("%s: %s" % (action.name, label), action, target)
                for label, target in action.target_options(squad, ctx)
                if action.use_limit_allows(self.action_controller.states, squad, target, ctx)]

    def start_action(self, action, squad, target):
        """Begin one action - the panel button's callback."""
        if self.action_controller is None:
            return None
        return self.action_controller.start(action, squad, target, self._context())

    def _resolve_actions(self, ending_player):
        """Complete this turn's actions and record what finished.

        Runs BEFORE the boxes are scored: Secure Asset's whole 4 VP comes from
        what completed at this instant. resolve_end_of_turn() is idempotent per
        player per turn, so this and the Secondary deck's identical call can
        both ask without firing any EFFECT twice."""
        mission = self.mission
        if self.action_controller is None or mission is None or mission.action is None:
            return
        completed = self.action_controller.resolve_end_of_turn(ending_player, self._context())
        done = [state.target for state in completed
                if state.definition is mission.action and state.target is not None]
        # Booby Trap records itself in its EFFECT, because being trapped
        # outlives the turn; only an action whose completions are a fact ABOUT
        # this turn is stored here.
        if not mission.action.completes_immediately:
            self.card_state[mission.action.result_slot] = done

    # --------------------------------------------------------- the instants

    def _score_boxes(self, timing, ctx, battle_round):
        """Score every box at `timing` whose round band allows it. Automatic -
        see the module docstring on why there is no prompt."""
        mission = self.mission
        if mission is None:
            return 0
        gained = 0
        for box in mission.boxes_at(timing):
            if not box.in_round_band(battle_round):
                continue
            points = box.score(ctx)
            if points <= 0:
                continue
            gained += points
            self._log("%s scores %d Primary VP (%s - %s)."
                      % (self.player, points, mission.name, box.label))
        if gained and self.mission_controller is not None:
            self.mission_controller.add_primary_points(self.player, gained)
        self.points += gained
        return gained

    def begin_end_of_turn(self, ending_player, battle_round=None):
        """The "END OF YOUR TURN" boxes, then this turn's bookkeeping is reset.

        Called at BOTH players' turn ends - the boxes themselves say which
        applies, exactly as the Secondary cards do - so the reset happens on
        every turn boundary and a kill made in the opponent's turn cannot be
        carried into yours. That is what "destroyed this turn" means on a box
        checked at the end of YOUR turn."""
        if not self.plays_card:
            self._clear_turn()
            return 0
        self._resolve_actions(ending_player)
        gained = 0
        if ending_player == self.player:
            ctx = self._context(ending_player=ending_player, battle_round=battle_round)
            gained = self._score_boxes(TIMING_END_OF_YOUR_TURN, ctx, battle_round)
        self._clear_turn()
        return gained

    def end_of_command_phase(self, phase_owner, battle_round=None):
        """The "END OF CMD PHASE" boxes, for the player whose Command phase
        just ended.

        The END and not the start, which is what every one of these cards
        prints and is NOT the instant "Hold the Line" uses: Battle Shock is
        resolved in between, and a battle-shocked unit's OC drops to a dash
        (01.07/02.02), so who controls what can differ between the two."""
        if not self.plays_card or phase_owner != self.player:
            return 0
        ctx = self._context(battle_round=battle_round)
        return self._score_boxes(TIMING_END_OF_COMMAND_PHASE, ctx, battle_round)

    def score_end_of_battle(self):
        """The "FINAL SCORING" boxes, once.

        Idempotent because main.py's _check_battle_end() is reached on every
        frame after the battle ends, exactly like BattleEndOverlay.show()."""
        if not self.plays_card or self._battle_scored:
            return 0
        self._battle_scored = True
        ctx = self._context()
        return self._score_boxes(TIMING_END_OF_BATTLE, ctx, None)

    def _clear_turn(self):
        self._destroyed_squads_this_turn = []
        # What was trapped THIS TURN, which is what the 2 VP box counts. The
        # battle-long DEATH_TRAP_ALL_SLOT is deliberately untouched.
        self.card_state.pop(DEATH_TRAP_SLOT, None)
        self.card_state.pop(SECURE_ASSET_SLOT, None)

    # ---------------------------------------------------------- the display

    def trapped_areas_on_board(self):
        """The terrain areas to draw an operation marker on - Death Trap's
        trapped ones, and an empty list for every other mission.

        A method rather than the renderer reaching into card_state, so the
        render path asks one question and gets an answer whatever mission is
        being played. Cheap: it is a dict lookup, run once a frame."""
        if not self.plays_card or self.mission is not DEATH_TRAP:
            return []
        return list((self.card_state.get(DEATH_TRAP_ALL_SLOT) or {}).values())

    # -- saving and restoring (game/scene_io.py) ---------------------------
    #
    # Same rule as the Secondary deck next door: a card_state key ending in
    # _this_turn is turn-scoped and is left out, because the autosave is taken
    # at a battle-round boundary where all of them are empty. What outlives a
    # turn is the running VP, the two once-per-battle latches, and Death Trap's
    # `trapped` set - whose UNITS line says "not yet trapped", so it has to
    # survive or the same ground could be trapped again every round.
    #
    # `trapped` is keyed by id(area), which means nothing after a rebuild, and
    # a TerrainArea has no name to key on instead. It is stored as INDICES into
    # state.terrain_areas: those are produced deterministically by
    # battle_map.build() from the map key, and the snapshot pins the map key,
    # so the same index is the same piece of ground.
    def save_state(self):
        trapped = self.card_state.get(DEATH_TRAP_ALL_SLOT) or {}
        areas = list(self._terrain_source()) if self._terrain_source else []
        index_of = {id(area): i for i, area in enumerate(areas)}
        return {
            "points": self.points,
            "battle_scored": self._battle_scored,
            "announced": self._announced,
            "trapped": sorted(index_of[key] for key in trapped if key in index_of),
        }

    def load_state(self, data):
        problems = []
        self.points = data.get("points") or 0
        self._battle_scored = bool(data.get("battle_scored"))
        self._announced = bool(data.get("announced"))
        areas = list(self._terrain_source()) if self._terrain_source else []
        trapped = {}
        for index in data.get("trapped") or ():
            if not isinstance(index, int) or not 0 <= index < len(areas):
                problems.append(f"the snapshot traps terrain area #{index}, "
                                f"which this scene does not have")
                continue
            trapped[id(areas[index])] = areas[index]
        if trapped:
            self.card_state[DEATH_TRAP_ALL_SLOT] = trapped
        return problems

    def detail(self):
        """One line of state the printed prose cannot carry, for the mission
        strip - which areas are trapped, whether the asset was secured. None
        when this mission has nothing to remember."""
        mission = self.mission
        if mission is None:
            return None
        if mission is DEATH_TRAP:
            ctx = self._context()
            trapped = trapped_areas(ctx)
            if not trapped:
                return "Nothing trapped yet. Start Booby Trap in your Shooting phase."
            return "Trapped: " + ", ".join(_area_label(ctx, a) for a in trapped)
        if mission is SECURE_ASSET:
            secured = self.card_state.get(SECURE_ASSET_SLOT) or ()
            if not secured:
                return "Asset not secured this turn. Start Secure Asset in your Shooting phase."
            return "Secured this turn: " + ", ".join(o.name for o in secured)
        return None

    def announce(self):
        """Log which Primary each player is on, once.

        The disposition is a list-building declaration and appears nowhere on
        the board, so without this line a log cannot be matched to the mission
        that was being played - the same reason the map and biome get a [setup]
        line.

        It also names a violated assumption rather than hiding it: all five
        cards are the deck for a game whose OPPONENT plays Take and Hold, and an
        AI list declaring something else is mispriced rather than broken."""
        if self._announced:
            return
        self._announced = True
        from game import army_lists
        mission = self.mission
        if mission is not None:
            self._log("[primary] %s plays %s (Force Disposition: %s)."
                      % (self.player, mission.name, mission.disposition_label),
                      file_only=True)
        opponent = _other_player(self.player)
        theirs = army_lists.force_disposition_for(opponent)
        if theirs and theirs != force_dispositions.TAKE_AND_HOLD:
            self._log("[primary] NOTE: %s Force Disposition is %s, not Take and Hold - "
                      "these Primary cards are the set for a Take and Hold opponent."
                      % (opponent, force_dispositions.label(theirs)), file_only=True)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)
