"""Which PRINTED rule is this decision prompt about?

User: "immer wenn ich aufgefordert werde durch eine Fähigkeit etwas auf dem
Spielfeld auszuwählen. zb. bei necron immortals oder deathguard, schreibe die
Fähigkeit Regel mit in die rechte Spalte, sonst weiß ich gar nicht was ich da
auswähle."

A board pick (game/unit_pick.py) deliberately draws NO overlay - the modal
would sit on the very units that have to be clicked - so all the player gets
is the left panel's one-line prompt and some rings. "Living Lightning - strike
which unit?" says what to do and nothing about what it does.

WHY THIS IS A LOOKUP AND NOT A NEW ARGUMENT ON request()
--------------------------------------------------------
The obvious build is `DecisionManager.request(..., rule="Living Lightning")`.
It was rejected on a measurement: there are 90 request() call sites in game/,
and ~55 of them tag units. Every one would have to name its own rule by hand,
every one is a chance to name it wrongly or not at all, and nothing would ever
go red when a new one forgot - the panel would just stay empty, which is
exactly today's behaviour.

The prompts ALREADY name the rule, because they were written for a human to
read: "{squad.name}: Living Lightning - strike which unit?",
"{MARKER_BEACON_NAME}: which objective does {squad.name} secure?". So this
module reads the name back out of the prompt instead of asking for it a second
time - one place to get right, and a new ability is covered the moment its
prompt says its own name, with no call site to remember.

MEASURED, NOT ASSUMED (survey over all 90 prompts x 300 printed names of the
five factions):
  * 56 prompts contain a printed rule name; the rest are core rules that have
    no corpus entry at all ([PRECISION], re-roll offers, Counteroffensive,
    missions, the pre-game roll-off) - nothing is being missed there, there is
    nothing to show.
  * ZERO prompts matched two DIFFERENT rules. The one double hit is one rule
    printed twice (a datasheet ability and a stratagem of the same name), so
    the longest-match tie-break is never arbitrating between two real answers.
  * The shortest printed ability name is 7 characters ("Pech'ra", "Sunforge") -
    none of them is a common English word that could turn up in an unrelated
    prompt. MIN_NAME_LEN is insurance, not the thing that makes this work;
    word-boundary matching is.

WHERE THE CANDIDATE NAMES COME FROM. Only rules that are actually ON THE TABLE:
the datasheets of the units passed in, plus the detachment Stratagems of the
army being asked. Searching the whole corpus would widen the false-match
surface for no gain - a rule nobody fields cannot be the one asking.

DEGRADES TO NOTHING. Every failure - no match, no corpus file, a name printed
under a different spelling - returns (None, []) and the panel simply shows what
it showed before. This runs from the render path, so "unresolvable" must never
be an exception mid-frame.
"""

import re

from game import rules_text

#: Insurance only - see the module docstring: the shortest name the corpus
#: actually prints is 7 characters long.
MIN_NAME_LEN = 4


def _datasheets(squads):
    """Every datasheet behind these units, components of a rule 19.01 merge
    included.

    The components matter and are the whole reason this is not
    `squad.datasheet`: the reported case is "1 Immortals 1 + Plasmancer", where
    the ability doing the asking (Living Lightning) is printed by the LEADER,
    and the merged unit's own datasheet is the Immortals'."""
    seen = {}
    for squad in squads or ():
        if squad is None:
            continue
        sheets = []
        if getattr(squad, "datasheet", None) is not None:
            sheets.append(squad.datasheet)
        for component in getattr(squad, "attached_components", ()) or ():
            if getattr(component, "datasheet", None) is not None:
                sheets.append(component.datasheet)
        for sheet in sheets:
            seen.setdefault(id(sheet), sheet)
    return list(seen.values())


