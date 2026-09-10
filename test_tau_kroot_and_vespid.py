"""The five Kroot / Vespid datasheets (Etappe 2).

  Kroot Hounds · Kroot Farstalkers · Vespid Stingwings ·
  Krootox Riders · Krootox Rampagers

Real objects throughout: the real datasheets, the real ShootingController and
FightController, the real ChargeController gate, the real objective. A/B probes
accompany every ability claim and are listed against the sections they protect.

  1. Stat lines, bases, keywords, points, compositions, wargear
  2. Loping Pounce + Hunting Hounds                  (Kroot Hounds)
  3. Airborne Agility + Oversight Drone              (Vespid Stingwings)
  4. Kroot Packmates                                 (Krootox Riders)
  5. Kroot Linebreakers                              (Krootox Rampagers)
  6. Bounty Hunters + Pech'ra                        (Kroot Farstalkers)
  7. Source guards
"""

import ast
import testkit as tk
from game import bounty_hunters as bh
from game import hunting_hounds, loping_pounce, objective_control, oversight_drone, plagues
from game.airborne_agility import AirborneAgilityController
from game.bounty_hunters import BountyHuntersController
from game.charge import ChargeController
from game.decision import DecisionManager
from game.factions.tau_empire import (
    FARSTALKER_FIREARM_TO_SKINNER, FARSTALKER_FIREARM_TO_TRIBALEST,
    KILL_BROKER_FIREARM_TO_TAU_TECH, KROOTOX_RAMPAGERS, KROOTOX_REPEATER_TO_TANGLECANNON,
    KROOTOX_RIDERS, KROOT_CARNIVORES, KROOT_FARSTALKERS, KROOT_FLESH_SHAPER, KROOT_HOUNDS,
    STRIKE_TEAM, VESPID_BLASTER_TO_RAIL_RIFLE, VESPID_STINGWINGS,
)
from game.game_state import GameState
from game.kroot_packmates import KrootPackmatesController
from game.mortal_wound_abilities import (
    KrootLinebreakersController, linebreaker_dice, linebreaker_targets,
)
from game.oversight_drone import OversightDroneController
from game.turn import TurnTracker
from game.weapons import KrootoxFistsProfile, RampagerKrootoxFistsProfile

ck = tk.Checks("Kroot and Vespid")

SHEETS = {
    "Kroot Hounds": KROOT_HOUNDS,
    "Kroot Farstalkers": KROOT_FARSTALKERS,
    "Vespid Stingwings": VESPID_STINGWINGS,
    "Krootox Riders": KROOTOX_RIDERS,
    "Krootox Rampagers": KROOTOX_RAMPAGERS,
}
MM = 25.4


def unit(sheet, owner="Player 1", ci=0, choices=None, gear=None):
    return tk.build(sheet, owner, name=f"1 {sheet.name} 1", composition_index=ci,
                    choices=choices, gear=gear)


# --- 1. Stat lines, bases, keywords, points, compositions -----------------
print("\n1. Stat lines, bases, keywords, points, compositions")


def stats(sheet, ci=0, index=0):
    p = unit(sheet, ci=ci).models[index].profile
    return (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc)


ck.eq("Kroot Hounds stat line", stats(KROOT_HOUNDS), (12, 3, "6+", 1, "8+", 0))
ck.eq("Vespid stat line", stats(VESPID_STINGWINGS), (12, 4, "4+", 1, "7+", 1))
ck.eq("Krootox Riders stat line", stats(KROOTOX_RIDERS), (7, 6, "5+", 5, "7+", 2))
ck.eq("Krootox Rampagers share it exactly",
      stats(KROOTOX_RAMPAGERS), stats(KROOTOX_RIDERS))
ck.eq("Kroot Farstalkers stat line", stats(KROOT_FARSTALKERS), (7, 3, "6+", 1, "7+", 1))

# Kroot Hounds' printed OC is 0 - the reason Hunting Hounds exists at all.
ck.eq("Kroot Hounds have no Objective Control of their own",
      unit(KROOT_HOUNDS).models[0].profile.oc, 0)

# The Farstalkers' own hounds print Ld 7+, not the 8+ on the Kroot Hounds
# datasheet. One number, two datasheets, two classes.
_fs = unit(KROOT_FARSTALKERS)
_fs_hound = next(m for m in _fs.models if m.profile.name.startswith("Kroot Hound"))
ck.eq("a Farstalker hound is Ld 7+, not the 8+ of its own datasheet",
      (_fs_hound.profile.leadership, unit(KROOT_HOUNDS).models[0].profile.leadership),
      ("7+", "8+"))
ck.true("...and has neither of the Kroot Hounds datasheet's abilities",
        not _fs_hound.profile.loping_pounce and not _fs_hound.profile.hunting_hounds)

