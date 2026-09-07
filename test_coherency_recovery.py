"""A unit that is ALREADY out of coherency, and what the AI does about it.

Reported from logs/game_20260816_210737.log ("da waren einige coherency
probleme dabei, wieder aufgrund von disembark"), two independent defects, both
of which cost whole models:

  1. FROZEN. Meganobz + Warboss in Mega Armour emergency-disembarked (18.05),
     were shot down 7 -> 4 models, and entered the next Movement phase split
     3+1 with a 4.93" gap (log line 899). Lines 942-992 are seventeen
     consecutive `[coherency] could not end its move here` rejections; line
     993 is "remain stationary"; lines 1206-1208 destroy three of the four
     survivors at the end of the turn. Nothing in the movement sweep aims at
     closing the gap, and confirm_move() rejects rule 09.02 absolutely, so
     every candidate - down to _creep_toward(), whose guarantee is that a
     rigid translation cannot CHANGE coherency - was thrown away at the door.

  2. THE OPPONENT CHOSE. Rule 09.02's Regaining Coherency is the controlling
     player's choice, one model at a time. The AI never made it: _is_blocked()
     treats a pending removal as a hard stop, so the only thing that could
     answer was a human clicking the board - including for Player 2's own
     units. Log lines 1596-1598: Boyz + Warboss split 4+1+1 and the two models
     destroyed were the Boss Nob and the Warboss.

Every check has an A/B counterpart, so the numbers show the test is touching
the reported cause and not an adjacent easy scenario.

Run: python test_coherency_recovery.py
"""
import inspect

from game import attached_units, config, maps
from game.coherency import CoherencyEnforcer, connected_groups
from game.factions import build_squad
from game.factions.orks import BOYZ, MEGANOBZ, WARBOSS, WARBOSS_MEGA_ARMOUR
from game.factions.tau_empire import STRIKE_TEAM
from game.game_state import GameState
from game.movement import MovementController
from game.squad import edge_distance
from game.turn import PHASES, PHASE_MOVEMENT, TurnTracker
from ai import agent_driver

m = maps.get("map2")
maps.apply_to_config(m)

checks, failed = 0, []


def ok(label, cond):
    global checks
    checks += 1
    if not cond:
        failed.append(label)
    print(("  [ok  ] " if cond else "  [FAIL] ") + label)


def head(title):
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


# The isolated model and the nearest member of the body are straight out of the
# log's line 899; the other two are tight around that anchor, so the unit really
# is the "(3 + 1 models)" the log reports. The enemy is parked far away - the
# reported unit was NOT engaged (it was ordered to advance), and an engaged one
# could not make a Normal move at all.
BROKEN_MEGANOBZ = [(31.10, 25.50), (29.60, 24.70), (30.40, 27.00), (36.54, 29.41)]
COHERENT_MEGANOBZ = [(31.10, 25.50), (29.60, 24.70), (30.40, 27.00), (32.40, 26.10)]
FAR_ENEMY = [(24.0, 32.0), (25.2, 32.4), (24.4, 33.6), (23.2, 31.2)]
AIM = (24.5, 32.3)


