"""FORCE DISPOSITIONS - the five of them, and nothing else.

WHAT A FORCE DISPOSITION IS
---------------------------
Every detachment permits exactly ONE Force Disposition, printed on the
detachment itself (Wahapedia renders it as an icon beside the DP cost in the
detachment's own heading; see fetch_datasheet_rules.py's
heading_force_dispositions(), which transcribes it into rules/*/detachments/).
A list that fields SEVERAL detachments may pick one of the dispositions they
grant, and that pick is written down as part of the list - user: "jedes
detachment hat zugang zu einer force disposition. diese waehlt man beim listen
bau ... ist aber in der Liste festgeschrieben."

The disposition decides which PRIMARY MISSION that army plays
(game/primary_missions.py maps one to each).

WHY THIS IS ITS OWN TINY MODULE
-------------------------------
Three unrelated layers need the five names: game/factions/detachment.py (pure
DATA, which must not import the mission engine), game/army_lists.py and
game/detachments.py (the declaration and its validation), and
game/primary_missions.py (the engine). Putting the constants next to the
missions would drag the whole mission engine into the faction data files; a
module with five strings in it cannot.

THE KEYS ARE SNAKE_CASE, THE LABELS ARE THE PRINTED TEXT
--------------------------------------------------------
`from_printed()` is what pins an engine constant to the corpus in
test_force_dispositions.py, rather than a hand-kept second copy of the same
five words.
"""

TAKE_AND_HOLD = "take_and_hold"
PURGE_THE_FOE = "purge_the_foe"
RECONNAISSANCE = "reconnaissance"
PRIORITY_ASSETS = "priority_assets"
DISRUPTION = "disruption"

# In the order Wahapedia's own filter row lists them.
ALL = (TAKE_AND_HOLD, PURGE_THE_FOE, RECONNAISSANCE, PRIORITY_ASSETS, DISRUPTION)

LABELS = {
    TAKE_AND_HOLD: "Take and Hold",
    PURGE_THE_FOE: "Purge the Foe",
    RECONNAISSANCE: "Reconnaissance",
    PRIORITY_ASSETS: "Priority Assets",
    DISRUPTION: "Disruption",
}

_BY_PRINTED = {label.lower(): key for key, label in LABELS.items()}


def label(key):
    """The printed name, e.g. "Take and Hold". Unknown keys come back as
    themselves rather than raising: this is only ever used for display, and a
    tile that says "take_and_hold" is a better failure than a crash."""
    return LABELS.get(key, key)


def from_printed(text):
    """The key for a printed name, or None.

    Takes the corpus's own spelling ("Force Disposition: Priority Assets"),
    so a test can walk rules/*/detachments/*.md and compare what the engine
    holds against what GW printed, instead of comparing two hand-typed lists.
    """
    return _BY_PRINTED.get((text or "").strip().lower())


def is_valid(key):
    return key in LABELS
