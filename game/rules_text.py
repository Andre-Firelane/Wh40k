"""Reads the PRINTED rules text out of the `rules/` corpus at runtime.

User: "und zeige bitte die original regeltexte an. keine selbst generierten
varianten."

`Datasheet.abilities_text` cannot answer that. It is a DEVELOPER note - its
own scaffold docstring says it exists "purely for reference/display" - and its
fidelity varies per faction by design: Orks and T'au are near-verbatim, but
Aeldari and Death Guard are paraphrase plus a `see game/...` pointer:

    'Bladestorm: ranged weapons equipped by models in this unit have
     [SUSTAINED HITS 1] while targeting an enemy unit within half range -
     see game/bladestorm.py.'

Putting that in front of a player is showing them a note I wrote about the
rule, not the rule. The verbatim text has been on disk since the corpus was
built (`fetch_datasheet_rules.py` -> `rules/<folder>/<Datasheet>.md`), and
until now NOTHING read it back - the corpus was a git-diff artifact only.
This module is that reader.

Two things are derived here rather than imported from
fetch_datasheet_rules.py: which folder a faction writes to, and how a
datasheet name becomes a file name. That script is a command-line tool which
pulls in urllib at import time, so importing it from the render path is the
wrong dependency direction. Instead both derivations are pinned AGAINST it in
test_rules_text.py - so there is still exactly one answer, and a change to
either side is caught rather than silently drifting.

Measured: all 130 built datasheets across the five factions resolve to a file
this way, with no alias table.
"""

import os
import unicodedata
import re

RULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules")

# The ability-bearing sections of a datasheet .md, in the order a real
# datasheet prints them. Everything else in the file is already on the card by
# other means (Profile -> the stat table, Ranged/Melee Weapons -> the weapon
# tables, Led By/Leader -> the attached-unit lines) or is army-building
# information a player does not need mid-battle (Points, Unit Composition,
# Wargear Options).
#
# "Damaged: ..." is matched by PREFIX because the threshold is part of the
# heading and differs per datasheet ("Damaged: 1-4 Wounds Remaining" through
# "1-20"), and it belongs here because it is a rule that fires from the
# model's CURRENT wounds - which is exactly what the player is hovering to
# find out.
ABILITY_SECTIONS = ("Abilities", "Wargear Abilities", "Transport")
ABILITY_SECTION_PREFIXES = ("Damaged:",)

# Typographic characters Wahapedia uses that pygame's default SysFont renders
# as tofu. Folded rather than dropped: the printed text is the point, so a
# curly apostrophe becoming a straight one is the smallest edit that keeps it
# readable. NOT a paraphrase - no word changes.
_GLYPH_FOLDS = {
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", " ": " ",
}

_cache = {}


class Ability:
    """One printed ability paragraph.

    `label` is the leading all-caps tag of a "CORE: **Deep Strike, Leader**"
    row; `title` is the bolded name of a "**Bladestorm:** ..." paragraph.
    Exactly one of them is set, or neither for a bare paragraph (the Damaged
    and Transport sections print no name). Keeping them apart is what lets the
    card draw a datasheet's own visual hierarchy instead of one grey blob -
    which is the readability half of the same request."""

    def __init__(self, section, label=None, title=None, body="", bullets=()):
        self.section = section
        self.label = label
        self.title = title
        self.body = body
        self.bullets = list(bullets)

    def __repr__(self):
        return f"<Ability {self.section}: {self.label or self.title or self.body[:30]!r}>"


