"""War Horde Stratagem: Breakin' Heads (1CP).

RULE (verbatim, rules/orks/detachments/War Horde.md):
  WHEN:   Any phase, when a friendly attached ORKS INFANTRY unit becomes
          battle-shocked.
  TARGET: That ORKS INFANTRY unit. You can target that unit with this
          stratagem even though it is battle-shocked.
  EFFECT: Roll one D3:
          - Your unit suffers a number of mortal wounds equal to the result.
          - Your unit is no longer battle-shocked.

"BECOMES BATTLE-SHOCKED" IS A MOMENT, and game/battle_shock.py has one door for
it: set_battle_shocked() calls every became-battle-shocked listener on the
transition, whatever caused it (a failed test, Elemental Ensnarement, a Combat or
Emergency Disembark). This controller is one of those listeners.

THE OFFER IS DEFERRED. The door is opened from inside another rule's resolution
(the failed test's own dice acknowledgement, a transport's disembark), and
DiceManager holds one roll. So the listener only QUEUES the unit, and main.py
calls offer_pending() once per frame, which waits while dice or a decision are
open. A unit that is no longer battle-shocked or no longer eligible by then is
dropped.

BOTH BULLETS, in the printed order: the D3 is a visible roll, the mortal wounds
are allocated by the unit's OWN player (rule 06.02 - it is their unit taking
them), and the unit stops being battle-shocked once that allocation is done.

"ATTACHED" is attached_units.is_attached_unit() - a unit formed by rule 19.01's
merge - and "ORKS INFANTRY" is rule 19.03's pooled keyword.

A MortalWoundAllocationSession this module opens, it can drain:
pending_damage_choice, choose_damage_model() and the Feel No Pain leg ahead of
the step checks (test_event_chain_wiring.py section 17).

THE AI (user decision; auto_players plus an injected verdict, no API call): buy
it for a unit with at least BREAKIN_HEADS_MIN_WOUNDS wounds left that is within
range of an objective or within BREAKIN_HEADS_ENEMY_RANGE_IN of an enemy.
"""

from game import ai_mode, attached_units, war_horde
from game.damage_resolution import MortalWoundAllocationSession
from game.stratagems import Stratagem

BREAKIN_HEADS_NAME = "Breakin' Heads"
BREAKIN_HEADS_CP = 1
#: The AI's rule: a unit worth 1 CP and D3 mortal wounds.
BREAKIN_HEADS_MIN_WOUNDS = 6
BREAKIN_HEADS_ENEMY_RANGE_IN = 9.0

AWAITING_D3 = "awaiting_d3"


