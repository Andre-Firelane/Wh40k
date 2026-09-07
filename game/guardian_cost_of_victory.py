"""Guardian Battlehost Stratagem: Cost of Victory (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Guardian Battlehost.md):
  WHEN:   End of your opponent's Fight phase.
  TARGET: One GUARDIANS unit from your army.
  EFFECT: If your unit is not within Engagement Range of one or more enemy
          units, remove it from the battlefield and place it into Strategic
          Reserves. When doing so, return every destroyed GUARDIANS model to
          your unit.
  RESTRICTIONS: none printed.

BOTH HALVES EXISTED AND HAD NEVER BEEN COMPOSED, which is the whole of the work
here:

  * game/strategic_reserves.py's withdraw_to_reserves() takes a unit off the
    board, clears its ingress lock and re-evaluates objective control - a unit
    that leaves must stop holding what it stood on.
  * game/model_return.py owns the four halves of putting a destroyed model
    back (tokens, Squad.models, off Squad.destroyed_models, real wounds).

THE ORDER IS FORCED, and getting it wrong loses the models silently:
withdraw_to_reserves() only removes what is in squad.models, so the dead have to
come back FIRST and then the whole unit leaves. Reversed, the returned models
would be set up on a board the rest of the unit had already left.

AND THE RETURN NEEDS NO PLACEMENT. model_return.set_up_model() takes a `spot`,
because its five existing callers all put a model back onto the battlefield.
This one does not: the unit is about to be removed anyway, so a coordinate
would be computed, validated against terrain and thrown away one line later.
The models are restored to the SQUAD without a board position - a genuinely new
composition rather than a fifth caller of the existing one, and the reason this
Stratagem needed more than an import.

"EVERY DESTROYED GUARDIANS MODEL" - not every destroyed model. Under rule 19.01
a Warlock or Farseer leading the unit is merged into Squad.models, so its corpse
sits on the same destroyed list; the printed text brings back the bodyguards
only. Read from the component provenance attach() records, the same source
Yvraine's Word of the Phoenix uses for its own "BODYGUARD models" clause.

THE TIMING IS THE ONE MOST EASILY READ BACKWARDS: "end of your OPPONENT'S Fight
phase", so the offer goes to whoever is NOT the turn owner - the same trap
game/airborne_agility.py and Ride the Wind both write out.

THE AI DECLINES (standing Aeldari instruction): taking a unit off the board is
a whole-army judgement this engine cannot make.
"""

from game import aeldari_detachments, ai_mode, defend_at_all_costs, engagement
from game.stratagems import Stratagem
from game.strategic_reserves import withdraw_to_reserves
from game.phase_window import PhaseWindow

COST_OF_VICTORY_NAME = "Cost of Victory"
COST_OF_VICTORY_CP = 1

COST_OF_VICTORY_KEYWORD = "GUARDIANS"


def eligible_unit(squad):
    if squad is None or not defend_at_all_costs.has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return unit_has_datasheet_keyword(squad, COST_OF_VICTORY_KEYWORD)


def is_engaged(squad, all_tokens=()):
    """"not within Engagement Range of one or more enemy units" - rule 03.04.

    Delegates to game/engagement.py, which is where this sentence now lives:
    it had been written out in three modules independently, and Warhost's two
    withdrawal Stratagems made five. See that module for why the living-model
    filter differs from Squad.is_engaged()."""
    return engagement.is_engaged(squad, all_tokens)


def _bodyguard_model_ids(squad):
    """The models that came from the BODYGUARD component, or None when this
    squad was never merged by attach() - in which case every destroyed model
    is its own.

    Read off AttachedComponent.role, the provenance attach() already keeps,
    rather than re-derived from what the corpses look like."""
    components = getattr(squad, "attached_components", None)
    if not components:
        return None
    ids = set()
    for component in components:
        if getattr(component, "is_leader_or_support", False):
            continue
        ids.update(id(m) for m in (getattr(component, "starting_models", None) or ()))
    return ids or None


def returnable_models(squad):
    """"every destroyed GUARDIANS model" - the bodyguards, not an attached
    character."""
    if squad is None:
        return []
    dead = list(getattr(squad, "destroyed_models", ()) or ())
    if not dead:
        return []
    bodyguards = _bodyguard_model_ids(squad)
    out = []
    for model in dead:
        if bodyguards is None:
            if getattr(model.profile, "leader", False) \
                    or getattr(model.profile, "support", False):
                continue
        elif id(model) not in bodyguards:
            continue
        out.append(model)
    return out


