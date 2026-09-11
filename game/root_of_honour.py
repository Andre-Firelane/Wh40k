"""Kroot War Shaper's "Root of Honour".

RULE (printed, word for word):
  "Once per battle, at the start of any phase, you can select one friendly
   KROOT unit that is Battle-shocked and within 12" of this model. That unit is
   no longer Battle-shocked."

THE MACHINE MOVED OUT, one printed word stayed. The Royal Warden's Engrammatic
Logic prints this same sentence with "NECRONS" for "KROOT", so the shared half
now lives in game/end_battle_shock.py - extracted at the second carrier, as
this repo does. Its docstring carries the four conditions and why each one is a
separate way to get this wrong.

ROOT_OF_HONOUR_RANGE_IN is RE-EXPORTED rather than moved, so every existing
reader of this module keeps working unchanged.
"""

from game.end_battle_shock import (  # noqa: F401  (re-exported, see below)
    BATTLE_SHOCK_RELIEF_RANGE_IN as ROOT_OF_HONOUR_RANGE_IN,
    EndBattleShockController,
)


def war_shaper_models(squad):
    """The living models in this unit that print Root of Honour."""
    return RootOfHonourController().bearer_models(squad)


def is_kroot(squad):
    """The KROOT keyword, read off the unit's living models."""
    return RootOfHonourController().is_eligible_faction(squad)


class RootOfHonourController(EndBattleShockController):
    bearer_flag = "root_of_honour"
    target_flag = "kroot"
    label = "Root of Honour"
    log_tag = "root of honour"
