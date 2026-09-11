"""Stage 4 of the Necron datasheet backfill: the TRIARCH batch.

Two datasheets, three printed abilities' worth of engine work, and the one
thing this stage exists to get right - it is the first batch in which a
printed weapon name has to be SHARED rather than forked.

WHAT EACH SECTION IS FOR

  1. chassis and statlines, against the corpus rather than against literals.
  2. weapons - and the collision sweep as a MEASUREMENT: the particle caster is
     asserted to be the SAME CLASS the Canoptek Wraiths carry, and the BS each
     wielder resolves is asserted to differ. Two lines that a fork would pass
     one of and fail the other.
  3. wargear, points and the attachment table (neither unit leads or is led).
  4. Relentless Combatants clause 1 - the Charge-roll re-roll, at its DECISION
     BOUNDARY in both directions and through a real ChargeController and a real
     DiceManager, because the offer's whole subtlety is WHEN it is legal.
  5. Relentless Combatants clause 2 - the Fall Back exemption, measured at
     can_declare_charge() rather than at the predicate, since that is the gate
     the rule is about.
  6. Targeting Relay - through the REAL ShootingController cover test, so the
     mark has to reach the place cover is decided rather than merely be set.
  7. the extraction itself: the Defiler's ability is behaviour-unchanged, both
     are subclasses, and there is ONE reader for the denial.
  8. wiring, the AI negative space, sprites and dormancy.
"""

import io
import ast

import testkit as tk
from testkit import Checks, build_squad

from game import (attached_units, cover_denial, move_exceptions,
                  relentless_combatants, sprites, targeting_relay)
from game.barrage_of_filth import BarrageOfFilthController
from game.charge import ChargeController
from game.decision import DecisionManager
from game.factions import necrons as nec
from game.factions.necrons_points import NECRONS_POINTS
from game.relentless_combatants import RelentlessCombatantsController
from game.game_state import GameState
from game.targeting_relay import TargetingRelayController
from game.turn import PHASE_CHARGE, PHASE_SHOOTING, TurnTracker
from game.units import TriarchPraetorianProfile, TriarchStalkerProfile
from game.weapons import (HeatRayDispersedProfile, HeatRayFocusedProfile,
                          HeavyGaussCannonArrayProfile, ParticleCasterProfile,
                          ParticleShredderProfile, RodOfCovenantMeleeProfile,
                          RodOfCovenantRangedProfile, StalkersForelimbsProfile,
                          VoidbladeProfile)

c = Checks("Necron TRIARCH")

D = nec.NECRONS.datasheets
PRAETORIANS = D["Triarch Praetorians"]
STALKER = D["Triarch Stalker"]
WARRIORS = D["Necron Warriors"]
WRAITHS = D["Canoptek Wraiths"]
DEFILER_SHEET = None


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

_p = TriarchPraetorianProfile
c.eq("Praetorian M", _p.movement_in, 10)
c.eq("Praetorian T", _p.toughness, 5)
c.eq("Praetorian Sv", _p.armor_save, "3+")
c.eq("Praetorian W", _p.wounds, 2)
c.eq("Praetorian Ld", _p.leadership, "7+")
c.eq("Praetorian OC", _p.oc, 1)
c.eq("Praetorian base is the printed 32 mm", _p.base_radius_in, 0.63)
c.true("Praetorians are INFANTRY that FLY", _p.infantry and _p.fly)
c.true("...with Deep Strike (Core)", _p.deep_strike)
c.true("...and Reanimation Protocols", _p.reanimation_protocols)
c.eq("Praetorians have NO invulnerable save", _p.invulnerable_save, "-")
c.true("both printed skills are 3+, so no weapon needs an override",
       _p.weapon_skill == "3+" and _p.ballistic_skill == "3+")

_s = TriarchStalkerProfile
c.eq("Stalker M", _s.movement_in, 8)
c.eq("Stalker T", _s.toughness, 8)
c.eq("Stalker Sv", _s.armor_save, "3+")
c.eq("Stalker W", _s.wounds, 12)
c.eq("Stalker Ld", _s.leadership, "7+")
c.eq("Stalker OC", _s.oc, 4)
c.eq("Stalker INSV", _s.invulnerable_save, "4+")
c.true("the Stalker is a VEHICLE and a WALKER", _s.vehicle and _s.walker)
c.eq("Scouts 8\" (Core)", _s.scouts, 8)
c.eq("Deadly Demise D3 is a NOTATION, not the flat placeholder beside it",
     (_s.deadly_demise_notation.sides, _s.deadly_demise_notation.bonus,
      _s.deadly_demise_notation.dice), (3, 0, 1))
