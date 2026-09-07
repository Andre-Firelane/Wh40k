"""Does declining the Advance re-roll end it, in the REAL main() loop?

User: "im letzten spiel wurde ich immer wieder gefragt, ob ich den advance
rerollen will mit den destroyern. es war eine schleife bis ich ihn gererollt
habe."

WHY THIS NEEDS THE REAL LOOP AND NOT JUST THE CONTROLLER. The loop is a
property of main.py's chain, not of either ability: the branch that clicks a
die away offers the re-roll first and then does `if decision_manager.is_pending:
continue`, so the roll is deliberately NOT acknowledged while a prompt is open
(it has to be - acknowledge() clears pending_values and reroll_die() then
refuses to throw anything). Declining therefore left exactly the board that
raised the question. A controller test can show the offer is booked; only the
chain can show that the NEXT click now gets through to acknowledge().

WHY THE FACT IS STAGED. Protocol of the Sudden Storm is a 1 CP Stratagem whose
Advance re-roll needs a CHARACTER leading, and a MockAgent run does not reach
"bought it, then advanced, then a human clicked the die" in a fixed frame budget
(this repo's documented harness limit). A passive counter would report 0 and
read like a pass. So this reaches into main()'s own frame, grants the re-roll to
a real led unit and puts a real Advance roll on the table - and everything after
that is the game: real mouse clicks, the real event chain, the real controllers.

Usage:  python verify_advance_reroll_loop.py [map2] [--neutralize]
        --neutralize restores the pre-fix world (an offer is never booked) and
        MUST report the loop: asked again and again, die never acknowledged.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import runpy

import pygame

MAP = "map2"
NEUTRALIZE = "--neutralize" in sys.argv
for arg in sys.argv[1:]:
    if arg.startswith("map"):
        MAP = arg

from game import config                                  # noqa: E402
from game import protocol_sudden_storm as ss             # noqa: E402
from game.decision import DecisionManager                # noqa: E402
from game.dice import ADVANCE_ROLL, DiceManager          # noqa: E402

config.PLAYER1_ARMY = "necrons"     # the human plays Necrons - the report
config.PLAYER2_ARMY = "necrons"
config.ARMY_SELECT = False
config.MAP_SELECT = False
config.MAP = MAP

STAGE_AT = 300      # frame to stage on - well past the pre-game
FRAMES = 420

if NEUTRALIZE:
    # The pre-fix world, at the source: an offer is never booked, so the same
    # roll can be offered forever.
    DiceManager.claim_reroll_offer = (
        lambda self, source: self.pending_values is not None)

SEEN = {"offers": 0, "declines": 0, "acknowledged": False,
        "staged": False, "unit": None}

# --- spies ------------------------------------------------------------------

_real_request = DecisionManager.request


def spy_request(self, player, prompt, options, **kwargs):
    if "re-roll it?" in prompt:
        SEEN["offers"] += 1
    return _real_request(self, player, prompt, options, **kwargs)


DecisionManager.request = spy_request

_real_ack = DiceManager.acknowledge


def spy_ack(self):
    if SEEN["staged"] and self.roll_kind == ADVANCE_ROLL:
        SEEN["acknowledged"] = True
    return _real_ack(self)


DiceManager.acknowledge = spy_ack



# --- staging ----------------------------------------------------------------

def stage(locals_):
    """Grant the re-roll to a real led unit of the human and roll an Advance."""
    ai = set(locals_["ai_players"])
    human = next((p for p in sorted(locals_["armies"]) if p not in ai), None)
    for squad in sorted(locals_["state"].all_squads(), key=lambda s: s.name):
        if squad.owner != human:
            continue
        squad.sudden_storm_advance_reroll = True
        if not ss.advance_reroll_available(squad):   # needs a CHARACTER leading
            squad.sudden_storm_advance_reroll = False
            continue
        SEEN["unit"] = squad.name
        locals_["movement_controller"].selected_squad = squad
        locals_["dice_manager"].roll(1, 6, label="Advance", roll_kind=ADVANCE_ROLL,
                                     target_squad=squad, subject_label="Advancing")
        SEEN["staged"] = True
        return True
    return False


def drive():
    board = {}
    frames = {"n": 0}
    real_flip = pygame.display.flip

    def flip(*args, **kwargs):
        frames["n"] += 1
        frame = sys._getframe(1)
        while frame is not None and frame.f_code.co_name != "main":
            frame = frame.f_back
        if frame is not None:
            locals_ = frame.f_locals
            if not SEEN["staged"] and frames["n"] >= STAGE_AT:
                if stage(locals_):
                    board["rect"] = locals_["board_rect_screen"]
                    board["dm"] = locals_["decision_manager"]
                    board["squad"] = locals_["movement_controller"].selected_squad
                    # Wrap selfplay's pump HERE, not before runpy: selfplay
                    # REPLACES pygame.event.get on import, so a pump installed
                    # earlier is silently overwritten and reports honest-looking
                    # zeroes (this repo's documented harness trap).
                    inner = pygame.event.get

                    def pump(*a, **kw):
                        events = inner(*a, **kw)
                        if SEEN["staged"] and not SEEN["acknowledged"]:
                            # REPLACE the frame's events rather than adding to
                            # them: selfplay clicks the board itself every
                            # frame, and one of those would resolve exactly what
                            # is being measured.
                            r = board["rect"]
                            return [pygame.event.Event(
                                pygame.MOUSEBUTTONDOWN, button=1,
                                pos=(r.centerx, r.centery))]
                        return events

                    pygame.event.get = pump
            elif SEEN["staged"]:
                # HOLD THE SELECTION. main.py reads
                # movement_controller.selected_squad to know whose Advance is
                # on the table, and selfplay drives the AI in parallel, which
                # calls select(None) between frames - a harness artefact, not
                # the game: a human who just advanced still has their unit
                # selected. Without this the branch measures a click with no
                # unit and reports an honest-looking zero.
                if not SEEN["acknowledged"] and board.get("squad") is not None:
                    locals_["movement_controller"].selected_squad = board["squad"]
                # Answer our own prompt with "Keep it" - the answer that used to
                # change nothing at all.
                dm = board.get("dm")
                if dm is not None and dm.is_pending and "re-roll it?" in dm.prompt:
                    SEEN["declines"] += 1
                    dm.choose(len(dm.options) - 1)
        return real_flip(*args, **kwargs)

    pygame.display.flip = flip
    sys.argv = ["selfplay.py", MAP, str(FRAMES)]
    try:
        runpy.run_module("selfplay", run_name="__main__")
    except SystemExit:
        pass
    finally:
        pygame.display.flip = real_flip


drive()

print("\n" + "=" * 74)
print("mode:", "NEUTRALIZED (pre-fix world)" if NEUTRALIZE else "fixed")
print("=" * 74)
if not SEEN["staged"]:
    print("FAILED: never staged an Advance roll - this measured nothing")
    raise SystemExit(1)
print("unit                         : %s" % SEEN["unit"])
print("re-roll prompts raised        : %d" % SEEN["offers"])
print("times the human said Keep it  : %d" % SEEN["declines"])
print("the Advance die was cleared   : %s" % SEEN["acknowledged"])

if NEUTRALIZE:
    ok = SEEN["offers"] > 1 and not SEEN["acknowledged"]
    print("\n" + ("PASS - reproduced: asked again and again, the die never cleared"
                  if ok else "FAIL - the pre-fix world was not restored"))
else:
    ok = SEEN["offers"] == 1 and SEEN["declines"] == 1 and SEEN["acknowledged"]
    print("\n" + ("PASS - asked once, declined, and the roll cleared"
                  if ok else "FAIL"))
sys.exit(0 if ok else 1)
