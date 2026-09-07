"""Mont'ka Stratagem: Pinpoint Counter-Offensive (1CP).

RULE (verbatim, rules/tau_empire/detachments/Mont'ka.md):
  WHEN:   Any phase.
  TARGET: One T'AU EMPIRE unit (excluding KROOT units) from your army that was
          just destroyed. You can use this Stratagem on that unit even though
          it was just destroyed.
  EFFECT: Until the end of the battle, each time a T'AU EMPIRE unit (excluding
          KROOT units) from your army makes an attack that targets the enemy
          unit that just destroyed your unit, you can re-roll the Hit roll.

WHO KILLED IT
-------------
"the enemy unit that just destroyed your unit" needs a killer, and this engine
has no general kill attribution - what it has is "who was attacking at the
time", which the death sweep already passes to Protocol of the Vengeful Stars.
That is exact for an attack sequence (one unit is resolving attacks) and it is
the only answer available, so it is the one used, with the phase widened:
Vengeful Stars is Shooting-phase-only, this is "any phase", so the Fight
phase's attacker counts too.

BATTLE-LONG, AND HELD PER PLAYER
---------------------------------
"Until the end of the battle" - so unlike almost every other grant here this is
NEVER cleared. It is a mark on the ENEMY unit, held per player because "each
time a T'AU EMPIRE unit FROM YOUR ARMY" makes the attack, not just the dead
unit's friends - the whole army gets the re-roll.

The re-roll reaches BOTH attack steps, because the text says "an attack".
"""

from game import ai_mode, montka, tau_detachments
from game.attached_units import unit_has_datasheet_keyword
from game.stratagems import Stratagem

PINPOINT_CP = 1
PINPOINT_NAME = "Pinpoint Counter-Offensive"
KROOT_KEYWORD = "KROOT"


def is_eligible_avenger(squad):
    """"a T'AU EMPIRE unit (excluding KROOT units) from your army" - both the
    unit that dies and every unit that later benefits."""
    if squad is None or not tau_detachments.is_tau_unit(squad):
        return False
    return not unit_has_datasheet_keyword(squad, KROOT_KEYWORD)


class PinpointCounterOffensiveController:
    def __init__(self, stratagem_controller, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._marks = {}          # player -> set of marked enemy Squads, for the battle
        self._pending = None      # (dead_squad, killer_squad) for the purchase in flight
        # Units wiped out while the death sweep could not name their killer -
        # see notify_unit_destroyed(). Drained by maybe_offer() at the end of
        # the activation that made them, cleared at every phase boundary.
        self._owed = []
        self._stratagem = Stratagem(
            name=PINPOINT_NAME, cp_cost=PINPOINT_CP, effect=self._mark,
            # "even though it was just destroyed" - and each death is its own
            # window, so 15.01's one-target-per-phase is the wrong limit.
            allow_repeat_target=True,
        )

    def marked_by(self, player):
        return set(self._marks.get(player, ()))

    def applies(self, attacking_squad, target_squad):
        """Read by both attack steps' _hit_reroll_reason()."""
        if attacking_squad is None or target_squad is None:
            return False
        if not is_eligible_avenger(attacking_squad):
            return False
        if not tau_detachments.has_detachment(attacking_squad.owner, montka.SETTING):
            return False
        return target_squad in self._marks.get(attacking_squad.owner, ())

    def notify_unit_destroyed(self, dead_squad, killer_squad):
        """Fed from the death sweep, once per wiped-out unit, with whoever was
        attacking at the time - which is regularly NOBODY.

        remove_dead_models() runs once per frame, AFTER that frame's event
        handling, and _actually_finish_squad() clears active_squad the moment
        an activation ends. A unit wiped by the LAST weapon group of an
        activation therefore reaches this method with killer_squad None - and
        that is the only case this Stratagem cares about, which is why it was
        reported as never offered.

        So an unattributed death is STASHED instead of dropped, and
        maybe_offer() supplies the killer from the after-activation hook, where
        the attacker is carried as an argument and cannot be guessed wrong.
        Same shape as game/protocol_vengeful_stars.py, which defers for the
        same reason.
        """
        if dead_squad is None:
            return False
        if killer_squad is None:
            if self._could_offer(dead_squad):
                self._owed.append(dead_squad)
            return False
        return self._offer(dead_squad, killer_squad)

    def _offer(self, dead_squad, killer_squad):
        if killer_squad.owner == dead_squad.owner:
            return False
        if not self._could_offer(dead_squad):
            return False
        if not self.stratagem_controller.can_use(dead_squad.owner, self._stratagem, [dead_squad]):
            return False

        def buy(dead=dead_squad, killer=killer_squad):
            # The killer is bound HERE, in the option's own closure, and only
            # written to _pending as the purchase goes through. Two units wiped
            # in one sweep queue two prompts, and a single shared slot written
            # at request() time had the second overwrite the first - so the
            # first answer marked the wrong enemy.
            self._pending = (dead, killer)
            used = self.stratagem_controller.use(dead.owner, self._stratagem, [dead])
            if not used:
                self._pending = None
            return used

        self.decision_manager.request(
            dead_squad.owner,
            f"{PINPOINT_NAME} ({PINPOINT_CP} CP): {dead_squad.name} has been destroyed by "
            f"{killer_squad.name} - mark it for re-rolled Hit rolls for the rest of the "
            "battle?",
            [(f"Use ({PINPOINT_CP} CP)", buy),
             ("Decline", self._clear_pending)],
            is_stratagem=True,
        )
        return True

    def _could_offer(self, dead_squad):
        """Everything about the DEAD unit that has to hold, with no killer yet."""
        if dead_squad is None:
            return False
        if not tau_detachments.has_detachment(dead_squad.owner, montka.SETTING):
            return False
        if not is_eligible_avenger(dead_squad):
            return False
        if dead_squad.owner in self.auto_players or self.decision_manager is None:
            return False
        return True

    def maybe_offer(self, killer_squad):
        """The other half of notify_unit_destroyed(): called from the hooks that
        fire when an attacking unit has finished its attacks, which is where
        the attacker is known by construction.

        NAMED LIMITATION: a unit wiped by something that is not an attack
        (Deadly Demise, a mortal-wound ability resolving between activations)
        leaves an owed entry that the next attacker to finish in the same phase
        would be blamed for. reset_phase() bounds that to one phase; nothing in
        this engine records who caused a given wound, so there is no narrower
        answer available here.
        """
        if killer_squad is None or not self._owed:
            return False
        owed, self._owed = self._owed, []
        offered = False
        for dead_squad in owed:
            if killer_squad.owner == dead_squad.owner:
                continue
            if self._offer(dead_squad, killer_squad):
                offered = True
        return offered

    def reset_phase(self):
        """An owed death does not outlive the phase it happened in."""
        self._owed = []

    def _clear_pending(self):
        self._pending = None
        return True

    def _mark(self, controller, player, targets):
        pending, self._pending = self._pending, None
        if pending is None:
            return
        _dead, killer = pending
        self._marks.setdefault(player, set()).add(killer)
        if self.game_log is not None:
            self.game_log.add(
                f"{PINPOINT_NAME}: {player}'s T'AU EMPIRE units (excluding KROOT) can "
                f"re-roll Hit rolls against {killer.name} for the rest of the battle."
            )
