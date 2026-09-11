"""Engrammatic Logic - the Royal Warden's own ability.

RULE (printed, word for word):

  "Once per battle, at the start of any phase, you can select one friendly
   NECRONS unit that is Battle-shocked and within 12" of this model. That unit
   is no longer Battle-shocked."

The machine is game/end_battle_shock.py's - extracted at this, its second
carrier, from the Kroot War Shaper's Root of Honour, which prints the same
sentence with "KROOT" for "NECRONS". This file is the one word that differs.

THE KEYWORD IS READ OFF THE MODELS, via the reanimation_protocols flag: the
army rule is printed on every Necron datasheet, so its flag IS the faction
test - the reading game/illuminor.py, game/spyder_wargear.py and
game/multi_threat_eliminator.py all settled on for the identical phrase. (There
is a second reading in this faction, awakened_dynasty.is_necrons_unit(), which
asks the DATASHEET's keyword; the two agree on every built datasheet and the
divergence is recorded in game/grand_illusion.py. The per-model flag is the one
used here because the base asks its target test per MODEL.)
"""

from game.end_battle_shock import EndBattleShockController

ENGRAMMATIC_LOGIC_LABEL = "Engrammatic Logic"


class EngrammaticLogicController(EndBattleShockController):
    bearer_flag = "engrammatic_logic"
    target_flag = "reanimation_protocols"
    label = ENGRAMMATIC_LOGIC_LABEL
    log_tag = "engrammatic logic"
