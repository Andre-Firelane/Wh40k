"""Howling Banshees (Aeldari) - the first unit with a CONDITIONAL invulnerable
save, and the datasheet that forced build_squad()'s model cursors to group by
overlapping replaced-weapon sets rather than matching ones.

Two of its three named abilities turned out to be rules this engine already
had under other flavour names (Fights First is core 24.13; Acrobatic is word
for word Stormboyz' Full Throttle), so the tests here check that they are
WIRED, not that new code exists.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from collections import Counter

from game import battle_focus, invulnerable_save, sprites
from game.factions.aeldari import (
    BANSHEE_BLADE_TO_EXECUTIONER,
    BANSHEE_BLADE_TO_TRISKELE,
    BANSHEE_TO_MIRRORSWORDS,
    HOWLING_BANSHEES,
)
from game.squad import squad_has_fights_first, squad_has_full_throttle
from game.units import HowlingBansheeExarchProfile, HowlingBansheeProfile
from game.weapons import MELEE, RANGED
from testkit import Checks, Log, build

checks = Checks("Howling Banshees")

NAME = "1 Howling Banshees 1"


def banshees(size=0, choices=None, name=NAME):
    return build(HOWLING_BANSHEES, "Player 1", name=name,
                 composition_index=size, choices=choices)


def weapons_of(squad):
    return Counter(w.name for m in squad.models for w in m.weapons)


# ------------------------------------------------------- 1. the datasheet

print("--- 1. datasheet ---")

small, big = banshees(0), banshees(1)
checks.eq("the 5-model build costs 85", (len(small.models), small.points), (5, 85))
checks.eq("the 10-model build costs 165", (len(big.models), big.points), (10, 165))
checks.eq("each build is 1 Exarch plus the rest",
          sorted(Counter(m.profile.name for m in big.models).items()),
          [("Howling Banshee", 9), ("Howling Banshee Exarch", 1)])
for keyword in ("INFANTRY", "ASPECT WARRIORS", "HOWLING BANSHEES"):
    checks.true(f"keyword {keyword}", keyword in HOWLING_BANSHEES.keywords)

b, e = HowlingBansheeProfile, HowlingBansheeExarchProfile
checks.eq("Banshee statline M/T/Sv/W/Ld/OC",
          (b.movement_in, b.toughness, b.armor_save, b.wounds, b.leadership, b.oc),
          (8, 3, "4+", 1, "6+", 1))
checks.eq("the Exarch differs only in wounds",
          (e.movement_in, e.toughness, e.armor_save, e.wounds, e.leadership, e.oc),
          (8, 3, "4+", 2, "6+", 1))
checks.true("and is the squad leader", e.squad_leader)
checks.eq("WS2+ / BS3+ - every melee row prints 2+, so no per-weapon override",
          (b.weapon_skill, b.ballistic_skill), ("2+", "3+"))
checks.eq("28.5mm base", b.base_radius_in, round(28.5 / 2 / 25.4, 3))
# The fastest Aeldari infantry so far - pinned so a copy from another profile fails.
from game.units import StrikingScorpionProfile as _scorpion
checks.eq("faster than Striking Scorpions", (b.movement_in, _scorpion.movement_in), (8, 7))


# ---------------------------------------------------------- 2. the weapons

print("--- 2. weapons ---")

trooper = small.models[1]
checks.eq("the printed loadout", sorted(w.name for w in trooper.weapons),
          ["Banshee Blade", "Shuriken Pistol"])
blade = next(w for w in trooper.weapons if w.name == "Banshee Blade")
checks.eq("Banshee Blade A/S/AP/D",
          (blade.attacks, blade.strength, blade.ap, blade.damage), (2, 4, -2, 2))
checks.eq("and no keywords", (blade.sustained_hits, blade.twin_linked, blade.devastating_wounds),
          (0, False, False))

exarch_ex = banshees(choices={"Howling Banshee Exarch": {BANSHEE_BLADE_TO_EXECUTIONER: 1}})
ex_weapon = next(w for w in exarch_ex.models[0].weapons if w.name == "Executioner")
checks.eq("Executioner A/S/AP/D",
          (ex_weapon.attacks, ex_weapon.strength, ex_weapon.ap, ex_weapon.damage), (3, 6, -3, 3))

exarch_mirror = banshees(choices={"Howling Banshee Exarch": {BANSHEE_TO_MIRRORSWORDS: 1}})
mirror = next(w for w in exarch_mirror.models[0].weapons if w.name == "Mirrorswords")
checks.eq("Mirrorswords A/S/AP/D",
          (mirror.attacks, mirror.strength, mirror.ap, mirror.damage), (4, 4, -2, 2))

exarch_tri = banshees(choices={"Howling Banshee Exarch": {BANSHEE_BLADE_TO_TRISKELE: 1}})
tri = [w for w in exarch_tri.models[0].weapons if w.name == "Triskele"]
checks.eq("Triskele is one name with a ranged and a melee row",
          sorted(w.weapon_type for w in tri), sorted([MELEE, RANGED]))
tri_r = next(w for w in tri if w.weapon_type == RANGED)
tri_m = next(w for w in tri if w.weapon_type == MELEE)
checks.eq("its ranged row", (tri_r.range_in, tri_r.attacks, tri_r.strength, tri_r.ap), (12, 3, 3, -1))
checks.true("with [ASSAULT]", tri_r.assault)
checks.eq("its melee row", (tri_m.attacks, tri_m.strength, tri_m.ap, tri_m.damage), (6, 3, -1, 1))


# ----------------------------- 3. the three Exarch options, and the cursor

print("--- 3. Exarch wargear ---")

checks.eq("Executioner replaces only the blade, the pistol stays",
          sorted(w.name for w in exarch_ex.models[0].weapons),
          ["Executioner", "Shuriken Pistol"])
checks.eq("Triskele likewise, and adds both of its rows",
          sorted(w.name for w in exarch_tri.models[0].weapons),
          ["Shuriken Pistol", "Triskele", "Triskele"])
checks.eq("Mirrorswords replaces the pistol AND the blade",
          sorted(w.name for w in exarch_mirror.models[0].weapons), ["Mirrorswords"])

# This datasheet is why build_squad() groups its model cursors by INTERSECTING
# replaced sets. Executioner and Triskele both give up {Banshee Blade};
# Mirrorswords gives up {Shuriken Pistol, Banshee Blade}. The sets overlap
# without matching, so before the grouping change the Exarch could take one of
# the first two AND Mirrorswords at once.
overlap = banshees(choices={"Howling Banshee Exarch": {
    BANSHEE_BLADE_TO_EXECUTIONER: 1, BANSHEE_TO_MIRRORSWORDS: 1}})
checks.eq("two overlapping options apply only the first - 'one of the following'",
          sorted(w.name for w in overlap.models[0].weapons), ["Executioner", "Shuriken Pistol"])
same_set = banshees(choices={"Howling Banshee Exarch": {
    BANSHEE_BLADE_TO_EXECUTIONER: 1, BANSHEE_BLADE_TO_TRISKELE: 1}})
checks.eq("and so do two options replacing exactly the same weapon",
          sorted(w.name for w in same_set.models[0].weapons), ["Executioner", "Shuriken Pistol"])
checks.eq("the troopers are untouched by an Exarch-only option",
          sorted(w.name for w in overlap.models[1].weapons), ["Banshee Blade", "Shuriken Pistol"])


# ------------------------------------- 4. the conditional invulnerable save

print("--- 4. invulnerable save ---")

checks.eq("printed 5+, with a 4+ clause against melee",
          (b.invulnerable_save, b.invulnerable_save_vs_melee), ("5+", "4+"))
checks.eq("against a ranged attack the engine reports 5+",
          invulnerable_save.effective_invulnerable_save(trooper, melee=False), "5+")
checks.eq("against a melee attack it reports 4+",
          invulnerable_save.effective_invulnerable_save(trooper, melee=True), "4+")
checks.eq("the default is the ranged answer, so no existing caller changes meaning",
          invulnerable_save.effective_invulnerable_save(trooper), "5+")

# End to end through the REAL save path, which is what actually matters: the
# attack type comes from the weapon the Save roll is made against, not from a
# caller passing a flag. Two otherwise identical probe weapons, one melee and
# one ranged, and the SAME save roll - AP-2 turns the printed 4+ armour save
# into a 6+, so only the invulnerable save can rescue it.
from game.damage_resolution import DamageAllocationSession
from game.weapons import WeaponProfile


class _MeleeProbe(WeaponProfile):
    name = "probe"
    weapon_type = MELEE
    range_in = 2
    attacks = 1
    strength = 4
    ap = -2
    damage = 1


class _RangedProbe(_MeleeProbe):
    weapon_type = RANGED
    range_in = 12


melee_session = DamageAllocationSession([4], _MeleeProbe(), banshees(name="1 Howling Banshees 5"))
ranged_session = DamageAllocationSession([4], _RangedProbe(), banshees(name="1 Howling Banshees 6"))
checks.eq("a save roll of 4 SAVES against a melee attack (invulnerable 4+)",
          (melee_session.saved, melee_session.failed), (1, 0))
checks.eq("and the same roll FAILS against an identical ranged attack (5+)",
          (ranged_session.saved, ranged_session.failed), (0, 1))

# A unit with no such clause is unaffected either way.
from game.factions.aeldari import STRIKING_SCORPIONS
plain = build(STRIKING_SCORPIONS, "Player 1", name="1 Striking Scorpions 1")
checks.eq("a unit without the clause reports the same thing in melee and at range",
          (invulnerable_save.effective_invulnerable_save(plain.models[1], melee=True),
           invulnerable_save.effective_invulnerable_save(plain.models[1], melee=False)),
          ("-", "-"))


# --------------------------------------------------------- 5. the abilities

print("--- 5. abilities ---")

checks.true("Fights First is the CORE ability (24.13), already implemented",
            squad_has_fights_first(small))
checks.true("Acrobatic rides Stormboyz' Full Throttle flag - word for word the same rule",
            squad_has_full_throttle(small))
checks.true("and the army rule reaches it", battle_focus.has_battle_focus(small))
checks.eq("no Fleet of Foot, so Fade Back costs a token",
          battle_focus.BattleFocusPool(players=("Player 1",), game_log=Log())
          .is_free(battle_focus.FADE_BACK, small), False)

# Acrobatic through the real charge gate: a unit that Advanced or Fell Back
# would normally be ineligible.
from game.charge import ChargeController
from game.movement import MovementController
from testkit import GameState, TurnTracker, PHASES, line_up
from game.turn import PHASE_CHARGE

state = GameState()
tracker = TurnTracker(first_player="Player 1")
tracker.phase_index = PHASES.index(PHASE_CHARGE)
tracker.turn_owner = "Player 1"
tracker.set_active("Player 1")
mover = MovementController(turn_tracker=tracker, all_tokens=state.tokens, player_name="Player 1")
chargers = banshees(name="1 Howling Banshees 2")
foes = build(STRIKING_SCORPIONS, "Player 2", name="1 Striking Scorpions 2")
line_up(chargers, x=10.0, y=20.0)
line_up(foes, x=10.0, y=26.0)
for squad_ in (chargers, foes):
    for model in squad_.models:
        state.add_token(model)
cc = ChargeController(turn_tracker=tracker, all_tokens=state.tokens,
                      movement_controller=mover, game_log=Log())

checks.true("baseline: it can declare a charge", cc.can_declare_charge(chargers))
chargers.fell_back_this_turn = True
checks.true("still eligible after a Fall Back", cc.can_declare_charge(chargers))
chargers.fell_back_this_turn = False
mover.advanced_squad_ids.add(chargers)
checks.true("and after an Advance", cc.can_declare_charge(chargers))

# Control: a unit without the ability is blocked by both.
control = build(STRIKING_SCORPIONS, "Player 1", name="1 Striking Scorpions 3")
line_up(control, x=30.0, y=20.0)
for model in control.models:
    state.add_token(model)
foes2 = build(STRIKING_SCORPIONS, "Player 2", name="1 Striking Scorpions 4")
line_up(foes2, x=30.0, y=26.0)
for model in foes2.models:
    state.add_token(model)
checks.true("control unit can charge normally", cc.can_declare_charge(control))
control.fell_back_this_turn = True
checks.eq("but not after falling back", cc.can_declare_charge(control), False)
control.fell_back_this_turn = False
mover.advanced_squad_ids.add(control)
checks.eq("nor after advancing", cc.can_declare_charge(control), False)

text = " ".join(HOWLING_BANSHEES.abilities_text)
# The Aspect Shrine token used to be asserted as NOT IMPLEMENTED here, so that
# adding it would be a visible change. It has been (see game/aspect_shrine.py
# and test_aspect_shrine.py), so the assertion flipped rather than vanished.
checks.eq("the Aspect Shrine token is no longer recorded as missing",
          "NOT IMPLEMENTED" in text, False)
checks.eq("and the unit really holds one per 5 models",
          small.aspect_shrine_tokens, 1)


# ------------------------------------------------------------ 6. sprites

print("--- 6. sprites ---")

checks.eq("one image for the whole unit",
          [os.path.basename(x) for x in sprites.portrait_paths(small, 4)],
          ["Howling Banshees.png"])


# ---------------------------------------------------------- 7. A/B probes

print("--- 7. A/B probes ---")

saved = HowlingBansheeProfile.invulnerable_save_vs_melee
for cls in (HowlingBansheeProfile, HowlingBansheeExarchProfile):
    cls.invulnerable_save_vs_melee = None
probe = banshees(name="1 Howling Banshees 3")
checks.eq("A/B: without the clause the melee save falls back to the printed 5+",
          invulnerable_save.effective_invulnerable_save(probe.models[1], melee=True), "5+")
for cls in (HowlingBansheeProfile, HowlingBansheeExarchProfile):
    cls.invulnerable_save_vs_melee = saved
checks.eq("A/B: and it comes back when restored",
          invulnerable_save.effective_invulnerable_save(banshees().models[1], melee=True), "4+")

saved_ft = HowlingBansheeProfile.full_throttle
for cls in (HowlingBansheeProfile, HowlingBansheeExarchProfile):
    cls.full_throttle = False
blocked = banshees(name="1 Howling Banshees 4")
line_up(blocked, x=10.0, y=20.0)
for model in blocked.models:
    state.add_token(model)
blocked.fell_back_this_turn = True
checks.eq("A/B: without Acrobatic a fall back blocks the charge",
          cc.can_declare_charge(blocked), False)
for cls in (HowlingBansheeProfile, HowlingBansheeExarchProfile):
    cls.full_throttle = saved_ft

# --- [ANTI-INFANTRY 3+] on every weapon row ---------------------------------
# User report: "anti-infanterie bei den banshees greift nicht". It was missing
# from all five rows - the printed Keywords column carries it on the Banshee
# blade, Executioner, Mirrorswords and BOTH Triskele rows.
print("--- [ANTI-INFANTRY 3+] ---")
from game.weapons import (  # noqa: E402
    BansheeBladeProfile, ExecutionerProfile, MirrorswordsProfile,
    TriskeleRangedProfile, TriskeleMeleeProfile,
)

for cls in (BansheeBladeProfile, ExecutionerProfile, MirrorswordsProfile,
            TriskeleRangedProfile, TriskeleMeleeProfile):
    checks.eq(f"{cls.name} ({cls.weapon_type}) is [ANTI-INFANTRY 3+]",
              cls.anti, ("INFANTRY", 3))

# ...and it reaches the real wound step, not just the profile. S4 into T5 Boyz
# normally wounds on 5+, so a hand of 3s and 4s is zero wounds - with
# [ANTI-INFANTRY 3+] every one of them is a CRITICAL wound and auto-wounds.
import testkit as _tk  # noqa: E402
from game.factions import orks as _orks  # noqa: E402
from game.squad import squad_has_fights_first  # noqa: E402
from testkit import script  # noqa: E402

fight = _tk.fight_scene(HOWLING_BANSHEES, _orks.BOYZ, attacker_owner="Player 1")
script(*([4] * 12), *([3] * 12), default=1)
fight["fight"].select_to_fight(fight["attacker"])
blade_key = next(k for k, label, *_ in fight["fight"].weapon_eligibility()
                 if "Banshee Blade" in label)
fight["fight"].choose_weapon(blade_key)
for _ in range(4):
    if fight["dice"].is_pending:
        fight["fight"].on_dice_acknowledged()
wound_line = next(l for l in fight["log"].lines if "wound roll" in l)
checks.true("the wound roll needed 5+ without it", "needed 5+" in wound_line)
checks.true("but every 3+ crits and auto-wounds", "10 wound(s) (of which 10 critical)" in wound_line)


# ---------------------------------------------------------------------------
# Fights First (24.13) is an ORDER, not an eligibility (rule 12.04)
# ---------------------------------------------------------------------------
#
# User report: "was ist diese meldung immer am ende des gegnerischen zugs?
# irgendeine aeldari trigger? verstehe ich nicht" - an unexplained
# "Fight: Player 1's turn to select a unit" plus a "Pass (no eligible unit in
# range)" button at the end of every enemy turn. It WAS an Aeldari trigger:
# _is_eligible_to_fight() read Fights First as a third way to be eligible, so
# every Banshee squad on the board was eligible every Fight phase no matter
# where it stood, and the phase refused to settle.
print("--- 8. Fights First does not make a unit eligible to fight ---")

far = _tk.fight_scene(HOWLING_BANSHEES, _orks.BOYZ, attacker_owner="Player 1", engaged=False)
checks.true("the datasheet ability is on the unit",
            squad_has_fights_first(far["attacker"]))
checks.true("...and it is genuinely nowhere near an enemy",
            far["attacker"].min_distance_to(far["target"]) > 5.0)
checks.eq("so it is NOT eligible to fight (12.04)",
          far["fight"].is_eligible_to_fight(far["attacker"]), False)
checks.eq("...and the Fight step settles instead of demanding a selection",
          far["fight"].state, "done")
checks.eq("...so there is no Pass to click either", far["fight"].can_pass(), False)

# The ability itself still works where it applies: engaged, it is eligible
# and selectable like any other unit (its ORDER within the step is what
# Fights First decides, via _eligible_fighters(fights_first_only=True)).
near = _tk.fight_scene(HOWLING_BANSHEES, _orks.BOYZ, attacker_owner="Player 1")
checks.eq("engaged, it is eligible", near["fight"].is_eligible_to_fight(near["attacker"]), True)
checks.true("...and selectable",
            near["attacker"] in near["fight"].eligible_to_select_now())

# A/B: the pre-fix predicate, as a local copy - it says the far-away unit IS
# eligible, which is the report.
def pre_fix_eligible(fc, squad):
    if squad in fc.fought_squad_ids or not any(not m.is_dead() for m in squad.models):
        return False
    return (squad.is_engaged(fc.all_tokens) or squad in fc.engaged_at_start
            or squad_has_fights_first(squad))


checks.eq("PRE-FIX: the same far-away unit came back eligible",
          pre_fix_eligible(far["fight"], far["attacker"]), True)


checks.finish()