# Bases.
for name, sheet, mm, idx in [("Kroot Hounds", KROOT_HOUNDS, 28.5, 0),
                             ("Vespid", VESPID_STINGWINGS, 28.5, 0),
                             ("Krootox Riders", KROOTOX_RIDERS, 50, 0),
                             ("Krootox Rampagers", KROOTOX_RAMPAGERS, 50, 0)]:
    ck.true(f"{name}: {mm}mm base",
            abs(unit(sheet).models[idx].profile.base_radius_in - mm / 2 / MM) < 0.002)
_kb = next(m for m in _fs.models if m.profile.name == "Kroot Kill-broker")
ck.true("the Kill-broker is on 32mm where his Farstalkers are on 28.5mm",
        abs(_kb.profile.base_radius_in - 32 / 2 / MM) < 0.002
        and abs(next(m for m in _fs.models if m.profile.name == "Kroot Farstalker")
                .profile.base_radius_in - 28.5 / 2 / MM) < 0.002)

# Compositions and points, both sizes of each.
ck.eq("Kroot Hounds 5 / 10 models",
      [(len(unit(KROOT_HOUNDS, ci=i).models), unit(KROOT_HOUNDS, ci=i).points)
       for i in (0, 1)], [(5, 45), (10, 65)])
ck.eq("Vespid 5 / 10 models",
      [(len(unit(VESPID_STINGWINGS, ci=i).models), unit(VESPID_STINGWINGS, ci=i).points)
       for i in (0, 1)], [(5, 70), (10, 115)])
ck.eq("Krootox Riders 1 / 2 / 3 models",
      [(len(unit(KROOTOX_RIDERS, ci=i).models), unit(KROOTOX_RIDERS, ci=i).points)
       for i in (0, 1, 2)], [(1, 45), (2, 60), (3, 90)])
ck.eq("Krootox Rampagers 3 / 6 models",
      [(len(unit(KROOTOX_RAMPAGERS, ci=i).models), unit(KROOTOX_RAMPAGERS, ci=i).points)
       for i in (0, 1)], [(3, 85), (6, 170)])
ck.eq("Kroot Farstalkers: 1 + 9 + 2 = 12 models, 75 pts",
      (len(_fs.models), _fs.points), (12, 75))

# The Rampagers' fists print the SAME name and numbers as the Riders' but add
# [SUSTAINED HITS 1] - so a subclass, and the test pins the pair rather than
# the literals, which is what stops the shared numbers drifting.
ck.eq("both Krootox fists share every number",
      (RampagerKrootoxFistsProfile.attacks, RampagerKrootoxFistsProfile.strength,
       RampagerKrootoxFistsProfile.ap, RampagerKrootoxFistsProfile.damage),
      (KrootoxFistsProfile.attacks, KrootoxFistsProfile.strength,
       KrootoxFistsProfile.ap, KrootoxFistsProfile.damage))
ck.eq("only the Rampagers' print [SUSTAINED HITS 1]",
      (RampagerKrootoxFistsProfile.sustained_hits, KrootoxFistsProfile.sustained_hits),
      (1, 0))
ck.true("both are [EXTRA ATTACKS], so 04.01 never locks them out",
        RampagerKrootoxFistsProfile.extra_attacks and KrootoxFistsProfile.extra_attacks)

# The Farstalker firearm and the T'au-tech rifle are renames, not copies.
from game.weapons import (  # noqa: E402
    FarstalkerFirearmProfile, KrootRifleProfile, PulseRifleProfile, TauTechRifleProfile,
)
ck.eq("the Farstalker firearm is the Kroot rifle under another name",
      (FarstalkerFirearmProfile.range_in, FarstalkerFirearmProfile.strength,
       FarstalkerFirearmProfile.rapid_fire),
      (KrootRifleProfile.range_in, KrootRifleProfile.strength, KrootRifleProfile.rapid_fire))
ck.eq("the T'au-tech rifle is the pulse rifle under another name",
      (TauTechRifleProfile.range_in, TauTechRifleProfile.strength,
       TauTechRifleProfile.rapid_fire),
      (PulseRifleProfile.range_in, PulseRifleProfile.strength, PulseRifleProfile.rapid_fire))
ck.eq("...and both keep their own printed names",
      (FarstalkerFirearmProfile.name, TauTechRifleProfile.name),
      ("Farstalker Firearm", "T'au-tech Rifle"))

# Wargear.
_tangle = unit(KROOTOX_RIDERS, ci=2,
               choices={"Krootox Riders": {KROOTOX_REPEATER_TO_TANGLECANNON: 3}})
ck.eq("\"any number of models\" really means all three",
      sum(1 for m in _tangle.models for w in m.weapons if w.name == "Tanglecannon"), 3)
ck.eq("Krootox Rampagers have no wargear options at all",
      len(KROOTOX_RAMPAGERS.wargear_options), 0)

