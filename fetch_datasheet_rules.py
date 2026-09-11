"""Snapshot the PRINTED rule text from Wahapedia into rules/.

Three kinds of file, all generated, all diffable:

    rules/<faction>/<Datasheet>.md        one per datasheet
    rules/<faction>/army_rules.md         the army rule (+ its errata)
    rules/<faction>/detachments/<Name>.md detachment rule, enhancements,
                                          and that detachment's stratagems


WHY THIS EXISTS
---------------
The only rule text in this repo lives in `Datasheet.abilities_text`, and it is
not equally faithful across the five factions: Orks and T'au are close to
verbatim, Necrons quote verbatim but sometimes lost the ability's heading, and
Aeldari and Death Guard are paraphrase plus a `see game/<module>.py` pointer.
None of that can answer "did Games Workshop change this rule?".

So this script writes ONE markdown file per datasheet holding the printed text
as Wahapedia renders it. Re-run it after a GW update and `git diff` names the
changed lines. That diff IS the product - which is why everything below is
built around producing byte-identical output for unchanged input:

  - No timestamp inside a datasheet file. The fetch date lives only in
    rules/README.md; putting it in each file would rewrite all of them on
    every run and destroy the whole point.
  - What each file DOES carry is Wahapedia's own version string for the
    expansion the datasheet came from ("T'au Empire (11th edition, version
    1.2)"). That moves only on a real update, so it is signal, not noise.
  - Section order, table column order and list order come from the page, not
    from a dict iteration or a set.

WHY A SCRAPER AND NOT WebFetch
------------------------------
Measured, not assumed: WebFetch's summariser REFUSES to reproduce a datasheet
verbatim (copyright filter) and offers a paraphrase instead - which is exactly
the thing that is already useless in abilities_text. Raw HTML plus this parser
has no such opinion.

WHY TEN REQUESTS AND NOT TWO HUNDRED
------------------------------------
`factions/<slug>/datasheets.html` embeds EVERY datasheet of that faction
inline (measured: 62 blocks for T'au, 99 for Aeldari). One request per faction
is the whole datasheet corpus, and it also means a single fetch is a
consistent snapshot rather than 113 pages caught at 113 different moments.

The faction's own index page is a second request per faction, and it is not a
convenience: measured, datasheets.html carries NO army rule at all ("For The
Greater Good" appears zero times on it), and it repeats only the detachments a
given datasheet happens to reference - which left three of T'au's seven with a
truncated stratagem list. The index page carries both in full: 5 army rules
and 56 detachments.

WHY AN HTMLParser AND NOT MORE REGEX
------------------------------------
Two structures on the page are genuinely nested and defeated a regex pass:
a weapon's keyword cell (`<span class="kwbw"><span class="tooltip"><span
class="ttw">rapid</span> <span>fire</span> <span>1</span></span></span>` - a
non-greedy `</span>` cuts "rapid" off from "fire 1"), and Wargear Options,
whose sub-choices are a `<ul>` inside an `<li>`. Both came out wrong before
the switch and are pinned by test_datasheet_rules.py.

USAGE
-----
    python fetch_datasheet_rules.py              # fetch + write everything
    python fetch_datasheet_rules.py --offline    # re-parse the cached HTML
    python fetch_datasheet_rules.py --only "Vespid Stingwings"
    python fetch_datasheet_rules.py --detachment "Kauyon"

The `--only` form is the one to use when ADDING a datasheet: per the standing
instruction, a datasheet that gets built in game/factions/ also gets its
rules/*.md saved alongside it, in the same session. See MISSING_BY_FOLDER below
for the entries that are deliberately snapshotted before they exist in game/.

`--detachment` is the same idea for a detachment. Each flag narrows to its own
kind of file and switches the other off, so neither re-downloads the pages the
other needs.

GUARDS (this repo fails loudly rather than writing half a corpus)
----------------------------------------------------------------
  - every datasheet named by game/factions/*.py must match a Wahapedia block
    (today 84/84, by name normalisation alone - no alias table needed)
  - a faction page that yields implausibly few blocks, or a non-200 response,
    aborts the run instead of truncating the corpus
"""

import argparse
import datetime
import html as html_mod
import os
import re
import sys
import unicodedata
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.factions import aeldari, death_guard, necrons, orks, tau_empire  # noqa: E402

BASE_URL = "https://wahapedia.ru/wh40k11ed/factions/{slug}/datasheets.html"
# The faction's own index page. A SECOND request per faction, and it is not
# optional: measured, `datasheets.html` carries no army rule at all ("For The
# Greater Good" appears zero times on it) and only the detachments a datasheet
# happens to reference, so three of T'au's seven come back with their stratagem
# list truncated. This page carries both in full.
FACTION_URL = "https://wahapedia.ru/wh40k11ed/factions/{slug}/"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "rules")
CACHE_DIR = os.path.join(OUT_DIR, ".cache")

# (output folder, wahapedia slug, the module's Faction object). The output
# folder mirrors game/factions/<name>.py rather than the printed faction name,
# so "T'au Empire" does not put a curly apostrophe in a directory name.
FACTIONS = [
    ("aeldari", "aeldari", aeldari.AELDARI),
    ("orks", "orks", orks.ORKS),
    ("necrons", "necrons", necrons.NECRONS),
    ("tau_empire", "t-au-empire", tau_empire.TAU_EMPIRE),
    ("death_guard", "death-guard", death_guard.DEATH_GUARD),
]

# Wahapedia block count below which we assume the page shape changed or the
# download was truncated. Measured today: 99/88/64/62/71.
MIN_BLOCKS_PER_FACTION = 40

# Same guard for the faction page. Measured today: 7/13/12/15/9 detachments.
MIN_DETACHMENTS_PER_FACTION = 5

# T'au datasheets that are NOT built yet but ARE snapshotted, because these
# files are the transcription source for building them. Everything else in the
# corpus is driven off what game/factions/*.py actually registers.
MISSING_TAU = [
    # Characters
    "Commander Shadowsun", "Darkstrider", "Ethereal", "Firesight Team",
    "Kroot Flesh Shaper", "Kroot Trail Shaper", "Kroot War Shaper",
    "Kroot Lone-Spear", "Commander In Enforcer Battlesuit",
    # Infantry / Beast / Mounted
    "Kroot Farstalkers", "Kroot Hounds", "Vespid Stingwings",
    "Krootox Rampagers", "Krootox Riders",
    # Walker
    "Broadside Battlesuits", "Crisis Fireknife Battlesuits",
    # Vehicle
    "Hammerhead Gunship", "Piranhas", "Sky Ray Gunship",
    # Deliberately out of scope for building (no verticality, and AIRCRAFT /
    # FORTIFICATION / TITANIC are documented no-ops in game/actions.py) but
    # free to snapshot from the same fetch, so a later decision to build them
    # needs no new research.
    "Razorshark Strike Fighter", "Sun Shark Bomber", "AX-1-0 Tiger Shark",
    "Manta", "Tiger Shark", "Stormsurge", "Ta'unar Supremacy Armour",
    "Tidewall Droneport", "Tidewall Gunrig", "Tidewall Shieldline",
]

