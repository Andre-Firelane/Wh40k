"""Grand Strategist - Imotekh the Stormlord's own ability.

RULE (printed, word for word):

  "At the start of your Command phase, if this model is on the battlefield,
   you gain 1CP."

Eldrad Ulthran's Diviner of Futures prints that sentence word for word, so the
machine is game/command_phase_cp.py's - extracted at this, its second carrier.
This file is the flag and the label.

IT SHARES THE HOUSE-RULE CAP RATHER THAN ADDING TO IT. gain_cp()'s
BONUS_CP_PER_ROUND_CAP is across all such abilities combined, so an army with
Imotekh gains one bonus CP per battle round, not one per ability - and Imotekh
alongside Gretchin still gains one. Enforced centrally, which is why this file
does not have to know about it.
"""

from game.command_phase_cp import CommandPhaseCpController

GRAND_STRATEGIST_REASON = "Grand Strategist"


class GrandStrategistController(CommandPhaseCpController):
    flag = "grand_strategist"
    reason = GRAND_STRATEGIST_REASON
