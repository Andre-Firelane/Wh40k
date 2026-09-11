from game.shooting import SNAP_SHOOTING
from game.stratagems import Stratagem

FIRE_OVERWATCH_CP_COST = 1

IDLE = "idle"
CHOOSING_UNIT = "choosing_unit"  # pick which of this player's own eligible units fires Snap Shooting


def _other_player(player):
    return "Player 2" if player == "Player 1" else "Player 1"


class FireOverwatchController:
    """Rule 15.08 (Fire Overwatch, Core Stratagem, 1CP) + 15.09 (Snap
    Shooting): WHEN end of your opponent's Movement phase, TARGET one
    friendly unengaged unit (excluding TITANIC - no TITANIC keyword exists
    yet, so this carve-out never excludes anyone, same reasoning as Rapid
    Ingress's AIRCRAFT carve-out, game/rapid_ingress.py), EFFECT that unit
    shoots using Snap Shooting - fully implemented as a fifth shooting type
    in game/shooting.py (ShootingController.start_snap_shooting(),
    SNAP_SHOOTING): hits only on an unmodified 6 irrespective of BS or any
    modifiers, no hit-roll re-rolls (a distinct SNAP_SHOT_HIT_ROLL dice-kind
    CommandRerollController's REROLLABLE_KINDS never includes), exactly one
    visible target within 24" (no split fire).

    Same reactive-decision shape as Rapid Ingress - see that module's
    docstring for the WHEN/chaining. Real user report/redesign request,
    though: the original implementation offered this as a
    game.decision.DecisionManager text-button list ("Fire Overwatch: <squad
    name> (1 CP)") - with several same-name-but-numbered squads on the
    board (e.g. two "Strike Team 1"/"Strike Team 2"), the player had no way
    to tell which button corresponded to which unit on the battlefield
    itself. Reworked into the SAME "own state machine + board-click target,
    left-panel Decline button" shape every other stratagem/ability target
    picker in this codebase already uses (Explosives' CHOOSING_TARGET,
    Crushing Impact's CHOOSING_ENEMY, For The Greater Good's
    CHOOSING_TARGET) - main.py highlights every eligible_squads() unit on
    the board itself (renderer.draw_shoot_targets(), reused) and routes a
    click on one of them to choose_unit(); the panel only ever needs a
    "Fire Overwatch (1 CP) - click a unit..." message and a Decline button,
    exactly what the user asked for, since "which button is which unit" is
    no longer a question at all when the units themselves are what's
    clicked.

    main.py's advance_turn_phase() still offers this right after Rapid
    Ingress, chained via Rapid Ingress's on_resolved (same instant, same
    "don't show two reactive things at once" reasoning as before) - it no
    longer shares DecisionManager's single-slot lock with anything, but the
    sequencing itself is still worth keeping.

    One wrinkle Rapid Ingress didn't have: the chosen unit belongs to the
    OPPONENT of whoever's phase this actually still nominally is (`mover`,
    captured here and never re-read from turn_tracker afterward, since
    ShootingController's own resolution repeatedly flips
    turn_tracker.active_player to whichever player is mid-decision, e.g.
    the defender during the save roll). _on_shot_finished() restores it
    once Snap Shooting actually concludes - completed OR cancelled,
    start_snap_shooting()'s on_finished fires from both
    _actually_finish_squad() and cancel()."""

    def __init__(self, stratagem_controller, shooting_controller, all_tokens=None, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        # Guardian Battlehost's Protector of the Paths, injected by main.py.
        # None means nobody plays that detachment.
        self.protector_of_the_paths = None
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.game_log = game_log

        self.state = IDLE
        self.player = None  # whose choice this is (the opponent of _mover), while state == CHOOSING_UNIT
        self._mover = None  # whose phase this actually is, to restore once the snap shot ends
        self._on_resolved = None
        # ...and where it waits while the snap shot it started plays out. See
        # choose_unit() for why picking a unit DEFERS the chain instead of
        # continuing it - the same deferral RapidIngressController._pick() does
        # one link earlier, for the same reason.
        self._deferred_on_resolved = None
        self._stratagem = Stratagem(name="Fire Overwatch", cp_cost=FIRE_OVERWATCH_CP_COST, effect=self._resolve)

    def _all_squads(self):
        return {t.squad for t in self.all_tokens if t.squad is not None}

    def _eligible_squads(self, player):
        """Rule 15.08/15.09: unengaged isn't enough on its own - the unit
        also needs at least one weapon that can actually reach a visible
        enemy within Snap Shooting's own 24" cap (SNAP_SHOT_RANGE_IN) once
        it activates. Real user report: this used to just check "has any
        ranged weapon at all" (_attack_groups(s)), so units clear across the
        board with nothing whatsoever in range were offered the stratagem
        every single time - has_valid_target() reuses the exact same
        eligibility logic real Snap Shooting targeting enforces (range,
        line of sight, Hidden, engagement, LONE OPERATIVE) instead of
        duplicating a looser approximation of it here."""
        return [
            s for s in self._all_squads()
            if s.owner == player and not s.is_engaged(self.all_tokens)
            and self.shooting_controller.has_valid_target(s, SNAP_SHOOTING, self.all_tokens)
        ]

    def offer(self, mover, on_resolved=None):
        """Called right after `mover`'s Movement phase ends - opens the
        "pick a unit on the battlefield" window for `mover`'s opponent. No-
        op (and, if given, `on_resolved()` fires right away) if nothing
        qualifies, so an empty offer never opens a "Decline"-only screen
        nor stalls a chained reactive-stratagem sequence."""
        opponent = _other_player(mover)
        if not self._qualifying_squads(opponent):
            if on_resolved is not None:
                on_resolved()
            return
        self.state = CHOOSING_UNIT
        self.player = opponent
        self._mover = mover
        self._on_resolved = on_resolved

    def _qualifying_squads(self, player):
        return [
            squad for squad in self._eligible_squads(player)
            if self.stratagem_controller.can_use(player, self._stratagem, [squad])
        ]

    def eligible_squads(self):
        """The units `self.player` can currently pick, computed live (not
        snapshotted at offer() time) - same reasoning as every other target
        picker in this file (Explosives, Crushing Impact, For The Greater
        Good): eligibility (engaged/CP/once-per-phase) could in principle
        change while this screen is open."""
        if self.state != CHOOSING_UNIT or self.player is None:
            return []
        return self._qualifying_squads(self.player)

    def choose_unit(self, squad):
        if self.state != CHOOSING_UNIT or squad not in self.eligible_squads():
            return
        player = self.player
        on_resolved = self._on_resolved
        self.state = IDLE
        self.player = None
        self._on_resolved = None
        # self._mover is deliberately left set - _resolve()/_on_shot_finished()
        # (below) still need it to restore turn_tracker.active_player once
        # the Snap Shooting activation this triggers actually concludes.
        #
        # THE CHAIN IS DEFERRED, NOT CONTINUED HERE. use() starts a whole Snap
        # Shooting activation - dice, saves, allocation, several frames of it -
        # and firing on_resolved() on this line would drop whatever comes next
        # on top of a salvo still being resolved. That is the same mistake
        # RapidIngressController._pick() records one link earlier in this very
        # chain ("this steals the decision-overlay modal away from the
        # Reserves-panel drag they still needed to make"), and the reported
        # collision it caused here was Eater Plague's dice landing underneath a
        # Rapid Ingress placement.
        #
        # _on_shot_finished() fires it instead, and that runs from BOTH exits
        # of start_snap_shooting()'s on_finished - completed and cancelled.
        self._deferred_on_resolved = on_resolved
        self.stratagem_controller.use(player, self._stratagem, [squad])

    def decline(self):
        if self.state != CHOOSING_UNIT:
            return
        on_resolved = self._on_resolved
        self.state = IDLE
        self.player = None
        self._mover = None
        self._on_resolved = None
        if on_resolved is not None:
            on_resolved()

    def _resolve(self, controller, player, targets):
        squad = targets[0]
        if self.game_log is not None:
            self.game_log.add(f"{player}: Fire Overwatch - {squad.name} shoots using Snap Shooting (rule 15.09).")
        mover = self._mover
        self.shooting_controller.start_snap_shooting(squad, on_finished=lambda: self._on_shot_finished(mover))
        # ...unless it never began. start_snap_shooting() has an early exit for
        # a squad with no attack groups, and on that path on_finished is never
        # set, so nothing would ever fire - the deferred chain would strand and
        # turn_tracker.active_player would stay on the wrong player, which is a
        # defect that predates the deferral. "Never started" is "already
        # finished", so it is settled here.
        if getattr(self.shooting_controller, "active_squad", None) is not squad:
            self._on_shot_finished(mover)

    def _on_shot_finished(self, mover):
        # Protector of the Paths' better threshold lasts only "while resolving
        # THAT Stratagem" - this is where that ends.
        if self.protector_of_the_paths is not None:
            self.protector_of_the_paths.clear_activation()
        if self.turn_tracker is not None and mover is not None:
            self.turn_tracker.set_active(mover)
        self._mover = None
        # The salvo is over, so whatever was chained behind this Stratagem may
        # run now. Taken rather than read, so a second call (cancel after a
        # completed shot, say) cannot fire it twice.
        callback, self._deferred_on_resolved = self._deferred_on_resolved, None
        if callback is not None:
            callback()
