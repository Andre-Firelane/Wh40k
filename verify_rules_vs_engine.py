"""Compare the printed rules in rules/*.md against what the engine actually has.

This is a REPORT, not a test, and that is deliberate. The standing decision in
this project is that the transcribed values win and a disagreement with the
published list is NAMED rather than quietly aligned (see the points notes all
over CLAUDE.md, where the deviations run in both directions). A suite that went
red on every such deviation would be wrong about what this repo has decided.

What it is good for is the OTHER direction: a value that drifted because Games
Workshop changed it, or because a transcription slipped. Both look identical
until something puts the two columns side by side.

    python verify_rules_vs_engine.py            # every faction
    python verify_rules_vs_engine.py necrons    # substring filter

Compared per datasheet:
  * the six characteristics (M / T / SV / W / LD / OC), per model line
  * base diameter, printed vs the engine's base_radius_in
  * the invulnerable save, INCLUDING the case the engine has one and the
    printed sheet no longer does
  * the points, per composition tier
  * every WEAPON's Range / A / BS or WS / S / AP / D, per datasheet

Two things the weapon pass has to get right or it drowns in false positives,
both learned the hard way while it was being written:
  * WS/BS live on the model PROFILE here, not on the weapon (WeaponProfile
    says so in its own docstring); a weapon only carries an override where
    its printed row disagrees with its wielder's own skill. So the comparison
    resolves override-else-profile, exactly as shooting.py's
    effective_ballistic_skill() does.
  * Attacks, Strength and Damage can each be a die roll rather than a number
    (attacks_notation / strength_notation / damage_notation). Where one is
    set, the plain int beside it is only a grouping placeholder, so the
    notation is what gets compared - reading the int instead reports every
    dice-notation weapon as wrong, and is the same mistake the unit datacard
    itself was making.

A weapon whose printed row cannot be found by name is reported separately
rather than skipped: a name that has drifted is exactly how a weapon stops
being compared at all.
"""

import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_datasheet_rules import FACTIONS, normalise_name, safe_filename  # noqa: E402
from game.dice_notation import describe  # noqa: E402
from game.weapons import MELEE  # noqa: E402

MM_PER_INCH = 25.4


def read_corpus():
    """Every rules/*.md, keyed by (folder, normalised datasheet name)."""
    corpus = {}
    for path in sorted(glob.glob(os.path.join("rules", "*", "*.md"))):
        folder = os.path.basename(os.path.dirname(path))
        text = io.open(path, encoding="utf-8").read()
        title = text.split("\n", 1)[0].lstrip("# ").strip()
        corpus[(folder, normalise_name(title))] = (path, text)
    return corpus


