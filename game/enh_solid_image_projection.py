"""Kauyon Enhancement: Solid-image Projection Unit (20 pts).

RULE (verbatim, rules/tau_empire/detachments/Kauyon.md):
  T'AU EMPIRE model only. After both players have deployed their armies, select
  up to three T'AU EMPIRE units from your army and redeploy them. When doing
  so, you can set those units up in Strategic Reserves if you wish, regardless
  of how many units are already in Strategic Reserves.

WHEN, AND WHY IT IS NOT A PRE-BATTLE STEP
------------------------------------------
"After both players have deployed their armies" is EARLIER than rule 03.01's
Resolve Pre-battle Abilities step - Determine First Turn sits between the two.
Putting it in the pre-battle queue beside Strike Swiftly would let a player
redeploy knowing who goes first, which is a materially different (and much
stronger) ability.

So it hangs off PregameController._finish_deployment(), which is exactly the
instant the printed text names.

REDEPLOY REUSES THE DEPLOYMENT FLOW RATHER THAN COPYING IT
-----------------------------------------------------------
A unit chosen for redeployment has its models taken off the board and is put
back into PregameController's own `_pending` queue, with the controller
returned to DEPLOYING. Placing it again then goes through start_deployment() /
confirm_deployment() - the same validation, the same overlay, the same
alternation - and when the queue empties, _advance_if_nothing_to_place() reaches
_finish_deployment() a second time. That is what the `_redeploy_done` flag
there is for: the second visit skips this step and goes on to the first-turn
roll-off.

Nothing here re-implements placement. The alternative - a bespoke "pick a new
spot" mode - would be a second placement validator, and the three bugs this
repo has already recorded about placement all came from a second path that
knew one condition less than confirm_setup() does.

"REGARDLESS OF HOW MANY UNITS ARE ALREADY IN STRATEGIC RESERVES" is the clause
that makes the Reserves branch worth anything: rule 20.01 caps an army's
reserves, and this deliberately ignores that cap. This engine enforces 20.01 in
PregameController.finish_formations_for()'s own declaration step, which has
already run by now - so the cap is structurally not in the way here, and the
clause is a documented no-op rather than something to switch off. Said out loud
because "we ignore the cap" reading as "there is no cap" is the sort of thing
that gets re-implemented later.

TAKING A UNIT OFF THE BOARD is game/strategic_reserves.py's removal step for
the Reserves branch. The redeploy branch needs the same removal WITHOUT the
reserves destination, which is the four lines in _take_off_board() - not shared,
because what makes that function worth having is the two things it does AFTER
the removal (clearing the ingress lock, recomputing objective control), and
neither is right for a unit that is about to be placed again in the same step.

UP TO THREE, one prompt per unit, declining legal - the same shape Student of
Kauyon and Strike Swiftly use, and for the same reason (a flat option list
cannot express "three of twelve").

An owner in `auto_players` DECLINES. That is not laziness: redeployment is a
whole-army positional judgement, the deployment AI has already placed this army
where it wanted it, and moving three units at random after the fact would make
its own deployment worse. A deterministic answer that does nothing is honest;
inventing a heuristic here would be inventing an AI path, which the standing
T'au rule says not to do.
"""

from game import ai_mode, enhancements
from game import pregame as pregame_module
from game.strategic_reserves import withdraw_to_reserves

SOLID_IMAGE_PROJECTION_UNIT = "Solid-image Projection Unit"
MAX_UNITS = 3

REDEPLOY = "redeploy"
RESERVES = "reserves"


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


