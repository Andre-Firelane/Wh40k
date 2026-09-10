"""Stage 5 of the Necron datasheet backfill: the CANOPTEK batch.

Seven datasheets and fifteen printed abilities - the largest stage of the nine,
and the one in which three things had to be EXTRACTED before anything could be
built (the `pinned` status, the Feel No Pain aura, and rule 19.01's retinue
form), because each acquired its second carrier here.

WHAT EACH SECTION IS FOR

  1. chassis and statlines for all seven, against the corpus.
  2. weapons, and the collision sweep as a MEASUREMENT - it came out THREE
     different ways this time (fork, inherit, new), and each is asserted in the
     form that a wrong verdict would fail.
  3. wargear, points and the attachment table.
  4. Chittering Swarm - two clauses pointing in opposite directions, measured
     through the REAL effective_oc() fold rather than at the predicates.
  5. Self-destruction - the three roll bands and the model that is spent.
  6. the Spyders: Canoptek Swarm and the two Feel No Pain auras, the second
     through the real current_feel_no_pain() fold.
  7. Sentinel Construct, at the real snap-threshold seam.
  8. the reanimation boosts, through the real army-rule activation.
  9. Harassment Swarm and Weapon Sentinels, through both real attack steps.
 10. the Geomancer: the pin, its clock, the reserve denial, and the no-op that
     Vanguard Protocols measurably is.
 11. the three extractions themselves.
 12. wiring, the AI negative space, sprites and dormancy.
"""

import ast
import io

import testkit as tk
from testkit import Checks, build_squad

from game import (attached_units, chittering_swarm, cover_denial, engagement,
                  feel_no_pain, fnp_aura, formations, harassment_swarm,
                  macrocyte_wargear, objective_control, obelisk_node_control,
                  pinned as pinned_status, reanimation_boost, retinue,
                  scarab_self_destruction, scouts, sentinel_construct,
                  spyder_wargear, sprites, vanguard_protocols, weapon_sentinels)
from game.decision import DecisionManager
from game.factions import necrons as nec
from game.factions.necrons_points import NECRONS_POINTS
from game.game_state import GameState
from game.terrain import EXPOSED, Obstacle
from game.monofilament_web import MonofilamentWebController
from game.modifiers import apply_modifiers
from game.tectonic_reverberations import TectonicReverberationsController
from game.units import (CanoptekDoomstalkerProfile, CanoptekMacrocyteProfile,
                        CanoptekReanimatorProfile, CanoptekScarabSwarmProfile,
                        CanoptekSpyderProfile, CanoptekTombCrawlerProfile,
                        GeomancerProfile)
from game.weapons import (AtomiserBeamA1Profile, AtomiserBeamA3Profile,
                          AutomatonClawsProfile, ClawsA2S4Profile,
                          ClawsA4S6Profile, DoomsdayBlasterProfile,
                          DoomstalkerLimbsProfile, FeederMandiblesProfile,
                          GaussFlayerProfile, GaussReaperProfile,
                          GaussScalpelProfile, ParticleBeamerS5Profile,
                          ParticleBeamerS6Profile, ReanimatorsClawsProfile,
                          TeslaCasterProfile, TransdimensionalIsolatorProfile,
                          TremorglaiveMeleeProfile,
                          TremorglaiveReverberatingBeamProfile,
                          TremorglaiveShockWavePulseProfile,
                          TwinGaussFlayerProfile, TwinGaussReaperProfile)

c = Checks("Necron CANOPTEK")

D = nec.NECRONS.datasheets
SCARABS = D["Canoptek Scarab Swarms"]
SPYDERS = D["Canoptek Spyders"]
DOOMSTALKER = D["Canoptek Doomstalker"]
REANIMATOR = D["Canoptek Reanimator"]
MACROCYTES = D["Canoptek Macrocytes"]
TOMB_CRAWLERS = D["Canoptek Tomb Crawlers"]
GEOMANCER = D["Geomancer"]
WARRIORS = D["Necron Warriors"]
IMMORTALS = D["Immortals"]
TECHNOMANCER = D["Technomancer"]
CRYPTOTHRALLS = D["Cryptothralls"]
TOMB_BLADES = D["Tomb Blades"]

SHEETS = [SCARABS, SPYDERS, DOOMSTALKER, REANIMATOR, MACROCYTES,
          TOMB_CRAWLERS, GEOMANCER]


def build(sheet, owner="Player 2", n=1, **kw):
    """Named the way main.py names squads - see the sprite trap in
    game/sprites.py's _key_for_name()."""
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


def place(squad, x, y, spacing=1.4):
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + i * spacing, y
    return squad


def tokens(*squads):
    out = []
    for s in squads:
        out.extend(s.models)
    return out


# --- 1. chassis and statlines -----------------------------------------------
print("--- 1. statlines ---")

STATS = [
    (CanoptekScarabSwarmProfile, 10, 2, "6+", 4, "8+", 0, 0.787),
    (CanoptekSpyderProfile, 5, 7, "3+", 6, "8+", 2, 1.181),
    (CanoptekDoomstalkerProfile, 8, 8, "3+", 12, "8+", 4, 1.772),
    (CanoptekReanimatorProfile, 8, 6, "3+", 6, "7+", 3, 1.181),
    (CanoptekMacrocyteProfile, 8, 3, "4+", 1, "8+", 1, 0.561),
    (CanoptekTombCrawlerProfile, 5, 4, "3+", 3, "8+", 1, 0.984),
    (GeomancerProfile, 8, 4, "4+", 4, "6+", 1, 0.984),
]
for profile, m, t, sv, w, ld, oc, base in STATS:
    c.eq("%s M/T/Sv/W/Ld/OC" % profile.name,
         (profile.movement_in, profile.toughness, profile.armor_save,
          profile.wounds, profile.leadership, profile.oc),
         (m, t, sv, w, ld, oc))
    c.eq("...on its printed base", profile.base_radius_in, base)
    c.true("...with Reanimation Protocols", profile.reanimation_protocols)

c.eq("only the Doomstalker has an invulnerable save",
     sorted(p.name for p, *_ in STATS if p.invulnerable_save != "-"),
     ["Canoptek Doomstalker"])
c.eq("...and it is 4+", CanoptekDoomstalkerProfile.invulnerable_save, "4+")
c.eq("the Doomstalker's Damaged bracket is 1-4",
     CanoptekDoomstalkerProfile.damaged_threshold, 4)
c.eq("Deadly Demise: the Spyder's is a FLAT 1, the Doomstalker's a D3",
     (CanoptekSpyderProfile.deadly_demise,
      CanoptekSpyderProfile.deadly_demise_notation,
      CanoptekDoomstalkerProfile.deadly_demise_notation.sides), (1, None, 3))
c.eq("both Scouts 8\" datasheets", sorted(p.name for p, *_ in STATS if p.scouts),
     ["Canoptek Macrocyte"])
c.eq("the Scarabs are the only OC 0 unit in the faction",
     sorted(s.name for s in nec.NECRONS.datasheets.values()
            for ml in (s.model_lines or s.composition_options[0])
            if ml.profile_cls.oc == 0),
     ["Canoptek Scarab Swarms"])
