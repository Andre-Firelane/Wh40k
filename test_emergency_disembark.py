"""Regression tests for the reported Emergency Disembark wipe.

logs/game_20260805_232655.log, battle round 4, Player 1's Shooting phase:

    Trukk was destroyed.
    2 Meganobz 1 could not be placed after disembarking from any facing
    2 Meganobz 1 is destroyed - could not be set up within 6" of its TRANSPORT

Cause: _disembark_pack_positions() validated every candidate slot for board
edge, terrain and model overlap - but never for Engagement Range (03.04),
which confirm_setup() then enforces on the FINISHED squad (03.02, waived only
by 18.04's Combat Disembark). The arcs are ordered toward the nearest enemy,
so the generator packed the squad into exactly the models that made the
placement illegal, and every one of the eight facings failed the same way.

Board state below is the last position that log recorded for every unit
before the Trukk died.
"""
import math

from game import maps, config
from game.game_state import GameState
from game.factions import build_squad
from game.factions.orks import (MEGANOBZ, TRUKK, STORMBOYZ, BOYZ, WARBIKERS, GRETCHIN,
                                DEFF_DREAD, DEFFKOPTAS)
from game.factions.tau_empire import (KROOT_CARNIVORES, STRIKE_TEAM, DEVILFISH,
                                      STEALTH_BATTLESUITS, GHOSTKEEL_BATTLESUIT, CRISIS_STARSCYTHE)
from game.setup import SetupController
from game.transport import (TransportController, DISEMBARK_DISTANCE_IN, COMBAT, EMERGENCY,
                            TACTICAL)
from game.movement import MovementController
from game.turn import TurnTracker
from game.dice import DiceManager
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance
from ai import agent_driver

checks, failed = 0, []


def ok(label, cond):
    global checks
    checks += 1
    if not cond:
        failed.append(label)
    print(("  PASS  " if cond else "  FAIL  ") + label)


m = maps.get('map2')
maps.apply_to_config(m)

TRUKK_POS = (7.83, 21.73)

POSITIONS = {
    "1 Kroot Carnivores 1": [(6.7, 26.8), (8.2, 26.8), (9.66, 26.76), (10.99, 26.61), (11.99, 25.58)],
    "1 Strike Team 1": [(11.45, 31.93), (12.95, 31.93), (14.45, 31.93), (15.95, 31.93), (17.45, 31.93),
                        (11.45, 33.93), (12.95, 33.93), (14.45, 33.93), (15.95, 33.93), (17.45, 33.93)],
    "1 Devilfish": [(3.65, 30.9)],
    "1 Strike Team 2": [(21.65, 28.12), (25.95, 27.93), (24.2, 29.92), (25.94, 29.39), (20.11, 28.35),
                        (23.11, 28.35), (24.61, 28.35)],
    "1 Kroot Carnivores 2": [(52.06, 30.58), (53.56, 30.58), (55.06, 30.58), (56.56, 30.58), (51.85, 32.46)],
    "1 Stealth Battlesuits 1": [(24.99, 39.24), (26.74, 39.25), (28.74, 39.25), (24.74, 41.25), (26.74, 41.25)],
    "1 Ghostkeel Battlesuit 1": [(8.99, 32.77)],
    "1 Crisis Starscythe Battlesuits 1 + Commander in Coldstar Battlesuit":
        [(7.85, 13.1), (10.19, 13.13), (6.86, 15.1), (5.41, 13.13)],
    "2 Boyz 1": [(38.33, 15.99), (39.83, 15.99), (41.33, 15.99), (46.75, 15.67), (45.84, 14.42),
                 (41.93, 13.99), (43.43, 13.99), (45.73, 13.16), (46.96, 13.45), (48.18, 13.73)],
    "2 Deff Dread 1": [(33.0, 20.5)],
    "2 Warbikers 2": [(21.2, 22.64), (21.43, 24.58), (21.78, 26.51)],
    "2 Stormboyz 1": [(6.72, 27.66), (6.24, 29.95), (7.96, 27.9), (9.3, 27.89), (11.31, 27.63),
                      (6.6, 25.96), (7.75, 26.48), (8.81, 25.69), (10.2, 25.67), (9.77, 22.7)],
    "2 Warbikers 1": [(39.63, 21.12), (42.45, 18.5), (44.4, 19.43)],
    "2 Trukk 2": [(48.47, 17.84)],
    "2 Gretchin 1": [(27.33, 10.07), (26.75, 7.0), (28.0, 7.0), (29.25, 7.0), (30.5, 7.0), (27.33, 8.07),
                     (28.58, 8.07), (29.83, 8.07), (31.08, 8.07), (32.33, 8.07), (27.29, 6.01)],
    "2 Deffkoptas 1": [(31.1, 15.02), (29.8, 13.42), (31.83, 13.09)],
}

