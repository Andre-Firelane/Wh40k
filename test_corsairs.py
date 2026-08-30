"""The Anhrathe: Corsairs, Kharseth, Prince Yriel and the Starfangs (Etappe 6).

SIX DATASHEETS, ONE SUB-FACTION. They share a foot chassis, a CORE Scouts 7"
line, and a wargear vocabulary; what they do not share is any state, so this
suite is mostly about each ability landing on the right seam.

WHERE THIS MEASURES, AND WHY THERE
----------------------------------
  * Fury of the Void is measured on the WOUND THRESHOLD, not on a modifier
    list: +1 Strength is a characteristic change, and its whole point is that
    it can cross a Toughness boundary. A test that only checked "the mark is
    set" would pass with the grant wired into the wrong step.
  * Reavers of the Void is measured on BOTH sides of its condition, because its
    two halves are alternatives - the 1s when the target is in the open, the
    whole-roll choice when it stands on an objective.
  * Piratical Hero is measured at BOTH its seams, since it is one ability that
    grants a keyword AND a modifier and they live in different places.
"""
import testkit as tk
from testkit import Checks

from game import (attached_units, corsair_abilities, fury_of_the_void,
                  hallucinogen_grenades, invulnerable_save, prince_of_corsairs,
                  raid_and_run, reavers_of_the_void, reroll_scope, sprites)
from game.factions import aeldari as ae
from game.factions.aeldari_points import AELDARI_POINTS
from game.movement import MovementController
from game.squad import squad_has_stealth
from game.units import (
    CorsairProfile, CorsairSkyreaverProfile, CorsairVoidreaverProfile,
    CorsairVoidscarredProfile, KharsethProfile, PrinceYrielProfile,
    StarfangProfile, VyperProfile,
)
from game.weapons import (
    BlasterProfile, CorsairBladeProfile, DreadOfTheDeepVoidProfile,
    ExecutionerProfile, NeuroDisruptorProfile, PowerSwordProfile,
    ShredderProfile, ShurikenRifleProfile, SpearOfTwilightProfile,
    VoidscarredExecutionerProfile, WaySeekerWitchStaffProfile, WitchStaffProfile,
)

checks = Checks("Anhrathe")

SHEETS = [ae.CORSAIR_VOIDREAVERS, ae.CORSAIR_VOIDSCARRED, ae.CORSAIR_SKYREAVERS,
          ae.STARFANGS, ae.KHARSETH, ae.PRINCE_YRIEL]


def build(sheet, owner="Player 1", n=1, **kw):
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


# --- 1. the Corsair chassis -------------------------------------------------
print("--- 1. the Corsair chassis ---")

base = CorsairProfile
checks.eq('M7"/T3/Sv4+/W1/Ld7+',
          (base.movement_in, base.toughness, base.armor_save, base.wounds, base.leadership),
          (7, 3, "4+", 1, "7+"))
checks.eq("28.5 mm base", round(base.base_radius_in, 3), round(28.5 / 2 / 25.4, 3))
checks.eq('Scouts 7" as a CORE line', base.scouts, 7.0)
for profile in (CorsairVoidreaverProfile, CorsairVoidscarredProfile,
                CorsairSkyreaverProfile):
    checks.true("%s rides the chassis" % profile.name, issubclass(profile, base))
checks.eq("the Voidreavers keep OC2, the Voidscarred print OC1",
          (CorsairVoidreaverProfile.oc, CorsairVoidscarredProfile.oc), (2, 1))
checks.eq("the Skyreavers are the jump-pack variant: M12, Sv5+, OC1",
          (CorsairSkyreaverProfile.movement_in, CorsairSkyreaverProfile.armor_save,
           CorsairSkyreaverProfile.oc), (12, "5+", 1))
checks.true("...with JUMP PACK, FLY and Deep Strike",
            CorsairSkyreaverProfile.jump_pack and CorsairSkyreaverProfile.fly
            and CorsairSkyreaverProfile.deep_strike)
checks.true("every ANHRATHE datasheet here prints Scouts 7\"",
            all(p.scouts == 7.0 for p in (base, KharsethProfile, PrinceYrielProfile,
                                          StarfangProfile)))
