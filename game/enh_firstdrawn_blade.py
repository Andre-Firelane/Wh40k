"""Windrider Host Enhancement: Firstdrawn Blade (10 pts).

RULE (verbatim, rules/aeldari/detachments/Windrider Host.md):
  "ASURYANI MOUNTED model only. Models in the bearer's unit have the Scouts 9"
  ability."

THE SAME TIMING TRAP AS ITS T'AU COUSIN, AND THE SAME ANSWER. Rule 24.31's
Scout move is resolved in game/scouts.py's ScoutsStep; a unit granted Scouts
AFTER that step has already been passed over and carries an ability it can
never use. The grant would be perfect in a unit test and inert in a game.

game/enh_strike_swiftly.py met this first and is why PregameController has an
ORDERED `prebattle_steps` list rather than a single scouts hook. This one
registers ahead of ScoutsStep for exactly the same reason - second instance of
one ordering question, and the list is what makes the order visible instead of
implicit in which attribute happened to be assigned first.

SIMPLER THAN STRIKE SWIFTLY IN EVERY OTHER WAY, and each difference is printed:

  * NO SELECTION. Strike Swiftly picks "up to two friendly units within 6"";
    this one just says "models in the BEARER'S UNIT". Nothing is asked, so
    there is no prompt and no AI path to worry about.
  * 9", NOT 6". A Scouts range is a distance the unit actually moves, so the
    number is the ability.
  * NO "that do not already have Scouts" CLAUSE. Strike Swiftly prints one;
    this does not. Granting it to a unit that already has Scouts is therefore
    legal here, and game/scouts.py takes the BETTER of the two ranges rather
    than overwriting - so a Ranger squad keeps its own if that is further.
"""
from game import enhancements

FIRSTDRAWN_BLADE = "Firstdrawn Blade"

FIRSTDRAWN_BLADE_LABEL = "Firstdrawn Blade"

#: 'the Scouts 9" ability'.
FIRSTDRAWN_BLADE_SCOUTS_IN = 9.0


def applies(squad):
    """Whether this unit's models have the granted Scouts."""
    return enhancements.is_active(squad, FIRSTDRAWN_BLADE)


def grant_scouts(squad, game_log=None):
    """"Models in the bearer's unit have the Scouts 9" ability".

    Written onto model.profile.scouts, the same field game/scouts.py reads and
    the same way game/enh_strike_swiftly.py's grant does - so the Scout move
    step needs no knowledge of where the ability came from.

    NEVER A DOWNGRADE. A model that already prints a LONGER Scouts range keeps
    it: this card has no "that do not have the Scouts ability" clause (its T'au
    cousin does), so it can legally land on a unit that already scouts, and
    shortening that unit's move would be a 10-point penalty."""
    if squad is None:
        return False
    for model in squad.models:
        printed = getattr(model.profile, "scouts", None) or 0.0
        model.profile.scouts = max(printed, FIRSTDRAWN_BLADE_SCOUTS_IN)
    if game_log is not None:
        game_log.add('%s: %s has Scouts %g" (rule 24.31) from the %s Enhancement.'
                     % (squad.owner, squad.name, FIRSTDRAWN_BLADE_SCOUTS_IN,
                        FIRSTDRAWN_BLADE))
    return True


class FirstdrawnBladeStep:
    """One of PregameController's pre-battle steps, registered BEFORE
    game/scouts.py's - see the module docstring.

    Nothing is asked: the card names the bearer's own unit, so this resolves
    itself and returns immediately."""

    def __init__(self, game_state=None, game_log=None):
        self.game_state = game_state
        self.game_log = game_log

    def _squads(self):
        seen, out = set(), []
        for token in getattr(self.game_state, "tokens", ()) or ():
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen.add(id(squad))
                out.append(squad)
        return out

    def start(self, pregame, on_finished=None):
        """PregameController's step protocol: return True to keep the queue
        waiting (a step that asks something), False to let it carry straight
        on. Nothing is asked here, so this always resolves inline."""
        for squad in self._squads():
            if applies(squad):
                grant_scouts(squad, game_log=self.game_log)
        return False
