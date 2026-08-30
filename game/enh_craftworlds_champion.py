"""Guardian Battlehost Enhancement: Craftworld's Champion (25 pts).

RULE (verbatim, rules/aeldari/detachments/Guardian Battlehost.md):
  "ASURYANI model only. The bearer has an Objective Control characteristic
  of 5."

A SET, NOT AN ADD, and that is the whole of the engineering. "HAS an Objective
Control characteristic of 5" replaces the number; "add 1 to the Objective
Control characteristic" (Strategic Savant, Light of Clarity, and the two T'au
Enhancements) moves it. game/objective_control.py's effective_oc() layers those
two kinds deliberately - set, then worsen, then add - so this belongs in layer
one beside Hunting Hounds and nowhere else. Put in the add layer it would read
+5.

SECOND SET SOURCE, AND THE TWO CANNOT MEET. Hunting Hounds sets 1 on a KROOT
model; this sets 5 on an ASURYANI one, and no model is both. That is MEASURED
rather than assumed, and pinned - if a third setter ever arrives the order
between setters becomes a real question, and this is the line that will say so.

THE BEARER ONLY, not its unit: "the BEARER has", where Strategic Savant next
door says "models in that unit". One word, and it is the difference between 25
points buying one model's OC and buying a whole squad's. Read per MODEL, which
is what effective_oc() already takes.

IT SURVIVES SOULROT'S FLOOR because it is applied first and Soulrot only
worsens by 1 to a minimum of 1 - so an afflicted bearer sits at 4, not at 1.
Measured in the test rather than reasoned about, since the two layers are one
line apart.
"""

from game import enhancements

CRAFTWORLDS_CHAMPION = "Craftworld's Champion"

#: "an Objective Control characteristic of 5".
CRAFTWORLDS_CHAMPION_OC = 5


def is_active(model):
    """Per MODEL - the printed text says "the bearer", not "the bearer's
    unit"."""
    if model is None:
        return False
    return enhancements.model_is_active(model, CRAFTWORLDS_CHAMPION)


def objective_control(model, printed):
    """The SET. Returns `printed` unchanged when the Enhancement does not
    apply, so the caller can fold it without a branch - the same contract
    game/hunting_hounds.py's objective_control() has."""
    return CRAFTWORLDS_CHAMPION_OC if is_active(model) else printed
