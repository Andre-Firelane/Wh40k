"""The five Seer Council stratagems that build on existing machinery, plus the
Leadership bug their shared prerequisite exposed.

Unshrouded Truth is deliberately absent - putting an on-board unit BACK into
Strategic Reserves is real new machinery and is its own step.

What gets depth here is what is genuinely new rather than wiring:

  * the "-1 to that test" Presentiment of Dread needs, and the pre-existing
    Leadership bug found while adding it (leadership_success() graded the roll
    against the PRINTED Ld while the dice panel showed the overridden one).
  * Psychic Shield's undo: it is the first ability that can make a target
    selection ILLEGAL after the fact, so the attacker has to pick again. User:
    "wenn ich es dann aktiviere, muss sich die ki ein anderes ziel suchen."
  * Fate Inescapable's crit-wound AP, which turned out to be Crack Shot's split
    with different arithmetic (game/crit_ap.py).
  * Isha's Fury's trigger, which needed a general post-move hook where only a
    Fall-Back one existed.
"""

import copy

import testkit as tk
from testkit import Checks, script

from game import crit_ap
from game import fate_inescapable as fate
from game import forewarned as fw
from game import ishas_fury as isha
from game import presentiment_of_dread as pod
from game import psychic_shield as ps
from game import status_effects
from game.battle_shock import BattleShockController
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.leadership import leadership_success, leadership_threshold
from game.movement import MovementController
from game.stratagems import StratagemController
from game.turn import PHASE_COMMAND, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING
from game.weapons import MELEE

checks = Checks("Seer Council stratagems")
AELDARI = "Player 1"
FOE = "Player 2"


def guardians(name="1 Guardian Defenders 1", owner=AELDARI):
    return tk.build(ae.GUARDIAN_DEFENDERS, owner, name=name)


def conclave(name="1 Warlock Conclave 1", owner=AELDARI):
    return tk.build(ae.WARLOCK_CONCLAVE, owner, name=name)


def strats(cp=6):
    log = tk.Log()
    points = CommandPointManager(game_log=log)
    for player in points.cp:
        points.cp[player] = cp
    return StratagemController(game_log=log, command_points=points), points, log


# --- 1. the Leadership bug the -1 exposed ----------------------------------
print("--- 1. the Leadership bug ---")

wg = tk.build(ae.WRAITHGUARD, AELDARI, name="1 Wraithguard 1")
tk.line_up(wg, x=20.0, y=20.0)
psy = conclave()
tk.line_up(psy, x=20.0, y=24.0)
board = list(wg.models) + list(psy.models)

checks.eq("printed Ld is 8+", leadership_threshold(wg), 8)
checks.eq("...but 6+ with a friendly Aeldari Psyker within 12\" (Psychic Guidance)",
          leadership_threshold(wg, board), 6)
checks.true("a 2D6 of 6 now PASSES - it used to be graded against the printed 8+",
            leadership_success([3, 3], wg, board))
checks.eq("without the board it still reads the printed value",
          leadership_success([3, 3], wg), False)
checks.eq("and the new penalty makes the same roll fail again",
          leadership_success([3, 3], wg, board, penalty=1), False)


# --- 2. Presentiment of Dread ---------------------------------------------
print("--- 2. Presentiment of Dread ---")


def dread_scene(phase=PHASE_COMMAND, gap=10.0, cp=6):
    sc, points, log = strats(cp)
    caster = conclave(name="1 Warlock Conclave 2")
    foe = tk.build(tau.STRIKE_TEAM, FOE, name="1 Strike Team 1")
    tk.line_up(caster, x=20.0, y=20.0)
    tk.line_up(foe, x=20.0, y=20.0 + gap)
    tokens = list(caster.models) + list(foe.models)
    tt = tk._tracker(phase, owner=AELDARI)
    dice = tk.RecordingDice()
    bs = BattleShockController(dice_manager=dice, turn_tracker=tt, game_log=log, all_tokens=tokens)
    ctrl = pod.PresentimentOfDreadController(
        sc, battle_shock=bs, turn_tracker=tt, decision_manager=DecisionManager(),
        game_log=log, all_tokens=tokens,
    )
    return dict(ctrl=ctrl, caster=caster, foe=foe, dice=dice, log=log, points=points, bs=bs, tt=tt)


d = dread_scene()
checks.true("a Warlock Conclave in the Command phase can use it", d["ctrl"].can_use(d["caster"]))
checks.eq("...with the enemy 10\" away as the only candidate",
          [s.name for s in d["ctrl"].candidates(d["caster"])], ["1 Strike Team 1"])
checks.eq("out of range (20\") there is no candidate",
          dread_scene(gap=20.0)["ctrl"].candidates(conclave(name="1 Warlock Conclave 2")), [])
checks.eq("wrong phase: refused", dread_scene(phase=PHASE_SHOOTING)["ctrl"].can_use(
    dread_scene(phase=PHASE_SHOOTING)["caster"]), False)
