"""Death Lord's Chosen Stratagem: BLOOMING PESTILENCE (1 CP, Epic Deed).

  WHEN: Start of any phase.
  TARGET: One TERMINATOR unit from your army.
  EFFECT: Until the end of the phase, add 3" to the Contagion Range of models
        in your unit.

IT IS WORTH THE SAME 3" IN EVERY ROUND, and that is worth stating because it
was first built the other way round. Nurgle's Gift's Contagion Range runs
3"/6"/9", and the 12" ceiling exists precisely so that this Stratagem's +3" can
take a round-3 aura to 12":

    round 1:  3" -> 6"
    round 2:  6" -> 9"
    round 3+: 9" -> 12"   (exactly the ceiling, never over it)

An earlier build had the table as 6"/9"/12" - values a summariser inferred from
diagrams it could not actually read - and under those the ceiling applied from
round 3 with no modifier at all, making this Stratagem provably worthless from
round 3 on. That was a tempting "sharp decision boundary" and it was an
artefact of the wrong table. bonus_is_worth_anything() is kept anyway: it is
the honest gate ("never offer what cannot help"), it simply answers yes in
every round the printed numbers produce, and it would start refusing again if
a second modifier ever pushed the aura to the ceiling on its own.

"START OF ANY PHASE" is the loosest WHEN of the six - no phase test and no
"your phase" test, so a Death Guard player can widen the aura in their
opponent's Command phase to feed Deadly Vectors, which is a real use and not an
accident. What the text does NOT allow is buying it mid-phase, and that is what
`started_phases` guards: the Stratagem is offered once, at the boundary.

THE BONUS IS PER UNIT, not per army: it says "the Contagion Range of models in
YOUR UNIT", so it lives on NurglesGiftController's per-squad bonus table rather
than on a global. Two Deathshroud squads would each need their own.
"""
from game import death_lords_chosen, nurgles_gift
from game.stratagems import Stratagem

BLOOMING_PESTILENCE_CP = 1
BLOOMING_PESTILENCE_NAME = "Blooming Pestilence"
BLOOMING_PESTILENCE_BONUS_IN = 3.0


def bonus_is_worth_anything(battle_round):
    """Whether +3" actually widens the aura in this battle round.

    A pure function of the round, because that is genuinely all it depends on -
    the cap is not about the board. Read by the Stratagem's own can_use() AND
    by the AI verdict, so the two cannot disagree about when it is pointless."""
    plain = nurgles_gift.contagion_range_in(battle_round)
    boosted = nurgles_gift.contagion_range_in(battle_round, BLOOMING_PESTILENCE_BONUS_IN)
    return boosted > plain


class BloomingPestilenceController:
    def __init__(self, stratagem_controller, nurgles_gift_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        # The bonus lives on the aura controller's own per-squad table - it is
        # that module's number, and expire_phase() there is what clears it.
        self.nurgles_gift = nurgles_gift_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._granted = set()   # id(squad) already boosted this phase
        self._stratagem = Stratagem(name=BLOOMING_PESTILENCE_NAME,
                                    cp_cost=BLOOMING_PESTILENCE_CP,
                                    effect=self._grant)

    def _battle_round(self):
        return getattr(self.turn_tracker, "battle_round", 1) or 1

    def is_active(self, squad):
        return squad is not None and id(squad) in self._granted

    def reset_phase(self, squads=()):
        """"Until the end of the phase". The RANGE bonus itself is cleared by
        NurglesGiftController.expire_phase(), which owns the table - this only
        forgets that the unit was granted one, so it can be bought again next
        phase."""
        self._granted.clear()

    def can_use(self, squad):
        if squad is None or self.is_active(squad):
            return False
        if not death_lords_chosen.stratagem_target_ok(squad):
            return False
        if not death_lords_chosen.is_terminator_unit(squad):
            return False
        # "Start of ANY phase" - no phase test and no "your phase" test. The
        # one thing that IS refused is a purchase that provably buys nothing,
        # which is this repo's standing rule: never offer what cannot help
        # (see game/aspect_shrine.py's own gate for the same reasoning).
        if not bonus_is_worth_anything(self._battle_round()):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            self._granted.add(id(squad))
            if self.nurgles_gift is not None:
                self.nurgles_gift.add_range_bonus(squad, BLOOMING_PESTILENCE_BONUS_IN)
            if self.game_log is not None:
                reach = nurgles_gift.contagion_range_in(
                    self._battle_round(), BLOOMING_PESTILENCE_BONUS_IN)
                self.game_log.add(
                    f"{BLOOMING_PESTILENCE_NAME}: {squad.name}'s Contagion Range "
                    f"reaches {reach:g}\" until the end of the phase.")
        return True
