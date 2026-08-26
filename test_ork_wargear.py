"""The three wargear items whose rules arrived after their datasheets:
Battlewagon's Zzap gun (a dice-rolled Strength), the Warboss's Attack Squig,
and Flash Gitz' Ammo Runt.

Run: python test_ork_wargear.py

Built on testkit.py (see its docstring for the headless-harness traps).
"""

from testkit import (
    Checks, DecisionManager, Log, build, options_of, pick_option, script,
    shooting_scene,
)

from game import ammo_runt as ar
from game.dice_notation import describe as describe_dice
from game.factions.orks import (
    BATTLEWAGON, BATTLEWAGON_ADD_BIG_SHOOTAS, BATTLEWAGON_ADD_ZZAP_GUN, BATTLEWAGON_ARD_CASE,
    BOYZ, FLASH_GITZ, FLASH_GITZ_AMMO_RUNT, WARBOSS, WARBOSS_ADD_ATTACK_SQUIG,
)
from game.factions.tau_empire import DEVILFISH, STRIKE_TEAM
from game.weapons import AttackSquigProfile, ZzapGunProfile

c = Checks("Ork wargear")

BW_CHOICES = {"Battlewagon": {BATTLEWAGON_ADD_BIG_SHOOTAS: 1, BATTLEWAGON_ADD_ZZAP_GUN: 1}}
BW_GEAR = {"Battlewagon": [BATTLEWAGON_ARD_CASE]}

# ---------------------------------------------------------------------------
# 1. Zzap gun: the profile
# ---------------------------------------------------------------------------

zzap = ZzapGunProfile()
c.eq("range", zzap.range_in, 36)
c.eq("attacks", zzap.attacks, 1)
c.eq("AP", zzap.ap, -3)
c.eq("damage", zzap.damage, 5)
c.eq("anti-vehicle 4+", zzap.anti, (("VEHICLE", 4),))
c.eq("needs no BS override (matches the Battlewagon's 5+)", zzap.ballistic_skill, None)
c.true("Strength is a dice notation, not a fixed number", zzap.strength_notation is not None)
c.eq("...printed as D6+6", describe_dice(zzap.strength_notation), "D6+6")
c.eq("...over sides 6", zzap.strength_notation.sides, 6)
c.eq("...plus 6", zzap.strength_notation.bonus, 6)
c.true("the fixed `strength` is only a placeholder, inside D6+6's real range",
       7 <= zzap.strength <= 12)

wagon = build(BATTLEWAGON, name="Battlewagon", gear=BW_GEAR, choices=BW_CHOICES)
c.eq("the Battlewagon carries it", sorted(w.name for w in wagon.models[0].weapons),
     ["Big Shoota"] * 4 + ["Tracks and Wheels", "Zzap Gun"])
c.eq("and it is still 160 points (both additions are free)", wagon.points, 160)


# ---------------------------------------------------------------------------
# 2. Zzap gun: the Strength is really rolled, END TO END
# ---------------------------------------------------------------------------

def fire_zzap(strength_die, hit=6, wound=4, target_sheet=DEVILFISH):
    """One Zzap gun shot through the real controller. `strength_die` is what
    the D6 comes up as, so the resolved Strength is that + 6."""
    scene = shooting_scene(BATTLEWAGON, target_sheet, gap=10.0,
                           attacker_choices=BW_CHOICES)
    sc = scene["shooting"]
    sc.start_shooting(scene["attacker"])
    sc.choose_target_squad(scene["target"])
    key = next(k for k, *rest in sc.weapon_eligibility() if "Zzap" in str(rest[0]))
    script(hit)                       # the hit roll
    sc.choose_weapon(key)
    sc.dice_manager.acknowledge()
    script(strength_die)              # then the Strength roll
    sc.on_dice_acknowledged()
    strength_step = sc.pending_step
    sc.dice_manager.acknowledge()
    script(wound)                     # then the wound roll
    sc.on_dice_acknowledged()
    # ...and acknowledge THAT too, or the wound line is never logged.
    sc.dice_manager.acknowledge()
    sc.on_dice_acknowledged()
    return scene, strength_step


