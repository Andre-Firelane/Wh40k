"""Meganobz' Krumpin' Time (2026-09 Ork codex).

RULE (verbatim, rules/orks/Meganobz.md):
  "Krumpin' Time: In the Fight phase, if this unit is riled up, this unit has
   +1 to hit rolls."

A Hit-roll Modifier (-1 on the threshold) in FightController._hit_modifiers().
"In the Fight phase" is structural - game/shooting.py does not read it. "Riled
up" is game/riled_up.py's is_riled_up(), the one question every reader asks.
Unit-wide (rule 19.04), so a Warboss in Mega Armour leading the Meganobz hits
with the same bonus.
"""

from game import riled_up
from game.modifiers import Modifier
from game.squad import unit_wide_ability

KRUMPIN_TIME_NAME = "Krumpin' Time"
KRUMPIN_TIME_HIT_BONUS = 1


def applies(squad):
    return (squad is not None and bool(unit_wide_ability(squad, "krumpin_time"))
            and riled_up.is_riled_up(squad))


def hit_modifiers(squad):
    return [Modifier(-KRUMPIN_TIME_HIT_BONUS, KRUMPIN_TIME_NAME)] if applies(squad) else []
