import random
import time

# Rule 15.02 (Command Re-roll) tags every roll with a "kind" so a stratagem
# can check "is this one of the roll types I apply to" without parsing the
# human-readable label text. Battle-shock rolls (01.07) are a leadership
# roll, not on 15.02's list, so they deliberately have no kind here.
ADVANCE_ROLL = "advance"
CHARGE_ROLL = "charge"
HIT_ROLL = "hit"
WOUND_ROLL = "wound"
SAVE_ROLL = "save"
DAMAGE_ROLL = "damage"
HAZARD_ROLL = "hazard"
ATTACKS_ROLL = "attacks"
# Rule 15.09 (Snap Shooting): "You cannot re-roll hit rolls" - a distinct
# kind from HIT_ROLL (rather than a special-cased HIT_ROLL) specifically so
# CommandRerollController's REROLLABLE_KINDS set can exclude just this one
# roll without touching every other hit roll in the game.
SNAP_SHOT_HIT_ROLL = "snap_shot_hit"
# Gretchin's own "Thievin' Scavengers" ability (user-supplied, not a core
# rule - see game/thievin_scavengers.py): not on rule 15.02's re-rollable
# list either (same reasoning as battle-shock rolls above), so likewise
# deliberately left out of command_reroll.py's REROLLABLE_KINDS.
THIEVIN_SCAVENGERS_ROLL = "thievin_scavengers"

REROLL_ANIMATION_DURATION = 0.4  # seconds - how long DicePanel flickers a re-rolled die before settling


