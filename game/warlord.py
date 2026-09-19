"""The army's WARLORD (Mecha Orks stage G2) - who it is, and which lists may name
whom.

Until this stage the engine had no Warlord at all, and every printed rule that
names one was a documented no-op: the Orks' Da Boss, Supreme Commander (Commander
Shadowsun, The Silent King, and now Ghazghkull Thraka), the C'tan Shards'
"cannot be your WARLORD", Hypercrypt Legion's Reanimation Crypts. The Mecha Orks
list prints a Kriegsherr, and Ghazghkull's Supreme Commander and Da Boss need
one, so a list can now name its Warlord.

WHERE IT LIVES. A list entry (a unit or one of its leaders) may carry
`"warlord": true` (game/army_io.py). The roster builder writes it onto the built
model - Token.warlord - while the character is still its own squad, before
attach() makes it one model among many (game/army_roster.py, pass 2). Nothing
saves it: a load rebuilds the army from its list.

WHAT A LIST MAY SAY (validate_roster(), run at load like every other check):
  * at most one Warlord;
  * a Warlord is a CHARACTER model - the entry must have one, and only its
    CHARACTER models carry the flag (The Silent King's Menhirs do not);
  * a model that "cannot be your WARLORD" (the C'tan Shards' Enslaved Star God)
    may not be named;
  * "SUPREME COMMANDER: If this model is in your army, it must be your WARLORD" -
    a list that fields one and names ANOTHER Warlord is refused; a list that names
    none gets the Supreme Commander as its Warlord (the rule leaves no choice);
    two Supreme Commanders cannot both be it.
A list that names no Warlord and fields no Supreme Commander simply has none -
every list shipped before this stage - and every Warlord rule stays dormant for
it, which is what they were.
"""


def _profiles(datasheet, composition_index=0):
    compositions = datasheet.compositions()
    lines = compositions[composition_index] if 0 <= composition_index < len(compositions) else compositions[0]
    return [line.profile_cls for line in lines]


def is_character_entry(spec):
    """A Warlord is a CHARACTER model. ANY model of the entry, because The Silent
    King is one unit of a CHARACTER (Szarekh) and two Triarchal Menhirs."""
    return any(getattr(p, "character", False) for p in _profiles(spec.datasheet, spec.composition_index))


def may_not_be_warlord(spec):
    """The C'tan Shards' Enslaved Star God: "This model cannot be your WARLORD"."""
    return any(getattr(p, "enslaved_star_god", False) for p in _profiles(spec.datasheet, spec.composition_index))


def is_supreme_commander(spec):
    return any(getattr(p, "supreme_commander", False) for p in _profiles(spec.datasheet, spec.composition_index))


def _entries(roster):
    """Every (spec, where) in the roster: each unit and each of its leaders."""
    for index, unit in enumerate(roster):
        yield unit, "roster[%d]" % index
        for i, leader in enumerate(getattr(unit, "leaders", ()) or ()):
            yield leader, "roster[%d].leaders[%d]" % (index, i)


def validate_roster(roster, problems):
    """Check the Warlord rules against a parsed roster, appending to `problems`,
    and settle an implicit Supreme Commander. Returns the warlord spec or None."""
    named = [(spec, where) for spec, where in _entries(roster) if getattr(spec, "warlord", False)]
    supreme = [(spec, where) for spec, where in _entries(roster) if is_supreme_commander(spec)]
    if len(named) > 1:
        problems.append("more than one warlord: %s" % ", ".join(where for _s, where in named))
    for spec, where in named:
        if not is_character_entry(spec):
            problems.append("%s: %s cannot be the warlord - a WARLORD is a CHARACTER" % (where, spec.datasheet.name))
        if may_not_be_warlord(spec):
            problems.append("%s: %s cannot be your WARLORD (Enslaved Star God)" % (where, spec.datasheet.name))
    if len(supreme) > 1:
        problems.append("two Supreme Commanders (%s): each must be the warlord"
                        % ", ".join(where for _s, where in supreme))
    elif supreme:
        spec, where = supreme[0]
        if named and named[0][0] is not spec:
            problems.append("%s: %s is a Supreme Commander and must be your WARLORD, not %s (%s)"
                            % (where, spec.datasheet.name, named[0][0].datasheet.name, named[0][1]))
        elif not named:
            spec.warlord = True
            named = [(spec, where)]
    return named[0][0] if len(named) == 1 else None


def warlord_model(squads, player):
    """`player`'s Warlord model among `squads`, alive or not - or None."""
    for squad in squads or ():
        if getattr(squad, "owner", None) != player:
            continue
        for model in getattr(squad, "models", ()) or ():
            if getattr(model, "warlord", False):
                return model
    return None


def living_warlord(squads, player):
    model = warlord_model(squads, player)
    return model if model is not None and not model.is_dead() else None
