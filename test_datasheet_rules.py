"""The rules/*.md corpus and the parser that writes it.

Every section here pins a defect that was real - each one was measured on the
live page, produced wrong markdown, and was fixed. A parser like this has no
natural failure signal: it never raises, it just quietly writes a slightly
wrong file, and the corpus is only worth having if what is in it is exactly
what is printed.

Runs entirely against rules/.cache/, so it makes no network request. If the
cache is absent (a fresh clone - it is gitignored) the parser sections skip
themselves and only the corpus checks run.

  1. Corpus shape: one file per built datasheet, plus the T'au entries that
     are snapshotted ahead of being built.
  2. Determinism: the rendering is a pure function of the HTML, and is
     insensitive to the line-ending drift that made two fetches of an
     unchanged page produce 60-odd spurious diffs.
  3. Parser fidelity, against the cached pages.
  4. Source guards on fetch_datasheet_rules.py itself.
"""

import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fetch_datasheet_rules as F
from game.factions import aeldari, death_guard, necrons, orks, tau_empire

PASS = []
FAIL = []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))


CACHE_READY = all(
    os.path.exists(os.path.join(F.CACHE_DIR, "%s.html" % slug))
    for _folder, slug, _faction in F.FACTIONS
)

_PAGES = {}


def page(slug):
    if slug not in _PAGES:
        _PAGES[slug] = F.fetch(slug, offline=True)
    return _PAGES[slug]


def sheet_named(slug, name):
    """The parsed datasheet dict for one unit on one faction page."""
    key = F.normalise_name(name)
    for block in F.split_blocks(page(slug)):
        parsed = F.parse_datasheet(block)
        if F.normalise_name(parsed["name"]) == key:
            return parsed
    return None


def corpus_text(folder, name):
    path = os.path.join("rules", folder, "%s.md" % F.safe_filename(name))
    if not os.path.exists(path):
        return ""
    return io.open(path, encoding="utf-8").read()


def corpus_text_path(path):
    """Like corpus_text(), but for the files that are not one-per-datasheet:
    army_rules.md and the detachments/ subfolder."""
    if not os.path.exists(path):
        return ""
    return io.open(path, encoding="utf-8").read()


