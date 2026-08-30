"""Aspect Host Stratagem: Doom Inescapable (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Aspect Host.md):
  WHEN:   Your Shooting phase.
  TARGET: One AVATAR OF KHAINE model from your army that has not been selected
          to shoot this phase.
  EFFECT: Until the end of the phase, your model's Wailing Doom ranged weapon
          has a Range characteristic of 18" and a Damage characteristic of 8.
  RESTRICTIONS: none printed.

THE FIRST RULE IN THIS ENGINE THAT SETS A RANGE RATHER THAN ADDING TO IT, and
that is why game/weapon_range.py changed. Its docstring said "THE TERMS ADD" -
true of all three sources it had, each of them +6" - so an override had nowhere
to go. It now folds an OVERRIDE that wins over the sum, the way
game/coldstar.py's effective_movement_in() already handles a Move override
beside its bonuses.

AND THE PRINTED RANGE IS 12", NOT 24" - measured, after I had assumed
otherwise. So 18" is a LENGTHENING here, and "+6"" would coincidentally give
the same answer TODAY. That coincidence is exactly why it is still written as
an override: the moment any of the three existing +6" sources applies to the
same weapon, a bonus would read 24" where the card says 18". The two readings
are pinned apart in the test by stacking a bonus source on top.

ITS HALF-RANGE MOVES WITH IT, for free: half_range_in() is defined as half of
effective_range_in(), which is the whole substance of that extraction. [MELTA]
and [RAPID FIRE X] therefore measure 9" instead of 12" while this is up - not
a case that arises today (the Wailing Doom prints neither keyword), and true by
construction rather than by a second edit.

DAMAGE 8 IS AN OVERRIDE TOO, NOT A MAXIMUM. The printed Damage is D6+2, a
NOTATION - so this is the one place where the notation has to be CLEARED as
well as the number set. Leaving it would make `damage` a preview placeholder
that the rolled value overwrites, which is exactly the trap
game/hand_of_asuryan.py records for its own Damage override.

MATCHED BY WEAPON CLASS, not by name string: "your model's Wailing Doom RANGED
weapon" - the Avatar also carries two MELEE Wailing Doom rows (Strike and
Sweep), and a name match on "Wailing Doom" would catch all three.

IDEMPOTENT. Bought twice in a phase it must not stack, and since it SETS rather
than adds, applying it twice is already harmless - stated so the next reader
does not add a guard that implies otherwise.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, detachment_gate
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING
from game.weapons import RANGED, WailingDoomProfile

DOOM_INESCAPABLE_NAME = "Doom Inescapable"
DOOM_INESCAPABLE_CP = 1

#: 'a Range characteristic of 18"' - an OVERRIDE. The printed range is 12",
#: so +6" would coincide today; see the docstring for why it is not written
#: that way.
DOOM_INESCAPABLE_RANGE_IN = 18.0

#: "and a Damage characteristic of 8".
DOOM_INESCAPABLE_DAMAGE = 8

DOOM_INESCAPABLE_KEYWORD = "AVATAR OF KHAINE"

SETTING = "ASPECT_HOST_PLAYERS"


def has_detachment(player):
    return detachment_gate.has_detachment(player, SETTING)


def is_active(squad):
    return bool(getattr(squad, "doom_inescapable_active", False))


def _is_wailing_doom_ranged(weapon):
    """The RANGED row only. Matched at the class, because the Avatar carries
    two melee rows printed under the same name."""
    return (weapon is not None
            and getattr(weapon, "weapon_type", None) == RANGED
            and isinstance(weapon, WailingDoomProfile))


def range_override_in(model, weapon):
    """Read by game/weapon_range.py. None means "no opinion", which is what an
    override must return whenever it does not apply - a number would silently
    win over every bonus."""
    if not _is_wailing_doom_ranged(weapon):
        return None
    if not is_active(getattr(model, "squad", None)):
        return None
    return DOOM_INESCAPABLE_RANGE_IN


def adjusted_weapon(weapon, squad):
    """Damage 8, on a copy. The NOTATION is cleared as well as the number -
    without that, `damage` stays a preview placeholder and the rolled D6+2
    overwrites it."""
    if weapon is None or not is_active(squad):
        return weapon
    if not _is_wailing_doom_ranged(weapon):
        return weapon
    import copy
    out = copy.copy(weapon)
    out.damage = DOOM_INESCAPABLE_DAMAGE
    out.damage_notation = None
    return out


def eligible_unit(squad):
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return unit_has_datasheet_keyword(squad, DOOM_INESCAPABLE_KEYWORD)


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.doom_inescapable_active = False


class DoomInescapableController:
    """A Shooting-phase panel button."""

    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=DOOM_INESCAPABLE_NAME, cp_cost=DOOM_INESCAPABLE_CP,
            effect=self._grant,
        )

    def panel_label(self, squad):
        return ('%s (%d CP) - the Wailing Doom becomes %g" Damage %d'
                % (DOOM_INESCAPABLE_NAME, DOOM_INESCAPABLE_CP,
                   DOOM_INESCAPABLE_RANGE_IN, DOOM_INESCAPABLE_DAMAGE))

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False               # "YOUR Shooting phase"
        if is_active(squad):
            return False
        if not eligible_unit(squad):
            return False
        if self.shooting_controller is not None \
                and self.shooting_controller.active_squad is squad:
            return False               # "has not been selected to shoot"
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.doom_inescapable_active = True
            if self.game_log is not None:
                self.game_log.add(
                    '%s: %s\'s Wailing Doom is %g" Damage %d this phase.'
                    % (DOOM_INESCAPABLE_NAME, squad.name,
                       DOOM_INESCAPABLE_RANGE_IN, DOOM_INESCAPABLE_DAMAGE))
