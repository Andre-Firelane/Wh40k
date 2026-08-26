from game import crewed_platform
from game.objectives import Objective
from game.terrain import TerrainArea


class GameState:
    def __init__(self):
        self.tokens = []
        self.obstacles = []
        self.terrain_areas = []
        self.objectives = []
        self.reserves = []  # Squads not yet set up on the battlefield (rule 03.02) - their models aren't in self.tokens
        self.embarked_squads = []  # Squads embarked within a TRANSPORT (rule 18.02) - their models aren't in self.tokens either
        self.deployment_zones = []
        self.blood_decals = []  # (x_in, y_in) left behind wherever a model died - purely cosmetic, see Renderer.draw_blood_decals. No size stored: every stain is the same one (sprites.BLOOD_DECAL_DIAMETER_IN)

    def add_token(self, token):
        self.tokens.append(token)

    def add_reserve_squad(self, squad):
        """Rule 03.02: a unit that starts off the battlefield (e.g. in
        strategic reserves) - its models stay out of self.tokens (so they
        don't show up on the board or interact with any on-board rules)
        until SetupController actually sets the unit up."""
        self.reserves.append(squad)

    def add_obstacle(self, obstacle):
        self.obstacles.append(obstacle)

    def add_deployment_zone(self, zone):
        self.deployment_zones.append(zone)
        return zone

    def add_terrain_area(self, features):
        """Rule 13.01/13.02: register a whole terrain area (one or more
        terrain features, e.g. a ruin's floor + walls from terrain.ruin(),
        or a single standalone Obstacle) - the features are still flattened
        into self.obstacles too, since movement/LoS blocking is checked per
        feature, not per area. Returns the TerrainArea, e.g. to hand to
        add_objective()."""
        area = TerrainArea(features)
        self.terrain_areas.append(area)
        self.obstacles.extend(features)
        return area

    def add_blood_decal(self, x_in, y_in):
        """Purely cosmetic (no rule attached) - a stain left at a model's
        last position once it dies, drawn by Renderer.draw_blood_decals.
        Kept here rather than discarded along with the dead token itself
        (see remove_dead_models) since the decal must outlive it.

        Position only: every stain is the same size
        (sprites.BLOOD_DECAL_DIAMETER_IN), so there is nothing per-decal to
        record. It used to take the dead model's base radius and scale to
        it - see that constant for why that stopped."""
        self.blood_decals.append((x_in, y_in))

    def add_objective(self, terrain_area, name="Objective"):
        """Rule 14.01: a terrain objective - the terrain area IS the
        objective (its location "should coincide with a terrain area")."""
        objective = Objective(terrain_area, name=name)
        self.objectives.append(objective)
        return objective

    def all_squads(self):
        """Every unit in the game, wherever it currently is - on the board,
        in Strategic Reserves (03.02/20.04) or embarked in a TRANSPORT
        (18.02). Deduped by identity and in a stable order (board first, in
        token order), so a caller listing units gets the same order twice.

        Exists for the UI: an overlay that wants to show a unit's own art
        next to its name has to resolve that name to a Squad, and the two
        off-board lists are exactly the ones a naive scan of self.tokens
        would miss - a Rapid Ingress offer or a disembark prompt names a
        unit that is, by definition, not on the board yet."""
        squads, seen = [], set()
        for token in self.tokens:
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen.add(id(squad))
                squads.append(squad)
        for squad in list(self.reserves) + list(self.embarked_squads):
            if id(squad) not in seen:
                seen.add(id(squad))
                squads.append(squad)
        return squads

    def find_token(self, token_id):
        for token in self.tokens:
            if token.id == token_id:
                return token
        return None

    def remove_dead_models(self):
        """Removes and returns any tokens whose wounds have reached 0.

        Loops rather than sweeping once, because a death can CAUSE a death:
        Guardian Defenders' "Crewed Platform" destroys a unit's weapon
        platforms the moment its last crew model dies (game/crewed_platform.py).
        Marking those and going round again means they are removed on the same
        frame and counted exactly like any other casualty - blood splats, the
        "No Mercy" secondary, Squad.destroyed_models - instead of standing alone
        for a frame and taking a second path out. Terminates because every pass
        removes at least one token from a finite list."""
        dead = []
        while True:
            batch = [token for token in self.tokens if token.is_dead()]
            if not batch:
                return dead
            self._remove_tokens(batch)
            dead.extend(batch)
            crewed_platform.mark_orphaned_platforms(
                {token.squad for token in batch if token.squad is not None}
            )

    def _remove_tokens(self, dead):
        for token in dead:
            self.tokens.remove(token)
            if token.squad is not None and token in token.squad.models:
                token.squad.models.remove(token)
                # Keep the Token, so an ability that returns destroyed models
                # to a unit has something to return - Painboy's Grot Orderly
                # is the first (see game/grot_orderly.py). Nothing else reads
                # this list, and holding the reference costs nothing: rule
                # 19.02/19.04 already rely on a dead Token outliving its
                # removal from Squad.models (game/attached_units.py's
                # AttachedComponent.starting_models).
                if token not in token.squad.destroyed_models:
                    token.squad.destroyed_models.append(token)