# The same thing for Aeldari, which is the faction furthest behind its own
# page (27 of 99 built). Measured off rules/.cache/aeldari.html rather than
# eyeballed: Legends is the `sLegendary` class on the datasheet's own frame,
# Forge World is `FW_logo2` in the index, and TITANIC is
# `tooltip_contentTitanic` in the KEYWORD BAR - not the mere word "TITANIC",
# which appears in the rules text of several perfectly ordinary datasheets as
# "excluding TITANIC units" (Stonesinger and the D-cannon Platform both read
# as titanic to a naive substring search and are not).
#
# NO LEGENDS HERE, deliberately: every MISSING_TAU entry is non-Legends, so
# the corpus has never carried a "**Legends:** yes" file, and the 23 Aeldari
# Legends sheets are out of scope by instruction. Keeping them out means the
# one thing this list changes is the count, not the shape of the corpus.
MISSING_AELDARI = [
    # -- build targets --------------------------------------------------
    # Wraith constructs
    "Wraithblades", "Wraithlord",
    # Support weapon platforms - three datasheets, one chassis
    "D-cannon Platform", "Shadow Weaver Platform", "Vibro Cannon Platform",
    # Vehicles
    "Fire Prism", "Night Spinner", "Vypers",
    # Asuryani characters
    "Autarch", "Autarch Wayleaper", "Warlock", "Spiritseer",
    "Farseer Skyrunner", "Maugan Ra",
    # Exodites
    "Dragon Knights", "Clanblade", "Leystalker", "Stonesinger",
    # Anhrathe / Corsairs
    "Corsair Voidreavers", "Corsair Voidscarred", "Corsair Skyreavers",
    "Starfangs", "Kharseth", "Prince Yriel",
    # Ynnari triumvirate
    "Yvraine", "The Visarch", "The Yncarne",
    # -- deliberately out of scope for building, snapshotted anyway ------
    # Same reasoning as the T'au tail above: free to take from the same
    # fetch, so a later decision to build one needs no new research.
    # AIRCRAFT (no verticality), TITANIC (a documented no-op), plus the
    # Harlequin and Ynnari-Drukhari blocks, which are their own wargear
    # vocabularies and were scoped out on purpose.
    "Crimson Hunter", "Hemlock Wraithfighter",
    "Wraithknight", "Wraithknight with Ghostglaive",
    "Troupe", "Troupe Master", "Death Jester", "Shadowseer", "Solitaire",
    "Starweaver", "Voidweaver", "Skyweavers",
    "Ynnari Archon", "Ynnari Succubus", "Ynnari Kabalite Warriors",
    "Ynnari Wyches", "Ynnari Incubi", "Ynnari Reavers", "Ynnari Raider",
    "Ynnari Venom",
]

# The same thing for Necrons, the faction furthest behind its own page once
# Aeldari caught up (15 of 64 built). Measured off rules/.cache/necrons.html
# with the same subtraction the Aeldari list documents above: 64 blocks, minus
# 15 built, minus 12 Legends (`sLegendary`), minus 5 TITANIC
# (`tooltip_contentTitanic` in the KEYWORD BAR), minus the three below that are
# out of scope for building = 31 build targets.
#
# Forge World removes nothing extra here, and that is worth writing down rather
# than leaving as a gap in the arithmetic: `FW_logo2` in the index marks the
# Obelisk, the Tesseract Vault, the Seraptek Heavy Construct and the Tomb
# Citadel Walls, and all four are already Legends or TITANIC.
#
# THE MONOLITH IS THE ONE TITANIC ENTRY, by instruction ("nur der monolith
# sollte als einzige titanische einheit angelegt werden"). It would be the
# FIRST datasheet in this engine to carry that keyword, which turns a family of
# clauses this repo has written out as documented no-ops into live rules - see
# CLAUDE.md. The other five TITANIC sheets stay out entirely, Legends and all.
#
# THE NIGHT SCYTHE IS OUT OF SCOPE, and the measurement that used to argue the
# opposite is kept rather than deleted, because it is still true and the next
# reader will otherwise make it again: its 11th-edition keyword bar really does
# say "VEHICLE; FLY; TRANSPORT" with no AIRCRAFT at all - only the Doom Scythe
# carries the keyword - so on the keyword bar alone it would be an ordinary
# transport. THE DECISION OVERRIDES THE KEYWORD BAR (user, stage 8: "night
# scythe bitte komplett weglassen (weil aircraft)"): the model is a flyer, and
# the standing "no aircraft" instruction is about the model, not about whether
# GW printed the keyword on this particular sheet. It is snapshotted with the
# Doom Scythe below and not built.
MISSING_NECRONS = [
    # -- build targets --------------------------------------------------
    # Crypteks - the SUPPORT-character chassis the Plasmancer/Technomancer
    # already share. The Geomancer sits with the Canopteks instead: it is the
    # only unit the Canoptek Macrocytes can be supported by, and its Vanguard
    # Protocols only grant Scouts while it is attached to one.
    "Chronomancer", "Psychomancer", "Orikan The Diviner",
    # Rank and file
    "Deathmarks", "Flayed Ones", "Cryptothralls", "Tomb Blades",
    # Destroyer Cult
    "Hexmark Destroyer", "Ophydian Destroyers", "Nekrosor Ammentar",
    # Triarch
    "Triarch Praetorians", "Triarch Stalker",
    # Canoptek - one closed sub-faction, plus the Geomancer that supports it
    "Canoptek Scarab Swarms", "Canoptek Spyders", "Canoptek Doomstalker",
    "Canoptek Reanimator", "Canoptek Macrocytes", "Canoptek Tomb Crawlers",
    "Geomancer",
    # The one named character left. It is NOT a Leader - it prints no Leader
    # section at all, unlike the four that stage 8 removed from this list - and
    # it is the largest single sheet here, which is why it sits with the
    # Monolith in the last stage rather than with the characters.
    "The Silent King",
    # The one TITANIC entry
    "Monolith",
    # -- deliberately out of scope for building, snapshotted anyway ------
    # Same reasoning as the two tails above: free to take from the same fetch,
    # so a later decision to build one needs no new research. AIRCRAFT and
    # FORTIFICATION are both documented no-op keywords in game/actions.py, and
    # there is no verticality here. The Night Scythe joins them by decision
    # rather than by keyword - see the note above the list.
    "Doom Scythe", "Night Scythe", "Convergence Of Dominion",
]

# folder -> the not-yet-built names that folder snapshots anyway. Keyed on the
# OUTPUT FOLDER rather than on the Faction object, so adding a third list is a
# dict entry instead of another `elif faction is ...` branch.
MISSING_BY_FOLDER = {
    "tau_empire": MISSING_TAU,
    "aeldari": MISSING_AELDARI,
    "necrons": MISSING_NECRONS,
}

BLOCK_TAGS = {"div", "p", "tr", "table", "h1", "h2", "h3", "h4", "ul", "ol"}

