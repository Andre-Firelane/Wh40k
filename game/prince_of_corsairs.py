"""Prince Yriel's "Prince of Corsairs" - a datasheet ability.

RULE (printed, word for word):
  "After both players have deployed their armies, if this unit is on the
  battlefield (or any TRANSPORT it is embarked within is on the battlefield),
  select up to three AELDARI units from your army and redeploy them. When doing
  so, you can set those units up in Strategic Reserves, regardless of how many
  units are already in Strategic Reserves."

THE SECOND CONSUMER OF PregameController.redeploy_step
-------------------------------------------------------
Kauyon's Solid-image Projection Unit is the first, and it fires at the same
instant: "after both players have deployed", which is EARLIER than Resolve
Pre-battle Abilities and therefore its own hook rather than a member of
prebattle_steps. Nothing new was needed for the timing.

WHAT IS NEW is the second half. Solid-image redeploys onto the board; this one
may put a unit into STRATEGIC RESERVES instead, and explicitly overrides the
50% limit that would normally cap it ("regardless of how many units are already
in Strategic Reserves"). game/strategic_reserves.py already has the withdrawal
- the Vespid's Airborne Agility takes units off the board the same way - so
what this adds is the override, not the mechanism.

"IF THIS UNIT IS ON THE BATTLEFIELD (or any TRANSPORT it is embarked within
is)" - so a Yriel who deep-struck into reserve grants nothing. Checked against
the board rather than assumed, because the reserve case is the one that would
silently keep working.

THE AI DECLINES, deliberately and for the same reason Solid-image does: a
redeployment is a whole-army judgement, the deployment AI has just placed
everything where it wanted it, and moving three units at random makes its own
deployment worse. Recorded as a decision rather than left as an omission.
"""

PRINCE_OF_CORSAIRS_LABEL = "Prince of Corsairs"

#: "select up to three AELDARI units".
MAX_REDEPLOYED_UNITS = 3


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def has_ability(squad):
    return any(getattr(m.profile, "prince_of_corsairs", False) for m in _living(squad))


class PrinceOfCorsairsStep:
    """PregameController.redeploy_step's protocol, shared with Kauyon's
    Solid-image Projection Unit."""

    def __init__(self, game_state=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self.redeployed = {}        # player -> [squads]

    def _squads(self):
        seen = []
        for token in (getattr(self.game_state, "tokens", None) or ()):
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in seen:
                seen.append(squad)
        return seen

    def bearer_on_battlefield(self, player):
        """"if this unit is ON THE BATTLEFIELD (or any TRANSPORT it is embarked
        within is)". A Yriel in Strategic Reserves grants nothing - and that is
        the case that would silently keep working if it went unchecked."""
        for squad in self._squads():
            if squad.owner == player and has_ability(squad):
                return True
        for squad in (getattr(self.game_state, "embarked_squads", None) or ()):
            if squad.owner != player or not has_ability(squad):
                continue
            transport = getattr(squad, "embarked_in", None)
            if transport is not None and transport in (
                    getattr(self.game_state, "tokens", None) or ()):
                return True
        return False

    def remaining(self, player):
        return MAX_REDEPLOYED_UNITS - len(self.redeployed.get(player, []))

    def candidates(self, player):
        from game import psychic_guidance
        already = self.redeployed.get(player, [])
        return [s for s in self._squads()
                if s.owner == player and s not in already
                and psychic_guidance._is_aeldari(s)]

    def send_to_reserves(self, player, squad):
        """"you can set those units up in Strategic Reserves, REGARDLESS of how
        many units are already in Strategic Reserves" - so the ordinary cap is
        explicitly bypassed here."""
        if squad is None or self.remaining(player) <= 0:
            return False
        # game/strategic_reserves.py is a MODULE, not a controller - the same
        # board->reserves move Starflare Ignition and Unshrouded Truth already
        # make, taking the GameState whose lists it moves the unit between.
        from game import strategic_reserves
        if self.game_state is not None:
            strategic_reserves.withdraw_to_reserves(
                self.game_state, squad, log=self.game_log,
                message="%s: %s redeploys into Strategic Reserves."
                        % (PRINCE_OF_CORSAIRS_LABEL, squad.name))
        self.redeployed.setdefault(player, []).append(squad)
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s is redeployed into Strategic Reserves (the usual limit "
                "does not apply)." % (PRINCE_OF_CORSAIRS_LABEL, squad.name))
        return True

    def start(self, pregame_controller=None, on_done=None):
        """Returns True while a human prompt is outstanding."""
        players = list(getattr(pregame_controller, "_owners", lambda: ())() or ())
        for player in players:
            if not self.bearer_on_battlefield(player):
                continue
            if player in self.auto_players or self.decision_manager is None:
                # The AI declines - see the module docstring.
                continue
            options = self.candidates(player)
            if not options or self.remaining(player) <= 0:
                continue
            self.decision_manager.request(
                player,
                "%s: redeploy a unit into Strategic Reserves? (%d left)"
                % (PRINCE_OF_CORSAIRS_LABEL, self.remaining(player)),
                [(s.name, (lambda p=player, s=s: self._answer(p, s, pregame_controller, on_done)))
                 for s in options]
                + [("No more", (lambda: self._finish(on_done)))])
            return True
        if on_done is not None:
            on_done()
        return False

    def _answer(self, player, squad, pregame_controller, on_done):
        self.send_to_reserves(player, squad)
        # Keep offering while there is room, then hand control back.
        self.start(pregame_controller, on_done)
        return True

    def _finish(self, on_done):
        if on_done is not None:
            on_done()
        return True