SHEETS = {
    "1 Kroot Carnivores 1": (KROOT_CARNIVORES, "Player 1"),
    "1 Strike Team 1": (STRIKE_TEAM, "Player 1"),
    "1 Devilfish": (DEVILFISH, "Player 1"),
    "1 Strike Team 2": (STRIKE_TEAM, "Player 1"),
    "1 Kroot Carnivores 2": (KROOT_CARNIVORES, "Player 1"),
    "1 Stealth Battlesuits 1": (STEALTH_BATTLESUITS, "Player 1"),
    "1 Ghostkeel Battlesuit 1": (GHOSTKEEL_BATTLESUIT, "Player 1"),
    "1 Crisis Starscythe Battlesuits 1 + Commander in Coldstar Battlesuit":
        (CRISIS_STARSCYTHE, "Player 1"),
    "2 Boyz 1": (BOYZ, "Player 2"),
    "2 Deff Dread 1": (DEFF_DREAD, "Player 2"),
    "2 Warbikers 2": (WARBIKERS, "Player 2"),
    "2 Stormboyz 1": (STORMBOYZ, "Player 2"),
    "2 Warbikers 1": (WARBIKERS, "Player 2"),
    "2 Trukk 2": (TRUKK, "Player 2"),
    "2 Gretchin 1": (GRETCHIN, "Player 2"),
    "2 Deffkoptas 1": (DEFFKOPTAS, "Player 2"),
}


def _closest_composition(sheet, wanted):
    best, gap = 0, 999
    for i, comp in enumerate(sheet.compositions()):
        n = sum(line.count for line in comp)
        if abs(n - wanted) < gap:
            best, gap = i, abs(n - wanted)
    return best


def reported_board():
    st = GameState()
    m.build(st)
    for name, (sheet, owner) in SHEETS.items():
        pos = POSITIONS[name]
        sq = build_squad(sheet, owner, name=name,
                         composition_index=_closest_composition(sheet, len(pos)))
        while len(sq.models) > len(pos):
            sq.models.pop()
        for model, (x, y) in zip(sq.models, pos):
            model.x_in, model.y_in = x, y
            st.add_token(model)
    return st


def controllers(st):
    turn = TurnTracker()
    setup = SetupController(st, obstacles=st.obstacles, all_tokens=st.tokens,
                            board_width_in=config.BOARD_WIDTH_IN,
                            board_height_in=config.BOARD_HEIGHT_IN)
    move = MovementController(obstacles=st.obstacles, turn_tracker=turn, all_tokens=st.tokens,
                              board_width_in=config.BOARD_WIDTH_IN,
                              board_height_in=config.BOARD_HEIGHT_IN)
    tc = TransportController(setup, st, st.tokens, move, None, DiceManager(), turn_tracker=turn,
                             board_width_in=config.BOARD_WIDTH_IN,
                             board_height_in=config.BOARD_HEIGHT_IN)
    return setup, tc


def start_emergency(st, setup, tc, squad, transport_token):
    squad.embarked_in = transport_token
    st.embarked_squads.append(squad)
    tc.queue_transport_destroyed(transport_token)
    tc.maybe_start_next_emergency()


def start_disembark_as(st, tc, squad, transport_token, mode):
    """Begin a Disembark Move in a specific mode. determine_mode() picks the
    mode from what the TRANSPORT did this phase (18.04), which a test can
    only reach indirectly - so the mode is set here and _begin_placement()
    driven directly, exactly as start_disembark() does."""
    squad.embarked_in = transport_token
    if squad not in st.embarked_squads:
        st.embarked_squads.append(squad)
    tc._disembarking_squad = squad
    tc._disembark_mode = mode
    tc._disembark_transport = transport_token
    tc._begin_placement()


