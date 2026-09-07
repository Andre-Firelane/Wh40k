"""Seer Council's "Isha's Fury" (1CP, Epic Deed).

RULE (printed, word for word):
  WHEN: "Your opponent's Movement phase, just after an enemy unit ends a Normal,
  Advance or Fall Back move"
  TARGET: "One ASURYANI PSYKER model from your army within 9" of that enemy
  unit"
  EFFECT: "Roll six D6: for each 3+, that enemy unit suffers 1 mortal wound."

THE EFFECT IS EXPLOSIVES' SHAPE. Six D6 at 3+, each success one mortal wound,
allocated by the DEFENDER (rule 06.02) - which is what game/explosives.py (15.05)
already does, down to flipping turn_tracker.set_active() to the target's owner
for the allocation and back afterwards. So the roll, the
MortalWoundAllocationSession and the Feel No Pain interleaving are all shapes
that exist; nothing here re-invents them.

THE TRIGGER IS WHAT WAS MISSING. "Just after an enemy unit ends a Normal,
Advance or Fall Back move" had no hook: game/movement.py had on_fall_back_finished
(added for Battle Focus's Opportunity Seized) but nothing for the other two. It
now has on_move_finished(squad, kind), fired at the same point and for the same
reason - after all of confirm_move()'s bookkeeping, because the handler opens a
break point for the opponent and that must not land mid-settle.

Note what does NOT qualify, and that it falls out of the mode rather than being
filtered here: a Charge, Pile-In, Consolidate, Surge, Scout, Battle Focus or
Retro-thrusters move is its own move_mode and never reaches the hook.

"WITHIN 9 INCHES OF THAT ENEMY UNIT" is measured from the psyker MODEL, because
the TARGET clause names a model - centre to centre, like every other "within X
of a model" test here.

"YOUR OPPONENT'S MOVEMENT PHASE" is checked as the phase plus "the mover is not
me", which is also what keeps this from firing on the reacting player's own
moves.
"""

from game.damage_resolution import MortalWoundAllocationSession
from game.turn import PHASE_MOVEMENT
from game.stratagems import Stratagem
from game import strands_of_fate

ISHAS_FURY_CP = 1
ISHAS_FURY_NAME = "Isha's Fury"
ISHAS_FURY_DICE_COUNT = 6
ISHAS_FURY_SUCCESS_THRESHOLD = 3
ISHAS_FURY_PSYKER_RANGE_IN = 9.0


