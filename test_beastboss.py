"""Beastboss (Orks) - datasheet, the generalised dual [ANTI-X], the Leader
pairing, and Ferocious Rage.

Run: python test_beastboss.py

Real build_squad() datasheets and real FightController/ChargeController/
DiceManager objects; dice are scripted through game.dice's randint, the way
the rest of this repo's suites do it.
"""

import sys

from game import attached_units, ferocious_rage
from game import dice as dice_mod
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import (
    BEASTBOSS, BEAST_SNAGGA_BOYZ, BOYZ, DEFF_DREAD, GRETCHIN, TANKBUSTAS,
)
from game.factions.tau_empire import DEVILFISH, STRIKE_TEAM
from game.game_state import GameState
from game.shooting import _wound_crit_threshold
from game.squad import squad_has_might_is_right
from game.weapons import BeastchoppaProfile, BeastSnaggaKlawProfile, SmashHammerProfile

FAILURES, CHECKS = [], [0]


def check(label, got, want):
    CHECKS[0] += 1
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def check_true(label, got):
    check(label, bool(got), True)


def build(sheet, owner="Player 2", name=None):
    return build_squad(sheet, owner, name=name or sheet.name)


# ---------------------------------------------------------------------------
# 1. Datasheet
# ---------------------------------------------------------------------------

boss_squad = build(BEASTBOSS, name="Beastboss 1")
check("single-model datasheet", len(boss_squad.models), 1)
check("points", boss_squad.points, 80)

boss = boss_squad.models[0]
p = boss.profile
check("base radius (50mm, same as Warboss)", round(p.base_radius_in, 2), 0.98)
check("move", p.movement_in, 6)
check("toughness", p.toughness, 5)
check("save", p.armor_save, "4+")
check("invulnerable save", p.invulnerable_save, "5+")
check("wounds", p.wounds, 6)
check("leadership", p.leadership, "6+")
check("OC", p.oc, 1)
check("ballistic skill", p.ballistic_skill, "4+")
check("Feel No Pain 6+", p.feel_no_pain, "6+")
check("CHARACTER", p.character, True)
check("INFANTRY", p.infantry, True)
check("Leader ability (24.22)", p.leader, True)
check("Waaagh!", p.waaagh, True)
check("Orks faction flag", p.orks, True)
check("Ferocious Rage flag", p.ferocious_rage, True)
check("datasheet keywords", set(BEASTBOSS.keywords),
      {"CHARACTER", "INFANTRY", "BEAST SNAGGA", "BEASTBOSS", "WARBOSS"})

# The two melee weapons disagree on WS, so one of them must override.
check("profile carries the better WS (2+)", p.weapon_skill, "2+")
klaw = next(w for w in boss.weapons if w.name == "Beast Snagga Klaw")
choppa = next(w for w in boss.weapons if w.name == "Beastchoppa")
shoota = next(w for w in boss.weapons if w.name == "Shoota")

check("klaw attacks", klaw.attacks, 4)
check("klaw strength", klaw.strength, 10)
check("klaw AP", klaw.ap, -2)
check("klaw damage", klaw.damage, 2)
check("klaw overrides WS down to 3+", klaw.weapon_skill, "3+")

check("beastchoppa attacks", choppa.attacks, 6)
check("beastchoppa strength", choppa.strength, 6)
check("beastchoppa AP", choppa.ap, -1)
check("beastchoppa damage", choppa.damage, 2)
check("beastchoppa needs no WS override (matches the model's 2+)", choppa.weapon_skill, None)

check("shoota range", shoota.range_in, 18)
check("shoota attacks", shoota.attacks, 2)
check("shoota is Rapid Fire 1", shoota.rapid_fire, 1)
check("shoota has no BS of its own, so it uses the Beastboss's 4+",
      shoota.ballistic_skill, None)

