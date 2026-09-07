"""A/B probes for the printed-rules datacard and the mission-card layout.

Each probe restores ONE pre-fix world at the SOURCE, re-runs the affected
suites, and must break its own checks. A probe that does NOT bite is a finding
about the TEST, not a clean bill of health (CLAUDE.md's Fehlerklasse 24) - so
the expected drop is written down per probe and a probe that meets its baseline
is reported as a failure of this script.

Run: python ab_datacard_rules.py
"""

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))

SUITES = ["test_unit_datacard.py", "test_rules_text.py",
          "test_mission_cards_ui.py", "test_primary_missions.py"]


def run(suite):
    """(passed, total) for one suite. Reads the "N/M checks passed" line rather
    than the exit code, because a probe that makes the suite CRASH is still a
    probe that bit - and a crash reports no numbers at all."""
    proc = subprocess.run([sys.executable, suite], cwd=ROOT,
                          capture_output=True, text=True, timeout=600)
    out = proc.stdout + proc.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", out)
    if not match:
        return (-1, -1)  # crashed: counts as bitten
    return int(match.group(1)), int(match.group(2))


def baseline():
    return {s: run(s) for s in SUITES}


class Patch:
    """Edit files, run the suites, put everything back - even on a crash."""

    def __init__(self, name, edits, expect):
        self.name = name
        self.edits = edits            # [(path, old, new)]
        self.expect = expect          # suites that must lose checks

    def __enter__(self):
        self.backup = {}
        for path, old, new in self.edits:
            full = os.path.join(ROOT, path)
            if full not in self.backup:
                self.backup[full] = io.open(full, encoding="utf-8").read()
            src = io.open(full, encoding="utf-8").read()
            if old not in src:
                raise SystemExit(f"{self.name}: anchor not found in {path}:\n  {old[:90]}")
            io.open(full, "w", encoding="utf-8").write(src.replace(old, new, 1))
        return self

    def __exit__(self, *exc):
        for full, text in self.backup.items():
            io.open(full, "w", encoding="utf-8").write(text)
        # The probes rewrite and restore files inside one second, which is the
        # documented __pycache__ race in this repo (Fehlerklasse 19): without
        # this the NEXT probe re-runs the PREVIOUS probe's bytecode.
        for dirpath, dirnames, _ in os.walk(ROOT):
            for d in list(dirnames):
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
                    dirnames.remove(d)
        return False


