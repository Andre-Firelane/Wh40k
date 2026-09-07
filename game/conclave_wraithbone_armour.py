"""Spirit Conclave Stratagem: Wraithbone Armour (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Spirit Conclave.md):
  WHEN:   Your opponent's Shooting phase or the Fight phase, just after an
          enemy unit has selected its targets.
  TARGET: One WRAITH CONSTRUCT unit from your army (excluding TITANIC units)
          that was selected as the target of one or more of the attacking
          unit's attacks.
  EFFECT: Until the end of the phase, each time an attack is allocated to a
          model in your unit, subtract 1 from the Damage characteristic of that
          attack.
  RESTRICTIONS: none printed.

CORPUS ARTEFACTS, transcribed rather than silently repaired: the flavour line
reads "be/ies" for "belies", and the TARGET clause closes its bracket with a
square one - "(excluding TITANIC units]". Both are Wahapedia's rendering, not
the card's, and both are quoted here as they stand so a future diff of
rules/*.md shows a real change rather than my tidying.

THE FIFTH SOURCE IN _reduced_damage(), which is exactly where it belongs: that
method is the one place "change the Damage characteristic of the attack
allocated to this model" is applied, it already floors every reduction at 1,
and it already runs BEFORE Feel No Pain - which is the order the printed text
needs, since FNP (24.12) is rolled per remaining wound.

Its four predecessors are Molten Form (a halving), Implacable Resilience and
Necrodermis (game/damage_reduction.py) and Mont'ka's Counterfire Defence
Systems. This is the second Stratagem among them, and the first that is bought
by the DEFENDER in reaction to being targeted.

"EXCLUDING TITANIC UNITS" IS A MEASURED NO-OP on every roster here: this engine
has no TITANIC keyword at all, the same exclusion game/rapid_ingress.py already
documents for itself. Written out and checked anyway, because "already
impossible" and "forgotten" look identical from the code - and because the
Wraithknights, which do print TITANIC, are exactly the datasheets a later stage
might add.

REACTIVE IN BOTH PHASES, like Lightning-Fast Reactions next door, so it joins
both target_reactions lists. THE ARGUMENT ORDER IS THE LIST'S: the protected
unit is the TARGET, the second argument.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, ai_mode, shepherds_of_the_dead
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

WRAITHBONE_ARMOUR_NAME = "Wraithbone Armour"
WRAITHBONE_ARMOUR_CP = 1

#: "subtract 1 from the Damage characteristic of that attack".
WRAITHBONE_ARMOUR_REDUCTION = 1

WRAITHBONE_ARMOUR_KEYWORD = "WRAITH CONSTRUCT"

#: The printed exclusion. A measured no-op: no datasheet in this engine carries
#: the keyword. Kept so the transcription is complete.
WRAITHBONE_ARMOUR_EXCLUDED_KEYWORD = "TITANIC"

SETTING = shepherds_of_the_dead.SETTING


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def is_active(squad):
    return bool(getattr(squad, "wraithbone_armour_active", False))


def damage_reduction_for(squad):
    """Read by DamageAllocationSession._reduced_damage(). 0 means no opinion,
    which is what every other source there returns."""
    return WRAITHBONE_ARMOUR_REDUCTION if is_active(squad) else 0


def eligible_unit(squad):
    """"One WRAITH CONSTRUCT unit from your army (excluding TITANIC units)"."""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    if not unit_has_datasheet_keyword(squad, WRAITHBONE_ARMOUR_KEYWORD):
        return False
    return not unit_has_datasheet_keyword(squad, WRAITHBONE_ARMOUR_EXCLUDED_KEYWORD)


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.wraithbone_armour_active = False


class WraithboneArmourController:
    """The just-after-targets-are-selected offer, in both attack phases."""

    def __init__(self, stratagem_controller, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._offered_this_phase = set()
        self._stratagem = Stratagem(
            name=WRAITHBONE_ARMOUR_NAME, cp_cost=WRAITHBONE_ARMOUR_CP,
            effect=self._grant,
        )

    def reset_phase(self, squads=()):
        self._offered_this_phase = set()
        reset_phase(squads)

    def can_use(self, attacker, target):
        if attacker is None or target is None or self.stratagem_controller is None:
            return False
        if self.turn_tracker is not None:
            phase = self.turn_tracker.phase
            if phase == PHASE_SHOOTING:
                # "YOUR OPPONENT'S Shooting phase".
                if target.owner == self.turn_tracker.turn_owner:
                    return False
            elif phase != PHASE_FIGHT:
                # "or THE Fight phase" - which belongs to nobody.
                return False
        if attacker.owner == target.owner:
            return False
        if is_active(target):
            return False
        if not eligible_unit(target):
            return False
        return self.stratagem_controller.can_use(target.owner, self._stratagem, [target])

    def maybe_offer(self, attacker, target, melee=False):
        """The target_reactions protocol, shared by both attack controllers."""
        if not self.can_use(attacker, target):
            return False
        key = (id(attacker), id(target))
        if key in self._offered_this_phase:
            return False
        self._offered_this_phase.add(key)
        if target.owner in self.auto_players or self.decision_manager is None:
            return False               # no AI path
        self.decision_manager.request(
            target.owner,
            "%s (%d CP): %s is attacking %s - subtract %d from the Damage of "
            "every attack allocated to it this phase?"
            % (WRAITHBONE_ARMOUR_NAME, WRAITHBONE_ARMOUR_CP, attacker.name,
               target.name, WRAITHBONE_ARMOUR_REDUCTION),
            [("Use (%d CP)" % WRAITHBONE_ARMOUR_CP, (lambda: self.use(target))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, target):
        if self.stratagem_controller is None or target is None:
            return False
        if is_active(target) or not eligible_unit(target):
            return False
        return self.stratagem_controller.use(target.owner, self._stratagem, [target])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.wraithbone_armour_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: attacks allocated to %s lose %d Damage this phase."
                    % (WRAITHBONE_ARMOUR_NAME, squad.name,
                       WRAITHBONE_ARMOUR_REDUCTION))