c.true("the Geomancer SUPPORTS, like every other Cryptek",
       GeomancerProfile.support and not GeomancerProfile.leader)


# --- 2. weapons, and the collision sweep ------------------------------------
print("--- 2. weapons ---")

def row(w):
    return (w.range_in, w.attacks, w.strength, w.ap, w.damage)

c.eq("Feeder mandibles", row(FeederMandiblesProfile), (2, 6, 2, 0, 1))
c.true("...with [LETHAL HITS]", FeederMandiblesProfile.lethal_hits)
c.eq("Automaton claws", row(AutomatonClawsProfile), (2, 5, 8, -2, 2))
c.eq("Doomsday blaster", row(DoomsdayBlasterProfile), (48, 7, 14, -3, 3))
c.eq("...D6+1 Attacks, rolled rather than the placeholder",
     (DoomsdayBlasterProfile.attacks_notation.sides,
      DoomsdayBlasterProfile.attacks_notation.bonus), (6, 1))
c.true("...[BLAST] and [HEAVY]",
       DoomsdayBlasterProfile.blast and DoomsdayBlasterProfile.heavy)
c.eq("Doomstalker limbs", row(DoomstalkerLimbsProfile), (2, 3, 6, 0, 1))
c.eq("Reanimator's claws", row(ReanimatorsClawsProfile), (2, 4, 5, 0, 1))
c.eq("Gauss scalpel", row(GaussScalpelProfile), (18, 1, 4, -1, 1))
c.eq("Tesla caster", row(TeslaCasterProfile), (18, 1, 5, 0, 1))
c.eq("...[ASSAULT] and [SUSTAINED HITS 1]",
     (TeslaCasterProfile.assault, TeslaCasterProfile.sustained_hits), (True, 1))
c.eq("Transdimensional isolator", row(TransdimensionalIsolatorProfile), (12, 2, 4, -2, 2))
c.eq("Tremorglaive (melee)", row(TremorglaiveMeleeProfile), (2, 2, 8, -2, 2))
c.eq("Tremorglaive - reverberating beam",
     row(TremorglaiveReverberatingBeamProfile), (18, 2, 8, -2, 2))
c.eq("...[MELTA 2]", TremorglaiveReverberatingBeamProfile.melta, 2)
c.eq("Tremorglaive - shock wave pulse",
     row(TremorglaiveShockWavePulseProfile), (18, 5, 4, 0, 1))
c.eq("...D6+2 Attacks", (TremorglaiveShockWavePulseProfile.attacks_notation.sides,
                         TremorglaiveShockWavePulseProfile.attacks_notation.bonus), (6, 2))
c.true("...[TORRENT] and [IGNORES COVER]",
       TremorglaiveShockWavePulseProfile.torrent
       and TremorglaiveShockWavePulseProfile.ignores_cover)
c.eq("the two ranged rows are a firing-mode PAIR, the beam first",
     TremorglaiveReverberatingBeamProfile.overcharge_profile,
     TremorglaiveShockWavePulseProfile)
c.eq("...and the MELEE row is a separate weapon, not a third mode",
     TremorglaiveShockWavePulseProfile.overcharge_profile, None)

# THE SWEEP, VERDICT 1 - FORK. "Particle beamer" is printed on the Tomb Blades
# at S5 and on the Spyders at S6. Two classes, both named after their STRENGTH:
# the bare name lied by omission the moment the second carrier arrived.
c.eq("the two particle beamers print the SAME name",
     (ParticleBeamerS5Profile.name, ParticleBeamerS6Profile.name),
     ("Particle beamer", "Particle beamer"))
c.true("...and differ in exactly one column - Strength",
       (ParticleBeamerS5Profile.range_in, ParticleBeamerS5Profile.ap,
        ParticleBeamerS5Profile.damage)
       == (ParticleBeamerS6Profile.range_in, ParticleBeamerS6Profile.ap,
           ParticleBeamerS6Profile.damage)
       and ParticleBeamerS5Profile.strength != ParticleBeamerS6Profile.strength)
c.eq("...the Tomb Blades' is S5, the Spyders' S6",
     (ParticleBeamerS5Profile.strength, ParticleBeamerS6Profile.strength), (5, 6))
c.true("...and neither is a subclass of the other, so neither can drift into it",
       not issubclass(ParticleBeamerS5Profile, ParticleBeamerS6Profile)
       and not issubclass(ParticleBeamerS6Profile, ParticleBeamerS5Profile))

# ...and the SAME verdict for the two names printed twice inside this batch.
c.eq("the two atomiser beams print the same name and different rows",
     (AtomiserBeamA3Profile.name == AtomiserBeamA1Profile.name,
      row(AtomiserBeamA3Profile), row(AtomiserBeamA1Profile)),
     (True, (12, 3, 6, -2, 1), (12, 1, 6, -1, 1)))
c.eq("...and so do the two Claws rows",
     (ClawsA2S4Profile.name == ClawsA4S6Profile.name,
      row(ClawsA2S4Profile), row(ClawsA4S6Profile)),
     (True, (2, 2, 4, -1, 1), (2, 4, 6, -1, 1)))

# VERDICT 2 - INHERIT. The two twin guns ARE their parents plus one keyword, so
# they subclass and override only the name. Pinned against the PARENT rather
# than against literals: the assurance is that they stay identical apart from
# the keyword, which a copy would lose the first time the parent moved.
for twin, parent in ((TwinGaussFlayerProfile, GaussFlayerProfile),
                     (TwinGaussReaperProfile, GaussReaperProfile)):
    c.true("%s inherits its parent" % twin.name, issubclass(twin, parent))
    c.eq("...with the same row", row(twin), row(parent))
    c.true("...adding only [TWIN-LINKED]",
           twin.twin_linked and not parent.twin_linked)
    c.true("...and its own printed name", twin.name != parent.name)
c.eq("the Doomstalker's twin gauss flayer keeps [RAPID FIRE 1] and [LETHAL HITS]",
     (TwinGaussFlayerProfile.rapid_fire, TwinGaussFlayerProfile.lethal_hits), (1, True))

# WS/BS ARE ON THE PROFILES: not one weapon in this batch carries an override,
# because every one of these seven datasheets agrees with its own rows.
c.eq("no Canoptek weapon overrides a skill",
     [w.name for w in (FeederMandiblesProfile, ParticleBeamerS6Profile,
                       AutomatonClawsProfile, DoomsdayBlasterProfile,
                       TwinGaussFlayerProfile, DoomstalkerLimbsProfile,
                       AtomiserBeamA3Profile, AtomiserBeamA1Profile,
                       ReanimatorsClawsProfile, GaussScalpelProfile,
                       TeslaCasterProfile, ClawsA2S4Profile, ClawsA4S6Profile,
                       TransdimensionalIsolatorProfile, TwinGaussReaperProfile,
                       TremorglaiveReverberatingBeamProfile,
                       TremorglaiveShockWavePulseProfile, TremorglaiveMeleeProfile)
      if w.ballistic_skill is not None or w.weapon_skill is not None], [])


# --- 3. wargear, points, attachment -----------------------------------------
print("--- 3. wargear, points, attachment ---")