# Interface furniture, badges and PROSE THAT IS NOT RULE TEXT, dropped whole.
#   btnFaqErrataToggle - the errata "Show"/"Hide" control, which sits INSIDE
#     the errata block and so lands mid-sentence in the rendered markdown.
#   EnhUpgrade - an "UPGRADE" badge nested inside an enhancement's NAME span,
#     which glues itself onto the name ("Negation EmittersUPGRADE"). Same kind
#     of glued-on badge as the "2DP" in a detachment's own heading.
#   ShowFluff - the lore paragraph printed above a rule ("In war, as in all
#     things, the Aeldari bring the full might of their intellect..."). User,
#     after reading the army rules in game: "keine hintergrund info texte und
#     example texte in den armeeregeln bitte. nur reine regeltexte."
#     This is WAHAPEDIA'S OWN classification, not a guess about which
#     sentences read like flavour - the site hangs its show/hide-fluff toggle
#     on exactly this class. Measured: it marks the lore above every army
#     rule, every detachment rule and every enhancement, plus a stratagem's
#     own legend; 2796 occurrences across the ten cached pages, and not one
#     of them carries a rule.
#   redExample - the worked example some rules print underneath themselves
#     ("Example: A unit of Lokhust Destroyers (which have a Wounds
#     characteristic of 3)..."). An illustration of the rule, not the rule.
#
# DROPPED AT THE SCRAPE rather than filtered by the reader, and that is the
# choice worth writing down. The corpus exists so `git diff` answers "did GW
# change this rule?" - flavour is pure noise in that diff, and a reader-side
# filter would have to GUESS which paragraphs are flavour, because a marker
# the reader could trust would have to be written here anyway.
SKIP_CLASSES = ("btnFaqErrataToggle", "EnhUpgrade", "ShowFluff", "redExample")

# Stands in for one level of list indentation until the whitespace pass is done.
INDENT = "\x02"


def _tighten_lists(text):
    """Drop the blank line between consecutive bullets.

    Every block tag emits a newline, so a plain <ul> comes out as a "loose"
    markdown list with a blank line between every item. The blank line before a
    list's FIRST item is correct markdown and is kept.
    """
    bullet = re.compile(r"^\s*(?:-|\d+\.) ")
    lines = text.split("\n")
    out = []
    for i, line in enumerate(lines):
        if not line.strip() and out and bullet.match(out[-1]):
            following = next((n for n in lines[i + 1:] if n.strip()), "")
            if bullet.match(following):
                continue
        out.append(line)
    return "\n".join(out)


# --------------------------------------------------------------------------
# HTML -> markdown
# --------------------------------------------------------------------------

class _Renderer(HTMLParser):
    """Render a datasheet fragment as markdown text.

    Deliberately narrow: it only knows the handful of constructs Wahapedia
    actually uses inside a datasheet - nested lists, bold ability names, the
    `dsLineHor` rule that separates two abilities sharing one container, and
    the `kwbw` spans that hold a weapon's keywords. `capture_keywords` pulls
    those keywords OUT of the flowing text into `self.keywords`, which is what
    lets the weapon tables give them their own column instead of gluing them
    onto the weapon's name.
    """

    def __init__(self, capture_keywords=False):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.keywords = []
        self.capture_keywords = capture_keywords
        self._list_depth = 0
        self._kw_depth = 0
        self._span_depth = 0
        self._skip_depth = 0
        self._skip_tag = None
        self._skip_count = 0

    # -- helpers ----------------------------------------------------------
    def _emit(self, text):
        if self._skip_depth or self._skip_tag is not None:
            return
        if self._kw_depth:
            self.keywords.append(text)
        else:
            self.parts.append(text)

    def _newline(self, count=1):
        if self._skip_depth or self._skip_tag is not None:
            return
        self.parts.append("\n" * count)

    # -- tags -------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()

        # Counted by tag name rather than by a flat depth: the skipped element
        # contains further <div>s, so a plain "stop at the next </div>" ends the
        # skip early and leaks the rest of the control into the text.
        if self._skip_tag is not None:
            if tag == self._skip_tag:
                self._skip_count += 1
            return
        if any(name in classes for name in SKIP_CLASSES):
            self._skip_tag = tag
            self._skip_count = 1
            return

        if tag in ("script", "style"):
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        if tag == "span":
            self._span_depth += 1
            if self.capture_keywords and "kwbw" in classes and not self._kw_depth:
                self._kw_depth = self._span_depth
                self.keywords.append("\x00")  # keyword boundary
            return

        if tag == "b" or tag == "strong":
            self._emit("**")
            return
        if tag == "br":
            self._newline()
            return
        if tag == "div" and "dsLineHor" in classes:
            # Two printed abilities sharing one container. Without this they
            # run together into one paragraph and read as a single rule.
            self._newline(2)
            return
        if tag in ("ul", "ol"):
            self._list_depth += 1
            self._newline()
            return
        if tag == "li":
            self._newline()
            # INDENT is a sentinel, not spaces: the whitespace pass in text()
            # strips leading blanks on every line (the raw markup is indented
            # with tabs), which silently flattened Wargear Options' nested
            # sub-choices onto the top level.
            self.parts.append(INDENT * max(0, self._list_depth - 1) + "- ")
            return
        if tag in BLOCK_TAGS:
            self._newline()

    def handle_endtag(self, tag):
        if self._skip_tag is not None:
            if tag == self._skip_tag:
                self._skip_count -= 1
                if self._skip_count <= 0:
                    self._skip_tag = None
            return
        if tag in ("script", "style"):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return

        if tag == "span":
            if self._kw_depth and self._span_depth == self._kw_depth:
                self._kw_depth = 0
            self._span_depth = max(0, self._span_depth - 1)
            return
        if tag == "b" or tag == "strong":
            self._emit("**")
            return
        if tag in ("ul", "ol"):
            self._list_depth = max(0, self._list_depth - 1)
            # A blank line, because prose follows a list often enough (Unit
            # Composition's "This model is equipped with:") that one newline
            # would fold it into the last bullet. Where a bullet follows
            # instead, _tighten_lists takes the blank back out.
            self._newline(2)
            return
        if tag == "li":
            # Deliberately silent: the next <li> opens with its own newline,
            # and emitting one here too puts a blank line between every bullet.
            return
        if tag in BLOCK_TAGS:
            self._newline()

    def handle_data(self, data):
        self._emit(data)

    # -- results ----------------------------------------------------------
    def text(self):
        out = "".join(self.parts)
        out = out.replace("\u00a0", " ")
        out = re.sub(r"[ \t]+", " ", out)
        out = re.sub(r" *\n *", "\n", out)
        out = re.sub(r"\*\* +", "** ", out)
        out = re.sub(r"\n{3,}", "\n\n", out)
        # An empty bold pair is markup noise from an <b> that wrapped only a
        # tooltip span whose text went elsewhere.
        out = out.replace("****", "")
        out = out.replace(INDENT, "  ")
        return _tighten_lists(out.strip())

    def keyword_list(self):
        joined = "".join(self.keywords).replace("\u00a0", " ")
        return [re.sub(r"\s+", " ", k).strip()
                for k in joined.split("\x00") if k.strip()]


def to_markdown(fragment):
    renderer = _Renderer()
    renderer.feed(fragment)
    return renderer.text()


def inline_text(fragment):
    return re.sub(r"\s+", " ", to_markdown(fragment)).strip()


