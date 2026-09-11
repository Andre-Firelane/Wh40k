from game import icon_of_despair  # imports nothing itself
from game import plagues  # imports only game/modifiers.py, so this cannot cycle
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
    if all_tokens is not None and psychic_guidance.applies_any(squad, all_tokens):
        granted = parse_threshold(psychic_guidance.PSYCHIC_GUIDANCE_LEADERSHIP)
        if granted is not None:
            # min() rather than a replacement: the rule reads as a flat value,
            # but taking the better of the two means a unit whose printed Ld is
            # already better can never be made worse by it.
            thresholds.append(granted)
    if not thresholds:
        return None
    # The Death Guard Plague Scabrous Soulrot ("worsen the ... Leadership ...
    # by 1"). Ld is a threshold, so worsening it means a HIGHER number, and it
    # is applied AFTER the min() rather than to each model: the rule worsens
    # the characteristic of every model in the unit, so the easiest threshold
    # present moves by 1 either way, and doing it here keeps Psychic
    # Guidance's "never make it worse than printed" min() meaning what it says.
    # The Death Guard wargear "icon of despair" is a second -1 Ld from an
    # enemy, and it stacks with the Plague above: two different sources, both
    # worsening the same characteristic, and the printed text of neither
    # excludes the other.
    # Auxiliary Cadre's Admired Leader Enhancement is the only IMPROVEMENT in
    # this sum: "+1 Ld" is a better characteristic, and Ld is an N+ threshold
    # here, so it SUBTRACTS. Applied alongside the two penalties rather than
    # before the min(), for the same reason they are: the rule changes the
    # characteristic of every model in the unit, so the easiest threshold
    # present moves by 1 either way.
    # The Silent King's own aura ("improve that unit's Leadership
    # characteristic by 1") is the SECOND improvement in this sum and
    # subtracts for the same reason Admired Leader does - a better
    # characteristic is a LOWER N+ threshold. It needs the board, because
    # its condition is a distance to Szarekh; without all_tokens it
    # degrades to the printed value, which is the same right degradation
    # Psychic Guidance above already takes.
    from game import enh_admired_leader, silent_king_leadership
    return (min(thresholds)
            + plagues.leadership_penalty(squad)
            + icon_of_despair.leadership_penalty(squad, all_tokens or ())
            + enh_admired_leader.leadership_bonus(squad)
            - silent_king_leadership.leadership_bonus(squad, all_tokens or ()))


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