c.true("...and Reanimation Protocols", _s.reanimation_protocols)
# ITS BASE IS A DECISION, not a transcription - the datasheet prints "Use
# model". Pinned against the closest hull this engine already fields rather
# than against a bare number, so "why that size" survives the pin.
from game.units import MyphiticBlightHaulerProfile  # noqa: E402
c.eq("the Stalker's base matches the Myphitic Blight-hauler, its nearest hull",
     _s.base_radius_in, MyphiticBlightHaulerProfile.base_radius_in)
c.true("...and it is NOT the big tracked-hull size the Defiler and the "
       "Plagueburst Crawler use", _s.base_radius_in < 2.1)
c.true("the corpus really does print no base for it",
       "Use model" in io.open("rules/necrons/Triarch Stalker.md", encoding="utf-8").read())


# --- 2. weapons, and the collision sweep ------------------------------------
print("--- 2. weapons ---")

def row(w):
    return (w.range_in, w.attacks, w.strength, w.ap, w.damage)

c.eq("Rod of covenant (ranged)", row(RodOfCovenantRangedProfile), (12, 1, 5, -2, 2))
c.eq("Rod of covenant (melee)", row(RodOfCovenantMeleeProfile), (2, 3, 5, -2, 2))
c.eq("both halves print the SAME name - one datasheet entry, two rows",
     (RodOfCovenantRangedProfile.name, RodOfCovenantMeleeProfile.name),
     ("Rod of covenant", "Rod of covenant"))
c.eq("Voidblade", row(VoidbladeProfile), (2, 4, 5, -2, 1))
c.eq("Stalker's forelimbs", row(StalkersForelimbsProfile), (2, 4, 7, -1, 3))
c.eq("Heavy gauss cannon array", row(HeavyGaussCannonArrayProfile), (24, 6, 8, -2, 2))
c.true("...with [LETHAL HITS]", HeavyGaussCannonArrayProfile.lethal_hits)
c.eq("Particle shredder", row(ParticleShredderProfile), (18, 6, 7, 0, 1))
c.true("...with [BLAST] and [DEVASTATING WOUNDS]",
       ParticleShredderProfile.blast and ParticleShredderProfile.devastating_wounds)
c.eq("...and D6+6 Attacks, rolled rather than the placeholder beside it",
     (ParticleShredderProfile.attacks_notation.sides,
      ParticleShredderProfile.attacks_notation.bonus,
      ParticleShredderProfile.attacks_notation.dice), (6, 6, 1))

# THE ONE PER-WEAPON SKILL OVERRIDE IN THIS BATCH, and it is printed: the
# shredder's row says 2+ while the Stalker's own profile says 3+. Both halves
# are pinned, because an override that merely repeated the profile would be
# noise and one that went missing would be a silent downgrade.
c.eq("the particle shredder carries its printed BS 2+",
     ParticleShredderProfile.ballistic_skill, "2+")
c.true("...and it really is BETTER than the Stalker's own",
       (ParticleShredderProfile.ballistic_skill or "9+")
       < TriarchStalkerProfile.ballistic_skill)
c.eq("no OTHER Triarch weapon overrides a skill",
     [w.name for w in (RodOfCovenantRangedProfile, RodOfCovenantMeleeProfile,
                       VoidbladeProfile, HeatRayDispersedProfile,
                       HeatRayFocusedProfile, HeavyGaussCannonArrayProfile,
                       StalkersForelimbsProfile)
      if w.ballistic_skill is not None or w.weapon_skill is not None], [])

# The heat ray is ONE datasheet entry with two modes, so they are a firing-mode
# pair rather than two guns - otherwise the Stalker fires both in one
# activation. Pinned in the direction that matters: the DEFAULT is the
# dispersed row (the printed first one), and the focused row hangs off it.
c.eq("Heat ray - dispersed", row(HeatRayDispersedProfile), (12, 2, 5, -1, 1))
c.eq("...2D6 Attacks", (HeatRayDispersedProfile.attacks_notation.sides,
                        HeatRayDispersedProfile.attacks_notation.dice), (6, 2))
c.true("...[TORRENT] and [IGNORES COVER]",
       HeatRayDispersedProfile.torrent and HeatRayDispersedProfile.ignores_cover)
