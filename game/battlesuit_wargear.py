"""The three non-weapon Battlesuit support systems, as Gear items.

The Commander in Enforcer Battlesuit is the first datasheet here whose wargear
menu mixes WEAPONS and SUPPORT SYSTEMS in one printed list ("up to three of the
following", naming six guns and three systems side by side). Weapons in such a
list are already expressible - gun_drone_gear() has appended a weapon from a
Gear effect since Strike Team - so the only new thing is the three systems, and
they go here rather than in game/drones.py because they are not drones.

All three effects are printed on other datasheets already, and each is wired to
the field that datasheet uses, so nothing new is enforced:

  * Battlesuit Support System - Crisis Starscythe Battlesuits' own ability
    (`battlesuit_support_system`, read by game/shooting.py's
    available_shooting_types()). The Enforcer's printed wording adds "but when
    doing so only models equipped with this wargear can make ranged attacks",
    which this engine does NOT enforce: the flag is unit-wide, and a per-model
    shooting gate does not exist. Noted on the datasheet, not silently dropped.
  * Shield Generator - a 4+ invulnerable save, the same `invulnerable_save`
    field every profile that prints one uses.
  * Weapon Support System - the Riptide's own ability under the same name
    (`ignores_hit_modifiers`, named after the EFFECT because Dark Reapers print
    it as "Inescapable Accuracy").

SAFE TO WRITE ONTO token.profile because build_squad() gives every Token its
own profile INSTANCE (game/factions/datasheet.py's `profile = line.profile_cls()`),
so these shadow the class attribute rather than changing it for every model
ever built from that datasheet.
"""

from game.factions import Gear

# The Enforcer's second printed menu is "up to three of the following", mixing
# guns and systems, so all of it shares one group and one cap.
BATTLESUIT_SUPPORT_GROUP = "battlesuit_support"
BATTLESUIT_SUPPORT_SLOTS = 3

SHIELD_GENERATOR_INVULNERABLE_SAVE = "4+"


def _battlesuit_support_system_effect(token):
    token.profile.battlesuit_support_system = True


def _shield_generator_effect(token):
    token.profile.invulnerable_save = SHIELD_GENERATOR_INVULNERABLE_SAVE


def _weapon_support_system_effect(token):
    token.profile.ignores_hit_modifiers = True


def battlesuit_support_system_gear(model_line_name):
    """Printed with a "*" - "this model cannot have duplicates of these pieces
    of wargear" - hence max_count=1 on all three."""
    return Gear(model_line_name, "Battlesuit Support System",
                _battlesuit_support_system_effect, max_count=1,
                group=BATTLESUIT_SUPPORT_GROUP)


def shield_generator_gear(model_line_name):
    return Gear(model_line_name, "Shield Generator", _shield_generator_effect,
                max_count=1, group=BATTLESUIT_SUPPORT_GROUP)


def weapon_support_system_gear(model_line_name):
    return Gear(model_line_name, "Weapon Support System",
                _weapon_support_system_effect, max_count=1,
                group=BATTLESUIT_SUPPORT_GROUP)


def _weapon_gear(model_line_name, label, weapon_cls, max_count):
    def effect(token, cls=weapon_cls):
        token.weapons.append(cls())
    return Gear(model_line_name, label, effect, max_count=max_count,
                group=BATTLESUIT_SUPPORT_GROUP)


def support_menu_gear(model_line_name, weapons):
    """The whole "up to three of the following" menu.

    `weapons` is [(printed label, WeaponProfile class, max_count)] - the
    max_count is 1 for every item the datasheet stars and higher for the ones
    it allows duplicates of, which is exactly what the printed footnote
    distinguishes."""
    return ([_weapon_gear(model_line_name, label, cls, count)
             for label, cls, count in weapons]
            + [battlesuit_support_system_gear(model_line_name),
               shield_generator_gear(model_line_name),
               weapon_support_system_gear(model_line_name)])
