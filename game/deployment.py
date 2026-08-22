class DeploymentZone:
    """Rule 03.01: the area within which a player sets up their army before
    the battle. Modeled as one or more axis-aligned rectangles (center-based,
    same (x_in, y_in, width_in, height_in) shape as Obstacle) rather than a
    single rectangle, so a zone with a stepped edge (e.g. one half of the
    board deploying slightly deeper than the other) can be built from a
    couple of rectangles instead of needing real polygon support.

    Enforced by game/pregame.py's PregameController during the pre-game
    deployment sequence (a unit must be set up wholly within its owner's
    zone, unless INFILTRATORS 24.20 says otherwise) and by
    game/ingress.py's IngressController for rule 20.04's "not in your
    opponent's deployment zone before battle round 3"."""

    def __init__(self, owner, rects):
        self.owner = owner
        self.rects = list(rects)

    def contains_point(self, x_in, y_in):
        for x, y, w, h in self.rects:
            if x - w / 2 <= x_in <= x + w / 2 and y - h / 2 <= y_in <= y + h / 2:
                return True
        return False

    def contains_circle(self, x_in, y_in, radius_in):
        """Rule 03.01's "wholly within": the model's whole base has to be
        inside the zone, not just its centre.

        Deliberately asks whether ANY SINGLE rectangle contains the whole
        circle, rather than testing against the union: a model straddling the
        seam between two rectangles of a stepped zone is genuinely inside the
        zone, but answering that honestly needs real polygon support. Both
        current maps define one rectangle per zone (see game/maps.py), so the
        distinction cannot arise today - and erring toward "not wholly
        within" only ever refuses a placement, never allows an illegal one."""
        for x, y, w, h in self.rects:
            if (
                x - w / 2 <= x_in - radius_in
                and x_in + radius_in <= x + w / 2
                and y - h / 2 <= y_in - radius_in
                and y_in + radius_in <= y + h / 2
            ):
                return True
        return False

    def distance_to_point(self, x_in, y_in):
        """0 if the point is inside the zone, otherwise the shortest distance
        to its nearest edge - what rule 24.20 (INFILTRATORS) measures when it
        says "more than 8" horizontally from your opponent's deployment
        zone"."""
        best = None
        for x, y, w, h in self.rects:
            dx = max(x - w / 2 - x_in, 0.0, x_in - (x + w / 2))
            dy = max(y - h / 2 - y_in, 0.0, y_in - (y + h / 2))
            dist = (dx * dx + dy * dy) ** 0.5
            if best is None or dist < best:
                best = dist
        return 0.0 if best is None else best


def zone_for(zones, owner):
    """That player's own deployment zone, or None if the map defines none."""
    for zone in zones or ():
        if zone.owner == owner:
            return zone
    return None


def enemy_zones(zones, owner):
    """Every deployment zone that is NOT this player's. A list rather than a
    single zone because nothing guarantees a two-player board here, and rule
    24.20 says "your opponent's deployment zone" - all of them have to be
    cleared, not just the first one found."""
    return [zone for zone in zones or () if zone.owner != owner]
