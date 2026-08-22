from game.squad import edge_distance, squad_is_attached_unit
from game.terrain import DENSE

BATTLE_SHOCKED = "battle_shocked"
HIDDEN = "hidden"
LONE_OPERATIVE = "lone_operative"
MARKED = "marked"  # T'au "For The Greater Good" army rule (game/greater_good.py) - Spotted this Shooting phase
# The three Aeldari marks that sit on an ENEMY unit. User request: "für die
# fähigkeit von lykhis und doom und guide wäre ein label nicht schlecht (2
# buchstaben)" - these last across phases (Guide and Doom until the start of
# their owner's next Command phase, Whispering Web until the end of the turn),
# so without a board label there is nothing at all to show which enemy unit is
# currently carrying one.
GUIDED = "guided"          # the Farseer's Guide (game/guide.py) - friendly AELDARI add 1 to Hit rolls against it
DOOMED = "doomed"          # Eldrad Ulthran's Doom (game/doom.py) - friendly AELDARI add 1 to Wound rolls against it
WEBBED = "webbed"          # Lhykhis' Whispering Web (game/whispering_web.py) - friendly AELDARI crit on an unmodified 5+ against it

LABELS = {
    BATTLE_SHOCKED: "BS",
    HIDDEN: "HD",
    LONE_OPERATIVE: "LONE OP",
    MARKED: "ML",
    GUIDED: "GD",
    DOOMED: "DM",
    WEBBED: "WW",
}

DETECTION_RANGE_IN = 15.0  # rule 13.09: a hidden model's default detection range
CLOSE_DETECTION_RANGE_IN = 12.0  # House rule (NOT in the rulebook - user call): if a Dense wall itself
# overlaps the hidden model's own footprint (not just "somewhere in the same terrain area" - rule
# 13.09's own has_dense_feature check is area-wide, satisfied by a wall anywhere in the area, e.g. a
# ruin's far corner), the model reads as tucked directly against/inside a wall rather than merely
# standing on open rubble within a walled area - detection range shrinks from 15" to 12" for it.
LONE_OPERATIVE_DEFAULT_RANGE_IN = 12.0  # rule 24.24: the range when the ability isn't given as "LONE OPERATIVE X\""


def targeting_range_limit(squad):
    """The tightest "can only be selected as the target of a ranged attack from
    within X inches" limit on this unit, or None.

    Two sources fold here, and the tighter wins:
      * LONE OPERATIVE (24.24), printed on the datasheet - permanent.
      * Seer Council's Psychic Shield, a stratagem - "until the end of the
        phase", so it lives on the unit as Squad.psychic_shield_range.

    Read off the squad rather than through the stratagem's controller, the same
    arrangement Squad.ard_as_nails_active and Squad.stim_injectors_active use -
    so game/shooting.py's two targeting sites need one call and no new
    dependency, and a third source later needs no third site."""
    limits = [r for r in (lone_operative_range(squad),
                          getattr(squad, "psychic_shield_range", None)) if r is not None]
    return min(limits) if limits else None


def lone_operative_range(squad):
    """Rule 24.24: the unit's Lone Operative range (X", default 12"), or
    None if it doesn't have the ability right now. "Unless part of an
    attached unit" (squad_is_attached_unit()) suspends it entirely - an
    attached Lone Operative loses the benefit for as long as it's attached.
    No explicit "if every model has this ability" qualifier appears in the
    rule text (unlike e.g. INFILTRATORS/DEEP STRIKE), so - like FLY -
    presence on any one model grants it to the whole unit; real datasheets
    with this ability are single-model units anyway, so any()-vs-all() is
    moot in practice."""
    if squad is None or squad_is_attached_unit(squad):
        return None
    values = [m.profile.lone_operative for m in squad.models if m.profile.lone_operative]
    if not values:
        return None
    return max(values)


def _has_hidden_keyword(model):
    """Rule 13.09: INFANTRY/BEASTS/SWARM - notably not MOBILE, unlike the
    Dense-terrain movement exception in rule 13.06."""
    profile = model.profile
    return bool(profile.infantry or profile.beasts or profile.swarm)


