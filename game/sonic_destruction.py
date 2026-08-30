"""The Vibro Cannon Platform's "Sonic Destruction" - a datasheet ability.

RULE (printed, word for word):
  "In your Shooting phase, each time this model makes an attack with its vibro
  cannon that targets an enemy unit, improve the Strength, Armour Penetration
  and Damage characteristics of that attack by 1 for each other friendly VIBRO
  CANNON PLATFORM model that made one or more attacks with its vibro cannon
  that also targeted that enemy unit this phase."

THE BONUS IS A COUNT, AND THE COUNT IS PER (PLATFORM, TARGET) PAIR
------------------------------------------------------------------
So this needs a ledger, and the ledger's key is the thing most easily got
wrong. It is NOT "how many platforms have shot this phase" and NOT "how many
platforms are on the board": it is how many OTHER platforms have fired their
vibro cannon AT THIS PARTICULAR TARGET this phase. Three platforms splitting
their fire across three targets give each other nothing.

  * "EACH OTHER friendly ... model" excludes the firing model itself, so the
    first platform to shoot a target always gets +0. Written as an explicit
    exclusion rather than an off-by-one on the count, because an off-by-one
    here is invisible: it would look like a working ability that is simply
    one better than it should be.
  * "IN YOUR SHOOTING PHASE" - so a reactive shot (Fire Overwatch, 15.08/09,
    which happens in the opponent's phase) neither earns the bonus nor feeds
    the ledger. The flag is passed in rather than inferred, keeping the
    reading with this module, exactly as Expert Fieldcraft does.
  * "THIS PHASE" is the lifetime, so the ledger is cleared with the shooting
    phase, not with the turn.

IMPROVE S, AP AND D BY 1 EACH. "Improve" the AP means MORE negative, the same
arithmetic game/crit_ap.py records. The adjusted weapon is a COPY - the shared
WeaponProfile instance is never mutated, which is the standing rule for every
adjuster in this engine.

WHY THE ADJUSTER CHAIN AND NOT THE WOUND STEP: the save roll reads the AP off
the weapon this returns, and the damage step reads its Damage. Both are
downstream of _adjusted_weapon(), so that is the one place all three
characteristics arrive together.
"""
import copy

from game.weapons import VibroCannonProfile

SONIC_DESTRUCTION_LABEL = "Sonic Destruction"


def is_vibro_cannon(weapon):
    """Read off the profile CLASS, not the printed name, which is free text."""
    return isinstance(weapon, VibroCannonProfile)


def has_sonic_destruction(model):
    return (model is not None and not model.is_dead()
            and getattr(model.profile, "sonic_destruction", False))


class SonicDestructionController:
    """One per battle. Remembers which platform fired at which target."""

    def __init__(self, game_log=None):
        self.game_log = game_log
        #: id(target_squad) -> set of id(firing model). A set, so a platform
        #: that shoots the same target twice in a phase still counts once -
        #: "one or more attacks" is the printed wording.
        self._fired_at = {}

    def note_attack(self, model, weapon, target_squad, reactive=False):
        """Fed from the shooting step once a (model, weapon, target) is real.

        A no-op for anything that is not a vibro cannon on a platform, and for
        reactive fire, so the caller does not have to know the rule."""
        if reactive or target_squad is None:
            return False
        if not is_vibro_cannon(weapon) or not has_sonic_destruction(model):
            return False
        self._fired_at.setdefault(id(target_squad), set()).add(id(model))
        return True

    def bonus_for(self, model, weapon, target_squad, reactive=False):
        """"+1 for each OTHER friendly VIBRO CANNON PLATFORM model that ...
        also targeted that enemy unit this phase"."""
        if reactive or target_squad is None:
            return 0
        if not is_vibro_cannon(weapon) or not has_sonic_destruction(model):
            return 0
        fired = self._fired_at.get(id(target_squad), ())
        # The firing model's own entry is excluded explicitly. It is normally
        # present already (the ledger is fed when the attack begins), and an
        # implicit "len - 1" would be right only while that stays true.
        return sum(1 for other in fired if other != id(model))

    def adjusted_weapon(self, weapon, model, target_squad, reactive=False):
        """The weapon with S/AP/D improved, or the SAME OBJECT when there is no
        bonus - so a caller can tell "unchanged" from "copied" by identity."""
        bonus = self.bonus_for(model, weapon, target_squad, reactive=reactive)
        if bonus <= 0:
            return weapon
        adjusted = copy.copy(weapon)
        adjusted.strength = weapon.strength + bonus
        adjusted.ap = weapon.ap - bonus          # "improve the AP" = more negative
        adjusted.damage = weapon.damage + bonus
        if self.game_log is not None:
            self.game_log.add(
                "[sonic destruction] %s: +%d S/AP/D from %d other platform(s) "
                "firing on %s." % (weapon.name, bonus, bonus, target_squad.name),
                file_only=True)
        return adjusted

    def reset_shooting_phase(self):
        """"this phase" - cleared with the phase, not the turn."""
        self._fired_at.clear()
