"""«After both players have deployed, redeploy up to N of your units.»

The machine behind two abilities that print that sentence with two words
changed, and the one PregameController hook they both hang on.

RULES (printed, word for word):

  SOLID-IMAGE PROJECTION UNIT - Kauyon Enhancement:
    "...after both players have deployed their armies, select up to three
     T'AU EMPIRE units from your army and redeploy them. When doing so, any of
     those units can be placed into Strategic Reserves, regardless of how many
     units are already in Strategic Reserves."

  GRAND ILLUSION - C'tan Shard of the Deceiver:
    "If your army includes this model, after both players have deployed their
     armies, select up to three NECRONS units from your army and redeploy them.
     When doing so, any of those units can be placed into Strategic Reserves,
     regardless of how many units are already in Strategic Reserves."

Two words: the faction, and who grants it. Everything else - the count, the two
destinations, the two-step board pick, the AI's refusal, and the whole
`_apply()` dance with the deployment queue - is the same, which is why it is
written here once.

WHY THE HOOK IS `redeploy_step` AND NOT `prebattle_steps`
----------------------------------------------------------
Both fire "after both players have deployed", which is EARLIER than Resolve
Pre-battle Abilities: Determine First Turn sits between the two moments. So
PregameController fires this from _finish_deployment() (game/pregame.py), and
main.py's `_RedeployChain` is what lets more than one of them exist.

THE RETURN VALUE OF start() IS LOAD-BEARING
---------------------------------------------
True means "I took over" - a prompt is on screen, or units are back in the
deployment queue. False means "there was nothing to do, carry straight on".
Calling on_done AND returning False runs _finish_deployment() twice, and the
second run starts a second first-turn roll-off - the bug that produced a
reported triple battle start. game/pregame.py's `Resume` one-shot now enforces
this at the DRIVER, so both readings are safe; this class still takes the
honest one.

"REGARDLESS OF HOW MANY UNITS ARE ALREADY IN STRATEGIC RESERVES" IS A
DOCUMENTED NO-OP, not a switch. Rule 20.01's cap is enforced once, in
PregameController.finish_formations_for()'s declaration step, which has already
run by the time this fires. There is nothing left here to override.

THE AI DECLINES OUTRIGHT, deliberately. A redeployment is a whole-army
judgement; the deployment AI has just placed everything where it wanted it, and
moving three units at random makes its own deployment worse. Recorded as a
decision rather than left as an omission.

A THIRD CARRIER EXISTS AND IS DELIBERATELY NOT CONVERTED.
game/prince_of_corsairs.py (Prince Yriel) prints the same sentence for AELDARI
and hangs on the same hook, but its implementation offers only the Strategic
Reserves half - it never puts a unit back in the deployment queue, which its
own printed "and redeploy them" asks for. Folding it in here would therefore
not be a refactor but a behaviour change to a shipped Aeldari ability, and that
belongs in its own measured step rather than riding along inside a Necron one.
Named here so the gap is visible rather than rediscovered.
"""

from game import ai_mode
from game import pregame as pregame_module
from game.strategic_reserves import withdraw_to_reserves

MAX_UNITS = 3

REDEPLOY = "redeploy"
RESERVES = "reserves"


def living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


class PostDeploymentRedeployStep:
    """Registered as PregameController.redeploy_step by main.py.

    A subclass supplies three things:

      label            what the prompts and the log call it
      grants(player)   whether this player's army has the thing at all
      in_faction(sq)   the printed faction test on the units it may move
    """

    label = "Redeploy"
    max_units = MAX_UNITS

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

    # --- what a subclass supplies -----------------------------------------

    def grants(self, player):
        """Whether this player's army contains the model or enhancement that
        grants the ability at all."""
        raise NotImplementedError

    def in_faction(self, squad):
        """The printed faction test - "three T'AU EMPIRE units", "three
        NECRONS units"."""
        raise NotImplementedError

    # --- the rule ---------------------------------------------------------

    def _squads(self):
        seen = []
        for token in (getattr(self.game_state, "tokens", None) or ()):
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in seen:
                seen.append(squad)
        return seen

    def eligible_targets(self, player):
        """On the battlefield, since a unit already in Strategic Reserves has
        nothing to redeploy."""
        taken = [s for s, _ in self.chosen.get(player, [])]
        return [s for s in self._squads()
                if s.owner == player and s not in taken
                and self.in_faction(s) and living(s)]

    def remaining(self, player):
        return self.max_units - len(self.chosen.get(player, []))

    # --- the step ---------------------------------------------------------

    def start(self, pregame_controller, on_done=None):
        """Returns True if it took over - see the module docstring."""
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
        if not self.grants(player):
            return False
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
                "%s: redeploy a unit? (%d left)" % (self.label, self.remaining(player)),
                options)
            return True
        return False

    def _offer_destination(self, player, squad):
        """Step two: what happens to the unit just picked on the board."""
        if self.decision_manager is None:
            return self.choose(player, squad, REDEPLOY)
        self.decision_manager.request(
            player,
            "%s: %s - set it up again, or put it into Strategic Reserves?"
            % (self.label, squad.name),
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
        """Act on every answer. See the module docstring on the return value."""
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
                        message=("%s: %s uses %s to redeploy into Strategic "
                                 "Reserves (rule 20.03)."
                                 % (player, squad.name, self.label)))
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
            self._log("%s: %s is redeployed with %s." % (player, squad.name, self.label))
        pregame.state = pregame_module.DEPLOYING
        pregame.active_player = redeploying[0][0]
        pregame._sync_turn_tracker()
        return True
