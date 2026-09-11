"""«Once per battle, at the start of any phase, end Battle-shock on one
friendly unit within 12".»

Two abilities print that sentence with one word changed - the keyword on the
unit they may free:

  ROOT OF HONOUR - Kroot War Shaper:
    "Once per battle, at the start of any phase, you can select one friendly
     KROOT unit that is Battle-shocked and within 12" of this model. That unit
     is no longer Battle-shocked."

  ENGRAMMATIC LOGIC - Royal Warden:
    "Once per battle, at the start of any phase, you can select one friendly
     NECRONS unit that is Battle-shocked and within 12" of this model. That
     unit is no longer Battle-shocked."

NO DICE AND NO COST, which makes this shorter than every ability it resembles.
The shape is the Technomancer's repair (game/technomancer.py): an offer made at
a phase seam from main.py, answered by the DecisionManager for a human and
deterministically for an `auto_players` owner.

FOUR CONDITIONS, and each one is a separate way to get this wrong. They are
written HERE, once, because the second carrier would otherwise have to get all
four right again from scratch:

  * "ONCE PER BATTLE" - per BEARER MODEL, not per army and not per phase, so
    the ledger is keyed on the model's id() and is never reset by any boundary.
    Contrast the War Shaper's own War Leader next door, whose "once per battle
    round" is per ARMY.
  * "AT THE START OF ANY PHASE" - any phase, including the opponent's. So
    main.py offers it at every phase change rather than only its owner's, and
    offer_at_start_of_phase() defaults to every owner on the table.
  * "FRIENDLY <KEYWORD> UNIT" - read off the models rather than assumed from
    the faction, and it is the one thing a subclass supplies.
  * "THAT IS BATTLE-SHOCKED" - checked at the moment of use. Firing on a unit
    that is not shocked would burn the once-per-battle use for nothing, so
    eligible_targets() filters on it and can_use() is false when the list is
    empty (standing rule: never offer what buys nothing).

12" IS MEASURED EDGE TO EDGE, like every other range in this engine
(game/squad.py's edge_distance), and from THE MODEL that prints the ability -
not from its unit - because the printed text says "within 12" of this model".
"""

from game import ai_mode
from game.squad import edge_distance

#: "within 12" of this model" - the same number on both printed cards.
BATTLE_SHOCK_RELIEF_RANGE_IN = 12.0


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


class EndBattleShockController:
    """Offered at the start of every phase from main.py's own phase-change
    block - "any phase" includes the opponent's, so it is not gated on whose
    turn it is.

    A subclass supplies four things and nothing else:

      bearer_flag   the UnitProfile attribute that prints the ability
      target_flag   the UnitProfile attribute standing for the printed keyword
      label         what the prompt calls it
      log_tag       the bracketed tag its log line carries
    """

    bearer_flag = None
    target_flag = None
    label = "End Battle-shock"
    log_tag = "battle shock relief"
    range_in = BATTLE_SHOCK_RELIEF_RANGE_IN

    def __init__(self, decision_manager=None, game_log=None, all_squads=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        # A callable returning every unit on the table, so the controller never
        # holds a list that goes stale as units die.
        self.all_squads = all_squads
        self.auto_players = ai_mode.players(auto_players)
        self._used = set()   # id(model) of bearers that have spent it

    # -- eligibility ------------------------------------------------------
    def bearer_models(self, squad):
        """The living models in this unit that print the ability.

        A list rather than a bool because the range is measured from the MODEL,
        and because the once-per-battle ledger is keyed on the model."""
        if squad is None or not self.bearer_flag:
            return []
        return [m for m in _living(squad)
                if getattr(m.profile, self.bearer_flag, False)]

    def is_eligible_faction(self, squad):
        """The printed keyword, read off the unit's living models."""
        if squad is None or not self.target_flag:
            return False
        return any(getattr(m.profile, self.target_flag, False) for m in _living(squad))

    def available_models(self, squad):
        """The bearers in this unit that have not used it yet."""
        return [m for m in self.bearer_models(squad) if id(m) not in self._used]

    def eligible_targets(self, model):
        """Friendly Battle-shocked units of the printed keyword within 12".

        Includes the bearer's OWN unit: the printed text says "one friendly
        <KEYWORD> unit", with no exclusion, and his unit is both."""
        owner = getattr(getattr(model, "squad", None), "owner", None)
        if owner is None or self.all_squads is None:
            return []
        out = []
        for squad in self.all_squads():
            if (squad.owner != owner or not squad.battle_shocked
                    or not self.is_eligible_faction(squad)):
                continue
            if any(edge_distance(model, m) <= self.range_in for m in _living(squad)):
                out.append(squad)
        return sorted(out, key=lambda s: s.name)

    def can_use(self, squad):
        return any(self.eligible_targets(m) for m in self.available_models(squad))

    # -- the offer --------------------------------------------------------
    def offer_at_start_of_phase(self, squads, player=None):
        """One offer per phase at most, for the first unit that can use it.

        `player` is optional and defaults to EVERY owner on the table, because
        the printed trigger is "at the start of any phase" with no mention of
        whose - so a bearer reacts in his opponent's phases too. The owner is
        taken off the squads themselves rather than from a turn tracker, the
        same way DeadlyVectorsController derives "every other player".

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
        options = [("Free %s from Battle-shock" % t.name,
                    (lambda target=t: self._use(model, target)), t)
                   for t in targets]
        options.append(("Decline", None))
        self.decision_manager.request(
            squad.owner,
            "%s: %s - end Battle-shock on one unit? (once per battle)"
            % (squad.name, self.label), options)
        return True

    def _pick(self, targets):
        """The biggest unit, because Battle-shock costs it the most Objective
        Control (14.02 zeroes OC while shocked); name breaks ties so a replay
        and a test agree."""
        return max(targets, key=lambda s: (len(_living(s)), s.name))

    def _use(self, model, target):
        if target is None or not target.battle_shocked:
            return False
        self._used.add(id(model))
        target.battle_shocked = False
        if self.game_log:
            self.game_log.add(
                "[%s] %s is no longer Battle-shocked (%s, once per battle)"
                % (self.log_tag, target.name, model.profile.name))
        return True