scene, step = fire_zzap(strength_die=3)
c.eq("a Strength step really happens, before the wound roll", step, "strength")
c.true("...and it is a visible dice roll",
       any("strength" in label.lower() for label, _ in scene["dice"].rolled))
c.true("...logged with the resolved value", scene["log"].has("Strength 9"))

# The whole point: the rolled value, not the placeholder, decides the wound
# threshold. The Devilfish is T9, so S7 needs a 5+ and S12 a 3+ - a wound
# roll of exactly 3 separates them completely. Same hit die, same wound die;
# only the Strength differs.
#
# 3 rather than the more obvious 4: this weapon's own [ANTI-VEHICLE 4+]
# makes an unmodified 4 a CRITICAL wound against a VEHICLE regardless of
# Strength, which would mask exactly the difference under test. Checked the
# hard way - the first version of this used 4 and passed for the wrong
# reason.
def wounds_from_log(scene):
    # A regex, not a split: the controller prefixes its lines with the
    # player name ("Player 2: Zzap Gun wound roll [4]: 0 wound(s) ..."), so
    # splitting on the first ": " lands in the wrong place.
    import re
    match = re.search(r"(\d+) wound\(s\)", scene["log"].find("wound roll"))
    return int(match.group(1)) if match else None


weak, _ = fire_zzap(strength_die=1, wound=3)
strong, _ = fire_zzap(strength_die=6, wound=3)
c.true("both runs reached the wound step",
       weak["log"].has("wound roll") and strong["log"].has("wound roll"))
c.eq("S7 vs T9 (needs 5+): a wound roll of 3 fails", wounds_from_log(weak), 0)
c.eq("S12 vs T9 (needs 3+): the same 3 wounds", wounds_from_log(strong), 1)
# And the masking effect itself, since it is worth pinning down: a 4 wounds
# either way, because [ANTI-VEHICLE 4+] makes it a critical wound.
c.eq("a 4 wounds even at S7, via [ANTI-VEHICLE 4+]",
     wounds_from_log(fire_zzap(strength_die=1, wound=4)[0]), 1)
c.true("...and the two rolled different Strengths",
       weak["log"].has("Strength 7") and strong["log"].has("Strength 12"))

# A weapon WITHOUT a dice Strength must not gain a Strength step.
plain = shooting_scene(BATTLEWAGON, DEVILFISH, gap=10.0, attacker_choices=BW_CHOICES)
sc = plain["shooting"]
sc.start_shooting(plain["attacker"])
sc.choose_target_squad(plain["target"])
big_key = next(k for k, *rest in sc.weapon_eligibility() if "Big Shoota" in str(rest[0]))
script(*([6] * 20))
sc.choose_weapon(big_key)
sc.dice_manager.acknowledge()
sc.on_dice_acknowledged()
c.eq("a Big Shoota goes straight to the wound roll", sc.pending_step, "wound")


# ---------------------------------------------------------------------------
# 3. Attack Squig
# ---------------------------------------------------------------------------

squig = AttackSquigProfile()
c.eq("melee", squig.weapon_type, "melee")
c.eq("attacks", squig.attacks, 2)
c.eq("strength", squig.strength, 4)
c.eq("AP", squig.ap, 0)
c.eq("damage", squig.damage, 1)
c.eq("has [EXTRA ATTACKS]", squig.extra_attacks, True)
c.eq("overrides WS down to 4+ (the Warboss himself is 2+)", squig.weapon_skill, "4+")

boss = build(WARBOSS, name="Warboss", choices={"Warboss": {WARBOSS_ADD_ATTACK_SQUIG: 1}})
c.eq("the Warboss carries it alongside everything else",
     sorted(w.name for w in boss.models[0].weapons),
     ["Attack Squig", "Big Choppa", "Kombi-weapon", "Twin Slugga"])
c.eq("and it is free", boss.points, build(WARBOSS, name="W2").points)
c.eq("the Warboss's own WS is unchanged", boss.models[0].profile.weapon_skill, "2+")
# [EXTRA ATTACKS] (24.11) is what stops it competing with the Big Choppa
# under rule 04.01 - the reason it can be a pure addition at all.
melee = [w for w in boss.models[0].weapons if w.weapon_type == "melee"]
c.eq("only one of its melee weapons competes under 04.01",
     sum(1 for w in melee if not w.extra_attacks), 1)


