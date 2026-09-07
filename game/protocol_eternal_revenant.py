"""Awakened Dynasty Stratagem: "Protocol of the Eternal Revenant".

RULE (printed, word for word):
  WHEN:   "Any phase."
  TARGET: "One NECRONS INFANTRY CHARACTER model from your army that was just
           destroyed."
  EFFECT: "At the end of the phase, set up the destroyed model on the
           battlefield, unengaged and as close as possible to where it was
           destroyed. That model is not part of an attached unit and its unit
           has a starting strength of 1. That model has half of its starting
           number of wounds remaining."

THIS EXISTS BECAUSE THE ARMY RULE REFUSES TO. Core rule 02.02.04 revives
destroyed models "excluding CHARACTER models", so Reanimation Protocols can
never bring an Overlord back - and this is the only thing in the detachment
that can. Worth stating, because the two rules read as though they overlap and
they deliberately do not.

STRUCTURALLY IT IS FUEGAN'S UNQUENCHABLE RESOLVE (game/unquenchable_resolve.py):
notified from the per-frame death sweep, resolved at the phase boundary, placed
by walking formation_layout.ring_candidates() outwards from where the model
fell, with the Engagement Range test that SetupController.position_valid()
explicitly does not cover. All of that is shared code now - game/model_return.py -
so what is actually different here is only what the printed text makes
different:

  * "at the END OF THE PHASE" rather than at the moment of death, which is the
    same timing Fuegan uses and for the same reason (the death sweep runs once
    per frame; every trigger before it still sees corpses).
  * "HALF of its starting number of wounds", not full - which is exactly the
    `wounds=` parameter model_return.set_up_model() grew for this and for
    Reanimation Protocols.
  * "its unit has a STARTING STRENGTH OF 1" and "is NOT part of an attached
    unit" - so a character who died leading a squad comes back as his own
    one-model unit rather than rejoining it. Fuegan does the opposite (his text
    says nothing about leaving), which is why that difference is spelled out in
    both modules rather than assumed.
  * it costs a CP and is optional, so unlike Fuegan there IS somebody to ask.

"EACH MODEL CAN ONLY BE TARGETED WITH THIS ONCE PER BATTLE" is not in the text
quoted above but is the standard once-per-model limit this Stratagem is printed
with; the ledger is keyed on id(model) exactly as Fuegan's is.
"""

import math

from game import ai_mode, awakened_dynasty, formation_layout, model_return
from game.stratagems import Stratagem

ETERNAL_REVENANT_CP_COST = 1
ETERNAL_REVENANT_NAME = "Protocol of the Eternal Revenant"
#: Generous, for the same reason Fuegan's is: the alternative to finding a spot
#: is losing the model, and this runs at most once per character per battle.
_SEARCH_RINGS = 24


def is_eligible_model(model):
    """"One NECRONS INFANTRY CHARACTER model from your army"."""
    profile = getattr(model, "profile", None)
    if profile is None:
        return False
    if not (getattr(profile, "infantry", False) and getattr(profile, "character", False)):
        return False
    squad = getattr(model, "squad", None)
    return squad is not None and awakened_dynasty.stratagem_target_ok(squad)


class EternalRevenantController:
    """Fed destroyed models as they are swept, resolved at every phase
    boundary - "any phase"."""

    def __init__(self, stratagem_controller, decision_manager=None, game_log=None,
                 game_state=None, position_valid=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.position_valid = position_valid
        self.auto_players = ai_mode.players(auto_players)
        self._pending = []   # models destroyed this phase that could still be bought back
        self._used = set()   # id(model) - once per battle, per model

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    def is_pending(self):
        return bool(self._pending)

    def notify_destroyed(self, models):
        """Called with whatever GameState.remove_dead_models() just swept.

        Filtering HERE rather than at the phase boundary keeps the ledger
        honest about when the model died - the same reasoning Fuegan's
        controller records."""
        for model in models or ():
            if not is_eligible_model(model) or id(model) in self._used:
                continue
            if model in self._pending:
                continue
            self._pending.append(model)

    def can_use(self, model):
        if model is None or id(model) in self._used:
            return False
        squad = getattr(model, "squad", None)
        if squad is None:
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem_for(model), [squad])

    def _stratagem_for(self, model):
        """A fresh Stratagem per resolution so its effect closes over WHICH
        model is coming back - the framework passes targets as units, and the
        unit is not enough here."""
        return Stratagem(
            name=ETERNAL_REVENANT_NAME, cp_cost=ETERNAL_REVENANT_CP_COST,
            effect=lambda controller, player, targets, m=model: self._set_up(m),
            allow_repeat_target=True,
        )

    def resolve_end_of_phase(self):
        """"At the end of the phase". Returns the models actually set back up."""
        returned = []
        pending, self._pending = self._pending, []
        for model in pending:
            if not self.can_use(model):
                continue
            owner = model.squad.owner
            if owner in self.auto_players:
                # Deterministic: a NECRONS INFANTRY CHARACTER is always worth
                # 1 CP, so there is nothing to weigh. The only question the AI
                # could get wrong is affordability, and can_use() answers it.
                if self.stratagem_controller.use(owner, self._stratagem_for(model), [model.squad]):
                    self._used.add(id(model))
                    returned.append(model)
                continue
            if self.decision_manager is None:
                continue
            self.decision_manager.request(
                owner,
                f"{model.profile.name} was destroyed - use {ETERNAL_REVENANT_NAME}? "
                f"({ETERNAL_REVENANT_CP_COST} CP, returns on half wounds)",
                [(f"Use {ETERNAL_REVENANT_NAME}",
                  (lambda m=model: self._buy(m))), ("Decline", None)],
                is_stratagem=True,
            )
        return returned

    def _buy(self, model):
        if not self.can_use(model):
            return False
        squad = model.squad
        if not self.stratagem_controller.use(squad.owner, self._stratagem_for(model), [squad]):
            return False
        self._used.add(id(model))
        return True

    def _set_up(self, model):
        """"set up ... unengaged and as close as possible to where it was
        destroyed", on half wounds, as its own one-model unit."""
        spot = self._spot_for(model)
        if spot is None:
            self._log(f"{ETERNAL_REVENANT_NAME}: no legal spot was found near where "
                      f"{model.profile.name} fell - he does not return.")
            return
        half = max(1, model.profile.wounds // 2)   # "half of its starting number of wounds"
        model_return.set_up_model(model, spot, wounds=half, game_state=self.game_state)
        squad = model.squad
        if squad is not None:
            # "its unit has a starting strength of 1" - and it is no longer an
            # attached unit, so the merge that 19.01 performed is undone for
            # him. He is the only model of that unit now either way.
            squad.starting_model_count = 1
        self._log(f"{ETERNAL_REVENANT_NAME}: {model.profile.name} is set back up at "
                  f"({spot[0]:.1f}, {spot[1]:.1f}) with {half} wound(s) remaining.")

    def _spot_for(self, model):
        enemies = model_return.enemy_tokens(model, self._tokens())
        step = max(model.radius_in * 2, 0.5)
        for x_in, y_in in formation_layout.ring_candidates(
                model.x_in, model.y_in, step, -math.pi / 2, rings=_SEARCH_RINGS):
            if self.position_valid is not None and not self.position_valid(model, x_in, y_in):
                continue
            if not model_return.clear_of_engagement(model, x_in, y_in, enemies):
                continue
            return (x_in, y_in)
        return None
