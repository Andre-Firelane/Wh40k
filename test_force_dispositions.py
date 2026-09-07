"""FORCE DISPOSITIONS: the transcription, the declaration, and the choice.

Every detachment permits exactly one Force Disposition, and it decides which
Primary Mission a list taking that detachment may play. This suite pins:

- the seventeen modelled detachments' dispositions AGAINST THE CORPUS
  (rules/*/detachments/*.md), not against literals. Those files are generated
  straight from Wahapedia's own headings, so this is engine-versus-GW rather
  than one hand-typed list versus another - and a GW change shows up as a
  corpus diff and then as a red line here.
- that a list may only declare a disposition one of its detachments permits,
  which IS the "if you play several, choose one of theirs" rule.
- the choice itself, driven with a constructed two-detachment pair: no shipped
  list has a real choice today (the T'au list's two detachments both permit
  Reconnaissance), so without that pair the mechanism would be untested.
"""

import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk  # noqa: E402
from game import army_lists  # noqa: E402
from game import detachments  # noqa: E402
from game import force_dispositions as fd  # noqa: E402
from game import primary_missions as pm  # noqa: E402
from game.factions.detachment import Detachment  # noqa: E402
from game.factions.faction import FACTIONS  # noqa: E402

checks = tk.Checks("Force Dispositions")

CORPUS_LINE = re.compile(r"^\*\*.*?\*\* - (\d+) DP detachment"
                         r"(?: - Force Disposition: (.+))?$", re.M)


def corpus_entry(folder, name):
    """(DP, printed disposition) as rules/<folder>/detachments/<name>.md has
    it, or None when there is no such file."""
    path = os.path.join("rules", folder, "detachments", f"{name}.md")
    if not os.path.exists(path):
        return None
    found = CORPUS_LINE.search(open(path, encoding="utf-8").read())
    return (int(found.group(1)), found.group(2)) if found else None


# ============================================== 1. the five, and their labels
print("--- 1. the five dispositions ---")

checks.eq("there are five", len(fd.ALL), 5)
checks.eq("ALL and LABELS agree", sorted(fd.ALL), sorted(fd.LABELS))
for key in fd.ALL:
    checks.true(f"{key} is valid", fd.is_valid(key))
    checks.eq(f"{key} round-trips through its printed name",
              fd.from_printed(fd.label(key)), key)
checks.eq("an unknown printed name is None", fd.from_printed("Grand Strategy"), None)
checks.eq("...and an empty one too", fd.from_printed(""), None)
checks.eq("is_valid() rejects an unknown key", fd.is_valid("purge_the_friend"), False)
checks.eq("label() of an unknown key falls back to the key rather than raising",
          fd.label("mystery"), "mystery")


# ================================ 2. every detachment, checked against GW
print("--- 2. the transcription, versus the corpus ---")

FOLDERS = {"AELDARI": "aeldari", "ORKS": "orks", "NECRONS": "necrons",
           "T'AU EMPIRE": "tau_empire", "DEATH GUARD": "death_guard"}

seen = 0
for keyword, folder in FOLDERS.items():
    faction = FACTIONS[keyword]
    for name, detachment in faction.detachments.items():
        entry = corpus_entry(folder, name)
        checks.true(f"{name}: the corpus has a file for it", entry is not None)
        if entry is None:
            continue
        dp, printed = entry
        seen += 1
        checks.eq(f"{name}: DP matches the corpus", detachment.points, dp)
        checks.true(f"{name}: the corpus states a Force Disposition", printed is not None)
        checks.eq(f"{name}: Force Disposition matches the corpus",
                  detachment.force_disposition, fd.from_printed(printed or ""))

checks.eq("all seventeen modelled detachments were checked", seen, 17)

# The corpus itself must be complete - all 56 detachment files carry the line.
files = []
for folder in FOLDERS.values():
    root = os.path.join("rules", folder, "detachments")
    files += [os.path.join(root, f) for f in os.listdir(root) if f.endswith(".md")]
checks.eq("the corpus holds 56 detachments", len(files), 56)
missing = [os.path.basename(f) for f in files
           if not re.search(r"Force Disposition: ", open(f, encoding="utf-8").read())]
checks.eq("every one of them states a Force Disposition", missing, [])
unknown = []
for path in files:
    found = CORPUS_LINE.search(open(path, encoding="utf-8").read())
    if found and found.group(2) and fd.from_printed(found.group(2)) is None:
        unknown.append((os.path.basename(path), found.group(2)))
checks.eq("...and every one of them is one of the five we model", unknown, [])


# =================================== 3. what each shipped list declares
print("--- 3. the five lists ---")