def _fold_folder(text):
    """The one folding rule for a `rules/` subfolder name: lowercase, drop
    apostrophes, everything else to underscores."""
    text = (text or "").lower().replace("’", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def rules_folder(faction):
    """`rules/` subfolder for a Faction - mirrors game/factions/<name>.py, so
    "T'au Empire" does not put a curly apostrophe in a directory name."""
    return _fold_folder(getattr(faction, "name", ""))


def folder_for_keyword(faction_keyword):
    """The same folder, from the faction KEYWORD ("T'AU EMPIRE") instead of a
    Faction object.

    Deliberately not a registry lookup. `faction.get_faction()` only answers
    once that faction's module has been imported - registration happens at
    import time and nothing imports the five eagerly - so a caller holding
    only a keyword got a silent [] rather than the rules. Silent-empty is the
    exact failure this module's docstring warns about, and the keyword already
    carries everything the folder needs.

    Same folding rule as rules_folder(), not a second one: test_rules_text.py
    pins that both inputs give the same folder for every built faction, so a
    future faction whose name and keyword disagree is caught rather than
    quietly losing its rules."""
    return _fold_folder(faction_keyword)


def safe_filename(name):
    """A datasheet name as a file name - same rule fetch_datasheet_rules.py
    writes with (only characters Windows forbids, and the curly apostrophe
    folded so one datasheet cannot produce two files)."""
    name = name.replace("’", "'")
    return re.sub(r'[\\/:*?"<>|]', "-", name).strip()


def rules_path(datasheet):
    """Where this datasheet's printed rules live, or None if it has no faction
    (a hand-built test Datasheet) - never raises, because this is the render
    path and a missing file must degrade to "no abilities shown"."""
    if datasheet is None:
        return None
    faction = getattr(datasheet, "faction", None)
    folder = rules_folder(faction)
    if not folder:
        return None
    return os.path.join(RULES_DIR, folder, safe_filename(datasheet.name) + ".md")


def _fold(text):
    for bad, good in _GLYPH_FOLDS.items():
        text = text.replace(bad, good)
    return text


def _strip_markdown(text):
    """Emphasis markers out, text untouched.

    The corpus bolds inline terms ("this unit's **Reanimation Protocols**
    activate"), which would otherwise render as literal asterisks. Only the
    markers go; not one word changes."""
    return _fold(re.sub(r"\*\*(.+?)\*\*", r"\1", text)).strip()


def _sections(path):
    """[(heading, body)] for every "## " section of a corpus file."""
    out, heading, buf = [], None, []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith("## "):
                if heading is not None:
                    out.append((heading, "\n".join(buf).strip()))
                heading, buf = line[3:].strip(), []
            elif heading is not None:
                buf.append(line)
    if heading is not None:
        out.append((heading, "\n".join(buf).strip()))
    return out


def _wanted(heading):
    return heading in ABILITY_SECTIONS or heading.startswith(ABILITY_SECTION_PREFIXES)


def _parse_paragraph(section, paragraph):
    """One blank-line-separated block of a section into an Ability.

    Three printed shapes, measured over the whole corpus (261 / 320 / 56):
      "CORE: **Deep Strike, Leader**"    -> a label row
      "**Bladestorm:** Ranged weapons..." -> a named ability
      bare prose                          -> Damaged/Transport, which print no name
    """
    lines = [ln.strip() for ln in paragraph.split("\n") if ln.strip()]
    if not lines:
        return None
    # A markdown bullet list is its own shape - joining it onto one line would
    # run "- [IGNORES COVER] - [PRECISION]" together as a sentence.
    bullets = [_strip_markdown(ln[2:]) for ln in lines if ln.startswith("- ")]
    head = " ".join(ln for ln in lines if not ln.startswith("- "))
    head = " ".join(head.split())

    match = re.match(r"^([A-Z][A-Z' /-]*):\s*\*\*(.+?)\*\*$", head)
    if match:
        return Ability(section, label=match.group(1), body=_strip_markdown(match.group(2)))
    match = re.match(r"^\*\*(.+?):?\*\*[:\s]\s*(.*)$", head)
    if match:
        return Ability(section, title=_strip_markdown(match.group(1)),
                       body=_strip_markdown(match.group(2)), bullets=bullets)
    return Ability(section, body=_strip_markdown(head), bullets=bullets)


def _normalise(text):
    """Fold a rule/detachment name to a comparison key - the same three
    disagreements fetch_datasheet_rules.normalise_name() folds: curly vs
    straight apostrophe, capitalisation, punctuation."""
    text = unicodedata.normalize("NFKD", text or "").replace("’", "'")
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _section_named(path, name):
    """The body of the "## <name>" section of a corpus file, or None.

    Matched on the FOLDED name, then on a folded PREFIX. Both are needed, and
    both are measured over the five shipped lists rather than guessed:
    "For The Greater Good" is written with a lowercase "the" on the page, and
    Death Guard's army rule is declared as "Nurgle's Gift" while the page
    prints "Nurgle's Gift (Aura)". A prefix match is safe here because these
    files hold a handful of top-level sections, not hundreds."""
    if not path or not os.path.exists(path):
        return None
    wanted = _normalise(name)
    if not wanted:
        return None
    found = _sections(path)
    for heading, body in found:
        if _normalise(heading) == wanted:
            return body
    for heading, body in found:
        if _normalise(heading).startswith(wanted):
            return body
    return None




def ability_blocks(datasheet, name):
    """ONE named printed ability of a datasheet, as classified RuleLines.

    The structured sibling of abilities_for()'s flat `Ability` record - the
    same "one parser, two views" split army_rule_text()/army_rule_blocks()
    already make. The card wants a title and a sentence; a panel that TYPESETS
    the rule wants the corpus lines, with their labels and bold runs intact.

    Matched on the FOLDED name (_normalise), so "Nurgle's Gift" finds
    "Nurgle’s Gift" and case never matters.

    [] for anything unresolvable, like every other reader here: this runs from
    the render path, where "no file" has to mean "show nothing"."""
    path = rules_path(datasheet)
    if not path or not name:
        return []
    wanted = _normalise(name)
    if not wanted:
        return []
    try:
        sections = _sections(path)
    except OSError:
        return []
    for heading, body in sections:
        if not _wanted(heading):
            continue
        for paragraph in re.split(r"\n\s*\n", body):
            ability = _parse_paragraph(heading, paragraph)
            if ability is None or not ability.title:
                continue
            if _normalise(ability.title) == wanted:
                return _corpus_lines(paragraph)
    return []


def army_rule_text(faction_keyword, rule_name):
    """The PRINTED text of one army rule, as paragraphs.

    [] for anything unresolvable, for the same reason abilities_for() degrades:
    this feeds a panel, and a missing corpus file must mean "nothing to show"
    rather than a crashed frame.

    Note the army_rules.md of a faction can hold SEVERAL top-level rules - the
    Aeldari file carries Battle Focus (ASURYANI) and Disparate Paths (YNNARI)
    - so the rule is looked up BY NAME rather than "the first section". Errata
    and FAQ blocks live in the same file and are skipped by the same
    mechanism: nobody asks for them by name."""
    folder = folder_for_keyword(faction_keyword)
    if not folder:
        return []
    return _flatten(army_rule_blocks(faction_keyword, rule_name))


def army_rule_blocks(faction_keyword, rule_name):
    """The same printed text as army_rule_text(), but as classified RuleLines.

    THE READER'S SOURCE. army_rule_text() above is the flat projection of this
    - one parser, two views, the shape game/ui/mission_cards.py already uses
    for info_rows()/info_lines(). A second parser here would be two places
    answering "what does this rule say" (error class 10), and the one that
    drifted would be the structured one, because only the flat one is pinned."""
    folder = folder_for_keyword(faction_keyword)
    if not folder:
        return []
    return _corpus_lines(
        _section_named(os.path.join(RULES_DIR, folder, "army_rules.md"), rule_name))


def detachment_rule_text(faction_keyword, detachment_name):
    """(rule name, paragraphs) for one detachment's own rule, or (None, []).

    Only the "## Detachment rule" section: a detachment file also carries its
    Stratagems and Enhancements, and those are pages of text that belong on a
    screen of their own rather than under a "see army rules" link. The rule's
    own name is the "### " heading inside that section, and it is returned
    separately because it is a NAME ("Strands of Fate"), not a paragraph - the
    detachment is called something else."""
    name, lines = detachment_rule_blocks(faction_keyword, detachment_name)
    return name, _flatten(lines)


def detachment_rule_blocks(faction_keyword, detachment_name):
    """(rule name, [RuleLine]) - the structured sibling of
    detachment_rule_text(), which is its flat projection."""
    folder = folder_for_keyword(faction_keyword)
    if not folder:
        return None, []
    path = os.path.join(RULES_DIR, folder, "detachments",
                        safe_filename(detachment_name) + ".md")
    body = _section_named(path, "Detachment rule")
    if body is None:
        return None, []
    lines = body.split("\n")
    name = None
    if lines and lines[0].strip().startswith("### "):
        name = _strip_markdown(lines[0].strip()[4:])
        lines = lines[1:]
    return name, _corpus_lines("\n".join(lines))


#: "### PRESENTIMENT OF DREAD - 1CP" - the printed heading of one Stratagem.
#: The cost is captured separately because it is a FACT about the Stratagem
#: rather than part of its name, and the panel already prints its own cost.
_STRATAGEM_HEADING = re.compile(r"^###\s+(?P<name>.+?)(?:\s*[-–]\s*(?P<cost>\d+\s*CP))?$",
                                re.IGNORECASE)


def rule_heading(name, cost):
    """A printed rule's heading: its name, plus its CP cost where it has one.

    ONE formatter with two readers - RuleStratagem below, and
    game/prompt_rule.py's PromptRule, which carries the same two facts out to
    the board-pick panel so the heading in the left column can say what the
    click costs. Written out at both ends they would drift on the separator,
    and the two would then be visibly different strings for one Stratagem.

    An ability has no cost, so this is its name unchanged - which is why the
    name says "rule" and not "stratagem": the caller with the cost is the
    Stratagem, the shape is every printed rule's."""
    return f"{name} - {cost}" if cost else name


class RuleStratagem:
    """One printed Stratagem of a detachment: its name, its CP cost, and its
    body as classified RuleLines.

    A LIST OF THESE rather than one flat block of lines, because two different
    callers ask two different questions of the same section: the army-rules
    reader wants all of them in printed order, and a button's tooltip wants
    exactly ONE by name. Flattening here would make the second caller re-split
    what this already split (error class 10)."""

    __slots__ = ("name", "cost", "lines")

    def __init__(self, name, cost, lines):
        self.name = name
        self.cost = cost
        self.lines = lines

    @property
    def heading(self):
        return rule_heading(self.name, self.cost)

    def __repr__(self):
        return f"RuleStratagem({self.name!r}, {self.cost!r}, {len(self.lines)} lines)"


def detachment_stratagems(faction_keyword, detachment_name):
    """[RuleStratagem] for one detachment, in printed order ([] if unreadable).

    Reads the "## Stratagems" section a detachment file carries alongside its
    rule. That section was deliberately skipped when the reader was built
    ("those are pages of text that belong on a screen of their own"), and this
    is the screen: user "was noch fehlt sind die Infos zu den detachment
    stratagems. die gehören zum einen in die Army Rules overlays."

    Each Stratagem's own "### " heading opens it, so the split is the corpus's
    own marker rather than a guess about where one ends."""
    folder = folder_for_keyword(faction_keyword)
    if not folder:
        return []
    path = os.path.join(RULES_DIR, folder, "detachments",
                        safe_filename(detachment_name) + ".md")
    body = _section_named(path, "Stratagems")
    if not body:
        return []
    out = []
    name = cost = None
    buffer = []
    for raw in body.split("\n"):
        stripped = raw.strip()
        match = _STRATAGEM_HEADING.match(stripped) if stripped.startswith("### ") else None
        if match:
            if name is not None:
                out.append(RuleStratagem(name, cost, _corpus_lines("\n".join(buffer))))
            name = _strip_markdown(match.group("name"))
            cost = (match.group("cost") or "").replace(" ", "").upper() or None
            buffer = []
            continue
        buffer.append(raw)
    if name is not None:
        out.append(RuleStratagem(name, cost, _corpus_lines("\n".join(buffer))))
    return out


def stratagem_named(faction_keyword, detachments, name):
    """The one Stratagem called `name` across these detachments, or None.

    Matched with the SAME folding the rest of this module uses for names
    (_normalise), because the corpus prints them in capitals ("PRESENTIMENT OF
    DREAD") while the engine spells them as they appear on a button
    ("Presentiment of Dread"). Comparing raw strings would find nothing and
    look exactly like "this Stratagem has no printed text".

    EXACT FIRST, THEN A UNIQUE SUFFIX. The panel shortens some names to fit a
    220px button - "Sudden Storm" for what the corpus prints as "PROTOCOL OF
    THE SUDDEN STORM", "Arro'kon Protocol" for "THE ARRO'KON PROTOCOL". A
    suffix match resolves those, and it is measured rather than hoped: over
    every Stratagem of every shipped list each of those shortened names has
    exactly ONE suffix candidate. An AMBIGUOUS suffix returns None rather than
    guessing - showing the wrong Stratagem's rules is worse than showing none,
    because nothing on screen would say it was the wrong one."""
    if not name:
        return None
    wanted = _normalise(name)
    if not wanted:
        return None
    candidates = [stratagem
                  for detachment in detachments or ()
                  for stratagem in detachment_stratagems(faction_keyword, detachment)]
    for stratagem in candidates:
        if _normalise(stratagem.name) == wanted:
            return stratagem
    suffixed = [s for s in candidates if _normalise(s.name).endswith(wanted)]
    return suffixed[0] if len(suffixed) == 1 else None


# A Wahapedia TABLE ROW, as the scraper flattens it: the cells run together
# with only the bold markers between them ("Incursion**2**", "Strike
# Force**4**"). Stripping the markers alone leaves "Incursion2", which is what
# the army-rules reader was showing.
#
# Deliberately narrow - a whole line that is exactly LABEL + one bold run and
# nothing after it. Prose is full of inline bold ("makes a **Normal** move,")
# and the obvious general rule ("space either side of a bold run") puts a space
# before the comma there. Measured over every army-rules and detachment file:
# 24 rows match, 0 of them prose.
#
# This inserts ONE SPACE at a boundary the corpus itself marks. No word
# changes, which is the standing rule for this module - it is a rendering
# decision about a cell boundary, not a rewrite.
_TABLE_ROW = re.compile(r"^(?P<label>\S.*?\w)\*\*(?P<value>[^*]+)\*\*$")


def _split_table_row(line):
    match = _TABLE_ROW.match(line)
    return f"{match.group('label')} {match.group('value')}" if match else line


#: An ALL-CAPS word (or two) followed by a colon, optionally wrapped in bold:
#: the corpus writes both `TRIGGER: ...` and `**EFFECT:** ...`. Allowing only
#: one of the two forms silently drops the other into prose.
#:
#: >= 2 characters before the colon is what keeps an errata "Q:"/"A:" line out.
#: Measured over all 61 corpus files: 9 distinct labels (EFFECT, WHEN, TARGET,
#: RESTRICTIONS, TRIGGER, RESTRICTION, UNIQUE, SUPPORT, LEADER), 0 false hits.
_LABEL_LINE = re.compile(r"^(?:\*\*)?([A-Z][A-Z' /&-]{1,24}):(?:\*\*)?\s*(.*)$")

#: A whole line in single-asterisk italics: the subtitle every printed
#: Stratagem carries under its name ("*Seer Council - Strategic Ploy
#: Stratagem*"). WHOLE-line only, and that is measured, not cautious: all 283
#: single-asterisk runs in the corpus are exactly this shape, 0 are inline.
#:
#: They all live in "## Stratagems" sections, which nothing read until the
#: Stratagems reader below - so teaching the parser about them cannot move any
#: existing output. Verified by the identity probe (181 sections, unchanged).
_SUBTITLE_LINE = re.compile(r"^\*(?!\*)([^*]+)\*$")
_RUN_SPLIT = re.compile(r"\*\*(.+?)\*\*")


def _runs(text):
    """[(text, bold)] for one corpus line - the markers become STRUCTURE
    instead of being deleted.

    LOSSLESS, and that is the whole point: "".join(t for t, _ in _runs(line))
    is exactly _strip_markdown(line) before its outer .strip(). 48% of the
    corpus's lines carry inline bold ("makes a **Normal** move"), so a reader
    that drops it loses nearly half the emphasis the rules were printed with -
    which is what "es fehlt an ... fett geschriebenen Namen" was about."""
    out = []
    for index, piece in enumerate(_RUN_SPLIT.split(text)):
        if piece:
            out.append((_fold(piece), bool(index % 2)))
    return out


class RuleLine:
    """One printed line of a rules section, classified by the shape the corpus
    itself marks.

    WHY THIS EXISTS: `_paragraphs()` below returns flat strings with every
    marker deleted, so the reader could not tell a heading from a sentence and
    rendered all of it in one font at one spacing. The structure was never
    missing from the corpus - it was being destroyed one layer below the UI.

    `text` reproduces exactly what `_paragraphs()` emits for this line, so the
    flat view stays a projection of this one rather than a second parser
    (error class 10). Every field below is a fact the corpus states; nothing
    here infers a hierarchy the printed text does not carry."""

    __slots__ = ("kind", "runs", "label", "cells", "starts_block", "_appends")

    def __init__(self, kind, runs, label=None, cells=None, starts_block=False,
                 appends=False):
        self.kind = kind
        self.runs = runs
        self.label = label
        self.cells = cells
        self.starts_block = starts_block
        # Whether _flatten() must APPEND this line rather than offer it to the
        # sentence-join. It tracks the ORIGINAL parser's two append-only
        # branches ("### " and "- ") and nothing else, because the flat view
        # has to stay byte-identical - a bare ALL-CAPS heading is a heading to
        # the reader but was ordinary prose to the join, and it has to keep
        # being ordinary prose there.
        self._appends = appends

    @property
    def body(self):
        return "".join(text for text, _bold in self.runs)

    @property
    def text(self):
        """The flat string this line contributes to `_paragraphs()`."""
        if self.kind == "bullet":
            return "- " + self.body.strip()
        if self.kind == "label":
            return f"{self.label}: {self.body}".strip()
        if self.kind == "table":
            return f"{self.cells[0]} {self.cells[1]}"
        if self.kind == "subtitle":
            # The markers stay in the FLAT view and are gone from the runs, and
            # that split is the whole point of having two views: the flat one
            # is defined as "what _paragraphs() has always emitted" and must
            # not move, while the reader draws from the runs and shows the
            # subtitle set in its own style instead of in asterisks.
            return f"*{self.body.strip()}*"
        return self.body.strip()

    def __repr__(self):
        return f"RuleLine({self.kind!r}, {self.text!r})"


def _classify(line, starts_block):
    """One corpus line -> one RuleLine. Detection order matters: a table row is
    also ALL-CAPS-ish, and a label line is also prose."""
    if line.startswith("### "):
        return RuleLine("heading", _runs(line[4:]), starts_block=starts_block,
                        appends=True)
    if line.startswith("- "):
        return RuleLine("bullet", _runs(line[2:]), starts_block=starts_block,
                        appends=True)
    match = _SUBTITLE_LINE.match(line)
    if match:
        return RuleLine("subtitle", _runs(match.group(1)), starts_block=starts_block)
    match = _TABLE_ROW.match(line)
    if match:
        label, value = _fold(match.group("label")), _fold(match.group("value"))
        return RuleLine("table", [(label + " ", False), (value, True)],
                        cells=(label, value), starts_block=starts_block)
    stripped = _strip_markdown(line)
    if stripped.isupper() and len(stripped) > 2 and ":" not in stripped \
            and not stripped.endswith("."):
        # A bare ALL-CAPS line: "AGILE MANOEUVRES", "SWIFT AS THE WIND". These
        # are headings on the printed page; the scrape kept the words and lost
        # the styling. Excluding lines with a colon keeps "UNIQUE: DYNASTY" a
        # label, and excluding a trailing full stop keeps a shouted SENTENCE
        # from becoming a heading.
        return RuleLine("heading", _runs(line), starts_block=starts_block)
    match = _LABEL_LINE.match(line)
    if match:
        return RuleLine("label", _runs(match.group(2)), label=_fold(match.group(1)),
                        starts_block=starts_block)
    return RuleLine("text", _runs(line), starts_block=starts_block)


def _corpus_lines(body):
    """A section body as classified lines, in printed order.

    One RuleLine per corpus LINE, deliberately unjoined - `_flatten()` below
    replays `_paragraphs()`'s sentence-joining for the flat view, but the
    reader wants the lines apart. The Orks' Waaagh! is the case that shows
    why: its flavour text and its actual rule are one newline apart in the
    corpus, and the join runs them into a single 480-character paragraph."""
    if not body:
        return []
    out = []
    for block in re.split(r"\n\s*\n", body):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        # The original parser asked `block.startswith("- ")` of the RAW block,
        # so the flag belongs to the block, not to each line.
        bullets = block.startswith("- ")
        for index, line in enumerate(lines):
            rule_line = _classify(line, starts_block=index == 0)
            rule_line.starts_block = index == 0
            if bullets:
                rule_line._appends = True
            out.append(rule_line)
    return out


def _flatten(lines):
    """RuleLines -> `_paragraphs()`'s exact historical output.

    The join rule is the original one, kept verbatim so this stays a
    projection: a prose line merges into the previous entry only when that
    entry was prose too and this line's own corpus block did not open with a
    bullet. Verified byte-identical against the pre-block parser over all 181
    sections of all 61 corpus files."""
    out = []
    for line in lines:
        if line.starts_block and out:
            out.append("")   # the original emitted this AFTER each block
        if not line._appends and out and not out[-1].startswith("- "):
            # Note there is no `out[-1]` truthiness test, and that is faithful,
            # not an oversight: when out[-1] is the "" separator this REPLACES
            # it, which is why the corpus's blank lines never reached the flat
            # view. The reader does not go through here - it reads
            # starts_block off the lines themselves - so the paragraph
            # structure is recovered there without moving this byte.
            out[-1] = (out[-1] + " " + line.text).strip()
        else:
            out.append(line.text)
    while out and not out[-1]:
        out.pop()
    return out


def _paragraphs(body):
    """A section body as display-ready paragraphs: markdown stripped, glyphs
    folded, blank-line-separated blocks kept apart.

    THE FLAT VIEW of `_corpus_lines()`, not a second parser - the same shape
    `game/ui/mission_cards.py` uses for info_lines()/info_rows(), so the two
    cannot drift apart (error class 10).

    Kept apart rather than joined, because these texts are long enough that a
    single block is unreadable - the same reason the mission cards set their
    printed text as separate paragraphs. Bullet lines keep their marker so a
    printed list still reads as a list."""
    return _flatten(_corpus_lines(body))


def abilities_for(datasheet):
    """Every printed ability of this datasheet, verbatim, in datasheet order.

    [] for anything that cannot be resolved - a hand-built Squad with no
    datasheet, a faction whose corpus folder is missing, a datasheet not yet
    snapshotted. This runs from the render path, so "no file" must mean "show
    no abilities", never an exception mid-frame.

    Cached by path: the parse is cheap but this is called every frame the
    hover card is open, and the files never change while the game runs."""
    path = rules_path(datasheet)
    if not path:
        return []
    if path in _cache:
        return _cache[path]
    abilities = []
    try:
        for heading, body in _sections(path):
            if not _wanted(heading):
                continue
            for paragraph in re.split(r"\n\s*\n", body):
                ability = _parse_paragraph(heading, paragraph)
                if ability is not None and (ability.body or ability.bullets):
                    abilities.append(ability)
    except OSError:
        abilities = []
    _cache[path] = abilities
    return abilities
