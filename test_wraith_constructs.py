"""Wraithlord and Wraithblades - the WRAITH CONSTRUCT pair (Etappe 1).

Two datasheets in one suite because they share a printed keyword, a chassis
lineage and one ability (Psychic Guidance) whose two PRINTED VARIANTS are the
thing most easily collapsed into one. A suite per datasheet could not state
"these agree here and differ there", which is most of what is worth pinning.

WHERE THIS MEASURES, AND WHY THERE
----------------------------------
  * Malevolent Souls is checked through the SHARED ledger and through a real
    death, not off a predicate: the whole ability is four halves of putting a
    model back on the board, and a "did the flag flip" test cannot see three of
    them. Fuegan's Unquenchable Resolve records what omitting one produces.
  * Fated Hero is checked at the RE-ROLL SITES, and the count of those sites is
    itself pinned. It touches four (hit and wound, in both attack steps) and a
    wiring that reaches two looks complete from either of them - the same trap
    Driven by Hatred documents and the same one that made a Hero of the Empire
    probe fail to bite.
  * Psychic Guidance is measured on the ACTUAL hit threshold, because the two
    variants are two flags that must both arrive at the same number.
"""
import testkit as tk
from testkit import Checks

from game import attached_units, fated_hero, invulnerable_save, leadership
from game import malevolent_souls, psychic_guidance, sprites
from game.factions import aeldari as ae
from game.factions.aeldari_points import AELDARI_POINTS
from game.units import WraithbladeProfile, WraithguardProfile, WraithlordProfile
from game.weapons import (
    AeldariFlamerProfile, BrightLanceProfile, GhostaxeProfile,
    GhostglaiveStrikeProfile, GhostglaiveSweepProfile, GhostswordsProfile,
    MissileLauncherStarshotProfile, ScatterLaserProfile, ShurikenCannonProfile,
    ShurikenCatapultProfile, StarcannonProfile, WraithboneFistsProfile,
    WraithboneHullProfile,
)

checks = Checks("Wraith Constructs")


def wraithlord(owner="Player 1", choices=None):
    return tk.build(ae.WRAITHLORD, owner, name="1 Wraithlord 1", choices=choices)


def wraithblades(owner="Player 1", choices=None, gear=None):
    return tk.build(ae.WRAITHBLADES, owner, name="1 Wraithblades 1",
                    choices=choices, gear=gear)


# --- 1. statlines -----------------------------------------------------------
print("--- 1. statlines ---")

p = WraithlordProfile
checks.eq('Wraithlord M8"', p.movement_in, 8)
checks.eq("Wraithlord T10", p.toughness, 10)
checks.eq("Wraithlord Sv2+", p.armor_save, "2+")
checks.eq("Wraithlord W10", p.wounds, 10)
checks.eq("Wraithlord Ld8+", p.leadership, "8+")
checks.eq("Wraithlord OC3", p.oc, 3)
checks.eq("Wraithlord WS4+/BS4+", (p.weapon_skill, p.ballistic_skill), ("4+", "4+"))
checks.true("Wraithlord is a MONSTER", p.monster)
checks.true("Wraithlord is a WALKER", p.walker)
checks.true("Wraithlord is a WRAITH CONSTRUCT", p.wraith_construct)
checks.eq("Wraithlord Deadly Demise 1 (a flat 1, so no notation)",
          (p.deadly_demise, p.deadly_demise_notation), (1, None))
checks.eq("no invulnerable save printed", p.invulnerable_save, "-")
checks.eq("60 mm base, converted like every other base here",
          round(p.base_radius_in, 3), round(60 / 2 / 25.4, 3))
checks.true("...and it does NOT take the enlarged grav-tank radius: a walker, "
            "not a grav-tank, the same call the War Walker records",
            p.base_radius_in < ae.FALCON.model_lines[0].profile_cls.base_radius_in)

