"""When a CRITICAL WOUND is pulled out of its group's Save roll and resolved
separately - the single place both attack steps ask.

RENAMED from game/crit_ap.py at the THIRD carrier. That name described what its
first two sources CHANGE (the Armour Penetration), and Spirit Conclave's Stave
of Kurnous changes something else entirely: "on a Critical Wound, that attack
has the [PRECISION] ability". Same split, different consequence - so the module
is named after the QUESTION, which is error class 11's standing remedy.
game/crit_ap.py re-exports every name, so nothing that already asked has to
change.

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

NO LONGER RANGED ONLY, and that is what the third source cost. Crack Shot
prints "makes a ranged attack" and Fate Inescapable's EFFECT is about "ranged
weapons", so game/fight.py never asked and had no crit split at all. Stave of
Kurnous says "each time a model in that unit makes AN ATTACK", and its targets
are Wraithblades - a melee datasheet - so the ranged-only reading would have
made it nearly inert. game/fight.py therefore grew the twin, and the per-source
RANGED test moved from this module's front door into the two sources that
print it.

THE THREE SOURCES DIFFER IN KIND, not just in arithmetic:
  * Crack Shot OVERRIDES the AP to a flat -3      (ranged)
  * Fate Inescapable IMPROVES the AP by 1         (ranged)
  * Stave of Kurnous grants [PRECISION]           (either phase)
which is why this returns an adjusted WEAPON rather than a number, and why the
split is worth its own sub-step for all three.
"""

from game.crack_shot import crack_shot_adjusted_weapon
from game.fate_inescapable import applies as fate_inescapable_applies
from game.fate_inescapable import fate_adjusted_weapon
from game import enh_stave_of_kurnous
from game.enh_stave_of_kurnous import STAVE_OF_KURNOUS
from game.weapons import RANGED


def sources(weapon, shooter_model, squad):
    """Which split sources are live for this weapon group, in application
    order. Empty means the critical wounds stay in the group's normal Save
    roll.

    The RANGED test is per SOURCE rather than at the door: two of the three
    print "ranged" and the third does not."""
    if weapon is None:
        return []
    out = []
    ranged = weapon.weapon_type == RANGED
    profile = getattr(shooter_model, "profile", None)
    if ranged and profile is not None and getattr(profile, "crack_shot", False):
        out.append("Crack Shot")
    if ranged and fate_inescapable_applies(squad):
        out.append("Fate Inescapable")
    if enh_stave_of_kurnous.applies(squad):
        out.append(STAVE_OF_KURNOUS)
    return out


def applies(weapon, shooter_model, squad):
    return bool(sources(weapon, shooter_model, squad))


def adjusted_weapon(weapon, shooter_model, squad):
    """The weapon the critical wounds' own Save roll resolves against."""
    adjusted = weapon
    for source in sources(weapon, shooter_model, squad):
        if source == "Crack Shot":
            adjusted = crack_shot_adjusted_weapon(adjusted)
        elif source == STAVE_OF_KURNOUS:
            adjusted = enh_stave_of_kurnous.adjusted_weapon(adjusted)
        else:
            adjusted = fate_adjusted_weapon(adjusted)
    return adjusted


def label(weapon, shooter_model, squad):
    """What the Save roll's own label should say it is."""
    return " + ".join(sources(weapon, shooter_model, squad))
