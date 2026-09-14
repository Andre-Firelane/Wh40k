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
import unicodedata

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
    # One sheet per LAYOUT: rules/orks/ has been refetched in the 2026-09
    # layout, the other four folders are still the old one, and the nested
    # <ul> is rendered by the same code in both - which is exactly what has to
    # stay true.
    guardians_md = corpus_text("aeldari", "Guardian Defenders")
    old_wargear = md_section(guardians_md, "Wargear Options")
    check("a nested wargear sub-choice is indented, not flattened (old layout)",
          "\n  - 1 missile launcher" in "\n" + old_wargear,
          old_wargear.split("\n")[1] if old_wargear else "")
    boyz_md = corpus_text("orks", "Boyz")
    wargear = md_section(boyz_md, "Wargear Options")
    check("...and in the 2026-09 layout",
          "\n  - 1 Kombi-rokkit" in "\n" + wargear,
          wargear.split("\n")[1] if wargear else "")
    check("consecutive bullets are not separated by blank lines",
          "\n\n- Any number of Nob models" not in wargear and "- Any number of Nob models" in wargear)

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
    # Both layouts, because both are live in the corpus: the old one on the
    # Aeldari page, the 2026-09 one on the refetched Ork page.
    _empty = {"profiles": [], "char_names": []}
    for slug, sheet, labels, wounds in (
            ("aeldari", "Dire Avengers", ["DIRE AVENGER", "DIRE AVENGER EXARCH"], "2"),
            ("orks", "Boyz", ["Boy", "Nob"], "3")):
        parsed = sheet_named(slug, sheet) or _empty
        profiles = parsed["profiles"]
        check("%s: both model profiles are parsed" % sheet, len(profiles) == 2,
              str(len(profiles)))
        check("%s: characteristic names carry over to the second profile "
              "(only the first prints them)" % sheet,
              parsed["char_names"] == ["M", "T", "SV", "W", "LD", "OC"],
              str(parsed["char_names"]))
        check("%s: each profile keeps its own model label" % sheet,
              [p["label"] for p in profiles] == labels,
              str([p["label"] for p in profiles]))
        check("%s: the second line's extra wound is not lost" % sheet,
              len(profiles) == 2 and profiles[1]["values"][3] == wounds,
              str(profiles[1]["values"]) if len(profiles) == 2 else "")

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
    "aeldari": 15, "orks": 15, "necrons": 12, "tau_empire": 7, "death_guard": 9,
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

# --- 5b. the FORCE DISPOSITION on every detachment heading -----------------
# Wahapedia prints it as an ICON in the same heading span the DP cost comes
# from, so page_headings() - which strips the tags to build its title - throws
# it away. It is read in a second pass over the raw heading html.
#
# This is checked at the PARSER and at the RENDERER, not only in the written
# files: a probe that stopped render_detachment() emitting the line changed
# nothing in a suite that only ever read rules/ (those files are already on
# disk), which made the check green against a broken scraper.
if CACHE_READY:
    # The FACTION INDEX page, not the datasheets page page() serves - the
    # detachments (and so their dispositions) live only on the former.
    _fd_seen, _fd_missing = 0, []
    _faction_pages = {slug: F.fetch_faction(slug, offline=True)
                      for _f, slug, _x in F.FACTIONS}
    for folder, slug, _faction in F.FACTIONS:
        _rules, _dets = F.parse_faction_page(_faction_pages[slug])
        for det in _dets:
            _fd_seen += 1
            if not det.get("force_disposition"):
                _fd_missing.append("%s/%s" % (folder, det["name"]))
    check("every detachment on every faction page parses a Force Disposition",
          _fd_seen >= 56 and not _fd_missing, "%d seen, missing: %s"
          % (_fd_seen, _fd_missing[:3]))
    # Wahapedia's detachment FILTER list spells Kauyon with a Cyrillic o
    # (U+043E); the HEADING spells it in Latin. Reading the heading is what
    # keeps rules/tau_empire/detachments/Kauyon.md addressable at all.
    _tau_fd = F.heading_force_dispositions(_faction_pages["t-au-empire"])
    check("the heading pass finds Kauyon under its LATIN spelling",
          "Kauyon2DP" in _tau_fd and _tau_fd["Kauyon2DP"] == "Reconnaissance",
          str(sorted(_tau_fd)[:3]))
    # ...and the renderer actually emits it.
    _rendered = F.render_detachment(
        "T'au Empire", "t-au-empire",
        {"name": "Kauyon", "dp": 2, "force_disposition": "Reconnaissance",
         "rule": [], "enhancements": [], "stratagems": []})
    check("render_detachment() writes the Force Disposition beside the DP",
          "**T'au Empire** - 2 DP detachment - Force Disposition: Reconnaissance"
          in _rendered)
    # A detachment whose page states none must not grow an empty tail.
    _bare = F.render_detachment(
        "T'au Empire", "t-au-empire",
        {"name": "Nameless", "dp": 1, "force_disposition": "",
         "rule": [], "enhancements": [], "stratagems": []})
    check("...and omits it entirely when the page states none",
          "**T'au Empire** - 1 DP detachment\n" in _bare
          and "Force Disposition" not in _bare)