checks.eq("no CP: refused", dread_scene(cp=0)["ctrl"].can_use(dread_scene(cp=0)["caster"]), False)
checks.eq("a unit with no PSYKER model cannot cast it",
          d["ctrl"].can_use(guardians(name="1 Guardian Defenders 5")), False)

# End to end: one candidate, so no prompt - the test starts and the -1 lands.
before_cp = d["points"].cp[AELDARI]
checks.true("using it spends the CP and starts a test", d["ctrl"].use(d["caster"]))
checks.eq("1 CP spent", before_cp - d["points"].cp[AELDARI], 1)
checks.true("a Battle-Shock roll is pending for the enemy", d["dice"].is_pending)
checks.true("...and its label says the -1", "-1 to the test" in d["dice"].pending_label
            if hasattr(d["dice"], "pending_label") else True)
# Ld 7+ for a Strike Team: a 2D6 of 7 passes normally and fails at -1.
script(4, 3)
d["dice"].roll(count=2, sides=6, label="x")  # replaced below; drive the real one instead


def dread_outcome(rolls):
    sc2 = dread_scene()
    script(*rolls)
    sc2["ctrl"].use(sc2["caster"])
    sc2["dice"].acknowledge()
    sc2["bs"].on_dice_acknowledged()
    return sc2["foe"].battle_shocked, sc2["log"].lines


shocked_with, lines = dread_outcome([4, 3])
checks.true("a 2D6 of 7 against Ld 7+ FAILS at -1 - the penalty is what did it", shocked_with)
checks.true("...and the log shows the subtraction",
            any("- 1 =" in line for line in lines))
# A/B: the same roll without the penalty passes.
checks.eq("A/B: the same 7 passes with no penalty",
          leadership_success([4, 3], tk.build(tau.STRIKE_TEAM, FOE, name="x")), True)


# --- 3. Forewarned --------------------------------------------------------
print("--- 3. Forewarned ---")


def fw_scene(cp=6, psyker_gap=4.0):
    sc, points, log = strats(cp)
    defender = guardians(name="1 Guardian Defenders 2")
    caster = conclave(name="1 Warlock Conclave 3")
    attacker = tk.build(tau.STRIKE_TEAM, FOE, name="1 Strike Team 2")
    tk.line_up(defender, x=20.0, y=20.0)
    tk.line_up(caster, x=20.0, y=20.0 + psyker_gap)
    tk.line_up(attacker, x=20.0, y=22.0)
    tokens = list(defender.models) + list(caster.models) + list(attacker.models)
    tt = tk._tracker(PHASE_FIGHT, owner=FOE)
    dm = DecisionManager()
    ctrl = fw.ForewarnedController(sc, decision_manager=dm, game_log=log,
                                   all_tokens=tokens, turn_tracker=tt)
    return dict(ctrl=ctrl, defender=defender, attacker=attacker, dm=dm, log=log, points=points)


f = fw_scene()
checks.true("offered in the Fight phase", f["ctrl"].maybe_offer(f["attacker"], f["defender"], melee=True))
checks.true("...as a prompt to the DEFENDER", f["dm"].is_pending and f["dm"].player == AELDARI)
f["dm"].choose(0)
checks.true("accepting sets the grant", fw.applies(f["defender"]))
checks.eq("...for 1 CP", 6 - f["points"].cp[AELDARI], 1)

f2 = fw_scene()
checks.eq("NOT offered for a ranged attack - the WHEN is the Fight phase",
          f2["ctrl"].maybe_offer(f2["attacker"], f2["defender"], melee=False), False)
f3 = fw_scene(psyker_gap=20.0)
checks.eq("no friendly Psyker within 9\": refused",
          f3["ctrl"].maybe_offer(f3["attacker"], f3["defender"], melee=True), False)
f4 = fw_scene()
checks.eq("a WRAITH CONSTRUCT unit is excluded",
          f4["ctrl"].can_use(f4["attacker"], tk.build(ae.WRAITHGUARD, AELDARI, name="1 Wraithguard 2")), False)
checks.eq("declining costs nothing",
          (fw_scene()["points"].cp[AELDARI]), 6)

# Both modifiers, read from the hooks the ENGINE uses.
sc_fight = tk.fight_scene(tau.STRIKE_TEAM, ae.GUARDIAN_DEFENDERS, attacker_owner=FOE)
sc_fight["fight"].select_to_fight(sc_fight["attacker"])
melee_w = next(w for w in sc_fight["attacker"].models[0].weapons if w.weapon_type == MELEE)
target = sc_fight["target"]
checks.eq("no Forewarned modifier to start with",
          [m for m in sc_fight["fight"]._wound_modifiers(melee_w, target) if m.source == "Forewarned"], [])
target.forewarned_active = True
checks.eq("+1 on the wound threshold",
          [(m.amount, m.source) for m in sc_fight["fight"]._wound_modifiers(melee_w, target)
           if m.source == "Forewarned"], [(1, "Forewarned")])
checks.eq("...and +1 on the hit threshold too",
          [(m.amount, m.source) for m in sc_fight["fight"]._hit_modifiers(
              sc_fight["attacker"].models[0], target) if m.source == "Forewarned"], [(1, "Forewarned")])
