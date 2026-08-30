"""The Daemon Prince of Nurgle's own ability "Fevered Strategist".

RULE (printed, word for word):

  "Once per battle round, one model from your army with this ability can use it
  when a friendly DEATH GUARD unit within 12" of that model is targeted with a
  Stratagem. If it does, reduce the CP cost of that usage of that Stratagem by
  1CP."

THE FOURTH cost_discounts COLLABORATOR, after the T'au Puretide engram neurochip,
the Aeldari Strands of Fate pool and the Necron Overlord's My Will Be Done. The
protocol is duck-typed and two methods wide - available_discount(player,
stratagem, targets) and consume(...) - so it plugs into StratagemController
without touching it.

IT IS MY WILL BE DONE PLUS A DISTANCE, and that difference is the whole reason
it is a separate module rather than a shared one: the Overlord's version asks
whether the TARGET UNIT ITSELF carries the ability, so a merged unit answers it
off its own models. This one asks whether some OTHER model is within 12" of the
target, which needs the board. Sharing a module would mean one of the two
questions being answered by a function that cannot see what it needs.

"ONE MODEL FROM YOUR ARMY WITH THIS ABILITY" caps the ARMY per battle round,
not the model - two Daemon Princes do not get two discounts in one round. Same
ledger shape as My Will Be Done, and stated because "one model ... can use it"
reads as a per-model allowance at a glance.

NOTHING TO ASK: a discount is never a downside, so it applies whenever it can,
for the human and the AI alike, and it needs no AI path of its own.
"""

FEVERED_STRATEGIST_DISCOUNT_CP = 1
FEVERED_STRATEGIST_RANGE_IN = 12.0


def _bearers(all_tokens, owner):
    return [t for t in all_tokens or ()
            if getattr(t, "squad", None) is not None
            and t.squad.owner == owner
            and not t.is_dead()
            and getattr(t.profile, "fevered_strategist", False)]


def _is_death_guard(squad):
    return any(getattr(m.profile, "nurgles_gift", False) and not m.is_dead()
               for m in getattr(squad, "models", ()) or ())


def in_range_of_a_bearer(squad, all_tokens=()):
    """"a friendly DEATH GUARD unit within 12" of that model".

    The bearer's own unit qualifies - it is a friendly Death Guard unit within
    12" of itself, and the printed text has no "other" (unlike
    game/mechanical_augmentation.py's aura, which does)."""
    if squad is None or not _is_death_guard(squad):
        return False
    for bearer in _bearers(all_tokens, squad.owner):
        if bearer.squad is squad:
            return True
        if squad.min_distance_to(bearer.squad) <= FEVERED_STRATEGIST_RANGE_IN:
            return True
    return False


class FeveredStrategistDiscount:
    """Appended to StratagemController.cost_discounts in main.py."""

    def __init__(self, turn_tracker=None, game_log=None, all_tokens=None):
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        # A live reference to main.py's token list, not a copy - the 12" has to
        # be measured against wherever the models are when the Stratagem is
        # bought, which is not where they were when this was constructed.
        self.all_tokens = all_tokens if all_tokens is not None else []
        self._used_in_round = {}   # player -> battle_round it was last spent in

    def _round(self):
        return getattr(self.turn_tracker, "battle_round", None)

    def available(self, player):
        """"Once per battle round" - per army, not per model."""
        return self._used_in_round.get(player) != self._round()

    def available_discount(self, player, stratagem=None, targets=()):
        """A pure query: asking the price never spends the entitlement, which
        is why consume() is separate. StratagemController's _cost_for() calls
        this from both can_use() and use(), so the two cannot disagree."""
        if not self.available(player):
            return 0
        if not any(in_range_of_a_bearer(t, self.all_tokens) for t in targets or ()):
            return 0
        return FEVERED_STRATEGIST_DISCOUNT_CP

    def consume(self, player, stratagem=None, targets=()):
        """Called only once a discounted use has actually gone through."""
        if self.available_discount(player, stratagem, targets) <= 0:
            return
        self._used_in_round[player] = self._round()
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: Fevered Strategist - that Stratagem costs "
                f"{FEVERED_STRATEGIST_DISCOUNT_CP}CP less."
            )
