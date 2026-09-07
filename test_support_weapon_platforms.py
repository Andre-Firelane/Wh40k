"""D-cannon / Shadow Weaver / Vibro Cannon Platform (Etappe 2).

ONE SUITE FOR THREE DATASHEETS, deliberately: they are one chassis printed
three times, and the assurance worth making is that they AGREE - which cannot
be written down in three independent suites. Same call the Kroot Shapers
record. What each sheet adds is one gun and one ability, and those are checked
separately below.

WHERE THIS MEASURES, AND WHY THERE
----------------------------------
  * Support Weapon's T3 is read through attached_unit_toughness(), the function
    the attack steps actually ask - not off the profile, which still prints T6
    and always will.
  * Structural Collapse is measured on the DIE, not the total. The D-cannon is
    D6+2, so a die of 1 arrives as a 3; a test written against the total would
    pass while re-rolling the wrong face.
  * Sonic Destruction is measured through the real adjuster chain, because the
    save step reads the AP off the weapon that chain returns.
  * Monofilament Snare is driven through a real confirm_move(), since the whole
    ability is a hook on a seam - a predicate test cannot see whether a move
    ever reaches it.
"""
import testkit as tk
from testkit import Checks

from game import monofilament_snare, sonic_destruction, sprites, structural_collapse
from game.damage_reroll import DamageRerollOffer
from game.factions import aeldari as ae
from game.factions.aeldari_points import AELDARI_POINTS
from game.squad import SUPPORT_WEAPON_TOUGHNESS, attached_unit_toughness
from game.units import (
    DCannonPlatformProfile, ShadowWeaverPlatformProfile,
    SupportWeaponPlatformProfile, VibroCannonPlatformProfile,
)
from game.weapons import (
    AeldariCloseCombatWeaponA2Profile, DCannonProfile, ShadowWeaverProfile,
    ShurikenCatapultProfile, VibroCannonProfile,
)

checks = Checks("Support Weapon Platforms")

SHEETS = [
    (ae.D_CANNON_PLATFORM, DCannonPlatformProfile, DCannonProfile),
    (ae.SHADOW_WEAVER_PLATFORM, ShadowWeaverPlatformProfile, ShadowWeaverProfile),
    (ae.VIBRO_CANNON_PLATFORM, VibroCannonPlatformProfile, VibroCannonProfile),
]


def platform(sheet, owner="Player 1", n=1):
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n))


# --- 1. the shared chassis --------------------------------------------------
print("--- 1. the shared chassis ---")

base = SupportWeaponPlatformProfile
checks.eq('M7"', base.movement_in, 7)
checks.eq("T6", base.toughness, 6)
checks.eq("Sv4+", base.armor_save, "4+")
checks.eq("W5", base.wounds, 5)
checks.eq("Ld7+", base.leadership, "7+")
checks.eq("OC1", base.oc, 1)
checks.eq("WS3+/BS3+", (base.weapon_skill, base.ballistic_skill), ("3+", "3+"))
checks.eq("40 mm base", round(base.base_radius_in, 3), round(40 / 2 / 25.4, 3))
checks.true("INFANTRY", base.infantry)
checks.true("SUPPORT (24.34), not LEADER", base.support and not base.leader)
# NO Battle Focus, and that is the PRINTED datasheet: it carries no FACTION
# line at all, where every Aeldari sheet that has the army rule prints
# "FACTION: **Battle Focus**". The engine used to set it - a transcription
# error on six datasheets - which let these units perform Agile Manoeuvres
# they are not entitled to. Unlike the wraith constructs, nothing
# grants it back to these three - a platform is simply not an Agile
# Manoeuvre unit, which is what the missing line says.
checks.true("no Battle Focus - the printed sheet has no FACTION line",
            not base.battle_focus)

