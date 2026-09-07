"""game/rules_text.py: the PRINTED rules text, read back out of the corpus.

User: "und zeige bitte die original regeltexte an. keine selbst generierten
varianten."

The load-bearing assertion here is section 4: every ability this module hands
to the UI must appear VERBATIM in the .md it came from. Anything less and the
module could be silently paraphrasing, which is the one thing it exists not to
do - and a test that merely checked "some text came back" would pass while it
did.

Two derivations (which folder a faction writes to, how a datasheet name becomes
a file name) are duplicated from fetch_datasheet_rules.py on purpose - that
script is a CLI tool that imports urllib at module scope, so importing it from
the render path is the wrong dependency direction. Section 2 pins them AGAINST
it, so there is still one answer and drift is caught rather than silent.
"""

import io
import os
import re

import testkit as tk

import fetch_datasheet_rules as fetch
from game import rules_text as rt
from game.factions import aeldari, death_guard, necrons, orks, tau_empire

checks = tk.Checks("Printed rules text")

FACTIONS = [aeldari.AELDARI, orks.ORKS, necrons.NECRONS,
            tau_empire.TAU_EMPIRE, death_guard.DEATH_GUARD]


# --- 1. every built datasheet resolves to a corpus file ---------------------
print("--- 1. resolution ---")

missing, total = [], 0
for faction in FACTIONS:
    for name, datasheet in faction.datasheets.items():
        total += 1
        path = rt.rules_path(datasheet)
        if not path or not os.path.exists(path):
            missing.append(f"{faction.name}/{name}")

checks.eq("all five factions are built", len(FACTIONS), 5)
checks.true("and between them field a real number of datasheets", total >= 130)
# No alias table: plain normalisation matches every one. If a future datasheet
# name and its Wahapedia file name disagree, this is where it shows up - as a
# named unit, not as a card that silently shows no abilities.
checks.eq("every built datasheet resolves to a corpus file", missing, [])


# --- 2. the two derivations agree with the fetch script ---------------------
print("--- 2. pinned against fetch_datasheet_rules.py ---")

for folder, _slug, faction in fetch.FACTIONS:
    checks.eq(f"{faction.name} writes to and is read from the same folder",
              rt.rules_folder(faction), folder)

for name in ["Dire Avengers", "Ta'unar Supremacy Armour", "Commander Shadowsun",
             "Kroot Lone-Spear", "Nurgle's Rot"]:
    checks.eq(f"same file name for {name!r}",
              rt.safe_filename(name), fetch.safe_filename(name))

checks.eq("and the corpus root is the same directory",
          os.path.normpath(rt.RULES_DIR), os.path.normpath(fetch.OUT_DIR))

# A caller holding only a faction KEYWORD must land in the same folder as one
# holding the Faction object. This used to go through faction.get_faction(),
# which only answers after that faction's module has been imported - and
# nothing imports the five eagerly, so an army-rules lookup from a fresh
# process silently returned nothing at all.
for faction in FACTIONS:
    checks.eq(f"{faction.name}: keyword and name fold to the same folder",
              rt.folder_for_keyword(faction.keyword), rt.rules_folder(faction))
checks.true("...and that folder exists",
            all(os.path.isdir(os.path.join(rt.RULES_DIR, rt.folder_for_keyword(f.keyword)))
                for f in FACTIONS))


# --- 3. the three printed shapes are parsed apart --------------------------
print("--- 3. the printed shapes ---")

avengers = rt.abilities_for(aeldari.AELDARI.datasheets["Dire Avengers"])
by_title = {a.title: a for a in avengers if a.title}
by_label = {a.label: a for a in avengers if a.label}

checks.true("a FACTION: row is read as a label", "FACTION" in by_label)
checks.eq("...carrying its value", by_label["FACTION"].body, "Battle Focus")
checks.true("a **Named:** paragraph is read as a title", "Bladestorm" in by_title)
checks.eq(
    "...with the printed wording, not a paraphrase",
    by_title["Bladestorm"].body,
    "Ranged weapons equipped by models in this unit have the [SUSTAINED HITS 1] "
    "ability while targeting an enemy unit within half range.",
)
checks.true("Wargear Abilities are included too",
            any(a.section == "Wargear Abilities" for a in avengers))
checks.true("...such as the Shimmershield", "Shimmershield" in by_title)

wagon = rt.abilities_for(orks.ORKS.datasheets["Battlewagon"])
sections = {a.section for a in wagon}
checks.true("a CORE: row is read as a label",
            any(a.label == "CORE" for a in wagon))
# Damaged is a rule that fires off the model's CURRENT wounds - which is
# exactly what a player is hovering the card to find out.
checks.true("the Damaged bracket is included",
            any(s.startswith("Damaged:") for s in sections))
checks.true("and the Transport line", "Transport" in sections)
damaged = next(a for a in wagon if a.section.startswith("Damaged:"))
checks.eq("a Damaged paragraph has no printed name, so neither has the entry",
          (damaged.label, damaged.title), (None, None))

