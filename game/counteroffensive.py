from game.stratagems import Stratagem

COUNTEROFFENSIVE_CP_COST = 2


def _other_player(player):
    return "Player 2" if player == "Player 1" else "Player 1"


class CounteroffensiveController:
    """Rule 15.12 (Counteroffensive, Core Stratagem, 2CP): WHEN the Fight
    step of your opponent's Fight phase, just after an enemy unit has
    resolved its attacks, TARGET one friendly unit that is eligible to
    fight, EFFECT: until the end of the phase, your unit has the Fights
    First ability and it must be the next unit you select to fight (12.04).

    Unlike Rapid Ingress/Fire Overwatch/Heroic Intervention (each a single
    phase-BOUNDARY event, offered once from main.py's advance_turn_phase()),
    this can fire repeatedly THROUGHOUT the Fight phase - "just after an
    enemy unit has resolved its attacks" is every single fight activation's
    conclusion, not just the phase's end. Both players' units fight within
    the SAME single Fight phase (rule 12.04's alternation - there's no
    separate "Player 1's Fight phase" and "Player 2's Fight phase"), so
    "enemy" here just means "whoever doesn't own the squad that just
    fought" - either player can react to the other's unit finishing.
    game/fight.py's FightController.on_unit_finished_fighting is a plain
    callback hook (set by main.py, called from _actually_finish_current_fight()
    - the one method every fight activation funnels through regardless of
    how it started) rather than a constructor dependency, since
    FightController is built before this controller can exist (it needs a
    FightController reference itself) - avoids a circular-construction
    dependency.

    Naturally capped to once per player per phase by StratagemController's
    rule 15.01 default (no override needed) - once a player has used it,
    every later offer_after() call simply finds can_use() already False for
    them and stays silent, exactly like an empty Rapid Ingress/Fire
    Overwatch/Heroic Intervention offer.

    The Fights First grant reuses Squad.fights_first (the same instance
    flag a charge grants, rule 11.04) - "until the end of the phase" and
    "until the end of the turn" coincide here since Fight is always the
    LAST phase in a turn (rule 07.02's phase order), so the existing
    end-of-turn clearing (main.py's advance_turn_phase()) already covers
    it correctly with no new cleanup needed.

    "Must be the next unit you select to fight" goes through
    FightController.force_next_fighter(), which sets the constraint AND
    hands rule 12.04's alternation to this player.

    That second half is NOT optional, and this docstring used to claim it
    was ("the granted unit is picked up correctly whenever alternation next
    reaches this player, with no extra bookkeeping needed here"). It is
    wrong: alternation does not "next reach" this player at all. The window
    is "just after an enemy unit has resolved its attacks", and the one
    place that fires it - _actually_finish_current_fight() - has already run
    _settle_turn_state() by then. So whose_turn is fixed BEFORE this grant
    exists, and if the settle handed the turn back to the opponent (which it
    does whenever they still have a Fights First unit and this player has
    none) the constraint is filed under a player who is not selecting and
    binds nothing. Reported from a game: 2 CP spent, the AI's next unit
    swung anyway."""

    def __init__(self, stratagem_controller, fight_controller, all_tokens=None, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.fight_controller = fight_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.game_log = game_log

        self._stratagem = Stratagem(name="Counteroffensive", cp_cost=COUNTEROFFENSIVE_CP_COST, effect=self._grant)

    def _all_squads(self):
        return {t.squad for t in self.all_tokens if t.squad is not None}

    def offer_after(self, just_fought_squad, decision_manager):
        """Called right after `just_fought_squad`'s fight activation ends -
        offers ITS OPPONENT a chance to react with one of their own
        eligible-to-fight units. No-op if nothing qualifies, so an empty
        offer never flashes a "Decline"-only prompt after every single
        fight activation."""
        if just_fought_squad is None:
            return
        reactor = _other_player(just_fought_squad.owner)
        # Sorted because _all_squads() is a SET: without this the offered
        # options come back in a different order from run to run, which is
        # both unpleasant to click and makes any test that picks "option 0"
        # non-deterministic.
        eligible = sorted((
            squad for squad in self._all_squads()
            if squad.owner == reactor and self.fight_controller._is_eligible_to_fight(squad)
            and self.stratagem_controller.can_use(reactor, self._stratagem, [squad])
        ), key=lambda s: s.name)
        if not eligible:
            return

        options = [
            (f"Counteroffensive: {squad.name} (2 CP)", lambda squad=squad: self._pick(reactor, squad), squad)
            for squad in eligible
        ]
        options.append(("Decline", None))
        decision_manager.request(
            reactor, "Counteroffensive (2 CP) - grant Fights First and fight next with an eligible unit?", options,
            is_stratagem=True,
        )

    def _pick(self, player, squad):
        self.stratagem_controller.use(player, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        squad = targets[0]
        squad.fights_first = True
        # Both halves of "it must be the next unit you select to fight" -
        # the constraint AND handing rule 12.04's alternation back to this
        # player. Writing forced_next_fighter directly (as this did) set
        # only the first: the settle in _actually_finish_current_fight()
        # runs BEFORE this callback, so whose_turn was already decided and
        # eligible_to_select_now() went on reading the OTHER player's entry.
        self.fight_controller.force_next_fighter(player, squad)
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: Counteroffensive - {squad.name} gains Fights First and must fight next (rule 15.12)."
            )
