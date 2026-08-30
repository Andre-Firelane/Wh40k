"""Aeldari Seer Council detachment rule: Strands of Fate, as supplied by the
user.

    "At the start of the first battle round, you generate Fate dice by rolling
     a number of D6 based on the battle size (Incursion 3 / Strike Force 6 /
     Onslaught 9). Keep your Fate dice to one side - this is your Fate dice
     pool.

     Each time you use one of the Stratagems below, if your Fate dice pool
     contains one or more Fate dice showing the corresponding value in the
     table below, you can discard one of those corresponding Fate dice. If you
     do, reduce the CP cost of that usage of that Stratagem by 1CP."

HOW THIS DIFFERS FROM BATTLE FOCUS
----------------------------------
Both are Aeldari pools and they are not the same shape, which is why they are
two modules:

  * Battle Focus tokens are a COUNT, refilled every battle round, and unspent
    ones are lost. Fate dice are VALUES, rolled ONCE for the whole battle, and
    what is left over simply stays.
  * A Battle Focus token pays for any Agile Manoeuvre. A Fate die of value N
    can only ever discount the ONE stratagem N maps to - so the pool is six
    independent little reserves that happen to be stored together.

WHY THE PLAYER PICKS THE DETACHMENT AND THE ENGINE CANNOT
--------------------------------------------------------
game/battle_focus.py derives whose army is ASURYANI from the units themselves
(they carry the ability). That is impossible here: a detachment is a
list-building declaration, and game/factions/detachment.py is deliberately
pure data whose own docstring says nothing applies a detachment rule
automatically. There is nothing on a unit to infer it from, so
config.SEER_COUNCIL_PLAYERS is a genuine setting rather than a forgettable
substitute for one - the same owner-keyed shape as WALL_CROSSING_PLAYERS and
SPREAD_LIMIT_PLAYERS.

THE DISCOUNT IS AUTOMATIC TODAY, AND THAT IS A CHOICE WORTH REVISITING
---------------------------------------------------------------------
The rule says "you CAN discard", so it is a decision, not a consequence. It is
taken automatically here because none of the six stratagems exist yet, so
nothing consumes it and the question is cheap to answer later - and because
asking on every stratagem use is the interruption the user already objected to
elsewhere ("das würde sehr nerven").

It is NOT a decision without content, though, and the reasoning is recorded so
it does not have to be found twice. Spending immediately looks dominant (the
die has no other use, and 1 CP now is as good as 1 CP later) - but it is not:
a die held back is what lets a stratagem be used at a moment when its owner is
at 0 CP and could not otherwise afford it at all. Any real choice belongs at
the stratagem's own button, showing both prices; `armed` exists so that can be
layered on without reworking this.
"""

from game import config
from game import detachment_gate
from game import dice as dice_module  # for random.randint, which testkit scripts

FATE_DICE_BY_BATTLE_SIZE = {
    "incursion": 3,
    "strike_force": 6,
    "onslaught": 9,
}

# The rule's own table. One die value, one stratagem - so a die is only ever
# worth anything to exactly one of the six.
STRATAGEM_BY_FATE_VALUE = {
    1: "Presentiment of Dread",
    2: "Forewarned",
    3: "Unshrouded Truth",
    4: "Fate Inescapable",
    5: "Isha's Fury",
    6: "Psychic Shield",
}

FATE_VALUE_BY_STRATAGEM = {name: value for value, name in STRATAGEM_BY_FATE_VALUE.items()}

FATE_DICE_DISCOUNT_CP = 1


#: The config constant game/detachments.py writes for this detachment. Named
#: here because this module IS the Seer Council rule, the same way each T'au
#: detachment module carries its own SETTING.
SETTING = "SEER_COUNCIL_PLAYERS"


def has_detachment(player):
    """Whether `player` actually fields Seer Council.

    THIS WAS MISSING FROM THE SIX STRATAGEMS, and it was harmless right up
    until it was not: while Seer Council was the only Aeldari detachment
    modelled, "an Aeldari army" and "a Seer Council army" were the same set, so
    ungated stratagems were accidentally correct. Seven more Aeldari
    detachments make them wrong - a Warhost army would own Strands of Fate's
    stratagems without paying for the detachment that prints them. Every T'au
    stratagem has carried this gate from the start; these six now do too."""
    return detachment_gate.has_detachment(player, SETTING)


