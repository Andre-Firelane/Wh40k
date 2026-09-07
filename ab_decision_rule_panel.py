"""A/B probes at the SOURCE for the rule shown beside a board pick.

Each probe restores one clause of the pre-fix world and must make
test_decision_rule_panel.py go red. A probe that does not bite is a finding
about the TEST.

Run: python ab_decision_rule_panel.py
"""
import io, os, re, shutil, subprocess, sys

PROMPT_RULE = os.path.join("game", "prompt_rule.py")
NL = chr(10)
PANEL = os.path.join("game", "ui", "action_panel.py")
MAIN = "main.py"
SUITE = "test_decision_rule_panel.py"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_pycache():
    for root, dirs, _f in os.walk("."):
        for n in list(dirs):
            if n == "__pycache__":
                shutil.rmtree(os.path.join(root, n), ignore_errors=True)
                dirs.remove(n)


def run():
    clear_pycache()
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True)
    t = out.stdout + out.stderr
    m = re.search(r"(\d+)/(\d+) checks passed", t)
    return (int(m.group(1)), int(m.group(2)), t) if m else (None, None, t)


PROBES = [
    # THE REPORT's harder half: a rule 19.01 merge hides the leader's own
    # datasheet behind the bodyguards'. Looking only at squad.datasheet finds
    # the Immortals and never Living Lightning.
    ("attached components dropped - the Immortals case (THE REPORT)", PROMPT_RULE,
     """        for component in getattr(squad, "attached_components", ()) or ():
            if getattr(component, "datasheet", None) is not None:
                sheets.append(component.datasheet)
""",
     ""),
    # Word boundaries are what stop "Guide" answering for "Guided".
    ("plain substring matching instead of word boundaries", PROMPT_RULE,
     '''        if re.search(r"(?<![A-Za-z])" + re.escape(candidate) + r"(?![A-Za-z])",
                     prompt, re.IGNORECASE):
            return True''',
     '''        if candidate.lower() in (prompt or "").lower():
            return True'''),
    # 11% of printed ability titles carry a "(Psychic)"/"(Aura)" tag the
    # prompts leave off - including the psychic marks, which ARE board picks.
    ("the bracketed-tag alias removed", PROMPT_RULE,
     "    for candidate in (name, _bare(name)):",
     "    for candidate in (name,):"),
    # The whole feature off: nothing is ever resolved.
    ("nothing is ever resolved (the pre-fix world)", PROMPT_RULE,
     "    if not prompt:\n        return None, []\n",
     "    if True:\n        return None, []\n"),
    # Resolved, but the panel never draws it.
    ("the panel never draws the rule", PANEL,
     "        if not decision_rule:" + NL + "            self._rule_key = None",
     "        if True:" + NL + "            self._rule_key = None"),
    # Drawn, but ON TOP of the pick screen it is meant to explain - the
    # prompt and the eligible-unit list are what the player is reading.
    ("the rule box drawn over the pick screen", PANEL,
     "        self._draw_decision_rule(surface, rect, text_y + 4, decision_rule)",
     "        self._draw_decision_rule(surface, rect, rect.y + 20, decision_rule)"),
    # A long rule silently cut off instead of scrolled - the failure the
    # move to this narrower column had to avoid.
    ("a long rule not scrollable", PANEL,
     "        self._rule_scroll_max = max(0, total - view_height)",
     "        self._rule_scroll_max = 0"),
    # Scroll offset carried over from a longer rule.
    ("the scroll offset shared between rules", PANEL,
     "        if name != self._rule_key:" + NL + "            self._rule_key = name" + NL     + "            self._rule_scroll = 0",
     "        self._rule_key = name"),
    # Built but never fed - the failure this repo has hit six times.
    ("main() never hands it to the panel", MAIN,
     "            decision_rule=frame_decision_rule,",
     "            "),
    # ...and the wheel never reaching it, which is what makes a long rule
    # readable in this column at all.
    ("the wheel never reaching the rule box", MAIN,
     "                if action_panel.handle_rule_scroll(mouse_pos, event.y):",
     "                if False:"),
    # Looked up against whoever's turn it is rather than whoever is deciding:
    # a reactive prompt in the opponent's turn would search the wrong army.
    ("the wrong player's rules searched", MAIN,
     "            _rule_owner = decision_manager.player",
     "            _rule_owner = turn_tracker.turn_owner"),
]

base, total, txt = run()
if base is None:
    print("BASELINE DID NOT RUN:\n" + txt[-1500:])
    raise SystemExit(2)
print("baseline: %s/%s\n" % (base, total))

bad = 0
for label, path, new, old in PROBES:
    src = read(path)
    if src.count(new) != 1:
        print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(new)))
        bad += 1
        continue
    try:
        write(path, src.replace(new, old))
        got, tot, t = run()
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < base:
            verdict, detail = "BITES", "%s/%s" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < base:
            for line in t.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:110])
                    break
    finally:
        write(path, src)

clear_pycache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
