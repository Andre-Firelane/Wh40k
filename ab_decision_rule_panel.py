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

    # --- name, then button, then explanation --------------------------------
    # User: "Erst als grosse ueberschrift der name der Ability. Dann der Knopf.
    # Unter dem Knopf dann die Erklaerung."
    ("the generic title instead of the ability's own name", PANEL,
     "        name = decision_rule[0] if decision_rule else None",
     "        name = None"),
    ("the title not shouted like the two headings next to it", PANEL,
     '            surface, rect, (name or "CHOOSE A UNIT").upper(), self.header_font, wrap=True,',
     '            surface, rect, name or "CHOOSE A UNIT", self.header_font, wrap=True,'),
    # Nine of the corpus's 147 printed ability titles are wider than this bar.
    ("a long printed name running off the panel instead of wrapping", PANEL,
     '            surface, rect, (name or "CHOOSE A UNIT").upper(), self.header_font, wrap=True,',
     '            surface, rect, (name or "CHOOSE A UNIT").upper(), self.header_font,'),
    # ...and the same clause from the other side: draw_panel_header keeping its
    # fixed one-line height, so wrap=True buys nothing.
    ("the header bar unable to grow a second line", os.path.join("game", "ui", "button_style.py"),
     "    lines = wrap_text(font, text, width - 2 * HEADER_TEXT_MARGIN) if wrap else []",
     "    lines = []"),
    # THE OLD ORDER: the way out drawn last, under the prompt, the eligible
    # list and the hint - i.e. everything the fix moved below it.
    ("the way out back at the bottom (the old order)", PANEL,
     """        for label, index in pick.skip_options:
            r = pygame.Rect(rect.x + BUTTON_MARGIN, text_y,
                            rect.width - 2 * BUTTON_MARGIN, BUTTON_HEIGHT)
            r = self._draw_button(surface, r, label, accent="danger")
            self._buttons.append((r, lambda i=index: pick.choose(i)))
            text_y = r.bottom + BUTTON_GAP
        text_y = self._draw_text(surface, rect, pick.prompt, text_y + 2, gap=6)
        if pick.squads:
            text_y = self._draw_text(surface, rect, "Eligible units:", text_y, gap=2)
            for squad in pick.squads:
                text_y = self._draw_text(surface, rect, f"- {squad.name}", text_y, gap=2)
        else:
            text_y = self._draw_text(surface, rect, "No unit is eligible.", text_y, gap=2)
        text_y = self._draw_text(
            surface, rect, "Click one of them on the battlefield.", text_y,
            color=HINT_COLOR, gap=10,
        )
""",
     """        text_y = self._draw_text(surface, rect, pick.prompt, text_y + 2, gap=6)
        if pick.squads:
            text_y = self._draw_text(surface, rect, "Eligible units:", text_y, gap=2)
            for squad in pick.squads:
                text_y = self._draw_text(surface, rect, f"- {squad.name}", text_y, gap=2)
        else:
            text_y = self._draw_text(surface, rect, "No unit is eligible.", text_y, gap=2)
        text_y = self._draw_text(
            surface, rect, "Click one of them on the battlefield.", text_y,
            color=HINT_COLOR, gap=10,
        )
        for label, index in pick.skip_options:
            r = pygame.Rect(rect.x + BUTTON_MARGIN, text_y,
                            rect.width - 2 * BUTTON_MARGIN, BUTTON_HEIGHT)
            r = self._draw_button(surface, r, label, accent="danger")
            self._buttons.append((r, lambda i=index: pick.choose(i)))
            text_y = r.bottom + BUTTON_GAP
"""),
    # A one-paragraph rule under a box that runs to the bottom edge - a mostly
    # empty frame, which reads as art that failed to load.
    ("the rule box always as tall as the column", PANEL,
     "        box.height = min(box.height, total + 2 * RULE_BOX_PADDING)",
     "        pass"),
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
