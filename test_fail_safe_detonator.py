"""Tests for Retaliation Cadre's Fail-Safe Detonator stratagem
(game/fail_safe_detonator.py).

RULE (user-supplied): 2CP, Epic Deed. WHEN any phase, just after a T'AU EMPIRE
BATTLESUIT model from your army that HAS the Deadly Demise ability is
destroyed. TARGET that destroyed model's unit - usable even if that unit was
just destroyed. EFFECT before removing the model, do not roll for that ability;
instead choose whether the result is a 1 or a 6.

Two things are being checked, and they fail in different ways:

  * the effect must NOT resolve anything itself - it has to replace rule
    24.08's roll and let that controller run, so the checks are "no dice were
    thrown for the ability" and "the outcome is the chosen one", both ways (a 6
    detonates, a 1 does not);
  * Deadly Demise is a CONDITION of the WHEN clause, not a branch. This was a
    user report: a destroyed Stealth Battlesuit - a BATTLESUIT with no Deadly
    Demise - was being offered the stratagem. Section 2 pins that down, and
    isolates the condition so "not offered" cannot be passing for some other
    reason.

Everything is checked against a destroyed model whose Token has already been
removed from play, which is the only state this hook is ever called in, and
whose death has been queued with DeadlyDemiseController first - exactly the
order main.py's dead-model loop uses.

Uses real DeadlyDemiseController/StratagemController/CommandPointManager/
DecisionManager/DiceManager/GameState objects and real datasheets, with
scripted dice.

Run: python test_fail_safe_detonator.py
"""
import copy
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import dice as dice_mod
from game import maps
from game.command_points import CommandPointManager
from game.deadly_demise import DeadlyDemiseController
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions import tau_empire as tau
from game.factions.orks import GRETCHIN
from game.factions.tau_empire import (CRISIS_STARSCYTHE, GHOSTKEEL_BATTLESUIT,
                                      RIPTIDE_BATTLESUIT, STEALTH_BATTLESUITS,
                                      STRIKE_TEAM)
from game.fail_safe_detonator import (FAIL_SAFE_CP_COST,
                                      FailSafeDetonatorController)
from game.game_state import GameState
from game.stratagems import StratagemController
from game.turn import PHASES, PHASE_SHOOTING, TurnTracker

m = maps.get("map2")
maps.apply_to_config(m)

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    print(f"  {'OK  ' if condition else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")


# --------------------------------------------------------------- scripted dice
_scripted = []
_default = [None]


def _scripted_randint(low, high):
    if _scripted:
        return _scripted.pop(0)
    return high if _default[0] is None else _default[0]


dice_mod.random.randint = _scripted_randint


def script(*values, default=None):
    _scripted[:] = list(values)
    _default[0] = default


def grant_deadly_demise(model, x=3):
    """Give ONE model Deadly Demise for a constructed case, without touching
    the profile object its squadmates share - same copy.copy() reasoning the
    engine itself uses for weapon instances. Only used where no real datasheet
    covers the shape being tested, and labelled as such at the call site."""
    model.profile = copy.copy(model.profile)
    model.profile.deadly_demise = x
    model.profile.deadly_demise_notation = None
    return model