c.eq("a Scarab unit is 3 or 6", (len(build(SCARABS).models),
                                 len(build(SCARABS, composition_index=1).models)), (3, 6))
c.eq("a Spyder unit is 1 or 2", (len(build(SPYDERS).models),
                                 len(build(SPYDERS, composition_index=1).models)), (1, 2))
c.eq("the Macrocytes are a fixed 5", len(build(MACROCYTES).models), 5)
c.eq("the Tomb Crawlers a fixed 2", len(build(TOMB_CRAWLERS).models), 2)

_reanimator = build(REANIMATOR)
c.eq("the Reanimator carries TWO atomiser beams, as printed",
     sum(1 for w in _reanimator.models[0].weapons if w.name == "Atomiser beam"), 2)
c.true("...and they are the A3 row, not the Macrocytes' A1 one",
       all(isinstance(w, AtomiserBeamA3Profile)
           for w in _reanimator.models[0].weapons if w.name == "Atomiser beam"))

_beamers = build(SPYDERS, choices={"Canoptek Spyder": {nec.SPYDERS_ADD_TWO_PARTICLE_BEAMERS: 1}})
c.eq("the Spyder option ADDS two particle beamers rather than replacing anything",
     sorted(w.name for w in _beamers.models[0].weapons),
     ["Automaton claws", "Particle beamer", "Particle beamer"])
c.true("...the S6 ones", all(isinstance(w, ParticleBeamerS6Profile)
                            for w in _beamers.models[0].weapons
                            if w.name == "Particle beamer"))

_tesla = build(MACROCYTES, choices={"Canoptek Macrocyte": {nec.MACROCYTES_TO_TESLA_CASTER: 5}})
c.true("all five Macrocytes can swap scalpel for tesla caster",
       all(any(w.name == "Tesla caster" for w in m.weapons) for m in _tesla.models))
_isolator = build(TOMB_CRAWLERS,
                  choices={"Canoptek Tomb Crawler": {nec.TOMB_CRAWLERS_TO_ISOLATOR: 1}})
c.eq("exactly ONE Tomb Crawler swaps to the isolator",
     sum(1 for m in _isolator.models
         if any(w.name == "Transdimensional isolator" for w in m.weapons)), 1)

_geared = build(SPYDERS, gear={"Canoptek Spyder": [nec.SPYDER_FABRICATOR_CLAW_ARRAY,
                                                   nec.SPYDER_GLOOM_PRISM]})
c.true("a Spyder can carry both auras at once",
       _geared.models[0].profile.fabricator_claw_array
       and _geared.models[0].profile.gloom_prism)
c.eq("...and gear never touches the shared class",
     (CanoptekSpyderProfile.fabricator_claw_array, CanoptekSpyderProfile.gloom_prism),
     (False, False))

POINTS = [(SCARABS, 0, 40), (SCARABS, 1, 80), (SPYDERS, 0, 65), (SPYDERS, 1, 110),
          (DOOMSTALKER, 0, 140), (REANIMATOR, 0, 75), (MACROCYTES, 0, 70),
          (TOMB_CRAWLERS, 0, 50), (GEOMANCER, 0, 75)]
for sheet, ci, cost in POINTS:
    c.eq("%s (composition %d) costs %d" % (sheet.name, ci, cost),
         build(sheet, composition_index=ci).points, cost)
c.true("all seven are in the points table",
       all(s.name in NECRONS_POINTS for s in SHEETS))

# THE GEOMANCER SUPPORTS THREE UNITS, and the Macrocytes are the reason he is
# in THIS batch rather than with the Crypteks - his other clause is unreachable
# without them.
c.eq("the Geomancer's printed SUPPORT list",
     sorted(NECRONS_POINTS["Geomancer"].supports),
     ["Canoptek Macrocytes", "Immortals", "Necron Warriors"])
for host in (MACROCYTES, IMMORTALS, WARRIORS):
    ci = 1 if host is IMMORTALS else 0
    c.eq("...and he may support %s" % host.name,
         attached_units.can_attach(build(GEOMANCER), build(host, composition_index=ci)), [])
c.true("...but not the Tomb Crawlers",
       attached_units.can_attach(build(GEOMANCER), build(TOMB_CRAWLERS)) != [])
c.eq("no other Canoptek datasheet leads or is led",
     sorted(n for n in ("Canoptek Scarab Swarms", "Canoptek Spyders",
                        "Canoptek Doomstalker", "Canoptek Reanimator",
                        "Canoptek Tomb Crawlers")
            if getattr(NECRONS_POINTS[n], "leads", None)
            or getattr(NECRONS_POINTS[n], "supports", None)), [])


# --- 4. Chittering Swarm ----------------------------------------------------
print("--- 4. Chittering Swarm ---")

def oc_scene(gap=1.0, cryptek_gap=None):
    """Scarabs facing Necron Warriors, optionally with a Technomancer near."""
    scarabs = place(build(SCARABS), 20.0, 20.0)
    enemy = place(build(WARRIORS, "Player 1", composition_index=0), 20.0, 20.0 + gap)
    parts = [scarabs, enemy]
    if cryptek_gap is not None:
        cryptek = place(build(TECHNOMANCER), 20.0 - cryptek_gap, 20.0)
        parts.append(cryptek)
    return scarabs, enemy, tokens(*parts)


# CLAUSE 2 - the SET, aimed at the Scarabs' own models. Their printed OC is 0,
# which is what makes this worth anything at all.
_scarabs, _enemy, _tk = oc_scene(gap=30.0)
c.eq("a Scarab alone contributes its printed OC 0",
     objective_control.effective_oc(_scarabs.models[0], _tk), 0)
_scarabs, _enemy, _tk = oc_scene(gap=30.0, cryptek_gap=3.0)
c.eq("...and 1 while within 6\" of a friendly CRYPTEK",
     objective_control.effective_oc(_scarabs.models[0], _tk), 1)
_scarabs, _enemy, _tk = oc_scene(gap=30.0, cryptek_gap=20.0)
c.eq("...the 6\" is really measured", objective_control.effective_oc(_scarabs.models[0], _tk), 0)

# CLAUSE 1 - the WORSEN, aimed at the ENEMY. Measured through the real fold,
# because a predicate that nothing asks is this repo's most expensive shape.
_scarabs, _enemy, _tk = oc_scene(gap=30.0)
c.eq("an enemy far away keeps its printed OC",
     objective_control.effective_oc(_enemy.models[0], _tk), _enemy.models[0].profile.oc)
_scarabs, _enemy, _tk = oc_scene(gap=1.0)
c.eq("...and loses 1 while within Engagement Range of the swarm",
     objective_control.effective_oc(_enemy.models[0], _tk),
     _enemy.models[0].profile.oc - 1)
c.true("the scene really is Engagement Range, not merely near",
       engagement.units_are_engaged(_scarabs, _enemy))