# The point of the base class: all three really are the same chassis.
for sheet, profile, _gun in SHEETS:
    checks.true("%s inherits the shared chassis" % sheet.name,
                issubclass(profile, SupportWeaponPlatformProfile))
    checks.eq("%s: statline identical to the chassis" % sheet.name,
              (profile.movement_in, profile.toughness, profile.armor_save,
               profile.wounds, profile.leadership, profile.oc,
               profile.weapon_skill, profile.ballistic_skill,
               profile.base_radius_in),
              (base.movement_in, base.toughness, base.armor_save, base.wounds,
               base.leadership, base.oc, base.weapon_skill, base.ballistic_skill,
               base.base_radius_in))
# ...and each carries exactly its OWN second ability, not its siblings'.
checks.eq("only the D-cannon Platform has Structural Collapse",
          [p.__name__ for _s, p, _g in SHEETS if p.structural_collapse],
          ["DCannonPlatformProfile"])
checks.eq("only the Shadow Weaver Platform has Monofilament Snare",
          [p.__name__ for _s, p, _g in SHEETS if p.monofilament_snare],
          ["ShadowWeaverPlatformProfile"])
checks.eq("only the Vibro Cannon Platform has Sonic Destruction",
          [p.__name__ for _s, p, _g in SHEETS if p.sonic_destruction],
          ["VibroCannonPlatformProfile"])


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

for sheet, _profile, gun in SHEETS:
    sq = platform(sheet)
    checks.eq("%s loadout" % sheet.name,
              sorted(w.name for w in sq.models[0].weapons),
              sorted([gun.name, "Shuriken Catapult", "Close Combat Weapon"]))
    checks.eq("%s has no wargear options at all" % sheet.name,
              len(sheet.wargear_options), 0)

d = DCannonProfile()
checks.eq('D-cannon 24"/S16/AP-4', (d.range_in, d.strength, d.ap), (24, 16, -4))
checks.eq("D-cannon Attacks is a D3", (d.attacks_notation.sides, d.attacks_notation.bonus), (3, 0))
checks.eq("D-cannon Damage is D6+2", (d.damage_notation.sides, d.damage_notation.bonus), (6, 2))
checks.true("D-cannon is [BLAST], [DEVASTATING WOUNDS] and [INDIRECT FIRE]",
            d.blast and d.devastating_wounds and d.indirect_fire)

sw = ShadowWeaverProfile()
checks.eq('Shadow Weaver 48"/S6/AP-1/D1', (sw.range_in, sw.strength, sw.ap, sw.damage), (48, 6, -1, 1))
checks.eq("Shadow Weaver Attacks is D6+2", (sw.attacks_notation.sides, sw.attacks_notation.bonus), (6, 2))
checks.true("...[BLAST] and [INDIRECT FIRE], but NOT devastating wounds",
            sw.blast and sw.indirect_fire and not sw.devastating_wounds)

vc = VibroCannonProfile()
checks.eq('Vibro Cannon 48"/S9/AP-1/D2', (vc.range_in, vc.strength, vc.ap, vc.damage), (48, 9, -1, 2))
checks.true("...and no weapon keywords at all - its stacking is an ABILITY",
            not (vc.blast or vc.indirect_fire or vc.devastating_wounds
                 or vc.lethal_hits or vc.sustained_hits))

# The two shared rows are reused, not re-declared - asserted so a future copy
# shows up as a change here.
checks.eq("the close combat row is the shared Aeldari A2 one",
          AeldariCloseCombatWeaponA2Profile().attacks, 2)
for cls in (DCannonProfile, ShadowWeaverProfile, VibroCannonProfile,
            ShurikenCatapultProfile):
    checks.eq("%s pins no BS, so the platform's 3+ is used" % cls.name,
              getattr(cls, "ballistic_skill", None), None)


# --- 3. points and the SUPPORT pairing --------------------------------------
print("--- 3. points and the SUPPORT pairing ---")

checks.eq("D-cannon Platform 110 for the 1st, 125 from the 2nd",
          (AELDARI_POINTS["D-cannon Platform"].cost_for(1, 1),
           AELDARI_POINTS["D-cannon Platform"].cost_for(1, 2)), (110, 125))
checks.eq("Shadow Weaver Platform 60, flat",
          (AELDARI_POINTS["Shadow Weaver Platform"].cost_for(1, 1),
           AELDARI_POINTS["Shadow Weaver Platform"].cost_for(1, 3)), (60, 60))
