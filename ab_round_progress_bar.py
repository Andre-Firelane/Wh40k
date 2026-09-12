"""A/B probes for the round progress bar, at the SOURCE.

The bar replaced a number ("ROUND 3") in the right-hand panel with a full-width
row at the top of the window. What these restore, one at a time:

  * THE LAYOUT, which is where the first version got it wrong: the bar owns a
    row and the three columns start under it. Drawn over the board instead, it
    covers the map and leaves the map's top edge below the panels' - both of
    which were reported;
  * every turn segment carries its owner's colour, not one colour for all;
  * the current phase is distinguishable from the played ones;
  * the track tiles the space instead of drifting off its right edge;
  * the badge follows whoever is playing;
  * the round number does not come back to the panel as well.

Each probe has to make test_round_progress_bar.py red.
"""

import io
import os
import re
import shutil
import subprocess
import sys

BAR = os.path.join("game", "ui", "round_progress_bar.py")
MAIN = "main.py"
PANEL = os.path.join("game", "ui", "game_status_panel.py")

SUITE = "test_round_progress_bar.py"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_cache():
    # The documented __pycache__ race: these rewrite and restore inside the
    # same second, so a stale .pyc reports the PREVIOUS run's result.
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


# 1. THE REPORTED FAULT, restored: the bar goes back to being drawn over the
#    board instead of owning a row, so the board column starts at the top of
#    the window again and the strip eats the map's first 28 px.
ROW_NEW = """    top_bar_height = round_progress_bar.BAR_HEIGHT
    top_row_height = window_height - config.RESERVES_PANEL_HEIGHT - top_bar_height"""
ROW_OLD = """    top_bar_height = 0
    top_row_height = window_height - config.RESERVES_PANEL_HEIGHT"""

# 2. The other half of the same report: the board steps down but the PANELS do
#    not, so the three columns stop sharing a top edge - "die map schliesst
#    jetzt nicht mehr links und rechts mit den 2 seiten panels ab".
LEFTPANEL_NEW = "    left_panel_rect = pygame.Rect(0, top_bar_height, config.LEFT_PANEL_WIDTH, top_row_height)"
LEFTPANEL_OLD = "    left_panel_rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, top_row_height)"

# 3. The reserves row left where it was, so the rows no longer tile the window
#    and the bottom panel overlaps the column above it.
RESERVES_NEW = "    reserves_panel_rect = pygame.Rect(0, top_bar_height + top_row_height, window_width, config.RESERVES_PANEL_HEIGHT)"
RESERVES_OLD = "    reserves_panel_rect = pygame.Rect(0, top_row_height, window_width, config.RESERVES_PANEL_HEIGHT)"

# 4. The reserves panel asked to give up the bar's FULL height, which is more
#    slack than it had - the card would be clipped.
SPACE_NEW = "RESERVES_PANEL_HEIGHT = 126"
SPACE_OLD = "RESERVES_PANEL_HEIGHT = 102"

# 5. One colour for the whole track. The bar still fills and still animates -
#    it just stops saying whose turn each segment was, which is half of "das
#    Volk Logo/Farbe muss drin sein".
COLOR_NEW = "    base = TOKEN_TEAM_COLORS.get(owner, EMPTY_COLOR)"
COLOR_OLD = '    base = TOKEN_TEAM_COLORS.get("Player 1", EMPTY_COLOR)'

# 6. The played and the current cell drawn the same. The bar still fills
#    correctly; you just cannot see where you are in the turn.
CURRENT_NEW = """    if turn == playing and phase == phase_now:
        return tuple(base[:3])"""
CURRENT_OLD = """    if turn == playing and phase == phase_now:
        return _dim(base, PLAYED_DIM)"""

# ---- the turn labels ON the bar, and the colours from the first turn on ----
# Reported: "momentan sind ganz kleine labels unter den zugabschnitten. die
# koennen weg. stattdessen koennen P1 bzw P2 labels direkt auf der leiste sein
# ... auch von anfang an in den richtigen farben".

# 10. THE REPORTED LAYOUT, restored: the label drawn under the cells again.
LABEL_UNDER_NEW = "    rect = ink.get_rect(center=middle.center)"
LABEL_UNDER_OLD = "    rect = ink.get_rect(midtop=(middle.centerx, segment.bottom))"

# 10b. ...and small again: the font the reported labels were set in.
LABEL_SIZE_NEW = "LABEL_FONT_SIZE = 18"
LABEL_SIZE_OLD = "LABEL_FONT_SIZE = 11"

# 11. ...and its other half: the cells give up a row for a label again.
ROW_RESERVED_NEW = "    for index, segment in enumerate(turn_segments(track, len(owners))):"
ROW_RESERVED_OLD = ("    for index, segment in enumerate(turn_segments(pygame.Rect(track.x, "
                    "track.y, track.width, track.height - font.get_height()), len(owners))):")

# 12. THE OTHER REPORTED HALF: a turn nobody has played yet is grey again, so
#     the bar cannot say whose turn is where until it has been played.
UPCOMING_NEW = "    return _dim(base, UPCOMING_DIM)"
UPCOMING_OLD = "    return EMPTY_COLOR"

# 13. The labels in one neutral colour, not the owners'.
LABEL_COLOUR_NEW = "    ink = font.render(text, True, label_color(owner))"
LABEL_COLOUR_OLD = "    ink = font.render(text, True, (150, 165, 180))"

