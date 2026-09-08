"""Maugan Ra's "Harvester of Souls" - a datasheet ability.

RULE (printed, word for word):
  "While this model is leading a unit, in your Shooting phase, after selecting
  targets for that unit's attacks, if every attack targets the same unit, roll
  one D6 for the target unit and one D6 for every other enemy unit within 3" of
  the target unit. On a 5+, the unit being rolled for is struck by explosive
  debris; after resolving all of that unit's attacks against the target unit,
  each unit struck by explosive debris suffers D3 mortal wounds."

"IF EVERY ATTACK TARGETS THE SAME UNIT" IS THE CONDITION THAT MATTERS
---------------------------------------------------------------------
It is the printed cost of the ability: Maugan Ra's unit gets the splash only if
it gives up Split Fire (10.04) entirely. So the test is "how many DISTINCT units
did this activation target", and one is the answer that pays.

A TIMING SIMPLIFICATION, NAMED RATHER THAN HIDDEN
--------------------------------------------------
The printed text rolls at target SELECTION and applies the wounds after the
attacks resolve. This resolves both at the END of the activation, from
ShootingController.on_squad_finished_shooting.

Why: "every attack targets the same unit" is not knowable at the first
selection - this engine picks targets per weapon group, so a unit that will
split fire looks identical to one that will not until the last group is
assigned. Rolling early would mean rolling for an ability whose own condition
is still undecided.

What the shift can change, stated exactly: the 3" measurement, and the set of
units it finds. A unit that was within 3" at selection and is wiped out by the
attacks is no longer there to be rolled for. That makes this reading slightly
NARROWER than the printed one, which is the safe direction - it can never
inflict wounds the rule would not - and it is the only observable difference,
since the D6 itself is independent of when it is thrown.

THE MORTAL WOUNDS go through the ordinary MortalWoundAllocationSession (06.02),
so Feel No Pain and the usual allocation still apply - the same route
game/mortal_wound_abilities.py takes for the four abilities it holds.
"""
from game.attached_units import leader_ability
from game.squad import edge_distance
from game import mortal_wound_sessions

HARVESTER_LABEL = "Harvester of Souls"

#: "roll one D6 ... On a 5+".
DEBRIS_THRESHOLD = 5
#: "every other enemy unit within 3" of the target unit".
DEBRIS_RANGE_IN = 3.0
#: "suffers D3 mortal wounds".
DEBRIS_MORTAL_SIDES = 3


def applies(squad):
    """"While this model is LEADING a unit" - 24.22's question, so Maugan Ra
    standing alone triggers nothing."""
    return bool(squad is not None and leader_ability(squad, "harvester_of_souls"))


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


class HarvesterOfSoulsController:
    """Sits in ShootingController.on_squad_finished_shooting."""

    def __init__(self, dice_manager=None, game_log=None, game_state=None,
                 all_tokens=None):
        self.dice_manager = dice_manager
        self.game_log = game_log
        self.game_state = game_state
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.mortal_wound_sessions = []

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def nearby_units(self, target_squad, exclude_owner=None):
        """"every OTHER enemy unit within 3" of the target unit" - the target
        itself is rolled for separately, so it is not in this list."""
        seen, out = set(), []
        mine = _living(target_squad)
        for token in self.all_tokens or ():
            other = getattr(token, "squad", None)
            if other is None or other is target_squad or id(other) in seen:
                continue
            if exclude_owner is not None and other.owner == exclude_owner:
                continue
            if not _living(other):
                continue
            if any(edge_distance(a, b) <= DEBRIS_RANGE_IN
                   for a in mine for b in _living(other)):
                seen.add(id(other))
                out.append(other)
        return out

    def after_shooting(self, squad, hit_squads, targeted_squads=None):
        """`targeted_squads` is every unit this activation SELECTED as a target,
        which is the set the printed condition is about - not `hit_squads`,
        which is only those actually hit. A unit that split its fire and missed
        with one group still split its fire."""
        if not applies(squad):
            return []
        targets = list(targeted_squads if targeted_squads is not None else hit_squads)
        if len(targets) != 1:
            if targets:
                self._log("[harvester] %s split its fire across %d units - no debris."
                          % (squad.name, len(targets)), file_only=True)
            return []
        target = targets[0]
        struck = []
        for unit in [target] + self.nearby_units(target, exclude_owner=squad.owner):
            rolled = self._roll(6)
            if rolled >= DEBRIS_THRESHOLD:
                struck.append(unit)
            self._log("[harvester] %s rolled a %d%s"
                      % (unit.name, rolled,
                         " - struck by explosive debris." if rolled >= DEBRIS_THRESHOLD
                         else " - unscathed."),
                      file_only=True)
        for unit in struck:
            self._inflict(unit)
        return struck

    def _inflict(self, unit):
        from game.damage_resolution import MortalWoundAllocationSession
        count = self._roll(DEBRIS_MORTAL_SIDES)
        self._log("%s: %s suffers %d mortal wound(s) from explosive debris."
                  % (HARVESTER_LABEL, unit.name, count))
        self.mortal_wound_sessions.append(MortalWoundAllocationSession(
            unit, count, dice_manager=self.dice_manager, log=self._log))

    def _roll(self, sides):
        from game.dice import random as dice_random
        return dice_random.randint(1, sides)

    @property
    def is_busy(self):
        return mortal_wound_sessions.any_open(self.mortal_wound_sessions)

    def reset_phase(self):
        # Only finished sessions should ever be here by now: main.py's phase
        # gate waits on is_busy(), so an unresolved allocation holds the phase
        # open. Pruned rather than cleared, so a future caller that reaches
        # this with one still open keeps it instead of dropping the wounds.
        mortal_wound_sessions.prune(self.mortal_wound_sessions)

    # ------------------------------------------------- rule 06.02 allocation
    # This ability can open SEVERAL sessions in one go, so the three members
    # main.py asks about delegate to game/mortal_wound_sessions.py rather than
    # being written twice - see that module for why insertion order is part of
    # the answer. Without them the wounds were rolled, logged and never
    # applied against any multi-model target.

    @property
    def pending_damage_choice(self):
        return mortal_wound_sessions.pending_choice(self.mortal_wound_sessions)

    def choose_damage_model(self, model):
        if mortal_wound_sessions.choose(self.mortal_wound_sessions, model):
            mortal_wound_sessions.prune(self.mortal_wound_sessions)

    def on_dice_acknowledged(self):
        """Only the Feel No Pain leg: this ability rolls its own dice inline,
        so there is no pending dice context to resume."""
        if not mortal_wound_sessions.acknowledge_fnp(self.mortal_wound_sessions):
            return False
        mortal_wound_sessions.prune(self.mortal_wound_sessions)
        return True
