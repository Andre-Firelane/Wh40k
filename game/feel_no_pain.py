from game.doks_toolz import doks_toolz_feel_no_pain
from game.rites_of_reanimation import rites_of_reanimation_feel_no_pain
from game.stim_injectors import stim_injectors_feel_no_pain
from game.thresholds import parse_threshold
from game.waaagh import effective_feel_no_pain


def _better_threshold(a, b):
    """The better (numerically lower) of two printed Feel No Pain thresholds,
    "-" meaning none - so a model keeps whatever it already had if a granted
    ability would be worse. Same "never worse than what's printed" principle
    game/waaagh.py's effective_feel_no_pain() applies to Krumpin' Time; needed
    a second time here because Stim Injectors is a THIRD source, granted per
    unit rather than per model, and the two can be active at once."""
    ta, tb = parse_threshold(a), parse_threshold(b)
    if ta is None:
        return b
    if tb is None:
        return a
    return a if ta <= tb else b


def current_feel_no_pain(model, waaagh=None):
    """Every Feel No Pain source that currently applies to this model, resolved
    to the single best threshold: the model's own printed value, Meganobz'
    Waaagh!-conditional Krumpin' Time, Retaliation Cadre's Stim Injectors
    stratagem, and a Painboy's Dok's Toolz. The one place that answers "what is
    this model's FNP right now".

    _better_threshold() folds pairwise, so adding a source is one more fold and
    the "never worse than what's printed" guarantee still holds across all of
    them: a model that already prints a 5+ keeps it under a granted 6+."""
    best = _better_threshold(effective_feel_no_pain(model, waaagh), stim_injectors_feel_no_pain(model))
    best = _better_threshold(best, doks_toolz_feel_no_pain(model))
    # The Necron Technomancer's Rites of Reanimation - the Painboy's Dok's
    # Toolz under another name, and folded in exactly the same way.
    return _better_threshold(best, rites_of_reanimation_feel_no_pain(model))


class FeelNoPainRoll:
    """Rule 24.12 (Feel No Pain X+): each time a model with this ability
    would lose a wound, roll one D6 per wound point about to be lost - a
    real, visible dice step (user's explicit instruction), not a silent
    computation - and reduce the damage by however many meet the X+
    threshold before it's actually applied. A model without Feel No Pain
    (or an amount of 0, or no dice_manager - e.g. the non-interactive
    resolve_damage()/resolve_mortal_wounds() convenience wrappers used by
    tests) resolves immediately (`is_pending` stays False, `reduced_amount`
    equals the full amount) - nothing to wait for.

    The threshold itself comes from current_feel_no_pain() above, which folds
    together every source that can grant one. `waaagh` (optional, like
    DamageAllocationSession's own) is what lets Meganobz's "Krumpin' Time"
    apply its conditional 5+ - see game/waaagh.py's effective_feel_no_pain()
    for that logic and which callers actually thread it through. Retaliation
    Cadre's Stim Injectors needs no such threading: it is a flag on the unit,
    so it reaches every damage source that builds a FeelNoPainRoll at all."""

    def __init__(self, model, amount, dice_manager, log=None, waaagh=None):
        self.model = model
        self.amount = amount
        self.dice_manager = dice_manager
        self.log = log
        self.is_pending = False
        self.reduced_amount = amount
        self._threshold = parse_threshold(current_feel_no_pain(model, waaagh))
        if self._threshold is not None and amount > 0 and dice_manager is not None:
            self.is_pending = True
            dice_manager.roll(
                count=amount, sides=6,
                label=f"Feel No Pain: {model.profile.name} ({amount} wound(s))",
                success_threshold=self._threshold,
            )

    @property
    def done(self):
        return not self.is_pending

    def on_dice_acknowledged(self):
        if not self.is_pending:
            return
        rolls = self.dice_manager.last_values
        successes = sum(1 for r in rolls if r >= self._threshold)
        self.reduced_amount = max(0, self.amount - successes)
        if self.log is not None:
            self.log(
                f"Feel No Pain ({self.model.profile.name}): rolled {rolls} - "
                f"{successes}/{self.amount} wound(s) saved."
            )
        self.is_pending = False
