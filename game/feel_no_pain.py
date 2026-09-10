from game.advanced_armour import advanced_armour_feel_no_pain
from game.doks_toolz import doks_toolz_feel_no_pain
from game.failure_is_not_an_option import failure_is_not_an_option_feel_no_pain
from game.nanoscarab_amulet import nanoscarab_amulet_feel_no_pain
from game.rites_of_feasting import rites_of_feasting_feel_no_pain
from game.rites_of_reanimation import rites_of_reanimation_feel_no_pain
from game.silent_bodyguard import silent_bodyguard_feel_no_pain
from game.stim_injectors import stim_injectors_feel_no_pain
from game.thresholds import parse_threshold
from game.waaagh import effective_feel_no_pain
from game import armoured_layered_wards
from game import enh_runes_of_warding
from game import ynnari_abilities
# Statistics reporting. battle_stats imports only game/weapons.py, so this
# cannot cycle back into anything here.
from game import battle_stats


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


def current_feel_no_pain(model, waaagh=None, mortal=False, psychic=False,
                         devastating=False):
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
    best = _better_threshold(best, rites_of_reanimation_feel_no_pain(model))
    # The Lokhust Lord's nanoscarab amulet. The first source here that is a
    # per-TOKEN wargear grant rather than a unit-wide or aura one - "the
    # BEARER has the Feel No Pain 5+ ability" - which changes nothing about
    # the folding, only about who it reaches.
    best = _better_threshold(best, nanoscarab_amulet_feel_no_pain(model))
    # The Deathshroud Terminators' Silent Bodyguard - the MIRROR of Rites of
    # Reanimation above: printed on the bodyguards, protecting the leader
    # rather than the other way round. At 4+ it is the best threshold any
    # source here grants, which the fold handles without a precedence rule.
    best = _better_threshold(best, silent_bodyguard_feel_no_pain(model))
    # The Kroot Flesh Shaper's Rites of Feasting - Rites of Reanimation with a
    # second gear (6+, improved to 5+ for the rest of the battle once the unit
    # has destroyed an enemy unit in the Fight phase). The WORSE of the two
    # thresholds is what makes this fold worth having: a Deathshroud bodyguard
    # keeps its own 4+ rather than being dragged down to 6+, which is exactly
    # what "never worse than printed" is for.
    best = _better_threshold(best, rites_of_feasting_feel_no_pain(model))
    # The Ethereal's Failure Is Not an Option - the THIRD datasheet to print
    # Rites of Reanimation's exact sentence, and folded identically.
    best = _better_threshold(best, failure_is_not_an_option_feel_no_pain(model))
    # The Broadsides' Advanced Armour - the first CONDITIONAL source here:
    # Feel No Pain 4+ against MORTAL WOUNDS only. `mortal` is set by
    # MortalWoundAllocationSession alone, so every other caller keeps the
    # default and keeps meaning what it did.
    best = _better_threshold(best, advanced_armour_feel_no_pain(model, mortal))
    # The Visarch's Yvraine's Champion - the first source that reaches only the
    # OTHER CHARACTERS in its unit, which is why the predicate takes a model
    # and reads three separate printed words rather than a single flag.
    best = _better_threshold(best, ynnari_abilities.yvraines_champion_feel_no_pain(model))
    # Armoured Warhost's Layered Wards - the SECOND conditional source after
    # Advanced Armour, and the first bought rather than printed, so its flag
    # sits on the Squad. Same `mortal` gate, one more fold.
    best = _better_threshold(
        best, armoured_layered_wards.layered_wards_feel_no_pain(model, mortal))
    # Seer Council's Runes of Warding - the first source here with THREE
    # conditions rather than one, and the reason `psychic` and `devastating`
    # exist alongside `mortal`. Each is set by exactly one caller: the mortal
    # path, the damage session that knows the weapon, and the devastating
    # session respectively - so every other caller keeps the defaults and
    # keeps meaning what it did.
    return _better_threshold(
        best, enh_runes_of_warding.feel_no_pain(
            model, mortal=mortal, psychic=psychic, devastating=devastating))


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

    def __init__(self, model, amount, dice_manager, log=None, waaagh=None, mortal=False,
                 psychic=False, devastating=False):
        self.model = model
        self.amount = amount
        self.dice_manager = dice_manager
        self.log = log
        self.is_pending = False
        self.reduced_amount = amount
        self._threshold = parse_threshold(current_feel_no_pain(
            model, waaagh, mortal, psychic=psychic, devastating=devastating))
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
        # Statistics: every wound this ability just shrugged off. Reported
        # from inside the roll rather than at its six users, because this is
        # the ONE place a Feel No Pain reduction is ever computed - all three
        # sessions in game/damage_resolution.py build one of these and then
        # only read `reduced_amount`. Capped at `amount` for the same reason
        # the line above is: successes can exceed the wounds on the table.
        battle_stats.report_prevented(self.model, min(successes, self.amount))
        if self.log is not None:
            self.log(
                f"Feel No Pain ({self.model.profile.name}): rolled {rolls} - "
                f"{successes}/{self.amount} wound(s) saved."
            )
        self.is_pending = False