c.eq("Heat ray - focused", row(HeatRayFocusedProfile), (18, 2, 9, -4, 6))
c.eq("...D6 Damage", (HeatRayFocusedProfile.damage_notation.sides,
                      HeatRayFocusedProfile.damage_notation.bonus), (6, 0))
c.eq("...[MELTA 4]", HeatRayFocusedProfile.melta, 4)
c.eq("the two are a firing-mode PAIR, dispersed first",
     HeatRayDispersedProfile.overcharge_profile, HeatRayFocusedProfile)
c.eq("...and the focused row is not itself a mode of anything",
     HeatRayFocusedProfile.overcharge_profile, None)

# THE COLLISION SWEEP, as a measurement rather than a note. The Praetorians'
# printed particle caster row is byte-for-byte the Canoptek Wraiths' - so it is
# the SAME CLASS, not a twin. A fork would pass every line above and fail this
# one.
def option_weapon(sheet, option_name):
    return [w for w in sheet.wargear_options
            if w.name == option_name][0].with_weapons[0]


_pra_caster = option_weapon(PRAETORIANS, nec.PRAETORIANS_TO_CASTER_AND_VOIDBLADE)
_wraith_caster = option_weapon(nec.CANOPTEK_WRAITHS, nec.WRAITHS_ADD_PARTICLE_CASTER)
# READ OFF BOTH DATASHEETS, not off the imported name: comparing the shared
# class to itself is a tautology that a fork passes untouched, which is
# precisely what the A/B probe for this line caught.
c.true("the Praetorians' particle caster IS the Canoptek Wraiths' class",
       _pra_caster is _wraith_caster)
c.eq("...and its row is what both datasheets print",
     row(_pra_caster), (12, 3, 5, 0, 1))
c.true("...with [DEVASTATING WOUNDS] and [PISTOL]",
       ParticleCasterProfile.devastating_wounds and ParticleCasterProfile.pistol)
# The one column that DOES differ is BS, and it lives on the model profile, so
# sharing the class still gives each wielder its printed skill. Measured
# through the shared class rather than asserted about the profiles, because
# that is the thing a fork would have been built to fix.
c.eq("...yet the skill still resolves per WIELDER",
     (_pra_caster.ballistic_skill or TriarchPraetorianProfile.ballistic_skill,
      _wraith_caster.ballistic_skill or
      nec.CANOPTEK_WRAITHS.composition_options[0][0].profile_cls.ballistic_skill),
     ("3+", "4+"))
c.true("...which is only true because the class carries NO override",
       _pra_caster.ballistic_skill is None)


# --- 3. wargear, points, attachment -----------------------------------------
print("--- 3. wargear, points, attachment ---")

_pra = build(PRAETORIANS)
c.eq("a default Praetorian unit is 5 models", len(_pra.models), 5)
c.eq("...each carrying both rows of the rod of covenant",
     sorted(w.name for w in _pra.models[0].weapons), ["Rod of covenant", "Rod of covenant"])
c.eq("...and 10 is the other printed size",
     len(build(PRAETORIANS, composition_index=1).models), 10)

_swap = build(PRAETORIANS, choices={"Triarch Praetorian": {nec.PRAETORIANS_TO_CASTER_AND_VOIDBLADE: 5}})
c.eq("the swap gives up BOTH rod rows on every model and takes two weapons back",
     sorted(w.name for w in _swap.models[0].weapons), ["Particle Caster", "Voidblade"])
c.true("...on ALL FIVE, since the printed text says 'all models ... can each'",
       all(sorted(w.name for w in m.weapons) == ["Particle Caster", "Voidblade"]
           for m in _swap.models))

_stalker = build(STALKER)
c.eq("a default Stalker carries the DISPERSED heat ray and its forelimbs",
     sorted(w.name for w in _stalker.models[0].weapons),
     ["Heat ray - dispersed", "Stalker's forelimbs"])
c.eq("...the focused row is a MODE, not a second gun in the loadout",
     [w.name for w in _stalker.models[0].weapons if w.name == "Heat ray - focused"], [])
c.eq("swapping to the particle shredder replaces the heat ray",
     sorted(w.name for w in build(STALKER, choices={"Triarch Stalker": {nec.STALKER_TO_PARTICLE_SHREDDER: 1}})
            .models[0].weapons),
     ["Particle shredder", "Stalker's forelimbs"])
c.eq("...and so does the heavy gauss cannon array",
     sorted(w.name for w in
            build(STALKER, choices={"Triarch Stalker": {nec.STALKER_TO_HEAVY_GAUSS_CANNON_ARRAY: 1}})
            .models[0].weapons),
     ["Heavy gauss cannon array", "Stalker's forelimbs"])
