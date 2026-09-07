"""Kauyon Stratagem: Combat Embarkation (1CP).

RULE (verbatim, rules/tau_empire/detachments/Kauyon.md):
  WHEN:   Your opponent's Charge phase, just after an enemy unit has declared a
          charge.
  TARGET: One T'AU EMPIRE INFANTRY unit from your army that was selected as one
          of the targets of that charge, and one friendly TRANSPORT.
  EFFECT: Your unit can embark within that TRANSPORT. If it does, your opponent
          can select new targets for that charge.
  RESTRICTIONS: Every model in your T'AU EMPIRE INFANTRY unit must be within 3"
          of that TRANSPORT and there must be sufficient transport capacity to
          embark the entire unit.

IT OVERRIDES *WHEN* YOU MAY EMBARK, NOT *WHETHER* YOU FIT
---------------------------------------------------------
Rule 18.02 lets a unit embark only after a Normal/Advance/Fall Back move in its
own Movement phase. This happens in the OPPONENT'S Charge phase, so that clause
has to be lifted - and only that clause. game/transport.py's can_embark() grew
a `require_move` flag for exactly this, so the 3", the capacity and the
transport's own keyword restrictions (a Devilfish still refuses BATTLESUIT,
KROOT and VESPID STINGWINGS models) all keep applying from their one
definition. The printed RESTRICTIONS line names the same 3" and the same
capacity, so nothing here restates them.

"YOUR OPPONENT CAN SELECT NEW TARGETS FOR THAT CHARGE" - A NAMED LIMITATION
---------------------------------------------------------------------------
The engine does not re-open target declaration mid-charge. What it does do is
re-check the charge's preconditions when the reaction hands control back:
ChargeController._start_declared_move() says so in its own docstring, because
"an arbitrary amount of resolution can have happened in between". An embarked
unit is off the board, so it stops being a legal target; a charge that named
only that unit therefore fizzles, and one that named others continues against
them.

What is MISSING is the opponent's permission to pick DIFFERENT targets than the
ones already declared. That is strictly worse for the charging player than the
printed rule, so this errs against the player who did NOT buy the Stratagem -
the wrong direction to err in, and it is written out here rather than left to
be discovered. Fixing it properly means re-entering DECLARING_TARGETS with the
roll already made, which is a change to the charge sequence itself.
"""

from game import ai_mode, kauyon, tau_detachments
from game.squad import edge_distance
from game.stratagems import Stratagem
from game.transport import EMBARK_RANGE_IN
from game.turn import PHASE_CHARGE

COMBAT_EMBARKATION_CP = 1
COMBAT_EMBARKATION_NAME = "Combat Embarkation"


