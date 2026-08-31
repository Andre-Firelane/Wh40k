"""Aeldari (ASURYANI) army rule: Battle Focus and its Agile Manoeuvres, as
supplied by the user.

    "If your Army Faction is ASURYANI, at the start of the battle round, you
     receive a number of Battle Focus tokens based on the battle size
     (Incursion 2 / Strike Force 4 / Onslaught 6).

     Each time one of the triggers shown in the Agile Manoeuvres section
     occurs, you can spend one Battle Focus token to enable the relevant
     eligible unit to perform that Agile Manoeuvre. A unit is eligible to
     perform an Agile Manoeuvre if it has this ability and has not already
     performed an Agile Manoeuvre in the same phase. Unless otherwise stated,
     you cannot trigger the same Agile Manoeuvre more than once per phase. At
     the end of the battle round, all unspent Battle Focus tokens are lost."

WHY THIS IS NOT StratagemController
-----------------------------------
It looks like the 15.01 ledger and is not: that one tracks "this stratagem once
per phase" plus "this unit targeted once per phase" for stratagems that cost
CP. Battle Focus has its own currency AND its restrictions are two independent
axes that both have to hold:

  * per UNIT - a unit is out for the rest of the phase after ANY manoeuvre,
    not just after this one, and
  * per MANOEUVRE - the same manoeuvre cannot fire twice in a phase, unless
    the manoeuvre itself says otherwise.

Swift as the Wind is the one that says otherwise ("provided a different unit
performs it each time") - and that proviso needs no code of its own, because
the per-unit axis already forbids the same unit doing it twice.

WHY THE EFFECTS ARE FLAGS ON THE SQUAD
--------------------------------------
Same reason Squad.stim_injectors_active is one: a flag reaches every reader,
whereas a controller has to be threaded into each one and the ones nobody
remembered to thread stay silently wrong (game/waaagh.py's conditional Feel No
Pain documents four damage sources it never reached for exactly this reason).
Here the readers are spread across five modules - the Move characteristic, the
[ASSAULT] grant, Fire Overwatch's target check, the pile-in range and the
consolidation range - and none of them should have to know this rule exists.

ALL SIX MANOEUVRES ARE HERE
---------------------------
Swift as the Wind, Flitting Shadows and Star Engines hang off the Movement
phase. Sudden Strike is bought before a unit is selected to fight. Opportunity
Seized and Fade Back are the two that fire in the OPPONENT's turn, and they are
the awkward ones: both grant a Normal move to a unit whose owner is not the
active player, which MovementController.select() refuses outside the Fight
phase - see _perform_reactive() for how that is handled and why it is not
cosmetic.

WHAT IS DELIBERATELY NOT WIRED
------------------------------
Flitting Shadows lists three triggers: a Normal/Advance/Fall Back move, being
set up on the battlefield, and declaring a charge. Only the move trigger is
offered, because in THIS engine Fire Overwatch (15.08) is offered from exactly
one place - main.py, right after a unit's Movement phase ends. There is no
overwatch window on a charge declaration or on arriving from Reserves, so
spending a token to be protected in those two moments would buy a guaranteed
nothing, which is worse than not offering it. If overwatch ever gains such a
window, the trigger belongs here and the two grant helpers already exist.

The AI never uses any of this: Aeldari are a human-only faction per the user
("die werden ausschliesslich vom menschlichen spieler gespielt"), so there is
no ai/agent_driver.py path and none is wanted.
"""

from game import attached_units  # no imports of its own, so this cannot cycle
from game import enh_timeless_strategist
from game import config
from game import martial_grace
from game.turn import PHASE_MOVEMENT, PHASE_FIGHT, PHASE_SHOOTING  # game/turn.py imports nothing, so this cannot cycle

# Battle sizes and their token counts, from the rule's own table.
TOKENS_BY_BATTLE_SIZE = {
    "incursion": 2,
    "strike_force": 4,
    "onslaught": 6,
}

SWIFT_AS_THE_WIND = "Swift as the Wind"
FLITTING_SHADOWS = "Flitting Shadows"
STAR_ENGINES = "Star Engines"
SUDDEN_STRIKE = "Sudden Strike"
OPPORTUNITY_SEIZED = "Opportunity Seized"
FADE_BACK = "Fade Back"

