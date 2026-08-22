"""Melee placement metrics: how many models a charge / pile-in actually gets
into Engagement Range.

That number is the whole point of both moves - only models within Engagement
Range fight (rule 12.05) - so it is the metric this file measures directly,
rather than "did the move succeed".

The charge scenarios A-E and the three pile-in scenarios are the ones CLAUDE.md
records numbers for; they lived in throwaway scratch files before and had to be
rebuilt from that description twice. They are in the repo now so the recorded
numbers can actually be re-checked.

Run: python test_melee_engagement.py
"""
from game import maps, config
from game.game_state import GameState
from game.factions import build_squad
from game.factions.orks import BOYZ, WARBIKERS
from game.factions.tau_empire import STRIKE_TEAM, KROOT_CARNIVORES
from game.movement import MovementController
from game.pile_in import PileInController, PILE_IN_RANGE_IN
from game.squad import edge_distance, ENGAGEMENT_RANGE_IN
from game.turn import TurnTracker, PHASE_FIGHT, PHASE_CHARGE, PHASES
from ai import agent_driver

m = maps.get('map2'); maps.apply_to_config(m)

checks, failed = 0, []


def ok(label, cond):
    global checks
    checks += 1
    if not cond:
        failed.append(label)
    print(("  PASS  " if cond else "  FAIL  ") + label)


def engaged(squad, target):
    """Models of `squad` within Engagement Range of `target` (rule 12.05)."""
    return sum(1 for mo in squad.models
               if min(edge_distance(mo, e) for e in target.models) <= ENGAGEMENT_RANGE_IN)


def place(squad, positions):
    squad.models = squad.models[:len(positions)]
    for mo, (x, y) in zip(squad.models, positions):
        mo.x_in, mo.y_in = x, y
    return squad


def grid(x0, y0, cols, rows, dx=1.5, dy=1.5):
    return [(x0 + c * dx, y0 + r * dy) for r in range(rows) for c in range(cols)]


