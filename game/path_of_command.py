"""Both Autarchs' "Path of Command" - a datasheet ability.

RULE (printed, word for word):
  "Once per battle round, one model from your army with this ability can use it
  when its unit is targeted with a Stratagem. If it does, reduce the CP cost of
  that usage of that Stratagem by 1CP."

THE FOURTH DATASHEET TO PRINT THIS SENTENCE, and the one that finally paid for
extracting it. Commander Farsight's Puretide's Teachings, the Necron Overlord's
My Will Be Done and the Kroot War Shaper's War Leader each carried their own
copy of the same twenty lines; game/cp_discount.py now holds them, and all four
name only the flag, the discount and the label.

Everything about WHY it behaves the way it does - the pure-query/consume split,
the discount applied to the cost rather than refunded, "once per battle round"
meaning per ARMY, and why it is automatic rather than a prompt - lives in that
module's docstring, because it is the same reasoning four times over.

BOTH AUTARCHS PRINT IT, and "one model from your army" means they still share
one use per round between them. That falls out of the shared window being keyed
per PLAYER, and has its own test line because two bearers is the case where a
per-model ledger would look right.
"""
from game.cp_discount import OncePerRoundCpDiscount

PATH_OF_COMMAND_DISCOUNT_CP = 1
PATH_OF_COMMAND_LABEL = "Path of Command"


def unit_has_path_of_command(squad):
    """Whether a living model in this unit prints it - read live, so it stops
    working the moment the Autarch dies."""
    if squad is None:
        return False
    return any(getattr(m.profile, "path_of_command", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


class PathOfCommandDiscount(OncePerRoundCpDiscount):
    """Appended to StratagemController.cost_discounts in main.py."""

    flag = "path_of_command"
    discount_cp = PATH_OF_COMMAND_DISCOUNT_CP
    label = PATH_OF_COMMAND_LABEL
