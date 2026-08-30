"""The left panel names the units that still owe a Pile In (rule 12.03).

User: "ich finde es manchmal schwierig zu erkennen, dass ich noch mit allen
einheiten pile in machen muss, bevor die KI weitermacht. kann das vielleicht
in der linken spalte stehen, dass ich noch einheiten habe, mit denen ich noch
pile ins machen muss?"

Measured before changing anything: the panel printed exactly one sentence -
"Both players must resolve Pile In (move or skip) for every eligible unit
before the Fight step can begin." It names no unit, no side and no next step,
so a game waiting on the HUMAN reads identically to one waiting on the AI.

Two halves, tested separately because they fail separately:
  1. the QUESTION - PileInController.squads_pending_pile_in();
  2. what the PANEL does with it, driven through the real ActionPanel rather
     than by re-deriving the string, since a screen unreachable behind a
     state gate is this repo's recurring UI bug (see test_scout_move_ui.py).
"""
import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from game import config, fight as fight_mod
from game.decision import DecisionManager
from game.dice import DiceManager
from game.fight import FightController
from game.movement import MovementController
from game.pile_in import PileInController
from game.shooting import ShootingController
from game.turn import PHASES, PHASE_FIGHT, PHASE_CHARGE, TurnTracker
from game.factions.aeldari import STORM_GUARDIANS, HOWLING_BANSHEES
from game.factions.orks import BOYZ
from game.ui import action_panel as ap
from game.ui.action_panel import ActionPanel

c = tk.Checks("Pile In - the left panel says who still owes one")

HUMAN = "Player 1"
AI = "Player 2"


def section(title):
    print(f"\n--- {title} ---")


pygame.init()
pygame.display.set_mode((1200, 800))


def scene(units, phase=PHASE_FIGHT):
    """`units` is [(datasheet, owner, name, y), ...] - y decides engagement."""
    state = tk.GameState()
    turn = TurnTracker(first_player=HUMAN)
    turn.phase_index = PHASES.index(phase)
    turn.turn_owner = HUMAN
    turn.set_active(HUMAN)

    squads = []
    for sheet, owner, name, y in units:
        squad = tk.build(sheet, owner, name=name)
        tk.line_up(squad, y=y)
        for model in squad.models:
            state.add_token(model)
        squads.append(squad)

    log, dice, dec = tk.Log(), DiceManager(), DecisionManager()
    move = MovementController(turn_tracker=turn, all_tokens=state.tokens, game_log=log,
                              dice_manager=dice, obstacles=[])
    pile_in = PileInController(game_log=log, turn_tracker=turn, all_tokens=state.tokens,
                               movement_controller=move)
    fight = FightController(dice_manager=dice, turn_tracker=turn, all_tokens=state.tokens,
                            decision_manager=dec, game_log=log, pile_in_controller=pile_in)
    shoot = ShootingController(turn_tracker=turn, all_tokens=state.tokens, dice_manager=dice)
    return dict(state=state, turn=turn, move=move, pile_in=pile_in, fight=fight,
                shoot=shoot, squads=squads)


# Two engaged human units and two engaged AI units - the reported situation.
TWO_V_TWO = [
    (STORM_GUARDIANS, HUMAN, "1 Storm Guardians 1", 20.0),
    (HOWLING_BANSHEES, HUMAN, "1 Howling Banshees 1", 26.0),
    (BOYZ, AI, "2 Boyz 1", 21.2),
    (BOYZ, AI, "2 Boyz 2", 27.2),
]


# ------------------------------------------------ 1. who still owes a pile-in

section("1. PileInController.squads_pending_pile_in()")

sc = scene(TWO_V_TWO)
pile_in = sc["pile_in"]
human_a, human_b, ai_a, ai_b = sc["squads"]

c.true("something is pending at all", pile_in.has_pending_squads())
c.eq("every engaged unit is listed", [s.name for s in pile_in.squads_pending_pile_in()],
     sorted([human_a.name, human_b.name, ai_a.name, ai_b.name]))
c.eq("asked per player, the human's are separable",
     [s.name for s in pile_in.squads_pending_pile_in(HUMAN)],
     sorted([human_a.name, human_b.name]))
