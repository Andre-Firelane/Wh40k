"""THE IDENTITY PROBE for the rules_text block API.

`army_rule_text()` / `detachment_rule_text()` are pinned by two suites, so the
whole "one parser, two views" design stands or falls on one claim: the flat
projection of the new typed lines is BYTE-IDENTICAL to what the old flat
parser emitted. This replays the pre-block `_paragraphs()` verbatim against
every section of every corpus file and diffs.

A refactor that "looks equivalent" is exactly the kind this repo measures
instead of asserting.
"""

import os
import re

from game import rules_text as rt

# ---------------------------------------------------------------- the OLD one
# Copied verbatim from before the block API, warts included - the separator
# that gets overwritten by the join is part of what must be reproduced.


def old_paragraphs(body):
    if not body:
        return []
    out = []
    for block in re.split(r"\n\s*\n", body):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        for line in lines:
            line = rt._split_table_row(line)
            if line.startswith("- "):
                out.append("- " + rt._strip_markdown(line[2:]))
            elif line.startswith("### "):
                out.append(rt._strip_markdown(line[4:]))
            else:
                text = rt._strip_markdown(line)
                if out and not out[-1].startswith("- ") and not block.startswith("- "):
                    out[-1] = (out[-1] + " " + text).strip()
                else:
                    out.append(text)
        out.append("")
    while out and not out[-1]:
        out.pop()
    return out


def corpus_files():
    for folder in sorted(os.listdir(rt.RULES_DIR)):
        base = os.path.join(rt.RULES_DIR, folder)
        if not os.path.isdir(base):
            continue
        army = os.path.join(base, "army_rules.md")
        if os.path.exists(army):
            yield army
        detach = os.path.join(base, "detachments")
        if os.path.isdir(detach):
            for name in sorted(os.listdir(detach)):
                if name.endswith(".md"):
                    yield os.path.join(detach, name)


files = sections = mismatch = lossy = 0
first = []
for path in corpus_files():
    files += 1
    for heading, body in rt._sections(path):
        sections += 1
        want, got = old_paragraphs(body), rt._paragraphs(body)
        if want != got:
            mismatch += 1
            if len(first) < 3:
                for a, b in zip(want, got):
                    if a != b:
                        first.append(f"{os.path.basename(path)} / {heading}\n"
                                     f"   old: {a[:90]!r}\n   new: {b[:90]!r}")
                        break
                else:
                    first.append(f"{os.path.basename(path)} / {heading}: "
                                 f"length {len(want)} -> {len(got)}")
        # The runs must be lossless too: joining them back has to give the
        # same string _strip_markdown would have produced.
        for line in rt._corpus_lines(body):
            if line.kind == "table":
                continue   # the one place a space is inserted, by design
            joined = "".join(t for t, _b in line.runs)
            raw = line.text
            if line.kind == "bullet":
                raw = raw[2:]
            elif line.kind == "label":
                raw = raw[len(line.label) + 1:]
            elif line.kind == "subtitle":
                # Its flat text deliberately KEEPS the italic markers so the
                # projection cannot move, while the runs have them stripped for
                # the reader. Comparing the two without accounting for that
                # would report all 283 subtitles as lossy.
                raw = raw.strip("*")
            if " ".join(joined.split()) != " ".join(raw.split()):
                lossy += 1

print(f"corpus files          : {files}")
print(f"sections compared     : {sections}")
print(f"flat-view MISMATCHES  : {mismatch}")
print(f"lossy run splits      : {lossy}")
for line in first:
    print("  " + line)
raise SystemExit(1 if (mismatch or lossy) else 0)