checks.eq("Vibro Cannon Platform 60, flat",
          AELDARI_POINTS["Vibro Cannon Platform"].cost_for(1, 1), 60)
for sheet, _p, _g in SHEETS:
    checks.eq("%s: Support Artillery names GUARDIAN DEFENDERS" % sheet.name,
              tuple(AELDARI_POINTS[sheet.name].supports), ("Guardian Defenders",))
    checks.eq("...and it is SUPPORT, so it leads nothing",
              tuple(AELDARI_POINTS[sheet.name].leads), ())

# The attachment really works through the ordinary 19.01 machinery.
from game import attached_units
guardians = tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 1")
plat = platform(ae.VIBRO_CANNON_PLATFORM)
checks.eq("a platform can join Guardian Defenders",
          attached_units.can_attach(plat, guardians), [])
banshees = tk.build(ae.HOWLING_BANSHEES, "Player 1", name="1 Howling Banshees 1")
checks.true("...and nothing else",
            bool(attached_units.can_attach(platform(ae.VIBRO_CANNON_PLATFORM), banshees)))


# --- 4. Support Weapon: T3 while in a bigger unit ---------------------------
print("--- 4. Support Weapon ---")

alone = platform(ae.D_CANNON_PLATFORM)
checks.eq("a platform standing alone keeps its printed T6 - it is not in a unit "
          "with other models", attached_unit_toughness(alone), 6)

# WHERE THE OVERRIDE IS REACHABLE, measured rather than assumed. Rule 19.02
# pools the BODYGUARDS' Toughness, and a SUPPORT model is not a bodyguard - so
# for a platform joined to Guardian Defenders the attack already resolves
# against the Guardians' own T3 and the override changes no number at all. It
# bites when the platform is itself part of the pool, which is what a unit of
# support models is.
pair = platform(ae.D_CANNON_PLATFORM, n=40)
second = platform(ae.SHADOW_WEAVER_PLATFORM, n=41)
pair.models.append(second.models[0])
second.models[0].squad = pair
checks.eq("...and drops to 3 once the unit contains other models",
          attached_unit_toughness(pair), SUPPORT_WEAPON_TOUGHNESS)

# The joined case, and the honest statement about it: T3 either way, because
# the Guardians are T3 themselves. Pinned so the day 19.02's pooling changes,
# this reads as a real assertion rather than a coincidence.
joined = tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 2")
plat2 = platform(ae.D_CANNON_PLATFORM, n=2)
attached_units.attach(plat2, joined)
checks.eq("a platform joined to Guardian Defenders resolves at T3",
          attached_unit_toughness(joined), 3)
checks.eq("...which is the GUARDIANS' own T, pooled by 19.02 - the platform's "
          "T6 was never going to raise it",
          joined.models[1].profile.toughness, 3)

# "cannot embark within a TRANSPORT", both halves from one per-model test.
from game.transport import TransportController
from game.movement import MovementController
falcon = tk.build(ae.FALCON, "Player 1", name="1 Falcon 1")
tk.line_up(falcon, x=12.0, y=10.0)
# Fire Dragons (5) fit the Falcon's capacity of 6 with exactly one slot
# spare, so adding the platform keeps it INSIDE capacity - the only thing
# left to fail on is the printed ban, which is what is being measured.
riders = tk.build(ae.FIRE_DRAGONS, "Player 1", name="1 Fire Dragons 1")
# Centred on the Falcon: line_up() spreads models 1.4" apart, which puts the
# far one outside the 3" embark range and fails the control case for a
# reason that has nothing to do with the rule being measured.
tk.line_up(riders, x=10.0, y=10.5, spacing=1.0)
mc = MovementController()
mc.moved_squad_ids = {riders}
# A real GameState: remaining_capacity() reads embarked_squads off it, so a
# None here fails the check for the wrong reason.
from game.game_state import GameState
_tstate = GameState()
for _m in list(falcon.models) + list(riders.models):
    _tstate.add_token(_m)
tc = TransportController(None, _tstate, list(_tstate.tokens), mc, None, None)
checks.true("plain Guardians can embark (the control case)",
            tc.can_embark(riders, falcon.models[0]))
