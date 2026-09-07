"""Kroot War Shaper's "Root of Honour".

RULE (printed, word for word):
  "Once per battle, at the start of any phase, you can select one friendly
   KROOT unit that is Battle-shocked and within 12" of this model. That unit is
   no longer Battle-shocked."

NO DICE AND NO COST - which makes it shorter than every ability it resembles.
The shape it follows is the Technomancer's repair (game/technomancer.py): an
offer made at a phase seam from main.py, answered by the DecisionManager for a
human and deterministically for an `auto_players` owner.

FOUR CONDITIONS, and each one is a separate way to get this wrong:

  * "ONCE PER BATTLE" - per War Shaper, not per army and not per phase, so the
    ledger is keyed on the model's id() and is never reset by any boundary.
    Contrast War Leader next door, whose "once per battle round" is per ARMY.
  * "AT THE START OF ANY PHASE" - any phase, including the opponent's. So
    main.py offers it at every phase change rather than only its owner's.
  * "FRIENDLY KROOT UNIT" - the KROOT keyword, which on this roster is Kroot
    Carnivores, the three Shapers and the Lone-Spear, but NOT the Fire Warrior
    teams. Read off the models rather than assumed from the faction.
  * "THAT IS BATTLE-SHOCKED" - checked at the moment of use. An ability that
    fired on a unit which is not shocked would burn the once-per-battle use for
    nothing, so `eligible_targets()` filters on it and `can_use()` is false
    when the list is empty (rule of this repo: never offer what buys nothing).

12" IS MEASURED EDGE TO EDGE, like every other range in this engine
(game/squad.py's edge_distance), and from THE MODEL that prints the ability -
not from its unit - because the printed text says "within 12" of this model".
"""

from game.squad import edge_distance
from game import ai_mode

ROOT_OF_HONOUR_RANGE_IN = 12.0


def war_shaper_models(squad):
    """The living models in this unit that print Root of Honour.

    A list rather than a bool because the range is measured from the MODEL, and
    because the once-per-battle ledger is keyed on the model."""
    if squad is None:
        return []
    return [m for m in getattr(squad, "models", ()) or ()
            if not m.is_dead() and getattr(m.profile, "root_of_honour", False)]


def is_kroot(squad):
    """The KROOT keyword, read off the unit's living models."""
    if squad is None:
        return False
    return any(getattr(m.profile, "kroot", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


class RootOfHonourController:
    """Offered at the start of every phase from main.py's own phase-change
    block - "any phase" includes the opponent's, so it is not gated on whose
    turn it is."""

    def __init__(self, decision_manager=None, game_log=None, all_squads=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        # A callable returning every unit on the table, so the controller never
        # holds a list that goes stale as units die.
        self.all_squads = all_squads
        self.auto_players = ai_mode.players(auto_players)
        self._used = set()   # id(model) of War Shapers that have spent it

    # -- eligibility ------------------------------------------------------
    def available_models(self, squad):
        """The War Shapers in this unit that have not used it yet."""
        return [m for m in war_shaper_models(squad) if id(m) not in self._used]

    def eligible_targets(self, model):
        """Friendly Battle-shocked KROOT units within 12" of `model`.

        Includes the Shaper's OWN unit: the printed text says "one friendly
        KROOT unit", with no exclusion, and his unit is both."""
        owner = getattr(getattr(model, "squad", None), "owner", None)
        if owner is None or self.all_squads is None:
            return []
        out = []
        for squad in self.all_squads():
            if squad.owner != owner or not squad.battle_shocked or not is_kroot(squad):
                continue
            if any(not m.is_dead()
                   and edge_distance(model, m) <= ROOT_OF_HONOUR_RANGE_IN
                   for m in getattr(squad, "models", ()) or ()):
                out.append(squad)
        return sorted(out, key=lambda s: s.name)

    def can_use(self, squad):
        return any(self.eligible_targets(m) for m in self.available_models(squad))

    # -- the offer --------------------------------------------------------
    def offer_at_start_of_phase(self, squads, player=None):
        """One offer per phase at most, for the first unit that can use it.

        `player` is optional and defaults to EVERY owner on the table, because
        the printed trigger is "at the start of any phase" with no mention of
        whose - so a War Shaper reacts in his opponent's phases too. The owner
        is taken off the squads themselves rather than from a turn tracker,
        the same way DeadlyVectorsController derives "every other player".

        Sorted by name so a replay and a test agree on which unit is offered."""
        candidates = [s for s in squads if player is None or s.owner == player]
        for squad in sorted(candidates, key=lambda s: (str(s.owner), s.name)):
            if self.offer(squad):
                return True
        return False

    def offer(self, squad):
        if not self.can_use(squad):
            return False
        model = next(m for m in self.available_models(squad)
                     if self.eligible_targets(m))
        targets = self.eligible_targets(model)
        if squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(model, self._pick(targets))
        options = [(f"Free {t.name} from Battle-shock", (lambda target=t: self._use(model, target)), t)
                   for t in targets]
        options.append(("Decline", None))
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: Root of Honour - end Battle-shock on one KROOT unit? "
            f"(once per battle)", options)
        return True

    def _pick(self, targets):
        """The biggest unit, because Battle-shock costs it the most Objective
        Control (14.02 zeroes OC while shocked); name breaks ties so a replay
        and a test agree."""
        return max(targets, key=lambda s: (len([m for m in s.models if not m.is_dead()]), s.name))

    def _use(self, model, target):
        if target is None or not target.battle_shocked:
            return False
        self._used.add(id(model))
        target.battle_shocked = False
        if self.game_log:
            self.game_log.add(
                f"[root of honour] {target.name} is no longer Battle-shocked "
                f"({model.profile.name}, once per battle)")
        return True
