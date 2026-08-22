"""What a unit adds to its Advance and Charge rolls - the single place the two
roll sites ask.

Extracted from game/ere_we_go.py, which owned it while that Ork stratagem was
the only source. The Avatar of Khaine's "The Bloody-Handed" is the second, and a
module named after one faction's stratagem is the wrong home for another
faction's datasheet aura. Seventh extraction of this shape, after
game/invulnerable_save.py, game/crit_hit.py, game/damage_reroll.py,
game/damage_estimate.py, game/unmodified_six.py and game/psychic_mark.py, and
for the same two reasons each time: a second foreign consumer, and one call site
per reader to update.

BOTH SOURCES MODIFY BOTH ROLLS, which is what makes one helper right: 'Ere We Go
prints "add 2 to Advance and Charge rolls", The Bloody-Handed "add 1 to Advance
and Charge rolls". So game/movement.py's advance_total() and game/charge.py's
_capped_roll() each ask once and get everything.

THEY STACK, unlike the crit-threshold and invulnerable-save sources next door
where the BEST value wins. Two different bonuses to the same roll are separate
modifiers and add up - nothing in either printed text says otherwise, and
"not cumulative" is a clause 40k prints explicitly when it means it (the
Grav-inhibitor Drone's own -2 does, and game/charge.py honours that separately).

`all_tokens` is optional because only the aura needs it: a caller that cannot
see the board still gets the flag-based bonus, which is the honest degradation -
it can under-report, never over-report.
"""

from game import bloody_handed
from game.ere_we_go import ERE_WE_GO_ROLL_BONUS


def _ere_we_go(squad):
    """War Horde's 'Ere We Go: read straight off the unit flag, so the two roll
    sites need no dependency on the controller - same arrangement as
    Squad.stim_injectors_active and Squad.ard_as_nails_active."""
    if squad is not None and getattr(squad, "ere_we_go_active", False):
        return ERE_WE_GO_ROLL_BONUS
    return 0


def advance_and_charge_bonus(squad, all_tokens=None):
    """The total this unit currently adds to an Advance or a Charge roll."""
    return _ere_we_go(squad) + bloody_handed.roll_bonus(squad, all_tokens)


def sources(squad, all_tokens=None):
    """(label, amount) per contributing source, for the log/note text a roll
    site prints - so a player can see WHY the roll went up, not just that it
    did."""
    out = []
    ere = _ere_we_go(squad)
    if ere:
        out.append(("'Ere We Go", ere))
    aura = bloody_handed.roll_bonus(squad, all_tokens)
    if aura:
        out.append(("The Bloody-Handed", aura))
    return out
