"""Lord of the Storm - Imotekh the Stormlord's own ability.

RULE (printed, word for word):

  "Once per battle, at the end of your Command phase, this model can use this
   ability. If it does, roll one D6 for each enemy unit within 12" of this
   model: on a 2-5, that enemy unit suffers D3 mortal wounds; on a 6, that
   enemy unit suffers D3+3 mortal wounds."

THE SECOND CARRIER of game/mortal_wound_sweep.py, and the one that justifies
the extraction: Drain Life arrived with it, this one proves the knobs are the
right knobs. Every difference from the Nightbringer's version is a value:

  * 12" rather than 6"
  * a threshold of 2 rather than 4 - so only a 1 does nothing at all
  * TWO BANDS rather than one, which is the knob no single-band ability would
    have needed: a 6 pays D3+3 where a 2-5 pays D3
  * ONCE PER BATTLE, where Drain Life has no entitlement at all
  * the end of YOUR Command phase, where Drain Life fires at the end of THE
    Fight phase

"THIS MODEL CAN USE THIS ABILITY" IS A CHOICE, and Drain Life's silence on that
point is the difference between the two. Once per battle means spending it now
costs the rest of the game, so a human is asked; an `auto_players` owner
answers deterministically, and its rule is the simplest honest one - take it
the first time it would hit anything at all. Nothing here is army-wide, so
there is no ai/agent_driver.py verdict (the standing instruction for this
backfill).
"""

from game.dice_notation import D3
from game.mortal_wound_sweep import MortalWoundSweepController

LORD_OF_THE_STORM_RANGE_IN = 12.0
LORD_OF_THE_STORM_THRESHOLD = 2   # "on a 2-5" - a 1 does nothing
LORD_OF_THE_STORM_BIG_ROLL = 6    # "on a 6"
LORD_OF_THE_STORM_SIDES = 3       # "D3 mortal wounds"
LORD_OF_THE_STORM_BIG_BONUS = 3   # "D3+3 mortal wounds"


def has_lord_of_the_storm(squad):
    from game.mortal_wound_abilities import bearers
    return bool(bearers(squad, "lord_of_the_storm"))


class LordOfTheStormController(MortalWoundSweepController):
    label = "Lord of the Storm"
    flag = "lord_of_the_storm"
    range_in = LORD_OF_THE_STORM_RANGE_IN
    threshold = LORD_OF_THE_STORM_THRESHOLD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._used = set()      # id(model) of Imotekhs that have spent it

    def wounds_for(self, roll):
        """Two bands. `roll` already met the 2+, so the only question left is
        whether it is the 6."""
        if roll >= LORD_OF_THE_STORM_BIG_ROLL:
            return D3(LORD_OF_THE_STORM_BIG_BONUS)
        return D3()

    # -- the once-per-battle entitlement ----------------------------------
    def available_models(self, squad):
        return [m for m in self.bearer_models(squad) if id(m) not in self._used]

    def can_use(self, squad):
        return bool(self.available_models(squad)) and super().can_use(squad)

    def offer_at_end_of_command_phase(self, squads, player):
        """main.py's hook. Takes a SIDE, unlike Drain Life: the printed text is
        "at the end of YOUR Command phase"."""
        for squad in sorted((s for s in squads if s.owner == player),
                            key=lambda s: s.name):
            if self.offer(squad):
                return True
        return False

    def offer(self, squad):
        if not self.can_use(squad):
            return False
        model = self.available_models(squad)[0]
        if squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad, model)
        targets = self.candidates(squad)
        self.decision_manager.request(
            squad.owner,
            "%s: %s - call the storm down on %d enemy unit(s)? (once per battle)"
            % (squad.name, self.label, len(targets)),
            [("Use %s" % self.label, (lambda: self._use(squad, model))),
             ("Decline", None)])
        return True

    def _use(self, squad, model):
        # Spent whether or not a single die lands: the printed cost is using
        # the ability, not hurting anything with it.
        self._used.add(id(model))
        return self.start(squad)