_joiner = platform(ae.D_CANNON_PLATFORM, n=5).models[0]
# Placed ON the transport: otherwise it sits at its build position, fails
# the 3" embark range and the case passes for the wrong reason.
_joiner.x_in, _joiner.y_in = falcon.models[0].x_in, falcon.models[0].y_in
_joiner.squad = riders
riders.models.append(_joiner)
checks.true("...but not once a platform has joined them",
            not tc.can_embark(riders, falcon.models[0]))


# --- 5. Structural Collapse -------------------------------------------------
print("--- 5. Structural Collapse ---")

dcannon_sq = platform(ae.D_CANNON_PLATFORM, n=6)
checks.true("it applies to the D-cannon",
            structural_collapse.applies(dcannon_sq, DCannonProfile()))
checks.true("...and NOT to the platform's own shuriken catapult",
            not structural_collapse.applies(dcannon_sq, ShurikenCatapultProfile()))
checks.true("...and not to another platform's gun",
            not structural_collapse.applies(
                platform(ae.VIBRO_CANNON_PLATFORM, n=7), VibroCannonProfile()))

# The die, not the total: D6+2 means a 1 arrives as a 3.
offer = DamageRerollOffer(
    structural_collapse.STRUCTURAL_COLLAPSE_LABEL,
    automatic_faces=structural_collapse.STRUCTURAL_COLLAPSE_AUTOMATIC_FACES,
    notation=DCannonProfile.damage_notation, dice_manager=tk.RecordingDice())
checks.eq("a total of 3 is a die of 1", offer.face_of(3), 1)
checks.true("...so it is re-rolled without asking", offer.auto_reroll_for(3))
checks.true("a total of 4 (a die of 2) is not", not offer.auto_reroll_for(4))
checks.true("neither is the maximum", not offer.auto_reroll_for(8))
checks.eq("no notation means no guessing", DamageRerollOffer("x").face_of(3), None)
# The mandatory half must not be offerable twice: one die, one re-roll.
spent = DamageRerollOffer(
    "x", automatic_faces=(1,), notation=DCannonProfile.damage_notation,
    dice_manager=tk.RecordingDice())
spent.dice_manager.already_rerolled.add(0)
checks.true("a die that already used its re-roll is not re-rolled again",
            not spent.auto_reroll_for(3))
# The TITANIC clause is live but unreachable - no built datasheet carries it.
checks.true("no built datasheet is TITANIC, so the second clause is a no-op",
            not structural_collapse.targets_titanic(guardians))

# END TO END through the real ShootingController: a source-string guard cannot
# tell a live branch from a dead one, and a probe that neutralised this branch
# left the suite fully green until this was added (error class 24).
dscene = tk.shooting_scene(ae.D_CANNON_PLATFORM, ae.GUARDIAN_DEFENDERS,
                           attacker_owner="Player 2")
dsc = dscene["shooting"]
dsc.active_squad = dscene["attacker"]
dsc._begin_damage_allocation([1], DCannonProfile(), dscene["target"], None)
built = dsc.damage_session.damage_reroll
checks.true("the real shooting step builds a Damage re-roll for the D-cannon",
            built is not None)
checks.eq("...labelled Structural Collapse", getattr(built, "label", None),
          structural_collapse.STRUCTURAL_COLLAPSE_LABEL)
checks.eq("...and it is the MANDATORY kind, re-rolling a die of 1",
          sorted(getattr(built, "automatic_faces", ())), [1])
# ...and NOT for the platform's other gun.
dsc2 = tk.shooting_scene(ae.D_CANNON_PLATFORM, ae.GUARDIAN_DEFENDERS,
                         attacker_owner="Player 2")["shooting"]
dsc2.active_squad = dscene["attacker"]
dsc2._begin_damage_allocation([1], ShurikenCatapultProfile(), dscene["target"], None)
checks.eq("the shuriken catapult gets no re-roll at all",
          dsc2.damage_session.damage_reroll, None)

