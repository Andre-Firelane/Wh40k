"""Da Big Hunt Stratagem: Where D'ya Fink You're Going? (1CP, Mecha Orks G5).

RULE (verbatim, rules/orks/detachments/Da Big Hunt.md):
  WHEN:   Your opponent's Movement phase, when an enemy unit is selected to make
          a fall-back move, if that enemy unit is engaged with a friendly BEAST
          SNAGGA unit.
  TARGET: That BEAST SNAGGA unit.
  EFFECT: When an enemy unit engaged with your unit is selected to make a
          fall-back move, that enemy unit must use the desperate escape mode. If
          that enemy unit is a MONSTER/VEHICLE unit, that enemy unit makes three
          additional hazard rolls for each BEAST SNAGGA unit it is engaged with,
          with -1 from those hazard rolls if that enemy unit is battle-shocked.

THE CLANBLADE'S CORNERED PREY, BOUGHT. The EFFECT is that datasheet ability's
sentence with an extra clause, so it goes through the same door:
game/forced_desperate_escape.py, the registry game/fall_back.py asks in its
three places (the mode at declare(), the refusal in choose_mode(), and the
hazard step at confirm()). That registry LISTS this module's three answers;
what this module owns is the mark, the offer and the price.

THE MARK IS ON THE TARGET, not on the victim: the printed EFFECT is written as
a standing property of "your unit" ("when an enemy unit engaged with YOUR unit
is selected..."), so the BEAST SNAGGA unit carries it (Squad.where_dya_fink_active)
and every enemy engaged with it is measured live. No printed duration, so it
lasts the phase - this engine's reading - and main.py clears it at the boundary.

THE MOMENT is FallBackController.declare()'s on_fall_back_declared listeners -
"when an enemy unit IS SELECTED to make a fall-back move", the same instant
Aspect Host's Khaine's Vengeance reacts to. A human answers frames later, and
that is safe here: declare() leaves a unit that is not battle-shocked in
CHOOSING_MODE, and choose_mode() asks the registry again - so the mark set by a
late "Use" still takes Ordered Retreat away. A unit that was ALREADY
battle-shocked is in Desperate Escape anyway, and then the mark only adds the
rolls and the -1, both read at confirm().

"THREE ADDITIONAL HAZARD ROLLS FOR EACH BEAST SNAGGA UNIT IT IS ENGAGED WITH"
is counted live here, and FROZEN by the registry: rule 09.07's fall-back move
must end unengaged, so by the time the hazard rolls are made no victim is
engaged with anything and a live count there is zero. forced_desperate_escape.snapshot()
owns that freezing for both sources (Cornered Prey had the same defect,
unnoticed), and this module calls it at the one moment the other two callers
cannot cover: the purchase, which for a battle-shocked victim comes after
fall_back has already chosen the mode.

THE AI buys it when the victim is a MONSTER/VEHICLE (the extra rolls are the
damage) or when the victim has enough models for the ordinary one-per-model
rolls to hurt - deterministic, 0 API calls.
"""

from game import ai_mode, da_big_hunt
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance, is_monster_or_vehicle_unit
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

WHERE_DYA_FINK_NAME = "Where D'ya Fink You're Going?"
WHERE_DYA_FINK_CP = 1
#: "three additional hazard rolls for each BEAST SNAGGA unit it is engaged with".
WHERE_DYA_FINK_EXTRA_ROLLS = 3
#: "-1 from those hazard rolls if that enemy unit is battle-shocked".
WHERE_DYA_FINK_PENALTY = 1
#: The AI's rule: a victim this big makes the ordinary rolls worth 1CP.
WHERE_DYA_FINK_MIN_MODELS = 5
USE_LABEL = "Use Where D'ya Fink You're Going? (1 CP)"
DECLINE_LABEL = "Decline"


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def is_marked(squad):
    return bool(getattr(squad, "where_dya_fink_active", False))


def reset_phase(squads=()):
    for squad in squads or ():
        if getattr(squad, "where_dya_fink_active", False):
            squad.where_dya_fink_active = False


def marked_hunters_engaged_with(victim, all_tokens=()):
    """The marked BEAST SNAGGA units of the victim's enemies that are engaged
    with it - measured live, as the printed sentence does."""
    seen, out = set(), []
    mine = _living(victim)
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other is victim or id(other) in seen:
            continue
        if other.owner == victim.owner or not is_marked(other):
            continue
        if not da_big_hunt.is_beast_snagga_unit(other):
            continue
        if any(edge_distance(a, b) <= ENGAGEMENT_RANGE_IN for a in mine for b in _living(other)):
            seen.add(id(other))
            out.append(other)
    return out


def forces_desperate_escape(victim, all_tokens=()):
    return bool(marked_hunters_engaged_with(victim, all_tokens))