checks.eq("the Starfangs take the Vyper's converted 105 x 70 oval",
          StarfangProfile.base_radius_in, VyperProfile.base_radius_in)
checks.true("both EPIC HEROES lead and both carry a 4+ invulnerable",
            KharsethProfile.leader and PrinceYrielProfile.leader
            and KharsethProfile.invulnerable_save == "4+"
            and PrinceYrielProfile.invulnerable_save == "4+")
checks.true("Kharseth is the PSYKER of the two",
            KharsethProfile.psyker and not PrinceYrielProfile.psyker)


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

vr, sk, vs = (build(ae.CORSAIR_VOIDREAVERS), build(ae.CORSAIR_SKYREAVERS),
              build(ae.CORSAIR_VOIDSCARRED))
checks.eq("Voidreaver loadout", sorted(w.name for w in vr.models[0].weapons),
          ["Close Combat Weapon", "Power Sword", "Shuriken Pistol"])
checks.eq("Skyreaver loadout", sorted(w.name for w in sk.models[0].weapons),
          ["Corsair Blade", "Shuriken Pistol"])
b = BlasterProfile()
checks.eq('Blaster 18"/A1/S8/AP-4', (b.range_in, b.attacks, b.strength, b.ap), (18, 1, 8, -4))
checks.eq("...D6+1 damage", (b.damage_notation.sides, b.damage_notation.bonus), (6, 1))
nd = NeuroDisruptorProfile()
checks.eq("Neuro Disruptor [ANTI-INFANTRY 2+], assault and pistol",
          (nd.anti, nd.assault, nd.pistol), (("INFANTRY", 2), True, True))
sr = ShurikenRifleProfile()
checks.eq('Shuriken Rifle 24"/[RAPID FIRE 1]', (sr.range_in, sr.rapid_fire), (24, 1))
checks.true("the Shredder is [TORRENT], which its printed N/A BS means",
            ShredderProfile().torrent)
cb = CorsairBladeProfile()
checks.eq("Corsair Blade A3/S4/AP-2/D1", (cb.attacks, cb.strength, cb.ap, cb.damage),
          (3, 4, -2, 1))
# The row that shares a NAME with an existing weapon and nothing else.
ve, ex = VoidscarredExecutionerProfile(), ExecutionerProfile()
checks.eq("the two Executioners share only their printed name",
          (ve.name, ex.name), ("Executioner", "Executioner"))
checks.true("...one is RANGED and the other MELEE", ve.weapon_type != ex.weapon_type)
checks.eq("...and their ANTI thresholds differ too", (ve.anti, ex.anti),
          (("INFANTRY", 2), ("INFANTRY", 3)))
checks.true("the Voidscarred one is [PSYCHIC], the melee one is not",
            ve.psychic and not ex.psychic)
checks.eq("the Way Seeker's Witch Staff is the Spiritseer's row plus WS2+",
          (WaySeekerWitchStaffProfile().weapon_skill, WitchStaffProfile.weapon_skill),
          ("2+", None))
checks.true("...and inherits everything else",
            WaySeekerWitchStaffProfile().strength == WitchStaffProfile().strength)
dd = DreadOfTheDeepVoidProfile()
checks.true("Kharseth's gun carries all five printed keywords",
            dd.anti and dd.blast and dd.hazardous and dd.ignores_cover and dd.psychic)
checks.true("Prince Yriel's Spear of Twilight is [LANCE]", SpearOfTwilightProfile().lance)


# --- 3. wargear, composition and points -------------------------------------
print("--- 3. wargear, composition and points ---")

felarch = build(ae.CORSAIR_VOIDREAVERS, n=2,
                choices={"Voidreaver Felarch": {ae.VOIDREAVER_PISTOL_TO_NEURO: 1}},
                gear={"Voidreaver Felarch": [ae.VOIDREAVER_MISTSHIELD]})
checks.true("the Felarch's pistol becomes a neuro disruptor",
            "Neuro Disruptor" in [w.name for w in felarch.models[0].weapons])
checks.eq("...and the mistshield is a 4+ invulnerable save",
          invulnerable_save.effective_invulnerable_save(felarch.models[0]), "4+")