src = open("game/shooting.py", encoding="utf-8").read()
checks.true("shooting.py builds the mandatory offer for the D-cannon",
            "structural_collapse.applies(self.active_squad, weapon)" in src)
res = open("game/damage_resolution.py", encoding="utf-8").read()
checks.true("...and the session re-rolls it without a prompt",
            "auto_reroll_for(amount)" in res)
checks.true("the re-roll's dice label no longer names one ability for all three",
            "Sunforge re-roll" not in res)


# --- 6. Sonic Destruction ---------------------------------------------------
print("--- 6. Sonic Destruction ---")

ctrl = sonic_destruction.SonicDestructionController()
p1 = platform(ae.VIBRO_CANNON_PLATFORM, n=10)
p2 = platform(ae.VIBRO_CANNON_PLATFORM, n=11)
p3 = platform(ae.VIBRO_CANNON_PLATFORM, n=12)
targetA = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 1")
targetB = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 2")
gun = VibroCannonProfile()

checks.eq("the FIRST platform to fire on a target gets nothing",
          ctrl.bonus_for(p1.models[0], gun, targetA), 0)
ctrl.note_attack(p1.models[0], gun, targetA)
checks.eq("...still nothing for itself after firing",
          ctrl.bonus_for(p1.models[0], gun, targetA), 0)
checks.eq("the second platform on the SAME target gets +1",
          ctrl.bonus_for(p2.models[0], gun, targetA), 1)
ctrl.note_attack(p2.models[0], gun, targetA)
checks.eq("...and a third gets +2",
          ctrl.bonus_for(p3.models[0], gun, targetA), 2)
checks.eq("but on a DIFFERENT target the count is its own",
          ctrl.bonus_for(p3.models[0], gun, targetB), 0)
ctrl.note_attack(p1.models[0], gun, targetA)
checks.eq("firing twice at the same target still counts once",
          ctrl.bonus_for(p2.models[0], gun, targetA), 1)

adjusted = ctrl.adjusted_weapon(gun, p2.models[0], targetA)
checks.eq("+1 improves S, AP and D together",
          (adjusted.strength, adjusted.ap, adjusted.damage),
          (gun.strength + 1, gun.ap - 1, gun.damage + 1))
checks.true("...and it is a COPY - the shared profile is never mutated",
            adjusted is not gun and VibroCannonProfile().ap == gun.ap)
fresh = sonic_destruction.SonicDestructionController()
checks.true("no bonus -> the very same object back, no copy",
            fresh.adjusted_weapon(gun, p1.models[0], targetA) is gun)
checks.eq("the shuriken catapult never stacks",
          ctrl.bonus_for(p2.models[0], ShurikenCatapultProfile(), targetA), 0)
checks.eq("a non-platform firing a vibro cannon gets nothing",
          ctrl.bonus_for(guardians.models[0], gun, targetA), 0)
# "In YOUR Shooting phase" - reactive fire neither earns nor feeds.
checks.eq("reactive fire earns no bonus",
          ctrl.bonus_for(p2.models[0], gun, targetA, reactive=True), 0)
checks.true("...and does not feed the ledger",
            not ctrl.note_attack(p3.models[0], gun, targetB, reactive=True))
# "this phase"
ctrl.reset_shooting_phase()
checks.eq("the ledger clears with the phase",
          ctrl.bonus_for(p2.models[0], gun, targetA), 0)

# End to end through the real adjuster chain, where the save step reads the AP.
scene = tk.shooting_scene(ae.VIBRO_CANNON_PLATFORM, ae.GUARDIAN_DEFENDERS,
                          attacker_owner="Player 2")
sc = scene["shooting"]
sc.active_squad = scene["attacker"]
live = sonic_destruction.SonicDestructionController()
sc.sonic_destruction = live
pairs = [(scene["attacker"].models[0], VibroCannonProfile())]
before = sc._adjusted_weapon(pairs, scene["target"])
checks.eq("through the real chain: one platform alone is unchanged",
          (before.strength, before.ap), (9, -1))