# Rule 04.01 makes carrying both melee weapons a choice, not a doubling.
check("both melee weapons are carried at once",
      sorted(w.name for w in boss.weapons if w.weapon_type == "melee"),
      ["Beast Snagga Klaw", "Beastchoppa"])


# ---------------------------------------------------------------------------
# 2. Dual [ANTI-X] (rule 24.03) - the field this datasheet generalised
# ---------------------------------------------------------------------------

def as_monster(squad):
    """Flip the MONSTER keyword on a real squad's own profile instances -
    build_squad() gives every token its own instance, so this touches
    nothing else."""
    for m in squad.models:
        m.profile.monster = True
    return squad


vehicle = build(DEVILFISH, "Player 1", name="Devilfish")
infantry = build(STRIKE_TEAM, "Player 1", name="Strike Team")
monster = as_monster(build(STRIKE_TEAM, "Player 1", name="Fake Monster"))
both = as_monster(build(DEVILFISH, "Player 1", name="Monstrous Vehicle"))

check("klaw carries BOTH anti keywords", klaw.anti, (("MONSTER", 4), ("VEHICLE", 4)))
check("beastchoppa carries both too", choppa.anti, (("MONSTER", 4), ("VEHICLE", 4)))

check("anti-vehicle half fires", _wound_crit_threshold(klaw, vehicle), 4)
check("anti-monster half fires too (this is what used to be lost)",
      _wound_crit_threshold(klaw, monster), 4)
check("both at once -> the better (equal here) threshold",
      _wound_crit_threshold(klaw, both), 4)
check("neither keyword -> rule 05.02's default 6",
      _wound_crit_threshold(klaw, infantry), 6)
check("beastchoppa resolves the same way", _wound_crit_threshold(choppa, monster), 4)

# Backwards compatibility: the single-tuple form still works untouched.
single = next(w for w in build(TANKBUSTAS).models[0].weapons if w.name == "Choppa")
check("a weapon with no anti at all is unaffected", _wound_crit_threshold(single, vehicle), 6)
seeker = SmashHammerProfile()
check("Smash Hammer now carries both halves", seeker.anti, (("MONSTER", 4), ("VEHICLE", 4)))
check("Smash Hammer's regained anti-monster half fires",
      _wound_crit_threshold(seeker, monster), 4)
check("Smash Hammer's original anti-vehicle half still fires",
      _wound_crit_threshold(seeker, vehicle), 4)

# A weapon written in the OLD single-tuple style must still resolve - the
# generalisation has to be additive, not a migration.
legacy = BeastchoppaProfile()
legacy.anti = ("VEHICLE", 4)
check("legacy single-tuple form still resolves", _wound_crit_threshold(legacy, vehicle), 4)
check("legacy single-tuple form still misses the other keyword",
      _wound_crit_threshold(legacy, monster), 6)

# Different thresholds -> the better one wins, which a single tuple could
# never express.
mixed = BeastSnaggaKlawProfile()
mixed.anti = (("MONSTER", 5), ("VEHICLE", 3))
check("with unequal thresholds the best applies", _wound_crit_threshold(mixed, both), 3)


# ---------------------------------------------------------------------------
# 3. Leader (24.22 / 19.01) - claimed to need no new code
# ---------------------------------------------------------------------------

boys = build(BEAST_SNAGGA_BOYZ, name="BSB 1")
check("Beastboss may lead Beast Snagga Boyz", attached_units.can_attach(boss_squad, boys), [])
check_true("but not Gretchin",
           attached_units.can_attach(build(BEASTBOSS, name="B2"), build(GRETCHIN, name="G1")))
check_true("and not Boyz either",
           attached_units.can_attach(build(BEASTBOSS, name="B3"), build(BOYZ, name="Boyz 1")))

check("the led unit has no Might is Right of its own before attaching",
      squad_has_might_is_right(boys), False)
