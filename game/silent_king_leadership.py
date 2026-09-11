"""The Silent King's fourth aura: "The Silent King".

RULE (verbatim, rules/necrons/The Silent King.md):

  "The Silent King: While a friendly NECRONS unit is within 6" of this unit's
   Szarekh model, improve that unit's Leadership characteristic by 1."

SEPARATE FROM THE THREE TRIARCH ABILITIES, and not by accident: those three are
swapped between by Voice of the Triarch, one per battle round. This one is not
on that list and is therefore ALWAYS on. A reader who folds it into
game/triarch_auras.py would make the army's Leadership flicker with a choice
the printed text never attaches it to.

ONE PRINTED WORD SEPARATES IT FROM ITS THREE NEIGHBOURS, and it is the word
that matters here: they say "a friendly NECRONS unit (EXCLUDING MONSTER
UNITS)", this one says "a friendly NECRONS unit". So a C'tan Shard beside
Szarekh gets this and none of the other three. Pinned in the suite from both
sides, because the natural mistake is to share one predicate between all four.

"IMPROVE ... BY 1" IS A SUBTRACTION HERE. Leadership is an N+ threshold in this
engine (game/leadership.py), so a BETTER characteristic is a LOWER number - the
same direction Auxiliary Cadre's Admired Leader Enhancement already folds in,
and the opposite of Scabrous Soulrot and the icon of despair beside it. Getting
the sign wrong would turn a bodyguard aura into an army-wide Battle Shock
penalty, which is why leadership.py applies all of them in one visible sum.
"""

from game import awakened_dynasty
from game.squad import edge_distance

SILENT_KING_RANGE_IN = 6.0
SILENT_KING_LABEL = "The Silent King"
SILENT_KING_LEADERSHIP_BONUS = 1


def _alive(squad):
    return [m for m in squad.models if not m.is_dead()] if squad else []


def bearer_models(all_tokens):
    """Every living Szarekh model on the board."""
    return [t for t in (all_tokens or ())
            if getattr(t.profile, "silent_king_leadership", False) and not t.is_dead()]


def applies(squad, all_tokens):
    """Whether this unit is inside a friendly Szarekh's 6"."""
    if squad is None or not awakened_dynasty.is_necrons_unit(squad):
        return False
    mine = _alive(squad)
    if not mine:
        return False
    for bearer in bearer_models(all_tokens):
        if getattr(bearer.squad, "owner", None) != squad.owner:
            continue
        if any(edge_distance(m, bearer) <= SILENT_KING_RANGE_IN for m in mine):
            return True
    return False


def leadership_bonus(squad, all_tokens):
    """The amount to SUBTRACT from the unit's Leadership threshold - see the
    module docstring for why an improvement subtracts."""
    return SILENT_KING_LEADERSHIP_BONUS if applies(squad, all_tokens) else 0