def split_weapon_cell(fragment):
    """A weapon's name cell -> (printed name, [keywords])."""
    renderer = _Renderer(capture_keywords=True)
    renderer.feed(fragment)
    name = re.sub(r"\s+", " ", renderer.text()).strip()
    return name, renderer.keyword_list()


def normalise_name(text):
    """Fold a datasheet name to a comparison key.

    Handles the three ways the engine and Wahapedia disagree in practice:
    curly vs straight apostrophe ("Ta'unar"/"Ta’unar"), capitalisation
    ("Commander in Coldstar" vs "Commander In Coldstar") and punctuation
    ("Kroot Lone-spear" vs "Kroot Lone-Spear"). Measured: this alone matches
    all 84 built datasheets, so there is no alias table to keep in sync.
    """
    text = unicodedata.normalize("NFKD", text).replace("’", "'")
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def md_cell(text):
    return text.replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------
# block parsing
# --------------------------------------------------------------------------

BLOCK_RE = re.compile(
    r'<a id="([^"]+)" name="\1"></a><div class="(dsOuterFrame datasheet[^"]*)"'
)
# Wahapedia's own markup uses a CYRILLIC "С" (U+0421) in these two class
# names. Spelling them with a Latin C silently matches nothing, which is how
# the faction-keywords line went missing on the first pass.
KW_LEFT_RE = re.compile(r'<div class="dsLeft\u0421olKW">(.*?)</div>', re.S)
KW_RIGHT_RE = re.compile(r'<div class="dsRight\u0421olKW">(.*?)</div>', re.S)


def split_blocks(page_html):
    """Cut the faction page into one HTML fragment per datasheet."""
    anchors = list(BLOCK_RE.finditer(page_html))
    blocks = []
    for i, match in enumerate(anchors):
        end = anchors[i + 1].start() if i + 1 < len(anchors) else len(page_html)
        blocks.append({
            "slug": match.group(1),
            "legends": "sLegendary" in match.group(2),
            "html": page_html[match.start():end],
        })
    return blocks


def parse_profiles(block_html):
    """Every statline on the datasheet, in printed order.

    A multi-profile datasheet prints the characteristic NAMES only above the
    first profile; the rest are positional. So the names are captured once and
    reused - reading them per profile would leave later lines without headers.
    """
    profiles = []
    names = []
    for wrap in re.finditer(
        r'<div class="dsProfileBaseWrap">(.*?)(?=<div class="dsProfileBaseWrap">|$)',
        block_html, re.S,
    ):
        chunk = wrap.group(1)
        row_names = re.findall(r'<div class="dsCharName">(.*?)</div>', chunk, re.S)
        if row_names and not names:
            names = [inline_text(n) for n in row_names]
        values = [inline_text(v) for v in
                  re.findall(r'<div class="dsCharValue[^"]*">(.*?)</div>', chunk, re.S)]
        if not values:
            continue
        label = re.search(r'<span class="dsModelName[^"]*">(.*?)</span>', chunk, re.S)
        base = re.search(r'<span class="dsModelBase[^"]*">(.*?)</span>', chunk, re.S)
        invul_label, invul = parse_invulnerable(chunk)
        profiles.append({
            "label": inline_text(label.group(1)) if label else "",
            "base": clean_base(inline_text(base.group(1))) if base else "",
            "values": values,
            "invul": invul,
            "invul_label": invul_label,
        })
    return names, profiles


def clean_base(text):
    return text.strip().lstrip("(").rstrip(")").strip()


def parse_invulnerable(block_html):
    """The invulnerable save, which is NOT part of the characteristics row.

    Wahapedia prints it in its own `dsInvulWrap` box beside the statline, so a
    parser that only reads `dsCharValue` drops it silently - which is how the
    first version of this corpus recorded no invulnerable save for any of the
    204 datasheets that have one. The label is "INSV", or "INSV*" when the save
    is conditional and a datasheet ability spells the condition out.

    It is PER MODEL LINE, not per datasheet: 14 blocks (every Aeldari Aspect
    Warrior squad, where the Exarch's save differs) carry two boxes, each
    following the profile it belongs to. So this is called on one profile's
    chunk, not on the whole block.
    """
    wrap = re.search(r'<div class="dsInvulWrap">(.*?)(?:<div class="ds2col|$)',
                     block_html, re.S)
    if not wrap:
        return "", ""
    chunk = wrap.group(1)
    label = re.search(r'<div class="dsCharInvulText[^"]*">(.*?)</div>', chunk, re.S)
    value = re.search(r'<div class="dsCharInvulValue[^"]*">(.*?)</div>', chunk, re.S)
    if not value:
        return "", ""
    return (inline_text(label.group(1)) if label else "INSV"), inline_text(value.group(1))


def parse_weapon_tables(block_html):
    """The RANGED and MELEE weapon tables.

    Each weapon appears TWICE in the markup: a `wTable2_long` row carrying
    only the name (the narrow-screen rendering) and a `wTable2_short` row
    carrying the name plus the six characteristics. Only the short row is
    read, which also means a multi-profile weapon (a two-mode gun) yields one
    row per mode, exactly as printed.
    """
    tables = []
    header_re = re.compile(
        r'<div class="ds(?:Ranged|Melee)Icon"></div>.*?'
        r'<div class="dsHeader[^"]*">((?:RANGED|MELEE) WEAPONS)</div>',
        re.S,
    )
    headers = list(header_re.finditer(block_html))
    for i, head in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(block_html)
        section = block_html[head.end():end]
        cols = [inline_text(c) for c in
                re.findall(r'<div class="ct dsHeader[^"]*">(.*?)</div>', section, re.S)][:6]
        rows = []
        for row in re.finditer(r"<tr[^>]*>(.*?)</tr>", section, re.S):
            row_html = row.group(1)
            if "wTable2_short" not in row_html:
                continue
            name_cell = re.search(
                r'<td class="wTable2_short[^"]*">(.*?)</td>', row_html, re.S)
            if not name_cell:
                continue
            name, keywords = split_weapon_cell(name_cell.group(1))
            values = [inline_text(v) for v in
                      re.findall(r'<div class="ct pad2626">(.*?)</div>', row_html, re.S)]
            rows.append({"name": name, "keywords": keywords, "values": values[:6]})
        if rows:
            tables.append({"title": head.group(1).title(), "cols": cols, "rows": rows})
    return tables


COST_TABLE_RE = re.compile(r"<table[^>]*>.*?</table>", re.S)


def parse_points(body_html):
    """The "YOUR UNIT COSTS" tables.

    These are not behind a `dsHeader`, so without pulling them out they get
    swallowed by whatever section precedes them (in practice UNIT COMPOSITION)
    and render as an unreadable "1 model50".
    """
    entries = []
    for table in COST_TABLE_RE.finditer(body_html):
        chunk = table.group(0)
        if "dsUnitCostHeader" not in chunk:
            continue
        # A tiered unit puts BOTH tiers in ONE table, as two header rows with
        # their own rows beneath. Reading the header once per table therefore
        # labelled every Boyz row "YOUR 1ST TO 3RD UNITS COST", including the
        # 4th+ prices - so the title is tracked row by row instead.
        title = "COSTS"
        for row in re.finditer(r"<tr[^>]*>(.*?)</tr>", chunk, re.S):
            row_html = row.group(1)
            header = re.search(r'<td[^>]*class="dsUnitCostHeader">(.*?)</td>',
                               row_html, re.S)
            if header:
                title = inline_text(header.group(1))
                continue
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)
            if len(cells) < 2:
                continue
            entries.append((title, inline_text(cells[0]), inline_text(cells[1])))
    return entries


