"""The end-of-Fight-phase EMBARK Stratagem - one mechanism, three printings.

  * Skyborne Sanctuary (Aeldari Warhost and Aspect Host, word for word):
    "One unengaged ASURYANI unit from your army that was eligible to fight this
    phase and one friendly TRANSPORT it is able to embark within ... If your
    ASURYANI unit is wholly within 6" of that TRANSPORT, it can embark within
    it." - game/skyborne_sanctuary.py
  * Keep It Runnin' (Orks Blitz Brigade, Mecha Orks G4): "One friendly
    unengaged ORKS INFANTRY unit that was eligible to fight this phase and is
    wholly within 6" of a friendly TRANSPORT unit that INFANTRY unit is able to
    embark within ... Your INFANTRY unit embarks within that TRANSPORT unit." -
    game/blitz_keep_it_runnin.py

WHY THIS EXISTS. The class was written as SkyborneSanctuaryController and grew
two instances for the two Aeldari printings. The Ork card is the same sentence
with another TARGET keyword, and an Ork Stratagem subclassing a class named
after an Aeldari one would carry a lying name (error class 11) - so the
mechanism moved here, verbatim, with the three things that differ as knobs:
NAME/CP, RANGE_IN and eligible_unit(). Every reading documented in
game/skyborne_sanctuary.py's docstring (the two-step pick, can_embark()'s
require_move=False and range_in, "wholly within" as the per-model test,
"unengaged" and "eligible to fight" as two clauses, the PhaseWindow instead of a
live phase test, "End of THE Fight phase" offered to both players) is a reading
of this shared code and holds for all three.

THE AI DECLINES every printing: game/unit_choice_offer.py raises no prompt for an
auto player, by design (taking a unit off the board unasked is a real cost).
"""

from game import ai_mode, engagement, unit_choice_offer
from game.phase_window import PhaseWindow
from game.stratagems import Stratagem


