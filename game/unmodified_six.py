"""Changing one die of a roll to an unmodified 6 - the arithmetic and the
"is it worth offering" gate, shared by every ability that grants it.

Extracted from game/aspect_shrine.py, which owned it while the ASPECT WARRIORS
token was the only source. The Farseer's Branching Fates is the second, and it
differs only in its RESOURCE (once per phase while leading, rather than a
per-battle token) and in which models are excluded - not in what changing a die
does or in when doing so buys anything. Fifth extraction of this shape, after
game/invulnerable_save.py, game/crit_hit.py, game/damage_reroll.py and
game/damage_estimate.py, and for the same two reasons each time: a second
foreign consumer, and one call site to update.

WHICH DIE IS CHANGED is not a question. Within one roll every die is identical
- same weapon, same target - so the best one is always determined:

  * a FAILURE, if there is one: it becomes a hit/wound AND a critical, which is
    strictly the largest possible gain;
  * otherwise a non-critical SUCCESS, which gains only the critical.

WHEN IT IS WORTH OFFERING is a CERTAINTY check rather than an estimate: there
must be a failure to convert, OR a non-critical success in a step where a
critical actually does something. A critical hit is worth nothing over an
ordinary one unless the weapon has [SUSTAINED HITS] or [LETHAL HITS]; a
critical wound likewise unless it has [DEVASTATING WOUNDS]. Without this an
ability like these would offer itself on essentially every roll, which is the
interruption this project has pushed back on before.
"""

# "An unmodified 6" - and rule 05.01 makes an unmodified 6 always a success,
# while rule 05.02 makes it a critical under any threshold at or below 6 (so
# also under Mandiblasters' or Unbridled Carnage's lowered 5+).
UNMODIFIED_SIX = 6


def crit_matters_on_hit(weapon):
    """A critical HIT differs from an ordinary one only through these two.

    [SUSTAINED HITS] is asked of BOTH fields: when its value is itself a die
    (sustained_hits_notation, the Avatar of Khaine's "d3") the plain
    sustained_hits is only a preview placeholder, and a weapon that set the
    notation alone would otherwise look as if a critical hit bought nothing."""
    return (bool(getattr(weapon, "sustained_hits", 0))
            or getattr(weapon, "sustained_hits_notation", None) is not None
            or bool(getattr(weapon, "lethal_hits", False)))


def crit_matters_on_wound(weapon):
    """...and a critical WOUND only through this one."""
    return bool(getattr(weapon, "devastating_wounds", False))


def gain(failures, successes, crits, crit_matters):
    """Is there a die worth changing? Returns "failure", "success" or None."""
    if failures > 0:
        return "failure"
    if successes - crits > 0 and crit_matters:
        return "success"
    return None


def hit_change(weapon, hits, crits, misses):
    """What changing one die of this HIT roll would buy, or None.

    Returns (new_hits, new_crits, what) so the caller can say what happened."""
    what = gain(misses, hits, crits, crit_matters_on_hit(weapon))
    if what is None:
        return None
    if what == "failure":
        return hits + 1, crits + 1, what
    return hits, crits + 1, what


def wound_change(weapon, wounds, crits, no_effect):
    """The same for a WOUND roll: (new_wounds, new_crits, new_no_effect, what)."""
    what = gain(no_effect, wounds, crits, crit_matters_on_wound(weapon))
    if what is None:
        return None
    if what == "failure":
        return wounds + 1, crits + 1, no_effect - 1, what
    return wounds, crits + 1, no_effect, what


def describes(what, step):
    """The half-sentence a prompt uses to say what the change buys."""
    if what == "failure":
        return "a miss becomes a critical hit" if step == "hit" else "a failed wound becomes a critical wound"
    return ("an ordinary hit becomes a critical hit" if step == "hit"
            else "an ordinary wound becomes a critical wound")
