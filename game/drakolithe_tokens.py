"""How many Drakolithe tokens a unit starts the battle with.

Split from game/drakolithe.py, which spends them, because the two answer
different questions at different times: this one runs once at build_squad()
and the other runs every time an enemy moves. Same split game/aspect_shrine.py
makes for its own tokens, and this follows that module's shape exactly.

TWO PRINTED SOURCES, ONE COUNT:

  Dragon Knights  wargear: "For every 3 models in this unit, this unit can be
                  equipped with 2 Drakolithe."
  Leystalker      equipped with: "2 Drakolithe" - flat, on its own line.

GRANTED RATHER THAN OFFERED. It is free, it has no downside, and there is no
army-building step to choose it in - the same reasoning game/aspect_shrine.py
records for the Aspect Shrine tokens, which are granted here too.

READ OFF STARTING STRENGTH, not the live model count: the tokens are placed
"next to the unit" at the start of the battle, so losing models later does not
take them away. That is also why they are counted at build time rather than
being derived on demand.
"""

#: "For every 3 models in this unit, ... 2 Drakolithe."
DRAGON_KNIGHT_MODELS_PER_GRANT = 3
DRAGON_KNIGHT_TOKENS_PER_GRANT = 2

#: The Leystalker's flat pair, printed on its equipment line.
LEYSTALKER_TOKENS = 2


def grant_tokens(squad):
    """Set Squad.drakolithe_tokens. A no-op for a unit without the ability, so
    build_squad() can call it unconditionally."""
    models = getattr(squad, "models", None) or ()
    bearers = [m for m in models if getattr(m.profile, "drakolithe", False)]
    if not bearers:
        return 0
    # A single-model bearer is the Leystalker's flat pair; a multi-model unit
    # is the Dragon Knights' per-three grant. Keyed on the printed COMPOSITION
    # rather than on the datasheet name, so neither is spelled out twice.
    if len(models) == 1:
        tokens = LEYSTALKER_TOKENS
    else:
        tokens = ((len(models) // DRAGON_KNIGHT_MODELS_PER_GRANT)
                  * DRAGON_KNIGHT_TOKENS_PER_GRANT)
    squad.drakolithe_tokens = tokens
    return tokens