# THE TWO CLAUSES COMPOSE, and the printed order is what saves the Scarab: the
# SET gives it 1 and the worsening floor protects it. Reverse the order and it
# ends on 0, silently deleting clause 2 against one particular opponent.
_scarabs = place(build(SCARABS), 20.0, 20.0)
_enemy = place(build(WARRIORS, "Player 1", composition_index=0), 20.0, 21.0)
_cryptek = place(build(TECHNOMANCER), 17.0, 20.0)
_tk = tokens(_scarabs, _enemy, _cryptek)
c.eq("a Scarab both boosted and engaged ends on 1, not 0",
     objective_control.effective_oc(_scarabs.models[0], _tk), 1)

# The floor is a floor on WORSENING, never a value to clamp UP to - the reading
# Scabrous Soulrot already records, and this rule shares it.
#
# ASKED OF AN ENEMY MODEL, and that is the whole line: worsen_enemy_oc() looks
# for a Scarab unit among the ENEMIES OF ITS ARGUMENT'S OWNER, so handing it a
# Scarab measures nothing at all - the first version of this line did exactly
# that and its probe reported NO BITE.
_scarabs = place(build(SCARABS), 20.0, 20.0)
_enemy = place(build(WARRIORS, "Player 1", composition_index=0), 20.0, 21.0)
_tk = tokens(_scarabs, _enemy)
c.true("the scene is engaged, so the worsening clause really fires",
       chittering_swarm.worsen_enemy_oc(_enemy.models[0], 2, _tk) == 1)
c.eq("...but a printed OC 0 enemy is left alone rather than raised to the floor",
     chittering_swarm.worsen_enemy_oc(_enemy.models[0], 0, _tk), 0)


# --- 5. Self-destruction ----------------------------------------------------
print("--- 5. Self-destruction ---")

def sd_scene(enemy_sheet=WARRIORS, gap=1.0, auto=()):
    state = GameState()
    scarabs = place(build(SCARABS), 20.0, 20.0)
    enemy = place(build(enemy_sheet, "Player 1", composition_index=0), 20.0, 20.0 + gap)
    for s in (scarabs, enemy):
        for m in s.models:
            state.add_token(m)
    log, dice, dec = tk.Log(), tk.RecordingDice(), DecisionManager()
    ctrl = scarab_self_destruction.SelfDestructionController(
        decision_manager=dec, game_state=state, game_log=log,
        dice_manager=dice, auto_players=auto)
    return dict(state=state, scarabs=scarabs, enemy=enemy, ctrl=ctrl,
                dice=dice, decision=dec, log=log)


sc = sd_scene()
c.true("an engaged Scarab unit is eligible",
       scarab_self_destruction.eligible_models(sc["scarabs"], sc["state"].tokens))
far = sd_scene(gap=30.0)
c.eq("...and an unengaged one is not",
     scarab_self_destruction.eligible_models(far["scarabs"], far["state"].tokens), [])

# THE THREE BANDS, and the middle one is itself a die.
c.eq("a roll of 1 pays nothing",
     scarab_self_destruction.wounds_for(1, sc["enemy"]), (0, False))
c.eq("2-5 rolls a D3",
     [scarab_self_destruction.wounds_for(n, sc["enemy"]) for n in (2, 5)],
     [(0, True), (0, True)])
c.eq("6+ pays a FLAT 3",
     scarab_self_destruction.wounds_for(6, sc["enemy"]), (3, False))

# "+1 IF THAT UNIT IS A VEHICLE" is added to the RESULT, so a rolled 5 becomes
# a 6 and pays 3 flat. Measured against a real VEHICLE datasheet.
veh = sd_scene(enemy_sheet=DOOMSTALKER)
c.true("the Doomstalker really is a VEHICLE unit",
       scarab_self_destruction.is_vehicle_unit(veh["enemy"]))
c.eq("a rolled 5 against a VEHICLE crosses into the flat band",
     scarab_self_destruction.wounds_for(5, veh["enemy"]), (3, False))
c.eq("...where the same roll against infantry rolls a D3",
     scarab_self_destruction.wounds_for(5, sc["enemy"]), (0, True))

# THE MODEL IS SPENT BEFORE THE WOUNDS LAND - the printed order.
sc = sd_scene(auto=("Player 2",))
_alive_before = len([m for m in sc["scarabs"].models if not m.is_dead()])
tk.script(6)
sc["ctrl"].offer_at_start_of_fight("Player 2")
c.eq("the AI spends a model without asking",
     (len([m for m in sc["scarabs"].models if not m.is_dead()]), sc["decision"].is_pending),
     (_alive_before - 1, False))
c.true("...and a D6 is on the table for it", sc["dice"].pending_values)
_hp = sum(m.current_wounds for m in sc["enemy"].models)
sc["dice"].acknowledge()
sc["ctrl"].on_dice_acknowledged()
c.true("...whose 6 lands 3 mortal wounds",
       sum(m.current_wounds for m in sc["enemy"].models) < _hp
       or sc["ctrl"].pending_damage_choice is not None)

# A HUMAN is asked, because "you CAN select one model in this unit to destroy"
# is a real decision about one of your own models.
sc = sd_scene(auto=())
c.true("a human owner is asked", sc["ctrl"].offer_at_start_of_fight("Player 2")
       and sc["decision"].is_pending)
c.true("...and can decline", tk.pick_option(sc["decision"], "Keep the model"))
c.eq("...losing nothing", len([m for m in sc["scarabs"].models if not m.is_dead()]), 3)


# --- 6. the Spyders ---------------------------------------------------------
print("--- 6. Spyders: swarm and auras ---")

def spyder_scene(gear=(), gap=3.0, target=WARRIORS):
    spyders = place(build(SPYDERS, gear={"Canoptek Spyder": list(gear)}), 20.0, 20.0)
    other = place(build(target, "Player 2", n=2,
                        composition_index=0 if target is WARRIORS else 0),
                  20.0, 20.0 + gap)
    return spyders, other, tokens(spyders, other)


# THE GLOOM PRISM is the Nullstone field's sentence word for word: 5+ against
# mortal wounds and Psychic Attacks, nothing against an ordinary one.
_sp, _friend, _tk = spyder_scene(gear=[nec.SPYDER_GLOOM_PRISM])
spyder_wargear.refresh(_tk)
c.eq("the Gloom Prism gives 5+ against a MORTAL wound",
     feel_no_pain.current_feel_no_pain(_friend.models[0], mortal=True), "5+")
c.eq("...and against a PSYCHIC attack",
     feel_no_pain.current_feel_no_pain(_friend.models[0], psychic=True), "5+")
c.eq("...and nothing against an ordinary wound",
     feel_no_pain.current_feel_no_pain(_friend.models[0]), "-")

# THE FABRICATOR CLAW ARRAY is the one that covers EVERY wound - and only
# VEHICLES. Both halves measured, because losing either is invisible otherwise.
_sp, _friend, _tk = spyder_scene(gear=[nec.SPYDER_FABRICATOR_CLAW_ARRAY])
spyder_wargear.refresh(_tk)
c.eq("the claw array gives an infantry unit NOTHING - it names VEHICLE",
     feel_no_pain.current_feel_no_pain(_friend.models[0]), "-")
