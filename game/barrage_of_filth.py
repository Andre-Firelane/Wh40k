"""The Defiler's own ability "Barrage of Filth".

RULE (printed, word for word):

  "In your Shooting phase, after this model has shot, select one enemy unit hit
  by one or more of those attacks. Until the end of the phase, that unit cannot
  have the benefit of Cover."

THE SEVENTH CONSUMER of ShootingController.on_squad_finished_shooting, and the
third whose effect is a MARK ON THE TARGET rather than a grant on the shooter -
Target Acquisition and Crystalline Targeting are the other two, and this is
modelled on them.

IT REMOVES COVER RATHER THAN GRANTING IT, which makes it the mirror of the two
cover-granting abilities this faction already has (the Daemon Prince's Miasma
of Pestilence and the Plague Marines' Skullsquirm Blight victims). All three
meet in game/shooting.py's _compute_benefit_of_cover(), and the ORDER matters:
this one is checked LAST and overrides, because "cannot have the benefit of
Cover" is an absolute statement while the others are grants.

"SELECT ONE ENEMY UNIT HIT BY ONE OR MORE OF THOSE ATTACKS" - so the candidates
are the units this Defiler actually hit, which the controller reports. Not
optional: the text says "select", not "you can", so the only decision is WHICH
unit, and with a single candidate there is nothing to ask. The AI answers it
with the shared damage-value ranking, the same measure every other
deterministic target choice in this engine uses, so it costs no API call.

"UNTIL THE END OF THE PHASE" - cleared at every phase boundary, not at the end
of the turn. One clock, and it is the shorter one.
"""

from game import ai_mode


class BarrageOfFilthController:
    """Fed from ShootingController.on_squad_finished_shooting."""

    def __init__(self, decision_manager=None, game_log=None, auto_players=(),
                 target_pick=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        # target_pick(attacker, candidates) -> squad. main.py passes the shared
        # damage-value ranking; None falls back to name order, which keeps a
        # headless test reproducible.
        self.target_pick = target_pick
        self._stripped = set()   # id(squad) that cannot have cover this phase

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    @staticmethod
    def has_ability(squad):
        return any(getattr(m.profile, "barrage_of_filth", False) and not m.is_dead()
                   for m in getattr(squad, "models", ()) or ())

    def denies_cover(self, squad):
        """Read by game/shooting.py's _compute_benefit_of_cover()."""
        return squad is not None and id(squad) in self._stripped

    def on_squad_finished_shooting(self, shooter_squad, target_squads=()):
        """`target_squads` is what the shooter actually hit, as the controller
        reports it. A Defiler that hit nothing simply finds no candidate - no
        separate "did it hit" test is needed or wanted."""
        if not self.has_ability(shooter_squad):
            return False
        candidates = [s for s in target_squads or ()
                      if s is not None and s.owner != shooter_squad.owner]
        if not candidates:
            return False
        if len(candidates) == 1 or shooter_squad.owner in self.auto_players \
                or self.decision_manager is None:
            return self._use(shooter_squad, self._pick(shooter_squad, candidates))
        options = [(f"Barrage of Filth: {t.name}",
                    (lambda target=t: self._use(shooter_squad, target)), t)
                   for t in candidates]
        self.decision_manager.request(
            shooter_squad.owner,
            f"{shooter_squad.name}: Barrage of Filth - strip cover from which unit?",
            options)
        return True

    def _pick(self, squad, candidates):
        if self.target_pick is not None:
            chosen = self.target_pick(squad, candidates)
            if chosen is not None:
                return chosen
        return sorted(candidates, key=lambda s: s.name)[0]

    def _use(self, shooter_squad, target):
        if target is None:
            return False
        self._stripped.add(id(target))
        self._log(f"Barrage of Filth ({shooter_squad.name}): {target.name} cannot have "
                  f"the benefit of Cover until the end of the phase.")
        return True

    def reset_phase(self):
        """"Until the end of the phase"."""
        self._stripped.clear()