def restore_without_placement(squad, models):
    """Put `models` back into `squad` at full wounds, with NO board position.

    The half game/model_return.py cannot do: set_up_model() takes a spot,
    because its callers put a model back on the battlefield. This unit is about
    to leave the battlefield, so a coordinate would be computed and discarded.
    Everything else is the same four halves - back in Squad.models, off
    Squad.destroyed_models, real wounds - minus the one that does not apply
    (GameState.tokens, which withdraw_to_reserves() would strip again anyway)."""
    restored = 0
    for model in list(models or ()):
        if model in squad.models:
            continue
        model.current_wounds = model.profile.wounds
        squad.models.append(model)
        if model in squad.destroyed_models:
            squad.destroyed_models.remove(model)
        restored += 1
    return restored


class CostOfVictoryController:
    """The end-of-opponent-Fight-phase offer."""

    def __init__(self, stratagem_controller, game_state=None, turn_tracker=None,
                 all_tokens=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        # The end-of-Fight-phase window this controller's own offer opens.
        # NOT a live turn_tracker.phase test - see game/phase_window.py.
        self._window = PhaseWindow()
        self._stratagem = Stratagem(
            name=COST_OF_VICTORY_NAME, cp_cost=COST_OF_VICTORY_CP, effect=self._withdraw,
        )

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.game_state is None:
            return False
        # The window is the one this controller's own offer opened, not a live
        # phase test: the offer runs AFTER advance_phase(), so the clock
        # already reads the next phase. See game/phase_window.py.
        if not self._window.is_open(squad.owner):
            return False
        if not eligible_unit(squad):
            return False
        if squad in (getattr(self.game_state, "reserves", None) or ()):
            return False
        if not any(not m.is_dead() for m in (getattr(squad, "models", ()) or ())):
            return False
        if is_engaged(squad, self.all_tokens):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def reset_phase(self):
        """The window lasts exactly one phase boundary. main.py clears it in
        the per-phase reset block, which runs BEFORE that boundary's offers."""
        self._window.close()

    def offer_at_end_of_fight_phase(self, squads, ending_player):
        """`ending_player` is whose turn the Fight phase belonged to, so the
        offer goes to everyone ELSE - "your OPPONENT'S Fight phase".

        `ending_player` must be main.py's `mover_before`, captured BEFORE
        advance_phase() - turn_tracker.turn_owner has already flipped here.
        There is deliberately no live phase test any more: this runs AFTER
        advance_phase(), so `phase != PHASE_FIGHT` was always true and this
        Stratagem never opened a prompt at all. See game/phase_window.py."""
        # Armed BEFORE the eligibility loop, because can_use() below asks the
        # window: the window IS this offer's own "right moment", and the offer
        # is only ever made at the boundary that owns it. Closed again if
        # nothing was actually put to the player.
        for squad in sorted((s for s in squads if s.owner != ending_player),
                            key=lambda s: (str(s.owner), s.name)):
            self._window.arm(squad.owner)
            if not self.can_use(squad):
                self._window.close()
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                self._window.close()
                return False           # no AI path
            self.decision_manager.request(
                squad.owner,
                "%s (%d CP): pull %s into Strategic Reserves and bring back its "
                "destroyed models?"
                % (COST_OF_VICTORY_NAME, COST_OF_VICTORY_CP, squad.name),
                [("Use (%d CP)" % COST_OF_VICTORY_CP, (lambda s=squad: self.use(s))),
                 ("Decline", lambda: None)],
                is_stratagem=True,
            )
            return True
        return False

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _withdraw(self, controller, player, targets):
        for squad in targets or ():
            # THE ORDER IS FORCED: withdraw_to_reserves() only removes what is
            # in squad.models, so the dead come back FIRST.
            restored = restore_without_placement(squad, returnable_models(squad))
            withdraw_to_reserves(
                self.game_state, squad, log=self.game_log,
                message="%s: %s withdraws into Strategic Reserves with %d "
                        "destroyed model(s) restored."
                        % (COST_OF_VICTORY_NAME, squad.name, restored))
