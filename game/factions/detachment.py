"""Detachment scaffold: a faction's detachment rule, its enhancements, and
its detachment stratagems - stored as data, independent of any battle.

Detachment stratagems reuse game.stratagems.Stratagem directly rather than
inventing a parallel shape - Core Stratagems (rule 15.01-15.12, already
implemented: Command Re-roll, Explosives, Epic Challenge, Insane Bravery,
Crushing Impact, Rapid Ingress, Fire Overwatch, Heroic Intervention,
Counteroffensive) and detachment-specific ones share the exact same WHEN/
TARGET/EFFECT/CP shape by rule; only WHICH stratagems a player has access to
differs (Core ones are always available, a detachment's own only while that
detachment is chosen) - which one applies is a StratagemController-usage
concern for whoever assembles a player's stratagem list, not something
Detachment itself needs to model."""


class Enhancement:
    """A detachment's Enhancement: a named, points-costed upgrade a single
    (usually CHARACTER) model can be given during army building. Stored
    descriptively, like Datasheet.abilities_text - this engine has no
    generic ability-application system, so actually GRANTING one is done
    the same way every other datasheet-level ability already is: setting
    the matching field directly on that specific model's UnitProfile/
    WeaponProfile instance after build_squad() creates it (e.g. an
    Enhancement that grants [LETHAL HITS] would set
    model.weapons[i].lethal_hits = True on the chosen model, exactly like
    Epic Challenge already does at runtime for its own temporary grant) -
    there's deliberately no "apply(model)" method here pretending to do
    that generically, since what field(s) to set is specific to each
    Enhancement's actual effect."""

    def __init__(self, name, points, description="", restricted_to=None):
        self.name = name
        self.points = points
        self.description = description
        self.restricted_to = restricted_to  # optional keyword string, e.g. "CHARACTER" or a specific datasheet name


class Detachment:
    """A faction's detachment: its detachment rule (descriptive text - see
    Enhancement's note on why nothing here "applies" it automatically),
    its enhancements, and its detachment stratagems. `faction` is set by
    Faction.add_detachment(), not passed in directly."""

    def __init__(self, name, rule_text="", enhancements=(), stratagems=()):
        self.name = name
        self.faction = None
        self.rule_text = rule_text
        self.enhancements = list(enhancements)
        self.stratagems = list(stratagems)
