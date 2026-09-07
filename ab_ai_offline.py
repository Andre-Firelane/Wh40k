"""A/B probes for the AI-offline handling, at the SOURCE.

Each restores one piece of the pre-fix world and reruns the suite. A probe that
does NOT go red is a finding about the test, not a clean bill of health.
"""

import io
import os
import re
import shutil
import subprocess
import sys

CONN = os.path.join("ai", "connection.py")
DRIVER = os.path.join("ai", "agent_driver.py")
OVERLAY = os.path.join("game", "ui", "ai_offline_overlay.py")
MAIN = "main.py"
SUITE = "test_ai_offline.py"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run():
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


PROBES = [
    ("the engine calling the agent directly (THE CRASH)", DRIVER,
     "    index = connection.ask(agent.decide, observation)",
     "    index = agent.decide(observation)"),
    ("take_one_action not absorbing an unreachable agent", DRIVER,
     "    try:\n        return _take_one_action(*args, **kwargs)\n"
     "    except connection.AIUnavailable:\n        return None",
     "    return _take_one_action(*args, **kwargs)"),
    ("...and not short-circuiting once offline (a round-trip per frame)", DRIVER,
     "    if not connection.is_online():\n        return None",
     "    if False:\n        return None"),
    ("a catch wide enough to swallow a real bug", DRIVER,
     "    except connection.AIUnavailable:\n        return None",
     "    except Exception:\n        return None"),
    ("the latch overwritten by every later failure", CONN,
     "    if _offline_reason is None:\n        _offline_reason = describe(exc)",
     "    _offline_reason = describe(exc)"),
    ("every failure reported as a lost connection", CONN,
     '    name = type(exc).__name__\n    text = str(exc).strip()',
     '    name = "APIConnectionError"\n    text = str(exc).strip()'),
    ("a notice that can be raised again and again", OVERLAY,
     "        if self._shown:\n            return False",
     "        if False:\n            return False"),
    ("main() never announcing it", MAIN,
     "            if ai_offline_overlay.show(ai_connection.reason()):",
     "            if False and ai_offline_overlay.show(ai_connection.reason()):"),
    ("the notice left out of the one-modal-at-a-time order", MAIN,
     "        for overlay in (battle_end_overlay, ai_offline_overlay,",
     "        for overlay in (battle_end_overlay,"),
]

base, total, text = run()
if base is None:
    print("BASELINE DID NOT RUN:\n" + text[-2000:])
    raise SystemExit(2)
print(f"baseline: {base}/{total}\n")

bad = 0
for label, path, new, old in PROBES:
    src = read(path)
    if src.count(new) != 1:
        print(f"  SKIP     {label}: anchor not unique in {path} ({src.count(new)})")
        bad += 1
        continue
    try:
        write(path, src.replace(new, old))
        got, tot, out = run()
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < base:
            verdict, detail = "BITES", f"{got}/{tot}"
        else:
            verdict, detail = "NO BITE", f"{got}/{tot} - FINDING ABOUT THE TEST"
            bad += 1
        print(f"  {verdict:8} {label}: {detail}")
        if got is not None and got < base:
            for line in out.splitlines():
                if line.strip().startswith("FAIL:"):
                    print(f"             {line.strip()[:104]}")
                    break
    finally:
        write(path, src)

for root, dirs, _files in os.walk("."):
    for name in list(dirs):
        if name == "__pycache__":
            shutil.rmtree(os.path.join(root, name), ignore_errors=True)
            dirs.remove(name)

print()
print("all probes bite" if not bad else f"{bad} probe(s) did not bite")
raise SystemExit(1 if bad else 0)