# The Vespid options are printed "if this unit contains 10 models" - which
# per_models=10 expresses exactly: the cap computes to 0 at five models.
_v5 = unit(VESPID_STINGWINGS, ci=0,
           choices={"Vespid Stingwings": {VESPID_BLASTER_TO_RAIL_RIFLE: 1}})
_v10 = unit(VESPID_STINGWINGS, ci=1,
            choices={"Vespid Stingwings": {VESPID_BLASTER_TO_RAIL_RIFLE: 1}})
ck.eq("a 5-model Vespid unit cannot take a rail rifle",
      sum(1 for m in _v5.models for w in m.weapons if w.name == "Neutron Rail Rifle"), 0)
ck.eq("a 10-model one can take exactly one",
      sum(1 for m in _v10.models for w in m.weapons if w.name == "Neutron Rail Rifle"), 1)

_kb_swap = unit(KROOT_FARSTALKERS,
                choices={"Kroot Kill-broker": {KILL_BROKER_FIREARM_TO_TAU_TECH: 1}})
ck.true("the Kill-broker can trade his firearm for a T'au-tech rifle",
        any(w.name == "T'au-tech Rifle" for m in _kb_swap.models for w in m.weapons))
# Either special weapon can be taken, one model at most.
for _opt, _weapon in ((FARSTALKER_FIREARM_TO_SKINNER, "Dvorgite Skinner"),
                      (FARSTALKER_FIREARM_TO_TRIBALEST, "Londaxi Tribalest")):
    _one = unit(KROOT_FARSTALKERS, choices={"Kroot Farstalkers": {_opt: 2}})
    ck.eq(f"at most one {_weapon}",
          sum(1 for m in _one.models for w in m.weapons if w.name == _weapon), 1)
# KNOWN LIMITATION, pinned so that fixing it is a visible change. The printed
# text is "1 Kroot Farstalker's Farstalker firearm can be replaced with ONE OF
# the following", i.e. one model and one weapon between the two options. Two
# WargearOptions that give up the same weapon share build_squad()'s cursor,
# which makes them NON-OVERLAPPING (they land on different models) rather than
# EXCLUSIVE - so a build can currently take both, on two models. On a
# single-model line the two readings coincide, which is why the Enforcer's
# six-way burst-cannon menu needs nothing extra; here the line has nine models
# and they come apart. Expressing it properly needs a shared allowance across
# options, which WargearOption does not have.
_both = unit(KROOT_FARSTALKERS,
             choices={"Kroot Farstalkers": {FARSTALKER_FIREARM_TO_SKINNER: 1,
                                            FARSTALKER_FIREARM_TO_TRIBALEST: 1}})
_special = sum(1 for m in _both.models for w in m.weapons
               if w.name in ("Dvorgite Skinner", "Londaxi Tribalest"))
ck.eq("KNOWN LIMITATION: both special weapons can be taken, on two models "
      "(the printed text allows one)", _special, 2)


# --- 2. Kroot Hounds ------------------------------------------------------
# A/B: the charge-gate entry removed -> 2 fail; the OC fold removed -> 3.
print("\n2. Kroot Hounds: Loping Pounce, Hunting Hounds")

_hounds = unit(KROOT_HOUNDS)
_carn = unit(KROOT_CARNIVORES)
tk.line_up(_hounds, x=20.0, y=20.0)
tk.line_up(_carn, x=23.0, y=20.0)
_all = [_hounds, _carn]

ck.true("not latched to begin with", not loping_pounce.is_active(_hounds))
ck.eq("the Command phase latches it when Kroot infantry are within 6\"",
      [s.name for s in loping_pounce.begin_command_phase(_all, "Player 1")], [_hounds.name])
ck.true("...and it is now active", loping_pounce.is_active(_hounds))

# LATCHED, not live: the hounds may run away and keep it.
tk.line_up(_carn, x=60.0, y=20.0)
ck.true("it survives the Kroot walking away (it is latched, not live)",
        loping_pounce.is_active(_hounds))
loping_pounce.reset_turn(_all)
ck.true("and is cleared at the end of the turn", not loping_pounce.is_active(_hounds))

# Out of range at the moment of latching, it never starts.
_far = unit(KROOT_HOUNDS)
tk.line_up(_far, x=20.0, y=20.0)
ck.eq("out of range at the start of the Command phase, nothing latches",
      loping_pounce.begin_command_phase([_far, _carn], "Player 1"), [])
# A MOUNTED Kroot unit is not KROOT INFANTRY.
_krootox = unit(KROOTOX_RIDERS)
tk.line_up(_krootox, x=23.0, y=20.0)
ck.eq("a MOUNTED Krootox does not satisfy \"KROOT INFANTRY\"",
      loping_pounce.begin_command_phase([_far, _krootox], "Player 1"), [])
