"""Seer Council's "Forewarned" (1CP, Strategic Ploy).

RULE (printed, word for word):
  WHEN: "Fight phase, just after an enemy unit has selected its targets"
  TARGET: "One ASURYANI INFANTRY unit from your army (excluding WRAITH
  CONSTRUCT units) that was selected as the target of one or more of the
  attacking unit's attacks and is within 9" of one or more friendly ASURYANI
  PSYKER models"
  EFFECT: "Until the end of the phase, each time an attack targets your unit,
  subtract 1 from the Hit roll and subtract 1 from the Wound roll."

NOTHING NEW - THIRD CONSUMER OF AN EXISTING HOOK
------------------------------------------------
"Just after an enemy unit has selected its targets" is game/shooting.py's and
game/fight.py's target_reactions list, built for Stim Injectors and reused by
'Ard as Nails. The two modifiers are the same defender-side maluses those two
and Protect already sit in, so both hooks exist too.

FIGHT PHASE ONLY, and that is the WHEN talking, not a simplification: the EFFECT
says "each time an attack targets your unit" without restricting to melee, but
the WHEN puts the whole thing in the Fight phase and the duration is "until the
end of the phase" - so no ranged attack can ever see it. Registered only in
game/fight.py's reaction list for that reason, which is also what makes the
melee=True check below redundant-but-honest.

"FIGHT PHASE" is bare, not "your Fight phase" - correct, because the Fight phase
is shared (12.04) and either player can be the one reacting. Same reading
game/counteroffensive.py spells out for its own WHEN.

NO RELEVANCE GATE, deliberately, unlike Stim Injectors. That one reacts to every
enemy target selection in two phases and needed a threshold to stop
interrupting; this one fires only in the Fight phase, only for an ASURYANI
INFANTRY unit near a Psyker, and 15.01 caps it at once per phase on top. The
printed clauses ARE the eligibility.
"""

from game import attached_units
from game import psychic_guidance
from game.stratagems import Stratagem

FOREWARNED_CP = 1
FOREWARNED_NAME = "Forewarned"
FOREWARNED_PSYKER_RANGE_IN = 9.0
# game/modifiers.py counts a POSITIVE amount as worsening a threshold, and
# "subtract 1 from the roll" makes both rolls harder - so +1 on each threshold,
# the same sign 'Ard as Nails and Protect use.
FOREWARNED_PENALTY = 1


def _is_wraith_construct(squad):
    return attached_units.unit_has_datasheet_keyword(squad, "WRAITH CONSTRUCT")


def eligible_unit(squad):
    """The TARGET clause's own conditions on the unit itself: ASURYANI (read the
    same way every other Aeldari ability here reads faction), INFANTRY, and not
    a WRAITH CONSTRUCT."""
    if squad is None or not squad.models:
        return False
    if not psychic_guidance._is_aeldari(squad):
        return False
    if not all(getattr(m.profile, "infantry", False) for m in squad.models):
        return False
    return not _is_wraith_construct(squad)


def near_friendly_psyker(squad, all_tokens):
    """"within 9" of one or more friendly ASURYANI PSYKER models". Centre to
    centre, like every other "within X of a model" test here, and the psyker may
    be in this very unit - the clause says friendly, not "another unit"."""
    for token in all_tokens or ():
        if token.is_dead() or not getattr(token.profile, "psyker", False):
            continue
        other = getattr(token, "squad", None)
        if other is None or other.owner != squad.owner or not psychic_guidance._is_aeldari(other):
            continue
        for model in squad.models:
            if model.is_dead():
                continue
            dx, dy = model.x_in - token.x_in, model.y_in - token.y_in
            if (dx * dx + dy * dy) ** 0.5 <= FOREWARNED_PSYKER_RANGE_IN:
                return True
    return False


def applies(squad):
    """Read by both of game/fight.py's modifier hooks."""
    return squad is not None and getattr(squad, "forewarned_active", False)


def reset_phase(squads=()):
    """"Until the end of the phase"."""
    for squad in squads:
        squad.forewarned_active = False


class ForewarnedController:
    """An entry in game/fight.py's target_reactions list - same
    maybe_offer(attacker, target, melee) contract as Stim Injectors and 'Ard as
    Nails, so that list needs to know nothing about this stratagem."""

    def __init__(self, stratagem_controller=None, decision_manager=None, game_log=None,
                 all_tokens=None, turn_tracker=None):
        self.stratagem_controller = stratagem_controller
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self._stratagem = Stratagem(name=FOREWARNED_NAME, cp_cost=FOREWARNED_CP, effect=self._effect)
        self._handled_this_phase = set()

    def reset_phase(self):
        self._handled_this_phase.clear()

    def can_use(self, attacker, target):
        if self.stratagem_controller is None or attacker is None or target is None:
            return False
        if target.owner == attacker.owner:
            return False
        if applies(target):
            return False   # already up on this unit
        if not eligible_unit(target):
            return False
        if not near_friendly_psyker(target, self.all_tokens):
            return False
        return self.stratagem_controller.can_use(target.owner, self._stratagem, [target])

    def maybe_offer(self, attacker, target, melee=False):
        """Returns True if this used the stratagem or opened a prompt."""
        if not melee:
            return False   # WHEN is the Fight phase; see the module docstring
        key = (id(attacker), id(target))
        if key in self._handled_this_phase:
            return False
        if not self.can_use(attacker, target):
            return False
        self._handled_this_phase.add(key)
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            target.owner,
            f"Forewarned ({FOREWARNED_CP} CP): {attacker.name} has targeted {target.name}. "
            "Until the end of the phase, attacks targeting it subtract 1 from the Hit roll "
            "AND 1 from the Wound roll.",
            [
                (f"Forewarned ({FOREWARNED_CP} CP)", lambda: self._use(target)),
                ("Decline", lambda: None),
            ],
        )
        return True

    def _use(self, target):
        self.stratagem_controller.use(target.owner, self._stratagem, [target])

    def _effect(self, controller, player, targets):
        target = targets[0]
        target.forewarned_active = True
        if self.game_log is not None:
            self.game_log.add(
                f"Forewarned: until the end of the phase, attacks targeting {target.name} "
                "subtract 1 from the Hit roll and 1 from the Wound roll."
            )
