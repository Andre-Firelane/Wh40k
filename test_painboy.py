"""Painboy (Orks) datasheet + its three abilities.

Built on testkit.py (see its docstring for the harness traps this avoids).

Every section that claims an ability DOES something carries an A/B probe that
unwires that ability and asserts the same scene then behaves the old way - a
green run against a scene the ability never reached would prove nothing.

Sections:
  1. datasheet - stat line, keywords, weapons, points, Grot Orderly gear
  2. Dok's Toolz          (leader-granted Feel No Pain 5+)
  3. Hold Still and Say 'Aargh!'  (D6 mortal wounds per critical wound)
  4. Grot Orderly         (returning destroyed models, in coherency)
  5. Leader / attachment legality
"""

import copy
import math

from testkit import (
    Checks, DecisionManager, DiceManager, GameState, PHASES, RecordingDice,
    TurnTracker, build, options_of, pick_option, script,
)

from game import attached_units, hold_still as hold_still_rule
from game.factions.orks import BOYZ, DEFF_DREAD, PAINBOY, TANKBUSTAS, WARBOSS
from game.factions.tau_empire import STRIKE_TEAM
from game.feel_no_pain import current_feel_no_pain
from game.fight import FightController
from game.formation_layout import returning_positions
from game.grot_orderly import (
    GrotOrderlyController, bearer_models, returnable_models, unit_has_grot_orderly,
)
from game.squad import COHERENCY_RANGE_IN, is_below_starting_strength
from game.turn import PHASE_COMMAND, PHASE_FIGHT
from game.units import PainboyProfile
from game.weapons import PowerKlawProfile, UrtySyringeProfile

c = Checks("Painboy")
GEAR = {"Painboy": {"Grot Orderly": 1}}


def painboy(owner="Player 2", gear=GEAR, name="Painboy 1"):
    return build(PAINBOY, owner, name=name, gear=gear)


# ---------------------------------------------------------------- 1. datasheet

p = painboy()
m = p.models[0]
c.eq("one model", len(p.models), 1)
c.eq("name", m.profile.name, "Painboy")
c.eq("M", m.profile.movement_in, 6)
c.eq("T", m.profile.toughness, 5)
c.eq("Sv", m.profile.armor_save, "5+")
c.eq("W", m.profile.wounds, 3)
c.eq("Ld", m.profile.leadership, "7+")
c.eq("OC", m.profile.oc, 1)
c.true("CHARACTER", m.profile.character)
c.true("INFANTRY", m.profile.infantry)
c.true("Waaagh! (army rule)", m.profile.waaagh)
c.true("ORKS faction flag", m.profile.orks)
c.eq("no invulnerable save printed", m.profile.invulnerable_save, "-")
c.eq("no printed Feel No Pain of its own", m.profile.feel_no_pain, "-")
c.eq("datasheet keywords", PAINBOY.keywords, ("CHARACTER", "INFANTRY", "PAINBOY"))
c.eq("points (flat 90)", p.points, 90)
c.eq("base radius (32mm assumption)", round(m.radius_in, 2), 0.63)

# WS: not in the supplied M/T/Sv/W/Ld/OC table - derived from the weapon
# tables. The syringe's printed 3+ IS the model's own, the klaw's 4+ is the
# real per-weapon override, so only one of the two carries a weapon_skill.
c.eq("model WS from the syringe's printed 3+", m.profile.weapon_skill, "3+")
c.eq("syringe defers WS to the model", UrtySyringeProfile.weapon_skill, None)
c.eq("power klaw overrides WS to 4+", PowerKlawProfile.weapon_skill, "4+")

names = [w.name for w in m.weapons]
c.eq("loadout", names, ["'Urty Syringe", "Power Klaw"])
syringe = next(w for w in m.weapons if w.name == "'Urty Syringe")
klaw = next(w for w in m.weapons if w.name == "Power Klaw")
c.eq("syringe A/S/AP/D", (syringe.attacks, syringe.strength, syringe.ap, syringe.damage), (1, 2, 0, 1))
c.eq("syringe [ANTI-INFANTRY 4+]", syringe.anti, ("INFANTRY", 4))
c.true("syringe [EXTRA ATTACKS]", syringe.extra_attacks)
c.true("syringe [PRECISION]", syringe.precision)
c.true("syringe carries the Hold Still hook", syringe.hold_still)
c.eq("klaw A/S/AP/D", (klaw.attacks, klaw.strength, klaw.ap, klaw.damage), (3, 9, -2, 2))
c.eq("klaw does NOT carry the Hold Still hook", klaw.hold_still, False)

