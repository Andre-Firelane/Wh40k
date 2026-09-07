"""The T'au detachment Stratagems.

What is worth guarding here is not "does the flag get set" - it is the WHEN and
the TARGET lines, and whether the effect reaches the seam that resolves it. So
most checks below drive can_use() across its printed boundary, and the effects
are read out of the real attack chains.

  1. The panel mechanism: one list, not one parameter per Stratagem.
  2. Experimental Prototype Cadre - Experimental Ammunition (two modes).
  3. Auxiliary Cadre - Experimental Modifications, Alien Expertise, Guided Fire.
  4. Source guards and wiring.
  5. A/B probes.
  6. Kauyon - its six.
  7. Mont'ka - its six.
  8. Advanced Acquisition Cadre - its three.
  9. All nineteen, counted.
"""

import inspect
import io
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import testkit as tk  # noqa: E402
from game import (aux_alien_expertise as alien, aux_experimental_modifications as mods,  # noqa: E402
                  aux_guided_fire as guided, config,
                  epc_experimental_ammunition as ammo, proactive_stratagems)
from game.command_points import CommandPointManager  # noqa: E402
from game.factions.orks import BOYZ  # noqa: E402
from game.factions.tau_empire import (COMMANDER_IN_COLDSTAR_BATTLESUIT,  # noqa: E402
                                      KROOT_CARNIVORES, STRIKE_TEAM)
from game.decision import DecisionManager  # noqa: E402
from game.stratagems import StratagemController  # noqa: E402
from game.turn import (PHASE_CHARGE, PHASE_FIGHT, PHASE_MOVEMENT,  # noqa: E402
                       PHASE_SHOOTING, PHASES, TurnTracker)
from game.weapons import MELEE, RANGED  # noqa: E402

c = tk.Checks("T'au detachment Stratagems")

HUMAN = "Player 1"


# The one definition lives in testkit - eight suites had their own copy.
settings_as = tk.settings_as

def turn_at(phase, owner=HUMAN):
    tracker = TurnTracker(first_player=owner)
    tracker.phase_index = PHASES.index(phase)
    tracker.turn_owner = owner
    tracker.active_player = owner
    return tracker


def strat_controller(cp=10):
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=tk.Log())


class ShootStub:
    """Stands in for ShootingController's two "selected to shoot" questions."""

    def __init__(self, can=True, active=None):
        self.can = can
        self.active_squad = active

    def can_shoot(self, squad):
        return self.can


class FightStub:
    def __init__(self, eligible=True, fought=()):
        self.eligible = eligible
        self.fought_squad_ids = set(fought)

    def is_eligible_to_fight(self, squad):
        return self.eligible


class MoveStub:
    """MovementController, as the Stratagem controllers ask it.

    `selected` matters: ActionPanel._draw_movement_ui() opens with
    `squad = movement_controller.selected_squad` and asks
    proactive_stratagems.buttons_for(squad) about that squad and no other. A
    stub without the attribute makes every "is this the selected squad" clause
    read None, which is how Aggressive Mobility's button could be unrenderable
    in every real game while this suite stayed green.
    """

    def __init__(self, moved=(), advanced=(), selected=None):
        self.moved_squad_ids = set(moved)
        self.advanced_squad_ids = set(advanced)
        self.selected_squad = selected


commander = tk.build(COMMANDER_IN_COLDSTAR_BATTLESUIT, HUMAN,
                     name="1 Commander in Coldstar Battlesuit 1")
kroot = tk.build(KROOT_CARNIVORES, HUMAN, name="1 Kroot Carnivores 1")
strike = tk.build(STRIKE_TEAM, HUMAN, name="1 Strike Team 1")
orks = tk.build(BOYZ, "Player 2", name="2 Boyz 1")
tk.line_up(kroot, 10, 10)
tk.line_up(orks, 10, 14)
tk.line_up(strike, 10, 30)


def ranged_weapon(squad):
    return next(w for w in squad.models[0].weapons if w.weapon_type == RANGED)


# --- 1. The panel mechanism ----------------------------------------------
print("\n1. One panel parameter for every proactive Stratagem")


class FakeStratagem:
    def __init__(self, ok, label="X (1 CP)"):
        self.ok, self._label, self.used = ok, label, []

    def can_use(self, squad):
        return self.ok

    def use(self, squad):
        self.used.append(squad)
        return True

    def panel_label(self, squad):
        return self._label


yes, no = FakeStratagem(True, "Yes (1 CP)"), FakeStratagem(False, "No (1 CP)")
registry = proactive_stratagems.ProactiveStratagems([yes, no])
c.eq("only usable Stratagems are offered",
     [label for label, _cb in registry.buttons_for(strike)], ["Yes (1 CP)"])
c.true("...and the hint helper agrees", registry.any_usable(strike))
c.eq("nothing is offered for None", registry.buttons_for(None), [])
# The callback must close over ITS OWN controller, not the loop variable - the
# classic late-binding bug that would fire the last button for every click.
second = FakeStratagem(True, "Also yes (1 CP)")
registry.add(second)
for label, callback in registry.buttons_for(strike):
    if label == "Yes (1 CP)":
        callback()
c.eq("the callback fires its own Stratagem", len(yes.used), 1)
c.eq("...and not another one's", len(second.used), 0)

panel_src = io.open("game/ui/action_panel.py", encoding="utf-8").read()
c.eq("the panel takes ONE parameter for all of them, on all three stages",
     panel_src.count("proactive_stratagems=None,"), 3)
c.true("...and renders whatever the list offers",
       "proactive_stratagems.buttons_for(squad)" in panel_src)
c.true("the \"nothing to do\" hint accounts for them",
       "and not detachment_stratagem_buttons" in panel_src)


# --- 2. Experimental Ammunition ------------------------------------------
print("\n2. Experimental Prototype Cadre - Experimental Ammunition")

EPC_ON = dict(EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS=(HUMAN,))
EPC_OFF = dict(EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS=())


def ammo_ctrl(mode=ammo.MODE_STRENGTH, phase=PHASE_SHOOTING, shoot=None):
    return ammo.ExperimentalAmmunitionController(
        strat_controller(), shooting_controller=shoot or ShootStub(),
        turn_tracker=turn_at(phase), game_log=tk.Log(), mode=mode)


with settings_as(**EPC_ON):
    c.true("offered to a BATTLESUIT CHARACTER unit in its Shooting phase",
           ammo_ctrl().can_use(commander))
    c.true("not in the Movement phase", not ammo_ctrl(phase=PHASE_MOVEMENT).can_use(commander))
    c.true("not to a unit that is not BATTLESUIT CHARACTER",
           not ammo_ctrl().can_use(strike))
    c.true("not to a unit already mid-activation",
           not ammo_ctrl(shoot=ShootStub(active=commander)).can_use(commander))
    c.true("not to a unit that has already shot",
           not ammo_ctrl(shoot=ShootStub(can=False)).can_use(commander))
with settings_as(**EPC_OFF):
    c.true("not without the detachment", not ammo_ctrl().can_use(commander))

# The two printed modes.
gun = ranged_weapon(commander)
with settings_as(**EPC_ON):
    plain = ammo_ctrl(ammo.MODE_STRENGTH)
    c.true("buying the plain mode works", plain.use(commander))
    got = ammo.adjusted_weapon(gun, commander)
    c.eq("+1 Strength", got.strength, gun.strength + 1)
    c.eq("...and AP untouched", got.ap, gun.ap)
    c.true("...and not [HAZARDOUS]", not got.hazardous)
    plain.reset_phase([commander])

    rich = ammo_ctrl(ammo.MODE_STRENGTH_AP_HAZARDOUS)
    c.true("buying the richer mode works", rich.use(commander))
    got = ammo.adjusted_weapon(gun, commander)
    c.eq("+1 Strength", got.strength, gun.strength + 1)
    c.eq("...and +1 AP (more negative)", got.ap, gun.ap - 1)
    c.true("...and [HAZARDOUS], which is the trade-off", got.hazardous)
    c.true("a second purchase is refused while it is up", not rich.can_use(commander))
    rich.reset_phase([commander])
    c.true("the grant is gone after the phase", ammo.active_mode(commander) is None)

# [HAZARDOUS] END TO END. Everything above asks adjusted_weapon() directly and
# was green while the third clause of the richer mode did NOTHING in a real
# game: ShootingController's hazard ledger read pairs[0][1].hazardous - the
# PRINTED weapon - so a GRANTED [HAZARDOUS] never incremented the count and
# _finish_squad() never rolled. Reported: "hazardous wurde nicht ausgeloest bei
# experimental ammunition", and visible in logs/game_20260905_212844.log:149-158
# (bought, +1S/+1AP applied, no Hazard Roll anywhere after it).
from game.factions import necrons as _haz_nec  # noqa: E402
D_SUNFORGE = __import__('game.factions.tau_empire', fromlist=['x']).TAU_EMPIRE.datasheets["Crisis Sunforge Battlesuits"]


def hazard_dice(mode, sheet=COMMANDER_IN_COLDSTAR_BATTLESUIT):
    """Every hazard die thrown by one full activation, and how many ranged
    weapons the unit actually has - rule 24.15 is one roll per WEAPON."""
    scene = tk.shooting_scene(sheet,
                              _haz_nec.NECRONS.datasheets["Necron Warriors"], gap=8.0)
    sh, dice, shooter = scene["shooting"], scene["dice"], scene["attacker"]
    shooter.experimental_ammunition_mode = mode
    weapons = sum(1 for m in shooter.models for w in m.weapons
                  if w.weapon_type == RANGED)
    tk.script(default=4)
    sh.start_shooting(shooter)
    if sh.state == "choosing_shooting_type":
        sh.choose_shooting_type(sh.available_types[0])
    sh.choose_target_squad(scene["target"])
    if sh.state == "choosing_weapon":
        sh.choose_weapon(sh.remaining_weapon_types[0])
    for _ in range(400):
        if dice.is_pending:
            dice.acknowledge()
            sh.on_dice_acknowledged()
        elif sh.pending_damage_choice:
            sh.choose_damage_model(sh.pending_damage_choice[0])
        else:
            break
    thrown = [values for label, values in dice.rolled if "Hazard" in label]
    return weapons, sum(len(v) for v in thrown), len(thrown)


c.eq("without the grant there is no hazard roll", hazard_dice(None)[1], 0)
c.eq("...nor with the plain +1 S mode", hazard_dice(ammo.MODE_STRENGTH)[1], 0)
_w1, _d1, _n1 = hazard_dice(ammo.MODE_STRENGTH_AP_HAZARDOUS)
c.eq("the richer mode really throws them - the whole trade-off", _n1, 1)

