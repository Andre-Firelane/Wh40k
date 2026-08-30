"""Kroot Farstalkers' "Bounty Hunters", and the Pech'ra that rides with it.

BOUNTY HUNTERS (printed, word for word):
  "At the start of the battle, select one unit from your opponent's army. Each
   time a model in this unit makes an attack that targets that unit, that attack
   has the [LETHAL HITS] and [PRECISION] abilities."

A MARK CHOSEN ONCE, BEFORE ANYTHING HAPPENS. Every other mark in this engine is
set during play - Guide and Doom at the end of a Movement phase, Advanced
Scouting by a hit, Spotted by an Observer. This one is picked in the pre-battle
sequence and never moves for the rest of the game, which makes it the first
piece of state here that belongs to a DATASHEET and outlives every phase reset.

  * IT IS PER FARSTALKER UNIT, not per army: "select one unit" is read by "a
    model in THIS unit", so two Farstalker units each pick their own bounty.
    Hence a ledger keyed on the hunting squad.
  * IT GRANTS TWO KEYWORDS, and they land in different places - [LETHAL HITS]
    at the hit step (its critical hits wound automatically) and [PRECISION] at
    allocation (24.28 lets the attacker pick a CHARACTER). Both ride on the
    weapon, so a single adjuster in each attack step's chain covers both, and
    _crit_note() sees the [LETHAL HITS] at roll time as it must.
  * "AN ATTACK", not "a ranged attack" - so both steps read it, the same
    reading Advanced Scouting gets and the opposite of Structural Analyser.

PECH'RA (printed, word for word):
  "Ranged weapons equipped by the bearer's unit have the [IGNORES COVER]
   ability."

Unconditional and unit-wide once taken, so it is the simplest possible weapon
adjuster - but it is RANGED-only by its own wording, which is why it is chained
in game/shooting.py alone.

BOTH COPY RATHER THAN MUTATE, the standing rule: a mutated shared WeaponProfile
instance would follow the model out of this unit and into the next battle.
"""

import copy

from game.weapons import MELEE

BOUNTY_HUNTERS_LABEL = "Bounty Hunters"
PECHRA_LABEL = "Pech'ra"


def unit_has_bounty_hunters(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "bounty_hunters", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def unit_has_pechra(squad):
    """The Pech'ra is one model's wargear but its effect is unit-wide ("the
    BEARER'S UNIT"), so any() rather than all() - the same shape
    squad_has_guardian_drone() uses for the same reason."""
    if squad is None:
        return False
    return any(getattr(m.profile, "pechra", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def pechra_adjusted_weapon(weapon, squad):
    """[IGNORES COVER] on this unit's ranged weapons while a Pech'ra lives."""
    if weapon is None or getattr(weapon, "ignores_cover", False):
        return weapon
    if getattr(weapon, "weapon_type", None) == MELEE:
        return weapon
    if not unit_has_pechra(squad):
        return weapon
    granted = copy.copy(weapon)
    granted.ignores_cover = True
    return granted


class BountyHuntersController:
    """The bounty ledger: one enemy unit per Farstalker unit, for the battle.

    Kept on the controller rather than on the Squad for the reason
    SecondaryMissionController gives about card state: the mark belongs to a
    pairing of two units, and a field on one of them would have to be cleaned
    up by whoever kills the other."""

    def __init__(self, game_log=None, target_pick=None):
        self.game_log = game_log
        # target_pick(hunter, candidates) -> squad, so the AI uses the same
        # damage-value ranking as every other deterministic target choice;
        # None falls back to name order, which keeps a test reproducible.
        self.target_pick = target_pick
        self._bounties = {}   # id(hunting squad) -> the marked enemy squad

    def bounty_for(self, squad):
        return self._bounties.get(id(squad))

    def select_at_start_of_battle(self, squads):
        """"At the start of the battle, select one unit from your opponent's
        army" - once, for every Farstalker unit on the table.

        Not optional and not a prompt: the printed text says "select", and with
        the choice made before a single model has moved there is nothing to
        judge it on that a player could not judge better next turn. The pick is
        deterministic so a replay and a test agree."""
        picked = []
        for hunter in sorted((s for s in squads if unit_has_bounty_hunters(s)),
                             key=lambda s: s.name):
            if id(hunter) in self._bounties:
                continue
            enemies = sorted((s for s in squads if s.owner != hunter.owner),
                             key=lambda s: s.name)
            if not enemies:
                continue
            target = (self.target_pick(hunter, enemies) if self.target_pick
                      else enemies[0]) or enemies[0]
            self._bounties[id(hunter)] = target
            picked.append((hunter, target))
            if self.game_log:
                self.game_log.add(
                    f"{hunter.name} takes a bounty on {target.name} (Bounty Hunters).")
        return picked

    def applies(self, attacking_squad, target_squad):
        """Whether THIS attack is against this unit's own bounty."""
        if attacking_squad is None or target_squad is None:
            return False
        if not unit_has_bounty_hunters(attacking_squad):
            return False
        return self._bounties.get(id(attacking_squad)) is target_squad

    def adjusted_weapon(self, weapon, attacking_squad, target_squad):
        """[LETHAL HITS] and [PRECISION] on an attack against the bounty.

        Both at once, from one copy - two separate adjusters would copy the
        weapon twice for no gain."""
        if weapon is None or not self.applies(attacking_squad, target_squad):
            return weapon
        if getattr(weapon, "lethal_hits", False) and getattr(weapon, "precision", False):
            return weapon
        granted = copy.copy(weapon)
        granted.lethal_hits = True
        granted.precision = True
        return granted


def pechra_gear(model_line_name):
    """The Pech'ra: "1 Kroot Farstalker equipped with a Farstalker firearm can
    be equipped with 1 Pech'ra."

    The "equipped with a Farstalker firearm" qualifier is NOT enforced - Gear
    runs after the weapon swaps (see game/factions/datasheet.py), so a build
    that traded that model's firearm away could still take it. Only one
    Farstalker in ten can be traded at all, so the case needs a deliberately
    awkward build to reach; recorded rather than silently assumed away."""
    from game.factions import Gear

    def effect(token):
        token.profile.pechra = True

    return Gear(model_line_name, "Pech'ra", effect, max_count=1)