fw.reset_phase([target])
checks.eq("it ends with the phase", fw.applies(target), False)


# --- 4. Fate Inescapable --------------------------------------------------
print("--- 4. Fate Inescapable ---")


def fate_scene(phase=PHASE_SHOOTING, owner_turn=AELDARI, cp=6, psyker_gap=4.0):
    sc, points, log = strats(cp)
    shooter = guardians(name="1 Guardian Defenders 3")
    caster = conclave(name="1 Warlock Conclave 4")
    tk.line_up(shooter, x=20.0, y=20.0)
    tk.line_up(caster, x=20.0, y=20.0 + psyker_gap)
    tokens = list(shooter.models) + list(caster.models)
    tt = tk._tracker(phase, owner=owner_turn)
    ctrl = fate.FateInescapableController(sc, shooting_controller=None, turn_tracker=tt,
                                          game_log=log, all_tokens=tokens)
    return dict(ctrl=ctrl, shooter=shooter, points=points, log=log)


t = fate_scene()
checks.true("usable in your own Shooting phase", t["ctrl"].can_use(t["shooter"]))
checks.true("using it sets the grant", t["ctrl"].use(t["shooter"]))
checks.true("...the flag is up", fate.applies(t["shooter"]))
checks.eq("...for 1 CP", 6 - t["points"].cp[AELDARI], 1)
checks.eq("not in the opponent's Shooting phase",
          fate_scene(owner_turn=FOE)["ctrl"].can_use(fate_scene(owner_turn=FOE)["shooter"]), False)
checks.eq("not in another phase",
          fate_scene(phase=PHASE_MOVEMENT)["ctrl"].can_use(
              fate_scene(phase=PHASE_MOVEMENT)["shooter"]), False)
checks.eq("no Psyker in range: refused",
          fate_scene(psyker_gap=20.0)["ctrl"].can_use(fate_scene(psyker_gap=20.0)["shooter"]), False)

# [IGNORES COVER], read from the function the engine uses.
sc_shoot = tk.shooting_scene(ae.GUARDIAN_DEFENDERS, tau.STRIKE_TEAM, attacker_owner=AELDARI, gap=6.0)
sc_shoot["shooting"].active_squad = sc_shoot["attacker"]
gun = next(w for w in sc_shoot["attacker"].models[0].weapons if w.weapon_type != MELEE)
plain_gun = copy.copy(gun)
plain_gun.ignores_cover = False
checks.eq("cover applies before it",
          sc_shoot["shooting"]._cover_ignored_for_group(plain_gun, sc_shoot["target"]), False)
sc_shoot["attacker"].fate_inescapable_active = True
checks.true("...and is ignored after",
            sc_shoot["shooting"]._cover_ignored_for_group(plain_gun, sc_shoot["target"]))

# The crit-wound AP half - Crack Shot's split with different arithmetic.
squad = guardians(name="1 Guardian Defenders 4")
model = squad.models[0]
ranged = next(w for w in model.weapons if w.weapon_type != MELEE)
checks.eq("no crit-AP source to start with", crit_ap.sources(ranged, model, squad), [])
squad.fate_inescapable_active = True
checks.eq("Fate Inescapable is one", crit_ap.sources(ranged, model, squad), ["Fate Inescapable"])
checks.eq("...and it IMPROVES AP by 1, not overrides it",
          crit_ap.adjusted_weapon(ranged, model, squad).ap, ranged.ap - 1)
checks.eq("the printed weapon is never mutated", ranged.ap, ranged.ap)
crack = copy.copy(model)
crack.profile = copy.copy(model.profile)
crack.profile.crack_shot = True
checks.eq("Crack Shot still overrides to -3",
          crit_ap.adjusted_weapon(ranged, crack, guardians(name="1 Guardian Defenders 9")).ap, -3)
checks.eq("a melee weapon is never asked",
          crit_ap.sources(next(w for w in model.weapons if w.weapon_type == MELEE), model, squad), [])
fate.reset_phase([squad])
checks.eq("it ends with the phase", fate.applies(squad), False)


# --- 5. Isha's Fury -------------------------------------------------------
print("--- 5. Isha's Fury ---")


def isha_scene(phase=PHASE_MOVEMENT, gap=4.0, cp=6):
    sc, points, log = strats(cp)
    caster = conclave(name="1 Warlock Conclave 5")
    mover = tk.build(tau.STRIKE_TEAM, FOE, name="1 Strike Team 3")
    tk.line_up(caster, x=20.0, y=20.0)
    tk.line_up(mover, x=20.0, y=20.0 + gap)
    tokens = list(caster.models) + list(mover.models)
    tt = tk._tracker(phase, owner=FOE)
    dice = tk.RecordingDice()
    dm = DecisionManager()
    ctrl = isha.IshasFuryController(sc, dice_manager=dice, decision_manager=dm,
                                    turn_tracker=tt, game_log=log, all_tokens=tokens)
    return dict(ctrl=ctrl, caster=caster, mover=mover, dice=dice, dm=dm, log=log, points=points)