# "Unless otherwise stated, you cannot trigger the same Agile Manoeuvre more
# than once per phase" - the manoeuvres that DO state otherwise.
REPEATABLE_PER_PHASE = frozenset({SWIFT_AS_THE_WIND})

SWIFT_AS_THE_WIND_BONUS_IN = 2.0

# Sudden Strike: "each time a model in that unit makes a Pile-in or
# Consolidation move, it can move up to 6" instead of up to 3"".
SUDDEN_STRIKE_RANGE_IN = 6.0

# Opportunity Seized and Fade Back both grant "a Normal move of up to D6+1"".
REACTIVE_MOVE_BONUS_IN = 1.0

# Both reactive manoeuvres exclude TITANIC units. No datasheet in this engine
# declares that keyword, so the check reads the datasheet keyword line rather
# than inventing a UnitProfile field - the same route 'Ard as Nails takes for
# GROTS, and it starts working by itself the day a TITANIC datasheet exists.
REACTIVE_EXCLUDED_KEYWORD = "TITANIC"


def tokens_for_battle_size(battle_size=None):
    """Token count for a battle size, defaulting to config.BATTLE_SIZE.

    An unknown size falls back to Strike Force rather than to zero: zero would
    make the whole army rule silently inert, which reads exactly like a bug in
    the rule instead of like a typo in a setting."""
    key = (battle_size or config.BATTLE_SIZE or "").strip().lower().replace(" ", "_")
    return TOKENS_BY_BATTLE_SIZE.get(key, TOKENS_BY_BATTLE_SIZE["strike_force"])


def has_battle_focus(squad):
    """Does this unit have the Battle Focus ability?

    The all-models form of rule 19.04, spelled out rather than calling
    game/squad.py's unit_wide_ability(): game/squad.py imports
    game/coldstar.py, which imports this module for the Move characteristic
    bonus, so importing squad.py back from here would close a cycle."""
    models = getattr(squad, "models", None)
    if bool(models) and all(
        getattr(m.profile, "battle_focus", False) for m in models
    ):
        return True
    # Spirit Conclave's Spirit Guides aura - the first TEMPORARY source of the
    # army rule, granted to a wraith unit standing within 12" of a friendly
    # ASURYANI PSYKER. It folds in here because this is the one place that
    # answers "does this unit have Battle Focus"; anywhere else and the pool,
    # the manoeuvres and this function could disagree.
    #
    # A near-no-op on the built roster - all three named datasheets already
    # print the ability - so it is written for the rule rather than for the
    # roster, and pinned with a unit that does not print it.
    grant = getattr(squad, "spirit_guides_source", None)
    return bool(grant is not None and grant.spirit_guides_reaches(squad))


def qualifying_players(squads):
    """Which players' armies count as ASURYANI for this rule.

    This engine has no army-faction declaration (there is no list-building
    flow at all - see CLAUDE.md's deferred list), so "your Army Faction is
    ASURYANI" is read as "this player's army contains units with the Battle
    Focus ability". Derived rather than configured on purpose: a config
    constant is a thing someone adds an Aeldari datasheet to an army and then
    forgets, and the failure mode is a whole army rule quietly doing nothing.

    Meant to be called ONCE, when the armies are complete and before the
    first grant - army faction is fixed at list-building and does not stop
    being ASURYANI when the last Guardian dies."""
    return tuple(sorted({
        squad.owner for squad in squads
        if squad.owner is not None and has_battle_focus(squad)
    }))


# --------------------------------------------------------------- effects
# Read by other modules. Each one is a plain question about a squad flag, so
# the reader needs neither this controller nor any knowledge of the rule.

def movement_bonus_in(model):
    """Swift as the Wind's addition to a model's Move characteristic.

    A BONUS, not an override - the wording is "add 2 inches to the Move
    characteristic" - so it stacks on top of anything that sets the
    characteristic outright (game/coldstar.py's flat 12 inches is the one
    such source today)."""
    squad = getattr(model, "squad", None)
    if squad is not None and getattr(squad, "swift_as_the_wind_active", False):
        # Warhost's Martial Grace adds "an ADDITIONAL 1 inch" on top of this
        # manoeuvre's own 2", so it is summed rather than substituted - and it
        # is conditional on the manoeuvre being active, which is why it is
        # inside this branch and not beside it.
        from game import martial_grace
        return SWIFT_AS_THE_WIND_BONUS_IN + martial_grace.extra_move_in(squad)
    return 0.0


