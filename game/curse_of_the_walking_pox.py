"""The Poxwalkers' own ability "Curse of the Walking Pox".

RULE (printed, word for word):

  "Each time a POXWALKER model in this unit makes an attack that destroys an
  enemy model (excluding MONSTER and VEHICLE models), after this unit has
  resolved its attacks, you can return one destroyed POXWALKER model to this
  unit. While TYPHUS is leading this unit, enemy models destroyed as a result
  of TYPHUS' Eater Plague ability count as enemy models destroyed by an attack
  made by a POXWALKER model in this unit for the purposes of this ability."

THE THIRD ABILITY IN THIS ENGINE THAT RETURNS A MODEL, after Painboy's Grot
Orderly and Fuegan's Unquenchable Resolve - so game/model_return.py's
set_up_model() does the four-part "back on the board" sequence and this module
only decides WHEN and HOW MANY.

ONE PER DESTROYED ENEMY MODEL, resolved in a batch. "Each time ... you can
return one" means a Poxwalker mob that killed four models gets four back, not
one - so the count is tallied during the unit's attacks and spent afterwards.
Bounded twice: by Squad.starting_model_count (rule 01.02.03's cap, which this
engine already applies to Reanimation Protocols) and by how many Poxwalkers
have actually died.

THE TYPHUS CLAUSE IS NOT DECORATION. Eater Plague inflicts MORTAL WOUNDS, which
are not "an attack made by a POXWALKER model" by any normal reading - the
clause exists precisely to overrule that, and without it the ability and the
psychic power would not interact at all. It is therefore a real, separate feed
(notify_eater_plague_kills()) rather than something that falls out of the
ordinary one, and it is gated on Typhus actually LEADING the unit.

PLACEMENT is Grot Orderly's, not Fuegan's: the returning model joins a unit
that is still standing, so it goes back in coherency with its squadmates
(formation_layout's ring around the unit) rather than "as close as possible to
where it fell". game/model_return.py's own Engagement Range test still applies -
SetupController.position_valid() does not cover it, and this ability fires in
the Fight phase when enemies are by definition close.
"""
from game import model_return
from game.attached_units import leader_ability
from game.formation_layout import returning_positions

MONSTER_OR_VEHICLE_EXCLUDED = True  # documented for the test that pins it


def has_ability(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "curse_of_the_walking_pox", False) and not m.is_dead()
               for m in getattr(squad, "models", ()) or ())


def _is_poxwalker(model):
    return bool(getattr(model.profile, "curse_of_the_walking_pox", False))


def counts_as_kill(dead_model):
    """"an enemy model (excluding MONSTER and VEHICLE models)"."""
    profile = getattr(dead_model, "profile", None)
    if profile is None:
        return False
    return not (getattr(profile, "monster", False) or getattr(profile, "vehicle", False))


def returnable_models(squad):
    """Destroyed Poxwalkers eligible to come back, respecting rule 01.02.03's
    starting-strength cap - the same bound Reanimation Protocols applies."""
    if squad is None:
        return []
    living = sum(1 for m in squad.models if not m.is_dead())
    headroom = max(0, getattr(squad, "starting_model_count", living) - living)
    dead = [m for m in getattr(squad, "destroyed_models", ()) or () if _is_poxwalker(m)]
    return dead[:headroom]


class CurseOfTheWalkingPoxController:
    """Tallies kills during the unit's attacks, spends them afterwards."""

    def __init__(self, game_log=None, game_state=None, position_valid=None):
        self.game_log = game_log
        self.game_state = game_state
        self.position_valid = position_valid
        self._credit = {}   # id(poxwalker squad) -> kills owed

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    def notify_kills(self, attacking_squad, destroyed_models):
        """Called from main.py's death sweep with whoever was attacking. Only
        counts models a POXWALKER could have killed."""
        if not has_ability(attacking_squad):
            return 0
        gained = sum(1 for m in destroyed_models or () if counts_as_kill(m))
        if gained:
            key = id(attacking_squad)
            self._credit[key] = self._credit.get(key, 0) + gained
        return gained

    def notify_eater_plague_kills(self, poxwalker_squad, destroyed_models):
        """The printed TYPHUS clause. A separate entry point because mortal
        wounds are not "an attack made by a POXWALKER model" - the clause
        exists to overrule that, so the code has to say so too."""
        if not has_ability(poxwalker_squad):
            return 0
        if not leader_ability(poxwalker_squad, "eater_plague"):
            return 0    # "While TYPHUS is leading this unit"
        return self.notify_kills(poxwalker_squad, destroyed_models)

    def credit_for(self, squad):
        return self._credit.get(id(squad), 0)

    def resolve_after_attacks(self, squad):
        """"after this unit has resolved its attacks". Returns the models that
        really came back."""
        owed = self._credit.pop(id(squad), 0)
        if owed <= 0:
            return []
        candidates = returnable_models(squad)[:owed]
        if not candidates:
            return []
        # Grot Orderly's placement, not Fuegan's: these models rejoin a unit
        # that is still standing, so returning_positions() seats them touching
        # the survivors and rule 09.02's coherency holds by construction. A
        # model that finds nowhere legal is simply not returned - "you CAN
        # return one" - which is the same call grot_orderly.py makes.
        spots = returning_positions(squad, candidates, position_valid=self._valid_for)
        returned = []
        for model, spot in zip(candidates, spots):
            if spot is None:
                continue
            model_return.set_up_model(model, spot, game_state=self.game_state)
            returned.append(model)
        if returned:
            self._log(f"Curse of the Walking Pox ({squad.name}): {len(returned)} "
                      f"Poxwalker(s) shamble back into the unit.")
        return returned

    def _valid_for(self, model, x_in, y_in):
        """SetupController's own predicate, plus the Engagement Range test it
        expressly does NOT cover (see its docstring) - this ability fires in
        the Fight phase, so enemies are by definition close and omitting that
        test would set a Poxwalker back up already in combat."""
        if self.position_valid is not None and not self.position_valid(model, x_in, y_in):
            return False
        return model_return.clear_of_engagement(
            model, x_in, y_in, model_return.enemy_tokens(model, self._tokens()))

    def reset_phase(self):
        self._credit.clear()