PROBES = [
    # 1. The whole point of the change: read the developer note instead of the
    #    printed text. The paraphrase and its "see game/...py" pointer come back.
    Patch(
        "datacard reads Datasheet.abilities_text again",
        [("game/ui/unit_datacard.py",
          "        abilities = rules_text.abilities_for(getattr(squad, \"datasheet\", None))\n"
          "        return [(None, abilities)] if abilities else []",
          "        datasheet = getattr(squad, \"datasheet\", None)\n"
          "        texts = getattr(datasheet, \"abilities_text\", ()) if datasheet else ()\n"
          "        abilities = [rules_text.Ability(\"Abilities\", body=t) for t in texts]\n"
          "        return [(None, abilities)] if abilities else []")],
        expect=["test_unit_datacard.py"],
    ),
    # 2. An attached unit falls back to the one datasheet Squad.datasheet names,
    #    so hovering a Boy hides the Warboss and Painboy rules entirely.
    Patch(
        "attached units collapse to squad.datasheet",
        [("game/ui/unit_datacard.py",
          "        if attached_units.is_attached_unit(squad):",
          "        if False:")],
        expect=["test_unit_datacard.py"],
    ),
    # 3. The measured height forgets the abilities - the card is sized for its
    #    stat block and clips every printed rule off the bottom.
    Patch(
        "content height ignores the abilities section",
        [("game/ui/unit_datacard.py",
          "        if ability_groups:\n            height += self._abilities_height(ability_groups)",
          "        if False:\n            height += self._abilities_height(ability_groups)")],
        expect=["test_unit_datacard.py"],
    ),
    # 4. No cap and no scrolling: the card grows past the window, and the wheel
    #    goes back to zooming the board underneath an open card.
    Patch(
        "the card is never capped, so it never scrolls",
        [("game/ui/unit_datacard.py",
          "        height = min(content_height, max_height)",
          "        height = content_height")],
        expect=["test_unit_datacard.py"],
    ),
    # 5. Drawn without a clip. Scrolled content is drawn at a negative offset,
    #    so it paints over the board above the card.
    Patch(
        "the scrolled card does not clip",
        [("game/ui/unit_datacard.py",
          "        surface.set_clip(content_rect.clip(prev_clip) if prev_clip else content_rect)",
          "        pass")],
        expect=["test_unit_datacard.py"],
    ),
    # 6. CTRL-only, i.e. the pre-change gesture. Resting on a unit does nothing.
    Patch(
        "no dwell-to-open, CTRL only",
        [("game/ui/unit_datacard.py",
          "        self.visible = bool(ctrl_held) or dwelt",
          "        self.visible = bool(ctrl_held)")],
        expect=["test_unit_datacard.py"],
    ),
    # 7. The wheel is claimed unconditionally - a short card that needs no
    #    scrolling would swallow the camera zoom.
    Patch(
        "an unscrollable card still eats the wheel",
        [("game/ui/unit_datacard.py",
          "        if not self.visible or self._scroll_max <= 0:\n            return False",
          "        if False:\n            return False")],
        expect=["test_unit_datacard.py"],
    ),
    # 8. The corpus reader stops folding markdown, so literal ** reaches the
    #    card and the text is no longer what the datasheet prints.
    Patch(
        "rules text keeps its markdown markers",
        [("game/rules_text.py",
          '    return _fold(re.sub(r"\\*\\*(.+?)\\*\\*", r"\\1", text)).strip()',
          "    return text.strip()")],
        expect=["test_rules_text.py"],
    ),
    # 9. The corpus reader loses a whole printed section - Wargear Abilities and
    #    the Damaged bracket vanish from every card that has them.
    Patch(
        "only the Abilities section is read",
        [("game/rules_text.py",
          'ABILITY_SECTIONS = ("Abilities", "Wargear Abilities", "Transport")',
          'ABILITY_SECTIONS = ("Abilities",)')],
        expect=["test_rules_text.py"],
    ),
    # 10. The folder derivation drifts from the one fetch_datasheet_rules.py
    #     writes with - every T'au and Death Guard card silently loses its rules.
    Patch(
        "the corpus folder derivation drifts",
        [("game/rules_text.py",
          '    name = name.lower().replace("’", "").replace("\'", "")',
          '    name = name.lower()')],
        expect=["test_rules_text.py"],
    ),
    # 11. Mission cards: back to space-padded single strings. They only line up
    #     in a monospace font, and the long row loses its indent when it wraps.
    Patch(
        "mission info rows are padded strings again",
        [("game/ui/mission_cards.py",
          "                info=card.info_rows(),",
          "                info=[(l, v) for l, v in [(x, '') for x in card.info_lines()]],")],
        expect=["test_mission_cards_ui.py", "test_primary_missions.py"],
    ),
    # 12. The info block's height stops accounting for wrapped values, so the
    #     printed mission text is drawn over its own metadata.
    Patch(
        "the info block is measured as one line per row",
        [("game/ui/mission_cards.py",
          "            rows = max(\n"
          "                wrapped_text_height(self.body_font, value, self._info_value_width(),\n"
          "                                    line_height=line_height),\n"
          "                line_height,\n"
          "            )",
          "            rows = line_height")],
        expect=["test_mission_cards_ui.py"],
    ),
    # 13. No scoring table: the VP go back to living only inside the prose,
    #     which is the state the user reported as "sehr unuebersichtlich".
    Patch(
        "the card drops its WHAT | WHEN | VP table",
        [("game/ui/mission_cards.py",
          "                scoring=mission.scoring_rows(),\n", "")],
        expect=["test_mission_cards_ui.py", "test_primary_missions.py"],
    ),
    # 14. The table is drawn but never measured, so the printed text below it
    #     is pushed out of the card and clipped.
    Patch(
        "the scoring table is not counted in the card's height",
        [("game/ui/mission_cards.py",
          "        if card.scoring:\n"
          "            # scoring table, then a separator rule before the printed prose\n"
          "            height += self._scoring_height(card) + block_gap",
          "        if False:\n"
          "            height += self._scoring_height(card) + block_gap")],
        expect=["test_mission_cards_ui.py"],
    ),
    # 15. The VP column stops being right-aligned - the numbers no longer form
    #     a column of numbers, which is the entire point of the table.
    Patch(
        "the VP column is left-aligned",
        [("game/ui/mission_cards.py",
          "            surface.blit(vp_surf, (vp_right - vp_surf.get_width(), y))",
          "            surface.blit(vp_surf, (vp_right - SCORE_VP_WIDTH, y))")],
        expect=["test_mission_cards_ui.py"],
    ),
    # 16. The printed prose goes back to one undivided block.
    Patch(
        "the printed text is one block again",
        [("game/ui/text_utils.py",
          '    return [piece for piece in re.split(r"(?<=[.!])\\s+(?=[A-Z0-9])", normalised) if piece]',
          "    return [normalised]")],
        expect=["test_mission_cards_ui.py"],
    ),
    # 17. The paragraph split stops being lossless - the guarantee that no word
    #     of a printed rule is changed by re-flowing it.
    Patch(
        "splitting paragraphs drops a word",
        [("game/ui/text_utils.py",
          '    normalised = " ".join(text.split())',
          '    normalised = " ".join(text.split()[:-1])')],
        expect=["test_mission_cards_ui.py"],
    ),
    # 18. A scoring box forgets its rate. A blank VP cell reads as "pays
    #     nothing", so this must be loud rather than silent.
    Patch(
        "a scoring box has no VP rate",
        [("game/primary_missions.py",
          '        ScoringBox("kills", TIMING_END_OF_YOUR_TURN, _recon_kills, "KILLS",\n'
          '                   "%d/unit" % RECON_PER_KILL_VP),',
          '        ScoringBox("kills", TIMING_END_OF_YOUR_TURN, _recon_kills, "KILLS", ""),')],
        expect=["test_mission_cards_ui.py"],
    ),
]


def main():
    print("baseline...")
    base = baseline()
    for suite, (passed, total) in base.items():
        print(f"  {suite:34s} {passed}/{total}")
        if passed != total:
            raise SystemExit(f"baseline is not green: {suite}")

    print()
    failures = []
    for probe in PROBES:
        with probe:
            results = {s: run(s) for s in probe.expect}
        bits = []
        bit = False
        for suite, (passed, total) in results.items():
            before = base[suite][0]
            if passed == -1:
                bits.append(f"{suite} CRASHED")
                bit = True
            else:
                bits.append(f"{suite} {passed}/{total} (was {before})")
                if passed < before:
                    bit = True
        mark = "BITES " if bit else "SILENT"
        print(f"{mark}  {probe.name}")
        for line in bits:
            print(f"           {line}")
        if not bit:
            failures.append(probe.name)

    print()
    if failures:
        print("PROBES THAT DID NOT BITE (a finding about the TEST, not the code):")
        for name in failures:
            print("  -", name)
        raise SystemExit(1)
    print(f"all {len(PROBES)} probes bit")


if __name__ == "__main__":
    main()