# Grot Orderly is Gear (grants an ability, swaps no weapon), and optional.
c.true("gear applies the flag", m.grot_orderly)
c.true("unit_has_grot_orderly", unit_has_grot_orderly(p))
bare = painboy(gear=None, name="Painboy bare")
c.eq("without the gear the flag stays off", bare.models[0].grot_orderly, False)
c.eq("...and the unit does not have the ability", unit_has_grot_orderly(bare), False)
c.eq("gear is free (no points change)", bare.points, 90)
c.eq("one gear slot", PAINBOY.gear_slots, {"Painboy": 1})


# ------------------------------------------------------------- 2. Dok's Toolz

def attached_mob(with_painboy=True, owner="Player 2"):
    """A Boyz mob, optionally with a Painboy attached (19.01)."""
    mob = build(BOYZ, owner, name="Boyz 1")
    state = GameState()
    for model in mob.models:
        state.add_token(model)
    if not with_painboy:
        return state, mob, None
    doc = painboy(owner)
    for model in doc.models:
        state.add_token(model)
    merged = attached_units.attach(doc, mob, game_state=state)
    return state, merged, doc


_, mob_with, doc = attached_mob()
_, mob_without, _ = attached_mob(with_painboy=False)

boy_with = next(m for m in mob_with.models if not getattr(m, "doks_toolz", False)
                and not m.profile.doks_toolz)
c.eq("led Boy has Feel No Pain 5+", current_feel_no_pain(boy_with), "5+")
c.eq("the Painboy himself is in that unit too", current_feel_no_pain(
    next(m for m in mob_with.models if m.profile.doks_toolz)), "5+")
# A/B: the SAME datasheet without a Painboy attached gets nothing.
c.eq("unled Boy has none", current_feel_no_pain(mob_without.models[0]), "-")
# A/B: a lone Painboy is not "leading a unit" (the false positive
# leader_ability() exists to avoid).
c.eq("lone Painboy grants nothing", current_feel_no_pain(painboy().models[0]), "-")

# 19.04: the grant dies with the last model that confers it.
state_d, mob_d, _ = attached_mob()
doc_model = next(m for m in mob_d.models if m.profile.doks_toolz)
boy_d = next(m for m in mob_d.models if not m.profile.doks_toolz)
c.eq("before the Painboy dies", current_feel_no_pain(boy_d), "5+")
doc_model.current_wounds = 0
state_d.remove_dead_models()
c.eq("after the Painboy dies", current_feel_no_pain(boy_d), "-")

# Never worse than what is printed: a model with its own better FNP keeps it.
state_b, mob_b, _ = attached_mob()
tough = next(m for m in mob_b.models if not m.profile.doks_toolz)
tough.profile = copy.copy(tough.profile)
tough.profile.feel_no_pain = "4+"
c.eq("a printed 4+ beats the granted 5+", current_feel_no_pain(tough), "4+")


# ------------------------------------------ 3. Hold Still and Say 'Aargh!'

def melee_scene(target_sheet=BOYZ, target_owner="Player 1"):
    """A lone Painboy engaged with a target unit, ready to fight."""
    state = GameState()
    doc = painboy()
    target = build(target_sheet, target_owner, name=f"{target_sheet.name} T")
    doc.models[0].x_in, doc.models[0].y_in = 20.0, 20.0
    for i, model in enumerate(target.models):
        model.x_in, model.y_in = 20.0 + i * 1.4, 21.2
    for squad in (doc, target):
        for model in squad.models:
            state.add_token(model)
    tt = TurnTracker()
    tt.phase_index = PHASES.index(PHASE_FIGHT)
    tt.turn_owner = "Player 2"
    tt.set_active("Player 2")
    dice, dec = RecordingDice(), DecisionManager()
    log = _Log()
    fc = FightController(dice_manager=dice, turn_tracker=tt, all_tokens=state.tokens,
                         decision_manager=dec, game_log=log)
    fc.begin_fight_step()
    return dict(state=state, doc=doc, target=target, fight=fc, dice=dice, decision=dec, log=log)