class SolidImageProjectionStep:
    """Registered as PregameController.redeploy_step by main.py."""

    def __init__(self, game_state=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self.chosen = {}          # player -> [(squad, destination)]
        self._pregame = None
        self._on_done = None
        self._pending_players = []

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    # --- the rule ---------------------------------------------------------

    def _squads(self):
        seen = []
        for token in (getattr(self.game_state, "tokens", None) or ()):
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in seen:
                seen.append(squad)
        return seen

    def bearer_units(self, player):
        return enhancements.bearer_units(self._squads(), SOLID_IMAGE_PROJECTION_UNIT,
                                         player=player)

    def eligible_targets(self, player):
        """"up to three T'AU EMPIRE units from your army" - on the battlefield,
        since a unit already in Strategic Reserves has nothing to redeploy."""
        from game import tau_detachments
        taken = [s for s, _ in self.chosen.get(player, [])]
        return [s for s in self._squads()
                if s.owner == player and s not in taken
                and tau_detachments.is_tau_unit(s) and _living(s)]

    def remaining(self, player):
        return MAX_UNITS - len(self.chosen.get(player, []))

    # --- the step ---------------------------------------------------------

    def start(self, pregame_controller, on_done=None):
        """Returns True if it took over - a prompt is on screen, or units are
        back in the deployment queue. False means there was nothing to do and
        the caller should carry straight on."""
        self._pregame = pregame_controller
        self._on_done = on_done
        self._pending_players = list(getattr(pregame_controller, "_owners", lambda: ())())
        return self._next_player()

    def _next_player(self):
        while self._pending_players:
            player = self._pending_players.pop(0)
            if self._offer(player):
                return True
        return self._apply()

    def _offer(self, player):
        """Ask for one unit. Returns True while a human prompt is outstanding."""
        if not self.bearer_units(player):
            return False
        # An owner that answers its own prompts declines outright - see the
        # module docstring on why there is deliberately no heuristic here.
        if player in self.auto_players or self.decision_manager is None:
            return False
        while self.remaining(player) > 0:
            targets = self.eligible_targets(player)
            if not targets:
                return False
            # TWO STEPS, so this can be answered on the BOARD (the standing
            # rule: "immer wenn man eine einheit auf dem schlachtfeld waehlen
            # muss ... will ich die einheit nicht aus einer liste waehlen").
            #
            # It used to be one prompt offering every unit TWICE - once per
            # destination - and game/unit_pick.py rightly refuses a prompt that
            # names the same unit in two options, because a click says "this
            # unit" and cannot pick between two fates. Splitting the question
            # removes that: step one names each unit exactly once and is
            # tagged, step two picks the fate and is an ordinary list (the two
            # destinations are not units).
            options = [
                (target.name, (lambda t=target: self._offer_destination(player, t)), target)
                for target in targets
            ]
            options.append(("No more", lambda: self.decline(player)))
            self.decision_manager.request(
                player,
                f"{SOLID_IMAGE_PROJECTION_UNIT}: redeploy a T'AU EMPIRE unit? "
                f"({self.remaining(player)} left)",
                options)
            return True
        return False

    def _offer_destination(self, player, squad):
        """Step two: what happens to the unit just picked on the board."""
        if self.decision_manager is None:
            return self.choose(player, squad, REDEPLOY)
        self.decision_manager.request(
            player,
            f"{SOLID_IMAGE_PROJECTION_UNIT}: {squad.name} - set it up again, or "
            "put it into Strategic Reserves?",
            [("Set up again elsewhere", (lambda: self.choose(player, squad, REDEPLOY))),
             ("Into Strategic Reserves", (lambda: self.choose(player, squad, RESERVES)))],
        )
        return True

    def choose(self, player, squad, destination):
        if squad is None or self.remaining(player) <= 0:
            return False
        self.chosen.setdefault(player, []).append((squad, destination))
        if not self._offer(player):
            self._next_player()
        return True

    def decline(self, player):
        """"Up to three" - stopping early is legal. Spends the allowance so the
        offer does not come straight back, then moves on."""
        self.chosen.setdefault(player, [])
        while self.remaining(player) > 0:
            self.chosen[player].append((None, None))
        self._next_player()
        return True

    # --- applying the answers ---------------------------------------------

    def _take_off_board(self, squad):
        """The models leave game_state.tokens. Deliberately NOT
        withdraw_to_reserves(): this unit is about to be placed again in the
        same step, so it must not be recorded in reserves, and neither of that
        function's two follow-ups (clearing the ingress lock, recomputing
        objective control) means anything for a unit mid-redeployment."""
        for model in list(squad.models):
            if model in self.game_state.tokens:
                self.game_state.tokens.remove(model)

    def _apply(self):
        """Act on every answer.

        Returns True if this step took over the sequence - either it resumed
        the caller itself (through on_done) or it put units back into the
        deployment queue. Returns False ONLY when nobody was ever asked, which
        is the case the caller must be free to carry straight on from.

        That distinction is load-bearing: calling on_done AND returning False
        would run _finish_deployment() twice, and the second run would start a
        second first-turn roll-off."""
        pregame = self._pregame
        if not self.chosen:
            return False
        redeploying = []
        for player, picks in sorted(self.chosen.items()):
            for squad, destination in picks:
                if squad is None:
                    continue
                if destination == RESERVES:
                    withdraw_to_reserves(
                        self.game_state, squad, log=self.game_log,
                        message=(f"{player}: {squad.name} uses the "
                                 f"{SOLID_IMAGE_PROJECTION_UNIT} to redeploy into Strategic "
                                 f"Reserves (rule 20.03)."))
                else:
                    self._take_off_board(squad)
                    redeploying.append((player, squad))
        if not redeploying:
            if self._on_done is not None:
                done, self._on_done = self._on_done, None
                done()
            return True
        for player, squad in redeploying:
            pregame._pending.setdefault(player, []).append(squad)
            self._log(f"{player}: {squad.name} is redeployed with the "
                      f"{SOLID_IMAGE_PROJECTION_UNIT}.")
        pregame.state = pregame_module.DEPLOYING
        pregame.active_player = redeploying[0][0]
        pregame._sync_turn_tracker()
        return True