def hazard_penalty_for(victim, all_tokens=()):
    """"-1 ... if that enemy unit is battle-shocked" - its own condition, so it
    is not folded into the clause above."""
    if not getattr(victim, "battle_shocked", False):
        return 0
    return WHERE_DYA_FINK_PENALTY if marked_hunters_engaged_with(victim, all_tokens) else 0


def extra_hazard_rolls_for(victim, all_tokens=()):
    """"If that enemy unit is a MONSTER/VEHICLE unit, three additional hazard
    rolls for each BEAST SNAGGA unit it is engaged with"."""
    if not is_monster_or_vehicle_unit(victim):
        return 0
    return WHERE_DYA_FINK_EXTRA_ROLLS * len(marked_hunters_engaged_with(victim, all_tokens))


class WhereDyaFinkController:
    """The offer at "an enemy unit is selected to make a fall-back move"."""

    def __init__(self, stratagem_controller, turn_tracker=None, decision_manager=None,
                 all_tokens=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._stratagem = Stratagem(WHERE_DYA_FINK_NAME, WHERE_DYA_FINK_CP, self._mark)
        self._acting = None
        self._offered = set()

    # ----------------------------------------------------------- questions
    def hunters_engaged_with(self, victim):
        """"a friendly BEAST SNAGGA unit" engaged with the victim - the TARGET,
        marked or not."""
        seen, out = set(), []
        mine = _living(victim)
        for token in self.all_tokens:
            other = getattr(token, "squad", None)
            if other is None or other is victim or id(other) in seen:
                continue
            if other.owner == victim.owner or not _living(other):
                continue
            if not da_big_hunt.fields_da_big_hunt(other.owner) or not da_big_hunt.is_beast_snagga_unit(other):
                continue
            if any(edge_distance(a, b) <= ENGAGEMENT_RANGE_IN for a in mine for b in _living(other)):
                seen.add(id(other))
                out.append(other)
        return sorted(out, key=lambda s: s.name)

    def can_use(self, victim):
        tt = self.turn_tracker
        if victim is None or tt is None or not _living(victim):
            return False
        # "YOUR OPPONENT'S Movement phase" - the victim is the moving player's.
        if tt.phase != PHASE_MOVEMENT or victim.owner != tt.turn_owner:
            return False
        hunters = [h for h in self.hunters_engaged_with(victim) if not is_marked(h)]
        if not hunters:
            return False
        return self.stratagem_controller.can_use(hunters[0].owner, self._stratagem, [hunters[0]])

    def worth_it(self, victim):
        """The AI's rule - see the module docstring."""
        return is_monster_or_vehicle_unit(victim) or len(_living(victim)) >= WHERE_DYA_FINK_MIN_MODELS

    # ------------------------------------------------------- the moment
    def notify_selected_to_fall_back(self, victim):
        """Fed from FallBackController.declare()."""
        if not self.can_use(victim):
            return False
        hunters = [h for h in self.hunters_engaged_with(victim) if not is_marked(h)]
        buyer = hunters[0].owner
        key = (id(victim), getattr(self.turn_tracker, "battle_round", None),
               getattr(self.turn_tracker, "turn_owner", None))
        if key in self._offered:
            return False
        self._offered.add(key)
        if buyer in self.auto_players or self.decision_manager is None:
            if not self.worth_it(victim):
                return False
            return self.use(hunters[0], victim)
        self.decision_manager.request(
            buyer,
            "%s (%d CP): %s is falling back from %s - force the desperate escape mode%s?"
            % (WHERE_DYA_FINK_NAME, WHERE_DYA_FINK_CP, victim.name, hunters[0].name,
               " and %d extra hazard rolls" % extra_hazard_rolls_for(victim, self.all_tokens)
               if is_monster_or_vehicle_unit(victim) else ""),
            [(USE_LABEL, lambda h=hunters[0], v=victim: self.use(h, v)),
             (DECLINE_LABEL, lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, hunter, victim=None):
        """Pay and mark - checked again, because a human answers frames later."""
        if hunter is None or is_marked(hunter):
            return False
        if victim is not None and not self.can_use(victim):
            return False
        self._acting = hunter
        try:
            paid = bool(self.stratagem_controller.use(hunter.owner, self._stratagem, [hunter]))
        finally:
            self._acting = None
        if paid and victim is not None:
            # The victim is still standing in the hunter's Engagement Range
            # right now, and will not be when the hazard rolls are made. A
            # local import: the registry lists this module, so it cannot be
            # imported at module level.
            from game import forced_desperate_escape
            forced_desperate_escape.snapshot(victim, self.all_tokens)
        return paid

    def _mark(self, controller, player, targets):
        hunter = self._acting
        if hunter is None:
            return False
        hunter.where_dya_fink_active = True
        if self.game_log is not None:
            self.game_log.add(
                "%s: every enemy unit engaged with %s must use the desperate escape mode this phase."
                % (WHERE_DYA_FINK_NAME, hunter.name))
        return True

    def reset_phase(self, squads=()):
        self._offered = set()
        reset_phase(squads)
