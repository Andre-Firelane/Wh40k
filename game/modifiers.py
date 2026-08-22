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
