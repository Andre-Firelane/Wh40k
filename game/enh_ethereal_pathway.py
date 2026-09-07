"""Armoured Warhost Enhancement: Ethereal Pathway (30 pts).

RULE (verbatim, rules/aeldari/detachments/Armoured Warhost.md):
  "ASURYANI model only. In the Deploy Armies step, select up to two GUARDIANS
  units from your army. Models in the selected units have the Infiltrators
  ability."

THE SECOND INSTANCE OF ONE ORDERING QUESTION, and it bites a step earlier than
Firstdrawn Blade's. Rule 24.20's INFILTRATORS changes TWO things in
game/pregame.py, and both happen while armies are being set up:

  * WHERE a unit may be placed (_infiltrator_position_valid(): more than 8"
    from every enemy unit, and out of the opponent's deployment zone), and
  * WHEN it is placed - infiltrator units deploy LAST, because the ability is
    evaluated at the moment of setting up and going early gains nothing.

So the grant has to land BEFORE the deployment order is decided. Granted after
it, the unit would carry INFILTRATORS, be validated against the wrong
predicate's opposite, and deploy in the ordinary sequence - perfect in a unit
test, inert in a game. That is the same failure Strike Swiftly documented for
the Scout step, one step earlier in 03.01.

"IN THE DEPLOY ARMIES STEP" IS THEREFORE READ AS "just before it", which is
where the choice can still change anything. Named rather than silently treated
as the same moment.

"UP TO TWO" IS A REAL CHOICE, so it is asked - unlike Firstdrawn Blade, which
names the bearer's own unit and resolves itself. "Up to" also means ZERO is a
legal answer, and the offer says so.

24.20 IS AN EVERY-MODEL ABILITY (squad_has_infiltrators() uses unit_wide_
ability()), so the grant marks every model of a selected unit - marking only
some would satisfy nothing.

GUARDIANS, NOT THE BEARER'S UNIT. The bearer is ASURYANI; what it selects is
"GUARDIANS units from your army", which need not include its own and need not
be anywhere near it - there is no distance in this card at all.
"""
from game import ai_mode, attached_units, enhancements

ETHEREAL_PATHWAY = "Ethereal Pathway"

ETHEREAL_PATHWAY_LABEL = "Ethereal Pathway"

#: "select up to TWO GUARDIANS units".
ETHEREAL_PATHWAY_MAX_UNITS = 2

#: "GUARDIANS units from your army".
ETHEREAL_PATHWAY_KEYWORD = "GUARDIANS"


def has_bearer(squad):
    return enhancements.is_active(squad, ETHEREAL_PATHWAY)


def is_eligible_target(squad, owner):
    """"up to two GUARDIANS units from YOUR army" - and one that already has
    INFILTRATORS is not offered, because the grant would buy it nothing."""
    if squad is None or squad.owner != owner:
        return False
    if not attached_units.unit_has_datasheet_keyword(squad, ETHEREAL_PATHWAY_KEYWORD):
        return False
    from game.squad import squad_has_infiltrators
    return not squad_has_infiltrators(squad)


def grant_infiltrators(squad, game_log=None):
    """"Models in the selected units have the Infiltrators ability".

    EVERY model, because rule 24.20 only applies "if every model in a unit has
    this ability" - marking some would grant nothing at all."""
    if squad is None:
        return False
    for model in squad.models:
        model.profile.infiltrators = True
    if game_log is not None:
        game_log.add("%s: %s has Infiltrators (rule 24.20) from the %s Enhancement."
                     % (squad.owner, squad.name, ETHEREAL_PATHWAY))
    return True


class EtherealPathwayStep:
    """One of PregameController's `deploy_armies_steps`, which run at the top
    of _set_deploy_order() - i.e. just before the Deploy Armies step reads
    either half of rule 24.20. See the module docstring."""

    def __init__(self, game_state=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._on_done = None
        self._pending_players = []
        self._chosen = 0

    def _squads(self):
        seen, out = set(), []
        for token in getattr(self.game_state, "tokens", ()) or ():
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen.add(id(squad))
                out.append(squad)
        return out

    def owners_with_bearer(self):
        return sorted({s.owner for s in self._squads() if has_bearer(s)})

    def candidates(self, player):
        return [s for s in self._squads() if is_eligible_target(s, player)]

    # --- the step protocol -------------------------------------------------

    def start(self, pregame_controller, on_done=None):
        """True when a prompt is on screen, False when there was nothing to
        do - the same contract game/enh_strike_swiftly.py's step has."""
        self._on_done = on_done
        self._pending_players = self.owners_with_bearer()
        return self._next_player()

    def _next_player(self):
        while self._pending_players:
            player = self._pending_players.pop(0)
            self._chosen = 0
            if self._offer(player):
                return True
        return False

    def _offer(self, player):
        if self._chosen >= ETHEREAL_PATHWAY_MAX_UNITS:
            return False
        options = self.candidates(player)
        if not options:
            return False
        if player in self.auto_players or self.decision_manager is None:
            # Deterministic and no API call: take the first eligible units, up
            # to the printed two. There is no board yet to judge them on - this
            # runs before anything is placed - so any ordering is as good as
            # another and a prompt nobody answers would stall the sequence.
            for squad in options[:ETHEREAL_PATHWAY_MAX_UNITS]:
                grant_infiltrators(squad, game_log=self.game_log)
            return False
        self.decision_manager.request(
            player,
            "%s: give Infiltrators to a GUARDIANS unit? (%d of %d chosen)"
            % (ETHEREAL_PATHWAY_LABEL, self._chosen, ETHEREAL_PATHWAY_MAX_UNITS),
            [(squad.name, (lambda s=squad, p=player: self._choose(p, s)), squad)
             for squad in options]
            # "UP TO two" - stopping early, or choosing none at all, is a legal
            # answer and has to be offered as one.
            + [("Done", lambda p=player: self._done(p))],
        )
        return True

    def _choose(self, player, squad):
        grant_infiltrators(squad, game_log=self.game_log)
        self._chosen += 1
        if not self._offer(player):
            self._done(player)
        return True

    def _done(self, player):
        if not self._next_player() and self._on_done is not None:
            self._on_done()
        return True
