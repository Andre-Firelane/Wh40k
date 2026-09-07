"""Every weapon's printed characteristics, against rules/<faction>/<sheet>.md.

Reported: "in den infos stehen voellig falsche schadenswerte ... wenn die
fehler echt sind, dann muesste dringend mal alle stats gegengecheckt werden.
die werte muessen genau sein."

The three reported weapons turned out to be a DISPLAY defect (see
test_unit_datacard.py section 9), but putting the two columns side by side to
prove that also found thirteen genuine ones, none of which any suite was
guarding: the Dark Reapers' missile launcher dealt a flat 6 for a printed D6,
the Farseer's Eldritch Storm hit on 2+ for a printed 3+, the Corsair
Voidscarred's three melee rows were each a characteristic out, and two pulse
pistols inherited a skill their printed row does not have.

WHY THIS IS A SUITE where verify_rules_vs_engine.py is deliberately only a
report: that report exists because points and base sizes deviate from the
published lists BY STANDING DECISION, and a suite that went red on those would
be wrong about what this repo has chosen. No such decision exists for weapon
characteristics - after the fixes above there are ZERO differences - so here
the report's own advice ("what to look at is anything that was NOT a deliberate
choice") can be enforced instead of printed. The exceptions below are the
deliberate ones, each named with its reason; an exception that stops matching
anything fails too, so the list cannot quietly rot.

The comparison itself lives in verify_rules_vs_engine.py and is imported, not
copied - two implementations of "what does this weapon print" is precisely the
drift this repo consolidates at the second consumer.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk  # noqa: E402
from fetch_datasheet_rules import FACTIONS, normalise_name  # noqa: E402
from game.weapons import MELEE  # noqa: E402
from verify_rules_vs_engine import (  # noqa: E402
    engine_weapon_stats, printed_weapons, read_corpus, same_value, weapon_pairs,
)

checks = tk.Checks("Weapon characteristics vs printed rules")


# --- deliberate exceptions -------------------------------------------------
# Each is a NAME the engine uses that its printed row does not, or a loadout
# question that is not a characteristic question. None of them is a wrong
# NUMBER - every one was checked by hand against its printed row.
UNMATCHED_BY_NAME = {
    # The engine spells a firing mode "<weapon> - <mode>"; the datasheet spells
    # it "<weapon> - <mode>" too, but not always with the same mode word.
    "Ion Accelerator - Overcharge": "printed 'ion accelerator - supercharge'; S10/AP-3/D4 match",
    "Plasma Gun": "printed 'plasma gun - standard'; S7/AP-2/D1 match",
    "Plasma Pistol": "printed 'plasma pistol - standard'; S7/AP-2/D1 match",
    # A keyword that was read as part of the name when this weapon was
    # transcribed: the printed row is "missile launcher - sunburst" with
    # [BLAST] in the keyword column.
    "Missile Launcher - Sunburst Blast": "printed 'missile launcher - sunburst', [BLAST] is the keyword",
    "Twin Missile Launcher - Sunburst Blast": "same, twin-mounted",
    # Flavour names the engine gave two rows the datasheet leaves generic.
    "Grot-Smacka": "printed 'Runtherd tools'; A3/S5/AP0/D1 match exactly",
    "Spiked Wheel": "printed 'Spiked wheels' (plural); A3/S6/AP0/D1 match",
    # NOT a name question: the engine's Riptide carries two Missile Drones, and
    # the 11th-edition datasheet in rules/ has no drones and no missile pod at
    # all. A composition difference, reported rather than silently dropped -
    # removing two guns from a fielded unit is a decision, not a transcription.
    "Missile Pod": "Riptide's 2x Missile Drone; the printed sheet has no drones",
}

VALUE_EXCEPTIONS = {}   # empty, and that is the point - see the docstring


corpus = read_corpus()
compared = 0
value_diffs = []
name_diffs = []
seen_exceptions = set()

for folder, _slug, faction in FACTIONS:
    for sheet_name, sheet in sorted(faction.datasheets.items()):
        key = (folder, normalise_name(sheet_name))
        if key not in corpus:
            continue
        _path, text = corpus[key]
        printed_rows = printed_weapons(text)
        for weapon_cls, profile_cls in weapon_pairs(sheet):
            is_melee = weapon_cls.weapon_type == MELEE
            row = printed_rows.get((is_melee, normalise_name(weapon_cls.name)))
            if row is None:
                if weapon_cls.name in UNMATCHED_BY_NAME:
                    seen_exceptions.add(weapon_cls.name)
                else:
                    name_diffs.append("%s/%s: %s" % (folder, sheet_name, weapon_cls.name))
                continue
            mine = engine_weapon_stats(weapon_cls, profile_cls)
            for column, engine_value in mine.items():
                if column not in row:
                    continue
                # [TORRENT] prints its skill as N/A because rule 24.37 makes it
                # hit automatically - no Hit roll is ever made, so the wielder's
                # skill is never read. Agreement, not a difference. A weapon
                # that prints N/A and is NOT torrent still fails.
                if (column in ("BS", "WS")
                        and row[column].strip().rstrip("*") in ("N/A", "-", "")
                        and getattr(weapon_cls, "torrent", False)):
                    continue
                compared += 1
                if not same_value(row[column], engine_value):
                    value_diffs.append("%s/%s %s %s: printed %s, engine %s"
                                       % (folder, sheet_name, weapon_cls.name,
                                          column, row[column], engine_value))

print("--- 1. every weapon characteristic matches its printed row ---")

# Guards the guard: a comparison that silently stopped finding weapons would
# report zero differences and look like a pass.
checks.true("the sweep actually compared a real number of characteristics (>3000)",
            compared > 3000)
checks.eq("no weapon characteristic differs from its printed row",
          sorted(value_diffs), [])

print("--- 2. every weapon's printed row is FOUND ---")

# A drifted name is how a weapon stops being compared at all, so it fails here
# rather than being skipped in silence.
checks.eq("every weapon matches a printed row, or is a named exception",
          sorted(name_diffs), [])

print("--- 3. the exception list does not rot ---")

# An exception that no longer matches anything is an expired excuse: it would
# sit here forever claiming to cover a case the engine has since renamed.
checks.eq("every named exception still applies to something",
          sorted(set(UNMATCHED_BY_NAME) - seen_exceptions), [])
checks.eq("...and there are no value exceptions at all", VALUE_EXCEPTIONS, {})

print("--- 4. the three weapons from the report ---")

# Pinned by name against the corpus, so this stays meaningful even if the
# comparison above is ever narrowed.
from game import weapons as w  # noqa: E402
from game.dice_notation import describe  # noqa: E402

for label, weapon_cls, want in (
        ("Spear of the Void Dragon", w.SpearOfTheVoidDragonAntiVehicleProfile, "D6+2"),
        ("Entropy Cannon", w.EntropyCannonProfile, "D6+1"),
        ("Multi-melta", w.MultiMeltaProfile, "D6"),
):
    checks.eq("%s rolls %s for Damage" % (label, want),
              describe(weapon_cls.damage_notation), want)

checks.finish()