# ------------------------------------------------------- 1. the reported wipe
print("\n1) the reported board: Trukk killed at (7.83,21.73) with 6 Meganobz aboard")
st = reported_board()
trukk = build_squad(TRUKK, "Player 2", name="2 Trukk 1")
tk = trukk.models[0]
tk.x_in, tk.y_in = TRUKK_POS
nobz = build_squad(MEGANOBZ, "Player 2", name="2 Meganobz 1", composition_index=1)
for mm in nobz.models:
    mm.x_in, mm.y_in = TRUKK_POS
setup, tc = controllers(st)
start_emergency(st, setup, tc, nobz, tk)

# How much legal, unengaged ground was actually inside the 6" limit - the
# user's "da war genug platz", measured rather than assumed.
enemies = [t for t in st.tokens if t.squad is not None and t.squad.owner != "Player 2"]
probe = nobz.models[0]
step, free = 0.25, 0
x = probe.radius_in
while x < config.BOARD_WIDTH_IN - probe.radius_in:
    y = probe.radius_in
    while y < config.BOARD_HEIGHT_IN - probe.radius_in:
        edge = math.hypot(x - tk.x_in, y - tk.y_in) - probe.radius_in - tk.radius_in
        if 0.05 <= edge <= 6.0 and setup.position_valid(probe, x, y, squad=nobz) and not any(
            math.hypot(x - e.x_in, y - e.y_in) - probe.radius_in - e.radius_in <= ENGAGEMENT_RANGE_IN
            for e in enemies
        ):
            free += 1
        y += step
    x += step
area = free * step * step
print(f"      legal, unengaged ground inside the 6\" limit: {area:.1f} sq.in")
ok("there was room for six 0.79\" bases (>20 sq.in)", area > 20)

placed = agent_driver._place_disembarked_squad(tc, setup, nobz, tk, st.tokens)
ok("the squad is placed", placed)
ok("all 6 models are on the battlefield",
   len(nobz.models) == 6 and all(mm in st.tokens for mm in nobz.models))
ok("unengaged (rule 03.02)", not nobz.is_engaged(st.tokens))
ok("coherent (rule 09.02)", not nobz.check_coherency())
ok("no model on terrain it cannot stand on", not nobz.check_terrain(st.obstacles))
ok("no model overlaps another", not nobz.check_model_overlap(st.tokens))
worst = max(edge_distance(mm, tk) for mm in nobz.models)
print(f"      furthest model {worst:.2f}\" from the wreck (limit 6\")")
ok("every model within 6\" of the TRANSPORT (rule 18.05)", worst <= 6.0)
ok("the post-placement hazard roll is now pending (rule 06.03)", tc.is_busy)

# --------------------------------------------- 2. it really was the engagement
print("\n2) the same board with the engagement filter patched back out fails")
st = reported_board()
trukk = build_squad(TRUKK, "Player 2", name="2 Trukk 1")
tk = trukk.models[0]
tk.x_in, tk.y_in = TRUKK_POS
nobz = build_squad(MEGANOBZ, "Player 2", name="2 Meganobz 1", composition_index=1)
for mm in nobz.models:
    mm.x_in, mm.y_in = TRUKK_POS
setup, tc = controllers(st)
start_emergency(st, setup, tc, nobz, tk)

real_allows = SetupController.allows_engaged
try:
    # Pretending every placement waives engagement is exactly the pre-fix
    # generator: candidates filtered for terrain and overlap only.
    SetupController.allows_engaged = property(lambda self: True)
    engaged_at = []
    for offset in agent_driver._DISEMBARK_FACINGS:
        agent_driver._spread_disembarked_squad(setup, nobz, tk, st.tokens,
                                               DISEMBARK_DISTANCE_IN[tc.disembark_mode], offset)
        engaged_at.append(nobz.is_engaged(st.tokens))
finally:
    SetupController.allows_engaged = real_allows
print(f"      facings that produced an ENGAGED placement: {sum(engaged_at)}/8")
ok("without the filter every facing is illegal (the reported wipe)", all(engaged_at))

