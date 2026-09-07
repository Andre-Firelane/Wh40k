"""Path of the Outcast Stratagem: Casting Back the Veil (1CP).

RULE (verbatim, rules/aeldari/detachments/Path of the Outcast.md):
  WHEN:   Your Shooting phase, when a friendly RANGERS/SHROUD RUNNERS unit has
          shot.
  TARGET: That RANGERS/SHROUD RUNNERS unit.
  EFFECT: Select one enemy unit hit by those ranged attacks. That enemy unit
          has +6" detection range.
  RESTRICTIONS: none printed.

THE FIFTH SOURCE IN game/detection_range.py, after the Auxiliary Cadre prey
marks, the Unmasking Suite, the Negation Emitters Enhancement and this
detachment's own rule. Attached the way the last two are - a module-level call
INSIDE bonus_in() - so neither of that function's two call sites grows a
parameter. That is the whole reason the fold was extracted.

THE SAME NUMBER AS THE DETACHMENT RULE, AND DELIBERATELY NOT SHARED WITH IT.
Far-Reaching Doom gives +6" to enemy units while a Rangers unit is inside its
"selected to shoot" window; this gives +6" to ONE enemy unit, permanently. Same
size, different scope and different lifetime, so they are two entries in the
fold rather than one - and because they ADD, a unit hit by this while the rule's
window is open is at +12", which is what two separate printed effects saying
"+6" ought to do.

WHICH DIRECTION, written out because it inverts cleanly and reads fine wrong:
detection range belongs to the HIDDEN model, so a POSITIVE contribution on an
enemy makes that enemy visible from FURTHER AWAY - a penalty on them, which is
what a sniper detachment should be buying.

NO DURATION IS PRINTED. Unlike the detachment rule, whose window closes when
the unit has shot, this names no end - so the mark is kept for the rest of the
battle, and there is no reset. That absence is the thing most likely to be
"fixed" by a later reader, so it is pinned.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import ai_mode, far_reaching_doom
from game.stratagems import Stratagem

CASTING_BACK_THE_VEIL_NAME = "Casting Back the Veil"
CASTING_BACK_THE_VEIL_CP = 1

#: "That enemy unit has +6\" detection range."
CASTING_BACK_THE_VEIL_BONUS_IN = 6.0

#: The marked enemy units, by id(). Module state rather than controller state,
#: for the same reason the detachment rule's window is: game/detection_range.py's
#: fold reads it from inside a pure function with nothing else in scope.
_marked = {}


def mark(target):
    if target is not None:
        _marked[id(target)] = target
    return True


def is_marked(squad):
    return squad is not None and id(squad) in _marked


def detection_bonus_in(squad):
    """This Stratagem's contribution to game/detection_range.py's fold.

    Named `..._bonus_in` like every other source there, and positive - see the
    module docstring on why that is the penalty and not the protection."""
    return CASTING_BACK_THE_VEIL_BONUS_IN if is_marked(squad) else 0.0


def reset():
    """For tests and a fresh battle. NOT called on any phase or turn boundary:
    the printed text names no duration."""
    _marked.clear()


class CastingBackTheVeilController:
    """The offer, made when a Rangers/Shroud Runners unit has finished shooting."""

    def __init__(self, stratagem_controller, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._pending_hits = ()
        self._stratagem = Stratagem(
            name=CASTING_BACK_THE_VEIL_NAME, cp_cost=CASTING_BACK_THE_VEIL_CP,
            effect=self._effect,
        )

    def can_use(self, squad, hit_squads=()):
        if squad is None or self.stratagem_controller is None:
            return False
        if not far_reaching_doom.applies(squad):
            return False
        # Never offered when it would buy nothing: a unit already marked gains
        # no second +6" from a second purchase, since the mark is a set.
        if not any(s is not None and not is_marked(s) for s in hit_squads or ()):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def offer_after_shooting(self, squad, hit_squads):
        if not self.can_use(squad, hit_squads):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return False                      # no AI path
        self._pending_hits = tuple(hit_squads or ())
        self.decision_manager.request(
            squad.owner,
            '%s (%d CP): %s has shot - give a unit it hit +%g" detection range?'
            % (CASTING_BACK_THE_VEIL_NAME, CASTING_BACK_THE_VEIL_CP, squad.name,
               CASTING_BACK_THE_VEIL_BONUS_IN),
            [("Use (%d CP)" % CASTING_BACK_THE_VEIL_CP,
              (lambda: self.use(squad, self._pending_hits))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, squad, hit_squads=()):
        if not self.can_use(squad, hit_squads):
            return False
        self._pending_hits = tuple(hit_squads or self._pending_hits)
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _effect(self, controller, player, targets):
        hits, self._pending_hits = self._pending_hits, ()
        squad = targets[0] if targets else None
        options = sorted((s for s in hits if s is not None and not is_marked(s)),
                         key=lambda s: s.name)
        if not options:
            return
        if len(options) == 1 or self.decision_manager is None:
            self._mark(options[0])
            return
        self.decision_manager.request(
            squad.owner,
            "%s: which unit?" % CASTING_BACK_THE_VEIL_NAME,
            [(t.name, (lambda t=t: self._mark(t)), t) for t in options],
            is_stratagem=True,
        )

    def _mark(self, target):
        mark(target)
        if self.game_log is not None:
            self.game_log.add(
                '%s: %s has +%g" detection range for the rest of the battle.'
                % (CASTING_BACK_THE_VEIL_NAME, target.name,
                   CASTING_BACK_THE_VEIL_BONUS_IN))
        return True
