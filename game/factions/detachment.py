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
    Faction.add_detachment(), not passed in directly.

    `setting` names the game/config.py constant that says WHO is fielding
    this detachment (e.g. "AWAKENED_DYNASTY_PLAYERS"), written by
    game/detachments.py's apply_to_config() from the player's choice. It is
    the one link between this descriptive record and the engine-wired rule,
    and the reason it exists rather than being derived: a detachment is a
    list-building declaration and CANNOT be read off the units - a Necron
    unit looks identical in every detachment.

    None means "this detachment's rule needs no such flag", which is only
    honest while it is the only detachment its faction models (War Horde is
    the remaining case; its rule and stratagems gate on the ORKS keyword and
    there is nothing to distinguish). Retaliation Cadre was in that position
    until the other T'au detachments were added, and both it and
    game/army_lists.py said so in as many words.

    `rule_name` is the printed name of the detachment rule itself ("Bonded
    Heroes", "Patient Hunter"), which is not derivable from `name`.

    `points` is the detachment's printed cost in DETACHMENT POINTS - the "2DP"
    glued onto its heading on Wahapedia. An army may field SEVERAL detachments
    at once and pays for each, so this is a real number and not decoration:
    Kauyon (2) plus Advanced Acquisition Cadre (1) is a legal pair, Mont'ka (3)
    plus Kauyon (2) is not. See game/detachments.py for the budget.

    `tag` is the printed exclusion group ("BATTLESUIT", "AUXILIARIES"): a
    detachment "cannot be taken with another <TAG> detachment". Two detachments
    sharing a tag are mutually exclusive however cheap they are, so this is a
    second, independent restriction on top of the points.

    `force_disposition` is the ONE disposition this detachment permits - a
    game/force_dispositions.py key, transcribed from the same heading `points`
    comes from and mirrored into rules/*/detachments/*.md. It decides which
    PRIMARY MISSION a list taking this detachment may play. A list fielding
    several detachments picks one of the dispositions they grant and writes it
    down (ArmyList.force_disposition); game/detachments.py's validate() is what
    checks the pick against this field.

    Note this is a plain string key rather than an import from
    game/primary_missions.py: this module is pure DATA and the mission engine
    reads it, not the other way round.
    """

    def __init__(self, name, rule_text="", enhancements=(), stratagems=(),
                 setting=None, rule_name="", description="", points=0, tag=None,
                 force_disposition=None):
        self.name = name
        self.faction = None
        self.rule_text = rule_text
        self.rule_name = rule_name
        self.description = description
        self.enhancements = list(enhancements)
        self.stratagems = list(stratagems)
        self.setting = setting
        self.points = points
        self.tag = tag
        self.force_disposition = force_disposition
