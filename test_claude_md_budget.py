"""Budget guard for CLAUDE.md and docs/stand/.

WHY THIS EXISTS: CLAUDE.md is loaded IN FULL into every request. It had grown to 1.19 MB (measured
~2 characters per token, so ~590k tokens per request), and longer tasks died with "prompt too
long", which /compact cannot fix because compaction never shrinks CLAUDE.md. On 2026-09-17 the
state sections moved, verbatim, to docs/stand/*.md, read only on demand; CLAUDE.md kept the working
rules, an index of docs/stand/, and the open items. The file's own maintenance rule ("condense,
don't append") had been in it the whole time and did not hold - a rule that lives only in prose
stays optional (error class 4), so this file is the enforcement.

WHAT IT HOLDS:
  * CLAUDE.md stays under CLAUDE_BUDGET_BYTES;
  * CLAUDE.md @-imports nothing - an import is loaded on every request, which would undo the split;
  * every docs/stand/ file is in the index, and every index line names a file that exists;
  * each file's '## ' headings match its index bullets exactly (in order), so the index cannot rot
    and a lookup by section title always finds the right file;
  * each docs/stand/ file stays under DOC_CAP_CHARS, so ONE Read call returns it whole (the Read
    tool refuses more than 25,000 tokens);
  * no nested CLAUDE.md under docs/ - Claude Code auto-loads those too.

The audit is a pure function over text, so section 3 proves every check BITES by feeding it
mutated copies in memory - no probe has to write the real files.
"""
import glob
import os
import re

from testkit import Checks

ROOT = os.path.dirname(os.path.abspath(__file__))
CLAUDE_BUDGET_BYTES = 100_000
DOC_CAP_CHARS = 42_000
INDEX_HEADING = "# Teil 2 — Stand: Verzeichnis von `docs/stand/`"
FILE_LINE = re.compile(r"^### `docs/stand/([^`]+\.md)` — (.+)$")
IMPORT = re.compile(r"(?m)(?:^|\s)@(?:[\w.\-]+[/\\])*[\w.\-]+\.(?:md|txt)\b")


def section_headings(text):
    """The '## ' titles of a markdown text, ignoring fenced code blocks."""
    fence, out = False, []
    for line in text.splitlines():
        if line.startswith("```"):
            fence = not fence
        elif not fence and line.startswith("## "):
            out.append(line[3:])
    return out


def parse_index(claude_text):
    """{filename: (description, [bullets])} from Teil 2 of CLAUDE.md, or None if it is missing."""
    lines = claude_text.splitlines()
    if INDEX_HEADING not in lines:
        return None
    start = lines.index(INDEX_HEADING) + 1
    index, current = {}, None
    for line in lines[start:]:
        if line.startswith("# "):  # Teil 3 begins
            break
        m = FILE_LINE.match(line)
        if m:
            current = m.group(1)
            index[current] = (m.group(2).strip(), [])
        elif line.startswith("## ") or line.startswith("### "):
            current = None  # a group heading, or a malformed file line
            if line.startswith("### "):
                index.setdefault("<malformed>", ("", []))[1].append(line)
        elif current and line.startswith("- "):
            index[current][1].append(line[2:])
    return index


def audit(claude_text, claude_bytes, docs):
    """Every broken promise, as readable strings. ``docs`` maps filename -> text."""
    problems = []
    if claude_bytes > CLAUDE_BUDGET_BYTES:
        problems.append(f"CLAUDE.md is {claude_bytes:,} bytes, budget {CLAUDE_BUDGET_BYTES:,} - "
                        "move state into docs/stand/ instead of appending here")
    for m in IMPORT.finditer(claude_text):
        problems.append(f"CLAUDE.md @-imports {m.group(0).strip()!r} - that loads it on every request")
    index = parse_index(claude_text)
    if index is None:
        return problems + ["CLAUDE.md has no index heading " + repr(INDEX_HEADING)]
    if "<malformed>" in index:
        problems.append(f"malformed index file line(s): {index.pop('<malformed>')[1]}")
    for name in sorted(set(index) - set(docs)):
        problems.append(f"index names docs/stand/{name}, which does not exist")
    for name in sorted(set(docs) - set(index)):
        problems.append(f"docs/stand/{name} is not in CLAUDE.md's index")
    for name in sorted(set(index) & set(docs)):
        desc, bullets = index[name]
        text = docs[name]
        if not desc:
            problems.append(f"index line for {name} has no description")
        if len(text) > DOC_CAP_CHARS:
            problems.append(f"docs/stand/{name} is {len(text):,} chars, cap {DOC_CAP_CHARS:,} - "
                            "split it at a '###' ('## <Abschnitt> — Fortsetzung') or start a new file")
        heads = section_headings(text)
        if not heads:
            problems.append(f"docs/stand/{name} has no '## ' section")
        if heads != bullets:
            missing = [h for h in heads if h not in bullets]
            stale = [b for b in bullets if b not in heads]
            problems.append(f"index bullets for {name} differ from its '## ' headings: "
                            f"not indexed {missing}, stale {stale}"
                            + ("" if missing or stale else " (order differs)"))
    return problems


