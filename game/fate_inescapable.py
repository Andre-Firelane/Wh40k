"""Seer Council's "Fate Inescapable" (1CP, Battle Tactic).

RULE (printed, word for word):
  WHEN: "Your Shooting phase"
  TARGET: "One ASURYANI INFANTRY unit from your army (excluding WRAITH
  CONSTRUCT units) that has not been selected to shoot this phase and is within
  9" of one or more friendly ASURYANI PSYKER models"
  EFFECT: "Until the end of the phase, ranged weapons equipped by models in your
  unit have the [IGNORES COVER] ability and each time a model in your unit makes
  an attack, on a Critical Wound, improve the Armour Penetration characteristic
  of that attack by 1."

TWO EFFECTS, BOTH ALREADY HAVE A HOME
-------------------------------------
The [IGNORES COVER] half joins the five terms already folded in
game/shooting.py's _cover_ignored_for_group() - a unit-level grant, so it sits
next to UnitProfile.ignores_cover and Exemplars of Mont'ka rather than being
baked onto a copied weapon.

The AP half is Cadre Fireblade's Crack Shot with a different arithmetic:
"on a Critical Wound, THIS attack has a different AP" needs the critical wounds
pulled out of the group's normal Save roll and given their own, because a
non-critical wound from the very same attack still uses the printed AP. That
split exists (_begin_crit_ap_save()); this is its second source, which is why the
two now fold in game/crit_ap.py.

IMPROVE, not override. Crack Shot forces AP to a flat -3; this shifts it by one,
so a weapon at AP-2 becomes AP-3 and one at AP0 becomes AP-1. AP is stored
negative here, so "improve by 1" is `ap - 1`.

TARGET requires the unit not to have shot yet, which is what makes this a
proactive stratagem the owner buys before activating - an ActionPanel button,
not a DecisionManager break point, the same shape as The Arro'kon Protocol.
"""

import copy
from game.stratagems import Stratagem

FATE_INESCAPABLE_CP = 1
FATE_INESCAPABLE_NAME = "Fate Inescapable"
FATE_INESCAPABLE_AP_IMPROVEMENT = 1


def applies(squad):
    return squad is not None and getattr(squad, "fate_inescapable_active", False)


def reset_phase(squads=()):
    """"Until the end of the phase"."""
    for squad in squads:
        squad.fate_inescapable_active = False


def fate_adjusted_weapon(weapon):
    """A shallow copy with AP improved by 1 - the shared WeaponProfile instance
    is never mutated, the same convention every other *_adjusted_weapon() helper
    here follows."""
    adjusted = copy.copy(weapon)
    adjusted.ap = weapon.ap - FATE_INESCAPABLE_AP_IMPROVEMENT
    return adjusted


class FateInescapableController:
    """Proactive, so no DecisionManager hook: an ActionPanel button for a human,
    and nothing for the AI (Aeldari are human-only here)."""

    def __init__(self, stratagem_controller=None, shooting_controller=None,
                 turn_tracker=None, game_log=None, all_tokens=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self._stratagem = Stratagem(
            name=FATE_INESCAPABLE_NAME, cp_cost=FATE_INESCAPABLE_CP, effect=self._effect,
        )

    def can_use(self, squad):
        from game.forewarned import eligible_unit, near_friendly_psyker
        from game.turn import PHASE_SHOOTING
        if squad is None or self.stratagem_controller is None:
            return False
        if applies(squad):
            return False
        if self.turn_tracker is None or self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if self.turn_tracker.turn_owner != squad.owner:
            return False   # "YOUR Shooting phase"
        # "has not been selected to shoot this phase" - both forms of it: an
        # activation already finished, and one in progress right now.
        if self.shooting_controller is not None:
            if squad in getattr(self.shooting_controller, "shot_squad_ids", ()):
                return False
            if self.shooting_controller.active_squad is squad:
                return False
        # The unit conditions are Forewarned's, word for word - read from there
        # rather than duplicated.
        if not eligible_unit(squad):
            return False
        if not near_friendly_psyker(squad, self.all_tokens):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _effect(self, controller, player, targets):
        squad = targets[0]
        squad.fate_inescapable_active = True
        if self.game_log is not None:
            self.game_log.add(
                f"Fate Inescapable: until the end of the phase, {squad.name}'s ranged weapons "
                "have [IGNORES COVER] and a Critical Wound improves their Armour Penetration by 1."
            )