def md_section(text, heading):
    match = re.search(r"^## %s\s*$" % re.escape(heading), text, re.M)
    if not match:
        return ""
    rest = text[match.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return (rest[:nxt.start()] if nxt else rest).strip()


# --- 1. Corpus shape ------------------------------------------------------
print("\n1. Corpus shape")

FACTION_MODULES = [
    ("aeldari", aeldari.AELDARI),
    ("orks", orks.ORKS),
    ("necrons", necrons.NECRONS),
    ("tau_empire", tau_empire.TAU_EMPIRE),
    ("death_guard", death_guard.DEATH_GUARD),
]

missing = []
for folder, faction in FACTION_MODULES:
    for name in faction.datasheets:
        if not corpus_text(folder, name):
            missing.append("%s/%s" % (folder, name))
check("every built datasheet has a rules/*.md file", not missing,
      "missing: %s" % missing[:5] if missing else
      "%d datasheets" % sum(len(f.datasheets) for _n, f in FACTION_MODULES))

# Every folder that snapshots not-yet-built entries is checked the same way,
# off MISSING_BY_FOLDER rather than off one hardcoded faction - a third list
# is then a dict entry in the script and needs no edit here.
_BUILT_BY_FOLDER = {folder: {F.normalise_name(n) for n in faction.datasheets}
                    for folder, faction in FACTION_MODULES}
for _folder, _extra in sorted(F.MISSING_BY_FOLDER.items()):
    _absent = [n for n in _extra if not corpus_text(_folder, n)]
    check("every not-yet-built %s datasheet is snapshotted too" % _folder,
          not _absent,
          "missing: %s" % _absent[:5] if _absent else "%d entries" % len(_extra))

# A MISSING_* list is deliberately NOT pruned as its entries get built - the
# script deduplicates instead, so the list is a stable record of what a roster
# was missing rather than something to maintain by hand. That means the
# expected file count has to deduplicate the same way.
files = [f for f in glob.glob(os.path.join("rules", "*", "*.md"))
         if os.path.basename(f) != "army_rules.md"]
still_missing = {
    folder: [n for n in extra
             if F.normalise_name(n) not in _BUILT_BY_FOLDER.get(folder, set())]
    for folder, extra in F.MISSING_BY_FOLDER.items()
}
expected = (sum(len(f.datasheets) for _n, f in FACTION_MODULES)
            + sum(len(v) for v in still_missing.values()))
check("no stray files in the corpus", len(files) == expected,
      "%d files, expected %d" % (len(files), expected))
_already_built = sum(
    len([n for n in extra
         if F.normalise_name(n) in _BUILT_BY_FOLDER.get(folder, set())])
    for folder, extra in F.MISSING_BY_FOLDER.items())
check("a datasheet that has since been built is not written twice",
      sum(len(v) for v in still_missing.values())
      == sum(len(v) for v in F.MISSING_BY_FOLDER.values()) - _already_built)
# The Aeldari list is the one that must stay Legends-free: the corpus has never
# carried a "**Legends:** yes" file, and a Legends entry would change its shape
# rather than just its size.
_legends_slugs = {b["slug"].replace("-", " ").lower()
                  for b in F.split_blocks(page("aeldari")) if b["legends"]}
check("no Legends unit is snapshotted for Aeldari",
      not [n for n in F.MISSING_AELDARI if n.lower() in _legends_slugs])

# The whole point of the folder: a re-run must be diffable, so a per-file
# timestamp is forbidden. The fetch date belongs in README.md alone.
dated = [f for f in files
         if re.search(r"\b20\d\d-\d\d-\d\d\b", io.open(f, encoding="utf-8").read())]
check("no fetch date inside a datasheet file (it would churn every run)",
      not dated, "dated: %s" % dated[:3] if dated else "")
check("the fetch date IS in rules/README.md",
      bool(re.search(r"Last fetched: 20\d\d-\d\d-\d\d",
                     io.open(os.path.join("rules", "README.md"),
                             encoding="utf-8").read())))

# --- 2. Determinism -------------------------------------------------------
print("\n2. Determinism")

if not CACHE_READY:
    check("rules/.cache present (skipping parser sections)", False,
          "run: python fetch_datasheet_rules.py")
else:
    sample = sheet_named("t-au-empire", "Cadre Fireblade")
    once = F.render_markdown(sample, "T'au Empire", "t-au-empire")
    twice = F.render_markdown(sheet_named("t-au-empire", "Cadre Fireblade"),
                              "T'au Empire", "t-au-empire")
    check("rendering the same block twice gives identical text", once == twice)

    # Measured failure: curl and urllib returned the same unchanged page with
    # different CRs, which reached the markdown and "changed" 60-odd files.
    raw = page("t-au-empire")
    crlf = raw.replace("\n", "\r\n")
    blocks = F.split_blocks(F.normalise_newlines(crlf))
    parsed = next(F.parse_datasheet(b) for b in blocks
                  if F.normalise_name(b["slug"]) == F.normalise_name("Cadre-Fireblade"))
    check("CRLF input renders identically to LF input",
          F.render_markdown(parsed, "T'au Empire", "t-au-empire") == once)

    check("normalise_newlines removes every CR",
          "\r" not in F.normalise_newlines("a\r\nb\rc"))

# --- 3. Parser fidelity ---------------------------------------------------
print("\n3. Parser fidelity (against the cached pages)")

if CACHE_READY:
    # -- weapon keywords are nested spans -------------------------------
    # "rapid fire 1" is three sibling spans inside the keyword span; a
    # non-greedy </span> cut it to "rapid" and left "fire 1" glued onto the
    # weapon's name.
    fireblade = sheet_named("t-au-empire", "Cadre Fireblade")
    ranged = fireblade["weapons"][0]["rows"][0]
    check("weapon name has no keyword text glued to it",
          ranged["name"] == "Fireblade pulse rifle", ranged["name"])
    check("a multi-word weapon keyword survives whole",
          ranged["keywords"] == ["rapid fire 1"], str(ranged["keywords"]))

    devilfish = sheet_named("t-au-empire", "Devilfish")
    sms = [r for r in devilfish["weapons"][0]["rows"]
           if r["name"] == "Smart missile system"]
    check("a weapon with one keyword parses it",
          len(sms) == 1 and sms[0]["keywords"] == ["indirect fire"],
          str(sms[0]["keywords"]) if sms else "row not found")

    bloat = sheet_named("death-guard", "Foetid Bloat-drone")
    spitter = bloat["weapons"][0]["rows"][0]
    check("a weapon with three keywords parses all three",
          spitter["keywords"] == ["anti-infantry 2+", "ignores cover", "torrent"],
          str(spitter["keywords"]))
    check("a [TORRENT] weapon keeps its printed N/A ballistic skill",
          "N/A" in spitter["values"], str(spitter["values"]))

    # -- the duplicate narrow-screen row is dropped ---------------------
    names = [r["name"] for r in fireblade["weapons"][0]["rows"]]
    check("each weapon appears once, not twice", len(names) == len(set(names)),
          str(names))

    # -- nested wargear lists -------------------------------------------
    boyz_md = corpus_text("orks", "Boyz")
    wargear = md_section(boyz_md, "Wargear Options")
    check("a nested wargear sub-choice is indented, not flattened",
          "\n  - 1 big choppa and 1 kustom shoota" in "\n" + wargear,
          wargear.split("\n")[1] if wargear else "")
    check("consecutive bullets are not separated by blank lines",
          "\n\n- Any number of Boyz" not in wargear)

    # -- points tiers ----------------------------------------------------
    # Both tiers live in ONE table as two header rows; reading the header once
    # per table labelled the 4th+ prices as 1st-to-3rd.
    boyz_points = md_section(boyz_md, "Points")
    check("a tiered unit keeps both tier labels",
          "YOUR 1ST TO 3RD UNITS COST" in boyz_points
          and "YOUR 4TH + UNIT COSTS" in boyz_points)
    check("tiered prices are not collapsed onto one tier",
          boyz_points.count("YOUR 4TH + UNIT COSTS") == 2, boyz_points)
    check("points are a section of their own, not swallowed by composition",
          "1 model50" not in corpus_text("tau_empire", "Cadre Fireblade"))

    # -- invulnerable save ----------------------------------------------
    # Not part of the characteristics row - its own dsInvulWrap box - and
    # genuinely per model line on the Aspect Warrior squads.
    scorpions = sheet_named("aeldari", "Striking Scorpions")
    check("the invulnerable save is captured at all",
          all(p["invul"] == "5+" for p in scorpions["profiles"]),
          str([p["invul"] for p in scorpions["profiles"]]))
    wraithguard = sheet_named("aeldari", "Wraithguard")
    check("a datasheet without one gets no invulnerable save",
          not any(p["invul"] for p in wraithguard["profiles"]))
    check("a conditional save keeps its printed asterisk",
          "5+*" in md_section(corpus_text("aeldari", "Rangers"), "Profile"))

    # -- multi-profile statlines ----------------------------------------
    boyz = sheet_named("orks", "Boyz")
    check("both model profiles are parsed", len(boyz["profiles"]) == 2,
          str(len(boyz["profiles"])))
    check("characteristic names carry over to the second profile "
          "(only the first prints them)",
          boyz["char_names"] == ["M", "T", "SV", "W", "LD", "OC"],
          str(boyz["char_names"]))
    check("each profile keeps its own model label and base",
          [p["label"] for p in boyz["profiles"]] == ["BOY", "BOSS NOB"],
          str([p["label"] for p in boyz["profiles"]]))
    check("the Boss Nob's extra wound is not lost",
          boyz["profiles"][1]["values"][3] == "2",
          str(boyz["profiles"][1]["values"]))

    # -- the Damaged profile --------------------------------------------
    # Its dsHeader carries a <span class="dsSkull2"> icon, not a "...Icon"
    # one, so requiring the Icon suffix folded it into the section above.
    riptide_md = corpus_text("tau_empire", "Riptide Battlesuit")
    check("a Damaged profile becomes its own section",
          "## Damaged: 1-4 Wounds Remaining" in riptide_md)

    # -- the cut point ---------------------------------------------------
    # Everything below the keywords bar is the faction's whole stratagem list,
    # repeated on all 384 blocks. Two attachment sections are the exception.
    for folder, name in [("tau_empire", "Cadre Fireblade"), ("orks", "Boyz"),
                         ("necrons", "Doomsday Ark")]:
        text = corpus_text(folder, name)
        check("%s carries no detachment furniture" % name,
              "## Stratagems" not in text and "## Detachment Ability" not in text
              and "## Enhancements" not in text)
    check("LED BY is rescued from below the keywords bar",
          "- WARBOSS" in md_section(boyz_md, "Led By"))
    check("SUPPORTED BY is rescued too",
          "- PAINBOY" in md_section(boyz_md, "Supported By"))
    check("a LEADER section above the bar still works",
          "- STRIKE TEAM" in md_section(
              corpus_text("tau_empire", "Cadre Fireblade"), "Leader"))

    # -- keywords --------------------------------------------------------
    # Wahapedia spells these two class names with a CYRILLIC "С"; a Latin C
    # matched nothing and dropped the faction keywords line silently.
    fireblade_md = corpus_text("tau_empire", "Cadre Fireblade")
    check("the keywords line is captured",
          "KEYWORDS: INFANTRY; CHARACTER; GRENADES; CADRE FIREBLADE" in fireblade_md)
    check("the faction keywords line is captured (Cyrillic class name)",
          "FACTION KEYWORDS: T’AU EMPIRE" in fireblade_md)

    # -- abilities are verbatim ------------------------------------------
    abilities = md_section(fireblade_md, "Abilities")
    check("an ability keeps its printed name and full sentence",
          "**Crack Shot:** Each time this model makes a ranged attack, on a "
          "Critical Wound, that attack has an Armour Penetration "
          "characteristic of -3." in abilities)
    check("two abilities sharing one container stay separate",
          "**Volley Fire:**" in abilities and "**Crack Shot:**" in abilities
          and abilities.count("\n\n**Crack Shot:**") == 1)
    check("CORE and FACTION ability lines are kept",
          "CORE: **Leader**" in abilities
          and "FACTION: **For the Greater Good**" in abilities)

    # -- name matching ---------------------------------------------------
    # The three ways the engine and the page disagree, all handled without an
    # alias table.
    check("normalisation folds a curly apostrophe",
          F.normalise_name("Ta’unar") == F.normalise_name("Ta'unar"))
    check("normalisation folds capitalisation",
          F.normalise_name("Commander in Coldstar Battlesuit")
          == F.normalise_name("Commander In Coldstar Battlesuit"))
    check("normalisation folds punctuation",
          F.normalise_name("Kroot Lone-spear") == F.normalise_name("Kroot Lone-Spear"))
    check("a file name never keeps a curly apostrophe",
          "’" not in F.safe_filename("Ta’unar Supremacy Armour"))

    # -- legends ----------------------------------------------------------
    legends = [b["slug"] for b in F.split_blocks(page("t-au-empire")) if b["legends"]]
    check("Legends datasheets are recognised", len(legends) == 19, str(len(legends)))
    check("no built datasheet is marked Legends",
          all("**Legends:** no" in corpus_text(folder, name)
              for folder, faction in FACTION_MODULES for name in faction.datasheets))

# --- 4. Source guards -----------------------------------------------------
print("\n4. Source guards")

src = io.open("fetch_datasheet_rules.py", encoding="utf-8").read()
check("the corpus is written UTF-8 explicitly (Windows defaults to cp1252, "
      "which cannot encode the base-size symbol)",
      src.count('encoding="utf-8", newline="\\n"') >= 2)
check("a datasheet the page no longer names aborts the run",
      # Matched without its indentation: this text moved into a helper when the
      # faction-page pass was added, and pinning the leading spaces made the
      # guard fail for a reason that had nothing to do with what it guards.
      re.search(r'raise SystemExit\(\s*\n\s*"no Wahapedia datasheet found for %s', src)
      is not None)
check("a short faction page aborts the run rather than truncating the corpus",
      "MIN_BLOCKS_PER_FACTION" in src and "refusing to write a" in src)
check("--only that names nothing is an error, not a silent no-op",
      '--only named no known datasheet' in src)
check("both fetch paths normalise newlines",
      src.count("normalise_newlines(") >= 3)

gitignore = io.open(".gitignore", encoding="utf-8").read()
check("the raw HTML cache is gitignored", "rules/.cache/" in gitignore)
check("the markdown itself is NOT gitignored",
      not re.search(r"^\s*rules/\s*$", gitignore, re.M))

# --- 5. Army rules and detachments ----------------------------------------
# A second page per faction (the faction index), because datasheets.html has
# neither: measured, "For The Greater Good" appears zero times on it, and the
# detachments it does mention carry only the stratagems the datasheet in hand
# can use - three of T'au's seven came back truncated.
print("\n5. Army rules and detachments")

for folder, _slug, _faction in F.FACTIONS:
    text = corpus_text_path(os.path.join("rules", folder, "army_rules.md"))
    check("%s has an army_rules.md with a rule in it" % folder,
          bool(text) and len(text) > 400, "%d chars" % len(text))

DETACHMENT_COUNTS = {
    # Measured on the live pages. A count that drops is the signal that the
    # page shape moved, which is the only way this corpus can go quietly wrong.
    "aeldari": 15, "orks": 13, "necrons": 12, "tau_empire": 7, "death_guard": 9,
}
for folder, expected_count in sorted(DETACHMENT_COUNTS.items()):
    found = glob.glob(os.path.join("rules", folder, "detachments", "*.md"))
    check("%s snapshots all %d detachments" % (folder, expected_count),
          len(found) == expected_count, "%d files" % len(found))

# The five T'au detachments being built, plus the one that already exists.
# Named individually rather than counted: a detachment whose rule text failed
# to parse still leaves a file behind, and only reading it says so.
for name in ["Retaliation Cadre", "Kauyon", "Mont'ka", "Experimental Prototype Cadre",
             "Advanced Acquisition Cadre", "Auxiliary Cadre"]:
    text = corpus_text_path(
        os.path.join("rules", "tau_empire", "detachments", "%s.md" % F.safe_filename(name)))
    check("%s carries its detachment rule" % name,
          "## Detachment rule" in text and len(md_section(text, "Detachment rule")) > 120)
    check("%s carries at least one stratagem" % name,
          "## Stratagems" in text and "**WHEN:**" in text)

# The errata block's own Show/Hide control sits INSIDE the errata text, so it
# lands mid-sentence unless the whole control is dropped.
kauyon = corpus_text_path(os.path.join("rules", "tau_empire", "detachments", "Kauyon.md"))
check("the errata Show/Hide toggle is not rendered as rule text",
      not re.search(r"^\s*Show\s*$", kauyon, re.M))
check("errata are kept, though - they are rule changes",
      "### Errata" in kauyon)

# Death Guard files its army rule in a SIBLING h2 after an empty "Army Rules"
# heading, where the other four use h3 children. Pinned because a parser that
# only reads the h3s returns nothing for it, silently.
check("Death Guard's sibling-h2 army rule is found",
      "Nurgle" in corpus_text_path(os.path.join("rules", "death_guard", "army_rules.md")))
# The enhancements heading is not always "Enhancements". Aeldari's Corsair
# detachments say "Corsair Enhancements" (which a suffix match would still
# catch) and Necrons' Pantheon of Woe says "Necrodermal Binding Abilities"
# (which it would not) - so they are found by markup, not by title. Pantheon
# is the one that actually discriminates; A/B: matching on the title loses all
# four of its enhancements and none of Corsair Coterie's.
for folder, name in [("necrons", "Pantheon of Woe"), ("aeldari", "Corsair Coterie")]:
    text = corpus_text_path(
        os.path.join("rules", folder, "detachments", "%s.md" % F.safe_filename(name)))
    check("%s's oddly-titled enhancements section is still found" % name,
          "## Enhancements" in text and text.count("### ") >= 4)

check("a short faction page aborts the run too",
      "MIN_DETACHMENTS_PER_FACTION" in src)
check("a faction page with no army rule aborts the run",
      "yielded no army rule" in src)
check("--detachment that names nothing is an error, not a silent no-op",
      "--detachment named no known detachment" in src)
check("the faction page is cached under its own name",
      '"%s-faction" % slug' in src)

print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print("  -", f)
    raise SystemExit(1)
