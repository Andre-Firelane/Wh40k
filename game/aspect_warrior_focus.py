"""Aspect Host Stratagem: Warrior Focus (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Aspect Host.md):
  WHEN:   Your Shooting phase or the Fight phase.
  TARGET: One ASPECT WARRIORS or AVATAR OF KHAINE unit from your army that has
          not been selected to shoot or fight this phase.
  EFFECT: Until the end of the phase, each time a model in your unit makes an
          attack, you can ignore any or all modifiers to that attack's
          Ballistic Skill, Weapon skill, Strength, Armour Penetration and
          Damage characteristics and/or any or all modifiers to the Hit roll.
  RESTRICTIONS: none printed.

  (The lower-case "Weapon skill" is Wahapedia's rendering, transcribed rather
  than corrected - the same treatment the Spirit Conclave artefacts get.)

FIVE PRINTED NOUNS, TWO MECHANISMS. That is the whole shape of this module:

  * BALLISTIC SKILL, WEAPON SKILL and the HIT ROLL all land on ONE threshold in
    this engine, and _hit_modifiers() already knows how to drop every worsening
    entry from it - that is exactly what UnitProfile.ignores_hit_modifiers does
    for the Riptide's Weapon Support System and the Dark Reapers' Inescapable
    Accuracy. So three of the five nouns are one existing filter, and this
    module simply joins it.
  * STRENGTH, ARMOUR PENETRATION and DAMAGE have no modifier list at all - they
    are flat values on a shallow copy by the time anything reads them. Those go
    through game/ignore_characteristic_modifiers.py, whose second consumer this
    is (Spirit Conclave's Seer's Eye was the first, with two of the three).

WIDER THAN SEER'S EYE IN TWO WAYS, both printed: it adds Strength, and it
applies to EVERY attack this unit makes rather than only to attacks against one
marked enemy. So it is a plain per-phase flag where that one is a per-pair mark.

"ANY OR ALL" IS RESOLVED AUTOMATICALLY - see the extraction's own docstring for
why (there is no board state in which keeping a modifier that worsened your own
attack is the better play, so a prompt per attack would cost a decision without
offering one). The same reading Kauyon and rule 24.29 [PSYCHIC] already take.

BOTH PHASES, and the asymmetry is printed: "YOUR Shooting phase" but "the Fight
phase", which belongs to nobody - so the Fight-phase half carries no owner
check. Its own test line, because one missing word is the whole difference.

AVATAR OF KHAINE IS NAMED SEPARATELY from ASPECT WARRIORS and is not one: it
carries neither the keyword nor the Aspect Shrine tokens the other Aspect Host
Stratagems spend, which is why it is listed by name on three of the six cards.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import (aeldari_detachments, detachment_gate,
                  ignore_characteristic_modifiers)
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

WARRIOR_FOCUS_NAME = "Warrior Focus"
WARRIOR_FOCUS_CP = 1

#: "ASPECT WARRIORS or AVATAR OF KHAINE" - the pairing three of this
#: detachment's six Stratagems print.
WARRIOR_FOCUS_KEYWORDS = ("ASPECT WARRIORS", "AVATAR OF KHAINE")

#: All three of the extraction's characteristics: this card names Strength as
#: well, where Seer's Eye names only AP and Damage.
WARRIOR_FOCUS_CHARACTERISTICS = ignore_characteristic_modifiers.ALL_CHARACTERISTICS

SETTING = "ASPECT_HOST_PLAYERS"


def has_detachment(player):
    return detachment_gate.has_detachment(player, SETTING)


def is_active(squad):
    return bool(getattr(squad, "warrior_focus_active", False))


def ignores_hit_modifiers(squad):
    """The Ballistic Skill / Weapon Skill / Hit roll third of the card.

    Read by BOTH attack chains' _hit_modifiers(), beside the two datasheet
    abilities that print the same permission."""
    return is_active(squad)


def adjusted_weapon(weapon, squad):
    """The Strength / AP / Damage two thirds. Runs LAST in the chain so it sees
    everything the chain did."""
    if weapon is None or not is_active(squad):
        return weapon
    return ignore_characteristic_modifiers.restore(
        weapon, WARRIOR_FOCUS_CHARACTERISTICS)


def eligible_unit(squad):
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, k) for k in WARRIOR_FOCUS_KEYWORDS)


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.warrior_focus_active = False


class WarriorFocusController:
    """A Shooting- or Fight-phase panel button."""

    def __init__(self, stratagem_controller, shooting_controller=None,
                 fight_controller=None, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.fight_controller = fight_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=WARRIOR_FOCUS_NAME, cp_cost=WARRIOR_FOCUS_CP, effect=self._grant,
        )

    def panel_label(self, squad):
        return ("%s (%d CP) - ignore penalties to BS/WS, S, AP and Damage"
                % (WARRIOR_FOCUS_NAME, WARRIOR_FOCUS_CP))

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        phase = self.turn_tracker.phase
        if phase == PHASE_SHOOTING:
            if squad.owner != self.turn_tracker.active_player:
                return False           # "YOUR Shooting phase"
            if self.shooting_controller is not None \
                    and self.shooting_controller.active_squad is squad:
                return False           # "has not been selected to shoot"
        elif phase == PHASE_FIGHT:
            # "or THE Fight phase" - it belongs to nobody, so no owner check.
            if self.fight_controller is not None \
                    and getattr(self.fight_controller, "fighting_squad", None) is squad:
                return False           # "...or fight this phase"
        else:
            return False
        if is_active(squad):
            return False
        if not eligible_unit(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.warrior_focus_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s ignores penalties to its Hit rolls, Strength, "
                    "Armour Penetration and Damage this phase."
                    % (WARRIOR_FOCUS_NAME, squad.name))