b = WraithbladeProfile
checks.eq('Wraithblade M6"', b.movement_in, 6)
checks.eq("Wraithblade T6", b.toughness, 6)
checks.eq("Wraithblade W3", b.wounds, 3)
checks.eq("Wraithblade Ld8+", b.leadership, "8+")
checks.eq("Wraithblade OC1", b.oc, 1)
checks.true("Wraithblade is INFANTRY", b.infantry)
checks.true("Wraithblade is a WRAITH CONSTRUCT", b.wraith_construct)
# Pinned against the sibling rather than against literals: they are the same
# printed construct in two roles, and a change to one that misses the other is
# exactly the drift worth catching.
w = WraithguardProfile
checks.eq("Wraithblade shares the Wraithguard chassis (M/T/Sv/W/Ld/OC)",
          (b.movement_in, b.toughness, b.armor_save, b.wounds, b.leadership, b.oc),
          (w.movement_in, w.toughness, w.armor_save, w.wounds, w.leadership, w.oc))
checks.eq("...and the same 40 mm base", b.base_radius_in, w.base_radius_in)
# NO Battle Focus, and that is the PRINTED datasheet: it carries no FACTION
# line at all, where every Aeldari sheet that has the army rule prints
# "FACTION: **Battle Focus**". The engine used to set it - a transcription
# error on six datasheets - which let these units perform Agile Manoeuvres
# they are not entitled to, and - worse - made Spirit Conclave's
# Spirit Guides aura inert, since it exists to GRANT them exactly this.
checks.true("neither carries Battle Focus - Spirit Guides has to grant it",
            not b.battle_focus and not WraithlordProfile.battle_focus)


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

wl = wraithlord()
checks.eq("Wraithlord default loadout",
          sorted(x.name for x in wl.models[0].weapons),
          ["Shuriken Catapult", "Shuriken Catapult", "Wraithbone Fists"])

fists = WraithboneFistsProfile()
checks.eq("Wraithbone Fists A4/S7/AP-2/D2",
          (fists.attacks, fists.strength, fists.ap, fists.damage), (4, 7, -2, 2))
hull = WraithboneHullProfile()
checks.true("...and they are NOT the Wraithbone Hull (A3/WS4+/S6/AP0/D1)",
            (fists.attacks, fists.strength, fists.ap, fists.damage)
            != (hull.attacks, hull.strength, hull.ap, hull.damage))

strike, sweep = GhostglaiveStrikeProfile(), GhostglaiveSweepProfile()
checks.eq("Ghostglaive strike A4/S10/AP-3",
          (strike.attacks, strike.strength, strike.ap), (4, 10, -3))
checks.eq("Ghostglaive strike damage is D6+1",
          (strike.damage_notation.sides, strike.damage_notation.bonus), (6, 1))
checks.eq("Ghostglaive sweep A8/S7/AP-2/D2",
          (sweep.attacks, sweep.strength, sweep.ap, sweep.damage), (8, 7, -2, 2))
checks.eq("...and sweep is the alternate FIRING MODE, not a second weapon",
          strike.overcharge_profile, GhostglaiveSweepProfile)

axe, swords = GhostaxeProfile(), GhostswordsProfile()
checks.eq("Ghostswords A5/S5/AP-2/D2",
          (swords.attacks, swords.strength, swords.ap, swords.damage), (5, 5, -2, 2))
checks.eq("Ghostaxe A3/S7/AP-2/D2",
          (axe.attacks, axe.strength, axe.ap, axe.damage), (3, 7, -2, 2))
checks.true("the axe trades two attacks for S7 - the whole point of the swap",
            axe.attacks < swords.attacks and axe.strength > swords.strength)