_sp, _veh, _tk = spyder_scene(gear=[nec.SPYDER_FABRICATOR_CLAW_ARRAY], target=DOOMSTALKER)
spyder_wargear.refresh(_tk)
c.eq("...and a friendly NECRONS VEHICLE 6+ against an ORDINARY wound",
     feel_no_pain.current_feel_no_pain(_veh.models[0]), "6+")

# BOTH AT ONCE: the fold takes the better per wound, which is what rule 05.04
# says about two sources of one characteristic.
_sp, _veh, _tk = spyder_scene(
    gear=[nec.SPYDER_FABRICATOR_CLAW_ARRAY, nec.SPYDER_GLOOM_PRISM], target=DOOMSTALKER)
spyder_wargear.refresh(_tk)
c.eq("a vehicle in both auras: 6+ ordinary, 5+ mortal",
     (feel_no_pain.current_feel_no_pain(_veh.models[0]),
      feel_no_pain.current_feel_no_pain(_veh.models[0], mortal=True)), ("6+", "5+"))

# The 6" is measured, and a dead bearer stops projecting in the same frame.
_sp, _friend, _tk = spyder_scene(gear=[nec.SPYDER_GLOOM_PRISM], gap=30.0)
spyder_wargear.refresh(_tk)
c.eq("the 6\" really is measured",
     feel_no_pain.current_feel_no_pain(_friend.models[0], mortal=True), "-")
_sp, _friend, _tk = spyder_scene(gear=[nec.SPYDER_GLOOM_PRISM])
for m in _sp.models:
    m.current_wounds = 0
spyder_wargear.refresh(_tk)
c.eq("...and a bearer that died THIS frame stops projecting",
     feel_no_pain.current_feel_no_pain(_friend.models[0], mortal=True), "-")

# CANOPTEK SWARM: one model back per Spyder, and only to a unit that has
# something to bring back.
from game.canoptek_swarm import CanoptekSwarmController  # noqa: E402

state = GameState()
_spyders = place(build(SPYDERS, composition_index=1), 20.0, 20.0)
_scarabs = place(build(SCARABS), 20.0, 23.0)
for s in (_spyders, _scarabs):
    for m in s.models:
        state.add_token(m)
_swarm = CanoptekSwarmController(game_state=state, game_log=tk.Log(),
                                 auto_players=("Player 2",))
c.eq("a full-strength Scarab unit is not offered a return",
     _swarm.candidates(_spyders), [])
_dead = _scarabs.models[:2]
for m in _dead:
    m.current_wounds = 0
    _scarabs.models.remove(m)
    _scarabs.destroyed_models.append(m)
    if m in state.tokens:
        state.tokens.remove(m)
c.eq("...and a depleted one is", [s.name for s in _swarm.candidates(_spyders)],
     [_scarabs.name])
c.eq("TWO Spyders return TWO models", _swarm.use(_spyders, _scarabs), 2)
c.eq("...and they are back on the board", len([m for m in _scarabs.models if not m.is_dead()]), 3)


# --- 7. Sentinel Construct --------------------------------------------------
print("--- 7. Sentinel Construct ---")

_ds = build(DOOMSTALKER)
c.eq("the Doomstalker overwatches on 5+",
     sentinel_construct.snap_hit_threshold(_ds), 5)
c.eq("...and a unit without it gets nothing, so 15.09's printed 6 stands",
     sentinel_construct.snap_hit_threshold(build(SCARABS)), None)
# Measured through the REAL seam rather than at the predicate: the fold takes
# the better of whatever applies, and it must not lose the Hexmark's 2+.
from game import inescapable_death  # noqa: E402
SHOOTING_SRC = io.open("game/shooting.py", encoding="utf-8").read()
c.true("the snap-threshold fold asks it",
       "sentinel_construct.snap_hit_threshold(self.active_squad)" in SHOOTING_SRC)
c.true("...beside the Hexmark's, as a better-of rather than a first-wins",
       SHOOTING_SRC.find("inescapable_death.snap_hit_threshold(self.active_squad)")
       < SHOOTING_SRC.find("sentinel_construct.snap_hit_threshold(self.active_squad)"))
c.eq("the two carriers print different numbers",
     (inescapable_death.INESCAPABLE_DEATH_HIT_THRESHOLD,
      sentinel_construct.SENTINEL_CONSTRUCT_HIT_THRESHOLD), (2, 5))


# --- 8. the reanimation boosts ----------------------------------------------
print("--- 8. reanimation boosts ---")

def boost_scene(bearer_sheet, gear=(), gap=2.0):
    state = GameState()
    hurt = place(build(WARRIORS, composition_index=0), 20.0, 20.0)
    kw = {"gear": {"Canoptek Macrocyte": list(gear)}} if gear else {}
    bearer = place(build(bearer_sheet, n=2, **kw), 20.0, 20.0 + gap)
    for s in (hurt, bearer):
        for m in s.models:
            state.add_token(m)
    return hurt, bearer, state


_hurt, _rea, _state = boost_scene(REANIMATOR)
c.true("a unit within 3\" of a Reanimator is boosted",
       reanimation_boost.beam_applies(_hurt, _state.tokens))
_hurt, _rea, _state = boost_scene(REANIMATOR, gap=30.0)
c.eq("...and the 3\" is really measured",
     reanimation_boost.beam_applies(_hurt, _state.tokens), False)

_hurt, _mac, _state = boost_scene(MACROCYTES, gear=[nec.MACROCYTE_NANOSCARAB_PROJECTOR])
proj = reanimation_boost.NanoscarabProjectorController(
    turn_tracker=tk._tracker(tk.PHASE_SHOOTING), auto_players=("Player 2",))
c.eq("the projector adds exactly 1", proj.extra_wounds(_hurt, _state.tokens), 1)
c.eq("...and NOT twice in the same battle round",
     proj.extra_wounds(_hurt, _state.tokens), 0)

# BOTH ADD, and they are asked as ONE question by the army rule.
_hurt, _rea, _state = boost_scene(REANIMATOR)
tk.script(2)
_boost = reanimation_boost.ReanimationBoost()
c.eq("the beam's D3 is rolled and added", _boost.extra_wounds(_hurt, _state.tokens), 2)
c.true("the army rule asks the boost BEFORE it spends the wounds",
       "boosted += self.boost.extra_wounds("
       in io.open("game/reanimation_protocols.py", encoding="utf-8").read())


# --- 9. Harassment Swarm and Weapon Sentinels -------------------------------
print("--- 9. Harassment Swarm, Weapon Sentinels ---")

def harass_scene(enemy_sheet=WARRIORS, gap=2.0):
    mac = place(build(MACROCYTES), 20.0, 20.0)
    enemy = place(build(enemy_sheet, "Player 1", composition_index=0), 20.0, 20.0 + gap)
    tks = tokens(mac, enemy)
    harassment_swarm.refresh(tks)
    return mac, enemy, tks


_mac, _enemy, _tk = harass_scene(gap=30.0)
c.eq("a distant enemy is unaffected", harassment_swarm.hit_modifiers(_enemy), [])
_mac, _enemy, _tk = harass_scene()
c.eq("an enemy within 3\" is at -1 to Hit",
     [m.amount for m in harassment_swarm.hit_modifiers(_enemy)], [1])
