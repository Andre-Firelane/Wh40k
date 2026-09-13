"""What the Necron detachment rules share - the mirror of game/aeldari_detachments.py
and game/tau_detachments.py.

WHY THIS EXISTS
---------------
Awakened Dynasty was the only Necron detachment, and game/awakened_dynasty.py
held its predicates. The Canoptek Court is the second, and every one of its
rules opens with one of two KEYWORD questions that Awakened Dynasty never asks:
"a CRYPTEK or CANOPTEK unit", and "a CRYPTEK/CANOPTEK MODEL". The Cryptek
Conclave (a later stage) asks the first of them again. So they live here, once,
and the detachment modules import them.

TWO GRANULARITIES, AND THEY ARE NOT INTERCHANGEABLE
---------------------------------------------------
  * UNIT - "a model in a CRYPTEK or CANOPTEK unit" (Power Matrix). Rule 19.03
    pools keywords across an attached unit, so a Technomancer leading Necron
    Warriors makes the whole unit a CRYPTEK unit. Asked through
    attached_units.unit_has_datasheet_keyword().
  * MODEL - "weapons equipped by CRYPTEK or CANOPTEK models" (Cynosure of
    Eradication), "a friendly CANOPTEK model makes an attack" (Curse of the
    Cryptek). Here a Warrior is NOT a CRYPTEK model just because a Technomancer
    stands beside it. Asked through attached_units.model_has_datasheet_keyword(),
    which answers per COMPONENT - a model does not know its own datasheet.

Reading the unit answer where the printed text says model would hand a
Technomancer's [DEVASTATING WOUNDS] to twenty Warriors.

WHAT IS DELIBERATELY NOT HERE: has_detachment() for Awakened Dynasty keeps its
own one-argument form in game/awakened_dynasty.py, which is pinned by its suite.
The generic two-argument form is re-exported from game/detachment_gate.py.
"""

from game.attached_units import model_has_datasheet_keyword, unit_has_datasheet_keyword
from game.awakened_dynasty import is_necrons_unit  # noqa: F401  (re-exported)
from game.detachment_gate import has_detachment  # noqa: F401  (re-exported)

CRYPTEK_KEYWORD = "CRYPTEK"
CANOPTEK_KEYWORD = "CANOPTEK"

CANOPTEK_COURT_SETTING = "CANOPTEK_COURT_PLAYERS"

#: The detachments whose rules ask a PER-MODEL CRYPTEK/CANOPTEK question during
#: an attack, and therefore need it in the attack-grouping key (see attack_key()).
PER_MODEL_KEYWORD_SETTINGS = (CANOPTEK_COURT_SETTING,)


def is_cryptek_unit(squad):
    """"a CRYPTEK unit" - rule 19.03's pooled reading."""
    return squad is not None and unit_has_datasheet_keyword(squad, CRYPTEK_KEYWORD)


def is_canoptek_unit(squad):
    """"a CANOPTEK unit" - rule 19.03's pooled reading."""
    return squad is not None and unit_has_datasheet_keyword(squad, CANOPTEK_KEYWORD)


def model_is_cryptek(squad, model):
    """"a CRYPTEK model" - the model's own component, not its unit."""
    return (squad is not None and model is not None
            and model_has_datasheet_keyword(squad, model, CRYPTEK_KEYWORD))


def model_is_canoptek(squad, model):
    """"a CANOPTEK model" - the model's own component, not its unit."""
    return (squad is not None and model is not None
            and model_has_datasheet_keyword(squad, model, CANOPTEK_KEYWORD))


def attack_key(model):
    """The per-model term game/shooting.py's _attack_key() and game/fight.py's
    _melee_attack_key() fold in, so a rule 04.03 group never mixes a CRYPTEK or
    CANOPTEK model with one that is neither.

    WHY: those groups resolve every attack with the FIRST model's answer (the
    one-representative shortcut this repo has fixed six times). Cynosure of
    Eradication grants [DEVASTATING WOUNDS] to CRYPTEK/CANOPTEK models' weapons
    and Curse of the Cryptek gives CANOPTEK models +1 to Hit and Wound - a mixed
    group would hand whichever answer pairs[0] happened to carry to the rest.

    CHEAP AND INERT FOR EVERYONE ELSE: a player who fields none of the settings
    above gets the constant (False, False), so no group that already existed
    splits - the same guarantee the Nebuloscope term gives.
    """
    squad = getattr(model, "squad", None)
    owner = getattr(squad, "owner", None)
    if squad is None or not any(has_detachment(owner, s) for s in PER_MODEL_KEYWORD_SETTINGS):
        return (False, False)
    return (model_is_cryptek(squad, model), model_is_canoptek(squad, model))