# The ledger is fed BY THE ENGINE at _begin_resolution(), not by hand here -
# a probe that stopped the feeding left this section green until the call went
# through the controller.
other = platform(ae.VIBRO_CANNON_PLATFORM, "Player 2", n=13)
sc._begin_resolution("vibro", "Vibro Cannon",
                     [(other.models[0], VibroCannonProfile())], scene["target"])
checks.eq("the engine itself recorded the other platform's attack",
          live.bonus_for(scene["attacker"].models[0], VibroCannonProfile(),
                         scene["target"]), 1)
after = sc._adjusted_weapon(pairs, scene["target"])
checks.eq("...and +1 once a second platform has fired on the same target",
          (after.strength, after.ap, after.damage), (10, -2, 3))


# --- 7. Monofilament Snare --------------------------------------------------
print("--- 7. Monofilament Snare ---")

snare = monofilament_snare.MonofilamentSnareController(game_log=tk.Log())
victim = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 9")
shooter = platform(ae.SHADOW_WEAVER_PLATFORM, "Player 1", n=20)
checks.true("nothing is snared to begin with", not snare.is_snared(victim))
snare.snare(victim, "Player 1")
checks.true("...and marking works", snare.is_snared(victim))
# "until the start of YOUR next turn" - the MARKING player's.
snare.clear_for_turn_of("Player 2")
checks.true("the opponent's turn beginning does not clear it",
            snare.is_snared(victim))
snare.clear_for_turn_of("Player 1")
checks.true("...the marking player's turn beginning does", not snare.is_snared(victim))

# The move types, at the seam.
checks.eq("a Charge is not one of the three printed move types",
          sorted(monofilament_snare.UNSNARED_MOVE_MODES),
          ["charge", "consolidate", "pile_in", "surge"])
snare2 = monofilament_snare.MonofilamentSnareController(game_log=tk.Log())
snare2.snare(victim, "Player 1")
tk.script(*([1] * 11))
checks.eq("eleven models (10 Guardians + the platform), eleven 1s -> 11 mortal wounds",
          snare2.notify_move(victim, None), 11)
snare3 = monofilament_snare.MonofilamentSnareController(game_log=tk.Log())
snare3.snare(victim, "Player 1")
tk.script(*([2] * 11), default=2)
checks.eq("...and none when nothing rolls a 1",
          snare3.notify_move(victim, None), 0)
snare4 = monofilament_snare.MonofilamentSnareController(game_log=tk.Log())
snare4.snare(victim, "Player 1")
tk.script(*([1] * 11))
checks.eq("a CHARGE move costs nothing", snare4.notify_move(victim, "charge"), 0)
checks.eq("a PILE-IN costs nothing", snare4.notify_move(victim, "pile_in"), 0)
tk.script(*([1] * 11))
checks.eq("a FALL BACK does", snare4.notify_move(victim, "fall_back"), 11)
tk.script(*([1] * 11))
checks.eq("...and so does a granted Normal move (Scouts prints one)",
          snare4.notify_move(victim, "scout"), 11)
unsnared = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 8")
tk.script(*([1] * 11))
checks.eq("an unsnared unit pays nothing at all",
          snare4.notify_move(unsnared, None), 0)

# The per-WEAPON condition on the offer.
snare5 = monofilament_snare.MonofilamentSnareController(game_log=tk.Log())
snare5.offer_after_shooting(shooter, [victim], shadow_weaver_hits=[])
checks.true("a unit hit only by the shuriken catapult is not a legal choice",
            not snare5.is_snared(victim))
snare5.offer_after_shooting(shooter, [victim], shadow_weaver_hits=[victim])
checks.true("...but one hit by the shadow weaver is", snare5.is_snared(victim))
snare6 = monofilament_snare.MonofilamentSnareController(game_log=tk.Log())
snare6.offer_after_shooting(guardians, [victim], shadow_weaver_hits=[victim])
checks.true("a unit without the ability snares nothing",
            not snare6.is_snared(victim))
checks.eq("SHADOW_WEAVER_NAME matches the printed weapon",
          monofilament_snare.SHADOW_WEAVER_NAME, ShadowWeaverProfile.name)

