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

from game import deployment
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
        human_player="Player 1",
    ):
        self.game_state = game_state
        self.setup_controller = setup_controller
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.on_battle_start = on_battle_start
        self.human_player = human_player

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
        # Optional callable(squad) - wired by main.py to the AI's own
        # deployment placer, so the human can hand a unit to it ("Auto-place
        # this unit"). A callback rather than an import so game/ never depends
        # on ai/.
        self.on_auto_place = None

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
        self.active_player = self.human_player
        self._sync_turn_tracker()
        self._log("Pre-battle: Declare Battle Formations (rule 03.01).")

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

    def declare(self, squad, destination, transport_token=None):
        """Record one unit's Declare Battle Formations answer."""
        if destination == EMBARK and transport_token is None:
            return
        self._declared[id(squad)] = (destination, transport_token if destination == EMBARK else None)
        return True

    def finish_formations_for(self, owner):
        """Apply that player's declarations to the game state and mark them
        done. Anything left undeclared defaults to deploying normally."""
        for squad in self.army(owner):
            if id(squad) not in self._declared:
                self._declared[id(squad)] = (DEPLOY, None)

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
        if winner == self.human_player:
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

    def position_valid(self, squad, token, x_in, y_in):
        """The live per-position predicate for a deployment placement - the
        same one the green/red overlay paints and clamp_drag() holds the
        mouse inside, so what you see and what you may do cannot drift."""
        if not self.setup_controller.position_valid(token, x_in, y_in, squad=squad):
            return False
        if squad_has_infiltrators(squad):
            return self._infiltrator_position_valid(squad, token.radius_in, x_in, y_in)
        zone = deployment.zone_for(getattr(self.game_state, "deployment_zones", ()), squad.owner)
        if zone is None:
            return True
        return zone.contains_circle(x_in, y_in, token.radius_in)

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
        self.state = DONE
        self.selected_unit = None
        winner = self.first_player or self.human_player
        if self.on_battle_start is not None:
            self.on_battle_start(winner)
