"""A/B probes for the range ruler: each one rebuilds a pre-fix world AT THE
SOURCE and must knock over its own checks in test_aura_ruler.py.

A suite that stays green when the feature is removed is testing nothing, and
this repo has caught itself doing exactly that often enough to make the probe a
convention rather than a nicety. Every entry below edits a real file, runs the
suite, and puts the file back.

Usage:  python ab_aura_ruler.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

SUITE = "test_aura_ruler.py"

PROBES = [
    # (file, needle, replacement, what world this rebuilds)
    ("game/aura_ruler.py",
     "    return _radius_in if _enabled else None",
     "    return _radius_in",
     "active_radius() ignores the toggle - the ruler can never be turned off"),

    ("game/renderer.py",
     "        if squad is None or not radius_in:\n            return",
     "        if squad is None:\n            return\n        radius_in = radius_in or 6",
     "the renderer draws a ring even when nothing asked for one"),

    ("game/ui/action_panel.py",
     "        radio_rows = (_radio_rows() if aura_ruler.is_enabled() else 0)",
     "        radio_rows = _radio_rows()",
     "the radius radio is on screen even while the ruler is off"),

    ("game/ui/action_panel.py",
     "            self._buttons.append((cell_rect, (lambda r: lambda: aura_ruler.set_radius(r))(radius)))",
     "            self._buttons.append((cell_rect, lambda: aura_ruler.set_radius(radius)))",
     "the classic late-binding closure: every button sets the LAST radius"),

    ("game/renderer.py",
     "        overlay.set_alpha(RANGE_AURA_ALPHA)\n        surface.blit(overlay, (0, 0))",
     "        surface.blit(overlay, (0, 0))",
     "the union is blitted opaque instead of faded once"),

    # Anchored on the comment ABOVE it: the same reset line also ends
    # draw_contagion_aura(), so the bare call is not unique in this file.
    ("game/renderer.py",
     "        # same Surface back next frame and set_alpha persists on it.\n        overlay.set_alpha(None)",
     "        # same Surface back next frame and set_alpha persists on it.\n        pass",
     "the shared overlay keeps the fade, poisoning its next user"),

    ("game/renderer.py",
     "            if model.is_dead():\n                continue",
     "            if False:\n                continue",
     "casualties still project an aura"),

    ("game/renderer.py",
     "            radius_px = board.in_to_px_len(model.radius_in + radius_in)",
     "            radius_px = board.in_to_px_len(radius_in)",
     "the ring is measured from the model's CENTRE, not its base edge"),

    ("game/renderer.py",
     "RANGE_AURA_ALPHA = 26",
     "RANGE_AURA_ALPHA = 4",
     "the ruler is faded until it is invisible on the default ground"),
]


def run_suite():
    result = subprocess.run([sys.executable, SUITE], capture_output=True, text=True)
    tail = [line for line in result.stdout.splitlines() if "checks passed" in line]
    return result.returncode, (tail[-1].strip() if tail else "(no summary)")


def main():
    baseline_rc, baseline = run_suite()
    print(f"baseline: {baseline}  (exit {baseline_rc})")
    if baseline_rc != 0:
        print("ABORT: the suite is not green to begin with, so no probe means anything.")
        return 1

    failures = []
    for path, needle, replacement, description in PROBES:
        original = io.open(path, encoding="utf-8").read()
        if original.count(needle) != 1:
            print(f"  SKIP  {description}\n        (anchor found {original.count(needle)}x in {path})")
            failures.append(description)
            continue
        backup = tempfile.mktemp(suffix=".bak")
        shutil.copyfile(path, backup)
        try:
            io.open(path, "w", encoding="utf-8").write(original.replace(needle, replacement))
            # The suites in this repo have been fooled by a stale __pycache__
            # written in the same second as the edit - see CLAUDE.md's error
            # class 19. Clearing it is cheaper than re-running to find out.
            for root, dirs, _files in os.walk("."):
                for directory in list(dirs):
                    if directory == "__pycache__":
                        shutil.rmtree(os.path.join(root, directory), ignore_errors=True)
                        dirs.remove(directory)
            rc, summary = run_suite()
        finally:
            shutil.copyfile(backup, path)
            os.remove(backup)
        bit = "BITES" if rc != 0 else "DOES NOT BITE"
        print(f"  {bit:14} {description}\n                 -> {summary}")
        if rc == 0:
            failures.append(description)

    print()
    if failures:
        print(f"{len(PROBES) - len(failures)}/{len(PROBES)} probes bite. "
              f"These did NOT, which is a finding about the TEST:")
        for description in failures:
            print(f"  - {description}")
        return 1
    print(f"all {len(PROBES)} probes bite")
    return 0


if __name__ == "__main__":
    sys.exit(main())
