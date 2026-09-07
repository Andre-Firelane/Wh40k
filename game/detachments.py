"""Which detachments each army list fields, and the one place that writes it.

A DETACHMENT BELONGS TO THE LIST
--------------------------------
It is part of how an army was written down, not a choice made at the table:
you cannot swap detachment before a game, so there is no selection screen. One
was built and taken back out again - the mistake was treating "which list" and
"which detachment" as two questions asked at two moments, when the second is
simply part of the first's answer.

What remains true, and is why this module exists at all, is that a detachment
cannot be DERIVED from the units: a Crisis suit looks identical in every
detachment. So the list declares it, and apply_to_config() writes that
declaration into the config constants the rules read.

SEVERAL AT ONCE, PAID FOR IN DETACHMENT POINTS
-----------------------------------------------
An army may field more than one. Each costs its printed DP (the "2DP" on its
Wahapedia heading, recorded on the Detachment), and they come out of one
budget - so Kauyon (2) plus Advanced Acquisition Cadre (1) is a legal pair
while Mont'ka (3) plus Kauyon (2) is not.

DETACHMENT_POINT_BUDGET IS AN ASSUMPTION, AND MARKED AS ONE
------------------------------------------------------------
The per-detachment COSTS are transcribed (they are printed on each detachment).
The BUDGET is not: no page fetched into rules/ states one - "Detachment Points"
appears nowhere in the corpus, which holds datasheets, army rules and
detachments but no core rules. 3 is the user's call, chosen because it is what
the priciest single detachments cost and what their own example (Kauyon +
Advanced Acquisition Cadre) adds up to. Replace it with the printed number when
that turns up; nothing else has to change.

THE TAG RULE IS SEPARATE, AND IS TRANSCRIBED
---------------------------------------------
"This detachment has the BATTLESUIT tag and cannot be taken with another
BATTLESUIT detachment" is printed, and it is not about points: two 1 DP
detachments sharing a tag are illegal together however much budget is left.
"""

from game import config, force_dispositions
from game.factions.faction import FACTIONS

# See the module docstring: an ASSUMPTION, not a transcription.
DETACHMENT_POINT_BUDGET = 3


def faction_for_army(army_key):
    """The Faction object behind an army-list key, or None."""
    from game import army_lists
    entry = army_lists.get(army_key)
    return FACTIONS.get(entry.faction_keyword)


def available(army_key):
    """Every detachment that army's faction models, in registration order.

    Not "what it may choose between" any more - nothing chooses. This is what
    a rules reference or a future army-building step would offer."""
    faction = faction_for_army(army_key)
    return list(faction.detachments.values()) if faction is not None else []


def get(army_key, name):
    """One named detachment of that army's faction, or None."""
    for detachment in available(army_key):
        if detachment.name == name:
            return detachment
    return None


def for_army(army_key):
    """The Detachment objects this list actually fields.

    A name the faction does not know is DROPPED rather than guessed at, and
    validate() reports it - a typo in ARMY_LISTS should surface as a named
    problem, not as a detachment rule that silently never fires."""
    from game import army_lists
    entry = army_lists.get(army_key)
    found = []
    for name in entry.detachments:
        detachment = get(army_key, name)
        if detachment is not None:
            found.append(detachment)
    return found


def names_for(army_key):
    return [d.name for d in for_army(army_key)]


def points_for(army_key):
    """What this list spends on detachments, in DP."""
    return sum(d.points for d in for_army(army_key))


def validate(army_key):
    """Every reason this list's detachments are not a legal set, as a list of
    strings - empty means legal.

    The same shape as game/attached_units.py's can_attach(): a caller can show
    the reason rather than a bare False.
    """
    from game import army_lists
    entry = army_lists.get(army_key)
    problems = []

    known = {d.name for d in available(army_key)}
    for name in entry.detachments:
        if name not in known:
            problems.append(
                f'"{name}" is not a detachment {entry.name} has '
                f"(known: {', '.join(sorted(known))}).")
    if not entry.detachments:
        problems.append(f"{entry.name} fields no detachment at all.")

    spent = points_for(army_key)
    if spent > DETACHMENT_POINT_BUDGET:
        problems.append(
            f"{entry.name} spends {spent} Detachment Points, over the "
            f"{DETACHMENT_POINT_BUDGET} available.")

    # "cannot be taken with another <TAG> detachment" - printed, and separate
    # from the points: two 1 DP detachments sharing a tag are still illegal.
    by_tag = {}
    for detachment in for_army(army_key):
        if detachment.tag:
            by_tag.setdefault(detachment.tag, []).append(detachment.name)
    for tag, names in sorted(by_tag.items()):
        if len(names) > 1:
            problems.append(
                f"{entry.name} takes {len(names)} {tag} detachments "
                f"({', '.join(sorted(names))}); only one is allowed.")

    # The list's declared FORCE DISPOSITION has to be one its detachments
    # permit. Each detachment allows exactly one, and a list fielding several
    # picks among them - so this check IS the "you may choose one" rule, and
    # for a single-detachment list it is simply "the one it grants".
    #
    # A list that declares nothing is not a problem here: the Primary Mission
    # system is per-player (config.PRIMARY_MISSION_CARD_PLAYERS), and a list
    # nobody plays a Primary card with needs no disposition. What is refused is
    # declaring one the detachments do not grant.
    declared = getattr(entry, "force_disposition", None)
    if declared is not None:
        granted = {d.force_disposition for d in for_army(army_key)
                   if d.force_disposition}
        if declared not in granted:
            problems.append(
                f"{entry.name} declares the {force_dispositions.label(declared)} "
                f"Force Disposition, which none of its detachments permits "
                f"(they permit: "
                f"{', '.join(sorted(force_dispositions.label(g) for g in granted)) or 'none'}).")
    return problems


def all_settings():
    """Every config constant any registered detachment uses.

    Collected from the faction data rather than listed here, so a detachment
    added to a faction module cannot be forgotten by the writer below - which
    would leave its setting holding whatever the previous battle wrote."""
    names = []
    for faction in FACTIONS.values():
        for detachment in faction.detachments.values():
            if detachment.setting and detachment.setting not in names:
                names.append(detachment.setting)
    return names


def apply_to_config(armies, config_module=None):
    """Write who fields which detachments into config, where the rules read it.

    `armies` is {player -> army key}; the detachments come from the lists.
    Written FROM SCRATCH so switching list really takes the old detachments
    away - adding to them instead is how a player ends up under two detachment
    rules at once, and that is pinned in both directions by the tests.
    """
    cfg = config_module if config_module is not None else config
    for setting in all_settings():
        setattr(cfg, setting, ())

    per_setting = {}
    for player, key in sorted(armies.items()):
        for detachment in for_army(key):
            if not detachment.setting:
                # War Horde: the documented "nothing to declare" case, because
                # its rule gates on the ORKS keyword.
                continue
            per_setting.setdefault(detachment.setting, []).append(player)
    for setting, players in per_setting.items():
        setattr(cfg, setting, tuple(players))
