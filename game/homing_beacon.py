"""T'au wargear item: Homing Beacon, as supplied by the user (not a rule
from the generic 40k core rulebook).

RULE: Once per battle, you can use the Rapid Ingress Stratagem for 0CP.
The target must be set up within 3" of the bearer's unit and more than 9"
away from all enemy units.

Designer's Note: Place a Homing Beacon token next to this unit, removing
it once this ability is used - modeled here as a plain "already used" flag
per bearer squad, never reset (matching how e.g. [ONE SHOT]'s
one_shot_used persists for the whole battle in ShootingController), rather
than an actual removable board token.

The "0CP" half is wired into game/rapid_ingress.py (RapidIngressController.
offer() calls extra_cp=-RAPID_INGRESS_CP_COST through StratagemController,
reusing rule 15.07's own once-per-phase/once-per-target bookkeeping instead
of a second, parallel one). The alternate placement rule (3" of the bearer,
9" from enemies, instead of Ingress's normal 6"-of-board-edge/8"-from-
enemies) is wired into game/ingress.py's IngressController, gated on its
`homing_beacon_bearer` attribute."""

from game.factions.datasheet import Gear

HOMING_BEACON_RANGE_IN = 3.0
HOMING_BEACON_MIN_ENEMY_DISTANCE_IN = 9.0


def _has_homing_beacon(squad):
    return any(m.profile.homing_beacon for m in squad.models)


def _homing_beacon_effect(token):
    token.profile.homing_beacon = True


def homing_beacon_gear(model_line_name):
    """A game/factions/datasheet.py Gear item for the "(0/1)" Homing Beacon
    wargear choice."""
    return Gear(model_line_name, "Homing Beacon", _homing_beacon_effect)


class HomingBeaconController:
    def __init__(self, all_tokens=None, game_log=None):
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self.used = set()  # bearer Squads that have already used their once-per-battle free Ingress

    def available_bearer(self, player):
        """The first still-on-the-battlefield, not-yet-used Homing-Beacon
        unit belonging to `player`, or None. "On the battlefield" (not in
        reserves/embarked/destroyed) the same way game/suppression.py
        checks "while this unit is on the battlefield"."""
        for squad in {t.squad for t in self.all_tokens if t.squad is not None and t.squad.owner == player}:
            if squad in self.used:
                continue
            if _has_homing_beacon(squad):
                return squad
        return None

    def mark_used(self, bearer_squad):
        self.used.add(bearer_squad)
        if self.game_log is not None:
            self.game_log.add(f"{bearer_squad.owner}: {bearer_squad.name}'s Homing Beacon is used (once per battle).")
