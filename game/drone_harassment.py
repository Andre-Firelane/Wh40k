"""Piranhas' "Drone Harassment Tactics".

RULE (printed, word for word):
  "At the end of your Movement phase, select one enemy unit within 12" of this
   unit; that enemy unit must take a Battle-shock test."

NOT OPTIONAL - the text says "select", not "you can" - so the only decision is
WHICH unit, and with a single candidate there is nothing to ask. Same reading
Crimson Harvest's own offer() takes of the same word.

THE TEST ITSELF IS ALREADY BUILT: BattleShockController.start_forced_roll() is
the "a rule orders a test out of turn" entry point, added for The Twin Lance's
Neocapacitor Shields and used since by Presentiment of Dread. It deliberately
skips 08.03's Command-phase gate, which is exactly what "at the end of your
MOVEMENT phase" needs, and it returns whether a roll really started - so a
caller that finds the dice busy learns so rather than silently dropping the
test.

12" IS MEASURED EDGE TO EDGE from the UNIT, not from one model: the printed
text says "within 12" of THIS UNIT". That is the opposite of Root of Honour
next door, whose "within 12" of this model" is measured from the bearer, and
the difference is one word.

ONE TEST PER PHASE PER UNIT, which is what "at the end of your Movement phase"
gives on its own - the seam fires once. No ledger is needed and none is kept,
the same reasoning Crimson Harvest records for its own trigger.
"""

from game.squad import edge_distance
from game import ai_mode

DRONE_HARASSMENT_RANGE_IN = 12.0
DRONE_HARASSMENT_LABEL = "Drone Harassment Tactics"


def unit_has_drone_harassment(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "drone_harassment", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def targets_for(squad, all_squads):
    """Enemy units within 12" of this unit, by name so a replay agrees."""
    if squad is None or not unit_has_drone_harassment(squad):
        return []
    out = []
    for other in all_squads or ():
        if other is squad or other.owner == squad.owner or other in out:
            continue
        if not any(not m.is_dead() for m in getattr(other, "models", ()) or ()):
            continue
        near = any(not mine.is_dead() and not theirs.is_dead()
                   and edge_distance(mine, theirs) <= DRONE_HARASSMENT_RANGE_IN
                   for mine in getattr(squad, "models", ()) or ()
                   for theirs in getattr(other, "models", ()) or ())
        if near:
            out.append(other)
    return sorted(out, key=lambda s: s.name)


class DroneHarassmentController:
    """Fired at the end of its owner's Movement phase from main.py's own
    phase-change block - the same seam the Technomancer's repair uses."""

    def __init__(self, battle_shock=None, decision_manager=None, game_log=None,
                 auto_players=(), target_pick=None):
        self.battle_shock = battle_shock
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        # target_pick(attacker, candidates) -> squad, so the AI uses the same
        # damage-value ranking as every other deterministic target choice.
        self.target_pick = target_pick

    def can_use(self, squad, all_squads):
        return bool(targets_for(squad, all_squads))

    def offer_at_end_of_movement(self, squads, player):
        """One Piranha unit at most per phase, because the dice manager holds
        a single pending roll - the first that can act does."""
        for squad in sorted((s for s in squads if s.owner == player), key=lambda s: s.name):
            if self.offer(squad, squads):
                return True
        return False

    def offer(self, squad, all_squads):
        if not self.can_use(squad, all_squads):
            return False
        targets = targets_for(squad, all_squads)
        if len(targets) == 1 or squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad, self._pick(squad, targets))
        options = [(f"{DRONE_HARASSMENT_LABEL}: {t.name}",
                    (lambda target=t: self._use(squad, target)), t) for t in targets]
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: Drone Harassment Tactics - which unit takes the test?",
            options)
        return True

    def _pick(self, squad, targets):
        if self.target_pick is not None:
            picked = self.target_pick(squad, targets)
            if picked is not None:
                return picked
        return targets[0]

    def _use(self, squad, target):
        if target is None or self.battle_shock is None:
            return False
        started = self.battle_shock.start_forced_roll(target, DRONE_HARASSMENT_LABEL)
        if started and self.game_log:
            self.game_log.add(
                f"{squad.name} uses Drone Harassment Tactics: {target.name} must take a "
                f"Battle-shock test.")
        return started
