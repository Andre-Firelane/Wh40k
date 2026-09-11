"""Tests for the Explosives core Stratagem's eligibility gate (rule 15.05,
game/explosives.py).

REPORTED: "explosives geht nur vor dem schiessen, weil man eligible to shoot
sein muss. ich konnte es aber nach dem schiessen machen."

THE PRINTED CARD (rules/.cache/orks.html, Core Stratagems block - the core
rules are NOT in rules/*/*.md, see the controller's own docstring):

    TARGET: One friendly unengaged EXPLOSIVES / GRENADES unit that is eligible
    to shoot and did not make an advance move this turn.

can_use() used to stop at available_shooting_types() and never consult
ShootingController, so a unit could Explosives after it had already shot.
There was NO test of can_use() at all, which is why that survived; this file
is that test.

WHAT IT ACTUALLY MEASURES, and why each piece is shaped the way it is:

  * the reported case runs a REAL activation through the real
    ShootingController rather than writing to shot_squad_ids by hand - the
    fact has to be produced the way the game produces it;
  * the TARGET line is THREE INDEPENDENT clauses, and two of them are proven
    independent by finding a case where can_shoot() says YES and the
    Stratagem still says no: an [ASSAULT] weapon after an Advance, and a
    VEHICLE engaged in combat (rule 10.06 lets it shoot out of the fight).
    Without those two cases "we deleted a redundant line" would look correct;
  * a counter-check that a unit which has NOT shot is still offered it -
    otherwise "refused after shooting" is indistinguishable from "never
    offered".

Uses real ShootingController/StratagemController/CommandPointManager/
TurnTracker/GameState objects and real datasheets throughout.

Run: python test_explosives.py
"""
import inspect
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import testkit as tk
from game import maps
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.explosives import ExplosivesController
from game.factions import build_squad
from game.factions.orks import BOYZ, DEFFKOPTAS, GRETCHIN
from game.game_state import GameState
from game.shooting import ShootingController
from game.stratagems import StratagemController
from game.turn import PHASES, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker
from game.weapons import WeaponProfile

m = maps.get("map2")
maps.apply_to_config(m)

checks = tk.Checks("explosives / rule 15.05 eligibility")


class PlainGun(WeaponProfile):
    """Featureless 36" gun: no keyword opens a prompt mid-activation, so the
    end-to-end run below measures THIS gate and nothing else."""
    name = "Plain Gun"
    range_in = 36
    attacks = 1
    strength = 4
    ap = 0
    damage = 1


class AssaultGun(PlainGun):
    """Same, but [ASSAULT] - so the unit is still eligible to shoot after an
    Advance (rule 24.04). That is what makes the Advance clause's
    independence measurable at all."""
    name = "Assault Gun"
    assault = True


class Blocker:
    """Minimal rule 16.01 action lock, the one clause the hand-built
    "shot_squad_ids + available_shooting_types" alternative would have
    missed."""

    def __init__(self, squad=None):
        self.squad = squad

    def blocks_shooting(self, squad):
        return squad is self.squad

    def blocks_charging(self, squad):
        return False


def scene(shooter_sheet=BOYZ, gun=PlainGun, gap=6.0, cp=3, second_shooter=False):
    """Two (or three) squads in the Shooting phase, all unengaged, the
    shooter(s) carrying GRENADES and a gun that reaches."""
    st = GameState()
    shooter = build_squad(shooter_sheet, "Player 1", name="1 Shooter 1")
    target = build_squad(GRETCHIN, "Player 2", name="2 Target 1")
    squads = [shooter, target]
    second = None
    if second_shooter:
        second = build_squad(shooter_sheet, "Player 1", name="1 Shooter 2")
        squads.append(second)

    tk.line_up(shooter, y=20.0)
    tk.line_up(target, y=20.0 + gap)
    if second is not None:
        tk.line_up(second, x=40.0, y=20.0)
    for squad in squads:
        for model in squad.models:
            model.weapons = [gun()]
            st.add_token(model)

    tt = TurnTracker()
    tt.started = True
    tt.phase_index = PHASES.index(PHASE_SHOOTING)
    tt.turn_owner = "Player 1"
    tt.set_active("Player 1")

    cps = CommandPointManager()
    cps.cp["Player 1"] = cp
    strat = StratagemController(command_points=cps)
    dice = tk.RecordingDice()
    dec = DecisionManager()
    sc = ShootingController(
        obstacles=[], dice_manager=dice, turn_tracker=tt, all_tokens=st.tokens,
        decision_manager=dec,
    )
    ctrl = ExplosivesController(
        strat, dice, all_tokens=st.tokens, obstacles=[], terrain_areas=[],
        turn_tracker=tt, shooting_controller=sc,
    )
    return dict(state=st, shooter=shooter, second=second, target=target, turn=tt,
                shooting=sc, explosives=ctrl, dice=dice, decision=dec, strat=strat, cps=cps)


def resolve(sc, dice, limit=400):
    """Drive one whole shooting activation the way main.py's loop does."""
    for _ in range(limit):
        if dice.is_pending:
            dice.acknowledge()
            sc.on_dice_acknowledged()
            continue
        if sc.pending_damage_choice:
            sc.choose_damage_model(sc.pending_damage_choice[0])
            continue
        return True
    return False


# ================================================== 1. liveness
print("\n1) liveness - the scene really offers it before anything happens")
sc1 = scene()
checks.true("the shooter has not shot yet", sc1["shooter"] not in sc1["shooting"].shot_squad_ids)
checks.true("...and Explosives is offered", sc1["explosives"].can_use(sc1["shooter"]))
checks.true("the real can_shoot() agrees", sc1["shooting"].can_shoot(sc1["shooter"]))