# ONE ROLL PER WEAPON, not per attack GROUP. Reported after the fix above:
# "Hazardous bei den sunforge viel zu wenig ... fuer jede waffe, die abgefeuert
# wurde muss gewuerfelt werden" - and rule 24.15 says exactly that ("for each
# [HAZARDOUS] weapon that was used to make one or more of those attacks").
# A three-model Sunforge team carries two Fusion Blasters each; grouped by
# rule 04.03 that is ONE attack group and used to be ONE die.
_sun_w, _sun_d, _sun_n = hazard_dice(ammo.MODE_STRENGTH_AP_HAZARDOUS,
                                     sheet=D_SUNFORGE)
c.true("the premise: the Sunforge team carries more weapons than attack groups",
       _sun_w > 1)
c.eq("one hazard die per weapon that fired", _sun_d, _sun_w)
c.eq("...thrown together as ONE roll, not one prompt per weapon", _sun_n, 1)
c.eq("a one-weapon model still owes exactly one", _d1, _w1)
# The ledger has to read the ADJUSTED weapon, or the next runtime grant of any
# keyword the hazard step cares about fails the same silent way.
_shoot_haz = io.open("game/shooting.py", encoding="utf-8").read()
c.true("the hazard ledger asks the adjusted weapon, not the printed one",
       "self._adjusted_weapon(pairs, target_squad).hazardous" in _shoot_haz)
_fight_haz = io.open("game/fight.py", encoding="utf-8").read()
c.true("...and the melee half has the same shape, for the next grant",
       "self._adjusted_weapon(pairs, _haz_target).hazardous" in _fight_haz)

blade = next((w for w in commander.models[0].weapons if w.weapon_type == MELEE), None)
with settings_as(**EPC_ON):
    ammo_ctrl().use(commander)
    c.true("a melee weapon is untouched - \"ranged attacks\"",
           blade is None or ammo.adjusted_weapon(blade, commander) is blade)
    commander.experimental_ammunition_mode = None
c.eq("the shared WeaponProfile was never mutated", gun.strength, ranged_weapon(commander).strength)

# Both modes are ONE Stratagem for rule 15.01 - buying either spends the
# once-per-phase allowance, which only holds because they share a name.
c.eq("both modes carry the same Stratagem name",
     ammo_ctrl(ammo.MODE_STRENGTH)._stratagem.name,
     ammo_ctrl(ammo.MODE_STRENGTH_AP_HAZARDOUS)._stratagem.name)
shared = strat_controller()
a = ammo.ExperimentalAmmunitionController(shared, shooting_controller=ShootStub(),
                                          turn_tracker=turn_at(PHASE_SHOOTING),
                                          game_log=tk.Log(), mode=ammo.MODE_STRENGTH)
b = ammo.ExperimentalAmmunitionController(shared, shooting_controller=ShootStub(),
                                          turn_tracker=turn_at(PHASE_SHOOTING),
                                          game_log=tk.Log(),
                                          mode=ammo.MODE_STRENGTH_AP_HAZARDOUS)
with settings_as(**EPC_ON):
    c.true("buying one mode...", a.use(commander))
    commander.experimental_ammunition_mode = None   # only 15.01 should stop the second
    c.true("...blocks the other this phase (15.01, one Stratagem)", not b.can_use(commander))
commander.experimental_ammunition_mode = None


# --- 3. Auxiliary Cadre's three ------------------------------------------
print("\n3. Auxiliary Cadre - three Stratagems")

AUX_ON = dict(AUXILIARY_CADRE_PLAYERS=(HUMAN,))
AUX_OFF = dict(AUXILIARY_CADRE_PLAYERS=())

# -- Experimental Modifications (+1 AP, BOTH phases) ----------------------
def mods_ctrl(phase=PHASE_SHOOTING, shoot=None, fight=None, owner=HUMAN):
    return mods.ExperimentalModificationsController(
        strat_controller(), shooting_controller=shoot or ShootStub(),
        fight_controller=fight or FightStub(), turn_tracker=turn_at(phase, owner),
        game_log=tk.Log())


with settings_as(**AUX_ON):
    c.true("offered to Kroot in the Shooting phase", mods_ctrl().can_use(kroot))
    c.true("...and in the Fight phase", mods_ctrl(phase=PHASE_FIGHT).can_use(kroot))
    # "YOUR Shooting phase" but "THE Fight phase" - the asymmetry is printed.
    c.true("not in the opponent's Shooting phase",
           not mods_ctrl(owner="Player 2").can_use(kroot))
    c.true("but YES in the Fight phase of the opponent's turn - \"the\", not \"your\"",
           mods_ctrl(phase=PHASE_FIGHT, owner="Player 2").can_use(kroot))
    c.true("not to a non-Kroot unit", not mods_ctrl().can_use(strike))
    c.true("not to a unit that already fought",
           not mods_ctrl(phase=PHASE_FIGHT, fight=FightStub(fought=[kroot])).can_use(kroot))
    c.true("not in the Charge phase", not mods_ctrl(phase=PHASE_CHARGE).can_use(kroot))
with settings_as(**AUX_OFF):
    c.true("not without the detachment", not mods_ctrl().can_use(kroot))

kroot_gun = ranged_weapon(kroot)
kroot_blade = next(w for w in kroot.models[0].weapons if w.weapon_type == MELEE)
with settings_as(**AUX_ON):
    ctrl = mods_ctrl()
    c.true("buying it works", ctrl.use(kroot))
    c.eq("ranged attacks get +1 AP", mods.adjusted_weapon(kroot_gun, kroot).ap, kroot_gun.ap - 1)
    c.eq("melee attacks too - \"attacks\", not \"ranged attacks\"",
         mods.adjusted_weapon(kroot_blade, kroot).ap, kroot_blade.ap - 1)
    ctrl.reset_phase([kroot])
    c.true("gone after the phase", not mods.is_active(kroot))

# -- Alien Expertise (Advance and still charge) ---------------------------
def alien_ctrl(phase=PHASE_MOVEMENT, move=None, owner=HUMAN):
    return alien.AlienExpertiseController(
        strat_controller(), movement_controller=move or MoveStub(),
        turn_tracker=turn_at(phase, owner), game_log=tk.Log())


with settings_as(**AUX_ON):
    c.true("offered to Kroot in the Movement phase", alien_ctrl().can_use(kroot))
    c.true("not in the Shooting phase", not alien_ctrl(phase=PHASE_SHOOTING).can_use(kroot))
    c.true("not to a non-Kroot unit", not alien_ctrl().can_use(strike))
    # "when it is SELECTED TO MAKE an advance move" - before the move.
    c.true("not once the unit has already moved",
           not alien_ctrl(move=MoveStub(moved=[kroot])).can_use(kroot))
    c.true("not once it has already Advanced",
           not alien_ctrl(move=MoveStub(advanced=[kroot])).can_use(kroot))
    ctrl = alien_ctrl()
    c.true("buying it works", ctrl.use(kroot))
    c.true("the flag charge.py reads is up", alien.is_active(kroot))
    ctrl.expire_for_turn([kroot])
    c.true("gone at the end of the TURN", not alien.is_active(kroot))
with settings_as(**AUX_OFF):
    c.true("not without the detachment", not alien_ctrl().can_use(kroot))

# It is the FOURTH source of one exception, and joins the shared fold. That
# fold used to be an inline disjunction inside can_declare_charge(); it now
# lives in game/move_exceptions.py, because three Aeldari Stratagems became the
# fifth, sixth and seventh sources of the same three bans. So the assurance
# moved with the code: what matters is that charge.py asks the shared question
# and that this ability is one of its sources.
charge_src = inspect.getsource(__import__("game.charge", fromlist=["x"]).ChargeController.can_declare_charge)
c.true("charge.py asks the shared advance-then-charge question",
       "move_exceptions.may_charge_after_advancing(" in charge_src)
_exc_src = io.open("game/move_exceptions.py", encoding="utf-8").read()
c.true("...and Alien Expertise is one of its sources",
       "aux_alien_expertise.is_active(squad)" in _exc_src)
c.true("...alongside the three that were already there",
       "squad_has_full_throttle" in _exc_src and "squad_waaagh_active" in _exc_src
       and "loping_pounce.is_active" in _exc_src)

# -- Guided Fire ([LETHAL HITS] near friendly Kroot) ----------------------
def guided_ctrl(phase=PHASE_SHOOTING, shoot=None):
    return guided.GuidedFireController(
        strat_controller(), shooting_controller=shoot or ShootStub(),
        turn_tracker=turn_at(phase), game_log=tk.Log())


with settings_as(**AUX_ON):
    c.true("offered to a non-Kroot T'au unit", guided_ctrl().can_use(strike))
    # "EXCLUDING KROOT/VESPID STINGWINGS units" - the Kroot are the spotters.
    c.true("NOT offered to the Kroot themselves", not guided_ctrl().can_use(kroot))
    c.true("not in the Movement phase", not guided_ctrl(phase=PHASE_MOVEMENT).can_use(strike))
with settings_as(**AUX_OFF):
    c.true("not without the detachment", not guided_ctrl().can_use(strike))

strike_gun = ranged_weapon(strike)
with settings_as(**AUX_ON):
    ctrl = guided_ctrl()
    c.true("buying it works", ctrl.use(strike))
    # The 9" is measured at RESOLUTION, against the TARGET - so the same unit
    # gets it against one target and not another.
    tk.line_up(kroot, 10, 10)
    tk.line_up(orks, 10, 14)       # 4" from the Kroot: inside 9"
    c.true("a target near friendly Kroot gets [LETHAL HITS]",
           guided.adjusted_weapon(strike_gun, strike, orks, [kroot, orks, strike]).lethal_hits)
    tk.line_up(orks, 10, 40)       # 30" away: outside
    c.true("...and one far from them does not",
           not guided.adjusted_weapon(strike_gun, strike, orks, [kroot, orks, strike]).lethal_hits)
    tk.line_up(orks, 10, 14)
    c.true("with no friendly Kroot at all, nothing",
           not guided.adjusted_weapon(strike_gun, strike, orks, [orks, strike]).lethal_hits)
    ctrl.reset_phase([strike])
    c.true("gone after the phase", not guided.is_active(strike))
c.true("the shared WeaponProfile was never mutated", not strike_gun.lethal_hits)


# --- 4. Wiring ------------------------------------------------------------
print("\n4. Wiring")

shooting_src = io.open("game/shooting.py", encoding="utf-8").read()
fight_src = io.open("game/fight.py", encoding="utf-8").read()
main_src = io.open("main.py", encoding="utf-8").read()

c.true("Experimental Ammunition is in the shooting weapon chain",
       "epc_experimental_ammunition.adjusted_weapon(" in shooting_src)
