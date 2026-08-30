"""Kroot Lone-Spear's "Advanced Scouting".

RULE (printed, word for word):
  "Each time this model makes a ranged attack that hits an enemy unit, until
   the end of the turn, each time another KROOT model from your army makes an
   attack that targets that enemy unit, you can re-roll the Hit roll."

A MARK ON THE TARGET, WHICH THIS ENGINE ALREADY DOES THREE TIMES OVER - the
Farseer's Guide, Eldrad's Doom and the Whispering Web all put a mark on an
ENEMY unit that the marking player's own attacks then read (game/
status_effects.py calls them the only effects that belong to the OPPONENT of
the model they sit on). So the state here is one more of those, kept on the
controller rather than on the marked squad for the same reason
SecondaryMissionController keeps card state off the cards: a Squad outlives a
turn, and a mark that outlives its own duration is the bug this shape avoids.

THREE THINGS THAT ARE EASY TO GET WRONG, each its own test line:

  * "THAT HITS" - the mark is placed by a HIT, not by the attack being made.
    A volley that misses entirely marks nothing, which means the hook is the
    hit step's result and not the target-selection step.
  * "ANOTHER KROOT MODEL" - another. The Lone-Spear does not re-roll his own
    subsequent attacks against the unit he marked, so the attacking unit is
    checked for a KROOT model that is not the marker itself.
  * "UNTIL THE END OF THE TURN" - a turn, not a phase and not a battle round,
    so the mark is cleared on the same seam every other end-of-turn state is.

"AN ATTACK", not "a ranged attack", on the READING half - so a Kroot melee
attack against the marked unit re-rolls too, unlike Precise Targeting next
door whose Spotted mark cannot survive into the Fight phase. Both steps
therefore consult this module.
"""

ADVANCED_SCOUTING_LABEL = "Advanced Scouting"


def unit_has_advanced_scouting(squad):
    """Read live off the living models, so it ends with the Lone-Spear."""
    if squad is None:
        return False
    return any(getattr(m.profile, "advanced_scouting", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def is_kroot(squad):
    """The KROOT keyword, read off the unit's living models."""
    if squad is None:
        return False
    return any(getattr(m.profile, "kroot", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


class AdvancedScoutingController:
    """One mark ledger per battle. Owned by main.py, cleared at end of turn."""

    def __init__(self, game_log=None):
        self.game_log = game_log
        self._marked = {}   # id(target squad) -> (owner, marking squad)

    def reset_turn(self):
        """"Until the end of the turn" - the same seam every other end-of-turn
        state in main.py is cleared on."""
        self._marked = {}

    def record_hit(self, attacking_squad, target_squad):
        """Called when an attack HIT - not when it was merely made.

        Silently does nothing unless the attacker actually has the ability,
        so the hit step can call it unconditionally."""
        if target_squad is None or not unit_has_advanced_scouting(attacking_squad):
            return False
        if id(target_squad) in self._marked:
            return False
        self._marked[id(target_squad)] = (attacking_squad.owner, attacking_squad)
        if self.game_log:
            self.game_log.add(
                f"[advanced scouting] {target_squad.name} is marked for the rest of "
                f"the turn - other KROOT units re-roll Hit rolls against it",
                file_only=True)
        return True

    def is_marked(self, target_squad):
        return id(target_squad) in self._marked

    def applies(self, attacking_squad, target_squad):
        """Whether THIS attacking unit may re-roll its Hit roll.

        Three conditions, all printed: the target is marked, the attacker is a
        friendly KROOT unit, and it is not the marker itself ("another KROOT
        model")."""
        if attacking_squad is None or target_squad is None:
            return False
        entry = self._marked.get(id(target_squad))
        if entry is None:
            return False
        owner, marker = entry
        if attacking_squad.owner != owner or attacking_squad is marker:
            return False
        return is_kroot(attacking_squad)