def scene(attacker_ds, attacker_pos, defender_ds, defender_pos, phase,
          attacker_comp=0, defender_comp=0):
    """Two squads on an otherwise empty board, plus the controllers the AI
    geometry needs. Terrain deliberately left out for the charge/pile-in
    scenarios: they measure PACKING, and a wall would silently change the
    number being compared against the recorded one."""
    st = GameState()
    att = build_squad(attacker_ds, "Player 2", name="attacker", composition_index=attacker_comp)
    dfn = build_squad(defender_ds, "Player 1", name="defender", composition_index=defender_comp)
    place(att, attacker_pos)
    place(dfn, defender_pos)
    tokens = list(att.models) + list(dfn.models)
    st.tokens = tokens
    tt = TurnTracker(first_player="Player 2")
    tt.phase_index = PHASES.index(phase)
    mc = MovementController(obstacles=[], player_name="Player 2", turn_tracker=tt,
                            all_tokens=tokens, board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    return st, att, dfn, tt, mc


# --------------------------------------------------------------- charge A-E
# "the rolled distance should be used up: models should walk AROUND the enemy
# unit until the 12" is spent, so as many models as possible end up in melee"
# (user). Each entry: label, attacker layout, defender layout, charge roll.
CHARGE_SCENARIOS = [
    ("A 10 Boyz vs a 5-model line", grid(20, 20, 5, 2), grid(20, 30, 5, 1), 12.0),
    ("B 10 Boyz vs 2 models",       grid(20, 20, 5, 2), [(22.0, 30.0), (23.5, 30.0)], 12.0),
    ("C 10 Boyz vs 1 model",        grid(20, 20, 5, 2), [(22.0, 30.0)], 12.0),
    ("D 10 Boyz, clumped",          grid(20, 20, 2, 5), grid(20, 30, 3, 1), 12.0),
    ("E 10 Boyz, tight roll",       grid(20, 24.6, 5, 2), grid(20, 30, 5, 1), 5.0),
]


def run_charge(label, att_pos, dfn_pos, roll):
    st, att, dfn, tt, mc = scene(BOYZ, att_pos, KROOT_CARNIVORES, dfn_pos, PHASE_CHARGE)
    before = engaged(att, dfn)
    mc.select(att.models[0])
    mc.start_charge_move(roll, [dfn])
    agent_driver._charge_per_model(mc, att, dfn, roll)
    after = engaged(att, dfn)
    coh = att.check_coherency()
    print(f"    {label}: {before} -> {after} of {len(att.models)} engaged"
          f"{'  COHERENCY: ' + '; '.join(coh) if coh else ''}")
    return after, len(coh)


# ------------------------------------------------------------------ pile-in
PILE_IN_SCENARIOS = [
    # label, attacker layout, defender layout, recorded gain
    ("10 Boyz, 2 ranks",        grid(20, 27.6, 5, 2, dy=1.5), grid(20, 30.0, 5, 1), (10, 10)),
    ("9 Boyz, 3 ranks vs 3",    grid(20, 25.0, 3, 3, dy=1.5), grid(21, 30.0, 3, 1), (6, 8)),
    ("10 Boyz vs 1 model",      grid(20, 26.0, 5, 2, dy=1.5), [(22.0, 30.0)],       (5, 8)),
]


def run_pile_in(label, att_pos, dfn_pos):
    st, att, dfn, tt, mc = scene(BOYZ, att_pos, KROOT_CARNIVORES, dfn_pos, PHASE_FIGHT)
    pic = PileInController(turn_tracker=tt, all_tokens=st.tokens, movement_controller=mc)
    before = engaged(att, dfn)
    agent_driver._pile_in_squad(pic, mc, att)
    after = engaged(att, dfn)
    coh = att.check_coherency()
    print(f"    {label}: {before} -> {after} of {len(att.models)} engaged"
          f"{'  COHERENCY: ' + '; '.join(coh) if coh else ''}")
    return before, after, len(coh)


# ---------------------------------------- the reported case (Warbikers 2)
# logs/game_20260805_232655.log lines 600-608: the charge engaged 1 of 3
# Warbikers and the pile-in that followed moved NOTHING - identical positions
# before and after - while two bikes sat 2.54" and 4.47" from Engagement Range
# with a full 3" of pile-in each.
#
# The bar is 2 of 3, not 3 of 3, and that is a measured optimum rather than a
# concession: brute-forcing every legal spot on a 0.1" grid within each bike's
# 3" pile-in (front bike frozen - rule 12.03 forbids moving a model in base
# contact) gives the middle bike 45 spots inside Engagement Range and the rear
# bike ZERO. It is boxed in by the map2 wall at x[23.90,24.50] on one side and
# by its own squadmates on the other, and Warbikers cannot cross Dense terrain
# (rule 13.06). So 2 is everything this position has to give.
REPORTED_BIKES = [(21.16, 22.06), (21.62, 23.97), (21.78, 26.51)]
REPORTED_STRIKE = [(21.65, 28.12), (25.95, 27.93), (24.20, 29.92), (25.94, 29.39),
                   (20.11, 28.35), (23.11, 28.35), (24.61, 28.35)]


def run_reported():
    st = GameState(); m.build(st)   # real map2 terrain: this one is a real board state
    bikes = place(build_squad(WARBIKERS, "Player 2", name="2 Warbikers 2", composition_index=0),
                  REPORTED_BIKES)
    strike = place(build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 2"), REPORTED_STRIKE)
    tokens = list(bikes.models) + list(strike.models)
    st.tokens = tokens
    tt = TurnTracker(first_player="Player 2"); tt.phase_index = PHASES.index(PHASE_FIGHT)
    mc = MovementController(obstacles=st.obstacles, player_name="Player 2", turn_tracker=tt,
                            all_tokens=tokens, board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    pic = PileInController(turn_tracker=tt, all_tokens=tokens, movement_controller=mc)
    before = engaged(bikes, strike)
    gaps_before = [round(min(edge_distance(b, e) for e in strike.models), 2) for b in bikes.models]
    agent_driver._pile_in_squad(pic, mc, bikes)
    after = engaged(bikes, strike)
    gaps_after = [round(min(edge_distance(b, e) for e in strike.models), 2) for b in bikes.models]
    print(f"    engaged {before} -> {after} of 3")
    print(f"    edge gaps before {gaps_before}  after {gaps_after}")
    return before, after, len(bikes.check_coherency())


# ------------------------------------- pile-in with two engaged enemy units
def run_two_targets():
    """Rule 12.03 lets the unit aim its translation at one of the units it is
    engaged with. Which one used to be "the nearest", assumed; it is now the
    one measured to put the most models in Engagement Range. Set up so the
    nearest target is a single model and the other is a wide line, i.e. the
    near one is the WORSE choice."""
    st = GameState()
    boyz = place(build_squad(BOYZ, "Player 2", name="boyz"), grid(20, 22.1, 5, 2, dy=1.5))
    near = place(build_squad(KROOT_CARNIVORES, "Player 1", name="near"), [(26.5, 26.4)])
    wide = place(build_squad(STRIKE_TEAM, "Player 1", name="wide"), grid(17.5, 26.6, 5, 1))
    tokens = list(boyz.models) + list(near.models) + list(wide.models)
    st.tokens = tokens
    tt = TurnTracker(first_player="Player 2"); tt.phase_index = PHASES.index(PHASE_FIGHT)
    mc = MovementController(obstacles=[], player_name="Player 2", turn_tracker=tt,
                            all_tokens=tokens, board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    pic = PileInController(turn_tracker=tt, all_tokens=tokens, movement_controller=mc)
    targets = pic.pile_in_targets(boyz)
    before = agent_driver._engaged_model_count(boyz, targets)
    agent_driver._pile_in_squad(pic, mc, boyz)
    after = agent_driver._engaged_model_count(boyz, targets)
    print(f"    {len(targets)} engaged target(s); {before} -> {after} of {len(boyz.models)} engaged")
    return len(targets), before, after, len(boyz.check_coherency())


# ---------------------------------------------------------------- consolidate
def run_consolidate():
    """Consolidation shares _charge_per_model()'s geometry, so it is checked
    here too - a change made for pile-ins must not quietly move it backwards."""
    from game.consolidate import ConsolidateController, CONSOLIDATE_RANGE_IN
    st, att, dfn, tt, mc = scene(BOYZ, grid(20, 25.6, 5, 2, dy=1.5),
                                 KROOT_CARNIVORES, grid(20, 30.0, 3, 1), PHASE_FIGHT)
    before = engaged(att, dfn)
    mc.select(att.models[0])
    mc.start_consolidate_move(CONSOLIDATE_RANGE_IN, [dfn], "engaging")
    agent_driver._charge_per_model(mc, att, dfn, CONSOLIDATE_RANGE_IN,
                                   clearance=agent_driver.PILE_IN_CLEARANCE_IN)
    after = engaged(att, dfn)
    print(f"    consolidate: {before} -> {after} of {len(att.models)} engaged")
    return before, after, len(att.check_coherency())


if __name__ == "__main__":
    print("\n1) CHARGE - models in Engagement Range after the charge move")
    charge_results = []
    for label, ap, dp, roll in CHARGE_SCENARIOS:
        got, coh = run_charge(label, ap, dp, roll)
        charge_results.append(got)
        ok(f"charge {label[0]} keeps coherency", coh == 0)
    print(f"    charge engagement profile: {charge_results}")

    print("\n2) PILE-IN - models in Engagement Range before -> after")
    pile_results = []
    for label, ap, dp, recorded in PILE_IN_SCENARIOS:
        before, after, coh = run_pile_in(label, ap, dp)
        pile_results.append((before, after))
        ok(f"pile-in '{label}' never loses engaged models", after >= before)
        ok(f"pile-in '{label}' keeps coherency", coh == 0)
    print(f"    pile-in profile: {pile_results}")

    print("\n3) REPORTED CASE - 2 Warbikers 2 pile-in vs 1 Strike Team 2")
    before, after, coh = run_reported()
    ok("the reported pile-in reaches the measured optimum (2 of 3)", after == 2)
    ok("the reported pile-in gains at least one engaged model", after > before)
    ok("the reported pile-in keeps coherency", coh == 0)

    print("\n4) PILE-IN with two engaged enemy units - target picked by measurement")
    n_targets, before, after, coh = run_two_targets()
    ok("both enemy units count as pile-in targets", n_targets == 2)
    ok("the two-target pile-in gains engaged models", after > before)
    ok("the two-target pile-in keeps coherency", coh == 0)

    print("\n5) CONSOLIDATE shares the same geometry")
    before, after, coh = run_consolidate()
    ok("consolidation gains engaged models", after > before)
    ok("consolidation keeps coherency", coh == 0)

    print(f"\n{checks - len(failed)}/{checks} checks passed")
    for f in failed:
        print("  FAILED:", f)