c.true("Experimental Modifications is in the shooting chain",
       "aux_experimental_modifications.adjusted_weapon(" in shooting_src)
c.true("...and in the FIGHT chain, because it says \"attacks\"",
       "aux_experimental_modifications.adjusted_weapon(" in fight_src)
c.true("Guided Fire is in the shooting chain, with its target and the board",
       "aux_guided_fire.adjusted_weapon(" in shooting_src)
# Experimental Ammunition and Modifications are S/AP only, so their place is
# free - but Guided Fire grants a keyword and must precede the hit step. Being
# in this chain at all is what guarantees that.
c.true("all three sit in _adjusted_weapon(), not at the wound step",
       "aux_guided_fire.adjusted_weapon("
       in inspect.getsource(__import__("game.shooting", fromlist=["x"]).ShootingController._adjusted_weapon))

for needle, label in [
    ("proactive_stratagems = ProactiveStratagems()", "the registry is built"),
    ("ExperimentalAmmunitionController(", "Experimental Ammunition is built"),
    ("ExperimentalModificationsController(", "Experimental Modifications is built"),
    ("AlienExpertiseController(", "Alien Expertise is built"),
    ("GuidedFireController(", "Guided Fire is built"),
    ("proactive_stratagems=proactive_stratagems,", "the panel is given the registry"),
    ("alien_expertise_controller.expire_for_turn(", "Alien Expertise expires with the TURN"),
    ("guided_fire_controller.reset_phase(", "Guided Fire expires with the phase"),
]:
    c.true(label, needle in main_src)

# Construction ORDER: Experimental Modifications takes fight_controller, so it
# must be built after it. This was a real UnboundLocalError, found by a smoke
# run rather than by any suite - error class 23.
c.true("the registry is built AFTER fight_controller",
       main_src.index("proactive_stratagems = ProactiveStratagems()")
       > main_src.index("    fight_controller = FightController("))

# No AI path, per the standing T'au instruction.
driver = io.open("ai/agent_driver.py", encoding="utf-8").read().lower()
for word in ("experimental_ammunition", "experimental_modifications",
             "alien_expertise", "guided_fire"):
    c.true("nothing in ai/ mentions %s - by design" % word, word not in driver)


# --- 5. A/B probes --------------------------------------------------------
print("\n5. A/B probes")

# The Kroot exclusion is what makes Guided Fire a support Stratagem rather than
# a self-buff; without it the spotters could buy it for themselves.
_real = guided.auxiliary_cadre.is_harnessed_unit
try:
    guided.auxiliary_cadre.is_harnessed_unit = lambda squad: False
    with settings_as(**AUX_ON):
        c.true("A/B: without the exclusion the Kroot could buy Guided Fire",
               guided_ctrl().can_use(kroot))
finally:
    guided.auxiliary_cadre.is_harnessed_unit = _real
with settings_as(**AUX_ON):
    c.true("A/B restored", not guided_ctrl().can_use(kroot))

# The richer Experimental Ammunition mode is only a choice because of the
# drawback; without [HAZARDOUS] it would strictly dominate the plain one.
with settings_as(**EPC_ON):
    rich = ammo_ctrl(ammo.MODE_STRENGTH_AP_HAZARDOUS)
    rich.use(commander)
    got = ammo.adjusted_weapon(gun, commander)
    c.true("A/B: the richer mode really carries its drawback", got.hazardous)
    commander.experimental_ammunition_mode = None

shadowsun = tk.build(__import__('game.factions.tau_empire', fromlist=['x']).COMMANDER_SHADOWSUN, HUMAN, name='1 Commander Shadowsun 1')
stealth = tk.build(__import__('game.factions.tau_empire', fromlist=['x']).STEALTH_BATTLESUITS, HUMAN, name='1 Stealth Battlesuits 1')


# --- 6. Kauyon's six ------------------------------------------------------
print("\n6. Kauyon - six Stratagems")

from game import (charge as charge_module, kauyon,  # noqa: E402
                  kauyon_combat_embarkation as embark_strat,
                  kauyon_coordinate_to_engage as coordinate,
                  kauyon_photon_grenades as photon,
                  kauyon_point_blank_ambush as ambush,
                  kauyon_tempting_trap as trap,
                  kauyon_wall_of_mirrors as mirrors)
from game.factions.tau_empire import (GHOSTKEEL_BATTLESUIT,  # noqa: E402
                                      PATHFINDER_TEAM, STEALTH_BATTLESUITS)

KAUYON_ON = dict(KAUYON_PLAYERS=(HUMAN,))
KAUYON_OFF = dict(KAUYON_PLAYERS=())


def kauyon_turn(phase=PHASE_SHOOTING, battle_round=3, owner=HUMAN):
    tracker = turn_at(phase, owner)
    tracker.battle_round = battle_round
    return tracker


# -- Point-Blank Ambush (+1 AP within 9") ---------------------------------
def ambush_ctrl(battle_round=3, shoot=None):
    return ambush.PointBlankAmbushController(
        strat_controller(), shooting_controller=shoot or ShootStub(),
        turn_tracker=kauyon_turn(battle_round=battle_round), game_log=tk.Log())


with settings_as(**KAUYON_ON):
    c.true("offered from the third battle round", ambush_ctrl(battle_round=3).can_use(strike))
    # "You cannot use this Stratagem during the first or second battle rounds."
    c.true("not in round 1", not ambush_ctrl(battle_round=1).can_use(strike))
    c.true("not in round 2", not ambush_ctrl(battle_round=2).can_use(strike))
    c.true("still offered in round 5 - unlike Patient Hunter it has no upper bound",
           ambush_ctrl(battle_round=5).can_use(strike))
    c.true("and in round 6", ambush_ctrl(battle_round=6).can_use(strike))
with settings_as(**KAUYON_OFF):
    c.true("not without the detachment", not ambush_ctrl().can_use(strike))

with settings_as(**KAUYON_ON):
    ctrl = ambush_ctrl()
    c.true("buying it works", ctrl.use(strike))
    shooter = strike.models[0]
    tk.line_up(strike, 10, 10)
    tk.line_up(orks, 10, 14)      # ~4": inside 9"
    near = ambush.adjusted_weapon(strike_gun, strike, [(shooter, strike_gun)], orks)
    c.eq("+1 AP against a target within 9\"", near.ap, strike_gun.ap - 1)
    tk.line_up(orks, 10, 40)      # 30": outside
    far = ambush.adjusted_weapon(strike_gun, strike, [(shooter, strike_gun)], orks)
    c.eq("...and nothing against a far one - the 9\" is per TARGET",
         far.ap, strike_gun.ap)
    ctrl.reset_phase([strike])
    c.true("gone after the phase", not ambush.is_active(strike))
tk.line_up(orks, 10, 14)


# -- Coordinate to Engage (+1 BS vs YOUR Spotted unit) --------------------
class GreaterGoodStub:
    def __init__(self, observer=None, spotted=None):
        self.spotted_by = {spotted: observer} if spotted is not None else {}
        self._observer = observer

    def is_observer(self, squad):
        return squad is self._observer

    def is_guided_attack(self, a, b):
        return False

    def marked_by_markerlight(self, squad):
        return False


pathfinders2 = tk.build(PATHFINDER_TEAM, HUMAN, name="1 Pathfinder Team 2")
gg = GreaterGoodStub(observer=pathfinders2, spotted=orks)
other_enemy = tk.build(BOYZ, "Player 2", name="2 Boyz other")


def coord_ctrl(greater_good=gg):
    return coordinate.CoordinateToEngageController(
        strat_controller(), shooting_controller=ShootStub(), greater_good=greater_good,
        turn_tracker=kauyon_turn(), game_log=tk.Log())


with settings_as(**KAUYON_ON):
    c.true("offered to a unit that just became an Observer", coord_ctrl().can_use(pathfinders2))
    c.true("not to a unit that is not an Observer", not coord_ctrl().can_use(strike))
    c.true("not to an Observer that marked nothing",
           not coord_ctrl(GreaterGoodStub(observer=pathfinders2)).can_use(pathfinders2))
    ctrl = coord_ctrl()
    c.true("buying it works", ctrl.use(pathfinders2))
    # "THEIR Spotted unit" - not any Spotted unit.
    c.true("it applies against the unit THIS observer marked",
           coordinate.applies(gg, pathfinders2, orks))
    c.true("...and not against another enemy",
           not coordinate.applies(gg, pathfinders2, other_enemy))
    # The [IGNORES COVER] half is conditional on MARKERLIGHT, separately.
    c.true("Pathfinders have MARKERLIGHT, so they also ignore cover",
           coordinate.ignores_cover(gg, pathfinders2, orks))
    ctrl.reset_phase([pathfinders2])
    c.true("gone after the phase", not coordinate.is_active(pathfinders2))

# A unit WITHOUT MARKERLIGHT gets the Ballistic Skill half alone.
ghost = tk.build(GHOSTKEEL_BATTLESUIT, HUMAN, name="1 Ghostkeel Battlesuit 2")
gg2 = GreaterGoodStub(observer=ghost, spotted=orks)
c.true("a Ghostkeel has no MARKERLIGHT",
       not __import__("game.attached_units", fromlist=["x"]).unit_has_datasheet_keyword(
           ghost, "MARKERLIGHT"))
ghost.coordinate_to_engage_active = True
c.true("...so it gets the BS half", coordinate.applies(gg2, ghost, orks))
c.true("...but NOT the cover half", not coordinate.ignores_cover(gg2, ghost, orks))
ghost.coordinate_to_engage_active = False


# -- A Tempting Trap (+1 Wound near the Trap objective) -------------------
class Zone:
    def __init__(self, owner, y_lo, y_hi):
        self.owner, self.y_lo, self.y_hi = owner, y_lo, y_hi

    def contains_point(self, x_in, y_in):
        return self.y_lo <= y_in <= self.y_hi


class Area:
    def __init__(self, x, y):
        self.center_x_in, self.center_y_in = x, y

    def distance_to_model(self, model):
        return ((model.x_in - self.center_x_in) ** 2
                + (model.y_in - self.center_y_in) ** 2) ** 0.5


class Objective:
    def __init__(self, name, x, y):
        self.name = name
        self.terrain_area = Area(x, y)


near_obj = Objective("Objective Near", 10.0, 14.0)
enemy_zone_obj = Objective("Enemy Home", 10.0, 90.0)
zones = {HUMAN: Zone(HUMAN, 0, 20), "Player 2": Zone("Player 2", 80, 100)}


def trap_ctrl(objectives=(near_obj, enemy_zone_obj), dm=None):
    return trap.TemptingTrapController(
        strat_controller(), shooting_controller=ShootStub(), turn_tracker=kauyon_turn(),
        objectives=objectives, deployment_zones=zones,
        decision_manager=dm, game_log=tk.Log())