checks.eq("...which the rest of the squad does NOT get - it is the BEARER's",
          invulnerable_save.effective_invulnerable_save(felarch.models[1]), "-")
heavy = build(ae.CORSAIR_VOIDREAVERS, n=3,
              choices={"Corsair Voidreaver": {ae.VOIDREAVER_TO_BLASTER: 1}})
checks.true("a Voidreaver can trade its power sword for a blaster",
            "Blaster" in [w.name for w in heavy.models[1].weapons])
sky_gun = build(ae.CORSAIR_SKYREAVERS, n=2,
                choices={"Skyreaver": {ae.SKYREAVER_TO_FUSION_GUN: 1}})
checks.eq("a Skyreaver gives up BOTH printed weapons and gets a gun plus a "
          "close combat weapon", sorted(w.name for w in sky_gun.models[1].weapons),
          ["Close Combat Weapon", "Fusion Gun", "Shuriken Pistol"])

ten = build(ae.CORSAIR_VOIDSCARRED, n=4, composition_index=1)
checks.eq("the 10-model Voidscarred build has FIVE model lines - the most of "
          "any datasheet here", len({m.profile.name for m in ten.models}), 5)
checks.true("...including all three 0-1 specialists",
            {"Shade Runner", "Soul Weaver", "Way Seeker"}
            <= {m.profile.name for m in ten.models})
checks.eq("...and it is still 10 models", len(ten.models), 10)

for name, small, big in (("Corsair Voidreavers", (5, 65), (10, 110)),
                         ("Corsair Voidscarred", (5, 70), (10, 140)),
                         ("Corsair Skyreavers", (5, 75), (10, 140)),
                         ("Starfangs", (1, 70), (2, 140))):
    checks.eq("%s points" % name,
              (AELDARI_POINTS[name].cost_for(small[0], 1),
               AELDARI_POINTS[name].cost_for(big[0], 1)), (small[1], big[1]))
checks.eq("Kharseth 85", AELDARI_POINTS["Kharseth"].cost_for(1, 1), 85)
checks.eq("Prince Yriel 95", AELDARI_POINTS["Prince Yriel"].cost_for(1, 1), 95)
checks.eq("every wargear option is free", felarch.points, 65)

for hero in ("Kharseth", "Prince Yriel"):
    checks.eq("%s leads the two Corsair foot squads" % hero,
              tuple(AELDARI_POINTS[hero].leads),
              ("Corsair Voidreavers", "Corsair Voidscarred"))
    checks.true("...and CORSAIR REAVER BAND is left out - a Legends datasheet",
                "Corsair Reaver Band" not in AELDARI_POINTS[hero].leads)
voidreavers = build(ae.CORSAIR_VOIDREAVERS, n=5)
checks.eq("Kharseth really attaches",
          attached_units.can_attach(build(ae.KHARSETH, n=5), voidreavers), [])
checks.eq("...and so does Prince Yriel",
          attached_units.can_attach(build(ae.PRINCE_YRIEL, n=5),
                                    build(ae.CORSAIR_VOIDSCARRED, n=5)), [])
checks.true("...but neither leads the Skyreavers",
            bool(attached_units.can_attach(build(ae.KHARSETH, n=6),
                                           build(ae.CORSAIR_SKYREAVERS, n=6))))


# --- 4. Reavers of the Void -------------------------------------------------
print("--- 4. Reavers of the Void ---")

checks.true("it registers as a ones-or-whole source",
            reroll_scope.is_ones_or_whole(reavers_of_the_void.REAVERS_OF_THE_VOID_LABEL))
checks.eq("...the seventh of them", len(reroll_scope.ONES_OR_WHOLE_LABELS), 7)
checks.true("the Voidreavers carry it", reavers_of_the_void.applies(vr))
checks.true("...and the Voidscarred do not", not reavers_of_the_void.applies(vs))

scene = tk.shooting_scene(ae.CORSAIR_VOIDREAVERS, ae.GUARDIAN_DEFENDERS,
                          attacker_owner="Player 2")
sc = scene["shooting"]
sc.active_squad = scene["attacker"]
sc.current_group = {"pairs": [(scene["attacker"].models[0], ShurikenRifleProfile())]}
checks.eq("with no objectives on the board the whole-roll half is not offered - "
          "the automatic 1s are the base clause",
          sc._hit_reroll_reason(scene["target"]), None)