def grants_assault(squad):
    """Star Engines: do this unit's ranged weapons have [ASSAULT] right now?"""
    return squad is not None and getattr(squad, "star_engines_active", False)


def blocks_fire_overwatch(squad):
    """Flitting Shadows: is this unit currently immune to Fire Overwatch?"""
    return squad is not None and getattr(squad, "flitting_shadows_active", False)


def melee_move_range_in(squad, printed_range_in):
    """Sudden Strike: how far this unit's Pile-in / Consolidation move may go.

    Read by game/pile_in.py and game/consolidate.py in place of their own 3"
    constants, so the manoeuvre cannot be applied to one and forgotten on the
    other. Takes the printed range rather than assuming it, so a caller with a
    different distance still gets a sane answer.

    Deliberately NOT used for game/pile_in.py's PILE_IN_TARGET_RANGE_IN: that
    is a separate constant for a separate question (rule 12.03's BEFORE MOVING
    target range, 5"), not the move distance this manoeuvre changes.
    Consolidation is the opposite case - there the engine derives which enemies
    and objectives are even reachable from the same 3" it moves, so widening
    the move widens those too, which is the reading the user chose."""
    if squad is not None and getattr(squad, "sudden_strike_active", False):
        return max(printed_range_in, SUDDEN_STRIKE_RANGE_IN)
    return printed_range_in


def is_on_the_battlefield(squad):
    """Whether this unit still has a model standing.

    Both halves matter, and the SECOND is the one that was missing (user:
    "Du brauchst nicht nach 'Fadeback' der aeldari zu fragen, wenn der Trupp
    vollstaendig gestorben ist"). Fade Back fires from
    ShootingController.on_squad_finished_shooting, and that hook runs INSIDE
    the activation that did the killing - GameState.remove_dead_models() runs
    once per frame, afterwards. So a unit this very activation wiped out is
    still sitting in `hit_squads` with a full `squad.models` list of corpses,
    and testing `squad.models` alone answers True for it. Measured on a
    10-model unit with every model at 0 wounds: the offer was raised, named
    the dead unit, and taking it would have spent a Battle Focus token.

    `squad.models` empty covers the same unit one frame later, after the
    sweep; `any(not m.is_dead())` covers it before. An empty list makes any()
    False, so one expression covers both."""
    return squad is not None and any(not m.is_dead() for m in squad.models)


def excluded_from_reactive_manoeuvre(squad):
    """Opportunity Seized / Fade Back: "excluding TITANIC units"."""
    return attached_units.unit_has_datasheet_keyword(squad, REACTIVE_EXCLUDED_KEYWORD)


# ------------------------------------------------------------ the account