# ------------------------------------------------- 3. Combat Disembark (18.04)
print("\n3) a Combat Disembark may still be set up engaged (rule 18.04)")
st = reported_board()
trukk = build_squad(TRUKK, "Player 2", name="2 Trukk 1")
tk = trukk.models[0]
tk.x_in, tk.y_in = TRUKK_POS
boyz = build_squad(BOYZ, "Player 2", name="2 Boyz 9")
for mm in boyz.models:
    mm.x_in, mm.y_in = TRUKK_POS
setup, tc = controllers(st)
start_disembark_as(st, tc, boyz, tk, COMBAT)
ok("SetupController reports the waiver", setup.allows_engaged)
placed = agent_driver._place_disembarked_squad(tc, setup, boyz, tk, st.tokens)
ok("the squad is placed", placed)
ok("all 10 models are on the battlefield", all(mm in st.tokens for mm in boyz.models))
ok("and it is allowed to end up engaged - the filter did not apply",
   setup.setting_up_squad is None)

# ----------------------------------------------------- 4. the human's overlay
print("\n4) the placement overlay paints the same rule the confirm enforces")
st = reported_board()
trukk = build_squad(TRUKK, "Player 2", name="2 Trukk 1")
tk = trukk.models[0]
tk.x_in, tk.y_in = TRUKK_POS
nobz = build_squad(MEGANOBZ, "Player 2", name="2 Meganobz 1", composition_index=1)
for mm in nobz.models:
    mm.x_in, mm.y_in = TRUKK_POS
setup, tc = controllers(st)
start_emergency(st, setup, tc, nobz, tk)
probe = nobz.models[0]
kroot = [t for t in st.tokens if t.squad is not None and t.squad.name == "1 Kroot Carnivores 1"][0]
# A point 1" of edge distance from a Kroot model, i.e. inside Engagement Range,
# and within 6" of the wreck.
ang = math.atan2(tk.y_in - kroot.y_in, tk.x_in - kroot.x_in)
d = probe.radius_in + kroot.radius_in + 1.0
engaged_pt = (kroot.x_in + d * math.cos(ang), kroot.y_in + d * math.sin(ang))
ok("that probe point really is inside 6\" of the wreck",
   math.hypot(engaged_pt[0] - tk.x_in, engaged_pt[1] - tk.y_in) - probe.radius_in - tk.radius_in <= 6.0)
ok("engaged ground is painted red for an Emergency Disembark",
   not tc.position_valid(nobz, probe, *engaged_pt))
clear_pt = (tk.x_in - 3.0, tk.y_in - 3.0)
ok("clear ground inside the limit is still painted green",
   tc.position_valid(nobz, probe, *clear_pt))
# Same point, Combat Disembark: the waiver has to reach the overlay too.
st2 = reported_board()
trukk2 = build_squad(TRUKK, "Player 2", name="2 Trukk 1")
tk2 = trukk2.models[0]
tk2.x_in, tk2.y_in = TRUKK_POS
nobz2 = build_squad(MEGANOBZ, "Player 2", name="2 Meganobz 2", composition_index=1)
for mm in nobz2.models:
    mm.x_in, mm.y_in = TRUKK_POS
setup2, tc2 = controllers(st2)
start_disembark_as(st2, tc2, nobz2, tk2, COMBAT)
ok("the same spot is green for a Combat Disembark",
   tc2.position_valid(nobz2, nobz2.models[0], *engaged_pt))

