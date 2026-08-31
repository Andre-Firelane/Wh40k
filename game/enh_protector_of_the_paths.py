"""Guardian Battlehost Enhancement: Protector of the Paths (20 pts).

RULE (verbatim, rules/aeldari/detachments/Guardian Battlehost.md):
  "ASURYANI model only. While the bearer is leading a DIRE AVENGERS or
  GUARDIANS unit, once per battle round, you can target the bearer's unit with
  the Fire Overwatch Stratagem for 0CP, and while resolving that Stratagem,
  hits are scored on unmodified Hit rolls of 5+, or unmodified Hit rolls of 4+
  instead if the bearer's unit is within range of an objective marker you
  control."

TWO CLAUSES THAT SHARE A TRIGGER. The first is the sentence its sibling Gift of
Foresight prints word for word with a different Stratagem, so it comes from
game/free_stratagem_once_per_round.py. The second is this card alone, and it is
the interesting half.

THE FIRST OVERRIDE OF SNAP SHOOTING'S 6. Rule 15.09 is deliberately absolute -
"each attack only hits on an unmodified hit roll of 6, IRRESPECTIVE of the
attacking weapon's BS characteristic" - and game/shooting.py's
_base_hit_threshold() returns a bare 6 for it, ahead of everything else. This
Enhancement is the first thing in the engine that changes that number, so it is
applied at that one place rather than as a modifier: 15.09 also says every
modifier is ignored, so a Modifier would be correctly thrown away.

5+ OR 4+, AND THE 4+ IS CONDITIONAL ON THE BOARD. "within range of an objective
marker YOU CONTROL" - both halves matter and each can be missed on its own: a
marker the opponent controls does not count, and neither does one the unit is
merely near without controlling. Read as "within range of any objective" it
would be a 4+ almost always, which is a materially different card.

WHY 5+ IS NOT A MODIFIER EITHER. Snap Shooting's own text says modifiers are
ignored; expressing "hits on 5+" as a -1 would be dropped by that rule, and
expressing it as a -1 applied afterwards would then also be improved by
anything else in the list. An override says what the card says.

"WHILE RESOLVING THAT STRATAGEM" - so the better threshold applies ONLY to the
free Overwatch this Enhancement paid for, not to every Fire Overwatch the army
makes. The two clauses are therefore linked by more than sharing a card: the
threshold half asks whether THIS activation is the one the discount opened.
"""
from game import attached_units, enhancements, objectives as objectives_mod
from game.free_stratagem_once_per_round import FreeNamedStratagemOncePerRound

PROTECTOR_OF_THE_PATHS = "Protector of the Paths"

PROTECTOR_LABEL = "Protector of the Paths"

#: The Stratagem this makes free.
PROTECTOR_STRATAGEM = "Fire Overwatch"

#: "hits are scored on unmodified Hit rolls of 5+..."
PROTECTOR_HIT_THRESHOLD = 5

#: "...or unmodified Hit rolls of 4+ instead if the bearer's unit is within
#: range of an objective marker you control."
PROTECTOR_HIT_THRESHOLD_ON_OBJECTIVE = 4

FLAG_ATTR = "protector_of_the_paths"

#: "While the bearer is leading a DIRE AVENGERS or GUARDIANS unit". EITHER
#: keyword qualifies - both are printed, and reading only one would switch the
#: Enhancement off for half the units it is written for.
PROTECTOR_KEYWORDS = ("DIRE AVENGERS", "GUARDIANS")


def unit_has_bearer(squad):
    """All THREE printed conditions: carried, LEADING (24.22), and leading a
    unit with one of the two named keywords.

    The keyword clause is not decoration - an Autarch or Farseer can lead
    things that are neither, and against those the whole card does nothing."""
    if squad is None:
        return False
    # is_active(), not a bare flag read: a living bearer AND the detachment.
    if not enhancements.is_active(squad, PROTECTOR_OF_THE_PATHS):
        return False
    if not attached_units.leader_ability(squad, FLAG_ATTR):
        return False
    return any(attached_units.unit_has_datasheet_keyword(squad, k)
               for k in PROTECTOR_KEYWORDS)


def snap_hit_threshold(discount, squad, objectives=()):
    """The unmodified Hit roll THIS Snap Shooting activation hits on, or None -
    in which case rule 15.09's plain 6 stands.

    Gated on the LATCH, not merely on the bearer: "while resolving THAT
    Stratagem" means the free Overwatch this Enhancement paid for, and a
    player can use Fire Overwatch again later in the same battle round at full
    price (used_this_phase is per PHASE, the discount is per battle ROUND).
    That second one is an ordinary Overwatch and hits on 6s."""
    if discount is None or squad is None:
        return None
    if not discount.is_free_activation(squad):
        return None
    if not unit_has_bearer(squad):
        return None
    if _on_controlled_objective(squad, objectives):
        return PROTECTOR_HIT_THRESHOLD_ON_OBJECTIVE
    return PROTECTOR_HIT_THRESHOLD


def _on_controlled_objective(squad, objectives=()):
    """"within range of an objective marker YOU CONTROL" - two conditions, and
    a marker the opponent holds satisfies neither."""
    owner = getattr(squad, "owner", None)
    controlled = [o for o in objectives or ()
                  if getattr(o, "controlled_by", None) == owner]
    if not controlled:
        return False
    # The shared 3" reading of "within range of an objective marker", so this
    # cannot drift from what rule 12.08 and every other caller measures. It
    # takes a LIST, and only the controlled ones are handed to it.
    return objectives_mod.is_within_range_of_objective(squad, controlled)


class ProtectorOfThePathsDiscount(FreeNamedStratagemOncePerRound):
    """The discount half, plus the LATCH that ties the threshold half to it.

    consume() runs exactly when a free Overwatch has actually been paid for
    (at 0CP), which is the one moment that identifies WHICH activation the
    second clause applies to. The latch is cleared when that activation
    finishes, so a later paid Overwatch in the same battle round hits on 6s."""

    flag = FLAG_ATTR
    stratagem_name = PROTECTOR_STRATAGEM
    enhancement_name = PROTECTOR_OF_THE_PATHS
    label = PROTECTOR_LABEL

    def unit_has_ability(self, squad):
        """The SAME three conditions the threshold half asks. Inheriting the
        base class's bare flag check would grant the free Overwatch to a bearer
        leading nothing, or leading a unit the card does not name - and the
        two halves of one sentence would then disagree."""
        return unit_has_bearer(squad)

    def __init__(self, turn_tracker=None, game_log=None):
        super().__init__(turn_tracker=turn_tracker, game_log=game_log)
        #: The squad whose FREE Overwatch is resolving right now, or None.
        self._free_activation = None

    def consume(self, player, stratagem=None, targets=()):
        opened = self.available_discount(player, stratagem, targets) > 0
        super().consume(player, stratagem, targets)
        if opened:
            self._free_activation = targets[0] if targets else None

    def is_free_activation(self, squad):
        return squad is not None and self._free_activation is squad

    def clear_activation(self):
        """Called when the Snap Shooting activation ends - see the latch."""
        self._free_activation = None