def is_hidden(model, terrain_areas, turn_tracker, last_ranged_attack_turn):
    """Rule 13.09: hidden while (a) this model has INFANTRY/BEASTS/SWARM and
    is within a terrain area that contains a Dense feature, and (b) its
    unit made no ranged attacks this turn or the previous one."""
    if not _has_hidden_keyword(model) or model.squad is None or turn_tracker is None:
        return False
    if not any(
        area.has_dense_feature and area.overlaps_model(model)
        for area in terrain_areas
    ):
        return False

    last_turn = last_ranged_attack_turn.get(model.squad)
    if last_turn is None:
        return True
    current_turn = turn_tracker.turn_number_for(model.squad.owner)
    return current_turn - last_turn > 1


def _wall_on_own_footprint(model, terrain_areas):
    """House rule (see CLOSE_DETECTION_RANGE_IN): unlike TerrainArea.has_dense_feature
    (true if ANY feature anywhere in the area is Dense), this checks whether a Dense
    feature specifically overlaps the model's own position - a wall standing directly
    on its footprint, not just a wall somewhere else in the same terrain area."""
    return any(
        feature.category == DENSE and feature.overlaps_circle(model.x_in, model.y_in, model.radius_in)
        for area in terrain_areas
        for feature in area.features
    )


def is_detectable(model, observer_squad, terrain_areas, turn_tracker, last_ranged_attack_turn):
    """Rule 13.09: a hidden model can only be seen by enemy models within its
    detection range (15" by default, or the closer 12" house rule above if a
    wall stands on its own footprint) - a non-hidden model imposes no such
    restriction (ordinary visibility rules apply elsewhere)."""
    if not is_hidden(model, terrain_areas, turn_tracker, last_ranged_attack_turn):
        return True
    detection_range = CLOSE_DETECTION_RANGE_IN if _wall_on_own_footprint(model, terrain_areas) else DETECTION_RANGE_IN
    return any(edge_distance(model, observer) <= detection_range for observer in observer_squad.models)


def active_effects(model, terrain_areas, turn_tracker, last_ranged_attack_turn, greater_good=None,
                   guide=None, doom=None, whispering_web=None):
    """Which status effects currently apply to this model, for the board
    label overlay. battle_shocked, lone_operative and marked are unit-wide;
    hidden is per-model. Every controller argument is optional, like everywhere
    else in this module, so a test can omit the ones it does not care about.

    The three Aeldari marks are asked of the controller rather than read off a
    Squad flag, because that is where they live: all three are held per PLAYER
    (they benefit the whole army, not one unit), so there is nothing on the
    marked squad itself to read. They are also the only effects here that
    belong to the OPPONENT of the model they are drawn on - the label is a
    warning, not a buff."""
    effects = []
    if model.squad is not None and model.squad.battle_shocked:
        effects.append(BATTLE_SHOCKED)
    if is_hidden(model, terrain_areas, turn_tracker, last_ranged_attack_turn):
        effects.append(HIDDEN)
    if lone_operative_range(model.squad) is not None:
        effects.append(LONE_OPERATIVE)
    if greater_good is not None and model.squad is not None and greater_good.is_spotted(model.squad):
        effects.append(MARKED)
    for controller, effect in ((guide, GUIDED), (doom, DOOMED), (whispering_web, WEBBED)):
        if controller is not None and model.squad is not None and _is_marked(controller, model.squad):
            effects.append(effect)
    return effects


def _is_marked(controller, squad):
    """Whether any player has this squad marked. Asked without naming an owner
    because the mark is only ever set on an ENEMY unit, so "someone marked it"
    and "its opponent marked it" are the same question - and the label has to
    show for the marked unit's own controller too, who is exactly the person
    who needs the warning."""
    marked_by = getattr(controller, "marked_by", None)
    if marked_by is None:
        return False
    for player in getattr(controller, "_marks", {}):
        if squad in marked_by(player):
            return True
    return False
