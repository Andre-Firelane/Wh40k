"""The battle size, and a table keyed by it.

THIRD CONSUMER, so it is extracted. Three printed rules scale with the battle
size and each kept its own copy of the same three lines:

  * game/battle_focus.py        - Battle Focus tokens (Incursion 2, Strike Force 4,
                                  Onslaught 6)
  * game/ride_the_wind.py       - Windrider Host's withdrawal cap (1 / 2 / 3)
  * game/hypercrypt_hyperphasing.py - Hypercrypt Legion's Hyperphasing cap (1 / 2 / 3)

What they share is not the numbers - those are each rule's own printed table -
but the READING of config.BATTLE_SIZE: case- and space-insensitive, and an
unknown size falls back to Strike Force rather than to zero. Zero would make a
rule silently inert, which reads exactly like a bug in the rule instead of like
a typo in a setting; both earlier copies wrote that reasoning out, and a third
copy is the drift this repo consolidates at the second consumer.
"""

from game import config

INCURSION = "incursion"
STRIKE_FORCE = "strike_force"
ONSLAUGHT = "onslaught"

BATTLE_SIZES = (INCURSION, STRIKE_FORCE, ONSLAUGHT)

#: What an unknown or empty setting reads as. Not zero - see the module docstring.
DEFAULT_BATTLE_SIZE = STRIKE_FORCE


def normalize(battle_size=None):
    """The table key for `battle_size`, defaulting to config.BATTLE_SIZE."""
    key = (battle_size or config.BATTLE_SIZE or "").strip().lower().replace(" ", "_")
    return key if key in BATTLE_SIZES else DEFAULT_BATTLE_SIZE


def lookup(table, battle_size=None):
    """`table[size]`, where `table` is a rule's own printed battle-size table.

    An unknown size reads the Strike Force row, and so does a size the table
    happens not to list - the same fallback both earlier copies used."""
    return table.get(normalize(battle_size), table[DEFAULT_BATTLE_SIZE])
