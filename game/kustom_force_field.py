"""The Big Mek in Mega Armour's Kustom Force Field (2026-09 Ork codex, Mecha Orks
stage G2).

RULE (verbatim, rules/orks/Big Mek In Mega Armour.md):
  "Kustom Force Field: This unit has 4+ InSv against ranged attacks."

WARGEAR, bought as "one of the following: 1 Tellyport Blasta / 1 Kustom Force
Field" - a Gear item that marks the bearer's token (Token.kustom_force_field).
The "one of" is not enforced: a WargearOption cannot exclude a Gear item, the
same named limitation as the Tankbustas' Busta Rokkit Launcha and Pulsa Rokkit.

"THIS UNIT" is the attached unit while the Big Mek leads it - rule 19.04, read
through attached_units.unit_has_ability(), so the Meganobz are covered while he
lives and lose it when he dies. It is a UNIT save, not the model field
`invulnerable_save_vs_ranged` (which is per model): the one door that answers
"what is this model's invulnerable save" - invulnerable_save.
effective_invulnerable_save() - asks here for the melee=False case.
"""

from game import attached_units

KUSTOM_FORCE_FIELD_NAME = "Kustom Force Field"
#: "4+ InSv against ranged attacks".
KUSTOM_FORCE_FIELD_SAVE = "4+"


def shields(squad):
    """Whether `squad` (a unit, attached or not) is under a Kustom Force Field."""
    if squad is None or not getattr(squad, "models", None):
        return False
    return attached_units.unit_has_ability(squad, lambda m: getattr(m, "kustom_force_field", False))


def ranged_invulnerable_save(model):
    """The save this model gains against a RANGED attack, or None."""
    squad = getattr(model, "squad", None)
    return KUSTOM_FORCE_FIELD_SAVE if shields(squad) else None