def fate_dice_for_battle_size(battle_size=None):
    """How many D6 to roll, defaulting to config.BATTLE_SIZE.

    An unrecognised size falls back to Strike Force rather than to zero, for
    the reason game/battle_focus.py's twin gives: zero would make the whole
    detachment rule silently inert, which reads as a bug in the rule rather
    than as a typo in a setting."""
    key = (battle_size or config.BATTLE_SIZE or "").strip().lower().replace(" ", "_")
    return FATE_DICE_BY_BATTLE_SIZE.get(key, FATE_DICE_BY_BATTLE_SIZE["strike_force"])


class FateDicePool:
    """The Fate dice pool plus the CP discount it pays for.

    Implements the cost-discount protocol game/stratagems.py consults
    (available_discount/consume), so StratagemController never learns that
    this rule exists - the same arrangement Commander Farsight's Puretide's
    Teachings already uses."""

    def __init__(self, players=None, battle_size=None, game_log=None, armed=True):
        if players is None:
            players = config.SEER_COUNCIL_PLAYERS
        self.players = tuple(players)
        self.battle_size = battle_size
        self.game_log = game_log
        # Whether a matching die is spent automatically - see the module
        # docstring. False makes the pool inert as a discount while still
        # showing in the panel, which is what a per-use choice would need.
        self.armed = armed
        self.dice = {player: [] for player in self.players}
        self._rolled = False

    # ------------------------------------------------------------- lifecycle

    def sync_battle_round(self, battle_round):
        """Roll the pool at the start of the FIRST battle round, once.

        Idempotent and safe to call on every phase change, like
        BattleFocusPool.sync_battle_round() - but note the difference: this one
        never rolls again. Nothing refills a Fate dice pool, so a second roll
        would not be a refresh, it would be a whole new pool.

        Rolled through game.dice's own random so a test can script the faces
        (testkit.script()); NOT through DiceManager, which holds a single
        pending roll that has to be acknowledged - injecting one into the
        battle's opening moment would collide with the pre-game sequence's own
        roll-offs. The result is logged instead, and the panel shows the pool
        for the rest of the battle."""
        if self._rolled or not self.players or not battle_round:
            return
        self._rolled = True
        count = fate_dice_for_battle_size(self.battle_size)
        for player in self.players:
            faces = sorted(dice_module.random.randint(1, 6) for _ in range(count))
            self.dice[player] = faces
            self._log(
                f"{player}: Strands of Fate - {count} Fate dice rolled: "
                + ", ".join(f"{v} ({STRATAGEM_BY_FATE_VALUE[v]})" for v in faces)
                + "."
            )

    # ------------------------------------------------------------ inspection

    def pool(self, player):
        return list(self.dice.get(player, ()))

    def count_of(self, player, value):
        return self.dice.get(player, []).count(value)

    def summary_rows(self, player):
        """(value, count, stratagem name) per distinct face still held, low to
        high - what the right-hand panel draws, so the display and the rule
        cannot disagree about which stratagem a die is worth anything to."""
        held = self.dice.get(player, [])
        return [
            (value, held.count(value), STRATAGEM_BY_FATE_VALUE[value])
            for value in sorted(set(held))
        ]

    # --------------------------------------------- cost-discount protocol

    def _value_for(self, stratagem):
        name = getattr(stratagem, "name", stratagem)
        return FATE_VALUE_BY_STRATAGEM.get(name)

    def available_discount(self, player, stratagem, targets=()):
        """How much this use's CP cost drops. A pure query - asking never
        discards a die (StratagemController relies on that: it prices a use
        while merely deciding whether to offer it)."""
        if not self.armed:
            return 0
        value = self._value_for(stratagem)
        if value is None:
            return 0
        if self.count_of(player, value) < 1:
            return 0
        return FATE_DICE_DISCOUNT_CP

    def consume(self, player, stratagem, targets=()):
        """Discard the die - called only once a discounted use has actually
        been paid for."""
        if self.available_discount(player, stratagem, targets) <= 0:
            return
        value = self._value_for(stratagem)
        self.dice[player].remove(value)
        name = getattr(stratagem, "name", stratagem)
        self._log(
            f"{player}: Strands of Fate - discards a Fate die showing {value} "
            f"to reduce {name} by {FATE_DICE_DISCOUNT_CP}CP "
            f"({len(self.dice[player])} Fate dice left)."
        )

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