# Coverage: no built datasheet comes back empty. A silent [] is precisely how
# this feature would fail in the field - the card just would not show a rule.
empty = []
parsed = 0
for faction in FACTIONS:
    for name, datasheet in faction.datasheets.items():
        abilities = rt.abilities_for(datasheet)
        parsed += len(abilities)
        if not abilities:
            empty.append(f"{faction.name}/{name}")
checks.eq("no built datasheet parses to zero abilities", empty, [])
checks.true("and the corpus yields hundreds of them", parsed >= 500)


# --- 4. VERBATIM: every word came out of the file ---------------------------
print("--- 4. verbatim ---")


def _folded_source(path):
    """The file as the parser sees it: emphasis markers gone, typographic
    glyphs folded, whitespace collapsed. Anything the module returns has to be
    a substring of this - that is what 'verbatim' means here."""
    raw = io.open(path, encoding="utf-8").read()
    raw = re.sub(r"\*\*(.+?)\*\*", r"\1", raw)
    for bad, good in rt._GLYPH_FOLDS.items():
        raw = raw.replace(bad, good)
    return " ".join(raw.split())


bad = []
checked = 0
for faction in FACTIONS:
    for name, datasheet in faction.datasheets.items():
        source = _folded_source(rt.rules_path(datasheet))
        for ability in rt.abilities_for(datasheet):
            for piece in [ability.body] + list(ability.bullets):
                if not piece:
                    continue
                checked += 1
                if " ".join(piece.split()) not in source:
                    bad.append(f"{name}: {piece[:60]}")
checks.true("this actually inspected the whole corpus", checked >= 500)
checks.eq("every ability body appears verbatim in its own .md", bad[:5], [])

# The counter-check, and the real point of the change: the DEVELOPER note this
# replaced is a paraphrase that ends in a source-file pointer. If any of that
# ever reached a player, this is the line that says so.
leaked = [f"{n}: {a.body[:50]}"
          for f in FACTIONS for n, d in f.datasheets.items()
          for a in rt.abilities_for(d)
          if "see game/" in a.body or ".py" in a.body]
checks.eq("no engine-implementation note leaks into the printed text", leaked, [])

# And that is not a claim about the corpus being clean - it is a difference
# between the two sources. abilities_text really does carry those pointers.
paraphrased = [t for t in aeldari.AELDARI.datasheets["Dire Avengers"].abilities_text
               if "see game/" in t or ".py" in t]
checks.true("...while Datasheet.abilities_text, the field NOT used here, does",
            len(paraphrased) > 0)


# --- 5. it degrades instead of raising -------------------------------------
print("--- 5. degradation ---")


class _Stub:
    def __init__(self, name, faction=None):
        self.name = name
        self.faction = faction


class _StubFaction:
    def __init__(self, name):
        self.name = name


# All four run on the RENDER PATH, where an exception is a crashed frame.
checks.eq("no datasheet at all", rt.abilities_for(None), [])
checks.eq("a hand-built datasheet with no faction",
          rt.abilities_for(_Stub("Whatever")), [])
checks.eq("a faction with no corpus folder",
          rt.abilities_for(_Stub("Whatever", _StubFaction("Made Up"))), [])
checks.eq("a datasheet the corpus has never seen",
          rt.abilities_for(_Stub("No Such Unit", _StubFaction("Aeldari"))), [])
# Not a security boundary (datasheet names are ours), but the reason the file
# name is built rather than concatenated: no separator survives, so a name can
# only ever address a file inside its own faction folder.
checks.eq("no path separator survives into a file name",
          rt.safe_filename('../../etc/pa*ss"wd'), "..-..-etc-pa-ss-wd")


# --- 6. glyphs a SysFont can actually draw ---------------------------------
print("--- 6. glyphs ---")

# Wahapedia sets curly quotes and en dashes; pygame's default SysFont renders
# them as tofu. Folded, never dropped - the printed text is the point, so this
# is the smallest edit that keeps it legible, and no word changes.
tofu = []
for faction in FACTIONS:
    for name, datasheet in faction.datasheets.items():
        for ability in rt.abilities_for(datasheet):
            for ch in ability.body + (ability.title or "") + (ability.label or ""):
                if ch in rt._GLYPH_FOLDS:
                    tofu.append(f"{name}: {ch!r}")
checks.eq("no unfolded typographic glyph survives into the card", tofu[:5], [])
checks.true("and the fold really fires - the corpus is full of them",
            "’" in io.open(rt.rules_path(orks.ORKS.datasheets["Battlewagon"]),
                           encoding="utf-8").read())
ard = next(a for a in rt.abilities_for(orks.ORKS.datasheets["Battlewagon"])
           if a.title and "Ard Case" in a.title)
checks.true("...so 'Ard Case reads with a straight apostrophe",
            "'" in ard.title and "’" not in ard.title)


# --- 7. army rules and detachment rules ------------------------------------
print("--- 7. army and detachment rules ---")

