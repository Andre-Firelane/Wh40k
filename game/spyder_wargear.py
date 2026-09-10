"""Canoptek Spyders' two wargear auras (Necrons).

RULES (printed, word for word):

  FABRICATOR CLAW ARRAY (Aura): "While a friendly NECRONS VEHICLE unit is
    within 6" of the bearer, that unit has the Feel No Pain 6+ ability."

  GLOOM PRISM (Aura): "While a friendly NECRONS unit is within 6" of the
    bearer, models in that unit have the Feel No Pain 5+ ability against
    mortal wounds and Psychic Attacks."

THE GLOOM PRISM IS NEKROSOR AMMENTAR'S NULLSTONE FIELD GENERATOR, WORD FOR
WORD - same range, same threshold, same two wound kinds, same faction test.
That is what game/fnp_aura.py was extracted for, and both are instances of it
rather than two implementations that happen to agree.

THE FABRICATOR CLAW ARRAY IS THE THIRD INSTANCE and the one that shows the
knobs are real: a different threshold (6+), a narrower set of covered units
(NECRONS **VEHICLE**), and - the one that would be easy to lose - NO WOUND
QUALIFIER AT ALL. It applies to every wound, where the other two apply only to
mortal wounds and Psychic Attacks. Folding the three into one "Necron FNP aura"
would silently widen the Gloom Prism or silently narrow this one.

A SPYDER CAN CARRY BOTH, and then a friendly Necron VEHICLE inside 6" has 6+
against ordinary wounds and 5+ against mortal ones - the fold takes the better
of the two per wound, which is what rule 05.04 says about two sources of one
characteristic. Measured rather than argued: the fold is
fnp_aura.best_threshold(), and it compares thresholds rather than trusting an
order.

THEY ARE WARGEAR, so they are Gear items on the datasheet rather than printed
abilities - "any number of models can each be equipped with 1 gloom prism".
Each sets its own profile flag, so a Spyder unit of two with one prism between
them projects one aura, which is what the printed option means.
"""

from game.fnp_aura import FeelNoPainAura

FABRICATOR_CLAW_ARRAY_LABEL = "Fabricator Claw Array"
GLOOM_PRISM_LABEL = "Gloom Prism"

FABRICATOR_CLAW_RANGE_IN = 6.0
FABRICATOR_CLAW_FEEL_NO_PAIN = "6+"
GLOOM_PRISM_RANGE_IN = 6.0
GLOOM_PRISM_FEEL_NO_PAIN = "5+"


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def is_necron_unit(squad):
    """"a friendly NECRONS unit". The army rule is printed on every Necron
    datasheet, so its flag IS the faction test - the same reading
    game/illuminor.py and game/nekrosor_ammentar.py use for the identical
    phrase."""
    return bool(squad) and any(
        getattr(m.profile, "reanimation_protocols", False) for m in _living(squad))


def is_necron_vehicle_unit(squad):
    """"a friendly NECRONS VEHICLE unit" - both keywords, and VEHICLE is asked
    with any() under rule 19.03's pooling, which is what "unit" means here."""
    return is_necron_unit(squad) and any(
        getattr(m.profile, "vehicle", False) for m in _living(squad))


FABRICATOR_CLAW_AURA = FeelNoPainAura(
    flag="fabricator_claw_array",
    threshold=FABRICATOR_CLAW_FEEL_NO_PAIN,
    range_in=FABRICATOR_CLAW_RANGE_IN,
    squad_flag="fabricator_claw_aura",
    label=FABRICATOR_CLAW_ARRAY_LABEL,
    unit_predicate=is_necron_vehicle_unit,
    # NO wound qualifier - this one covers every wound, unlike its two
    # siblings. The single most losable difference between the three.
    mortal_or_psychic_only=False,
)

GLOOM_PRISM_AURA = FeelNoPainAura(
    flag="gloom_prism",
    threshold=GLOOM_PRISM_FEEL_NO_PAIN,
    range_in=GLOOM_PRISM_RANGE_IN,
    squad_flag="gloom_prism_aura",
    label=GLOOM_PRISM_LABEL,
    unit_predicate=is_necron_unit,
    mortal_or_psychic_only=True,
)

#: Both, for main.py's per-frame aura block and for feel_no_pain.py's fold.
SPYDER_AURAS = (FABRICATOR_CLAW_AURA, GLOOM_PRISM_AURA)


def refresh(all_tokens=()):
    """Stamp both auras, once per frame - beside Nurgle's Gift and the
    Nullstone field, and for the two reasons that block records: positions
    change every frame, and a wiped-out bearer must stop projecting in the
    same frame it dies."""
    for aura in SPYDER_AURAS:
        aura.refresh(all_tokens)


def feel_no_pain(model, mortal=False, psychic=False):
    """The better of the two thresholds this model is standing in, or "-"."""
    from game.fnp_aura import best_threshold
    return best_threshold(SPYDER_AURAS, model, mortal=mortal, psychic=psychic)


def equip_fabricator_claw_array(token):
    token.profile.fabricator_claw_array = True


def equip_gloom_prism(token):
    token.profile.gloom_prism = True
