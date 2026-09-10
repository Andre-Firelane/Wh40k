"""Deathmarks, Flayed Ones, Cryptothralls and Tomb Blades (Etappe 2).

FOUR DATASHEETS THAT SHARE NOTHING but a faction, which is the opposite of
Etappe 1 - so this suite is almost entirely about each ability landing on the
right seam, and about the three seams that are genuinely new.

WHERE THIS MEASURES, AND WHY THERE
----------------------------------
  * Flesh Hunger is measured against the HIT THRESHOLD, not against a number.
    "A successful Hit roll scores a Critical Hit" means the crit threshold IS
    the hit threshold, so a test that pinned a 6 or a 5 would pass with the
    rule implemented as a fixed value - and would not notice a WS3+ model
    critting on 3s, which is the whole ability.

  * Shieldvanes is measured on BOTH halves, because it is a TRADE: Sv 4+ -> 3+
    is better and M 12" -> 8" is WORSE. A grant written the usual _better()
    way would keep the 12" and hand out the save for free, and a test that
    only looked at the save would pass.

  * Shadowloom is measured at the UNIT, on one bearer and then on all of them.
    Rule 24.33 is an every-model ability, so one shadowloom must grant the
    unit nothing - the case that separates "the gear works" from "the gear is
    read the way the rule reads".

  * Cryptek Retinue is measured on STARTING STRENGTH, not on the model count.
    That number is what 01.02.03 caps Reanimation Protocols at and what Below
    Half-strength reads, so it is the half of the rule that reaches other
    rules.

  * Bound Creation is measured on all THREE kinds of model in the merged unit
    - the Cryptek, a bodyguard, and a Cryptothrall - because the printed
    subject is "that CRYPTEK model" and every wrong reading of it gives the 4+
    to at least one of the other two.
"""
import io

import testkit as tk
from testkit import Checks

from game import (attached_units, coldstar, crit_hit, cryptothralls,
                  damage_resolution, evasion_engrams, feel_no_pain,
                  formations, hyperspace_hunters, shooting, sprites,
                  squad as squad_mod, tomb_blade_wargear)
from game.factions import aeldari as ae, necrons as nec
from game.factions.necrons_points import NECRONS_POINTS
from game.movement import MovementController
from game.units import (CryptothrallProfile, DeathmarkProfile,
                        FlayedOneProfile, TombBladeProfile)
from game.weapons import (FlayerClawsProfile, GaussBlasterProfile,
                          GaussFlayerProfile, NecronCloseCombatWeaponA1Profile,
                          NecronCloseCombatWeaponA2Profile,
                          ParticleBeamerS5Profile, ScouringEyeProfile,
                          ScythedLimbsProfile, SynapticDisintegratorProfile,
                          TeslaCarbineProfile, TwinGaussBlasterProfile,
                          TwinTeslaCarbineProfile)

checks = Checks("Necron rank and file")

D = nec.NECRONS.datasheets
DEATHMARKS = D["Deathmarks"]
FLAYED_ONES = D["Flayed Ones"]
CRYPTOTHRALLS = D["Cryptothralls"]
TOMB_BLADES = D["Tomb Blades"]
WARRIORS = D["Necron Warriors"]
IMMORTALS = D["Immortals"]

SHEETS = [(DEATHMARKS, DeathmarkProfile), (FLAYED_ONES, FlayedOneProfile),
          (CRYPTOTHRALLS, CryptothrallProfile), (TOMB_BLADES, TombBladeProfile)]


def build(sheet, owner="Player 2", n=1, **kw):
    """Named the way main.py names squads - see the sprite trap in
    game/sprites.py's _key_for_name()."""
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


# --- 1. statlines ---
print("--- 1. statlines ---")

for sheet, profile in SHEETS:
    checks.true("%s: Reanimation Protocols" % sheet.name, profile.reanimation_protocols)

checks.eq("Deathmark: M5\" T5 Sv3+ W1 Ld7+ OC1 on 32 mm",
          (DeathmarkProfile.movement_in, DeathmarkProfile.toughness,
           DeathmarkProfile.armor_save, DeathmarkProfile.wounds,
           DeathmarkProfile.leadership, DeathmarkProfile.oc,
           round(DeathmarkProfile.base_radius_in, 3)),
          (5, 5, "3+", 1, "7+", 1, 0.630))