class _Log:
    def __init__(self):
        self.lines = []

    def add(self, message, file_only=False):
        self.lines.append(message)

    def find(self, needle):
        return next((l for l in self.lines if needle.lower() in l.lower()), "")


# applies(): the rule's own conditions, read off real datasheets.
boyz_target = build(BOYZ, "Player 1", name="Boyz T")
dread_target = build(DEFF_DREAD, "Player 1", name="Deff Dread T")
c.true("applies vs INFANTRY", hold_still_rule.applies(syringe, boyz_target))
c.eq("does NOT apply vs a VEHICLE", hold_still_rule.applies(syringe, dread_target), False)
c.true("the Deff Dread really is the VEHICLE half", dread_target.models[0].profile.vehicle)
c.eq("does NOT apply to the power klaw", hold_still_rule.applies(klaw, boyz_target), False)
c.eq("D6 per critical wound", hold_still_rule.dice_count(3), 3)
c.eq("mortal wounds are the sum", hold_still_rule.mortal_wounds([4, 2, 6]), 12)

# 19.03: a VEHICLE component makes the whole attached unit VEHICLE, so the
# exclusion is read at unit level rather than per model.
c.eq("empty/no target -> no", hold_still_rule.applies(syringe, None), False)


def run_syringe_activation(scene, wound_faces, save_faces=(), hold_still_faces=(), hit_face=5):
    # hit_face is deliberately NOT a 6: War Horde's Get Stuck In gives every
    # Ork melee weapon [SUSTAINED HITS 1], so a critical hit would add a
    # second hit and a second wound die, and the scripted dice would no
    # longer line up with what the test means to test.
    fc, dice = scene["fight"], scene["dice"]
    fc.select_to_fight(scene["doc"])
    if fc.state == "choosing_target":
        fc.choose_target_squad(scene["target"])
    # pick the syringe by name, whichever order the groups come in
    # weapon_eligibility() yields (attack_key, label, ...) - the key is an
    # opaque stat tuple, so match on the printed label.
    key = next(k for k, label, *_ in fc.weapon_eligibility() if "syringe" in label.lower())
    # Attacks(1) -> hit(1 die) -> wound(1 die) -> ...
    # The dice this activation draws, in order: Hit, Wound, Save (rule
    # 05.02 - a CRITICAL wound wounds automatically, so a 5 here still
    # reaches a save even against T5), then Hold Still's own D6 per crit.
    script(hit_face, *wound_faces, *save_faces, *hold_still_faces, default=1)
    fc.choose_weapon(key)
    guard = 0
    while dice.pending_values is not None and guard < 40:
        guard += 1
        dice.acknowledge()
        fc.on_dice_acknowledged()
        # any mortal-wound allocation choice: take the first candidate
        choice = fc.pending_damage_choice
        while choice:
            fc.choose_damage_model(choice[0])
            choice = fc.pending_damage_choice
    return guard


# The real thing: S2 vs T5 wounds on a 6+, but [ANTI-INFANTRY 4+] makes a 4+
# a CRITICAL wound - so a 5 is a critical wound that does not even wound.
scene = melee_scene()
before = len([m for m in scene["target"].models if not m.is_dead()])
# Measure WOUNDS lost, not models: the mob's Boss Nob has 2 of them, so how
# many models 6 mortal wounds kill depends on which models the defender picks
# (05.03/06.02) - the wounds inflicted do not.
wounds_before = sum(m.current_wounds for m in scene["target"].models)
run_syringe_activation(scene, wound_faces=[5], save_faces=[6], hold_still_faces=[6])
line = scene["log"].find("Hold Still")
c.true("the ability fired and logged", bool(line))
c.true("...and named the mortal wound total", "6 mortal wound" in line)
after = len([m for m in scene["target"].models if not m.is_dead()])
wounds_after = sum(max(0, m.current_wounds) for m in scene["target"].models)
c.true("Boyz died to the mortal wounds", after < before)
c.eq("6 mortal wounds took 6 wounds off the unit", wounds_before - wounds_after, 6)
c.eq("the save held, so the attack itself did nothing",
     scene["log"].find("save roll"), "'Urty Syringe save roll [6]: 1 saved, 0 failed.")