# "ONE OF the following" - both options give up the same weapon, so on this
# one-model line they cannot both land. Measured rather than trusted to the
# comment, because that exclusivity is a property of build_squad()'s cursor.
_both = build(STALKER, choices={"Triarch Stalker": {
    nec.STALKER_TO_PARTICLE_SHREDDER: 1,
    nec.STALKER_TO_HEAVY_GAUSS_CANNON_ARRAY: 1}})
c.eq("asking for BOTH replacements still leaves exactly one gun",
     len([w for w in _both.models[0].weapons if w.name != "Stalker's forelimbs"]), 1)

c.eq("Praetorians cost 80 for 5", build(PRAETORIANS).points, 80)
c.eq("...and 160 for 10", build(PRAETORIANS, composition_index=1).points, 160)
c.eq("the wargear swap is free", _swap.points, 80)
c.eq("a Stalker costs 110 for the 1st",
     build_squad(STALKER, "Player 2", name="2 Triarch Stalker 1", unit_index=1).points, 110)
c.eq("...and 120 from the 3rd",
     build_squad(STALKER, "Player 2", name="2 Triarch Stalker 3", unit_index=3).points, 120)
c.true("both are in the points table", "Triarch Praetorians" in NECRONS_POINTS
       and "Triarch Stalker" in NECRONS_POINTS)

# NEITHER ATTACHES TO ANYTHING - measured off the page's own LED BY blocks
# (six on this faction, none naming a Triarch datasheet), so this is a
# datasheet fact rather than a gap in the pairing table.
c.true("no Necron character may lead Triarch Praetorians",
       all(attached_units.can_attach(build(sheet), build(PRAETORIANS)) != []
           for sheet in (nec.OVERLORD, nec.TECHNOMANCER, nec.CHRONOMANCER)))
c.true("...and the Praetorians lead nothing either",
       attached_units.can_attach(build(PRAETORIANS), build(WARRIORS, composition_index=0)) != [])
c.eq("neither Triarch unit appears on any leads/supports line",
     sorted(n for n, p in NECRONS_POINTS.items()
            if any("Triarch" in x for x in
                   (getattr(p, "leads", ()) or ()) + (getattr(p, "supports", ()) or ()))), [])


# --- 4. Relentless Combatants, clause 1: the Charge re-roll -----------------
print("--- 4. Relentless Combatants: the charge re-roll ---")

class _NoController:
    """Stand-in for a controller a probe has broken. Every reader below
    calls maybe_offer_charge_reroll(), so returning False turns the probe
    into a named RED line instead of an AttributeError that takes the
    whole suite down and says nothing about which assurance broke."""

    def maybe_offer_charge_reroll(self, squad=None):
        return False

    def can_offer(self, squad):
        return False


def charge_scene(charger_sheet, gap=9.0, owner="Player 2", auto=()):
    """A real ChargeController mid-roll: the dice are on the table and NOT yet
    acknowledged, which is the only instant this re-roll is legal."""
    state = GameState()
    charger = place(build(charger_sheet, owner, n=1), 20.0, 20.0)
    enemy = place(build(WARRIORS, "Player 1", n=1, composition_index=0), 20.0, 20.0 + gap)
    for s in (charger, enemy):
        for m in s.models:
            state.add_token(m)
    tt = TurnTracker(first_player=owner)
    while tt.phase != PHASE_CHARGE or tt.turn_owner != owner:
        tt.advance_phase()
    log, dice, dec = tk.Log(), tk.RecordingDice(), DecisionManager()
    cc = ChargeController(game_log=log, dice_manager=dice, turn_tracker=tt,
                          all_tokens=state.tokens)
    # DEGRADED, not bare: a probe must make this suite RED, not abort it.
    # Stage 9 moved the machinery into game/charge_reroll.py, and the probe
    # that takes this class back off that base leaves a constructor with no
    # keyword arguments at all - which a bare call turns into a TypeError
    # before any check reports.
    try:
        rc = RelentlessCombatantsController(
            dice_manager=dice, decision_manager=dec, charge_controller=cc,
            game_log=log, auto_players=auto)
    except TypeError:
        rc = _NoController()
    return dict(state=state, charger=charger, enemy=enemy, charge=cc, relentless=rc,
                dice=dice, decision=dec, log=log, turn=tt)


AI = ("Player 2",)

