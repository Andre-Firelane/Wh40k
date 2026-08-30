"""The Farseer Skyrunner's "Misfortune" - a datasheet ability.

RULE (printed, word for word):
  "At the end of your Movement phase, select one enemy unit within 18" of and
  visible to this model. Until the start of your next Command phase, each time
  a model in that unit makes an attack, subtract 1 from the Wound roll. Each
  unit can only be selected for this ability once per turn."

THE THIRD PSYCHIC MARK, AND THE FIRST THAT READS FROM THE OTHER SIDE
---------------------------------------------------------------------
Word for word it is the Farseer's Guide and Eldrad's Doom - same trigger, same
18", same visibility, same "until the start of your next Command phase", same
once-per-turn cap. So the whole of game/psychic_mark.py applies unchanged, and
this is a subclass rather than a third copy.

What differs is WHO reads it. Guide and Doom improve a FRIENDLY attack that
TARGETS the marked unit. Misfortune penalises the MARKED UNIT'S OWN attacks:

  Guide/Doom   attacker = any friendly AELDARI unit, target = the marked unit
  Misfortune   attacker = the marked unit, target = anyone

So `PsychicMark.applies_to_squad()` - which asks "is the attacker friendly and
the target marked" - is the wrong question here and is deliberately NOT used.
`afflicts()` asks the right one. Getting this backwards would produce an
ability that fires only when the Farseer's own army shoots the marked unit,
which looks like a working mark and is the opposite of the printed rule; it has
its own test line for that reason.

BOTH ATTACK STEPS, because the text says "makes an attack" and not "makes a
ranged attack" - the same reading Doom gets.

A DEFENDER-INDEPENDENT PENALTY: unlike every other entry in _wound_modifiers(),
which asks something about the TARGET, this one asks only about the attacker.
It therefore sits with Tank Hunters and Darkstrider's Structural Analyser, the
other attacker-side terms in that fold.
"""
from game.psychic_mark import PsychicMark

MISFORTUNE_LABEL = "Misfortune"

#: "subtract 1 from the Wound roll" - a MALUS, so a POSITIVE modifier under
#: game/modifiers.py's convention (positive worsens a threshold).
MISFORTUNE_PENALTY = 1


class MisfortuneController(PsychicMark):
    ability_name = MISFORTUNE_LABEL
    flag = "misfortune"
    effect_text = "subtracts 1 from its own Wound rolls"
    once_per_turn = True        # printed, unlike Doom

    def afflicts(self, attacking_squad):
        """Whether THIS unit is currently marked, i.e. whether its own attacks
        take the -1. Marked by any opponent - a mark is only ever placed on an
        enemy unit, so membership in any player's set is the whole test."""
        if attacking_squad is None:
            return False
        return any(attacking_squad in marked for marked in self._marks.values())


def squad_has_misfortune(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "misfortune", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())