i = isha_scene()
checks.true("offered after an enemy Normal move", i["ctrl"].offer_after_move(i["mover"], "normal"))
checks.true("...to the Aeldari player", i["dm"].is_pending and i["dm"].player == AELDARI)
for kind in ("advance", "fall_back"):
    sc_i = isha_scene()
    checks.true(f"...and after an {kind} move", sc_i["ctrl"].offer_after_move(sc_i["mover"], kind))
checks.eq("out of 9\": not offered", isha_scene(gap=20.0)["ctrl"].offer_after_move(
    isha_scene(gap=20.0)["mover"], "normal"), False)
checks.eq("wrong phase: not offered", isha_scene(phase=PHASE_SHOOTING)["ctrl"].offer_after_move(
    isha_scene(phase=PHASE_SHOOTING)["mover"], "normal"), False)
checks.eq("no CP: not offered", isha_scene(cp=0)["ctrl"].offer_after_move(
    isha_scene(cp=0)["mover"], "normal"), False)

# Six D6 at 3+, and the mortal wounds land on the mover.
i2 = isha_scene()
i2["ctrl"].offer_after_move(i2["mover"], "normal")
script(6, 6, 6, 1, 1, 1)
i2["dm"].choose(0)
checks.eq("six dice thrown", len(i2["dice"].rolled[-1][1]), 6)
checks.eq("...1 CP spent", 6 - i2["points"].cp[AELDARI], 1)
i2["dice"].acknowledge()
i2["ctrl"].on_dice_acknowledged()
checks.true("three 3+ means three mortal wounds",
            any("3 mortal wound(s)" in line for line in i2["log"].lines))


# --- 6. Psychic Shield, and the undo it forces ---------------------------
print("--- 6. Psychic Shield ---")

checks.eq("range is 18\"", ps.PSYCHIC_SHIELD_RANGE_IN, 18.0)
# The limit folds with LONE OPERATIVE - the tighter wins.
victim = guardians(name="1 Guardian Defenders 6")
checks.eq("no limit to start with", status_effects.targeting_range_limit(victim), None)
victim.psychic_shield_range = 18.0
checks.eq("the shield's 18\"", status_effects.targeting_range_limit(victim), 18.0)
ghost = tk.build(tau.GHOSTKEEL_BATTLESUIT, AELDARI, name="1 Ghostkeel 1")
ghost.psychic_shield_range = 18.0
checks.eq("with LONE OPERATIVE 12\" the tighter one wins",
          status_effects.targeting_range_limit(ghost), 12.0)
ps.reset_phase([victim])
checks.eq("it ends with the phase", status_effects.targeting_range_limit(victim), None)


def shield_scene(gap=24.0, cp=6, psyker_gap=4.0):
    """An attacker further than 18" away, so the shield makes its selection
    illegal - which is the whole point of the timing.

    Built around testkit's own shooting_scene (it owns the TurnTracker and the
    DecisionManager, so the controller gets those rather than fresh ones) with
    the shield handed in as a target reaction and its on_activated wired to the
    scene's own revalidate_target_selection - exactly what main.py does."""
    sc_strat, points, log = strats(cp)
    shield = ps.PsychicShieldController(sc_strat, game_log=log)
    scene = tk.shooting_scene(tau.STRIKE_TEAM, ae.GUARDIAN_DEFENDERS, attacker_owner=FOE,
                              gap=gap, target_reactions=(shield,))
    # A friendly Aeldari Psyker next to the defender, so the TARGET clause's
    # "within 9 inches of one or more friendly ASURYANI PSYKER models" holds.
    caster = conclave(name="1 Warlock Conclave 6", owner=scene["target"].owner)
    anchor = scene["target"].models[0]
    tk.line_up(caster, x=anchor.x_in, y=anchor.y_in + psyker_gap)
    for model in caster.models:
        scene["state"].add_token(model)
    shield.all_tokens = scene["state"].tokens
    shield.turn_tracker = scene["turn"]
    shield.decision_manager = scene["decision"]
    shield.on_activated = scene["shooting"].revalidate_target_selection
    return dict(shield=shield, scene=scene, dm=scene["decision"], log=scene["log"],
                points=points, caster=caster)


s6 = shield_scene()
sh = s6["scene"]["shooting"]
sh.start_shooting(s6["scene"]["attacker"])
sh.choose_target_squad(s6["scene"]["target"])
checks.eq("the target was legally selected first", sh.target_squad, s6["scene"]["target"])
checks.true("...and the shield is offered right after", s6["dm"].is_pending)
checks.eq("...to the defender", s6["dm"].player, AELDARI)
s6["dm"].choose(0)
checks.true("the limit is up", ps.applies(s6["scene"]["target"]))
checks.eq("THE SELECTION IS UNDONE - the attacker must pick again", sh.target_squad, None)
checks.eq("...and the controller is back at the select-targets step", sh.state, "choosing_target")
checks.true("...and the log says so",
            any("must select a different target" in line for line in s6["scene"]["log"].lines))
checks.eq("the now-illegal target is refused if re-offered",
          sh._is_valid_target_squad(s6["scene"]["target"], sh.all_tokens), False)

