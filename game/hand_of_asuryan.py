"""Asurmen's "Hand of Asuryan" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "Once per battle, when this model is selected to shoot, it can use this
  ability. If it does, until the end of the phase, its Bloody Twins weapon has
  a Damage characteristic of 3 and the [ANTI-INFANTRY 5+] and [DEVASTATING
  WOUNDS] abilities."

SAME SHAPE AS NOVA CHARGE, WITH ONE FEWER QUESTION
--------------------------------------------------
The Riptide's Nova Charge is once per battle, offered at the same moment
("when this model is selected to shoot"), and grants a weapon an ability until
the end of the phase - so this reuses that shape wholesale: the offer hangs off
ShootingController.start_shooting(), and the effect is an adjuster chained in
beside the others, granting on a shallow copy so the shared WeaponProfile
instance is never mutated.

The one difference is that Nova Charge asks WHICH weapon and this does not -
the rule names it ("its Bloody Twins weapon"), so there is nothing to choose
and the offer is a plain yes/no.

NOT offered on a reactive Snap Shot (Fire Overwatch, 15.08/15.09): that runs
through start_snap_shooting(), not start_shooting(), which is where this hangs
- the same deliberate exclusion Nova Charge documents for itself.

WHY THE GRANT IS PER MODEL RATHER THAN PER UNIT: "once per battle for THIS
MODEL", and Asurmen is a CHARACTER who joins a Dire Avenger squad (19.01), so
the unit around him outlives any per-unit reading of the sentence.
"""

import copy

HAND_OF_ASURYAN_WEAPON = "Bloody Twins"
HAND_OF_ASURYAN_DAMAGE = 3
HAND_OF_ASURYAN_ANTI = ("INFANTRY", 5)


def _bearers(squad):
    return [m for m in getattr(squad, "models", None) or () if getattr(m.profile, "hand_of_asuryan", False)]


def can_use(squad):
    """A living bearer that has not spent it yet. Tracked on the MODEL (see
    the module docstring), like the Riptide's Nova Charge and Flash Gitz'
    Ammo Runt."""
    return any(not m.is_dead() and not getattr(m, "hand_of_asuryan_used", False)
               for m in _bearers(squad))


def use(squad):
    """Spend it and arm the grant for the rest of the phase. Returns the model
    it was spent on, or None."""
    for model in _bearers(squad):
        if model.is_dead() or getattr(model, "hand_of_asuryan_used", False):
            continue
        model.hand_of_asuryan_used = True
        model.hand_of_asuryan_active = True
        return model
    return None


def reset_phase(squads=()):
    """"Until the end of the phase" - the GRANT expires, the once-per-battle
    spend does not. Two lifetimes, kept apart deliberately: the same split
    Nova Charge draws, and getting it wrong would either hand the ability back
    every phase or make the grant permanent."""
    for squad in squads:
        for model in _bearers(squad):
            model.hand_of_asuryan_active = False


def hand_of_asuryan_adjusted_weapon(weapon, pairs):
    """The three characteristic changes, on a shallow copy.

    Whether this group is the granted weapon is decided from its
    representative pair (pairs[0]), the simplification every adjuster in this
    codebase uses - and exact on both halves here: a group IS one weapon by
    construction (_attack_key()), and the bearer is a single CHARACTER model,
    so a group containing him contains only him.

    GRANTS rather than overwrites: a Damage already better than 3 is kept, and
    an [ANTI-X] already at or below 5+ is kept, so nothing this ability
    touches can be made worse by it."""
    if not pairs:
        return weapon
    model, _ = pairs[0]
    if not getattr(model, "hand_of_asuryan_active", False):
        return weapon
    if weapon.name != HAND_OF_ASURYAN_WEAPON:
        return weapon
    boosted = copy.copy(weapon)
    boosted.damage = max(weapon.damage, HAND_OF_ASURYAN_DAMAGE)
    boosted.devastating_wounds = True
    existing = weapon.anti
    # WeaponProfile.anti is a (keyword, threshold) tuple or a tuple of them;
    # rule 24.03 already takes the BEST (lowest) threshold where several match,
    # so simply adding this one alongside whatever was printed is correct.
    if existing is None:
        boosted.anti = HAND_OF_ASURYAN_ANTI
    elif isinstance(existing[0], str):
        boosted.anti = (existing, HAND_OF_ASURYAN_ANTI)
    else:
        boosted.anti = tuple(existing) + (HAND_OF_ASURYAN_ANTI,)
    return boosted


class HandOfAsuryanController:
    """The once-per-battle offer, made at the moment the rule names."""

    def __init__(self, decision_manager=None, game_log=None):
        self.decision_manager = decision_manager
        self.game_log = game_log

    def maybe_offer(self, squad):
        """Called from ShootingController.start_shooting(), the same hook Nova
        Charge and Ammo Runt use."""
        if self.decision_manager is None or not can_use(squad):
            return
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: Hand of Asuryan - once per battle, give Bloody Twins Damage "
            f"{HAND_OF_ASURYAN_DAMAGE}, [ANTI-INFANTRY {HAND_OF_ASURYAN_ANTI[1]}+] and "
            "[DEVASTATING WOUNDS] until the end of the phase?",
            [("Use Hand of Asuryan", lambda: self._use(squad)), ("Save it", lambda: None)],
        )

    def _use(self, squad):
        if use(squad) is not None and self.game_log is not None:
            self.game_log.add(
                f"{squad.name} uses Hand of Asuryan: Bloody Twins has Damage "
                f"{HAND_OF_ASURYAN_DAMAGE}, [ANTI-INFANTRY {HAND_OF_ASURYAN_ANTI[1]}+] and "
                "[DEVASTATING WOUNDS] until the end of the phase."
            )
