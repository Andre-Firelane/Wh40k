"""The Doomsday Ark's "Overwhelming Obliteration".

RULE (printed, word for word):
  "In your Movement phase, if this model Remains Stationary, until the end of
   the turn, its doomsday cannon has the [DEVASTATING WOUNDS] ability."

NOT A DECISION, A CONSEQUENCE. There is no "you can" here: the trigger is the
move type the unit already chose, so nothing prompts and nothing is offered.
That also means the AI needs no path of its own for it - the choice it makes is
whether to move, and this simply follows.

WHERE IT HOOKS: MovementController.on_remain_stationary, the existing single
hook that fires when a unit's Movement-phase choice is Remain Stationary. The
flag it sets is cleared at the end of the TURN, alongside the other
until-end-of-turn grants in main.py's advance_turn_phase().

WEAPON-SPECIFIC, which is what makes it different from the other
[DEVASTATING WOUNDS] grants in this engine (Ferocious Rage, the Plasmacyte),
both of which say "melee weapons" and so apply to a whole category. This one
names ONE weapon, so adjusted_weapon() matches on the weapon rather than
granting to everything the model carries - the Ark's two gauss flayer arrays
and its armoured bulk are untouched.
"""

import copy

from game.weapons import DoomsdayCannonProfile


def has_ability(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "overwhelming_obliteration", False)
               for m in squad.models if not m.is_dead())


def on_remain_stationary(squad, game_log=None):
    """Called from MovementController's Remain Stationary hook."""
    if not has_ability(squad):
        return False
    squad.overwhelming_obliteration_active = True
    if game_log is not None:
        game_log.add(f"Overwhelming Obliteration: {squad.name} Remains Stationary - its "
                     f"doomsday cannon has [DEVASTATING WOUNDS] until the end of the turn.")
    return True


def expire_for_turn(squads=()):
    """"until the end of the turn"."""
    for squad in squads or ():
        squad.overwhelming_obliteration_active = False


def adjusted_weapon(weapon, squad):
    """[DEVASTATING WOUNDS] on the DOOMSDAY CANNON only, while the grant is
    up. Copies rather than mutating the shared instance."""
    if weapon is None or not getattr(squad, "overwhelming_obliteration_active", False):
        return weapon
    if not isinstance(weapon, DoomsdayCannonProfile) or weapon.devastating_wounds:
        return weapon
    granted = copy.copy(weapon)
    granted.devastating_wounds = True
    return granted
