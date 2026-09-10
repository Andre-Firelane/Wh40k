"""Canoptek Spyders' "Canoptek Swarm" (Necrons).

RULE (printed, word for word):
  "In your Command phase, select one friendly CANOPTEK SCARAB SWARM unit
   within 6" of this unit. One destroyed model is returned to that CANOPTEK
   SCARAB SWARM unit for each SPYDER model in this unit."

THE SEVENTH MODEL-RETURN ABILITY, and structurally the Painboy's Grot Orderly:
same game/model_return.py, same formation_layout.returning_positions(), same
routing through game/return_placement.py so a HUMAN sets up what comes back
(rule 01.02.03 says a returning model is SET UP, and setting up is the
controlling player's job) while an owner in `auto_players` lands on the
engine's spots outright.

THREE PRINTED DIFFERENCES FROM ITS SIX PREDECESSORS:

  * THE COUNT IS NOT A DIE. "one destroyed model ... for each SPYDER model in
    this unit" - so a two-Spyder unit returns two Scarabs, deterministically.
    Nothing is rolled, which is why this module never touches DiceManager.
  * IT RETURNS MODELS TO ANOTHER UNIT. Every earlier one puts a model back
    into the unit that has the ability; this one reaches across to a friendly
    CANOPTEK SCARAB SWARM unit within 6". So the placement is anchored on the
    RECIPIENT's survivors, not the bearer's.
  * "SELECT ONE" IS A CHOICE when more than one Scarab unit is in range, and
    the options are TAGGED with their squads so it can be answered on the
    BOARD rather than from a list of names.

MODELS COME BACK ON FULL WOUNDS, which is set_up_model()'s default and the
right one here: unlike Reanimation Protocols (02.02.04, one wound) and the
Eternal Revenant (half), this ability's text says only "returned" - so the
model is set up as the datasheet prints it.

THE STARTING STRENGTH CAP STILL APPLIES: a unit can never hold more models than
it started with, which is what makes "one per Spyder" an upper bound rather
than a promise. Honoured by returning only as many as there are destroyed
models to bring back.
"""

from game import ai_mode, model_return
from game.formation_layout import returning_positions
from game.squad import edge_distance

CANOPTEK_SWARM_LABEL = "Canoptek Swarm"

#: "within 6" of this unit".
CANOPTEK_SWARM_RANGE_IN = 6.0


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def spyder_models(squad):
    """"for each SPYDER model in this unit" - counted per MODEL, so a
    two-Spyder unit returns two."""
    return [m for m in _living(squad) if getattr(m.profile, "canoptek_swarm", False)]


def unit_has_ability(squad):
    return bool(spyder_models(squad))


def is_scarab_swarm_unit(squad):
    """"one friendly CANOPTEK SCARAB SWARM unit". Read off the datasheet
    ability rather than a keyword string, because Chittering Swarm is printed
    on exactly that datasheet and nothing else."""
    return squad is not None and any(
        getattr(m.profile, "chittering_swarm", False) for m in _living(squad))


class CanoptekSwarmController:
    """Offered at the start of the owner's Command phase, once per Spyder
    unit."""

    def __init__(self, decision_manager=None, game_state=None, game_log=None,
                 auto_players=(), placer=None, position_valid=None):
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        #: A ReturnPlacementController - see the module docstring for why.
        self.placer = placer
        self.position_valid = position_valid
        self._offered = set()

    def _tokens(self):
        return getattr(self.game_state, "tokens", None) or []

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _squads(self, owner=None):
        seen = {}
        for token in self._tokens():
            squad = getattr(token, "squad", None)
            if squad is None:
                continue
            if owner is not None and squad.owner != owner:
                continue
            seen[id(squad)] = squad
        return list(seen.values())

    def candidates(self, spyders):
        """Friendly CANOPTEK SCARAB SWARM units within 6" that actually have
        something to bring back.

        THE "SOMETHING TO BRING BACK" HALF IS NOT DECORATION: offering a
        return to a unit at full strength is offering what buys nothing, and
        this engine refuses that on principle."""
        mine = _living(spyders)
        out = []
        for squad in self._squads(getattr(spyders, "owner", None)):
            if squad is spyders or not is_scarab_swarm_unit(squad):
                continue
            if not getattr(squad, "destroyed_models", None):
                continue
            others = _living(squad)
            if not others:
                continue
            if any(edge_distance(a, b) <= CANOPTEK_SWARM_RANGE_IN
                   for a in mine for b in others):
                out.append(squad)
        return sorted(out, key=lambda s: s.name)

    def offer_at_command_phase(self, player):
        raised = False
        for spyders in self._squads(player):
            if not unit_has_ability(spyders) or id(spyders) in self._offered:
                continue
            targets = self.candidates(spyders)
            if not targets:
                continue
            self._offered.add(id(spyders))
            if len(targets) == 1 or player in self.auto_players \
                    or self.decision_manager is None:
                self.use(spyders, targets[0])
                continue
            options = [("%s: %s" % (CANOPTEK_SWARM_LABEL, t.name),
                        (lambda target=t, s=spyders: self.use(s, target)), t)
                       for t in targets]
            self.decision_manager.request(
                player,
                "%s: return scarabs to which unit?" % CANOPTEK_SWARM_LABEL,
                options)
            raised = True
        return raised

    def use(self, spyders, target):
        """Return one model per Spyder, capped by what is actually dead."""
        if target is None or not unit_has_ability(spyders):
            return 0
        dead = list(getattr(target, "destroyed_models", ()) or ())
        if not dead:
            return 0
        wanted = min(len(spyder_models(spyders)), len(dead))
        coming = dead[:wanted]
        spots = returning_positions(target, coming,
                                    position_valid=self._valid_for(target))
        if self.placer is not None:
            returned = self.placer.place(target, coming, spots)
        else:
            returned = 0
            for model, spot in zip(coming, spots):
                if spot is None:
                    continue
                model_return.set_up_model(model, spot, game_state=self.game_state)
                returned += 1
        if returned:
            self._log("%s: %s returns %d model(s) to %s."
                      % (CANOPTEK_SWARM_LABEL, spyders.name, returned, target.name))
        return returned

    def _valid_for(self, _squad):
        """main.py passes the same three-argument predicate the army rule uses
        (it reads the squad off the model), so this just forwards it."""
        return self.position_valid

    def reset_phase(self):
        self._offered.clear()