# 14. Every segment named the same, whoever owns it. Right place, right colour,
#     wrong TEXT - which a pixel-colour check alone would pass.
LABEL_TEXT_NEW = """    text = owner_label(owner)
    ink = """
LABEL_TEXT_OLD = """    text = "P1"
    ink = """

# 15. No outline: the label vanishes into its own full-colour current cell.
OUTLINE_NEW = "        surface.blit(outline, rect.move(dx, dy))"
OUTLINE_OLD = "        pass"

# 16. Labels squeezed into any segment, however narrow.
SQUEEZE_NEW = """    if rect.width + 2 * (LABEL_MARGIN + 1) > segment.width:
        return None"""
SQUEEZE_OLD = """    if False:
        return None"""

# 17. Labels during deployment, in the PLACEHOLDER order TurnTracker carries
#     before the first-turn roll-off - an order that can flip a moment later.
DEPLOY_LABELS_NEW = """        if playing is not None:
            drawn = _draw_owner_label("""
DEPLOY_LABELS_OLD = """        if True:
            drawn = _draw_owner_label("""

# 18. ...and the same for the colours: the placeholder order painted in.
DEPLOY_COLOURS_NEW = """    if playing is None:
        return EMPTY_COLOR
"""
DEPLOY_COLOURS_OLD = """    if playing is None:
        playing, phase_now = -1, 0
"""

# 7. The integer-division layout. Loses up to a pixel per segment, so the
#    track's right-hand end drifts away from its own border - the reason
#    turn_segments() carries a running float.
DRIFT_NEW = """        left = int(round(cursor))
        cursor += step
        right = int(round(cursor))
        out.append(pygame.Rect(left, track.y, max(1, right - left), track.height))"""
DRIFT_OLD = """        left = int(cursor)
        cursor += step
        right = left + int(step)
        out.append(pygame.Rect(left, track.y, max(1, right - left), track.height))"""

# 8. The badge follows a fixed side instead of whoever is playing.
BADGE_NEW = "    keyword = (player_factions or {}).get(turn_tracker.turn_owner)"
BADGE_OLD = '    keyword = (player_factions or {}).get("Player 1")'

# 9. The round number back in the panel as well. Not a crash and not even
#    wrong - just the thing that was asked to be REPLACED rather than joined.
PANEL_NEW = """        # THE ROUND NUMBER IS NOT DRAWN HERE ANY MORE."""
PANEL_OLD = """        _round_label = f"ROUND {turn_tracker.battle_round}"
        # THE ROUND NUMBER IS NOT DRAWN HERE ANY MORE."""

CONFIG = os.path.join("game", "config.py")

PROBES = [
    ("the bar covers the map again (the reported fault)",
     [(MAIN, ROW_NEW, ROW_OLD)], SUITE),
    ("the panels do not step down with the board",
     [(MAIN, LEFTPANEL_NEW, LEFTPANEL_OLD)], SUITE),
    ("the reserves row stays put, so the rows overlap",
     [(MAIN, RESERVES_NEW, RESERVES_OLD)], SUITE),
    ("the reserves panel gives up more room than it has",
     [(CONFIG, SPACE_NEW, SPACE_OLD)], SUITE),
    ("one colour for every turn segment", [(BAR, COLOR_NEW, COLOR_OLD)], SUITE),
    ("the current phase looks like a played one", [(BAR, CURRENT_NEW, CURRENT_OLD)], SUITE),
    ("integer-division layout (the track drifts)", [(BAR, DRIFT_NEW, DRIFT_OLD)], SUITE),
    ("the badge shows a fixed side, not the turn owner", [(BAR, BADGE_NEW, BADGE_OLD)], SUITE),
    ("the round number comes back to the panel", [(PANEL, PANEL_NEW, PANEL_OLD)], SUITE),
    ("the turn label is drawn under the cells again (reported)",
     [(BAR, LABEL_UNDER_NEW, LABEL_UNDER_OLD)], SUITE),
    ("the turn label is as small as the reported one",
     [(BAR, LABEL_SIZE_NEW, LABEL_SIZE_OLD)], SUITE),
    ("the cells give up a row for the label again",
     [(BAR, ROW_RESERVED_NEW, ROW_RESERVED_OLD)], SUITE),
    ("upcoming turns are grey until played (reported)",
     [(BAR, UPCOMING_NEW, UPCOMING_OLD)], SUITE),
    ("the labels are one neutral colour", [(BAR, LABEL_COLOUR_NEW, LABEL_COLOUR_OLD)], SUITE),
    ("every segment is labelled P1", [(BAR, LABEL_TEXT_NEW, LABEL_TEXT_OLD)], SUITE),
    ("the label has no outline", [(BAR, OUTLINE_NEW, OUTLINE_OLD)], SUITE),
    ("labels squeezed into any width", [(BAR, SQUEEZE_NEW, SQUEEZE_OLD)], SUITE),
    ("labels during deployment, in the placeholder order",
     [(BAR, DEPLOY_LABELS_NEW, DEPLOY_LABELS_OLD)], SUITE),
    ("colours during deployment, in the placeholder order",
     [(BAR, DEPLOY_COLOURS_NEW, DEPLOY_COLOURS_OLD)], SUITE),
]

baselines = {}
for suite in sorted({p[2] for p in PROBES}):
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
                print("  SKIP     %s: anchor not unique in %s (%d)"
                      % (label, path, src.count(new)))
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
