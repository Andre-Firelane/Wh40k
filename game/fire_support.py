"""The Falcon's "Fire Support" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "In your Shooting phase, after this model has shot, select one enemy unit hit
  by one or more of those attacks. Until the end of the turn, each time a
  friendly model that disembarked from this TRANSPORT this turn makes an attack
  that targets that enemy unit, you can re-roll the Wound roll."

THREE PIECES, AND ONLY THE MIDDLE ONE IS NEW
--------------------------------------------
  * The TRIGGER already exists. ShootingController.on_squad_finished_shooting
    fires with the enemy squads this activation actually HIT - built for
    Suppression Volley, reused since by Battle Focus's Fade Back, and it is
    word for word this ability's "after this model has shot, select one enemy
    unit hit by one or more of those attacks".
  * The MARK is new: which enemy unit was picked, and it lasts until the end of
    the turn rather than the phase. Kept on this controller rather than as a
    Squad flag because it is a PAIR (this Falcon, that target) - two Falcons
    can each have marked a different unit, and a passenger only benefits from
    the one it actually rode in.
  * The EFFECT joins game/shooting.py's _wound_reroll_reason()/
    _wound_reroll_is_full(), alongside [TWIN-LINKED], Breach and Clear,
    Sunforge and Assured Destruction. "You can re-roll the Wound roll" with no
    "failed" is the same wording that settled all of those as WHOLE-roll
    re-rolls.

"THAT DISEMBARKED FROM THIS TRANSPORT THIS TURN"
------------------------------------------------
Needed a fact the engine did not record: TransportController knew which
transport the squad being placed right now came out of, but nothing survived
the placement. Squad.disembarked_from_this_turn now holds that token, set in
confirm_disembark() and cleared at end of turn with the other turn-scoped
flags - one field, one write, one clear.

Note the ability does NOT require the passenger to have ridden in the Falcon
when it shot, only to have disembarked from it this turn - so the ordinary
sequence (disembark, then the Falcon shoots, then the passengers shoot) is
exactly the case it is written for.

OFFERED, NOT AUTOMATIC. With one unit hit there is nothing to choose and the
mark is simply taken - it costs nothing and there is no reason to decline, the
same reasoning that makes Puretide's Teachings automatic. With several, the
player picks, because which one matters and only they know what their
passengers intend to shoot at.
"""

FIRE_SUPPORT_LABEL = "Fire Support"


class FireSupportController:
    """The mark, and the offer that sets it.

    Human-only in practice, like the rest of the Aeldari work, but it is an
    ordinary DecisionManager break point and so an AI would resolve it through
    the generic path without anything extra here."""

    def __init__(self, decision_manager=None, game_log=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self._marks = {}  # id(transport token) -> marked enemy Squad

    def _log(self, message, **kwargs):
        if self.game_log is not None:
            self.game_log.add(message, **kwargs)

    def reset_turn(self):
        """"Until the end of the turn". Called from main.py's end-of-turn
        block, next to the other turn-scoped flags."""
        self._marks.clear()

    def marked_by(self, transport_token):
        return self._marks.get(id(transport_token))

    def _carriers(self, squad):
        """Every Falcon this unit disembarked from this turn that also has a
        mark. A list rather than a single value only for symmetry with the
        possibility of several - a unit disembarks from one transport, so it
        holds at most one entry."""
        token = getattr(squad, "disembarked_from_this_turn", None)
        if token is None:
            return []
        return [token] if id(token) in self._marks else []

    def applies(self, attacking_squad, target_squad):
        """Whether this attack is one the ability covers: the attacking unit
        disembarked from a Falcon that has marked exactly this target."""
        if attacking_squad is None or target_squad is None:
            return False
        return any(self._marks.get(id(t)) is target_squad for t in self._carriers(attacking_squad))

    def offer_after_shooting(self, squad, hit_squads):
        """Wired into ShootingController.on_squad_finished_shooting.

        `squad` is the unit that just shot and `hit_squads` the enemy units at
        least one of its attacks hit - exactly the printed selection pool, so
        nothing here re-derives who was hit."""
        transport = self._bearer(squad)
        if transport is None:
            return
        candidates = sorted((s for s in hit_squads if s is not None), key=lambda s: s.name)
        if not candidates:
            return
        if len(candidates) == 1:
            self._mark(transport, candidates[0])
            return
        if self.decision_manager is None:
            self._mark(transport, candidates[0])
            return
        options = [
            (target.name, (lambda t=target: self._mark(transport, t)), target)
            for target in candidates
        ]
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: Fire Support - which unit it hit should its passengers "
            "re-roll Wound rolls against for the rest of the turn?",
            options,
        )

    def _bearer(self, squad):
        """The single model with the ability, if this unit is one. Fire Support
        is written for a one-model TRANSPORT ("after THIS MODEL has shot"), so
        a unit that somehow held two would mark once per model - which is why
        the mark is keyed on the token, not the squad."""
        if squad is None:
            return None
        for model in squad.models:
            if getattr(model.profile, "fire_support", False) and not model.is_dead():
                return model
        return None

    def _mark(self, transport, target):
        self._marks[id(transport)] = target
        self._log(
            f"Fire Support: units that disembarked from {transport.profile.name} this turn "
            f"can re-roll Wound rolls against {target.name} until the end of the turn."
        )