# A non-Kroot T'au unit does not either.
_strike = unit(STRIKE_TEAM)
tk.line_up(_strike, x=23.0, y=20.0)
ck.eq("neither does a Strike Team",
      loping_pounce.begin_command_phase([_far, _strike], "Player 1"), [])

# The charge gate itself: a unit that Advanced may not normally charge.
_state = GameState()
_enemy = unit(KROOT_CARNIVORES, owner="Player 2")
tk.line_up(_hounds, x=20.0, y=20.0)
tk.line_up(_enemy, x=34.0, y=20.0)   # clear of Engagement Range: a 5-model line is 5.6" wide
for _s in (_hounds, _enemy):
    for _m in _s.models:
        _state.add_token(_m)
_tt = TurnTracker(first_player="Player 1")
while _tt.phase != "Charge":
    _tt.advance_phase()


class _Mover:
    def __init__(self, advanced):
        self.advanced_squad_ids = advanced


_cc = ChargeController(all_tokens=_state.tokens, turn_tracker=_tt,
                       movement_controller=_Mover({_hounds}))
_hounds.loping_pounce_active = False
ck.true("after Advancing, a normal unit cannot declare a charge",
        not _cc.can_declare_charge(_hounds))
_hounds.loping_pounce_active = True
ck.true("with Loping Pounce latched, it can", _cc.can_declare_charge(_hounds))

# Hunting Hounds: the live "while", and the only thing that gives them any OC.
_shaper = unit(KROOT_FLESH_SHAPER)
tk.line_up(_hounds, x=20.0, y=20.0)
tk.line_up(_shaper, x=25.0, y=20.0)
_tokens = list(_hounds.models) + list(_shaper.models)
ck.eq("within 12\" of a Kroot character, OC is 1",
      objective_control.effective_oc(_hounds.models[0], _tokens), 1)
tk.line_up(_shaper, x=60.0, y=20.0)
ck.eq("beyond 12\", OC is back to the printed 0",
      objective_control.effective_oc(_hounds.models[0], _tokens), 0)
# Both halves of "friendly KROOT CHARACTER", isolated from each other - a unit
# that fails BOTH would leave either test unexercised.
_plain_kroot = unit(KROOT_CARNIVORES)          # KROOT, but no CHARACTER
tk.line_up(_plain_kroot, x=22.0, y=20.0)
ck.eq("a KROOT unit with no CHARACTER grants nothing",
      objective_control.effective_oc(
          _hounds.models[0], list(_hounds.models) + list(_plain_kroot.models)), 0)
_tau_character = unit(KROOT_FLESH_SHAPER)      # CHARACTER, and KROOT - the control
tk.line_up(_tau_character, x=22.0, y=20.0)
ck.eq("...while a KROOT CHARACTER at the same distance does",
      objective_control.effective_oc(
          _hounds.models[0], list(_hounds.models) + list(_tau_character.models)), 1)
ck.true("...and it is a LIVE condition, unlike Loping Pounce next door",
        not hunting_hounds.applies(_hounds, list(_hounds.models)))

# The sixteenth extraction still answers the Death Guard's question correctly.
ck.eq("objective_control also carries Scabrous Soulrot's worsening",
      objective_control.effective_oc(unit(STRIKE_TEAM).models[0], []),
      plagues.worsen_oc(unit(STRIKE_TEAM).models[0]))


# --- 3. Vespid Stingwings -------------------------------------------------
# A/B: withdraw_to_reserves() call removed -> 2 fail; the drone's chain entry
# removed -> 2; its once-per-battle ledger removed -> 1.
print("\n3. Vespid Stingwings: Airborne Agility, Oversight Drone")

_vstate = GameState()
_vespid = unit(VESPID_STINGWINGS, ci=1)
_foe = unit(KROOT_CARNIVORES, owner="Player 2")
tk.line_up(_vespid, x=20.0, y=20.0)
tk.line_up(_foe, x=40.0, y=20.0)
for _s in (_vespid, _foe):
    for _m in _s.models:
        _vstate.add_token(_m)
_aa = AirborneAgilityController(decision_manager=DecisionManager(), game_state=_vstate)

ck.true("out of Engagement Range, it can leave", _aa.can_use(_vespid))
tk.line_up(_foe, x=20.5, y=20.0)
ck.true("engaged, it cannot", not _aa.can_use(_vespid))
tk.line_up(_foe, x=40.0, y=20.0)
_before = len(_vstate.tokens)
ck.true("using it takes the unit off the board", _aa.use(_vespid))
ck.eq("...all ten models", _before - len(_vstate.tokens), 10)
ck.true("...and into Strategic Reserves", _vespid in _vstate.reserves)

# The timing: "at the end of your OPPONENT'S turn".
_aa2 = AirborneAgilityController(decision_manager=DecisionManager(), game_state=_vstate,
                                 auto_players=())
_v2 = unit(VESPID_STINGWINGS, ci=0)
for _m in _v2.models:
    _vstate.add_token(_m)