# THE PRAETORIANS ARE 9" AWAY from the enemy front rank in this scene, so a
# roll of 5 reaches nothing and a 12 reaches. Both facts are measured through
# the REAL rule 11.04 gate rather than assumed from the gap, since base sizes
# and coherency move the real number.
sc = charge_scene(PRAETORIANS, auto=AI)
tk.script(2, 3)                      # 5" - a failed charge
sc["charge"].declare_charge(sc["charger"])
c.eq("the scene really is a failed charge",
     sorted(s.name for s in sc["charge"].targets_reachable_with(5)), [])
c.true("...and a maximum roll would reach", sc["charge"].targets_reachable_with(12))
_before = list(sc["dice"].pending_values)
c.true("the AI re-rolls a charge that reached nothing - it is free",
       sc["relentless"].maybe_offer_charge_reroll())
c.true("...and the dice on the table really changed",
       sc["dice"].already_rerolled == {0, 1})
c.eq("...without asking anyone", sc["decision"].is_pending, False)
c.true("the log names the ability and both totals",
       any("Relentless Combatants" in line and "re-rolled in full" in line
           for line in sc["log"].lines))

# THE OTHER SIDE OF THE BOUNDARY: a roll that DID reach something is kept by
# the AI, because re-rolling a charge is all-or-nothing and free does not make
# gambling a live charge good.
sc = charge_scene(PRAETORIANS, auto=AI)
tk.script(6, 6)
sc["charge"].declare_charge(sc["charger"])
c.true("the scene really is a SUCCESSFUL charge",
       sc["charge"].targets_reachable_with(12))
c.eq("the AI keeps a charge roll that reached", sc["relentless"].maybe_offer_charge_reroll(), False)
c.eq("...and the dice are untouched", sc["dice"].already_rerolled, set())
c.eq("...and nobody was asked", sc["decision"].is_pending, False)

# A HUMAN owner IS asked in that same state - trading a hit for a longer one is
# a real judgement, which is the split ai/agent_driver.py's CP verdict makes at
# exactly this point.
sc = charge_scene(PRAETORIANS, auto=())
tk.script(6, 6)
sc["charge"].declare_charge(sc["charger"])
c.true("a HUMAN owner is asked even when the charge reached",
       sc["relentless"].maybe_offer_charge_reroll() and sc["decision"].is_pending)
c.true("...and the prompt offers both answers",
       len(tk.options_of(sc["decision"])) == 2
       and any("Keep" in o for o in tk.options_of(sc["decision"])))
c.true("...and choosing the re-roll really throws the dice",
       tk.pick_option(sc["decision"], "Re-roll") and sc["dice"].already_rerolled == {0, 1})

# NEVER OFFER WHAT CANNOT BUY ANYTHING: with no enemy in reach even on a 12,
# nobody is asked at all - not the AI, not a human.
sc = charge_scene(PRAETORIANS, auto=())
tk.script(2, 3)
sc["charge"].declare_charge(sc["charger"])
place(sc["enemy"], 20.0, 70.0)
c.eq("the scene really is hopeless - nothing is reachable even on a 12",
     sorted(s.name for s in sc["charge"].targets_reachable_with(12)), [])
c.eq("a hopeless charge is not offered a re-roll at all",
     sc["relentless"].maybe_offer_charge_reroll(), False)
c.eq("...and no prompt was raised", sc["decision"].is_pending, False)

# ONCE PER ROLL. Declining leaves exactly the board that produced the question,
# so without DiceManager.claim_reroll_offer() the next click asks again - the
# reported infinite loop that helper exists for.
sc = charge_scene(PRAETORIANS, auto=())
tk.script(2, 3)
sc["charge"].declare_charge(sc["charger"])
c.true("first ask opens the prompt", sc["relentless"].maybe_offer_charge_reroll())
c.true("declining closes it", tk.pick_option(sc["decision"], "Keep"))
c.eq("...and it does NOT come back", sc["relentless"].maybe_offer_charge_reroll(), False)
c.eq("...so no second prompt is standing", sc["decision"].is_pending, False)

# A UNIT WITHOUT THE ABILITY gets nothing, which is what stops this being an
# army-wide re-roll.
sc = charge_scene(WARRIORS, auto=AI)
tk.script(2, 3)
sc["charge"].declare_charge(sc["charger"])
c.eq("Necron Warriors get no charge re-roll", sc["relentless"].maybe_offer_charge_reroll(), False)

