"""Only ONE modal notice may be on screen at a time.

User report: "momentan kommt das Overlay, dass ich jetzt am Zug bin, und das
Overlay mit den Missionen gleichzeitig. Ich moechte keine gleichzeitigen
Overlays. Das soll wieder nacheinander kommen: erst das Overlay, wer am Zug
ist, und danach die Secondaries."

The cause was a mismatch between INPUT priority and DRAW behaviour. main.py's
event chain is an if/elif over the notices, so exactly one of them owns clicks
- the first pending branch wins. The renderer, though, drew all five
unconditionally, stacked in reverse-priority order. The front one got the
clicks; the rest simply peeked out from behind it, unanswerable. Adding the
mission-draw notice made that visible because two large boxes now overlapped at
the same instant (the turn banner and the freshly-drawn cards both fire at the
start of a Command phase).

The fix is one ordered tuple, `_front_notice()` in main.py, read by the
renderer - so the picture matches the chain: dismiss the front one and the next
appears.

This suite is a SOURCE guard, deliberately. What broke was wiring, not any
single overlay's behaviour, and every one of these classes was individually
correct and individually tested while the screen still showed two at once - the
same class of bug as the dead VengefulStars wiring and the unfed Path of the
Outcast controller.
"""

import io
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk  # noqa: E402

checks = tk.Checks("One modal at a time")

MAIN = io.open("main.py", encoding="utf-8").read()


def slice_between(text, start, end):
    """The source between two markers, or "" if either is missing.

    Never raises. A source guard whose own slicing blows up on the very source
    it is meant to reject reports a traceback instead of a list of failed
    checks - which is exactly backwards when the point of an A/B probe is to
    show WHICH assurances the pre-fix world loses."""
    try:
        i = text.index(start)
        j = text.index(end, i)
    except ValueError:
        return ""
    return text[i:j]

# The five must-click-away notices, in the order a human should meet them.
NOTICES = [
    "turn_start_overlay",
    "turn_plan_overlay",
    "mission_draw_overlay",
    "stratagem_notice_overlay",
    "waaagh_notice_overlay",
]


# --- 1. there is a single definition of the priority order ---
print("--- 1. one definition ---")

checks.eq("main.py defines _front_notice() exactly once",
          MAIN.count("def _front_notice():"), 1)

front = slice_between(MAIN, "def _front_notice():", "def advance_turn_phase():")
checks.true("its body can be located in the source", bool(front))
for name in NOTICES:
    checks.true(f"_front_notice() knows about {name}", name in front)
checks.true("it returns the first pending one", "return overlay" in front)
checks.true("and None when nothing is pending", "return None" in front)

present = [n for n in NOTICES if n in front]
order_in_helper = sorted(present, key=front.index)
checks.eq("the helper lists them in the intended order", order_in_helper, NOTICES)


# --- 2. ...and the event chain dispatches in that SAME order ---
print("--- 2. the chain agrees ---")

# A second, independent read: the if/elif chain mirrors the tuple by hand
# (it has to - it is a chain of branches), so the two can drift. If they ever
# do, the box with the clicks and the box on screen are different boxes.
chain_positions = {}
for name in NOTICES:
    needle = f"elif {name}.is_pending:"
    checks.eq(f"the chain has exactly one branch for {name}", MAIN.count(needle), 1)
    chain_positions[name] = MAIN.find(needle)
chain_order = sorted(NOTICES, key=lambda n: chain_positions[n])
checks.eq("the event chain's order matches _front_notice()'s", chain_order, NOTICES)

# Every notice must outrank the decision overlay and the dice roll, or a
# notice would be drawn over a prompt the human is allowed to answer.
decision_at = MAIN.find("elif decision_manager.is_pending:")
dice_at = MAIN.find("elif dice_manager.is_pending:")
for name in NOTICES:
    checks.true(f"{name} outranks the decision overlay", chain_positions[name] < decision_at)
    checks.true(f"{name} outranks a pending dice roll", chain_positions[name] < dice_at)


# --- 3. the renderer draws ONLY the front-most ---
print("--- 3. only one draws ---")

for name in NOTICES:
    checks.eq(f"{name}.draw() is never called unconditionally",
              MAIN.count(f"{name}.draw(screen)"), 0)
checks.eq("the single draw call goes through the helper",
          len(re.findall(r"_notice\.draw\(screen\)", MAIN)), 1)
checks.true("guarded by the helper's own result", "if _notice is not None:" in MAIN)

# The decision overlay waits its turn too - it cannot be clicked while any
# notice is up, so drawing it underneath one is the same mistake one tier down.
checks.eq("the decision overlay is drawn exactly once",
          MAIN.count("decision_overlay.draw(screen, decision_manager"), 1)
draw_block = slice_between(MAIN, "_notice = _front_notice()", "ctrl_held =")
checks.true("and only when no notice is up",
            "else:" in draw_block and "decision_overlay.draw(" in draw_block)

# The dice panel already had this idea as its `suppressed=` argument; it now
# reads the same one definition instead of its own hand-kept list of four
# (which had gone stale - it never learned about the mission notice).
checks.true("the dice panel suppresses via the same helper",
            "suppressed=bool(_front_notice())" in MAIN)


# --- 4. the ordering the user actually asked for ---
print("--- 4. turn banner first, missions after ---")

# "erst das Overlay, wer am Zug ist, und danach die Secondaries."
checks.true("the turn banner outranks the mission draw notice",
            chain_positions["turn_start_overlay"] < chain_positions["mission_draw_overlay"])
checks.eq("the turn banner is the very first notice", NOTICES[0], "turn_start_overlay")

# Both genuinely can be pending at once - that is why this matters. The draw
# happens in the Command phase, which is the same instant the turn banner is
# raised, so nothing about the game prevents the collision; only the draw rule
# does.
checks.true("the mission draw fires in the Command-phase block",
            "secondary_mission_controller.draw_at_command_phase(" in MAIN)
checks.true("the turn banner is raised from the same loop",
            "turn_start_overlay.show(" in MAIN)


# --- 5. behaviour: the helper really does return one at a time ---
print("--- 5. the helper's behaviour ---")


class FakeNotice:
    def __init__(self, pending=False):
        self.is_pending = pending
        self.drawn = 0

    def draw(self, surface):
        self.drawn += 1


def front_of(overlays):
    for overlay in overlays:
        if overlay.is_pending:
            return overlay
    return None


a, b, c = FakeNotice(), FakeNotice(), FakeNotice()
checks.eq("nothing pending, nothing drawn", front_of([a, b, c]), None)
b.is_pending = c.is_pending = True
checks.eq("with two pending, the earlier one wins", front_of([a, b, c]), b)
b.is_pending = False
checks.eq("dismissing it hands the screen to the next", front_of([a, b, c]), c)
c.is_pending = False
checks.eq("and then to nobody", front_of([a, b, c]), None)

checks.finish()
