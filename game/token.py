import itertools
from dataclasses import dataclass, field

_id_counter = itertools.count()


@dataclass(eq=False)  # identity semantics: two tokens are only equal if they're the same object
class Token:
    x_in: float
    y_in: float
    radius_in: float
    color: tuple
    id: int = field(default_factory=lambda: next(_id_counter))
    profile: object = None
    squad: object = None
    weapons: list = field(default_factory=list)
    current_wounds: int = None
    # Names of the non-weapon Gear items this model was built with (drones and
    # the like - see game/drones.py). A Gear item is applied as a callback that
    # mutates the token, so its identity is otherwise gone the moment it runs:
    # a Shield Drone shows up only as +1 Wound, a Guardian Drone only as a
    # flag, a Marker Drone can be a complete no-op. Recorded by build_squad()
    # purely so a unit's loadout can be DESCRIBED (game/loadout.py); no rule
    # reads this.
    gear_names: list = field(default_factory=list)
    # Flash Gitz' "Ammo Runt" wargear item. Unlike the drone effects
    # above this one IS read by a rule (game/ammo_runt.py), so it needs a
    # real field rather than just a gear_names entry.
    ammo_runt: bool = False
    # Painboy's "Grot Orderly" wargear item - same shape as ammo_runt above
    # (a real rule reads it: game/grot_orderly.py).
    grot_orderly: bool = False

    def __post_init__(self):
        if self.current_wounds is None and self.profile is not None:
            self.current_wounds = self.profile.wounds

    def contains_point(self, x_in, y_in):
        dx = self.x_in - x_in
        dy = self.y_in - y_in
        return (dx * dx + dy * dy) ** 0.5 <= self.radius_in

    def apply_damage(self, amount):
        if self.current_wounds is None:
            return
        self.current_wounds = max(0, self.current_wounds - amount)

    def is_dead(self):
        return self.current_wounds is not None and self.current_wounds <= 0