c.eq("...and so are the AI's", [s.name for s in pile_in.squads_pending_pile_in(AI)],
     sorted([ai_a.name, ai_b.name]))

# Sorted, because _all_squads() is a set and the panel prints these.
names = [s.name for s in pile_in.squads_pending_pile_in()]
c.eq("sorted by name, not by set iteration order", names, sorted(names))
pile_src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "game", "pile_in.py"),
                   encoding="utf-8").read()
c.true("...and the sort is in the source, not left to the set's luck",
       "key=lambda s: s.name" in pile_src)

# One filter, two questions: has_pending_squads() must keep agreeing with the
# list, and must keep its short-circuit rather than building one.
c.true("has_pending_squads() reads the same filter", "any(self._pending())" in pile_src)
pile_in.skip_pile_in(human_a)
c.eq("a skipped unit drops off the list",
     [s.name for s in pile_in.squads_pending_pile_in(HUMAN)], [human_b.name])
c.true("...and something is still pending overall", pile_in.has_pending_squads())
for squad in (human_b, ai_a, ai_b):
    pile_in.skip_pile_in(squad)
c.eq("all skipped: the list is empty", pile_in.squads_pending_pile_in(), [])
c.eq("...and the two answers still agree", pile_in.has_pending_squads(), False)

# 12.03 eligibility is unchanged: out of the Fight phase, nobody owes one.
out_of_phase = scene(TWO_V_TWO, phase=PHASE_CHARGE)
c.eq("nothing is pending outside the Fight phase",
     out_of_phase["pile_in"].squads_pending_pile_in(), [])

# An unengaged unit owes nothing either.
apart = scene([
    (STORM_GUARDIANS, HUMAN, "1 Storm Guardians 1", 20.0),
    (BOYZ, AI, "2 Boyz 1", 21.2),
    (HOWLING_BANSHEES, HUMAN, "1 Howling Banshees far", 45.0),
])
c.eq("a unit nowhere near an enemy is not listed",
     [s.name for s in apart["pile_in"].squads_pending_pile_in(HUMAN)], ["1 Storm Guardians 1"])


# ------------------------------------------------------ 2. what the panel says

section("2. the real ActionPanel")

panel = ActionPanel()
surface = pygame.display.get_surface()
rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 700)

_real_box = ActionPanel._draw_message_box
_real_text = ActionPanel._draw_text


def _capture(sc, selected=None):
    """Draw the panel for real and return (message-box lines, loose lines,
    button count). Spies on the two text sinks rather than OCRing pixels;
    section 2b checks that something is actually painted."""
    lines, loose = [], []

    def spy_box(self, surf, r, bw, y, messages, tc, bc, bg_color=None):
        lines.extend(messages)
        return _real_box(self, surf, r, bw, y, messages, tc, bc, bg_color=bg_color)

    def spy_text(self, surf, r, text, y, color=None, font=None, gap=4):
        loose.append(text)
        return _real_text(self, surf, r, text, y, color=color, font=font, gap=gap)

    ActionPanel._draw_message_box = spy_box
    ActionPanel._draw_text = spy_text
    try:
        surface.fill((0, 0, 0))
        sc["move"].select(selected.models[0] if selected is not None else None)
        panel.draw(surface, rect, sc["move"], sc["shoot"],
                   pile_in_controller=sc["pile_in"], fight_controller=sc["fight"])
    finally:
        ActionPanel._draw_message_box = _real_box
        ActionPanel._draw_text = _real_text
    return lines, loose, len(panel._buttons)


sc = scene(TWO_V_TWO)
lines, loose, _ = _capture(sc)
blob = " | ".join(lines)

# The reported gap, closed: the panel now says HOW MANY, WHOSE, and WHAT NEXT.
c.true("it says how many are outstanding", "4 unit(s)" in blob)
c.true("the human's own units are named",
       "Player 1: 1 Howling Banshees 1, 1 Storm Guardians 1" in blob)
c.true("the AI's are named too, so 'is it me?' is answerable",
       "Player 2: 2 Boyz 1, 2 Boyz 2" in blob)
c.true("it says what to do next",
       any("Select one on the battlefield" in line for line in lines))
c.true("rule 12.03 is cited, like every other status line here", "12.03" in blob)

