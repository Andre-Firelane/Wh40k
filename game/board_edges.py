"""Distance to the battlefield edges - the one place that measures it.

Written inside game/secondary_missions.py for Outflank ("within 6" of one or
more battlefield edges") and moved here when Da Big Hunt's Instinctive Hunters
became its second reader (Mecha Orks G5): a detachment Stratagem asking the
MISSION DECK for board geometry would be a lying import path (error class 11).
secondary_missions re-exports both names, so none of its call sites move.

BASE EDGE TO BOARD EDGE, not centre: a model's own radius counts, which is what
"within X of a battlefield edge" means for a model that is itself several
inches wide.

UNIT-LEVEL IS PERMISSIVE: any model close enough puts the unit at that edge -
the reading "units ... are within X of Y" takes everywhere here. The strict
"wholly within" form says so and is a different function elsewhere.
"""

from game import config

EDGE_NORTH = "north"
EDGE_SOUTH = "south"
EDGE_WEST = "west"
EDGE_EAST = "east"
EDGES = (EDGE_NORTH, EDGE_SOUTH, EDGE_WEST, EDGE_EAST)

#: The distance the rules that read this print today - Outflank's "within 6"",
#: Instinctive Hunters' "within 6" of a battlefield edge".
DEFAULT_EDGE_RANGE_IN = 6.0


def model_distance_to_edges(model):
    """Base-EDGE distance from a model to each of the four board edges."""
    width, height = config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN
    r = model.radius_in
    return {
        EDGE_NORTH: max(0.0, model.y_in - r),
        EDGE_SOUTH: max(0.0, height - model.y_in - r),
        EDGE_WEST: max(0.0, model.x_in - r),
        EDGE_EAST: max(0.0, width - model.x_in - r),
    }


def unit_edges_within(squad, range_in=None):
    """Which board edges this unit is within `range_in` of (default 6")."""
    if range_in is None:
        range_in = DEFAULT_EDGE_RANGE_IN
    edges = set()
    for model in (getattr(squad, "models", ()) or ()):
        if model.is_dead():
            continue
        for edge, distance in model_distance_to_edges(model).items():
            if distance <= range_in:
                edges.add(edge)
    return edges


def unit_is_within_of_edge(squad, range_in=None):
    """"within X of a battlefield edge" as a yes/no."""
    return bool(unit_edges_within(squad, range_in))