# The optional leading span is a section icon. It is NOT always named
# "...Icon" - the Damaged profile's is <span class="dsSkull2">, and requiring
# the Icon suffix dropped every DAMAGED section into the preceding one. The
# colon in the character class is there for the same heading
# ("DAMAGED: 1-4 WOUNDS REMAINING").
HEADER_RE = re.compile(
    r'<div class="dsHeader dsColorBg[A-Z]+"[^>]*>(?:<span class="ds[A-Za-z0-9]*"></span>)?'
    r"([A-Z][A-Z0-9 :'’&/+-]*[A-Z0-9])</div>"
)

# Handled by dedicated parsers, so they must not be re-emitted as loose text.
SKIP_SECTIONS = {"RANGED WEAPONS", "MELEE WEAPONS"}

# Sections printed BELOW the keywords bar that still belong to the datasheet.
# Surveyed across all 384 blocks, the post-keyword headings are exactly
# STRATAGEMS (384), DETACHMENT ABILITY (381), ENHANCEMENTS (118) - all faction
# furniture repeated on every datasheet - plus these two, which are this
# datasheet's own attachment table. A "LEADER" section on the character sits
# ABOVE the bar; the matching "LED BY" on the bodyguard unit sits below it, so
# dropping everything after the bar loses one half of every pairing.
POST_KEYWORD_SECTIONS = {"LED BY", "SUPPORTED BY"}


def parse_sections(body_html, keep_only=None):
    """Every remaining `dsHeader`-titled section, in printed order.

    Kept generic on purpose: ABILITIES, WARGEAR OPTIONS, UNIT COMPOSITION,
    LEADER, LED BY, SUPPORTED BY, TRANSPORT, DAMAGED and INVULNERABLE SAVE all
    have the same container shape, and a datasheet GW adds next year with a new
    heading comes through rather than being silently dropped.
    """
    sections = []
    heads = list(HEADER_RE.finditer(body_html))
    for i, head in enumerate(heads):
        title = head.group(1).strip()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body_html)
        if title in SKIP_SECTIONS:
            continue
        if keep_only is not None and title not in keep_only:
            continue
        chunk = COST_TABLE_RE.sub(
            lambda m: "" if "dsUnitCostHeader" in m.group(0) else m.group(0),
            body_html[head.end():end])
        text = to_markdown(chunk)
        if text:
            sections.append((title, text))
    return sections


def parse_datasheet(block):
    """Everything one datasheet contributes to its markdown file."""
    block_html = block["html"]

    name_match = re.search(r'<div class="dsH2Header"><div>(.*?)</div>', block_html, re.S)
    name = inline_text(name_match.group(1)) if name_match else block["slug"]

    base_match = re.search(r'<span class="dsModelBase2[^"]*">(.*?)</span>', block_html, re.S)
    base = clean_base(inline_text(base_match.group(1))) if base_match else ""

    version_match = re.search(r'title="([^"]*\(11th edition, version [^"]*)"', block_html)
    version = html_mod.unescape(version_match.group(1)) if version_match else ""

    # The datasheet proper ends at the keywords bar; everything after it is
    # page furniture (the faction's whole stratagem list, detachment ability,
    # enhancements). `ds2colKW` occurs exactly once per block, which makes it
    # an exact cut point - far safer than searching for the word "STRATAGEMS",
    # which also occurs inside printed rule text.
    cut = block_html.find('<div class="ds2colKW')
    body = block_html[:cut] if cut > 0 else block_html

    char_names, profiles = parse_profiles(body)

    keywords = ""
    faction_keywords = ""
    if cut > 0:
        kw_html = block_html[cut:]
        left = KW_LEFT_RE.search(kw_html)
        right = KW_RIGHT_RE.search(kw_html)
        if left:
            keywords = inline_text(left.group(1))
        if right:
            faction_keywords = inline_text(right.group(1))

    errata = []
    for entry in re.finditer(
        r'<div class="faqErrataHead">(.*?)</div>\s*<div class="faqErrataSpoiler[^"]*">(.*?)</div>',
        block_html, re.S,
    ):
        errata.append((inline_text(entry.group(1)), to_markdown(entry.group(2))))

    return {
        "name": name,
        "slug": block["slug"],
        "legends": block["legends"],
        "base": base,
        "version": version,
        "char_names": char_names,
        "profiles": profiles,
        "weapons": parse_weapon_tables(body),
        "points": parse_points(body),
        "sections": (parse_sections(body)
                     + (parse_sections(block_html[cut:], POST_KEYWORD_SECTIONS)
                        if cut > 0 else [])),
        "keywords": keywords,
        "faction_keywords": faction_keywords,
        "errata": errata,
    }


# --------------------------------------------------------------------------
# markdown rendering
# --------------------------------------------------------------------------

def render_markdown(sheet, faction_name, slug):
    out = ["# %s" % sheet["name"], ""]
    out.append("- **Faction:** %s" % faction_name)
    out.append("- **Source:** %s#%s" % (BASE_URL.format(slug=slug), sheet["slug"]))
    if sheet["version"]:
        out.append("- **Wahapedia version:** %s" % sheet["version"])
    out.append("- **Legends:** %s" % ("yes" if sheet["legends"] else "no"))
    if sheet["base"]:
        out.append("- **Base:** %s" % sheet["base"])
    out.append("")

    if sheet["profiles"]:
        out.append("## Profile")
        out.append("")
        names = sheet["char_names"] or ["M", "T", "SV", "W", "LD", "OC"]
        multi = len(sheet["profiles"]) > 1 or bool(sheet["profiles"][0]["label"])
        # The invulnerable save is a column rather than a datasheet-wide note
        # because it genuinely varies per model line (an Aspect Warrior squad
        # and its Exarch print different ones).
        any_invul = any(p["invul"] for p in sheet["profiles"])
        head = ((["Model"] if multi else []) + names
                + (["INSV"] if any_invul else [])
                + (["Base"] if multi else []))
        out.append("| " + " | ".join(head) + " |")
        out.append("| " + " | ".join(["---"] * len(head)) + " |")
        for profile in sheet["profiles"]:
            cells = list(profile["values"])
            if any_invul:
                # A "*" on the printed label marks a conditional save; the
                # condition is spelled out by one of the abilities below.
                star = "*" if profile["invul_label"].endswith("*") else ""
                cells = cells + [(profile["invul"] + star) if profile["invul"] else "-"]
            if multi:
                cells = [profile["label"] or sheet["name"]] + cells + [profile["base"]]
            out.append("| " + " | ".join(md_cell(c) for c in cells) + " |")
        out.append("")

    for table in sheet["weapons"]:
        out.append("## %s" % table["title"])
        out.append("")
        head = ["Weapon"] + table["cols"] + ["Keywords"]
        out.append("| " + " | ".join(head) + " |")
        out.append("| " + " | ".join(["---"] * len(head)) + " |")
        for row in table["rows"]:
            cells = [row["name"]] + row["values"] + [", ".join(row["keywords"])]
            out.append("| " + " | ".join(md_cell(c) for c in cells) + " |")
        out.append("")

    for title, text in sheet["sections"]:
        out.append("## %s" % title.title())
        out.append("")
        out.append(text)
        out.append("")
        if title == "UNIT COMPOSITION" and sheet["points"]:
            out.extend(render_points(sheet["points"]))

    if sheet["points"] and not any(t == "UNIT COMPOSITION" for t, _ in sheet["sections"]):
        out.extend(render_points(sheet["points"]))

    if sheet["keywords"] or sheet["faction_keywords"]:
        out.append("## Keywords")
        out.append("")
        if sheet["keywords"]:
            out.append(sheet["keywords"])
            out.append("")
        if sheet["faction_keywords"]:
            out.append(sheet["faction_keywords"])
            out.append("")

    if sheet["errata"]:
        out.append("## Errata")
        out.append("")
        for head, text in sheet["errata"]:
            out.append("**%s**" % head)
            out.append("")
            out.append(text)
            out.append("")

    body = re.sub(r"\n{3,}", "\n\n", "\n".join(out))
    return body.rstrip() + "\n"