checks.true("...and the base clause still applies",
            reavers_of_the_void.applies(scene["attacker"]))


class _Objective:
    def __init__(self, squad):
        self.terrain_area = _Area(squad)


class _Area:
    def __init__(self, squad):
        self.squad = squad

    def distance_to_model(self, model):
        return 0.0 if model in self.squad.models else 99.0


sc.objectives = [_Objective(scene["target"])]
checks.eq("with the target on an objective the WHOLE roll is on offer instead",
          sc._hit_reroll_reason(scene["target"]),
          reavers_of_the_void.REAVERS_OF_THE_VOID_LABEL)
checks.true("...and the module agrees",
            reavers_of_the_void.offers_full_reroll(
                scene["attacker"], scene["target"], sc.objectives))


# --- 5. Piratical Hero, Faolchu and Piratical Raiders -----------------------
print("--- 5. the adjuster-chain grants ---")

led = build(ae.CORSAIR_VOIDREAVERS, n=7)
attached_units.attach(build(ae.PRINCE_YRIEL, n=7), led)
checks.true("Piratical Hero needs him LEADING", corsair_abilities.piratical_hero_applies(led))
checks.true("...and a lone Yriel grants nothing",
            not corsair_abilities.piratical_hero_applies(build(ae.PRINCE_YRIEL, n=8)))
plain = ShurikenRifleProfile()
granted = corsair_abilities.piratical_hero_adjusted_weapon(plain, led)
checks.eq("its first half grants [SUSTAINED HITS 1]", granted.sustained_hits, 1)
checks.true("...as a copy", granted is not plain and ShurikenRifleProfile().sustained_hits == 0)
# ...and the SECOND half is a modifier, at a different seam.
hscene = tk.shooting_scene(ae.CORSAIR_VOIDREAVERS, ae.GUARDIAN_DEFENDERS,
                           attacker_owner="Player 2")
hsc = hscene["shooting"]
hsc.active_squad = hscene["attacker"]
_group = {"pairs": [(hscene["attacker"].models[0], plain)],
          "target_squad": hscene["target"]}
before = sum(m.amount for m in hsc._hit_modifiers(_group))
attached_units.attach(build(ae.PRINCE_YRIEL, "Player 2", n=9), hscene["attacker"])
after = sum(m.amount for m in hsc._hit_modifiers(_group))
checks.eq("its second half is a +1 to Hit - a MODIFIER, at the other seam",
          after - before, -1)

# Faolchu: RANGED only, and that word is the half easiest to drop.
bearer = build(ae.CORSAIR_VOIDSCARRED, n=8)
for model in bearer.models:
    model.profile = type("WithFaolchu", (type(model.profile),), {"faolchu": True})()
checks.true("Faolchu applies to the bearer's unit", corsair_abilities.faolchu_applies(bearer))
ranged = corsair_abilities.faolchu_adjusted_weapon(ShurikenRifleProfile(), bearer)
checks.true("a RANGED weapon gains [IGNORES COVER]", ranged.ignores_cover)
melee = corsair_abilities.faolchu_adjusted_weapon(PowerSwordProfile(), bearer)
checks.true("...and a MELEE one does not - the printed text says ranged",
            not melee.ignores_cover)

pr = corsair_abilities.PiraticalRaidersController(game_log=tk.Log())
foe_a = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 1")
foe_b = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 2")
checks.true("the Voidscarred carry Piratical Raiders", pr.applies(vs))
checks.true("nothing is granted before the mark", not pr.grants(vs, foe_a))
pr.mark(vs, foe_a)
checks.true("the marked unit is hunted", pr.grants(vs, foe_a))
checks.true("...and another is not", not pr.grants(vs, foe_b))
raided = pr.adjusted_weapon(ShurikenRifleProfile(), vs, foe_a)
checks.true("BOTH keywords are granted in one copy - neither can arrive alone",
            raided.lethal_hits and raided.precision)
checks.true("...and the shared profile is untouched",
            not ShurikenRifleProfile().lethal_hits)
