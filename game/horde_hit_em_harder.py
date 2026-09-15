"""War Horde Stratagem: Hit 'Em Harder (1CP).

RULE (verbatim, rules/orks/detachments/War Horde.md):
  WHEN:   Fight phase, when a friendly ORKS unit is selected to fight.
  TARGET: That ORKS unit.
  EFFECT: Your unit's melee attacks have [Lethal Hits].

"FIGHT PHASE" WITHOUT "YOUR" - the Fight phase is shared (rule 12.04), so both
players may buy it, and "selected to fight" is read the way every other
Stratagem with this WHEN reads it here (Hungry Void, Experimental
Modifications): a unit that is eligible to fight, has not fought and is not
fighting right now. The button stands above "Fight".

A KEYWORD GRANT WITH ONE READER - the adjuster chain. [LETHAL HITS] has no
eligibility gate of its own; game/fight.py's hit step and _crit_note() read it
off the weapon _adjusted_weapon() returns.

NEVER OFFERED WHEN IT BUYS NOTHING (error class 5): a unit whose every melee
weapon already has [LETHAL HITS] is refused.

THE AI (ai/agent_driver.py's _handle_hit_em_harder()) buys it when the grant is
expected to add HIT_EM_HARDER_MIN_GAIN wounds against the engaged enemy it helps
most - expected_lethal_gain() below, built from game/damage_estimate.py's pieces.
"""

import copy

from game import war_horde
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT
from game.weapons import MELEE

HIT_EM_HARDER_NAME = "Hit 'Em Harder"
HIT_EM_HARDER_CP = 1
#: The AI's rule: 1 CP for at least two more wounds.
HIT_EM_HARDER_MIN_GAIN = 2.0


def is_active(squad):
    return bool(getattr(squad, "hit_em_harder_active", False))


def adjusted_weapon(weapon, squad):
    """[LETHAL HITS] on this unit's melee weapons while the grant is up."""
    if weapon is None or not is_active(squad):
        return weapon
    if getattr(weapon, "weapon_type", None) != MELEE or weapon.lethal_hits:
        return weapon
    granted = copy.copy(weapon)
    granted.lethal_hits = True
    return granted


def reset_phase(squads=()):
    """"Until the end of the phase" - the grant is bought for one fight."""
    for squad in squads or ():
        if getattr(squad, "hit_em_harder_active", False):
            squad.hit_em_harder_active = False


def would_change_anything(squad):
    """Whether a living model of the unit carries a melee weapon without
    [LETHAL HITS] - otherwise the Stratagem buys nothing."""
    return any(getattr(w, "weapon_type", None) == MELEE and not w.lethal_hits
               for m in getattr(squad, "models", ()) or () if not m.is_dead()
               for w in m.weapons)


def expected_lethal_gain(squad, target):
    """Extra wounds [LETHAL HITS] is expected to add against `target`: every
    critical hit (an unmodified 6, 1 in 6 of the attacks) that would otherwise
    have had to roll to wound. Rule 04.01's one melee weapon per model is kept.
    Inherits game/damage_estimate.py's caveats (no re-rolls, no Sustained Hits)."""
    from game import damage_estimate as de
    if squad is None or target is None or not any(not m.is_dead() for m in target.models):
        return 0.0
    profile, _ = de.defender_soak(target)
    armour = de._skill_value(profile.armor_save, 7)
    invuln = de._skill_value(profile.invulnerable_save, 7)
    total = 0.0
    for model in squad.models:
        if model.is_dead():
            continue
        best = 0.0
        for weapon in model.weapons:
            if getattr(weapon, "weapon_type", None) != MELEE or weapon.lethal_hits:
                continue
            wound = de._threshold_chance(de.wound_threshold(weapon.strength, profile.toughness))
            fail_save = max(0.0, min(1.0, (min(armour - weapon.ap, invuln) - 1) / 6.0))
            damage = min(weapon.damage, max(1, profile.wounds))
            gain = weapon.attacks * (1.0 / 6.0) * (1.0 - wound) * fail_save * damage
            if weapon.extra_attacks:
                total += gain
            else:
                best = max(best, gain)
        total += best
    return total


class HitEmHarderController:
    """A panel button (game/proactive_stratagems.py): can_use / use / panel_label."""

    def __init__(self, stratagem_controller, turn_tracker=None, fight_controller=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.fight_controller = fight_controller
        self.game_log = game_log
        self._stratagem = Stratagem(HIT_EM_HARDER_NAME, HIT_EM_HARDER_CP, self._grant)

    def panel_label(self, squad):
        return f"{HIT_EM_HARDER_NAME} ({HIT_EM_HARDER_CP} CP) - [LETHAL HITS] on melee attacks"

    def reset_phase(self, squads=()):
        reset_phase(squads)

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None or self.fight_controller is None:
            return False
        if self.turn_tracker.phase != PHASE_FIGHT:
            return False
        if is_active(squad):
            return False
        if not war_horde.fields_war_horde(squad.owner) or not war_horde.is_orks_unit(squad):
            return False
        fc = self.fight_controller
        if squad in getattr(fc, "fought_squad_ids", ()) or getattr(fc, "fighting_squad", None) is squad:
            return False
        if not fc.is_eligible_to_fight(squad):
            return False
        if not would_change_anything(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.hit_em_harder_active = True
            if self.game_log is not None:
                self.game_log.add(f"{HIT_EM_HARDER_NAME}: {squad.name}'s melee attacks have "
                                  "[LETHAL HITS] this phase.")
        return True