# The reuse that makes the Wraithlord cheap, and the reason it is safe: not one
# shared Aeldari gun pins ballistic_skill, so each reads the FIRING MODEL's BS.
# A hardcoded skill on a shared class is the MissilePodProfile bug already paid
# for once in this repo, so it is asserted rather than assumed.
for cls in (BrightLanceProfile, ScatterLaserProfile, ShurikenCannonProfile,
            StarcannonProfile, ShurikenCatapultProfile,
            MissileLauncherStarshotProfile):
    checks.eq("%s pins no BS, so the Wraithlord's 4+ is used" % cls.name,
              getattr(cls, "ballistic_skill", None), None)
checks.true("the flamer is [TORRENT], which is why its printed N/A BS needs no "
            "override either", AeldariFlamerProfile().torrent)


# --- 3. wargear -------------------------------------------------------------
print("--- 3. wargear ---")

flamers = wraithlord(choices={"Wraithlord": {ae.WRAITHLORD_CATAPULTS_TO_FLAMERS: 1}})
names = sorted(x.name for x in flamers.models[0].weapons)
checks.eq("both catapults go at once - build_squad addresses models, not copies",
          names, ["Flamer", "Flamer", "Wraithbone Fists"])

glaive = wraithlord(choices={"Wraithlord": {ae.WRAITHLORD_GHOSTGLAIVE: 1}})
gnames = sorted(x.name for x in glaive.models[0].weapons)
checks.true("the ghostglaive is a pure ADDITION - the catapults stay",
            gnames.count("Shuriken Catapult") == 2)
checks.true("...and only the STRIKE profile is granted, not both",
            "Ghostglaive - Strike" in gnames and "Ghostglaive - Sweep" not in gnames)

heavy = wraithlord(choices={"Wraithlord": {ae.WRAITHLORD_ADD_BRIGHT_LANCE: 1}})
checks.true("a heavy weapon is added without giving anything up",
            "Bright Lance" in [x.name for x in heavy.models[0].weapons]
            and len(heavy.models[0].weapons) == 4)

# KNOWN LIMITATION, measured rather than claimed: "up to two of the following"
# is a list-building cap across a GROUP of options, and gear_slots caps Gear
# only. Same shape as the Kroot Farstalkers' "one of the following".
five = wraithlord(choices={"Wraithlord": {
    ae.WRAITHLORD_ADD_BRIGHT_LANCE: 1, ae.WRAITHLORD_ADD_MISSILE: 1,
    ae.WRAITHLORD_ADD_SCATTER_LASER: 1, ae.WRAITHLORD_ADD_SHURIKEN_CANNON: 1,
    ae.WRAITHLORD_ADD_STARCANNON: 1}})
added = [x for x in five.models[0].weapons
         if x.name in ("Bright Lance", "Missile Launcher - Starshot", "Scatter Laser",
                       "Shuriken Cannon", "Starcannon")]
checks.eq("KNOWN LIMITATION: 'up to two' is not expressible, so five land",
          len(added), 5)

wb = wraithblades()
checks.eq("Wraithblades are 5 models with ghostswords", len(wb.models), 5)
checks.eq("...all of them", sorted({x.name for m in wb.models for x in m.weapons}),
          ["Ghostswords"])
axed = wraithblades(choices={"Wraithblade": {ae.WRAITHBLADE_TO_GHOSTAXE: 5}},
                    gear={"Wraithblade": [ae.WRAITHBLADE_TO_GHOSTAXE]})
checks.eq("the swap reaches every model", sorted({x.name for m in axed.models for x in m.weapons}),
          ["Ghostaxe"])
checks.true("...and the forceshield comes with it",
            all(getattr(m, "forceshield", False) for m in axed.models))
checks.eq("forceshield is a 4+ invulnerable save",
          invulnerable_save.effective_invulnerable_save(axed.models[0]), "4+")
checks.eq("...which a model that kept its ghostswords does NOT get",
          invulnerable_save.effective_invulnerable_save(wb.models[0]), "-")