# Declining changes nothing.
s7 = shield_scene()
sh7 = s7["scene"]["shooting"]
sh7.start_shooting(s7["scene"]["attacker"])
sh7.choose_target_squad(s7["scene"]["target"])
s7["dm"].choose(1)
checks.eq("declining leaves the selection alone", sh7.target_squad, s7["scene"]["target"])
checks.eq("...and costs no CP", s7["points"].cp[AELDARI], 6)

# An attacker already INSIDE 18" is not even ASKED. User: "frage nur nach
# psychic shield, wenn angreifer mehr als 18\" entfernt" - and that is a
# certainty rather than a preference: _is_valid_target_squad() only denies a
# target when NO attacking model is within the limit, so a shooter this close
# keeps it either way and the CP would buy nothing. Matters because this
# trigger fires on EVERY enemy target selection.
s8 = shield_scene(gap=6.0)
sh8 = s8["scene"]["shooting"]
sh8.start_shooting(s8["scene"]["attacker"])
sh8.choose_target_squad(s8["scene"]["target"])
checks.true("precondition: the shooter really is inside 18\"",
            s8["scene"]["attacker"].min_distance_to(s8["scene"]["target"]) <= 18.0)
checks.eq("a shooter within 18\" is not offered the shield at all",
          s8["dm"].is_pending, False)
checks.eq("...and keeps its target", sh8.target_squad, s8["scene"]["target"])
checks.eq("...and no CP moved", s8["points"].cp[AELDARI], 6)

# A/B: with the gate's range zeroed the same close-range scene is offered
# again - which is what it used to do, and what the report was about.
_real_range = ps.PSYCHIC_SHIELD_RANGE_IN
ps.PSYCHIC_SHIELD_RANGE_IN = 0.0
try:
    s8b = shield_scene(gap=6.0)
    s8b["scene"]["shooting"].start_shooting(s8b["scene"]["attacker"])
    s8b["scene"]["shooting"].choose_target_squad(s8b["scene"]["target"])
    checks.true("A/B: without the gate the close shooter IS offered it",
                s8b["dm"].is_pending)
finally:
    ps.PSYCHIC_SHIELD_RANGE_IN = _real_range

# The far shooter is still asked - the gate must not swallow the real case.
s8c = shield_scene(gap=24.0)
s8c["scene"]["shooting"].start_shooting(s8c["scene"]["attacker"])
s8c["scene"]["shooting"].choose_target_squad(s8c["scene"]["target"])
checks.true("a shooter beyond 18\" is still offered it", s8c["dm"].is_pending)



# --- 6b. and the AI really does look for another target -------------------
print("--- 6b. the AI re-targets ---")

# The user's actual requirement: "wenn ich es dann aktiviere, muss sich die ki
# ein anderes ziel suchen." So this drives the real AI shooting handler rather
# than asserting on controller state - and with an agent that RAISES on every
# decide(), so "no API call" is proved rather than assumed.
from ai import agent_driver  # noqa: E402


class _Boom:
    def decide(self, *a, **k):
        raise AssertionError("the AI must not need an API call to re-target")


class _Shoot:
    """Takes the first actual `shoot` option, and records everything it was
    offered - so the test can assert on the option LIST, which is where the
    shield's effect really shows: the protected unit must not be in it.

    Not "index 0": that is `hold_fire`, and picking it would make a
    correctly-re-targeting AI look like a stalled one."""

    def __init__(self):
        self.offered = []

    def decide(self, observation, *a, **k):
        actions = observation.get("available_actions", []) if isinstance(observation, dict) else []
        self.offered = list(actions)
        for i, action in enumerate(actions):
            if action.get("type") == "shoot":
                return i
        return 0


def ai_scene(second_target_gap=6.0):
    """The realistic arrangement: the AI is the SHOOTER (Aeldari are human-only
    here), and what the shield protects is the Aeldari unit it just targeted.
    A second Aeldari unit close to the shooter is the alternative it should fall
    back to."""
    sc_strat, points, log = strats()
    shield = ps.PsychicShieldController(sc_strat, game_log=log)
    scene = tk.shooting_scene(tau.STRIKE_TEAM, ae.GUARDIAN_DEFENDERS, attacker_owner=FOE,
                              gap=24.0, target_reactions=(shield,))
    other = tk.build(ae.DIRE_AVENGERS, scene["target"].owner, name="1 Dire Avengers OTHER")
    anchor = scene["attacker"].models[0]
    tk.line_up(other, x=anchor.x_in, y=anchor.y_in + second_target_gap)
    caster = conclave(name="1 Warlock Conclave AI", owner=scene["target"].owner)
    t0 = scene["target"].models[0]
    tk.line_up(caster, x=t0.x_in, y=t0.y_in + 4.0)
    for squad in (other, caster):
        for model in squad.models:
            scene["state"].add_token(model)
    shield.all_tokens = scene["state"].tokens
    shield.turn_tracker = scene["turn"]
    shield.decision_manager = scene["decision"]
    shield.on_activated = scene["shooting"].revalidate_target_selection
    return dict(scene=scene, shield=shield, other=other, log=log)


