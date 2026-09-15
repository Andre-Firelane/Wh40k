"""Boyz' Never Too Busy to Fight (2026-09 Ork codex).

RULE (verbatim, rules/orks/Boyz.md):
  "Never Too Busy to Fight: Being engaged does not prevent this unit from being
   eligible to start an action."

Read by game/actions.py's start_eligibility(), beside rule 16.01's TITANIC
exception to the same "engaged" clause. Only that clause: every other 16.01
condition (battle-shocked, OC 0, Fell Back, Advanced, one action per turn) still
applies.
"""

from game.squad import unit_wide_ability

NEVER_TOO_BUSY_NAME = "Never Too Busy to Fight"


def applies(squad):
    return squad is not None and bool(unit_wide_ability(squad, "never_too_busy_to_fight"))
