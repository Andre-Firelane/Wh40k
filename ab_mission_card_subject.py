"""A/B probes for "ich sehe bei Tempting Target nicht welches gewaehlt wurde",
at the SOURCE.

The card's chosen objective used to be its LAST block - below the whole printed
prose, in plain body type, and drawn only once the card was expanded. So it was
invisible on the strip and easy to miss even on hover.

Each probe restores ONE half of the pre-fix world and has to make its own suite
red. Two of them matter more than the rest:

  * "the subject carries the live half too" is the probe against the
    REGRESSION this fix is closest to. A bar showing a reading that changes
    every frame was the first version of this strip and was reported as wrong
    ("mir ist aufgefallen, dass ich gerade Center Ground mitten im Zug schon
    erfuellt habe"). If that probe does not bite, the new checks are not
    measuring the thing that matters.

  * "a live card gets a subject too" is its twin from the other side: the
    counter-checks have to fail when a live readout reaches the bar.
"""

import io
import os
import re
import shutil
import subprocess
import sys

CARDS = os.path.join("game", "ui", "mission_cards.py")
MISSIONS = os.path.join("game", "secondary_missions.py")

STRIP = "test_mission_cards_ui.py"
DECK = "test_secondary_missions.py"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_cache():
    # The documented __pycache__ race: these probes rewrite and restore inside
    # the same second, so a stale .pyc reports the PREVIOUS run's result.
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


# The bar as it was: the timing, always, for every card.
BAR_NEW = '''                if not vp:
                    # READY still wins the slot: a prompt that is open right
                    # now is the more urgent of the two, and it is the only
                    # state in which the card is about to pay.
                    status, color = subject, CARD_DETAIL_COLOR'''
BAR_OLD = '''                if False:
                    status, color = subject, CARD_DETAIL_COLOR'''

# The info block as it was: no TARGET row, the choice left at the foot.
ROW_NEW = '''            if subject is not None and detail:
                info.insert(0, ("TARGET", detail, CARD_DETAIL_COLOR))
                detail = None'''
ROW_OLD = '''            if False:
                info.insert(0, ("TARGET", detail, CARD_DETAIL_COLOR))
                detail = None'''

# The highlight removed, while the row stays: the row would be there and read
# as ordinary metadata, which is what "hervorgehoben" rules out.
HILITE_NEW = '''                info.insert(0, ("TARGET", detail, CARD_DETAIL_COLOR))'''
HILITE_OLD = '''                info.insert(0, ("TARGET", detail))'''

# The per-row colour ignored at the drawing end - the same picture as having no
# highlight, reached from the other side.
DRAWCOL_NEW = '''            value_color = row[2] if len(row) > 2 else CARD_INFO_COLOR'''
DRAWCOL_OLD = '''            value_color = CARD_INFO_COLOR'''

# The title no longer outranks the choice for room. A card whose NAME is cut
# cannot be found in the stack.
ROOM_NEW = '''            room = (rect.right - CARD_PADDING - title_x
                    - title_surf.get_width() - SUBJECT_GAP)
            status_text = (ellipsised(self.status_font, status_text, room)
                           if room >= SUBJECT_MIN_WIDTH else None)'''
ROOM_OLD = '''            pass'''

# THE one that matters: the subject carries the live half as well, i.e. it is
# just a shortened detail. Everything still renders - only the bar now makes a
# claim that changes between frames.
LIVE_NEW = '''    target = ctx.card_state.get("objective")
    return target.name if target is not None else None'''
LIVE_OLD = '''    target = ctx.card_state.get("objective")
    if target is None:
        return None
    return "%s (held by %s)" % (target.name, target.controlled_by or "nobody")'''

# ...and from the other side: a LIVE readout declares itself a remembered
# choice, so a live reading reaches the collapsed bar.
CLASS_NEW = '''    detail=_engage_detail,
    detail_is_live=True,'''
CLASS_OLD = '''    detail=_engage_detail,
    subject=lambda ctx: "2 of 4 quarters",'''

PROBES = [
    ("the bar shows the timing again, never the choice",
     [(CARDS, BAR_NEW, BAR_OLD)], STRIP),
    ("the choice is left at the foot of the card",
     [(CARDS, ROW_NEW, ROW_OLD)], STRIP),
    ("the TARGET row loses its highlight",
     [(CARDS, HILITE_NEW, HILITE_OLD)], STRIP),
    ("...and the same, ignored at the drawing end",
     [(CARDS, DRAWCOL_NEW, DRAWCOL_OLD)], STRIP),
    ("the choice may cut into the title's room",
     [(CARDS, ROOM_NEW, ROOM_OLD)], STRIP),
    ("THE REGRESSION: the subject carries the live half too",
     [(MISSIONS, LIVE_NEW, LIVE_OLD)], DECK),
    ("...and the same, against the strip",
     [(MISSIONS, LIVE_NEW, LIVE_OLD)], STRIP),
    ("a live readout declares itself a remembered choice",
     [(MISSIONS, CLASS_NEW, CLASS_OLD)], DECK),
    ("...and the same, against the strip's counter-checks",
     [(MISSIONS, CLASS_NEW, CLASS_OLD)], STRIP),
    ("THE WHOLE PRE-FIX WORLD",
     [(CARDS, BAR_NEW, BAR_OLD), (CARDS, ROW_NEW, ROW_OLD)], STRIP),
]


baselines = {}
for suite in (STRIP, DECK):
    got, total, text = run(suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (suite, text[-1500:]))
        raise SystemExit(2)
    baselines[suite] = got
    print("baseline %-30s %d/%d" % (suite, got, total))
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
