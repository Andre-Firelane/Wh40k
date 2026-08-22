"""T'au Strike Team ability: DS8 Support Turret, as supplied by the user
(datasheet-specific, not a rule from the generic 40k core rulebook).

RULE: In your Movement phase, if this unit Remains Stationary, until the
start of your next turn, its Shas'ui model is equipped with the support
turret weapon.

Modeled the same way game/firing_deck.py lends a weapon onto a model: the
actual WeaponProfile instance is appended to (and later removed from) the
bearer model's own .weapons list, rather than threading a live "does this
model conditionally have this weapon right now" check through every
weapon-reading call site."""

from game.squad import support_turret_bearer
from game.weapons import SupportTurretProfile


class SupportTurretController:
    def __init__(self, game_log=None):
        self.game_log = game_log
        self._granted = {}  # bearer Token -> (weapon instance, owner)

    def on_remain_stationary(self, squad):
        """Hook for MovementController.on_remain_stationary (see main.py) -
        a no-op unless the squad actually has a DS8-bearing model."""
        bearer = support_turret_bearer(squad)
        if bearer is None or bearer in self._granted:
            return  # no bearer, or it's already carrying one this turn
        weapon = SupportTurretProfile()
        bearer.weapons.append(weapon)
        self._granted[bearer] = (weapon, squad.owner)
        if self.game_log is not None:
            self.game_log.add(
                f"{squad.owner}: {bearer.profile.name} ({squad.name}) is equipped with the support turret "
                f"(DS8 Support Turret)."
            )

    def expire_for(self, player):
        """Rule text: "until the start of your next turn" - called at the
        start of every Command phase for `player` (see main.py's
        advance_turn_phase()). Command is always a turn's FIRST phase, so
        any grant still on record for `player` at that point is necessarily
        from an earlier turn (a fresh grant can only happen later, in that
        same turn's own Movement phase) and comes off unconditionally - no
        turn-number bookkeeping needed on the grant itself."""
        for bearer, (weapon, owner) in list(self._granted.items()):
            if owner != player:
                continue
            if weapon in bearer.weapons:
                bearer.weapons.remove(weapon)
            del self._granted[bearer]
