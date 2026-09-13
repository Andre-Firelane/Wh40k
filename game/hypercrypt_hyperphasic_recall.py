"""Hypercrypt Legion Stratagem: Hyperphasic Recall (2CP).

RULE (verbatim, rules/necrons/detachments/Hypercrypt Legion.md):
  WHEN:   Your opponent's Shooting phase or the Fight phase, just after an enemy
          unit has shot or fought.
  TARGET: One NECRONS INFANTRY unit from your army that had one or more of its
          models destroyed as a result of the attacking unit's attacks and one
          friendly MONOLITH model.
  EFFECT: Remove your INFANTRY unit from the battlefield and then set it back up
          anywhere on the battlefield that is wholly within 6" of your MONOLITH
          model and not within Engagement Range of one or more enemy units.

THE MOMENT is the after-activation hooks main.py already feeds Undying Legions,
Curse of the Cryptek and the Repair Barge from - "just after it has shot or
fought" - where the attacker arrives as an argument.

"HAD ONE OR MORE OF ITS MODELS DESTROYED AS A RESULT OF THE ATTACKING UNIT'S
ATTACKS" is a count per activation, and each attack controller keeps it:
ShootingController.models_lost_this_activation() and its Fight-phase mirror
(FightController.models_lost_this_activation(), added with this detachment).
The hook hands the right one in, so this module never guesses which phase's
ledger applies.

"NECRONS INFANTRY" is game/eternity_gate.py's is_eligible_passenger() - the same
two keywords the Monolith's own gate asks, INFANTRY read of every living model.
"ONE FRIENDLY MONOLITH MODEL" is the datasheet keyword, asked per model of the
component it came from (attached_units.model_has_datasheet_keyword()).

"WHOLLY WITHIN 6" OF YOUR MONOLITH MODEL" is measured base to base: every part
of the placed base within 6" of the Monolith's base, i.e. centres + the placed
radius - the Monolith's radius <= 6". Plain "within" would subtract both radii,
and it is the reading a probe checks this module does NOT take.

THE SET-UP IS THE ENGINE'S ONE PLACEMENT FLOW (SetupController.start_setup()),
with a per-position validator carrying both printed clauses - so the overlay
paints them, the drag clamp holds to them, and Confirm adds the coherency and
Engagement Range checks every Set Up has. A human starts from the engine's own
proposal and drags from there; an owner in auto_players lands on it outright.
Cancelling puts the unit back where it stood (rule 03.02's "return it to its
original position") - the CP stays spent, the convention every Stratagem here
follows.

WHY THE SET-UP WAITS FOR THE DEATH SWEEP. The hooks fire inside the frame's event
handling, while the models this attack just destroyed are still in squad.models
(game_state.remove_dead_models() runs once per frame, afterwards - error class
12). Squad.check_coherency() and its siblings do not filter corpses, so a Confirm
at that instant would judge the unit by models lying where they fell. A human
answers the prompt frames later, after the sweep; an AI owner's answer is
therefore DEFERRED, and main.py calls resolve_deferred() right after the sweep.
The OFFER does not wait: it is decided on the living models alone.

NEVER OFFERED WHEN IT BUYS NOTHING: no candidate unit, no living MONOLITH on the
battlefield, or no legal placement anywhere wholly within 6" of one - each makes
the EFFECT impossible, and 2CP would buy a refusal.

THE AI (injected `ai_verdict`, ai/agent_driver.py hyperphasic_recall_verdict())
buys it for a unit whose expected incoming wounds this turn reach its remaining
wounds - a unit about to be wiped out is moved to the Monolith.
"""

import math

from game import ai_mode, attached_units, eternity_gate, formation_layout, necron_detachments
from game import unit_choice_offer
from game.squad import COHERENCY_RANGE_IN, ENGAGEMENT_RANGE_IN
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

HYPERPHASIC_RECALL_NAME = "Hyperphasic Recall"
HYPERPHASIC_RECALL_CP = 2
HYPERPHASIC_RECALL_RANGE_IN = 6.0
MONOLITH_KEYWORD = "MONOLITH"
SETTING = "HYPERCRYPT_LEGION_PLAYERS"

#: How far from the Monolith's base the proposal's drop points sit, and how
#: many directions around it are tried - a bounded search, not a solver.
PROPOSAL_RING_OFFSETS_IN = (1.0, 2.5, 4.0)
PROPOSAL_DIRECTIONS = 16
_EPSILON = 1e-9


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def _dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def wholly_within_monolith(radius_in, x_in, y_in, monolith_model):
    """Every part of a base of `radius_in` at (x, y) within 6" of the Monolith's base."""
    gap = _dist(x_in, y_in, monolith_model.x_in, monolith_model.y_in)
    return gap + radius_in - monolith_model.radius_in <= HYPERPHASIC_RECALL_RANGE_IN + _EPSILON


