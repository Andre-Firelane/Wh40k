"""Skorpekh Destroyers' "Plasmacyte" wargear.

RULE (printed, word for word):
  "Once per battle for each Plasmacyte this unit has, when this unit is
   selected to fight, you can use this ability. If you do, until the end of the
   phase, melee weapons equipped by models in this unit have the
   [DEVASTATING WOUNDS] ability."

THE COUNT IS THE INTERESTING PART. "Once per battle FOR EACH Plasmacyte this
unit has" is not once per battle - a six-model unit may take two Plasmacytes
and therefore gets two uses over the whole game. So the ledger is a REMAINING
USES counter seeded from how many the unit was built with, not a boolean and
not a set of unit ids.

WHERE THE COUNT COMES FROM: game/factions/necrons.py's Gear item increments
Token.plasmacyte_count as it is applied. That is per-token, and the printed
allowance is per-UNIT, so remaining_uses() sums across the unit's models - and
because it sums live models only, losing the model carrying the Plasmacyte
takes its use with it, which is the same reading every other wargear ability
here uses (rule 19.04).

THE GRANT ITSELF is a [DEVASTATING WOUNDS] keyword on melee weapons until the
end of the phase, which is exactly the shape of Ferocious Rage
(game/ferocious_rage.py) - so it is a chain entry in FightController's
_adjusted_weapon(), reading a phase-scoped flag on the Squad. It must be in the
chain rather than applied at the wound step because _crit_note() has to know at
ROLL time whether a critical die is a [DEVASTATING WOUNDS] one.

KNOWN GAP, stated in game/factions/necrons.py too: the printed "for every 3
models in this unit, this unit can have 1 Plasmacyte" ratio is a LIST-BUILDING
limit, and this engine has no army-building step to enforce it in. What is
enforced here is the part that matters in play - a unit cannot use the ability
more times than it has Plasmacytes.
"""

import copy

from game import ai_mode


def plasmacyte_count(squad):
    """How many Plasmacytes this unit still has, summed over its living
    models."""
    if squad is None:
        return 0
    return sum(int(getattr(m, "plasmacyte_count", 0) or 0)
               for m in squad.models if not m.is_dead())


def uses_spent(squad):
    return int(getattr(squad, "plasmacyte_uses_spent", 0) or 0)


def remaining_uses(squad):
    """"Once per battle for each Plasmacyte this unit has"."""
    return max(0, plasmacyte_count(squad) - uses_spent(squad))


def can_use(squad):
    """The whole condition line: the unit has an unspent Plasmacyte, and the
    grant is not already running this phase (using a second one on top of the
    first would spend it for nothing)."""
    if squad is None or getattr(squad, "plasmacyte_active", False):
        return False
    return remaining_uses(squad) > 0


def use(squad):
    """Spend one Plasmacyte and turn the grant on for the phase."""
    if not can_use(squad):
        return False
    squad.plasmacyte_uses_spent = uses_spent(squad) + 1
    squad.plasmacyte_active = True
    return True


def reset_phase(squads=()):
    """"until the end of the phase". The SPENT count deliberately survives -
    it is a per-battle ledger, not a per-phase one."""
    for squad in squads or ():
        squad.plasmacyte_active = False


def adjusted_weapon(weapon, squad):
    """[DEVASTATING WOUNDS] on melee weapons while the grant is up.

    Copies rather than mutating: the WeaponProfile instance is shared, and
    this repo's standing rule is that effects copy."""
    if weapon is None or not getattr(squad, "plasmacyte_active", False):
        return weapon
    if weapon.devastating_wounds:
        return weapon
    granted = copy.copy(weapon)
    granted.devastating_wounds = True
    return granted


class PlasmacyteController:
    """The OFFER, and the reason this class exists at all.

    BUILT, WIRED, AND NEVER FED - the eighth instance of that class in this
    repo, and measured rather than suspected: `use()` and `can_use()` above had
    ZERO callers anywhere in game/, ai/ or main.py. The grant was in
    FightController's adjuster chain, the per-phase reset was called from
    main.py, the Gear item counted the tokens - and nothing ever asked the
    player, so no Skorpekh Destroyer unit has ever used a Plasmacyte. A unit
    test that drives use() directly is green throughout; only the absence of a
    CALLER shows it, which is why CLAUDE.md keeps a source-side guard for this
    shape rather than a behaviour test.

    Found when the Ophydian Destroyers arrived printing the identical wargear
    ability - the second carrier is where a missing half becomes visible.

    "WHEN THIS UNIT IS SELECTED TO FIGHT" is FightController._start_fighting(),
    the one place rule 12.04's selection happens for both routes into it
    (normal selection and 12.08's forced fight). It is offered beside Aspect
    Host's Path of the Warrior, which is asked at that same instant and for the
    same reason: before any dice, once per activation.

    "YOU CAN USE THIS ABILITY" is a real choice and stays one - the uses are a
    per-BATTLE ledger, so holding one back for a better activation is a genuine
    decision, unlike the once-per-round entitlements this repo resolves
    automatically. The AI answers it deterministically instead of paying for a
    prompt."""

    def __init__(self, decision_manager=None, game_log=None, auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)

    def offer(self, squad):
        """Raise the choice for `squad`, or resolve it for an AI owner."""
        if not can_use(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad)
        self.decision_manager.request(
            squad.owner,
            "%s: Plasmacyte - spend one for [DEVASTATING WOUNDS] on this unit's "
            "melee weapons until the end of the phase? (%d left)"
            % (squad.name, remaining_uses(squad)),
            [("Spend a Plasmacyte", lambda: self._use(squad)),
             ("Save it", lambda: None)],
        )
        return True

    def _use(self, squad):
        if not use(squad):
            return False
        if self.game_log is not None:
            self.game_log.add(
                "%s uses a Plasmacyte: its melee weapons have [DEVASTATING WOUNDS] "
                "until the end of the phase (%d left)."
                % (squad.name, remaining_uses(squad)))
        return True