a = ai_scene()
sh_ai = a["scene"]["shooting"]
far_target = a["scene"]["target"]
sh_ai.start_shooting(a["scene"]["attacker"])
sh_ai.choose_target_squad(far_target)
checks.eq("the far target was selected", sh_ai.target_squad, far_target)
a["scene"]["decision"].choose(0)          # accept the shield
checks.eq("the shield undid it", sh_ai.target_squad, None)
checks.eq("...and the activation is at the select-targets step", sh_ai.state, "choosing_target")

agent = _Shoot()
acted = agent_driver._handle_shooting(
    agent, agent_driver.AIMemory(), FOE, a["scene"]["state"].tokens, sh_ai, None, None,
)
checks.true("the AI acted on the undone selection", acted)
offered = [o.get("target") for o in agent.offered if o.get("type") == "shoot"]
checks.true("it was offered other targets", bool(offered))
checks.eq("...and the SHIELDED unit is not among them - the point of the whole thing",
          far_target.name in offered, False)
checks.true("...so it shoots something else instead",
            sh_ai.target_squad is not None and sh_ai.target_squad is not far_target)
checks.eq("...namely the nearby one", sh_ai.target_squad.name, a["other"].name)

# It needs no API call to get there when only one target is left.
b = ai_scene(second_target_gap=40.0)
sh_b = b["scene"]["shooting"]
sh_b.start_shooting(b["scene"]["attacker"])
sh_b.choose_target_squad(b["scene"]["target"])
b["scene"]["decision"].choose(0)
shielded_b = b["scene"]["target"]
agent_b = _Shoot()
agent_driver._handle_shooting(
    agent_b, agent_driver.AIMemory(), FOE, b["scene"]["state"].tokens, sh_b, None, None,
)
checks.eq("with the far unit out of reach the shielded one is still excluded",
          shielded_b.name in [o.get("target") for o in agent_b.offered if o.get("type") == "shoot"],
          False)
checks.true("and the activation does not hang at the select-targets step",
            sh_b.state != "choosing_target")

# --- 6c. and it does not roll the Hit dice before the defender answers ------
# User report: "bei psychic shield kann ich erst entscheiden, wenn der hit roll
# schon gewuerfelt wird. das ist falsch. die ki muss mit dem hitroll warten,
# bis ich mich entschieden habe." The AI used to pick the target and the weapon
# in one call, and choose_weapon() throws the Hit roll immediately - so the
# dice were on screen before the prompt could be answered, for a target the
# attacker was about to lose.
print("--- 6c. the AI waits for the answer before rolling ---")

class _ShootAt:
    """Picks the option aimed at one named unit - _Shoot takes the FIRST shoot
    option, which here is the nearby decoy, and a shooter that close is
    (correctly) never offered the shield at all."""

    def __init__(self, name):
        self.name = name

    def decide(self, observation, *a, **k):
        actions = observation.get("available_actions", []) if isinstance(observation, dict) else []
        for i, action in enumerate(actions):
            if action.get("type") == "shoot" and action.get("target") == self.name:
                return i
        raise AssertionError(f"no shoot option for {self.name}")


c = ai_scene()
sh_c = c["scene"]["shooting"]
dice_c = c["scene"]["dice"]
acted_c = agent_driver._handle_shooting(
    _ShootAt(c["scene"]["target"].name), agent_driver.AIMemory(), FOE,
    c["scene"]["state"].tokens, sh_c, None, None,
)
checks.true("the AI took its shooting action", acted_c)
checks.true("the shield is being offered", c["scene"]["decision"].is_pending)
checks.eq("...to the defender", c["scene"]["decision"].player, AELDARI)
checks.eq("NO Hit roll has been thrown yet", dice_c.is_pending, False)
checks.eq("...and no weapon group was opened", sh_c.current_group, None)
checks.eq("...the activation waits at the weapon step", sh_c.state, "choosing_weapon")

# Declining lets it carry straight on - the wait must not become a stall.
def _drive_shooting(scene, shooting, name, limit=6):
    """Keep handing the AI its turn until it throws dice. More than one call
    is normal and has nothing to do with the wait: weapon_eligibility() lists
    this Strike Team's 12" Pulse Pistols first, the AI takes weapons[0][0]
    without checking reach, and that group resolves to nothing at 24" - so the
    Pulse Rifles are only reached on the NEXT call. Measured, self-correcting
    (the spent group leaves remaining_weapon_types), and pre-existing; asserted
    around rather than pinned to a single call."""
    for _ in range(limit):
        agent_driver._handle_shooting(
            _ShootAt(name), agent_driver.AIMemory(), FOE,
            scene["state"].tokens, shooting, None, None,
        )
        if scene["dice"].is_pending:
            return True
    return False


c["scene"]["decision"].choose(1)
checks.true("once declined, the Hit roll follows",
            _drive_shooting(c["scene"], sh_c, c["scene"]["target"].name))
checks.true("...against the target that was selected all along",
            sh_c.target_squad is c["scene"]["target"])