# AND IT IS ALL OR NOTHING: once any die of the roll has been thrown twice,
# can_reroll_all() refuses, so a Command Re-roll and this cannot stack.
sc = charge_scene(PRAETORIANS, auto=AI)
tk.script(2, 3)
sc["charge"].declare_charge(sc["charger"])
sc["dice"].reroll_die(0)
c.eq("a roll with one die already re-rolled cannot be re-rolled in full",
     sc["relentless"].maybe_offer_charge_reroll(), False)


# --- 5. Relentless Combatants, clause 2: charging after a Fall Back ---------
print("--- 5. Relentless Combatants: the Fall Back exemption ---")

_pra = build(PRAETORIANS)
c.true("the predicate reads the datasheet ability",
       relentless_combatants.squad_has_relentless_combatants(_pra))
c.eq("...and Necron Warriors do not have it",
     relentless_combatants.squad_has_relentless_combatants(build(WARRIORS, composition_index=0)),
     False)
c.true("it registers in move_exceptions' 09.07 CHARGE fold",
       move_exceptions.may_charge_after_falling_back(_pra))
# ONLY the charge half. The printed text says "declare a charge", not "shoot" -
# the difference between this and Hovering Death, and the reason that module
# keeps three separate lists.
c.eq("...and NOT in the SHOOTING one - the printed text says only 'charge'",
     move_exceptions.may_shoot_after_falling_back(_pra), False)
c.eq("...nor in either Advance fold",
     (move_exceptions.may_charge_after_advancing(_pra),
      move_exceptions.may_shoot_after_advancing(_pra)), (False, False))

# MEASURED AT THE GATE, not at the predicate: can_declare_charge() is what the
# rule is about, and a predicate that nothing asks is the failure mode this
# repo has paid for repeatedly.
sc = charge_scene(PRAETORIANS)
sc["charger"].fell_back_this_turn = True
c.true("a Praetorian unit that Fell Back may still declare a charge",
       sc["charge"].can_declare_charge(sc["charger"]))
sc = charge_scene(WARRIORS)
sc["charger"].fell_back_this_turn = True
c.eq("...where a unit without the ability may not",
     sc["charge"].can_declare_charge(sc["charger"]), False)


# --- 6. Targeting Relay ------------------------------------------------------
print("--- 6. Targeting Relay ---")

def cover_scene(shooter_sheet, auto=()):
    """A real ShootingController, so the mark has to reach the place cover is
    actually decided."""
    sc = tk.shooting_scene(shooter_sheet, WARRIORS, attacker_owner="Player 2")
    relay = TargetingRelayController(decision_manager=sc["decision"],
                                     game_log=sc["log"], auto_players=auto)
    sc["shooting"].targeting_relay = relay
    sc["relay"] = relay
    return sc


sc = cover_scene(STALKER, auto=("Player 2",))
_shooter, _target = sc["attacker"], sc["target"]
c.true("the Stalker has the ability", TargetingRelayController.has_ability(_shooter))
c.eq("...and a Praetorian unit does not",
     TargetingRelayController.has_ability(build(PRAETORIANS)), False)
c.eq("nothing is stripped before it shoots", sc["relay"].denies_cover(_target), False)
c.true("firing at a unit it HIT strips that unit's cover",
       sc["relay"].on_squad_finished_shooting(_shooter, [_target]))
c.true("...and the mark is set", sc["relay"].denies_cover(_target))
c.true("...and the log names the ability",
       any("Targeting Relay" in line for line in sc["log"].lines))
c.eq("a shooter that hit NOTHING has no candidate and does nothing",
     cover_scene(STALKER, auto=("Player 2",))["relay"]
     .on_squad_finished_shooting(_shooter, []), False)

# THE MARK HAS TO REACH THE COVER TEST. Measured through the real
# ShootingController: the target is given Stealth (rule 24.33's unconditional
# grant) so that cover is TRUE for a reason the denial has to beat, which is
# exactly the ordering _compute_benefit_of_cover() is written for.
sc = cover_scene(STALKER, auto=("Player 2",))
_shooter, _target = sc["attacker"], sc["target"]
for m in _target.models:
    m.profile = type("Stealthy", (type(m.profile),), {"stealth": True})
c.true("a STEALTH unit has the benefit of cover to begin with",
       sc["shooting"]._compute_benefit_of_cover(_shooter.models[0], _target))
sc["relay"].on_squad_finished_shooting(_shooter, [_target])
c.eq("...and Targeting Relay beats it, because 'cannot have' is absolute",
     sc["shooting"]._compute_benefit_of_cover(_shooter.models[0], _target), False)

