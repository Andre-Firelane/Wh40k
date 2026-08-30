"""The Starfangs' "Hallucinogen Grenades" - a datasheet ability.

RULE (printed, word for word):
  "At the start of your opponent's Shooting phase, this unit can use this
  ability. If it does, select one AELDARI INFANTRY unit from your army visible
  to and within 36" of this unit: until the end of the phase, that unit has the
  Stealth ability."

STEALTH IS GRANTED FOR A PHASE, WHICH IT HAS NEVER BEEN BEFORE
---------------------------------------------------------------
Rule 24.33's Stealth is answered by game/squad.py's squad_has_stealth(), which
until now read a printed flag off the models - every carrier has it or does
not. This is the first TEMPORARY grant, so that question grows a second source
rather than the grant being written as a flag someone has to remember to clear.

Held per squad with an expiry, not as a bare boolean, for the reason
game/montka_pulse_onslaught.py gives for `shaken`: a flag cleared in "the usual
end-of-phase block" is one phase boundary away from being cleared in the wrong
one, and this effect lives across a boundary the granting player does not own.

"AT THE START OF YOUR OPPONENT'S SHOOTING PHASE" is the awkward part and the
reason this is offered rather than automatic: it fires in the phase the OTHER
player is about to shoot in, so the decision belongs to the Starfangs' owner
while the turn belongs to their opponent. Same shape as every reactive
Stratagem here, and `auto_players` answers it for the AI so nothing stalls.
"""

HALLUCINOGEN_GRENADES_LABEL = "Hallucinogen Grenades"

#: "visible to and within 36 inches of this unit".
HALLUCINOGEN_RANGE_IN = 36.0


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def has_ability(squad):
    return any(getattr(m.profile, "hallucinogen_grenades", False) for m in _living(squad))


def has_granted_stealth(squad):
    """The second source game/squad.py's squad_has_stealth() asks."""
    return bool(getattr(squad, "granted_stealth_until_phase", None))


class HallucinogenGrenadesController:
    """The offer, the grant, and the phase-long expiry."""

    def __init__(self, decision_manager=None, game_log=None, all_tokens=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.auto_players = set(auto_players)
        self._granted = []

    def _squads(self):
        seen = []
        for token in self.all_tokens or ():
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in seen:
                seen.append(squad)
        return seen

    def candidates(self, bearer, visible_to=None):
        """"one AELDARI INFANTRY unit from YOUR army, visible to and within
        36 inches" - so it is friendly, and both keywords must hold."""
        from game import psychic_guidance
        from game.squad import edge_distance
        mine = _living(bearer)
        out = []
        for squad in self._squads():
            if squad is bearer or squad.owner != bearer.owner:
                continue
            living = _living(squad)
            if not living or not any(m.profile.infantry for m in living):
                continue
            if not psychic_guidance._is_aeldari(squad):
                continue
            if visible_to is not None and not visible_to(squad):
                continue
            if any(edge_distance(a, b) <= HALLUCINOGEN_RANGE_IN
                   for a in mine for b in living):
                out.append(squad)
        return out

    def grant(self, bearer, target):
        if target is None:
            return False
        target.granted_stealth_until_phase = True
        self._granted.append(target)
        if self.game_log is not None:
            self.game_log.add("%s: %s has the Stealth ability until the end of the phase."
                              % (HALLUCINOGEN_GRENADES_LABEL, target.name))
        return True

    def offer_at_start_of_opponent_shooting(self, shooting_player, visible_to=None):
        """`shooting_player` is whose Shooting phase is beginning; the OFFER
        goes to everyone else."""
        for bearer in self._squads():
            if bearer.owner == shooting_player or not has_ability(bearer):
                continue
            options = self.candidates(bearer, visible_to=visible_to)
            if not options:
                continue
            if bearer.owner in self.auto_players or self.decision_manager is None:
                self.grant(bearer, options[0])
                continue
            self.decision_manager.request(
                bearer.owner,
                "%s: %s - give which friendly AELDARI INFANTRY unit Stealth?"
                % (HALLUCINOGEN_GRENADES_LABEL, bearer.name),
                [(t.name, (lambda b=bearer, t=t: self.grant(b, t))) for t in options]
                + [("Do not use it", None)])
            return True
        return False

    def reset_phase(self):
        """"Until the end of the phase"."""
        for squad in self._granted:
            squad.granted_stealth_until_phase = False
        self._granted = []