# Driven through a REAL confirm_move(), because the ability is a hook on a seam
# and a predicate test cannot see whether a move ever reaches it.
# Fire Dragons (5) rather than Guardian Defenders (11): line_up() spreads
# models 1.4" apart, and eleven of them break rule 09.02's 9" spread limit,
# so confirm_move() would reject the move before reaching the snare at all.
mscene = tk.fight_scene(ae.FIRE_DRAGONS, ae.FIRE_DRAGONS,
                        attacker_owner="Player 1", engaged=False)
mover = mscene["attacker"]
live_snare = monofilament_snare.MonofilamentSnareController(game_log=mscene["log"])
live_snare.snare(mover, "Player 2")
mc2 = MovementController()
mc2.obstacles = []
mc2.all_tokens = list(mscene["state"].tokens)
mc2.monofilament_snare = live_snare
mc2.selected_squad = mover
mc2.move_mode = None
mc2.state = getattr(mc2, "state", None)
tk.script(*([1] * 5))
mc2.confirm_move()
checks.true("a confirmed Normal move really reaches the snare",
            live_snare.mortal_wound_session is not None)

move_src = open("game/movement.py", encoding="utf-8").read()
checks.true("confirm_move() reports the move to the snare",
            "self.monofilament_snare.notify_move(self.selected_squad, self.move_mode)" in move_src)
def _before(text, first, second):
    """Order guard that goes RED rather than raising when a needle is gone -
    str.index() throws, which hides WHICH check broke (this repo has been
    caught by that twice)."""
    i, j = text.find(first), text.find(second)
    return i >= 0 and j >= 0 and i < j


checks.true("...from the same seam rule 16.01 uses",
            _before(move_src, "action_controller.notify_move",
                    "monofilament_snare.notify_move"))


# --- 8. main.py wiring and sprites ------------------------------------------
print("--- 8. wiring and sprites ---")

main_src = open("main.py", encoding="utf-8").read()
for needle, label in [
    ("shooting_controller.monofilament_snare = monofilament_snare_controller",
     "the shooting controller can place snares"),
    ("movement_controller.monofilament_snare = monofilament_snare_controller",
     "the movement controller can resolve them"),
    ("monofilament_snare_controller.clear_for_turn_of(turn_tracker.turn_owner)",
     "snares expire at the start of the marking player's turn"),
    ("shooting_controller.sonic_destruction = sonic_destruction_controller",
     "the Sonic Destruction ledger is reachable"),
    ("sonic_destruction_controller.reset_shooting_phase()",
     "...and cleared with the phase"),
    ("shooting_controller.squads_hit_by_weapon(SHADOW_WEAVER_NAME)",
     "the snare gets the per-WEAPON hit subset"),
]:
    checks.true("main.py: %s" % label, needle in main_src)

# No AI path (standing instruction), checked as negative space.
ai_src = open("ai/agent_driver.py", encoding="utf-8").read()
checks.true("no AI path for any of the three",
            not any(n in ai_src for n in
                    ("monofilament_snare", "sonic_destruction", "structural_collapse")))

ART = {  # datasheets whose art the user has since supplied
    # ALL THREE share one file (user decision) - which is this suite's own
    # thesis in the art: one chassis, three guns bolted on.
    'D-cannon Platform': 'D-Cannon Platform.png',
    'Shadow Weaver Platform': 'D-Cannon Platform.png',
    'Vibro Cannon Platform': 'D-Cannon Platform.png',
}
for sheet, _p2, _g2 in SHEETS:
    sq = platform(sheet, n=30)
    _p = sprites.sprite_for(sq.models[0])
    if sheet.name in ART:
        # AT THE MODEL, so a key naming a file that is not on disk fails here
        # rather than passing on a mapping table nobody checked. Named file, so
        # a datasheet quietly borrowing a NEIGHBOUR's art by substring match
        # fails too - which is how "Autarch" would shadow "Autarch Wayleaper".
        checks.true("%s draws its own art" % sheet.name,
                    ART[sheet.name] in (_p or ""))
    else:
        checks.eq("%s has no art yet - pinned so adding one is visible" % sheet.name,
                  _p, None)

checks.finish()
