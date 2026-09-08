"""Rule 03.01: everything that happens before Battle Round 1.

    Declare Battle Formations -> roll-off -> the winner decides who places
    first -> players alternate placing one unit each until one side runs out,
    then the other places the rest -> roll-off for the first turn -> Resolve
    Pre-battle Abilities (SCOUTS 24.31, game/scouts.py).

Deliberately a thin SEQUENCER, not a placement engine: every actual placement
goes through SetupController.start_setup() exactly the way IngressController
(20.04) and TransportController (18.04/18.05) already do. That inherits the
green/red legality overlay, clamp_drag(), the Confirm/Cancel panel and
confirm_setup()'s coherency/terrain/overlap/unengaged checks for free, and -
more importantly - means there is one Set Up implementation rather than two
that can drift apart. SetupController's own docstring already named "or,
later, initial deployment" as an expected caller.

INFILTRATORS (24.20) is NOT a step here. Its rules text says "During
deployment", so it is only a different position_valid predicate for that one
unit during its normal turn to place - see _infiltrator_position_valid().

What the pre-game deliberately does NOT do: spend a single API call. Every
AI decision in it is deterministic (ai/agent_driver.py's
plan_battle_formations/_auto_deploy_squad), and the "you won the roll-off"
prompt only goes through DecisionManager when the winner is the human -
routing the AI's answer through there could consult the agent.
"""

from game import attached_units, deployment
from game.squad import (
    INFILTRATORS_MIN_ENEMY_DISTANCE_IN,
    infiltrators_clear_of_enemies,
    squad_has_infiltrators,
)

IDLE = "idle"
FORMATIONS = "formations"
DEPLOY_ROLLOFF = "deploy_rolloff"
DEPLOY_ORDER_CHOICE = "deploy_order_choice"
DEPLOYING = "deploying"
FIRST_TURN_ROLLOFF = "first_turn_rolloff"
PREBATTLE_ABILITIES = "prebattle_abilities"
DONE = "done"

# Where a unit was declared to start (rule 03.01's Declare Battle Formations).
DEPLOY = "deploy"
RESERVES = "reserves"
EMBARK = "embark"
#: A SUPPORT WEAPON platform joining a Guardian Defenders unit ("Support
#: Artillery": "At the start of the Declare Battle Formations step, this model
#: can join one GUARDIAN DEFENDERS unit from your army"). Its target is a
#: SQUAD, where EMBARK's is a transport TOKEN - both ride in the same slot of
#: the declaration, because a unit has exactly one destination and the two are
#: mutually exclusive by the printed text (a joined unit cannot embark).
JOIN = "join"

# The official sequence is Deploy Armies -> Determine First Turn -> Resolve
# Pre-battle Abilities, and the order matters: a Scouts move (24.32) is a
# different decision once you know whether you are going first. Kept as a
# constant so flipping it is one line rather than a state-machine edit.
SCOUTS_BEFORE_FIRST_TURN_ROLLOFF = False

# Pure liveness guard on the tie re-roll loop. The rules re-roll ties
# indefinitely (user: "bei gleichstand muss solange gewuerfelt werden bis es
# keinen gleichstand mehr gibt") and 6**-50 is unreachable - this exists only
# so a harness that stops acknowledging dice cannot spin forever.
MAX_ROLLOFF_ATTEMPTS = 50


class Resume:
    """A pre-game step's `on_done` continuation, wrapped so it runs ONCE - and
    so its caller can ask whether it already ran.

    Every hand-off in this file has the same shape: the controller pops a step,
    calls `step.start(self, on_done)`, and carries on itself if the step
    answers "nothing to do". Two readings of that protocol shipped side by
    side, and they contradict each other. enh_solid_image_projection.py's
    _apply() writes out one of them ("calling on_done AND returning False would
    run _finish_deployment() twice, and the second run would start a second
    first-turn roll-off"); test_wraith_constructs.py pins the other on
    fated_hero, asserting start() returns False *and* that on_done fired.

    Four shipped steps take the second reading, and every one of them made the
    controller advance TWICE - once through the continuation, once by falling
    through. Measured through the real main() loop: deployment finished 3x, the
    Pre-battle Abilities step ran its Scouts queue 3x, and the battle STARTED
    3x, so the first Command phase scored its Primary and handed out its Core
    CP three times over (user report: "der erste zug ging noch nicht los und
    der gegner spieler 2 hat schon 36 VP").

    So the protocol is enforced here rather than merely documented: whichever
    reading a step takes, the continuation fires at most once, and `fired` tells
    the caller not to run the rest of the sequence a second time."""

    __slots__ = ("_fn", "fired")

    def __init__(self, fn):
        self._fn = fn
        self.fired = False

    def __call__(self):
        if self.fired:
            return
        self.fired = True
        self._fn()