checks.true("...with Deep Strike", DeathmarkProfile.deep_strike)
checks.eq("Flayed One: M5\" T4 Sv4+ W1 on 28.5 mm",
          (FlayedOneProfile.movement_in, FlayedOneProfile.toughness,
           FlayedOneProfile.armor_save, round(FlayedOneProfile.base_radius_in, 3)),
          (5, 4, "4+", 0.561))
checks.true("...with Infiltrators and Stealth",
            FlayedOneProfile.infiltrators and FlayedOneProfile.stealth)
checks.eq("Cryptothrall: Sv3+ W3 Ld8+ - a bodyguard, not a gun",
          (CryptothrallProfile.armor_save, CryptothrallProfile.wounds,
           CryptothrallProfile.leadership), ("3+", 3, "8+"))
checks.eq("Tomb Blade: M12\" T5 Sv4+ W2 OC2",
          (TombBladeProfile.movement_in, TombBladeProfile.toughness,
           TombBladeProfile.armor_save, TombBladeProfile.wounds,
           TombBladeProfile.oc), (12, 5, "4+", 2, 2))
checks.true("...MOUNTED, FLY and Scouts 9\"",
            TombBladeProfile.mounted and TombBladeProfile.fly
            and TombBladeProfile.scouts == 9.0)

# --- 2. weapons, and the four shares ---
print("--- 2. weapons, and the four shares ---")

sd = SynapticDisintegratorProfile()
checks.eq("Synaptic disintegrator: 36\" A1 S5 AP-2 D2",
          (sd.range_in, sd.attacks, sd.strength, sd.ap, sd.damage), (36, 1, 5, -2, 2))
checks.true("...[HEAVY] and [PRECISION]", sd.heavy and sd.precision)
fc = FlayerClawsProfile()
checks.eq("Flayer claws: A4 S4 AP-1 D1",
          (fc.attacks, fc.strength, fc.ap, fc.damage), (4, 4, -1, 1))
checks.true("...[SUSTAINED HITS 1] and [TWIN-LINKED]",
            fc.sustained_hits == 1 and fc.twin_linked)
checks.eq("Scouring eye is a 6\" gun", ScouringEyeProfile().range_in, 6)
checks.eq("Scythed limbs: A4 S5 AP-1",
          (ScythedLimbsProfile().attacks, ScythedLimbsProfile().strength,
           ScythedLimbsProfile().ap), (4, 5, -1))
pb = ParticleBeamerS5Profile()
checks.true("Particle beamer rolls a real D6 for Attacks",
            pb.attacks_notation is not None)
checks.true("...[BLAST] and [DEVASTATING WOUNDS]", pb.blast == 1 and pb.devastating_wounds)

# THE TWO INHERITANCES, pinned against their siblings rather than against
# literals - which is what keeps them from drifting apart.
checks.true("Twin gauss blaster IS the Gauss Blaster plus [TWIN-LINKED]",
            issubclass(TwinGaussBlasterProfile, GaussBlasterProfile)
            and TwinGaussBlasterProfile.twin_linked
            and not GaussBlasterProfile.twin_linked)
checks.eq("...and nothing else differs",
          (TwinGaussBlasterProfile.range_in, TwinGaussBlasterProfile.attacks,
           TwinGaussBlasterProfile.strength, TwinGaussBlasterProfile.ap),
          (GaussBlasterProfile.range_in, GaussBlasterProfile.attacks,
           GaussBlasterProfile.strength, GaussBlasterProfile.ap))
checks.true("Twin tesla carbine IS the Tesla Carbine plus [TWIN-LINKED]",
            issubclass(TwinTeslaCarbineProfile, TeslaCarbineProfile)
            and TwinTeslaCarbineProfile.twin_linked)

# THE SHARES. Cloning either of these would have been the inverse of the
# "same name, other numbers" trap - the numbers ARE the same.
dm = build(DEATHMARKS)
checks.true("Deathmarks SHARE the Necron A2 close combat weapon",
            any(isinstance(w, NecronCloseCombatWeaponA2Profile)
                for w in dm.models[0].weapons))
