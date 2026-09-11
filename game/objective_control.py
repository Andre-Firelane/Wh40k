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
      3. the ADDERS add to the result - four Enhancements and, since stage 8,
         one DATASHEET AURA (the Catacomb Command Barge's Carrier Wave).
    The set-then-worsen order is the printed one and was decided when Hunting
    Hounds arrived; the additions come last so that paying points for a +1
    always buys one, rather than being clamped away by Soulrot's floor or
    overwritten by a setter. See game/enh_strategic_conqueror.py.

    AN ADDER CAN NOW MEET A SETTER, which until Carrier Wave none could: the
    four Enhancements are bought by T'au and Aeldari lists and the setters are
    KROOT, ASURYANI and CANOPTEK, so no model was ever eligible for both.
    Carrier Wave raises any friendly NECRONS unit, and a Canoptek Scarab Swarm
    is one - so a Scarab in a Cryptek's range AND in a Barge's 6" is SET by
    Chittering Swarm and then RAISED by one. That is what step 3 coming last
    is for, and the suite pins the resulting number rather than the intent.

    THE TWO SETTERS CANNOT MEET, and that is measured rather than assumed:
    Hunting Hounds sets 1 on a KROOT model, Craftworld's Champion sets 5 on an
    ASURYANI one, and no model is both. If a third setter ever arrives, the
    order BETWEEN setters becomes a real question that this comment does not
    answer - which is why the test pins the current disjointness rather than
    leaving it to luck.
    """
    from game import (carrier_wave, chittering_swarm, enh_admired_leader,
                      enh_craftworlds_champion, enh_light_of_clarity,
                      enh_strategic_conqueror, enh_strategic_savant)
    oc = hunting_hounds.objective_control(model, all_tokens)
    oc = enh_craftworlds_champion.objective_control(model, oc)
    # Chittering Swarm's SECOND clause - the THIRD setter, and the first that
    # can meet another one: a Scarab is neither KROOT nor ASURYANI, so it is
    # still disjoint from the two above, but that is now a fact about three
    # sets rather than two and the test pins it as such.
    oc = chittering_swarm.objective_control(model, oc, all_tokens)
    oc = plagues.worsen_oc(model, oc)
    # Chittering Swarm's FIRST clause - the SECOND worsener, aimed at the
    # ENEMY of the unit that has the ability. Beside Soulrot rather than after
    # the adders, because both are worseners with the same printed floor, and
    # the adders come last so a purchased +1 always buys one.
    oc = chittering_swarm.worsen_enemy_oc(model, oc, all_tokens)
    oc += enh_strategic_conqueror.oc_bonus(model, objective, all_tokens)
    oc += enh_admired_leader.oc_bonus(model)
    oc += enh_strategic_savant.oc_bonus(model)
    oc += enh_light_of_clarity.oc_bonus(model)
    # The Catacomb Command Barge's Carrier Wave - the first adder that is a
    # DATASHEET AURA rather than an Enhancement, and the first source of any
    # kind that CAN meet a setter: a Canoptek Scarab Swarm is NECRONS, so a
    # Scarab inside a friendly Cryptek's range and inside a Barge's 6" is set
    # by Chittering Swarm and then raised by one. See game/carrier_wave.py.
    oc += carrier_wave.oc_bonus(model, all_tokens)
    return oc
