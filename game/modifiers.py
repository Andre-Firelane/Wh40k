"""Hit and Wound roll modifiers, and the two limits every such roll obeys.

User report: "wenn etwas +1 oder -1 auf hit oder wound gibt, dann kann diese
modifikation maximal 1 vom ursprungswert abweichen. es stackt also nicht ...
aber modifikatoren koennen sich gegenseitig neutralisieren ... 3+ kann also
maximal zu 2+ oder 4+ werden" and "1+ gibt es nicht, das beste moegliche ist
immer 2+, 1 ist immer fehlschlag". And, the half that decides the design:
"das betrifft hit und wound roll, aber modifikationen auf werte zb. Ballistic
Skill werden extra behandelt. Zb Cover".

So there are TWO kinds of Modifier, and they are summed differently:

  * ROLL - "add 1 to the Hit roll", "subtract 1 from the Wound roll", "+1 to
    hit rolls". All of these are added up FIRST and the net result is then
    capped at +/-1, so they cancel against each other (+1 and -2 is -1) but
    never stack past one step (-1 and -1 is still -1).
  * CHARACTERISTIC - "improve the Ballistic Skill characteristic of that
    attack by 1", "worsen the ... characteristic by 1" (Benefit of Cover,
    Guided, Target Uploaded, Coordinate to Engage, the Wraithlord's Psychic
    Guidance, Close-Quarters). They change the number the roll is made
    AGAINST, not the roll, so the cap does not see them.

Everything was ONE summed list before, which is why a unit with two -1 to hit
maluses was hit on a 5+ from a 3+ and a Guided +1 on a base 2+ printed
"needed 1+". The default kind is ROLL because that is what 54 of the 62
constructions in this engine print; a CHARACTERISTIC source says so at its
construction. test_roll_modifier_cap.py holds BOTH lists, so a new Modifier
anywhere in game/ fails there until someone has read its printed text and
put it on one of them.

Rules 05.01/05.02's "an unmodified 1 always fails / an unmodified 6 always
succeeds" were already honoured on the RAW die by shooting.py's
_resolve_roll(); what was missing was the threshold itself, which the dice
panel, the log and every crit rule that compares against it read."""

from dataclasses import dataclass

#: "add 1 to the Hit roll" / "subtract 1 from the Wound roll" - capped as a sum.
ROLL = "roll"
#: "improve/worsen the Ballistic Skill (Weapon Skill) characteristic by 1" -
#: moves the number the roll is made against, outside the cap.
CHARACTERISTIC = "characteristic"
MODIFIER_KINDS = (ROLL, CHARACTERISTIC)

#: The net of every ROLL modifier is capped at this many steps either way.
ROLL_MODIFIER_CAP = 1
#: "1+ gibt es nicht" - no Hit or Wound roll ever needs less than a 2.
BEST_THRESHOLD = 2
#: Shown in the dice panel and the log when the cap actually bit.
ROLL_CAP_LABEL = "roll modifiers capped at ±1"


@dataclass(frozen=True)
class Modifier:
    """A single temporary adjustment to a stat threshold or die roll, with a
    human-readable source so the game log/UI can say *why* (e.g. "+1
    (Benefit of Cover)"). Positive amounts worsen a threshold (higher number
    needed), negative amounts improve it - matches how thresholds like BS/WS
    work in this engine (lower is better, so "worse" means "add").

    `kind` says WHAT the printed rule modifies - see the module docstring.
    ROLL unless the rule names a characteristic."""

    amount: int
    source: str
    kind: str = ROLL

    def __post_init__(self):
        # A misspelt kind would otherwise fall out of BOTH sums below and
        # silently do nothing - the one failure mode worth refusing loudly.
        if self.kind not in MODIFIER_KINDS:
            raise ValueError(f"Modifier kind must be one of {MODIFIER_KINDS}, not {self.kind!r}")


def raw_roll_modifier(modifiers):
    """The plain sum of every ROLL modifier, before the cap."""
    return sum(m.amount for m in modifiers or () if m.kind == ROLL)


