""""The Stars Are Right" - Orikan The Diviner's once-per-battle (Necrons).

RULE (printed, word for word):
  "Once per battle, at the start of the Fight phase, this model can use this
   ability. If it does, until the end of the phase, triple the Attacks and
   Strength characteristics of this model's Staff of Tomorrow and every
   successful Wound roll made for this model's attacks scores a Critical
   Wound."

TWO EFFECTS, TWO SEAMS, and they are asked at different places on purpose.

1. TRIPLE ATTACKS AND STRENGTH -> FightController._adjusted_weapon().
   That is the chain every other "this weapon is different for a moment"
   grant already sits in, and it hands out a COPY, which is what keeps the
   printed profile from being mutated (a WeaponProfile subclass is a shared
   class object - this repo's standing rule).

   "TRIPLE" IS A MULTIPLIER, NOT AN ADDITION, and that is the whole reason it
   is worth writing down: A2 S4 becomes A6 S12, which crosses two Toughness
   boundaries at once. A test that only checked "the mark is set" would pass
   with the arithmetic wrong.

   IT NAMES THE WEAPON. "this model's Staff of Tomorrow" - so the grant is
   keyed on the profile class, not on "every melee weapon this model has".
   Orikan carries exactly one weapon today, which is precisely why the check
   has to be written rather than assumed: it would be invisible until he
   gained a second.

2. EVERY SUCCESSFUL WOUND IS A CRITICAL WOUND -> the crit-wound threshold.
   Rule 05.02's default is "an unmodified 6", and 24.03's [ANTI-X Y+] lowers
   it. This clause does not lower it to a number at all - it says every
   SUCCESS counts - so it is expressed as "the critical threshold IS the
   wound threshold", which is exactly what that sentence means once
   _resolve_roll() has both numbers in hand.

   THIS MODEL'S ATTACKS, not the unit's. Orikan is a SUPPORT model who spends
   the battle attached to Immortals or Necron Warriors, so a unit-wide reading
   would hand ten bodyguards auto-crits. The per-MODEL check is what stops
   that, and it is why the flag is read off the attacking model rather than
   off the squad.

ONCE PER BATTLE, per bearer model, and the ledger is NOT cleared on any phase
or turn boundary - "once per battle" is the one duration in this engine that
outlives everything else. Its neighbours (Root of Honour, the Resurrection
Orb) keep theirs the same way.
"""

from game import ai_mode, per_unit_offer
from game.weapons import StaffOfTomorrowProfile

#: "triple the Attacks and Strength characteristics".
MULTIPLIER = 3

LABEL = "The Stars Are Right"


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def bearers(squad):
    """The models that print the ability - a per-MODEL question, see above."""
    return [m for m in _living(squad)
            if getattr(m.profile, "the_stars_are_right", False)]


def is_active(model):
    """Whether THIS model is riding the ability right now."""
    return bool(getattr(model, "stars_are_right_active", False))


def adjusted_weapon(weapon, model):
    """The first effect. Returns `weapon` untouched unless this model is
    active AND the weapon is the one the rule names."""
    if weapon is None or not is_active(model):
        return weapon
    if not isinstance(weapon, StaffOfTomorrowProfile):
        return weapon
    import copy
    out = copy.copy(weapon)
    out.attacks = weapon.attacks * MULTIPLIER
    out.strength = weapon.strength * MULTIPLIER
    return out


def crit_wound_threshold(model, wound_threshold, default_crit):
    """The second effect. "Every successful Wound roll scores a Critical
    Wound" is, in this engine's terms, a critical threshold equal to the
    WOUND threshold - so a roll that wounds also crits, and one that does not
    still does neither.

    Returns the BETTER (lower) of the two, so an [ANTI-X] weapon that already
    crits on a 4+ against this target is never made worse by the grant."""
    if not is_active(model) or wound_threshold is None:
        return default_crit
    return min(default_crit, wound_threshold)


class TheStarsAreRightController:
    """The once-per-battle offer at the start of the Fight phase."""

    def __init__(self, decision_manager=None, game_log=None, auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._used = set()

    def can_use(self, squad):
        return any(id(m) not in self._used for m in bearers(squad))

    def offer_at_start_of_fight_phase(self, squads):
        """"at the start of THE Fight phase" - bare, not "your Fight phase".
        The Fight phase is shared (12.04), so it is offered to whoever owns a
        bearer, the same reading game/counteroffensive.py spells out.

        EVERY eligible bearer gets its OWN offer, chained through
        game/per_unit_offer.py. This is "this model can use this ability", not
        "choose one of several units" - the difference game/unit_choice_offer.py
        exists to keep apart, and the wrong code for the two looks the same. It
        cannot bite on a shipped roster (Orikan is an EPIC HERO, so there is
        only ever one of him) and it is written correctly anyway, because the
        shape is what the next carrier inherits."""
        eligible = [s for s in sorted(squads, key=lambda s: s.name)
                    if self.can_use(s)]
        auto = [s for s in eligible if s.owner in self.auto_players]
        for squad in auto:
            # Deterministic for the AI: tripling A and S for a phase is
            # strictly better than holding a once-per-battle ability that only
            # ever triggers in the Fight phase, and Orikan is only in one when
            # something already reached him.
            self._use(squad)
        asked = [s for s in eligible if s.owner not in self.auto_players]
        if not asked or self.decision_manager is None:
            for squad in asked:
                self._use(squad)
            return bool(eligible)
        per_unit_offer.offer_each(
            self.decision_manager, asked, self.can_use,
            lambda s: ("%s: The Stars Are Right - triple the Staff of Tomorrow's "
                       "Attacks and Strength this phase, and make every successful "
                       "Wound a Critical Wound? (once per battle)" % s.name),
            lambda s: [("Use it", lambda s=s: self._use(s)), ("Save it", None)],
        )
        return True

    def _use(self, squad):
        used = []
        for model in bearers(squad):
            if id(model) in self._used:
                continue
            self._used.add(id(model))
            model.stars_are_right_active = True
            used.append(model)
        if used and self.game_log:
            self.game_log.add(
                "%s uses The Stars Are Right: the Staff of Tomorrow strikes at "
                "A%d S%d and every successful Wound roll is critical this phase."
                % (squad.name,
                   StaffOfTomorrowProfile.attacks * MULTIPLIER,
                   StaffOfTomorrowProfile.strength * MULTIPLIER))
        return bool(used)

    def reset_phase(self, squads=()):
        """"Until the end of the phase" - the ACTIVE mark clears, the
        once-per-battle ledger deliberately does not."""
        for squad in squads or ():
            for model in getattr(squad, "models", ()) or ():
                if getattr(model, "stars_are_right_active", False):
                    model.stars_are_right_active = False
