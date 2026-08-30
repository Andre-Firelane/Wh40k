"""Guardian Battlehost's "Defend at All Costs" - the detachment rule.

RULE (printed, word for word):
  "Each time a DIRE AVENGER, GUARDIAN, SUPPORT WEAPON or WAR WALKER model from
  your army makes an attack, if that model's unit and/or the target unit are
  within range of one or more objective markers, add 1 to the Hit roll."

"AND/OR" IS AN OR, and it is the whole shape of the rule. Three of the four
board states pay: the attacker on an objective, the target on one, or both.
Reading it as an AND would make it a rule about two units standing on the same
kind of ground, which is a much narrower and much rarer thing. Each of the four
states is its own test line, because the wrong reading passes any test that
only puts both units in range.

BOTH PHASES. "makes an attack", not "a ranged attack", so it hangs in
_hit_modifiers() in game/shooting.py AND game/fight.py - the same two-site
wiring Command Protocols and Doom need, and the same reason to count the call
sites per file in the test rather than spot-check one.

THE SIGN IS NEGATIVE. game/modifiers.py adjusts the THRESHOLD, so "add 1 to the
Hit roll" is Modifier(-1, ...) - an easier roll. Positive would turn a
detachment bonus into an army-wide penalty, which is the mistake Command
Protocols records having nearly made.

IT MUST BE APPENDED BEFORE THE IGNORE-MODIFIER FILTERS. Both attack steps end
by dropping worsening modifiers for [PSYCHIC] and for units that ignore hit
modifiers; a bonus added after that point is simply lost. Improving modifiers
survive those filters, so the only requirement is to be in the list by then.

THE FOUR KEYWORDS ARE PRINTED SINGULAR AND STORED PLURAL. The datasheet keyword
lines read DIRE AVENGERS, GUARDIANS, WAR WALKERS and SUPPORT WEAPON - the rule
text names a MODEL, the keyword line names the unit type. Measured on the built
roster: 1 + 2 + 1 + 3 datasheets. SUPPORT WEAPON only became answerable when the
three platform profiles started setting the flag, which happened one batch ago;
this is its second reader.

PER MODEL, PER GROUP. "each time a MODEL ... makes an attack" is per model, and
both attack steps ask about a whole group at once. The group form therefore
grants only when EVERY model in the group qualifies - conservative on purpose,
the same argument Driven by Hatred and Fated Hero both write out: the other way
round would hand a Guardian's entitlement to whatever else is swinging with it.
"""

from game import aeldari_detachments, objectives as objectives_module
from game.modifiers import Modifier

DEFEND_AT_ALL_COSTS_LABEL = "Defend at All Costs"

#: "add 1 to the Hit roll" - negative, because modifiers adjust the THRESHOLD.
DEFEND_AT_ALL_COSTS_BONUS = -1

#: The datasheet keyword line spellings of the four the rule names.
DEFEND_AT_ALL_COSTS_KEYWORDS = ("DIRE AVENGERS", "GUARDIANS", "SUPPORT WEAPON",
                                "WAR WALKERS")

#: The config constant game/detachments.py writes for Guardian Battlehost.
SETTING = "GUARDIAN_BATTLEHOST_PLAYERS"


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def _model_qualifies(model, squad):
    """Does THIS MODEL have one of the four keywords?

    THE GRANULARITY IS THE COMPONENT, NOT THE UNIT, and that is the whole
    difficulty. The printed text names a MODEL, but a model does not know which
    datasheet it came from - unit_has_datasheet_keyword()'s own docstring says
    so. Asking the UNIT instead would be wrong in a way that only shows on an
    ATTACHED unit, which is a real board state here: a Farseer leading Guardian
    Defenders is not a GUARDIAN, and a unit-level answer would hand him the
    bonus because his squadmates have the keyword.

    So it is answered per COMPONENT, which is the granularity the keyword line
    actually has and the one rule 19.01's merge preserves. A squad that was
    never merged has exactly one datasheet and the two readings coincide.

    SUPPORT WEAPON is checked first and per MODEL, because it is one of the
    handful of keywords with a real UnitProfile flag."""
    if model is None or model.is_dead():
        return False
    if getattr(model.profile, "support_weapon", False):
        return True
    for component in getattr(squad, "attached_components", None) or ():
        if model in (getattr(component, "starting_models", None) or ()):
            sheet = getattr(component, "datasheet", None)
            return any(keyword in (getattr(sheet, "keywords", None) or ())
                       for keyword in DEFEND_AT_ALL_COSTS_KEYWORDS)
    sheet = getattr(squad, "datasheet", None)
    return any(keyword in (getattr(sheet, "keywords", None) or ())
               for keyword in DEFEND_AT_ALL_COSTS_KEYWORDS)


def applies(attacking_squad, target_squad, objectives=()):
    """The whole printed condition for one attack.

    `objectives` is passed in rather than reached for: both attack steps
    already hold the objective list, and a module that fetched it from a global
    would be untestable at the boundary that matters."""
    if attacking_squad is None or not objectives:
        return False
    if not has_detachment(getattr(attacking_squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(attacking_squad):
        return False
    # "that model's unit AND/OR the target unit" - an OR.
    on_objective = objectives_module.is_within_range_of_objective(
        attacking_squad, objectives)
    if not on_objective and target_squad is not None:
        on_objective = objectives_module.is_within_range_of_objective(
            target_squad, objectives)
    return bool(on_objective)


def applies_to_model(model, attacking_squad, target_squad, objectives=()):
    return (_model_qualifies(model, attacking_squad)
            and applies(attacking_squad, target_squad, objectives))


def applies_to_group(models, attacking_squad, target_squad, objectives=()):
    """The group form the two attack steps need - all(), not any(); see the
    module docstring."""
    models = [m for m in (models or ()) if m is not None]
    if not models:
        return False
    if not applies(attacking_squad, target_squad, objectives):
        return False
    return all(_model_qualifies(m, attacking_squad) for m in models)


def hit_modifiers(models, attacking_squad, target_squad, objectives=()):
    """A list, so a caller can `modifiers.extend(...)` it - the shape
    game/awakened_dynasty.py and game/plagues.py already use."""
    if applies_to_group(models, attacking_squad, target_squad, objectives):
        return [Modifier(DEFEND_AT_ALL_COSTS_BONUS, DEFEND_AT_ALL_COSTS_LABEL)]
    return []
