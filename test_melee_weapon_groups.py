"""A model with two melee weapons keeps its rule-04.01 choice.

User report: "beispiel warpspider. alle close combat weapons des squads werden
gruppiert. wenn ich jetzt zuerst auf den knopf close combat weapon klicke,
handelt jede einheit die angriffe ab. auch der exarch, der aber noch ein power
blade array hat. da ich aber nur mit einer waffe zuschlagen kann, kann ich
danach nicht mehr mit dem powerblade array zuschlagen. das ist sehr aergerlich.
der einfachste fix waere. characters, leader und rest des squads zu trennen bei
den auswahllisten der nahkampfwaffen. oder gruppen zu erstellen mit waffen
loadouts und diese dann einzeln abzuhandeln."

Reproduced before changing anything: the Exarch shared the squad's "Close
Combat Weapon" group (identical WS/S/AP/D), so the squad's own button swung his
close combat weapon too and 04.01 locked the Array out. The choice was never
offered - it was made for him by a button about somebody else's weapon.

The second of the user's two suggestions is the one implemented, in its minimal
form: a model that has a choice gets its OWN groups. The first (split off
characters and leaders) would not have covered this case - an Aspect Exarch is
deliberately not a CHARACTER in this engine, and is not squad_leader either.

A second, smaller bug fell out of the same report: once every model of a group
was locked out, the group was still listed, labelled with _group_label()'s
empty-list placeholder - a button reading just "Weapon" that did nothing.
"""
import testkit as tk
from game.factions import aeldari as ae
from game.factions import orks as ork
from game.fight import _melee_attack_groups, _melee_choice_owner, _melee_group_label
from game.weapons import MELEE

c = tk.Checks("melee weapon groups - one model, one choice")


def section(title):
    print(f"\n--- {title} ---")


ARRAY = {"Warp Spider Exarch": {ae.WARP_SPIDER_TO_POWERBLADE_ARRAY: 1}}


def spiders(choices=None):
    return tk.fight_scene(ae.WARP_SPIDERS, ae.DIRE_AVENGERS, attacker_owner="Player 1",
                          attacker_choices=choices)


def swing(sc, label):
    """Fight with the group labelled EXACTLY `label`, to a standstill.
    Returns the labels still on offer afterwards.

    Exact, not a substring: "Close Combat Weapon" is a prefix of "Close Combat
    Weapon (Warp Spider Exarch)", and a substring match picked the Exarch's
    group when the test meant the squad's - which is the very confusion the
    label was added to prevent."""
    offered = sc["fight"].weapon_eligibility()
    option = next((o for o in offered if o[1] == label), None)
    if option is None:
        c.eq(f"swing({label!r}) found its group", [o[1] for o in offered], label)
        return []
    tk.script(*([4] * 60), default=4)
    sc["fight"].choose_weapon(option[0])
    for _ in range(16):
        if sc["dice"].is_pending:
            sc["dice"].acknowledge()
            sc["fight"].on_dice_acknowledged()
        elif sc["decision"].is_pending:
            tk.pick_option(sc["decision"], "Keep")
        else:
            break
    if sc["fight"].state != "choosing_weapon":
        return []
    return [o[1] for o in sc["fight"].weapon_eligibility()]


def started(choices=None):
    sc = spiders(choices)
    sc["fight"].select_to_fight(sc["attacker"])
    if sc["fight"].state == "choosing_target":
        sc["fight"].choose_target_squad(sc["target"])
    return sc


# ------------------------------------------------ 1. who has a choice at all

section("1. _melee_choice_owner()")

sq = tk.build(ae.WARP_SPIDERS, "Player 1", name="1 Warp Spiders 1", choices=ARRAY)
exarch, spider = sq.models[0], sq.models[1]
exarch_melee = [w for w in exarch.weapons if w.weapon_type == MELEE]
c.eq("the Exarch really does carry two melee weapons",
     sorted(w.name for w in exarch_melee), ["Close Combat Weapon", "Powerblade Array"])
c.eq("a plain Warp Spider carries one",
     len([w for w in spider.weapons if w.weapon_type == MELEE]), 1)

for weapon in exarch_melee:
    c.eq(f"the Exarch owns his own {weapon.name} group",
         _melee_choice_owner(exarch, weapon), exarch.id)
c.eq("a model with one weapon owns nothing",
     _melee_choice_owner(spider, spider.weapons[-1]), None)

# The Exarch is neither a CHARACTER nor the squad_leader, which is exactly why
# the user's first suggestion would have missed him.
c.eq("the Exarch is not a CHARACTER", getattr(exarch.profile, "character", False), False)
c.eq("...nor flagged as the squad leader", bool(getattr(exarch, "squad_leader", False)), False)

# [EXTRA ATTACKS] weapons take no choice away (24.11), so they never get an
# owner - splitting them off would only fragment the list.
extra = type("W", (), {"weapon_type": MELEE, "extra_attacks": True, "name": "X"})()
c.eq("an [EXTRA ATTACKS] weapon owns nothing", _melee_choice_owner(exarch, extra), None)


