""""After this model has shot, one enemy unit it HIT cannot have the benefit of
Cover until the end of the phase" - the shared head of the Defiler's Barrage of
Filth and the Triarch Stalker's Targeting Relay.

THE 41st EXTRACTION, at the SECOND consumer, which is where this repo's
standing rule puts it. The two printed texts are the same sentence with two
names on it:

  Barrage of Filth (Defiler, Death Guard)
    "In your Shooting phase, after this model has shot, select one enemy unit
     hit by one or more of those attacks. Until the end of the phase, that
     unit cannot have the benefit of Cover."

  Targeting Relay (Triarch Stalker, Necrons)
    "In your Shooting phase, each time this model is selected to shoot, after
     resolving its attacks, select one enemy unit that was hit by one or more
     of those attacks. Until the end of the phase, that unit cannot have the
     Benefit of Cover."

The two openings differ in wording and not in meaning: a shooting activation
is exactly "this model is selected to shoot ... after resolving its attacks",
and ShootingController.on_squad_finished_shooting fires once per activation, so
both land on the same seam with the same argument.

WHAT IS SHARED IS THE PART THAT IS SUBTLY WRONG TWICE.

  * The candidates are the units the shooter actually HIT, which the
    controller reports - not "every unit it targeted". A shooter that hit
    nothing simply finds no candidate; there is no separate "did it hit" test
    to forget.
  * It is NOT optional. Both texts say "select", not "you can", so the only
    decision is WHICH unit, and with a single candidate there is nothing to
    ask at all.
  * The mark lives for a PHASE, not a turn. One clock, and it is the shorter
    one.
  * A friendly unit can never be a candidate even if the attack somehow
    reported one, because "enemy unit" is in the printed text.

WHAT A SUBCLASS OWNS is two class attributes - the profile flag its datasheet
sets, and the printed ability NAME that goes in the prompt and the log. As
class attributes rather than constructor arguments, so a subclass that forgets
one fails loudly at definition rather than silently offering an unnamed choice.

IT REMOVES COVER RATHER THAN GRANTING IT, which is why game/shooting.py's
_compute_benefit_of_cover() asks this FIRST and returns False: "cannot have the
benefit of Cover" is an absolute statement, while STEALTH, Miasma of Pestilence
and the Rune of Mists are grants. It has to beat them rather than join them.

denied() below is the one reader for that gate. It takes the SOURCES as an
argument instead of holding a registry, because ShootingController already owns
its collaborators; a third source is one more name at that call site, which is
visible in a diff, rather than an import that nothing shows.
"""

from game import ai_mode


def denied(squad, sources=()):
    """Does ANY of these sources currently deny `squad` the benefit of Cover?

    Read by game/shooting.py's _compute_benefit_of_cover(). `sources` may
    contain None - the controllers are optional collaborators there, exactly
    like greater_good and suppression beside them."""
    if squad is None:
        return False
    return any(s is not None and s.denies_cover(squad) for s in sources or ())


class CoverDenialAfterShooting:
    """Fed from ShootingController.on_squad_finished_shooting."""

    #: The UnitProfile attribute this ability's datasheet sets.
    flag = None
    #: The printed ability name, as it appears in the prompt and the log.
    label = None

    def __init__(self, decision_manager=None, game_log=None, auto_players=(),
                 target_pick=None):
        assert self.flag and self.label, (
            "a %s subclass must set both `flag` and `label`" % type(self).__name__)
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

    @classmethod
    def has_ability(cls, squad):
        return any(getattr(m.profile, cls.flag, False) and not m.is_dead()
                   for m in getattr(squad, "models", ()) or ())

    def denies_cover(self, squad):
        """Read by game/shooting.py's _compute_benefit_of_cover(), through
        denied() above."""
        return squad is not None and id(squad) in self._stripped

    def on_squad_finished_shooting(self, shooter_squad, target_squads=()):
        """`target_squads` is what the shooter actually hit, as the controller
        reports it."""
        if not self.has_ability(shooter_squad):
            return False
        candidates = [s for s in target_squads or ()
                      if s is not None and s.owner != shooter_squad.owner]
        if not candidates:
            return False
        if len(candidates) == 1 or shooter_squad.owner in self.auto_players \
                or self.decision_manager is None:
            return self._use(shooter_squad, self._pick(shooter_squad, candidates))
        options = [("%s: %s" % (self.label, t.name),
                    (lambda target=t: self._use(shooter_squad, target)), t)
                   for t in candidates]
        self.decision_manager.request(
            shooter_squad.owner,
            "%s: %s - strip cover from which unit?" % (shooter_squad.name, self.label),
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
        self._log("%s (%s): %s cannot have the benefit of Cover until the end of "
                  "the phase." % (self.label, shooter_squad.name, target.name))
        return True

    def reset_phase(self):
        """"Until the end of the phase"."""
        self._stripped.clear()
