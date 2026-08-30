"""What a model's Objective Control characteristic is RIGHT NOW.

THE SIXTEENTH EXTRACTION, and made at the second consumer exactly as this
project's standing rule says. The answer used to live in game/plagues.py as
`effective_oc()`, which was correct while the Death Guard's Scabrous Soulrot
was the only thing that could change an OC - but a function named after one
faction's disease is a lying name the moment a second source appears, and the
Kroot Hounds' Hunting Hounds is that second source. Same treatment
`ere_we_go.py`, `melee_crit.py` and `_reduced_damage()` got.

TWO SOURCES, AND THEY PULL IN OPPOSITE DIRECTIONS:

  * Hunting Hounds SETS the characteristic to 1 ("the Objective Control
    characteristic of models in this unit IS 1"), which on a printed 0 is the
    only thing that lets a Kroot Hound hold anything at all.
  * Scabrous Soulrot WORSENS it by 1, to a minimum of 1, and explicitly must
    not raise a printed 0 - see game/plagues.py's own note on why the floor is
    a floor on worsening rather than a value to clamp up to.

ORDER MATTERS AND IS THE PRINTED ONE: the set happens first, the worsening
second. A hound inside a friendly Kroot character's 12" and also Afflicted
therefore ends on 1, not 0 - Soulrot's own minimum protects it, which is what
the two rules say when read in that order. The reverse order would give 0 and
silently delete Hunting Hounds against one particular opponent.

`all_tokens` IS OPTIONAL because Hunting Hounds is the only source that needs
to look at the board, and every caller that has no token list in hand keeps
meaning exactly what it did - the same arrangement _wound_modifiers()'s
`strength` parameter uses.
"""

from game import hunting_hounds, plagues


def effective_oc(model, all_tokens=None, objective=None):
    """This model's Objective Control, after every source that can change it.

    Returns a NUMBER, so callers keep treating OC as a number.

    `objective` is the objective marker this question is being asked ABOUT,
    and is optional for the same reason `all_tokens` is: only one source needs
    it, and every caller without one keeps meaning exactly what it did. Two
    sources use it:

      * Mont'ka's Strategic Conqueror Enhancement, whose +1 applies only "within
        range of THAT objective marker";
      * Auxiliary Cadre's Admired Leader Enhancement, which is objective-blind
        and therefore does NOT use it - listed here only so the next reader
        does not assume every Enhancement below needs one.

    ORDER, and all three orderings are deliberate:
      1. the SETTERS replace the characteristic - Hunting Hounds (to 1) and
         Guardian Battlehost's Craftworld's Champion (to 5),
      2. Scabrous Soulrot WORSENS it by 1, to a minimum of 1,
      3. the ADDERS add to the result - four Enhancements now.
    The set-then-worsen order is the printed one and was decided when Hunting
    Hounds arrived; the additions come last so that paying points for a +1
    always buys one, rather than being clamped away by Soulrot's floor or
    overwritten by a setter. See game/enh_strategic_conqueror.py.

    THE TWO SETTERS CANNOT MEET, and that is measured rather than assumed:
    Hunting Hounds sets 1 on a KROOT model, Craftworld's Champion sets 5 on an
    ASURYANI one, and no model is both. If a third setter ever arrives, the
    order BETWEEN setters becomes a real question that this comment does not
    answer - which is why the test pins the current disjointness rather than
    leaving it to luck.
    """
    from game import (enh_admired_leader, enh_craftworlds_champion,
                      enh_light_of_clarity, enh_strategic_conqueror,
                      enh_strategic_savant)
    oc = hunting_hounds.objective_control(model, all_tokens)
    oc = enh_craftworlds_champion.objective_control(model, oc)
    oc = plagues.worsen_oc(model, oc)
    oc += enh_strategic_conqueror.oc_bonus(model, objective, all_tokens)
    oc += enh_admired_leader.oc_bonus(model)
    oc += enh_strategic_savant.oc_bonus(model)
    oc += enh_light_of_clarity.oc_bonus(model)
    return oc
