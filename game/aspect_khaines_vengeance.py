"""Aspect Host Stratagem: Khaine's Vengeance (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Aspect Host.md):
  WHEN:   Your opponent's Movement phase, just after an enemy unit (excluding
          MONSTERS and VEHICLES) is selected to Fall Back.
  TARGET: One ASPECT WARRIORS or AVATAR OF KHAINE unit from your army that is
          within Engagement Range of that enemy unit.
  EFFECT: All models in that enemy unit must take a Desperate Escape test. When
          doing so, if that enemy unit is Battle-shocked, subtract 1 from each
          of those tests.
  RESTRICTIONS: none printed.

A DIFFERENT MOMENT FROM FEIGNED RETREAT, and one word apart on the page. That
Stratagem fires "just after an ASURYANI unit FALLS BACK" - after the move. This
one fires when a unit "IS SELECTED TO Fall Back" - before it. So they hook two
different points of FallBackController: declare(), which is where the unit is
selected, and confirm(), which is where the move lands. Two hooks, because a
unit selected to Fall Back has not moved yet and the tests this forces happen
regardless of where it ends up.

IT DOES NOT CHANGE THE MODE. A Desperate Escape mode already rolls its own
tests; this forces tests on top, so an ORDERED RETREAT - which normally rolls
nothing - suddenly costs models. Reading it as "force the Desperate Escape
mode" would be weaker (the unit would then choose its own path) and is not what
the text says.

THE TESTS ARE game/hazard.py's HazardRollStep, which is what a Desperate Escape
test already is here: one D6 per model, mortal wounds for the failures,
allocated through the ordinary interactive session. Its `penalty` parameter
exists for exactly the clause below - the Clanblade's Cornered Prey was its
first user, and this is the second.

"IF THAT ENEMY UNIT IS BATTLE-SHOCKED, SUBTRACT 1" is read at the moment the
tests are rolled, not when the Stratagem is bought - one is a property of the
unit and the other is a purchase. On this engine the two coincide (nothing
between the two instants can change it), which is stated rather than relied on.

"EXCLUDING MONSTERS AND VEHICLES" is a real exclusion, not boilerplate: those
are exactly the units that shrug off a Desperate Escape, and both keywords are
carried by real datasheets here.

THE TARGET IS MINE, THE VICTIM IS THEIRS. The Stratagem's TARGET clause names
one of MY units within Engagement Range - which is what pays for the effect -
while the models that roll belong to the ENEMY. Getting that round the wrong
way would test my own unit, which is why both halves are named separately here
and checked separately in the test.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, detachment_gate
from game.hazard import HazardRollStep
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

KHAINES_VENGEANCE_NAME = "Khaine's Vengeance"
KHAINES_VENGEANCE_CP = 1

#: "if that enemy unit is Battle-shocked, subtract 1 from each of those tests".
KHAINES_VENGEANCE_BATTLE_SHOCK_PENALTY = 1

KHAINES_VENGEANCE_KEYWORDS = ("ASPECT WARRIORS", "AVATAR OF KHAINE")

#: "excluding MONSTERS and VEHICLES" - the units that would shrug it off.
KHAINES_VENGEANCE_EXCLUDED_KEYWORDS = ("MONSTER", "VEHICLE")

SETTING = "ASPECT_HOST_PLAYERS"


def has_detachment(player):
    return detachment_gate.has_detachment(player, SETTING)


def eligible_avenger(squad):
    """MY unit - the one that pays."""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, k)
               for k in KHAINES_VENGEANCE_KEYWORDS)


def eligible_victim(squad):
    """THEIR unit - the one that rolls. A different question from the one
    above, and the two are never the same unit."""
    if squad is None:
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return not any(unit_has_datasheet_keyword(squad, k)
                   for k in KHAINES_VENGEANCE_EXCLUDED_KEYWORDS)


def penalty_for(victim_squad):
    """"if that enemy unit is Battle-shocked, subtract 1". Read when the tests
    are rolled - a property of the unit, not of the purchase."""
    return (KHAINES_VENGEANCE_BATTLE_SHOCK_PENALTY
            if getattr(victim_squad, "battle_shocked", False) else 0)


def avengers_in_range(victim_squad, all_tokens=(), player=None):
    """"One ... unit from your army that is within Engagement Range of that
    enemy unit"."""
    if victim_squad is None:
        return []
    theirs = [m for m in (getattr(victim_squad, "models", ()) or ())
              if not m.is_dead()]
    if not theirs:
        return []
    out = []
    for token in all_tokens or ():
        mine = getattr(token, "squad", None)
        if mine is None or mine is victim_squad or token.is_dead():
            continue
        if mine.owner == victim_squad.owner:
            continue
        if player is not None and mine.owner != player:
            continue
        if mine in out or not eligible_avenger(mine):
            continue
        if any(edge_distance(token, m) <= ENGAGEMENT_RANGE_IN for m in theirs):
            out.append(mine)
    return out


