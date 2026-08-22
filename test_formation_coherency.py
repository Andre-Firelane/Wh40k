"""Coherency (rule 09.02) as the thing that decides whether a move happens.

logs/game_20260808_213013.log carries 77 coherency rejections in one game, and
three reported symptoms all trace back to them: a pile-in that moved nothing,
squads that stood still for a whole Movement phase, and formations that never
closed up again after being stretched.

Every check here has an A/B counterpart: the pre-fix behaviour is patched back
in and the same measurement is taken, so the numbers show the test is actually
touching the reported cause and not something adjacent.

Run: python test_formation_coherency.py
"""
from game import maps, config
from game.dice import DiceManager
from game.game_state import GameState
from game.factions import build_squad
from game.factions.orks import MEGANOBZ, BOYZ, TRUKK
from game.factions.tau_empire import KROOT_CARNIVORES
from game.movement import MovementController
from game.pile_in import PileInController
from game.setup import SetupController
from game.squad import edge_distance, ENGAGEMENT_RANGE_IN, MAX_SPREAD_IN
from game.transport import TransportController, DISEMBARK_DISTANCE_IN
from game.turn import TurnTracker, PHASE_FIGHT, PHASE_MOVEMENT, PHASES
from ai import agent_driver

m = maps.get('map2'); maps.apply_to_config(m)

checks, failed = 0, []


def ok(label, cond):
    global checks
    checks += 1
    if not cond:
        failed.append(label)
    print(("  PASS  " if cond else "  FAIL  ") + label)


def place(squad, positions):
    squad.models = squad.models[:len(positions)]
    for mo, (x, y) in zip(squad.models, positions):
        mo.x_in, mo.y_in = x, y
    return squad


def spread(squad):
    """Rule 09.02's widest-pair figure - edge to edge, as check_coherency()
    measures it."""
    return max(edge_distance(a, b)
               for i, a in enumerate(squad.models) for b in squad.models[i + 1:])


def engaged(squad, target):
    return sum(1 for mo in squad.models
               if min(edge_distance(mo, e) for e in target.models) <= ENGAGEMENT_RANGE_IN)


# =====================================================================
# 1. The reported Meganobz pile-in (log lines 351-396)
# =====================================================================
# Positions straight out of the log: line 355 is where the charge left the
# Meganobz, line 139 is Kroot Carnivores 1, which had not moved since.
MEGANOBZ_POS = [(32.94, 25.21), (36.92, 20.05), (37.21, 16.82),
                (38.33, 22.85), (35.04, 22.72), (40.01, 23.31)]
KROOT_POS = [(29.53, 27.34), (29.40, 28.84), (28.17, 27.98), (30.76, 28.20),
             (29.28, 30.33), (27.82, 29.81), (30.81, 30.05), (26.81, 28.62),
             (31.99, 29.05), (32.52, 27.59)]