# The coupling enforces itself because Gear runs AFTER the weapon swaps - the
# same trick the Lychguard's dispersion shield uses. Asking for the shield
# without the swap must therefore do nothing.
shield_only = wraithblades(gear={"Wraithblade": [ae.WRAITHBLADE_TO_GHOSTAXE]})
checks.true("gear alone grants nothing - the pairing enforces itself",
            not any(getattr(m, "forceshield", False) for m in shield_only.models))


# --- 4. points --------------------------------------------------------------
print("--- 4. points ---")

checks.eq("Wraithlord 125 for 1 model", AELDARI_POINTS["Wraithlord"].cost_for(1, 1), 125)
checks.eq("Wraithblades 140 for 5 models", AELDARI_POINTS["Wraithblades"].cost_for(5, 1), 140)
checks.eq("no copy tiers - the same price for the army's third Wraithlord",
          AELDARI_POINTS["Wraithlord"].cost_for(1, 3), 125)
checks.eq("the built squad carries its cost", (wl.points, wb.points), (125, 140))
checks.eq("every wargear option is free", five.points, 125)
# Neither is LED BY anything built: the Bonesinger is Legends and deliberately
# absent, so no leader in this engine names them. Pinned from both sides so
# that adding one later is a visible change.
named_by = [n for n, entry in AELDARI_POINTS.items()
            if "Wraithblades" in (entry.leads or ()) or "Wraithlord" in (entry.leads or ())]
checks.eq("no built leader names either - the Bonesinger is Legends", named_by, [])


# --- 5. Psychic Guidance: two printed variants ------------------------------
print("--- 5. Psychic Guidance ---")

checks.true("Wraithblades carry the HIT-ROLL variant, like the Wraithguard",
            WraithbladeProfile.psychic_guidance
            and not WraithbladeProfile.psychic_guidance_characteristics)
checks.true("the Wraithlord carries the CHARACTERISTIC variant instead",
            WraithlordProfile.psychic_guidance_characteristics
            and not WraithlordProfile.psychic_guidance)
checks.eq("...and the Wraithguard's flag is untouched",
          (WraithguardProfile.psychic_guidance,
           WraithguardProfile.psychic_guidance_characteristics), (True, False))


def _psyker_scene(target_squad, near=True):
    """A real Farseer on the board, in or out of the 12" aura."""
    farseer = tk.build(ae.FARSEER, target_squad.owner, name="1 Farseer 1")
    tk.line_up(target_squad, x=20.0, y=20.0)
    tk.line_up(farseer, x=20.0, y=(24.0 if near else 60.0))
    return list(target_squad.models) + list(farseer.models)


for squad_fn, label in ((wraithblades, "Wraithblades"), (wraithlord, "Wraithlord")):
    sq = squad_fn()
    near = _psyker_scene(sq, near=True)
    far_sq = squad_fn()
    far = _psyker_scene(far_sq, near=False)
    checks.true("%s: Ld 8+ improves to 6+ inside the aura" % label,
                leadership.leadership_threshold(sq, near) == 6)
    checks.true("%s: ...and stays 8+ outside it" % label,
                leadership.leadership_threshold(far_sq, far) == 8)

# The two predicates must not answer for each other.
blades = wraithblades()
btok = _psyker_scene(blades, near=True)
lord = wraithlord()
ltok = _psyker_scene(lord, near=True)
checks.true("the hit-roll predicate fires for Wraithblades only",
            psychic_guidance.applies(blades, btok)
            and not psychic_guidance.applies(lord, ltok))
checks.true("the characteristic predicate fires for the Wraithlord only",
            psychic_guidance.applies_characteristics(lord, ltok)
            and not psychic_guidance.applies_characteristics(blades, btok))
checks.true("applies_any() covers both - what the Leadership half needs",
            psychic_guidance.applies_any(lord, ltok)
            and psychic_guidance.applies_any(blades, btok))