# --------------------------------------------- 5. historical spots still land
print("\n5) known-good disembark spots still place their whole squad")
CASES = [
    ("map2", (7.83, 21.73), MEGANOBZ, 1, EMERGENCY),
    ("map2", (15.70, 21.50), MEGANOBZ, 1, TACTICAL),
    ("map2", (48.47, 17.84), BOYZ, 0, TACTICAL),
    ("map2", (3.0, 3.0), BOYZ, 0, EMERGENCY),
    ("map2", (57.0, 41.0), BOYZ, 0, EMERGENCY),
    ("map2", (30.0, 22.0), BOYZ, 0, TACTICAL),
    ("map1", (3.0, 3.0), BOYZ, 0, EMERGENCY),
    ("map1", (21.70, 23.20), BOYZ, 0, TACTICAL),
    ("map1", (22.0, 30.0), BOYZ, 0, TACTICAL),
]
for map_name, spot, sheet, comp, mode in CASES:
    board = maps.get(map_name)
    maps.apply_to_config(board)
    st = GameState()
    board.build(st)
    setup, tc = controllers(st)
    tr = build_squad(TRUKK, "Player 2", name="carrier")
    tr.models[0].x_in, tr.models[0].y_in = spot
    sq = build_squad(sheet, "Player 2", name="cargo", composition_index=comp)
    for mm in sq.models:
        mm.x_in, mm.y_in = spot
    if mode == EMERGENCY:
        start_emergency(st, setup, tc, sq, tr.models[0])
    else:
        start_disembark_as(st, tc, sq, tr.models[0], mode)
    placed = agent_driver._place_disembarked_squad(tc, setup, sq, tr.models[0], st.tokens)
    good = (placed and all(mm in st.tokens for mm in sq.models)
            and not sq.check_coherency() and not sq.is_engaged(st.tokens)
            and max(edge_distance(mm, tr.models[0]) for mm in sq.models)
            <= DISEMBARK_DISTANCE_IN[mode] + 1e-6)
    ok(f"{map_name} {mode} at {spot}: {len(sq.models)} models placed", good)


# --------------------------- 6. Tactical vs Combat when everything is engaged
print("\n6) a TRANSPORT ringed by enemies gets the Combat Disembark 18.04 gives it")
maps.apply_to_config(m)
st = GameState()
m.build(st)
cx, cy = 30.0, 22.0
ring = build_squad(STRIKE_TEAM, "Player 1", name="ring")
ring.models = ring.models[:5]
for i, mm in enumerate(ring.models):
    a = 2 * math.pi * i / 5
    mm.x_in, mm.y_in = cx + 5.0 * math.cos(a), cy + 5.0 * math.sin(a)
    st.add_token(mm)
tr = build_squad(TRUKK, "Player 2", name="ringed trukk")
tk = tr.models[0]
tk.x_in, tk.y_in = cx, cy
boyz = build_squad(BOYZ, "Player 2", name="ringed boyz")
for mm in boyz.models:
    mm.x_in, mm.y_in = cx, cy
setup, tc = controllers(st)


def _old_sampler(self, transport_token, squad):
    """The pre-fix sampler: outer edge of the band only, judged by terrain and
    overlap but not by Engagement Range."""
    rep = squad.models[0]
    radius = 3.0 + transport_token.radius_in
    for i in range(12):
        a = 2 * math.pi * i / 12
        if self.setup_controller.position_valid(
            rep, transport_token.x_in + radius * math.cos(a),
            transport_token.y_in + radius * math.sin(a), squad=squad,
        ):
            return True
    return False


real_sampler = TransportController._tactical_placement_feasible
try:
    TransportController._tactical_placement_feasible = _old_sampler
    ok("before the fix the mode was Tactical - which can never confirm here",
       tc.determine_mode(tk, boyz) == TACTICAL)
finally:
    TransportController._tactical_placement_feasible = real_sampler
mode = tc.determine_mode(tk, boyz)
ok("now it is Combat (rule 18.04's fallback)", mode == COMBAT)
start_disembark_as(st, tc, boyz, tk, mode)
placed = agent_driver._place_disembarked_squad(tc, setup, boyz, tk, st.tokens)
ok("and the squad actually gets out", placed)
ok("all 10 models on the battlefield", all(mm in st.tokens for mm in boyz.models))
ok("battle-shocked, as a Combat Disembark requires", boyz.battle_shocked)

# Open ground must still resolve as Tactical - the wider sampling must not
# push units into Combat's Battle-shock and hazard roll for nothing.
st = GameState()
m.build(st)
setup, tc = controllers(st)
tr = build_squad(TRUKK, "Player 2", name="open trukk")
tr.models[0].x_in, tr.models[0].y_in = 30.0, 22.0
boyz = build_squad(BOYZ, "Player 2", name="open boyz")
for mm in boyz.models:
    mm.x_in, mm.y_in = 30.0, 22.0
boyz.embarked_in = tr.models[0]
ok("open ground still resolves as Tactical",
   tc.determine_mode(tr.models[0], boyz) == TACTICAL)

maps.apply_to_config(m)
print(f"\n{checks - len(failed)}/{checks} checks passed")
if failed:
    print("FAILED:")
    for f in failed:
        print("  -", f)