def _alive(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def is_eligible_unit(squad):
    """The WHEN's unit, minus "becomes battle-shocked": a living, attached ORKS
    INFANTRY unit whose owner fields War Horde."""
    if squad is None or not _alive(squad):
        return False
    if not war_horde.fields_war_horde(getattr(squad, "owner", None)):
        return False
    if not war_horde.is_orks_unit(squad):
        return False
    if not attached_units.is_attached_unit(squad):
        return False
    return attached_units.unit_has_keyword(squad, lambda m: getattr(m.profile, "infantry", False))


def remaining_wounds(squad):
    return sum(max(0, m.current_wounds or 0) for m in _alive(squad))


def ai_verdict(squad, all_tokens=(), objectives=()):
    """The AI's rule - see the module docstring. Pure board geometry, so it lives
    here and main.py injects it; game/ never imports ai/."""
    from game.objectives import is_within_range_of_objective
    if squad is None or remaining_wounds(squad) < BREAKIN_HEADS_MIN_WOUNDS:
        return False
    if objectives and is_within_range_of_objective(squad, objectives):
        return True
    enemies = {t.squad for t in all_tokens or ()
               if t.squad is not None and t.squad.owner != squad.owner and not t.is_dead()}
    return any(squad.min_distance_to(e) <= BREAKIN_HEADS_ENEMY_RANGE_IN for e in enemies)


class BreakinHeadsController:
    def __init__(self, stratagem_controller, dice_manager=None, decision_manager=None,
                 turn_tracker=None, game_log=None, auto_players=(), verdict=None):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        # verdict(squad) -> bool: the AI's answer. None means "always".
        self.verdict = verdict
        self._stratagem = Stratagem(BREAKIN_HEADS_NAME, BREAKIN_HEADS_CP, self._effect,
                                    allow_battle_shocked_target=True)
        self._queue = []
        self._squad = None
        self._step = None
        self.mortal_wound_session = None

    # ------------------------------------------------------------ plumbing
    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)

    @property
    def is_busy(self):
        return self._step is not None or self.mortal_wound_session is not None

    @property
    def queued(self):
        return list(self._queue)

    # ------------------------------------------------------------ the moment
    def on_became_battle_shocked(self, squad, source=None):
        """game/battle_shock.py's listener: queue, never offer from here."""
        if is_eligible_unit(squad) and squad not in self._queue:
            self._queue.append(squad)

    def can_use(self, squad):
        if squad is None or not getattr(squad, "battle_shocked", False):
            return False
        if not is_eligible_unit(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def offer_pending(self):
        """Raise the next queued offer while nothing else is open. Returns True
        if something was offered or bought."""
        if self.is_busy:
            return False
        if self.dice_manager is not None and getattr(self.dice_manager, "pending_values", None) is not None:
            return False
        if self.decision_manager is not None and self.decision_manager.is_pending:
            return False
        while self._queue:
            squad = self._queue.pop(0)
            if not self.can_use(squad):
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                if self.verdict is not None and not self.verdict(squad):
                    continue
                return self.use(squad)
            self.decision_manager.request(
                squad.owner,
                f"{squad.name} became battle-shocked - {BREAKIN_HEADS_NAME} "
                f"({BREAKIN_HEADS_CP} CP)? It suffers D3 mortal wounds and is no longer "
                f"battle-shocked.",
                [(f"Use {BREAKIN_HEADS_NAME} ({BREAKIN_HEADS_CP} CP)", lambda s=squad: self.use(s)),
                 ("Decline", None)],
                is_stratagem=True)
            return True
        return False

    def use(self, squad):
        if self.is_busy or not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _effect(self, controller, player, targets):
        squad = next(iter(targets or ()), None)
        if squad is None:
            return False
        self._squad = squad
        self._log(f"{BREAKIN_HEADS_NAME}: heads are broken in {squad.name}.")
        if self.dice_manager is None:
            from game import dice
            self._inflict(dice.random.randint(1, 3))
            return True
        self._step = AWAITING_D3
        self.dice_manager.roll(
            count=1, sides=3, label=f"{BREAKIN_HEADS_NAME}: D3 mortal wounds",
            target_name=squad.name, target_squad=squad, rolled_for=squad,
        )
        return True

    # ------------------------------------------------------------ resolution
    def on_dice_acknowledged(self):
        if self.dice_manager is None:
            return False
        # Rule 24.12: this acknowledgement may be Feel No Pain's dice step
        # inside the allocation - drained BEFORE the step check below, or the
        # session parks for ever (test_event_chain_wiring.py section 17).
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_mortal_wounds_done()
            return True
        if self._step == AWAITING_D3:
            self._step = None
            rolled = (self.dice_manager.last_values or [1])[0]
            self._inflict(rolled)
            return True
        return False

    def _inflict(self, wounds):
        squad = self._squad
        if squad is None:
            return
        self._log(f"{BREAKIN_HEADS_NAME}: {squad.name} suffers {wounds} mortal wound(s).")
        if self.turn_tracker is not None:
            # Rule 06.02: the unit taking the wounds is the Ork player's own.
            self.turn_tracker.set_active(squad.owner)
        self.mortal_wound_session = MortalWoundAllocationSession(
            squad, wounds, dice_manager=self.dice_manager, log=self._log,
        )
        self._check_mortal_wounds_done()

    @property
    def pending_damage_choice(self):
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_mortal_wounds_done()

    def _check_mortal_wounds_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None
        self._finish()

    def _finish(self):
        """The second bullet: the unit is no longer battle-shocked."""
        squad, self._squad = self._squad, None
        if self.turn_tracker is not None and getattr(self.turn_tracker, "turn_owner", None) is not None:
            self.turn_tracker.set_active(self.turn_tracker.turn_owner)
        if squad is not None:
            squad.battle_shocked = False
            self._log(f"{BREAKIN_HEADS_NAME}: {squad.name} is no longer battle-shocked.")