# ...and both must reach the same NUMBER, through the real fight step.
scene = tk.fight_scene(ae.WRAITHLORD, ae.GUARDIAN_DEFENDERS, attacker_owner="Player 2")
fc = scene["fight"]
# _hit_modifiers() reads self.fighting_squad, which begin_fight_step() leaves
# unset until a unit is actually selected - so a test that forgets this measures
# a controller with no attacker and sees every unit-scoped modifier as absent.
fc.fighting_squad = scene["attacker"]
attacker_model = scene["attacker"].models[0]
base_mods = fc._hit_modifiers(attacker_model, scene["target"])
fc.all_tokens = list(scene["state"].tokens) + list(
    tk.build(ae.FARSEER, "Player 2", name="2 Farseer 1",
             x=scene["attacker"].models[0].x_in,
             y=scene["attacker"].models[0].y_in + 2.0).models)
guided = fc._hit_modifiers(attacker_model, scene["target"])
checks.eq("the Wraithlord's variant reaches the fight step's hit modifiers",
          sum(m.amount for m in guided) - sum(m.amount for m in base_mods), -1)
checks.true("...labelled as Psychic Guidance",
            any(m.source == "Psychic Guidance" for m in guided))


# --- 6. Fated Hero ----------------------------------------------------------
print("--- 6. Fated Hero ---")

checks.eq("the four printed choices, in printed order", list(fated_hero.FATED_HERO_KEYWORDS),
          ["INFANTRY", "MONSTER", "MOUNTED", "VEHICLE"])

ctrl = fated_hero.FatedHeroController()
lord = wraithlord("Player 2")
tk.line_up(lord, x=10.0, y=10.0)
guardians = tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 1")
falcon = tk.build(ae.FALCON, "Player 1", name="1 Falcon 1")

checks.true("nothing applies before a keyword is chosen",
            not ctrl.applies(lord.models[0], guardians))
ctrl.choose(lord.models[0], "INFANTRY")
checks.eq("the choice is remembered per MODEL",
          ctrl.chosen_keyword(lord.models[0]), "INFANTRY")
checks.true("...and never written onto the shared profile class",
            not hasattr(WraithlordProfile, "fated_hero_keyword"))
checks.true("it applies against an INFANTRY unit", ctrl.applies(lord.models[0], guardians))
checks.true("...and not against a VEHICLE one", not ctrl.applies(lord.models[0], falcon))

ctrl2 = fated_hero.FatedHeroController()
lord2 = wraithlord("Player 2")
ctrl2.choose(lord2.models[0], "VEHICLE")
checks.true("a Wraithlord that chose VEHICLE hates the Falcon instead",
            ctrl2.applies(lord2.models[0], falcon)
            and not ctrl2.applies(lord2.models[0], guardians))

checks.true("the group form grants only when EVERY model carries it",
            ctrl.applies_to_group([(lord.models[0], None)], guardians)
            and not ctrl.applies_to_group(
                [(lord.models[0], None), (guardians.models[0], None)], guardians))
checks.true("an empty group grants nothing", not ctrl.applies_to_group([], guardians))

# MOUNTED has no profile flag in this engine - it is a datasheet keyword - so
# the keyword test has to reach the datasheet line, not just the profile.
spears = tk.build(ae.SHINING_SPEARS, "Player 1", name="1 Shining Spears 1")
checks.true("MOUNTED is answered off the datasheet keyword line",
            fated_hero.unit_has_keyword(spears, "MOUNTED"))
checks.true("...and the profile-flag keywords still work",
            fated_hero.unit_has_keyword(guardians, "INFANTRY")
            and fated_hero.unit_has_keyword(falcon, "VEHICLE"))
checks.true("a Wraithlord is itself a MONSTER, so MONSTER is a real choice",
            fated_hero.unit_has_keyword(lord, "MONSTER"))

# It is NOT a reroll_scope source - the printed text has no "instead" and no
# "you can", so offering a "1s only" choice would invent an option.
from game import reroll_scope
src = open("game/reroll_scope.py", encoding="utf-8").read()
checks.true("Fated Hero is deliberately NOT a reroll_scope source",
            "fated_hero" not in src)