ctrl = trap_ctrl()
c.eq("an objective in the OPPONENT'S zone is not a legal Trap",
     [o.name for o in ctrl.candidate_objectives(HUMAN)], ["Objective Near"])
# Your OWN zone is legal - the clause names the opponent's zone only, which is
# wider than the "No Man's Land only" some mission cards use.
own_zone_obj = Objective("My Home", 10.0, 5.0)
ctrl2 = trap_ctrl(objectives=(own_zone_obj,))
c.eq("...but one in your own zone IS", [o.name for o in ctrl2.candidate_objectives(HUMAN)],
     ["My Home"])

with settings_as(**KAUYON_ON):
    ctrl = trap_ctrl()
    c.true("offered in round 3", ctrl.can_use(strike))
    c.true("not in round 2", not trap_ctrl().can_use(strike) if False else
           not trap.TemptingTrapController(
               strat_controller(), shooting_controller=ShootStub(),
               turn_tracker=kauyon_turn(battle_round=2), objectives=(near_obj,),
               deployment_zones=zones, game_log=tk.Log()).can_use(strike))
    # Never offer what cannot be completed: with no legal objective the first
    # use could not choose a Trap at all.
    c.true("not offered when no objective is legal",
           not trap_ctrl(objectives=(enemy_zone_obj,)).can_use(strike))

    ctrl = trap_ctrl(objectives=(near_obj,))
    c.true("buying it works", ctrl.use(strike))
    c.eq("the single legal objective is taken without asking",
         ctrl.trap_for(HUMAN).name, "Objective Near")
    tk.line_up(orks, 10, 14)     # on the Trap objective
    c.true("+1 Wound against an enemy in range of the Trap",
           ctrl.wound_bonus_applies(strike, orks))
    tk.line_up(orks, 10, 60)     # far away
    c.true("...and nothing against one far from it",
           not ctrl.wound_bonus_applies(strike, orks))
    # TWO lifetimes: the grant is phase-scoped, the Trap lasts the battle.
    ctrl.reset_phase([strike])
    c.true("the grant is gone after the phase", not trap.is_active(strike))
    c.eq("...but the Trap objective survives it", ctrl.trap_for(HUMAN).name, "Objective Near")
tk.line_up(orks, 10, 14)


# -- Wall of Mirrors (withdraw to Strategic Reserves) ---------------------
c.true("a Stealth unit is eligible", mirrors.is_eligible_unit(stealth))
c.true("a Ghostkeel is eligible", mirrors.is_eligible_unit(ghost))
c.true("Commander Shadowsun is eligible by NAME - she shares no keyword with them",
       mirrors.is_eligible_unit(shadowsun))
c.true("a Strike Team is not", not mirrors.is_eligible_unit(strike))

# THE WHOLE POINT of this block: everything above was already green while the
# Stratagem was, in a real game, offered to the WRONG PLAYER and then did
# NOTHING when accepted. Reported: "Frage nach Wall of Mirrors kam am Anfang
# der Gegner Runde ... funktioniert auch nicht". Only driving the real phase
# BOUNDARY - advance_phase() first, offer second, exactly as
# advance_turn_phase() orders them - can see either half.
from game.game_state import GameState as _GS  # noqa: E402
from game.factions import necrons as _nec  # noqa: E402


def mirrors_boundary(kauyon_owner=HUMAN, use_mover_before=True):
    """One end-of-Fight-phase boundary, in main.py's order."""
    other = "Player 2" if kauyon_owner == HUMAN else HUMAN
    state = _GS()
    hider = tk.build(STEALTH_BATTLESUITS, kauyon_owner, name="Stealth W")
    foe = tk.build(_nec.NECRONS.datasheets["Necron Warriors"], other, name="Warriors W")
    tk.line_up(hider, 10.0, 10.0)
    tk.line_up(foe, 10.0, 40.0)          # far apart: the Engagement Range clause is clear
    for squad in (hider, foe):
        for model in squad.models:
            state.add_token(model)
    tracker = TurnTracker(first_player=other)
    while tracker.phase != PHASE_FIGHT:
        tracker.advance_phase()
    dec, log = DecisionManager(), tk.Log()
    ctrl = mirrors.WallOfMirrorsController(
        strat_controller(), game_state=state, turn_tracker=tracker,
        all_tokens=state.tokens, decision_manager=dec, game_log=log,
        auto_players=())
    mover_before = tracker.turn_owner        # main.py:3166, BEFORE the advance
    tracker.advance_phase()                  # main.py:3187
    ctrl.reset_phase()                       # main.py's per-phase reset block
    ctrl.offer_at_end_of_fight_phase(mover_before if use_mover_before
                                     else tracker.turn_owner)
    return dict(state=state, hider=hider, dec=dec, log=log, ctrl=ctrl,
                tracker=tracker, mover_before=mover_before)


with settings_as(**KAUYON_ON):
    # Kauyon is the HUMAN's, and it is the OPPONENT whose Fight phase ends -
    # so "end of your opponent's Fight phase" must offer it to the HUMAN.
    b = mirrors_boundary()
    c.true("the offer is made at the boundary at all", b["dec"].is_pending)
    c.eq("...to the side whose OPPONENT just fought", b["dec"].player, HUMAN)
    c.true("...naming the eligible unit",
           any(o["label"] == "Stealth W" for o in b["dec"].options))
    # The clock has ALREADY moved on by now - that is the whole trap.
    c.true("...even though the phase already reads the next one",
           b["tracker"].phase != PHASE_FIGHT)

    _before = len(b["state"].tokens)
    _idx = next(i for i, o in enumerate(b["dec"].options) if o["squad"] is not None)
    b["dec"].choose(_idx)
    c.true("accepting really withdraws the unit",
           b["hider"] in b["state"].reserves)
    c.eq("...and takes every one of its models off the board",
         [t for t in b["state"].tokens if getattr(t, "squad", None) is b["hider"]], [])
    c.true("...leaving the enemy's models where they were",
           len(b["state"].tokens) < _before and len(b["state"].tokens) > 0)
    c.true("...and says so in the log",
           any("Wall of Mirrors" in line for line in b["log"].lines))

    # The pre-fix argument named the side whose own Fight phase just ended.
    b2 = mirrors_boundary(use_mover_before=False)
    c.true("passing the post-advance turn_owner asks nobody with the detachment",
           not b2["dec"].is_pending)

    # The window is one boundary wide.
    b3 = mirrors_boundary()
    b3["ctrl"].reset_phase()
    c.true("a later phase cannot answer a stale window",
           not b3["ctrl"].can_use(b3["hider"]))


# -- Photon Grenades (-2 Charge, Battle-shock) ----------------------------
c.eq("the penalty is the printed 2", photon.PHOTON_GRENADES_CHARGE_PENALTY, 2)
c.eq("an unaffected unit has no penalty", photon.charge_penalty_for(orks), 0)
orks.photon_grenades_penalty = True
c.eq("a dazzled unit subtracts 2 from its Charge roll", photon.charge_penalty_for(orks), 2)
orks.photon_grenades_penalty = False
# "Charge rolls made FOR that enemy unit" - the CHARGER's side, so it belongs
# beside Neocapacitor Shields rather than with the Grav-inhibitor Drone's -2.
capped_src = inspect.getsource(charge_module.ChargeController._capped_roll)
c.true("the -2 is applied to the CHARGING unit's roll",
       "kauyon_photon_grenades.charge_penalty_for(self.active_squad)" in capped_src)
c.true("...beside Neocapacitor Shields, the other charger-side penalty",
       "neocapacitor_shields.charge_penalty_for(self.active_squad)" in capped_src)


# NOT while the unit is inside a TRANSPORT. The reaction chain hands every
# reactor the SAME target list, captured once when the charge was declared -
# and Combat Embarkation sits on that very chain, so the unit named as a target
# can be in a vehicle by the time this one is asked. Reported: "Photon granades
# Stratagem soll nicht gehen, wenn embarked".
_ph_state = _GS()
_ph_def = tk.build(STRIKE_TEAM, HUMAN, name="Photon Def")
_ph_foe = tk.build(BOYZ, "Player 2", name="Photon Foe")
tk.line_up(_ph_def, 20.0, 20.0)
tk.line_up(_ph_foe, 20.0, 40.0)            # far apart: the Engagement clause is clear
for _s in (_ph_def, _ph_foe):
    for _m in _s.models:
        _ph_state.add_token(_m)
_ph = photon.PhotonGrenadesController(
    strat_controller(), turn_tracker=kauyon_turn(PHASE_CHARGE),
    all_tokens=_ph_state.tokens, game_log=tk.Log())
with settings_as(**KAUYON_ON):
    c.eq("a GRENADES unit on the board is offered it",
         [s.name for s in _ph.eligible_defenders(_ph_foe, [_ph_def])], ["Photon Def"])
    # Exactly what TransportController.embark() does to the board
    # (game/transport.py): the models leave the token list and their
    # COORDINATES are left alone - which is why is_engaged() is no substitute.
    for _m in list(_ph_def.models):
        if _m in _ph_state.tokens:
            _ph_state.tokens.remove(_m)
    _ph_def.embarked_in = object()
    c.eq("...and not once it has boarded a transport",
         [s.name for s in _ph.eligible_defenders(_ph_foe, [_ph_def])], [])
    c.true("the coordinates it left behind still read as un-engaged, so the "
           "Engagement clause could never have caught this",
           not _ph_def.is_engaged(_ph_state.tokens))
    # The two clauses are SEPARATE, and each has to be tested where the other
    # cannot cover for it - otherwise removing either one leaves this block
    # green (found by ab_charge_window_and_prompts.py).
    for _m in _ph_def.models:
        _ph_state.add_token(_m)
    c.eq("embarked_in alone is enough, even with models still listed",
         [s.name for s in _ph.eligible_defenders(_ph_foe, [_ph_def])], [])
    _ph_def.embarked_in = None
    for _m in list(_ph_def.models):
        if _m in _ph_state.tokens:
            _ph_state.tokens.remove(_m)
    c.eq("...and being off the board alone is too - a unit wiped this frame",
         [s.name for s in _ph.eligible_defenders(_ph_foe, [_ph_def])], [])
    for _m in _ph_def.models:
        _ph_state.add_token(_m)
    c.eq("back on the board and out of any vehicle, it is offered again",
         [s.name for s in _ph.eligible_defenders(_ph_foe, [_ph_def])], ["Photon Def"])


# -- Combat Embarkation ---------------------------------------------------
# It overrides WHEN you may embark (18.02's "after a move this phase"), and
# nothing else - the 3", the capacity and the transport's keyword bans all
# still come from their one definition.
embark_src = io.open("game/transport.py", encoding="utf-8").read()
c.true("can_embark grew a require_move flag rather than a second copy",
       "def can_embark(self, squad, transport_token, require_move=True" in embark_src)