tk.line_up(_v2, x=20.0, y=30.0)
_dec = _aa2.decision_manager
ck.true("its own player's turn ending offers nothing",
        not _aa2.offer_at_end_of_turn([_v2], "Player 1"))
ck.true("the OPPONENT's turn ending does", _aa2.offer_at_end_of_turn([_v2], "Player 2"))
ck.true("...as a real choice, with a decline",
        any("Stay on the battlefield" in o for o in tk.options_of(_dec)))

# EVERY eligible unit is offered, not just the first. Reported: "ich habe 2
# vespiden, aber die rueckkehr in reserve wurde mir immer nur von einem der
# beiden squads angeboten" - the old loop raised one prompt and returned, and
# THIS SUITE could not see it, because every check above passes a single squad.
# So the check is the COUNT over a two-unit army, drained through the real
# DecisionManager queue (game/per_unit_offer.py chains them).
_pair_state = GameState()
_pair = [unit(VESPID_STINGWINGS, ci=0) for _ in range(2)]
for _i, _u in enumerate(_pair):
    _u.name = f"1 Vespid Stingwings {_i + 1}"
    tk.line_up(_u, x=15.0, y=15.0 + _i * 17.0)
    for _m in _u.models:
        _pair_state.add_token(_m)
_pair_foe = unit(KROOT_CARNIVORES, owner="Player 2")
tk.line_up(_pair_foe, x=45.0, y=20.0)
for _m in _pair_foe.models:
    _pair_state.add_token(_m)
_pair_dec = DecisionManager()
_pair_aa = AirborneAgilityController(decision_manager=_pair_dec, game_state=_pair_state,
                                     auto_players=())
ck.eq("both Vespid units are eligible",
      len(_pair_aa.eligible_squads(_pair, "Player 1")), 2)
_pair_aa.offer_at_end_of_turn(set(_pair) | {_pair_foe}, "Player 2")
_asked = []
while _pair_dec.is_pending and len(_asked) < 5:
    _asked.append(_pair_dec.prompt)
    _labels = [o["label"] for o in _pair_dec.options]
    _pair_dec.choose(_labels.index("Stay on the battlefield"))
ck.eq("...and BOTH are asked at one turn end", len(_asked), 2)
ck.true("...each prompt naming its own unit",
        all(any(u.name in p for p in _asked) for u in _pair))
# Declining left both on the board - otherwise "two prompts" could pass on a
# chain that withdrew a unit and then asked about the leftovers.
ck.eq("declining both leaves the board alone", len(_pair_state.reserves), 0)

# The AI is filtered OUT of the candidates rather than ending the sweep, so an
# AI unit earlier in the order cannot swallow a human one's offer. What the AI
# does is unchanged: it stays put.
_ai_dec = DecisionManager()
_ai_aa = AirborneAgilityController(decision_manager=_ai_dec, game_state=_pair_state,
                                   auto_players=("Player 1",))
ck.true("an auto_players owner is never prompted",
        not _ai_aa.offer_at_end_of_turn(set(_pair) | {_pair_foe}, "Player 2"))
ck.true("...and nothing is queued for it", not _ai_dec.is_pending)

# The Oversight Drone.
_drone_unit = unit(VESPID_STINGWINGS, ci=1,
                   gear={"Vespid Strain Leader": ["Oversight Drone"]})
ck.true("the drone marks its bearer",
        any(getattr(m.profile, "oversight_drone", False) for m in _drone_unit.models))
ck.true("a plain unit has none",
        not any(getattr(m.profile, "oversight_drone", False)
                for m in unit(VESPID_STINGWINGS, ci=1).models))
_od = OversightDroneController()
_blaster = next(w for w in _drone_unit.models[0].weapons if w.name == "Neutron Blaster")
ck.true("before use, no [IGNORES COVER]",
        not oversight_drone.adjusted_weapon(_blaster, _drone_unit).ignores_cover)
ck.true("it can be used", _od.can_use(_drone_unit))
_od.use(_drone_unit)
ck.true("after use the unit's ranged weapons ignore cover",
        oversight_drone.adjusted_weapon(_blaster, _drone_unit).ignores_cover)
ck.true("the shared weapon instance is not mutated", not _blaster.ignores_cover)
ck.true("melee is untouched",
        not oversight_drone.adjusted_weapon(
            next(w for w in _drone_unit.models[0].weapons if w.name == "Stingwing Claws"),
            _drone_unit).ignores_cover)
_od.reset_phase([_drone_unit])
ck.true("the grant ends with the phase",
        not oversight_drone.adjusted_weapon(_blaster, _drone_unit).ignores_cover)
ck.true("but the once-per-battle ledger does not reset", not _od.can_use(_drone_unit))


# --- 4. Krootox Riders ----------------------------------------------------
# A/B: the KROOT INFANTRY test dropped -> 2 fail; the once-per-turn ledger
# dropped -> 1; the deferral removed -> 1.
print("\n4. Krootox Riders: Kroot Packmates")

