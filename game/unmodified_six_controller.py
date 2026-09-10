"""Spending an "unmodified 6" ability from the left panel, against the roll
that is on the table - instead of being asked about it after every roll.

USER REPORT
-----------
"momentan werde ich bei aeldari jedes mal gefragt, ob ich aspect shrine tokens
verwenden will, um wuerfel ergebnisse zu manipulieren. nach jedem wurf. kann
das nicht eine option im linken panel sein, statt eines overlays? command
reroll funktioniert ja auch so. ich klicke aspect shrine button an und waehle
dann den wuerfel aus, den ich aendern will. genau das gleiche mit branching
fates vom farseer."

WHAT WAS WRONG, MEASURED FIRST
------------------------------
The offer was a DecisionManager prompt raised at the END of the hit/wound
step - i.e. in the exact frame the player acknowledged the roll. So every
single roll cost two clicks: dismiss the dice, then answer a modal about a
resource you were probably hoarding anyway. With an unspent Aspect Shrine
token, that repeated for the whole battle.

THE GATE IS KEPT, AND ASKED OF BETTER DATA
------------------------------------------
game/unmodified_six.py gates the offer hard: there must be a failure to
convert, or a non-critical success in a step where a critical actually does
something. Its stated reason was that an offer INTERRUPTS, and a button does
not - so it was worth asking whether the gate could go. It stays, because it
has a second and independent reason: never offer what buys nothing (error
class 5). A button that changes a die from a 5 to a 6 on a weapon where a
critical does nothing is a button that lies about what it is for.

What DID change is where the counts come from. The old path recovered the
failure count from a per-group dice COUNT threaded through nine signatures,
because by the time it asked, the dice were gone. This asks the dice on the
table, through the dice manager's own is_success()/is_critical() - the same
two functions the panel colours them with.

WHY THIS MOMENT, AND WHAT IT COSTS
----------------------------------
Command Re-roll's shape needs the dice to still be on the table, so the offer
moves from the END of the step to WHILE THE ROLL STANDS. That is earlier than
before: game/aspect_shrine.py argued the offer belonged after every re-roll,
"a once-per-battle resource should be spent against the roll that actually
stands". It still can be - a re-roll is a pending roll of its own, and the
button is offered on that one too. What changes is that the player CAN now
spend it on a die that a later re-roll then throws away. That is the same
freedom Command Re-roll already has, and it is theirs to use.

WHAT IT DOES
------------
Changes the chosen die to 6 and lets the ordinary resolution read it. That is
strictly more correct than the arithmetic it replaces: the old path adjusted
hit/crit COUNTERS after the fact, while this changes the roll itself, so
[SUSTAINED HITS], [LETHAL HITS], [DEVASTATING WOUNDS], [ANTI-X]'s lowered
critical threshold and every future reader of that die all see it. Modifiers
in this engine adjust the THRESHOLD, never the die (game/modifiers.py), so a
die set to 6 is literally an unmodified 6.
"""

from game.dice import DAMAGE_ROLL, HIT_ROLL, WOUND_ROLL
from game import aspect_shrine
from game import branching_fates
from game import unmodified_six

# Every ability that grants "change the result of one roll to an unmodified 6",
# in the order their buttons appear. Aspect Shrine first: it is the scarcer
# resource (once per battle per token, against Branching Fates' once per
# phase), so it is the one a player looks for deliberately.
SOURCES = (aspect_shrine, branching_fates)

# The roll kinds a die can be changed on, per ability. Both cover the Hit and
# Wound rolls; only Branching Fates covers the Damage roll.
#
# The Damage roll is still handled apart from the other two, but only because
# of its SHAPE, not its arithmetic: it is not a die that succeeds or fails, so
# there is no failure to convert and no "does a critical buy anything" gate -
# the offer stands whenever the die is not already a 6. What it does to the
# die is now identical to the Hit and Wound halves (set it to 6), which is
# what the printed sentence's single predicate requires - see
# game/branching_fates.py. It was NOT identical before: it set the RESULT to
# 6, so a D6+2 got a 4 and the ability capped a weapon at less than its own
# maximum.
DIE_ROLL_KINDS = (HIT_ROLL, WOUND_ROLL)
ROLL_KINDS = {
    aspect_shrine: (HIT_ROLL, WOUND_ROLL),
    branching_fates: (HIT_ROLL, WOUND_ROLL, DAMAGE_ROLL),
}


