"""T'au Empire detachment stratagem: Retaliation Cadre's Fail-Safe Detonator,
as supplied by the user (not a rule from the generic 40k core rulebook, so it
lives in its own module - same reasoning as game/retaliation_cadre.py for that
detachment's Bonded Heroes rule, and its five sibling stratagems in
game/stim_injectors.py, game/arrokon_protocol.py, game/shortened_blade.py,
game/torchstar_gambit.py and game/grav_inhibitor_field.py).

RULE (Fail-Safe Detonator, 2CP, Retaliation Cadre Epic Deed Stratagem):
  WHEN:   Any phase, just after a T'AU EMPIRE BATTLESUIT model from your army
          that has the Deadly Demise ability is destroyed.
  TARGET: That destroyed model's unit. You can use this Stratagem on that unit
          even if that unit was just destroyed.
  EFFECT: Before removing your model from play, do not roll for its Deadly
          Demise ability; instead, you can choose whether the result of that
          roll is a 1 or a 6.

DEADLY DEMISE IS A CONDITION, NOT A BRANCH

This module first read the rule as having a second branch for models WITHOUT
Deadly Demise ("roll one D6 for each unit within 6"; on a 4+ that unit suffers
D3 mortal wounds"), and implemented it. A user report corrected that: the
stratagem was being offered for a destroyed Stealth Battlesuit, which has no
Deadly Demise, and should not have been. Having the ability is a condition of
the WHEN clause, so a model without it never triggers this at all.

That branch and everything it needed has been removed rather than left
unreachable: the one-D6-per-nearby-unit roll, the per-unit D3, the
MortalWoundAllocationSession, the turn_tracker flip that rule 06.02 needed for
it, and the pending_damage_choice/choose_damage_model/is_busy plumbing main.py
routed board clicks and highlights through. What is left is what the rule
actually is - a choice, made once, that replaces one die.

"BEFORE REMOVING YOUR MODEL FROM PLAY"

This engine notices a death in main.py's once-per-frame
GameState.remove_dead_models() loop, which has already taken the token out of
state.tokens and its Squad. That is not a problem for this rule, and the
existing Deadly Demise implementation (24.08) already relies on the same
thing: a removed Token keeps its last x_in/y_in and its .squad reference, so
"that destroyed model's unit" is still answerable, and 24.08 measures its own
6" from the preserved position.

The TARGET clause's second sentence ("even if that unit was just destroyed")
is why nothing here checks that the unit still has models - it usually will
not, since a BATTLESUIT unit is often one or three models.

WHY THIS RESOLVES NOTHING ITSELF

The effect REPLACES rule 24.08's D6 with a chosen value, so this hands the
choice to DeadlyDemiseController.force_roll() and lets 24.08 run exactly as it
always does. That matters for more than tidiness: that controller is what
serialises several deaths in one frame, and what holds a detonation back until
a destroyed TRANSPORT's passengers have made their emergency disembark (24.08's
own ordering clause). Choosing 1 rather than 6 is a real option, not a
formality - it is how you protect your OWN units standing next to the wreck
(24.08's detonation hits every unit within 6", friendly ones included), so both
are offered up front, in one prompt.

SIMPLIFICATION (documented, matching game/retaliation_cadre.py's own note):
this engine has no army-building/detachment-selection flow yet, and
Retaliation Cadre is currently the only detachment that exists - the T'AU
EMPIRE half of the WHEN clause is therefore not checked, exactly as Bonded
Heroes applies unconditionally to any BATTLESUIT model. The BATTLESUIT half
IS checked, and per MODEL rather than per unit: the WHEN clause is about the
destroyed MODEL, so a drone dying out of an otherwise-Battlesuit unit does
not trigger it. Deadly Demise is likewise checked per model, for the same
reason.
"""

from game.deadly_demise import DEADLY_DEMISE_RANGE_IN
from game.stratagems import Stratagem

FAIL_SAFE_CP_COST = 2
FAIL_SAFE_DEMISE_HIGH = 6           # the two values the Deadly Demise roll may be chosen to be
FAIL_SAFE_DEMISE_LOW = 1


def is_battlesuit_model(model):
    """The WHEN clause is about the destroyed MODEL, not its unit - so this is
    deliberately the model's own profile flag rather than rule 19.03's unit-
    wide keyword pooling that the other Retaliation Cadre stratagems use."""
    return bool(model.profile.battlesuit)


def has_deadly_demise(model):
    """The other half of the WHEN clause, per model for the same reason.
    Reported by the user after a destroyed Stealth Battlesuit - which has no
    Deadly Demise - was offered this stratagem."""
    return model.profile.deadly_demise is not None


