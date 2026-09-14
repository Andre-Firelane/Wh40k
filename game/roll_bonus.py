"""What a unit adds to its Advance and Charge rolls - the single place the two
roll sites ask.

Extracted from game/ere_we_go.py, which owned it while that Ork stratagem was
the only source; the Avatar of Khaine's "The Bloody-Handed" was the second. The
2026-09 Ork codex retired 'Ere We Go, so the aura is the one source today. The
module stays: game/movement.py's advance_total() and game/charge.py's
_capped_roll() each ask once and get everything, and a second source later needs
no second site.

SOURCES STACK, unlike the crit-threshold and invulnerable-save sources next door
where the BEST value wins. Two different bonuses to the same roll are separate
modifiers and add up - "not cumulative" is a clause 40k prints explicitly when it
means it (the Grav-inhibitor Drone's own -2 does, and game/charge.py honours that
separately).

`all_tokens` is optional because only the aura needs it: a caller that cannot
see the board gets 0 from it, which is the honest degradation - it can
under-report, never over-report.
"""

from game import bloody_handed


def advance_and_charge_bonus(squad, all_tokens=None):
    """The total this unit currently adds to an Advance or a Charge roll."""
    return bloody_handed.roll_bonus(squad, all_tokens)


def sources(squad, all_tokens=None):
    """(label, amount) per contributing source, for the log/note text a roll
    site prints - so a player can see WHY the roll went up, not just that it
    did."""
    out = []
    aura = bloody_handed.roll_bonus(squad, all_tokens)
    if aura:
        out.append(("The Bloody-Handed", aura))
    return out
