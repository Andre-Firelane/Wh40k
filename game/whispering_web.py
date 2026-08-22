"""Lhykhis' "Whispering Web" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "In your Shooting phase, after this model has shot, select one enemy unit hit
  by one or more of those attacks. Until the end of the turn, each time a
  friendly Aeldari model makes an attack that targets that unit, an unmodified
  Hit roll of 5+ scores a Critical Hit."

THREE PIECES, AND EACH ONE ALREADY HAD A HOME
---------------------------------------------
  * The TRIGGER exists. ShootingController.on_squad_finished_shooting fires
    with the enemy squads this activation actually HIT - built for Suppression
    Volley, since reused by Battle Focus's Fade Back and the Falcon's Fire
    Support - and it is word for word this ability's "after this model has
    shot, select one enemy unit hit by one or more of those attacks". Fourth
    consumer of the same list.
  * The MARK is this module's own, and it is shaped like the Falcon's Fire
    Support rather than like Guide/Doom: same trigger, same "until the end of
    the turn" life. It differs from Fire Support in SCOPE - Fire Support only
    benefits models that disembarked from that one transport, this benefits
    every friendly AELDARI model, so the mark is held per PLAYER (like
    game/psychic_mark.py's) rather than per source token.
  * The EFFECT is a crit threshold, and that is game/crit_hit.py - which had to
    be renamed out of game/melee_crit.py to accept it, because this is the
    first source of a lowered crit threshold that is not melee-only.

WHY IT IS NOT game/psychic_mark.py. That module shares Guide and Doom, which
agree on trigger (end of Movement phase), selection (within 18" and visible)
and duration (until the start of your next Command phase). This ability agrees
with neither the trigger nor the duration, and its selection pool is "whatever
you just hit" rather than a range-and-visibility sweep. What it does share is
the army-wide AELDARI read, which is four lines - not worth coupling two
different triggers to reuse.

"FRIENDLY AELDARI MODEL" is asked of the SQUAD, using the same faction test
game/psychic_guidance.py and game/psychic_mark.py use: rule 19.01 only merges
same-faction units, so no attached unit's models can disagree, and the hit steps
have the attacking squad to hand anyway.

HER OWN GUN NEVER BENEFITS, and that is not an oversight: Brood Twain is
[TORRENT] (24.37), so it makes no hit roll at all. The ability is army-wide, so
it is written for everyone else's attacks - which is also why the mark cannot
live on her own squad.
"""

from game import psychic_guidance

WHISPERING_WEB_LABEL = "Whispering Web"


class WhisperingWebController:
    """The mark, and the offer that sets it.

    Human-only in practice like the rest of the Aeldari work, but the selection
    is an ordinary DecisionManager break point, so an AI would resolve it
    through the generic path with nothing extra here."""

    def __init__(self, decision_manager=None, game_log=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self._marks = {}   # player -> set of marked enemy Squads

    def _log(self, message, **kwargs):
        if self.game_log is not None:
            self.game_log.add(message, **kwargs)

    def reset_turn(self):
        """"Until the end of the turn". Called from main.py's end-of-turn
        block, next to the other turn-scoped flags."""
        self._marks.clear()

    def marked_by(self, player):
        return set(self._marks.get(player, ()))

    def applies(self, attacking_squad, target_squad):
        """Whether attacks by this squad against that unit crit on a 5+: a
        friendly AELDARI unit attacking one its owner has marked."""
        if attacking_squad is None or target_squad is None:
            return False
        if not psychic_guidance._is_aeldari(attacking_squad):
            return False
        return target_squad in self._marks.get(attacking_squad.owner, ())

    def _bearer(self, squad):
        """The living model with the ability, if this unit has one. Written for
        a one-model EPIC HERO ("after THIS MODEL has shot"), but she attaches to
        Warp Spiders, so the unit that shot is usually much bigger than her."""
        for model in getattr(squad, "models", None) or ():
            if getattr(model.profile, "whispering_web", False) and not model.is_dead():
                return model
        return None

    def offer_after_shooting(self, squad, hit_squads):
        """Wired into ShootingController.on_squad_finished_shooting.

        `squad` is the unit that just shot and `hit_squads` the enemy units at
        least one of its attacks hit - exactly the printed selection pool, so
        nothing here re-derives who was hit.

        Taken without asking when only one unit was hit: there is nothing to
        choose and no reason to decline, the same reasoning that makes
        Puretide's Teachings automatic."""
        if self._bearer(squad) is None:
            return
        candidates = sorted((s for s in hit_squads if s is not None), key=lambda s: s.name)
        if not candidates:
            return
        if len(candidates) == 1 or self.decision_manager is None:
            self.mark(squad.owner, candidates[0])
            return
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: Whispering Web - which unit it hit should friendly AELDARI "
            "models score Critical Hits against on an unmodified 5+ for the rest of the turn?",
            [(target.name, (lambda t=target: self.mark(squad.owner, t))) for target in candidates],
        )

    def mark(self, player, target):
        self._marks.setdefault(player, set()).add(target)
        self._log(
            f"Whispering Web: friendly AELDARI models score a Critical Hit on an unmodified "
            f"5+ against {target.name} until the end of the turn."
        )