# -------------------------------------------------------- 2. the grouping

section("2. the groups that come out")

groups = _melee_attack_groups(sq)
by_label = {_melee_group_label(pairs): [m.profile.name for m, _w in pairs]
            for pairs in groups.values()}
c.eq("three groups, not two", len(groups), 3)
c.eq("the four plain spiders share one",
     sorted(by_label.get("Close Combat Weapon", [])), ["Warp Spider"] * 4)
c.eq("the Exarch's close combat weapon is his own",
     by_label.get("Close Combat Weapon (Warp Spider Exarch)"), ["Warp Spider Exarch"])
c.eq("...and so is his Array",
     by_label.get("Powerblade Array (Warp Spider Exarch)"), ["Warp Spider Exarch"])
# The label matters as much as the split: two buttons both reading "Close
# Combat Weapon" would be worse than the bug.
c.eq("no two groups share a label", len(by_label), 3)

# A squad with no multi-weapon model is untouched - this must not fragment
# every unit in the game.
plain = tk.build(ae.WARP_SPIDERS, "Player 1", name="1 Warp Spiders 2")
plain_groups = _melee_attack_groups(plain)
c.eq("a squad where nobody has a choice keeps ONE group", len(plain_groups), 1)
c.eq("...holding all five models", len(next(iter(plain_groups.values()))), 5)
c.eq("...and labelled plainly",
     _melee_group_label(next(iter(plain_groups.values()))), "Close Combat Weapon")


# ------------------------------------------------- 3. the reported sequence

section("3. the reported sequence, end to end")

sc = started(ARRAY)
offered = [o[1] for o in sc["fight"].weapon_eligibility()]
c.eq("three buttons are offered", len(offered), 3)
c.true("...one of them the Exarch's Array", any("Powerblade Array" in l for l in offered))

# THE REPORT: click the squad's own close combat weapon first.
left = swing(sc, "Close Combat Weapon")
c.true("after the squad swings, the Exarch's Array is STILL there",
       any("Powerblade Array" in l for l in left))
c.true("...and so is his own close combat weapon",
       "Close Combat Weapon (Warp Spider Exarch)" in left)
c.eq("...while the squad's group is spent", "Close Combat Weapon" in left, False)
# The ghost button is gone: a group with every model locked out is not listed.
c.eq("no placeholder 'Weapon' button is left", [l for l in left if l == "Weapon"], [])

# And 04.01 still bites where it should: once the Exarch HAS chosen, his other
# melee weapon is locked. The fix restores the choice, it does not remove the
# rule.
sc2 = started(ARRAY)
left2 = swing(sc2, "Powerblade Array (Warp Spider Exarch)")
c.eq("the Exarch's own close combat weapon is locked after he swings",
     "Close Combat Weapon (Warp Spider Exarch)" in left2, False)
c.true("...and the squad's own group is untouched", "Close Combat Weapon" in left2)
# ...and the emptied group is not listed under _group_label()'s placeholder
# either. This is the second, smaller bug from the same report: a group whose
# every model is locked out used to stay on the list as a button reading just
# "Weapon", which did nothing when clicked.
c.eq("the emptied group leaves no placeholder button", [l for l in left2 if l == "Weapon"], [])
c.eq("...and exactly one button is left", len(left2), 1)

# The order does not matter - the whole point is that neither click steals the
# other's choice.
sc3 = started(ARRAY)
after_exarch = swing(sc3, "Powerblade Array (Warp Spider Exarch)")
c.true("Exarch first: the squad can still swing", "Close Combat Weapon" in after_exarch)


# --------------------------------------------- 4. it is not an Aeldari quirk

section("4. the other factions")

# Measured across all 72 datasheets: 14 model loadouts carry more than one
# selectable melee weapon. An Ork Boss Nob with a Power Klaw is the same shape
# in another faction, and it is a squad LEADER rather than an Exarch - so the
# split has to key on the loadout, not on any one role flag.
bikers = tk.build(ork.WARBIKERS, "Player 2", name="2 Warbikers 1",
                  choices={"Boss Nob on Warbike": {ork.WARBIKERS_ADD_POWER_KLAW: 1}})
nob = next(m for m in bikers.models if "Nob" in m.profile.name)
nob_melee = sorted(w.name for w in nob.weapons if w.weapon_type == MELEE)
c.eq("the Boss Nob carries two melee weapons", nob_melee, ["Close Combat Weapon", "Power Klaw"])
biker_groups = _melee_attack_groups(bikers)
labels = {_melee_group_label(pairs) for pairs in biker_groups.values()}
c.true("his Power Klaw is its own group", any("Power Klaw" in l for l in labels))
c.true("...and his close combat weapon is separated from the squad's",
       any(l.startswith("Close Combat Weapon (") for l in labels))
c.true("...while the plain bikers keep a shared one", "Close Combat Weapon" in labels)


c.finish()
