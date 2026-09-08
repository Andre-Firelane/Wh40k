"""The "you can re-roll the result" offer for a DICE-NOTATION roll.

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

AND THE SAME MOVE AGAIN, ONE LEVEL UP. This was game/damage_reroll.py until
Guardian Battlehost's Breath of Vaul arrived: it re-rolls the ATTACKS
characteristic of a flamer, which is the same dice-notation roll and the same
"you can re-roll the result" offer, just not a Damage one. A module named
after the first KIND of roll it served is the wrong home for the second - the
same rename crit_ap.py -> critical_wound_split.py got for the same reason.

So the only Damage-specific thing left, the word in the prompt, is a parameter
too (`roll_name`), defaulting to "Damage" so every existing caller is
unchanged. game/damage_reroll.py stays as a re-export, which keeps ONE
definition.
"""


class DamageRerollOffer:
    """maybe_offer/on_resolved, the same contract StealthDronesController
    already satisfies inside DamageAllocationSession.

    Built per weapon group by game/shooting.py, and only when the granting
    ability already applies - so this object's mere existence means "a
    re-roll is on offer for this group". It does not re-check the target."""

    def __init__(self, label, decision_manager=None, dice_manager=None, game_log=None,
                 owner=None, weapon_name="", prompt_suffix="", automatic_faces=(),
                 notation=None, roll_name="Damage", offerable=True):
        self.label = label          # the ability's own name, for the prompt and the log
        # Which roll this is, for the prompt and the log - "Damage" or
        # "Attacks". The rest of the class does not care which.
        self.roll_name = roll_name
        self.decision_manager = decision_manager
        self.dice_manager = dice_manager
        self.game_log = game_log
        self.owner = owner          # the ATTACKING player - "you can re-roll" is the attacker's choice
        self.weapon_name = weapon_name
        self.prompt_suffix = prompt_suffix  # e.g. "against this MONSTER/VEHICLE target"
        # An ability whose text says "re-roll a Damage roll of 1" rather than
        # "you can re-roll" is MANDATORY, so it is not an offer at all: the die
        # faces listed here are re-rolled without asking. The D-cannon
        # Platform's Structural Collapse is the first such source.
        self.automatic_faces = set(automatic_faces)
        # Needed only by automatic_faces, and only because "a Damage roll of 1"
        # names the DIE, not the total - a D6+2 showing a 1 arrives here as a
        # 3. Same distinction Branching Fates' face_for_total() had to make.
        self.notation = notation
        # Whether the "you can re-roll" QUESTION may be asked at all, as
        # opposed to whether there is a die left to ask about (can_offer()).
        # A source can be mandatory-only: the D-cannon's Structural Collapse
        # re-rolls a 1 without asking, and grants the free re-roll ONLY
        # against a TITANIC target - two clauses of one printed sentence,
        # served by one of these objects. Without this the mandatory half
        # fired on a 1 and the optional half fired on everything else, which
        # is a free re-roll on every shot the rule never granted.
        self.offerable = offerable

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

    def face_of(self, total):
        """The die face behind an acknowledged Damage `total`.

        Only meaningful for a single-die notation, which every Damage roll in
        this repo is; returns None otherwise rather than guessing, so a future
        multi-die Damage characteristic cannot be silently mis-read."""
        if self.notation is None or self.notation.dice != 1:
            return None
        return total - self.notation.bonus

    def auto_reroll_for(self, total):
        """Whether this Damage roll is re-rolled WITHOUT asking.

        Checked before maybe_offer() by the session, and gated on the same
        already_rerolled ledger, so a mandatory re-roll still cannot throw the
        same die twice."""
        if not self.automatic_faces or not self.can_offer():
            return False
        face = self.face_of(total)
        return face is not None and face in self.automatic_faces

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
        if self.decision_manager is None or not self.offerable or not self.can_offer():
            return False
        options = [
            (f"{self.label}: re-roll the {self.roll_name} roll ({total})", lambda: self._chose(on_resolved, True)),
            (f"Keep the {self.roll_name} roll ({total})", lambda: self._chose(on_resolved, False)),
        ]
        suffix = f" {self.prompt_suffix}" if self.prompt_suffix else ""
        self.decision_manager.request(
            self.owner,
            f"{self.weapon_name}: {self.label} - re-roll the {self.roll_name} roll{suffix}?",
            options,
        )
        return True

    def _chose(self, on_resolved, reroll):
        if reroll and self.game_log is not None:
            self.game_log.add(f"{self.label}: re-rolling {self.weapon_name}'s {self.roll_name} roll.")
        on_resolved(reroll)
