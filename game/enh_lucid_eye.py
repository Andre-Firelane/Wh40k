"""Seer Council Enhancement: Lucid Eye (30 pts).

RULE (verbatim, rules/aeldari/detachments/Seer Council.md):
  "ASURYANI PSYKER model only. In your Command phase, you can add 1 to or
  subtract 1 from the value of one Fate dice in your Fate dice pool."

THE MOST EXPENSIVE OF THE 28, and what it buys is not a bonus but a SWAP.

A Fate dice pool is a list of FACES (game/strands_of_fate.py's
FateDicePool.dice[player]), and a die's face IS which Stratagem it pays for -
STRATAGEM_BY_FATE_VALUE maps value to Stratagem. consume() then removes a die
BY VALUE. So "+1 to the value of one Fate dice" is not a modifier applied when
the die is spent; it REPLACES a 3 in the pool with a 4, and the pool now pays
for a different Stratagem. Modelled as a bonus laid on top, the pool would
still hold a 3 and consume() would still find one - the Enhancement would look
wired and change nothing.

CLAMPED TO A REAL DIE FACE. A 6 cannot become a 7 and a 1 cannot become a 0:
there is no Stratagem at either value, and a pool holding one would be a die
that can never be spent. So the offer only lists the changes that land on a
face the pool can actually use.

"ONE FATE DICE" - exactly one per Command phase, and it is a genuine choice
(which die, and which direction), so it is asked rather than resolved. Unlike
the "any or all modifiers" clauses this engine auto-resolves, both directions
here are live: a player may want a cheaper Stratagem available or a dearer one.
"""
from game import enhancements
from game.strands_of_fate import STRATAGEM_BY_FATE_VALUE

LUCID_EYE = "Lucid Eye"

LUCID_EYE_LABEL = "Lucid Eye"

#: "add 1 to or subtract 1 from".
LUCID_EYE_STEPS = (1, -1)


def bearer_models(squad):
    return enhancements.bearer_models(squad, LUCID_EYE)


def legal_values():
    """The faces a Fate die can actually hold - every value that names a
    Stratagem."""
    return sorted(STRATAGEM_BY_FATE_VALUE)


def adjustments(faces):
    """(from_value, to_value) for every change this could make to `faces`.

    Deduplicated on the PAIR rather than per die: two 3s in the pool offer one
    "3 -> 4", not two identical choices."""
    legal = set(legal_values())
    out = []
    for value in sorted(set(faces or ())):
        for step in LUCID_EYE_STEPS:
            new = value + step
            if new in legal and (value, new) not in out:
                out.append((value, new))
    return out


def apply_adjustment(faces, from_value, to_value):
    """Replace ONE die of `from_value` with `to_value`, in place. Returns True
    when a die was actually changed."""
    if faces is None or from_value not in faces:
        return False
    if to_value not in set(legal_values()):
        return False
    faces[faces.index(from_value)] = to_value
    return True


class LucidEyeController:
    """The Command-phase offer."""

    def __init__(self, game_state=None, fate_pool=None, decision_manager=None,
                 game_log=None, auto_players=()):
        self.game_state = game_state
        self.fate_pool = fate_pool
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)

    def _squads(self):
        seen, out = set(), []
        for token in getattr(self.game_state, "tokens", ()) or ():
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen.add(id(squad))
                out.append(squad)
        return out

    def has_bearer(self, player):
        return any(bearer_models(s) for s in self._squads() if s.owner == player)

    def options_for(self, player):
        if self.fate_pool is None or not self.has_bearer(player):
            return []
        return adjustments(self.fate_pool.dice.get(player, []))

    def begin_command_phase(self, player):
        """"In your Command phase, you can add 1 to or subtract 1 from ..."."""
        options = self.options_for(player)
        if not options:
            return False
        if player in self.auto_players or self.decision_manager is None:
            # No deterministic answer is better than another here - the value
            # of a face depends entirely on which Stratagem the player wants -
            # so an automatic player simply declines rather than reshaping its
            # own pool at random.
            return False
        self.decision_manager.request(
            player,
            "%s: change one Fate dice?" % LUCID_EYE_LABEL,
            [("%d -> %d (%s)" % (a, b, STRATAGEM_BY_FATE_VALUE[b]),
              (lambda x=a, y=b: self._apply(player, x, y)))
             for a, b in options] + [("Leave the pool alone", lambda: False)],
        )
        return True

    def _apply(self, player, from_value, to_value):
        if not apply_adjustment(self.fate_pool.dice.get(player), from_value, to_value):
            return False
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s - one Fate dice becomes a %d (%s)."
                % (player, LUCID_EYE_LABEL, to_value, STRATAGEM_BY_FATE_VALUE[to_value]))
        return True
