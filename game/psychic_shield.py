"""Seer Council's "Psychic Shield" (1CP, Strategic Ploy).

RULE (printed, word for word):
  WHEN: "Your opponent's Shooting phase, just after an enemy unit has selected
  its targets"
  TARGET: "One ASURYANI INFANTRY unit from your army (excluding WRAITH
  CONSTRUCT units) that was selected as the target of one or more of the
  attacking unit's attacks and is within 9" of one or more friendly ASURYANI
  PSYKER models"
  EFFECT: "Until the end of the phase, your unit can only be selected as the
  target of a ranged attack if the attacking model is within 18"."

THE EFFECT IS AN EXISTING MECHANIC. "Can only be selected as the target of a
ranged attack if the attacking model is within X inches" is word for word what
LONE OPERATIVE (24.24) does, and game/shooting.py already reads that at the two
places targeting is decided. So this needs no new rule - only a second,
phase-scoped source of the same limit, which is why the range is stored on the
unit (Squad.psychic_shield_range) and folded in game/status_effects.py's
targeting_range_limit(): the tighter of the two wins, and neither module has to
know about the other.

THE HARD PART IS THE TIMING, and it is what makes this different from the two
reactive stratagems that share its trigger. User, spelling it out: "denke daran,
dass dich das aktiviere, nachdem ich als ziel gewählt wurde. das heißt. wenn ich
es dann aktiviere, muss sich die ki ein anderes ziel suchen."

Exactly right, and it follows from the printed text: the EFFECT restricts what
can be "SELECTED as the target", and the WHEN fires just after a selection was
made. Stim Injectors and 'Ard as Nails only add a modifier to attacks that are
already going ahead; this one can make the selection that just happened ILLEGAL.
So the attacker's activation has to go back to the select-targets step -
ShootingController.revalidate_target_selection() does that, and this controller
calls it once the stratagem actually lands.

Rule 10.02's snapshot is not in the way: _is_valid_target_squad() answers from
live positions (it measures LONE OPERATIVE's range with edge_distance() there and
then), so the newly-illegal target is refused as soon as the limit is up. The
snapshot only freezes reach/cover FOR a target already legally selected, and
revalidate_target_selection() drops the entries for a selection it undoes.

NOT FIRE OVERWATCH. A snap shot (15.08/15.09) is a ranged attack made at the end
of the opponent's MOVEMENT phase, and this WHEN names their Shooting phase - so
the offer is gated on the phase, not merely on "someone shot at me".

AND NOT WHEN THE SHOOTER IS ALREADY INSIDE 18". See the gate in can_use() - a
shooter that close keeps this target whether the stratagem is used or not, so
the offer would be a pure interruption. That gate is the one thing here that is
a choice about WHEN TO ASK rather than about the rule.
"""

from game import attached_units
from game import psychic_guidance
from game.turn import PHASE_SHOOTING
from game.stratagems import Stratagem

PSYCHIC_SHIELD_CP = 1
PSYCHIC_SHIELD_NAME = "Psychic Shield"
PSYCHIC_SHIELD_RANGE_IN = 18.0
PSYCHIC_SHIELD_PSYKER_RANGE_IN = 9.0


def applies(squad):
    return squad is not None and getattr(squad, "psychic_shield_range", None) is not None


def reset_phase(squads=()):
    """"Until the end of the phase"."""
    for squad in squads:
        squad.psychic_shield_range = None


