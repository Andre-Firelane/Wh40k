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

# `dice` is how many dice ONE instance of the characteristic rolls - 1 for
# every printed "D3"/"D6"/"D6+2", and 2 for Dark Reapers' Tempest Launcher,
# whose Attacks characteristic is printed "2D6". It was added when that weapon
# arrived rather than approximating it as D6+3: the two have the same mean and
# a different spread, and quietly restating a printed characteristic is exactly
# what this module exists to stop.
DiceNotation = namedtuple("DiceNotation", ["sides", "bonus", "dice"])
DiceNotation.__new__.__defaults__ = (1,)   # `dice` defaults to 1


def D3(bonus=0, dice=1):
    return DiceNotation(3, bonus, dice)


def D6(bonus=0, dice=1):
    return DiceNotation(6, bonus, dice)


def describe(notation):
    text = f"D{notation.sides}"
    if notation.dice > 1:
        text = f"{notation.dice}{text}"
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

    def __init__(self, notation, count, dice_manager, label, roll_kind=None, log=None, is_reroll=False,
                 target_name=None, attacker_squad=None, target_squad=None):
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
            # attacker_squad/target_squad carry no rule meaning at all -
            # they only let DicePanel show the two units' art alongside the
            # roll, so an Attacks/Damage step in the middle of an attack
            # sequence keeps saying who is shooting at whom instead of
            # dropping that line for one roll and bringing it back for the
            # next. Either may be left out (a Deadly Demise X roll has no
            # attacker in this sense).
            dice_manager.roll(
                count=count * notation.dice, sides=notation.sides, label=label, roll_kind=roll_kind,
                is_reroll=is_reroll, target_name=target_name,
                attacker_squad=attacker_squad, target_squad=target_squad,
            )
        else:
            rolls = [random.randint(1, notation.sides) for _ in range(count * notation.dice)]
            self.total = sum(rolls) + notation.bonus * count

    @property
    def done(self):
        return not self.is_pending

    @property
    def projected_total(self):
        """What total() would come out as if the dice on the table were
        acknowledged right now, or None when nothing is pending.

        Same formula as on_dice_acknowledged() below, and deliberately the
        only other place it exists: game/unmodified_six_controller.py needs
        the amount BEFORE the roll is acknowledged (that is when its button is
        offered), and a second copy of "sum plus bonus times count" is exactly
        the drift this repo keeps consolidating away."""
        if not self.is_pending or self.dice_manager is None:
            return None
        values = self.dice_manager.pending_values
        if not values:
            return None
        return sum(values) + self.notation.bonus * self.count

    def face_for_total(self, wanted):
        """The single die face that would make this roll come to `wanted`, or
        None if this roll is not one die or no face could.

        Not simply `wanted`: a Damage characteristic can print a bonus (nine
        weapons in this repo do - D6+1, D6+2), and game/branching_fates.py
        commits to reading "change the result of one Damage roll to an
        unmodified 6" as the RESULT becoming 6. So on a D6+2 the die has to
        become a 4. Setting it to 6 instead would mean 8, which is a different
        reading of the rule.

        Deliberately refuses a multi-die roll rather than guessing how to
        spread a target across several dice. Measured: every dice-notation
        Damage characteristic in this repo throws exactly one die, so this
        never declines in practice - but a future 2D6 would, loudly, instead
        of silently doing something arbitrary."""
        if self.count * self.notation.dice != 1:
            return None
        face = wanted - self.notation.bonus * self.count
        return face if 1 <= face else None

    def on_dice_acknowledged(self):
        if not self.is_pending:
            return
        rolls = self.dice_manager.last_values
        self.total = sum(rolls) + self.notation.bonus * self.count
        if self.log is not None:
            bonus_text = f" + {self.notation.bonus * self.count}" if self.notation.bonus else ""
            self.log(f"{self.dice_manager.label}: rolled {rolls}{bonus_text} = {self.total}.")
        self.is_pending = False