# ---------------------------------------------------------------------------
# 4. Ammo Runt
# ---------------------------------------------------------------------------

AR_GEAR = {"Kaptin": [FLASH_GITZ_AMMO_RUNT]}
gitz = build(FLASH_GITZ, name="Flash Gitz", composition_index=1, gear=AR_GEAR)
c.eq("exactly one model carries the Ammo Runt", sum(1 for m in gitz.models if m.ammo_runt), 1)
c.eq("it is free (no published price to charge)", gitz.points,
     build(FLASH_GITZ, name="FG2", composition_index=1).points)
c.eq("unit predicate", ar.unit_has_ammo_runt(gitz), True)
c.eq("a unit without one", ar.unit_has_ammo_runt(build(FLASH_GITZ, name="FG3", composition_index=1)), False)
c.eq("...and a unit of something else entirely", ar.unit_has_ammo_runt(build(BOYZ, name="B")), False)

dead = build(FLASH_GITZ, name="FG4", composition_index=1, gear=AR_GEAR)
for m in dead.models:
    m.current_wounds = 0
c.eq("the wargear dies with its bearer (19.04)", ar.unit_has_ammo_runt(dead), False)

dm = DecisionManager()
log = Log()
ctrl = ar.AmmoRuntController(decision_manager=dm, game_log=log)
target = build(FLASH_GITZ, name="Gitz A", composition_index=1, gear=AR_GEAR)

c.eq("offered for a unit that has one", ctrl.can_use(target), True)
c.eq("not offered for a unit that has not", ctrl.can_use(build(BOYZ, name="B2")), False)
c.true("the offer is raised", ctrl.offer(target))
labels = options_of(dm)
c.eq("two options - use it or keep it", len(labels), 2)
c.true("declining is possible - it is a once-per-battle resource",
       any("save it" in l.lower() for l in labels))
c.eq("nothing is granted until a choice is made", target.ammo_runt_active, False)

pick_option(dm, "Save it")
c.eq("declining grants nothing", target.ammo_runt_active, False)
c.eq("...and does NOT spend the once-per-battle use", ctrl.has_been_used(target), False)

ctrl.offer(target)
pick_option(dm, "Use the")
c.eq("using it grants the ability", target.ammo_runt_active, True)
c.eq("...spends the once-per-battle use", ctrl.has_been_used(target), True)
c.true("...and is logged", log.has("Ammo Runt"))
c.eq("a second offer is refused (once per battle)", ctrl.can_use(target), False)

ctrl.reset_phase([target])
c.eq('"until the end of the phase" is cleared', target.ammo_runt_active, False)
c.eq("but the once-per-battle record is NOT", ctrl.has_been_used(target), True)
c.eq("...so it still cannot be used again", ctrl.can_use(target), False)

# The AI answers this one itself, at the first opportunity (user: "die ki soll
# das bei der ersten gelegenheit deterministisch benutzen und gut").
auto_dm = DecisionManager()
auto_log = Log()
auto = ar.AmmoRuntController(decision_manager=auto_dm, game_log=auto_log,
                             auto_players=("Player 2",))
ai_gitz = build(FLASH_GITZ, "Player 2", name="Gitz AI", composition_index=1, gear=AR_GEAR)
c.true("the AI's offer resolves itself", auto.offer(ai_gitz))
c.eq("...without ever asking", auto_dm.is_pending, False)
c.eq("...and the ability is up immediately", ai_gitz.ammo_runt_active, True)
c.eq("...spending the once-per-battle use", auto.has_been_used(ai_gitz), True)
c.true("...and it is logged", auto_log.has("Ammo Runt"))

# A/B: the SAME squad through a controller without auto_players asks instead -
# so the block above proves auto_players, not something else about the scene.
probe_dm = DecisionManager()
probe = ar.AmmoRuntController(decision_manager=probe_dm, game_log=Log())
probe_gitz = build(FLASH_GITZ, "Player 2", name="Gitz AB", composition_index=1, gear=AR_GEAR)
probe.offer(probe_gitz)
c.eq("without auto_players the same squad is asked", probe_dm.is_pending, True)
c.eq("...and nothing is granted until it answers", probe_gitz.ammo_runt_active, False)