class FailSafeDetonatorController:
    """WHEN/TARGET bookkeeping and one prompt. Reactive, offered through
    DecisionManager - which is also what would make it AI-resolvable with no
    extra wiring. Resolves nothing itself; see the module docstring."""

    def __init__(self, stratagem_controller, deadly_demise_controller=None,
                 decision_manager=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.deadly_demise_controller = deadly_demise_controller
        self.decision_manager = decision_manager
        self.game_log = game_log
        self._stratagem = Stratagem(
            name="Fail-Safe Detonator", cp_cost=FAIL_SAFE_CP_COST, effect=self._apply,
            # rule 15.01's "not the same unit twice this phase" would otherwise
            # be re-checked against a unit that is usually already destroyed;
            # the TARGET clause explicitly allows that unit, and there is only
            # ever one use per phase anyway (the once-per-stratagem cap).
            allow_repeat_target=True,
        )
        self._dead_model = None
        self._chosen_demise = None
        # Which units have already been asked about this phase. A destroyed
        # unit is not tracked by rule 15.01's targeted_this_phase in any useful
        # way (see allow_repeat_target above), and several models of the same
        # unit routinely die in the same frame - without this, one weapon
        # killing a three-model Battlesuit team would ask three times. Same
        # "the engine has no 'declined' concept of its own" memo AIMemory keeps.
        self._asked = set()

    def reset_phase(self):
        """"Any phase" - so the once-per-unit memo above is scoped to a phase,
        alongside StratagemController.reset_phase()'s own 15.01 bookkeeping."""
        self._asked = set()

    def can_offer(self, dead_model):
        if dead_model is None or self.decision_manager is None:
            return False
        if not is_battlesuit_model(dead_model) or not has_deadly_demise(dead_model):
            return False
        squad = getattr(dead_model, "squad", None)
        if squad is None or squad in self._asked:
            return False
        # The choice only exists while that ability's roll is still ahead of
        # us - once it has resolved there is nothing left to replace.
        if self.deadly_demise_controller is None or not self.deadly_demise_controller.has_queued_death(dead_model):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def notify_destroyed(self, dead_model):
        """Called from main.py's dead-model loop for every destroyed token.
        Returns True if an offer was opened.

        Fire-and-forget, like game/stim_injectors.py: DecisionManager is a
        queue and main.py's event loop gives a pending decision priority over
        everything else - including the gate that lets Deadly Demise start its
        own roll, which is what guarantees this offer is answered BEFORE the
        roll it replaces."""
        if not self.can_offer(dead_model):
            return False
        squad = dead_model.squad
        self._asked.add(squad)
        self._dead_model = dead_model

        # One prompt, not two: "use it" and "which result" are a single
        # decision, and both results are genuinely wanted (a 1 spares your own
        # nearby units, a 6 detonates).
        x = dead_model.profile.deadly_demise_notation or dead_model.profile.deadly_demise
        self.decision_manager.request(
            squad.owner,
            f"Fail-Safe Detonator ({FAIL_SAFE_CP_COST} CP): {dead_model.profile.name} was destroyed. "
            f"Instead of rolling for Deadly Demise, choose the result - a {FAIL_SAFE_DEMISE_HIGH} detonates "
            f'(every unit within {DEADLY_DEMISE_RANGE_IN:.0f}" suffers {x} mortal wounds, friendly units too), '
            f"a {FAIL_SAFE_DEMISE_LOW} does not.",
            [
                (f"Use Fail-Safe Detonator ({FAIL_SAFE_CP_COST} CP) - detonate (count it as a {FAIL_SAFE_DEMISE_HIGH})",
                 lambda: self._use(FAIL_SAFE_DEMISE_HIGH)),
                (f"Use Fail-Safe Detonator ({FAIL_SAFE_CP_COST} CP) - do not detonate (count it as a {FAIL_SAFE_DEMISE_LOW})",
                 lambda: self._use(FAIL_SAFE_DEMISE_LOW)),
                ("Decline", self._declined),
            ],
            is_stratagem=True,
        )
        return True

    def _use(self, chosen_demise):
        self._chosen_demise = chosen_demise
        squad = self._dead_model.squad
        if not self.stratagem_controller.use(squad.owner, self._stratagem, [squad]):
            self._declined()

    def _declined(self):
        self._dead_model = None
        self._chosen_demise = None

    def _apply(self, controller, player, targets):
        dead_model = self._dead_model
        self._log(
            f"{player}: Fail-Safe Detonator - {dead_model.profile.name}'s Deadly Demise is not rolled; "
            f"the result counts as a {self._chosen_demise}."
        )
        self.deadly_demise_controller.force_roll(dead_model, self._chosen_demise)
        self._dead_model = None
        self._chosen_demise = None

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
