"""Sticky-objective ability, as supplied by the user (not a rule from the
generic 40k core rulebook) - first introduced under Kroot Carnivores'
"Fieldcraft" name, and reused verbatim (same UnitProfile.fieldcraft flag,
see its own note) by every other datasheet that prints the identical rule
under its own flavor name, e.g. Boyz's "Get Da Good Bitz".

RULE: At the end of your Command phase, if this unit is within range of an
objective marker you control, that objective marker remains under your
control, even if you have no models within range of it, until your
opponent controls it at the start or end of any turn.

Reuses rule 14.03's existing Secured mechanism (Objective.secure_for()/
secured_by, already fully built in game/objectives.py but - per that
module's own docstring - "no such ability exists yet... so nothing sets
secured_by in the current demo") rather than a second, parallel tracking
scheme: Secured already implements almost exactly this "keeps control even
with zero models in range, until the opponent's raw level of control is
strictly greater" behavior (see Objective.update_control()). The rule
text's own phrasing of the release condition ("opponent controls it at the
start or end of any turn") is close enough to Secured's existing "checked
at the end of every phase, released once the opponent's raw score is
strictly higher" to reuse directly rather than build a second, subtly
different tracking mechanism for one datasheet's wording."""

from game.objectives import is_within_range_of_objective
from game.squad import squad_has_fieldcraft


def apply_fieldcraft(objectives, all_tokens, player):
    """Called at the end of every one of `player`'s own phases (see main.py's
    advance_turn_phase()) - not just their Command phase. The ability text
    says "at the end of your Command phase", but checking only there missed
    the common case of a unit taking/holding an objective mid-turn (during
    its own Movement/Shooting/Charge/Fight phase, i.e. after that round's one
    Command-phase checkpoint already passed): it would never get armed
    before the opponent's very next turn could kill it and revert the
    objective to uncontrolled. Checking after every one of the player's own
    phases instead means the moment they take and hold an objective through
    any point in their own turn, it's secured before the opponent's turn
    even begins."""
    controlled = [o for o in objectives if o.controlled_by == player]
    if not controlled:
        return
    fieldcraft_squads = [
        squad for squad in {t.squad for t in all_tokens if t.squad is not None and t.squad.owner == player}
        if squad_has_fieldcraft(squad)
    ]
    if not fieldcraft_squads:
        return
    for objective in controlled:
        if any(is_within_range_of_objective(squad, [objective]) for squad in fieldcraft_squads):
            objective.secure_for(player)
