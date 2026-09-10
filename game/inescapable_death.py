"""The Hexmark Destroyer's "Inescapable Death" (Necrons).

RULE (printed, word for word):
  "Once per turn, one unit from your army with this ability can be targeted
   with the Fire Overwatch Stratagem for 0CP, even if you have already used
   that Stratagem on a different unit this phase. In addition, each time you
   target this unit with the Fire Overwatch Stratagem, while resolving that
   Stratagem, hits are scored on unmodified Hit rolls of 2+."

THREE CLAUSES, AND ONLY TWO OF THEM SHARE AN ENTITLEMENT. That split is the
whole content of this module, and getting it wrong in either direction is easy:

  1. "for 0CP"                          |  once per TURN
  2. "even if you have already used     |  once per TURN  (same sentence)
      that Stratagem ... this phase"    |
  3. "each time you target this unit    |  EVERY time - no entitlement at all
      ... hits are scored on 2+"        |

Clauses 1 and 2 are one sentence and one allowance, which is why one object
implements both interfaces rather than two objects agreeing by accident.
Clause 3 opens with "each time", so a SECOND, fully paid Fire Overwatch on the
same Hexmark later in the battle still hits on 2+.

THE CONTRAST THAT MAKES CLAUSE 3 WORTH WRITING DOWN is its near-twin,
game/enh_protector_of_the_paths.py, whose own version of clause 3 reads "while
resolving THAT Stratagem" and is therefore latched to the free use it paid for.
That Enhancement carries a `_free_activation` latch for exactly that reason.
This card does not print those words, so it does not get that latch - and a
copied implementation would have silently narrowed it.

"ONCE PER TURN", NOT "ONCE PER BATTLE ROUND". Every other consumer of
game/cp_discount.py prints the latter; this is the first that does not, and a
battle round holds BOTH players' turns (07.03) - so reading them as the same
window would halve the card. The window is `(battle_round, turn_owner)`, which
is what identifies a turn: TurnTracker.turn_owner changes only in
advance_phase(), and Fire Overwatch is offered at the end of a Movement phase,
where it is unambiguous.

"ONE UNIT FROM YOUR ARMY WITH THIS ABILITY" - per ARMY, not per bearer, which
is what the base class's per-player ledger already means. Two Hexmarks share
one free Overwatch a turn.

THE 2+ IS AN OVERRIDE, NOT A MODIFIER, for the reason its twin records: rule
15.09 says Snap Shooting hits on an unmodified 6 "irrespective of the attacking
weapon's BS characteristic" and that every modifier is ignored, so a Modifier
expressing "hits on 2+" would be correctly thrown away by the very rule it is
meant to beat.
"""

from game.free_stratagem_once_per_round import FreeNamedStratagemOncePerRound

INESCAPABLE_DEATH_LABEL = "Inescapable Death"

#: The Stratagem this makes free, and the only one it touches.
INESCAPABLE_DEATH_STRATAGEM = "Fire Overwatch"

#: "hits are scored on unmodified Hit rolls of 2+" - an override of rule
#: 15.09's flat 6, the SECOND thing in this engine to change that number.
INESCAPABLE_DEATH_HIT_THRESHOLD = 2

FLAG_ATTR = "inescapable_death"


def unit_has_bearer(squad):
    """Whether this unit contains a living model with the ability.

    No leading clause and no keyword clause, unlike its Aeldari twin: the
    Hexmark Destroyer prints no LEADER line at all, so "one unit from your army
    with this ability" is simply the unit he is."""
    if squad is None:
        return False
    return any(getattr(m.profile, FLAG_ATTR, False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def snap_hit_threshold(squad):
    """The unmodified Hit roll a Snap Shooting activation by `squad` hits on,
    or None - in which case rule 15.09's plain 6 stands.

    NOT gated on the free use, and that is clause 3's own wording: "EACH TIME
    you target this unit with the Fire Overwatch Stratagem". Contrast
    enh_protector_of_the_paths.snap_hit_threshold(), which asks its discount
    whether this is the activation it paid for, because that card says "while
    resolving THAT Stratagem"."""
    if not unit_has_bearer(squad):
        return None
    return INESCAPABLE_DEATH_HIT_THRESHOLD


class InescapableDeathDiscount(FreeNamedStratagemOncePerRound):
    """Clauses 1 and 2: plugged into BOTH StratagemController.cost_discounts
    and StratagemController.repeat_permissions.

    Two lists, one object, because they are one printed sentence with one
    allowance - split across two objects they could disagree about whether the
    entitlement is still there, and the player would get a free use that 15.01
    then refused, or a permitted repeat that cost CP."""

    flag = FLAG_ATTR
    stratagem_name = INESCAPABLE_DEATH_STRATAGEM
    label = INESCAPABLE_DEATH_LABEL
    #: A printed DATASHEET ability, not an Enhancement - so no detachment gate,
    #: and the base class's bare living-bearer check is the right one.
    enhancement_name = None

    def window_key(self):
        """"Once per TURN". `(battle_round, turn_owner)` is what identifies a
        turn - the round alone would give one use per two turns, the owner
        alone would never reset."""
        return (getattr(self.turn_tracker, "battle_round", None),
                getattr(self.turn_tracker, "turn_owner", None))

    def permits_repeat(self, player, stratagem=None, targets=()):
        """Clause 2, and deliberately the SAME condition as clause 1's price:
        the sentence gives one allowance, so the repeat is permitted exactly
        when the free use is.

        A PURE QUERY - available_discount() is one too, and refusal() calls
        this every frame from Fire Overwatch's eligibility sweep."""
        return self.available_discount(player, stratagem, targets) > 0

    def log_line(self, player, stratagem=None):
        return ("%s: %s - %s costs 0CP this turn, even if it was already used "
                "this phase." % (player, self.label,
                                 getattr(stratagem, "name", "that Stratagem")))