class UnmodifiedSixController:
    """One controller for every "change a die to an unmodified 6" ability,
    not one per ability: the eligibility question, the die-selection step and
    the panel wiring are identical for all of them, and only the RESOURCE
    differs - which each ability module already owns.

    Deliberately shaped after game/command_reroll.py, because the user asked
    for that shape by name: can_use -> start -> choose_die, with selecting_die
    driving both the panel and main.py's dice-click routing."""

    def __init__(self, dice_manager, attack_controllers=(), game_log=None):
        self.dice_manager = dice_manager
        # The controllers that own an attack in progress - shooting and fight.
        # Asked in order; the one with a weapon group open is the one whose
        # roll is on the table.
        self.attack_controllers = list(attack_controllers)
        self.game_log = game_log
        self.selecting_die = False
        self._source = None

    # -------------------------------------------------------------- context

    def _context(self):
        """(squad, model, weapon) the roll on the table belongs to, or None.

        Read from whichever attack controller has a weapon group open rather
        than from the dice manager: the die's owner is not enough, the
        exclusion clauses ("excluding CHARACTER models", "excluding SUPPORT
        WEAPON models") are about the MODEL making the attack, and whether a
        critical is worth anything depends on the WEAPON."""
        for controller in self.attack_controllers:
            if controller is None:
                continue
            context = controller.unmodified_six_context()
            if context is not None:
                return context
        return None

    def _damage_context(self):
        """(squad, model, notation_roll) when a DAMAGE roll is on the table,
        or None. Asked of the same controllers as _context()."""
        for controller in self.attack_controllers:
            if controller is None:
                continue
            context = controller.unmodified_six_damage_context()
            if context is not None:
                return context
        return None

    # ---------------------------------------------------------- eligibility

    def _changeable_indices(self):
        """Dice that are not already the result this would set them to.
        Offering one that is already a 6 would buy nothing (error class 5)."""
        values = self.dice_manager.pending_values if self.dice_manager is not None else None
        if not values:
            return []
        return [i for i, v in enumerate(values) if v != unmodified_six.UNMODIFIED_SIX]

    def worth_changing(self, weapon):
        """game/unmodified_six.py's "is there a die worth changing" gate, asked
        of the roll ON THE TABLE: "failure", "success" or None.

        The counts come straight from the pending dice through the dice
        manager's own is_success()/is_critical(), which is strictly better
        than what this replaced - the old path recovered the failure count
        from a per-group dice COUNT threaded through nine signatures, and had
        to, because by the time it asked, the dice were gone.

        The gate itself is kept even though the offer is no longer a prompt.
        Its original job was to stop the ability interrupting on every roll,
        and a button does not interrupt - but "never offer what buys nothing"
        (error class 5) is a second, independent reason, and that one still
        holds."""
        values = self.dice_manager.pending_values or ()
        if not values:
            return None
        successes = sum(1 for v in values if self.dice_manager.is_success(v))
        crits = sum(1 for v in values if self.dice_manager.is_critical(v))
        failures = len(values) - successes
        crit_matters = (unmodified_six.crit_matters_on_hit(weapon)
                        if self.dice_manager.roll_kind == HIT_ROLL
                        else unmodified_six.crit_matters_on_wound(weapon))
        return unmodified_six.gain(failures, successes, crits, crit_matters)

    def _damage_offer(self):
        """(new_face, squad, model) for a DAMAGE roll worth changing, or None.

        The DIE becomes an unmodified 6, exactly as on a Hit or Wound roll -
        the printed sentence has one predicate for all three. The weapon's
        printed bonus is deliberately NOT consulted: it rides along, so a
        D6+2 pays 8. Declines a multi-die roll, where "the die" would name
        nothing (DiceNotationRoll.single_die)."""
        context = self._damage_context()
        if context is None:
            return None
        squad, model, roll = context
        if not roll.single_die:
            return None
        values = self.dice_manager.pending_values
        if not values:
            return None
        face = branching_fates.damage_change(squad, model, values[0])
        if face is None:
            return None  # the die is already a 6, or the ability is not live
        return (face, squad, model)

    def available_sources(self):
        """Every ability that could change the roll on the table, as
        [(module, squad, model), ...]. Empty when there is nothing to offer -
        which is what the panel draws off."""
        if self.dice_manager is None or not self.dice_manager.is_pending:
            return []
        kind = self.dice_manager.roll_kind

        if kind == DAMAGE_ROLL:
            # Only Branching Fates covers this one, and there is no die to
            # pick: a Damage roll is a single die (measured across every
            # dice-notation Damage characteristic in this repo), so the button
            # applies straight away, the same shortcut Command Re-roll takes.
            offer = self._damage_offer()
            if offer is None:
                return []
            _face, squad, model = offer
            return [(branching_fates, squad, model)]

        if kind not in DIE_ROLL_KINDS:
            return []
        if not self._changeable_indices():
            return []
        context = self._context()
        if context is None:
            return []
        squad, model, weapon = context
        if self.worth_changing(weapon) is None:
            return []
        return [(source, squad, model) for source in SOURCES
                if kind in ROLL_KINDS[source] and source.usable(squad, model)]

    def can_use(self, source=None):
        available = self.available_sources()
        if source is None:
            return bool(available)
        return any(s is source for s, _squad, _model in available)

    def label_for(self, source):
        """The button's text. Each ability says how much of its resource is
        left, because that is the whole question a player has here."""
        context = self._context()
        squad = context[0] if context is not None else None
        return source.button_label(squad)

    def preferred_index(self):
        """The die game/unmodified_six.py would pick: a failure if there is
        one, otherwise a non-critical success. Not used to decide FOR the
        player - the user asked to pick the die - but it is what a
        single-candidate roll collapses to, and what the panel could hint
        with. Returns None when nothing is worth changing."""
        values = self.dice_manager.pending_values or ()
        changeable = set(self._changeable_indices())
        failures = [i for i, v in enumerate(values)
                    if i in changeable and not self.dice_manager.is_success(v)]
        if failures:
            return failures[0]
        plain = [i for i, v in enumerate(values)
                 if i in changeable and not self.dice_manager.is_critical(v)]
        return plain[0] if plain else None

    # ------------------------------------------------------------- the flow

    def start(self, source):
        """The player clicked this ability's button in the left panel."""
        if not self.can_use(source):
            return
        self._source = source
        if self.dice_manager.roll_kind == DAMAGE_ROLL:
            # One die, and it becomes a 6 - so there is nothing to pick.
            self._apply_damage()
            return
        changeable = self._changeable_indices()
        if len(changeable) == 1:
            # Nothing to choose. Same shortcut Command Re-roll takes when only
            # one die is re-rollable - a "pick one of one" step is a click that
            # asks nothing.
            self._apply(changeable[0])
            return
        self.selecting_die = True

    def choose_die(self, index):
        """The player clicked a die in the DicePanel while selecting_die."""
        if not self.selecting_die:
            return
        if index not in self._changeable_indices():
            return  # already a 6: ignore the click rather than spend on nothing
        self.selecting_die = False
        self._apply(index)

    def cancel_selection(self):
        self.selecting_die = False
        self._source = None

    def _apply(self, index):
        source, self._source = self._source, None
        context = self._context()
        if source is None or context is None:
            return
        squad, _model, _weapon = context
        was = self.dice_manager.pending_values[index]
        if not self.dice_manager.set_die(index, unmodified_six.UNMODIFIED_SIX):
            return
        source.spend(squad)
        if self.game_log is not None:
            self.game_log.add(
                f"{squad.name}: {source.ACCEPT_LABEL} - {self.dice_manager.label or 'a roll'} "
                f"die {index + 1} counts as an unmodified {unmodified_six.UNMODIFIED_SIX} "
                f"(was {was})."
            )

    def _apply_damage(self):
        """Set the single Damage die to an unmodified 6, and spend.

        The log line names the resulting AMOUNT as well as the die, because
        with a printed bonus the two differ (a D6+2 die of 6 is 8 damage) and
        a line that says only "an unmodified 6" next to 8 wounds sends the
        next investigation back to the board."""
        source, self._source = self._source, None
        offer = self._damage_offer()
        if source is not branching_fates or offer is None:
            return
        face, squad, _model = offer
        was = self.dice_manager.pending_values[0]
        if not self.dice_manager.set_die(0, face):
            return
        source.spend(squad)
        if self.game_log is not None:
            context = self._damage_context()
            total = context[2].projected_total if context is not None else None
            amount = "" if total is None else f", for {total} damage"
            self.game_log.add(
                f"{squad.name}: {source.ACCEPT_LABEL} - {self.dice_manager.label or 'a Damage roll'} "
                f"die {was} counts as an unmodified {unmodified_six.UNMODIFIED_SIX}{amount}."
            )

    def reset(self):
        """Any die selection left open when the roll it belonged to goes away.
        Called from main.py's dice-acknowledge path, so a selection can never
        outlive its own roll and strand the panel in a mode with nothing to
        click."""
        self.selecting_die = False
        self._source = None
