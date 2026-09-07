"""War Walkers' "Crystalline Targeting".

RULE (printed, word for word):
  "In your Shooting phase, after this unit has shot, select one enemy unit hit
   by one or more of those attacks. Until the end of the phase, each time a
   friendly AELDARI unit makes an attack that targets that enemy unit, improve
   the Armour Penetration characteristic of that attack by 1. Each unit can
   only be selected for this ability once per turn."

THE SAME SHAPE AS SHROUD RUNNERS' TARGET ACQUISITION, which is the useful thing
to say about it: the trigger is ShootingController.on_squad_finished_shooting
(the seventh listener on that hook), and the effect is a MARK ON THE TARGET
rather than a grant to the shooter - "each time a friendly AELDARI unit makes
an attack that targets that enemy unit", so it helps the whole army, not the
War Walkers.

TWO DIFFERENCES from Target Acquisition, both in the printed text:
  * no weapon qualifier - any of those attacks will do, so it needs none of the
    per-weapon hit record that one required;
  * "each unit can only be selected for this ability ONCE PER TURN", which is a
    limit on the TARGET, not on the War Walkers. So a second War Walker unit
    may still use its own ability - just not on a unit already picked this
    turn. Held per marked squad for that reason, and cleared per turn rather
    than per phase, while the AP effect itself expires at the end of the phase.
    Those are two different lifetimes on purpose.

"IMPROVE THE ARMOUR PENETRATION BY 1" means a MORE negative AP - see
game/crit_ap.py, which does the same arithmetic for Fate Inescapable. It is
applied on a copy of the weapon in the adjuster chain, never by mutating the
shared profile.

THE ATTACKER MUST BE AELDARI, and that is read off the datasheet keyword line
via attached_units.unit_has_datasheet_keyword() - the same route Whispering Web
and Doom take for their own army-wide clauses.
"""

from game import attached_units

CRYSTALLINE_TARGETING_AP_BONUS = 1
CRYSTALLINE_TARGETING_LABEL = "Crystalline Targeting"


def applies(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "crystalline_targeting", False)
               for m in squad.models if not m.is_dead())


def _is_aeldari(squad):
    return attached_units.unit_has_datasheet_keyword(squad, "AELDARI")


class CrystallineTargetingController:
    """Wired into ShootingController.on_squad_finished_shooting in main.py, and
    read back by the AP adjuster in the same controller."""

    def __init__(self, decision_manager=None, game_log=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self._marked = set()          # id(squad), "until the end of the phase"
        self._used_this_turn = set()  # id(squad), "once per turn" - per TARGET

    # -- lifetimes (two of them, deliberately) ----------------------------
    def reset_phase(self):
        """The AP effect: "until the end of the phase"."""
        self._marked = set()

    def reset_turn(self):
        """The selection limit: "each unit can only be selected... once per
        turn". Longer-lived than the effect, which is why it is separate."""
        self._used_this_turn = set()

    def is_marked(self, squad):
        return squad is not None and id(squad) in self._marked

    def ap_bonus(self, attacker_squad, target_squad):
        """How much to improve this attack's AP by - 0 unless the target is
        marked AND the attacker is AELDARI."""
        if not self.is_marked(target_squad) or not _is_aeldari(attacker_squad):
            return 0
        return CRYSTALLINE_TARGETING_AP_BONUS

    # -- the trigger ------------------------------------------------------
    def offer_after_shooting(self, squad, hit_squads):
        if not applies(squad):
            return
        candidates = [s for s in hit_squads if id(s) not in self._used_this_turn]
        if not candidates:
            return
        if len(candidates) == 1 or self.decision_manager is None:
            self._mark(candidates[0], squad)
            return
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: {CRYSTALLINE_TARGETING_LABEL} - which unit is easier to hurt?",
            [(target.name, (lambda t=target: self._mark(t, squad)), target) for target in candidates],
        )

    def _mark(self, target, squad):
        self._marked.add(id(target))
        self._used_this_turn.add(id(target))
        if self.game_log is not None:
            self.game_log.add(
                f"{squad.owner}: {CRYSTALLINE_TARGETING_LABEL} - AELDARI attacks against "
                f"{target.name} improve their AP by {CRYSTALLINE_TARGETING_AP_BONUS} until "
                "the end of the phase."
            )


def adjusted_weapon(weapon, controller, attacker_squad, target_squad):
    """A copy with the AP improved, or the weapon untouched.

    Never mutates the shared profile - the convention every adjuster in
    game/shooting.py's chain follows, and the reason each one copies."""
    if controller is None or weapon is None:
        return weapon
    bonus = controller.ap_bonus(attacker_squad, target_squad)
    if not bonus:
        return weapon
    import copy
    adjusted = copy.copy(weapon)
    adjusted.ap = weapon.ap - bonus
    return adjusted
