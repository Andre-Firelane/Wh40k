"""The Orks' psychic roll (2026-09 Ork codex, stage E3e).

PRINTED (rules/orks/Kill Rig.md), the same frame on both of its psychic
abilities:

    "... if this unit is not battle-shocked, you can make a psychic roll for
     this unit by rolling one D6. If you do:
     - On a 1, this unit is battle-shocked.
     - <the ability's effect>"

READ AS (user decision in the plan): the effect happens on EVERY roll, and a 1
additionally battle-shocks the unit. So a caller applies its grant the moment it
uses the ability, and this module owns only what the D6 decides - the shock.

THREE GATES, all of them the unit's, asked through why_not():
  * "if this unit is not battle-shocked";
  * Unstable Energies (game/unstable_energies.py, the Orks army rule): the psychic
    levels used this battle round may not exceed the unit's psyker level. A roll
    SPENDS the level - the ability was used, whatever the die shows;
  * a free DiceManager. It holds exactly one pending roll, and a second roll()
    replaces the first without a trace, so an ability is not usable while
    another roll is on the table.

THE ROLL IS VISIBLE and its outcome is read on acknowledgement
(on_dice_acknowledged(), routed from main.py like every other controller's), so
the shock lands after the player has seen the die. If another roll REPLACED it
before that acknowledgement (the one-slot trap above, which the AI's fight driver
fell into until stage E3e), the face this roll really showed decides, and a
file-only [psychic roll] line says it happened - reading the other roll's die
would shock or spare the unit at random. The battle-shock goes through
battle_shock.set_battle_shocked() - the one door, which tells War Horde's
Breakin' Heads that a unit became battle-shocked.
"""

from game import battle_shock, unstable_energies

PSYCHIC_ROLL_SIDES = 6
PSYCHIC_ROLL_FAILURE = 1


class PsychicRollController:
    def __init__(self, dice_manager=None, turn_tracker=None, game_log=None):
        self.dice_manager = dice_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._pending = None  # (squad, ability name, label, rolled face) while the D6 is on the table

    @property
    def is_busy(self):
        return self._pending is not None

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)

    def _battle_round(self):
        return getattr(self.turn_tracker, "battle_round", 0) or 0

    def why_not(self, squad, psychic_level=1):
        """None when `squad` may make a psychic roll for an ability of
        `psychic_level` right now, else the reason."""
        if squad is None or not any(not m.is_dead() for m in squad.models):
            return "no living unit"
        if getattr(squad, "battle_shocked", False):
            return "%s is battle-shocked" % squad.name
        if not unstable_energies.can_use(squad, psychic_level, self._battle_round()):
            return "%s has used its psyker level this battle round (Unstable Energies)" % squad.name
        if self.dice_manager is None or self.dice_manager.is_pending or self._pending is not None:
            return "another roll is on the table"
        return None

    def can_roll(self, squad, psychic_level=1):
        return self.why_not(squad, psychic_level) is None

    def roll(self, squad, ability_name, psychic_level=1):
        """Spend the level and throw the D6. Returns False (and does nothing)
        when a gate refuses."""
        if not self.can_roll(squad, psychic_level):
            return False
        unstable_energies.spend(squad, psychic_level, self._battle_round())
        self._log("%s: %s makes a psychic roll for %s (psychic level %d) - on a 1 it is battle-shocked."
                  % (squad.owner, squad.name, ability_name, psychic_level))
        label = "Psychic roll: %s (%s) - a 1 battle-shocks it" % (ability_name, squad.name)
        values = self.dice_manager.roll(
            count=1, sides=PSYCHIC_ROLL_SIDES, label=label,
            title="Psychic Roll", subtitle=ability_name,
            target_name=squad.name, rolled_for=squad,
        )
        self._pending = (squad, ability_name, label, values[0] if values else None)
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            return False
        squad, ability_name, label, rolled = self._pending
        self._pending = None
        if getattr(self.dice_manager, "label", None) == label:
            values = getattr(self.dice_manager, "last_values", None) or []
            value = values[0] if values else rolled
        else:
            value = rolled
            if self.game_log is not None:
                self.game_log.add("[psychic roll] %s's roll for %s was replaced by another roll before it was "
                                  "acknowledged - resolved on the face it showed (%s)."
                                  % (squad.name, ability_name, rolled), file_only=True)
        if value == PSYCHIC_ROLL_FAILURE:
            battle_shock.set_battle_shocked(squad, source="a psychic roll (%s)" % ability_name)
            self._log("%s: %s rolled a 1 for %s and is battle-shocked."
                      % (squad.owner, squad.name, ability_name))
        else:
            self._log("%s: %s rolled a %s for %s." % (squad.owner, squad.name, value, ability_name))
        return True
