"""Mont'ka Stratagem: Focused Fire (1CP).

RULE (verbatim, rules/tau_empire/detachments/Mont'ka.md):
  WHEN:   Start of your Shooting phase.
  TARGET: Two T'AU EMPIRE units from your army that have not been selected to
          shoot this phase, and one enemy unit.
  EFFECT: Until the end of the phase, each time a model in either of your units
          makes an attack, it can only target that enemy unit (and only if it
          is an eligible target for that attack), and when resolving that
          attack, improve the Armour Penetration characteristic by 1.
  RESTRICTIONS: You cannot use this Stratagem during the fourth or fifth battle
          rounds.

IT IS A COST AS WELL AS A BONUS
--------------------------------
"it can ONLY target that enemy unit" is a restriction the buyer accepts, not a
side effect - two units lose their choice of target for the phase in exchange
for +1 AP. Both halves live on the same per-squad mark, so a unit cannot end up
with the bonus and not the restriction (or the reverse, which would be worse).

The "(and only if it is an eligible target for that attack)" clause means the
restriction NARROWS the legal set rather than forcing a shot: a unit with no
line of sight to the named enemy simply has nothing to shoot, which is the
cost landing.

THREE THINGS ARE CHOSEN, SO THE PURCHASE IS THREE STEPS
--------------------------------------------------------
The panel button names the first unit (that is what a per-unit button can say),
and the second unit and the enemy are picked through DecisionManager. Both
selections are made BEFORE the CP is spent, so backing out costs nothing -
a Stratagem that took the CP and then found no legal enemy would be the
Fehlerklasse-5 mistake of offering something that buys nothing.
"""

import copy

from game import montka, tau_detachments
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

FOCUSED_FIRE_CP = 1
FOCUSED_FIRE_NAME = "Focused Fire"
# "You cannot use this Stratagem during the fourth or fifth battle rounds."
FOCUSED_FIRE_LATEST_ROUND = 3


def focus_target(squad):
    """The enemy unit this squad is locked onto, or None."""
    return getattr(squad, "focused_fire_target", None)


def restricts_targets(squad):
    return focus_target(squad) is not None


def target_allowed(squad, target_squad):
    """"it can only target that enemy unit" - read by
    ShootingController._is_valid_target_squad()."""
    focus = focus_target(squad)
    return focus is None or target_squad is focus


def adjusted_weapon(weapon, squad, target_squad):
    """+1 AP, and only against the named enemy - the same mark, so the bonus
    cannot come apart from the restriction."""
    if weapon is None or target_squad is None:
        return weapon
    if focus_target(squad) is not target_squad:
        return weapon
    granted = copy.copy(weapon)
    granted.ap = weapon.ap - 1   # AP is stored negative; "improve" is more negative
    return granted


class FocusedFireController:
    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, all_tokens=None, decision_manager=None,
                 game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.decision_manager = decision_manager
        self.game_log = game_log
        self._pending = None       # (first, second, enemy) while being assembled
        self._stratagem = Stratagem(
            name=FOCUSED_FIRE_NAME, cp_cost=FOCUSED_FIRE_CP, effect=self._grant,
        )

    def reset_phase(self, squads=()):
        for squad in squads or ():
            squad.focused_fire_target = None

    # -- candidates -------------------------------------------------------
    def _squads(self):
        seen = {}
        for token in self.all_tokens:
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen[id(squad)] = squad
        return list(seen.values())

    def _is_partner(self, squad, other):
        """"Two T'AU EMPIRE units ... that have not been selected to shoot"."""
        if other is squad or getattr(other, "owner", None) != squad.owner:
            return False
        if not tau_detachments.is_tau_unit(other):
            return False
        if restricts_targets(other):
            return False
        if self.shooting_controller is None:
            return False
        if self.shooting_controller.active_squad is other:
            return False
        return self.shooting_controller.can_shoot(other)

    def partners_for(self, squad):
        return sorted((o for o in self._squads() if self._is_partner(squad, o)),
                      key=lambda s: s.name)

    def enemies_for(self, squad):
        return sorted((o for o in self._squads()
                       if getattr(o, "owner", None) not in (None, squad.owner)
                       and any(not m.is_dead() for m in o.models)),
                      key=lambda s: s.name)

    # -- the Stratagem ----------------------------------------------------
    def panel_label(self, squad):
        return (f"{FOCUSED_FIRE_NAME} ({FOCUSED_FIRE_CP} CP) - "
                "+1 AP, but this unit and one other may only shoot one target")

    def can_use(self, squad):
        if squad is None or self.shooting_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False
        if getattr(self.turn_tracker, "battle_round", 0) > FOCUSED_FIRE_LATEST_ROUND:
            return False
        if restricts_targets(squad):
            return False
        if not tau_detachments.has_detachment(squad.owner, montka.SETTING):
            return False
        if not tau_detachments.is_tau_unit(squad):
            return False
        if self.shooting_controller.active_squad is squad:
            return False
        if not self.shooting_controller.can_shoot(squad):
            return False
        # It names TWO of your units and one enemy - without a partner or an
        # enemy there is nothing to buy.
        if not self.partners_for(squad) or not self.enemies_for(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        """Opens the two selections. The CP is spent only once both are made."""
        if not self.can_use(squad):
            return False
        partners = self.partners_for(squad)
        if self.decision_manager is None:
            return self._choose_enemy(squad, partners[0])
        self.decision_manager.request(
            squad.owner,
            f"{FOCUSED_FIRE_NAME}: which second unit joins {squad.name}?",
            [(p.name, (lambda p=p: self._choose_enemy(squad, p)), p) for p in partners]
            + [("Cancel", lambda: None)],
        )
        return True

    def _choose_enemy(self, first, second):
        enemies = self.enemies_for(first)
        if not enemies:
            return False
        if self.decision_manager is None:
            return self._commit(first, second, enemies[0])
        self.decision_manager.request(
            first.owner,
            f"{FOCUSED_FIRE_NAME}: which enemy unit will {first.name} and {second.name} "
            "focus on for the rest of the phase?",
            [(e.name, (lambda e=e: self._commit(first, second, e)), e) for e in enemies]
            + [("Cancel", lambda: None)],
        )
        return True

    def _commit(self, first, second, enemy):
        self._pending = (first, second, enemy)
        used = self.stratagem_controller.use(first.owner, self._stratagem, [first])
        if not used:
            self._pending = None
        return used

    def _grant(self, controller, player, targets):
        pending, self._pending = self._pending, None
        if pending is None:
            return
        first, second, enemy = pending
        for squad in (first, second):
            squad.focused_fire_target = enemy
        if self.game_log is not None:
            self.game_log.add(
                f"{FOCUSED_FIRE_NAME}: {first.name} and {second.name} may only target "
                f"{enemy.name} this phase, with +1 Armour Penetration."
            )