c.true("...and only 18.02's move clause is behind it",
       "if require_move and squad not in self.movement_controller.moved_squad_ids:" in embark_src)
# The distance later grew a `range_in=` override of its own, for Skyborne
# Sanctuary's printed 6". What this line is really for is that there is ONE
# distance check reading ONE default, so it now pins that shape rather than the
# exact expression - the same lesson the advance-then-charge pin next door
# learned when its disjunction kept growing.
c.true("there is still exactly one distance check in can_embark",
       embark_src.count("edge_distance(m, transport_token) <= reach") == 1)
c.true("...and it defaults to the shared definition",
       "reach = EMBARK_RANGE_IN if range_in is None else range_in" in embark_src)
c.eq("and it is the printed 3 inches",
     __import__("game.transport", fromlist=["x"]).EMBARK_RANGE_IN, 3.0)
ce_src = io.open("game/kauyon_combat_embarkation.py", encoding="utf-8").read()

# "IF IT DOES, YOUR OPPONENT CAN SELECT NEW TARGETS FOR THAT CHARGE."
# This half used to be a NAMED LIMITATION, and the limitation was worse than it
# read: _start_declared_move() re-checks state, targets-non-empty and
# max_distance but never the TARGETS, and embark() takes a unit's models off
# the token list while leaving their coordinates alone - so the charge was
# resolved against a unit sitting inside a vehicle and engaged it at 0.0".
# Seen in a real game (logs/game_20260905_203642.log:191-196). Reported: "nach
# combat embarkation stratagem: auswahl bei attacker muss zurueckspringen auf
# choose charge targets".
_charge_src_early = io.open("game/charge.py", encoding="utf-8").read()
c.true("reopen_target_selection() exists on the charge controller",
       "def reopen_target_selection(self, dropped_squad=None):" in _charge_src_early)
c.true("...and Combat Embarkation calls it after a successful embark",
       "self.charge_controller.reopen_target_selection(squad)" in ce_src)


class _EmbarkTransport:
    """The two things Combat Embarkation asks of TransportController, doing
    exactly what the real embark() does to the board (game/transport.py)."""

    def __init__(self, state):
        self.state = state

    def can_embark(self, squad, token, require_move=True, range_in=None):
        return True

    def embark(self, squad, token, require_move=True, range_in=None):
        for model in list(squad.models):
            if model in self.state.tokens:
                self.state.tokens.remove(model)
        squad.embarked_in = token
        self.state.embarked_squads.append(squad)


class _EmbarkMove:
    move_mode = None
    selected_squad = None
    advanced_squad_ids = set()
    moved_squad_ids = set()
    fell_back_squad_ids = set()

    def __init__(self):
        self.started = None

    def start_charge_move(self, distance, targets):
        self.started = (distance, [t.name for t in targets])


def embark_scene(wired=True, second_target=False):
    """One declared charge, answered with Combat Embarkation."""
    from game.dice import DiceManager as _DM
    from game.factions import necrons as _nec
    from game.factions import tau_empire as _tau
    state = _GS()
    riders = tk.build(_tau.TAU_EMPIRE.datasheets["Breacher Team"], HUMAN, name="Breachers E")
    ride = tk.build(_tau.TAU_EMPIRE.datasheets["Devilfish"], HUMAN, name="Devilfish E")
    foe = tk.build(_nec.NECRONS.datasheets["Skorpekh Destroyers"], "Player 2",
                   name="Skorpekh E")
    tk.line_up(riders, 20.0, 20.0)
    tk.line_up(ride, 21.0, 22.0)
    tk.line_up(foe, 20.0, 28.0)
    for squad in (riders, ride, foe):
        for model in squad.models:
            state.add_token(model)
    tracker = turn_at(PHASE_CHARGE, "Player 2")
    dice, dec, log = _DM(), DecisionManager(), tk.Log()
    move = _EmbarkMove()
    cc = charge_module.ChargeController(
        game_log=log, dice_manager=dice, turn_tracker=tracker,
        all_tokens=state.tokens, movement_controller=move)
    ctrl = embark_strat.CombatEmbarkationController(
        strat_controller(), transport_controller=_EmbarkTransport(state),
        turn_tracker=tracker, all_tokens=state.tokens, decision_manager=dec,
        game_log=log, auto_players=(),
        charge_controller=cc if wired else None)
    cc.charge_declaration_reactions.append(ctrl.maybe_offer)
    tk.script(default=6)
    cc.declare_charge(foe)
    dice.acknowledge()
    cc.max_distance = 10.0
    move.selected_squad = foe
    cc.toggle_charge_target(riders)
    if second_target:
        cc.toggle_charge_target(ride)
    cc.begin_charge_move()
    return dict(cc=cc, dec=dec, move=move, riders=riders, foe=foe, tracker=tracker)


with settings_as(**KAUYON_ON):
    _e = embark_scene()
    c.true("the charge really was declared against the Breachers",
           [s.name for s in _e["cc"].charge_targets] == ["Breachers E"])
    c.true("Combat Embarkation is offered on that declaration", _e["dec"].is_pending)
    _ei = next(i for i, o in enumerate(_e["dec"].options) if o["squad"] is not None)
    _e["dec"].choose(_ei)
    c.true("the unit really boards the transport",
           getattr(_e["riders"], "embarked_in", None) is not None)
    c.eq("the embarked unit is dropped from the declared targets",
         [s.name for s in _e["cc"].charge_targets], [])
    c.eq("...and the charge does NOT move against it",
         _e["move"].started, None)
    c.eq("...while the declaration stays open for new targets",
         _e["cc"].state, charge_module.DECLARING_TARGETS)
    c.eq("...with the roll kept - the effect re-opens targets, not the dice",
         _e["cc"].max_distance, 10.0)
    # Deliberately NOT asserting a set_active() restore here: nothing on this
    # Stratagem's path moves active_player in the first place (its sibling only
    # restores it because the Battle-shock test it starts moves it). Measured,
    # so the absence is a fact rather than an omission.
    c.eq("the charging player never lost the decision window to begin with",
         _e["tracker"].active_player, "Player 2")
    # TWO declared targets, only one of which boards. charge_targets is then
    # still non-empty, so _start_declared_move()'s own guards would happily let
    # the charge run - the re-opened window is the ONLY thing that stops it,
    # and this is the case that says so.
    _e3 = embark_scene(second_target=True)
    c.true("the premise: two targets were declared",
           len(_e3["cc"].charge_targets) == 2)
    _ei3 = next(i for i, o in enumerate(_e3["dec"].options) if o["squad"] is not None)
    _e3["dec"].choose(_ei3)
    c.eq("the one that boarded is dropped and the other stays",
         [s.name for s in _e3["cc"].charge_targets], ["Devilfish E"])
    c.eq("...and the charge still does NOT move - the opponent re-declares",
         _e3["move"].started, None)

    # THE PRE-FIX WORLD, so this block cannot pass by accident.
    _e2 = embark_scene(wired=False)
    _ei2 = next(i for i, o in enumerate(_e2["dec"].options) if o["squad"] is not None)
    _e2["dec"].choose(_ei2)
    c.true("unwired, the charge resolves into the transport - the reported bug",
           _e2["move"].started is not None
           and "Breachers E" in _e2["move"].started[1])


# -- both reactive ones share one chained hook ----------------------------
# on_charge_declared is a single slot with a return-value protocol, so two
# reactors needed chaining - "first one wins" would have swallowed the second.
charge_src = io.open("game/charge.py", encoding="utf-8").read()
c.true("the declaration reactions are a LIST", "self.charge_declaration_reactions = []" in charge_src)
c.true("...and they are CHAINED, not first-wins",
       "def _offer_declaration_reactions(self, targets):" in charge_src)
c.true("the old single slot still goes first, so its owner needed no change",
       "[self.on_charge_declared] if self.on_charge_declared is not None else []" in charge_src)


class FakeCharge:
    """Drives the chain to prove each reactor gets its own window."""

    def __init__(self, reactors):
        self.on_charge_declared = None
        self.charge_declaration_reactions = list(reactors)
        self.active_squad = strike
        # The real controller is in this state throughout the window - the
        # chain reads it to answer "is this declaration still standing".
        self.state = charge_module.DECLARING_TARGETS
        self.moved = False

    def end_the_charge(self):
        """What _finish_charge() leaves behind: no active squad, not
        declaring any more."""
        self.active_squad = None
        self.state = charge_module.IDLE

    def _start_declared_move(self):
        self.moved = True

    _offer_declaration_reactions = charge_module.ChargeController._offer_declaration_reactions


seen = []


def reactor_a(squad, targets, resume):
    seen.append("a")
    return False


def reactor_b(squad, targets, resume):
    seen.append("b")
    return False


fake = FakeCharge([reactor_a, reactor_b])
fake._offer_declaration_reactions([orks])
c.eq("every reactor that declines is still offered", seen, ["a", "b"])
c.true("...and the charge then proceeds", fake.moved)

held = {}


def reactor_takes(squad, targets, resume):
    held["resume"] = resume
    return True


seen.clear()
fake2 = FakeCharge([reactor_takes, reactor_b])
fake2._offer_declaration_reactions([orks])
c.true("a reactor that takes ownership stops the chain there", not fake2.moved)
c.eq("...and the next one has not run yet", seen, [])
held["resume"]()
c.eq("resuming continues to the NEXT reactor, not straight to the move", seen, ["b"])
c.true("...and only then does the charge proceed", fake2.moved)

# REPORTED CRASH: a reactor's own resolution can END the charge - the
# Grav-Inhibitor Field's mortal wounds can destroy the charging unit, and
# Photon Grenades hands control back through the same resume. The chain used to
# re-read self.active_squad per step, so the NEXT reactor was handed None and
# game/kauyon_combat_embarkation.py died on charging_squad.owner.
seen.clear()
held.clear()
fake3 = FakeCharge([reactor_takes, reactor_b])
fake3._offer_declaration_reactions([orks])
fake3.end_the_charge()
held["resume"]()
c.eq("a charge that ended mid-chain does not offer the remaining reactors",
     seen, [])
c.true("...and does not start a move for a charge that is over", not fake3.moved)

# The same thing again with the REAL reactor from the traceback, so the check
# reproduces the reported AttributeError rather than a stand-in for it.
real_embark = embark_strat.CombatEmbarkationController(
    strat_controller(), turn_tracker=None, all_tokens=[])
fake5 = FakeCharge([reactor_takes, real_embark.maybe_offer])
held.clear()
fake5._offer_declaration_reactions([strike])
fake5.end_the_charge()
try:
    held["resume"]()
    crashed = None