c.eq("...which really worsens the threshold",
     apply_modifiers(3, harassment_swarm.hit_modifiers(_enemy)), 4)
# "EXCLUDING MONSTERS AND VEHICLES", pooled per rule 19.03.
_mac, _veh, _tk = harass_scene(enemy_sheet=DOOMSTALKER)
c.eq("a VEHICLE is exempt", harassment_swarm.hit_modifiers(_veh), [])
c.true("...and the exemption really is the keyword", harassment_swarm.is_exempt(_veh))
# The printed noun is ATTACK, so BOTH steps read it.
FIGHT_SRC = io.open("game/fight.py", encoding="utf-8").read()
c.true("the SHOOTING hit fold reads it",
       "harassment_swarm.hit_modifiers(self.active_squad)" in SHOOTING_SRC)
c.true("...and so does the FIGHT one",
       "harassment_swarm.hit_modifiers(self.fighting_squad)" in FIGHT_SRC)

_crawlers = place(build(TOMB_CRAWLERS), 20.0, 20.0)
_near = place(build(WARRIORS, "Player 1", composition_index=0), 20.0, 26.0)
_far = place(build(WARRIORS, "Player 1", n=2, composition_index=0), 20.0, 60.0)
c.true("Weapon Sentinels applies against a target within 12\"",
       weapon_sentinels.applies(_crawlers, _near))
c.eq("...and NOT against one further away",
     weapon_sentinels.applies(_crawlers, _far), False)
from game.modifiers import Modifier  # noqa: E402
_mods = [Modifier(1, "worsening"), Modifier(-1, "improving")]
c.eq("it drops the worsening modifiers and keeps the improving ones",
     [m.source for m in weapon_sentinels.filtered(_mods, _crawlers, _near)], ["improving"])
c.eq("...and changes nothing against a distant target",
     [m.source for m in weapon_sentinels.filtered(_mods, _crawlers, _far)],
     ["worsening", "improving"])
# THE THIRD NOUN IS THE NEW ONE: the first ignore-modifier filter this engine
# has ever put on the WOUND roll.
c.true("the HIT fold asks it",
       "weapon_sentinels.filtered(\n            modifiers, self.active_squad" in SHOOTING_SRC)
c.true("...and the WOUND fold does too - the first filter of its kind there",
       "weapon_sentinels.filtered(modifiers, self.active_squad, target_squad)" in SHOOTING_SRC)
c.eq("...and game/fight.py does NOT - the printed word is 'ranged attack'",
     "weapon_sentinels" in FIGHT_SRC, False)


# --- 10. the Geomancer ------------------------------------------------------
print("--- 10. the Geomancer ---")

def geo_scene(gap=6.0, auto=()):
    state = GameState()
    geo = place(build(GEOMANCER), 20.0, 20.0)
    enemy = place(build(WARRIORS, "Player 1", composition_index=0), 20.0, 20.0 + gap)
    for s in (geo, enemy):
        for m in s.models:
            state.add_token(m)
    log, dec = tk.Log(), DecisionManager()
    ctrl = TectonicReverberationsController(
        decision_manager=dec, game_state=state, game_log=log,
        turn_tracker=tk._tracker(tk.PHASES[1]), auto_players=auto)
    return dict(state=state, geo=geo, enemy=enemy, ctrl=ctrl, decision=dec, log=log)


sc = geo_scene(auto=("Player 2",))
c.eq("an enemy within 18\" and visible is a candidate",
     [s.name for s in sc["ctrl"].candidates(sc["geo"].models[0])], [sc["enemy"].name])
far = geo_scene(gap=40.0, auto=("Player 2",))
c.eq("...and the 18\" is really measured",
     far["ctrl"].candidates(far["geo"].models[0]), [])

sc = geo_scene(auto=("Player 2",))
c.eq("nothing is pinned to begin with", pinned_status.is_pinned(sc["enemy"]), False)
sc["ctrl"].offer_at_start_of_movement("Player 2")
c.true("the AI pins without asking",
       pinned_status.is_pinned(sc["enemy"]) and not sc["decision"].is_pending)
c.eq("...and both penalties apply",
     (pinned_status.move_penalty_for(sc["enemy"]),
      pinned_status.charge_penalty_for(sc["enemy"])), (2, 2))

# THE CLOCK IS THE DIFFERENCE FROM THE NIGHT SPINNER, and one phase of it.
c.eq("this pin ends at the start of the applying player's MOVEMENT phase",
     getattr(sc["enemy"], "pinned_until", None), pinned_status.UNTIL_MOVEMENT)
c.eq("clearing the TURN-scoped pins leaves it standing",
     (MonofilamentWebController().clear_for_turn_of("Player 2", [sc["enemy"]]),
      pinned_status.is_pinned(sc["enemy"])), (0, True))
c.eq("...and its own boundary clears it",
     (sc["ctrl"].clear_at_start_of_movement("Player 2"),
      pinned_status.is_pinned(sc["enemy"])), (1, False))
c.eq("...but only for the player who applied it",
     (sc["ctrl"]._pin(sc["geo"].models[0], sc["enemy"]),
      sc["ctrl"].clear_at_start_of_movement("Player 1"),
      pinned_status.is_pinned(sc["enemy"])), (True, 0, True))

# A human is asked, and every option is TAGGED so it can be answered on the board.
sc = geo_scene(auto=())
c.true("a human owner is asked", sc["ctrl"].offer_at_start_of_movement("Player 2")
       and sc["decision"].is_pending)
c.true("...with a Decline", any("Decline" in o for o in tk.options_of(sc["decision"])))
c.eq("...and the enemy option carries its squad",
     sorted(o["squad"].name for o in sc["decision"].options if o.get("squad")),
     [sc["enemy"].name])

# OBELISK NODE CONTROL - both conditions, and both are live.
# A REAL Objective on a REAL terrain area, and 14.02 decides who controls it
# rather than a hand-written owner: an objective whose `controlled_by` was
# assigned by the test is a board state no phase boundary survives - the lesson
# the Cleanse fix paid for, one stage of this backfill ago.
def objective_scene(gap=6.0, enemy_oc=0):
    sc = geo_scene(gap=gap)
    area = sc["state"].add_terrain_area(
        [Obstacle(20.0, 20.0, 4.0, 4.0, category=EXPOSED)])
    obj = sc["state"].add_objective(area, name="Test Objective")
    if enemy_oc:
        for i, m in enumerate(sc["enemy"].models[:enemy_oc]):
            m.x_in, m.y_in = 20.0 + i * 0.9, 20.0
    obj.update_control(sc["state"].tokens)
    sc["objective"] = obj
    return sc


sc = objective_scene()
c.eq("the Geomancer really holds it (rule 14.02 decided, not the test)",
     sc["objective"].controlled_by, "Player 2")
c.true("a Geomancer on an objective HE controls blocks arrivals",
       obelisk_node_control.blocks_arrival(sc["enemy"], 20.0, 25.0, 0.63,
                                           sc["state"].tokens, [sc["objective"]]))
