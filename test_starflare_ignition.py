"""Tests for the Starflare Ignition System Enhancement
(game/starflare_ignition.py) - the first Enhancement this engine implements.

RULE (user-supplied, 20 pts): T'AU EMPIRE BATTLESUIT model only. At the end of
your opponent's turn, if the bearer's unit is not within Engagement Range of
one or more enemy units, you can remove that unit from the battlefield and
place it into Strategic Reserves.

Three things actually need proving, and each gets an A/B where a pass could
otherwise come from something unrelated:

  1. GRANTING puts it on ONE model and enforces the bearer restriction - the
     A/B being that the same call against a non-BATTLESUIT or a non-CHARACTER
     unit is refused, so "it worked" is not just "any squad accepts anything".
  2. The CONDITIONS gate correctly - in particular, the same unit is offered
     when clear and refused when an enemy is inside Engagement Range, at the
     same board position bar the enemy's distance.
  3. The WITHDRAWAL really takes the unit off the battlefield in the way the
     rest of the engine reads as off-board (models out of game_state.tokens,
     unit in game_state.reserves) - checked through the real IngressController,
     which must then be willing to bring it back.

Uses real GameState/DecisionManager/TurnTracker/IngressController/
SetupController objects and real datasheets.

Run: python test_starflare_ignition.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import maps
from game.decision import DecisionManager
from game.factions import build_squad
from game.factions.orks import GRETCHIN
from game.factions.tau_empire import COMMANDER_IN_COLDSTAR_BATTLESUIT, CRISIS_STARSCYTHE, STRIKE_TEAM
from game.game_state import GameState
from game.ingress import IngressController
from game.setup import SetupController
from game.squad import ENGAGEMENT_RANGE_IN
from game.terrain import EXPOSED, Obstacle
from game.starflare_ignition import (
    STARFLARE_IGNITION_SYSTEM_NAME, STARFLARE_IGNITION_SYSTEM_POINTS,
    StarflareIgnitionController, bearer_models, grant, has_starflare_ignition_system,
)
from game.turn import TurnTracker

m = maps.get("map2")
maps.apply_to_config(m)

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    print(f"  {'OK  ' if condition else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")


def line_up(squad, x=30.0, y=30.0, step=2.6):
    for i, mdl in enumerate(squad.models):
        mdl.x_in, mdl.y_in = x + i * step, y
    return squad


def scene(enemy_y=40.0):
    """One T'au unit carrying the Enhancement, one Ork unit `enemy_y` away.
    Open ground, well clear of terrain, so nothing but distance is in play."""
    st = GameState()
    bearer = build_squad(COMMANDER_IN_COLDSTAR_BATTLESUIT, "Player 1", name="1 Coldstar 1")
    grant(bearer)
    enemy = build_squad(GRETCHIN, "Player 2", name="2 Gretchin 1")
    for squad in (bearer, enemy):
        line_up(squad, y=30.0 if squad is bearer else enemy_y, step=1.6 if squad is enemy else 2.6)
        for mdl in squad.models:
            st.add_token(mdl)

    tt = TurnTracker()
    tt.started = True
    tt.battle_round = 2  # rule 20.03: reserves can arrive again from round 2
    dm = DecisionManager()
    ctrl = StarflareIgnitionController(st, game_log=None)
    return dict(state=st, bearer=bearer, enemy=enemy, turn=tt, dm=dm, ctrl=ctrl)


# ===================================================== 1. granting the thing
print("\n1) granting: one model, and only a legal one")

squad = build_squad(COMMANDER_IN_COLDSTAR_BATTLESUIT, "Player 1", name="1 Coldstar 1")
base_points = squad.points
model = grant(squad)
check("the bearer is the Coldstar Commander model", model is squad.models[0])
check("the unit now has it", has_starflare_ignition_system(squad))
check("exactly one model carries it", len(bearer_models(squad)) == 1)
check(f"it costs {STARFLARE_IGNITION_SYSTEM_POINTS} pts on top of the unit",
      squad.points == base_points + STARFLARE_IGNITION_SYSTEM_POINTS,
      f"{base_points} -> {squad.points}")

# A fresh unit of the same datasheet must NOT inherit it: build_squad() makes a
# UnitProfile instance per model, and this rule leans on that entirely.
fresh = build_squad(COMMANDER_IN_COLDSTAR_BATTLESUIT, "Player 1", name="1 Coldstar 2")
check("a second unit of the same datasheet does not inherit it",
      not has_starflare_ignition_system(fresh))


def refuses(squad):
    try:
        grant(squad)
    except ValueError:
        return True
    return False


# A/B on the bearer restriction: the grant above proves acceptance, these prove
# it is not simply accepting everything.
check("a non-BATTLESUIT CHARACTER unit is refused",
      refuses(build_squad(GRETCHIN, "Player 2", name="2 Gretchin 1")))
check("a BATTLESUIT unit with no CHARACTER model is refused",
      refuses(build_squad(CRISIS_STARSCYTHE, "Player 1", name="1 Crisis 1")))
check("granting it twice to the same unit is refused", refuses(squad))

check("the Enhancement is registered as faction data too",
      any(e.name == STARFLARE_IGNITION_SYSTEM_NAME and e.points == STARFLARE_IGNITION_SYSTEM_POINTS
          for e in __import__("game.factions.tau_empire", fromlist=["x"]).RETALIATION_CADRE.enhancements))


# ================================================================ 2. the gate
print("\n2) when it can and cannot be used")

sc = scene(enemy_y=40.0)  # 10" apart - well clear
check("a clear unit can withdraw", sc["ctrl"].can_withdraw(sc["bearer"]))

# A/B on the Engagement Range condition: same scene, enemy moved inside 2".
gap = ENGAGEMENT_RANGE_IN - 0.5
engaged = scene(enemy_y=30.0 + gap + sc["bearer"].models[0].radius_in + 0.63)
check("an engaged unit cannot withdraw", not engaged["ctrl"].can_withdraw(engaged["bearer"]),
      f'enemy within {ENGAGEMENT_RANGE_IN}"')

sc2 = scene()
plain = build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
line_up(plain, x=10.0, y=10.0, step=1.6)
for mdl in plain.models:
    sc2["state"].add_token(mdl)
check("a unit without the Enhancement cannot withdraw", not sc2["ctrl"].can_withdraw(plain))

# Already off the battlefield: nothing to remove.
sc3 = scene()
sc3["ctrl"].withdraw(sc3["bearer"])
check("a unit already in reserves cannot withdraw again", not sc3["ctrl"].can_withdraw(sc3["bearer"]))

sc4 = scene()
sc4["bearer"].embarked_in = object()  # rule 18.02 - embarked is off-board
check("an embarked unit cannot withdraw", not sc4["ctrl"].can_withdraw(sc4["bearer"]))

# A TRANSPORT with passengers would orphan them - guarded even though no
# BATTLESUIT datasheet is a TRANSPORT today.
sc5 = scene()
passengers = build_squad(GRETCHIN, "Player 1", name="1 Passengers 1")
passengers.embarked_in = sc5["bearer"].models[0]
sc5["state"].embarked_squads.append(passengers)
check("a unit carrying passengers cannot withdraw", not sc5["ctrl"].can_withdraw(sc5["bearer"]))


# ============================================================== 3. the offer
print("\n3) the end-of-opponent's-turn offer")

sc = scene()
sc["ctrl"].offer("Player 2", sc["dm"])  # Player 2's turn just ended
check("the prompt is raised", sc["dm"].is_pending)
check("it belongs to the bearer's owner", sc["dm"].player == "Player 1")
check("it names the Enhancement", STARFLARE_IGNITION_SYSTEM_NAME in (sc["dm"].prompt or ""))
check("it is not flagged as a stratagem", not sc["dm"].is_stratagem)
check("it offers withdraw and stay", len(sc["dm"].options or []) == 2)

# Declining leaves the unit exactly where it was.
before = list(sc["state"].tokens)
sc["dm"].choose(1)
check("declining leaves the unit on the battlefield",
      sc["state"].tokens == before and not sc["state"].reserves)
check("declining resolves the prompt", not sc["dm"].is_pending)

# The offer goes to the OPPONENT of whoever's turn ended - not to the ending
# player themselves.
sc = scene()
sc["ctrl"].offer("Player 1", sc["dm"])
check("no offer at the end of the bearer's OWN turn", not sc["dm"].is_pending)

# An engaged unit is never offered at all.
engaged = scene(enemy_y=30.0 + 1.0)
engaged["ctrl"].offer("Player 2", engaged["dm"])
check("an engaged unit is not offered", not engaged["dm"].is_pending)


# ========================================================= 4. the withdrawal
print("\n4) what withdrawing actually does")

sc = scene()
bearer = sc["bearer"]
models = list(bearer.models)
bearer.ingress_locked = True  # as if it had arrived from reserves earlier
sc["ctrl"].offer("Player 2", sc["dm"])
sc["dm"].choose(0)

check("its models are off the board", not any(mo in sc["state"].tokens for mo in models))
check("the unit is in Strategic Reserves", bearer in sc["state"].reserves)
check("the unit keeps its models", list(bearer.models) == models)
check("the enemy is untouched", all(mo in sc["state"].tokens for mo in sc["enemy"].models))
check("rule 20.04's post-arrival lock is cleared", not bearer.ingress_locked)
check("it still carries the Enhancement", has_starflare_ignition_system(bearer))

# The real test of "off the battlefield": the rest of the engine has to agree.
setup = SetupController(sc["state"], obstacles=sc["state"].obstacles, all_tokens=sc["state"].tokens,
                        board_width_in=m.width_in, board_height_in=m.height_in)
ingress = IngressController(setup, sc["state"], sc["state"].tokens, turn_tracker=sc["turn"],
                            board_width_in=m.width_in, board_height_in=m.height_in)
check("IngressController will bring it back (rule 20.04)", ingress.can_ingress(bearer))
check("it is no longer engaged-checkable on the board",
      not any(mo.squad is bearer for mo in sc["state"].tokens))

# Objective control is recomputed on the way out (rule 14.02) - the withdrawing
# unit may have been the only thing holding one, and leaving it "controlled" by
# a unit that is no longer on the board would score points for nobody standing
# there.
sc = scene()
area = sc["state"].add_terrain_area([Obstacle(28.0, 28.0, 6.0, 6.0, category=EXPOSED)])
objective = sc["state"].add_objective(area, name="Test Objective")
objective.update_control(sc["state"].tokens)
check("the bearer controls the objective first", objective.controlled_by == "Player 1",
      str(objective.controlled_by))
sc["ctrl"].withdraw(sc["bearer"])
check("control is recomputed when it leaves", objective.controlled_by is None,
      str(objective.controlled_by))
check("withdrawing the same unit twice is refused", not sc["ctrl"].withdraw(sc["bearer"]))


# ============ 6. the reported bug: corpses that have not been swept up yet
# User: "ich habe gewaehlt, dass der squad wieder in strategic reserves soll,
# aber er ist auf dem feld geblieben."
#
# main.py's frame order is: event loop / run_ai_action() -> advance_turn_phase()
# -> offer(), and only THEN, further down the same frame (main.py:2501),
# state.remove_dead_models(). So this rule is ALWAYS evaluated on a board that
# still holds every model killed during the turn that just ended, each with
# current_wounds <= 0 but still in Squad.models and in GameState.tokens.
#
# Reproduced here by doing exactly that, in that order. Each case carries its
# own A/B, because "the prompt did/didn't appear" could otherwise come from the
# scene rather than from the corpse.
print("\n6) models killed on the opponent's turn are not swept up yet")


class RecordingLog:
    def __init__(self):
        self.lines = []

    def add(self, message, file_only=False):
        self.lines.append(message)


# --- A: the BEARER is the model that died -----------------------------------
sc = scene()
log = RecordingLog()
sc["ctrl"].game_log = log
bearer_model = bearer_models(sc["bearer"])[0]
check("A/B: the same unit is offered while its bearer lives", sc["ctrl"].can_withdraw(sc["bearer"]))
bearer_model.current_wounds = 0
check("a dead bearer still sits in the unit and in tokens (that IS the moment)",
      bearer_model in sc["bearer"].models and bearer_model in sc["state"].tokens)
sc["ctrl"].offer("Player 2", sc["dm"])
check("no prompt is raised for a unit whose bearer just died", not sc["dm"].is_pending,
      "otherwise the human is offered a withdrawal that cannot happen")
check("and the game log says why it was not offered",
      any("is not offered" in line for line in log.lines), str(log.lines))

# ...and if one is answered anyway, the refusal is written down rather than
# closing the prompt in silence, which is what made the report undiagnosable.
sc["state"].remove_dead_models()
check("the withdrawal is refused", not sc["ctrl"].withdraw(sc["bearer"]))
check("and the refusal names its reason in the log",
      any("cannot use the" in line and "Enhancement" in line for line in log.lines),
      str(log.lines))

# --- B: the only enemy inside Engagement Range is a corpse ------------------
engaged = scene(enemy_y=30.0 + ENGAGEMENT_RANGE_IN - 0.5)
check("A/B: the live enemy really does engage it", not engaged["ctrl"].can_withdraw(engaged["bearer"]))
for mdl in engaged["enemy"].models:
    mdl.current_wounds = 0
check("a wiped-out enemy no longer counts as Engagement Range",
      engaged["ctrl"].can_withdraw(engaged["bearer"]))
engaged["ctrl"].offer("Player 2", engaged["dm"])
check("so the offer is raised", engaged["dm"].is_pending)
engaged["state"].remove_dead_models()
engaged["dm"].choose(0)
check("and choosing it really does take the unit off the board",
      not any(mo in engaged["state"].tokens for mo in engaged["bearer"].models)
      and engaged["bearer"] in engaged["state"].reserves)


# =================================================================== summary
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for name in FAIL:
    print(f"  FAILED: {name}")
sys.exit(1 if FAIL else 0)