# "UNTIL THE END OF THE PHASE" - one clock, and it is the shorter one.
sc["relay"].reset_phase()
c.true("the mark is gone at the phase boundary",
       sc["shooting"]._compute_benefit_of_cover(_shooter.models[0], _target))

# A FRIENDLY unit can never be the candidate - "enemy unit" is printed.
sc = cover_scene(STALKER, auto=("Player 2",))
_friend = build(WARRIORS, "Player 2", composition_index=0)
c.eq("a friendly unit is not a candidate",
     sc["relay"].on_squad_finished_shooting(sc["attacker"], [_friend]), False)

# WITH TWO CANDIDATES A HUMAN IS ASKED, and each option is TAGGED with its
# unit, so it can be answered on the board.
sc = cover_scene(STALKER, auto=())
_a = build(WARRIORS, "Player 1", n=1, composition_index=0)
_b = build(WARRIORS, "Player 1", n=2, composition_index=0)
c.true("a human with two hit units is asked which",
       sc["relay"].on_squad_finished_shooting(sc["attacker"], [_a, _b])
       and sc["decision"].is_pending)
c.eq("...with one option per unit", len(tk.options_of(sc["decision"])), 2)
c.eq("...each tagged with its squad, so the board can answer it",
     sorted(o["squad"].name for o in sc["decision"].options if o.get("squad")),
     sorted([_a.name, _b.name]))
c.true("...and choosing one strips exactly that one",
       tk.pick_option(sc["decision"], _b.name)
       and sc["relay"].denies_cover(_b) and not sc["relay"].denies_cover(_a))
# ONE candidate is not a question: "select" is not "you can", so the only
# decision is WHICH, and with one there is nothing to ask.
sc = cover_scene(STALKER, auto=())
c.true("...but ONE candidate is applied without a prompt",
       sc["relay"].on_squad_finished_shooting(sc["attacker"], [sc["target"]])
       and not sc["decision"].is_pending)


# --- 7. the extraction ------------------------------------------------------
print("--- 7. the shared head ---")

c.true("both abilities are subclasses of the shared head",
       issubclass(BarrageOfFilthController, cover_denial.CoverDenialAfterShooting)
       and issubclass(TargetingRelayController, cover_denial.CoverDenialAfterShooting))
c.eq("...and each owns exactly the two knobs",
     (BarrageOfFilthController.flag, BarrageOfFilthController.label,
      TargetingRelayController.flag, TargetingRelayController.label),
     ("barrage_of_filth", "Barrage of Filth", "targeting_relay", "Targeting Relay"))
# A subclass that forgets a knob fails LOUDLY at construction rather than
# offering an unnamed choice.
try:
    type("Nameless", (cover_denial.CoverDenialAfterShooting,), {})()
    _loud = False
except AssertionError:
    _loud = True
c.true("a subclass missing a knob fails loudly", _loud)

# ONE READER for the denial, so the two can never disagree about what "denied"
# means. Measured on the fold rather than on either controller.
_bof = BarrageOfFilthController()
_rel = TargetingRelayController()
_victim = build(WARRIORS, "Player 1", composition_index=0)
c.eq("denied() is False with nothing set", cover_denial.denied(_victim, (_bof, _rel)), False)
_rel._stripped.add(id(_victim))
c.true("...True when EITHER source says so", cover_denial.denied(_victim, (_bof, _rel)))
c.eq("...and it tolerates a missing collaborator",
     cover_denial.denied(_victim, (None, None)), False)

# THE DEFILER'S ABILITY IS BEHAVIOUR-UNCHANGED by the extraction - the prompt
# and log strings are the ones it always produced.
sc = tk.shooting_scene(STALKER, WARRIORS, attacker_owner="Player 2")
_bof = BarrageOfFilthController(decision_manager=sc["decision"], game_log=sc["log"],
                                auto_players=("Player 2",))
_defiler = build(WARRIORS, "Player 2", composition_index=0)
for m in _defiler.models:
    m.profile = type("Filthy", (type(m.profile),), {"barrage_of_filth": True})
_bof.on_squad_finished_shooting(_defiler, [sc["target"]])
c.true("Barrage of Filth still logs under its own name",
       any(line.startswith("Barrage of Filth (") and
           "cannot have the benefit of Cover until the end of the phase." in line
           for line in sc["log"].lines))


# --- 8. wiring, the AI negative space, sprites ------------------------------
print("--- 8. wiring, AI, sprites ---")