class EndOfFightEmbarkController:
    """The end-of-Fight-phase embark offer. A subclass names the Stratagem
    (NAME, CP), its distance (RANGE_IN) and which unit may be its TARGET
    (eligible_unit()); everything else is here."""

    NAME = None
    CP = 1
    #: The printed distance, overriding 18.02's ordinary 3".
    RANGE_IN = 6.0

    def __init__(self, stratagem_controller, transport_controller=None,
                 fight_controller=None, game_state=None, all_tokens=None,
                 turn_tracker=None, decision_manager=None, game_log=None,
                 auto_players=()):
        if not self.NAME:
            raise TypeError("%s must set NAME" % type(self).__name__)
        self.stratagem_controller = stratagem_controller
        self.transport_controller = transport_controller
        self.fight_controller = fight_controller
        self.game_state = game_state
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        # The end-of-Fight-phase window this controller's own offer opens.
        # NOT a live turn_tracker.phase test - see game/phase_window.py.
        self._window = PhaseWindow()
        self._pending = {}
        self._stratagem = Stratagem(name=self.NAME, cp_cost=self.CP, effect=self._embark)

    # ------------------------------------------------------------- subclass
    def eligible_unit(self, squad):
        """The TARGET's own words ("One unengaged ASURYANI unit from your
        army", "One friendly unengaged ORKS INFANTRY unit") - the detachment
        gate included. The shared clauses below are not part of it."""
        raise NotImplementedError

    def was_eligible_to_fight(self, squad):
        """"that was eligible to fight this phase" - asked of the controller
        that owns rule 12.04's sticky engaged_at_start set. Nothing else can
        still answer this once the phase has ended."""
        if self.fight_controller is None:
            return True
        return self.fight_controller.is_eligible_to_fight(squad)

    def transports_for(self, squad):
        """"one friendly TRANSPORT it is able to embark within", within 6".

        Every part of "able to embark within" is can_embark()'s to answer -
        capacity, the keyword bans, 18.02 - which is why the two overrides are
        parameters on it rather than a second opinion here."""
        if self.transport_controller is None or squad is None:
            return []
        out = []
        for token in (self.all_tokens or ()):
            other = getattr(token, "squad", None)
            if other is None or other.owner != squad.owner or other is squad:
                continue
            if token.is_dead():
                continue
            if self.transport_controller.can_embark(
                    squad, token, require_move=False,
                    range_in=self.RANGE_IN):
                out.append(token)
        return out

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None:
            return False
        # The window is the one this controller's own offer opened, not a live
        # phase test: the offer runs AFTER advance_phase(), and Fight is the
        # last phase, so the clock already reads Command by then. See
        # game/phase_window.py.
        if not self._window.is_open(squad.owner):
            return False
        if not self.eligible_unit(squad):
            return False
        if not any(not m.is_dead() for m in (getattr(squad, "models", ()) or ())):
            return False
        # "UNENGAGED" - a separate clause from "eligible to fight", and both
        # can be true at once, which is the case this Stratagem is for.
        if engagement.is_engaged(squad, self.all_tokens):
            return False
        if not self.was_eligible_to_fight(squad):
            return False
        if not self.transports_for(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def reset_phase(self):
        """The window lasts exactly one phase boundary. main.py clears it in
        the per-phase reset block, which runs BEFORE that boundary's offers."""
        self._window.close()

    def offer_at_end_of_fight_phase(self, squads):
        """"End of THE Fight phase" - it belongs to nobody, so both players
        are offered it at the same boundary, and no owner is passed in.

        There is deliberately no live phase test any more: this runs AFTER
        advance_phase(), so `phase != PHASE_FIGHT` was always true and this
        Stratagem never opened a prompt at all. See game/phase_window.py."""
        # ONE prompt listing EVERY eligible unit, each tagged with itself, so
        # the choice is made by clicking on the board. It used to raise a
        # yes/no about whichever unit sorted first, with the TRANSPORT picked
        # silently as transports_for(squad)[0]. See game/unit_choice_offer.py.
        #
        # TWO STEPS, because the printed TARGET names TWO things: "One
        # unengaged ASURYANI unit ... AND one friendly TRANSPORT it is able to
        # embark within". Step one is the board pick; step two is an ordinary
        # list, and only when there is really a choice - see _choose_transport.
        #
        # The window is armed BEFORE the eligibility test, because can_use()
        # asks it: the window IS this offer's own "right moment". Closed again
        # if nothing was actually put to that player.
        for player in sorted({s.owner for s in squads}, key=str):
            self._window.arm(player)
            candidates = [s for s in sorted(squads, key=lambda s: s.name)
                          if s.owner == player and self.can_use(s)]
            if unit_choice_offer.offer_one_of(
                    self.decision_manager, player, candidates,
                    "%s (%d CP): which unit embarks within a TRANSPORT?"
                    % (self.NAME, self.CP),
                    self._choose_transport, auto_players=self.auto_players,
                    is_stratagem=True):
                return True
            self._window.close()       # nothing offered - and no AI path
        return False

    def _choose_transport(self, squad):
        """Step two: WHICH TRANSPORT, and only when that is a real question.

        A single legal transport is resolved without asking - "never offer what
        cannot be chosen" - which is also why the old one-step prompt read
        correctly on the boards where only one Wave Serpent was in range, and
        silently took transports_for(squad)[0] everywhere else.

        An ordinary LIST, not a second board pick: the options name TRANSPORTS
        that belong to the same player and may sit under the unit that was just
        clicked, so rings would be ambiguous about which of the two things on
        that spot is being chosen."""
        transports = self.transports_for(squad)
        if not transports:
            return False
        if len(transports) == 1 or self.decision_manager is None:
            return self.use(squad, transports[0])
        self.decision_manager.request(
            squad.owner,
            "%s: embark %s within which TRANSPORT?"
            % (self.NAME, squad.name),
            [(token.squad.name, (lambda s=squad, t=token: self.use(s, t)))
             for token in transports]
            + [("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, squad, transport_token=None):
        if not self.can_use(squad):
            return False
        if transport_token is None:
            transport_token = self.transports_for(squad)[0]
        self._pending[squad.owner] = (squad, transport_token)
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _embark(self, controller, player, targets):
        squad, transport_token = self._pending.pop(player, (None, None))
        if squad is None or self.transport_controller is None:
            return
        if self.transport_controller.embark(
                squad, transport_token, require_move=False,
                range_in=self.RANGE_IN):
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s embarks within %s."
                    % (self.NAME, squad.name,
                       transport_token.squad.name))
