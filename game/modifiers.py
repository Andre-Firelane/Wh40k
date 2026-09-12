from dataclasses import dataclass


@dataclass(frozen=True)
class Modifier:
    """A single temporary adjustment to a stat threshold or die roll, with a
    human-readable source so the game log/UI can say *why* (e.g. "+1
    (Benefit of Cover)"). Positive amounts worsen a threshold (higher number
    needed), negative amounts improve it - matches how thresholds like BS/WS
    work in this engine (lower is better, so "worse" means "add")."""

    amount: int
    source: str


def apply_modifiers(base_value, modifiers):
    """Sum every modifier's amount onto base_value. None-safe: a
    characteristic of "-" (no such stat, e.g. WS on a Vehicle) parses to
    None and stays None regardless of modifiers."""
    if base_value is None:
        return None
    return base_value + sum(m.amount for m in modifiers)


def describe_modifiers(modifiers):
    """Human-readable summary for logs, e.g. '+1 (Benefit of Cover)'."""
    return ", ".join(f"{m.amount:+d} ({m.source})" for m in modifiers)


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
    harmful ones, each group in the order given - the order the user asked for."""
    shown = []
    for mod in modifiers or ():
        if isinstance(mod, Modifier):
            delta, source = (-mod.amount if lower_is_better else mod.amount), mod.source
        else:
            delta, source = mod
        if delta:
            shown.append((delta, source))
    return tuple([m for m in shown if m[0] > 0] + [m for m in shown if m[0] < 0])
