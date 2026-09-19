"""Green Tide Stratagem: Unbridled Carnage (1CP, Mecha Orks stage G3).

RULE (verbatim, rules/orks/detachments/Green Tide.md):
  WHEN:   Fight phase, when a friendly BOYZ unit that made a charge move this
          turn is selected to fight.
  TARGET: That BOYZ unit.
  EFFECT: Your unit's melee attacks have +1 A.

"FIGHT PHASE" WITHOUT "YOUR" - the Fight phase is shared (rule 12.04), so
either player may buy it, and "selected to fight" is read the way Hit 'Em
Harder reads its identical WHEN: a unit that is eligible to fight, has not
fought and is not fighting right now. The button stands above "Fight".

"MADE A CHARGE MOVE THIS TURN" is Squad.charged_this_turn (rule 11.04's flag,
cleared at the end of the turn). "BOYZ" is the datasheet (game/green_tide.py's
is_boyz_unit()), so a Warboss-led mob qualifies and its Warboss swings with +1 A
too - "your unit's melee attacks".

THE EFFECT LASTS THE PHASE: the fight it is bought for is in this phase, and
reset_phase() clears it at the boundary. +1 A on a dice-notation Attacks lands
on the notation's flat part (game/dice_notation.py's plus()).

The pre-codex module of the same name (War Horde, retired in 1786db5) was a
different card - "+1 to wound" on any ORKS unit; nothing of it is reused.

THE AI (ai/agent_driver.py's _handle_unbridled_carnage()) buys it when the extra
attacks are expected to add UNBRIDLED_CARNAGE_MIN_GAIN wounds against the
engaged enemy they help most - expected_extra_wounds() below, built from
game/damage_estimate.py's pieces.
"""

import copy

from game import dice_notation, green_tide
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT
from game.weapons import MELEE

UNBRIDLED_CARNAGE_NAME = "Unbridled Carnage"
UNBRIDLED_CARNAGE_CP = 1
#: "+1 A".
UNBRIDLED_CARNAGE_ATTACKS = 1
#: The AI's rule: 1 CP for at least two more wounds.
UNBRIDLED_CARNAGE_MIN_GAIN = 2.0


def is_active(squad):
    return bool(getattr(squad, "unbridled_carnage_active", False))


def adjusted_weapon(weapon, squad):
    """+1 A on this unit's melee weapons while the grant is up. A copy."""
    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE or not is_active(squad):
        return weapon
    boosted = copy.copy(weapon)
    boosted.attacks = weapon.attacks + UNBRIDLED_CARNAGE_ATTACKS
    boosted.attacks_notation = dice_notation.plus(
        getattr(weapon, "attacks_notation", None), UNBRIDLED_CARNAGE_ATTACKS)
    return boosted


def reset_phase(squads=()):
    for squad in squads or ():
        if getattr(squad, "unbridled_carnage_active", False):
            squad.unbridled_carnage_active = False


def is_eligible_target(squad):
    """TARGET, both clauses: a friendly BOYZ unit that made a charge move this
    turn, of a player fielding Green Tide."""
    return (squad is not None and green_tide.fields_green_tide(getattr(squad, "owner", None))
            and green_tide.is_boyz_unit(squad)
            and bool(getattr(squad, "charged_this_turn", False)))


def expected_extra_wounds(squad, target):
    """Wounds one more attack per living model is expected to add against
    `target` - each model's best melee weapon, one attack of it. Inherits
    game/damage_estimate.py's caveats (no re-rolls, no Sustained/Lethal Hits)."""
    from game import damage_estimate as de
    from game.fight import effective_weapon_skill
    if squad is None or target is None or not any(not m.is_dead() for m in target.models):
        return 0.0
    profile, _ = de.defender_soak(target)
    total = 0.0
    for model in squad.models:
        if model.is_dead():
            continue
        best = 0.0
        for weapon in model.weapons:
            if getattr(weapon, "weapon_type", None) != MELEE or weapon.extra_attacks:
                continue
            best = max(best, de.expected_wounds(
                weapon, UNBRIDLED_CARNAGE_ATTACKS, effective_weapon_skill(model, weapon), profile))
        total += best
    return total


class UnbridledCarnageController:
    """A panel button (game/proactive_stratagems.py): can_use / use / panel_label."""

    def __init__(self, stratagem_controller, turn_tracker=None, fight_controller=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.fight_controller = fight_controller
        self.game_log = game_log
        self._stratagem = Stratagem(UNBRIDLED_CARNAGE_NAME, UNBRIDLED_CARNAGE_CP, self._grant)

    def panel_label(self, squad):
        return f"{UNBRIDLED_CARNAGE_NAME} ({UNBRIDLED_CARNAGE_CP} CP) - +1 A on melee attacks"

    def reset_phase(self, squads=()):
        reset_phase(squads)

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None or self.fight_controller is None:
            return False
        if self.turn_tracker.phase != PHASE_FIGHT:
            return False
        if is_active(squad) or not is_eligible_target(squad):
            return False
        fc = self.fight_controller
        if squad in getattr(fc, "fought_squad_ids", ()) or getattr(fc, "fighting_squad", None) is squad:
            return False
        if not fc.is_eligible_to_fight(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.unbridled_carnage_active = True
            if self.game_log is not None:
                self.game_log.add(f"{UNBRIDLED_CARNAGE_NAME}: {squad.name}'s melee attacks have "
                                  "+1 A this phase.")
        return True