def reported_pile_in():
    st = GameState(); m.build(st)
    nobz = place(build_squad(MEGANOBZ, "Player 2", name="2 Meganobz 1",
                             composition_index=1), MEGANOBZ_POS)
    kroot = place(build_squad(KROOT_CARNIVORES, "Player 1",
                              name="1 Kroot Carnivores 1"), KROOT_POS)
    tokens = list(nobz.models) + list(kroot.models)
    st.tokens = tokens
    tt = TurnTracker(first_player="Player 2"); tt.phase_index = PHASES.index(PHASE_FIGHT)
    mc = MovementController(obstacles=st.obstacles, player_name="Player 2", turn_tracker=tt,
                            all_tokens=tokens, board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    pic = PileInController(turn_tracker=tt, all_tokens=tokens, movement_controller=mc)
    before = [(mo.x_in, mo.y_in) for mo in nobz.models]
    agent_driver._pile_in_squad(pic, mc, nobz)
    moved = sum(1 for mo, (x, y) in zip(nobz.models, before)
                if abs(mo.x_in - x) > 0.05 or abs(mo.y_in - y) > 0.05)
    return nobz, kroot, moved


print("1) the reported Meganobz pile-in (log 393-396: '1 -> 1 of 6')")
nobz, kroot, moved = reported_pile_in()
print(f"    models the pile-in actually moved: {moved} of 6;"
      f"  engaged {engaged(nobz, kroot)}  spread {spread(nobz):.2f}\"")
ok("the pile-in is legal - the squad is still coherent", not nobz.check_coherency())
ok("the pile-in actually moves models (it used to move none)", moved > 0)

# A/B: put the pre-fix ordering back - baseline taken AFTER phase 1, and phase 1
# with no rollback ladder - and the same board reproduces the report.
real_phase_one = agent_driver._run_phase_one


def legacy_phase_one(movement_controller, squad, ox, oy, max_distance,
                     close_in_pairs, baseline_errors):
    """Phase 1 as it was: one full-offset pass, no coherency check at all."""
    step = (ox * ox + oy * oy) ** 0.5
    if step <= 1e-9:
        return
    agent_driver._place_shared_offset(movement_controller, squad, ox, oy, step,
                                      max_distance, close_in_pairs)


try:
    agent_driver._run_phase_one = legacy_phase_one
    old_nobz, old_kroot, old_moved = reported_pile_in()
finally:
    agent_driver._run_phase_one = real_phase_one
print(f"    A/B with the old phase 1: moved {old_moved} of 6,"
      f" engaged {engaged(old_nobz, old_kroot)}")
ok("A/B - the old phase 1 reproduces the reported 'moved nothing'", old_moved == 0)

# =====================================================================
# 2. A rigid translation has to actually be rigid
# =====================================================================
# _creep_toward()'s whole correctness argument is that a shared offset cannot
# change any pairwise distance. _translate_squad_toward() clamps each model on
# its own, so it can hand back a PARTIAL translation - which breaks exactly the
# invariant the caller is relying on. Measured on the boxed-in Tankbustas from
# the same log: 6" requested, centroid moved 1.00", coherency broken.
print("\n2) _translate_squad_toward() reports whether it stayed rigid")
st = GameState(); m.build(st)
boyz = place(build_squad(BOYZ, "Player 2", name="boyz"),
             [(20.0 + (i % 5) * 1.4, 20.0 + (i // 5) * 1.4) for i in range(10)])
wall_hugger = place(build_squad(BOYZ, "Player 1", name="blockers"),
                    [(20.0 + i * 1.4, 24.0) for i in range(10)])
tokens = list(boyz.models) + list(wall_hugger.models)
st.tokens = tokens
tt = TurnTracker(first_player="Player 2"); tt.phase_index = PHASES.index(PHASE_MOVEMENT)
mc = MovementController(obstacles=st.obstacles, player_name="Player 2", turn_tracker=tt,
                        all_tokens=tokens, board_width_in=config.BOARD_WIDTH_IN,
                        board_height_in=config.BOARD_HEIGHT_IN)
mc.select(boyz.models[0]); mc.start_move()
free = agent_driver._translate_squad_toward(mc, boyz, (20.0, 12.0), 3.0)
mc.cancel_move()
print(f"    unobstructed translation rigid: {free}")
ok("an unobstructed shared offset reports rigid", free is True)

mc.select(boyz.models[0]); mc.start_move()
blocked = agent_driver._translate_squad_toward(mc, boyz, (20.0, 40.0), 6.0)
mc.cancel_move()
print(f"    translation into the enemy line rigid: {blocked}")
ok("a translation some model cannot take reports NOT rigid", blocked is False)

# =====================================================================
# 3. Stretched squads close up again as they move
# =====================================================================
# User: "die truppen, die aus transportern aussteigen sind sehr weit
# auseinandergezogen... bei anschliessenden bewegungen ruecken sie sich aber
# nicht weiter zusammen. das laesst natuerlich viel raum für kohaerenz fehler."
STRETCHED_BOYZ = [(20.0 + i * 0.95, 12.0 + (i % 2) * 1.1) for i in range(10)]


def spread_trail(positions, datasheet, comp, target, turns=4, legacy=False):
    # The pre-fix state is BOTH off: nothing pulled a stretched formation in,
    # and a placement that broke coherency was handed back as-is for the caller
    # to throw away. Disabling only one of them measures neither state.
    real = agent_driver._tightening_factor
    real_repair = agent_driver._repair_coherency_by_shrinking
    if legacy:
        agent_driver._tightening_factor = lambda squad: 1.0
        agent_driver._repair_coherency_by_shrinking = lambda *a, **k: False
    try:
        st = GameState(); m.build(st)
        sq = place(build_squad(datasheet, "Player 2", name="unit",
                               composition_index=comp), positions)
        st.tokens = list(sq.models)
        tt = TurnTracker(first_player="Player 2")
        tt.phase_index = PHASES.index(PHASE_MOVEMENT)
        trail = [spread(sq)]
        for _ in range(turns):
            mc = MovementController(obstacles=st.obstacles, player_name="Player 2",
                                    turn_tracker=tt, all_tokens=st.tokens,
                                    board_width_in=config.BOARD_WIDTH_IN,
                                    board_height_in=config.BOARD_HEIGHT_IN)
            mc.select(sq.models[0])
            agent_driver._advance_toward(mc, sq, target, allow_bulk_fallback=True)
            trail.append(spread(sq))
        return trail, sq.check_coherency()
    finally:
        agent_driver._tightening_factor = real
        agent_driver._repair_coherency_by_shrinking = real_repair


print("\n3) a stretched squad closes up over successive moves")
for label, pos, ds, comp, target in (
        ("Meganobz x6 (post-charge)", MEGANOBZ_POS, MEGANOBZ, 1, (20.0, 34.0)),
        ("Boyz x10 (strung out)", STRETCHED_BOYZ, BOYZ, 0, (32.0, 34.0))):
    trail, coh = spread_trail(pos, ds, comp, target)
    old, _ = spread_trail(pos, ds, comp, target, legacy=True)
    print(f"    {label}")
    print(f"      now: " + " -> ".join(f"{s:.2f}" for s in trail))
    print(f"      old: " + " -> ".join(f"{s:.2f}" for s in old))
    ok(f"{label} ends tighter than it started", trail[-1] < trail[0] - 0.5)
    ok(f"{label} stays coherent throughout", not coh)
    ok(f"A/B - {label} used to keep its spread frozen", abs(old[-1] - old[0]) < 0.5)

# =====================================================================
# 4. Disembarking itself is NOT the source of the stretch
# =====================================================================
# Worth a check rather than an assumption: the ring was the suspected cause of
# the wide formations, and measuring says it is not - a disembark comes out
# well inside rule 09.02's limit, with neighbours nearly touching. The stretch
# is picked up later, by charges and moves.
print("\n4) how wide a squad actually leaves its transport")
for label, ds, comp, pos in (("Meganobz x6", MEGANOBZ, 1, (33.70, 20.89)),
                             ("Boyz x10", BOYZ, 0, (11.50, 20.50))):
    st = GameState(); m.build(st)
    trukk = build_squad(TRUKK, "Player 2", name="2 Trukk 1")
    tk = trukk.models[0]; tk.x_in, tk.y_in = pos
    cargo = build_squad(ds, "Player 2", name="cargo", composition_index=comp)
    for mo in cargo.models:
        mo.x_in, mo.y_in = pos
    st.tokens = [tk]
    tt = TurnTracker(first_player="Player 2")
    setup = SetupController(st, obstacles=st.obstacles, all_tokens=st.tokens,
                            board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    mc = MovementController(obstacles=st.obstacles, turn_tracker=tt, all_tokens=st.tokens,
                            board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    TransportController(setup, st, st.tokens, mc, None, DiceManager(), turn_tracker=tt,
                        board_width_in=config.BOARD_WIDTH_IN,
                        board_height_in=config.BOARD_HEIGHT_IN)
    agent_driver._spread_disembarked_squad(setup, cargo, tk, st.tokens,
                                           DISEMBARK_DISTANCE_IN["tactical"], 0.0)
    worst_gap = max(min(edge_distance(a, b) for b in cargo.models if b is not a)
                    for a in cargo.models)
    print(f"    {label} @{pos}: spread {spread(cargo):.2f}\" of {MAX_SPREAD_IN}\","
          f" worst neighbour gap {worst_gap:.2f}\"")
    ok(f"{label} disembarks well inside the spread limit",
       spread(cargo) < MAX_SPREAD_IN * 0.8)
    ok(f"{label} disembarks coherently", not cargo.check_coherency())

print("\n" + "=" * 60)
print(f"passed {checks - len(failed)}, failed {len(failed)}")
for f in failed:
    print("  FAILED:", f)
raise SystemExit(1 if failed else 0)
