"""One printed sentence, three carriers: "if the Strength characteristic of
that attack is greater than [the target's] Toughness characteristic, subtract
1 from the Wound roll".

THE 48TH EXTRACTION, and OVERDUE rather than early - it should have been made
at the second carrier, and game/guardian_protocols.py's own docstring says so
in as many words:

    "Writing a second S>T comparison would be exactly the 'two places, same
     question, two answers' drift this repo keeps consolidating away, so the
     shared arithmetic stays shared and only the condition differs."

It was not. Only the HOOK was shared; wave_serpent_shield.py:53 and
guardian_protocols.py:66 each carried their own
`toughness is not None and strength > toughness`. A comment that promises a
behaviour no code delivers is the class this repo keeps finding (the
scouts/resolve_scouts() precedent), and the Catacomb Command Barge's Advanced
Quantum Shielding is the third carrier that makes it worth paying off.

THE THREE PRINTED LINES, word for word:

  WAVE SERPENT SHIELD - Wave Serpent:
    "Each time a RANGED attack targets this model, if the Strength
     characteristic of that attack is greater than the Toughness
     characteristic of this model, subtract 1 from the Wound roll."

  GUARDIAN PROTOCOLS - Lychguard:
    "WHILE A NOBLE MODEL IS LEADING THIS UNIT, each time an attack targets
     this unit, if the Strength characteristic of that attack is greater than
     this unit's Toughness characteristic, subtract 1 from the Wound roll."

  ADVANCED QUANTUM SHIELDING - Catacomb Command Barge (stage 8):
    "Each time an attack targets this model, if the Strength characteristic of
     that attack is greater than this model's Toughness characteristic,
     subtract 1 from the Wound roll."

WHAT IS SHARED: the S > T comparison itself; the Toughness SOURCE
(attached_unit_toughness(), rule 19.02, so the comparison reads the same value
the wound threshold it modifies does); the SIGN (positive - game/modifiers.py's
convention is that a modifier adjusts the THRESHOLD, and "subtract 1 from the
Wound roll" makes the roll harder); and the 19.03 per-model read of the flag,
so a merged unit has the ability if any component brought it.

WHAT A CARRIER OWNS - four class attributes and one method, as CLASS
ATTRIBUTES rather than constructor arguments, so a subclass that forgets one
fails loudly at definition instead of quietly protecting nothing. That is the
discipline game/cover_denial.py, game/reactive_bodyguard_shooting.py and
game/fnp_aura.py already use:

    flag        the UnitProfile attribute that marks a model as carrying it
    label       what the dice panel and the log call it
    penalty     the threshold adjustment (1 for all three, and printed)
    ranged_only whether the printed text says "a RANGED attack"
    extra_condition(squad)  the carrier's own extra clause, default "none"

ONE READER PER PHASE, NOT THREE `if`s. shooting.py and fight.py each call
wound_modifiers() once with the same SHIELDS tuple, so the two can never end up
disagreeing about what "S > T" means - the arrangement game/cover_denial.py
made for _compute_benefit_of_cover(). A fourth carrier is one more name in that
tuple and shows up as a one-line diff.

THE MELEE FILTER IS THE RANGED CLAUSE, not a second list. fight.py passes
melee=True, which drops every `ranged_only` carrier; today that is exactly the
Wave Serpent Shield, which is why the shield has always been shooting-only.
"""

from game.attached_units import leader_ability
from game.modifiers import Modifier
from game.squad import attached_unit_toughness


class StrengthOverToughnessShield:
    """One carrier of the S > T wound penalty. See the module docstring."""

    flag = None          # required
    label = None         # required
    penalty = 1          # every printed line says "subtract 1"
    ranged_only = False  # True only where the text says "a RANGED attack"

    def __init__(self):
        if not self.flag or not self.label:
            raise TypeError(
                "%s must set both `flag` and `label` - see "
                "game/strength_over_toughness.py" % type(self).__name__)

    def unit_has(self, squad):
        """Rule 19.03: a merged unit carries it if ANY living model does.

        Read off the MODELS rather than off the squad's datasheet, which is
        what makes the 19.03 pooling fall out for free - both existing
        carriers already did this and it is the half that was genuinely
        shared."""
        if squad is None:
            return False
        return any(getattr(m.profile, self.flag, False)
                   for m in squad.models if not m.is_dead())

    def extra_condition(self, squad):
        """The carrier's own extra clause. Default: there is none.

        Two of the three print nothing here. Guardian Protocols prints "while
        a NOBLE model is LEADING this unit", which is rule 24.22's real
        attached unit and not merely a squad containing an Overlord."""
        return True

    def applies(self, target_squad, strength):
        """Whether this carrier modifies THIS attack's Wound roll.

        `strength` is the attack's Strength as the wound step computes it -
        the ALREADY-ADJUSTED value, not the printed one, so a weapon pushed
        past the target's Toughness by something else is caught too. Both
        original carriers said so and both meant it."""
        if strength is None or not self.unit_has(target_squad):
            return False
        if not self.extra_condition(target_squad):
            return False
        toughness = attached_unit_toughness(target_squad)
        return toughness is not None and strength > toughness


class _WaveSerpentShield(StrengthOverToughnessShield):
    flag = "wave_serpent_shield"
    label = "Wave Serpent Shield"
    ranged_only = True   # "each time a RANGED attack targets this model"


class _GuardianProtocols(StrengthOverToughnessShield):
    flag = "guardian_protocols"
    label = "Guardian Protocols"

    def extra_condition(self, squad):
        """"While a NOBLE model is leading this unit" - rule 24.22's real
        attached unit (19.01), which is leader_ability()'s exact job. Using it
        also brings 19.04's grace window along, so a Noble killed mid-sequence
        does not silently drop the protection for the rest of the attacking
        unit's attacks."""
        return leader_ability(squad, "noble")


class _AdvancedQuantumShielding(StrengthOverToughnessShield):
    """The Catacomb Command Barge's. Guardian Protocols' shape with NO gate at
    all - it protects the model unconditionally, in both phases.

    Like the Wave Serpent's, its Toughness can never actually come from a
    merge (a VEHICLE is not joinable), and like the Wave Serpent's it reads
    attached_unit_toughness() anyway, because reading the same source as the
    roll it modifies is what keeps the two from ever disagreeing."""
    flag = "advanced_quantum_shielding"
    label = "Advanced Quantum Shielding"


WAVE_SERPENT_SHIELD = _WaveSerpentShield()
GUARDIAN_PROTOCOLS = _GuardianProtocols()
ADVANCED_QUANTUM_SHIELDING = _AdvancedQuantumShielding()

# The whole set, in the order they were built. Both phases read THIS, so a
# fourth carrier reaches shooting.py and fight.py together or not at all.
SHIELDS = (WAVE_SERPENT_SHIELD, GUARDIAN_PROTOCOLS, ADVANCED_QUANTUM_SHIELDING)


def wound_modifiers(target_squad, strength, shields=SHIELDS, melee=False):
    """Every S > T penalty that applies to this attack, as Modifiers.

    `melee=True` drops the `ranged_only` carriers - see the module docstring.
    Returns a list so the caller can `.extend()` it, the shape
    way_of_the_short_blade.wound_modifiers() already uses."""
    out = []
    for shield in shields:
        if melee and shield.ranged_only:
            continue
        if shield.applies(target_squad, strength):
            out.append(Modifier(shield.penalty, shield.label))
    return out