_pstate = GameState()
_krootox = unit(KROOTOX_RIDERS, ci=2)
_friend = unit(KROOT_CARNIVORES)
_shooter = unit(STRIKE_TEAM, owner="Player 2")
tk.line_up(_krootox, x=20.0, y=20.0)
tk.line_up(_friend, x=23.0, y=20.0)
tk.line_up(_shooter, x=40.0, y=20.0)
for _s in (_krootox, _friend, _shooter):
    for _m in _s.models:
        _pstate.add_token(_m)
_ptt = TurnTracker(first_player="Player 2")
_pk = KrootPackmatesController(game_state=_pstate, turn_tracker=_ptt,
                               decision_manager=DecisionManager())

ck.eq("a friendly KROOT INFANTRY unit within 6\" has a reactor",
      [s.name for s in _pk.reactors_for(_friend)], [_krootox.name])
# Both negative cases are placed IN RANGE, so the 6" test cannot stand in for
# the keyword test - with them at their build position the keyword check would
# never be exercised at all.
_near_strike = unit(STRIKE_TEAM)
tk.line_up(_near_strike, x=23.0, y=20.0)
ck.eq("a non-Kroot friendly unit in range does not react",
      _pk.reactors_for(_near_strike), [])
# The Krootox themselves are MOUNTED, so they are not their own trigger.
_near_krootox = unit(KROOTOX_RIDERS)
tk.line_up(_near_krootox, x=23.0, y=20.0)
ck.eq("another Krootox unit in range is not KROOT INFANTRY either",
      _pk.reactors_for(_near_krootox), [])
tk.line_up(_friend, x=60.0, y=20.0)
ck.eq("beyond 6\", nothing reacts", _pk.reactors_for(_friend), [])
tk.line_up(_friend, x=23.0, y=20.0)

# "IN YOUR OPPONENT'S SHOOTING PHASE", so a MELEE trigger is declined - the
# half of maybe_offer()'s contract this suite did not measure. Found by an A/B
# probe that deleted the melee clause from the shared base
# (game/reactive_bodyguard_shooting.py) and reported NO BITE here: a change to
# that base is meant to be visible to BOTH its carriers, and it was visible to
# only one.
ck.true("a MELEE attack never triggers it - the printed WHEN names a phase",
        not _pk.maybe_offer(_shooter, _friend, melee=True))
ck.true("...and the ranged form still does",
        _pk.maybe_offer(_shooter, _friend))
_pk._owed = None
_pk._used_this_turn.clear()
tk.pick_option(_pk.decision_manager, "Decline")

ck.true("the reaction is offered when the enemy picks its target",
        _pk.on_targets_selected(_shooter, [_friend]))
tk.pick_option(_pk.decision_manager, "Shoot back")
ck.true("once per turn: a second reaction is refused",
        not _pk.reactors_for(_friend))
ck.true("the shot is OWED, not fired at the trigger", _pk._owed is not None)
_ptt.battle_round += 1
_ptt.turn_owner = "Player 1"
ck.true("a new turn restores the use", bool(_pk.reactors_for(_friend)))


# --- 5. Krootox Rampagers -------------------------------------------------
# A/B: the per-model dice count replaced by the unit size -> 1 fails; the
# charge hook removed -> 1.
print("\n5. Krootox Rampagers: Kroot Linebreakers")

_lstate = GameState()
_ramp = unit(KROOTOX_RAMPAGERS, ci=0)
_prey = unit(KROOT_CARNIVORES, owner="Player 2")
tk.line_up(_ramp, x=20.0, y=20.0, spacing=1.4)
tk.line_up(_prey, x=20.0, y=21.0, spacing=1.4)
for _s in (_ramp, _prey):
    for _m in _s.models:
        _lstate.add_token(_m)
_lb = KrootLinebreakersController(dice_manager=tk.RecordingDice(), game_state=_lstate,
                                  auto_players=("Player 1",))
ck.eq("an enemy in Engagement Range is a target",
      [s.name for s in linebreaker_targets(_ramp, _lstate.tokens)], [_prey.name])
ck.eq("one D6 per model of THIS unit in Engagement Range",
      linebreaker_dice(_ramp, _prey), 3)
# Pull one Rampager out of contact: the dice count drops, the unit size does not.
_ramp.models[2].x_in, _ramp.models[2].y_in = 60.0, 60.0
ck.eq("a model out of contact rolls no die",
      (linebreaker_dice(_ramp, _prey), len(_ramp.models)), (2, 3))
_ramp.models[2].x_in, _ramp.models[2].y_in = 20.0 + 2 * 1.4, 20.0

_far_prey = unit(KROOT_CARNIVORES, owner="Player 2")
tk.line_up(_far_prey, x=60.0, y=60.0)
ck.eq("a charge that fell short finds no target",
      linebreaker_dice(_ramp, _far_prey), 0)
