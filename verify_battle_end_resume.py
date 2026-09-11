"""Runtime probe: does the end of a REAL battle raise the statistics overlay?

User: "am Ende des Spiels soll das Statistik Overlay angezeigt werden."

A suite pins the chain and a source guard pins the call site. Neither shows
that main()'s own loop runs it - "built but never FED" has caught this repo out
eight times - so this drives selfplay.py's real main() loop and reports:

  * that main()'s own per-frame _check_battle_end() raised the score box;
  * that the resume was NOT up behind it (otherwise "it opened" measures
    nothing);
  * that a REAL MOUSEBUTTONDOWN posted into main()'s own pump dismissed the
    score box and opened the resume, with rows in it;
  * that the resume was then really DRAWN, frame after frame.

  python verify_battle_end_resume.py [map] [frames] [--neutralize]

ONE FACT IS STAGED, and here is why. A whole battle is fifty phase changes and
a MockAgent run manages about seven per three thousand frames (the documented
harness limit), so the last turn end is passively unreachable and a passive
counter would report a clean zero that reads exactly like a pass. What is
staged is `turn_tracker.battle_over` - the single flag advance_phase() would
set on the last turn of the last round. EVERYTHING after it is real: main()'s
own _check_battle_end() with its live decision gate, its own event chain, its
own overlays, and the ledger it published.

A standing prompt is answered through the pump rather than bypassed, because
_check_battle_end() deliberately waits for one (see its docstring) and
selfplay answers no prompt belonging to the human outside the pre-game - one
left open holds the battle end back for ever and swallows every click after.

--neutralize restores the pre-fix world PRECISELY: the corner STATS button
still works, and only the battle-end branch's own call site is ignored. It
must report that the resume never opened.
"""

import ast
import io
import runpy
import sys

import pygame

from game.ui.unit_stats_overlay import UnitStatsOverlay

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

R = {
    "frames": 0, "staged_at": None, "locals_at": None,
    "declined": 0, "clicks": 0,
    "score_box_raised_at": None,
    "resume_up_behind_score_box": None,
    "resume_opened_at": None, "resume_rows": None, "resume_player": None,
    "resume_drawn": 0,
    "score_box_gone_after_click": None,
    "hint": None,
    "error": None,
}

# The battle-end branch's own call site, found in the source rather than
# guessed: --neutralize has to blind THAT call and leave the corner button's
# alone, which is what makes the neutralized world the pre-fix world rather
# than a world with the feature switched off wholesale.
_SRC = io.open("main.py", encoding="utf-8").read()
_BRANCH = [n for n in ast.walk(ast.parse(_SRC))
           if isinstance(n, ast.If) and isinstance(n.test, ast.Attribute)
           and n.test.attr == "is_pending" and isinstance(n.test.value, ast.Name)
           and n.test.value.id == "battle_end_overlay"]
BATTLE_END_LINES = set()
if _BRANCH:
    for node in ast.walk(_BRANCH[0]):
        if (isinstance(node, ast.Call)
                and ast.unparse(node.func) == "unit_stats_overlay_view.show"):
            BATTLE_END_LINES.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))

_real_show = UnitStatsOverlay.show
_real_draw = UnitStatsOverlay.draw


def show(self, stats, players, squads):
    from_battle_end = sys._getframe(1).f_lineno in BATTLE_END_LINES
    if NEUTRALIZE and from_battle_end:
        # The pre-fix world: the battle ended and nothing raised the resume.
        return False
    opened = _real_show(self, stats, players, squads)
    if opened and from_battle_end and R["resume_opened_at"] is None:
        R["resume_opened_at"] = R["frames"]
        R["resume_player"] = self.player
        ledger = self.stats
        rows = 0
        for player, _kw in self._players:
            rows += (len(ledger.top_killers(player, limit=99))
                     + len(ledger.top_tanks(player, limit=99))
                     + len(ledger.top_movers(player, limit=99)))
        R["resume_rows"] = rows
    return opened


def draw(self, surface):
    if self.is_pending:
        R["resume_drawn"] += 1
    return _real_draw(self, surface)


UnitStatsOverlay.show = show
UnitStatsOverlay.draw = draw

_pump = {"real": None}
L = {}


def _install_pump():
    """selfplay REPLACES pygame.event.get at import, so a wrapper installed
    before runpy is silently overwritten and reports truthful-looking zeroes.
    Installed from the frame hook, by which point selfplay's pump is in place."""
    if _pump["real"] is None:
        _pump["real"] = pygame.event.get
        pygame.event.get = event_get


