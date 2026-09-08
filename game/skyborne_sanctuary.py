"""Skyborne Sanctuary (1CP, Strategic Ploy) - printed by TWO detachments.

RULE (verbatim, and byte-identical in rules/aeldari/detachments/Warhost.md and
rules/aeldari/detachments/Aspect Host.md apart from one comma in the flavour
line):
  WHEN:   End of the Fight phase.
  TARGET: One unengaged ASURYANI unit from your army that was eligible to fight
          this phase and one friendly TRANSPORT it is able to embark within.
  EFFECT: If your ASURYANI unit is wholly within 6" of that TRANSPORT, it can
          embark within it.
  RESTRICTIONS: none printed.

THE TARGET LINE NAMES TWO THINGS, SO THE OFFER ASKS TWICE. It used to ask
neither: it raised a prompt about whichever eligible unit sorted FIRST and took
`transports_for(squad)[0]` for the transport, silently. Step one is now a board
pick over every eligible unit (game/unit_choice_offer.py, shared with the three
sibling Stratagems that print the same "One <X> unit from your army"); step two
is an ordinary list, and only when there is more than one legal transport -
never offer what cannot be chosen. That the old one-step prompt read correctly
wherever exactly one Wave Serpent was in range is why it survived.

ONE MODULE, TWO CONTROLLER INSTANCES - the arrangement game/enh_exemplars.py
already uses for the two Exemplars. Two copies of a Stratagem that is the same
sentence twice is the drift this repo consolidates at the second consumer, and
the only thing that differs between the two printings is which config constant
gates it, which is a constructor argument rather than a second file.

"IT IS ABLE TO EMBARK WITHIN" IS THE TRANSPORT'S OWN QUESTION, not a new one.
TransportController.can_embark() already owns capacity, the keyword bans and
rule 18.02's "not set up this turn" - so this asks it rather than re-deriving
any of that, and passes the two things the printed text overrides:

  * require_move=False, because 18.02's "after it has made a Normal move this
    phase" cannot be satisfied at the end of the Fight phase - the unit's move
    was two phases ago. That the Stratagem is about a moment where the normal
    permission cannot apply is the whole reason it exists.
  * range_in=6.0, because the printed distance is 6" and not the ordinary 3".

Both were added to can_embark() as named parameters beside its existing ones,
so every other caller keeps meaning exactly what it did.

"WHOLLY WITHIN 6"" IS THE STRICTER READING, and it is the one printed. WITHIN
would let one model's toe do it; wholly within means every model. This repo has
a whole test section on that distinction because the two look alike and the
wrong one passes any test that puts a unit clearly inside or clearly outside.
can_embark()'s range test is already per model, so passing range_in gets the
strict reading for free - measured rather than assumed, with a straggler.

"UNENGAGED" AND "ELIGIBLE TO FIGHT THIS PHASE" ARE DIFFERENT CLAUSES AND BOTH
ARE CHECKED. A unit can be eligible to fight and still be unengaged by the end
of the phase - it consolidated away, or everything near it died - and that is
precisely the unit this Stratagem is for. Engagement is asked of
game/engagement.py; eligibility is asked of the FightController, which owns
rule 12.04's sticky engaged_at_start set and is the only thing that can still
answer once the phase is over.

"END OF THE FIGHT PHASE", not "your Fight phase" - it belongs to nobody, so
both players are offered it at the same boundary and there is no owner check.

THE WINDOW IS A FACT THIS MODULE OWNS, NOT A LIVE PHASE TEST. This used to read

    if self.turn_tracker.phase != PHASE_FIGHT:
        return False

and that check could never hold. Its only offer is main.py's advance_turn_phase(),
which calls turn_tracker.advance_phase() FIRST and only then runs the
end-of-phase offers - and Fight is the LAST phase, so by the time the offer is
made the clock has rolled all the way round to Command. Both printings of this
Stratagem were therefore a guaranteed, silent no-op: never offered, for either
detachment. Same shape, same cause and same fix as Cost of Victory and Webway
Tunnel before it - see game/phase_window.py.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import (aeldari_detachments, ai_mode, detachment_gate, engagement,
                  unit_choice_offer)
from game.phase_window import PhaseWindow
from game.stratagems import Stratagem

SKYBORNE_SANCTUARY_NAME = "Skyborne Sanctuary"
SKYBORNE_SANCTUARY_CP = 1

#: 'wholly within 6"' - the printed distance, overriding the ordinary 3".
SKYBORNE_SANCTUARY_RANGE_IN = 6.0


def eligible_unit(squad, setting):
    """"One unengaged ASURYANI unit from your army"."""
    if squad is None or not detachment_gate.has_detachment(
            getattr(squad, "owner", None), setting):
        return False
    return aeldari_detachments.is_asuryani_unit(squad)


class SkyborneSanctuaryController:
    """The end-of-Fight-phase offer. Built once per detachment that prints it,
    each with its own `setting`."""

    def __init__(self, stratagem_controller, setting, transport_controller=None,
                 fight_controller=None, game_state=None, all_tokens=None,
                 turn_tracker=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        #: Which detachment's copy this instance is - the ONLY difference
        #: between the two printings.
        self.setting = setting
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
        self._stratagem = Stratagem(
            name=SKYBORNE_SANCTUARY_NAME, cp_cost=SKYBORNE_SANCTUARY_CP,
            effect=self._embark,
        )

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
                    range_in=SKYBORNE_SANCTUARY_RANGE_IN):
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
        if not eligible_unit(squad, self.setting):
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
                    % (SKYBORNE_SANCTUARY_NAME, SKYBORNE_SANCTUARY_CP),
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
            % (SKYBORNE_SANCTUARY_NAME, squad.name),
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
                range_in=SKYBORNE_SANCTUARY_RANGE_IN):
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s embarks within %s."
                    % (SKYBORNE_SANCTUARY_NAME, squad.name,
                       transport_token.squad.name))
