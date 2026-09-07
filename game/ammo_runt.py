"""Flash Gitz' "Ammo Runt" wargear ability, as supplied by the user (not a
rule from the generic 40k core rulebook, so it lives in its own module - same
reasoning as game/gun_crazy_showoffs.py for that datasheet's OWN ability).

RULE: Once per battle, when this unit is selected to shoot, it can use this
ability. If it does, until the end of the phase, ranged weapons equipped by
models in this unit have the [LETHAL HITS] ability.

SHAPED LIKE NOVA CHARGE, WITH TWO DIFFERENCES
----------------------------------------------
The Riptide's Nova Charge (game/nova_charge.py) has the same trigger - once
per battle, offered when the unit is selected to shoot - so this reuses that
shape: the offer is raised from ShootingController.start_shooting(), and
declining is a real option, because holding it for a better target is the
whole point of a once-per-battle resource.

What differs:
  * Nova Charge grants its keyword to ONE chosen weapon, tracked by weapon
    instance. This grants it to every ranged weapon in the unit, so it is a
    UNIT flag (like game/arrokon_protocol.py's) rather than a per-weapon
    ledger - there is no choice of weapon to make, only whether to use it.
  * It is a WARGEAR item, not a printed ability: only a unit that actually
    took the Ammo Runt has it, which is why the flag lives on the token
    (`ammo_runt`) rather than on the UnitProfile class.

"ONCE PER BATTLE" vs "UNTIL THE END OF THE PHASE"
-------------------------------------------------
Two different lifetimes, tracked separately and deliberately: `used` is
never cleared (a spent Ammo Runt stays spent), while the granted keyword is
cleared on every phase change by reset_phase(), alongside every other
per-phase grant in main.py's own block.

NOT OFFERED FOR A SNAP SHOT
---------------------------
start_snap_shooting() deliberately does not raise the offer. Fire Overwatch
(15.08/15.09) happens in the opponent's Movement phase, and this ability's
own trigger is "when this unit is selected to shoot" in the shooting step -
the same line game/nova_charge.py draws, for the same reason.

WHO DECIDES
-----------
`auto_players` - main.py passes the AI's side, per the user ("die ki soll das
bei der ersten gelegenheit deterministisch benutzen und gut"). For those
players the ability is simply used the first time the unit is selected to
shoot; there is no relevance gate, because unlike 'Ard as Nails or Stim
Injectors this costs no CP and forecloses nothing - the only thing "saving
it" can buy is a better target later, and the AI has no way to know a better
one is coming. Anyone else keeps the DecisionManager prompt and the choice,
the same auto_players split game/ard_as_nails.py and game/spirit_of_gork.py
use.
"""

import copy

from game.weapons import RANGED
from game import ai_mode


def unit_has_ammo_runt(squad):
    """True while at least one live model carrying the wargear is in the
    unit - the rule 19.04 reading every other datasheet ability here uses."""
    if squad is None:
        return False
    return any(getattr(m, "ammo_runt", False) for m in squad.models if not m.is_dead())


def ammo_runt_adjusted_weapon(weapon, squad):
    """Grants [LETHAL HITS] (24.23) to a RANGED weapon while the ability is
    up on its unit.

    A real characteristic change on a shallow copy - the shared
    WeaponProfile instance is never mutated, same reasoning as every other
    adjuster in this codebase. Granting never removes the keyword from a
    weapon that already had it."""
    if weapon.weapon_type != RANGED or weapon.lethal_hits or squad is None:
        return weapon
    if not getattr(squad, "ammo_runt_active", False):
        return weapon
    boosted = copy.copy(weapon)
    boosted.lethal_hits = True
    return boosted


class AmmoRuntController:
    """Offers the ability when a unit carrying an Ammo Runt is selected to
    shoot. ShootingController calls offer(); main.py clears the grant on
    every phase change.

    `auto_players` is the set of players who use it outright at the first
    opportunity rather than being asked - see the module docstring."""

    def __init__(self, decision_manager=None, game_log=None, auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._used = set()  # id(squad) - once per battle, never cleared

    def has_been_used(self, squad):
        return id(squad) in self._used

    def can_use(self, squad):
        if squad is None:
            return False
        if self.has_been_used(squad):
            return False
        if getattr(squad, "ammo_runt_active", False):
            return False
        return unit_has_ammo_runt(squad)

    def offer(self, squad):
        """Resolves the ability for this activation. Returns True if that
        actually did something - used it outright for an auto_players side,
        or opened a prompt for anyone else."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players:
            self._use(squad)
            return True
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: Ammo Runt (once per battle) - give this unit's ranged weapons "
            f"[LETHAL HITS] until the end of the phase?",
            [
                ("Use the Ammo Runt", lambda: self._use(squad)),
                ("Save it for later", lambda: None),
            ],
        )
        return True

    def _use(self, squad):
        self._used.add(id(squad))
        squad.ammo_runt_active = True
        if self.game_log is not None:
            self.game_log.add(
                f"{squad.name} uses its Ammo Runt: its ranged weapons have [LETHAL HITS] "
                f"until the end of the phase."
            )

    def reset_phase(self, squads=()):
        """"Until the end of the phase" only - the once-per-battle record in
        `_used` is deliberately NOT cleared here."""
        for squad in squads:
            squad.ammo_runt_active = False