class KhainesVengeanceController:
    """The just-after-a-unit-is-SELECTED-to-Fall-Back offer."""

    def __init__(self, stratagem_controller, dice_manager=None, all_tokens=None,
                 turn_tracker=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self._hazard_step = None
        self._pending = {}
        self._stratagem = Stratagem(
            name=KHAINES_VENGEANCE_NAME, cp_cost=KHAINES_VENGEANCE_CP,
            effect=self._force_tests,
        )

    @property
    def is_busy(self):
        return self._hazard_step is not None

    def can_use(self, victim_squad, player=None):
        if victim_squad is None or self.stratagem_controller is None:
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_MOVEMENT:
                return False
            # "YOUR OPPONENT'S Movement phase" - the unit falling back belongs
            # to the turn owner, so the buyer is anyone else.
            if victim_squad.owner != self.turn_tracker.turn_owner:
                return False
        if not eligible_victim(victim_squad):
            return False
        avengers = avengers_in_range(victim_squad, self.all_tokens, player)
        if not avengers:
            return False
        return self.stratagem_controller.can_use(
            avengers[0].owner, self._stratagem, [avengers[0]])

    def notify_selected_to_fall_back(self, victim_squad):
        """Fed from FallBackController.declare() - "IS SELECTED to Fall Back",
        which is a different instant from Feigned Retreat's "FALLS BACK"."""
        if not self.can_use(victim_squad):
            return False
        avengers = avengers_in_range(victim_squad, self.all_tokens)
        buyer = avengers[0].owner
        if buyer in self.auto_players or self.decision_manager is None:
            return False               # no AI path
        self.decision_manager.request(
            buyer,
            "%s (%d CP): %s is falling back from %s - make all its models take "
            "a Desperate Escape test?"
            % (KHAINES_VENGEANCE_NAME, KHAINES_VENGEANCE_CP, victim_squad.name,
               avengers[0].name),
            [("Use (%d CP)" % KHAINES_VENGEANCE_CP,
              (lambda v=victim_squad: self.use(v, buyer))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, victim_squad, player=None):
        if not self.can_use(victim_squad, player):
            return False
        avengers = avengers_in_range(victim_squad, self.all_tokens, player)
        buyer = avengers[0].owner
        self._pending[buyer] = victim_squad
        return self.stratagem_controller.use(buyer, self._stratagem, [avengers[0]])

    def _force_tests(self, controller, player, targets):
        victim = self._pending.pop(player, None)
        if victim is None or self.dice_manager is None:
            return
        models = [m for m in (getattr(victim, "models", ()) or ()) if not m.is_dead()]
        if not models:
            return
        penalty = penalty_for(victim)
        self._hazard_step = HazardRollStep(
            victim, len(models), self.dice_manager,
            log=(lambda m: self.game_log.add(m)) if self.game_log is not None else None,
            penalty=penalty)
        if self.game_log is not None:
            self.game_log.add(
                "%s: all %d model(s) in %s take a Desperate Escape test%s."
                % (KHAINES_VENGEANCE_NAME, len(models), victim.name,
                   " at -%d (Battle-shocked)" % penalty if penalty else ""))

    # --------------------- the hazard step's own plumbing, as Fall Back does

    @property
    def pending_damage_choice(self):
        return (self._hazard_step.pending_damage_choice
                if self._hazard_step is not None else None)

    def choose_damage_model(self, model):
        if self._hazard_step is None:
            return
        self._hazard_step.choose_damage_model(model)
        if self._hazard_step.done:
            self._hazard_step = None

    def on_dice_acknowledged(self):
        if self._hazard_step is None:
            return
        self._hazard_step.on_dice_acknowledged()
        if self._hazard_step.done:
            self._hazard_step = None