except AttributeError as exc:      # what the report showed
    crashed = str(exc)
c.eq("game/kauyon_combat_embarkation.py is never handed a charge that ended",
     crashed, None)

# The squad is captured ONCE, so a reactor can never be handed a different one
# than the window opened with.
got = []


def reactor_records(squad, targets, resume):
    got.append(squad)
    return False


fake4 = FakeCharge([reactor_takes, reactor_records])
held.clear()
fake4._offer_declaration_reactions([orks])
held["resume"]()
c.eq("every reactor sees the squad the window opened with", got, [strike])
c.true("the chain captures it once instead of re-reading the field",
       "charging = self.active_squad" in charge_src
       and "reactor(charging, list(targets)" in charge_src)

# Same crash shape one line further along: the destroyed-unit branch
# short-circuited on None and then formatted None.name.
c.true("_start_declared_move() checks None before it formats a name",
       0 <= charge_src.find("if self.active_squad is None:")
       < charge_src.find("cannot complete its charge - the unit was destroyed"))


# -- wiring ----------------------------------------------------------------
for needle, label in [
    ("PointBlankAmbushController(", "Point-Blank Ambush is built"),
    ("CoordinateToEngageController(", "Coordinate to Engage is built"),
    ("TemptingTrapController(", "A Tempting Trap is built"),
    ("WallOfMirrorsController(", "Wall of Mirrors is built"),
    ("PhotonGrenadesController(", "Photon Grenades is built"),
    ("CombatEmbarkationController(", "Combat Embarkation is built"),
    ("shooting_controller.tempting_trap = tempting_trap_controller",
     "A Tempting Trap reaches the wound step"),
    ("charge_controller.charge_declaration_reactions.extend(",
     "both charge reactions are registered"),
    ("wall_of_mirrors_controller.offer_at_end_of_fight_phase(",
     "Wall of Mirrors is offered at the end of the Fight phase"),
    ("photon_grenades_controller.on_dice_acknowledged()",
     "Photon Grenades resumes the charge on its dice acknowledgement"),
]:
    c.true(label, needle in main_src)

c.true("Photon Grenades' dice hook is AFTER battle_shock's, so the test resolves first",
       main_src.index("photon_grenades_controller.on_dice_acknowledged()")
       > main_src.index("battle_shock_controller.on_dice_acknowledged()"))

shooting_src2 = io.open("game/shooting.py", encoding="utf-8").read()
c.true("Point-Blank Ambush is in the weapon chain",
       "kauyon_point_blank_ambush.adjusted_weapon(" in shooting_src2)
c.true("Coordinate to Engage reaches the hit step",
       "kauyon_coordinate_to_engage.applies(" in shooting_src2)
c.true("...and the cover step, for its MARKERLIGHT half",
       "kauyon_coordinate_to_engage.ignores_cover(" in shooting_src2)
c.true("A Tempting Trap reaches the wound step",
       "self.tempting_trap.wound_bonus_applies(" in shooting_src2)

for word in ("point_blank_ambush", "coordinate_to_engage", "tempting_trap",
             "wall_of_mirrors", "photon_grenades", "combat_embarkation"):
    c.true("nothing in ai/ mentions %s - by design" % word, word not in driver)

pathfinders = tk.build(__import__('game.factions.tau_empire', fromlist=['x']).PATHFINDER_TEAM, HUMAN, name='1 Pathfinder Team 1')


# --- 7. Mont'ka's six -----------------------------------------------------
print("\n7. Mont'ka - six Stratagems")

from game import (coldstar, damage_reduction,  # noqa: E402
                  montka_aggressive_mobility as mobility,
                  montka_combat_debarkation as debark,
                  montka_counterfire_defence as counterfire,
                  montka_focused_fire as focused,
                  montka_pinpoint_counter_offensive as pinpoint,
                  montka_pulse_onslaught as pulse)

MONTKA_ON = dict(MONTKA_PLAYERS=(HUMAN,))
MONTKA_OFF = dict(MONTKA_PLAYERS=())


def montka_turn(phase=PHASE_SHOOTING, battle_round=2, owner=HUMAN):
    tracker = turn_at(phase, owner)
    tracker.battle_round = battle_round
    return tracker


# -- Aggressive Mobility (no Advance roll, +6" Move) ----------------------
def mobility_ctrl(move=None):
    return mobility.AggressiveMobilityController(
        strat_controller(), movement_controller=move or MoveStub(),
        turn_tracker=montka_turn(PHASE_MOVEMENT), game_log=tk.Log())


with settings_as(**MONTKA_ON):
    c.true("offered in the Movement phase", mobility_ctrl().can_use(strike))
    # THE QUESTION THE PANEL ACTUALLY ASKS. It only ever asks about
    # movement_controller.selected_squad, so a clause that refuses THAT squad
    # makes the button unrenderable - which is exactly what happened.
    # Reported: "Aggressive mobility stratagem wird nie angeboten".
    c.true("...and about the SELECTED squad, which is the only one the panel asks about",
           mobility_ctrl(MoveStub(selected=strike)).can_use(strike))
    c.true("not once the unit has moved",
           not mobility_ctrl(MoveStub(moved=[strike])).can_use(strike))
    c.true("...nor once it has advanced",
           not mobility_ctrl(MoveStub(advanced=[strike])).can_use(strike))
    ctrl = mobility_ctrl()
    c.true("buying it works", ctrl.use(strike))
    # BOTH halves, or the Stratagem is a downgrade: no roll AND +6" Move.
    c.true("the Advance roll is skipped", mobility.skips_advance_roll(strike))
    c.eq("...and the Move characteristic grows by 6",
         mobility.move_bonus_for(strike), 6.0)
    base_move = strike.models[0].profile.movement_in
    c.eq("which the one Move definition really returns",
         coldstar.effective_movement_in(strike.models[0]), base_move + 6.0)
    ctrl.reset_phase([strike])
    c.true("gone after the phase", not mobility.is_active(strike))
with settings_as(**MONTKA_OFF):
    c.true("not without the detachment", not mobility_ctrl().can_use(strike))

# It joins the EXISTING no-roll branch rather than adding a second one.
move_src = io.open("game/movement.py", encoding="utf-8").read()
c.true("it shares Whirling Death's no-roll Advance branch",
       "montka_aggressive_mobility.skips_advance_roll(self.selected_squad)" in move_src)
c.true("...which is still the same single branch",
       move_src.count("no_roll_bonus is not None") == 1)


# -- Pulse Onslaught (the shaken status) ----------------------------------
c.true("a fresh unit is not shaken", not pulse.is_shaken(orks))
orks.shaken_until_turn = 99
c.true("a shaken unit is shaken", pulse.is_shaken(orks))
c.eq("-2 Move", pulse.move_penalty_for(orks), 2)
c.eq("-2 on Advance and Charge rolls", pulse.roll_penalty_for(orks), 2)
ork_base = orks.models[0].profile.movement_in
c.eq("the Move penalty reaches the one Move definition",
     coldstar.effective_movement_in(orks.models[0]), ork_base - 2)
orks.shaken_until_turn = None
c.eq("...and is gone once it is not shaken",
     coldstar.effective_movement_in(orks.models[0]), ork_base)

# "excluding MONSTERS and VEHICLES"
c.true("infantry can be shaken", pulse.can_be_shaken(orks))
falcon = tk.build(__import__("game.factions.tau_empire", fromlist=["x"]).DEVILFISH,
                  "Player 2", name="2 Devilfish 1")
c.true("a VEHICLE cannot", not pulse.can_be_shaken(falcon))
c.true("Kroot cannot be the SHOOTER - \"excluding KROOT units\"",
       not pulse.is_eligible_shooter(kroot))
c.true("...but a Fire Warrior team can", pulse.is_eligible_shooter(strike))

# "Until the end of your opponent's NEXT turn" - two boundaries away, so it is
# stored as a deadline rather than cleared on a boundary.
onslaught = pulse.PulseOnslaughtController(
    strat_controller(), turn_tracker=montka_turn(), game_log=tk.Log())
orks.shaken_until_turn = onslaught.turn_tracker.turn_number_for("Player 2") + 1
onslaught.expire([orks])
c.true("a mark whose deadline has not passed survives", pulse.is_shaken(orks))
orks.shaken_until_turn = onslaught.turn_tracker.turn_number_for("Player 2") - 1
onslaught.expire([orks])
c.true("...and one whose deadline has passed is cleared", not pulse.is_shaken(orks))

charge_src2 = io.open("game/charge.py", encoding="utf-8").read()
c.true("the -2 Charge reaches the charge roll",
       "montka_pulse_onslaught.roll_penalty_for(self.active_squad)" in charge_src2)
c.true("the -2 Advance reaches advance_total, where the re-roll is reconciled",
       "montka_pulse_onslaught.roll_penalty_for(squad)" in move_src)


# -- Counterfire Defence Systems (-1 Damage) ------------------------------
c.eq("an unaffected unit loses no Damage", counterfire.damage_reduction_for(strike), 0)
strike.counterfire_defence_active = True
c.eq("an affected one subtracts 1", counterfire.damage_reduction_for(strike), 1)
strike.counterfire_defence_active = False

cf_ctrl = counterfire.CounterfireDefenceController(
    strat_controller(), turn_tracker=montka_turn(), decision_manager=None, game_log=tk.Log())
with settings_as(**MONTKA_ON):
    # It reacts through target_reactions, whose protocol includes a melee flag.
    c.true("melee is declined - the WHEN names the Shooting phase",
           not cf_ctrl.maybe_offer(orks, strike, melee=True))
with settings_as(**MONTKA_OFF):
    c.true("nothing without the detachment", not cf_ctrl.maybe_offer(orks, strike))

dmg_src = io.open("game/damage_resolution.py", encoding="utf-8").read()
c.true("the reduction joins the ONE damage-reduction fold",
       "montka_counterfire_defence.damage_reduction_for(" in dmg_src)
c.true("...and takes that fold's minimum-1 floor",
       "max(1, reduced - counterfire)" in dmg_src)


# -- Combat Debarkation (re-roll Wound vs the closest) --------------------
c.true("a unit that has not disembarked does not qualify",
       not debark.disembarked_this_turn(strike))
strike.disembarked_from_this_turn = object()
c.true("...and one that has, does", debark.disembarked_this_turn(strike))


def debark_ctrl(shoot=None):
    return debark.CombatDebarkationController(
        strat_controller(), shooting_controller=shoot or ShootStub(),
        turn_tracker=montka_turn(), game_log=tk.Log())