ck.true("...so the hook simply does nothing",
        not KrootLinebreakersController(
            dice_manager=tk.RecordingDice(),
            game_state=GameState()).on_charge_move_finished(_ramp))

tk.script(4, 4, 1)      # two 4+ out of three dice
ck.true("the charge hook starts the roll", _lb.on_charge_move_finished(_ramp))
ck.eq("...with one die per model in contact", len(_lb.dice_manager.last_roll[1]), 3)


# --- 6. Kroot Farstalkers -------------------------------------------------
# A/B: the shooting chain entry removed -> 2 fail; the fight one -> 1; the
# Pech'ra entry -> 2.
print("\n6. Kroot Farstalkers: Bounty Hunters, Pech'ra")

_hunter = unit(KROOT_FARSTALKERS)
_bounty = unit(KROOT_CARNIVORES, owner="Player 2")
_other = unit(STRIKE_TEAM, owner="Player 2")
_bhc = BountyHuntersController()
_picked = _bhc.select_at_start_of_battle([_hunter, _bounty, _other])
ck.eq("a bounty is taken at the start of the battle", len(_picked), 1)
ck.true("...on an enemy unit", _bhc.bounty_for(_hunter).owner == "Player 2")
ck.true("it applies against the bounty", _bhc.applies(_hunter, _bhc.bounty_for(_hunter)))
_notbounty = next(s for s in (_bounty, _other) if s is not _bhc.bounty_for(_hunter))
ck.true("and not against anyone else", not _bhc.applies(_hunter, _notbounty))
ck.true("a unit without the ability gets nothing",
        not _bhc.applies(unit(KROOT_CARNIVORES), _bhc.bounty_for(_hunter)))
ck.eq("choosing twice does not re-pick",
      len(_bhc.select_at_start_of_battle([_hunter, _bounty, _other])), 0)

_firearm = next(w for w in _hunter.models[0].weapons if w.name == "Farstalker Firearm")
_granted = _bhc.adjusted_weapon(_firearm, _hunter, _bhc.bounty_for(_hunter))
ck.true("the attack gains BOTH [LETHAL HITS] and [PRECISION]",
        _granted.lethal_hits and _granted.precision)
ck.true("the shared weapon instance is not mutated",
        not _firearm.lethal_hits and not _firearm.precision)
ck.true("against another unit it grants nothing",
        not _bhc.adjusted_weapon(_firearm, _hunter, _notbounty).lethal_hits)

# Pech'ra: unit-wide, ranged only.
_pechra = unit(KROOT_FARSTALKERS, gear={"Kroot Farstalkers": ["Pech'ra"]})
ck.true("the Pech'ra is unit-wide once taken", bh.unit_has_pechra(_pechra))
ck.true("a plain unit has none", not bh.unit_has_pechra(unit(KROOT_FARSTALKERS)))
_p_firearm = next(w for w in _pechra.models[0].weapons if w.name == "Farstalker Firearm")
ck.true("ranged weapons gain [IGNORES COVER]",
        bh.pechra_adjusted_weapon(_p_firearm, _pechra).ignores_cover)
_p_blade = next(w for w in _pechra.models if w.profile.name == "Kroot Kill-broker")
ck.true("melee weapons do not",
        not bh.pechra_adjusted_weapon(
            next(w for w in _p_blade.weapons if w.name == "Ritual Blade"),
            _pechra).ignores_cover)


# --- 7. Source guards -----------------------------------------------------
print("\n7. Source guards")

_main = open("main.py", encoding="utf-8").read()
ck.true("Loping Pounce latches at the start of the Command phase",
        "loping_pounce.begin_command_phase(" in _main)
ck.true("...and is cleared at end of turn", "loping_pounce.reset_turn(" in _main)
ck.true("Airborne Agility is offered at end of turn",
        "airborne_agility_controller.offer_at_end_of_turn(" in _main)
ck.true("Bounty Hunters is chosen at the start of the battle",
        "bounty_hunters_controller.select_at_start_of_battle(" in _main)
ck.true("the SAME bounty ledger reaches both attack controllers",
        _main.count("bounty_hunters=bounty_hunters_controller") == 2)
# Read as a SET of names via the AST rather than as the literal tuple text,
# which pinned Kroot Packmates as the LAST element and went red the moment a
# sixth reactor was appended - formatting, not meaning. The same lesson the
# closing-bracket and indentation pins in this repo already record.
_rx_names = []
for _node in ast.walk(ast.parse(_main)):
    if (isinstance(_node, ast.Assign) and len(_node.targets) == 1
            and isinstance(_node.targets[0], ast.Name)
            and _node.targets[0].id == "shooting_target_reactions"
            and isinstance(_node.value, ast.Tuple)):
        _rx_names = [e.id for e in _node.value.elts if isinstance(e, ast.Name)]
