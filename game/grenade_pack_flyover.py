"""Swooping Hawks' "Grenade Pack Flyover".

RULE (printed, word for word):
  "Once per turn, in your Movement phase, when this unit is set up on the
   battlefield or ends a Normal, Advance or Fall Back move, it can use this
   ability. If it does, select one enemy unit within 8" of and visible to this
   unit and roll one D6 for each SWOOPING HAWKS model in this unit: for each
   4+, that enemy unit suffers 1 mortal wound (to a maximum of 6 mortal
   wounds). Each time this unit uses this ability, until the end of the turn,
   you cannot target this unit with the Explosives Stratagem."

MECHANICALLY THIS IS SEER COUNCIL'S ISHA'S FURY, with three differences that
are all in the numbers rather than the shape: the dice count is the unit's own
model count instead of a flat six, the threshold is 4+ rather than 3+, the
total is capped, and it is the ACTIVE player's ability rather than a reaction.
So it reuses that module's arrangement - one visible roll, then rule 06.02's
MortalWoundAllocationSession, whose owner is the DEFENDER.

TWO TRIGGERS, and both already exist:
  * "ends a Normal, Advance or Fall Back move" is MovementController's
    on_move_finished - third consumer, after Isha's Fury and Rangers' Path of
    the Outcast, which is why that hook is a list.
  * "is set up on the battlefield" is IngressController.on_ingress_resolved -
    second consumer, after Rapid Ingress, which is why THAT hook is a list too.

"ONE D6 FOR EACH SWOOPING HAWKS MODEL" counts models with the ability, not
every model in the unit: after a 19.01 merge Baharroth is in there too, and he
is a BAHARROTH, not a SWOOPING HAWKS. Counted off the flag, which is exactly
that distinction.

THE CAP IS ON THE MORTAL WOUNDS, not on the dice - "(to a maximum of 6 mortal
wounds)". A ten-model unit still rolls ten dice; it just cannot inflict more
than six. Rolling six would be a different, worse distribution.

"YOU CANNOT TARGET THIS UNIT WITH THE EXPLOSIVES STRATAGEM" is a flag on the
squad with the same until-end-of-turn lifetime as charge_locked_until_end_of_turn,
and read by game/explosives.py's own eligibility.
"""

from game.damage_resolution import MortalWoundAllocationSession
from game.dice_notation import D6, DiceNotationRoll
from game.turn import PHASE_MOVEMENT

FLYOVER_RANGE_IN = 8.0
FLYOVER_SUCCESS_THRESHOLD = 4
FLYOVER_MAX_MORTAL_WOUNDS = 6
FLYOVER_LABEL = "Grenade Pack Flyover"


def applies(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "grenade_pack_flyover", False)
               for m in squad.models if not m.is_dead())


def dice_count(squad):
    """"One D6 for each SWOOPING HAWKS model in this unit" - the models with
    the ability, which after a 19.01 merge is not the same as every model."""
    if squad is None:
        return 0
    return len([m for m in squad.models
                if not m.is_dead() and getattr(m.profile, "grenade_pack_flyover", False)])