def render_points(entries):
    out = ["## Points", "", "| Unit | Models | Points |", "| --- | --- | --- |"]
    for title, models, cost in entries:
        out.append("| %s | %s | %s |" % (md_cell(title), md_cell(models), md_cell(cost)))
    out.append("")
    return out


def safe_filename(name):
    """A datasheet name as a file name.

    Only characters Windows actually forbids are replaced; the curly
    apostrophe is folded to a straight one so "Ta'unar" and "Ta’unar" cannot
    produce two files for one datasheet.
    """
    name = name.replace("’", "'")
    return re.sub(r'[\\/:*?"<>|]', "-", name).strip()


# --------------------------------------------------------------------------
# faction page: army rules + detachments
# --------------------------------------------------------------------------
#
# The faction index page is a FLAT run of headings, not nested containers, so
# everything below is heading-driven:
#
#   h2 Army Rules            -> h3 For the Greater Good, h3 Errata, ...
#   h2 <Name><N>DP           -> h2 Detachment Rule -> h3 <Rule name>
#                               h2 Enhancements
#                               h2 Stratagems
#
# Three shapes broke a first, more literal pass, and each is handled by name
# below rather than worked around:
#
#   1. Death Guard puts its army rule in a SIBLING h2 ("Nurgle's Gift (Aura)")
#      after the empty "Army Rules" heading, where the other four use h3
#      children. Hence the `in_army` mode rather than "read this body".
#   2. The enhancements heading is not always called "Enhancements": Aeldari's
#      Corsair detachments say "Corsair Enhancements" and Necrons' Pantheon of
#      Woe says "Necrodermal Binding Abilities". So enhancements are detected
#      by their MARKUP (a `ul.EnhancementsPts`), not by the heading's title.
#      Measured: matching titles that merely END in "enhancements" is enough
#      for the Corsair pair but still loses all four of Pantheon of Woe's,
#      which is why the test names that detachment specifically.
#   3. An h3 "Errata" inside a Stratagems section must not end it. That is why
#      chunks() runs to the next heading of the SAME OR HIGHER level instead of
#      to the next heading of any level, which truncated Kauyon to 1 of its 6.
#
# A detachment is closed by its Stratagems section rather than by "some other
# h2 appeared". Both matter: an unknown h2 in the middle must not orphan the
# sections after it (shape 2), while the page's later "Boarding Actions" block
# has an h2 "Stratagems" of its own that must NOT land on the last detachment.

HEADING_RE = re.compile(r"<h([1-4])[^>]*>(.*?)</h\1>", re.S)
# "Kauyon2DP" - the detachment's points cost is glued onto its own heading.
DP_RE = re.compile(r"^(.*?)(\d+)DP$")
# ...and so is its FORCE DISPOSITION, as an icon's tooltip in the same span:
#     <h2 ...>Warhost<span class="dpPts">
#       <img title="Force Disposition: Reconnaissance" ...>3DP</span></h2>
FORCE_DISPOSITION_RE = re.compile(r'title="Force Disposition:\s*([^"]+)"')
RULE_TITLES = ("detachment rule", "detachment rules")
ENHANCEMENT_RE = re.compile(
    r'<ul class="EnhancementsPts">(.*?)</ul>(.*?)(?=<ul class="EnhancementsPts">|\Z)', re.S)
STRATAGEM_RE = re.compile(r'<div class="str11Wrap">(.*?)(?=<div class="str11Wrap">|\Z)', re.S)
# A stratagem's lore line ("str11Legend ShowFluff") is deliberately ABSENT
# here. Every other block of flavour on the page is dropped by SKIP_CLASSES
# above, but this one is lifted out by its own regex, so the class never
# reaches the renderer - it has to be left unread instead. Same rule, one
# more place, because of how this section is parsed.
STRATAGEM_FIELDS = (
    ("name", re.compile(r'class="str11HeadBlock str11Name"[^>]*>(.*?)</div>', re.S)),
    ("cp", re.compile(r'<div class="str11CP">(.*?)</div>', re.S)),
    ("type", re.compile(r'<div class="str11Type[^"]*">(.*?)</div>', re.S)),
    ("text", re.compile(r'<div class="str11Text">(.*?)</div>\s*</div>', re.S)),
)


def page_headings(page_html):
    return [(match.start(), match.end(), int(match.group(1)),
             re.sub(r"\s+", " ", re.sub("<[^>]+>", "", match.group(2))).strip())
            for match in HEADING_RE.finditer(page_html)]


def heading_force_dispositions(page_html):
    """{stripped heading title: Force Disposition} for every heading carrying one.

    A SECOND pass over the RAW heading html, because page_headings() strips the
    tags to build its title and the disposition lives in an <img> tooltip - the
    stripping that turns the heading into "Warhost3DP" is exactly what throws
    it away.

    Read off the HEADING rather than off the page's detachment FILTER list,
    which carries the same fact in a data-det-name attribute: that list spells
    Kauyon with a CYRILLIC o (U+043E), the same trap this file already
    documents for dsLeftColKW's Cyrillic C. The heading spells it in Latin, and
    rules/tau_empire/detachments/ is already named from the heading.
    """
    out = {}
    for match in HEADING_RE.finditer(page_html):
        raw = match.group(2)
        found = FORCE_DISPOSITION_RE.search(raw)
        if not found:
            continue
        title = re.sub(r"\s+", " ", re.sub("<[^>]+>", "", raw)).strip()
        out[title] = found.group(1).strip()
    return out


def chunks(page_html, level):
    """[(title, body_html)] for every heading at `level`.

    A body runs to the next heading of the same or higher level, so a
    subheading inside it stays part of it.
    """
    headings = page_headings(page_html)
    out = []
    for index, (_start, end, this_level, title) in enumerate(headings):
        if this_level != level:
            continue
        stop = len(page_html)
        for next_start, _e, next_level, _t in headings[index + 1:]:
            if next_level <= level:
                stop = next_start
                break
        out.append((title, page_html[end:stop]))
    return out


