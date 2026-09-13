"""Canoptek Court Stratagem: Cynosure of Eradication (2CP).

RULE (verbatim, rules/necrons/detachments/Canoptek Court.md):
  WHEN:   The start of your Shooting phase or the start of the Fight phase.
  TARGET: One CRYPTEK or CANOPTEK unit from your army that is wholly within your
          army's Power Matrix.
  EFFECT: Until the end of the phase, weapons equipped by CRYPTEK or CANOPTEK
          models in your unit have the [DEVASTATING WOUNDS] ability.

A KEYWORD GRANT WITH ONE READER - the adjuster chain. [DEVASTATING WOUNDS] has no
eligibility gate of its own (unlike [ASSAULT] and [PISTOL]), so the grant lands on
the copied weapon in game/shooting.py's and game/fight.py's _adjusted_weapon(),
where the wound step and _crit_note() read it at roll time.

PER MODEL, not per unit. A Technomancer leading Necron Warriors makes a CRYPTEK
unit (19.03), so it is a legal TARGET - but only the Technomancer's own weapons are
"weapons equipped by CRYPTEK models". game/necron_detachments.py's attack_key()
keeps the two apart in 04.03 grouping, so the representative model is exact.

"THE START OF" IS READ FROM THE PHASE'S OWN LEDGERS, and the two halves differ:
  * your Shooting phase - the turn is yours and no unit has been selected to shoot
    yet (shot_squad_ids empty, nothing mid-activation);
  * the Fight phase - it belongs to nobody, so either player, while the Fight step
    has not begun (FightController.state == NOT_STARTED). NAMED READING: this is
    looser than "before the first Pile In", because the AI piles its own units in
    on its first frame of the phase - a strict reading would close a human's window
    in their own turn before they could click. A Pile In does not change what the
    grant is worth.

"WHOLLY WITHIN YOUR ARMY'S POWER MATRIX" is asked when the Stratagem is bought, the
moment its TARGET line is checked; moving out of the matrix later in the phase does
not take the grant away - the EFFECT names no such condition.
"""

import copy

from game import court_power_matrix, necron_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

CYNOSURE_NAME = "Cynosure of Eradication"
CYNOSURE_CP = 2
SETTING = "CANOPTEK_COURT_PLAYERS"
#: The AI buys it only when [DEVASTATING WOUNDS] is expected to push this many
#: extra wounds past saves - 2 CP is the most expensive Canoptek Court Stratagem.
CYNOSURE_MIN_EXPECTED_GAIN = 1.5


def is_active(squad):
    return bool(getattr(squad, "court_cynosure_active", False))


def model_qualifies(squad, model):
    return (necron_detachments.model_is_cryptek(squad, model)
            or necron_detachments.model_is_canoptek(squad, model))


def adjusted_weapon(weapon, squad, model):
    """[DEVASTATING WOUNDS] on the weapon of a CRYPTEK/CANOPTEK model of a unit
    under the grant. Copied, never mutated (the weapon-instance rule)."""
    if weapon is None or squad is None or not is_active(squad):
        return weapon
    if getattr(weapon, "devastating_wounds", False):
        return weapon
    if not model_qualifies(squad, model):
        return weapon
    granted = copy.copy(weapon)
    granted.devastating_wounds = True
    return granted


def reset_phase(squads=()):
    """"Until the end of the phase"."""
    for squad in squads or ():
        if getattr(squad, "court_cynosure_active", False):
            squad.court_cynosure_active = False


def expected_devastating_gain(squad, target, melee=False):
    """How many extra wounds [DEVASTATING WOUNDS] is expected to push past the
    target's saves: every critical wound (an unmodified 6, 1 in 6 of the wound
    rolls) that the save would have stopped.

    Built from game/damage_estimate.py's own pieces rather than a second copy of
    the arithmetic, and inheriting its caveats (no re-rolls, no [ANTI-X] crit
    thresholds, no cover). Only CRYPTEK/CANOPTEK models' weapons count - the
    grant does not reach anyone else's."""
    from game import damage_estimate as de
    if squad is None or target is None:
        return 0.0
    if not any(not m.is_dead() for m in target.models):
        return 0.0
    want = "melee" if melee else "ranged"
    profile, _ = de.defender_soak(target)
    armour = de._skill_value(profile.armor_save, 7)
    invuln = de._skill_value(profile.invulnerable_save, 7)
    total = 0.0
    for model in squad.models:
        if model.is_dead() or not model_qualifies(squad, model):
            continue
        printed = model.profile.weapon_skill if melee else model.profile.ballistic_skill
        best_selectable = 0.0
        for weapon in model.weapons:
            if getattr(weapon, "weapon_type", None) != want:
                continue
            if getattr(weapon, "devastating_wounds", False):
                continue   # already has it - the grant adds nothing to this weapon
            override = weapon.weapon_skill if melee else weapon.ballistic_skill
            hit = de._threshold_chance(de._skill_value(override if override is not None else printed))
            # P(the save would have SUCCEEDED) - exactly what a devastating
            # wound takes away. _threshold_chance() carries the "a 1 always
            # fails" floor, and a save of 7+ comes out as 0.
            saved = de._threshold_chance(min(armour - weapon.ap, invuln))
            damage = min(weapon.damage, max(1, profile.wounds))
            # An unmodified 6 always wounds, so 1 in 6 of the hits is a
            # critical wound whatever the Strength.
            value = weapon.attacks * hit * (1.0 / 6.0) * saved * damage
            if melee and not weapon.extra_attacks:
                best_selectable = max(best_selectable, value)   # rule 04.01: one melee weapon
            else:
                total += value
        total += best_selectable
    return total


class CynosureOfEradicationController:
    """A panel button (game/proactive_stratagems.py): can_use / use / panel_label."""

    def __init__(self, stratagem_controller, turn_tracker=None, shooting_controller=None,
                 fight_controller=None, power_matrix=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.shooting_controller = shooting_controller
        self.fight_controller = fight_controller
        self.power_matrix = power_matrix
        self.game_log = game_log
        self._stratagem = Stratagem(name=CYNOSURE_NAME, cp_cost=CYNOSURE_CP, effect=self._grant)

    def panel_label(self, squad):
        return (f"{CYNOSURE_NAME} ({CYNOSURE_CP} CP) - [DEVASTATING WOUNDS] on CRYPTEK/CANOPTEK "
                "weapons this phase")

    def at_start_of_phase_for(self, squad):
        """The WHEN, for this unit's owner - see the module docstring."""
        tt = self.turn_tracker
        if tt is None or squad is None:
            return False
        if tt.phase == PHASE_SHOOTING:
            if tt.turn_owner != squad.owner:
                return False
            sc = self.shooting_controller
            if sc is None:
                return False
            return sc.active_squad is None and not sc.shot_squad_ids
        if tt.phase == PHASE_FIGHT:
            fc = self.fight_controller
            if fc is None:
                return False
            from game import fight as fight_module
            return fc.state == fight_module.NOT_STARTED and not fc.fought_squad_ids
        return False

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None:
            return False
        if not self.at_start_of_phase_for(squad):
            return False
        if is_active(squad):
            return False
        if not court_power_matrix.is_court_unit(squad):
            return False
        if not court_power_matrix.unit_wholly_within(squad, self.power_matrix):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.court_cynosure_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{CYNOSURE_NAME}: weapons of CRYPTEK and CANOPTEK models in {squad.name} "
                    "have [DEVASTATING WOUNDS] until the end of the phase.")
