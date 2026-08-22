from game import psychic_guidance
from game.thresholds import parse_threshold

LEADERSHIP_DICE_COUNT = 2
LEADERSHIP_DICE_SIDES = 6
IMPOSSIBLE_THRESHOLD = 13  # unreachable on 2D6 - used when Ld is "-" (no roll can ever succeed)


def leadership_threshold(squad, all_tokens=None):
    """Rule 01.06: a leadership roll succeeds if the 2D6 result is equal to
    or greater than one or more of the unit's Ld characteristics - i.e. it
    only needs to beat the lowest (easiest) Ld threshold present.

    `all_tokens` is optional and only needed by abilities that OVERRIDE the
    characteristic from off the datasheet - currently Wraithguard's Psychic
    Guidance, whose condition is a distance to another unit. Without it the
    printed values are used, which is the right degradation: a caller that
    cannot see the board cannot answer the proximity question either."""
    thresholds = [parse_threshold(model.profile.leadership) for model in squad.models]
    thresholds = [t for t in thresholds if t is not None]
    if all_tokens is not None and psychic_guidance.applies(squad, all_tokens):
        granted = parse_threshold(psychic_guidance.PSYCHIC_GUIDANCE_LEADERSHIP)
        if granted is not None:
            # min() rather than a replacement: the rule reads as a flat value,
            # but taking the better of the two means a unit whose printed Ld is
            # already better can never be made worse by it.
            thresholds.append(granted)
    return min(thresholds) if thresholds else None


def leadership_success(rolls, squad, all_tokens=None, penalty=0):
    """Whether this 2D6 passes the unit's Leadership test.

    `all_tokens` matters and used to be missing - a real bug: the caller in
    game/battle_shock.py computes the threshold WITH the board for the dice
    panel (so an ability that overrides the characteristic, currently
    Wraithguard's Psychic Guidance, is shown), while this function recomputed
    it WITHOUT and judged the roll against the printed value. A Wraithguard
    unit near a friendly Aeldari Psyker was shown Ld 6+ and graded on 8+.

    `penalty` is a modifier some rule imposes on the test itself - Seer
    Council's Presentiment of Dread prints "must take a Battle-shock test,
    subtracting 1 from that test". Applied to the ROLL rather than the
    threshold so the log can report both the dice and what they became."""
    threshold = leadership_threshold(squad, all_tokens)
    if threshold is None:
        return False
    return sum(rolls) - penalty >= threshold