def parse_enhancements(body_html):
    """[{name, points, text}] from `ul.EnhancementsPts` headers plus the prose
    that follows each one."""
    out = []
    for header, rest in ENHANCEMENT_RE.findall(body_html):
        spans = re.findall(r"<span[^>]*>(.*?)</span>", header, re.S)
        out.append({
            "name": inline_text(spans[0]) if spans else "",
            "points": inline_text(spans[1]) if len(spans) > 1 else "",
            "text": to_markdown(rest),
        })
    return [item for item in out if item["name"]]


def parse_stratagems(body_html):
    """[{name, cp, type, text}] - text holds the WHEN/TARGET/EFFECT."""
    out = []
    for blob in STRATAGEM_RE.findall(body_html):
        entry = {}
        for key, pattern in STRATAGEM_FIELDS:
            match = pattern.search(blob)
            if not match:
                entry[key] = ""
            elif key == "text":
                entry[key] = to_markdown(match.group(1))
            else:
                entry[key] = inline_text(match.group(1))
        if entry["name"]:
            out.append(entry)
    return out


def parse_faction_page(page_html):
    """(army_rules, detachments) off a faction's index page."""
    army_rules = []
    detachments = []
    current = None
    in_army = False
    dispositions = heading_force_dispositions(page_html)
    for title, body in chunks(page_html, 2):
        lowered = title.lower()
        named = DP_RE.match(title)
        if named:
            in_army = False
            current = {
                "name": named.group(1).strip(),
                "dp": int(named.group(2)),
                # Keyed on the SAME stripped title chunks() produced, so the
                # two passes cannot disagree about which heading is which.
                "force_disposition": dispositions.get(title, ""),
                "rule": [],
                "enhancements": [],
                "stratagems": [],
            }
            detachments.append(current)
        elif lowered == "army rules":
            in_army = True
            current = None
            army_rules.extend((t, to_markdown(b)) for t, b in chunks(body, 3))
        elif current is not None and lowered.startswith(RULE_TITLES):
            current["rule"] = [(t, to_markdown(b)) for t, b in chunks(body, 3)]
        elif current is not None and "EnhancementsPts" in body:
            current["enhancements"] += parse_enhancements(body)
        elif current is not None and lowered == "stratagems":
            current["stratagems"] = parse_stratagems(body)
            current = None
        elif in_army:
            army_rules.append((title, to_markdown(body)))
            army_rules.extend((t, to_markdown(b)) for t, b in chunks(body, 3))
    return army_rules, detachments


def render_army_rules(faction_name, slug, army_rules):
    out = ["# %s - army rules" % faction_name, ""]
    out.append("Source: <%s>" % FACTION_URL.format(slug=slug))
    out.append("")
    for title, text in army_rules:
        out.append("## %s" % title)
        out.append("")
        if text:
            out.append(text)
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_detachment(faction_name, slug, detachment):
    out = ["# %s" % detachment["name"], ""]
    line = "**%s** - %d DP detachment" % (faction_name, detachment["dp"])
    if detachment.get("force_disposition"):
        # The Force Disposition decides which Primary Mission a list playing
        # this detachment may take (game/force_dispositions.py). It is printed
        # on the detachment, so it is transcribed here rather than assigned.
        line += " - Force Disposition: %s" % detachment["force_disposition"]
    out.append(line)
    out.append("")
    out.append("Source: <%s>" % FACTION_URL.format(slug=slug))
    out.append("")
    if detachment["rule"]:
        out.append("## Detachment rule")
        out.append("")
        for title, text in detachment["rule"]:
            out.append("### %s" % title)
            out.append("")
            if text:
                out.append(text)
                out.append("")
    if detachment["enhancements"]:
        out.append("## Enhancements")
        out.append("")
        for item in detachment["enhancements"]:
            heading = item["name"]
            if item["points"]:
                heading += " - %s" % item["points"]
            out.append("### %s" % heading)
            out.append("")
            if item["text"]:
                out.append(item["text"])
                out.append("")
    if detachment["stratagems"]:
        out.append("## Stratagems")
        out.append("")
        for item in detachment["stratagems"]:
            heading = item["name"]
            if item["cp"]:
                heading += " - %s" % item["cp"]
            out.append("### %s" % heading)
            out.append("")
            if item["type"]:
                out.append("*%s*" % item["type"])
                out.append("")
            if item["text"]:
                out.append(item["text"])
                out.append("")
    return "\n".join(out).rstrip() + "\n"


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------

def normalise_newlines(payload):
    """Make the parse insensitive to how the page's line endings arrived.

    Measured: two fetches of the same unchanged page, one via curl and one via
    urllib, differed only in stray CRs - which survived into the markdown and
    made 60-odd files "change" without a single rule changing. Since a false
    diff is exactly the failure this whole corpus is meant to avoid, the
    newlines are flattened before anything reads the HTML.
    """
    return payload.replace("\r\n", "\n").replace("\r", "\n")


def fetch(slug, offline):
    return _fetch(BASE_URL.format(slug=slug), slug, offline)


def fetch_faction(slug, offline):
    """The faction's index page - army rules, detachments, enhancements and
    the complete stratagem list. Cached under its own name so it cannot
    collide with the datasheets page of the same slug."""
    return _fetch(FACTION_URL.format(slug=slug), "%s-faction" % slug, offline)


def _fetch(url, cache_name, offline):
    path = os.path.join(CACHE_DIR, "%s.html" % cache_name)
    if offline:
        if not os.path.exists(path):
            raise SystemExit(
                "--offline but no cached page for %s (expected %s); "
                "run once without --offline first" % (cache_name, path))
        with open(path, encoding="utf-8", errors="replace") as handle:
            return normalise_newlines(handle.read())

    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(request, timeout=90) as response:
        if response.status != 200:
            raise SystemExit("%s returned HTTP %s" % (url, response.status))
        payload = normalise_newlines(response.read().decode("utf-8", errors="replace"))
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
    return payload


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Snapshot datasheet rules as markdown.")
    parser.add_argument("--offline", action="store_true",
                        help="re-parse rules/.cache/ instead of downloading")
    parser.add_argument("--only", action="append", default=[], metavar="NAME",
                        help="write just these datasheets (repeatable)")
    parser.add_argument("--detachment", action="append", default=[], metavar="NAME",
                        help="write just these detachments (repeatable)")
    args = parser.parse_args()

    only = {normalise_name(n) for n in args.only}
    only_detachments = {normalise_name(n) for n in args.detachment}
    # Each flag narrows to its own kind of file and switches the other off, so
    # `--only "Vespid Stingwings"` does not also re-download five faction pages
    # and `--detachment Kauyon` does not re-render 113 datasheets.
    do_datasheets = bool(only) or not only_detachments
    do_faction_pages = bool(only_detachments) or not only
    matched = set()
    matched_detachments = set()
    written = []
    index_rows = []
    detachment_rows = []

    for folder, slug, faction in FACTIONS:
        blocks = []
        faction_written = []
        if do_datasheets:
            page = fetch(slug, args.offline)
            blocks = split_blocks(page)
            if len(blocks) < MIN_BLOCKS_PER_FACTION:
                raise SystemExit(
                    "%s yielded only %d datasheet blocks (expected >= %d) - the page "
                    "shape changed or the download was truncated; refusing to write a "
                    "half corpus" % (slug, len(blocks), MIN_BLOCKS_PER_FACTION))

            faction_written = _write_datasheets(
                folder, slug, faction, blocks, only, matched, written)

        if do_faction_pages:
            _write_faction_rules(
                folder, slug, faction, args.offline, only_detachments,
                matched_detachments, written, detachment_rows)

        if faction_written:
            version = next((s["version"] for s in faction_written if s["version"]), "")
            index_rows.append((folder, faction.name, version, len(faction_written),
                               sorted(s["name"] for s in faction_written)))
        print("%-12s %3d blocks on the page, %3d written"
              % (folder, len(blocks), len(faction_written)))

    unknown = sorted(only - matched)
    if unknown:
        raise SystemExit("--only named no known datasheet: %s" % ", ".join(unknown))
    unknown = sorted(only_detachments - matched_detachments)
    if unknown:
        raise SystemExit("--detachment named no known detachment: %s" % ", ".join(unknown))

    if not only and not only_detachments:
        write_index(index_rows, detachment_rows)
    print("\n%d markdown files under %s" % (len(written), OUT_DIR))