# The four wiring sites, counted per file: a wiring that reaches two looks
# complete from either of them.
for path in ("game/fight.py", "game/shooting.py"):
    text = open(path, encoding="utf-8").read()
    checks.eq("%s reads Fated Hero at BOTH its reroll sites" % path,
              text.count("self.fated_hero.applies_to_group"), 2)
    checks.true("%s guards the optional collaborator" % path,
                "self.fated_hero is not None" in text)

# End to end: the reason actually comes back out of the real fight controller.
scene = tk.fight_scene(ae.WRAITHLORD, ae.GUARDIAN_DEFENDERS, attacker_owner="Player 2")
fc = scene["fight"]
fc.current_group = {"pairs": [(scene["attacker"].models[0], None)]}
checks.eq("no reason before a keyword is chosen",
          fc._hit_reroll_reason(scene["target"]), None)
hero = fated_hero.FatedHeroController()
hero.choose(scene["attacker"].models[0], "INFANTRY")
fc.fated_hero = hero
checks.eq("the hit step names Fated Hero",
          fc._hit_reroll_reason(scene["target"]), fated_hero.FATED_HERO_LABEL)
checks.eq("...and so does the wound step",
          fc._wound_reroll_reason(WraithboneFistsProfile(), scene["target"]), fated_hero.FATED_HERO_LABEL)
# ...and the SAME thing through the real ShootingController. Without this the
# source-count guard above is the only thing covering shooting.py, and a probe
# that neutralised those two sites left the suite fully green - a finding about
# the test, not the code (error class 24, the third time in this repo).
sc_scene = tk.shooting_scene(ae.WRAITHLORD, ae.GUARDIAN_DEFENDERS, attacker_owner="Player 2")
sc = sc_scene["shooting"]
sc.active_squad = sc_scene["attacker"]
sc.current_group = {"pairs": [(sc_scene["attacker"].models[0], ShurikenCatapultProfile())]}
checks.eq("the shooting step names nothing before a keyword is chosen",
          sc._hit_reroll_reason(sc_scene["target"]), None)
shoot_hero = fated_hero.FatedHeroController()
shoot_hero.choose(sc_scene["attacker"].models[0], "INFANTRY")
sc.fated_hero = shoot_hero
checks.eq("the shooting hit step names Fated Hero",
          sc._hit_reroll_reason(sc_scene["target"]), fated_hero.FATED_HERO_LABEL)
checks.eq("...and so does the shooting wound step",
          sc._wound_reroll_reason(ShurikenCatapultProfile(), sc_scene["target"]),
          fated_hero.FATED_HERO_LABEL)
checks.eq("...and not against a target without the chosen keyword",
          sc._hit_reroll_reason(tk.build(ae.FALCON, "Player 1", name="1 Falcon 2")), None)

# A/B: unplug the collaborator and both reasons must go.
fc.fated_hero = None
checks.eq("A/B: unplugged, the hit step names nothing",
          fc._hit_reroll_reason(scene["target"]), None)
checks.eq("A/B: unplugged, the wound step names nothing",
          fc._wound_reroll_reason(WraithboneFistsProfile(), scene["target"]), None)

# The AI's deterministic pick: the most numerous enemy keyword, so no prompt
# and no API call. Guardians are 10 INFANTRY against one VEHICLE.
auto = fated_hero.FatedHeroController(auto_players=("Player 2",))
state_tokens = list(guardians.models) + list(falcon.models)


class _State:
    tokens = state_tokens


auto.game_state = _State()
lord3 = wraithlord("Player 2")
state_tokens.extend(lord3.models)
checks.eq("the AI picks the most numerous enemy keyword", auto._auto_pick(lord3.models[0]),
          "INFANTRY")
_done = []
checks.true("the pre-battle step needs no prompt for an AI-owned model",
            auto.start(None, lambda: _done.append(1)) is False)