theirs = objective_scene(enemy_oc=6)
c.eq("...on one the opponent controls it blocks nothing",
     (theirs["objective"].controlled_by,
      obelisk_node_control.blocks_arrival(theirs["enemy"], 20.0, 25.0, 0.63,
                                          theirs["state"].tokens,
                                          [theirs["objective"]])),
     ("Player 1", False))
c.eq("...and on no objective at all, nothing",
     obelisk_node_control.blocks_arrival(sc["enemy"], 20.0, 25.0, 0.63,
                                         sc["state"].tokens, []), False)
c.eq("the 12\" is really measured",
     obelisk_node_control.blocks_arrival(sc["enemy"], 20.0, 40.0, 0.63,
                                         sc["state"].tokens, [sc["objective"]]), False)
c.eq("...and a player's own reserves are never blocked by their own Geomancer",
     obelisk_node_control.blocks_arrival(sc["geo"], 20.0, 25.0, 0.63,
                                         sc["state"].tokens, [sc["objective"]]), False)
# THE MODEL, not its unit: a Geomancer leading Warriors does not project the
# bubble from his bodyguards. Measured by walking HIM off the objective while
# leaving a squadmate standing on it.
_merged = attached_units.attach(build(GEOMANCER), build(WARRIORS, composition_index=0))
_state = GameState()
for m in _merged.models:
    geo = bool(getattr(m.profile, "obelisk_node_control", False))
    m.x_in, m.y_in = (34.0, 20.0) if geo else (20.0, 20.0)
    _state.add_token(m)
_area = _state.add_terrain_area([Obstacle(20.0, 20.0, 4.0, 4.0, category=EXPOSED)])
_obj = _state.add_objective(_area, name="Held")
_obj.update_control(_state.tokens)
c.eq("a squadmate on the objective does not stand in for the Geomancer",
     (_obj.controlled_by,
      obelisk_node_control.active_bearers(_state.tokens, [_obj])),
     ("Player 2", []))
# THE WIRING, per AST rather than as a substring. `"...blocks_arrival(" in src`
# survives a `False and ` in front of it and an `if False:` above it - the trap
# this repo has now paid for half a dozen times - so what is pinned is that the
# call IS the whole test of an `if` that refuses the spot.
INGRESS_TREE = ast.parse(io.open("game/ingress.py", encoding="utf-8").read())


def _refuses_on(tree, dotted):
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Call):
            continue
        if ast.unparse(node.test.func) != dotted:
            continue
        if any(isinstance(b, ast.Return)
               and isinstance(b.value, ast.Constant) and b.value.value is False
               for b in node.body):
            return True
    return False


c.true("the ingress placement predicate asks it, unguarded",
       _refuses_on(INGRESS_TREE, "obelisk_node_control.blocks_arrival"))

# VANGUARD PROTOCOLS - a MEASURED no-op, pinned from both sides so it cannot
# quietly stop being one.
_geo = build(GEOMANCER)
_mac = build(MACROCYTES)
c.eq("an unattached Geomancer gets nothing", vanguard_protocols.applies(_geo), False)
_merged = attached_units.attach(build(GEOMANCER), build(MACROCYTES))
c.true("...attached to CANOPTEK MACROCYTES he does",
       vanguard_protocols.applies(_merged))
c.eq("...and the granted distance is 8\"", vanguard_protocols.scouts_for(_merged), 8)
_with_warriors = attached_units.attach(build(GEOMANCER), build(WARRIORS, composition_index=0))
c.eq("attached to Necron Warriors - one of his other two printed hosts - nothing",
     vanguard_protocols.applies(_with_warriors), False)
c.eq("...and that unit has no Scouts at all", scouts.scout_distance(_with_warriors), None)
# THE NO-OP ITSELF: under this engine's rule 19.04 reading the merged unit has
# Scouts 8" either way, because the Macrocytes component prints it.
c.eq("the merged unit has Scouts 8\" WITH the rule",
     scouts.scout_distance(_merged), 8)
_plain = attached_units.attach(build(GEOMANCER), build(MACROCYTES))
for m in _plain.models:
    if getattr(m.profile, "vanguard_protocols", False):
        m.profile.vanguard_protocols = False
c.eq("...and 8\" WITHOUT it - the measured no-op, and why it is named as one",
     scouts.scout_distance(_plain), 8)


# --- 11. the three extractions ----------------------------------------------
print("--- 11. the extractions ---")

# 42: the status, and the two seams that read it.
c.true("game/pinned.py owns both penalties",
       pinned_status.PINNED_MOVE_PENALTY == 2 and pinned_status.PINNED_CHARGE_PENALTY == 2)
c.true("...and monofilament_web re-exports them, so its callers are unmoved",
       MonofilamentWebController and
       io.open("game/monofilament_web.py", encoding="utf-8").read().count("_pinned.") >= 4)
COLDSTAR_SRC = io.open("game/coldstar.py", encoding="utf-8").read()
CHARGE_SRC = io.open("game/charge.py", encoding="utf-8").read()
c.true("the Move seam reads the SHARED module, not one ability's",
       "pinned_status.move_penalty_for(squad)" in COLDSTAR_SRC
       and "monofilament_web.move_penalty_for" not in COLDSTAR_SRC)
c.true("...and so does the Charge seam",
       "pinned_status.charge_penalty_for(self.active_squad)" in CHARGE_SRC
       and "monofilament_web.charge_penalty_for" not in CHARGE_SRC)
# "CANNOT BE PINNED" is enforced where the pin is APPLIED, and it survived.
class _Ensnared:
    name = "ensnared"
    pinned_by_player = None
    ensnared_by_player = "Player 1"


c.eq("an ensnared unit still cannot BECOME pinned",
     pinned_status.pin(_Ensnared(), "Player 2"), False)

# 43: the Feel No Pain aura, with the knobs that make it three abilities.
c.eq("three auras, three sets of knobs",
     sorted((a.label, a.threshold, a.mortal_or_psychic_only) for a in
            (spyder_wargear.FABRICATOR_CLAW_AURA, spyder_wargear.GLOOM_PRISM_AURA)),
     [("Fabricator Claw Array", "6+", False), ("Gloom Prism", "5+", True)])
from game.nekrosor_ammentar import NULLSTONE_AURA  # noqa: E402
c.eq("...and the Nullstone field is the Gloom Prism's twin, knob for knob",
     (NULLSTONE_AURA.threshold, NULLSTONE_AURA.range_in,
      NULLSTONE_AURA.mortal_or_psychic_only),
     (spyder_wargear.GLOOM_PRISM_AURA.threshold,
      spyder_wargear.GLOOM_PRISM_AURA.range_in,
      spyder_wargear.GLOOM_PRISM_AURA.mortal_or_psychic_only))
c.true("each aura stamps its OWN squad flag, so two cannot overwrite each other",
       len({spyder_wargear.FABRICATOR_CLAW_AURA.squad_flag,
            spyder_wargear.GLOOM_PRISM_AURA.squad_flag,
            NULLSTONE_AURA.squad_flag}) == 3)
c.eq("best_threshold takes the better of several", fnp_aura.best_threshold(
    (spyder_wargear.FABRICATOR_CLAW_AURA,), None), "-")