attached_units.attach(boss_squad, boys)
check("merged unit size (10 + 1)", len(boys.models), 11)
check("merged points (90 + 80)", boys.points, 170)
check('"Beastboss" reuses Might is Right, so the mob gets +1 to hit',
      squad_has_might_is_right(boys), True)
check("the mob keeps its own Monster Hunters",
      any(m.profile.monster_hunters for m in boys.models), True)
check("and the Beastboss did NOT hand it Monster Hunters",
      all(m.profile.monster_hunters for m in boys.models), False)

# 19.04: the leader ability lasts exactly as long as the leader model does.
boss_in_unit = next(m for m in boys.models if m.profile.ferocious_rage)
boss_in_unit.current_wounds = 0
check("Might is Right dies with the Beastboss", squad_has_might_is_right(boys), False)
boss_in_unit.current_wounds = 6


# ---------------------------------------------------------------------------
# 4. Ferocious Rage - the predicate
# ---------------------------------------------------------------------------

class FakeCharge:
    def __init__(self, charged=()):
        self.charged_squad_ids = set(charged)


solo = build(BEASTBOSS, name="Solo Boss")
solo_boss = solo.models[0]
solo_klaw = next(w for w in solo_boss.weapons if w.name == "Beast Snagga Klaw")
solo_shoota = next(w for w in solo_boss.weapons if w.name == "Shoota")
pairs = [(solo_boss, solo_klaw)]

check("no charge this turn -> nothing granted",
      ferocious_rage.applies(pairs, FakeCharge(), solo), False)
check("after a Charge move -> granted",
      ferocious_rage.applies(pairs, FakeCharge([solo]), solo), True)
check("no charge controller at all degrades quietly",
      ferocious_rage.applies(pairs, None, solo), False)

raged = ferocious_rage.ferocious_rage_adjusted_weapon(solo_klaw, pairs, FakeCharge([solo]), solo)
check("the granted weapon has [DEVASTATING WOUNDS]", raged.devastating_wounds, True)
check("the base instance is never mutated", solo_klaw.devastating_wounds, False)
check_true("a copy is made, not the original", raged is not solo_klaw)

unraged = ferocious_rage.ferocious_rage_adjusted_weapon(solo_klaw, pairs, FakeCharge(), solo)
check_true("without a charge the weapon is returned untouched", unraged is solo_klaw)

ranged_pairs = [(solo_boss, solo_shoota)]
shot = ferocious_rage.ferocious_rage_adjusted_weapon(solo_shoota, ranged_pairs, FakeCharge([solo]), solo)
check_true("MELEE only - the Shoota is untouched", shot is solo_shoota)
check("...and gains nothing", shot.devastating_wounds, False)

# Per MODEL, not per unit: the mob's own Choppas get nothing even though the
# unit charged, because the models swinging them do not have the ability.
mob_boy = next(m for m in boys.models if not m.profile.ferocious_rage)
mob_choppa = next(w for w in mob_boy.weapons if w.weapon_type == "melee")
mob_pairs = [(mob_boy, mob_choppa)]
check("a led mob's own models get nothing from their leader's rage",
      ferocious_rage.applies(mob_pairs, FakeCharge([boys]), boys), False)
boss_pairs = [(boss_in_unit, next(w for w in boss_in_unit.weapons if w.name == "Beastchoppa"))]
check("...while the Beastboss in the same unit does get it",
      ferocious_rage.applies(boss_pairs, FakeCharge([boys]), boys), True)

# 19.04 again: the grant dies with the model.
boss_in_unit.current_wounds = 0
check("a dead Beastboss grants nothing",
      ferocious_rage.applies(boss_pairs, FakeCharge([boys]), boys), False)
boss_in_unit.current_wounds = 6

# Idempotent: a weapon that already has the ability is returned as-is.
already = BeastchoppaProfile()
already.devastating_wounds = True
check_true("an already-devastating weapon is not re-copied",
           ferocious_rage.ferocious_rage_adjusted_weapon(
               already, pairs, FakeCharge([solo]), solo) is already)