class RollOff:
    """Rule 03.01's roll-off: both players roll a D6, highest wins, ties are
    re-rolled until they aren't.

    Rolls SEQUENTIALLY, one player at a time through the normal
    DiceManager/DicePanel acknowledge flow, rather than as one two-die roll.
    DiceManager holds a single pending roll, and DicePanel's
    label/success_threshold/target_name presentation has no concept of two
    competing rollers - sequencing also means each player's die is shown and
    acknowledged on its own, which is what a table roll-off looks like.

    roll_kind is left None deliberately: a roll-off is not on rule 15.02's
    re-rollable list, and CommandRerollController filters on roll_kind, so
    this keeps Command Re-roll out of it with no extra check. Same reasoning
    game/dice.py already applies to battle-shock and Thievin' Scavengers."""

    def __init__(self, dice_manager, players, label, game_log=None, on_resolved=None):
        self.dice_manager = dice_manager
        self.players = tuple(players)
        self.label = label
        self.game_log = game_log
        self.on_resolved = on_resolved
        self.results = {}
        self.winner = None
        self._index = 0
        self._attempts = 0
        self.active = False

    def start(self):
        self.active = True
        self.results = {}
        self._index = 0
        self._attempts += 1
        self._roll_for_current()

    def _roll_for_current(self):
        player = self.players[self._index]
        self.dice_manager.roll(1, 6, label=f"{self.label}: {player}", target_name=player)

    def on_dice_acknowledged(self):
        """Called from main.py's dice-acknowledge chain. Records the die that
        was just cleared, then either rolls for the next player or resolves."""
        if not self.active:
            return
        values = self.dice_manager.last_values or []
        if not values:
            return
        self.results[self.players[self._index]] = values[0]
        self._index += 1
        if self._index < len(self.players):
            self._roll_for_current()
            return
        self._resolve()

    def _resolve(self):
        rolled = ", ".join(f"{p} rolled {self.results[p]}" for p in self.players)
        best = max(self.results.values())
        leaders = [p for p in self.players if self.results[p] == best]
        if len(leaders) > 1:
            if self._attempts >= MAX_ROLLOFF_ATTEMPTS:
                # Unreachable by dice; see MAX_ROLLOFF_ATTEMPTS.
                self._log(f"{self.label}: {rolled} - tie limit reached, defaulting to {self.players[0]}.")
                self._finish(self.players[0])
                return
            self._log(f"{self.label}: {rolled} - a tie, roll again (rule 03.01).")
            self.start()
            return
        self._log(f"{self.label}: {rolled} - {leaders[0]} wins.")
        self._finish(leaders[0])

    def _finish(self, winner):
        self.winner = winner
        self.active = False
        if self.on_resolved is not None:
            self.on_resolved(winner)

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)


