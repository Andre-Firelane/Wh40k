"""Split Fire: the option NOT to shoot/attack with a weapon.

User report: "bei Split fire brauche ich noch die Option, mit einer Waffe
nicht zu schiessen, denn hat eine Waffe kein Ziel, laufe ich derzeit beim
Assignment in eine Sackgasse und es geht nicht weiter."

Two separate things are checked here, and only the first one is what was
asked for:

  * skip_current()/finish_assignment() - the deliberate choice to leave a
    weapon unfired (rule 04.01, "one or more" weapons). The non-split flow
    has had stop_shooting() for this all along; split fire had nothing.
  * _prune_unassignable() - a weapon with NO legal target is dropped before
    the player is ever asked about it, so the reported dead end cannot
    happen in the first place rather than merely being escapable.

Every "the fix works" check has an A/B probe that puts the pre-fix world
back (prune neutralised), because a green run against a scene that simply
never hits the dead end would prove nothing.
"""

import contextlib

import testkit as tk
from game import fight as fight_mod
from game import shooting as shooting_mod
from game.factions import orks, tau_empire as tau
from game.squad import model_engaged_with

c = tk.Checks("Split Fire: skip a weapon")


def check(label, condition, detail=None):
    """tk.Checks.true() with an optional value appended to the failure line."""
    ok = c.true(label, condition)
    if not ok and detail is not None:
        c.failures[-1] += " [%r]" % (detail,)
    return ok


@contextlib.contextmanager
def no_prune(cls):
    """The pre-fix world: the assignment queue is never pruned, so a weapon
    with no legal target sits at its front forever."""
    original = cls._prune_unassignable
    cls._prune_unassignable = lambda self: None
    try:
        yield
    finally:
        cls._prune_unassignable = original


def shooting_at(gap):
    s = tk.shooting_scene(tau.STRIKE_TEAM, orks.BOYZ, gap=gap)
    sc = s["shooting"]
    sc.start_shooting(s["attacker"])
    sc.choose_shooting_type(shooting_mod.NORMAL_SHOOTING)
    sc.toggle_split_fire()
    return s


# ---------------------------------------------------------------- scene
# The reported shape: a unit whose models each carry two ranged weapons of
# very different range, activating at a distance only one of them covers.
s = shooting_at(20.0)
att, tgt = s["attacker"], s["target"]
ranges = sorted({w.range_in for m in att.models for w in m.weapons if w.weapon_type == "ranged"})
check("scene: the unit carries weapons of two different ranges", len(ranges) >= 2, ranges)
check("scene: the shorter one cannot reach at this distance", ranges[0] < 20.0, ranges[0])
check("scene: the longer one can", ranges[-1] >= 20.0, ranges[-1])


# ------------------------------------------------- 1. the reported dead end
with no_prune(shooting_mod.ShootingController):
    s0 = shooting_at(20.0)
    sc0, tgt0 = s0["shooting"], s0["target"]
    sc0.begin_assignment()
    queued_before = len(sc0.assignment_queue)
    frozen_on = None
    for _ in range(80):
        cur = sc0.current_assignment()
        if cur is None:
            break
        before = len(sc0.assignment_queue)
        sc0.assign_current(tgt0)
        if len(sc0.assignment_queue) == before:
            frozen_on = cur
            break
    check("A/B pre-fix: every weapon is queued, in range or not", queued_before == 20, queued_before)
    check("A/B pre-fix: the queue freezes on an out-of-range weapon",
            frozen_on is not None and frozen_on[1].range_in == ranges[0],
            frozen_on[1].name if frozen_on else None)
    check("A/B pre-fix: the board highlights nothing to click",
            len(sc0.valid_target_models(s0["state"].tokens)) == 0)
    check("A/B pre-fix: still stuck in ASSIGNING", sc0.state == shooting_mod.ASSIGNING, sc0.state)
    sc0.stop_shooting()
    check("A/B pre-fix: stop_shooting() is no escape - wrong state",
            sc0.state == shooting_mod.ASSIGNING, sc0.state)


# --------------------------------- 2. the prune: unreachable weapons dropped
s1 = shooting_at(20.0)
sc1, tgt1 = s1["shooting"], s1["target"]
sc1.begin_assignment()
check("prune: only the weapons that can reach anything are queued",
        len(sc1.assignment_queue) == 10, len(sc1.assignment_queue))
check("prune: none of the queued weapons is the short-ranged one",
        all(w.range_in >= 20.0 for _, w in sc1.assignment_queue))
