"""Rule 04.01.03: a weapon with more than one profile.

PRINTED TEXT: "In the Select Weapons step (04.01), if a selected weapon has
more than one profile, then the controlling player must also select one of
those profiles. The selected profile is then used in the Resolve Attacks step
(04.03). Some of these profiles are known as Hunter profiles. Hunter profiles
can only target units with the specified keywords. Note that if a unit is
equipped with more than one such weapon, a different profile can be selected
for each model within that unit."

THE CHAIN. A model carries ONE instance - the first printed profile - and
WeaponProfile.overcharge_profile links it to the next profile's class, which
may link on again (Kombi-weapon - Shoota -> Kill Shot -> Point Blank). That
field predates this module under the name of its first carrier (an Ion
weapon's Overcharge) and was already the generic "alternate mode" hook: the
Pathfinder grenade launcher, the Visarch's three stances and the Nightbringer's
scythe all use it, and verify_rules_vs_engine.py's firing_modes() already walks
it. So there is ONE mechanism and this is its ONE reader, rather than a second
`profiles` tuple beside it that the two controllers could read differently.

WHAT THE 2026-09 ORK CODEX CHANGED. Until then shooting.py read exactly one
link (a Standard/Overcharge toggle) and fight.py read none - so the Visarch's
stances could not be selected in a fight at all, and nothing could express a
profile that differs from its sibling in RANGE or in [CLOSE-QUARTERS]: Meganobz'
Kustom Shoota is 18" "Aimed" and 6" [CLOSE-QUARTERS] "Point Blank", and only the
second may shoot while engaged. Every eligibility question - which shooting
types the unit may pick, which weapons a type allows, 24.07's side lock, reach,
the 10.02 snapshot - now asks about each PROFILE, and a weapon is offered if
any of its profiles is.

STABLE INSTANCES. The alternates are built once per carried instance and cached
on it, tagged with the carried instance's id() (`overcharge_of_id`, which rule
24.26's [ONE SHOT] ledger already keys on). Stable ids are what let the 10.02
reach snapshot hold an answer for a profile at all; a fresh copy per call would
miss it every time.

PER MODEL VS PER GROUP. The printed note lets each model pick its own profile.
The group flow selects one profile for the group - every model firing that
weapon uses it - and Split Fire, which assigns each model and weapon on its own,
is where a player picks per model. Named here rather than discovered later.
"""

_CACHE_ATTRIBUTE = "_weapon_profiles_chain"


def profile_classes(weapon):
    """[type(weapon), next profile class, ...] - the chain by CLASS, built
    without instantiating anything (cheap enough for a grouping key)."""
    first = type(weapon)
    chain = [first]
    cls = getattr(weapon, "overcharge_profile", None)
    while cls is not None and cls not in chain:
        chain.append(cls)
        cls = getattr(cls, "overcharge_profile", None)
    return chain


def profiles(weapon):
    """[weapon, alternate instance, ...]. Index 0 is always `weapon` itself.

    Pass the CARRIED instance (the one in model.weapons). A shallow copy made
    by an adjuster inherits the cache attribute of its original, whose first
    entry is not the copy - that case is answered freshly and not stored."""
    cached = getattr(weapon, _CACHE_ATTRIBUTE, None)
    if cached is not None and cached[0] is weapon:
        return cached
    chain = [weapon]
    for cls in profile_classes(weapon)[1:]:
        instance = cls()
        instance.overcharge_of_id = id(weapon)
        chain.append(instance)
    if cached is None:
        try:
            setattr(weapon, _CACHE_ATTRIBUTE, chain)
        except AttributeError:
            pass
    return chain


def has_alternates(weapon):
    return getattr(weapon, "overcharge_profile", None) is not None


def chain_key(weapon):
    """Part of both controllers' rule-04.03 grouping key: () for a weapon with
    one profile, so no existing group splits.

    Needed because two weapons can share every characteristic of their FIRST
    profile and differ in the rest - a Boy's Shoota and his Nob's Kombi-skorcha
    both print 18" A2 S4 AP0 D1. Grouped together, choosing the Skorcha profile
    would have to drop the Shootas from the volley, and the group's key is gone
    once it has fired, so those Shootas would never fire at all."""
    return tuple(cls.__name__ for cls in profile_classes(weapon)[1:])


def hunter_allows(profile, target_squad):
    """Rule 04.01.03's Hunter restriction. A profile without one allows any
    target; a Hunter profile with no target in hand allows none."""
    condition = getattr(profile, "hunter_keywords", None)
    if condition is None:
        return True
    return condition.matches(target_squad)


def is_hunter(profile):
    return getattr(profile, "hunter_keywords", None) is not None