ck.true("the sweep found the tuple at all (%d reactors)" % len(_rx_names),
        len(_rx_names) >= 4)
ck.true("Kroot Packmates is in the shooting target_reactions list",
        "kroot_packmates_controller" in _rx_names)
ck.true("...and fires only once the attacker has finished",
        "kroot_packmates_controller.on_squad_finished_shooting)" in _main)
ck.true("Kroot Linebreakers is on the charge hook",
        "kroot_linebreakers_controller.on_charge_move_finished)" in _main)
ck.true("...its dice are acknowledged",
        "kroot_linebreakers_controller.on_dice_acknowledged()" in _main)
ck.true("...and its Battle-shock test is resolved afterwards",
        "kroot_linebreakers_controller.resolve_pending_battle_shock()" in _main)
ck.true("the Oversight Drone's grant is cleared at the phase boundary",
        "oversight_drone_controller.reset_phase(" in _main)

_charge = open("game/charge.py", encoding="utf-8").read()
# The gate grew from an inline disjunction in charge.py into
# game/move_exceptions.py, once three Aeldari Stratagems needed the same three
# bans lifted. Pinned in two halves so neither can rot silently: charge.py asks
# the shared question, and Loping Pounce is one of the answers. (This line was
# already once matched WITHOUT a closing paren, for the same reason - the
# disjunction kept growing.)
ck.true("charge.py asks the shared advance-then-charge question",
        "move_exceptions.may_charge_after_advancing(" in _charge)
ck.true("...and Loping Pounce is one of its sources",
        "loping_pounce.is_active(squad)"
        in open("game/move_exceptions.py", encoding="utf-8").read())
_shooting = open("game/shooting.py", encoding="utf-8").read()
_fight = open("game/fight.py", encoding="utf-8").read()
ck.true("Bounty Hunters is in BOTH attack chains (its text says 'an attack')",
        "self.bounty_hunters.adjusted_weapon(" in _shooting
        and "self.bounty_hunters.adjusted_weapon(" in _fight)
ck.true("the Pech'ra is shooting-only (its text says 'ranged weapons')",
        "pechra_adjusted_weapon" in _shooting and "pechra_adjusted_weapon" not in _fight)
ck.true("so is the Oversight Drone",
        "oversight_drone_module.adjusted_weapon" in _shooting
        and "oversight_drone" not in _fight)
_objectives = open("game/objectives.py", encoding="utf-8").read()
# Checks the CALL, not its full argument list: the funnel grew an optional
# `objective=` argument when Mont'ka's Strategic Conqueror Enhancement became
# the third OC source, and pinning the whole call text made this line fail for
# a reason it never meant to test. Same lesson as the two other pins in this
# repo that froze punctuation instead of the call.
ck.true("objectives read the extracted OC funnel, not the Death Guard module",
        "objective_control.effective_oc(token, all_tokens" in _objectives
        and "plagues.effective_oc(" not in _objectives)
_plagues_src = open("game/plagues.py", encoding="utf-8").read()
ck.true("the old lying name is gone",
        "def effective_oc(" not in _plagues_src and "def worsen_oc(" in _plagues_src)

# ART ARRIVED for the other four; Vespid.png had been sitting unused in the
# folder since before its datasheet existed. Asserted at the MODEL, never at
# the mapping table.
from game import sprites  # noqa: E402
for name, sheet in SHEETS.items():
    for _m in unit(sheet).models:
        ck.true(f"{name}: {_m.profile.name} has art", sprites.sprite_for(_m) is not None)

# KROOT FARSTALKERS IS THE INTERESTING ONE: three model lines, two images.
# User instruction "fuer Farstalkers die normalen Kroot Sprites" - so the
# Kill-broker and his nine Farstalkers borrow the Kroot Carnivores art, while
# the two Kroot Hounds printed inside the unit take the Kroot Hounds image.
# A squad-level key cannot reach those hounds at all: the squad is named
# "1 Kroot Farstalkers 1", so the "Kroot Hounds" key never matches it - which
# is precisely what MODEL_SPRITE_KEYS exists for.
_fs_art = {m.profile.name: sprites._squad_key(m) for m in unit(KROOT_FARSTALKERS).models}
ck.eq("the Kill-broker and the Farstalkers take the normal Kroot art",
      (_fs_art["Kroot Kill-broker"], _fs_art["Kroot Farstalker"]),
      ("Kroot Carnivores", "Kroot Carnivores"))
ck.eq("...while the hounds inside the unit take the Kroot Hounds art",
      _fs_art["Kroot Hound (Farstalker)"], "Kroot Hounds")
ck.eq("...which is the same image the Kroot Hounds datasheet uses",
      sprites._squad_key(unit(KROOT_HOUNDS).models[0]), "Kroot Hounds")

ck.finish()