# The split: a human running Orks keeps the choice and is still asked.
human_gitz = build(FLASH_GITZ, "Player 1", name="Gitz Human", composition_index=1, gear=AR_GEAR)
auto.offer(human_gitz)
c.eq("a player outside auto_players is still asked", auto_dm.is_pending, True)
c.eq("...and nothing is granted yet", human_gitz.ammo_runt_active, False)
pick_option(auto_dm, "Save it")

# "Once per battle" is not weakened by deciding automatically.
auto.reset_phase([ai_gitz])
c.eq("the grant still expires with the phase", ai_gitz.ammo_runt_active, False)
c.eq("a later activation does NOT use it again", auto.offer(ai_gitz), False)
c.eq("...and raises no prompt either", auto_dm.is_pending, False)

# END TO END through the real activation hook: selected to shoot -> already up.
e2e = shooting_scene(FLASH_GITZ, STRIKE_TEAM, gap=10.0,
                     ammo_runt=ar.AmmoRuntController(decision_manager=DecisionManager(),
                                                     game_log=Log(),
                                                     auto_players=("Player 2",)))
e2e["attacker"].models[0].ammo_runt = True
e2e["shooting"].start_shooting(e2e["attacker"])
c.eq("start_shooting() alone puts the ability up for the AI",
     e2e["attacker"].ammo_runt_active, True)
c.eq("...before a target has even been chosen", e2e["shooting"].target_squad, None)

# The grant itself.
git = gitz.models[1]
snazz = next(w for w in git.weapons if w.name == "Snazzgun")
choppa = next(w for w in git.weapons if w.name == "Choppa")


class _Active:
    ammo_runt_active = True


class _Inactive:
    ammo_runt_active = False


boosted = ar.ammo_runt_adjusted_weapon(snazz, _Active())
c.eq("a ranged weapon gains [LETHAL HITS]", boosted.lethal_hits, True)
c.eq("the shared instance is never mutated", snazz.lethal_hits, False)
c.true("melee is untouched - the rule says ranged weapons",
       ar.ammo_runt_adjusted_weapon(choppa, _Active()) is choppa)
c.true("without the grant nothing changes",
       ar.ammo_runt_adjusted_weapon(snazz, _Inactive()) is snazz)


# END TO END: [LETHAL HITS] shows up in the real shooting pipeline.
def shoot_gitz(active):
    scene = shooting_scene(FLASH_GITZ, STRIKE_TEAM, gap=10.0)
    scene["attacker"].ammo_runt_active = active
    sc = scene["shooting"]
    sc.start_shooting(scene["attacker"])
    sc.choose_target_squad(scene["target"])
    key = next(k for k, *rest in sc.weapon_eligibility() if "Snazzgun" in str(rest[0]))
    script(*([6] * 60))  # every hit critical
    sc.choose_weapon(key)
    sc.dice_manager.acknowledge()
    sc.on_dice_acknowledged()
    return scene


with_runt = shoot_gitz(True)
without = shoot_gitz(False)
# Rule 24.23 is taken for every critical hit without asking (user: "das
# koennen wir uns sparen") - so the tell is not a prompt any more, it is
# that the critical hits skip the wound roll: with the Ammo Runt the wound
# step gets strictly fewer dice than the hits that reached it.
def wound_dice(scene):
    """The wound roll is still pending at this point (the scene stops after
    one acknowledgement), so it is read off the dice manager rather than out
    of the log - the log line only appears once the roll resolves."""
    return len(scene["dice"].pending_values or [])


c.eq("no prompt interrupts the activation any more",
     with_runt["decision"].is_pending, False)
c.true("both runs reached the wound step", wound_dice(without) > 0)
c.true("with the Ammo Runt the critical hits auto-wound instead of rolling",
       wound_dice(with_runt) < wound_dice(without))
c.eq("A/B: without it, the same all-6 hit roll rolls every hit to wound",
     without["decision"].is_pending, False)

c.finish()