def meganobz_scene(positions):
    st = GameState()
    m.build(st)
    nobz = build_squad(MEGANOBZ, "Player 2", name="2 Meganobz 1", composition_index=1)
    boss = build_squad(WARBOSS_MEGA_ARMOUR, "Player 2", name="2 Warboss in Mega Armour 1")
    attached_units.attach(boss, nobz)
    nobz.models = nobz.models[:len(positions)]
    for mo, (x, y) in zip(nobz.models, positions):
        mo.x_in, mo.y_in = x, y
    enemy = build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
    enemy.models = enemy.models[:len(FAR_ENEMY)]
    for mo, (x, y) in zip(enemy.models, FAR_ENEMY):
        mo.x_in, mo.y_in = x, y
    st.tokens = list(nobz.models) + list(enemy.models)
    tt = TurnTracker(first_player="Player 2")
    tt.phase_index = PHASES.index(PHASE_MOVEMENT)
    mc = MovementController(obstacles=st.obstacles, player_name="Player 2", turn_tracker=tt,
                            all_tokens=st.tokens, board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    return st, nobz, mc


def run_move(nobz, mc, aim=AIM):
    """One _advance_toward() through the real controller. Returns
    (returned True?, furthest single model moved, coherent afterwards?)."""
    before = [(mo.x_in, mo.y_in) for mo in nobz.models]
    mc.select(nobz.models[0])
    moved = agent_driver._advance_toward(mc, nobz, aim)
    travelled = max(((mo.x_in - x) ** 2 + (mo.y_in - y) ** 2) ** 0.5
                    for mo, (x, y) in zip(nobz.models, before))
    return moved, travelled, not nobz.check_coherency()


class regroup_disabled:
    """A/B: put the pre-fix behaviour back - no regroup stage at all.

    Also disables the packed-block candidate (_place_packed), which did not
    exist when this suite was written and which catches part of the same
    ground: measured over the 95 scenarios below, with neither mechanism 24 are
    frozen, with packing alone 8, with the regroup stage alone 0. So switching
    off only the regroup stage no longer reproduces the reported freeze - the
    A/B would quietly report that the bug never existed, which is the same trap
    this project has now hit three times. The regroup stage is still what
    carries this case; packing is not a replacement for it."""

    def __enter__(self):
        self.real = agent_driver._regroup_move
        self.real_pack = agent_driver._place_packed
        agent_driver._regroup_move = lambda *a, **k: False
        agent_driver._place_packed = lambda *a, **k: False

    def __exit__(self, *exc):
        agent_driver._regroup_move = self.real
        agent_driver._place_packed = self.real_pack


class spread_limit_on_everyone:
    """Put rule 09.02's 9" spread half back for BOTH players.

    The reported freeze happened in that world, and it is no longer the live
    one: config.SPREAD_LIMIT_PLAYERS now exempts the AI. Reproducing the freeze
    therefore has to reproduce its conditions too - without this, the A/B below
    measures today's rules and quietly reports that the bug never existed."""

    def __enter__(self):
        self.real = config.SPREAD_LIMIT_PLAYERS
        config.SPREAD_LIMIT_PLAYERS = ("Player 1", "Player 2")

    def __exit__(self, *exc):
        config.SPREAD_LIMIT_PLAYERS = self.real


# =====================================================================
head("1. the reported freeze: the squad enters the phase already broken")
# =====================================================================
_st, nobz, mc = meganobz_scene(BROKEN_MEGANOBZ)
gap = min(edge_distance(nobz.models[3], other) for other in nobz.models[:3])
ok(f"the scene really is the reported one - 2 groups, {gap:.2f}\" gap",
   len(connected_groups(nobz.models)) == 2 and 4.5 < gap < 5.5)
ok("and it is not engaged, so a Normal move is legal at all (09.05)",
   mc.can_make_move(nobz))

_st, nobz, mc = meganobz_scene(BROKEN_MEGANOBZ)
with spread_limit_on_everyone(), regroup_disabled():
    moved_ab, dist_ab, coherent_ab = run_move(nobz, mc)
print(f"    A/B (pre-fix): returned {moved_ab}, furthest model {dist_ab:.2f}\", coherent {coherent_ab}")
ok("A/B - without the regroup stage the squad is frozen exactly as reported",
   moved_ab is False and dist_ab < 0.01 and not coherent_ab)

# And it is still the regroup stage that rescues it, not anything since. Worth
# pinning explicitly, because a change that DID rescue this scene on its own
# came and went in the meantime (a size-derived formation-tightening target, see
# _tightening_factor()) - while it existed, this same scene escaped with the
# regroup stage switched off, which would have made the A/B above look like a
# bug that never existed. It was reverted for costing 8% of the army's ground,
# so the freeze is back to being the regroup stage's job alone.
_st, nobz, mc = meganobz_scene(BROKEN_MEGANOBZ)
with regroup_disabled():
    moved_live, dist_live, coherent_live = run_move(nobz, mc)
print(f"    live rules, regroup still off: returned {moved_live}, "
      f"furthest model {dist_live:.2f}\", coherent {coherent_live}")
ok("lifting the 9\" limit does NOT rescue it - the regroup stage is what does",
   moved_live is False and dist_live < 0.01)

_st, nobz, mc = meganobz_scene(BROKEN_MEGANOBZ)
moved, dist, coherent = run_move(nobz, mc)
print(f"    now: returned {moved}, furthest model {dist:.2f}\", coherent {coherent}")
ok("the squad moves instead of standing still", moved is True and dist > 1.0)
ok("and it ends the move in coherency (rule 09.02)", coherent)
ok("no model is left on Dense terrain or on top of another (confirm_move accepted it)",
   not mc.errors)

# =====================================================================
head("2. a healthy squad is untouched")
# =====================================================================
_st, nobz, mc = meganobz_scene(COHERENT_MEGANOBZ)
ok("control scene is coherent to begin with", not nobz.check_coherency())
after_fix = None
moved, dist, coherent = run_move(nobz, mc)
after_fix = [(round(mo.x_in, 4), round(mo.y_in, 4)) for mo in nobz.models]
print(f"    now: returned {moved}, furthest model {dist:.2f}\"")

_st, nobz2, mc2 = meganobz_scene(COHERENT_MEGANOBZ)
with regroup_disabled():
    moved_ab, dist_ab, _ = run_move(nobz2, mc2)
before_fix = [(round(mo.x_in, 4), round(mo.y_in, 4)) for mo in nobz2.models]
ok("a coherent squad still moves", moved is True and dist > 1.0)
ok("and lands on exactly the same positions as before the change",
   after_fix == before_fix)

# =====================================================================
head("3. how often a broken squad is frozen, measured")
# =====================================================================
# Same unit, same target, but the straggler broken off in every direction and
# at several distances - so the numbers are not one lucky geometry.
import math

SPOTS = [(31.0, 25.5), (20.0, 22.0), (38.0, 27.0), (14.0, 30.0), (44.0, 18.0)]
OFFSETS = [(ang, d) for ang in range(0, 360, 45) for d in (4.0, 6.0, 8.0)]


def stress(disable):
    frozen = incoherent = total = 0
    for (bx, by) in SPOTS:
        for (ang, d) in OFFSETS:
            body = [(bx, by), (bx - 1.5, by - 0.8), (bx - 0.7, by + 1.5)]
            sx = bx + d * math.cos(math.radians(ang))
            sy = by + d * math.sin(math.radians(ang))
            if not (1.5 < sx < config.BOARD_WIDTH_IN - 1.5 and 1.5 < sy < config.BOARD_HEIGHT_IN - 1.5):
                continue
            _s, squad, ctrl = meganobz_scene(body + [(sx, sy)])
            if not squad.check_coherency() or not ctrl.can_make_move(squad):
                continue  # not actually a broken, movable scenario
            total += 1
            if disable:
                with regroup_disabled():
                    _mv, travelled, coherent = run_move(squad, ctrl)
            else:
                _mv, travelled, coherent = run_move(squad, ctrl)
            if travelled < 0.5:
                frozen += 1
            if not coherent:
                incoherent += 1
    return total, frozen, incoherent


tot_a, frozen_a, incoh_a = stress(True)
tot_b, frozen_b, incoh_b = stress(False)
print(f"    A/B (pre-fix): {frozen_a}/{tot_a} frozen, {incoh_a}/{tot_a} still incoherent after the move")
print(f"    now:           {frozen_b}/{tot_b} frozen, {incoh_b}/{tot_b} still incoherent after the move")
ok("the stress set really is made of broken, movable squads", tot_a == tot_b and tot_a >= 40)
# Not every broken squad was frozen before: a per-model pass whose straggler
# happens to end up back in range fixes itself via _close_up_to_placed(). The
# claim is that the ones it CANNOT fix - the reported case among them - are no
# longer left standing.
ok("A/B - a substantial share of them used to be frozen", frozen_a >= 0.15 * tot_a)
ok("at least two thirds of those are now moving", frozen_b * 3 <= frozen_a)
ok("frozen and still-incoherent are the same squads (a frozen one cannot re-form)",
   frozen_a == incoh_a and frozen_b == incoh_b)

# =====================================================================
head("4. Regaining Coherency: the owner chooses, and keeps its characters")
# =====================================================================
def boyz_scene(positions):
    """A Boyz mob with its Warboss attached (19.01), cut down to as many models
    as there are positions. `positions` is read in model order: index 0 is the
    Boss Nob, the LAST one is the Warboss, everything between is rank and
    file - so a scene decides for itself where its characters stand."""
    st = GameState()
    m.build(st)
    b = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
    w = build_squad(WARBOSS, "Player 2", name="2 Warboss 1")
    attached_units.attach(w, b)
    b.models = b.models[:len(positions) - 1] + [b.models[-1]]  # keep the Warboss
    for mo, (x, y) in zip(b.models, positions):
        mo.x_in, mo.y_in = x, y
    st.tokens = list(b.models)
    return st, b


# The reported end-of-turn shape (log line 1596): 4 + 1 + 1. Both characters are
# put in the BODY here, and two plain Boyz are the stragglers - i.e. the pick
# genuinely has something to get wrong. (In the reported log the characters
# were themselves the two singletons, which makes losing them forced rather
# than a bad choice; the point being pinned here is that when it IS a choice,
# the AI makes it and makes it the right way round.)
REPORTED = [(30.0, 20.0), (31.0, 20.5), (35.57, 22.44), (32.73, 25.32),
            (30.5, 21.4), (31.6, 21.6)]
st, boyz = boyz_scene(REPORTED)
names = [mo.profile.name for mo in boyz.models]
ok("scene has both characters in it", "Boss Nob" in names and "Warboss" in names)
ok("and it is split 4 + 1 + 1 as reported",
   sorted(len(g) for g in connected_groups(boyz.models)) == [1, 1, 4])
ok("with both characters inside the body, so the stragglers are plain Boyz",
   all(mo.profile.name == "Boy"
       for g in connected_groups(boyz.models) if len(g) == 1 for mo in g))

enf = CoherencyEnforcer(all_tokens=st.tokens)
removed = []
for _ in range(10):
    enf.check_end_of_turn("Player 2")
    if enf.pending_squad is None:
        break
    before = list(boyz.models)
    if not agent_driver._maybe_resolve_coherency_removal(enf, "Player 2"):
        break
    removed.extend(mo.profile.name for mo in before if mo not in boyz.models)
survivors = [mo.profile.name for mo in boyz.models]
print(f"    removed: {removed}   survivors: {survivors}")
ok("the AI resolves it itself - the enforcer is no longer waiting", enf.pending_squad is None)
ok("the unit is coherent again", not boyz.check_coherency())
ok("it gave up plain Boyz, not its characters", removed and set(removed) == {"Boy"})
ok("the Boss Nob survives (the log destroyed it)", "Boss Nob" in survivors)
ok("the Warboss survives (the log destroyed it)", "Warboss" in survivors)

# A/B: the pre-fix path is "nobody answers", which is exactly what _is_blocked()
# then reports to the AI for the rest of the turn.
st, boyz = boyz_scene(REPORTED)
enf = CoherencyEnforcer(all_tokens=st.tokens)
enf.check_end_of_turn("Player 2")
ok("A/B - a pending removal really does exist to be answered", enf.pending_squad is boyz)
ok("A/B - and _is_blocked() would stop the AI dead on it",
   agent_driver._is_blocked(TurnTracker(first_player="Player 2"), _NoDecisions := type(
       "D", (), {"is_pending": False})(), type("Dice", (), {"is_pending": False})(),
       enf, "Player 2", None, None, None, None, None))

# Two singletons of the same size, one of them a character: the tie-break is
# the whole point of the cost key.
st, boyz = boyz_scene([(30.0, 20.0), (31.0, 20.5), (30.5, 21.4), (31.6, 21.6),
                       (35.57, 22.44), (32.73, 25.32)])
straggler_names = {mo.profile.name for g in connected_groups(boyz.models)
                   if len(g) == 1 for mo in g}
ok("tie-break scene: a plain Boy and the Warboss are both broken off alone",
   straggler_names == {"Boy", "Warboss"})
ok("the Boy is given up first, not the Warboss",
   agent_driver._coherency_removal_pick(boyz).profile.name == "Boy")

# The other half of rule 09.02: one group, but wider than 9". Only reachable
# for an owner the limit still binds - config.SPREAD_LIMIT_PLAYERS exempts the
# AI - so the removal logic is exercised in the world where it can happen, and
# the exemption itself is checked immediately afterwards.
st, boyz = boyz_scene([(20.0, 20.0), (21.2, 20.0), (22.4, 20.0), (23.6, 20.0),
                       (24.8, 20.0), (26.0, 20.0)])
# A chain: every neighbour inside the 2" half of the rule, the ends 11.4" apart.
for mo, x in zip(boyz.models, (20.0, 22.6, 25.2, 27.8, 30.4, 33.0)):
    mo.x_in = x
ok("spread-only scene: a single connected group, ends over 9\" apart",
   len(connected_groups(boyz.models)) == 1
   and max(edge_distance(a, b) for a in boyz.models for b in boyz.models) > 9.0)
ok("the AI is exempt from the spread half, so this chain is legal for it",
   not boyz.check_coherency())
with spread_limit_on_everyone():
    ok("A/B - the same chain is a violation for an owner the limit binds",
       bool(boyz.check_coherency()))
    pick = agent_driver._coherency_removal_pick(boyz)
widest = max(((edge_distance(a, b), a, b) for i, a in enumerate(boyz.models)
              for b in boyz.models[i + 1:]), key=lambda t: t[0])
ok("it gives up an END of the widest pair, the only models that can shorten it",
   pick is widest[1] or pick is widest[2])

# Ownership: the AI never touches the human's own choice.
st, boyz = boyz_scene(REPORTED)
enf = CoherencyEnforcer(all_tokens=st.tokens)
enf.check_end_of_turn("Player 2")
ok("the AI does not answer a removal that belongs to the other player",
   agent_driver._maybe_resolve_coherency_removal(enf, "Player 1") is False
   and enf.pending_squad is boyz)

# Wiring: it has to be checked BEFORE _is_blocked(), or it can never run.
#
# _take_one_action, not take_one_action: the public name is now a thin wrapper
# that absorbs an unreachable agent (see ai/connection.py), so the body this
# claim is about moved one function down. Reading the wrapper instead would
# make this check pass on an empty search - which is what it did the moment
# the wrapper appeared.
src = inspect.getsource(agent_driver._take_one_action)
ok("take_one_action() resolves the removal before _is_blocked()",
   "if _maybe_resolve_coherency_removal(" in src
   and src.index("if _maybe_resolve_coherency_removal(") < src.index("if _is_blocked("))

print(f"\npassed {checks - len(failed)}, failed {len(failed)}")
for f in failed:
    print("  FAIL:", f)
raise SystemExit(1 if failed else 0)