class DiceManager:
    def __init__(self):
        self.pending_values = None  # list[int] while a roll awaits acknowledgement, else None
        self.last_values = None     # the most recent roll, still readable after acknowledgement
        self.label = None           # what this roll represents, e.g. "Hit Roll"
        self.success_threshold = None  # min value to succeed, or None if pass/fail doesn't apply
        self.target_name = None    # who this roll is being resolved against, if anyone
        # What target_name IS to this roll. Most rolls resolve against an
        # enemy, so "Target" is the default - but plenty do not: a Charge
        # roll's name is the unit DOING the charging, a battle-shock test's
        # is the unit taking it. The panel prints "{subject_label}: {name}",
        # so a roll that means something else can say so instead of calling
        # its own unit a target.
        self.subject_label = "Target"
        # The two units this roll is BETWEEN, when it is part of an attack
        # sequence - held purely so DicePanel can show their art next to the
        # names (user: "wenn du beim wuerfel panel anzeigst, was auf wen
        # schiesst, baue bitte die sprites mit ein, damit man es besser auf
        # den ersten blick erkennen kann"). Plain references, never read for
        # any rule; cleared/replaced by the next roll() like every other
        # field here, so a later Advance/Charge roll cannot inherit the
        # matchup of the shot before it. Either may be None (a roll that has
        # no attacker, e.g. a battle-shock test, or a unit whose art the
        # panel then simply omits).
        self.attacker_squad = None
        self.target_squad = None
        # Rule 05.02's critical threshold for THIS roll (an unmodified 6
        # normally; [ANTI-X Y+] 24.03 lowers it on a wound roll, Whispering
        # Web / Unbridled Carnage / Mandiblasters on a hit roll), plus what
        # a critical die on it actually BUYS - "LETHAL HIT", "SUSTAINED HIT",
        # "DEVASTATING WOUND". User: "markiere bitte die kritischen
        # gewuerfelten treffer mit 'lethal hit', wenn diese Regel aktiv ist."
        # Presentation only, like target_name: the engine re-derives both
        # from the weapon when it resolves the roll, this is what lets the
        # panel say so while the dice are still on screen.
        self.crit_threshold = None
        self.crit_labels = ()
        self.sides = None          # die type of the current roll - needed to re-roll it later
        self.roll_kind = None       # one of the *_ROLL constants above, or None if not reroll-eligible
        self.rerolled_indices = set()   # which pending_values indices were just re-rolled (rule 15.02)
        self.rerolled_at = None         # time.monotonic() timestamp of that re-roll, for DicePanel's animation
        # Core rule: a dice can never be re-rolled more than once, no matter
        # how many different effects would each allow a re-roll of it. This
        # is the ONE place that memory lives, because the sources are spread
        # out (Command Re-roll 15.02, [TWIN-LINKED] 24.38, Breach and Clear,
        # Forward Observers) and none of them can see the others. Indices
        # into pending_values/last_values; deliberately NOT cleared by
        # acknowledge(), since the ability re-rolls decide how many dice they
        # may throw AFTER the roll has been acknowledged (see the callers in
        # shooting.py/fight.py) - only a brand new roll() clears it.
        self.already_rerolled = set()
        self.damage_per_failure = None  # SAVE_ROLL only: damage a single failed save inflicts, for DicePanel's summary line

    @property
    def is_pending(self):
        return self.pending_values is not None

    def roll(self, count=1, sides=6, label=None, success_threshold=None, target_name=None, roll_kind=None, damage_per_failure=None, is_reroll=False, attacker_squad=None, target_squad=None,
             crit_threshold=None, crit_labels=(), subject_label="Target"):
        """`is_reroll` marks a roll that IS itself the re-roll of earlier
        dice (an ability throwing the failures again, rather than a fresh
        roll) - every die in it has then already used up its one re-roll and
        none of them may be re-rolled a second time."""
        values = [random.randint(1, sides) for _ in range(count)]
        self.pending_values = values
        self.last_values = values
        self.label = label
        self.success_threshold = success_threshold
        self.target_name = target_name
        self.subject_label = subject_label
        self.attacker_squad = attacker_squad
        self.target_squad = target_squad
        self.crit_threshold = crit_threshold
        self.crit_labels = tuple(crit_labels)
        self.sides = sides
        self.roll_kind = roll_kind
        self.rerolled_indices = set()
        self.rerolled_at = None
        self.already_rerolled = set(range(count)) if is_reroll else set()
        self.damage_per_failure = damage_per_failure
        return values

    def is_critical(self, value):
        """Whether a single die of the CURRENT roll is a critical one, given
        what the caller said this roll's threshold is (None if it did not say
        - most rolls have no notion of a critical result at all).

        Rules 05.01/05.02: an unmodified 1 is always a failure, so it can
        never be critical however far a threshold was lowered - the same
        floor is_success() applies, for the same reason."""
        if self.crit_threshold is None or value == 1:
            return False
        return value >= self.crit_threshold

    def is_success(self, value):
        """Whether a single die of the CURRENT roll passed, or None if this
        roll has no pass/fail notion at all (an Advance/Charge/Damage roll,
        which has no success_threshold).

        Rules 05.01/05.04: "an unmodified roll of 1 always fails", whatever
        the threshold ended up as after modifiers. This is the one place
        that floor lives for presentation - real user report ("ich sehe oft
        das Wuerfelwurf von 1 gruen ist. 1 failt aber immer egal welche
        modifikatoren"): the dice panel used to re-derive the outcome as a
        plain `value >= success_threshold`, so any roll whose threshold had
        been modified down to 1+ (e.g. Might is Right's +1 on a base 2+, or
        a Guided +1 on a base 2+ - 17 such dice across the logs in this
        repo) painted a natural 1 green and filed it under the successes,
        while game/shooting.py's _resolve_roll() and
        game/damage_resolution.py's _resolve_save() had both, correctly,
        already counted it as a failure.

        Deliberately NOT also re-deriving rule 05.02's "an unmodified 6 is
        always a critical success" or a save's invulnerable alternative:
        both would need data this class isn't given (the crit threshold,
        which [ANTI-X] 24.03 can lower; the target model's invulnerable
        save). Measured over every log in this repo before leaving them
        out - zero dice would have been coloured differently by either,
        against 17 for the floor above. See CLAUDE.md for the residual."""
        if self.success_threshold is None:
            return None
        if value == 1:
            return False
        return value >= self.success_threshold

    def acknowledge(self):
        self.pending_values = None
        self.rerolled_indices = set()
        self.rerolled_at = None

    def rerollable_indices(self):
        """Which of the pending dice may still be re-rolled - i.e. all of
        them minus the ones that have already been re-rolled once."""
        if self.pending_values is None:
            return []
        return [i for i in range(len(self.pending_values)) if i not in self.already_rerolled]

    def can_reroll_all(self):
        """Whether a "re-roll it in full" effect (rule 15.02 on a Charge
        roll) is still legal - it is not once any single die of the roll has
        already been re-rolled, since that die would be going twice."""
        return self.pending_values is not None and not self.already_rerolled

    def reroll_die(self, index):
        """Rule 15.02: re-roll a single die from a multi-die pending roll -
        "select one of those dice to re-roll". Refuses a die that has already
        been re-rolled once; returns whether it actually threw it."""
        if self.pending_values is None or not (0 <= index < len(self.pending_values)):
            return False
        if index in self.already_rerolled:
            return False
        self.pending_values[index] = random.randint(1, self.sides)
        self.rerolled_indices = {index}
        self.already_rerolled.add(index)
        self.rerolled_at = time.monotonic()
        return True

    def set_die(self, index, value):
        """Change one die of the pending roll to a fixed result - the
        "change the result of one Hit roll ... to an unmodified 6" abilities
        (game/unmodified_six.py's two consumers).

        NOT a re-roll, and deliberately not booked as one: rule 05.03's "a
        dice can never be re-rolled more than once" is about throwing it
        again, and these abilities throw nothing. So `already_rerolled` is
        left alone and a die changed this way can still be re-rolled
        afterwards (and vice versa) - which is the player's business, not
        this class's.

        Marked in `rerolled_indices` all the same, because that is what the
        panel highlights: the point of picking a die by hand is seeing which
        one changed. Returns whether it applied."""
        if self.pending_values is None or not (0 <= index < len(self.pending_values)):
            return False
        if self.pending_values[index] == value:
            return False
        self.pending_values[index] = value
        self.rerolled_indices = {index}
        self.rerolled_at = time.monotonic()
        return True

    def reroll_all(self):
        """Rule 15.02: charge rolls "must" be re-rolled in full, not just
        one die. All-or-nothing: if any die of this roll has already been
        re-rolled, re-rolling "in full" would throw it twice, so nothing is
        thrown at all."""
        if not self.can_reroll_all():
            return False
        for i in range(len(self.pending_values)):
            self.pending_values[i] = random.randint(1, self.sides)
        self.rerolled_indices = set(range(len(self.pending_values)))
        self.already_rerolled = set(range(len(self.pending_values)))
        self.rerolled_at = time.monotonic()
        return True