checks.true("a unit without the ability gets nothing",
            pr.adjusted_weapon(ShurikenRifleProfile(), vr, foe_a).lethal_hits is False)


# --- 6. Fury of the Void ----------------------------------------------------
print("--- 6. Fury of the Void ---")

fv = fury_of_the_void.FuryOfTheVoidController(game_log=tk.Log())
kh = build(ae.KHARSETH, n=10)
checks.true("Kharseth carries it", fv.applies(kh))
checks.true("nothing is riven to begin with", not fv.is_riven(foe_a))
checks.true("a unit hit only by the rest of the squad is not a legal choice",
            not fv.offer_after_shooting(kh, [foe_a], dread_hits=[]))
checks.true("...but one his Dread of the Deep Void hit is",
            fv.offer_after_shooting(kh, [foe_a], dread_hits=[foe_a]))
checks.true("...and it is riven", fv.is_riven(foe_a, kh.owner))
# THE reading that matters: it changes STRENGTH, not a roll.
gun = ShurikenRifleProfile()
riven_gun = fv.adjusted_weapon(gun, kh, foe_a)
checks.eq("+1 Strength against a riven unit", riven_gun.strength, gun.strength + 1)
checks.true("...as a copy", riven_gun is not gun
            and ShurikenRifleProfile().strength == gun.strength)
checks.true("an unriven target is untouched",
            fv.adjusted_weapon(gun, kh, foe_b) is gun)
# ...and it really moves the wound threshold, which is the point of a
# characteristic change rather than a modifier.
from game.damage_estimate import wound_threshold
checks.eq("S4 vs T4 needs a 4+", wound_threshold(4, 4), 4)
checks.eq("...and the riven S5 needs a 3+ - the boundary a modifier could not "
          "have crossed", wound_threshold(5, 4), 3)
# ARMY-WIDE, and only for AELDARI.
other_aeldari = build(ae.CORSAIR_VOIDREAVERS, n=11)
checks.true("any AELDARI unit of the marking player benefits",
            fv.adjusted_weapon(gun, other_aeldari, foe_a).strength == gun.strength + 1)
# END TO END through the real adjuster chain: everything above measures the
# controller, and a probe that unplugged it from shooting.py left the section
# fully green until this was added (error class 24).
fscene = tk.shooting_scene(ae.KHARSETH, ae.GUARDIAN_DEFENDERS, attacker_owner="Player 2")
fsc = fscene["shooting"]
fsc.active_squad = fscene["attacker"]
live_fv = fury_of_the_void.FuryOfTheVoidController()
fsc.fury_of_the_void = live_fv
pairs = [(fscene["attacker"].models[0], ShurikenRifleProfile())]
plain_s = fsc._adjusted_weapon(pairs, fscene["target"]).strength
live_fv.mark(fscene["attacker"], fscene["target"])
checks.eq("the real chain adds the riven +1 Strength",
          fsc._adjusted_weapon(pairs, fscene["target"]).strength, plain_s + 1)
# ...and in the Fight phase too, since the printed text says "makes an attack".
mscene = tk.fight_scene(ae.KHARSETH, ae.GUARDIAN_DEFENDERS, attacker_owner="Player 2")
mfc = mscene["fight"]
mfc.fighting_squad = mscene["attacker"]
melee_fv = fury_of_the_void.FuryOfTheVoidController()
mfc.fury_of_the_void = melee_fv
mpairs = [(mscene["attacker"].models[0], PowerSwordProfile())]
melee_plain = mfc._adjusted_weapon(mpairs, mscene["target"]).strength
melee_fv.mark(mscene["attacker"], mscene["target"])
checks.eq("...and the fight chain does the same",
          mfc._adjusted_weapon(mpairs, mscene["target"]).strength, melee_plain + 1)

# Piratical Hero's keyword half reaches the FIGHT chain too - its printed text
# says "makes an attack", not "a ranged attack", and nothing above measured it
# there (a probe that unplugged it left the suite green).
yscene = tk.fight_scene(ae.CORSAIR_VOIDREAVERS, ae.GUARDIAN_DEFENDERS,
                        attacker_owner="Player 2")