def event_get(*args, **kwargs):
    events = list(_pump["real"](*args, **kwargs))
    if R["staged_at"] is None:
        return events

    # A STANDING PROMPT FIRST - _check_battle_end() waits for one by design.
    decisions = L.get("decision_manager")
    if decisions is not None and getattr(decisions, "is_pending", False):
        options = list(getattr(decisions, "options", ()) or ())
        if options:
            R["declined"] += 1
            decisions.choose(len(options) - 1)
        return events

    # THE CLICK, once the score box is really up. REPLACING selfplay's own
    # events on this frame rather than adding to them: it clicks the board
    # every frame, and one of those would dismiss the box for the wrong reason.
    box = L.get("battle_end_overlay")
    if box is not None and box.is_pending and R["clicks"] == 0:
        surface = pygame.display.get_surface()
        w, h = surface.get_size() if surface else (1200, 800)
        pos = (w // 2, h // 2)
        R["clicks"] += 1
        return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
                pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]

    # ...and then HANDS OFF for a moment. selfplay clicks the board on every
    # frame, and a click dismisses the resume - so without this it opened and
    # closed again inside two frames, which measures "it was drawn" about as
    # well as not measuring it. A human simply would not click for a beat.
    # Only the mouse buttons are held back, and only briefly; the battle is
    # over, so nothing is waiting on them.
    opened = R["resume_opened_at"]
    if opened is not None and R["frames"] - opened < DWELL_FRAMES:
        return [e for e in events
                if e.type not in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)]
    return events


_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    _install_pump()
    R["frames"] += 1

    if not L:
        frame = sys._getframe(1)
        while frame is not None and frame.f_code.co_name != "main":
            frame = frame.f_back
        if frame is not None and "battle_end_overlay" in frame.f_locals:
            L.update(frame.f_locals)
            R["locals_at"] = R["frames"]

    box = L.get("battle_end_overlay")
    resume = L.get("unit_stats_overlay_view")
    tracker = L.get("turn_tracker")

    if (R["staged_at"] is None and tracker is not None
            and getattr(tracker, "started", False) and R["frames"] >= STAGE_AT):
        try:
            # THE ONE STAGED FACT - see the module docstring.
            tracker.battle_over = True
            R["staged_at"] = R["frames"]
        except Exception as exc:                # a probe must not mask a real run
            R["error"] = repr(exc)

    if box is not None and box.is_pending and R["score_box_raised_at"] is None:
        R["score_box_raised_at"] = R["frames"]
        # The counter-check: if the resume were already up, "the click opened
        # it" would pass without any chain at all.
        R["resume_up_behind_score_box"] = bool(resume is not None and resume.is_pending)
        R["hint"] = getattr(__import__("game.ui.battle_end_overlay", fromlist=["x"]),
                            "DISMISS_HINT", None)

    if (R["clicks"] and box is not None and R["score_box_gone_after_click"] is None
            and not box.is_pending):
        R["score_box_gone_after_click"] = True

    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

FRAMES = 1500
_args = [a for a in sys.argv[1:]]
for arg in list(_args):
    if arg.isdigit():
        FRAMES = int(arg)
        _args.remove(arg)
STAGE_AT = max(40, FRAMES // 3)
#: How long the probe keeps its hands off the mouse once the resume is up, so
#: that "it was drawn" is a measurement rather than a two-frame accident.
DWELL_FRAMES = 60

sys.argv = ["selfplay.py"] + _args + [str(FRAMES)]
runpy.run_module("selfplay", run_name="__main__")

print()
print("=" * 72)
print("THE BATTLE ENDS -> THE RESUME%s"
      % ("   (--neutralize: the pre-fix world)" if NEUTRALIZE else ""))
print("=" * 72)
print("  frames run                        %d" % R["frames"])
print("  main()'s locals reached at frame  %s" % R["locals_at"])
print("  battle_over staged at frame       %s" % R["staged_at"])
print("  standing prompts declined         %d" % R["declined"])
if R["error"]:
    print("  staging error                     %s" % R["error"])
print()
print("  score box raised at frame         %s   <- main()'s own _check_battle_end()"
      % R["score_box_raised_at"])
print("  ...with the resume already up?    %s   <- must be False"
      % R["resume_up_behind_score_box"])
print("  its hint reads                    %r" % (R["hint"],))
print("  real clicks posted                %d" % R["clicks"])
print("  score box gone after the click    %s" % R["score_box_gone_after_click"])
print()
print("  RESUME opened at frame            %s" % R["resume_opened_at"])
print("     on army                        %s" % R["resume_player"])
print("     rows across both armies        %s" % R["resume_rows"])
print("     frames it was drawn            %d" % R["resume_drawn"])
print("=" * 72)

if R["locals_at"] is None:
    print("INCONCLUSIVE: main()'s frame was never reached - nothing was observed.")
    raise SystemExit(2)
if R["score_box_raised_at"] is None:
    print("INCONCLUSIVE: the battle end was never raised, so the click never had a box "
          "to dismiss. Try more frames.")
    raise SystemExit(2)
if not R["clicks"]:
    print("INCONCLUSIVE: no click was posted.")
    raise SystemExit(2)

if NEUTRALIZE:
    ok = R["resume_opened_at"] is None and R["resume_drawn"] == 0
    print("neutralized: the battle ended and the resume was never offered -> %s"
          % ("as expected" if ok else "UNEXPECTED"))
    raise SystemExit(0 if ok else 1)

ok = (R["resume_up_behind_score_box"] is False
      and R["score_box_gone_after_click"] is True
      and R["resume_opened_at"] is not None
      and R["resume_drawn"] > 0)
print("the end of the battle really opens the statistics overlay -> %s"
      % ("yes" if ok else "NO"))
raise SystemExit(0 if ok else 1)