class PregameController:
    """The pre-game state machine. See module docstring."""

    def __init__(
        self, game_state, setup_controller, dice_manager, decision_manager,
        turn_tracker=None, game_log=None, on_battle_start=None,
        human_players=("Player 1",),
    ):
        self.game_state = game_state
        self.setup_controller = setup_controller
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.on_battle_start = on_battle_start
        # A SET, not one name. With the AI mode switched off there is no AI
        # side at all, and both armies are played at one keyboard - so every
        # step that used to ask "is this THE human?" has to ask "is this ONE OF
        # the humans?". Reported: "ohne angeschalteten KI-Modus geht es direkt
        # vor beginn der aufstellung nicht weiter. es gibt keinen knopf mit dem
        # man den roll fuer attacker/defender ausloesen koennte" - Declare
        # Battle Formations only ever offered Player 1's units, so Player 2's
        # were never declared, and the roll-off that waits on both never began.
        #
        # KEPT AS HANDED, deliberately not copied into a set: main() passes
        # game/ai_mode.py's live view, and a copy would freeze it in whatever
        # state the mode happened to be in when the battle was built.
        self.human_players = human_players

        self.state = IDLE
        self.active_player = None
        self.first_player = None
        # Undeployed pool per owner: squads declared to start on the
        # battlefield but not yet placed. Deliberately NOT game_state.reserves
        # - that list means Strategic Reserves (20.01), a different thing that
        # IngressController owns.
        self._pending = {}
        # Declared battle formations, per squad: DEPLOY / RESERVES / EMBARK.
        self._declared = {}
        self._formations_done = set()
        self._all_units = {}
        self._transport_tokens = []
        self._deploying_squad = None
        self.selected_unit = None
        self.rolloff = None
        self.errors = []
        self.scouts_step = None  # set by game/scouts.py in PREBATTLE_ABILITIES
        # Other Resolve Pre-battle Abilities steps, run IN ORDER and BEFORE
        # scouts_step. An ordered list rather than more named attributes,
        # because at least one entry's correctness is entirely about its place
        # in that order: Mont'ka's Strike Swiftly Enhancement grants Scouts 6",
        # and a unit granted it after ScoutsStep has already walked the army
        # carries an ability it can never use. Each entry offers
        # start(pregame_controller, on_done) and returns True if it took over
        # (a prompt is on screen); on_done resumes this queue.
        # A step may ALSO take over by simply calling on_done and then
        # answering False - four shipped ones do. The driver treats that as
        # "took over" too, so neither reading of the protocol can advance the
        # queue twice; see Resume.
        self.prebattle_steps = []
        # ...and the same idea one step EARLIER: abilities whose printed timing
        # is "in the Deploy Armies step", which therefore have to land before
        # the deployment order and the placement rules are read. Ordered, for
        # the same reason prebattle_steps is.
        self.deploy_armies_steps = []
        self._prebattle_queue = []
        # Kauyon's Solid-image Projection Unit fires "after both players have
        # deployed their armies", which is BEFORE Determine First Turn - so it
        # hangs off _finish_deployment() rather than the pre-battle queue above.
        # It may put units back into _pending and return the controller to
        # DEPLOYING, which reaches _finish_deployment() a second time; the flag
        # is what stops it from running twice and re-offering a redeploy of the
        # redeploy.
        self.redeploy_step = None
        self._redeploy_done = False
        # Optional callable(squad) - wired by main.py to the AI's own
        # deployment placer, so the human can hand a unit to it ("Auto-place
        # this unit"). A callback rather than an import so game/ never depends
        # on ai/.
        self.on_auto_place = None
        # Optional callable(owners) fired once, at the moment Declare Battle
        # Formations begins. The Death Guard army rule selects its Plague
        # "during the Declare Battle Formations step" (game/plagues.py), which
        # is a per-army choice with nothing to do with this controller's job of
        # placing units - so it is a hook, like on_auto_place above, rather
        # than a seventh state. main.py wires it; nothing here waits on the
        # answer, because the DecisionManager prompt it opens is modal and is
        # therefore resolved long before the first shot, which is all the rule
        # actually requires.
        self.on_formations_started = None

    # --- lifecycle -------------------------------------------------------

    @property
    def is_active(self):
        return self.state not in (IDLE, DONE)

    @property
    def awaiting_drop(self):
        """A unit is selected and the next board click should place it."""
        return self.state == DEPLOYING and self.selected_unit is not None

    def start(self, units_by_owner, transport_tokens=()):
        """`units_by_owner` maps owner -> list of squads that make up that
        player's army (transports included, passengers as their own squads).
        Nothing is on the battlefield yet."""
        self._all_units = {owner: list(units) for owner, units in units_by_owner.items()}
        self._transport_tokens = list(transport_tokens)
        self._declared = {}
        self._formations_done = set()
        self._pending = {owner: [] for owner in self._all_units}
        self.state = FORMATIONS
        self.active_player = self.first_human()
        self._sync_turn_tracker()
        self._log("Pre-battle: Declare Battle Formations (rule 03.01).")
        if self.on_formations_started is not None:
            self.on_formations_started(self._owners())

    def _sync_turn_tracker(self):
        # active_player is exactly "whose decision is this right now" (see
        # TurnTracker.set_active) - it never touches turn_owner/phase_index/
        # battle_round, so it is the right channel for pre-game alternation
        # and makes PlayerBanner and MovementController.can_select() correct
        # for the Scouts move with no changes there.
        if self.turn_tracker is not None and self.active_player is not None:
            self.turn_tracker.set_active(self.active_player)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _owners(self):
        return list(self._all_units.keys())

    def _other(self, owner):
        for other in self._owners():
            if other != owner:
                return other
        return owner

    # --- Declare Battle Formations (03.01 / 18.01 / 20.01) ---------------

    def army(self, owner):
        return list(self._all_units.get(owner, ()))

    def declaration_for(self, squad):
        return self._declared.get(id(squad), (DEPLOY, None))

    def undeclared_units(self, owner):
        return [s for s in self.army(owner) if id(s) not in self._declared]

    def current_formation_unit(self, owner=None):
        owner = owner or self.active_player
        remaining = self.undeclared_units(owner)
        return remaining[0] if remaining else None

    def reserve_units(self, owner):
        return [s for s in self.army(owner) if self.declaration_for(s)[0] == RESERVES]

    def transports_for(self, owner):
        return [
            t for t in self._transport_tokens
            if t.squad is not None and t.squad.owner == owner
        ]

    def squads_assigned_to(self, transport_token):
        return [
            s for s in self.army(transport_token.squad.owner)
            if self.declaration_for(s) == (EMBARK, transport_token)
        ]

    def assignments_map(self, owner):
        out = {}
        for transport in self.transports_for(owner):
            out[id(transport)] = self.squads_assigned_to(transport)
        return out

    def squads_joining(self, target_squad):
        """The SUPPORT WEAPON platforms declared to join `target_squad`."""
        return [
            s for s in self.army(target_squad.owner)
            if self.declaration_for(s) == (JOIN, target_squad)
        ]

    def joins_map(self, owner):
        """id(target squad) -> the platforms declared into it. The shape
        assignments_map() has for transports, for the same reason: the panel
        and the AI both need "what is already joined here" to ask
        formations.support_join_errors() the one-per-unit question."""
        out = {}
        for squad in self.army(owner):
            destination, target = self.declaration_for(squad)
            if destination == JOIN and target is not None:
                out.setdefault(id(target), []).append(squad)
        return out

    def destinations_map(self, owner):
        """id(unit) -> its declared destination, for the units that have one.
        What formations.eligible_join_targets() needs to refuse a host that is
        already declared into a TRANSPORT."""
        return {id(s): self.declaration_for(s)[0]
                for s in self.army(owner) if id(s) in self._declared}

    def declare(self, squad, destination, transport_token=None, join_target=None):
        """Record one unit's Declare Battle Formations answer.

        A declaration that names no target where one is required is REFUSED
        rather than stored as a bare destination - "embark, in nothing" and
        "join, nobody" are not answers, and storing them would make the unit
        look declared while nothing could resolve it."""
        if destination == EMBARK and transport_token is None:
            return
        if destination == JOIN and join_target is None:
            return
        target = None
        if destination == EMBARK:
            target = transport_token
        elif destination == JOIN:
            target = join_target
        self._declared[id(squad)] = (destination, target)
        return True

    def finish_formations_for(self, owner):
        """Apply that player's declarations to the game state and mark them
        done. Anything left undeclared defaults to deploying normally."""
        for squad in self.army(owner):
            if id(squad) not in self._declared:
                self._declared[id(squad)] = (DEPLOY, None)

        # Support Artillery FIRST, and the order is load-bearing. The printed
        # text puts the join "at the start of the Declare Battle Formations
        # step", and mechanically the merged unit is what everything below has
        # to act on: a platform joined to a unit held in Reserves goes to
        # Reserves with it, and _pending must never list the platform as a
        # separate thing to place.
        for squad in list(self.army(owner)):
            destination, target = self.declaration_for(squad)
            if destination != JOIN or target is None:
                continue
            merged = attached_units.attach(squad, target, game_state=self.game_state)
            # attach() mutates the host in place today and says so is its own
            # business, not the caller's - so the result is re-bound, and the
            # host's declaration travels with it if it ever stops being the
            # same object. Without that, the merged unit would fall back to
            # the DEPLOY default and a Reserves declaration would be lost.
            if merged is not target:
                if id(target) in self._declared:
                    self._declared[id(merged)] = self._declared.pop(id(target))
                self._all_units[owner] = [
                    merged if s is target else s for s in self._all_units.get(owner, ())
                ]
            self._log(
                f"{owner}: {squad.name} joins {merged.name} for the battle "
                f"(Support Artillery, rule 19.01)."
            )
        # The absorbed platforms are no longer units of this army - attach()
        # has emptied them and taken them off the board. Dropped here for the
        # same reason attach() drops them from the GameState lists: a squad
        # with no models left in army() is a unit that every later pass has to
        # remember to skip.
        self._all_units[owner] = [
            s for s in self._all_units.get(owner, ())
            if getattr(s, "absorbed_into", None) is None
        ]

        for squad in self.army(owner):
            destination, transport = self.declaration_for(squad)
            if destination == RESERVES:
                self.game_state.add_reserve_squad(squad)
                self._log(f"{owner}: {squad.name} starts in Strategic Reserves (rule 20.01).")
            elif destination == EMBARK and transport is not None:
                # Same two lines TransportController.embark() ends with; its
                # own can_embark() gate is mid-battle only (see
                # game/formations.py's module docstring for why).
                squad.embarked_in = transport
                self.game_state.embarked_squads.append(squad)
                self._log(f"{owner}: {squad.name} starts embarked within {transport.profile.name} (rule 18.01).")

        # A transport carrying declared passengers is placed as one unit; its
        # passengers ride along and are never placed separately.
        self._pending[owner] = [
            s for s in self.army(owner)
            if self.declaration_for(s)[0] == DEPLOY
        ]
        self._formations_done.add(owner)
        if all(owner in self._formations_done for owner in self._owners()):
            self._begin_deploy_rolloff()

    # --- roll-offs -------------------------------------------------------

    def _begin_deploy_rolloff(self):
        self.state = DEPLOY_ROLLOFF
        self._log("Pre-battle: roll off to decide who deploys first (rule 03.01).")
        self.rolloff = RollOff(
            self.dice_manager, self._owners(), "Deployment roll-off",
            game_log=self.game_log, on_resolved=self._on_deploy_rolloff,
        )
        self.rolloff.start()

    def _on_deploy_rolloff(self, winner):
        self.state = DEPLOY_ORDER_CHOICE
        if winner in self.human_players:
            self.decision_manager.request(
                winner,
                "You won the roll-off. Who places the first unit?",
                [
                    ("I place first", lambda: self._set_deploy_order(winner)),
                    ("My opponent places first", lambda: self._set_deploy_order(self._other(winner))),
                ],
            )
            return
        # Resolved in place rather than through DecisionManager: that queue is
        # auto-resolved by ai/agent_driver.py, which may consult the agent -
        # an API call the pre-game is specifically built not to need.
        # Placing SECOND is the stronger choice (you get to react), so the AI
        # makes its opponent go first.
        opponent = self._other(winner)
        self._log(f"{winner} won the roll-off and chooses to place second.")
        self._set_deploy_order(opponent)

    def _set_deploy_order(self, first_to_place):
        # "IN THE DEPLOY ARMIES STEP" - resolved just BEFORE it, which is the
        # last moment such a grant can still change anything. Rule 24.20's
        # INFILTRATORS decides both WHERE a unit may be placed and WHEN (they
        # deploy last), and both are read from here on, so a grant made after
        # this point would be carried and never used. Same ordering trap the
        # Scouts grants meet one step later; see game/enh_ethereal_pathway.py.
        for step in self.deploy_armies_steps:
            step.start(self)
        self.state = DEPLOYING
        self.active_player = first_to_place
        self._sync_turn_tracker()
        self._log(f"Pre-battle: {first_to_place} places the first unit.")
        self._advance_if_nothing_to_place()

    def _begin_first_turn_rolloff(self):
        self.state = FIRST_TURN_ROLLOFF
        self._log("Pre-battle: roll off to decide who takes the first turn (rule 03.01).")
        self.rolloff = RollOff(
            self.dice_manager, self._owners(), "First turn roll-off",
            game_log=self.game_log, on_resolved=self._on_first_turn_rolloff,
        )
        self.rolloff.start()

    def _on_first_turn_rolloff(self, winner):
        self.first_player = winner
        self._log(f"{winner} takes the first turn.")
        self._begin_prebattle_abilities()

    def on_dice_acknowledged(self):
        if self.rolloff is not None and self.rolloff.active:
            self.rolloff.on_dice_acknowledged()

    # --- alternating deployment ------------------------------------------

    @property
    def human_player(self):
        """The first human owner, under the name this used to be a plain
        attribute.

        Kept as a forwarding property rather than removed: eight headless
        harnesses drive deployment through `pregame_ctrl.human_player`, and
        with the AI mode ON it answers exactly what it always did. The SET is
        the real answer now, so anything deciding whether to offer a choice
        must ask `human_players` - see the note on it in __init__."""
        return self.first_human()

    def first_human(self):
        """The player the human-facing steps open on.

        The first owner this battle has that nobody answers for - or, if the
        engine answers for everyone (which no shipped setup does, but a probe
        can), simply the first owner, so a step can still open on somebody."""
        owners = self._owners()
        return next((o for o in owners if o in self.human_players),
                    owners[0] if owners else None)

    def humans_with_undeclared_units(self):
        """Every human owner that still owes a Declare Battle Formations
        answer, in owner order - what the panel walks through."""
        return [o for o in self._owners()
                if o in self.human_players and self.undeclared_units(o)]

    def pending_units(self, owner=None):
        if owner is None:
            return [s for units in self._pending.values() for s in units]
        return list(self._pending.get(owner, ()))

    def has_pending(self, owner):
        return bool(self._pending.get(owner))

    def _advance_if_nothing_to_place(self):
        """Rule 03.01: "if one player has finished deploying, their opponent
        then deploys the rest of their army" - so the turn only passes to the
        other player if they still have something to place."""
        if not any(self._pending.get(o) for o in self._owners()):
            self._finish_deployment()
            return
        if not self.has_pending(self.active_player):
            self.active_player = self._other(self.active_player)
            self._sync_turn_tracker()

    def _finish_deployment(self):
        self._log("Pre-battle: deployment complete.")
        if self.redeploy_step is not None and not self._redeploy_done:
            self._redeploy_done = True
            # Returns True if it took over - either a prompt is on screen or it
            # has put units back into _pending and returned this controller to
            # DEPLOYING, in which case placing them reaches here again with the
            # flag already set.
            #
            # `resume.fired` is the other way a step can take over: it may
            # finish synchronously by calling the continuation and still answer
            # "nothing to do" (see Resume). Then the rest of the sequence has
            # already run and falling through would start a SECOND first-turn
            # roll-off.
            #
            # The continuation is _deployment_finished, not _finish_deployment:
            # a step handing control back has not made the deployment complete
            # a second time, so it must not log that it did. The genuine second
            # visit - a redeploy that put units back into _pending - comes
            # through _advance_if_nothing_to_place() and does log again, which
            # is honest.
            resume = Resume(self._deployment_finished)
            if self.redeploy_step.start(self, resume) or resume.fired:
                return
        self._deployment_finished()

    def _deployment_finished(self):
        if SCOUTS_BEFORE_FIRST_TURN_ROLLOFF:
            self._begin_prebattle_abilities(then_rolloff=True)
        else:
            self._begin_first_turn_rolloff()

    def select_unit(self, squad):
        """Human flow: pick a unit from the undeployed pool. The next board
        click places it - see start_deployment()."""
        if self.state != DEPLOYING:
            return False
        if squad is None or squad not in self._pending.get(self.active_player, ()):
            return False
        self.selected_unit = squad
        return True

    def can_deploy(self, squad):
        return (
            self.state == DEPLOYING
            and squad is not None
            and squad in self._pending.get(self.active_player, ())
            and self.setup_controller.can_start_setup(squad)
        )

    def start_deployment(self, squad, x_in, y_in):
        if not self.can_deploy(squad):
            return False
        self._pending[self.active_player].remove(squad)
        self._deploying_squad = squad
        self.selected_unit = None
        self.errors = []
        self.setup_controller.start_setup(
            squad, x_in, y_in,
            on_cancel=self._on_cancel_deployment,
            extra_check=self._extra_check,
            placement_validator=lambda token, x, y: self.position_valid(squad, token, x, y),
        )
        return True

    def _on_cancel_deployment(self, squad):
        # Back into the undeployed pool, not into Strategic Reserves - it was
        # never declared there.
        self._pending.setdefault(squad.owner, []).insert(0, squad)
        self._deploying_squad = None

    def is_deploying(self, squad):
        return squad is not None and squad is self._deploying_squad

    @property
    def deploying_squad(self):
        return self._deploying_squad

    def confirm_deployment(self):
        """Returns True if the placement was accepted. Mirrors
        IngressController.confirm_ingress(): SetupController stays in PLACING
        with .errors populated if it wasn't."""
        squad = self._deploying_squad
        if squad is None:
            return False
        self.setup_controller.confirm_setup()
        if self.setup_controller.setting_up_squad is not None:
            self.errors = list(self.setup_controller.errors)
            return False
        self.errors = []
        self._deploying_squad = None
        # Rule 03.01 alternation.
        other = self._other(self.active_player)
        if self.has_pending(other):
            self.active_player = other
            self._sync_turn_tracker()
        self._advance_if_nothing_to_place()
        return True

    def cancel_deployment(self):
        if self._deploying_squad is None:
            return
        self.setup_controller.cancel_setup()
        self.errors = []

    def request_auto_place(self, squad):
        """Let the AI's placer put this unit down for the human. Also the one
        gesture a headless harness can drive, so it keeps the whole sequence
        testable without synthesising drags."""
        if self.on_auto_place is None or not self.can_deploy(squad):
            return False
        self.selected_unit = None
        return bool(self.on_auto_place(squad))

    def give_up_on(self, squad):
        """Drop a unit that could not be placed anywhere out of the pool, so
        the sequence keeps moving instead of retrying it forever.

        Safe in a way an Emergency Disembark (18.05) is not: a failed
        deployment destroys nothing, it just means this unit does not start on
        the table. Without it, a unit with no legal spot would be picked again
        every frame and the pre-game would never end."""
        for owner, units in self._pending.items():
            if squad in units:
                units.remove(squad)
                self._log(
                    f"{owner}: {squad.name} could not be deployed anywhere and is "
                    f"left off the battlefield."
                )
                break
        self._advance_if_nothing_to_place()

    # --- placement legality (03.01 / 24.20) ------------------------------

    def _enemy_zones_for(self, squad):
        return deployment.enemy_zones(getattr(self.game_state, "deployment_zones", ()), squad.owner)

    def position_valid(self, squad, token, x_in, y_in, ignore_model_overlap=False):
        """The live per-position predicate for a deployment placement - what
        clamp_drag() holds the mouse inside, what the AI's placer probes, and
        (minus one term, see overlay_position_valid()) what the green/red
        overlay paints."""
        if not self.setup_controller.position_valid(
            token, x_in, y_in, squad=squad, ignore_model_overlap=ignore_model_overlap,
        ):
            return False
        if squad_has_infiltrators(squad):
            return self._infiltrator_position_valid(squad, token.radius_in, x_in, y_in)
        zone = deployment.zone_for(getattr(self.game_state, "deployment_zones", ()), squad.owner)
        if zone is None:
            return True
        return zone.contains_circle(x_in, y_in, token.radius_in)

    def overlay_position_valid(self, squad, token, x_in, y_in):
        """What the green/red placement overlay paints DURING DEPLOYMENT: the
        full predicate above minus the "another model already stands here"
        term (user: "ich finde es sinnlos bei der aufstellung. ich sehe ja,
        wenn sich modelle ueberlappen").

        The omitted term is the only one you can read off the board with your
        own eyes - a base is drawn where it stands. Everything the overlay
        still paints is invisible information: the deployment zone edge
        (03.01), Dense terrain you may not end on (13.05), the board edge, and
        the 8" INFILTRATORS bubbles (24.20).

        Deliberately NOT dropped from the real predicate. The rule is still
        enforced twice over - clamp_drag()/apply_group_drag() slide a model to
        the boundary rather than onto a neighbour, and confirm_setup() runs
        Squad.check_model_overlap() - so what this hides can never be
        committed, only un-nagged about. This is therefore a painted region
        slightly LARGER than the legal one, and that direction is the safe
        one: a drag into it stops with the reason visibly standing there.

        Only deployment. Ingress (20.04) and Disembark (18.04/18.05) keep the
        full picture: those place a unit next to enemies under a distance
        limit, where a spot lost to a foreign base is neither obvious nor
        cheap - a failed Emergency Disembark destroys the unit.
        """
        return self.position_valid(squad, token, x_in, y_in, ignore_model_overlap=True)

    def _infiltrator_position_valid(self, squad, radius_in, x_in, y_in):
        """Rule 24.20 (INFILTRATORS): "During deployment, if every model in a
        unit has this ability, it can be set up anywhere on the battlefield
        that is more than 8" horizontally from your opponent's deployment
        zone and all enemy units."

        "Horizontally" is plain 2D board distance here - this engine models no
        vertical axis (a deliberate simplification, see CLAUDE.md), so it is
        the same edge distance used everywhere else.

        Measuring against only the enemy models CURRENTLY on the battlefield
        is not an approximation: 24.20 is evaluated at the instant the unit is
        set up. The consequence is about ORDER, not legality - an INFILTRATORS
        unit placed early gains nothing from the ability, which is why
        ai/agent_driver.py's _deployment_order_key puts them last."""
        for zone in self._enemy_zones_for(squad):
            if zone.distance_to_point(x_in, y_in) - radius_in <= INFILTRATORS_MIN_ENEMY_DISTANCE_IN:
                return False
        return infiltrators_clear_of_enemies(
            x_in, y_in, radius_in, self.setup_controller.all_tokens, squad.owner
        )

    def _extra_check(self, squad):
        """Confirm-time counterpart of position_valid(), per model, with
        human-readable messages. SetupController.confirm_setup() already
        covers coherency, terrain, overlap and rule 03.02's unengaged
        requirement."""
        errors = []
        if squad_has_infiltrators(squad):
            for model in squad.models:
                if not self._infiltrator_position_valid(squad, model.radius_in, model.x_in, model.y_in):
                    errors.append(
                        f"Rule 24.20 (INFILTRATORS): every model must be set up more than "
                        f'{INFILTRATORS_MIN_ENEMY_DISTANCE_IN:g}" from your opponent\'s deployment '
                        f"zone and from all enemy units."
                    )
                    break
            return errors

        zone = deployment.zone_for(getattr(self.game_state, "deployment_zones", ()), squad.owner)
        if zone is None:
            return errors
        for model in squad.models:
            if not zone.contains_circle(model.x_in, model.y_in, model.radius_in):
                errors.append("Rule 03.01: your unit must be set up wholly within your deployment zone.")
                break
        return errors

    # --- Resolve Pre-battle Abilities (24.31) ----------------------------

    def _begin_prebattle_abilities(self, then_rolloff=False):
        self.state = PREBATTLE_ABILITIES
        self._pending_rolloff_after_scouts = then_rolloff
        self._log("Pre-battle: Resolve Pre-battle Abilities (rule 03.01).")
        self._prebattle_queue = list(self.prebattle_steps)
        self._run_next_prebattle_step()

    def _run_next_prebattle_step(self):
        """Drain prebattle_steps in order, then hand over to scouts_step.

        With an empty prebattle_steps this is exactly what this method used to
        do inline, which is what keeps every existing harness and test
        unchanged."""
        while self._prebattle_queue:
            step = self._prebattle_queue.pop(0)
            # Two ways a step takes over: True ("a prompt is on screen") or a
            # continuation it already fired itself. Without the second test the
            # step's synchronous on_done drains the rest of THIS queue and
            # starts the Scouts step, and then this loop - now looking at an
            # empty queue - starts it again. See Resume.
            resume = Resume(self._run_next_prebattle_step)
            if step.start(self, resume) or resume.fired:
                return
        if self.scouts_step is None:
            self.finish_prebattle_abilities()
            return
        self.scouts_step.start(self)

    def finish_prebattle_abilities(self):
        if getattr(self, "_pending_rolloff_after_scouts", False):
            self._pending_rolloff_after_scouts = False
            self._begin_first_turn_rolloff()
            return
        self._begin_battle()

    def _begin_battle(self):
        # The battle begins ONCE. on_battle_start hands out Core CP and scores
        # the first Command phase's Primary (main.py's begin_battle), neither
        # of which is idempotent, so a second call is worth a whole extra round
        # of VP to whoever holds the most objectives at deployment. The
        # re-entrancy that produced it is fixed at its source (see Resume), and
        # this is the backstop: nothing that reaches here twice can pay twice.
        if self.state == DONE:
            return
        self.state = DONE
        self.selected_unit = None
        winner = self.first_player or self.first_human()
        if self.on_battle_start is not None:
            self.on_battle_start(winner)
