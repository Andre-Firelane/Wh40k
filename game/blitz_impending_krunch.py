"""Blitz Brigade Stratagem: Impending Krunch (1CP, Mecha Orks stage G4).

RULE (verbatim, rules/orks/detachments/Blitz Brigade.md):
  WHEN:   Your Charge phase, when a friendly WAGON unit ends a charge move.
  TARGET: That WAGON unit.
  EFFECT: Each enemy unit engaged with your unit makes a battle-shock roll,
          with -1 to that battle-shock roll.

WHERE IT HANGS: ChargeController.on_charge_move_finished - rule 11.04's "ends a
charge move", the hook Mobbed, Crimson Harvest and Krushin' Impetus use. "YOUR
Charge phase" is read off turn_owner at that instant (a live hook, not a phase
boundary, so the clock is right): a WAGON's Heroic Intervention in the
opponent's Charge phase ends a charge move too, and is not offered. A charge
that engaged nothing has no target for the EFFECT and is not offered either
(error class 5).

AN OFFER, NOT A BUTTON: the moment is the end of one charge move, which a panel
button could only catch if the player happened to have the WAGON selected then.
The owner is asked once per charge move (a memo keyed on the unit and the turn,
since the hook may be heard again for the same move); the CP is paid on "Use".

THE TESTS go through game/forced_shock_queue.py - the queue Mobbed wrote, shared
since this became its second user - so several engaged units test one after
another, each at -1, and a roll some other rule has open is waited out.
main.py's dice acknowledgement releases the next one.

THE AI buys it when at least one engaged enemy unit is NOT already
battle-shocked: a passed test REMOVES battle-shock (rule 01.07), so testing only
units that are already shocked can help the opponent. Deterministic, 0 API calls.
"""

from game import ai_mode, blitz_brigade
from game.engagement import units_are_engaged
from game.forced_shock_queue import ForcedShockQueue
from game.stratagems import Stratagem
from game.turn import PHASE_CHARGE

IMPENDING_KRUNCH_NAME = "Impending Krunch"
IMPENDING_KRUNCH_CP = 1
#: "with -1 to that battle-shock roll".
IMPENDING_KRUNCH_PENALTY = 1
USE_LABEL = "Use Impending Krunch (1 CP)"
DECLINE_LABEL = "Decline"


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def worth_it(targets):
    """The AI's rule: someone would actually be at risk of becoming shocked."""
    return any(not getattr(t, "battle_shocked", False) for t in targets)


class ImpendingKrunchController:
    def __init__(self, stratagem_controller, battle_shock_controller=None, turn_tracker=None,
                 decision_manager=None, all_tokens=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self.queue = ForcedShockQueue(battle_shock_controller, game_log)
        self._offered = set()
        self._stratagem = Stratagem(IMPENDING_KRUNCH_NAME, IMPENDING_KRUNCH_CP, self._effect)
        self._acting = None

    # ----------------------------------------------------------- questions
    def targets_for(self, squad):
        """Each enemy unit engaged with `squad`, by name."""
        if squad is None:
            return []
        enemies = {t.squad for t in self.all_tokens
                   if getattr(t, "squad", None) is not None and t.squad.owner != squad.owner
                   and not t.is_dead()}
        return sorted((e for e in enemies if _living(e) and units_are_engaged(squad, e)),
                      key=lambda s: s.name)

    def _memo_key(self, squad):
        tt = self.turn_tracker
        return (id(squad), getattr(tt, "battle_round", None), getattr(tt, "turn_owner", None))

    def can_use(self, squad):
        tt = self.turn_tracker
        if squad is None or tt is None or not _living(squad):
            return False
        if tt.phase != PHASE_CHARGE or squad.owner != tt.turn_owner:
            return False
        if not blitz_brigade.applies(squad):
            return False
        if not self.targets_for(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    # --------------------------------------------------------- the moment
    def on_charge_move_finished(self, squad):
        if not self.can_use(squad):
            return False
        key = self._memo_key(squad)
        if key in self._offered:
            return False
        self._offered.add(key)
        if squad.owner in self.auto_players or self.decision_manager is None:
            if not worth_it(self.targets_for(squad)):
                return False
            return self.use(squad)
        names = ", ".join(t.name for t in self.targets_for(squad))
        self.decision_manager.request(
            squad.owner,
            "%s (%d CP): %s ended its charge - every enemy unit engaged with it (%s) takes a "
            "Battle-shock test at -%d?" % (IMPENDING_KRUNCH_NAME, IMPENDING_KRUNCH_CP, squad.name,
                                           names, IMPENDING_KRUNCH_PENALTY),
            [(USE_LABEL, lambda s=squad: self.use(s)), (DECLINE_LABEL, lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, squad):
        """Pay and queue the tests - checked again, because a human answers
        frames later."""
        if not self.can_use(squad):
            return False
        self._acting = squad
        try:
            return bool(self.stratagem_controller.use(squad.owner, self._stratagem, [squad]))
        finally:
            self._acting = None

    def _effect(self, controller, player, targets):
        squad = self._acting
        if squad is None:
            return False
        for target in self.targets_for(squad):
            self.queue.enqueue(
                target, IMPENDING_KRUNCH_PENALTY, IMPENDING_KRUNCH_NAME,
                "%s: %s is engaged with %s, which takes a Battle-Shock test at -%d."
                % (IMPENDING_KRUNCH_NAME, target.name, squad.name, IMPENDING_KRUNCH_PENALTY))
        self.queue.drain()
        return True

    def on_dice_acknowledged(self):
        return self.queue.on_dice_acknowledged()

    @property
    def is_busy(self):
        return self.queue.is_busy
