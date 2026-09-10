"""A/B probes for the 2026-09-09 keyword report, at the SOURCE.

  "Keywords fehlen in Einheiten Info"

Every printed datasheet ends with a keyword bar. The hover card drew ten
sections and none of them was that one - and it was never a decision:
game/rules_text.py's ABILITY_SECTIONS whitelist filtered "## Keywords" out,
while the comment listing the DELIBERATE exclusions (Profile, weapons, Points,
Wargear Options) did not mention it.

The source is the CORPUS, and that is measured, not stylistic: of the 130 built
datasheets 66 have a Datasheet.keywords tuple that differs from the printed
line (most omit the faction keyword) and 76 set no faction_keywords at all.

Each probe restores one piece of the pre-fix world and has to make its suite red.
"""

import io
import os
import re
import shutil
import subprocess
import sys

RT = os.path.join("game", "rules_text.py")
CARD = os.path.join("game", "ui", "unit_datacard.py")

SUITE = "test_unit_datacard.py"


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


# ------------------------------------------- 1. the whole pre-fix world
READER_NEW = '''    rows = []
    try:
        body = _section_named(path, "Keywords")
        for line in _corpus_lines(body or ""):
            if line.kind == "label":
                rows.append(Ability("Keywords", label=line.label, body=line.body))
            elif line.body:
                rows.append(Ability("Keywords", body=line.body))
    except OSError:
        rows = []'''
READER_OLD = '''    rows = []   # probe: the section is filtered out again'''

# ------------------- 2. the ENGINE tuples instead of the printed corpus
ENGINE_OLD = '''    rows = []
    try:
        _sheet_kw = list(getattr(datasheet, "keywords", ()) or ())
        if _sheet_kw:
            rows.append(Ability("Keywords", label="KEYWORDS", body="; ".join(_sheet_kw)))
        _fac_kw = list(getattr(datasheet, "faction_keywords", ()) or ())
        if _fac_kw:
            rows.append(Ability("Keywords", label="FACTION KEYWORDS", body=", ".join(_fac_kw)))
    except OSError:
        rows = []'''

# --------------- 3. a hand-rolled parser instead of the shared classifier
PARSER_OLD = '''    rows = []
    try:
        body = _section_named(path, "Keywords")
        for _para in (body or "").splitlines():
            _para = _para.strip()
            if _para.startswith("KEYWORDS:"):
                rows.append(Ability("Keywords", label="KEYWORDS",
                                    body=_para[len("KEYWORDS:"):].strip()))
            elif _para.startswith("FACTION KEYWORDS:"):
                rows.append(Ability("Keywords", label="FACTION KEYWORDS",
                                    body=_para[len("FACTION KEYWORDS:"):].strip()))
    except OSError:
        rows = []'''

# ------------------------------------------ 4. the card never draws it
DRAW_NEW = '''        if keyword_groups:
            self._draw_abilities(surface, box_rect, y, keyword_groups, title="KEYWORDS")'''
DRAW_OLD = '''        pass  # probe: the keyword section is never drawn'''

# --------------------------------- 5. the height forgets the new section
HEIGHT_NEW = '''        if keyword_groups:
            height += self._abilities_height(keyword_groups)'''
HEIGHT_OLD = '''        pass  # probe: the height forgets the keyword section'''

# ------------------------- 6. one datasheet only, for an attached unit
GROUPS_NEW = '''        if attached_units.is_attached_unit(squad):
            groups, seen = [], set()
            for component in attached_units.components(squad):
                datasheet = getattr(component, "datasheet", None)
                if datasheet is None or id(datasheet) in seen:
                    continue
                seen.add(id(datasheet))
                keywords = rules_text.keywords_for(datasheet)
                if keywords:
                    groups.append((component.name, keywords))
            return groups
        keywords = rules_text.keywords_for(getattr(squad, "datasheet", None))
        return [(None, keywords)] if keywords else []'''
GROUPS_OLD = '''        keywords = rules_text.keywords_for(getattr(squad, "datasheet", None))
        return [(None, keywords)] if keywords else []'''

PROBES = [
    ("the section is filtered out again (the whole pre-fix world)",
     [(RT, READER_NEW, READER_OLD)]),
    ("the ENGINE tuples are read instead of the printed corpus",
     [(RT, READER_NEW, ENGINE_OLD)]),
    ("a hand-rolled startswith() parser replaces the shared classifier",
     [(RT, READER_NEW, PARSER_OLD)]),
    ("the card never draws the section",
     [(CARD, DRAW_NEW, DRAW_OLD)]),
    ("the height forgets the section it draws",
     [(CARD, HEIGHT_NEW, HEIGHT_OLD)]),
    ("an attached unit shows only one datasheet's bar (19.03 pools them)",
     [(CARD, GROUPS_NEW, GROUPS_OLD)]),
]

print(__doc__.strip())
print()
base, total, _t = run(SUITE)
print("BASELINE %s: %s/%s" % (SUITE, base, total))
print()

bad = 0
for label, edits in PROBES:
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
        got, tot, text = run(SUITE)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < base:
            verdict, detail = "BITES", "%d/%d" % (got, tot)
        else:
            verdict, detail = "NO BITE", "%d/%d - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < base:
            for line in text.splitlines():
                if line.strip().startswith("FAIL"):
                    print("             " + line.strip()[:112])
                    break
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