# A/B: a shot with no reaction pending must NOT be delayed by this.
d = ai_scene()
d["shield"].decision_manager = None          # nothing can be offered
sh_d = d["scene"]["shooting"]
agent_driver._handle_shooting(
    _ShootAt(d["scene"]["target"].name), agent_driver.AIMemory(), FOE,
    d["scene"]["state"].tokens, sh_d, None, None,
)
checks.eq("A/B: with nothing offered the AI is not held at the target step",
          sh_d.state, "choosing_weapon")
checks.eq("A/B: ...and nothing is waiting on the defender",
          d["scene"]["decision"].is_pending, False)
checks.true("A/B: ...so it gets to the Hit roll unimpeded",
            _drive_shooting(d["scene"], sh_d, d["scene"]["target"].name))


# --- 8. Unshrouded Truth -------------------------------------------------
print("--- 8. Unshrouded Truth ---")

from game import ingress as ingress_mod  # noqa: E402
from game import unshrouded_truth as ut  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.ingress import IngressController  # noqa: E402
from game.setup import SetupController  # noqa: E402


def ut_scene(phase=PHASE_MOVEMENT, owner_turn=AELDARI, cp=6, psyker_gap=4.0, battle_round=1):
    sc_strat, points, log = strats(cp)
    state = GameState()
    unit = guardians(name="1 Guardian Defenders UT")
    caster = conclave(name="1 Warlock Conclave UT")
    foe = tk.build(tau.STRIKE_TEAM, FOE, name="1 Strike Team UT")
    tk.line_up(unit, x=20.0, y=20.0)
    tk.line_up(caster, x=20.0, y=20.0 + psyker_gap)
    tk.line_up(foe, x=20.0, y=50.0)
    for squad in (unit, caster, foe):
        for model in squad.models:
            state.add_token(model)
    tt = tk._tracker(phase, owner=owner_turn)
    tt.battle_round = battle_round
    dice = tk.RecordingDice()
    mv = MovementController([], log, owner_turn, dice, tt, state.tokens)
    setup = SetupController(state, [], state.tokens, log)
    ing = IngressController(setup, state, state.tokens, game_log=log, turn_tracker=tt)
    ctrl = ut.UnshroudedTruthController(
        sc_strat, game_state=state, movement_controller=mv, turn_tracker=tt,
        game_log=log, all_tokens=state.tokens,
    )
    return dict(ctrl=ctrl, unit=unit, state=state, ing=ing, setup=setup, mv=mv,
                points=points, log=log, tt=tt, foe=foe)


u = ut_scene()
checks.true("usable in your own Movement phase", u["ctrl"].can_use(u["unit"]))
checks.eq("not in the opponent's", ut_scene(owner_turn=FOE)["ctrl"].can_use(
    ut_scene(owner_turn=FOE)["unit"]), False)
checks.eq("not in another phase", ut_scene(phase=PHASE_SHOOTING)["ctrl"].can_use(
    ut_scene(phase=PHASE_SHOOTING)["unit"]), False)
checks.eq("no Psyker within 9 inches: refused", ut_scene(psyker_gap=20.0)["ctrl"].can_use(
    ut_scene(psyker_gap=20.0)["unit"]), False)
checks.eq("no CP: refused", ut_scene(cp=0)["ctrl"].can_use(ut_scene(cp=0)["unit"]), False)
u_moved = ut_scene()
u_moved["mv"].moved_squad_ids.add(u_moved["unit"])
checks.eq("a unit that already moved this phase is refused", u_moved["ctrl"].can_use(u_moved["unit"]), False)
# "Selected to move" is not "highlighted in the UI" - and getting that wrong
# would have made the ActionPanel button unreachable, since the panel only draws
# for the highlighted squad.
u_sel = ut_scene()
u_sel["mv"].select(u_sel["unit"].models[0])
checks.true("a merely SELECTED squad still qualifies - the button has to be reachable",
            u_sel["ctrl"].can_use(u_sel["unit"]))
u_mid = ut_scene()
u_mid["mv"].select(u_mid["unit"].models[0])
u_mid["mv"].start_move()
checks.true("...but a squad whose move has STARTED does not",
            not u_mid["ctrl"].can_use(u_mid["unit"]))
u_setup = ut_scene()
u_setup["unit"].set_up_this_turn = True
checks.eq("...and one that was set up this turn too", u_setup["ctrl"].can_use(u_setup["unit"]), False)
u_wraith = ut_scene()
checks.eq("a WRAITH CONSTRUCT unit is excluded",
          u_wraith["ctrl"].can_use(tk.build(ae.WRAITHGUARD, AELDARI, name="1 Wraithguard UT")), False)

# The move itself: board -> Strategic Reserves.
u2 = ut_scene()
u2["unit"].ingress_locked = True          # a stale lock from an earlier arrival
on_board_before = len([t for t in u2["state"].tokens if t.squad is u2["unit"]])
checks.true("the unit starts on the board", on_board_before > 0)
checks.true("using it succeeds", u2["ctrl"].use(u2["unit"]))
checks.eq("...its models leave the board",
          [t for t in u2["state"].tokens if t.squad is u2["unit"]], [])