checks.eq("...and it chose", auto.chosen_keyword(lord3.models[0]), "INFANTRY")
# PregameController calls step.start(self, self._run_next_prebattle_step)
# POSITIONALLY, and a step that never reaches on_done stalls the whole pregame
# on a prompt nobody is waiting for. Both halves pinned here, because the only
# other thing that would catch them is a real battle with a Wraithlord in it -
# and neither demo army fields one.
checks.eq("...and it hands control back, or the pregame would stall", len(_done), 1)

lord4 = wraithlord("Player 1")


class _HumanState:
    # Its own board on purpose: the AI controller above shares no ledger with
    # this one, so a shared token list would have this controller prompt for
    # the AI's Wraithlord first and answer the wrong model's question.
    tokens = list(lord4.models) + list(guardians.models)


human = fated_hero.FatedHeroController(
    game_state=_HumanState(), decision_manager=tk.DecisionManager())
_done2 = []
checks.true("a human-owned Wraithlord gets a prompt instead",
            human.start(None, lambda: _done2.append(1)) is True)
checks.eq("...offering exactly the four printed keywords",
          tk.options_of(human.decision_manager), list(fated_hero.FATED_HERO_KEYWORDS))
checks.true("...and answering it chains on to the next step",
            tk.pick_option(human.decision_manager, "MONSTER") is not None)
checks.eq("the answer is recorded", human.chosen_keyword(lord4.models[0]), "MONSTER")
checks.eq("...and control is handed back", len(_done2), 1)


# --- 7. Malevolent Souls ----------------------------------------------------
print("--- 7. Malevolent Souls ---")

checks.eq("threshold is 3+, not Undying Spite's 4+",
          malevolent_souls.MALEVOLENT_SOULS_THRESHOLD, 3)


def _souls_scene(phase_fight=True, rolled=6):
    scene = tk.fight_scene(ae.GUARDIAN_DEFENDERS, ae.WRAITHBLADES,
                           attacker_owner="Player 1")
    blades = scene["target"]
    turn = scene["turn"]
    if not phase_fight:
        turn.phase_index = 0
    ctrl = malevolent_souls.MalevolentSoulsController(
        game_state=scene["state"], game_log=scene["log"], turn_tracker=turn,
        fight_controller=scene["fight"])
    tk.script(rolled)
    return scene, blades, ctrl


scene, blades, ctrl = _souls_scene()
victim = blades.models[0]
victim.wounds_remaining = 0
scene["state"].tokens.remove(victim)
blades.models.remove(victim)
blades.destroyed_models.append(victim)
kept = ctrl.intercept_destroyed([victim])
checks.eq("a 6 keeps the model up", len(kept), 1)
# The four halves of "back on the board", each one separately.
checks.true("...back in its squad", victim in blades.models)
checks.true("...off the destroyed list", victim not in blades.destroyed_models)
checks.true("...back among the board tokens", victim in scene["state"].tokens)
checks.eq("...and owed an activation", ctrl.models_owed_an_activation(), [victim])
checks.true("the controller reports itself busy while one is owed", ctrl.is_busy)
# "...and is then removed from play."
removed = ctrl.resolve_after_attacks(blades)
checks.eq("it is removed after the attacker finishes", removed, [victim])
checks.true("...out of the squad again", victim not in blades.models)
checks.true("...back on the destroyed list", victim in blades.destroyed_models)
checks.true("...and off the board", victim not in scene["state"].tokens)
checks.true("...and nothing is left owed", not ctrl.is_busy)

scene, blades, ctrl = _souls_scene(rolled=2)
victim = blades.models[0]
checks.eq("a 2 falls - below the 3+", len(ctrl.intercept_destroyed([victim])), 0)

# "destroyed by a MELEE attack": answered from the phase, which is exact.
scene, blades, ctrl = _souls_scene(phase_fight=False, rolled=6)
checks.true("a Wraithblade shot down outside the Fight phase gets nothing",
            not ctrl.is_eligible(blades.models[0]))

