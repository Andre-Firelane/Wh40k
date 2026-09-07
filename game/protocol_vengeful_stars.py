"""Awakened Dynasty Stratagem: "Protocol of the Vengeful Stars".

RULE (printed, word for word):
  WHEN:   "Your opponent's Shooting phase, just after an enemy unit destroys a
           NECRONS unit from your army."
  TARGET: "One NECRONS CHARACTER unit from your army that was within 6" of that
           NECRONS unit when it was destroyed."
  EFFECT: "After the attacking unit has resolved its attacks, your unit can
           shoot as if it were your Shooting phase, but it must target only
           that enemy unit when doing so, and can only do so if that enemy unit
           is an eligible target."

THE MOST EXPENSIVE PROTOCOL AT 2 CP, and the only one that grants an
out-of-turn ACTIVATION rather than a modifier or a re-roll. That makes it the
sibling of Fire Overwatch (15.08) rather than of the other five: the engine
already knows how to let a unit shoot outside its own phase, and this reuses
that rather than inventing a second route.

THE 6" IS MEASURED AT THE MOMENT OF DEATH, not when the Stratagem resolves -
"was within 6" of that unit WHEN IT WAS DESTROYED". By the time this is offered
the dead unit's models are off the board, so the distance has to be captured in
notify_destroyed() while they are still standing. Getting that backwards would
make the condition unmeasurable, which is the sort of thing that only shows up
as "the button never appears".

"MUST TARGET ONLY THAT ENEMY UNIT" is carried through as a target restriction
on the granted activation, so the shooting step cannot wander onto a better
target - and "only if that enemy unit is an eligible target" means the whole
thing simply does not fire when the killer is out of range or out of sight,
which is a normal outcome rather than an error.
"""

from game import ai_mode, awakened_dynasty
from game.stratagems import Stratagem

VENGEFUL_STARS_CP_COST = 2
VENGEFUL_STARS_NAME = "Protocol of the Vengeful Stars"
VENGEFUL_STARS_RANGE_IN = 6.0


def is_character_unit(squad):
    """"One NECRONS CHARACTER unit from your army"."""
    if squad is None or not awakened_dynasty.is_necrons_unit(squad):
        return False
    return any(getattr(m.profile, "character", False)
               for m in squad.models if not m.is_dead())


class VengefulStarsController:
    """Reactive, and two-staged: the candidates are captured when the unit
    dies, and the offer is made once the attacking unit has finished."""

    def __init__(self, stratagem_controller, decision_manager=None, game_log=None,
                 game_state=None, shooting_controller=None, turn_tracker=None,
                 auto_players=(), worth_using=None):
        self.stratagem_controller = stratagem_controller
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.auto_players = ai_mode.players(auto_players)
        # worth_using(avenger, killer) -> bool. main.py passes a gate built on
        # game/damage_estimate.py, so the AI spends 2 CP only when the shot is
        # actually worth something; None means "always worth it", which is what
        # a headless test wants.
        self.worth_using = worth_using
        self._candidates = []   # [(avenger_squad, killer_squad)] captured at death
        self._stratagem = Stratagem(
            name=VENGEFUL_STARS_NAME, cp_cost=VENGEFUL_STARS_CP_COST,
            effect=self._grant, allow_repeat_target=True,
        )

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    @staticmethod
    def _fallen_models(dead_squad):
        """Where the dead unit STOOD.

        By the time main.py's death sweep hands this over,
        GameState.remove_dead_models() has already emptied Squad.models - but
        it keeps the Tokens on Squad.destroyed_models and nothing resets their
        coordinates, which is the same property Reanimation Protocols relies
        on. So the positions the printed "was within 6" WHEN IT WAS DESTROYED"
        needs are still there; they are just not in `models` any more."""
        standing = [m for m in getattr(dead_squad, "models", ()) or () if not m.is_dead()]
        return standing or list(getattr(dead_squad, "destroyed_models", ()) or ())

    def notify_unit_destroyed(self, dead_squad, killer_squad):
        """Called from the death sweep with a unit that has just been wiped
        out and whoever was attacking at the time."""
        if dead_squad is None or killer_squad is None:
            return
        if not awakened_dynasty.stratagem_target_ok(dead_squad):
            return
        fallen = self._fallen_models(dead_squad)
        if not fallen:
            return
        for token in self._tokens():
            squad = getattr(token, "squad", None)
            if squad is None or squad is dead_squad or squad.owner != dead_squad.owner:
                continue
            if not is_character_unit(squad):
                continue
            if any(pair[0] is squad for pair in self._candidates):
                continue
            gap = min(
                ((a.x_in - b.x_in) ** 2 + (a.y_in - b.y_in) ** 2) ** 0.5
                - a.radius_in - b.radius_in
                for a in squad.models if not a.is_dead()
                for b in fallen
            )
            if gap <= VENGEFUL_STARS_RANGE_IN:
                self._candidates.append((squad, killer_squad))

    def has_candidates(self):
        return bool(self._candidates)

    def can_use(self, avenger, killer):
        if avenger is None or killer is None:
            return False
        if not awakened_dynasty.stratagem_target_ok(avenger):
            return False
        if not any(not m.is_dead() for m in avenger.models):
            return False
        if not any(not m.is_dead() for m in killer.models):
            return False   # "only if that enemy unit is an eligible target"
        return self.stratagem_controller.can_use(avenger.owner, self._stratagem, [avenger])

    def maybe_offer(self):
        """Called once the attacking unit has resolved its attacks. Returns
        True if anything was used or prompted."""
        candidates, self._candidates = self._candidates, []
        for avenger, killer in candidates:
            if not self.can_use(avenger, killer):
                continue
            if avenger.owner in self.auto_players:
                if self.worth_using is not None and not self.worth_using(avenger, killer):
                    continue
                return self._use(avenger, killer)
            if self.decision_manager is None:
                continue
            self.decision_manager.request(
                avenger.owner,
                f"{avenger.name} watched a unit die - use {VENGEFUL_STARS_NAME}? "
                f"({VENGEFUL_STARS_CP_COST} CP, shoot {killer.name} back)",
                [(f"Use {VENGEFUL_STARS_NAME}",
                  (lambda a=avenger, k=killer: self._use(a, k))), ("Decline", None)],
                is_stratagem=True,
            )
            return True
        return False

    def _use(self, avenger, killer):
        self._grant_target = killer
        return self.stratagem_controller.use(avenger.owner, self._stratagem, [avenger])

    def _grant(self, controller, player, targets):
        avenger = targets[0]
        killer = getattr(self, "_grant_target", None)
        self._log(f"{VENGEFUL_STARS_NAME}: {avenger.name} shoots back at {killer.name}.")
        if self.shooting_controller is None or killer is None:
            return
        # "can shoot as if it were your Shooting phase, but it MUST target only
        # that enemy unit". start_reactive_shooting(), NOT start_snap_shooting():
        # the latter is rule 15.09's deliberately weaker mode, and this grants
        # the ordinary thing. The restriction rides along with the activation so
        # the targeting step cannot wander onto something better.
        self.shooting_controller.start_reactive_shooting(avenger, restrict_to=[killer])

    def reset_phase(self):
        self._candidates = []