def section(text, heading):
    match = re.search(r"^## %s\s*$" % re.escape(heading), text, re.M)
    if not match:
        return ""
    rest = text[match.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return (rest[:nxt.start()] if nxt else rest).strip()


def table_rows(block):
    rows = []
    for line in block.split("\n"):
        line = line.strip()
        if not line.startswith("|") or re.match(r"^\|(?: --- \|)+$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    return rows


def printed_profiles(text):
    """[(model label or '', {char: value})] from the ## Profile table.

    "INSV" stays in the dict: the invulnerable save is a per-model-line
    characteristic on this sheet (an Aspect Warrior and its Exarch can print
    different ones), so it is compared alongside the other six.
    """
    rows = table_rows(section(text, "Profile"))
    if not rows:
        return []
    header = rows[0]
    out = []
    for row in rows[1:]:
        entry = dict(zip(header, row))
        label = entry.pop("Model", "")
        entry.pop("Base", None)
        out.append((label, entry))
    return out


def printed_base_mm(text, label=""):
    """The printed base diameter in mm, or None.

    Oval bases print as "120 x 92mm"; the engine stores an equal-area circle
    for those, so they are reported but not arithmetic-checked.
    """
    source = ""
    if label:
        for row in table_rows(section(text, "Profile"))[1:]:
            if row and row[0] == label:
                source = row[-1]
                break
    if not source:
        match = re.search(r"^- \*\*Base:\*\* (.+)$", text, re.M)
        source = match.group(1) if match else ""
    if not source:
        return None, ""
    cleaned = source.replace("⌀", "").strip()
    if "x" in cleaned.lower():
        return None, cleaned
    number = re.search(r"([\d.]+)\s*mm", cleaned)
    return (float(number.group(1)) if number else None), cleaned



def printed_weapons(text):
    """{(is_melee, normalised name): {column: value}} from both weapon tables."""
    out = {}
    for heading, is_melee in (("Ranged Weapons", False), ("Melee Weapons", True)):
        rows = table_rows(section(text, heading))
        if not rows:
            continue
        header = rows[0]
        for row in rows[1:]:
            entry = dict(zip(header, row))
            name = entry.get("Weapon")
            if name:
                out[(is_melee, normalise_name(name))] = entry
    return out


def firing_modes(weapon_cls):
    """A weapon and every alternate firing mode hanging off it (an Ion
    weapon's Overcharge, a Plasma weapon's Supercharge) - each of those is a
    printed row of its own and so gets compared of its own."""
    chain = []
    while weapon_cls is not None and weapon_cls not in chain:
        chain.append(weapon_cls)
        weapon_cls = getattr(weapon_cls, "overcharge_profile", None)
    return chain


def weapon_pairs(sheet):
    """[(weapon class, the UnitProfile that wields it)] for everything this
    datasheet can field - default loadouts, wargear swaps and weapon-granting
    gear alike. The wielder comes along because BS/WS are read off it."""
    pairs, seen = [], set()
    compositions = list(sheet.compositions())
    default_holder = compositions[0][0].profile_cls if compositions and compositions[0] else None

    def add(weapon_cls, holder):
        for mode in firing_modes(weapon_cls):
            if (mode, holder) not in seen:
                seen.add((mode, holder))
                pairs.append((mode, holder))

    for composition in compositions:
        for model_line in composition:
            for weapon_cls in model_line.default_weapons:
                add(weapon_cls, model_line.profile_cls)
    for option in getattr(sheet, "wargear_options", None) or []:
        holder = default_holder
        for composition in compositions:
            for model_line in composition:
                if model_line.name == getattr(option, "model_line_name", None):
                    holder = model_line.profile_cls
        for weapon_cls in getattr(option, "with_weapons", None) or []:
            add(weapon_cls, holder)
    for item in getattr(sheet, "gear_options", None) or []:
        for weapon_cls in getattr(item, "weapons", None) or []:
            add(weapon_cls, default_holder)
    return pairs


def engine_weapon_stats(weapon_cls, profile_cls):
    """The engine's answer for one weapon's printed row, in the corpus's own
    spelling. `describe` renders a dice-notation characteristic the way the
    datasheet prints it ("D6+2"), so the two columns are comparable."""
    is_melee = weapon_cls.weapon_type == MELEE
    attribute = "weapon_skill" if is_melee else "ballistic_skill"
    skill = getattr(weapon_cls, attribute, None) or getattr(profile_cls, attribute, None)

    def characteristic(which):
        notation = getattr(weapon_cls, which + "_notation", None)
        return describe(notation) if notation is not None else str(getattr(weapon_cls, which))

    return {
        "RANGE": "Melee" if is_melee else '%g"' % weapon_cls.range_in,
        "A": characteristic("attacks"),
        "WS" if is_melee else "BS": "N/A" if skill in (None, "N/A") else str(skill),
        "S": characteristic("strength"),
        "AP": str(weapon_cls.ap),
        "D": characteristic("damage"),
    }


def same_value(printed, engine):
    """A trailing "*" marks a characteristic an ability modifies; the number
    itself is the comparison, as it already is for the statline."""
    return normalise_name(printed.strip().rstrip("*")) == normalise_name(engine)


def engine_stats(profile_cls):
    return {
        "M": "%g\"" % profile_cls.movement_in,
        "T": str(profile_cls.toughness),
        "SV": str(profile_cls.armor_save),
        "W": str(profile_cls.wounds),
        "LD": str(profile_cls.leadership),
        "OC": str(profile_cls.oc),
    }


def main():
    needle = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    corpus = read_corpus()
    findings = []
    checked = 0

    for folder, _slug, faction in FACTIONS:
        if needle and needle not in folder.lower():
            continue
        for sheet_name, sheet in sorted(faction.datasheets.items()):
            key = (folder, normalise_name(sheet_name))
            if key not in corpus:
                findings.append((folder, sheet_name, "no rules/*.md file", "", ""))
                continue
            _path, text = corpus[key]
            checked += 1

            lines = []
            for composition in sheet.compositions():
                for model_line in composition:
                    if model_line.profile_cls not in [m.profile_cls for m in lines]:
                        lines.append(model_line)

            printed = printed_profiles(text)

            # -- statline ---------------------------------------------------
            # Matched by LABEL, never by position: the engine builds its model
            # lines leader-first (Exarch, Boss Nob) while the printed sheet
            # lists the rank and file first, so a positional match reports
            # every two-line datasheet as two wrong wound counts. Where the
            # sheet prints one unlabelled profile for a unit the engine splits
            # into two lines (Tankbustas), that single profile is the right
            # comparison for both.
            by_label = {normalise_name(label): values
                        for label, values in printed if label}
            for model_line in lines:
                values = None
                label = ""
                for candidate in (model_line.name, model_line.profile_cls.name):
                    if candidate and normalise_name(candidate) in by_label:
                        label = candidate
                        values = by_label[normalise_name(candidate)]
                        break
                if values is None:
                    if len(printed) == 1:
                        label, values = printed[0]
                    else:
                        findings.append((
                            folder, sheet_name,
                            "no printed profile matches this model line",
                            model_line.name or model_line.profile_cls.name, ""))
                        continue
                mine = engine_stats(model_line.profile_cls)
                for char in ("M", "T", "SV", "W", "LD", "OC"):
                    if char not in values:
                        continue
                    # A trailing "*" marks a characteristic a datasheet ability
                    # modifies (the Runtherd's T5*); the number itself is the
                    # comparison.
                    want = values[char].strip().rstrip("*")
                    got = mine[char]
                    if want != got:
                        findings.append((
                            folder, sheet_name,
                            "%s (%s)" % (char, label or model_line.profile_cls.name),
                            want, got))

                # -- base ---------------------------------------------------
                printed_mm, raw = printed_base_mm(text, label)
                if printed_mm:
                    engine_mm = model_line.profile_cls.base_radius_in * 2 * MM_PER_INCH
                    if abs(engine_mm - printed_mm) > 1.0:
                        findings.append((
                            folder, sheet_name,
                            "base (%s)" % (label or model_line.profile_cls.name),
                            raw, "%.1fmm (r=%.3f\")"
                            % (engine_mm, model_line.profile_cls.base_radius_in)))

            # -- invulnerable save ------------------------------------------
            for model_line in lines:
                profile_cls = model_line.profile_cls
                values = None
                for candidate in (model_line.name, profile_cls.name):
                    if candidate and normalise_name(candidate) in by_label:
                        values = by_label[normalise_name(candidate)]
                        break
                if values is None and len(printed) == 1:
                    values = printed[0][1]
                raw_inv = (values or {}).get("INSV", "-").rstrip("*")
                printed_inv = None if raw_inv in ("-", "") else raw_inv
                # "-" is this engine's spelling of "no invulnerable save"
                # (game/units.py:25), and a conditional printed save ("INSV*",
                # e.g. Rangers' ranged-only 5+) is stored on one of the two
                # scoped fields instead - so all three have to be consulted or
                # every conditional save reads as missing.
                engine_inv = getattr(profile_cls, "invulnerable_save", "-")
                if engine_inv in ("-", None, ""):
                    engine_inv = (getattr(profile_cls, "invulnerable_save_vs_ranged", None)
                                  or getattr(profile_cls, "invulnerable_save_vs_melee", None))
                if engine_inv in ("-", None, ""):
                    engine_inv = None
                what = "invulnerable save (%s)" % (
                    model_line.name or profile_cls.name)
                if printed_inv != (str(engine_inv) if engine_inv else None):
                    findings.append((
                        folder, sheet_name, what,
                        printed_inv or "not printed",
                        str(engine_inv) if engine_inv else "none in engine"))

            # -- weapons ----------------------------------------------------
            printed_rows = printed_weapons(text)
            for weapon_cls, profile_cls in weapon_pairs(sheet):
                is_melee = weapon_cls.weapon_type == MELEE
                row = printed_rows.get((is_melee, normalise_name(weapon_cls.name)))
                if row is None:
                    # Reported, not skipped: a drifted name is precisely how a
                    # weapon quietly stops being compared at all.
                    findings.append((
                        folder, sheet_name, "no printed row for this weapon",
                        "%s weapon" % ("melee" if is_melee else "ranged"),
                        weapon_cls.name))
                    continue
                mine = engine_weapon_stats(weapon_cls, profile_cls)
                for column, engine_value in mine.items():
                    if column not in row:
                        continue
                    # A [TORRENT] weapon prints its skill as "N/A"/"-" because
                    # rule 24.37 makes it hit automatically - no Hit roll is
                    # ever made with it, so whatever skill the wielder happens
                    # to have is never read. That is agreement, not a
                    # difference; reporting all 35 of them every run is how a
                    # report stops being read. A weapon that prints N/A and is
                    # NOT torrent still shows up, which is the case worth
                    # seeing.
                    if (column in ("BS", "WS")
                            and row[column].strip().rstrip("*") in ("N/A", "-", "")
                            and getattr(weapon_cls, "torrent", False)):
                        continue
                    if not same_value(row[column], engine_value):
                        findings.append((
                            folder, sheet_name,
                            "%s %s" % (weapon_cls.name, column),
                            row[column], engine_value))

            # -- points -----------------------------------------------------
            if sheet.points:
                printed_points = {}
                for row in table_rows(section(text, "Points")):
                    if len(row) < 3 or row[0] in ("Unit", "WARGEAR OPTIONS"):
                        continue
                    count = re.search(r"(\d+)", row[1])
                    cost = re.search(r"(\d+)", row[2])
                    if count and cost:
                        printed_points.setdefault(int(count.group(1)), []).append(
                            int(cost.group(1)))
                for tier in sheet.points.tiers:
                    for models, cost in sorted(tier.costs.items()):
                        options = printed_points.get(models, [])
                        if options and cost not in options:
                            findings.append((
                                folder, sheet_name, "points (%d models)" % models,
                                "/".join(str(o) for o in sorted(set(options))), str(cost)))

    print("Compared %d datasheets against rules/*.md\n" % checked)
    if not findings:
        print("No differences.")
        return

    print("%-12s %-32s %-34s %-22s %s"
          % ("FACTION", "DATASHEET", "WHAT", "PRINTED", "ENGINE"))
    print("-" * 118)
    seen = set()
    for row in findings:
        if row in seen:
            continue
        seen.add(row)
        print("%-12s %-32s %-34s %-22s %s" % row)
    print("\n%d difference(s). These are reported, not errors: the transcribed "
          "values win by standing decision.\nWhat to look at is anything that "
          "was NOT a deliberate choice - that is a rules change or a slip."
          % len(seen))


if __name__ == "__main__":
    main()
