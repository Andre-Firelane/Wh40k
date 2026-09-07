"""Kharseth's "Fury of the Void" - a datasheet ability.

RULE (printed, word for word):
  "In your Shooting phase, after this model's unit has shot, select one enemy
  unit hit by one or more attacks made with this model's Dread of the Deep
  Void. Until the end of the turn, that unit is riven. Each time an AELDARI
  model from your army makes an attack that targets a riven unit, add 1 to the
  Strength characteristic of that attack."

THE SEVENTH ENEMY MARK, AND THE FIRST THAT CHANGES A CHARACTERISTIC
--------------------------------------------------------------------
Guide (+1 Hit), Doom (+1 Wound), Misfortune (-1 Wound), Whispering Web,
Advanced Scouting and Harnessed Alien Instincts are the others. Every one of
them adjusts a ROLL. This one adds to STRENGTH, which is not a modifier at all
- it changes the number the wound THRESHOLD is computed from, so it has to
reach the weapon before that computation rather than the roll after it.

That puts it in the adjuster chain, not in _wound_modifiers(). The difference
is visible: +1 Strength that crosses a Toughness boundary moves the threshold a
whole step, and +1 that does not moves nothing - which is exactly the measuring
Protocol of the Hungry Void's AI verdict already has to do.

ARMY-WIDE, not unit-wide: "each time an AELDARI model FROM YOUR ARMY". So the
mark is held per PLAYER, like Guide and Doom, and every Aeldari unit that
player owns reads it.

"WITH THIS MODEL'S DREAD OF THE DEEP VOID" is a per-WEAPON condition, so a unit
hit only by the rest of the squad is not a legal choice - the same per-weapon
subset the Shadow Weaver's and the Night Spinner's marks need, and the same
source: ShootingController.squads_hit_by_weapon().

"UNTIL THE END OF THE TURN" - one boundary shorter than Guide and Doom, which
run to the start of the next Command phase. So it is cleared in the ordinary
end-of-turn block rather than at a Command phase.
"""
import copy

from game import psychic_guidance
from game.weapons import DreadOfTheDeepVoidProfile

FURY_OF_THE_VOID_LABEL = "Fury of the Void"

#: "add 1 to the Strength characteristic of that attack".
RIVEN_STRENGTH_BONUS = 1

#: Exported so main.py can ask for the per-weapon hit subset without importing
#: game/weapons.py - the shape target_acquisition.LONG_RIFLE_NAME has.
DREAD_OF_THE_DEEP_VOID_NAME = DreadOfTheDeepVoidProfile.name


class FuryOfTheVoidController:
    """The riven marks. One per battle, held per player."""

    def __init__(self, decision_manager=None, game_log=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self._riven = {}        # player -> set of marked enemy Squads

    def applies(self, squad):
        return any(getattr(m.profile, "fury_of_the_void", False)
                   for m in getattr(squad, "models", ()) or () if not m.is_dead())

    def is_riven(self, target_squad, by_player=None):
        if by_player is not None:
            return target_squad in self._riven.get(by_player, ())
        return any(target_squad in marked for marked in self._riven.values())

    def mark(self, bearer_squad, target):
        if bearer_squad is None or target is None:
            return False
        self._riven.setdefault(bearer_squad.owner, set()).add(target)
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s is riven until the end of the turn - AELDARI attacks against "
                "it add %d to their Strength."
                % (FURY_OF_THE_VOID_LABEL, target.name, RIVEN_STRENGTH_BONUS))
        return True

    def offer_after_shooting(self, squad, hit_squads, dread_hits=()):
        """The per-WEAPON subset again: a unit hit only by the rest of the
        squad is not a legal choice."""
        if not self.applies(squad):
            return False
        candidates = [s for s in hit_squads
                      if s in dread_hits and not self.is_riven(s, squad.owner)]
        if not candidates:
            return False
        if len(candidates) == 1 or self.decision_manager is None:
            return self.mark(squad, candidates[0])
        self.decision_manager.request(
            squad.owner,
            "%s: %s - which unit is riven?" % (squad.name, FURY_OF_THE_VOID_LABEL),
            [(t.name, (lambda t=t: self.mark(squad, t)), t) for t in candidates],
        )
        return True

    def adjusted_weapon(self, weapon, attacking_squad, target_squad):
        """+1 Strength for any AELDARI attacker of the marking player.

        The faction test is the same one game/psychic_guidance.py and the two
        psychic marks use - read off the datasheet's FACTION, since
        game/factions/aeldari.py deliberately does not repeat the keyword on
        each datasheet."""
        if weapon is None or attacking_squad is None or target_squad is None:
            return weapon
        if not psychic_guidance._is_aeldari(attacking_squad):
            return weapon
        if not self.is_riven(target_squad, attacking_squad.owner):
            return weapon
        adjusted = copy.copy(weapon)
        adjusted.strength = weapon.strength + RIVEN_STRENGTH_BONUS
        return adjusted

    def reset_turn(self, player=None):
        """"Until the end of the turn" - one boundary shorter than Guide."""
        if player is None:
            self._riven.clear()
        else:
            self._riven.pop(player, None)