tb = build(TOMB_BLADES)
checks.true("Tomb Blades SHARE the Necron A1 one",
            any(isinstance(w, NecronCloseCombatWeaponA1Profile)
                for w in tb.models[0].weapons))

# --- 3. composition, points and wargear ---
print("--- 3. composition, points and wargear ---")

checks.eq("Deathmarks come 5 or 10",
          [len(build(DEATHMARKS, n=i, composition_index=i).models) for i in (0, 1)], [5, 10])
checks.eq("Flayed Ones come 5 or 10",
          [len(build(FLAYED_ONES, n=i, composition_index=i).models) for i in (0, 1)], [5, 10])
checks.eq("Cryptothralls come as exactly 2", len(build(CRYPTOTHRALLS).models), 2)
checks.eq("Tomb Blades come 3 or 6",
          [len(build(TOMB_BLADES, n=i, composition_index=i).models) for i in (0, 1)], [3, 6])

checks.eq("Deathmarks: 60/120, then 70/130 from the third unit",
          (NECRONS_POINTS["Deathmarks"].cost_for(5, 1),
           NECRONS_POINTS["Deathmarks"].cost_for(10, 1),
           NECRONS_POINTS["Deathmarks"].cost_for(5, 3),
           NECRONS_POINTS["Deathmarks"].cost_for(10, 3)), (60, 120, 70, 130))
checks.eq("Flayed Ones: 55/100 flat",
          (NECRONS_POINTS["Flayed Ones"].cost_for(5, 1),
           NECRONS_POINTS["Flayed Ones"].cost_for(10, 3)), (55, 100))
checks.eq("Cryptothralls: 60", NECRONS_POINTS["Cryptothralls"].cost_for(2, 1), 60)
checks.eq("Tomb Blades: 70/140, then 80/150",
          (NECRONS_POINTS["Tomb Blades"].cost_for(3, 1),
           NECRONS_POINTS["Tomb Blades"].cost_for(6, 1),
           NECRONS_POINTS["Tomb Blades"].cost_for(3, 3),
           NECRONS_POINTS["Tomb Blades"].cost_for(6, 3)), (70, 140, 80, 150))

swapped = build(TOMB_BLADES, n=2,
                choices={"Tomb Blade": {nec.TOMB_BLADES_TO_PARTICLE_BEAMER: 1}})
checks.true("a Tomb Blade can trade its twin gauss blaster for a particle beamer",
            any(isinstance(w, ParticleBeamerS5Profile) for w in swapped.models[0].weapons))
checks.true("...and the rest of the squad keeps theirs",
            any(isinstance(w, TwinGaussBlasterProfile) for w in swapped.models[1].weapons))

# --- 4. Hyperspace Hunters ---
print("--- 4. Hyperspace Hunters ---")

hunters = build(DEATHMARKS, n=3)
tk.line_up(hunters, x=20.0, y=20.0)
arrival = build(IMMORTALS, owner="Player 1", n=3)
tk.line_up(arrival, x=20.0, y=30.0)          # 10" - inside the 18"
far = build(IMMORTALS, owner="Player 1", n=4)
tk.line_up(far, x=20.0, y=60.0)              # 40" - outside


class _Ingress:
    def __init__(self, arrived=()):
        self.ingressed_this_turn = set(arrived)


class _Shooting:
    """Records what the ability actually STARTS. The controller's return value
    is False whenever there is no shooting controller at all, so a test that
    reads it cannot tell "declined" from "fired" - which is exactly how the
    own-phase clause went unmeasured until an A/B probe said so."""

    def __init__(self):
        self.calls = []

    def start_reactive_shooting(self, squad, restrict_to=None):
        self.calls.append((squad.name, getattr(restrict_to, "name", None)))
        return True


tokens = list(hunters.models) + list(arrival.models) + list(far.models)
hh = hyperspace_hunters.HyperspaceHuntersController(
    ingress_controller=_Ingress([arrival, far]), all_tokens=tokens, game_log=tk.Log())
checks.eq("it reaches 18 inches", hyperspace_hunters.HYPERSPACE_HUNTERS_RANGE_IN, 18.0)
checks.eq("a unit arriving 10\" away is hunted",
          [s.name for s in hh.hunters_for(arrival)], [hunters.name])
