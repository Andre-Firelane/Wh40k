"""Illuminor Szeras's "Mechanical Augmentation" and "Atomic Energy Manipulator".

RULES (printed, word for word):

  Mechanical Augmentation (Aura): "While a friendly NECRONS BATTLELINE unit is
  within 3" of this model, each time a model in that unit makes an attack,
  improve the Armour Penetration characteristic of that attack by 1, and each
  time an attack targets that unit, worsen the Armour Penetration
  characteristic of that attack by 1."

  Atomic Energy Manipulator: "At the end of the Fight phase, if this model
  destroyed one or more models this phase, until the end of the battle, add 3"
  to the range of its Mechanical Augmentation ability (to a maximum of 12")."

ONE AURA, TWO DIRECTIONS, and that is unusual enough to spell out: the same 3"
bubble makes its unit's attacks sharper AND incoming attacks blunter. They are
two separate clauses of one sentence, so both live here and both read the same
range.

BOTH HALVES GO IN THE ADJUSTER CHAIN, not in the save step. That is not a
shortcut - it is where AP is actually decided: the Save roll reads the AP off
the weapon the chain returns (the same reasoning game/crystalline_targeting.py
records). The chain is also the only place that has BOTH squads and the token
list in hand, which the 3" measurement needs.

  * attacker half: the ATTACKING squad is the augmented one.
  * defender half: the TARGET squad is the augmented one.

"IMPROVE BY 1" MEANS MORE NEGATIVE, "worsen" means less - the same arithmetic
game/crit_ap.py and game/ramshackle.py already use, and worsening is clamped at
0 exactly as Ramshackle clamps it (AP cannot become a bonus).

THE GROWING RANGE is the first ability in this engine whose numbers change over
the course of a battle. Two decisions worth recording:

  * The growth is stored on the TOKEN, never on the profile. UnitProfile
    subclasses are shared class objects, and writing to one would silently
    grow every other Szeras built from the same datasheet - CLAUDE.md flags
    that exact trap.
  * "if THIS MODEL destroyed one or more models this phase" needs kill
    attribution, which this engine does not have. It does not need it here:
    Szeras has no LEADER line, so his unit is always exactly one model, and
    "his unit killed something" and "he killed something" are the same
    statement. Recorded because the shortcut stops being valid the moment a
    second carrier of this ability can be attached to anything.
"""

import copy

BATTLELINE_KEYWORD = "BATTLELINE"
AUGMENTATION_AP_STEP = 1


def _augmenting_models(all_tokens, owner):
    """Every living model with the aura, on `owner`'s side."""
    return [t for t in all_tokens or ()
            if getattr(t, "squad", None) is not None
            and t.squad.owner == owner
            and not t.is_dead()
            and getattr(t.profile, "mechanical_augmentation", 0)]


def current_range_in(model):
    """This model's aura range right now: the printed 3" plus whatever Atomic
    Energy Manipulator has added, capped at the printed maximum."""
    profile = getattr(model, "profile", None)
    base = getattr(profile, "mechanical_augmentation", 0) or 0
    if not base:
        return 0
    ceiling = getattr(profile, "mechanical_augmentation_max", 0) or base
    return min(ceiling, base + int(getattr(model, "mechanical_augmentation_bonus", 0) or 0))


def _is_battleline(squad):
    """"a friendly NECRONS BATTLELINE unit". BATTLELINE is a datasheet keyword
    rather than a UnitProfile flag, so it is read off the datasheet - the same
    place attached_units.unit_has_datasheet_keyword() looks."""
    sheet = getattr(squad, "datasheet", None)
    if sheet is None:
        return False
    return BATTLELINE_KEYWORD in (getattr(sheet, "keywords", ()) or ())


def is_augmented(squad, all_tokens=()):
    """Whether `squad` is currently inside a friendly Szeras's aura."""
    if squad is None or not _is_battleline(squad):
        return False
    if not any(not m.is_dead() for m in squad.models):
        return False
    for model in _augmenting_models(all_tokens, squad.owner):
        if model.squad is squad:
            continue  # "a friendly ... unit", i.e. not the bearer's own
        reach = current_range_in(model)
        if reach and squad.min_distance_to(model.squad) <= reach:
            return True
    return False


def adjusted_weapon(weapon, attacking_squad, target_squad, all_tokens=()):
    """The weapon after both halves of the aura.

    Applied in one place so the two clauses cannot disagree about the range,
    and so an attack made BY an augmented unit AGAINST another augmented unit
    nets out to no change - which is what the printed text says happens."""
    if weapon is None:
        return weapon
    ap = weapon.ap
    if is_augmented(attacking_squad, all_tokens):
        ap -= AUGMENTATION_AP_STEP          # "improve" - more negative
    if is_augmented(target_squad, all_tokens):
        ap = min(0, ap + AUGMENTATION_AP_STEP)   # "worsen", clamped like Ramshackle
    if ap == weapon.ap:
        return weapon
    adjusted = copy.copy(weapon)             # never mutate the shared instance
    adjusted.ap = ap
    return adjusted


class AtomicEnergyManipulatorController:
    """The growth half. Fed destroyed models as they are swept, resolved at the
    end of the Fight phase."""

    def __init__(self, game_log=None):
        self.game_log = game_log
        self._credited = set()   # id(szeras model) - killed something this phase

    def notify_destroyed(self, models, attacking_squad):
        """Called from main.py's per-frame death sweep with whatever
        GameState.remove_dead_models() just removed and the unit that was
        fighting at the time.

        Credited to the SQUAD's models rather than to a specific killer, which
        is exact here for the reason this module's docstring gives: Szeras is
        always a one-model unit."""
        if not models or attacking_squad is None:
            return
        for model in attacking_squad.models:
            if getattr(model.profile, "atomic_energy_manipulator", 0) and not model.is_dead():
                self._credited.add(id(model))

    def resolve_end_of_fight_phase(self, squads=()):
        """"at the end of the Fight phase... add 3" ... to a maximum of 12"".

        Returns the models that actually grew, for tests and callers that want
        to report it."""
        grown = []
        for squad in squads or ():
            for model in squad.models:
                step = getattr(model.profile, "atomic_energy_manipulator", 0) or 0
                if not step or id(model) not in self._credited or model.is_dead():
                    continue
                before = current_range_in(model)
                model.mechanical_augmentation_bonus = (
                    int(getattr(model, "mechanical_augmentation_bonus", 0) or 0) + step)
                after = current_range_in(model)
                if after != before and self.game_log is not None:
                    self.game_log.add(
                        f"Atomic Energy Manipulator: {model.profile.name} destroyed models "
                        f"this phase - Mechanical Augmentation now reaches {after:g}\".")
                if after != before:
                    grown.append(model)
        self._credited.clear()
        return grown

    def reset_phase(self):
        """The credit is per PHASE, so it clears even when nothing grew."""
        self._credited.clear()