with settings_as(**MONTKA_ON):
    c.true("offered to a unit that disembarked this turn", debark_ctrl().can_use(strike))
    ctrl = debark_ctrl()
    c.true("buying it works", ctrl.use(strike))
    # "the CLOSEST enemy unit" - so the same unit gets it against one target
    # and not another, decided by the shared closest-target helper.
    c.true("the re-roll applies against the closest enemy",
           debark.applies(strike, orks, orks))
    c.true("...and not against another one", not debark.applies(strike, orks, falcon))
    ctrl.reset_phase([strike])
strike.disembarked_from_this_turn = None
shooting_src3 = io.open("game/shooting.py", encoding="utf-8").read()
c.true("closest is asked of the shared helper, not measured again",
       "exemplars_of_montka.closest_eligible_target(" in shooting_src3)


# -- Pinpoint Counter-Offensive (battle-long hit re-roll) -----------------
c.true("a T'au non-Kroot unit qualifies", pinpoint.is_eligible_avenger(strike))
c.true("Kroot do not - \"excluding KROOT units\"", not pinpoint.is_eligible_avenger(kroot))
c.true("nor does an Ork unit", not pinpoint.is_eligible_avenger(orks))

pin = pinpoint.PinpointCounterOffensiveController(
    strat_controller(), turn_tracker=montka_turn(), decision_manager=None, game_log=tk.Log())
with settings_as(**MONTKA_ON):
    c.true("nothing applies before anything died", not pin.applies(strike, orks))
    pin._marks.setdefault(HUMAN, set()).add(orks)
    c.true("the whole army may re-roll against the marked killer",
           pin.applies(strike, orks))
    c.true("...but Kroot may not - the EFFECT excludes them too",
           not pin.applies(kroot, orks))
    c.true("...and not against a different enemy", not pin.applies(strike, falcon))
with settings_as(**MONTKA_OFF):
    c.true("nothing without the detachment", not pin.applies(strike, orks))
pin._marks.clear()

fight_src2 = io.open("game/fight.py", encoding="utf-8").read()
c.true("the re-roll reaches the SHOOTING hit step",
       "self.pinpoint_counter_offensive.applies(" in shooting_src3)
c.true("...and the FIGHT one, because it says \"an attack\"",
       "self.pinpoint_counter_offensive.applies(" in fight_src2)

# WHY IT WAS NEVER OFFERED. The death sweep passes whoever was attacking, and
# _actually_finish_squad() has already cleared active_squad by the time the
# sweep runs - so a unit wiped by the LAST weapon group of an activation, which
# is the only case this Stratagem is about, arrives with killer_squad None.
# Reported: "Pinpoint counter offensive stratagem wird nie angeboten".
def pin_ctrl(dec=None):
    return pinpoint.PinpointCounterOffensiveController(
        strat_controller(), turn_tracker=montka_turn(),
        decision_manager=dec if dec is not None else DecisionManager(),
        game_log=tk.Log(), auto_players=())


with settings_as(**MONTKA_ON):
    _p = pin_ctrl()
    c.true("an unattributed death opens nothing on the spot",
           not _p.notify_unit_destroyed(strike, None))
    c.true("...and does not silently drop it either", _p._owed == [strike])
    c.true("the after-activation hook supplies the killer and offers it",
           _p.maybe_offer(orks))
    c.eq("...to the owner of the unit that died", _p.decision_manager.player, HUMAN)
    _p.decision_manager.choose(0)
    c.true("...and accepting marks the KILLER, army-wide", _p.applies(strike, orks))
    c.true("the owed list is drained, so a later attacker is not blamed too",
           _p._owed == [] and not _p.maybe_offer(falcon))

    # A killer that IS known at sweep time still works, unchanged - that is the
    # path the reported game did hit (a Piranha destroyed mid-activation).
    _p2 = pin_ctrl()
    c.true("a death WITH a killer is offered immediately",
           _p2.notify_unit_destroyed(strike, orks))

    # An owed death does not outlive its phase.
    _p3 = pin_ctrl()
    _p3.notify_unit_destroyed(strike, None)
    _p3.reset_phase()
    c.true("reset_phase() forgets an unattributed death",
           not _p3.maybe_offer(orks))

    # TWO units wiped in one sweep: a single shared _pending slot was written
    # at request() time, so the second prompt overwrote the first and the first
    # answer marked the wrong enemy. The killer rides in the option's closure.
    _p4 = pin_ctrl()
    _second = tk.build(STRIKE_TEAM, HUMAN, name="1 Strike Team 77")
    _p4.notify_unit_destroyed(strike, orks)
    _p4.notify_unit_destroyed(_second, falcon)
    _first_options = _p4.decision_manager.options
    c.true("the first prompt is still the first unit's",
           "1 Strike Team 1" in _p4.decision_manager.prompt)
    _p4.decision_manager.choose(0)
    c.true("...and answering it marks ITS killer, not the later one",
           _p4.applies(strike, orks) and not _p4.applies(strike, falcon))


# -- Focused Fire (two units, one target) ---------------------------------
def focused_ctrl(battle_round=2, tokens=None):
    return focused.FocusedFireController(
        strat_controller(), shooting_controller=ShootStub(),
        turn_tracker=montka_turn(battle_round=battle_round),
        all_tokens=tokens if tokens is not None else
        [m for sq in (strike, pathfinders, orks) for m in sq.models],
        decision_manager=None, game_log=tk.Log())


with settings_as(**MONTKA_ON):
    ctrl = focused_ctrl()
    c.eq("the partner list is the other eligible friendly unit",
         [s.name for s in ctrl.partners_for(strike)], [pathfinders.name])
    c.true("offered in round 2", ctrl.can_use(strike))
    # "You cannot use this Stratagem during the fourth or fifth battle rounds."
    c.true("not in round 4", not focused_ctrl(battle_round=4).can_use(strike))
    c.true("not in round 5", not focused_ctrl(battle_round=5).can_use(strike))
    c.true("still offered in round 3", focused_ctrl(battle_round=3).can_use(strike))

    ctrl = focused_ctrl()
    c.true("buying it works (both picks auto-resolve without a prompt)", ctrl.use(strike))
    c.true("the first unit is locked onto the enemy", focused.focus_target(strike) is orks)
    c.true("...and so is the second", focused.focus_target(pathfinders) is orks)
    # BOTH halves ride the same mark: the +1 AP and the restriction.
    c.true("it may shoot the named enemy", focused.target_allowed(strike, orks))
    c.true("...and nothing else - that is the COST", not focused.target_allowed(strike, falcon))
    got = focused.adjusted_weapon(strike_gun, strike, orks)
    c.eq("+1 AP against the named enemy", got.ap, strike_gun.ap - 1)
    c.true("...and no bonus against another (which it may not shoot anyway)",
           focused.adjusted_weapon(strike_gun, strike, falcon) is strike_gun)
    ctrl.reset_phase([strike, pathfinders])
    c.true("the lock is gone after the phase", not focused.restricts_targets(strike))

c.true("the restriction is enforced where targets are validated",
       "montka_focused_fire.target_allowed(attacking_squad, target_squad)" in shooting_src3)
c.true("...and the +1 AP in the weapon chain",
       "montka_focused_fire.adjusted_weapon(" in shooting_src3)


# -- wiring ----------------------------------------------------------------
for needle, label in [
    ("AggressiveMobilityController(", "Aggressive Mobility is built"),
    ("marker_beacon_controller = MarkerBeaconController(",
     "Marker Beacon is NOT on the proactive panel registry"),
    ("CombatDebarkationController(", "Combat Debarkation is built"),
    ("FocusedFireController(", "Focused Fire is built"),
    ("PinpointCounterOffensiveController(", "Pinpoint Counter-Offensive is built"),
    ("PulseOnslaughtController(", "Pulse Onslaught is built"),
    ("CounterfireDefenceController(", "Counterfire Defence Systems is built"),
    ("shooting_controller.pinpoint_counter_offensive = pinpoint_controller",
     "Pinpoint reaches the shooting hit step"),
    ("fight_controller.pinpoint_counter_offensive = pinpoint_controller",
     "...and the fight one"),
    ("pinpoint_controller.notify_unit_destroyed(", "Pinpoint is fed from the death sweep"),
    # ...and ANSWERED where the attacker is known. The sweep half alone is what
    # made this Stratagem look wired while never firing: it hands over None for
    # exactly the deaths the rule is about.
    ("pinpoint_controller.maybe_offer(shooter_squad)",
     "Pinpoint is answered when a shooting activation ends"),
    ("pinpoint_controller.maybe_offer(_fighter)",
     "...and when a melee one does - its WHEN is \"any phase\""),
    ("pinpoint_controller.reset_phase()", "an unattributed death expires with the phase"),
    # Marker Beacon is an end-of-Movement-phase OFFER, not a panel button:
    # objective control is only recomputed at a phase boundary, so a mid-phase
    # button could never see ground taken by the move that just happened.
    ("marker_beacon_controller.offer_at_end_of_movement_phase(mover_before)",
     "Marker Beacon is offered at the end of the Movement phase"),
    ("marker_beacon_controller.reset_phase()", "...and its window is one boundary wide"),
    ("pulse_onslaught_controller.offer_after_shooting", "Pulse Onslaught is offered after shooting"),
    ("counterfire_defence_controller,", "Counterfire joins the target reactions"),
    ("pulse_onslaught_controller.expire(", "shaken expires by deadline, not on a boundary"),
]:
    c.true(label, needle in main_src)

for word in ("aggressive_mobility", "combat_debarkation", "focused_fire",
             "pinpoint_counter", "pulse_onslaught", "counterfire_defence"):
    c.true("nothing in ai/ mentions %s - by design" % word, word not in driver)

# --- 8. Advanced Acquisition Cadre's three --------------------------------
print("\n8. Advanced Acquisition Cadre - three Stratagems")

from game import (aac_autoreactive_camouflage as camo,  # noqa: E402
                  aac_marker_beacon as beacon,
                  aac_microdrone_support as microdrone,
                  damage_resolution)

AAC2_ON = dict(ADVANCED_ACQUISITION_CADRE_PLAYERS=(HUMAN,))
AAC2_OFF = dict(ADVANCED_ACQUISITION_CADRE_PLAYERS=())


# -- Marker Beacon (secure an objective) ----------------------------------
class BeaconArea:
    def __init__(self, x, y):
        self.center_x_in, self.center_y_in = x, y

    def distance_to_model(self, model):
        return ((model.x_in - self.center_x_in) ** 2
                + (model.y_in - self.center_y_in) ** 2) ** 0.5


class BeaconObjective:
    def __init__(self, name, x, y, controlled_by=None):
        self.name = name
        self.terrain_area = BeaconArea(x, y)
        self.controlled_by = controlled_by
        self.secured_by = None

    def secure_for(self, player):
        self.secured_by = player


