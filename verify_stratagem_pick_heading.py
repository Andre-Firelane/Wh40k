"""Runtime proof through the REAL main() loop that a board pick whose rule is a
STRATAGEM says so in its heading - in violet, with the CP cost in it.

USER: "wenn es sich umbei der fähigkeit ind er linken spalte um ein stratagem
handelt, muss schon in der überschrift durch violette farbe zu erkenn esien,
dass es sich um ein tratatgem handelt und die die CP kosten müssen auch teil
der Überschrift sein."

WHY A RUNTIME PROBE AND NOT ONLY THE SUITE. game/ui/action_panel.py runs once
per frame, and "built but never FED" has caught this repo six times: a source
guard shows the call is THERE, and test_decision_rule_panel.py renders the
panel itself. What is measured here is the panel main() ACTUALLY draws, with
the PromptRule main() actually derived from the prompt its own controller
raised - and the colours are read off the drawn pixels rather than off the
constants that produced them.

THE ARMY AND THE STAGING ARE verify_cost_of_victory_choice.py's, for the same
reasons written out there: armies/aeldari_guardian_battlehost.json fields
Guardian Battlehost and is the report's own shape, it goes on PLAYER 1 because
"end of your opponent's Fight phase" offers the side that did not just fight
(and a question about the human's panel measures the AI's army if the list is
put on the wrong side), and ONE fact is staged - that the battle reaches the
end of a Fight phase at all, which this harness cannot do passively inside a
sane frame budget (the documented MockAgent limit; a passive counter would
report 0 and look like a pass). Everything after that is real: the controller
raises its own prompt, main() resolves the rule, main() draws the panel.

NOTHING ANSWERS THE PROMPT, and that is deliberate: selfplay does not answer a
human prompt outside the pre-game, so the pick screen stays up and the panel
redraws it every remaining frame - which is exactly the state a player sits in.

--neutralize restores the PRE-FIX WORLD at the lookup: the kind and the cost
thrown away, and the heading left in the rule box as its first block, which is
what the panel had before this. The heading then falls back to the bare name in
the panel's ordinary gold.

Usage:  python verify_stratagem_pick_heading.py [map2 [frames]]
        python verify_stratagem_pick_heading.py map2 1500 --neutralize
"""

import runpy
import sys

import pygame

from game import config, prompt_rule
from game.turn import PHASE_FIGHT, PHASES, TurnTracker

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

# The Guardian Battlehost list on the HUMAN side - see the docstring.
config.PLAYER1_ARMY = "aeldari_guardian_battlehost"
config.PLAYER2_ARMY = "necrons"

stats = {"boundaries_staged": 0, "pick_screens_drawn": 0,
         "screens_whose_rule_is_a_stratagem": 0,
         "violet_fill_px": 0, "violet_letter_px": 0,
         "ordinary_navy_px": 0, "ordinary_gold_px": 0,
         "headings_carrying_the_cp_cost": 0}
seen = []
live = {"tracker": None}

_real_init = TurnTracker.__init__
_real_flip = pygame.display.flip
_real_for_prompt = prompt_rule.for_prompt


def tracker_init(self, *args, **kwargs):
    out = _real_init(self, *args, **kwargs)
    live["tracker"] = self
    return out


def flip(*args, **kwargs):
    """Park the live clock on the Fight phase - see the docstring. Repeated,
    because ending one player's Fight phase ends their TURN, so the next staged
    boundary belongs to the other player, and only the one belonging to the
    Guardian side's OPPONENT is the one the printed WHEN is about."""
    tracker = live["tracker"]
    if (tracker is not None and getattr(tracker, "started", False)
            and stats["boundaries_staged"] < 4
            and tracker.phase != PHASE_FIGHT):
        tracker.phase_index = PHASES.index(PHASE_FIGHT)
        stats["boundaries_staged"] += 1
    return _real_flip(*args, **kwargs)


def old_for_prompt(*args, **kwargs):
    """THE PRE-FIX WORLD: the lookup resolved the rule and threw away both the
    kind and the cost, and the Stratagem's heading rode along as the rule box's
    first block instead of being in the title bar."""
    rule = _real_for_prompt(*args, **kwargs)
    if not rule.is_stratagem:
        return rule
    from game.ui import rules_body
    blocks = [rules_body.Block("stratagem", rule.heading)] + list(rule.blocks)
    return prompt_rule.PromptRule(rule.name, blocks)


TurnTracker.__init__ = tracker_init
pygame.display.flip = flip
if NEUTRALIZE:
    prompt_rule.for_prompt = old_for_prompt

# Imported after the patches above so the panel picks up whichever lookup is in
# force; the spy itself wraps the real method either way.
from game.ui import button_style                            # noqa: E402
from game.ui.action_panel import ActionPanel                # noqa: E402
import game.ui.action_panel as action_panel                 # noqa: E402

_real_pick_ui = ActionPanel._draw_unit_pick_ui

TITLE_BAND = button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT
VIOLET_FILL = tuple(action_panel.STRATAGEM_HEADER_BG_COLOR)
VIOLET_TEXT = tuple(action_panel.STRATAGEM_HEADER_TEXT_COLOR)
NAVY_FILL = tuple(button_style.HEADER_BG_COLOR)
GOLD_TEXT = tuple(config.PANEL_HEADER_COLOR)


def pick_ui(self, surface, rect, pick, decision_rule=None):
    """Draw for real, then read the title band off the drawn surface.

    The band is measured on the LIVE screen the loop is painting, which is the
    difference between "the panel was asked to draw violet" and "violet is on
    the screen"."""
    out = _real_pick_ui(self, surface, rect, pick, decision_rule=decision_rule)
    if decision_rule is None:
        return out
    stats["pick_screens_drawn"] += 1
    counts = {}
    band = pygame.Rect(rect.x, rect.y, rect.width, TITLE_BAND)
    band = band.clip(surface.get_rect())
    for y in range(band.top, band.bottom):
        for x in range(band.left, band.right):
            key = surface.get_at((x, y))[:3]
            counts[key] = counts.get(key, 0) + 1
    for name, colour in (("violet_fill_px", VIOLET_FILL),
                         ("violet_letter_px", VIOLET_TEXT),
                         ("ordinary_navy_px", NAVY_FILL),
                         ("ordinary_gold_px", GOLD_TEXT)):
        stats[name] = max(stats[name], counts.get(colour, 0))
    heading = decision_rule.heading or ""
    if decision_rule.is_stratagem:
        stats["screens_whose_rule_is_a_stratagem"] += 1
    if decision_rule.cost and decision_rule.cost.upper() in heading.upper():
        stats["headings_carrying_the_cp_cost"] += 1
    line = ("heading %r | is_stratagem=%s cost=%s | violet fill %d, letters %d "
            "| navy %d, gold %d"
            % (heading, decision_rule.is_stratagem, decision_rule.cost,
               counts.get(VIOLET_FILL, 0), counts.get(VIOLET_TEXT, 0),
               counts.get(NAVY_FILL, 0), counts.get(GOLD_TEXT, 0)))
    if line not in seen:
        seen.append(line)
    return out


ActionPanel._draw_unit_pick_ui = pick_ui

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2", "1500"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- board-pick heading spy" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
for key, value in stats.items():
    print("  %-38s %s" % (key, value))
for line in seen[:6]:
    print("    " + line)
if not stats["pick_screens_drawn"]:
    print("  INCONCLUSIVE: main() never drew a board-pick screen - raise the "
          "frame budget.")
elif not stats["screens_whose_rule_is_a_stratagem"]:
    print("  the panel never saw a Stratagem behind a board pick "
          "(this is what --neutralize reports).")