def net_roll_modifier(modifiers):
    """The ROLL modifiers as they actually apply: summed, so opposite ones
    cancel, then capped at +/-ROLL_MODIFIER_CAP."""
    raw = raw_roll_modifier(modifiers)
    return max(-ROLL_MODIFIER_CAP, min(ROLL_MODIFIER_CAP, raw))


def characteristic_modifier(modifiers):
    """The sum of every CHARACTERISTIC modifier - uncapped."""
    return sum(m.amount for m in modifiers or () if m.kind == CHARACTERISTIC)


def apply_modifiers(base_value, modifiers):
    """The Hit or Wound threshold `base_value` becomes under `modifiers`:
    characteristic changes in full, roll modifiers capped at +/-1 as a sum,
    and never better than 2+. None-safe: a characteristic of "-" (no such
    stat, e.g. WS on a Vehicle) parses to None and stays None regardless of
    modifiers.

    Only an upper bound on QUALITY, not on difficulty: a 6+ worsened to 7+
    stays 7+, and _resolve_roll()'s "an unmodified 6 always succeeds" is what
    still lets such a roll pass."""
    if base_value is None:
        return None
    modified = base_value + characteristic_modifier(modifiers) + net_roll_modifier(modifiers)
    return max(BEST_THRESHOLD, modified)


def _cap_correction(modifiers):
    """How far the cap moved the threshold, in threshold terms (0 when it did
    not bite)."""
    return net_roll_modifier(modifiers) - raw_roll_modifier(modifiers)


def describe_modifiers(modifiers):
    """Human-readable summary for logs, e.g. '+1 (Benefit of Cover)'. When
    the roll modifiers were capped it says so, because a log line reading
    "base 3+, +1 (A), +1 (B)" next to "needed 4+" is exactly the diagnostic
    that omits the one number in dispute."""
    text = ", ".join(f"{m.amount:+d} ({m.source})" for m in modifiers)
    if _cap_correction(modifiers):
        raw = raw_roll_modifier(modifiers)
        text += f"; roll modifiers {raw:+d} capped at {net_roll_modifier(modifiers):+d}"
    return text


def for_display(modifiers, lower_is_better=True):
    """((delta, source), ...) in PLAYER terms, for the dice panel: a positive
    delta helps whoever is rolling, a negative one hurts.

    THE SIGN IS THE WHOLE POINT. A Modifier here adjusts a THRESHOLD, where
    lower is better - Benefit of Cover is Modifier(+1, ...) and makes a hit
    HARDER, Target Uploaded is Modifier(-1, ...) and makes it easier. Printed
    as-is the panel would put a green up-arrow on cover. User: "Positive
    Modifikatoren wie +1 (Ability XY) mit grünen Pfeil nach oben / Darunter
    negative Modifikatoren wie -1 (Cover) mit rotem Pfeil nach unten" - so a
    threshold list is negated, an additive one (a Charge roll's bonuses) is
    not.

    Accepts Modifier objects or (delta, source) pairs already in roll terms.
    Zero deltas say nothing and are dropped. Helpful ones come first, then
    harmful ones, each group in the order given - the order the user asked for.

    When the +/-1 cap on ROLL modifiers bit, one more row comes LAST, after
    both groups: the correction itself ("+1 (roll modifiers capped at ±1)"
    under two -1 maluses). It is a correction of the rows above rather than
    a modifier of its own, and without it the panel would show -1, -1 beside
    a target number that moved by one."""
    shown = []
    for mod in modifiers or ():
        if isinstance(mod, Modifier):
            delta, source = (-mod.amount if lower_is_better else mod.amount), mod.source
        else:
            delta, source = mod
        if delta:
            shown.append((delta, source))
    ordered = [m for m in shown if m[0] > 0] + [m for m in shown if m[0] < 0]
    if lower_is_better:
        correction = _cap_correction([m for m in modifiers or () if isinstance(m, Modifier)])
        if correction:
            ordered.append((-correction, ROLL_CAP_LABEL))
    return tuple(ordered)
