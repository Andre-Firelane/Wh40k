"""Dice-notation characteristics - a weapon's Attacks/Damage (or an
ability's "X" value, e.g. Deadly Demise DX) printed as "D3", "D6", "D6+1"
etc. rather than a fixed number.

User report: a live weapon (Ghostkeel Battlesuit's Twin Fusion Blaster,
printed Damage "D6") and both T'au vehicles' "Deadly Demise D3" were being
resolved with the earlier "store the die's max value as a fixed int, never
actually roll it" placeholder convention documented all over game/weapons.py/
game/units.py - correct as far as it went (nothing was hidden; there
genuinely was no roll to show), but not what a real "D6"/"D3" characteristic
is supposed to do, and exactly the kind of silent, un-rerollable computation
the user wants every dice-backed value in this game to avoid. This module
replaces that placeholder for the characteristics that are actually wired
into live play (see WeaponProfile.damage_notation, UnitProfile.
deadly_demise_notation) with a real, visible, Command-Reroll-eligible
dice_manager step - the plain "attacks"/"damage"/"deadly_demise" ints stay
as they are (still read for grouping/preview purposes, e.g.
shooting.py's _attack_key) wherever nothing has been converted yet (every
still-inert "Unselected Profiles" weapon, plus dice-notation Attacks in
general - see this module's own docstring note in CLAUDE.md for why that
one's deliberately not wired into the live Hit-roll pipeline yet)."""

import random
from collections import namedtuple

DiceNotation = namedtuple("DiceNotation", ["sides", "bonus"])


def D3(bonus=0):
    return DiceNotation(3, bonus)


def D6(bonus=0):
    return DiceNotation(6, bonus)


def describe(notation):
    text = f"D{notation.sides}"
    if notation.bonus:
        text += f"+{notation.bonus}"
    return text


class DiceNotationRoll:
    """Rolls `count` dice of `notation` (e.g. one D6 per model with a
    dice-notation Attacks characteristic, or a single D6/D3 for a
    dice-notation Damage/ability-X characteristic) as one real, visible
    dice_manager step - mirrors game/feel_no_pain.py's FeelNoPainRoll shape
    exactly (is_pending/done/on_dice_acknowledged()), just summing to a
    `total` instead of counting successes against a threshold (there's no
    pass/fail here, so no success_threshold is passed to dice_manager.roll()
    - DicePanel already renders an un-thresholded roll in plain, uncolored
    dice, same as an Advance/Charge roll).

    Without a dice_manager (the non-interactive resolve_damage()/
    resolve_mortal_wounds() test wrappers in game/damage_resolution.py),
    resolves immediately via a plain random roll - same convenience-wrapper
    convention those already use for Feel No Pain."""

    def __init__(self, notation, count, dice_manager, label, roll_kind=None, log=None, is_reroll=False):
        """`is_reroll` marks this as itself the re-roll of an earlier
        dice-notation roll (Crisis Sunforge Battlesuits' Sunforge ability
        re-rolling a Damage roll) - forwarded to DiceManager.roll() so its
        already_rerolled ledger records that these dice have now used up
        their one re-roll, which is what stops the same die being thrown a
        third time by anything else."""
        self.notation = notation
        self.count = count
        self.dice_manager = dice_manager
        self.log = log
        self.is_pending = False
        self.total = None
        if dice_manager is not None:
            self.is_pending = True
            dice_manager.roll(count=count, sides=notation.sides, label=label, roll_kind=roll_kind, is_reroll=is_reroll)
        else:
            rolls = [random.randint(1, notation.sides) for _ in range(count)]
            self.total = sum(rolls) + notation.bonus * count

    @property
    def done(self):
        return not self.is_pending

    def on_dice_acknowledged(self):
        if not self.is_pending:
            return
        rolls = self.dice_manager.last_values
        self.total = sum(rolls) + self.notation.bonus * self.count
        if self.log is not None:
            bonus_text = f" + {self.notation.bonus * self.count}" if self.notation.bonus else ""
            self.log(f"{self.dice_manager.label}: rolled {rolls}{bonus_text} = {self.total}.")
        self.is_pending = False