# --- 5c. no flavour, no worked examples -----------------------------------
# User, after a game spent reading the army rules in the panel: "keine
# hintergrund info texte und example texte in den armeeregeln bitte. nur
# reine regeltexte."
#
# Wahapedia marks both itself - ShowFluff is the class its own show/hide-fluff
# toggle hangs on, redExample is the worked example printed under a rule - so
# this is measured against the CACHED PAGES rather than against a handful of
# quoted lore sentences. A pin naming three paragraphs goes green the moment a
# fourth appears.
#
# THREE LEVELS, and section 5b above is why: a suite that only reads rules/
# stays green against a broken scraper, because those files are already on
# disk. So the renderer and the stratagem parser are driven directly too.


def _fluff_key(text):
    """A line folded to a comparison key - the same folding this file already
    uses for names, so markdown emphasis and curly quotes cannot make a lore
    paragraph look like a different string than the one on the page."""
    text = unicodedata.normalize("NFKD", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


_FLUFF_HTML = (
    re.compile(r'<(p|div)[^>]*class="[^"]*\bShowFluff\b[^"]*"[^>]*>(.*?)</\1>', re.S),
    re.compile(r'<div[^>]*class="[^"]*\bredExample\b[^"]*"[^>]*>(.*?)</div>', re.S),
)

print("\n5c. Flavour and worked examples are not rule text")

# -- the renderer itself ---------------------------------------------------
check("to_markdown() drops a ShowFluff lore paragraph",
      F.to_markdown('<p class="ShowFluff legend2">Lore about dying gods.</p>'
                    '<div>If your Army Faction is X, do the thing.</div>')
      == "If your Army Faction is X, do the thing.")
check("to_markdown() drops a redExample block",
      F.to_markdown('<div>If your Army Faction is X, do the thing.</div>'
                    '<div class="redExample"><b>Example:</b> A unit of three.</div>')
      == "If your Army Faction is X, do the thing.")
# The counterpart: it must not have become a parser that drops everything.
check("...while ordinary prose in the same shape survives",
      F.to_markdown('<p class="legend2">Kept.</p><div>Also kept.</div>')
      == "Kept.\n\nAlso kept.")

if CACHE_READY:
    _pages = {slug: F.fetch_faction(slug, offline=True) for _f, slug, _x in F.FACTIONS}

    # -- the stratagem legend, which SKIP_CLASSES cannot reach --------------
    # It is lifted out of the page by its own regex, so the class never gets
    # near the renderer; it has to be left unread in STRATAGEM_FIELDS instead.
    _detachments = F.parse_faction_page(_pages["aeldari"])[1]
    _strats = [s for d in _detachments for s in d["stratagems"]]
    check("stratagems still parse off the page", len(_strats) >= 60,
          "%d found" % len(_strats))
    check("no stratagem carries a legend field any more",
          all("legend" not in s for s in _strats))
    check("...and every one still carries its WHEN/TARGET/EFFECT",
          all("WHEN:" in s["text"] for s in _strats))
    check("...and its printed type line, which is NOT flavour",
          all(s["type"] for s in _strats))

    # -- the written corpus ------------------------------------------------
    _fluff = set()
    for _folder, _slug, _x in F.FACTIONS:
        for _pattern in _FLUFF_HTML:
            for _match in _pattern.finditer(_pages[_slug]):
                _key = _fluff_key(re.sub("<[^>]+>", "", _match.group(_match.lastindex)))
                if len(_key) > 40:
                    _fluff.add(_key)
    # Without this, the absence check below would pass on an empty harvest.
    check("the flavour harvest is not empty", len(_fluff) >= 400,
          "%d blocks" % len(_fluff))

    _corpus_files = sorted(glob.glob(os.path.join("rules", "*", "army_rules.md"))
                           + glob.glob(os.path.join("rules", "*", "detachments", "*.md"))
                           + glob.glob(os.path.join("rules", "*", "*.md")))
    _leaks = []
    for _path in _corpus_files:
        for _line in io.open(_path, encoding="utf-8"):
            _key = _fluff_key(_line)
            if len(_key) > 40 and _key in _fluff:
                _leaks.append("%s: %s" % (_path, _line.strip()[:70]))
    check("no flavour or example paragraph reaches the corpus",
          not _leaks, "%d leaks, first: %s" % (len(_leaks), _leaks[:1]))

# -- the controls ----------------------------------------------------------
# Each pairs a removed paragraph with the rule that stood beside it, because
# "the lore is gone" is also true of a corpus that lost the rule with it.
_ael = corpus_text_path(os.path.join("rules", "aeldari", "army_rules.md"))
check("Battle Focus lost its lore paragraph",
      "In war, as in all things" not in _ael)
check("...and kept the rule that followed it",
      "If your Army Faction is ASURYANI, at the start of the battle round" in _ael
      and all(name in _ael for name in
              ("SWIFT AS THE WIND", "FLITTING SHADOWS", "STAR ENGINES",
               "SUDDEN STRIKE", "OPPORTUNITY SEIZED", "FADE BACK"))
      # Six printed Agile Manoeuvres, plus the one the Errata section quotes
      # back - errata are rule changes and are deliberately kept.
      and _ael.count("TRIGGER:") == 7 and _ael.count("EFFECT:") == 7)

_nec = corpus_text_path(os.path.join("rules", "necrons", "army_rules.md"))
check("Reanimation Protocols lost its worked example",
      "Example:" not in _nec)
check("...and kept the rule it was illustrating",
      "that unit **heals** D3 wounds" in _nec)

# Death Guard is the case where lore and rule alternate line by line: each of
# the three Plagues prints one sentence of flavour above its own effect.
_dg = corpus_text_path(os.path.join("rules", "death_guard", "army_rules.md"))
check("every Plague lost its flavour line",
      "This horrifying affliction" not in _dg
      and "Limbs shuddering with fever palsy" not in _dg
      and "Victims of this insidious ailment" not in _dg)
check("...and all three Plagues kept their name and their effect",
      all(name in _dg for name in
          ("Skullsquirm Blight", "Rattlejoint Ague", "Scabrous Soulrot"))
      and "Worsen the Save characteristic" in _dg)

_seer_md = corpus_text_path(
    os.path.join("rules", "aeldari", "detachments", "Seer Council.md"))
check("a detachment rule and its enhancements lost their lore",
      "Though future sight is not a precise art" not in _seer_md
      and "This helm houses a psychocrystalline weave" not in _seer_md)
check("a stratagem lost its legend but kept its subtitle and its text",
      "The seer plucks fate to find the foe" not in _seer_md
      and "*Seer Council" in _seer_md and "**WHEN:** Command phase." in _seer_md)

# -- source guards ---------------------------------------------------------
check("ShowFluff and redExample are skipped by name",
      'SKIP_CLASSES = (' in src and '"ShowFluff"' in src and '"redExample"' in src)
check("the stratagem legend is not even parsed",
      "str11Legend" not in src.split("STRATAGEM_FIELDS")[1].split("\n)")[0])


check("a short faction page aborts the run too",
      "MIN_DETACHMENTS_PER_FACTION" in src)
check("a faction page with no army rule aborts the run",
      "yielded no army rule" in src)
check("--detachment that names nothing is an error, not a silent no-op",
      "--detachment named no known detachment" in src)
check("the faction page is cached under its own name",
      '"%s-faction" % slug' in src)


# --- 6. The 2026-09 datasheet LAYOUT ---------------------------------------
# Wahapedia moved the Ork page to a new datasheet layout (2026-09), and the old
# parser read it WITHOUT an error while losing four things: the KEYWORDS bar
# (its class attribute grew a second class), the CORE and FACTION lines (they
# moved into a table the section cutter either swallowed into MELEE WEAPONS or
# glued onto WARGEAR OPTIONS), a Hunter profile's condition (a row of its own
# above the weapon), and the Damaged X marker. Each is pinned twice: on a
# committed, INVENTED fixture - so it runs on a fresh clone, where rules/.cache/
# is absent - and on the refetched Ork corpus itself. Sections 3 and 5 keep
# running against the old layout, which the other four factions still use.
print("\n6. The 2026-09 datasheet layout")

FIXTURE_PATH = os.path.join("testdata", "wahapedia_new_layout_blocks.html")
fixture_html = (io.open(FIXTURE_PATH, encoding="utf-8").read()
                if os.path.exists(FIXTURE_PATH) else "")
fixture = {}
for _block in F.split_blocks(fixture_html):
    _parsed = F.parse_datasheet(_block)
    fixture[_parsed["name"]] = _parsed
check("the committed fixture parses into its two invented datasheets",
      sorted(fixture) == ["Test Brute", "Test Mob"], str(sorted(fixture)))
_empty_sheet = {"keywords": "", "faction_keywords": "", "damaged": "",
                "sections": [], "weapons": []}
brute = fixture.get("Test Brute") or _empty_sheet
mob = fixture.get("Test Mob") or _empty_sheet


def _section_of(parsed, title):
    return next((text for t, text in parsed["sections"] if t == title), "")


check("the KEYWORDS bar is read although its class grew a second class",
      brute["keywords"] == "KEYWORDS: VEHICLE; TEST BRUTE", brute["keywords"])
check("...and so is the FACTION KEYWORDS bar beside it",
      brute["faction_keywords"] == "FACTION KEYWORDS: TESTERS", brute["faction_keywords"])
check("...on both blocks", mob["keywords"] == "KEYWORDS: INFANTRY; MOB", mob["keywords"])

_brute_abilities = _section_of(brute, "ABILITIES")
check("a core table after MELEE WEAPONS is not swallowed: CORE and FACTION head ABILITIES",
      _brute_abilities.startswith("CORE: **Damaged 4, Deep Strike**\n\nFACTION: **Test Rally**"),
      _brute_abilities[:60])
check("...and the section's own ability still follows them",
      "**Invented Stomp:**" in _brute_abilities)
_mob_abilities = _section_of(mob, "ABILITIES")
check("a core table after WARGEAR OPTIONS is not glued onto them",
      _mob_abilities.startswith("FACTION: **Test Rally**")
      and "Test Rally" not in _section_of(mob, "WARGEAR OPTIONS"),
      _mob_abilities[:60])
check("moving the lines never duplicates the ABILITIES section",
      [t for t, _ in brute["sections"]].count("ABILITIES") == 1
      and [t for t, _ in mob["sections"]].count("ABILITIES") == 1)

check("the Damaged marker is read", brute["damaged"] == "4", repr(brute["damaged"]))
check("...and agrees with the Damaged X its CORE line prints",
      bool(brute["damaged"]) and ("Damaged %s" % brute["damaged"]) in _brute_abilities)
check("...while a sheet without one reads none", mob["damaged"] == "", repr(mob["damaged"]))

_fixture_rows = {row["name"]: row for table in brute["weapons"] for row in table["rows"]}
check("weapon names lose the new layout's bold markers",
      sorted(_fixture_rows) == ["Test Choppa", "Test Launcha - Hunter", "Test Launcha - Standard"],
      str(sorted(_fixture_rows)))
_hunter = _fixture_rows.get("Test Launcha - Hunter") or {"keywords": []}
_standard = _fixture_rows.get("Test Launcha - Standard") or {"keywords": []}
check("the Hunter row's condition lands on the Hunter profile's keywords",
      _hunter["keywords"] == ["HUNTER: MONSTER/VEHICLE"], str(_hunter["keywords"]))
check("...and not on the Standard profile printed above it",
      "HUNTER: MONSTER/VEHICLE" not in _standard["keywords"], str(_standard["keywords"]))
check("a conditional keyword survives whole, colon and all",
      "LETHAL HITS: non-MONSTER/VEHICLE" in _standard["keywords"], str(_standard["keywords"]))

_brute_md = F.render_markdown(brute, "Testers", "testers") if "name" in brute else ""
check("the rendered file carries the KEYWORDS bar and the CORE line",
      "\nKEYWORDS: VEHICLE; TEST BRUTE\n" in _brute_md
      and "\nCORE: **Damaged 4, Deep Strike**\n" in _brute_md)

# The two labels the table prints are mapped; a third one is a layout change
# nobody has looked at, and dropping it would lose rule text without a sound.
try:
    for _block in F.split_blocks(fixture_html.replace("ARMY RULES", "SOMETHING NEW")):
        F.parse_datasheet(_block)
    _raised = False
except SystemExit:
    _raised = True
check("an unknown core-table row aborts the run instead of being dropped", _raised)
check("...while a body with no core table (the old layout) passes through untouched",
      F.extract_core_army("<div>old layout</div>") == ("<div>old layout</div>", [], None))

# -- the refetched Ork corpus ------------------------------------------------
_ork_files = sorted(p for p in glob.glob(os.path.join("rules", "orks", "*.md"))
                    if os.path.basename(p) != "army_rules.md")
check("the Ork folder holds one file per built Ork datasheet",
      len(_ork_files) == len(orks.ORKS.datasheets) and len(_ork_files) > 10,
      "%d files, %d built" % (len(_ork_files), len(orks.ORKS.datasheets)))
_bars_missing = []
for _path in _ork_files:
    _text = corpus_text_path(_path)
    if (len(re.findall(r"^KEYWORDS: ", _text, re.M)) != 1
            or not re.search(r"^FACTION KEYWORDS: ORKS$", _text, re.M)
            or not re.search(r"^FACTION: \*\*.*Waaagh!.*\*\*$", _text, re.M)):
        _bars_missing.append(os.path.basename(_path))
check("every Ork sheet carries its KEYWORDS bar and its FACTION line",
      not _bars_missing, str(_bars_missing))

_beastboss = corpus_text("orks", "Beastboss")
check("Beastboss (table swallowed by MELEE WEAPONS) keeps CORE and FACTION in its abilities",
      md_section(_beastboss, "Abilities").startswith(
          "CORE: **Feel No Pain 6+, Leader**\n\nFACTION: **Da Boss, Waaagh!**"))
_warboss = corpus_text("orks", "Warboss")
check("Warboss (table glued onto WARGEAR OPTIONS) keeps them in its abilities too",
      md_section(_warboss, "Abilities").startswith(
          "CORE: **Leader**\n\nFACTION: **Da Boss, Waaagh!**")
      and "Da Boss" not in md_section(_warboss, "Wargear Options"))
check("no Ork weapon row keeps the bold name marker",
      not [os.path.basename(p) for p in _ork_files
           if re.search(r"^\| \*\*", corpus_text_path(p), re.M)])
check("Tankbustas' Hunter rows carry their printed condition",
      re.search(r"^\| Busta Rokkit Launcha - Hunter \|.*\| HUNTER: MONSTER/VEHICLE \|$",
                corpus_text("orks", "Tankbustas"), re.M) is not None)

_war_horde = corpus_text_path(os.path.join("rules", "orks", "detachments", "War Horde.md"))
check("War Horde's heading prints BOTH of its Force Dispositions",
      "Force Disposition: Take and Hold; Purge the Foe" in _war_horde)
_withdrawn = ["Equatorial Hordes", "Freebooter Krew", "More Dakka!", "Rollin' Deff",
              "Speedwaaagh!"]
check("the five detachments GW withdrew left no file behind",
      not [n for n in _withdrawn if os.path.exists(os.path.join(
          "rules", "orks", "detachments", "%s.md" % F.safe_filename(n)))])

# A one-faction refresh still rewrites rules/README.md and rebuilds the other
# factions' rows from the files on disk. Run through the real writer, those
# rows must reproduce the committed README - otherwise `--faction orks`
# quietly drops or reorders the other four.
import shutil  # noqa: E402
import tempfile  # noqa: E402

_index_rows, _detachment_rows = [], []
for _folder, _slug, _faction in F.FACTIONS:
    _index_row, _detachment_row = F._index_rows_from_disk(_folder, _faction)
    if _index_row:
        _index_rows.append(_index_row)
    if _detachment_row:
        _detachment_rows.append(_detachment_row)
_saved_out_dir = F.OUT_DIR
_tmp_dir = tempfile.mkdtemp()
try:
    F.OUT_DIR = _tmp_dir
    F.write_index(_index_rows, _detachment_rows)
    _rebuilt_readme = io.open(os.path.join(_tmp_dir, "README.md"), encoding="utf-8").read()
finally:
    F.OUT_DIR = _saved_out_dir
    shutil.rmtree(_tmp_dir, ignore_errors=True)


def _undated(text):
    return [line for line in text.splitlines() if not line.startswith("Last fetched:")]


check("every faction's README rows rebuild from disk",
      len(_index_rows) == len(F.FACTIONS) and len(_detachment_rows) == len(F.FACTIONS),
      "%d / %d" % (len(_index_rows), len(_detachment_rows)))
_committed_readme = corpus_text_path(os.path.join("rules", "README.md"))
check("...and reproduce the committed rules/README.md line for line, date aside",
      bool(_committed_readme) and _undated(_rebuilt_readme) == _undated(_committed_readme))

# -- source guards -----------------------------------------------------------
check("--faction is a flag, and a folder that does not exist is an error",
      'add_argument("--faction"' in src and "--faction named no known faction folder" in src)
check("a one-faction run takes the other factions' rows from disk",
      "_index_rows_from_disk(folder, faction)" in src)
_write_rules_src = src.split("def _write_faction_rules")[-1].split("\ndef ")[0]
_guard_at = _write_rules_src.find("if not only_detachments:", _write_rules_src.find("names.append"))
check("a withdrawn detachment's file is removed only on a full faction pass",
      _guard_at != -1 and "no longer on the page" in _write_rules_src
      and _guard_at < _write_rules_src.find("os.remove("))

print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print("  -", f)
    raise SystemExit(1)