check("prune: it says so in the log",
        any("no target in range" in line for line in s1["log"].lines), s1["log"].lines[-1:])
for _ in range(40):
    if sc1.current_assignment() is None:
        break
    sc1.assign_current(tgt1)
check("prune: the assignment step now runs to completion",
        sc1.state != shooting_mod.ASSIGNING, sc1.state)


# ------------------------------------------ 3. skip_current on a live weapon
s2 = shooting_at(6.0)
sc2, tgt2 = s2["shooting"], s2["target"]
sc2.begin_assignment()
check("skip: at 6in every weapon can reach, so nothing is pruned",
        len(sc2.assignment_queue) == 20, len(sc2.assignment_queue))
head = sc2.current_assignment()
before = len(sc2.assignment_queue)
sc2.skip_current()
check("skip: the pair leaves the queue", len(sc2.assignment_queue) == before - 1)
check("skip: it is not the head any more", sc2.current_assignment() != head)
check("skip: nothing was assigned for it", not sc2.assignments)
check("skip: logged by name",
        any(head[1].name in line and "does not fire" in line for line in s2["log"].lines))


# ------------------------------------------------ 4. skip disarms Overcharge
s3 = shooting_at(6.0)
sc3 = s3["shooting"]
sc3.begin_assignment()
sc3.assignment_overcharge = True
sc3.skip_current()
check("skip: the armed alternate firing mode is disarmed", sc3.assignment_overcharge is False)


# -------------------------------- 5. finish_assignment resolves what is set
s4 = shooting_at(6.0)
sc4, att4, tgt4 = s4["shooting"], s4["attacker"], s4["target"]
sc4.begin_assignment()
sc4.assign_current(tgt4)
sc4.assign_current(tgt4)
left = len(sc4.assignment_queue)
sc4.finish_assignment()
check("finish: leaves ASSIGNING behind", sc4.state != shooting_mod.ASSIGNING, sc4.state)
check("finish: the two assigned weapons are being resolved, not thrown away",
        sc4.current_group is not None or sc4.resolved_groups or sc4.pending_step is not None)
check("finish: logs how many were left unfired",
        any("%d weapon(s) left unfired" % left in line for line in s4["log"].lines))


# --------------------------- 6. skipping everything still ends the activation
s5 = shooting_at(6.0)
sc5, att5 = s5["shooting"], s5["attacker"]
sc5.begin_assignment()
sc5.finish_assignment()
check("skip all: the activation ends", sc5.state == shooting_mod.IDLE, sc5.state)
check("skip all: no dice were rolled", s5["dice"].rolled == [], s5["dice"].rolled)
check("skip all: the unit still used up its shooting (rule 04.01, like stop_shooting)",
        att5 in sc5.shot_squad_ids)
check("skip all: rule 13.09 bookkeeping ran too", att5 in sc5.last_ranged_attack_turn)


# -------------------- 7. nothing can shoot at all: no dead end, no assignment
s6 = shooting_at(60.0)
sc6, att6 = s6["shooting"], s6["attacker"]
sc6.begin_assignment()
check("nothing in range: begin_assignment ends the activation outright",
        sc6.state == shooting_mod.IDLE, sc6.state)
check("nothing in range: the unit is not left mid-assignment", not sc6.assignment_queue)


# ----------------------------------------------------------- 8. guards
s7 = shooting_at(6.0)
sc7 = s7["shooting"]
sc7.skip_current()
check("guard: skip_current does nothing outside ASSIGNING",
        sc7.state == shooting_mod.CHOOSING_TARGET, sc7.state)
sc7.finish_assignment()
check("guard: finish_assignment does nothing outside ASSIGNING",
        sc7.state == shooting_mod.CHOOSING_TARGET, sc7.state)
sc7.begin_assignment()
sc7.finish_assignment()
sc7.finish_assignment()
check("guard: a second finish_assignment after the activation ended is a no-op",
        sc7.state == shooting_mod.IDLE, sc7.state)


