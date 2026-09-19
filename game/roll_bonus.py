"""What a unit adds to its Advance and Charge rolls - the single place the two
roll sites ask.

Extracted from game/ere_we_go.py, which owned it while that Ork stratagem was
the only source; the Avatar of Khaine's "The Bloody-Handed" was the second. The
2026-09 Ork codex retired that 'Ere We Go, so the aura is the one source of
BOTH rolls today. The module stays: game/movement.py's advance_total() and
game/charge.py's _capped_roll() each ask once and get everything, and a second
source later needs no second site.

GREEN TIDE'S 'ERE WE GO (Mecha Orks G3) is a different card under the old name:
"+2 to advance rolls", nothing on a Charge. So it is a term of advance_sources()
only, which the Advance side reads and the Charge side does not.

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


def advance_sources(squad, all_tokens=None):
    """sources() plus every bonus that names the ADVANCE roll alone - Green
    Tide's 'Ere We Go ("+2 to advance rolls", Mecha Orks stage G3). The Charge
    roll keeps reading sources()/advance_and_charge_bonus(), so a bonus here can
    never leak into a charge; game/movement.py's advance_roll_modifiers() is the
    one reader."""
    from game import green_tide_ere_we_go
    out = sources(squad, all_tokens)
    ere_we_go = green_tide_ere_we_go.advance_bonus(squad)
    if ere_we_go:
        out.append((green_tide_ere_we_go.ERE_WE_GO_NAME, ere_we_go))
    return out