def scene(dying_sheet=GHOSTKEEL_BATTLESUIT, cp=4, near=(("2 Orks 1", GRETCHIN, "Player 2", 3.0),)):
    """A T'au unit at (20,20) plus whatever should be standing near it.
    `near` entries are (name, datasheet, owner, distance in inches straight
    down the board) - so "within 6"" is a single number per unit."""
    st = GameState()
    dying = build_squad(dying_sheet, "Player 1", name="1 Suits 1")
    for i, mdl in enumerate(dying.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 2.4, 20.0
        st.add_token(mdl)
    neighbours = {}
    for name, sheet, owner, dist in near:
        squad = build_squad(sheet, owner, name=name)
        for i, mdl in enumerate(squad.models):
            mdl.x_in, mdl.y_in = 20.0 + i * 1.4, 20.0 + dist
            st.add_token(mdl)
        neighbours[name] = squad

    tt = TurnTracker()
    tt.started = True
    tt.battle_round = 2
    tt.phase_index = PHASES.index(PHASE_SHOOTING)
    tt.turn_owner = tt.active_player = "Player 2"

    cps = CommandPointManager()
    cps.cp["Player 1"] = cp
    strat = StratagemController(command_points=cps)
    dm = DiceManager()
    dec = DecisionManager()
    dd = DeadlyDemiseController(dm, st.tokens, turn_tracker=tt)
    fs = FailSafeDetonatorController(strat, deadly_demise_controller=dd, decision_manager=dec)
    return dict(state=st, dying=dying, near=neighbours, turn=tt, cps=cps, strat=strat,
                dice=dm, decision=dec, demise=dd, fail_safe=fs)


def kill(sc, *models):
    """Destroy models exactly the way main.py's own loop leaves them: wounds at
    zero, token already removed from play, death queued with rule 24.08 BEFORE
    the stratagem is offered, position and .squad preserved."""
    for model in models:
        model.current_wounds = 0
    sc["state"].remove_dead_models()
    for model in models:
        sc["demise"].queue_death(model)
    return models[0]


def ack(sc):
    sc["dice"].acknowledge()
    sc["demise"].on_dice_acknowledged()


# ================================= 1. the roll is replaced, not resolved here
print("\n1) with Deadly Demise: the roll is replaced, not resolved here")

sc = scene()
dead = sc["dying"].models[0]
check("this datasheet is a BATTLESUIT and really has Deadly Demise",
      dead.profile.battlesuit and dead.profile.deadly_demise is not None,
      f"battlesuit={dead.profile.battlesuit} demise={dead.profile.deadly_demise}")
kill(sc, dead)
check("rule 24.08 has it queued", sc["demise"].has_queued_death(dead))
check("the offer opens", sc["fail_safe"].notify_destroyed(dead) and sc["decision"].is_pending)
check("and belongs to the destroyed model's owner", sc["decision"].player == "Player 1",
      str(sc["decision"].player))
labels = " | ".join(o["label"] for o in (sc["decision"].options or []))
check("both results are offered as options, plus Decline",
      "detonate" in labels and "do not detonate" in labels and "Decline" in labels, labels)

sc["decision"].choose(0)  # force a 6
check("using it costs exactly 2 CP", sc["cps"].cp["Player 1"] == 4 - FAIL_SAFE_CP_COST,
      str(sc["cps"].cp["Player 1"]))
check("no dice were thrown for the ability", not sc["dice"].is_pending)
# The detonation now runs through rule 24.08's own controller, unchanged.
script(default=3)  # for this datasheet's printed "Deadly Demise D3"
sc["demise"].maybe_start_next()
# "the D6 is skipped" means precisely: that controller never put its own
# detonation die on the table. Its dice-notation X roll (the D3 that decides
# how many mortal wounds) is a SEPARATE, later step and still happens - so
# _rolling_for, not is_busy, is the thing to assert.
check("the D6 itself is never rolled", sc["demise"]._rolling_for is None)
# Anything pending now can only be the per-unit mortal-wound D3, which rule
# 24.08 throws once for EACH unit caught in the blast (see
# game/deadly_demise.py's _begin_next_squad) - those rolls are labelled
# "<model> vs <unit>", the detonation die is not.
check("what is pending instead is a per-unit mortal-wound D3, if anything",
      not sc["dice"].is_pending or " vs " in (sc["dice"].label or ""),
      sc["dice"].label or "nothing pending")
if sc["dice"].is_pending:
    ack(sc)
check("a chosen 6 detonates (mortal wounds are being allocated)",
      sc["demise"].pending_damage_choice is not None or sc["demise"].mortal_wound_session is not None)

# A chosen 1 must do the opposite, on the same board.
sc = scene()
dead = kill(sc, sc["dying"].models[0])
sc["fail_safe"].notify_destroyed(dead)
sc["decision"].choose(1)  # force a 1
sc["demise"].maybe_start_next()
check("a chosen 1 does not detonate", sc["demise"].pending_damage_choice is None
      and sc["demise"].mortal_wound_session is None and not sc["dice"].is_pending)

# Declining leaves rule 24.08 to roll normally.
sc = scene()
dead = kill(sc, sc["dying"].models[0])
sc["fail_safe"].notify_destroyed(dead)
sc["decision"].choose(2)  # decline
check("declining spends no CP", sc["cps"].cp["Player 1"] == 4, str(sc["cps"].cp["Player 1"]))
script(6)
sc["demise"].maybe_start_next()
check("and the normal Deadly Demise D6 is rolled instead",
      sc["dice"].is_pending and "Deadly Demise" in (sc["dice"].label or ""), sc["dice"].label or "")

# The choice only exists while 24.08's roll is still ahead of us.
sc = scene()
dead = kill(sc, sc["dying"].models[0])
script(1)
sc["demise"].maybe_start_next()
ack(sc)
check("once that ability has already resolved there is nothing left to replace",
      not sc["fail_safe"].can_offer(dead))


# ============================ 2. Deadly Demise is a condition, not a branch
print("\n2) no Deadly Demise: not offered at all (reported Stealth Battlesuit case)")

# The reported case, verbatim: a destroyed Stealth Battlesuit.
sc = scene(dying_sheet=STEALTH_BATTLESUITS)
stealth = sc["dying"].models[0]
check("Stealth Battlesuits are BATTLESUIT models",
      stealth.profile.battlesuit, str(stealth.profile.battlesuit))
check("...but have no Deadly Demise", stealth.profile.deadly_demise is None)
kill(sc, stealth)
check("so the stratagem is NOT offered", not sc["fail_safe"].can_offer(stealth))
check("and no prompt is opened", not sc["fail_safe"].notify_destroyed(stealth)
      and not sc["decision"].is_pending)

# A/B: "not offered" has to be BECAUSE of Deadly Demise, not because something
# else about this scene disqualifies it. Grant that one model the ability and
# the very same death must be offered.
sc = scene(dying_sheet=STEALTH_BATTLESUITS)
granted = grant_deadly_demise(sc["dying"].models[0])   # constructed, not a real datasheet
kill(sc, granted)
check("the same death IS offered once that model has Deadly Demise",
      sc["fail_safe"].can_offer(granted), "so the rejection above is the condition, nothing else")

# Crisis Starscythe: the other multi-model BATTLESUIT datasheet, same answer.
sc = scene(dying_sheet=CRISIS_STARSCYTHE)
crisis = kill(sc, sc["dying"].models[0])
check("Crisis Starscythe Battlesuits are not offered either",
      crisis.profile.deadly_demise is None and not sc["fail_safe"].can_offer(crisis))

# And the whole roster, so this cannot silently drift with a new datasheet.
suits, with_demise = [], []
for name in dir(tau):
    sheet = getattr(tau, name)
    if not hasattr(sheet, "model_lines"):
        continue
    try:
        squad = build_squad(sheet, "Player 1", name="x")
    except Exception:
        continue
    if any(mdl.profile.battlesuit for mdl in squad.models):
        suits.append(name)
        if any(mdl.profile.deadly_demise is not None for mdl in squad.models):
            with_demise.append(name)
check("only Ghostkeel and Riptide can ever trigger it today",
      sorted(with_demise) == ["GHOSTKEEL_BATTLESUIT", "RIPTIDE_BATTLESUIT"],
      f"{len(suits)} BATTLESUIT datasheets, of which {sorted(with_demise)}")

# The other one, so the check above is not resting on a single datasheet.
sc = scene(dying_sheet=RIPTIDE_BATTLESUIT)
riptide = kill(sc, sc["dying"].models[0])
check("a destroyed Riptide is offered it", sc["fail_safe"].can_offer(riptide))


# ================================================== 3. WHEN / TARGET clauses
print("\n3) WHEN / TARGET clauses")

sc = scene()
dead = kill(sc, sc["dying"].models[0])
check("a destroyed BATTLESUIT model with Deadly Demise qualifies", sc["fail_safe"].can_offer(dead))

# The WHEN clause is about the MODEL, so a non-Battlesuit death does not fire
# it. Granted Deadly Demise so it can only be failing on the BATTLESUIT half.
sc2 = scene(dying_sheet=STRIKE_TEAM)
other = grant_deadly_demise(sc2["dying"].models[0])     # constructed, isolates the keyword
kill(sc2, other)
check("a non-BATTLESUIT model does not, even with Deadly Demise",
      not other.profile.battlesuit and not sc2["fail_safe"].can_offer(other))

sc["cps"].cp["Player 1"] = 1
check("2 CP required", not sc["fail_safe"].can_offer(dead), "1 CP available")
sc["cps"].cp["Player 1"] = 4

# TARGET: "you can use this Stratagem on that unit even if that unit was just
# destroyed" - so an emptied-out unit must still be eligible. A Ghostkeel is a
# one-model unit, so this is the normal case rather than an edge one.
sc = scene()
only_model = sc["dying"].models[0]
kill(sc, only_model)
check("the unit really is wiped out", not sc["dying"].models)
check("a destroyed unit's model is still offered the stratagem (TARGET clause)",
      sc["fail_safe"].can_offer(only_model))

# Several models of the SAME unit dying together must ask once, not once each.
# Constructed: no real BATTLESUIT datasheet with Deadly Demise has more than
# one model, so this shape is currently unreachable in play - but the memo it
# guards is what keeps one weapon killing a whole team from prompting once per
# model, and that is worth keeping covered.
sc = scene(dying_sheet=CRISIS_STARSCYTHE)
models = [grant_deadly_demise(mdl) for mdl in sc["dying"].models]
kill(sc, *models)
opened = sum(1 for mdl in models if sc["fail_safe"].notify_destroyed(mdl))
check("three models of one unit dying together ask once", opened == 1, f"{opened} prompts")

# Rule 15.01: once per phase.
sc = scene()
dead = kill(sc, sc["dying"].models[0])
sc["fail_safe"].notify_destroyed(dead)
sc["decision"].choose(1)  # use it, forcing a 1 so nothing detonates
other_squad = build_squad(GHOSTKEEL_BATTLESUIT, "Player 1", name="1 Suits 2")
for i, mdl in enumerate(other_squad.models):
    mdl.x_in, mdl.y_in = 30.0 + i * 2.4, 20.0
    sc["state"].add_token(mdl)
second = other_squad.models[0]
kill(sc, second)
check("a second destroyed unit the same phase gets no offer", not sc["fail_safe"].can_offer(second))
sc["strat"].reset_phase()
sc["fail_safe"].reset_phase()
check("but does once the phase turns over", sc["fail_safe"].can_offer(second))


# =================================================================== summary
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for name in FAIL:
    print(f"  FAILED: {name}")
sys.exit(1 if FAIL else 0)