EXPECTED = {
    "aeldari": (fd.PRIORITY_ASSETS, "Secure Asset"),
    "orks": (fd.TAKE_AND_HOLD, "Battlefield Dominance"),
    "necrons": (fd.TAKE_AND_HOLD, "Battlefield Dominance"),
    # User's explicit pick: "fuer die Tau Liste nehme ich reconnaissance
    # (advanced acquisition cadre)". Kauyon permits Reconnaissance too, so the
    # mission is the same either way - but which detachment it comes from is
    # the list-building fact, and it is checked below.
    "tau": (fd.RECONNAISSANCE, "Reconnaissance Sweep"),
    "death_guard": (fd.PRIORITY_ASSETS, "Secure Asset"),
}
for key, (disposition, mission_name) in EXPECTED.items():
    entry = army_lists.get(key)
    checks.eq(f"{entry.name} declares {fd.label(disposition)}",
              entry.force_disposition, disposition)
    checks.eq(f"{entry.name} therefore plays {mission_name}",
              pm.mission_for(entry.force_disposition).name, mission_name)
    checks.eq(f"{entry.name}'s detachments are a legal set",
              detachments.validate(key), [])
    granted = {d.force_disposition for d in detachments.for_army(key)}
    checks.true(f"{entry.name}'s declaration is one its detachments permit",
                entry.force_disposition in granted)

# The T'au list is the only one with more than one detachment, and the user
# named which one the pick comes from.
tau_granted = {d.name: d.force_disposition for d in detachments.for_army("tau")}
checks.eq("Advanced Acquisition Cadre permits Reconnaissance",
          tau_granted["Advanced Acquisition Cadre"], fd.RECONNAISSANCE)
checks.eq("...and so does Kauyon, so the pick is unambiguous either way",
          tau_granted["Kauyon"], fd.RECONNAISSANCE)

# MEASURED CONSEQUENCE, pinned so it cannot drift unnoticed: the shipped lists
# now reach ALL FIVE missions. The dormant column emptied one T'au list at a
# time - Death Trap with the Prototypes list (Disruption) and Unstoppable Force
# with the Retaliation Cadre one (Purge the Foe) - which is exactly the visible
# change this pin was set for. Nothing here is built-and-never-played any more.
reachable = sorted({pm.mission_for(e.force_disposition).name
                    for e in army_lists.ARMY_LISTS})
checks.eq("the shipped lists reach ALL five missions", reachable,
          sorted(m.name for m in pm.ALL_MISSIONS))
dormant = sorted(m.name for m in pm.ALL_MISSIONS if m.name not in reachable)
checks.eq("...leaving none dormant", dormant, [])
checks.eq("Death Trap is reached by the Prototypes list",
          [e.key for e in army_lists.ARMY_LISTS
           if pm.mission_for(e.force_disposition).name == "Death Trap"],
          ["tau_epc"])
checks.eq("...and Unstoppable Force by the Retaliation Cadre one",
          [e.key for e in army_lists.ARMY_LISTS
           if pm.mission_for(e.force_disposition).name == "Unstoppable Force"],
          ["tau_retaliation"])
# ...and each is one detachment swap away, which is what makes "dormant"
# different from "unreachable". These three are already modelled.
for name, want in [("Windrider Host", fd.DISRUPTION),
                   ("Auxiliary Cadre", fd.DISRUPTION),
                   ("Retaliation Cadre", fd.PURGE_THE_FOE)]:
    found = next((d for f in FACTIONS.values() for d in f.detachments.values()
                  if d.name == name), None)
    checks.true(f"{name} is modelled", found is not None)
    checks.eq(f"{name} would unlock {fd.label(want)}",
              found.force_disposition if found else None, want)

# The standing assumption behind all five cards: the opponent plays Take and
# Hold. Both default lists satisfy it.
checks.eq("the default AI list (Necrons) is Take and Hold, as the cards assume",
          army_lists.get("necrons").force_disposition, fd.TAKE_AND_HOLD)


# ======================================= 4. the declaration is validated
print("--- 4. validate() enforces the choice ---")

orks = army_lists.get("orks")
was = orks.force_disposition
orks.force_disposition = fd.DISRUPTION      # War Horde permits Take and Hold
problems = detachments.validate("orks")
checks.eq("declaring a disposition no detachment permits is ONE problem",
          len(problems), 1)
checks.true("...and the message names both the pick and what is on offer",
            "Disruption" in problems[0] and "Take and Hold" in problems[0])
orks.force_disposition = None
checks.eq("declaring NOTHING is not a problem - a list nobody plays a Primary "
          "with needs no disposition", detachments.validate("orks"), [])
orks.force_disposition = was
checks.eq("restored", detachments.validate("orks"), [])


# ============================ 5. the CHOICE, on a constructed pair
print("--- 5. choosing between two detachments that permit different ones ---")