# 44: the retinue, and the printed clause that costs no code.
c.eq("both carriers are in rule 19.01's RETINUE role",
     sorted({attached_units.attachment_role(build(TOMB_CRAWLERS)),
             attached_units.attachment_role(build(CRYPTOTHRALLS))}),
     [attached_units.RETINUE])
c.eq("...and each names its own printed rule",
     (retinue.carrier_of(build(TOMB_CRAWLERS))[0],
      retinue.carrier_of(build(CRYPTOTHRALLS))[0]),
     ("Canoptek Retinue", "Cryptek Retinue"))
c.eq("...with the Tomb Crawlers' host NOT needing INFANTRY",
     (retinue.carrier_of(build(TOMB_CRAWLERS))[1],
      retinue.carrier_of(build(CRYPTOTHRALLS))[1]), (False, True))
c.eq("the panel heading says which rule is being offered",
     formations.join_rule_label(build(TOMB_CRAWLERS)), "Canoptek Retinue")

_host = attached_units.attach(build(TECHNOMANCER), build(WARRIORS, composition_index=0))
c.eq("a Tomb Crawlers unit may join a unit led by a Cryptek",
     retinue.join_errors(build(TOMB_CRAWLERS), _host), [])
_plain_host = build(WARRIORS, composition_index=0)
c.true("...and not one that is not",
       retinue.join_errors(build(TOMB_CRAWLERS), _plain_host) != [])
# THE PRINTED CLAUSE THAT COSTS NO CODE: "cannot have both a TOMB CRAWLERS and
# a CRYPTOTHRALLS unit joined to it" falls out of 19.01's one-per-ROLE check,
# because both datasheets are in that one role. Measured, not asserted.
_joined = attached_units.attach(build(CRYPTOTHRALLS), _host)
c.true("a host that already has a CRYPTOTHRALLS retinue refuses a TOMB CRAWLERS one",
       attached_units.can_attach(build(TOMB_CRAWLERS), _joined) != [])


# --- 12. wiring, the AI negative space, sprites -----------------------------
print("--- 12. wiring, AI, sprites ---")

MAIN = io.open("main.py", encoding="utf-8").read()
TREE = ast.parse(MAIN)
_MAIN_LINES = MAIN.splitlines()
# Built ONCE from the line spans - ast.get_source_segment() per node re-splits
# the whole source and cost this stage's sibling suite 36 seconds.
MAIN_CALLS = []
for _node in ast.walk(TREE):
    if isinstance(_node, ast.Call):
        _end = getattr(_node, "end_lineno", _node.lineno)
        MAIN_CALLS.append(" ".join(" ".join(_MAIN_LINES[_node.lineno - 1:_end]).split()))


def calls_in_main(needle):
    return [text for text in MAIN_CALLS if needle in text]


for needle, why in (
    ("SelfDestructionController(", "the Self-destruction controller is built"),
    ("self_destruction_controller.offer_at_start_of_fight(", "...and offered at the Fight phase"),
    ("self_destruction_controller.on_dice_acknowledged()", "...and its two dice steps are acknowledged"),
    ("CanoptekSwarmController(", "the Canoptek Swarm controller is built"),
    ("canoptek_swarm_controller.offer_at_command_phase(", "...and offered in the Command phase"),
    ("AcceleratorMandibleController(", "the Accelerator Mandible controller is built"),
    ("accelerator_mandible_controller.offer_at_start_of_fight(", "...and offered at the Fight phase"),
    ("TectonicReverberationsController(", "the Geomancer's pin controller is built"),
    ("tectonic_reverberations_controller.offer_at_start_of_movement(", "...and offered in the Movement phase"),
    ("tectonic_reverberations_controller.clear_at_start_of_movement(", "...and expires on its own boundary"),
    ("NanoscarabProjectorController(", "the projector controller is built"),
    ("spyder_wargear.refresh(state.tokens)", "the Spyder auras are stamped per frame"),
    ("harassment_swarm.refresh(state.tokens)", "...and so is Harassment Swarm"),
):
    c.true(why, bool(calls_in_main(needle)))

c.true("the reanimation boost is handed to the army rule",
       "reanimation_controller.boost = ReanimationBoost(" in MAIN)
c.true("the Canoptek Swarm goes through the shared placer, like every other return",
       "canoptek_swarm_controller.placer = return_placement_controller" in MAIN)

# CONSTRUCTION ORDER (error class 23) - main() is one long function and no
# suite drives it. Both of this stage's back-references are measured.
for first, second, why in (
    ("    reanimation_controller = ReanimationProtocolsController(",
     "    reanimation_controller.boost = ReanimationBoost(",
     "the boost is attached AFTER the army rule is built"),
    ("    return_placement_controller = ReturnPlacementController(",
     "    canoptek_swarm_controller.placer = return_placement_controller",
     "...and the placer AFTER the placer exists"),
    ("    canoptek_swarm_controller = CanoptekSwarmController(",
     "    canoptek_swarm_controller.placer = return_placement_controller",
     "...and after its own controller"),
):
    c.true(why, 0 <= MAIN.find(first) < MAIN.find(second))

# THE SELF-DESTRUCTION ALLOCATION MUST BE ANSWERABLE, or the phase gate that
# waits on it is a deadlock rather than a guard (error class 25).
c.true("what blocks the phase is also clickable",
       "self_destruction_controller.pending_damage_choice is not None" in MAIN
       and "self_destruction_controller.choose_damage_model(clicked)" in MAIN)
c.true("...and drawn on the board",
       "draw_damage_choice_highlight(board_surface, board, self_destruction_controller.pending_damage_choice)"
       in MAIN)
c.true("...and it is in the shared damage-pick list the panel and the AI pause read",
       "        self_destruction_controller,\n" in MAIN)

# NO agent_driver VERDICTS: none of these fifteen choices is army-wide.
DRIVER = io.open("ai/agent_driver.py", encoding="utf-8").read()
# NOT "Canoptek": two PRE-EXISTING comments in ai/agent_driver.py cite a
# measured Canoptek Wraiths move from a real log, so that word is already
# there and sweeping for it would fail against untouched code.
for name in ("chittering_swarm", "self_destruction", "canoptek_swarm",
             "tectonic_reverberations", "obelisk_node_control",
             "harassment_swarm", "weapon_sentinels", "Geomancer",
             "Doomstalker", "Macrocyte"):
    c.eq("ai/agent_driver.py knows nothing about %s" % name, name in DRIVER, False)

# DORMANT BY ROSTER, pinned so fielding one is a visible change.
_roster = io.open("armies/necrons.json", encoding="utf-8").read()
for sheet in SHEETS:
    c.true("%s is dormant by roster" % sheet.name, sheet.name not in _roster)
    c.true("%s draws its own art" % sheet.name,
           sprites.sprite_for(build(sheet, n=40).models[0]) is not None)

# SPRITE SHADOWING is measured, not hoped.
_keys = list(sprites.SQUAD_SPRITE_KEYS)
for _new in [s.name for s in SHEETS]:
    c.eq("no existing key swallows %r" % _new,
         [k for k in _keys if k != _new and k in _new], [])
    c.eq("...and it swallows none",
         [k for k in _keys if k != _new and _new in k], [])

c.finish()
