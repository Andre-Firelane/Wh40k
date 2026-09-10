""""Once per battle round, reduce the cost of a Stratagem used on this unit."

TWENTIETH EXTRACTION - and an overdue one, at the FOURTH consumer rather than
the second.

Four datasheets across four factions print this sentence with the name changed:

  Puretide's Teachings  (T'au, Commander Farsight)      game/puretide.py
  My Will Be Done       (Necrons, Overlord)             game/my_will_be_done.py
  War Leader            (T'au, Kroot War Shaper)        game/war_leader.py
  Path of Command       (Aeldari, both Autarchs)        game/path_of_command.py

  "Once per battle round, one model from your army with this ability can use it
   when its unit is targeted with a Stratagem. If it does, reduce the CP cost of
   that usage of that Stratagem by 1CP."

The first three each grew their own copy of the same twenty lines. Adding a
fourth was the point at which that stopped being defensible, so the machinery
moved here and all four now name only what differs: the flag that marks a
bearer, the discount, and the log line.

WHAT THE SHARED PART ACTUALLY GUARANTEES, and why it is worth having once:

  * TWO METHODS, DELIBERATELY SPLIT. available_discount() is a PURE QUERY that
    StratagemController.can_use() may call as often as it likes; consume() is
    the only thing that spends the once-per-round use. Merely asking whether a
    Stratagem is affordable must never burn the ability - and that is an easy
    thing to get wrong independently in four places.
  * APPLIED TO THE COST, NOT REFUNDED AFTERWARDS. "Reduce the CP cost of that
    use" means a player with exactly enough CP only because of the discount can
    still use the Stratagem. A refund would fail the affordability check first
    and never happen.
  * ONCE PER BATTLE ROUND, PER PLAYER - keyed off TurnTracker.battle_round, not
    per phase and not per turn. A battle round contains both players' turns
    (07.03), and "ONE model from your army" means two bearers still share one
    use between them.
  * AUTOMATIC, NOT A PROMPT. The text says "can use it", but holding the
    entitlement back cannot help: it returns next round regardless, so there is
    no better Stratagem to save it for. Logged rather than asked, the same call
    rule 24.29's [PSYCHIC] modifier-ignoring gets.

game/strands_of_fate.py is deliberately NOT one of these: its discount keys off
WHICH Stratagem is being used rather than off the target, which is the whole
reason `stratagem` is a parameter here at all.
"""


class OncePerRoundCpDiscount:
    """Plugged into StratagemController.cost_discounts.

    Subclass and set `flag`, `discount_cp` and `label`; override `log_line()`
    for an ability whose log wording differs."""

    flag = None             # the UnitProfile attribute naming a bearer
    discount_cp = 1
    label = "CP discount"

    def __init__(self, turn_tracker=None, game_log=None):
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._used_in_round = {}   # player -> battle_round it was last spent in

    # --- bearers ----------------------------------------------------------

    def unit_has_ability(self, squad):
        """Read live off the living models, so it ends with the model."""
        if squad is None:
            return False
        return any(getattr(m.profile, self.flag, False)
                   for m in getattr(squad, "models", ()) or () if not m.is_dead())

    # --- the once-per-round window ---------------------------------------

    def _round(self):
        return getattr(self.turn_tracker, "battle_round", None)

    def window_key(self):
        """The ONCE-PER window this entitlement resets on.

        A battle round for every ability here today, all of which print
        "once per battle round". A card whose printed text says something else
        overrides THIS rather than _round(), so the base name keeps meaning
        exactly the battle round it is named after - the Hexmark Destroyer's
        Inescapable Death is the first such card, and it says "once per TURN"
        (game/inescapable_death.py). A battle round holds both players' turns
        (07.03), so the two windows are genuinely different."""
        return self._round()

    def available(self, player):
        """"Once per battle round" - per army, not per bearer. The window
        itself comes from window_key(), so a subclass with a different printed
        one changes only that."""
        return self._used_in_round.get(player) != self.window_key()

    # --- the two halves ---------------------------------------------------

    def available_discount(self, player, stratagem=None, targets=()):
        """A PURE QUERY - see the module docstring on why asking the price must
        not spend the entitlement."""
        if not self.available(player):
            return 0
        if not any(self.unit_has_ability(t) for t in targets or ()):
            return 0
        return self.discount_cp

    def consume(self, player, stratagem=None, targets=()):
        """Called only once a discounted use has actually gone through."""
        if self.available_discount(player, stratagem, targets) <= 0:
            return
        self._used_in_round[player] = self.window_key()
        if self.game_log is not None:
            self.game_log.add(self.log_line(player, stratagem))

    def log_line(self, player, stratagem=None):
        return ("%s: %s - that Stratagem costs %dCP less."
                % (player, self.label, self.discount_cp))