# A/B on the SAME scene: unwire the hook and nothing happens.
saved = UrtySyringeProfile.hold_still
try:
    UrtySyringeProfile.hold_still = False
    scene_ab = melee_scene()
    before_ab = len([m for m in scene_ab["target"].models if not m.is_dead()])
    run_syringe_activation(scene_ab, wound_faces=[5], save_faces=[6], hold_still_faces=[6])
    c.eq("A/B: no Hold Still line without the hook", scene_ab["log"].find("Hold Still"), "")
    after_ab = len([m for m in scene_ab["target"].models if not m.is_dead()])
    c.eq("A/B: the attack itself kills nobody (save held)", before_ab - after_ab, 0)
finally:
    UrtySyringeProfile.hold_still = saved

# A wound roll that is NOT a critical does nothing.
scene_plain = melee_scene()
run_syringe_activation(scene_plain, wound_faces=[3], hold_still_faces=[6])
c.eq("no crit -> no Hold Still", scene_plain["log"].find("Hold Still"), "")

# VEHICLE target: the syringe still swings, the ability does not trigger.
scene_v = melee_scene(target_sheet=DEFF_DREAD)
run_syringe_activation(scene_v, wound_faces=[6], save_faces=[1], hold_still_faces=[6])
c.eq("VEHICLE target -> no Hold Still", scene_v["log"].find("Hold Still"), "")

# The mortal wounds are ADDITIONAL: the critical wound still goes to a save.
# A 6 wounds outright AND crits, so the save roll must still have happened.
scene_add = melee_scene()
run_syringe_activation(scene_add, wound_faces=[6], save_faces=[1], hold_still_faces=[3])
c.true("critical wound still went to a save", bool(scene_add["log"].find("save roll")))
c.true("...and the mortal wounds happened too", bool(scene_add["log"].find("Hold Still")))


# ------------------------------------------------------------ 4. Grot Orderly

