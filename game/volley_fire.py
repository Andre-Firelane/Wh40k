"""T'au Empire datasheet ability: Cadre Fireblade's Volley Fire, as supplied
by the user (not a core rulebook rule):

    "While this model is leading a unit, add 1 to the Attacks characteristic
     of ranged weapons equipped by models in that unit."

Wired the same way the Orks army rule Waaagh! is (game/waaagh.py's
waaagh_extra_attacks()): a per-model bonus to the Attacks characteristic is
just extra attack dice for the group, added alongside extra_attack_dice() at
every total_attacks computation. The difference is who grants it. Waaagh! is a
property each model carries itself, so it reads the firing model's own profile;
Volley Fire is granted by ANOTHER model - the Fireblade leading the unit - to
every model in it, so it has to ask the SQUAD.

Deferred until now for a reason that has since expired: the ability only ever
does anything on an attached unit (19.01), and there was no way to form one.
Attached Units are implemented, this was not brought along with them, and the
gap surfaced as a plain wrong dice count - user report: "breacher hatten nur 20
schuss, trotz fireblade. hätten 30 sein müssen" (10 Pulse Blasters at A2, which
Volley Fire makes A3).
"""
from game.squad import squad_has_volley_fire
from game.weapons import RANGED

VOLLEY_FIRE_ATTACKS_BONUS = 1


def volley_fire_extra_attacks(pairs):
    """Extra attack dice this ranged group gets from Volley Fire: +1 per
    (model, weapon) pair in it.

    Per PAIR rather than per model on purpose. The ability adds 1 to the
    Attacks characteristic of "ranged weapons equipped by models in that
    unit" - a model firing two different ranged weapons resolves them as two
    groups and each weapon's characteristic goes up, so it gets +1 in each.
    Counting models once for the whole activation would instead give such a
    model a single extra shot in total.

    Melee groups are excluded explicitly rather than by relying on the caller:
    the same helper shape is used from game/fight.py for Waaagh!, and this
    ability is ranged-only.
    """
    if not pairs:
        return 0
    weapon = pairs[0][1]
    if getattr(weapon, "weapon_type", None) != RANGED:
        return 0
    shooter = pairs[0][0]
    squad = getattr(shooter, "squad", None)
    if squad is None or not squad_has_volley_fire(squad):
        return 0
    return len(pairs) * VOLLEY_FIRE_ATTACKS_BONUS