def is_necrons_infantry_unit(squad):
    return eternity_gate.is_eligible_passenger(squad)


def monolith_models(squad):
    return [m for m in _living(squad)
            if attached_units.model_has_datasheet_keyword(squad, m, MONOLITH_KEYWORD)]


class _UnitView:
    """A unit with only some of its models - the living ones - for the Squad
    checks, which do not filter corpses. Everything else reads through."""

    def __init__(self, squad, models):
        self._squad = squad
        self.models = list(models)

    def __getattr__(self, name):
        return getattr(self._squad, name)


class HyperphasicRecallController:
    """Offered from main.py's two after-activation hooks."""

    def __init__(self, stratagem_controller, setup_controller=None, turn_tracker=None,
                 game_state=None, decision_manager=None, game_log=None, auto_players=(),
                 ai_verdict=None):
        self.stratagem_controller = stratagem_controller
        self.setup_controller = setup_controller
        self.turn_tracker = turn_tracker
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        #: ai_verdict(squad) -> bool, injected by main.py (game/ must not import ai/).
        self.ai_verdict = ai_verdict
        self._asked = set()          # (player, id(attacker)) offered this phase
        self._auto_due = []          # (player, [candidate squads]) awaiting the sweep
        self._placement_due = None   # (squad, monolith model) bought, awaiting the sweep
        self._pending = None         # (squad, monolith model) for the purchase in flight
        self._restore = {}           # id(squad) -> [(model, x, y)] for a cancelled set-up
        self._stratagem = Stratagem(name=HYPERPHASIC_RECALL_NAME, cp_cost=HYPERPHASIC_RECALL_CP,
                                    effect=self._effect)

    # ------------------------------------------------------------- plumbing
    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return getattr(self.game_state, "tokens", None) or []

    def reset_phase(self):
        self._asked = set()

    # ------------------------------------------------------------- the target
    def _phase_allows(self, attacker):
        tt = self.turn_tracker
        if tt is None:
            return False
        if tt.phase == PHASE_FIGHT:
            return True
        return tt.phase == PHASE_SHOOTING and tt.turn_owner == attacker.owner

    def monoliths_for(self, player):
        """Living friendly MONOLITH models on the battlefield."""
        tokens = self._tokens()
        seen, out = set(), []
        for token in tokens:
            squad = getattr(token, "squad", None)
            if squad is None or squad.owner != player or id(squad) in seen:
                continue
            seen.add(id(squad))
            out.extend(m for m in monolith_models(squad) if m in tokens)
        return sorted(out, key=lambda m: (m.squad.name, m.id if hasattr(m, "id") else 0))

    def is_candidate(self, squad, attacker, lost):
        if squad is None or attacker is None or squad.owner == attacker.owner:
            return False
        if not necron_detachments.has_detachment(squad.owner, SETTING):
            return False
        if getattr(squad, "embarked_in", None) is not None:
            return False
        living = _living(squad)
        tokens = self._tokens()
        if not living or not any(m in tokens for m in living):
            return False
        if not is_necrons_infantry_unit(squad):
            return False
        return bool(lost is not None and lost(squad) > 0)

    # ------------------------------------------------------------ the placement
    def validator(self, squad, monolith_model):
        """Per position: the Set Up checks, wholly within 6" of the Monolith, and
        clear of every enemy model's Engagement Range."""
        setup = self.setup_controller

        def _valid(token, x_in, y_in):
            if not wholly_within_monolith(token.radius_in, x_in, y_in, monolith_model):
                return False
            for other in self._tokens():
                osq = getattr(other, "squad", None)
                if osq is None or osq.owner == squad.owner or other.is_dead():
                    continue
                if (_dist(x_in, y_in, other.x_in, other.y_in) - token.radius_in - other.radius_in
                        <= ENGAGEMENT_RANGE_IN):
                    return False
            if setup is not None and not setup.position_valid(token, x_in, y_in, squad=squad):
                return False
            return True

        return _valid

    def placement_errors(self, models, monolith_model):
        """The printed half of the Confirm, per model."""
        if all(wholly_within_monolith(m.radius_in, m.x_in, m.y_in, monolith_model) for m in models):
            return []
        return [f'Every model must be set up wholly within {HYPERPHASIC_RECALL_RANGE_IN:.0f}" of '
                f"{monolith_model.squad.name} ({HYPERPHASIC_RECALL_NAME})."]

    def _pack(self, models, origin, base_angle, valid):
        step = max(formation_layout.MODEL_GAP_IN, 2 * min(m.radius_in for m in models) + 0.1)
        candidates = formation_layout.ring_candidates(origin[0], origin[1], step, base_angle)
        placed = []
        for model in sorted(models, key=lambda m: -m.radius_in):
            spot = None
            for x_in, y_in in candidates:
                if any(_dist(x_in, y_in, px, py) < model.radius_in + pm.radius_in + 0.05
                       for pm, (px, py) in placed):
                    continue
                if placed and not any(
                        _dist(x_in, y_in, px, py) - model.radius_in - pm.radius_in <= COHERENCY_RANGE_IN
                        for pm, (px, py) in placed):
                    continue
                if not valid(model, x_in, y_in):
                    continue
                spot = (x_in, y_in)
                break
            if spot is None:
                return None
            placed.append((model, spot))
        where = {id(m): spot for m, spot in placed}
        return [where[id(m)] for m in models]

    def _trial_errors(self, squad, models, positions, monolith_model):
        """The Confirm's own checks with the models moved onto `positions` -
        judged on the living models only, and restored afterwards."""
        view = _UnitView(squad, models)
        saved = [(m, m.x_in, m.y_in) for m in models]
        others = [t for t in self._tokens() if t not in models and not t.is_dead()]
        obstacles = getattr(self.setup_controller, "obstacles", None) or []
        klass = type(squad)
        try:
            for model, (x_in, y_in) in zip(models, positions):
                model.x_in, model.y_in = x_in, y_in
            errors = list(klass.check_coherency(view))
            errors += klass.check_terrain(view, obstacles)
            errors += klass.check_model_overlap(view, others + list(models))
            if klass.is_engaged(view, others):
                errors.append("Your unit must be set up unengaged (rule 03.02).")
            errors += self.placement_errors(models, monolith_model)
            return errors
        finally:
            for model, x_in, y_in in saved:
                model.x_in, model.y_in = x_in, y_in

    def proposed_positions(self, squad, monolith_model, models=None):
        """A legal set-up wholly within 6" of the Monolith, or None. Drop points
        ring the Monolith, safest (furthest from the enemy) first."""
        models = list(models if models is not None else _living(squad))
        if not models or monolith_model is None:
            return None
        valid = self.validator(squad, monolith_model)
        enemies = [t for t in self._tokens()
                   if getattr(t, "squad", None) is not None and t.squad.owner != squad.owner
                   and not t.is_dead()]
        origins = []
        for ring, offset in enumerate(PROPOSAL_RING_OFFSETS_IN):
            reach = monolith_model.radius_in + offset
            for k in range(PROPOSAL_DIRECTIONS):
                angle = 2 * math.pi * k / PROPOSAL_DIRECTIONS
                ox = monolith_model.x_in + reach * math.cos(angle)
                oy = monolith_model.y_in + reach * math.sin(angle)
                safety = min((_dist(ox, oy, e.x_in, e.y_in) for e in enemies), default=float("inf"))
                origins.append((-safety, ring, k, (ox, oy)))
        for _safety, _ring, _k, origin in sorted(origins):
            base_angle = math.atan2(monolith_model.y_in - origin[1], monolith_model.x_in - origin[0])
            positions = self._pack(models, origin, base_angle, valid)
            if positions is None:
                continue
            if not self._trial_errors(squad, models, positions, monolith_model):
                return positions
        return None

    def monoliths_with_room(self, squad):
        return [m for m in self.monoliths_for(squad.owner)
                if self.proposed_positions(squad, m) is not None]

    # ------------------------------------------------------------ the offer
    def maybe_offer(self, attacker, lost):
        """From the after-activation hooks: `attacker` just shot or fought, and
        `lost(squad)` is that phase's models_lost_this_activation()."""
        if attacker is None or lost is None or self.stratagem_controller is None:
            return False
        if not self._phase_allows(attacker):
            return False
        by_player = {}
        seen = set()
        for token in self._tokens():
            squad = getattr(token, "squad", None)
            if squad is None or id(squad) in seen:
                continue
            seen.add(id(squad))
            if self.is_candidate(squad, attacker, lost):
                by_player.setdefault(squad.owner, []).append(squad)
        offered = False
        for player in sorted(by_player, key=str):
            key = (player, id(attacker))
            if key in self._asked:
                continue
            candidates = sorted(by_player[player], key=lambda s: s.name)
            # monoliths_with_room() reads monoliths_for(), so "no MONOLITH on the
            # battlefield" empties this list by itself - a separate early-out here
            # was measured redundant (its A/B probe could not bite).
            candidates = [s for s in candidates if self.monoliths_with_room(s)]
            if not candidates:
                continue
            if not self.stratagem_controller.can_use(player, self._stratagem, [candidates[0]]):
                continue
            self._asked.add(key)
            if player in self.auto_players:
                self._auto_due.append((player, candidates))
                continue
            if unit_choice_offer.offer_one_of(
                    self.decision_manager, player, candidates,
                    f"{HYPERPHASIC_RECALL_NAME} ({HYPERPHASIC_RECALL_CP} CP): {attacker.name} destroyed "
                    "models of your NECRONS INFANTRY - set which unit back up wholly within "
                    f'{HYPERPHASIC_RECALL_RANGE_IN:.0f}" of a MONOLITH?',
                    self._choose_monolith, is_stratagem=True):
                offered = True
        return offered

    def _choose_monolith(self, squad):
        monoliths = self.monoliths_with_room(squad)
        if not monoliths:
            self._log(f"{HYPERPHASIC_RECALL_NAME}: no MONOLITH has room for {squad.name} any more.")
            return False
        if len(monoliths) == 1 or self.decision_manager is None:
            return self._buy(squad, monoliths[0])
        self.decision_manager.request(
            squad.owner,
            f"{HYPERPHASIC_RECALL_NAME}: set {squad.name} back up beside which MONOLITH?",
            [(m.squad.name, (lambda m=m: self._buy(squad, m)), m.squad) for m in monoliths]
            + [("Cancel", lambda: None)],
            is_stratagem=True,
        )
        return True

    def _buy(self, squad, monolith_model):
        self._pending = (squad, monolith_model)
        used = self.stratagem_controller.use(squad.owner, self._stratagem,
                                             [squad, monolith_model.squad])
        if not used:
            self._pending = None
        return used

    def _effect(self, controller, player, targets):
        pending, self._pending = self._pending, None
        if pending is None:
            return
        self._placement_due = pending
        self.resolve_deferred()

    # -------------------------------------------------------- after the sweep
    def resolve_deferred(self):
        """Called by main.py every frame right after the death sweep. Opens a
        bought set-up, and answers an AI owner's deferred offer."""
        acted = False
        if self._placement_due is not None:
            squad, monolith_model = self._placement_due
            if any(m.is_dead() for m in getattr(squad, "models", ()) or ()):
                return False        # the sweep has not taken the corpses yet
            self._placement_due = None
            acted = self._set_back_up(squad, monolith_model) or acted
        while self._auto_due:
            player, candidates = self._auto_due.pop(0)
            if any(m.is_dead() for s in candidates for m in s.models):
                self._auto_due.insert(0, (player, candidates))
                return acted
            acted = self._answer_for_ai(player, candidates) or acted
        return acted

    def _answer_for_ai(self, player, candidates):
        if self.ai_verdict is None:
            return False
        for squad in sorted(candidates, key=lambda s: (-(s.points or 0), s.name)):
            if not _living(squad) or not self.ai_verdict(squad):
                continue
            monoliths = self.monoliths_with_room(squad)
            if not monoliths:
                continue
            if not self.stratagem_controller.can_use(player, self._stratagem,
                                                     [squad, monoliths[0].squad]):
                continue
            return self._buy(squad, monoliths[0])
        return False

    def _set_back_up(self, squad, monolith_model):
        setup = self.setup_controller
        models = _living(squad)
        if not models or setup is None or not setup.can_start_setup(squad):
            self._log(f"{HYPERPHASIC_RECALL_NAME}: {squad.name} could not be set back up right now.")
            return False
        positions = self.proposed_positions(squad, monolith_model, models)
        tokens = self._tokens()
        self._restore[id(squad)] = [(m, m.x_in, m.y_in) for m in models]
        # "Remove your INFANTRY unit from the battlefield".
        for model in models:
            if model in tokens:
                tokens.remove(model)
        origin = positions[0] if positions else (monolith_model.x_in, monolith_model.y_in)
        setup.start_setup(
            squad, origin[0], origin[1],
            on_cancel=self._on_cancel,
            extra_check=lambda s, mono=monolith_model: self.placement_errors(_living(s), mono),
            placement_validator=self.validator(squad, monolith_model),
            positions=positions,
        )
        self._log(f"{HYPERPHASIC_RECALL_NAME}: {squad.name} is removed from the battlefield and set "
                  f'back up wholly within {HYPERPHASIC_RECALL_RANGE_IN:.0f}" of {monolith_model.squad.name}.')
        if squad.owner not in self.auto_players:
            return True
        if positions is not None:
            for model, (x_in, y_in) in zip(models, positions):
                model.x_in, model.y_in = x_in, y_in
        setup.confirm_setup()
        if setup.setting_up_squad is squad:
            setup.cancel_setup()
            return False
        self._restore.pop(id(squad), None)
        return True

    def _on_cancel(self, squad):
        """Rule 03.02: a unit that cannot be set up returns to where it stood."""
        tokens = self._tokens()
        for model, x_in, y_in in self._restore.pop(id(squad), []):
            model.x_in, model.y_in = x_in, y_in
            if model not in tokens:
                tokens.append(model)
        self._log(f"{HYPERPHASIC_RECALL_NAME}: {squad.name} was not set back up and stays where it "
                  "stood.")
