"""What may the player do with the roll that is on the table right now?

User: "Momentan akzeptiert man das Würfelergebnis durch ein Klick irgendwo hin.
Besser wäre: Unten im Panel Buttons je nach Situation: Wurf akzeptieren / 1en
wiederholen (wenns geht) / alles wiederholen (wenns geht) / Fehlschläge
wiederholen (wenns geht). Dann poppen nicht so viele Overlays hintereinander
auf."

ONE answer, read by four places - the dice panel's button row, main.py's click
branch, its keyboard branch and the click-anywhere gate - the shape of
game/unit_pick.py and game/damage_pick.py.

THE QUESTION MOVES, THE ARITHMETIC DOES NOT. A hit or wound re-roll offer is
built inside the controller's on_dice_acknowledged(): it counts the roll, and a
taken re-roll is a new roll whose successes are added to what was carried
over. That arithmetic is pinned by well over a hundred checks and stays exactly
where it is. What changes is WHEN the player is asked:

  * the controller exposes pending_roll_choice(), which runs the SAME step
    method as the acknowledgement in preview mode - so the buttons and the
    offer cannot disagree by construction;
  * a click on a button records its key on the roll
    (DiceManager.choose_reroll()) and accepts the roll;
  * the offer site then calls take() - a recorded key runs that option's
    callback directly, anything else opens the prompt exactly as before.

The prompt path therefore stays as the fallback, which is what keeps this
change from ever deadlocking a harness that calls acknowledge() itself.

Only a HUMAN's roll gets buttons: an AI-owned offer is answered through the
DecisionManager queue by ai/agent_driver.py, as it always was.
"""

ACCEPT = "accept"
FAILURES = "failures"
WHOLE = "whole"
ONES = "ones"

#: What a button says. Short on purpose - the dice under it show which dice
#: these are, and the count in brackets says how many.
BUTTON_LABELS = {
    ACCEPT: "Accept",
    FAILURES: "Re-roll failures",
    WHOLE: "Re-roll all",
    ONES: "Re-roll 1s",
}

#: Left to right on the panel. Accept first: it is the button pressed most.
KEY_ORDER = (ACCEPT, FAILURES, ONES, WHOLE)

#: The Stratagem and ability buttons (ability_actions()).
COMMAND_REROLL = "command_reroll"
ACTIVATION_REROLL = "activation_reroll"
UNMODIFIED_SIX = "unmodified_six"
CANCEL = "cancel"

#: What the dice panel says while a die is being picked, per mode.
REROLL_PICK_HINT = "Click a die to re-roll it."
UNMODIFIED_SIX_PICK_HINT = "Click a die to make it an unmodified 6."


class RollOption:
    """One button. `acknowledges`: the button accepts the roll and lets the
    controller act on the recorded key (a hit/wound re-roll). Otherwise
    `apply` re-rolls the dice in place and the roll stays on the table (an
    Advance or Charge re-roll)."""

    __slots__ = ("key", "count", "label", "acknowledges", "apply", "accent")

    def __init__(self, key, count=0, label=None, acknowledges=True, apply=None, accent=None):
        self.key = key
        self.count = count
        self.label = label if label is not None else button_label(key, count)
        self.acknowledges = acknowledges
        self.apply = apply
        # button_style's accent, when the button says what it COSTS rather than
        # what it does to the roll: "stratagem" for a CP spend, "danger" for a
        # Cancel. None is the default palette (and Accept draws in "confirm").
        self.accent = accent

    def __repr__(self):
        return f"RollOption({self.key!r}, {self.count!r})"


class RollChoice:
    """Everything the player may do with the roll on the table. `claims` names
    the pre-acknowledgement offer sources (claim_reroll_offer keys) that
    pressing Accept answers, so they do not open a prompt afterwards."""

    __slots__ = ("player", "options", "claims")

    def __init__(self, player, options, claims=()):
        self.player = player
        self.options = tuple(sorted(options, key=lambda o: KEY_ORDER.index(o.key)
                                    if o.key in KEY_ORDER else len(KEY_ORDER)))
        self.claims = tuple(claims)

    @property
    def keys(self):
        return tuple(o.key for o in self.options)

    @property
    def accept_allowed(self):
        """False when a MANDATORY re-roll is on the table (a two-clause source
        with 1s rolled - see game/reroll_scope.py): keeping the result is not a
        legal answer then, so there is no Accept button and a click anywhere
        does not accept either."""
        return ACCEPT in self.keys

    @property
    def has_rerolls(self):
        return any(o.key != ACCEPT for o in self.options)

    def option(self, key):
        for opt in self.options:
            if opt.key == key:
                return opt
        return None


def button_label(key, count=0):
    text = BUTTON_LABELS.get(key, key)
    return f"{text} ({count})" if count and key != ACCEPT else text


def from_offer(player, keyed_options):
    """A RollChoice from a controller's keyed offer options -
    [(key, count, prompt_label, callback), ...] - the shape shooting.py and
    fight.py build their re-roll prompts from."""
    return RollChoice(player, [RollOption(key, count) for key, count, _label, _cb in keyed_options])


