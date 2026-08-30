"""When a CRITICAL WOUND resolves its Save roll at a different Armour
Penetration than the rest of its group - the single place the wound step asks.

Extracted from game/crack_shot.py, which owned it while Cadre Fireblade's Crack
Shot was the only source. Seer Council's Fate Inescapable is the second, and a
module named after one datasheet's ability is the wrong home for another
faction's stratagem. Eighth extraction of this shape, after
game/invulnerable_save.py, game/crit_hit.py, game/damage_reroll.py,
game/damage_estimate.py, game/unmodified_six.py, game/psychic_mark.py and
game/roll_bonus.py, and for the same two reasons each time: a second foreign
consumer, and one call site to update.

WHY IT NEEDS ITS OWN SAVE SUB-STEP AT ALL, rather than an adjusted weapon for
the whole group like starscythe_adjusted_weapon(): both sources change the AP
only for the wounds that actually rolled a CRITICAL, and a non-critical wound
from the very same attack still uses the printed AP. One group, two APs - which
this engine's batched Save roll cannot express in a single roll. So the critical
share is pulled out and rolled separately; see game/shooting.py's
_begin_crit_ap_save() and its caller.

THE TWO SOURCES DIFFER IN ARITHMETIC, which is why this returns an adjusted
WEAPON rather than a number:
  * Crack Shot OVERRIDES the AP to a flat -3.
  * Fate Inescapable IMPROVES it by 1.

They can never both apply in practice - one is a T'au datasheet ability, the
other an Aeldari stratagem, and rule 19.01 does not merge factions. If they ever
could, Crack Shot's override is applied first and the improvement on top, which
is the order that treats an override as the stronger statement. Noted rather
than left to be discovered.

RANGED ONLY, and that comes from the sources: Crack Shot prints "makes a ranged
attack", and Fate Inescapable's EFFECT is about "ranged weapons equipped by
models in your unit". game/fight.py therefore never asks.
"""

from game.crack_shot import crack_shot_adjusted_weapon
from game.fate_inescapable import applies as fate_inescapable_applies
from game.fate_inescapable import fate_adjusted_weapon
from game.weapons import RANGED


def sources(weapon, shooter_model, squad):
    """Which crit-AP sources are live for this weapon group, in application
    order. Empty means the critical wounds stay in the group's normal Save
    roll."""
    if weapon is None or weapon.weapon_type != RANGED:
        return []
    out = []
    profile = getattr(shooter_model, "profile", None)
    if profile is not None and getattr(profile, "crack_shot", False):
        out.append("Crack Shot")
    if fate_inescapable_applies(squad):
        out.append("Fate Inescapable")
    return out


def applies(weapon, shooter_model, squad):
    return bool(sources(weapon, shooter_model, squad))


def adjusted_weapon(weapon, shooter_model, squad):
    """The weapon the critical wounds' own Save roll resolves against."""
    adjusted = weapon
    for source in sources(weapon, shooter_model, squad):
        if source == "Crack Shot":
            adjusted = crack_shot_adjusted_weapon(adjusted)
        else:
            adjusted = fate_adjusted_weapon(adjusted)
    return adjusted


def label(weapon, shooter_model, squad):
    """What the Save roll's own label should say it is."""
    return " + ".join(sources(weapon, shooter_model, squad))