# User: "es fehlt noch ein ort, wo man armeeregel und detachment regeln
# anschauen kann." Same corpus, two more section shapes.
from game import army_lists  # noqa: E402

empty_rules, empty_detachments = [], []
for entry in army_lists.ARMY_LISTS:
    paragraphs = rt.army_rule_text(entry.faction_keyword, entry.army_rule)
    if not paragraphs:
        empty_rules.append(f"{entry.name}/{entry.army_rule}")
    for detachment in entry.detachments:
        name, body = rt.detachment_rule_text(entry.faction_keyword, detachment)
        if not body or not name:
            empty_detachments.append(f"{entry.name}/{detachment}")

checks.true("there are eight lists to check", len(army_lists.ARMY_LISTS) == 8)
# Every one of them, because a missing rule shows as an empty panel rather
# than as an error - the exact silent failure this module degrades into.
checks.eq("every shipped list's army rule resolves", empty_rules, [])
checks.eq("...and so does every one of their detachment rules", empty_detachments, [])

# The two name disagreements this needs a fold for, both measured on the
# shipped data: a lowercase "the" on the page, and a "(Aura)" suffix the list
# does not declare. Named individually so a future exact match cannot quietly
# turn the fold into dead code.
checks.true("a case-only difference still matches (For The/the Greater Good)",
            bool(rt.army_rule_text("T'AU EMPIRE", "For The Greater Good")))
checks.true("...and so does a suffixed heading (Nurgle's Gift (Aura))",
            bool(rt.army_rule_text("DEATH GUARD", "Nurgle's Gift")))

# The detachment RULE has its own name, which is not the detachment's.
_name, _body = rt.detachment_rule_text("AELDARI", "Seer Council")
checks.eq("a detachment rule carries its own printed name", _name, "Strands of Fate")
checks.true("...and its text", any("Fate dice" in p for p in _body))
# Only the "## Detachment rule" section: the file also holds the detachment's
# Stratagems and Enhancements, which are pages of text and belong on a screen
# of their own. Checked by a name that appears ONLY in those sections - the
# rule's own text does mention Stratagems and CP, so searching for those words
# would fail against correct output.
checks.true("Lucid Eye really is an Enhancement in that file",
            "Lucid Eye" in io.open(
                os.path.join(rt.RULES_DIR, "aeldari", "detachments", "Seer Council.md"),
                encoding="utf-8").read())
checks.eq("...but the reader does not pick up the Enhancements section",
          [p for p in _body if "Lucid Eye" in p], [])

# The army_rules.md of a faction can hold SEVERAL top-level rules, so the
# lookup is BY NAME. Aeldari is the case: Battle Focus and Disparate Paths.
_battle_focus = rt.army_rule_text("AELDARI", "Battle Focus")
_disparate = rt.army_rule_text("AELDARI", "Disparate Paths")
checks.true("both of a faction's army rules are readable",
            bool(_battle_focus) and bool(_disparate))
checks.true("...and they are different texts", _battle_focus != _disparate)
# Errata/FAQ blocks live in the same file and must not be picked up as a rule.
checks.true("an army rule's text is not the Errata block",
            not any("Q:" in p for p in _battle_focus))

# Verbatim again, for this second family of sections - the same load-bearing
# claim as section 4. Table rows are excluded because they are the ONE place a
# character is inserted (see below); everything else must be a substring of
# its own file.
_folded = _folded_source(os.path.join(rt.RULES_DIR, "aeldari", "army_rules.md"))
_lost = []
for _p in _battle_focus:
    if not _p:
        continue
    _flat = " ".join(_p.split())
    if _flat in _folded or _flat.replace(" ", "") in _folded.replace(" ", ""):
        continue
    _lost.append(_flat[:60])
checks.true("army rule paragraphs come out of the file", len(_battle_focus) > 10)
checks.eq("...and every one of them verbatim", _lost, [])

# The one rendering decision: a flattened Wahapedia TABLE ROW gets its cells
# separated. "Incursion**2**" is a label and a value run together by the
# scraper; stripping the markers alone shows "Incursion2".
checks.true("a flattened table row is split at its own marker",
            any(p == "Incursion 2" for p in _battle_focus))
checks.eq("...and no word changes doing it",
          rt._split_table_row("Strike Force**4**"), "Strike Force 4")
# Narrow on purpose: inline bold inside prose must be left alone, or a comma
# after a bolded phrase ends up with a space before it.
checks.eq("inline bold in prose is not touched",
          rt._split_table_row("makes a **Normal** move, then stops."),
          "makes a **Normal** move, then stops.")
checks.true("...so no rule paragraph has a space before its punctuation",
            not any(" ," in p or " ." in p for p in _battle_focus))

# Degradation, again on the render path.
checks.eq("an unknown faction keyword", rt.army_rule_text("NO SUCH", "Whatever"), [])
checks.eq("an unknown army rule", rt.army_rule_text("AELDARI", "No Such Rule"), [])
checks.eq("an unknown detachment",
          rt.detachment_rule_text("AELDARI", "No Such Detachment"), (None, []))


checks.finish()
