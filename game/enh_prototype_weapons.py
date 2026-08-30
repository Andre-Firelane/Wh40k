"""Three Experimental Prototype Cadre Enhancements, one mechanism: an upgraded
version of one named weapon the bearer already carries.

RULES (verbatim, rules/tau_empire/detachments/Experimental Prototype Cadre.md):
  Thermoneutronic Projector (15 pts)
    BATTLESUIT model only. In the Declare Battle Formations step, select one of
    this model's T'au Flamer weapons. That weapon's attacks have:
      +2 S ; +1 AP and D.

  Plasma Accelerator Rifle (20 pts)
    BATTLESUIT model only. In the Declare Battle Formations step, select one of
    this model's Plasma Rifle weapons. That weapon's attacks have:
      +2 S ; +1 A, AP and D.

  Supernova Launcher (15 pts)
    BATTLESUIT model only. In the Declare Battle Formations step, select one of
    this model's Airbursting Fragmentation Projector weapons. That weapon's
    attacks have:
      +3 S ; +1 AP and D.

WHY ALL THREE LIVE HERE
-----------------------
One shape, three rows of numbers: same bearer restriction, same timing, same
"pick one of this model's <named weapon>" and the same four characteristics.
Three files would be three copies of the weapon-matching and the timing, whose
only differences are in a table - which is what UPGRADES below is.

"BATTLESUIT model only", printed WITHOUT the T'AU EMPIRE qualifier the other
Enhancements carry, and without CHARACTER. Kept as printed (the restriction
lives in game/enhancements.py's registry, like every other bearer line): the
effect names one of the bearer's own weapon rows, so a non-character battlesuit
bearing one is a legal build and there is no reason to invent a narrower rule.

WHICH WEAPON, AND WHY THERE IS NOTHING TO CHOOSE
--------------------------------------------------
"Select ONE of this model's T'au Flamer weapons" is a choice only when the
model carries more than one - and when it does, every candidate is an instance
of the SAME WeaponProfile class with the same printed characteristics, so every
possible choice produces the same board. Offering a prompt whose options are
indistinguishable is the Fehlerklasse-5 mistake this repo keeps out, so the
first match is taken and the equivalence is written down here rather than left
to look like a shortcut.

MATCHED BY PROFILE CLASS, NOT BY NAME. A weapon row's `name` is free text; its
class is its identity, which is how game/sprites.py's printed-loadout lookup
settled the same question. Today the two readings coincide exactly:
TwinTauFlamerProfile, TwinPlasmaRifleProfile and
HighIntensityPlasmaRifleProfile are all DIRECT WeaponProfile subclasses rather
than subclasses of the three named here, so "a T'au Flamer weapon" does not
catch a twin or a high-intensity variant either way. That coincidence is pinned
in the tests, because a future refactor that made one of them a subclass would
silently widen all three Enhancements.

APPLIED IN PLACE, ONCE, AT THE PRINTED MOMENT
----------------------------------------------
Unlike every other Enhancement here this one is not a conditional adjuster in
the shooting chain: it is a permanent change to one weapon, decided before the
battle. build_squad() gives every model its own WeaponProfile instances (this
repo's standing rule - effects copy rather than mutate the shared class
instance), so writing the new numbers onto that one instance touches nothing
else.

Applied from rule 03.01's Declare Battle Formations step, which is the printed
timing, and made IDEMPOTENT (a marker on the upgraded weapon) so that a second
pass - a reloaded scene, a test that calls it twice - cannot stack +2 S twice.

"+1 AP" IS AN IMPROVEMENT, SO ap - 1. AP is stored negative here; the same
arithmetic game/fate_inescapable.py and game/aux_experimental_modifications.py
both write out.

A NAMED, MEASURED LIMITATION: THE PREDEFINED LIST HAS NO BEARER
-----------------------------------------------------------------
Measured across the built T'au list, no model carries a T'au Flamer, a Plasma
Rifle or an Airbursting Fragmentation Projector: the Crisis Starscythes' three
flamers are all traded for burst cannons by that list, Crisis Fireknife
Battlesuits (the only Plasma Rifle datasheet) are not fielded, and no T'au
datasheet in this engine has an Airbursting Fragmentation Projector at all. So
all three of these are inert in the predefined army, exactly the way Death
Guard's Signal Pox is - built, tested and with nothing to attach to. Said
plainly rather than fixed by rewriting the user's army list.
"""