tk.line_up(pathfinders, 10, 10)
held = BeaconObjective("Objective Held", 10.0, 11.0, controlled_by=HUMAN)
far_held = BeaconObjective("Objective Far", 10.0, 90.0, controlled_by=HUMAN)
enemy_held = BeaconObjective("Objective Theirs", 10.0, 11.0, controlled_by="Player 2")


def beacon_ctrl(objectives, armed_for=HUMAN):
    """Its WHEN is a phase BOUNDARY, so the window its own offer opens is what
    makes can_use() answer - not turn_tracker.phase. See game/phase_window.py.
    """
    ctrl = beacon.MarkerBeaconController(
        strat_controller(), turn_tracker=turn_at(PHASE_MOVEMENT),
        objectives=objectives, all_tokens=[m for m in pathfinders.models],
        decision_manager=None, game_log=tk.Log())
    if armed_for is not None:
        ctrl._window.arm(armed_for)
    return ctrl


ctrl = beacon_ctrl([held, far_held, enemy_held])
c.eq("only an objective this unit holds AND stands on is offered",
     [o.name for o in ctrl.controllable_objectives(pathfinders)], ["Objective Held"])
with settings_as(**AAC2_ON):
    c.true("offered at the end of the Movement phase", ctrl.can_use(pathfinders))
    c.true("not to a unit the rule does not name",
           not beacon_ctrl([held]).can_use(strike))
    # Never offer what buys nothing.
    c.true("not offered with no controlled objective in range",
           not beacon_ctrl([far_held, enemy_held]).can_use(pathfinders))
    c.true("...and not at all outside the window its offer opened",
           not beacon_ctrl([held, far_held, enemy_held], armed_for=None)
           .can_use(pathfinders))
    c.true("buying it works", ctrl.use(pathfinders))
    c.eq("the objective is secured for this player", held.secured_by, HUMAN)
    c.true("...and it is not offered again", not ctrl.can_use(pathfinders))
with settings_as(**AAC2_OFF):
    c.true("nothing without the detachment",
           not beacon_ctrl([enemy_held]).can_use(pathfinders))

# THE BUG THIS BLOCK COULD NOT SEE. Everything above hands the controller
# objectives whose controlled_by is already set. In a real game
# Objective.controlled_by is recomputed ONLY in advance_turn_phase() (rule
# 14.02), so a button drawn DURING the Movement phase reads the board as it
# stood before anything moved - and "walk onto an objective and nail it down",
# the one case this Stratagem exists for, was unreachable. Reported:
# "Stratagem marker beacon wird nie angeboten".
from game.objectives import Objective as _RealObjective  # noqa: E402
from game.terrain import EXPOSED as _EXPOSED, Obstacle as _RealObstacle  # noqa: E402
from game.terrain import TerrainArea as _RealArea  # noqa: E402

_walkers = tk.build(PATHFINDER_TEAM, HUMAN, name="1 Pathfinder Team 9")
_real_obj = _RealObjective(
    _RealArea([_RealObstacle(18.0, 18.0, 4.0, 4.0, category=_EXPOSED)]),
    name="Objective Taken")
_tokens9 = list(_walkers.models)


def _beacon9():
    return beacon.MarkerBeaconController(
        strat_controller(), turn_tracker=turn_at(PHASE_MOVEMENT),
        objectives=[_real_obj], all_tokens=_tokens9,
        decision_manager=DecisionManager(), game_log=tk.Log(), auto_players=())


with settings_as(**AAC2_ON):
    tk.line_up(_walkers, 40.0, 40.0)
    _real_obj.update_control(_tokens9)        # the Command-phase boundary
    tk.line_up(_walkers, 19.0, 19.0)          # it MOVES onto the objective
    _mid = _beacon9()
    _mid._window.arm(HUMAN)
    c.true("mid-phase the control snapshot is still stale, so nothing is offered",
           not _mid.can_use(_walkers))
    _real_obj.update_control(_tokens9)        # main.py:3191, at the boundary
    _end = _beacon9()
    c.true("the end-of-Movement-phase offer sees the objective it just took",
           _end.offer_at_end_of_movement_phase(HUMAN))
    c.eq("...and asks the player whose Movement phase ended",
         _end.decision_manager.player, HUMAN)
    c.true("...naming the unit, tagged for a board pick",
           any(o["label"] == _walkers.name and o["squad"] is _walkers
               for o in _end.decision_manager.options))
    _end.decision_manager.choose(0)
    c.eq("...and accepting secures it (rule 14.03)", _real_obj.secured_by, HUMAN)
    c.true("the other player is never offered it",
           not _beacon9().offer_at_end_of_movement_phase("Player 2"))

# It is the first caller of a hook that was written and left waiting.
obj_src = io.open("game/objectives.py", encoding="utf-8").read()
c.true("rule 14.03's secure_for() is what it calls", "def secure_for(self, player):" in obj_src)
c.true("Marker Beacon calls it",
       "objective.secure_for(player)" in io.open("game/aac_marker_beacon.py", encoding="utf-8").read())


# -- Microdrone Support (shoot despite an action) -------------------------
class ActionStub:
    def __init__(self, blocked=True):
        self.blocked = blocked

    def blocks_shooting(self, squad):
        return self.blocked


def micro_ctrl(actions=None):
    return microdrone.MicrodroneSupportController(
        strat_controller(), action_controller=actions or ActionStub(),
        turn_tracker=turn_at(PHASE_SHOOTING), game_log=tk.Log())


with settings_as(**AAC2_ON):
    c.true("offered to a named unit whose action is blocking its shooting",
           micro_ctrl().can_use(pathfinders))
    # "when a unit STARTS AN ACTION" - with nothing blocking, it buys nothing.
    c.true("not offered when no action is blocking it",
           not micro_ctrl(ActionStub(blocked=False)).can_use(pathfinders))
    c.true("not to a unit the rule does not name", not micro_ctrl().can_use(strike))
    ctrl = micro_ctrl()
    c.true("buying it works", ctrl.use(pathfinders))
    c.true("the flag actions.py reads is up", microdrone.is_active(pathfinders))
    ctrl.reset_phase([pathfinders])
    c.true("gone after the phase", not microdrone.is_active(pathfinders))

# It lifts the SHOOTING half of rule 16.01 only.
actions_src = io.open("game/actions.py", encoding="utf-8").read()
c.true("blocks_shooting() consults it",
       "aac_microdrone_support.is_active(squad)" in actions_src)
_charge_half = actions_src[actions_src.index("def blocks_charge"):]
c.true("...and blocks_charge() does NOT - the text says nothing about charging",
       "aac_microdrone_support" not in _charge_half)


# -- Autoreactive Camouflage (+1 Sv while hidden) -------------------------
c.eq("an unaffected unit gets no save bonus", camo.save_bonus_for(pathfinders), 0)
pathfinders.autoreactive_camouflage_active = True
c.eq("an affected one gets 1", camo.save_bonus_for(pathfinders), 1)

# "+1 Sv" is a BETTER save, so a LOWER threshold - checked through the one
# function the panel and the resolution share.
_model = pathfinders.models[0]
_weapon = next(w for w in orks.models[0].weapons if w.weapon_type == RANGED)
sv_with, _inv, _ap = damage_resolution.save_thresholds(_model, _weapon)
pathfinders.autoreactive_camouflage_active = False
sv_without, _inv2, _ap2 = damage_resolution.save_thresholds(_model, _weapon)
c.eq("the save threshold really improves by 1", sv_with, sv_without - 1)


def camo_ctrl(hidden=True, dm=True):
    # A REAL DecisionManager by default: with None the controller declines
    # every offer for want of anyone to ask, which masked the Hidden check
    # under test - an A/B probe that removed that check still passed. Same
    # "a second condition hides the one being measured" trap as elsewhere here.
    return camo.AutoreactiveCamouflageController(
        strat_controller(), turn_tracker=turn_at(PHASE_SHOOTING),
        is_hidden_check=lambda squad: hidden,
        decision_manager=DecisionManager() if dm else None, game_log=tk.Log())


with settings_as(**AAC2_ON):
    c.true("melee is declined - the WHEN names the Shooting phase",
           not camo_ctrl().maybe_offer(orks, pathfinders, melee=True))
    # "if that friendly unit is HIDDEN" - not free, and checked.
    # The positive case first, so the negative one below cannot pass by
    # accident: with everything else satisfied, ONLY hidden decides.
    c.true("a hidden named unit IS offered the save", camo_ctrl().maybe_offer(orks, pathfinders))
    c.true("...and one that is not hidden is not",
           not camo_ctrl(hidden=False).maybe_offer(orks, pathfinders))
    c.true("a unit the rule does not name is not covered",
           not camo_ctrl().maybe_offer(orks, strike))
    # With no decision manager it declines rather than granting silently.
    c.true("no is_hidden_check reads as NOT hidden, which withholds it",
           not camo.AutoreactiveCamouflageController(
               strat_controller(), turn_tracker=turn_at(PHASE_SHOOTING),
               decision_manager=DecisionManager(),
               game_log=tk.Log()).maybe_offer(orks, pathfinders))
with settings_as(**AAC2_OFF):
    c.true("nothing without the detachment", not camo_ctrl().maybe_offer(orks, pathfinders))

for needle, label in [
    ("MarkerBeaconController(", "Marker Beacon is built"),
    ("MicrodroneSupportController(", "Microdrone Support is built"),
    ("AutoreactiveCamouflageController(", "Autoreactive Camouflage is built"),
    ("autoreactive_camouflage_controller,", "Autoreactive joins the target reactions"),
    ("is_hidden_check=lambda squad:", "its Hidden clause is answered by an injected check"),
]:
    c.true(label, needle in main_src)

for word in ("marker_beacon", "microdrone_support", "autoreactive_camouflage"):
    c.true("nothing in ai/ mentions %s - by design" % word, word not in driver)


# --- 9. All nineteen ------------------------------------------------------
print("\n9. All nineteen")

# Every Stratagem of the five new detachments has a module, and every module
# gates on its own detachment. A count, so a twentieth cannot be added without
# this line moving.
import glob  # noqa: E402
_modules = sorted(os.path.basename(p)[:-3] for p in glob.glob("game/*.py")
                  if os.path.basename(p).startswith(
                      ("kauyon_", "montka_", "aac_", "aux_", "epc_")))
c.eq("nineteen Stratagem modules, one per printed Stratagem", len(_modules), 19)
for name in _modules:
    src = io.open("game/%s.py" % name, encoding="utf-8").read()
    c.true("%s gates on a detachment setting" % name,
           "has_detachment(" in src or "stratagem_target_ok(" in src)
    c.true("%s quotes its printed rule" % name, "RULE (verbatim" in src)

c.finish()