# ---------------------------------------------------------------------------
# 5. Ferocious Rage END TO END through the real fight chain
# ---------------------------------------------------------------------------

from game.charge import ChargeController  # noqa: E402
from game.fight import FightController  # noqa: E402
from game.turn import PHASES, PHASE_FIGHT, TurnTracker  # noqa: E402

_scripted, _default = [], [1]


def _scripted_randint(low, high):
    return _scripted.pop(0) if _scripted else _default[0]


dice_mod.random.randint = _scripted_randint


class Log:
    def __init__(self):
        self.lines = []

    def add(self, message, file_only=False):
        self.lines.append(message)


def fight_scene(charged):
    """A lone Beastboss engaged with a Deff Dread, optionally having charged."""
    st = GameState()
    atk = build_squad(BEASTBOSS, "Player 2", name="Beastboss 1")
    tgt = build_squad(DEFF_DREAD, "Player 1", name="Deff Dread 1")
    atk.models[0].x_in, atk.models[0].y_in = 20.0, 20.0
    tgt.models[0].x_in, tgt.models[0].y_in = 20.0, 21.5
    for sq in (atk, tgt):
        for m in sq.models:
            st.add_token(m)
    tt = TurnTracker()
    tt.phase_index = PHASES.index(PHASE_FIGHT)
    tt.turn_owner = "Player 2"
    tt.set_active("Player 2")
    cc = ChargeController(all_tokens=st.tokens, turn_tracker=tt)
    if charged:
        cc.charged_squad_ids.add(atk)
    log = Log()
    fc = FightController(
        dice_manager=DiceManager(), turn_tracker=tt, all_tokens=st.tokens,
        decision_manager=DecisionManager(), game_log=log, charge_controller=cc,
    )
    fc.begin_fight_step()
    return dict(attacker=atk, target=tgt, fight=fc, log=log, charge=cc)


def swing_beastchoppa(scene, hit_roll, wound_roll):
    """Swing the Beastchoppa once, with scripted hit and wound dice."""
    fc = scene["fight"]
    fc.select_to_fight(scene["attacker"])
    if fc.state == "choosing_target":
        fc.choose_target_squad(scene["target"])
    groups = fc.weapon_eligibility()
    key = next(k for k, label, *_ in groups if "Beastchoppa" in str(label)) \
        if groups and len(groups[0]) > 1 else groups[0][0]
    _scripted[:] = list(hit_roll)
    fc.choose_weapon(key)
    fc.dice_manager.acknowledge()
    _scripted[:] = list(wound_roll)
    fc.on_dice_acknowledged()
    fc.dice_manager.acknowledge()
    fc.on_dice_acknowledged()
    return scene["log"].lines


# Six attacks at WS2+; a wound roll of all 6s is a Critical Wound, which is
# what [DEVASTATING WOUNDS] (24.10) turns into mortal wounds.
SIXES = [6] * 6

after_charge = swing_beastchoppa(fight_scene(charged=True), SIXES, SIXES)
no_charge = swing_beastchoppa(fight_scene(charged=False), SIXES, SIXES)


def mentions_devastating(lines):
    return any("devastating" in l.lower() or "mortal" in l.lower() for l in lines)


check("e2e: after a Charge move the critical wounds go devastating",
      mentions_devastating(after_charge), True)
check("e2e A/B: the same dice without a charge do NOT",
      mentions_devastating(no_charge), False)
check_true("e2e: both runs actually reached the wound step",
           any("wound roll" in l for l in after_charge) and any("wound roll" in l for l in no_charge))


# ---------------------------------------------------------------------------

print(f"{CHECKS[0] - len(FAILURES)}/{CHECKS[0]} checks passed")
for f in FAILURES:
    print("  FAIL:", f)
sys.exit(1 if FAILURES else 0)
