"""Rule 19.01's THIRD attachment form: a whole non-character UNIT joins a
bodyguard unit at Declare Battle Formations.

THE 44th EXTRACTION, at the SECOND carrier. The Cryptothralls printed it first
and it lived in their module; the Canoptek Tomb Crawlers print the same
paragraph, so the rule moved out from under one datasheet's name.

  CRYPTEK RETINUE (Cryptothralls)
    "At the start of the Declare Battle Formations step, this unit can join one
     other unit from your army that is being led by a CRYPTEK INFANTRY model
     (a unit cannot have more than one CRYPTOTHRALLS unit joined to it). If it
     does, until the end of the battle, every model in this unit counts as
     being part of that Bodyguard unit, and that Bodyguard unit's Starting
     Strength is increased accordingly."

  CANOPTEK RETINUE (Canoptek Tomb Crawlers)
    the same paragraph, with "a CRYPTEK model" where the first says "a CRYPTEK
    INFANTRY model", and one extra parenthesis: "...and cannot have both a
    TOMB CRAWLERS and a CRYPTOTHRALLS unit joined to it".

ALMOST ALL OF IT WAS ALREADY BUILT, and that has not changed:

  * attached_units.attach() merges models, sums points AND sums
    starting_model_count from the components - which IS the printed "Starting
    Strength is increased accordingly", and it matters far beyond bookkeeping:
    that number is what 01.02.03 caps Reanimation Protocols at and what Below
    Half-strength reads.
  * pregame.py's JOIN destination and its resolution loop are generic.
  * 19.01's one-unit-per-ROLE check gives BOTH parentheses for free. The
    first ("not more than one CRYPTOTHRALLS unit") was already why RETINUE is
    its own role rather than a second kind of SUPPORT; the second ("not both a
    TOMB CRAWLERS and a CRYPTOTHRALLS unit") falls out of the SAME check,
    because both datasheets are in that one role. Measured in the suite rather
    than asserted here - a printed clause that costs no code is exactly the
    kind that quietly stops being true.

WHAT DIFFERS IS ONE QUALIFIER, and it is a MEASURED no-op today: every Cryptek
in this faction is INFANTRY, so "a CRYPTEK model" and "a CRYPTEK INFANTRY
model" pick out the same hosts. It is still written as two different predicates,
because the day a non-INFANTRY Cryptek is printed they stop agreeing and the
Tomb Crawlers are the ones that should widen.

THE HOST CONDITION IS KEPT OUT OF can_attach() on purpose: that function owns
rule 19.01 and has no business knowing what a Cryptek is. This is a condition
of the Declare Battle Formations STEP, the same split game/formations.py's
support_join_errors() already draws for Support Artillery.
"""

from game.attached_units import (RETINUE, attachment_role, can_attach,
                                 leader_components)

CRYPTEK_KEYWORD = "CRYPTEK"
INFANTRY_KEYWORD = "INFANTRY"


def host_is_led_by_cryptek(host, require_infantry=True):
    """"one other unit from your army that is being LED BY a CRYPTEK [INFANTRY]
    model".

    LED BY, so a component in the LEADER role - a Cryptek that merely stands
    nearby is not one, and neither is a SUPPORT component... except that every
    Cryptek in this faction prints CORE: Support, so the printed phrase and
    this engine's role would never agree if it were read strictly. It is
    therefore asked of any ATTACHED CHARACTER component that carries the
    CRYPTEK keyword, which is what "being led by" means at the table.

    `require_infantry` is the one word the two carriers differ in."""
    if host is None:
        return False
    for component in leader_components(host) or ():
        sheet = getattr(component, "datasheet", None)
        if sheet is None:
            continue
        keywords = getattr(sheet, "keywords", None) or ()
        if CRYPTEK_KEYWORD not in keywords:
            continue
        if require_infantry and INFANTRY_KEYWORD not in keywords:
            continue
        return True
    return False


def join_errors(retinue, host, already_joined=(), require_infantry=True,
                unit_label="retinue"):
    """Why `retinue` cannot join `host` at Declare Battle Formations. Empty
    list = allowed.

    The PAIRING is delegated to can_attach() rather than re-derived - that is
    where rule 19.01 lives, and its one-per-role check is what enforces both of
    the printed parentheses."""
    if retinue is None or host is None:
        return ["No unit selected."]
    if attachment_role(retinue) != RETINUE:
        return ["%s is not a %s unit." % (getattr(retinue, "name", "?"), unit_label)]
    if retinue is host:
        return ["A unit cannot join itself."]
    if getattr(retinue, "owner", None) != getattr(host, "owner", None):
        return ["%s is not from your army." % getattr(host, "name", "?")]
    errors = list(can_attach(retinue, host))
    # 19.01's one-per-ROLE check gives this once the join has HAPPENED; while
    # declarations are still being collected nothing has attached yet, so the
    # already-declared list is what makes it checkable - the same argument
    # game/formations.py's support_join_errors() makes for its own limit.
    if already_joined and retinue not in already_joined:
        errors.append("%s already has a retinue unit joined to it." % host.name)
    if not host_is_led_by_cryptek(host, require_infantry=require_infantry):
        errors.append(
            "%s is not being led by a CRYPTEK%s model."
            % (host.name, " INFANTRY" if require_infantry else ""))
    return errors


def eligible_hosts(retinue, army, joins=None, require_infantry=True,
                   unit_label="retinue"):
    """Every unit in `army` this retinue could legally join.

    `joins` maps id(host) -> the units already declared into it."""
    joins = joins or {}
    return [unit for unit in (army or ())
            if not join_errors(retinue, unit, joins.get(id(unit), ()),
                               require_infantry=require_infantry,
                               unit_label=unit_label)]


# TWO CARRIERS, TWO PRINTED NAMES AND TWO QUALIFIERS. The panel heading has to
# say WHICH rule is being offered - "Cryptek Retinue" over a Tomb Crawlers
# offer would name the wrong one, the same reason game/formations.py already
# separates Support Artillery from the retinue. Keyed on the DATASHEET keyword
# rather than a second profile flag: both carriers set `cryptek_retinue`
# because attachment_role() reads it, and that shared flag is exactly what
# gives them the printed "cannot have both" for free.
_CARRIERS = (
    # (datasheet keyword, printed rule name, does the host need INFANTRY?)
    ("TOMB CRAWLERS", "Canoptek Retinue", False),
    ("CRYPTOTHRALLS", "Cryptek Retinue", True),
)


def carrier_of(squad):
    """(printed rule name, require_infantry) for this retinue, or None."""
    from game.attached_units import unit_has_datasheet_keyword
    if squad is None or attachment_role(squad) != RETINUE:
        return None
    for keyword, label, require_infantry in _CARRIERS:
        if unit_has_datasheet_keyword(squad, keyword):
            return label, require_infantry
    # A third carrier that nobody taught this table still gets the STRICTER
    # reading rather than the looser one, which is the safe direction.
    return "Retinue", True
