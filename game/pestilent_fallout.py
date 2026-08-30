"""The Malignant Plaguecaster's own ability "Pestilent Fallout".

RULE (printed, word for word):

  "In your Shooting phase, after this model has shot, select one enemy INFANTRY
  unit hit by one or more of this model's Plague Wind attacks. Until the end of
  your opponent's next turn, that unit is enfeebled. While a unit is enfeebled,
  subtract 2" from the Move characteristic of models in that unit."

THE EIGHTH CONSUMER of ShootingController.on_squad_finished_shooting, and the
fourth whose effect is a mark on the TARGET. Modelled on Target Acquisition and
Crystalline Targeting, with two differences that are both printed:

  * IT NAMES A WEAPON ("this model's Plague Wind attacks"), so unlike Barrage
    of Filth it is not enough that the unit was hit by anything - it has to
    have been hit by the Plague Wind. The controller is therefore told which
    weapon did the hitting.
  * IT NAMES A KEYWORD (enemy INFANTRY), so a vehicle hit by the same shot is
    not a candidate.

THE LIFETIME IS THE LONGEST IN THIS FACTION: "until the end of your OPPONENT'S
next turn" is nearly two full turns, and it is neither a phase nor a turn
boundary that this engine already clears things on. It is therefore stored as
the turn number it expires after and checked against the tracker, rather than
cleared by a reset hook - the same treatment a "until the start of your next
turn" mark gets in game/nurgles_gift.py, one turn further out.

The -2" lands in game/coldstar.py's effective_movement_in(), the one place this
engine asks how far a model actually moves - so it composes with the Death
Guard Plague Scabrous Soulrot (-1") without either knowing about the other.
"""

ENFEEBLED_MOVE_PENALTY_IN = 2.0
PLAGUE_WIND_NAMES = ("Plague Wind - witchfire", "Plague Wind - focused witchfire")


class PestilentFalloutController:
    """Fed from ShootingController.on_squad_finished_shooting."""

    def __init__(self, turn_tracker=None, game_log=None, auto_players=(),
                 target_pick=None):
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self.target_pick = target_pick
        # id(squad) -> the player whose turn must END before it wears off.
        self._enfeebled = {}

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    @staticmethod
    def has_ability(squad):
        return any(getattr(m.profile, "pestilent_fallout", False) and not m.is_dead()
                   for m in getattr(squad, "models", ()) or ())

    @staticmethod
    def _is_infantry(squad):
        return any(getattr(m.profile, "infantry", False) and not m.is_dead()
                   for m in getattr(squad, "models", ()) or ())

    def is_enfeebled(self, squad):
        return squad is not None and id(squad) in self._enfeebled

    def on_squad_finished_shooting(self, shooter_squad, target_squads=(), weapon_names=()):
        """`weapon_names` is what the shooter actually fired. The Plague Wind
        clause is checked here rather than by the caller so the whole condition
        lives in one place."""
        if not self.has_ability(shooter_squad):
            return False
        if not any(name in PLAGUE_WIND_NAMES for name in weapon_names or ()):
            return False
        candidates = [s for s in target_squads or ()
                      if s is not None and s.owner != shooter_squad.owner
                      and self._is_infantry(s)]
        if not candidates:
            return False
        if len(candidates) == 1 or shooter_squad.owner in self.auto_players:
            return self._use(shooter_squad, self._pick(shooter_squad, candidates))
        return self._use(shooter_squad, self._pick(shooter_squad, candidates))

    def _pick(self, squad, candidates):
        if self.target_pick is not None:
            chosen = self.target_pick(squad, candidates)
            if chosen is not None:
                return chosen
        return sorted(candidates, key=lambda s: s.name)[0]

    def _use(self, shooter_squad, target):
        if target is None:
            return False
        self._enfeebled[id(target)] = target.owner
        self._log(f"Pestilent Fallout ({shooter_squad.name}): {target.name} is enfeebled "
                  f"(-{ENFEEBLED_MOVE_PENALTY_IN:g}\" Move) until the end of its owner's next turn.")
        return True

    def expire_for_turn(self, ending_player):
        """"Until the end of your opponent's next turn" - so a mark placed in
        the Plaguecaster's turn survives the victim's whole following turn and
        clears when it ends. Returns what was cleared, for tests."""
        cleared = [key for key, owner in self._enfeebled.items() if owner == ending_player]
        for key in cleared:
            del self._enfeebled[key]
        return cleared
