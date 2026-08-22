"""The Damage-roll re-roll offer, as a DamageAllocationSession collaborator.

Extracted from game/sunforge.py, which owned it while Crisis Sunforge
Battlesuits were the only ability granting one. Fire Dragons' Assured
Destruction is the second, and a module named after one datasheet is the wrong
home for another datasheet's rule - the same move already made for
game/invulnerable_save.py and game/crit_hit.py, and for the same two
reasons: a second foreign consumer, and exactly one call site to update.

Nothing about the offer was ever Sunforge-specific except the label in its
prompt, so `label` is now a parameter and the class itself says nothing about
which ability opened it - matching DamageAllocationSession, which likewise
knows nothing about that.
"""


class DamageRerollOffer:
    """maybe_offer/on_resolved, the same contract StealthDronesController
    already satisfies inside DamageAllocationSession.

    Built per weapon group by game/shooting.py, and only when the granting
    ability already applies - so this object's mere existence means "a
    re-roll is on offer for this group". It does not re-check the target."""

    def __init__(self, label, decision_manager=None, dice_manager=None, game_log=None,
                 owner=None, weapon_name="", prompt_suffix=""):
        self.label = label          # the ability's own name, for the prompt and the log
        self.decision_manager = decision_manager
        self.dice_manager = dice_manager
        self.game_log = game_log
        self.owner = owner          # the ATTACKING player - "you can re-roll" is the attacker's choice
        self.weapon_name = weapon_name
        self.prompt_suffix = prompt_suffix  # e.g. "against this MONSTER/VEHICLE target"

    def can_offer(self):
        """Whether this Damage die still has its one re-roll left.

        Checked against DiceManager.already_rerolled, NOT can_reroll_all():
        by the time this runs the roll has been acknowledged, and
        acknowledge() clears pending_values - so can_reroll_all() would be
        False for every Damage roll in a real game and the ability would
        silently never fire. already_rerolled deliberately survives
        acknowledge() for exactly this reason (see its own note in
        game/dice.py); it is the same thing shooting.py's
        _rerollable_dice_indices() reads for the wound-roll abilities.

        A single die, so index 0 is the whole question."""
        if self.dice_manager is None:
            return False
        return 0 not in self.dice_manager.already_rerolled

    def maybe_offer(self, total, on_resolved):
        """Called with the Damage roll's acknowledged `total`. Requests the
        choice and returns True when it is worth offering; returns False when
        there is nothing to ask, in which case the caller carries on with the
        unmodified total.

        `on_resolved(reroll)` is how the answer comes back, as a plain bool -
        the caller owns the dice machinery (it is the one holding the
        DiceNotationRoll), so it does the throwing; this object only asks the
        question. The caller must not continue on its own once this returned
        True (DecisionManager.request() never resolves inline)."""
        if self.decision_manager is None or not self.can_offer():
            return False
        options = [
            (f"{self.label}: re-roll the Damage roll ({total})", lambda: self._chose(on_resolved, True)),
            (f"Keep the Damage roll ({total})", lambda: self._chose(on_resolved, False)),
        ]
        suffix = f" {self.prompt_suffix}" if self.prompt_suffix else ""
        self.decision_manager.request(
            self.owner,
            f"{self.weapon_name}: {self.label} - re-roll the Damage roll{suffix}?",
            options,
        )
        return True

    def _chose(self, on_resolved, reroll):
        if reroll and self.game_log is not None:
            self.game_log.add(f"{self.label}: re-rolling {self.weapon_name}'s Damage roll.")
        on_resolved(reroll)