yfc = yscene["fight"]
yfc.fighting_squad = yscene["attacker"]
ypairs = [(yscene["attacker"].models[0], PowerSwordProfile())]
checks.eq("unled, the melee weapon has no [SUSTAINED HITS]",
          yfc._adjusted_weapon(ypairs, yscene["target"]).sustained_hits, 0)
attached_units.attach(build(ae.PRINCE_YRIEL, "Player 2", n=21), yscene["attacker"])
yfc.fighting_squad = yscene["attacker"]
checks.eq("...and Yriel leading grants it in the fight chain as well",
          yfc._adjusted_weapon(ypairs, yscene["target"]).sustained_hits, 1)

fv.reset_turn()
checks.true('"until the end of the turn" - the mark clears there',
            not fv.is_riven(foe_a))


# --- 7. Raid and Run, Aethersense, Channeller Stones ------------------------
print("--- 7. Raid and Run, Aethersense, Channeller Stones ---")

checks.true("raid_and_run is registered as a reactive move mode - the set that "
            "stops the AI walking over a human's granted move",
            "raid_and_run" in MovementController.REACTIVE_MOVE_MODES)
rr = raid_and_run.RaidAndRunController(game_log=tk.Log(), all_tokens=[])
sky = build(ae.CORSAIR_SKYREAVERS, n=10)
checks.true("the Skyreavers carry it", raid_and_run.applies(sky))
checks.true("...but it does nothing until they were eligible to fight",
            not rr.can_use(sky))
rr.note_eligible(sky)
checks.true("...and then it does", rr.can_use(sky))
checks.eq("the distance is the roll plus 3", rr.distance_for(2), 5)
# The branch is chosen by the board, not by a second condition.
enemy = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 3")
tk.line_up(sky, x=20.0, y=20.0)
tk.line_up(enemy, x=20.0, y=60.0)
checks.eq("unengaged -> a Normal move",
          raid_and_run.move_kind_for(sky, list(sky.models) + list(enemy.models)),
          raid_and_run.NORMAL)
tk.line_up(enemy, x=20.0, y=20.8)
checks.eq("engaged -> a Fall Back move",
          raid_and_run.move_kind_for(sky, list(sky.models) + list(enemy.models)),
          raid_and_run.FALL_BACK)
rr.reset_phase()
checks.true("the eligibility sample clears with the phase", not rr.can_use(sky))

# Aethersense: measured to the MODEL, and only against ENEMIES.
tk.line_up(kh, x=30.0, y=30.0)
board = list(kh.models)
checks.true("an enemy arrival within 12\" of the model is blocked",
            corsair_abilities.aethersense_blocks((30.0, 36.0), board, arriving_player="Player 2"))
checks.true("...and one further out is not",
            not corsair_abilities.aethersense_blocks((30.0, 60.0), board,
                                                     arriving_player="Player 2"))
checks.true("...and his OWN side is never blocked",
            not corsair_abilities.aethersense_blocks((30.0, 36.0), board,
                                                     arriving_player=kh.owner))

# Channeller Stones: a per-TURN resource on the squad.
weaver = build(ae.CORSAIR_VOIDSCARRED, n=9, composition_index=1)
checks.true("the 10-model build brings a Soul Weaver, so the unit has them",
            corsair_abilities.channeller_stones_available(weaver))
checks.true("...spending them works once", corsair_abilities.spend_channeller_stones(weaver))
checks.true("...and not twice in the same turn",
            not corsair_abilities.spend_channeller_stones(weaver))
corsair_abilities.reset_channeller_stones([weaver])
checks.true("...but they come back next turn",
            corsair_abilities.channeller_stones_available(weaver))
checks.true("a unit without a Soul Weaver has none",
            not corsair_abilities.channeller_stones_available(vr))


# --- 8. Prince of Corsairs and Hallucinogen Grenades ------------------------
print("--- 8. Prince of Corsairs and Hallucinogen Grenades ---")

yriel = build(ae.PRINCE_YRIEL, n=20)


class _State:
    tokens = list(yriel.models)
    embarked_squads = []


step = prince_of_corsairs.PrinceOfCorsairsStep(game_state=_State(), game_log=tk.Log())
checks.true("he is on the battlefield, so the ability is live",
            step.bearer_on_battlefield("Player 1"))
