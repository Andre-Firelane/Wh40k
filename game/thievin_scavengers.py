"""Gretchin's Thievin' Scavengers (2026-09 Ork codex).

RULE (verbatim, rules/orks/Gretchin.md):
  "Thievin' Scavengers: At the end of your Movement phase, if this unit is
   controlling an objective, that objective is secured."

REPLACES the pre-codex rule of the same name (a Movement-phase-START D6 per
controlled objective for 1CP, with its own DiceManager roll). Nothing of that
survives: no roll, no CP, no controller.

"SECURED" is rule 14.03's existing mechanism, Objective.secure_for() - the same
sticky control Fieldcraft and Marker Beacon grant, so a Gretchin unit can walk
off afterwards and the objective stays theirs until the opponent's raw Level of
Control is strictly greater.

"AT THE END OF YOUR MOVEMENT PHASE" is main.py's `phase_before ==
PHASE_MOVEMENT` block, which runs AFTER the phase boundary's update_control():
an objective the Gretchin walked onto in this very move is controlled_by their
player from that recount on - asked before it, they would secure nothing they
took this turn. The player is `mover_before`, never the flipped turn_owner.

"THIS UNIT IS CONTROLLING AN OBJECTIVE": its player controls the objective AND
the unit is part of that control - a living model counted by rule 14.02 there
(inside the footprint, effective OC above 0, not battle-shocked). The same
three filters Objective.level_of_control() applies, asked of this unit's
models, so the two cannot disagree about who is "controlling". A Gretchin unit
3" away from an objective its army holds is not controlling it.
"""

from game.squad import squad_has_thievin_scavengers

THIEVIN_SCAVENGERS_NAME = "Thievin' Scavengers"


def unit_is_controlling(squad, objective, all_tokens):
    if squad is None or objective.controlled_by != squad.owner or squad.battle_shocked:
        return False
    from game import objective_control
    for model in squad.models:
        if model.is_dead() or not objective.terrain_area.overlaps_model(model):
            continue
        if objective_control.effective_oc(model, all_tokens, objective=objective) > 0:
            return True
    return False


def secure_at_end_of_movement(objectives, all_tokens, player, game_log=None):
    """Secure every objective a Thievin' Scavengers unit of `player` is
    controlling. Returns the objectives it secured (already-secured ones are
    re-secured silently)."""
    squads = sorted({t.squad for t in all_tokens or ()
                     if t.squad is not None and t.squad.owner == player},
                    key=lambda s: s.name)
    scavengers = [s for s in squads if squad_has_thievin_scavengers(s)]
    if not scavengers:
        return []
    secured = []
    for objective in objectives or ():
        holders = [s for s in scavengers if unit_is_controlling(s, objective, all_tokens)]
        if not holders:
            continue
        newly = objective.secured_by != player
        objective.secure_for(player)
        if newly:
            secured.append(objective)
            if game_log is not None:
                game_log.add(f"{THIEVIN_SCAVENGERS_NAME}: {holders[0].name} secures "
                             f"{objective.name} for {player}.")
    return secured
