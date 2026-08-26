"""The Overlord's "My Will Be Done".

RULE (printed, word for word):
  "Once per battle round, one unit from your army with this ability can use it
   when its unit is targeted with a Stratagem. If it does, reduce the CP cost
   of that use of that Stratagem by 1CP."

THE THIRD cost_discounts COLLABORATOR, after the T'au Puretide engram neurochip
(game/puretide.py) and the Aeldari Strands of Fate pool
(game/strands_of_fate.py). The protocol is duck-typed and two methods wide -
available_discount(player, stratagem, targets) and consume(...) - so this
plugs into StratagemController without touching it.

IT IS PURETIDE ALMOST EXACTLY, and that is worth saying rather than hiding: the
same "once per battle round, per army, when a unit carrying it is TARGETED"
shape, the same 1 CP. It gets its own module anyway because the two are
different factions' rules and would otherwise share a file named after the
wrong one - the mistake CLAUDE.md records for ere_we_go.py and melee_crit.py.

THE LEDGER IS PER PLAYER, PER BATTLE ROUND, not per model: "ONE unit from your
army with this ability can use it" caps the army, so two Overlords do not get
two discounts in the same round.

NOTHING TO ASK. The discount is never a downside, so there is no decision to
offer - it applies whenever it can, for a human and for the AI alike. That also
means it needs no AI path of its own.
"""

MY_WILL_BE_DONE_DISCOUNT_CP = 1


def unit_has_my_will_be_done(squad):
    """Rule 19.03: a merged unit counts as having it if any component brought
    it, which reading it live off the models gives for free - and which also
    makes it stop working the moment the Overlord dies."""
    if squad is None:
        return False
    return any(getattr(m.profile, "my_will_be_done", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


class MyWillBeDoneDiscount:
    """Appended to StratagemController.cost_discounts in main.py."""

    def __init__(self, turn_tracker=None, game_log=None):
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._used_in_round = {}   # player -> battle_round it was last spent in

    def _round(self):
        return getattr(self.turn_tracker, "battle_round", None)

    def available(self, player):
        """"Once per battle round" - per army."""
        return self._used_in_round.get(player) != self._round()

    def available_discount(self, player, stratagem=None, targets=()):
        """How much to knock off this use. A pure query: asking the price never
        spends the entitlement, which is why consume() is separate."""
        if not self.available(player):
            return 0
        if not any(unit_has_my_will_be_done(t) for t in targets or ()):
            return 0
        return MY_WILL_BE_DONE_DISCOUNT_CP

    def consume(self, player, stratagem=None, targets=()):
        """Called only once a discounted use has actually gone through."""
        if self.available_discount(player, stratagem, targets) <= 0:
            return
        self._used_in_round[player] = self._round()
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: My Will Be Done - that Stratagem costs "
                f"{MY_WILL_BE_DONE_DISCOUNT_CP}CP less."
            )