def _write_datasheets(folder, slug, faction, blocks, only, matched, written):
    """Render the datasheet files for one faction; returns those written."""
    by_key = {}
    for block in blocks:
        sheet = parse_datasheet(block)
        by_key[normalise_name(sheet["name"])] = sheet

    wanted = list(faction.datasheets)
    # DEDUPLICATED against what is already built, so a MISSING_* list needs
    # no editing as those datasheets get built one by one - a name that
    # appears in both lists would otherwise write its file twice and
    # make every "expected file count" wrong.
    built = {normalise_name(n) for n in faction.datasheets}
    wanted += [n for n in MISSING_BY_FOLDER.get(folder, ())
               if normalise_name(n) not in built]

    missing = [n for n in wanted if normalise_name(n) not in by_key]
    if missing:
        raise SystemExit(
            "no Wahapedia datasheet found for %s: %s\n"
            "(the printed name may have changed - check %s)"
            % (folder, ", ".join(sorted(missing)), BASE_URL.format(slug=slug)))

    out_folder = os.path.join(OUT_DIR, folder)
    os.makedirs(out_folder, exist_ok=True)
    faction_written = []
    for wanted_name in wanted:
        key = normalise_name(wanted_name)
        if only and key not in only:
            continue
        matched.add(key)
        sheet = by_key[key]
        path = os.path.join(out_folder, "%s.md" % safe_filename(sheet["name"]))
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(render_markdown(sheet, faction.name, slug))
        faction_written.append(sheet)
        written.append(path)
    return faction_written


def _write_faction_rules(folder, slug, faction, offline, only_detachments,
                         matched, written, detachment_rows):
    """Render `<folder>/army_rules.md` and `<folder>/detachments/*.md`."""
    page = fetch_faction(slug, offline)
    army_rules, detachments = parse_faction_page(page)
    if len(detachments) < MIN_DETACHMENTS_PER_FACTION:
        raise SystemExit(
            "%s yielded only %d detachments (expected >= %d) - the faction page "
            "shape changed or the download was truncated; refusing to write a "
            "half corpus" % (slug, len(detachments), MIN_DETACHMENTS_PER_FACTION))
    if not army_rules:
        raise SystemExit(
            "%s yielded no army rule - the faction page shape changed (see "
            "parse_faction_page's note on Death Guard's sibling h2)" % slug)

    out_folder = os.path.join(OUT_DIR, folder)
    os.makedirs(out_folder, exist_ok=True)
    if not only_detachments:
        path = os.path.join(out_folder, "army_rules.md")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(render_army_rules(faction.name, slug, army_rules))
        written.append(path)

    det_folder = os.path.join(out_folder, "detachments")
    os.makedirs(det_folder, exist_ok=True)
    names = []
    for detachment in detachments:
        key = normalise_name(detachment["name"])
        if only_detachments and key not in only_detachments:
            continue
        matched.add(key)
        path = os.path.join(det_folder, "%s.md" % safe_filename(detachment["name"]))
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(render_detachment(faction.name, slug, detachment))
        written.append(path)
        names.append(detachment["name"])
    if names:
        # "Errata"/"FAQ" are sections of the army rule, not further army
        # rules, so they do not belong in the index's label for it.
        rule_names = [t for t, _ in army_rules
                      if not re.search(r"errata|faq", t, re.I)]
        detachment_rows.append((folder, faction.name, rule_names, sorted(names)))


def write_index(rows, detachment_rows=()):
    out = [
        "# Printed rules",
        "",
        "One file per datasheet, plus each faction's `army_rules.md` and one file",
        "per detachment under `<faction>/detachments/` (its detachment rule,",
        "enhancements and stratagems). All of it holds the rule text as printed and",
        "is generated by `fetch_datasheet_rules.py` from Wahapedia. **Do not",
        "hand-edit** - the point of this folder is that re-running the script and",
        "reading `git diff` tells you exactly which rules Games Workshop changed.",
        "",
        "    python fetch_datasheet_rules.py                  # refresh everything",
        "    python fetch_datasheet_rules.py --offline        # re-parse the cached HTML",
        "    python fetch_datasheet_rules.py --only NAME      # just these datasheets",
        "    python fetch_datasheet_rules.py --detachment X   # just these detachments",
        "",
        "Every datasheet built in `game/factions/` has a file here. The T'au and",
        "Aeldari folders additionally carry entries that are not built yet, because",
        "these files are the transcription source when they are (see MISSING_BY_FOLDER",
        "in the script). Detachments are snapshotted in full for every faction, built",
        "or not, for the same reason.",
        "",
        "Last fetched: %s" % datetime.date.today().isoformat(),
        "",
        "| Faction | Files | Wahapedia version |",
        "| --- | --- | --- |",
    ]
    for folder, name, version, count, _names in rows:
        out.append("| [%s](%s/) | %d | %s |" % (name, folder, count, version or "-"))
    out.append("")
    by_folder = {folder: (army, names) for folder, _n, army, names in detachment_rows}
    for folder, name, _version, _count, names in rows:
        out.append("## %s" % name)
        out.append("")
        army, detachments = by_folder.get(folder, ([], []))
        if army:
            out.append("**Army rule:** [%s](%s/army_rules.md)" % (", ".join(army), folder))
            out.append("")
        if detachments:
            out.append("**Detachments:**")
            out.append("")
            for entry in detachments:
                out.append("- [%s](%s/detachments/%s.md)"
                           % (entry, folder, safe_filename(entry)))
            out.append("")
            out.append("**Datasheets:**")
            out.append("")
        for entry in names:
            out.append("- [%s](%s/%s.md)" % (entry, folder, safe_filename(entry)))
        out.append("")
    with open(os.path.join(OUT_DIR, "README.md"), "w",
              encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(out).rstrip() + "\n")


if __name__ == "__main__":
    main()