# No shipped list has a real choice, so the mechanism is driven here on a made
# up faction. Without this the "pick one of theirs" rule would be exercised
# only in the degenerate one-detachment case, where it cannot tell a correct
# implementation from one that ignores the list's declaration entirely.
from game.factions.faction import Faction  # noqa: E402

TESTBED = Faction("TESTBED FORCE", keyword="TESTBED")
TESTBED.add_detachment(Detachment("Probe Vanguard", points=1,
                                  force_disposition=fd.RECONNAISSANCE))
TESTBED.add_detachment(Detachment("Probe Anvil", points=1,
                                  force_disposition=fd.TAKE_AND_HOLD))
TESTBED.add_detachment(Detachment("Probe Blade", points=1,
                                  force_disposition=fd.PURGE_THE_FOE))
FACTIONS["TESTBED"] = TESTBED

probe = army_lists.ArmyList("testbed", "Testbed", "TESTBED", "Probe Rule",
                            ("Probe Vanguard", "Probe Anvil"), lambda *a, **k: None,
                            force_disposition=fd.RECONNAISSANCE)
army_lists.ARMY_LISTS.append(probe)
army_lists.BY_KEY["testbed"] = probe
try:
    checks.eq("two detachments, and the list picks the first one's: legal",
              detachments.validate("testbed"), [])
    probe.force_disposition = fd.TAKE_AND_HOLD
    checks.eq("...picking the SECOND one's is equally legal",
              detachments.validate("testbed"), [])
    checks.eq("the two picks really are different missions",
              (pm.mission_for(fd.RECONNAISSANCE).name,
               pm.mission_for(fd.TAKE_AND_HOLD).name),
              ("Reconnaissance Sweep", "Battlefield Dominance"))
    probe.force_disposition = fd.PURGE_THE_FOE
    problems = detachments.validate("testbed")
    checks.eq("picking a THIRD detachment's disposition, which this list does "
              "not field, is refused", len(problems), 1)
    checks.true("...and the message lists both permitted options",
                "Reconnaissance" in problems[0] and "Take and Hold" in problems[0])
finally:
    army_lists.ARMY_LISTS.remove(probe)
    del army_lists.BY_KEY["testbed"]
    del FACTIONS["TESTBED"]


# ================================== 6. resolving a player to their mission
print("--- 6. player -> list -> disposition -> mission ---")

from game import config  # noqa: E402

was1, was2 = config.PLAYER1_ARMY, config.PLAYER2_ARMY
try:
    config.PLAYER1_ARMY, config.PLAYER2_ARMY = "aeldari", "necrons"
    checks.eq("Player 1 on Aeldari: Priority Assets",
              army_lists.force_disposition_for("Player 1"), fd.PRIORITY_ASSETS)
    checks.eq("Player 2 on Necrons: Take and Hold",
              army_lists.force_disposition_for("Player 2"), fd.TAKE_AND_HOLD)
    config.PLAYER1_ARMY = "tau"
    checks.eq("switching Player 1's list really switches the disposition",
              army_lists.force_disposition_for("Player 1"), fd.RECONNAISSANCE)
    checks.eq("...and therefore the mission",
              pm.mission_for(army_lists.force_disposition_for("Player 1")).name,
              "Reconnaissance Sweep")
finally:
    config.PLAYER1_ARMY, config.PLAYER2_ARMY = was1, was2


# ============================================ 7. the tile shows it
print("--- 7. the army selection tile ---")

from game.ui import army_select  # noqa: E402

for entry in army_lists.ARMY_LISTS:
    summary = army_select.force_disposition_summary(entry)
    checks.true(f"{entry.name}'s tile line names the disposition",
                fd.label(entry.force_disposition) in summary)
    checks.true(f"...and the mission it brings",
                pm.mission_for(entry.force_disposition).name in summary)

SELECT_SRC = open("game/ui/army_select.py", encoding="utf-8").read()
# Counting the NAME was the first version of this and it was wrong twice over:
# it counted a mention inside _header_height()'s docstring, and a name count
# cannot tell a call from a definition anyway. This repo has a recorded case of
# exactly that guard staying green after the real call site was deleted. So:
# one definition, and each consumer checked by its own call expression.
checks.eq("there is exactly ONE definition",
          SELECT_SRC.count("def force_disposition_summary("), 1)
checks.true("the tile draws it",
            "self.font.render(force_disposition_summary(entry), True, TEXT_COLOR)"
            in SELECT_SRC)
checks.true("the header note draws it too, so the two cannot disagree",
            "{force_disposition_summary(entry)}" in SELECT_SRC)
# The header height is a LINE COUNT and the tile now draws four header lines.
# A fifth line without moving this is how the header eats the portrait grid.
checks.true("_header_height() budgets four header lines",
            "4 * self.font.get_height() + 26" in SELECT_SRC)


checks.finish()