# The old generic sentence is gone - it was the whole complaint.
c.eq("the old say-nothing sentence is gone",
     sum("Both players must resolve" in line for line in lines + loose), 0)

# Once the human is done, only the AI's line remains - which is how "I am
# finished, it is waiting on the AI" now reads.
for squad in sc["pile_in"].squads_pending_pile_in(HUMAN):
    sc["pile_in"].skip_pile_in(squad)
lines, _, _ = _capture(sc)
blob = " | ".join(lines)
c.true("the human's line is gone once they are done", "Player 1:" not in blob)
c.true("...and the AI's is still there", "Player 2: 2 Boyz 1, 2 Boyz 2" in blob)
c.true("...and the count follows", "2 unit(s)" in blob)

# Nothing outstanding: back to the Begin Fight Step screen, untouched.
for squad in sc["pile_in"].squads_pending_pile_in():
    sc["pile_in"].skip_pile_in(squad)
lines, loose, buttons = _capture(sc)
c.eq("no pile-in box once everything is resolved",
     sum("Pile In pending" in line for line in lines), 0)
c.true("...and the old 'resolved' line takes over",
       any("Pile In resolved" in line for line in loose))
c.true("...with the Begin Fight Step button", buttons >= 1)

# The status is still shown WITH a squad selected - a previous user report
# ("the AI just stopped doing anything") is what put it there, and this
# change must not quietly undo it.
sc2 = scene(TWO_V_TWO)
lines, _, buttons = _capture(sc2, selected=sc2["squads"][0])
c.true("the pile-in box also shows with a unit selected",
       any("Pile In pending" in line for line in lines))
c.true("...and that unit's own buttons are still offered", buttons >= 2)

# The cap. Six engaged human units, four names plus "+2 more".
many = [(BOYZ, AI, "2 Boyz 1", 21.2)]
many += [(HOWLING_BANSHEES, HUMAN, f"1 Banshees {i}", 20.0) for i in range(1, 7)]
sc3 = scene(many)
c.eq("six human units really are pending",
     len(sc3["pile_in"].squads_pending_pile_in(HUMAN)), 6)
lines, _, _ = _capture(sc3)
blob = " | ".join(lines)
c.true("the overflow is announced", "+2 more" in blob)
# Named individually, not just "+2 more" somewhere: an early version of this
# check passed with all six names still printed AND "+2 more" tacked on the
# end, because the cap had been removed but the suffix left behind. Caught by
# the A/B probe, which is what those are for.
human_line = next((l for l in lines if l.startswith("Player 1:")), "")
c.eq(f"only {ap.PILE_IN_NAMES_SHOWN} names are listed",
     sum(f"1 Banshees {i}" in human_line for i in range(1, 7)), ap.PILE_IN_NAMES_SHOWN)
c.true("...and it is the LAST ones that are dropped, not a random subset",
       "1 Banshees 4" in human_line and "1 Banshees 5" not in human_line)
c.true("...but the total count is still honest", "7 unit(s)" in blob)


section("2b. it is actually painted")

sc4 = scene(TWO_V_TWO)
before = pygame.Surface(rect.size)
before.fill((0, 0, 0))
surface.fill((0, 0, 0))
sc4["move"].select(None)
panel.draw(surface, rect, sc4["move"], sc4["shoot"],
           pile_in_controller=sc4["pile_in"], fight_controller=sc4["fight"])
painted = surface.subsurface(rect).copy()
c.true("the panel is not blank",
       pygame.image.tobytes(painted, "RGB") != pygame.image.tobytes(before, "RGB"))
# The accent is on screen, so the box reads as a thing to DO rather than as
# more of the flat grey phase chatter around it.
found = any(painted.get_at((x, y))[:3] == ap.PILE_IN_ACCENT_COLOR
            for y in range(rect.height) for x in range(0, rect.width, 2))
c.true("the pile-in accent colour is drawn", found)
c.true("...and it is not one of the colours already in use here",
       ap.PILE_IN_ACCENT_COLOR not in (ap.ERROR_COLOR, ap.DAMAGE_CHOICE_ACCENT_COLOR,
                                       ap.COHERENCY_ACCENT_COLOR))


c.finish()
