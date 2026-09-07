"""Armoured Warhost Stratagem: Layered Wards (1CP).

RULE (verbatim, rules/aeldari/detachments/Armoured Warhost.md):
  WHEN:   Any phase, when a friendly AELDARI VEHICLE unit suffers a mortal
          wound.
  TARGET: That AELDARI VEHICLE unit.
  EFFECT: Your unit has Feel No Pain 5+ against mortal wounds.
  RESTRICTIONS: none printed.

ONE FOLD, NO NEW PLUMBING. game/feel_no_pain.py's current_feel_no_pain()
already takes `mortal`, set by MortalWoundAllocationSession alone - that
session IS the mortal-wound path (rule 06.02), so "was this a mortal wound"
needed no argument threading when the Broadsides' Advanced Armour asked the
same question first. This is the SECOND conditional Feel No Pain and it is one
more `_better_threshold()` line.

WHY IT IS A SQUAD FLAG AND ADVANCED ARMOUR IS A PROFILE FIELD. Advanced Armour
is printed on the Broadside datasheet - it is what the model IS. This is bought
for one unit in the middle of a battle, so it lives on the Squad, like every
other Stratagem latch here.

"ANY PHASE" IS THE WHOLE OF THE WHEN, and that is unusual enough to be worth
saying: almost every Stratagem in this batch names a phase, and the phase gate
is the first line of its can_use(). This one has none. What bounds it instead
is the trigger - a mortal wound actually being suffered - so can_use() asks
whether one is on the table rather than what time it is.

NO DURATION IS PRINTED, so it is cleared at the end of the turn like every
other latch whose text is silent. Writing it down because the alternative
readings (this allocation only; the rest of the battle) are both defensible
and neither is what the other Stratagem latches in this detachment do.

THE AI DECLINES. Standing Aeldari instruction, so an owner in auto_players
never buys it and no prompt can stall the loop.
"""

from game import aeldari_detachments, ai_mode, skilled_crews
from game.stratagems import Stratagem

LAYERED_WARDS_NAME = "Layered Wards"
LAYERED_WARDS_CP = 1

#: "Feel No Pain 5+ against mortal wounds."
LAYERED_WARDS_FEEL_NO_PAIN = "5+"


def is_active(squad):
    return bool(getattr(squad, "layered_wards_active", False))


def layered_wards_feel_no_pain(model, mortal=False):
    """This model's Feel No Pain threshold against a MORTAL wound, or "-".

    Same shape and same return convention as
    advanced_armour.advanced_armour_feel_no_pain(): a threshold STRING, so the
    fold keeps parsing it with parse_threshold(), and "-" for an ordinary
    wound however the unit is buffed."""
    if not mortal or model is None:
        return "-"
    return LAYERED_WARDS_FEEL_NO_PAIN if is_active(getattr(model, "squad", None)) else "-"


def applies(squad):
    """"a friendly AELDARI VEHICLE unit" of a player fielding the detachment."""
    # The detachment gate. Its SETTING lives in the RULE module - one
    # definition per detachment, the same one Skilled Crews itself reads.
    if squad is None or not skilled_crews.has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    return any(getattr(m.profile, "vehicle", False)
               for m in (getattr(squad, "models", ()) or ()) if not m.is_dead())


def reset_turn(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.layered_wards_active = False


class LayeredWardsController:
    """The offer, made when a mortal wound is actually about to land."""

    def __init__(self, stratagem_controller, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._stratagem = Stratagem(
            name=LAYERED_WARDS_NAME, cp_cost=LAYERED_WARDS_CP, effect=self._grant,
            # "Any phase, when a friendly unit SUFFERS a mortal wound" - a unit
            # can be hit by mortal wounds from two sources in one phase, and
            # each is its own trigger, so 15.01's once-per-target-per-phase
            # would be wrong here.
            allow_repeat_target=True,
        )

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None:
            return False
        if is_active(squad):
            return False                     # already up on this unit
        if not applies(squad):
            return False
        if not any(not m.is_dead() for m in (getattr(squad, "models", ()) or ())):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def maybe_offer(self, squad):
        """Called when `squad` is about to take one or more mortal wounds.

        Fed from the mortal-wound path rather than from a phase hook, because
        the printed WHEN names no phase - the trigger IS the timing."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return False                     # no AI path; see the docstring
        self.decision_manager.request(
            squad.owner,
            "%s (%d CP): %s is suffering a mortal wound - give it Feel No Pain "
            "%s against mortal wounds?"
            % (LAYERED_WARDS_NAME, LAYERED_WARDS_CP, squad.name,
               LAYERED_WARDS_FEEL_NO_PAIN),
            [("Use (%d CP)" % LAYERED_WARDS_CP, (lambda: self.use(squad))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.layered_wards_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s has Feel No Pain %s against mortal wounds."
                    % (LAYERED_WARDS_NAME, squad.name, LAYERED_WARDS_FEEL_NO_PAIN))
