"""Kauyon Enhancement: Solid-image Projection Unit (20 pts).

RULE (verbatim, rules/tau_empire/detachments/Kauyon.md):
  T'AU EMPIRE model only. After both players have deployed their armies, select
  up to three T'AU EMPIRE units from your army and redeploy them. When doing
  so, you can set those units up in Strategic Reserves if you wish, regardless
  of how many units are already in Strategic Reserves.

WHEN, AND WHY IT IS NOT A PRE-BATTLE STEP
------------------------------------------
"After both players have deployed their armies" is EARLIER than rule 03.01's
Resolve Pre-battle Abilities step - Determine First Turn sits between the two.
Putting it in the pre-battle queue beside Strike Swiftly would let a player
redeploy knowing who goes first, which is a materially different (and much
stronger) ability.

So it hangs off PregameController._finish_deployment(), which is exactly the
instant the printed text names.

REDEPLOY REUSES THE DEPLOYMENT FLOW RATHER THAN COPYING IT
-----------------------------------------------------------
A unit chosen for redeployment has its models taken off the board and is put
back into PregameController's own `_pending` queue, with the controller
returned to DEPLOYING. Placing it again then goes through start_deployment() /
confirm_deployment() - the same validation, the same overlay, the same
alternation - and when the queue empties, _advance_if_nothing_to_place() reaches
_finish_deployment() a second time. That is what the `_redeploy_done` flag
there is for: the second visit skips this step and goes on to the first-turn
roll-off.

Nothing here re-implements placement. The alternative - a bespoke "pick a new
spot" mode - would be a second placement validator, and the three bugs this
repo has already recorded about placement all came from a second path that
knew one condition less than confirm_setup() does.

"REGARDLESS OF HOW MANY UNITS ARE ALREADY IN STRATEGIC RESERVES" is the clause
that makes the Reserves branch worth anything: rule 20.01 caps an army's
reserves, and this deliberately ignores that cap. This engine enforces 20.01 in
PregameController.finish_formations_for()'s own declaration step, which has
already run by now - so the cap is structurally not in the way here, and the
clause is a documented no-op rather than something to switch off. Said out loud
because "we ignore the cap" reading as "there is no cap" is the sort of thing
that gets re-implemented later.

TAKING A UNIT OFF THE BOARD is game/strategic_reserves.py's removal step for
the Reserves branch. The redeploy branch needs the same removal WITHOUT the
reserves destination, which is the four lines in _take_off_board() - not shared,
because what makes that function worth having is the two things it does AFTER
the removal (clearing the ingress lock, recomputing objective control), and
neither is right for a unit that is about to be placed again in the same step.

UP TO THREE, one prompt per unit, declining legal - the same shape Student of
Kauyon and Strike Swiftly use, and for the same reason (a flat option list
cannot express "three of twelve").

An owner in `auto_players` DECLINES. That is not laziness: redeployment is a
whole-army positional judgement, the deployment AI has already placed this army
where it wanted it, and moving three units at random after the fact would make
its own deployment worse. A deterministic answer that does nothing is honest;
inventing a heuristic here would be inventing an AI path, which the standing
T'au rule says not to do.
"""

from game import enhancements
from game.post_deployment_redeploy import (  # noqa: F401  (re-exported, see below)
    MAX_UNITS, REDEPLOY, RESERVES, PostDeploymentRedeployStep,
)

SOLID_IMAGE_PROJECTION_UNIT = "Solid-image Projection Unit"


class SolidImageProjectionStep(PostDeploymentRedeployStep):
    """Registered as PregameController.redeploy_step by main.py.

    THE MACHINE MOVED OUT, the two printed words stayed. The C'tan Shard of the
    Deceiver's Grand Illusion prints this same sentence with "NECRONS" for
    "T'AU EMPIRE" and a datasheet for an Enhancement, so the shared half now
    lives in game/post_deployment_redeploy.py - extracted at the second
    carrier, as this repo does.

    MAX_UNITS, REDEPLOY and RESERVES are RE-EXPORTED above rather than moved,
    so every existing reader of this module keeps working unchanged."""

    label = SOLID_IMAGE_PROJECTION_UNIT

    def bearer_units(self, player):
        return enhancements.bearer_units(self._squads(), SOLID_IMAGE_PROJECTION_UNIT,
                                         player=player)

    def grants(self, player):
        return bool(self.bearer_units(player))

    def in_faction(self, squad):
        '''"up to three T'AU EMPIRE units from your army".'''
        from game import tau_detachments
        return tau_detachments.is_tau_unit(squad)