def wounded_mob(dead=3, owner="Player 2", gear=GEAR):
    """A Painboy-led Boyz mob with `dead` bodyguard models destroyed and
    removed, laid out in a legal line."""
    state = GameState()
    mob = build(BOYZ, owner, name="Boyz 1")
    # A block, not a line: ten models at a 1.4" pitch in one row is 12.6"
    # across, which breaks rule 09.02's own 9" spread limit before this test
    # has done anything at all.
    for i, model in enumerate(mob.models):
        model.x_in, model.y_in = 20.0 + (i % 4) * 1.4, 20.0 + (i // 4) * 1.4
        state.add_token(model)
    doc = painboy(owner, gear=gear)
    doc.models[0].x_in, doc.models[0].y_in = 18.6, 20.0
    state.add_token(doc.models[0])
    merged = attached_units.attach(doc, mob, game_state=state)
    for model in [m for m in merged.models if not m.profile.doks_toolz][:dead]:
        model.current_wounds = 0
    state.remove_dead_models()
    return state, merged


def command_tracker(owner="Player 2"):
    tt = TurnTracker()
    tt.phase_index = PHASES.index(PHASE_COMMAND)
    tt.turn_owner = owner
    tt.set_active(owner)
    return tt


state_g, mob_g = wounded_mob(dead=3)
c.eq("destroyed models were recorded", len(mob_g.destroyed_models), 3)
c.eq("...and are gone from the unit", len(mob_g.models), 8)  # 10 Boyz + Painboy - 3
c.true("unit is below starting strength", is_below_starting_strength(mob_g))
c.eq("returnable = the 3 destroyed bodyguard models", len(returnable_models(mob_g)), 3)
c.eq("the Painboy is the bearer", len(bearer_models(mob_g)), 1)

# The Painboy himself is never returnable, even once destroyed.
state_dead, mob_dead = wounded_mob(dead=1)
doc_model = next(m for m in mob_dead.models if m.profile.doks_toolz)
doc_model.current_wounds = 0
state_dead.remove_dead_models()
c.eq("a destroyed leader is not a returnable BODYGUARD model",
     [m for m in returnable_models(mob_dead) if m.profile.doks_toolz], [])

# --- the controller ---------------------------------------------------------

def controller(state, auto=(), dice=None, dec=None, log=None):
    return GrotOrderlyController(
        dice_manager=dice, decision_manager=dec, game_log=log, game_state=state,
        auto_players=auto,
    )


state_1, mob_1 = wounded_mob(dead=3)
tt = command_tracker()
log = _Log()
ctrl = controller(state_1, log=log)
c.true("can_use in the Command phase", ctrl.can_use(mob_1, tt))

# Every clause, isolated - each of these fails ONLY on the clause named.
tt_wrong_phase = command_tracker()
tt_wrong_phase.phase_index = PHASES.index(PHASE_FIGHT)
c.eq("not in the Command phase", ctrl.can_use(mob_1, tt_wrong_phase), False)
tt_other = command_tracker(owner="Player 1")
c.eq("not this player's turn", ctrl.can_use(mob_1, tt_other), False)

state_full, mob_full = wounded_mob(dead=0)
c.eq("at full starting strength", controller(state_full).can_use(mob_full, tt), False)
c.true("...and that is the only thing wrong with it",
       bool(bearer_models(mob_full)) and attached_units.is_attached_unit(mob_full))

state_lone = GameState()
lone = painboy()
lone.models[0].x_in, lone.models[0].y_in = 20.0, 20.0
state_lone.add_token(lone.models[0])
c.eq("a lone Painboy is not leading a unit", controller(state_lone).can_use(lone, tt), False)

state_nogear, mob_nogear = wounded_mob(dead=3, gear=None)
c.eq("without the Grot Orderly wargear", controller(state_nogear).can_use(mob_nogear, tt), False)
c.true("...and that IS the only difference", is_below_starting_strength(mob_nogear)
       and bool(returnable_models(mob_nogear)))

# --- the effect -------------------------------------------------------------

state_2, mob_2 = wounded_mob(dead=3)
dice = DiceManager()
log2 = _Log()
ctrl2 = controller(state_2, auto=("Player 2",), dice=dice, log=log2)
alive_before = len(mob_2.models)
script(2)
c.true("the AI uses it outright", ctrl2.offer_at_command_phase([mob_2], command_tracker()))
c.true("a D3 is on the table", dice.pending_values is not None)
c.eq("...and it is a D3", dice.sides, 3)
dice.acknowledge()
ctrl2.on_dice_acknowledged()
c.eq("rolled a 2 -> 2 models back", len(mob_2.models) - alive_before, 2)
c.eq("...and they left the destroyed list", len(mob_2.destroyed_models), 1)
c.true("logged", "Grot Orderly" in log2.find("Grot Orderly"))
returned = [m for m in mob_2.models if m.current_wounds == m.profile.wounds]
c.true("returned models are back on full wounds", len(returned) >= 2)
c.true("returned models are back among the live tokens",
       all(m in state_2.tokens for m in mob_2.models))
c.eq("coherency intact after the return", mob_2.check_coherency(), [])
c.eq("starting strength is unchanged by the return", mob_2.starting_model_count, 11)

# Once per battle.
c.eq("cannot be used again", ctrl2.can_use(mob_2, command_tracker()), False)
for model in [m for m in mob_2.models if not m.profile.doks_toolz][:4]:
    model.current_wounds = 0
state_2.remove_dead_models()
c.true("even with fresh casualties and models to return",
       is_below_starting_strength(mob_2) and bool(returnable_models(mob_2)))
c.eq("...it is still spent", ctrl2.can_use(mob_2, command_tracker()), False)

# A human is asked instead of it firing.
state_3, mob_3 = wounded_mob(dead=3, owner="Player 1")
dec = DecisionManager()
ctrl3 = controller(state_3, auto=("Player 2",), dice=DiceManager(), dec=dec, log=_Log())
c.true("a non-auto player is offered a prompt",
       ctrl3.offer_at_command_phase([mob_3], command_tracker(owner="Player 1")))
c.true("the prompt is pending", dec.is_pending)
c.eq("the prompt belongs to the defender's owner", dec.player, "Player 1")
labels = options_of(dec)
c.eq("two options", len(labels), 2)
c.true("...one of them declines", any("save it" in l.lower() for l in labels))
before_decline = len(mob_3.models)
pick_option(dec, "save it")
c.eq("declining returns nothing", len(mob_3.models), before_decline)
c.true("...and does not spend the ability",
       ctrl3.can_use(mob_3, command_tracker(owner="Player 1")))

# "Up to D3": rolling higher than the number destroyed returns only those.
state_4, mob_4 = wounded_mob(dead=1)
dice4 = DiceManager()
ctrl4 = controller(state_4, auto=("Player 2",), dice=dice4, log=_Log())
script(3)
ctrl4.offer_at_command_phase([mob_4], command_tracker())
dice4.acknowledge()
ctrl4.on_dice_acknowledged()
c.eq("rolled 3 with only 1 destroyed -> 1 back", len(mob_4.destroyed_models), 0)

# --- the geometry -----------------------------------------------------------

state_5, mob_5 = wounded_mob(dead=3)
coming_back = returnable_models(mob_5)
spots = returning_positions(mob_5, coming_back)
c.eq("one spot per returning model", len(spots), 3)
c.true("all three found somewhere", all(s is not None for s in spots))
survivors = [(m.x_in, m.y_in, m.radius_in) for m in mob_5.models]
ok_coh, ok_overlap = True, True
placed = list(survivors)
for model, spot in zip(coming_back, spots):
    near = any(math.dist(spot, (px, py)) <= COHERENCY_RANGE_IN + model.radius_in + pr
               for px, py, pr in placed)
    clear = all(math.dist(spot, (px, py)) >= model.radius_in + pr
                for px, py, pr in placed)
    ok_coh = ok_coh and near
    ok_overlap = ok_overlap and clear
    placed.append((spot[0], spot[1], model.radius_in))
c.true("every returning model lands in coherency of the group", ok_coh)
c.true("...and overlaps nobody", ok_overlap)

# "Up to": a model with nowhere legal to stand is simply not returned, and
# the whole return is not thrown away.
state_6, mob_6 = wounded_mob(dead=3)
spots_blocked = returning_positions(mob_6, returnable_models(mob_6),
                                    position_valid=lambda model, x, y: False)
c.eq("nothing legal -> nothing placed", spots_blocked, [None, None, None])
dice6 = DiceManager()
log6 = _Log()
ctrl6 = GrotOrderlyController(dice_manager=dice6, game_log=log6, game_state=state_6,
                              auto_players=("Player 2",),
                              position_valid=lambda model, x, y: False)
alive6 = len(mob_6.models)
script(3)
ctrl6.offer_at_command_phase([mob_6], command_tracker())
dice6.acknowledge()
ctrl6.on_dice_acknowledged()
c.eq("no model forced onto illegal ground", len(mob_6.models), alive6)
c.true("...and the log says why", "coherency" in log6.find("Grot Orderly").lower())


# --------------------------------------------------------- 5. Leader legality

mob_legal = build(BOYZ, "Player 2", name="Boyz L")
c.eq("Painboy may lead Boyz", attached_units.can_attach(painboy(), mob_legal), [])
c.eq("Painboy may lead Tankbustas",
     attached_units.can_attach(painboy(), build(TANKBUSTAS, "Player 2", name="TB")), [])
c.true("Painboy may NOT lead a Deff Dread",
       bool(attached_units.can_attach(painboy(), build(DEFF_DREAD, "Player 2", name="DD"))))
c.true("Painboy may NOT lead an enemy unit",
       bool(attached_units.can_attach(painboy(), build(BOYZ, "Player 1", name="Enemy Boyz"))))
c.eq("attachment role reads the printed 'Abilities (Leader)' heading",
     attached_units.attachment_role(painboy()), attached_units.LEADER)
c.true("the pairing list resolves (falls back to the points entry)",
       "Boyz" in attached_units.leadable_unit_names(painboy()))
c.true("a T'au unit is not on it",
       "Strike Team" not in attached_units.leadable_unit_names(painboy()))

# 19.01's one-leader-per-bodyguard rule, given the Leader reading above.
state_two = GameState()
mob_two = build(BOYZ, "Player 2", name="Boyz Two")
for model in mob_two.models:
    state_two.add_token(model)
boss = build(WARBOSS, "Player 2", name="Warboss 1")
for model in boss.models:
    state_two.add_token(model)
with_boss = attached_units.attach(boss, mob_two, game_state=state_two)
c.true("a mob that already has a Warboss cannot also take a Painboy (19.01)",
       bool(attached_units.can_attach(painboy(), with_boss)))

c.finish()