def candidates(squads, faction_keyword=None, detachments=()):
    """[(name, kind, source)] - every printed rule these units could be asked
    about. `kind` is "ability" or "stratagem"; `source` is the datasheet or the
    detachment name it was found in."""
    out = []
    for sheet in _datasheets(squads):
        for ability in rules_text.abilities_for(sheet):
            if ability.title and len(ability.title) >= MIN_NAME_LEN:
                out.append((ability.title, "ability", sheet))
    for detachment in detachments or ():
        name = getattr(detachment, "name", detachment)
        for stratagem in rules_text.detachment_stratagems(faction_keyword, name):
            if stratagem.name and len(stratagem.name) >= MIN_NAME_LEN:
                out.append((stratagem.name, "stratagem", name))
    return out


def _bare(name):
    """A printed name without its trailing bracketed tag, or None.

    MEASURED: 29 of the 264 printed ability titles across the five factions end
    in one - "Guide (Psychic)", "Doom (Psychic)", "The Bloody-Handed (Aura)",
    "Pestilent Fallout (Psychic)". The prompts write the name without it, so
    without this alias the psychic marks - which are board picks, the exact
    shape this exists for - would never resolve. Not a special case for one
    datasheet: it is how the corpus prints a whole class of abilities."""
    stripped = re.sub(r"\s*\([^()]*\)$", "", name or "").strip()
    return stripped if stripped and stripped != name else None


def _mentioned(prompt, name):
    """Is `name` printed in `prompt` as a whole word?

    Word boundaries rather than a bare `in`: without them "Guide" would match
    inside "Guided" and a prompt could be attributed to a rule it never named.
    Letters only on the boundary, because most of these names end in a
    punctuation-adjacent position ("Living Lightning - strike which unit?")."""
    for candidate in (name, _bare(name)):
        if not candidate:
            continue
        if re.search(r"(?<![A-Za-z])" + re.escape(candidate) + r"(?![A-Za-z])",
                     prompt, re.IGNORECASE):
            return True
    return False


def for_prompt(prompt, squads, faction_keyword=None, detachments=()):
    """(name, blocks) for the rule this prompt is about, or (None, []).

    `blocks` are game/ui/rules_body.py Blocks - the same typesetting the army
    rules reader and the stratagem tooltip use, so the three cannot drift into
    three house styles for one corpus.

    Longest name first: where two names both appear, the longer one is the more
    specific, and (measured over every shipped prompt) the only time two match
    at all is one rule printed under two headings.

    Cached, because this is asked once per FRAME for as long as the prompt is
    open and a prompt stays open for as long as the player takes to answer it.
    Measured at 0.55ms per call (31 candidate names, ~50 regexes) - about 3% of
    a frame, for an answer that cannot change while the prompt does not. The
    key includes the datasheets because those decide the candidate list;
    they are module-level singletons, so their ids are stable for the run."""
    if not prompt:
        return None, []
    from game.ui import rules_body      # UI import kept local - game/ does not depend on game/ui/

    key = (prompt, faction_keyword,
           tuple(getattr(d, "name", d) for d in detachments or ()),
           tuple(sorted(id(s) for s in _datasheets(squads))))
    if key in _prompt_cache:
        return _prompt_cache[key]
    answer = _look_up(prompt, squads, faction_keyword, detachments, rules_body)
    _prompt_cache[key] = answer
    return answer


_prompt_cache = {}


def _look_up(prompt, squads, faction_keyword, detachments, rules_body):
    for name, kind, source in sorted(candidates(squads, faction_keyword, detachments),
                                     key=lambda c: len(c[0]), reverse=True):
        if not _mentioned(prompt, name):
            continue
        if kind == "ability":
            lines = rules_text.ability_blocks(source, name)
            if lines:
                return name, rules_body.blocks_for(lines)
        else:
            stratagem = rules_text.stratagem_named(faction_keyword, detachments, name)
            if stratagem is not None:
                blocks = [rules_body.Block("stratagem", stratagem.heading)]
                blocks.extend(rules_body.blocks_for(stratagem.lines))
                return name, blocks
    return None, []
