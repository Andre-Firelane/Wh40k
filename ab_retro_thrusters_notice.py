"""A/B probes for "Zug 3 KI macht nichts mehr nach Fight Step", at the SOURCE.

The AI was not stuck. It was holding its own turn-end open for a human unit's
Retro-thrusters move - correctly - and the only sign of that was one line in
the game log. Four halves were added; each probe restores one and has to make
its own suite red.

The fourth is the one worth naming: ai/agent_driver.py's Fight-phase branch had
no `else` at all, so EVERY other reason it stops there was a silent frame loop.
That probe is the only one whose failure would otherwise look like nothing at
all - the AI still works, it just never says why it is waiting.
"""

import io
import os
import re
import shutil
import subprocess
import sys

MAIN = "main.py"
PANEL = os.path.join("game", "ui", "action_panel.py")
RENDERER = os.path.join("game", "renderer.py")
OVERLAY = os.path.join("game", "ui", "fight_warning_overlay.py")
DRIVER = os.path.join("ai", "agent_driver.py")
RETRO = os.path.join("game", "retro_thrusters.py")

SUITE = "test_retro_thrusters_notice.py"
WARN = "test_fight_end_turn_warning.py"
LANCE = "test_twin_lance.py"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_cache():
    for root, dirs, _f in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)


def run(suite):
    clear_cache()
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    if not match:
        return None, None, text
    return int(match.group(1)), int(match.group(2)), text


# --- (a) the panel hint, in both branches ----------------------------------
PANEL_DONE_NEW = '''            if (retro_thrusters_controller is not None
                    and retro_thrusters_controller.pending_squads()):
                return self._draw_retro_thrusters_pending(
                    surface, rect, button_width, retro_thrusters_controller, text_y)
            return self._draw_text(surface, rect, "Fight step complete.", text_y, gap=0)'''
PANEL_DONE_OLD = '''            return self._draw_text(surface, rect, "Fight step complete.", text_y, gap=0)'''

PANEL_SEL_NEW = '''            if (retro_thrusters_controller is not None
                    and retro_thrusters_controller.pending_squads()):
                text_y = self._draw_retro_thrusters_pending(
                    surface, rect, button_width, retro_thrusters_controller, text_y)'''
PANEL_SEL_OLD = '''            pass'''

# ...and the same box painted in a colour the pile-in hint already owns, which
# would make two different messages read as one.
PANEL_COLOUR_NEW = '''RETRO_ACCENT_COLOR = (90, 225, 215)'''
PANEL_COLOUR_OLD = '''RETRO_ACCENT_COLOR = PILE_IN_ACCENT_COLOR'''

# --- (b) the board ring ----------------------------------------------------
BOARD_NEW = '''        if not _any_pending_damage_choice():
            renderer.draw_retro_thrusters_pending(
                board_surface, board, retro_thrusters_controller.pending_squads())'''
BOARD_OLD = '''        pass'''

RING_COLOUR_NEW = '''RETRO_PENDING_COLOR = (90, 225, 215)'''
RING_COLOUR_OLD = '''RETRO_PENDING_COLOR = COHERENCY_REMOVAL_COLOR'''

# --- (c) the second reason on the End Turn warning -------------------------
GATE_NEW = '''            retro_names=[s.name for s in retro_thrusters_controller.pending_squads("Player 1")])'''
GATE_OLD = ''')'''

OVERLAY_NEW = '''        if self._warned or not (unit_names or retro_names):'''
OVERLAY_OLD = '''        if self._warned or not unit_names:'''

# --- (d) the AI says WHY it is waiting -------------------------------------
ELSE_NEW = '''            _announce_fight_wait(player, turn_tracker, fight_controller,
                                 pile_in_controller, fight_wait_notice)'''
ELSE_OLD = '''            pass'''

# ...and said every frame instead of once, which is the same as not saying it.
ONCE_NEW = '''        if key in self._said:
            return False
        self._said.add(key)'''
ONCE_OLD = '''        if False:
            return False'''

# --- the shared ledger, kept twice again -----------------------------------
SHARED_NEW = '''        self._wait_notice.reset()'''
SHARED_OLD = '''        pass'''

PROBES = [
    ("the panel says 'Fight step complete' over an open decision",
     [(PANEL, PANEL_DONE_NEW, PANEL_DONE_OLD)], SUITE),
    ("...and says nothing at all during the alternation",
     [(PANEL, PANEL_SEL_NEW, PANEL_SEL_OLD)], SUITE),
    ("the hint borrows the pile-in colour, so two messages read as one",
     [(PANEL, PANEL_COLOUR_NEW, PANEL_COLOUR_OLD)], SUITE),
    ("the board rings nothing",
     [(MAIN, BOARD_NEW, BOARD_OLD)], SUITE),
    ("the ring borrows the coherency red, which means something else",
     [(RENDERER, RING_COLOUR_NEW, RING_COLOUR_OLD)], SUITE),
    ("End Turn stops asking for the second reason",
     [(MAIN, GATE_NEW, GATE_OLD)], SUITE),
    ("...and the overlay refuses to raise on it alone",
     [(OVERLAY, OVERLAY_NEW, OVERLAY_OLD)], SUITE),
    ("...and the same, against the existing warning suite",
     [(OVERLAY, OVERLAY_NEW, OVERLAY_OLD)], WARN),
    ("THE SILENT ONE: the AI's Fight branch loses its else again",
     [(DRIVER, ELSE_NEW, ELSE_OLD)], SUITE),
    ("...and the reason is repeated every frame instead of once",
     [(os.path.join("game", "wait_notice.py"), ONCE_NEW, ONCE_OLD)], SUITE),
    ("the retro-thrusters ledger is never cleared for a new phase",
     [(RETRO, SHARED_NEW, SHARED_OLD)], SUITE),
    ("THE WHOLE PRE-FIX WORLD: no hint, no ring, no warning, no reason",
     [(PANEL, PANEL_DONE_NEW, PANEL_DONE_OLD), (MAIN, BOARD_NEW, BOARD_OLD),
      (MAIN, GATE_NEW, GATE_OLD), (DRIVER, ELSE_NEW, ELSE_OLD)], SUITE),
]


baselines = {}
for suite in (SUITE, WARN, LANCE):
    got, total, text = run(suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (suite, text[-1500:]))
        raise SystemExit(2)
    baselines[suite] = got
    print("baseline %-34s %d/%d" % (suite, got, total))
print()

bad = 0
for label, edits, suite in PROBES:
    originals = {}
    try:
        ok = True
        for path, new, old in edits:
            originals.setdefault(path, read(path))
            src = read(path)
            if src.count(new) != 1:
                print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(new)))
                ok = False
                bad += 1
                break
            write(path, src.replace(new, old))
        if not ok:
            continue
        got, total, text = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < baselines[suite]:
            verdict, detail = "BITES", "%d/%d" % (got, total)
        else:
            verdict, detail = "NO BITE", "%d/%d - FINDING ABOUT THE TEST" % (got, total)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < baselines[suite]:
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:110])
                    break
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