# ============================================================ FIGHT PHASE
def melee_scene():
    """A mob with only its front rank in Engagement Range, and two engaged
    enemy units so the target choice is not auto-picked (which is the only
    way split fire is reachable in melee at all)."""
    s = tk.fight_scene(orks.BOYZ, tau.STRIKE_TEAM)
    state, att, tgt, fc = s["state"], s["attacker"], s["target"], s["fight"]
    tx, ty = tgt.models[0].x_in, tgt.models[0].y_in
    tgt2 = tk.build(tau.BREACHER_TEAM, "Player 1", name="Breachers")
    for i, m in enumerate(tgt2.models):
        m.x_in, m.y_in = tx + 14 + i * 1.4, ty
        state.add_token(m)
    for i, m in enumerate(att.models):
        if i < 3:
            m.x_in, m.y_in = tx + i * 1.4, ty - 1.0
        elif i == 3:
            m.x_in, m.y_in = tx + 14, ty - 1.0
        else:
            m.x_in, m.y_in = tx + (i - 4) * 1.4, ty - 12.0
    fc.begin_fight_step()
    fc.select_to_fight(att)
    fc.split_fire = True
    s["target2"] = tgt2
    return s


f0 = melee_scene()
engaged = sum(1 for m in f0["attacker"].models
              if model_engaged_with(m, f0["target"]) or model_engaged_with(m, f0["target2"]))
check("melee scene: only part of the mob is within Engagement Range",
        engaged == 4 and len(f0["attacker"].models) == 10, engaged)
check("melee scene: two engaged targets, so the choice is not auto-picked",
        len(f0["fight"].engaged_enemy_squads(f0["attacker"])) == 2)


# ------------------------------------------- 9. the melee dead end, pre-fix
with no_prune(fight_mod.FightController):
    f1 = melee_scene()
    fc1, t1, t1b = f1["fight"], f1["target"], f1["target2"]
    fc1.begin_assignment()
    frozen = None
    for _ in range(60):
        cur = fc1.current_assignment()
        if cur is None:
            break
        before = len(fc1.assignment_queue)
        fc1.assign_current(t1)
        if len(fc1.assignment_queue) == before:
            fc1.assign_current(t1b)
        if len(fc1.assignment_queue) == before:
            frozen = cur
            break
    check("A/B pre-fix (melee): the queue freezes on an unengaged model",
            frozen is not None and not any(model_engaged_with(frozen[0], sq) for sq in (t1, t1b)))
    check("A/B pre-fix (melee): still stuck in ASSIGNING",
            fc1.state == fight_mod.ASSIGNING, fc1.state)
    check("A/B pre-fix (melee): nothing to click on the board",
            len(fc1.valid_target_models()) == 0)


# ---------------------------------- 10. melee prune: trailing models dropped
f2 = melee_scene()
fc2, t2, t2b = f2["fight"], f2["target"], f2["target2"]
fc2.begin_assignment()
assigned = 0
for _ in range(60):
    cur = fc2.current_assignment()
    if cur is None:
        break
    before = len(fc2.assignment_queue)
    fc2.assign_current(t2)
    if len(fc2.assignment_queue) == before:
        fc2.assign_current(t2b)
    if len(fc2.assignment_queue) == before:
        break
    assigned += 1
check("melee prune: the assignment step completes instead of freezing",
        fc2.state != fight_mod.ASSIGNING, fc2.state)
check("melee prune: exactly the engaged models were asked about (rule 12.05)",
        assigned == 4, assigned)
check("melee prune: the trailing models are logged as not attacking",
        any("out of Engagement Range" in line for line in f2["log"].lines))


# ------------------------------------------- 11. melee skip / finish
f3 = melee_scene()
fc3 = f3["fight"]
fc3.begin_assignment()
head = fc3.current_assignment()
before = len(fc3.assignment_queue)
fc3.skip_current()
check("melee skip: the pair leaves the queue", len(fc3.assignment_queue) < before)
check("melee skip: logged by name",
        any(head[1].name in line and "does not attack" in line for line in f3["log"].lines))

f4 = melee_scene()
fc4 = f4["fight"]
fc4.begin_assignment()
fc4.assign_current(f4["target"])
fc4.finish_assignment()
check("melee finish: leaves ASSIGNING behind", fc4.state != fight_mod.ASSIGNING, fc4.state)

f5 = melee_scene()
fc5 = f5["fight"]
fc5.begin_assignment()
fc5.finish_assignment()
check("melee skip all: the fight activation ends without dice",
        fc5.state != fight_mod.ASSIGNING and f5["dice"].rolled == [], (fc5.state, f5["dice"].rolled))
fc5.skip_current()
check("guard (melee): skip_current outside ASSIGNING is a no-op",
        fc5.state != fight_mod.ASSIGNING, fc5.state)

