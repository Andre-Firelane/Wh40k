"""The Stonesinger's "Elemental Ensnarement" - a datasheet ability.

RULE (printed, word for word):
  "At the end of your Fight phase, if this unit is not battle-shocked, you can
  use this ability. If you do, roll one D6:
    - On a 1, this unit is battle-shocked.
    - Select one visible enemy MONSTER/VEHICLE unit (excluding TITANIC units)
      within 18" of this unit. That enemy unit is ensnared until the start of
      your next turn:
      - While a unit is ensnared, that unit has -2" M and cannot be pinned."

THE TWO BULLETS ARE NOT ALTERNATIVES - READ THE INDENTATION
------------------------------------------------------------
Both fire. A 1 battle-shocks the Stonesinger AND the enemy is still ensnared;
the roll is the price, not the gate. Reading them as an either/or would make a
1 a total whiff, which is the naive reading and the one worth pinning against.

ENSNARED IS A THIRD MOVEMENT STATUS, alongside Mont'ka's `shaken` and the Night
Spinner's `pinned`, and it is the first that INTERACTS with another one:

  shaken    -2 Move, -2 Advance, -2 Charge    (game/montka_pulse_onslaught.py)
  pinned    -2 Move,             -2 Charge    (game/monofilament_web.py)
  ensnared  -2 Move,  and CANNOT BE PINNED    (here)

"Cannot be pinned" is a real clause and not flavour: an ensnared unit that a
Night Spinner then hits does NOT stack the two -2s, because the second status
never lands. That is enforced where the pin is APPLIED rather than where it is
read, so a unit ensnared AFTER being pinned keeps the pin it already had - the
printed text prevents becoming pinned, not being pinned.

Stored on the squad like its two siblings, for the reason
game/monofilament_web.py sets out: the Move penalty is read by
game/coldstar.py's effective_movement_in(), which has no controller in scope.
"""

from game import ai_mode

ELEMENTAL_ENSNAREMENT_LABEL = "Elemental Ensnarement"

#: "-2 inches M".
ENSNARED_MOVE_PENALTY = 2
#: "On a 1, this unit is battle-shocked."
SELF_SHOCK_FACE = 1
#: "within 18 inches".
ENSNAREMENT_RANGE_IN = 18.0


def is_ensnared(squad):
    return getattr(squad, "ensnared_by_player", None) is not None


def move_penalty_for(squad):
    """-2 to the Move characteristic, read by effective_movement_in()."""
    return ENSNARED_MOVE_PENALTY if is_ensnared(squad) else 0


def blocks_pinning(squad):
    """"cannot be pinned" - asked by game/monofilament_web.py when it tries to
    APPLY a pin, not when one is read."""
    return is_ensnared(squad)


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def has_ability(squad):
    return any(getattr(m.profile, "elemental_ensnarement", False)
               for m in _living(squad))


class ElementalEnsnarementController:
    """The end-of-Fight-phase offer, the roll, and the status's lifetime."""

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 all_tokens=None, auto_players=()):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.auto_players = ai_mode.players(auto_players)

    def can_use(self, squad):
        """"if this unit is not battle-shocked" - and it must still exist."""
        return (has_ability(squad) and _living(squad)
                and not getattr(squad, "battle_shocked", False))

    def candidates(self, squad, visible_to=None):
        """"one visible enemy MONSTER/VEHICLE unit (excluding TITANIC) within
        18 inches".

        `visible_to(other)` is injected so this module owns no line-of-sight
        opinion; without it every unit in range is offered, which is what a
        headless test wants."""
        from game.squad import edge_distance, is_monster_or_vehicle_unit
        if not self.can_use(squad):
            return []
        mine = _living(squad)
        seen, out = set(), []
        for token in self.all_tokens or ():
            other = getattr(token, "squad", None)
            if other is None or id(other) in seen or other.owner == squad.owner:
                continue
            if not _living(other) or not is_monster_or_vehicle_unit(other):
                continue
            if any(getattr(m.profile, "titanic", False) for m in _living(other)):
                continue
            if visible_to is not None and not visible_to(other):
                continue
            if any(edge_distance(a, b) <= ENSNAREMENT_RANGE_IN
                   for a in mine for b in _living(other)):
                seen.add(id(other))
                out.append(other)
        return out

    def use(self, squad, target):
        """Both bullets, in the printed order. The D6 is the PRICE, not the
        gate - a 1 battle-shocks the Stonesinger and the target is ensnared
        anyway."""
        if not self.can_use(squad) or target is None:
            return False
        rolled = self._roll_one()
        if rolled == SELF_SHOCK_FACE:
            squad.battle_shocked = True
            if self.game_log is not None:
                self.game_log.add("%s: %s rolled a 1 and is battle-shocked."
                                  % (ELEMENTAL_ENSNAREMENT_LABEL, squad.name))
        target.ensnared_by_player = squad.owner
        if self.game_log is not None:
            self.game_log.add(
                '%s: %s is ensnared until the start of %s\'s next turn '
                '(-%d" M, and it cannot be pinned).'
                % (ELEMENTAL_ENSNAREMENT_LABEL, target.name, squad.owner,
                   ENSNARED_MOVE_PENALTY))
        return True

    def offer_at_end_of_fight(self, player, squads, visible_to=None):
        """One offer per bearer unit that has a legal selection."""
        for squad in squads or ():
            if squad.owner != player or not self.can_use(squad):
                continue
            options = self.candidates(squad, visible_to=visible_to)
            if not options:
                continue
            if player in self.auto_players or self.decision_manager is None:
                self.use(squad, options[0])
                continue
            self.decision_manager.request(
                player,
                "%s: %s - ensnare which enemy MONSTER/VEHICLE unit?"
                % (ELEMENTAL_ENSNAREMENT_LABEL, squad.name),
                [(t.name, (lambda s=squad, t=t: self.use(s, t)), t) for t in options]
                + [("Do not use it", None)],
            )
            return True
        return False

    def clear_for_turn_of(self, player, squads=()):
        """"Until the start of YOUR next turn"."""
        for squad in squads or ():
            if getattr(squad, "ensnared_by_player", None) == player:
                squad.ensnared_by_player = None

    def _roll_one(self):
        from game.dice import random as dice_random
        return dice_random.randint(1, 6)