checks.eq("...one arriving 40\" away is not", hh.hunters_for(far), [])

# THE TRAP: on_ingress_resolved fires on CANCEL too, and a cancelled placement
# must not hand out a free volley.
cancelled = hyperspace_hunters.HyperspaceHuntersController(
    ingress_controller=_Ingress([]), all_tokens=tokens, game_log=tk.Log())
checks.eq("a CANCELLED ingress hunts nothing", cancelled.hunters_for(arrival), [])

# END TO END, because "shoot as if it were your Shooting phase, BUT MUST ONLY
# TARGET THAT ENEMY UNIT" is two clauses and the second one is the restriction.
shots = _Shooting()
auto = hyperspace_hunters.HyperspaceHuntersController(
    ingress_controller=_Ingress([arrival]), all_tokens=tokens, game_log=tk.Log(),
    shooting_controller=shots, auto_players=("Player 2",))
checks.true("in the opponent's Movement phase it really shoots",
            auto.offer_on_arrival(arrival, phase_owner="Player 1"))
checks.eq("...restricted to the unit that just arrived",
          shots.calls, [(hunters.name, arrival.name)])

# "your OPPONENT'S Movement phase" - the hunter may not be the one moving.
own = _Shooting()
auto2 = hyperspace_hunters.HyperspaceHuntersController(
    ingress_controller=_Ingress([arrival]), all_tokens=tokens, game_log=tk.Log(),
    shooting_controller=own, auto_players=("Player 2",))
auto2.offer_on_arrival(arrival, phase_owner="Player 2")
checks.eq("...and it does not fire in the hunter's own Movement phase",
          own.calls, [])

checks.true("...and it is once per turn: the second arrival finds it spent",
            not auto.offer_on_arrival(far, phase_owner="Player 1"))

# --- 5. Flesh Hunger ---
print("--- 5. Flesh Hunger ---")

claws = build(FLAYED_ONES, n=5)
prey = build(WARRIORS, owner="Player 1", n=5)
checks.eq("against a full-strength unit, rule 05.01's unmodified 6",
          crit_hit.crit_hit_threshold(claws.models[0], prey, melee_only=True,
                                      hit_threshold=3), 6)
checks.eq("the prey starts at ten models", len(prey.models), 10)
del prey.models[:5]                          # strength is counted in MODELS
checks.true("EXACTLY half is not Below Half-strength - the boundary",
            not squad_mod.is_below_half_strength(prey))
checks.eq("...so the ability still grants nothing there",
          crit_hit.crit_hit_threshold(claws.models[0], prey, melee_only=True,
                                      hit_threshold=3), 6)
del prey.models[0]
checks.true("one model further down, it IS Below Half-strength",
            squad_mod.is_below_half_strength(prey))
checks.eq("...so a successful Hit roll crits - the threshold IS the hit roll",
          crit_hit.crit_hit_threshold(claws.models[0], prey, melee_only=True,
                                      hit_threshold=3), 3)
checks.eq("...and it follows the hit roll rather than being a fixed number",
          crit_hit.crit_hit_threshold(claws.models[0], prey, melee_only=True,
                                      hit_threshold=5), 5)
checks.eq("RANGED attacks are untouched - the clause says melee",
          crit_hit.crit_hit_threshold(claws.models[0], prey, melee_only=False,
                                      hit_threshold=3), 6)
checks.eq("...and a unit without the ability gets nothing",
          crit_hit.crit_hit_threshold(build(WARRIORS, n=6).models[0], prey,
                                      melee_only=True, hit_threshold=3), 6)

# --- 6. the Cryptothralls' three rules ---
print("--- 6. the Cryptothralls' three rules ---")

host = build(WARRIORS, n=7)
before = host.starting_model_count
attached_units.attach(build(D["Technomancer"], n=7), host)
thralls = build(CRYPTOTHRALLS, n=7)
checks.eq("Cryptothralls attach by a THIRD role",
          attached_units.attachment_role(thralls), attached_units.RETINUE)
checks.true("a host led by a Cryptek qualifies",
            cryptothralls.host_is_led_by_cryptek(host))