def load():
    path = os.path.join(ROOT, "CLAUDE.md")
    raw = open(path, "rb").read()
    docs = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "docs", "stand", "*.md"))):
        docs[os.path.basename(p)] = open(p, encoding="utf-8").read()
    # the byte budget counts the file as it sits on disk (CRLF); the text is compared with LF, the
    # way the docs are read - a mutation that searches for '\n' must be able to find it
    return raw.decode("utf-8").replace("\r\n", "\n"), len(raw), docs


checks = Checks("CLAUDE.md budget and docs/stand index")
claude_text, claude_bytes, docs = load()
index = parse_index(claude_text) or {}

# ================================================== 1. the real files keep every promise
print("1) the shipped CLAUDE.md and docs/stand/ keep every promise")
problems = audit(claude_text, claude_bytes, docs)
checks.eq("no budget, import, index or size problems", problems, [])
checks.true(f"CLAUDE.md is under budget ({claude_bytes:,} bytes)", claude_bytes <= CLAUDE_BUDGET_BYTES)
checks.eq("no nested CLAUDE.md under docs/ (Claude Code would auto-load it)",
          glob.glob(os.path.join(ROOT, "docs", "**", "CLAUDE.md"), recursive=True), [])

# ================================================== 2. liveness - an empty world passes every check above
print("2) liveness: the audit had something to audit")
checks.true(f"docs/stand/ holds the split files (found {len(docs)})", len(docs) >= 30)
bullets = sum(len(b) for _, b in index.values())
checks.true(f"the index lists the sections (found {bullets})", bullets >= 70)
checks.true("the Teil-1 catalogues point at their new homes",
            "docs/stand/extraktionen.md" in claude_text and "docs/stand/werkzeuge.md" in claude_text)
checks.true("the maintenance rule names this guard", "test_claude_md_budget.py" in claude_text)
checks.true("the open items stayed in CLAUDE.md",
            "## Bekannte offene Punkte" in claude_text and "## Später-Liste" in claude_text)

# ================================================== 3. every check bites, on mutated copies in memory
print("3) each promise, broken on a copy, is reported")


def bites(label, text, nbytes, docset, needle):
    found = [p for p in audit(text, nbytes, docset) if needle in p]
    checks.true(f"{label} -> reported ({needle!r})", found)


some_doc = sorted(docs)[0] if docs else "x.md"
bites("CLAUDE.md over budget", claude_text, CLAUDE_BUDGET_BYTES + 1, docs, "budget")
bites("an @-import of a docs file", claude_text + "\n@docs/stand/ki-weiche.md\n", claude_bytes, docs,
      "@-imports")
bites("an @-import mid-line", claude_text + "\nsiehe @CLAUDE.history.md\n", claude_bytes, docs, "@-imports")
checks.eq("an '@(x,y)' log-format mention is NOT an import",
          [p for p in audit(claude_text + "\n`@(x,y)`\n", claude_bytes, docs) if "@-imports" in p], [])
first_bullet = next((f"- {b[0]}\n" for _, b in index.values() if b), "\n")
bites("an index bullet removed", claude_text.replace(first_bullet, "", 1), claude_bytes, docs, "not indexed")
bites("a file line removed from the index",
      "\n".join(l for l in claude_text.splitlines() if not l.startswith(f"### `docs/stand/{some_doc}`")),
      claude_bytes, docs, "not in CLAUDE.md's index")
bites("a doc file deleted", claude_text, claude_bytes, {k: v for k, v in docs.items() if k != some_doc},
      "does not exist")
bites("an unlisted doc file added", claude_text, claude_bytes, {**docs, "neu.md": "## Neu\n"},
      "not in CLAUDE.md's index")
bites("a doc over the cap", claude_text, claude_bytes,
      {**docs, some_doc: docs.get(some_doc, "") + "x" * (DOC_CAP_CHARS + 1)}, "cap")
bites("a section appended to a doc without an index line", claude_text, claude_bytes,
      {**docs, some_doc: docs.get(some_doc, "") + "\n## Ein neuer Abschnitt\n"}, "not indexed")
two = next((n for n, (_, b) in index.items() if len(b) >= 2 and n in docs), None)
checks.true("liveness: some doc holds two sections to swap", two)
if two:
    b1, b2 = index[two][1][:2]
    bites("two sections swapped in order (same set)", claude_text, claude_bytes,
          {**docs, two: f"## {b2}\n## {b1}\n" + "".join(f"## {b}\n" for b in index[two][1][2:])},
          "order differs")
checks.eq("a '## ' line inside a code fence is not a section",
          section_headings("## A\n```\n## not a heading\n```\n## B\n"), ["A", "B"])
bites("the index heading renamed", claude_text.replace(INDEX_HEADING, "# Teil 2", 1), claude_bytes, docs,
      "no index heading")

checks.finish()
