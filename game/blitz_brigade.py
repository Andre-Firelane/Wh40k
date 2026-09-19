"""Orks detachment rule: Blitz Brigade's Unstoppable Momentum (2026-09 codex,
Mecha Orks stage G4).

PRINTED (rules/orks/detachments/Blitz Brigade.md):

    Unstoppable Momentum
    - Friendly WAGON units can re-roll charge rolls.
    - When a friendly WAGON unit is selected to make an advance move, that
      unit can change advance rolls to a 6.

WAGON is a DATASHEET keyword (Kill Rig, Battlewagon, Gunwagon print it), read
through attached_units.unit_has_datasheet_keyword() - no UnitProfile flag.

THE CHARGE RE-ROLL is the THIRD carrier of game/charge_reroll.py (after Relentless
Combatants and Phaeron of the Blades): the one-instant offer before
acknowledge(), the once-per-roll claim, the all-or-nothing re-roll and the AI's
deterministic two-sided answer are the base class's; this module owns the label
and the predicate.

THE ADVANCE ROLL. "Can change advance rolls to a 6" - a die that may always be
turned into its own maximum IS a 6, so no die is thrown: game/movement.py's
start_run() takes its no-roll branch (the one Whirling Death and Aggressive
Mobility use), but unlike those flat bonuses this one is a ROLL of 6, so the
Advance modifiers still apply on top (advance_total(squad, [6]) - Mont'ka's
`shaken` -2 lands on it). Throwing a die only to overwrite it would open three
offers that buy nothing - the Waaagh! Advance re-roll, Command Re-roll, any
other re-roll - which is error class 5. "Can" is not asked: 6 is the best a D6
can show, so the choice has one answer.

READIED BRAWLERS IS NOT WIRED - user decision (2026-09-19): "den 'assault
disembark move' gibt es in meinem Regelbuch nicht. Keine Bewegungsart erfinden,
die Lücke benennen und im Test pinnen." NOT_WIRED below is that name, and
test_ork_blitz_brigade.py pins that nothing offers it.

The two Enhancements are game/enh_targetin_gizmos.py and game/enh_boss_boomer.py;
the two wired Stratagems are game/blitz_keep_it_runnin.py and
game/blitz_impending_krunch.py.
"""

from game import attached_units
from game.charge_reroll import ChargeRerollController
from game.detachment_gate import has_detachment

#: The config constant game/detachments.py writes for this detachment.
SETTING = "BLITZ_BRIGADE_PLAYERS"
UNSTOPPABLE_MOMENTUM = "Unstoppable Momentum"
#: "change advance rolls to a 6".
UNSTOPPABLE_MOMENTUM_ADVANCE = 6

#: Printed, deliberately NOT wired - see the module docstring.
NOT_WIRED = {
    "Readied Brawlers": ("its EFFECT is an 'assault disembark move', a move type the user's "
                         "rulebook does not have (user decision, 2026-09-19) - not invented"),
}


def fields_blitz_brigade(player):
    return has_detachment(player, SETTING)


def is_wagon_unit(squad):
    """"WAGON unit" - the datasheet keyword, pooled over 19.01 components."""
    return squad is not None and attached_units.unit_has_datasheet_keyword(squad, "WAGON")


def applies(squad):
    """Unstoppable Momentum: a friendly WAGON unit of a player fielding Blitz
    Brigade."""
    return (squad is not None and fields_blitz_brigade(getattr(squad, "owner", None))
            and is_wagon_unit(squad))


def advance_roll_is_fixed(squad):
    """game/movement.py's start_run() asks this: the Advance roll is a 6, no die."""
    return applies(squad)


class UnstoppableMomentumChargeRerollController(ChargeRerollController):
    """"Friendly WAGON units can re-roll charge rolls." - the third carrier of
    game/charge_reroll.py."""

    LABEL = UNSTOPPABLE_MOMENTUM

    def applies(self, squad):
        return applies(squad)