from game import enhancements
from game.weapons import (AirburstingFragmentationProjectorProfile, PlasmaRifleProfile,
                          TauFlamerProfile)

THERMONEUTRONIC_PROJECTOR = "Thermoneutronic Projector"
PLASMA_ACCELERATOR_RIFLE = "Plasma Accelerator Rifle"
SUPERNOVA_LAUNCHER = "Supernova Launcher"

# Marker written onto an upgraded weapon instance so a second pass is a no-op.
UPGRADED_ATTR = "prototype_weapon_upgrade"


class WeaponUpgrade:
    """One row of the table: which weapon, and by how much."""

    def __init__(self, enhancement, weapon_cls, strength=0, attacks=0, ap=0, damage=0):
        self.enhancement = enhancement
        self.weapon_cls = weapon_cls
        self.strength = strength
        self.attacks = attacks
        self.ap = ap            # printed "+N AP" - an IMPROVEMENT, applied as ap - N
        self.damage = damage


UPGRADES = (
    WeaponUpgrade(THERMONEUTRONIC_PROJECTOR, TauFlamerProfile,
                  strength=2, ap=1, damage=1),
    WeaponUpgrade(PLASMA_ACCELERATOR_RIFLE, PlasmaRifleProfile,
                  strength=2, attacks=1, ap=1, damage=1),
    WeaponUpgrade(SUPERNOVA_LAUNCHER, AirburstingFragmentationProjectorProfile,
                  strength=3, ap=1, damage=1),
)


def upgrade_for(name):
    for upgrade in UPGRADES:
        if upgrade.enhancement == name:
            return upgrade
    raise KeyError(f"No prototype weapon upgrade named {name!r}.")


def candidate_weapons(model, upgrade):
    """"one of this model's <named> weapons" - matched by profile CLASS, and
    exactly that class, not its subclasses. See the module docstring."""
    if model is None:
        return []
    return [w for w in getattr(model, "weapons", ()) or () if type(w) is upgrade.weapon_cls]


def is_upgraded(weapon):
    return getattr(weapon, UPGRADED_ATTR, None) is not None


def apply_to_model(model, name):
    """Upgrade the first matching weapon of `model`, or return None.

    Idempotent: a weapon already carrying the marker is left alone and None is
    returned, so a second Declare Battle Formations pass cannot stack it."""
    upgrade = upgrade_for(name)
    for weapon in candidate_weapons(model, upgrade):
        if is_upgraded(weapon):
            return None
        weapon.strength += upgrade.strength
        weapon.attacks += upgrade.attacks
        weapon.ap -= upgrade.ap          # "+1 AP" improves; AP is stored negative
        weapon.damage += upgrade.damage
        setattr(weapon, UPGRADED_ATTR, name)
        return weapon
    return None


def apply_to_squad(squad, game_log=None):
    """Apply every prototype weapon Enhancement borne in `squad`.

    Returns [(model, weapon, enhancement name), ...] for what actually changed
    - a list rather than a count, because a rule that silently upgrades nothing
    (no matching weapon on the bearer) is exactly the case that has to be
    reportable. See the named limitation in the module docstring."""
    changed = []
    for upgrade in UPGRADES:
        if not enhancements.is_active(squad, upgrade.enhancement):
            continue
        for model in enhancements.bearer_models(squad, upgrade.enhancement):
            weapon = apply_to_model(model, upgrade.enhancement)
            if weapon is not None:
                changed.append((model, weapon, upgrade.enhancement))
                if game_log is not None:
                    game_log.add(
                        f"{squad.owner}: {model.profile.name}'s {weapon.name} is upgraded by "
                        f"the {upgrade.enhancement} Enhancement "
                        f"(S{weapon.strength}, AP{weapon.ap}, D{weapon.damage}).")
            elif game_log is not None:
                game_log.add(
                    f"{squad.owner}: {model.profile.name} carries the {upgrade.enhancement} "
                    f"Enhancement but has no {upgrade.weapon_cls.name} to upgrade.",
                    file_only=True)
    return changed


def apply_all(squads, game_log=None):
    """The Declare Battle Formations pass over a whole army."""
    changed = []
    for squad in squads or ():
        changed.extend(apply_to_squad(squad, game_log=game_log))
    return changed