checks.true("...and his opponent has no such ability",
            not step.bearer_on_battlefield("Player 2"))
checks.eq("up to three units", prince_of_corsairs.MAX_REDEPLOYED_UNITS, 3)
checks.eq("...and that is the starting allowance", step.remaining("Player 1"), 3)


class _EmptyState:
    tokens = []
    embarked_squads = []


checks.true("a Yriel who is NOT on the battlefield grants nothing - the case "
            "that would silently keep working",
            not prince_of_corsairs.PrinceOfCorsairsStep(
                game_state=_EmptyState()).bearer_on_battlefield("Player 1"))

# Hallucinogen Grenades: the first TEMPORARY grant of Stealth.
star = build(ae.STARFANGS, n=20)
friend = tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 4")
tk.line_up(star, x=20.0, y=20.0)
tk.line_up(friend, x=20.0, y=24.0)
hg = hallucinogen_grenades.HallucinogenGrenadesController(
    game_log=tk.Log(), all_tokens=list(star.models) + list(friend.models))
checks.true("the Starfangs carry it", hallucinogen_grenades.has_ability(star))
checks.eq("a friendly AELDARI INFANTRY unit in range is a candidate",
          [s.name for s in hg.candidates(star)], [friend.name])
checks.true("the unit has no Stealth to begin with", not squad_has_stealth(friend))
hg.grant(star, friend)
checks.true("...and the grant reaches the real question",
            squad_has_stealth(friend))
hg.reset_phase()
checks.true('"until the end of the phase" - and then it is gone',
            not squad_has_stealth(friend))
# The offer goes to the player whose phase is NOT beginning.
hg2 = hallucinogen_grenades.HallucinogenGrenadesController(
    game_log=tk.Log(), all_tokens=list(star.models) + list(friend.models),
    auto_players=("Player 1",))
checks.true("it fires at the start of the OPPONENT'S Shooting phase",
            hg2.offer_at_start_of_opponent_shooting("Player 2") is not False
            or squad_has_stealth(friend))
hg2.reset_phase()
checks.true("...and not in its owner's own",
            not hg2.offer_at_start_of_opponent_shooting("Player 1"))


# --- 9. wiring and sprites --------------------------------------------------
print("--- 9. wiring and sprites ---")

main_src = open("main.py", encoding="utf-8").read()
for needle, label in [
    ("piratical_raiders=piratical_raiders_controller", "Piratical Raiders reaches the attack controllers"),
    ("fury_of_the_void=fury_of_the_void_controller", "...and so does Fury of the Void"),
    ("shooting_controller.squads_hit_by_weapon(DREAD_OF_THE_DEEP_VOID_NAME)",
     "Fury of the Void gets the per-WEAPON subset"),
    ("fury_of_the_void_controller.reset_turn()", "...and clears at the end of the turn"),
    ("raid_and_run_controller.note_eligibility()", "Raid and Run samples eligibility in the Fight phase"),
    ("raid_and_run_controller.fight_controller = fight_controller",
     "...from the controller that keeps that ledger"),
    ("hallucinogen_grenades_controller.reset_phase()", "the Stealth grant expires with the phase"),
    ("corsair_abilities.reset_channeller_stones(", "Channeller Stones reset each turn"),
    ("_RedeployChain(", "both redeployment abilities share the one hook"),
]:
    checks.true("main.py: %s" % label, needle in main_src)
checks.eq("...and the marks reach BOTH attack controllers",
          main_src.count("piratical_raiders=piratical_raiders_controller"), 2)

ai_src = open("ai/agent_driver.py", encoding="utf-8").read()
checks.true("no AI path for any of the Anhrathe abilities",
            not any(n in ai_src for n in
                    ("reavers_of_the_void", "piratical_raiders", "piratical_hero",
                     "fury_of_the_void", "raid_and_run", "aethersense",
                     "prince_of_corsairs", "hallucinogen_grenades")))

for sheet in SHEETS:
    sq = build(sheet, n=30)
    checks.eq("%s has no art yet - pinned so adding one is visible" % sheet.name,
              sprites.sprite_for(sq.models[0]), None)

checks.finish()