MAIN = io.open("main.py", encoding="utf-8").read()
TREE = ast.parse(MAIN)


# Every CALL EXPRESSION in main.py, collected ONCE. Built from the line span
# rather than ast.get_source_segment(), which re-splits the whole source per
# node - measured at 36 s over main.py's thousands of calls, against 0.2 s for
# the entire rest of this suite.
_MAIN_LINES = MAIN.splitlines()
MAIN_CALLS = []
for _node in ast.walk(TREE):
    if isinstance(_node, ast.Call):
        _end = getattr(_node, "end_lineno", _node.lineno)
        MAIN_CALLS.append(" ".join(
            " ".join(_MAIN_LINES[_node.lineno - 1:_end]).split()))


def calls_in_main(needle):
    """Every call expression in main.py whose source contains `needle` - the
    expression, not a mention, because a name that only appears in a docstring
    has burned this repo five times."""
    return [text for text in MAIN_CALLS if needle in text]


for needle, why in (
    ("TargetingRelayController(", "the Targeting Relay controller is built"),
    ("targeting_relay_controller.on_squad_finished_shooting",
     "...and fed from the shooting hook"),
    ("targeting_relay_controller.reset_phase()", "...and cleared at the phase boundary"),
    ("RelentlessCombatantsController(", "the Relentless Combatants controller is built"),
    ("relentless_combatants_controller.maybe_offer_charge_reroll()",
     "...and asked when a Charge roll lands"),
):
    c.true(why, bool(calls_in_main(needle)))
c.true("shooting_controller is handed the relay",
       "shooting_controller.targeting_relay = targeting_relay_controller" in MAIN)

# CONSTRUCTION ORDER (error class 23): the re-roll controller holds
# charge_controller, and main() is one long function in which that is a real
# hazard. The AST guard in test_event_chain_wiring.py covers `a.b = c`, not
# constructor kwargs, so this is measured here.
c.true("the re-roll controller is built AFTER charge_controller",
       MAIN.find("charge_controller = ChargeController(")
       < MAIN.find("relentless_combatants_controller = RelentlessCombatantsController("))
# AND THE OFFER MUST PRECEDE acknowledge(), which is the whole of clause 1's
# subtlety: acknowledge() clears pending_values and reroll_all() then refuses.
_offer = MAIN.find("relentless_combatants_controller.maybe_offer_charge_reroll()")
_ack = MAIN.find("dice_manager.acknowledge()", MAIN.find("if dice_manager.roll_kind == ADVANCE_ROLL:"))
c.true("...and the offer is made BEFORE the roll is acknowledged",
       0 < _offer < _ack)

# NO agent_driver VERDICTS: neither choice is army-wide, so both are answered
# in their own controller through auto_players. Pinned as a negative space.
DRIVER = io.open("ai/agent_driver.py", encoding="utf-8").read()
for name in ("relentless_combatants", "targeting_relay", "Triarch"):
    c.eq("ai/agent_driver.py knows nothing about %s" % name, name in DRIVER, False)
# Guarded for the same reason charge_scene() is: a probe that takes this
# class off its shared base leaves a constructor with no keyword arguments,
# and a bare call here aborts the run instead of reddening this line.
def _gates_on_auto(cls):
    try:
        return "Player 2" in cls(auto_players=("Player 2",)).auto_players
    except TypeError:
        return False


c.true("both controllers gate on auto_players at the OBJECT",
       _gates_on_auto(RelentlessCombatantsController)
       and _gates_on_auto(TargetingRelayController))

# DORMANT BY ROSTER, pinned so fielding one is a visible change.
_roster = io.open("armies/necrons.json", encoding="utf-8").read()
for _n in ("Triarch Praetorians", "Triarch Stalker"):
    c.true("%s is dormant by roster" % _n, _n not in _roster)

for sheet in (PRAETORIANS, STALKER):
    c.true("%s draws its own art" % sheet.name,
           sprites.sprite_for(build(sheet, n=40).models[0]) is not None)

# SPRITE SHADOWING is measured, not hoped: _key_for_name() returns the FIRST
# key that is a substring of the squad name.
_keys = list(sprites.SQUAD_SPRITE_KEYS)
for _new in ("Triarch Praetorians", "Triarch Stalker"):
    c.eq("no existing key swallows %r" % _new,
         [k for k in _keys if k != _new and k in _new], [])
    c.eq("...and it swallows none",
         [k for k in _keys if k != _new and _new in k], [])

c.finish()