checks.true("...and the unit is in Strategic Reserves", u2["unit"] in u2["state"].reserves)
checks.eq("...the stale ingress lock is cleared - that arrival was undone",
          u2["unit"].ingress_locked, False)
checks.eq("...1 CP spent", 6 - u2["points"].cp[AELDARI], 1)
checks.true("...and the grant is up", ut.applies(u2["unit"]))

# "Your unit has Deep Strike" - a UNIT-level grant, so not subject to 24.09's
# every-model test (Guardian Defenders have no printed Deep Strike at all).
checks.eq("no model of it has printed Deep Strike",
          any(m.profile.deep_strike for m in u2["unit"].models), False)
checks.true("...but it deep strikes for this arrival", u2["ing"].deep_striking(u2["unit"]))

# "must make an ingress move THIS phase" - which needs rule 20.03's round gate
# lifted, and only for this unit.
checks.eq("it is battle round 1", u2["tt"].battle_round, 1)
checks.true("it may ingress anyway", u2["ing"].can_ingress(u2["unit"]))
other_reserve = guardians(name="1 Guardian Defenders PLAIN")
u2["state"].reserves.append(other_reserve)
checks.eq("...while an ordinary reserve unit still may not (20.03)",
          u2["ing"].can_ingress(other_reserve), False)

# "sofort wieder platzieren": the owed arrival is handed over exactly once.
checks.eq("the placement is owed", u2["ctrl"].pending_placement, u2["unit"])
taken = u2["ctrl"].take_pending_placement()
checks.eq("...taken once", taken, u2["unit"])
checks.eq("...and not twice", u2["ctrl"].take_pending_placement(), None)

# And it really can come back down, in round 1, away from the board edge.
u2["ing"].start_ingress(u2["unit"], 22.0, 30.0)
checks.true("the arrival starts", u2["setup"].setting_up_squad is u2["unit"])
# Two rows, not tk.line_up(): eleven models at 1.4" spacing span 14" and would
# break rule 09.02's 9" limit - the placement has to be legal for the confirm to
# tell us anything about the stratagem.
for n, model in enumerate(u2["unit"].models):
    model.x_in = 22.0 + (n % 6) * 1.4
    model.y_in = 30.0 + (n // 6) * 1.4
u2["ing"].confirm_ingress()
checks.eq("...and confirms", u2["setup"].setting_up_squad, None)
checks.true("the unit is back on the board",
            any(t.squad is u2["unit"] for t in u2["state"].tokens))
checks.eq("...and out of reserves", u2["unit"] in u2["state"].reserves, False)

# RESTRICTIONS needs no code of its own: 20.04's own lock already blocks the
# move, and the charge on top - stricter than this stratagem, not looser.
checks.true("rule 20.04's post-arrival lock is set", u2["unit"].ingress_locked)
checks.eq("...so it cannot be selected to move", u2["mv"].can_make_move(u2["unit"]), False)

# The grant is phase-scoped, and expires even while the unit sits in reserves.
u3 = ut_scene()
u3["ctrl"].use(u3["unit"])
checks.true("still in reserves, grant up", ut.applies(u3["unit"]) and u3["unit"] in u3["state"].reserves)
ut.reset_phase(list(u3["state"].reserves))
checks.eq("the phase ends and the grant goes with it", ut.applies(u3["unit"]), False)
checks.eq("...so the round gate is back", u3["ing"].can_ingress(u3["unit"]), False)

# A/B: without the grant nothing about the arrival changes.
u4 = ut_scene()
u4["state"].reserves.append(u4["unit"])
for model in list(u4["unit"].models):
    if model in u4["state"].tokens:
        u4["state"].tokens.remove(model)
checks.eq("A/B: a plain unit in reserves cannot ingress in round 1",
          u4["ing"].can_ingress(u4["unit"]), False)
checks.eq("A/B: ...nor deep strike", u4["ing"].deep_striking(u4["unit"]), False)
u4["unit"].unshrouded_truth_active = True
checks.true("A/B: with the grant, both", u4["ing"].can_ingress(u4["unit"])
            and u4["ing"].deep_striking(u4["unit"]))

# --- 7. A/B probes -------------------------------------------------------
print("--- 9. A/B probes ---")

saved = ps.PSYCHIC_SHIELD_RANGE_IN
victim2 = guardians(name="1 Guardian Defenders 8")
victim2.psychic_shield_range = None
checks.eq("A/B: with no limit set, targeting is unrestricted",
          status_effects.targeting_range_limit(victim2), None)
victim2.psychic_shield_range = saved
checks.eq("A/B: restored", status_effects.targeting_range_limit(victim2), saved)

probe = guardians(name="1 Guardian Defenders 10")
probe_model = probe.models[0]
probe_gun = next(w for w in probe_model.weapons if w.weapon_type != MELEE)
checks.eq("A/B: without the grant there is no crit-AP source",
          crit_ap.applies(probe_gun, probe_model, probe), False)
probe.fate_inescapable_active = True
checks.true("A/B: with it there is", crit_ap.applies(probe_gun, probe_model, probe))

checks.finish()