# ================================================== 2. the reported case
print("\n2) the reported case - a unit that has SHOT is refused")
s2 = scene()
sc, shooter = s2["shooting"], s2["shooter"]
tk.script(default=4)
sc.start_shooting(shooter)
if sc.state == "choosing_shooting_type":
    sc.choose_shooting_type(sc.available_types[0])
sc.choose_target_squad(s2["target"])
sc.choose_weapon(sc.weapon_eligibility()[0][0])
checks.true("the activation ran to completion", resolve(sc, s2["dice"]))
checks.true("the engine really booked the unit as having shot",
            shooter in sc.shot_squad_ids)
checks.true("...so Explosives is now refused", not s2["explosives"].can_use(shooter))
checks.true("and the real can_shoot() refuses it too", not sc.can_shoot(shooter))


# ================================================== 3. counter-check
print("\n3) counter-check - a unit that has NOT shot is still offered it")
s3 = scene(second_shooter=True)
sc, shooter, second = s3["shooting"], s3["shooter"], s3["second"]
tk.script(default=4)
sc.start_shooting(shooter)
if sc.state == "choosing_shooting_type":
    sc.choose_shooting_type(sc.available_types[0])
sc.choose_target_squad(s3["target"])
sc.choose_weapon(sc.weapon_eligibility()[0][0])
resolve(sc, s3["dice"])
checks.true("the unit that shot is refused", not s3["explosives"].can_use(shooter))
checks.true("...but the one that did NOT shoot is still offered it",
            s3["explosives"].can_use(second))


# ================================================== 4. mid-activation
print("\n4) mid-activation - selected to shoot, but not yet booked")
s4 = scene()
sc, shooter = s4["shooting"], s4["shooter"]
checks.true("before: offered", s4["explosives"].can_use(shooter))
sc.active_squad = shooter
checks.true("a unit mid-activation HAS been selected to shoot, so it is refused",
            not s4["explosives"].can_use(shooter))
checks.true("...and shot_squad_ids alone would not have caught it",
            shooter not in sc.shot_squad_ids)
sc.active_squad = None
checks.true("after: offered again", s4["explosives"].can_use(shooter))


# ================================================== 5. rule 16.01
print("\n5) rule 16.01's action lock - the clause a hand-built gate would miss")
s5 = scene()
s5["shooting"].action_controller = Blocker(s5["shooter"])
checks.true("a unit performing an action is not eligible to shoot",
            not s5["shooting"].can_shoot(s5["shooter"]))
checks.true("...so Explosives is refused as well",
            not s5["explosives"].can_use(s5["shooter"]))


# ================================================== 6. three independent clauses
print("\n6) the TARGET line is three independent clauses")

# 6a. "did not make an advance move this turn" - proven independent by an
# [ASSAULT] weapon, which keeps the unit eligible to shoot after an Advance.
s6 = scene(gun=AssaultGun)
shooter = s6["shooter"]


class Mover:
    def __init__(self, advanced):
        self.advanced_squad_ids = advanced


s6["explosives"].movement_controller = Mover({shooter})
s6["shooting"].movement_controller = Mover({shooter})
checks.true("with [ASSAULT], an Advanced unit IS still eligible to shoot",
            s6["shooting"].can_shoot(shooter))
checks.true("...and Explosives still refuses it - the Advance clause is its own",
            not s6["explosives"].can_use(shooter))

# 6b. "unengaged" - proven independent by a VEHICLE, which rule 10.06 lets
# shoot out of combat.
s6b = scene(shooter_sheet=DEFFKOPTAS, gap=1.0)
kopta = s6b["shooter"]
checks.true("the scene really has them engaged", kopta.is_engaged(s6b["state"].tokens))
checks.true("a VEHICLE engaged in combat IS still eligible to shoot (10.06)",
            s6b["shooting"].can_shoot(kopta))
checks.true("...and Explosives still refuses it - the unengaged clause is its own",
            not s6b["explosives"].can_use(kopta))

# 6c. the phase clause.
s6c = scene()
s6c["turn"].phase_index = PHASES.index(PHASE_MOVEMENT)
checks.true("outside the Shooting phase it is refused",
            not s6c["explosives"].can_use(s6c["shooter"]))


# ================================================== 7. turn_owner, not active_player
print("\n7) ownership is read from turn_owner, not the transient active_player")
s7 = scene()
checks.true("before: offered", s7["explosives"].can_use(s7["shooter"]))
# What a defender's save roll does mid-activation (game/shooting.py's
# set_active(target_squad.owner)). testkit's tracker sets both fields to the
# same value, so this has to be flipped explicitly or the check proves nothing.
s7["turn"].set_active("Player 2")
checks.eq("the scene really separated the two fields",
          (s7["turn"].turn_owner, s7["turn"].active_player), ("Player 1", "Player 2"))
checks.true("...and Explosives is STILL offered", s7["explosives"].can_use(s7["shooter"]))


# ================================================== 8. no collaborator
print("\n8) without a ShootingController it refuses rather than crashing")
s8 = scene()
s8["explosives"].shooting_controller = None
checks.true("refused, not crashed", not s8["explosives"].can_use(s8["shooter"]))


# ================================================== 9. provenance
print("\n9) the printed text's provenance survives in the docstring")
doc = inspect.getdoc(ExplosivesController) or ""
checks.true("the source of the printed card is cited", "rules/.cache/" in doc)
checks.true("...and the superseded reading is recorded by name",
            "CLAUDE.history.md" in doc)
checks.true("the Swooping Hawks lock-out still lives in can_use's own body",
            "explosives_locked_until_end_of_turn" in inspect.getsource(ExplosivesController.can_use))


checks.finish()