class GrenadePackFlyoverController:
    """Wired to MovementController.on_move_finished AND
    IngressController.on_ingress_resolved in main.py."""

    def __init__(self, game_state=None, decision_manager=None, dice_manager=None,
                 turn_tracker=None, game_log=None, line_of_sight=None):
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.dice_manager = dice_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        # callable(squad, target) -> bool; None means "do not test visibility",
        # which degrades safely (the range test still applies).
        self.line_of_sight = line_of_sight
        self._used_this_turn = set()      # id(squad)
        self._roll = None
        self._pending = None              # (squad, target)
        self._wounds = None

    # -- lifetime ---------------------------------------------------------
    def reset_turn(self):
        """"Once per TURN"."""
        self._used_this_turn = set()

    @property
    def is_busy(self):
        return self._roll is not None or self._wounds is not None

    def used_this_turn(self, squad):
        return squad is not None and id(squad) in self._used_this_turn

    # -- triggers ---------------------------------------------------------
    def offer_after_move(self, squad, kind=None):
        """`kind` is reported by on_move_finished. The printed text names
        exactly Normal, Advance and Fall Back - which is the whole qualifying
        set that hook reports, so nothing is filtered out here."""
        self._offer(squad)

    def offer_after_setup(self, squad):
        """"when this unit is SET UP on the battlefield" - the arrival half."""
        self._offer(squad)

    def _offer(self, squad):
        if not self.can_use(squad):
            return
        targets = self.targets_for(squad)
        if not targets:
            return
        options = [(t.name, (lambda tt=t: self.use(squad, tt))) for t in targets]
        options.append(("Do not use it", lambda: None))
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: {FLYOVER_LABEL} - which unit takes the grenades?",
            options,
        )

    def can_use(self, squad):
        if squad is None or self.decision_manager is None or self.game_state is None:
            return False
        if not applies(squad) or self.used_this_turn(squad):
            return False
        if self.turn_tracker is None:
            return False
        # "In YOUR Movement phase" - so the unit's own, not the opponent's.
        if self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if self.turn_tracker.turn_owner != squad.owner:
            return False
        return dice_count(squad) > 0

    def targets_for(self, squad):
        """"one enemy unit within 8" of and visible to this unit"."""
        out, seen = [], set()
        for token in list(getattr(self.game_state, "tokens", ())):
            other = getattr(token, "squad", None)
            if other is None or id(other) in seen or other.owner == squad.owner:
                continue
            seen.add(id(other))
            if not [m for m in other.models if not m.is_dead()]:
                continue
            if squad.min_distance_to(other) > FLYOVER_RANGE_IN:
                continue
            if self.line_of_sight is not None and not self.line_of_sight(squad, other):
                continue
            out.append(other)
        return out

    # -- resolution -------------------------------------------------------
    def use(self, squad, target):
        if not self.can_use(squad):
            return False
        self._used_this_turn.add(id(squad))
        # "until the end of the turn, you cannot target this unit with the
        # Explosives Stratagem" - read by game/explosives.py.
        squad.explosives_locked_until_end_of_turn = True
        count = dice_count(squad)
        self._pending = (squad, target)
        self._roll = DiceNotationRoll(
            D6(dice=count), count=1, dice_manager=self.dice_manager,
            label=(f"{FLYOVER_LABEL}: {squad.name} vs {target.name} "
                   f"({count} dice, {FLYOVER_SUCCESS_THRESHOLD}+ each)"),
        )
        if self._roll.done:                    # no dice_manager (tests)
            self._resolve(self._roll_values())
        return True

    def _roll_values(self):
        if self.dice_manager is not None:
            return list(self.dice_manager.last_values or ())
        return []

    def on_dice_acknowledged(self):
        if self._roll is None:
            return
        values = list(self.dice_manager.last_values or ()) if self.dice_manager else []
        self._roll = None
        self._resolve(values)

    def _resolve(self, values):
        squad, target = self._pending or (None, None)
        self._pending = None
        if squad is None or target is None:
            return
        successes = sum(1 for v in values if v >= FLYOVER_SUCCESS_THRESHOLD)
        wounds = min(successes, FLYOVER_MAX_MORTAL_WOUNDS)
        if self.game_log is not None:
            capped = " (capped)" if successes > wounds else ""
            self.game_log.add(
                f"{squad.owner}: {FLYOVER_LABEL} {values} - {successes} at "
                f"{FLYOVER_SUCCESS_THRESHOLD}+ -> {wounds} mortal wound(s){capped} on {target.name}."
            )
        if wounds <= 0:
            return
        # Rule 06.02: the DEFENDER chooses which models take them, so the
        # active player is flipped for the allocation exactly as
        # game/explosives.py does it.
        self._wounds = MortalWoundAllocationSession(target, wounds)
        if self.turn_tracker is not None:
            self._restore_active = self.turn_tracker.active_player
            self.turn_tracker.set_active(target.owner)

    @property
    def pending_damage_choice(self):
        return self._wounds.pending_choice if self._wounds is not None else None

    def choose_damage_model(self, model):
        if self._wounds is None:
            return
        self._wounds.choose_model(model)
        if self._wounds.done:
            self._wounds = None
            if self.turn_tracker is not None and getattr(self, "_restore_active", None):
                self.turn_tracker.set_active(self._restore_active)
                self._restore_active = None