_bare = build(IMMORTALS, n=7)
checks.true("...one without does not",
            not cryptothralls.host_is_led_by_cryptek(_bare))
checks.eq("...and the join is legal", cryptothralls.retinue_join_errors(thralls, host), [])
checks.true("...while the join into an unled host is REFUSED - the clause "
            "measured where the step asks it, not just at its predicate",
            bool(cryptothralls.retinue_join_errors(thralls, _bare)))
# attach() RAISES on an illegal pairing, and an A/B probe that removes the
# RETINUE role would abort the whole run instead of turning it red - which is
# the least useful thing a probe can do, because an aborted run does not say
# WHICH assurance broke. Degraded on purpose.
try:
    attached_units.attach(thralls, host)
    _joined = True
except ValueError as exc:
    _joined = False
    checks.true("the retinue can attach at all: %s" % exc, False)
checks.eq("STARTING STRENGTH grows by the retinue - what 01.02.03 and Below "
          "Half-strength read", host.starting_model_count,
          before + 1 + 2 if _joined else -1)


def first(models, name):
    for m in models:
        if m.profile.name == name:
            return m
    return None


_cryptek = first(host.models, "Technomancer")
_warrior = first(host.models, "Necron Warrior")
_thrall = first(host.models, "Cryptothrall")
def fnp(model):
    return feel_no_pain.current_feel_no_pain(model) if model is not None else "(absent)"


checks.eq("Bound Creation gives the CRYPTEK 4+", fnp(_cryptek), "4+")
checks.eq("...and not the bodyguards", fnp(_warrior), "5+")
checks.eq("...nor the Cryptothralls themselves", fnp(_thrall), "5+")

# One retinue per host, checkable while declarations are still being collected.
checks.true("a SECOND Cryptothralls unit is refused",
            bool(cryptothralls.retinue_join_errors(
                build(CRYPTOTHRALLS, n=8), host, already_joined=(thralls,))))

# ...AND ONCE THE JOIN HAS HAPPENED, which is the half this suite was missing
# and the reason the printed parenthesis went unenforced for two stages. The
# line above measures the DECLARATION-time list that pregame.py keeps; the
# claim it was written next to was about rule 19.01 itself ("one unit per ROLE
# gives this for free"), and 19.01's check read leader_components(), which
# deliberately excludes the RETINUE role - so it never saw one. Both halves are
# pinned now, because only the second one is the RULE.
checks.true("...and 19.01 itself refuses one, now that the join stands",
            bool(attached_units.can_attach(build(CRYPTOTHRALLS, n=10), host)))
checks.eq("...while the FIRST retinue was allowed - the check narrows, not bans",
          attached_units.can_attach(
              build(CRYPTOTHRALLS, n=11),
              attached_units.attach(build(D["Technomancer"], n=12),
                                    build(WARRIORS, n=13, composition_index=0))),
          [])
# The one-per-role check is UNMOVED for the two older roles: same components,
# same role filter, one helper earlier. Measured rather than asserted.
_lead_host = attached_units.attach(build(D["Technomancer"], n=14),
                                   build(WARRIORS, n=15, composition_index=0))
checks.true("a second SUPPORT unit is still refused",
            bool(attached_units.can_attach(build(D["Technomancer"], n=16), _lead_host)))

# Systematic Vigour: eligibility, at the boundary its two siblings do not print.
sv = cryptothralls.SystematicVigourController(game_log=tk.Log())
lone = build(CRYPTOTHRALLS, n=9)
checks.eq("it rolls a 2+", cryptothralls.SYSTEMATIC_VIGOUR_THRESHOLD, 2)
checks.true("a Cryptothrall that has not fought is eligible",
            sv.is_eligible(lone.models[0]))
checks.true("...a Necron Warrior never is",
            not sv.is_eligible(build(WARRIORS, n=9).models[0]))


class _Fought:
    def __init__(self, squads):
        self.fought_squad_ids = list(squads)


sv2 = cryptothralls.SystematicVigourController(
    game_log=tk.Log(), fight_controller=_Fought([lone]))
checks.true("...and one whose unit has already fought is NOT - the clause its "
            "two siblings do not print", not sv2.is_eligible(lone.models[0]))

# --- 7. the Tomb Blades' wargear ---
print("--- 7. the Tomb Blades' wargear ---")

