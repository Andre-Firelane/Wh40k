"""Orks detachment stratagem: War Horde's 'Ere We Go, as supplied by the user
(not a rule from the generic 40k core rulebook, so it lives in its own module -
same reasoning as game/war_horde.py for that detachment's Get Stuck In rule and
game/unbridled_carnage.py / game/ard_as_nails.py for its other stratagems).

RULE ('Ere We Go, 1CP, War Horde Battle Tactic Stratagem):
  WHEN:   Start of your Movement phase.
  TARGET: One ORKS INFANTRY unit from your army.
  EFFECT: Until the end of the turn, add 2 to Advance and Charge rolls made
          for your unit.

WHERE THE +2 IS APPLIED
-----------------------
On the roll TOTAL, in the one place each of the two rolls is turned into a
distance, so every caller downstream sees the boosted number without knowing
about this stratagem:

  * Advance - game/movement.py's advance_total(), which start_run() and its
    Command Re-roll reconciliation both go through. They HAVE to share it: the
    bonus is applied synchronously when the die is rolled, and the
    reconciliation compares that against the re-rolled value, so a +2 in one
    and not the other would silently un-apply itself on any re-roll.
  * Charge - game/charge.py's _capped_roll(), which is likewise shared by the
    roll being acknowledged and by targets_reachable_with()'s forecast (the
    Command Re-roll verdict). Applying it there also gets rule 15.11's "if the
    result is greater than 6 AFTER MODIFIERS" right for free: the +2 is a
    modifier, so it lands before the cap.

Deliberately NOT modeled as a game/modifiers.py Modifier: those adjust a
THRESHOLD a die has to beat (hit/wound/save), and this changes the distance a
roll produces. Different quantity, different place.

"UNTIL THE END OF THE TURN"
---------------------------
A unit-level flag (Squad.ere_we_go_active), cleared in main.py's end-of-turn
block alongside fights_first / set_up_this_turn / charge_locked_until_end_of_
turn - the other three "until the end of the turn" flags, which is exactly the
lifetime this one has. expire_for_turn() below is the one definition of that,
so it stays testable without the game loop.

SIMPLIFICATION (documented, matching game/war_horde.py's own note): no
army-building/detachment-selection flow exists yet and War Horde is the only
Orks detachment, so there is no "is this army actually running War Horde"
check. Both halves of the TARGET clause ARE checked - ORKS and INFANTRY, both
through rule 19.03's keyword pooling.
"""

from game.attached_units import unit_has_keyword
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT
from game.unbridled_carnage import is_orks_unit

ERE_WE_GO_CP_COST = 1
ERE_WE_GO_ROLL_BONUS = 2


def is_orks_infantry_unit(squad):
    """TARGET: "One ORKS INFANTRY unit from your army".

    Both keywords via rule 19.03's pooling ("an attached unit has all of the
    keywords of all of its component units"), so a Boyz mob with a Warboss
    joined still qualifies - the same reading, and the same helper, that
    game/ard_as_nails.py's own TARGET clause uses."""
    if squad is None or not squad.models:
        return False
    if not is_orks_unit(squad):
        return False
    return unit_has_keyword(squad, lambda m: getattr(m.profile, "infantry", False))


def roll_bonus(squad):
    """The +2 this unit currently adds to its Advance and Charge rolls, or 0.

    Read straight off the unit flag so game/movement.py and game/charge.py can
    consult it without depending on the controller - same arrangement as
    Squad.stim_injectors_active and Squad.ard_as_nails_active."""
    if squad is not None and getattr(squad, "ere_we_go_active", False):
        return ERE_WE_GO_ROLL_BONUS
    return 0


class EreWeGoController:
    """WHEN/TARGET bookkeeping plus the "until the end of the turn" grant. The
    EFFECT itself is roll_bonus() above, read by the two roll sites.

    Proactive, like The Arro'kon Protocol and Unbridled Carnage: the active
    player buys it at a moment of their own choosing, so there is no
    DecisionManager hook - a plain ActionPanel button for a human, and a
    deterministic call for the AI (see ai/agent_driver.py's
    _handle_ere_we_go(), per the user: "auch deterministisch. bei der ersten
    gelegenheit eines squads im waagh zug")."""

    def __init__(self, stratagem_controller, movement_controller=None, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(name="'Ere We Go", cp_cost=ERE_WE_GO_CP_COST, effect=self._grant)

    def expire_for_turn(self, squads=()):
        """End of turn: the grant expires ("until the end of the turn").

        Lives here rather than in main.py's turn loop so "when does this stop
        applying" has exactly one answer and is testable without the game loop
        - same shape as ArdAsNailsController.reset_phase(). Callers pass the
        ENDING player's own squads; nobody else can be holding this grant,
        since only the active player can buy it in their own Movement phase."""
        for squad in squads:
            squad.ere_we_go_active = False

    def can_use(self, squad):
        if squad is None:
            return False
        if self.turn_tracker is not None:
            # WHEN: "Start of YOUR Movement phase" - the phase, and whose it is.
            if self.turn_tracker.phase != PHASE_MOVEMENT:
                return False
            if squad.owner != self.turn_tracker.turn_owner:
                return False
        if getattr(squad, "ere_we_go_active", False):
            return False  # already up on this unit - nothing left to buy
        if not is_orks_infantry_unit(squad):
            return False
        # "START of your Movement phase". This engine has no sub-phase clock,
        # so the checkable reading is "before anything of yours has moved" -
        # once a unit has been moved (or has remained stationary, which is
        # equally a movement decision, rule 09.02), the start of the phase has
        # passed. Deliberately a whole-ARMY check rather than a per-unit one:
        # the clause is about the moment, not about this unit.
        if self.movement_controller is not None:
            if any(s.owner == squad.owner for s in self.movement_controller.moved_squad_ids):
                return False
            # A move already OPEN (mid-drag) also means the phase is under way.
            # Compared as a literal rather than importing movement.MOVING:
            # game/movement.py imports THIS module for the Advance bonus, so an
            # import back the other way would be a cycle. Merely SELECTING a
            # unit is not movement and deliberately does not close the window -
            # that is how the human reaches the button at all, since the
            # ActionPanel only offers it for a selected squad.
            if self.movement_controller.state == "moving":
                return False
        # Rule 15.01's once-per-phase/one-target-per-phase, CP, and 01.07's
        # battle-shock block.
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        """Spends the CP and puts the grant up. TARGET is trivial (always this
        one unit), so there is no separate selection step to cancel out of -
        the CP is committed right here, exactly like ArrokonProtocolController
        and UnbridledCarnageController."""
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        squad = targets[0]
        squad.ere_we_go_active = True
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: 'Ere We Go - {squad.name} adds {ERE_WE_GO_ROLL_BONUS} to its Advance and "
                "Charge rolls until the end of the turn."
            )
