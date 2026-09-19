"""A model's Save CHARACTERISTIC - the one place that answers it.

Two rules REPLACE the printed value rather than modifying a roll:

  * the Tomb Blades' Shieldvanes - "the bearer has a 3+ Save characteristic"
    (game/tomb_blade_wargear.py), per bearer;
  * Green Tide's 'Ardboyz - "BOYZ unit only. This unit has 4+ Sv."
    (game/enh_ardboyz.py), per unit.

WHY THIS EXISTS. The Save characteristic had SIX readers - the save roll and
its dice-panel heading (game/damage_resolution.py), the allocation order
(game/squad.py), every AI damage estimate (game/damage_estimate.py's
defender_soak()), the AI's observation of a unit, the AI's weapon-matchup hint
and the hover datacard - and Shieldvanes, the first override, reached exactly
one of them: a Tomb Blade rolled its 3+ and the datacard, the AI and the
allocation order all read 4+. Extracted at the second override (Mecha Orks G3,
error class 10), and test_event_chain_wiring.py section 30 now names every
remaining `.armor_save` read so a seventh reader cannot go around it.

An override replaces the printed string; a MODIFIER to the characteristic
(Rattlejoint Ague's -1, Autoreactive Camouflage's +1) is not a replacement and
stays where it is, in damage_resolution.save_thresholds() - applied on top of
whatever this returns, which is the order the printed words give ("has a 3+
Save characteristic" is the characteristic those modifiers then change).

Two overrides on one model cannot happen today (Shieldvanes is Tomb Blades
wargear, 'Ardboyz a BOYZ Enhancement); if a third source ever makes it
possible, the order below is a decision to take then, not an accident to
inherit.
"""


def override(model):
    """The replacement Save characteristic for `model`, or None when no rule
    replaces the printed one."""
    if model is None:
        return None
    from game import enh_ardboyz, tomb_blade_wargear
    for source in (tomb_blade_wargear.save_override, enh_ardboyz.save_override):
        value = source(model)
        if value is not None:
            return value
    return None


def armour_save(model):
    """The Save characteristic `model` has right now, as the printed string
    ("4+", "-")."""
    value = override(model)
    if value is not None:
        return value
    return model.profile.armor_save
