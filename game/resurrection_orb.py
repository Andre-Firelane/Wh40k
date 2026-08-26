"""The Overlord's "Resurrection Orb" wargear.

RULE (printed, word for word):
  "Once per battle, per unit. At the end of any phase, you can use this
   ability. If you do, this unit resurrects: When a unit resurrects, that
   unit's Reanimation Protocols activate, but that unit heals D6 wounds
   (instead of D3 wounds). You cannot resurrect more than one unit per turn."

THIS IS THE ARMY RULE WITH A BIGGER DIE, and it is written that way: the whole
effect is game/reanimation_protocols.py's reanimate(), handed a D6 instead of a
D3. Nothing about healing, reviving, placement or the starting-strength cap is
restated here - a second copy of that arithmetic is exactly the drift this repo
keeps consolidating away.

THREE SEPARATE LEDGERS, because the printed text really does impose three
different limits, and collapsing them would be wrong in both directions:

  * "once per battle, PER UNIT" - keyed on the unit, never cleared;
  * "not more than one unit per TURN" - keyed on the player, cleared each turn;
  * "at the end of ANY phase" - so it is offered at every phase boundary, not
    only in the Command phase like the army rule itself.

THE AI'S ANSWER IS DETERMINISTIC and gated on the shared recoverable_wounds()
measure: use it once the unit could actually turn at least
RESURRECTION_ORB_MIN_RECOVERABLE wounds into something. A D6 averages 3.5, so
spending a once-per-battle orb on a unit that can only use one wound wastes it,
and waiting for a bigger loss is the whole point of holding it.
"""

from game import reanimation_protocols

RESURRECTION_ORB_DICE_SIDES = 6
#: How much a unit must be able to recover before the AI spends the orb on it.
#: Deliberately below the D6's 3.5 average - the orb is worth using on a real
#: loss, not only on a catastrophic one.
RESURRECTION_ORB_MIN_RECOVERABLE = 4


def bearers(squad):
    """The models carrying an orb. Set by the Gear item in
    game/factions/necrons.py, so it is a token flag, not a profile one."""
    return [m for m in getattr(squad, "models", ()) or ()
            if getattr(m, "resurrection_orb", False) and not m.is_dead()]


def has_orb(squad):
    return bool(bearers(squad))


class ResurrectionOrbController:
    """Offered at every phase boundary - "at the end of any phase"."""

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, position_valid=None, auto_players=()):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.position_valid = position_valid
        self.auto_players = set(auto_players)
        self._used_squads = set()    # id(squad) - once per battle, per unit
        self._used_this_turn = set()  # player - one unit per turn
        self._pending = None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    @property
    def is_busy(self):
        return self._pending is not None

    def reset_turn(self):
        """"You cannot resurrect more than one unit per turn"."""
        self._used_this_turn.clear()

    def can_use(self, squad):
        if self._pending is not None or squad is None or not has_orb(squad):
            return False
        if id(squad) in self._used_squads or squad.owner in self._used_this_turn:
            return False
        return reanimation_protocols.recoverable_wounds(squad) > 0

    def is_worth_using(self, squad):
        """The AI's deterministic gate - see this module's docstring."""
        return (self.can_use(squad)
                and reanimation_protocols.recoverable_wounds(squad) >= RESURRECTION_ORB_MIN_RECOVERABLE)

    def offer_at_end_of_phase(self, squads, player):
        """Returns True if anything was used or prompted. One unit at a time:
        the per-turn limit means a second offer could never be taken anyway."""
        candidates = sorted((s for s in squads if s.owner == player and self.can_use(s)),
                            key=lambda s: s.name)
        if not candidates:
            return False
        if player in self.auto_players or self.decision_manager is None:
            worth = [s for s in candidates if self.is_worth_using(s)]
            if not worth:
                return False
            best = max(worth, key=lambda s: (reanimation_protocols.recoverable_wounds(s), s.name))
            return self._use(best)
        squad = candidates[0]
        self.decision_manager.request(
            player,
            f"{squad.name}: use the Resurrection Orb? (reanimates D6 instead of D3)",
            [("Use the Resurrection Orb", lambda: self._use(squad)), ("Decline", None)],
        )
        return True

    def _use(self, squad):
        if not self.can_use(squad):
            return False
        self._used_squads.add(id(squad))
        self._used_this_turn.add(squad.owner)
        self._pending = squad
        if self.dice_manager is None:
            self._resolve(RESURRECTION_ORB_DICE_SIDES)
            return True
        self.dice_manager.roll(
            1, RESURRECTION_ORB_DICE_SIDES, label="Resurrection Orb",
            target_name=squad.name, target_squad=squad, subject_label="Resurrecting")
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            return False
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or [1]
        self._resolve(values[0])
        return True

    def _resolve(self, rolled):
        squad, self._pending = self._pending, None
        spent, revived = reanimation_protocols.reanimate(
            squad, rolled,
            all_tokens=self._tokens(),
            position_valid=self.position_valid,
            game_state=self.game_state,
        )
        detail = f"{spent} wound(s)"
        if revived:
            detail += f", {len(revived)} model(s) back on the battlefield"
        self._log(f"Resurrection Orb ({squad.name}): rolled a {rolled} - reanimated {detail}.")