class IshasFuryController:
    """Wired to MovementController.on_move_finished in main.py.

    Human-only in practice like the rest of the Aeldari work, but the offer is an
    ordinary DecisionManager break point, so an AI would resolve it through the
    generic path with nothing extra here."""

    def __init__(self, stratagem_controller=None, dice_manager=None, decision_manager=None,
                 turn_tracker=None, game_log=None, all_tokens=None):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.target_squad = None
        self.acting_squad = None
        self.mortal_wound_session = None
        self._pending_roll = False
        self._stratagem = Stratagem(name=ISHAS_FURY_NAME, cp_cost=ISHAS_FURY_CP, effect=self._effect)
        self._pending_mover = None

    def _log(self, message, **kwargs):
        if self.game_log is not None:
            self.game_log.add(message, **kwargs)

    @property
    def is_busy(self):
        return self._pending_roll or self.mortal_wound_session is not None

    def _psyker_units_in_range(self, mover, player):
        """`player`'s units holding an ASURYANI PSYKER model within 9" of the
        unit that just moved."""
        from game import psychic_guidance
        out = []
        for token in self.all_tokens:
            if token.is_dead() or not getattr(token.profile, "psyker", False):
                continue
            squad = getattr(token, "squad", None)
            if squad is None or squad.owner != player or squad in out:
                continue
            if not psychic_guidance._is_aeldari(squad):
                continue
            for enemy in mover.models:
                if enemy.is_dead():
                    continue
                dx, dy = token.x_in - enemy.x_in, token.y_in - enemy.y_in
                if (dx * dx + dy * dy) ** 0.5 <= ISHAS_FURY_PSYKER_RANGE_IN:
                    out.append(squad)
                    break
        return sorted(out, key=lambda s: s.name)

    def offer_after_move(self, mover, kind=None):
        """Wired to MovementController.on_move_finished. `kind` is one of
        "normal"/"advance"/"fall_back" - all three qualify, so it is only used
        for the prompt text."""
        if self.is_busy or mover is None or self.stratagem_controller is None:
            return False
        if self.turn_tracker is None or self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        reactor = self._opponent_of(mover.owner)
        if reactor is None:
            return False
        # Seer Council only - see game/strands_of_fate.py's has_detachment().
        # The REACTOR is the one who pays, so it is their detachment that
        # matters, not the mover's.
        if not strands_of_fate.has_detachment(reactor):
            return False
        candidates = [s for s in self._psyker_units_in_range(mover, reactor)
                      if self.stratagem_controller.can_use(reactor, self._stratagem, [s])]
        if not candidates:
            return False
        if self.decision_manager is None:
            return False
        moved = {"fall_back": "fell back", "advance": "advanced"}.get(kind, "moved")
        self.decision_manager.request(
            reactor,
            f"Isha's Fury ({ISHAS_FURY_CP} CP): {mover.name} {moved}. Roll six D6 - "
            f"each {ISHAS_FURY_SUCCESS_THRESHOLD}+ inflicts 1 mortal wound on it.",
            [(f"{s.name} ({ISHAS_FURY_CP} CP)", (lambda x=s: self._use(x, mover)), s) for s in candidates]
            + [("Decline", lambda: None)],
        )
        return True

    def _opponent_of(self, player):
        for token in self.all_tokens:
            squad = getattr(token, "squad", None)
            if squad is not None and squad.owner != player:
                return squad.owner
        return None

    def _use(self, acting_squad, mover):
        self._pending_mover = mover
        self.stratagem_controller.use(acting_squad.owner, self._stratagem, [acting_squad])

    def _effect(self, controller, player, targets):
        acting_squad = targets[0]
        mover = self._pending_mover
        self._pending_mover = None
        if mover is None:
            return
        self.acting_squad = acting_squad
        self.target_squad = mover
        self.dice_manager.roll(
            count=ISHAS_FURY_DICE_COUNT, sides=6,
            label=f"Isha's Fury: {acting_squad.name}",
            success_threshold=ISHAS_FURY_SUCCESS_THRESHOLD,
            target_name=mover.name, target_squad=mover,
        )
        self._pending_roll = True

    def on_dice_acknowledged(self):
        if not self._pending_roll or self.dice_manager is None:
            return
        # Rule 24.12 (Feel No Pain): this acknowledgement might be that
        # ability's own dice step rather than the original six D6.
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_done()
            return
        rolls = self.dice_manager.last_values
        hits = sum(1 for r in rolls if r >= ISHAS_FURY_SUCCESS_THRESHOLD)
        self._log(f"Isha's Fury roll {rolls}: {hits} mortal wound(s) to {self.target_squad.name}.")
        if hits <= 0:
            self._finish()
            return
        if self.turn_tracker is not None:
            # Rule 06.02: the DEFENDING player chooses which model takes each
            # mortal wound - the same flip game/explosives.py makes.
            self.turn_tracker.set_active(self.target_squad.owner)
        self.mortal_wound_session = MortalWoundAllocationSession(
            self.target_squad, hits, dice_manager=self.dice_manager, log=self._log,
        )
        self._check_done()

    @property
    def pending_damage_choice(self):
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_done()

    def _check_done(self):
        if self.mortal_wound_session is not None and self.mortal_wound_session.done:
            self.mortal_wound_session = None
            self._finish()

    def _finish(self):
        self._pending_roll = False
        if self.turn_tracker is not None and self.target_squad is not None:
            # Hand the turn back to whoever was moving.
            self.turn_tracker.set_active(self.target_squad.owner)
        self.target_squad = None
        self.acting_squad = None
