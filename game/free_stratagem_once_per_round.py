""""Once per battle round, you can target the bearer's unit with the <NAMED>
Stratagem for 0CP."

TWENTY-NINTH EXTRACTION, at the SECOND consumer as the convention asks:

  Protector of the Paths  (Guardian Battlehost)  Fire Overwatch
  Gift of Foresight       (Warhost)              Command Re-roll

Both print that sentence with only the Stratagem's name changed - and Protector
of the Paths then adds a second, unrelated clause about hit rolls, which is why
that one is not simply this class with a different name.

A SUBCLASS OF game/cp_discount.py's OncePerRoundCpDiscount, not a fifth flat
consumer of it, because two things genuinely differ:

  1. IT KEYS OFF THE STRATAGEM, not just off the target. The four abilities in
     that module reduce the cost of ANY Stratagem used on the bearer's unit;
     these two name ONE Stratagem and do nothing for any other. That module's
     own docstring already draws this line - it says game/strands_of_fate.py is
     deliberately not one of its consumers for exactly this reason.
  2. IT IS FREE, NOT CHEAPER. "For 0CP" is not "-1CP": the discount is whatever
     the Stratagem happens to cost, so a 2CP use is as free as a 1CP one.
     Reading it as a flat -1 would leave the player paying for something the
     card says is free, and would look right on every 1CP Stratagem.

EVERYTHING ELSE IS INHERITED AND IS THE POINT OF INHERITING: the pure-query /
consume split (asking the price must never burn the entitlement), the
once-per-BATTLE-ROUND-per-ARMY ledger keyed off TurnTracker.battle_round, and
the "applied to the cost rather than refunded afterwards" guarantee that lets a
player with no CP at all still use it.

AUTOMATIC, NOT A PROMPT - the same call the base class makes and for the same
reason: the entitlement returns next round regardless, and it only ever applies
to one named Stratagem, so there is nothing better to save it for.
"""
from game import enhancements
from game.cp_discount import OncePerRoundCpDiscount


class FreeNamedStratagemOncePerRound(OncePerRoundCpDiscount):
    """Subclass and set `flag`, `stratagem_name`, `enhancement_name` and
    `label`."""

    #: The ONE Stratagem this makes free. Compared by name, which is what
    #: StratagemController hands over and what the card prints.
    stratagem_name = None

    #: The Enhancement's registry name, for the DETACHMENT GATE. The four
    #: abilities in the base class are printed on datasheets and are always on;
    #: an Enhancement only exists while its detachment is fielded, and
    #: inheriting the bare flag check would leave it working without one -
    #: exactly the limitation game/starflare_ignition.py was fixed for.
    enhancement_name = None

    def unit_has_ability(self, squad):
        """A living bearer AND the detachment - see enhancement_name."""
        if self.enhancement_name is None:
            return super().unit_has_ability(squad)
        return enhancements.is_active(squad, self.enhancement_name)

    def matches_stratagem(self, stratagem):
        if stratagem is None or self.stratagem_name is None:
            return False
        return getattr(stratagem, "name", None) == self.stratagem_name

    def available_discount(self, player, stratagem=None, targets=()):
        """The Stratagem's WHOLE cost, so the use is free - a pure query, like
        the base class's."""
        if not self.matches_stratagem(stratagem):
            return 0
        if not self.available(player):
            return 0
        if not any(self.unit_has_ability(t) for t in targets or ()):
            return 0
        return max(0, getattr(stratagem, "cp_cost", 0))

    def log_line(self, player, stratagem=None):
        return ("%s: %s - %s costs 0CP this battle round."
                % (player, self.label, getattr(stratagem, "name", "that Stratagem")))