plain = build(TOMB_BLADES, n=10)
vaned = build(TOMB_BLADES, n=11, gear={"Tomb Blade": [nec.TOMB_BLADES_SHIELDVANES]})
gun = GaussFlayerProfile()
checks.eq("Shieldvanes IMPROVES the save: 4+ -> 3+",
          (damage_resolution.save_thresholds(plain.models[0], gun)[0],
           damage_resolution.save_thresholds(vaned.models[0], gun)[0]), (4, 3))
checks.eq("...and WORSENS the move: 12\" -> 8\". A trade, so both are overrides",
          (coldstar.effective_movement_in(plain.models[0]),
           coldstar.effective_movement_in(vaned.models[0])), (12, 8))

scoped = build(TOMB_BLADES, n=12, gear={"Tomb Blade": [nec.TOMB_BLADES_NEBULOSCOPE]})
checks.true("Nebuloscope grants [IGNORES COVER] to a RANGED weapon",
            tomb_blade_wargear.adjusted_weapon(
                TwinGaussBlasterProfile(), scoped.models[0]).ignores_cover)
checks.true("...and never to a melee one",
            not getattr(tomb_blade_wargear.adjusted_weapon(
                NecronCloseCombatWeaponA1Profile(), scoped.models[0]),
                "ignores_cover", False))
checks.true("...and nothing for an unscoped model",
            not tomb_blade_wargear.adjusted_weapon(
                TwinGaussBlasterProfile(), plain.models[0]).ignores_cover)

# THE MODEL'S OWN instance, not a fresh one: a fresh instance survives a grant
# that mutates in place, so only this can tell a copy from a mutation.
_carried = [w for w in scoped.models[0].weapons
            if isinstance(w, TwinGaussBlasterProfile)][0]
_out = tomb_blade_wargear.adjusted_weapon(_carried, scoped.models[0])
checks.true("...granted on a COPY, so the model's own weapon is untouched",
            _out is not _carried and not getattr(_carried, "ignores_cover", False))

# END TO END through the real ranged chain, because a grant that only reaches
# its own module is this repo's most expensive failure shape.
_scene = tk.shooting_scene(TOMB_BLADES, WARRIORS, attacker_owner="Player 2")
_shooter = _scene["attacker"].models[0]
_shooter.nebuloscope = True
_scene["shooting"].active_squad = _scene["attacker"]
_gun = [w for w in _shooter.weapons if isinstance(w, TwinGaussBlasterProfile)][0]
checks.true("the chain hands the hit step a scoped weapon",
            _scene["shooting"]._adjusted_weapon(
                [(_shooter, _gun)], _scene["target"]).ignores_cover)
_plain_shooter = _scene["attacker"].models[1]
_plain_gun = [w for w in _plain_shooter.weapons
              if isinstance(w, TwinGaussBlasterProfile)][0]
checks.true("...and an unscoped squadmate's is unchanged",
            not _scene["shooting"]._adjusted_weapon(
                [(_plain_shooter, _plain_gun)], _scene["target"]).ignores_cover)
checks.true("...and the two do not share an attack group, so the "
            "one-representative shortcut cannot answer for both",
            shooting._attack_key(_shooter, _gun)
            != shooting._attack_key(_plain_shooter, _plain_gun))

# SHADOWLOOM AT THE UNIT, which is where 24.33 asks.
loomed_one = build(TOMB_BLADES, n=13)
loomed_one.models[0].shadowloom = True
checks.eq("one shadowloom grants the UNIT nothing - rule 24.33 is every-model",
          squad_mod.squad_has_stealth(loomed_one), False)
loomed_all = build(TOMB_BLADES, n=14)
for m in loomed_all.models:
    m.shadowloom = True
checks.true("...and a shadowloom on every model does",
            squad_mod.squad_has_stealth(loomed_all))

# --- 8. Evasion Engrams ---
print("--- 8. Evasion Engrams ---")

checks.eq("it moves 6 inches", evasion_engrams.EVASION_ENGRAMS_MOVE_IN, 6.0)
checks.true("its move mode is waited on at a phase change",
            evasion_engrams.EVASION_ENGRAMS_MOVE_MODE
            in MovementController.OUT_OF_PHASE_MOVE_MODES)