class CombatEmbarkationController:
    def __init__(self, stratagem_controller, transport_controller=None,
                 turn_tracker=None, all_tokens=None, decision_manager=None,
                 game_log=None, auto_players=(), charge_controller=None):
        self.stratagem_controller = stratagem_controller
        self.transport_controller = transport_controller
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._stratagem = Stratagem(
            name=COMBAT_EMBARKATION_NAME, cp_cost=COMBAT_EMBARKATION_CP, effect=self._embark,
            allow_repeat_target=True,   # each enemy charge is its own window
        )
        self.charge_controller = charge_controller
        self._pending = None      # (squad, transport_token)
        self._resume = None
        self._charging = None     # whose declaration this window belongs to

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)

    def transports_for(self, squad):
        """Friendly TRANSPORTs this unit could board right now - the printed
        3" and capacity, asked of game/transport.py so there is one answer."""
        if self.transport_controller is None:
            return []
        found = []
        for token in self.all_tokens:
            if not getattr(token.profile, "transport", False):
                continue
            if getattr(token, "squad", None) is None or token.squad.owner != squad.owner:
                continue
            if not self.transport_controller.can_embark(squad, token, require_move=False):
                continue
            found.append(token)
        return found

    def eligible_defenders(self, charging_squad, targets):
        out = []
        for squad in targets or ():
            if squad is None or squad.owner == charging_squad.owner:
                continue
            if not tau_detachments.has_detachment(squad.owner, kauyon.SETTING):
                continue
            if not tau_detachments.is_tau_unit(squad):
                continue
            if not all(m.profile.infantry for m in squad.models if not m.is_dead()):
                continue
            if not self.transports_for(squad):
                continue
            if not self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad]):
                continue
            out.append(squad)
        return sorted(out, key=lambda s: s.name)

    def maybe_offer(self, charging_squad, targets, on_resolved=None):
        """ChargeController's declaration-reaction protocol."""
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_CHARGE:
            return False
        candidates = self.eligible_defenders(charging_squad, targets)
        if not candidates:
            return False
        reactor = candidates[0].owner
        if reactor in self.auto_players or self.decision_manager is None:
            return False
        self._resume = on_resolved
        self._charging = charging_squad
        options = []
        for squad in candidates:
            for transport in self.transports_for(squad):
                options.append((
                    f"{squad.name} -> {transport.profile.name}",
                    (lambda s=squad, t=transport: self._accept(s, t)),
                    # Tagged with the EMBARKING unit, so the usual case - one
                    # transport in range - is answered by clicking it on the
                    # board. A unit with two transports in range lands in the
                    # list twice, and game/unit_pick.py refuses the whole prompt
                    # then: a click says "this unit", which cannot pick between
                    # two vehicles. Falling back to the list is always
                    # answerable, so the ambiguous case simply reads as before.
                    squad,
                ))
        self.decision_manager.request(
            reactor,
            f"{COMBAT_EMBARKATION_NAME} ({COMBAT_EMBARKATION_CP} CP): "
            f"{charging_squad.name} has declared a charge - board a TRANSPORT instead?",
            options + [("Decline", self._decline)],
        )
        return True

    def _accept(self, squad, transport_token):
        self._pending = (squad, transport_token)
        used = self.stratagem_controller.use(squad.owner, self._stratagem, [squad])
        if not used:
            self._pending = None
            self._finish()
        return used

    def _decline(self):
        self._finish()
        return True

    def _embark(self, controller, player, targets):
        pending, self._pending = self._pending, None
        reopened = False
        if pending is not None:
            squad, transport_token = pending
            self.transport_controller.embark(squad, transport_token, require_move=False)
            self._log(
                f"{COMBAT_EMBARKATION_NAME}: {squad.name} boards "
                f"{transport_token.profile.name} to escape the charge."
            )
            # "If it does, your opponent can select new targets for that
            # charge." Hand declaration back with the roll intact, instead of
            # resuming into a move that would still be resolved against the
            # unit now sitting inside the vehicle - embark() takes its models
            # out of the token list but leaves their coordinates alone, so
            # check_charge_engagement() happily engages a phantom.
            if self.charge_controller is not None:
                reopened = self.charge_controller.reopen_target_selection(squad)
        self._finish(reopened=reopened)

    def _finish(self, reopened=False):
        """Hand the chain on, exactly as the declaration-reaction protocol says.

        The resume is called even when the declaration has been RE-OPENED, and
        that is deliberate: swallowing it here would stop the chain by accident
        and leave ChargeController's own window_is_open() guard unreachable -
        a branch no input can reach is the shape this repo keeps finding rotted
        (an A/B probe caught exactly that). Instead the guard does its job: it
        sees the re-opened declaration, the chain ends without calling
        _start_declared_move(), and any reactor still queued behind this one is
        correctly skipped, because the declaration those reactors were
        answering no longer stands.

        NOTE, measured rather than assumed: there is deliberately no
        turn_tracker.set_active() here. Its sibling on this chain
        (game/kauyon_photon_grenades.py) restores the charging player in its
        own _finish(), but only because the Battle-shock test it starts moves
        active_player in the first place. Nothing on this Stratagem's path
        moves it, so "restoring" it would be a no-op dressed up as a fix.
        """
        del reopened          # the CHARGE controller owns that fact, not this
        self._charging = None
        resume, self._resume = self._resume, None
        if resume is not None:
            resume()


def models_within_embark_range(squad, transport_token):
    """The printed RESTRICTION, exposed for tests: every model within 3"."""
    alive = [m for m in squad.models if not m.is_dead()]
    return bool(alive) and all(
        edge_distance(m, transport_token) <= EMBARK_RANGE_IN for m in alive)