class BattleFocusPool:
    """The token account plus both usage restrictions.

    `players` is who receives tokens at all - see qualifying_players(). A
    player not in it can never spend, so the rule is inert for a non-Aeldari
    army without any caller having to check."""

    def __init__(self, players=(), battle_size=None, game_log=None,
                 movement_controller=None, turn_tracker=None,
                 squads_provider=None, dice_manager=None,
                 decision_manager=None, fight_controller=None,
                 all_tokens=None):
        self.players = tuple(players)
        self.battle_size = battle_size
        self.game_log = game_log
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        # Optional callable() -> every squad in the battle. The normal path:
        # who counts as ASURYANI is then derived on the first grant instead of
        # having to be handed in at construction time, which the pre-game
        # sequence makes impossible (nothing is on the board, embarked or in
        # reserve yet when the controllers are built). Self-healing on
        # purpose - a caller cannot forget a step that does not exist.
        self._squads_provider = squads_provider
        #: Optional, and only Timeless Strategist reads it: "or any TRANSPORT
        #: it is embarked within is on the battlefield". None means "nothing is
        #: embarked", which is what a headless harness gets.
        self._embarked_provider = None
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.fight_controller = fight_controller
        self.all_tokens = all_tokens
        # Opportunity Seized needs "a unit that STARTED THE PHASE within
        # Engagement Range of that enemy unit" - which is not a question the
        # board can answer once the enemy has finished falling back, since the
        # whole point is that it is no longer there. Snapshotted per phase in
        # reset_phase(): {id(squad): {id(enemy squad), ...}}.
        self._engaged_at_phase_start = {}
        self._reactive_restore_player = None  # whose turn to hand back after a reactive move (see _perform_reactive)
        self.tokens = {player: 0 for player in self.players}
        self._units_this_phase = set()       # id(squad) - ANY manoeuvre, per the per-unit axis
        self._manoeuvres_this_phase = set()  # (player, manoeuvre name)
        self._granted_round = None

    # ------------------------------------------------------ round / phase

    def adopt_players(self, players):
        """Set who receives tokens, once the armies are complete.

        Separate from __init__ because of the pre-game sequence (03.01): with
        deployment enabled, nothing is on the board, embarked or in reserve at
        the moment the controllers are built, so qualifying_players() would
        see an empty army and conclude nobody is ASURYANI. main.py calls this
        from begin_battle(), the same place the army points lines are logged
        and for the same reason."""
        self.players = tuple(players)
        self.tokens = {player: 0 for player in self.players}
        self._granted_round = None

    def set_embarked_source(self, source):
        """The same shape game/secondary_missions.py takes for the same
        question - main.py hands it `lambda: state.embarked_squads`."""
        self._embarked_provider = source

    def _board_squads(self):
        return list(self._squads_provider()) if self._squads_provider else []

    def _embarked_squads(self):
        return list(self._embarked_provider()) if self._embarked_provider else []

    def _derive_players(self):
        """Fill in self.players from the squads provider, if it can yet."""
        if self._squads_provider is None:
            return
        players = qualifying_players(self._squads_provider())
        if players:
            self.adopt_players(players)

    def sync_battle_round(self, battle_round):
        """Grant this round's tokens, losing any left over from the last one.

        Idempotent, and safe to call on every phase change as well as once at
        the start of the battle: it only does anything when the round number
        it is given differs from the one already granted for. Written that way
        so "the tokens got refreshed" cannot depend on a caller remembering to
        hit exactly one moment - the failure mode of missing it is an army
        rule that stops working halfway through a game."""
        if not battle_round:
            return
        if not self.players:
            self._derive_players()
        if not self.players or battle_round == self._granted_round:
            return
        if self._granted_round is not None:
            for player in self.players:
                lost = self.tokens.get(player, 0)
                if lost:
                    self._log(
                        f"{player}: {lost} unspent Battle Focus token(s) are lost "
                        f"at the end of battle round {self._granted_round}."
                    )
        amount = tokens_for_battle_size(self.battle_size)
        for player in self.players:
            # Warhost's Martial Grace: "at the start of the battle round, you
            # receive 1 ADDITIONAL Battle Focus token". Per PLAYER, so it is
            # added here rather than inside tokens_for_battle_size(), which
            # answers a question about the battle size and would have handed
            # the extra token to both armies.
            # Warhost's Timeless Strategist is the SECOND source of an extra
            # token, and unlike Martial Grace above it is conditional on where
            # a specific MODEL is - so it takes the board rather than just the
            # player. Two terms rather than one shared helper, because they
            # answer differently shaped questions and only happen to add to
            # the same number.
            self.tokens[player] = (
                amount
                + martial_grace.extra_tokens_for(player)
                + enh_timeless_strategist.extra_tokens_for(
                    player, self._board_squads(), self._embarked_squads()))
        self._granted_round = battle_round
        self._log(
            f"Battle Focus: {', '.join(self.players)} receive {amount} token(s) "
            f"for battle round {battle_round} ({self.battle_size or config.BATTLE_SIZE})."
        )

    def reset_phase(self, squads=()):
        """Clear the per-phase ledger and the one grant that only lasts a
        phase (Swift as the Wind).

        Lives here rather than in main.py's phase loop so that "when does
        this stop applying" has one answer and is testable without the game
        loop - the shape ArdAsNailsController.reset_phase() established.
        Callers pass every squad on the board."""
        self._units_this_phase = set()
        self._manoeuvres_this_phase = set()
        for squad in squads:
            squad.swift_as_the_wind_active = False
            squad.sudden_strike_active = False
        # Snapshot engagement for Opportunity Seized (see the field's note).
        # Taken here because reset_phase() runs on every phase change, which is
        # exactly "the start of the phase" - and O(n^2) over ~25 squads is a
        # few hundred cheap comparisons, once per phase.
        squads = list(squads)
        self._engaged_at_phase_start = {
            id(squad): {
                id(other) for other in squads
                if other is not squad and other.owner != squad.owner
                and squad.is_engaged_with(other)
            }
            for squad in squads
        }

    def expire_for_turn(self, squads=()):
        """End of turn: the two "until the end of the turn" grants expire."""
        for squad in squads:
            squad.star_engines_active = False
            squad.flitting_shadows_active = False

    # ------------------------------------------------------- eligibility

    def is_free(self, manoeuvre, squad):
        """Guardian Defenders' "Fleet of Foot": this unit performs Fade Back
        without spending a token, is not blocked by another unit having done it
        this phase, and does not block others from doing it either.

        Exactly those three clauses and no more. In particular the unit still
        spends its own one-manoeuvre-per-phase allowance: the ability says
        nothing about the per-UNIT restriction, only about the token and the
        per-MANOEUVRE one."""
        if manoeuvre != FADE_BACK or squad is None:
            return False
        models = getattr(squad, "models", None)
        return bool(models) and all(
            getattr(m.profile, "fleet_of_foot", False) for m in models
        )

    def refusal_reason(self, player, manoeuvre, squad):
        """Why this manoeuvre cannot be used right now, or None if it can.

        A reason rather than a bare bool because every refusal gets logged:
        the alternative is a button that silently does not appear, which is
        indistinguishable from a bug from the outside."""
        if player not in self.tokens:
            return "this army does not have the Battle Focus ability"
        if squad is None or squad.owner != player:
            return "not this player's unit"
        if not has_battle_focus(squad):
            return "the unit does not have the Battle Focus ability"
        free = self.is_free(manoeuvre, squad)
        # Fleet of Foot waives the token and the per-manoeuvre limit, so those
        # two checks are skipped for it - but NOT the per-unit one below, which
        # the ability says nothing about.
        if not free and self.tokens.get(player, 0) < 1:
            return "no Battle Focus tokens left this battle round"
        if id(squad) in self._units_this_phase:
            return "the unit has already performed an Agile Manoeuvre this phase"
        if (not free and manoeuvre not in REPEATABLE_PER_PHASE
                and (player, manoeuvre) in self._manoeuvres_this_phase):
            return f"{manoeuvre} has already been triggered this phase"
        return None

    def can_use(self, player, manoeuvre, squad):
        return self.refusal_reason(player, manoeuvre, squad) is None

    # Each manoeuvre's own TRIGGER, so the UI and the tests ask one question
    # instead of two that can drift apart. All three triggers named in this
    # step's manoeuvres happen in the unit's owner's Movement phase.

    def _own_movement_phase(self, squad):
        if self.turn_tracker is None:
            return True  # no tracker (tests, headless probes): timing is the caller's business
        return (
            self.turn_tracker.phase == PHASE_MOVEMENT
            and squad is not None
            and squad.owner == self.turn_tracker.turn_owner
        )

    def can_swift_as_the_wind(self, squad):
        """TRIGGER: selected to make a Normal, Advance or Fall Back move.

        Offered until the unit's move is CONFIRMED rather than only before it
        starts: the budget is handed out when the move begins, and this
        engine's Advance button only exists once a unit is already moving, so
        a strictly-before rule would make the manoeuvre unusable on the very
        trigger the rule lists first. use_swift_as_the_wind() tops up the
        remaining range accordingly."""
        if not self._own_movement_phase(squad):
            return False
        mover = self.movement_controller
        if mover is not None and squad in mover.moved_squad_ids:
            return False
        return self.can_use(squad.owner, SWIFT_AS_THE_WIND, squad)

    def can_flitting_shadows(self, squad):
        """TRIGGER: selected to make a Normal, Advance or Fall Back move.

        Not gated on the move being unfinished, unlike Swift as the Wind: the
        effect is not about the move at all, it denies Fire Overwatch, which
        this engine only offers once the whole Movement phase has ended. So
        the honest window is that phase.

        The rule's other two triggers (being set up on the battlefield,
        declaring a charge) are deliberately not offered - see the module
        docstring: this engine has no Fire Overwatch window at either moment,
        so a token spent there would buy a guaranteed nothing."""
        if not self._own_movement_phase(squad):
            return False
        return self.can_use(squad.owner, FLITTING_SHADOWS, squad)

    def can_star_engines(self, squad):
        """TRIGGER: an eligible VEHICLE unit selected to make an Advance move.

        Requires the Advance to have actually HAPPENED (the unit is in
        MovementController.advance_bonus_by_squad), not merely to be possible.
        Otherwise a player could buy [ASSAULT] for the whole turn and then
        make an ordinary move instead - the effect lasts until the end of the
        turn and pays off in the Shooting phase, so nothing later would ever
        catch it."""
        if not self._own_movement_phase(squad):
            return False
        if not any(getattr(m.profile, "vehicle", False) for m in squad.models):
            return False
        mover = self.movement_controller
        if mover is None or squad not in mover.advance_bonus_by_squad:
            return False
        return self.can_use(squad.owner, STAR_ENGINES, squad)

    def can_sudden_strike(self, squad):
        """TRIGGER: an eligible unit is selected to fight.

        Bought BEFORE the unit is selected, like War Horde's Unbridled
        Carnage, and gated on the same predicate that stratagem uses - a unit
        that cannot fight this phase never makes the Pile-in or Consolidation
        move this improves, so offering it would sell a guaranteed nothing.

        WHEN is the bare "Fight phase", not "your Fight phase": that phase is
        shared and alternates between both players (12.04), the reading
        game/counteroffensive.py spells out."""
        if squad is None:
            return False
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_FIGHT:
            return False
        if getattr(squad, "sudden_strike_active", False):
            return False  # already up on this unit
        fight = self.fight_controller
        if fight is not None:
            if squad in fight.fought_squad_ids or fight.fighting_squad is squad:
                return False
            if not fight.is_eligible_to_fight(squad):
                return False
        return self.can_use(squad.owner, SUDDEN_STRIKE, squad)

    def use_sudden_strike(self, squad):
        """EFFECT: until the end of the phase, this unit's Pile-in and
        Consolidation moves may go up to 6" instead of 3"."""
        if not self._spend(squad.owner, SUDDEN_STRIKE, squad):
            return False
        squad.sudden_strike_active = True
        return True

    # ------------------------------------------------- reactive manoeuvres
    # Both grant the same thing (a Normal move of up to D6+1") and differ only
    # in when they fire and which units qualify, so they share everything
    # below. Offered through DecisionManager rather than a panel button: they
    # happen in the OPPONENT's turn, where this player has no activation of
    # their own to hang a button on, and a break point is also modal - it
    # cannot be clicked past by accident.
    #
    # Offered EVERY time the trigger fires, with no relevance gate. That is the
    # user's explicit choice for these two ("immer fragen"), made knowing the
    # worst case: Fade Back can fire after every enemy shooting activation.

    def _reactive_candidates(self, player, manoeuvre, squads):
        out = []
        for squad in squads:
            if squad is None or squad.owner != player:
                continue
            if not is_on_the_battlefield(squad):
                continue
            if excluded_from_reactive_manoeuvre(squad):
                continue
            # "Can make a Normal move" - and rule 09.05 has no Normal move for
            # a unit that is already within Engagement Range. Same check
            # TorchstarGambitController makes for its own granted Normal move.
            if self.all_tokens is not None and squad.is_engaged(self.all_tokens):
                continue
            if not self.can_use(player, manoeuvre, squad):
                continue
            out.append(squad)
        return out

    def offer_fade_back(self, shooter, hit_squads):
        """TRIGGER: in your opponent's Shooting phase, just after an enemy unit
        has shot - for one of your units hit by one or more of those attacks.

        `hit_squads` comes straight from ShootingController's own
        _hit_target_squads_this_activation, which already tracks exactly "was
        hit by one or more of these attacks" (it was built for Suppression
        Volley), so neither half of this trigger needed new bookkeeping."""
        if shooter is None or not hit_squads:
            return False
        for player in self.players:
            if player == shooter.owner:
                continue  # your OPPONENT's shooting phase
            candidates = self._reactive_candidates(player, FADE_BACK, hit_squads)
            if self._raise_offer(player, FADE_BACK, candidates,
                                 f"hit by {shooter.name}"):
                return True
        return False

    def offer_opportunity_seized(self, fallen_back_squad):
        """TRIGGER: an enemy unit ends a Fall Back move - for one of your units
        that started the phase within Engagement Range of it."""
        if fallen_back_squad is None:
            return False
        started_engaged = {
            squad_id for squad_id, engaged in self._engaged_at_phase_start.items()
            if id(fallen_back_squad) in engaged
        }
        for player in self.players:
            if player == fallen_back_squad.owner:
                continue
            candidates = [
                squad for squad in self._reactive_candidates(
                    player, OPPORTUNITY_SEIZED, self._all_squads())
                if id(squad) in started_engaged
            ]
            if self._raise_offer(player, OPPORTUNITY_SEIZED, candidates,
                                 f"{fallen_back_squad.name} fell back"):
                return True
        return False

    def _all_squads(self):
        if self._squads_provider is not None:
            return list(self._squads_provider())
        if self.all_tokens is None:
            return []
        return list({t.squad for t in self.all_tokens if t.squad is not None})

    def _raise_offer(self, player, manoeuvre, candidates, because):
        if not candidates or self.decision_manager is None:
            return False
        # (label, callback) TUPLES - DecisionManager.request() builds the dicts
        # itself. Only the READ side (DecisionManager.options) holds dicts,
        # which is the trap testkit.py's docstring warns about from the other
        # direction: passing dicts here unpacks their KEYS into label/callback
        # and the "callback" ends up being the string "callback".
        options = [
            (f"{manoeuvre}: {squad.name} makes a D6+1\" Normal move",
             (lambda s=squad: self._perform_reactive(s, manoeuvre)))
            for squad in candidates
        ]
        # is_stratagem stays False: this is a datasheet/army rule spending its
        # own token, not rule 15.01 spending CP - the distinction the overlay
        # colours its heading by.
        options.append(("Decline", None))
        self.decision_manager.request(
            player,
            f"{manoeuvre} ({because}) - spend 1 Battle Focus token?",
            options,
        )
        return True

    def is_reactive_move_active(self):
        mover = self.movement_controller
        return mover is not None and mover.move_mode == "battle_focus"

    def confirm_reactive_move(self):
        """Confirm the granted Normal move and hand the turn back.

        Wrapped rather than letting the panel call confirm_move() directly, for
        the same reason PileInController.confirm_pile_in() is: something has to
        happen after a SUCCESSFUL confirm - here, restoring whose decision it
        is. Success is read the way IngressController.confirm_ingress() reads
        it: confirm_move() clears move_mode only when it worked, and leaves the
        move open with errors set when it did not."""
        mover = self.movement_controller
        if mover is None or not self.is_reactive_move_active():
            return False
        mover.confirm_move()
        if mover.move_mode == "battle_focus":
            return False  # rejected - the player can reposition and try again
        self._restore_active_player()
        return True

    def cancel_reactive_move(self):
        """Back out. The token is gone either way - nothing in the rule refunds
        it, the same way a cancelled stratagem move does not refund its CP."""
        if not self.is_reactive_move_active():
            return False
        self.movement_controller.cancel_move()
        self._restore_active_player()
        return True

    def _restore_active_player(self):
        if self._reactive_restore_player is None or self.turn_tracker is None:
            return
        self.turn_tracker.set_active(self._reactive_restore_player)
        self._reactive_restore_player = None

    def _perform_reactive(self, squad, manoeuvre):
        """Spend the token, roll the D6+1" and open the move.

        turn_tracker.set_active() is flipped to the reacting player first, and
        that is not cosmetic: MovementController.select() refuses a unit whose
        owner is not the active player outside the Fight phase, so without this
        both reactive manoeuvres would spend a token and then silently move
        nothing. set_active() is exactly the transient "whose decision is this"
        flag for the job (game/explosives.py flips it for rule 06.02 the same
        way); it is handed back in confirm_reactive_move()/
        cancel_reactive_move(), mirroring how game/overwatch.py restores it
        once its own Snap Shooting concludes."""
        if not self._spend(squad.owner, manoeuvre, squad):
            return False
        if self.turn_tracker is not None:
            self._reactive_restore_player = self.turn_tracker.active_player
            self.turn_tracker.set_active(squad.owner)
        distance = REACTIVE_MOVE_BONUS_IN
        if self.dice_manager is not None:
            # roll_kind stays unset: a granted move distance is not on rule
            # 15.02's re-rollable list (Hit/Wound/Damage/save/Advance/Charge/
            # Desperate Escape/Battle-shock), and CommandRerollController
            # filters on roll_kind - the same reasoning the pre-game roll-offs
            # use.
            values = self.dice_manager.roll(
                count=1, sides=6, label=f"{manoeuvre}: {squad.name} moves D6+1\"",
            )
            distance += sum(values or [0])
            # Warhost's Martial Grace: "each time a unit performs an Agile
            # Manoeuvre that involves rolling a D6, add 1 to the RESULT".
            # Measured, this is the only such roll: of the six manoeuvres only
            # Opportunity Seized and Fade Back throw anything, and both come
            # through here. Added to the result, so the die itself is untouched
            # and anything that later re-reads the roll still sees what fell.
            distance += martial_grace.roll_bonus_for(squad)
        mover = self.movement_controller
        if mover is None or not squad.models:
            return False
        mover.select(squad.models[0])
        mover.start_battle_focus_move(squad, distance)
        self._log(f"{squad.name} may make a Normal move of up to {distance:.0f}\" ({manoeuvre}).")
        return True

    # Set by main.py - the Autarch Wayleaper's token refund, read in
    # _spend(). A class attribute so every existing BattleFocusController
    # (tests, harnesses) keeps working without a constructor change.
    indomitable = None

    def _spend(self, player, manoeuvre, squad):
        reason = self.refusal_reason(player, manoeuvre, squad)
        if reason is not None:
            self._log(f"Battle Focus: {manoeuvre} not available - {reason}.")
            return False
        free = self.is_free(manoeuvre, squad)
        # The unit is spent for the phase either way; only the token and the
        # per-manoeuvre entry are waived. Not recording the manoeuvre is the
        # third clause of Fleet of Foot - "does not prevent other units from
        # performing the same Agile Manoeuvre in the same phase".
        self._units_this_phase.add(id(squad))
        if free:
            self._log(
                f"{squad.name} performs {manoeuvre} for free (Fleet of Foot) - "
                f"no token spent, and it does not use up this phase's {manoeuvre}."
            )
            return True
        self.tokens[player] -= 1
        self._manoeuvres_this_phase.add((player, manoeuvre))
        self._log(
            f"{player} spends 1 Battle Focus token: {squad.name} performs "
            f"{manoeuvre} ({self.tokens[player]} token(s) left)."
        )
        # The Autarch Wayleaper's Indomitable Strength of Will refunds the
        # token on a 3+. Fed from HERE, after the decrement and on the PAID
        # path only: the free branch above returns early, and a refund hung
        # on "performed a manoeuvre" would print tokens out of Fleet of
        # Foot's free ones. Optional, so every existing caller is unchanged.
        if self.indomitable is not None:
            self.indomitable.on_token_spent(player, squad, manoeuvre)
        return True

    # --------------------------------------------------- agile manoeuvres

    def use_swift_as_the_wind(self, squad):
        """EFFECT: until the end of the phase, add 2 inches to the Move
        characteristic of models in that unit.

        Tops up a move that has already begun. The engine hands out the whole
        move budget in one go when the move starts (MovementController.
        _begin_move()), and this engine's Advance button only exists once a
        unit is already moving - so requiring the token to be spent strictly
        before the move would make the manoeuvre unusable on the very trigger
        the rule names first. Adding to remaining_range afterwards is exactly
        how start_run() applies the Advance roll."""
        if not self._spend(squad.owner, SWIFT_AS_THE_WIND, squad):
            return False
        squad.swift_as_the_wind_active = True
        mover = self.movement_controller
        if mover is not None and mover.selected_squad is squad:
            for model in squad.models:
                if model.id in mover.remaining_range:
                    mover.remaining_range[model.id] += SWIFT_AS_THE_WIND_BONUS_IN
        return True

    def use_flitting_shadows(self, squad):
        """EFFECT: until the end of the turn, enemy units cannot use the Fire
        Overwatch Stratagem to shoot at that unit."""
        if not self._spend(squad.owner, FLITTING_SHADOWS, squad):
            return False
        squad.flitting_shadows_active = True
        return True

    def use_star_engines(self, squad):
        """EFFECT: until the end of the turn, Ranged weapons equipped by this
        unit have the [ASSAULT] ability."""
        if not self._spend(squad.owner, STAR_ENGINES, squad):
            return False
        squad.star_engines_active = True
        return True

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