mover = build(TOMB_BLADES, n=15)
tk.line_up(mover, x=20.0, y=20.0)
foe = build(IMMORTALS, owner="Player 1", n=15)
tk.line_up(foe, x=20.0, y=20.8)              # inside Engagement Range
checks.true("it is available while ENGAGED - it prints no Engagement Range "
            "clause, unlike its two closest neighbours",
            evasion_engrams.can_use(mover, list(mover.models) + list(foe.models)))
# ...and the two that DO print one still refuse, so this is a real difference.
from game import chronometron, fire_and_fade
chrono = build(D["Chronomancer"], n=15)
tk.line_up(chrono, x=20.0, y=20.0)
checks.true("...where the Chronometron refuses in the same position",
            not chronometron.can_use(chrono, list(chrono.models) + list(foe.models)))

# --- 9. wiring, AI negative space and sprites ---
print("--- 9. wiring, AI negative space and sprites ---")

main_src = io.open("main.py", encoding="utf-8").read()
for needle, label in [
    ("shooting_controller.on_squad_finished_shooting.append("
     "evasion_engrams_controller.offer_after_shooting)",
     "Evasion Engrams is offered after shooting"),
    ("evasion_engrams_controller=evasion_engrams_controller,",
     "...and its Confirm button reaches its own controller"),
    ("hyperspace_hunters_controller.offer_on_arrival(",
     "Hyperspace Hunters is fed by the ingress listener"),
    ("hyperspace_hunters_controller.reset_turn()",
     "...and its once-per-turn ledger is cleared"),
    ("systematic_vigour_controller.intercept_destroyed(_swept)",
     "Systematic Vigour is fed by the death sweep"),
    ("systematic_vigour_controller.resolve_after_attacks(_fighter)",
     "...and drained when the attacker finishes"),
    ("or systematic_vigour_controller.is_busy",
     "...and it blocks the phase while it owes an activation"),
    ("systematic_vigour_controller.reset_phase()",
     "...and gives up anything still owed at the end of the phase"),
]:
    checks.true("main.py: %s" % label, needle in main_src)

for ctor, user in [
    ("evasion_engrams_controller = EvasionEngramsController(",
     "evasion_engrams_controller.offer_after_shooting"),
    ("hyperspace_hunters_controller = HyperspaceHuntersController(",
     "hyperspace_hunters_controller.offer_on_arrival("),
    ("systematic_vigour_controller = SystematicVigourController(",
     "systematic_vigour_controller.intercept_destroyed(_swept)"),
]:
    checks.true("main.py builds %s before it is used" % ctor.split(" =")[0],
                0 <= main_src.find(ctor) < main_src.find(user))

# The join offer names the RIGHT rule - two printed rules share that panel now.
checks.eq("the Cryptothralls' offer is labelled Cryptek Retinue",
          formations.join_rule_label(build(CRYPTOTHRALLS, n=16)),
          formations.CRYPTEK_RETINUE)
checks.eq("...and the platform's is still Support Artillery",
          formations.join_rule_label(tk.build(
              ae.AELDARI.datasheets["D-cannon Platform"], "Player 1",
              name="1 D-cannon Platform 1")), formations.SUPPORT_ARTILLERY)
checks.eq("...and an ordinary unit is offered neither",
          formations.join_rule_label(build(WARRIORS, n=16)), None)

ai_src = io.open("ai/agent_driver.py", encoding="utf-8").read()
checks.true("no AI path names any of these abilities",
            not any(n in ai_src for n in ("hyperspace_hunters", "flesh_hunger",
                                          "bound_creation", "systematic_vigour",
                                          "evasion_engrams", "nebuloscope",
                                          "shadowloom", "shieldvanes",
                                          "cryptek_retinue")))

WITHOUT_ART = {"Flayed Ones"}
for sheet, _p in SHEETS:
    art = sprites.sprite_for(build(sheet, n=30).models[0])
    if sheet.name in WITHOUT_ART:
        checks.eq("%s has no art yet - pinned so adding one is visible" % sheet.name,
                  art, None)
    else:
        checks.true("%s draws its own art" % sheet.name, art is not None)

checks.finish()