# "if that model has not fought this phase"
scene, blades, ctrl = _souls_scene(rolled=6)
scene["fight"].fought_squad_ids.add(blades)
checks.true("a unit that already fought gets nothing",
            not ctrl.is_eligible(blades.models[0]))

# 19.04's shape: only models that PRINT the ability come back. A leader
# attached to the unit does not rise again.
scene, blades, ctrl = _souls_scene(rolled=6)
guardian = tk.build(ae.GUARDIAN_DEFENDERS, blades.owner, name="1 Guardian Defenders 2")
stranger = guardian.models[0]
stranger.squad = blades
checks.true("a model without the printed ability is not eligible",
            not ctrl.is_eligible(stranger))

# The phase reset must not let a model survive into a phase it cannot strike in.
scene, blades, ctrl = _souls_scene(rolled=6)
victim = blades.models[0]
ctrl.intercept_destroyed([victim])
checks.true("owed at the end of the phase", ctrl.is_busy)
ctrl.reset_phase()
checks.true("...and cleared by the phase reset", not ctrl.is_busy)
checks.true("...with the model really gone", victim not in scene["state"].tokens)

# The extraction: both consumers must share one ledger, or the four halves drift.
from game import fight_after_death
from game import dlc_undying_spite
checks.true("Malevolent Souls uses the shared ledger",
            "FightAfterDeath" in open("game/malevolent_souls.py", encoding="utf-8").read())
checks.true("...and so does Undying Spite",
            "FightAfterDeath" in open("game/dlc_undying_spite.py", encoding="utf-8").read())
checks.eq("the two thresholds stay different",
          (malevolent_souls.MALEVOLENT_SOULS_THRESHOLD,
           dlc_undying_spite.UNDYING_SPITE_THRESHOLD), (3, 4))

# main.py wiring - a controller that is built but never FED is invisible to a
# behaviour test, which is the failure this repo has hit four times.
main_src = open("main.py", encoding="utf-8").read()
checks.true("main.py feeds it from the death sweep",
            "malevolent_souls_controller.intercept_destroyed(_swept)" in main_src)
checks.true("main.py drains it when the attacker finishes",
            "malevolent_souls_controller.resolve_after_attacks(_fighter)" in main_src)
checks.true("main.py resets it at the end of the phase",
            "malevolent_souls_controller.reset_phase()" in main_src)
checks.true("main.py blocks the phase change while one is owed",
            "or malevolent_souls_controller.is_busy" in main_src)
checks.true("main.py registers the Fated Hero pre-battle step",
            "pregame_controller.prebattle_steps.append(fated_hero_controller)" in main_src)
checks.true("...and hands the ledger to BOTH attack controllers",
            "fight_controller.fated_hero = fated_hero_controller" in main_src
            and "shooting_controller.fated_hero = fated_hero_controller" in main_src)

# No AI path, checked as negative space (standing instruction for these).
ai_src = open("ai/agent_driver.py", encoding="utf-8").read()
checks.true("no AI path for either datasheet",
            "malevolent_souls" not in ai_src and "fated_hero" not in ai_src)


# --- 8. sprites -------------------------------------------------------------
print("--- 8. sprites ---")

checks.true("the Wraithlord resolves a sprite - the file had been sitting "
            "unused in the folder", sprites.sprite_for(wl.models[0]))
checks.true("...and it is the Wraithlord file",
            "Wraithlord" in (sprites.sprite_for(wl.models[0]) or ""))
checks.eq("Wraithblades have no art yet - pinned so adding one is visible",
          sprites.sprite_for(wb.models[0]), None)
checks.true("...and they do not borrow the Wraithguard's art by substring match",
            "Wraithguard" not in (sprites.sprite_for(wb.models[0]) or ""))

checks.finish()