def take(dice_manager, keyed_options):
    """At an offer site, after acknowledgement: run the option the player
    already picked on the dice panel. Returns True if one ran - the caller
    then opens no prompt. A recorded key that matches none of the options (the
    board changed under the preview) is dropped and the prompt opens as it
    always did."""
    if dice_manager is None or not hasattr(dice_manager, "take_chosen_reroll"):
        return False
    key = dice_manager.take_chosen_reroll()
    if key is None:
        return False
    for option_key, _count, _label, callback in keyed_options:
        if option_key == key:
            if callback is not None:
                callback()
            return True
    return False


def ability_actions(command_reroll=None, activation_reroll=None, unmodified_six=None):
    """(hint, [RollOption, ...]): what a Stratagem or an ability can still do
    to the roll on the table, as buttons on the dice panel - Command Re-roll
    (15.02), the free single-die re-roll of Targeting Array / Crystal Matrix
    (game/activation_reroll.py), and every "change a die to an unmodified 6"
    ability (Aspect Shrine tokens, Branching Fates).

    User: "buttons fuer faehigkeiten und stratagems sollen doch mit in das
    wuerfel panel rein, statt links in die spalte." They were the left panel's
    whole pending-roll screen (ActionPanel._draw_command_reroll()), and the
    SHAPE is unchanged - press the button, then pick the die. Only where it is
    drawn moved: next to the dice it acts on.

    None of these accepts the roll, so every option is acknowledges=False -
    the in-place shape the Advance and Charge re-roll buttons already have.
    While a die is being picked the buttons stand aside for a Cancel, and
    `hint` names what the pick does; otherwise `hint` is None.

    ONE definition read by main.py's event branch and by its draw call, so the
    button that is drawn and the button that is clicked cannot be two lists."""
    for controller, hint in ((command_reroll, REROLL_PICK_HINT),
                             (activation_reroll, REROLL_PICK_HINT),
                             (unmodified_six, UNMODIFIED_SIX_PICK_HINT)):
        if controller is not None and controller.selecting_die:
            return hint, [RollOption(CANCEL, label="Cancel", acknowledges=False,
                                     apply=controller.cancel_selection, accent="danger")]
    actions = []
    if command_reroll is not None and command_reroll.can_use():
        actions.append(RollOption(COMMAND_REROLL, label="Command Re-roll (1 CP)", acknowledges=False,
                                  apply=command_reroll.start, accent="stratagem"))
    # The LABEL comes from the controller because two datasheet abilities share
    # this button - the gunships' Targeting Array and the Fire Prism's Crystal
    # Matrix - and the panel should not have to know which.
    if activation_reroll is not None and activation_reroll.can_use():
        actions.append(RollOption(ACTIVATION_REROLL, acknowledges=False, apply=activation_reroll.start,
                                  label=activation_reroll.panel_label() or "Targeting Array",))
    # One button per ability that could change a die of THIS roll; the
    # controller decides which those are, so a third such ability needs no
    # change here.
    if unmodified_six is not None:
        for source, _squad, _model in unmodified_six.available_sources():
            actions.append(RollOption(UNMODIFIED_SIX, acknowledges=False,
                                      label=unmodified_six.label_for(source),
                                      apply=lambda s=source: unmodified_six.start(s)))
    return None, actions


def prompt_options(keyed_options):
    """The (label, callback) pairs DecisionManager.request() takes."""
    return [(label, callback) for _key, _count, label, callback in keyed_options]


class RollChoiceView:
    """Asks the registered providers once per ROLL, not once per frame.

    A preview runs the controller's whole step - thresholds, re-roll sources,
    and for some sources a target-eligibility sweep - so it is cached against
    a fingerprint of the roll: which roll (the list's identity), what it shows
    (a Command Re-roll or an unmodified-six change edits the dice in place),
    which dice are spent, and which offers were already claimed."""

    def __init__(self, providers=()):
        self.providers = list(providers)
        self._key = None
        self._choice = None

    def pending(self, dice_manager, human_players):
        if dice_manager is None or not dice_manager.is_pending:
            self._key = None
            self._choice = None
            return None
        key = (
            id(dice_manager.pending_values), tuple(dice_manager.pending_values),
            frozenset(dice_manager.already_rerolled),
            frozenset(getattr(dice_manager, "_reroll_offers", ()) or ()),
        )
        if key != self._key:
            self._key = key
            self._choice = self._ask(dice_manager)
        choice = self._choice
        if choice is None or choice.player not in human_players:
            return None
        return choice

    def invalidate(self):
        self._key = None
        self._choice = None

    def _ask(self, dice_manager):
        for provider in self.providers:
            # A controller that knows its own roll, or a plain callable for
            # one that needs an argument from main() (the Advance offers ask
            # which unit is moving).
            ask = getattr(provider, "pending_roll_choice", None)
            if ask is None and callable(provider):
                ask = provider
            if ask is None:
                continue
            choice = ask()
            if choice is not None and choice.options:
                return choice
        return None