# ================================================================ the panel
# Rendered for real, and the new buttons identified by CLICKING them - the
# panel keeps only (rect, callback), so there is no label to match on, and a
# rect that is computed but never wired up would pass anything weaker.
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from game import config as game_config
from game.movement import MovementController
from game.shooting import ShootingController
from game.ui.action_panel import ActionPanel

pygame.init()
pygame.display.set_mode((320, 240))
panel = ActionPanel()
panel_rect = pygame.Rect(0, 0, game_config.LEFT_PANEL_WIDTH, 900)
surface = pygame.Surface((game_config.LEFT_PANEL_WIDTH, 900))


def panel_buttons(scene, shooting_controller=None, fight_controller=None):
    mover = MovementController(turn_tracker=scene["turn"], all_tokens=scene["state"].tokens,
                               player_name="Player 2", dice_manager=scene["dice"])
    mover.select(scene["attacker"].models[0])
    sc = shooting_controller or ShootingController(
        all_tokens=scene["state"].tokens, dice_manager=scene["dice"],
        decision_manager=scene["decision"], player_name="Player 2",
    )
    panel.draw(surface, panel_rect, mover, sc, None,
               fight_controller=fight_controller)
    return list(panel._buttons)


def click_until(make_scene, controller_of, predicate, **draw_kwargs):
    """Click each button of a freshly rendered panel in turn (rebuilding the
    scene between tries, since a click is not undoable) and report whether
    any of them satisfies `predicate`."""
    probe = make_scene()
    buttons = panel_buttons(probe, **{k: controller_of(probe) if v else None
                                      for k, v in draw_kwargs.items()})
    for index in range(len(buttons)):
        probe = make_scene()
        buttons = panel_buttons(probe, **{k: controller_of(probe) if v else None
                                          for k, v in draw_kwargs.items()})
        buttons[index][1]()
        if predicate(probe, controller_of(probe)):
            return True
    return False


# ---- shooting panel
def shooting_probe():
    p = shooting_at(6.0)
    p["shooting"].begin_assignment()
    return p


probe = shooting_probe()
buttons = panel_buttons(probe, shooting_controller=probe["shooting"])
check("panel: buttons are drawn during assignment", bool(buttons))
check("panel: every button stays inside the panel",
      all(panel_rect.contains(r) for r, _ in buttons))
check("panel: assignment now offers more than the old lone Cancel", len(buttons) >= 3, len(buttons))

check(
    "panel: one button skips exactly the weapon at the front of the queue",
    click_until(
        shooting_probe, lambda p: p["shooting"],
        lambda p, sc: sc.state == shooting_mod.ASSIGNING and len(sc.assignment_queue) == 19,
        shooting_controller=True,
    ),
)
# Deliberately NOT just "the activation ended" - Cancel does that too. The
# distinguishing fact is that this one used the unit's shooting up (rule
# 04.01, like stop_shooting) while Cancel leaves it able to shoot later.
check(
    "panel: another ends the activation and uses the unit's shooting up",
    click_until(
        shooting_probe, lambda p: p["shooting"],
        lambda p, sc: (sc.state == shooting_mod.IDLE and p["dice"].rolled == []
                       and p["attacker"] in sc.shot_squad_ids),
        shooting_controller=True,
    ),
)


# ---- fight panel
def fight_probe():
    p = melee_scene()
    p["fight"].begin_assignment()
    return p


probe_f = fight_probe()
fbuttons = panel_buttons(probe_f, fight_controller=probe_f["fight"])
check("panel (melee): buttons are drawn during assignment", bool(fbuttons))
check("panel (melee): every button stays inside the panel",
      all(panel_rect.contains(r) for r, _ in fbuttons))

queued = len(probe_f["fight"].assignment_queue)
check(
    "panel (melee): one button skips the model at the front of the queue",
    click_until(
        fight_probe, lambda p: p["fight"],
        lambda p, fc: fc.state == fight_mod.ASSIGNING and len(fc.assignment_queue) == queued - 1,
        fight_controller=True,
    ),
)
# Same distinction as above: FightController.cancel() deliberately leaves the
# unit still eligible to fight, this one finishes its activation.
check(
    "panel (melee): another ends the assignment and the unit's fight with it",
    click_until(
        fight_probe, lambda p: p["fight"],
        lambda p, fc: (fc.state != fight_mod.ASSIGNING and p["dice"].rolled == []
                       and p["attacker"] in fc.fought_squad_ids),
        fight_controller=True,
    ),
)

c.finish()