class PsychicShieldController:
    """An entry in game/shooting.py's target_reactions list - the same
    maybe_offer(attacker, target, melee) contract as Stim Injectors and 'Ard as
    Nails.

    `on_activated` is wired (in main.py) to
    ShootingController.revalidate_target_selection, because unlike those two this
    stratagem can invalidate the selection that triggered it. Kept as a plain
    callback rather than a controller reference, the same arrangement
    MovementController.on_fall_back_finished uses."""

    def __init__(self, stratagem_controller=None, decision_manager=None, game_log=None,
                 all_tokens=None, turn_tracker=None, on_activated=None):
        self.stratagem_controller = stratagem_controller
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.on_activated = on_activated
        self._stratagem = Stratagem(
            name=PSYCHIC_SHIELD_NAME, cp_cost=PSYCHIC_SHIELD_CP, effect=self._effect,
        )
        self._handled_this_phase = set()

    def reset_phase(self):
        self._handled_this_phase.clear()

    def can_use(self, attacker, target):
        from game.forewarned import eligible_unit, near_friendly_psyker
        if self.stratagem_controller is None or attacker is None or target is None:
            return False
        if target.owner == attacker.owner:
            return False
        if applies(target):
            return False   # already up on this unit
        # "Your opponent's Shooting phase": the phase, and the turn belongs to
        # the attacker - which also keeps a Fire Overwatch snap shot out.
        if self.turn_tracker is None or self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if self.turn_tracker.turn_owner != attacker.owner:
            return False
        # The TARGET clause's unit conditions are identical to Forewarned's, so
        # they are read from there rather than duplicated - one wording, one
        # implementation. Imported inside the method only to keep these two
        # sibling modules from importing each other at module level.
        if not eligible_unit(target):
            return False
        if not near_friendly_psyker(target, self.all_tokens):
            return False
        # RELEVANCE GATE (user: "frage nur nach psychic shield, wenn angreifer
        # mehr als 18\" entfernt"). Not a heuristic - a certainty, and it is
        # measured with the SAME yardstick the effect itself is enforced with:
        # game/shooting.py's _is_valid_target_squad() denies the target only
        # when NO attacking model is within the limit of ANY target model, i.e.
        # exactly when the closest pair is beyond it. min_distance_to() is that
        # closest edge-to-edge pair. So a shooter already inside 18" would be
        # allowed to keep this target either way and the CP buys literally
        # nothing against it. Same honest-eligibility line as Fire Overwatch's
        # _eligible_squads() and The Arro'kon Protocol's "nothing in reach is
        # big enough" - and it matters more here than for most, because this
        # trigger fires on EVERY enemy target selection.
        #
        # Deliberately not a "the offer is still worth something against some
        # OTHER unit later this phase" allowance: the effect lasts the phase,
        # but the prompt names this attacker and this target, and offering it
        # on a shooter it cannot affect is the interruption the user asked to
        # be rid of.
        if attacker.min_distance_to(target) <= PSYCHIC_SHIELD_RANGE_IN:
            return False
        return self.stratagem_controller.can_use(target.owner, self._stratagem, [target])

    def maybe_offer(self, attacker, target, melee=False):
        if melee:
            return False   # ranged only, per the EFFECT
        key = (id(attacker), id(target))
        if key in self._handled_this_phase:
            return False
        if not self.can_use(attacker, target):
            return False
        self._handled_this_phase.add(key)
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            target.owner,
            f"Psychic Shield ({PSYCHIC_SHIELD_CP} CP): {attacker.name} has targeted "
            f"{target.name}. Until the end of the phase it can only be targeted by ranged "
            f'attacks from within {PSYCHIC_SHIELD_RANGE_IN:g}" - which may force '
            f"{attacker.name} to pick a different target.",
            [
                (f"Psychic Shield ({PSYCHIC_SHIELD_CP} CP)", lambda: self._use(target)),
                ("Decline", lambda: None),
            ],
        )
        return True

    def _use(self, target):
        self.stratagem_controller.use(target.owner, self._stratagem, [target])

    def _effect(self, controller, player, targets):
        target = targets[0]
        target.psychic_shield_range = PSYCHIC_SHIELD_RANGE_IN
        if self.game_log is not None:
            self.game_log.add(
                f"Psychic Shield: until the end of the phase, {target.name} can only be "
                f'selected as the target of a ranged attack from within {PSYCHIC_SHIELD_RANGE_IN:g}".'
            )
        # The selection that triggered this may now be illegal - see the module
        # docstring. Only the attacker's own controller can undo it.
        if self.on_activated is not None:
            self.on_activated()
