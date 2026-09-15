"""Stormboyz' Rokkit Charge (2026-09 Ork codex).

RULE (verbatim, rules/orks/Stormboyz.md):
  "Rokkit Charge: When this unit is selected to fight, if this unit made a
   charge move this turn, you can use this ability. If you do, this unit's
   melee attacks have:
   - +1 A and S.
   - [Hazardous]."

WHERE IT HANGS: "when this unit is selected to fight" is
FightController._start_fighting(), the one place rule 12.04's selection
happens for both routes into it - the instant the Plasmacyte and Path of the
Warrior are offered at, before any dice.

THE GRANT is a Squad flag for the phase, read in the fight adjuster chain:
+1 Attacks and +1 Strength on EVERY melee weapon (read per weapon, the accepted
reading - a dice-notation characteristic takes the +1 on its flat bonus, the
way game/psychic_communion.py does it) and [HAZARDOUS]. The hazard ledger in
game/fight.py reads the adjusted weapon, so each weapon used rolls its test.

"You can use this ability" is a trade (extra damage against hazard losses), so
a human is asked every time. The AI answers through an injected verdict
(ai/agent_driver.py's rokkit_charge_verdict()), 0 API calls; with no verdict an
auto player uses it outright.
"""

import copy

from game import ai_mode
from game.dice_notation import DiceNotation
from game.squad import unit_wide_ability
from game.weapons import MELEE

ROKKIT_CHARGE_NAME = "Rokkit Charge"
ROKKIT_CHARGE_BONUS = 1


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "rokkit_charge"))


def is_active(squad):
    return bool(getattr(squad, "rokkit_charge_active", False))


def _plus(notation):
    if notation is None:
        return None
    return DiceNotation(notation.sides, notation.bonus + ROKKIT_CHARGE_BONUS, notation.dice)


def adjusted_weapon(weapon, squad):
    """+1 A, +1 S and [HAZARDOUS] on a melee weapon while the grant is up. A
    copy - the shared WeaponProfile instance is never mutated."""
    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE or not is_active(squad):
        return weapon
    boosted = copy.copy(weapon)
    boosted.attacks = weapon.attacks + ROKKIT_CHARGE_BONUS
    boosted.attacks_notation = _plus(getattr(weapon, "attacks_notation", None))
    boosted.strength = weapon.strength + ROKKIT_CHARGE_BONUS
    if getattr(weapon, "strength_notation", None) is not None:
        boosted.strength_notation = _plus(weapon.strength_notation)
    boosted.hazardous = True
    return boosted


def reset_phase(squads=()):
    for squad in squads or ():
        if getattr(squad, "rokkit_charge_active", False):
            squad.rokkit_charge_active = False


class RokkitChargeController:
    def __init__(self, decision_manager=None, game_log=None, auto_players=(), verdict=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self.verdict = verdict  # callable(squad) -> bool, the AI's rule; injected (game/ must not import ai/)

    def can_use(self, squad):
        return (has_ability(squad) and bool(getattr(squad, "charged_this_turn", False))
                and not is_active(squad))

    def offer(self, squad):
        """Called from FightController._start_fighting()."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players:
            if self.verdict is not None and not self.verdict(squad):
                if self.game_log is not None:
                    self.game_log.add(f"{squad.name} does not use {ROKKIT_CHARGE_NAME}.")
                return False
            return self.use(squad)
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: {ROKKIT_CHARGE_NAME} - +1 Attacks and +1 Strength on this unit's "
            f"melee attacks, and they gain [HAZARDOUS]?",
            [
                ("Use Rokkit Charge", lambda s=squad: self.use(s)),
                ("Decline", lambda: None),
            ],
        )
        return True

    def use(self, squad):
        if not self.can_use(squad):
            return False
        squad.rokkit_charge_active = True
        if self.game_log is not None:
            self.game_log.add(f"{squad.name} uses {ROKKIT_CHARGE_NAME}: +1 A and +1 S on its melee "
                              "attacks, which gain [HAZARDOUS].")
        return True

    def reset_phase(self, squads=()):
        reset_phase(squads)
