"""Spirit Conclave Stratagem: Seer's Eye (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Spirit Conclave.md):
  WHEN:   Your Shooting phase or the Fight phase.
  TARGET: One AELDARI PSYKER model from your army and one friendly WRAITH
          CONSTRUCT unit within 12" of it that has not been selected to shoot
          or fight this phase.
  EFFECT: Select one enemy unit visible to your PSYKER model. Until the end of
          the phase, each time a model in your WRAITH CONSTRUCT unit makes an
          attack that targets that enemy unit, you can ignore any or all
          modifiers to the Armour Penetration and/or Damage characteristics of
          that attack.
  RESTRICTIONS: none printed.

"IGNORE ANY OR ALL MODIFIERS TO AP AND/OR DAMAGE" HAD NO LIST TO IGNORE, and
that is the whole engineering problem. The HIT roll has a real modifier list
(game/modifiers.py), and three abilities already filter it. AP and Damage do
not: they come out of _adjusted_weapon() as flat values on a shallow copy, with
every source having already overwritten them. By the time the Save roll reads
the AP, there is nothing left that remembers what changed it.

SO IT IS ANSWERED BY COMPARISON, not by a ledger. The adjusted weapon is
compared against its own PRINTED class - which is the untouched original, since
every adjuster copies before writing - and the BETTER of the two is taken per
characteristic. No new bookkeeping, and it cannot drift from the chain, because
it reads the chain's own output.

"ANY OR ALL" IS RESOLVED AUTOMATICALLY, and this is the same reading Kauyon's
Patient Hunter writes out for the identical wording: there is no board state in
which a player wants to KEEP a modifier that made their own attack worse, so a
prompt per attack would be rule 15.01's cost with none of its choice. Taking
the better of printed and adjusted is exactly "ignore the ones that hurt, keep
the ones that help".

BETTER MEANS: AP more NEGATIVE, Damage HIGHER. Written out because the two run
in opposite numeric directions and a single min()/max() would silently be right
for one and wrong for the other.

A DAMAGE NOTATION IS LEFT ALONE. Nine weapons in this repo print a rolled
Damage (D6+1 and friends); comparing a resolved number against a notation is
meaningless, so a weapon whose printed Damage is a notation keeps whatever the
chain produced. Named rather than left as a silent branch - the same call
game/branching_fates.py makes when it refuses a multi-die roll.

THE MARK IS PER (WRAITH UNIT, ENEMY UNIT). "each time a model in your unit
makes an attack that targets THAT enemy unit" - so the same unit shooting at a
second target gets nothing, which is the difference between this and a plain
"until the end of the phase" buff. Stored on the wraith unit as the enemy it
was pointed at.

AELDARI PSYKER, NOT ASURYANI - as printed, and confirmed with the user. The two
are different sets in this engine (game/aeldari_detachments.py), and Soul
Bridge next door says ASURYANI, so the difference is deliberate on the card
rather than sloppy transcription.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import (aeldari_detachments, ignore_characteristic_modifiers,
                  shepherds_of_the_dead)
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING
from game import ai_mode

SEERS_EYE_NAME = "Seer's Eye"
SEERS_EYE_CP = 1

#: 'one friendly WRAITH CONSTRUCT unit within 12" of it'.
SEERS_EYE_RANGE_IN = 12.0

SEERS_EYE_UNIT_KEYWORD = "WRAITH CONSTRUCT"

SETTING = shepherds_of_the_dead.SETTING


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def marked_target(squad):
    """The enemy unit this unit was pointed at, or None."""
    return getattr(squad, "seers_eye_target", None)


def applies(squad, target_squad):
    """"an attack that targets THAT enemy unit" - per pair, not per phase."""
    return target_squad is not None and marked_target(squad) is target_squad


#: The two characteristics this card names - NOT Strength, which Aspect Host's
#: Warrior Focus adds. Each rule passes its own printed list, so neither can
#: quietly ignore a characteristic its card does not mention.
SEERS_EYE_CHARACTERISTICS = (ignore_characteristic_modifiers.ARMOUR_PENETRATION,
                             ignore_characteristic_modifiers.DAMAGE)


def adjusted_weapon(weapon, squad, target_squad):
    """Undo every WORSENING modifier to AP and Damage, keep every improving
    one.

    Runs LAST in the chain, and reads that chain's own output against the
    printed class - so it needs no ledger and cannot fall out of step with a
    new adjuster. The comparison itself lives in
    game/ignore_characteristic_modifiers.py, extracted when Warrior Focus
    became its second consumer."""
    if weapon is None or not applies(squad, target_squad):
        return weapon
    return ignore_characteristic_modifiers.restore(
        weapon, SEERS_EYE_CHARACTERISTICS)


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.seers_eye_target = None


def eligible_unit(squad):
    """"one friendly WRAITH CONSTRUCT unit"."""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return unit_has_datasheet_keyword(squad, SEERS_EYE_UNIT_KEYWORD)


def psyker_models_for(player, all_tokens=()):
    """"One AELDARI PSYKER model from your army" - AELDARI, not ASURYANI. Its
    own predicate for that reason."""
    out = []
    for token in all_tokens or ():
        squad = getattr(token, "squad", None)
        if squad is None or squad.owner != player or token.is_dead():
            continue
        if not getattr(token.profile, "psyker", False):
            continue
        if not aeldari_detachments.is_aeldari_unit(squad):
            continue
        out.append(token)
    return out


class SeersEyeController:
    """A Shooting- or Fight-phase panel button."""

    def __init__(self, stratagem_controller, all_tokens=None, visible=None,
                 shooting_controller=None, fight_controller=None,
                 turn_tracker=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        #: visible(observer_model, target_model) -> bool. Optional, like every
        #: other line-of-sight collaborator here; without one every enemy
        #: counts as visible, which is what a headless harness gets.
        self.visible = visible
        self.shooting_controller = shooting_controller
        self.fight_controller = fight_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._pending = {}
        self._stratagem = Stratagem(
            name=SEERS_EYE_NAME, cp_cost=SEERS_EYE_CP, effect=self._mark,
        )

    def panel_label(self, squad):
        return ("%s (%d CP) - ignore AP and Damage penalties against one unit"
                % (SEERS_EYE_NAME, SEERS_EYE_CP))

    def psykers_near(self, squad):
        """'One AELDARI PSYKER model ... and one friendly WRAITH CONSTRUCT unit
        within 12" of IT' - the distance is psyker-to-unit, so both halves are
        answered together."""
        mine = [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]
        if not mine:
            return []
        out = []
        for psyker in psyker_models_for(squad.owner, self.all_tokens):
            if any(((m.x_in - psyker.x_in) ** 2 + (m.y_in - psyker.y_in) ** 2) ** 0.5
                   <= SEERS_EYE_RANGE_IN for m in mine):
                out.append(psyker)
        return out

    def visible_enemies(self, squad, psyker):
        """"Select one enemy unit VISIBLE to your PSYKER model" - visible to
        the psyker, not to the unit that will be shooting. Its own clause, and
        the reason the psyker is carried this far."""
        out = []
        for token in (self.all_tokens or ()):
            enemy = getattr(token, "squad", None)
            if enemy is None or enemy.owner == squad.owner or token.is_dead():
                continue
            if enemy in out:
                continue
            if self.visible is None or self.visible(psyker, token):
                out.append(enemy)
        return out

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
        if marked_target(squad) is not None:
            return False
        if not eligible_unit(squad):
            return False
        psykers = self.psykers_near(squad)
        if not psykers:
            return False
        if not self.visible_enemies(squad, psykers[0]):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad, enemy_squad=None):
        if not self.can_use(squad):
            return False
        psyker = self.psykers_near(squad)[0]
        candidates = self.visible_enemies(squad, psyker)
        if enemy_squad is None:
            if len(candidates) > 1 and squad.owner not in self.auto_players \
                    and self.decision_manager is not None:
                self.decision_manager.request(
                    squad.owner,
                    "%s: %s ignores AP and Damage penalties against which unit?"
                    % (SEERS_EYE_NAME, squad.name),
                    [(e.name, (lambda s=squad, e=e: self.use(s, e)), e)
                     for e in candidates],
                    is_stratagem=True,
                )
                return True
            enemy_squad = candidates[0]
        self._pending[squad.owner] = (squad, enemy_squad)
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _mark(self, controller, player, targets):
        squad, enemy = self._pending.pop(player, (None, None))
        if squad is None or enemy is None:
            return
        squad.seers_eye_target = enemy
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s ignores AP and Damage penalties against %s this phase."
                % (SEERS_EYE_NAME, squad.name, enemy.name))
