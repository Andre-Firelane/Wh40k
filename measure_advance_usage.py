"""How often the AI can even CHOOSE to Advance (rule 09.06), and what it buys.

WHY THIS EXISTS
---------------
User report: "was mir auffaellt ist, dass die ki sehr wenig rennen benutzt.
gerade im waagh zug hat man dadurch ja kaum abzuege. man darf danach noch
chargen."

Counting Advances in the logs confirms it but does not say why. The reported
WAAAGH turn (logs/game_20260821_112241.log) is the sharpest case: the planner
wrote "WAAAGH! lets you Advance and still charge" into six separate orders and
the tactical layer Advanced exactly once - for the one unit whose plan named no
position at all.

That last clause is the whole finding, and it is a loop that had closed on
itself rather than a judgement the model was getting wrong:

  * ai/observation.py told the planner its position orders must lie inside a
    circle of radius M (the flat Move characteristic);
  * ai/agent_driver.py's _validate_turn_plan() clamped anything outside that
    circle back onto it;
  * and the tactical layer only builds an "Advance toward the planned
    position" option when the commanded point is FURTHER away than a plain
    move - a condition the first two rules had just made impossible.

So the Advance was not being weighed and rejected. It was never on the table.

WHAT THIS MEASURES
------------------
Section 1 walks the whole chain, which is the only level the fault is visible
at: an order in the Advance band goes through _validate_turn_plan() and then
into _handle_movement(), and we look at whether an Advance option comes out the
far end. Feeding the plan straight to the tactical layer would show no change
at all, because the option-building gate is the one part of the chain that was
already correct.

Section 2 prices it: the charge probability after a plain move against the
probability after Advancing first, from the positions the units actually stood
at when that WAAAGH movement phase opened. The second number is the exact joint
distribution over both rolls, not "average Advance, then charge" - charge
probability is a step function of the remaining gap, so the mean of the
outcomes is not the outcome of the mean.

Both run twice: once as the engine is now, and once with the pre-fix world
restored, so the difference is attributable rather than assumed.

Run: python measure_advance_usage.py
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ai import agent_driver, observation
from game import attached_units, maps
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import (
    BEAST_SNAGGA_BOYZ, BEASTBOSS, BOYZ, DEFF_DREAD, FLASH_GITZ, MEGANOBZ,
    PAINBOY, STORMBOYZ, TANKBUSTAS, WARBIKERS, WARBOSS, WARBOSS_MEGA_ARMOUR,
)
from game.factions.tau_empire import KROOT_CARNIVORES, STRIKE_TEAM
from game.game_state import GameState
from game.movement import MovementController
from game.squad import min_model_movement
from game.turn import PHASE_MOVEMENT, PHASES, TurnTracker
from game.waaagh import WaaaghController

maps.apply_to_config(maps.get("map2"))


class plain_move_reach:
    """The pre-fix world: reach is the flat Move characteristic, with no
    Advance counted."""

    def __enter__(self):
        self._saved = observation.advance_reach_in
        observation.advance_reach_in = min_model_movement
        return self

    def __exit__(self, *exc):
        observation.advance_reach_in = self._saved
        return False


# --------------------------------------------------------------- the board
#
# Where Player 2 stood when its WAAAGH movement phase opened (the end of the
# previous turn), and where the Tau stood after their own turn. Both straight
# out of the reported log, so this is the real board rather than a sketch of it.

ORK_POSITIONS = {
    "2 Boyz 1 + Warboss + Painboy": [
        (24.49, 15.46), (24.49, 14.18), (25.59, 14.82), (23.38, 14.82),
        (24.50, 12.83), (23.21, 13.24), (25.79, 13.17), (26.70, 14.18),
        (22.27, 14.18), (24.56, 11.34), (23.22, 11.66), (25.88, 11.56),
        (22.03, 12.48), (27.03, 12.28), (21.16, 13.54), (27.86, 13.41),
        (28.27, 14.79), (24.60, 9.86), (23.30, 10.09), (25.90, 9.99),
        (20.71, 16.12), (23.38, 16.10)],
    "2 Tankbustas 1": [(47.25, 15.52), (48.55, 14.77), (48.55, 16.27),
                       (49.85, 14.02), (50.25, 15.52), (50.14, 12.08)],
    "2 Deff Dread 1": [(40.00, 15.00)],
    "2 Flash Gitz 1": [(50.15, 6.00), (45.12, 7.59), (51.60, 5.16), (43.67, 8.43),
                       (51.60, 6.84), (48.70, 6.84), (50.15, 7.68), (45.12, 5.91),
                       (43.44, 6.36), (46.80, 6.36)],
    "2 Warbikers 2": [(11.80, 11.18)],
    # Not logged that turn (embarked / in reserve); placed on their own side of
    # the field so they still stand somewhere the plan could plausibly order
    # them from. Flagged rather than presented as measured.
    "2 Beast Snagga Boyz 1 + Beastboss": [(17.7, 13.0)],
    "2 Meganobz 1 + Warboss in Mega Armour": [(53.0, 15.8)],
    "2 Stormboyz 1": [(30.0, 12.0)],
}

TAU_POSITIONS = {
    "1 Kroot Carnivores 1": [(27.96, 21.72), (26.39, 21.69), (24.20, 23.98),
                             (30.89, 23.29), (25.18, 22.62), (29.46, 22.15),
                             (23.52, 25.72)],
    "1 Strike Team 1": [(49.57, 31.21), (50.86, 31.98), (49.55, 32.71),
                        (48.26, 31.94), (52.15, 32.75), (52.57, 31.26),
                        (51.03, 33.83), (49.53, 34.21)],
}

UNITS = list(ORK_POSITIONS)


def scene():
    """Player 2's assault half of the reported roster against the two Tau units
    it actually had charge decisions about that turn."""
    state = GameState()
    squads = {}

    def place(squad, name):
        squad.name = name
        spots = ORK_POSITIONS.get(name) or TAU_POSITIONS[name]
        for model, (x, y) in zip(squad.models, spots):
            model.x_in, model.y_in = x, y
        # A squad with more models than the log listed keeps the rest packed in
        # beside the last one, so coherency (09.02) still holds.
        for i, model in enumerate(squad.models[len(spots):]):
            model.x_in = spots[-1][0] + 1.3 * ((i % 4) + 1)
            model.y_in = spots[-1][1] - 1.3 * (i // 4)
        for model in squad.models:
            state.add_token(model)
        squads[name] = squad
        return squad

    mob = build_squad(BOYZ, owner="Player 2", composition_index=1, name="Boyz")
    mob = attached_units.attach(build_squad(WARBOSS, owner="Player 2", name="Warboss"), mob)
    mob = attached_units.attach(build_squad(PAINBOY, owner="Player 2", name="Painboy"), mob)
    place(mob, "2 Boyz 1 + Warboss + Painboy")

    place(attached_units.attach(
        build_squad(BEASTBOSS, owner="Player 2", name="Beastboss"),
        build_squad(BEAST_SNAGGA_BOYZ, owner="Player 2", name="Beast Snagga Boyz")),
        "2 Beast Snagga Boyz 1 + Beastboss")

    place(attached_units.attach(
        build_squad(WARBOSS_MEGA_ARMOUR, owner="Player 2", name="Warboss in Mega Armour"),
        build_squad(MEGANOBZ, owner="Player 2", composition_index=1, name="Meganobz")),
        "2 Meganobz 1 + Warboss in Mega Armour")

    place(build_squad(TANKBUSTAS, owner="Player 2", name="Tankbustas"), "2 Tankbustas 1")
    place(build_squad(DEFF_DREAD, owner="Player 2", name="Deff Dread"), "2 Deff Dread 1")
    place(build_squad(FLASH_GITZ, owner="Player 2", name="Flash Gitz"), "2 Flash Gitz 1")
    place(build_squad(WARBIKERS, owner="Player 2", name="Warbikers"), "2 Warbikers 2")
    place(build_squad(STORMBOYZ, owner="Player 2", name="Stormboyz"), "2 Stormboyz 1")

    place(build_squad(KROOT_CARNIVORES, owner="Player 1", name="Kroot"), "1 Kroot Carnivores 1")
    place(build_squad(STRIKE_TEAM, owner="Player 1", name="Strike"), "1 Strike Team 1")

    turn = TurnTracker()
    turn.phase_index = PHASES.index(PHASE_MOVEMENT)
    turn.turn_owner = "Player 2"
    turn.set_active("Player 2")
    waaagh = WaaaghController()
    waaagh.active_players.add("Player 2")
    mover = MovementController(obstacles=state.obstacles, turn_tracker=turn,
                               all_tokens=state.tokens, dice_manager=DiceManager())
    return state, turn, waaagh, mover, squads


def nearest_foe(squad, squads):
    return min((squads["1 Kroot Carnivores 1"], squads["1 Strike Team 1"]),
               key=lambda e: squad.min_distance_to(e))


def toward(squad, foe, inches):
    """A point `inches` from this squad's centre, straight at `foe`."""
    cx = sum(m.x_in for m in squad.models) / len(squad.models)
    cy = sum(m.y_in for m in squad.models) / len(squad.models)
    fx = sum(m.x_in for m in foe.models) / len(foe.models)
    fy = sum(m.y_in for m in foe.models) / len(foe.models)
    dx, dy = fx - cx, fy - cy
    span = (dx * dx + dy * dy) ** 0.5 or 1.0
    return (cx + dx / span * inches, cy + dy / span * inches)


# ------------------------------------------- section 1: does the chain allow it

def chain(name, band_inches):
    """Order this unit `band_inches` toward its nearest enemy, run the order
    through the plan validator, then through the movement handler. Returns
    (kept_position, offered_an_advance)."""
    state, turn, waaagh, mover, squads = scene()
    squad = squads[name]
    spot = toward(squad, nearest_foe(squad, squads), band_inches)

    plan = {"turn_intent": "", "malformed": False, "unit_plans": {
        name: {"role": "advance", "target": None, "position": spot,
               "priority": 1, "reason": "measured"}}}
    validated = agent_driver._validate_turn_plan(plan, "Player 2", state, turn, None)
    kept = validated["unit_plans"][name].get("position")
    survived = kept is not None and abs(kept[0] - spot[0]) < 0.05 and abs(kept[1] - spot[1]) < 0.05

    seen = {}

    def spy(agent, all_tokens, tracker, options, player, on_thinking, **kwargs):
        seen.setdefault("types", [o["type"] for o in options])
        seen.setdefault("descriptions", [o["description"] for o in options])
        return options[0]

    memory = agent_driver.AIMemory()
    memory.turn_plan = validated
    memory._turn_key = (turn.battle_round, "Player 2")
    # Only this squad may move, so the spy reports its option list and not a
    # neighbour's. moved_squad_ids holds SQUAD OBJECTS, not ids.
    for token in list(state.tokens):
        if token.squad is not squad and token.squad.owner == "Player 2":
            mover.moved_squad_ids.add(token.squad)
    real_choose, agent_driver._choose = agent_driver._choose, spy
    try:
        agent_driver._handle_movement(None, memory, "Player 2", state, mover,
                                      None, None, None, None, waaagh_controller=waaagh)
    finally:
        agent_driver._choose = real_choose
    advanced = any(t.startswith("advance") for t in seen.get("types", []))
    return survived, advanced, seen.get("descriptions", [])


def section_1():
    print("=" * 78)
    print("1. An order in the Advance band, through validator and tactical layer")
    print("=" * 78)
    print("   Each unit is ordered to a point M+3\" toward its nearest enemy - inside")
    print("   what an Advance reaches, outside what a plain move does.\n")
    print(f"   {'unit':<40} {'M':>3}  {'order survives':<20} {'Advance offered'}")
    now, pre = [], []
    for name in UNITS:
        state, _, _, _, squads = scene()
        move = min_model_movement(squads[name])
        survived, advanced, _ = chain(name, move + 3.0)
        now.append((name, move, survived, advanced))
    with plain_move_reach():
        for name in UNITS:
            state, _, _, _, squads = scene()
            move = min_model_movement(squads[name])
            survived, advanced, _ = chain(name, move + 3.0)
            pre.append((name, move, survived, advanced))
    for (name, move, s_now, a_now), (_, _, s_pre, a_pre) in zip(now, pre):
        print(f"   {name:<40} {move:>3.0f}  "
              f"{('yes' if s_now else 'CLAMPED') + ' (was ' + ('yes' if s_pre else 'CLAMPED') + ')':<20} "
              f"{('yes' if a_now else 'no') + ' (was ' + ('yes' if a_pre else 'no') + ')'}")
    print(f"\n   orders that survive validation:      {sum(1 for r in pre if r[2])}"
          f" -> {sum(1 for r in now if r[2])} of {len(now)}")
    print(f"   units offered an Advance afterwards: {sum(1 for r in pre if r[3])}"
          f" -> {sum(1 for r in now if r[3])} of {len(now)}")


# ------------------------------------------------- section 2: what it is worth

def section_2():
    print()
    print("=" * 78)
    print("2. What the extra D6 buys")
    print("=" * 78)
    print("   Charge chance from where the unit stood when that movement phase opened:")
    print("   plain move then charge, against Advance then charge. WAAAGH! is active,")
    print("   so rule 09.06's charge forfeit does not apply.\n")
    state, turn, waaagh, mover, squads = scene()
    print(f"   {'unit':<40} {'target':<22} {'gap':>6} {'plain':>7} {'advance':>8}")
    gains = []
    for name in UNITS:
        squad = squads[name]
        foe = nearest_foe(squad, squads)
        gap = squad.min_distance_to(foe)
        plain = observation.charge_now(squad, foe)
        after = observation.charge_chance_after_advancing(squad, foe)
        before = float(plain["chance_to_reach_it_this_turn"].rstrip("%"))
        gains.append(after - before)
        print(f"   {name:<40} {foe.name:<22} {gap:>5.1f}\" {before:>6.0f}% {after:>7.0f}%")
    print(f"\n   mean gain in charge probability: {sum(gains) / len(gains):+.0f} points")
    print(f"   biggest single gain:             {max(gains):+.0f} points")
    crossed = sum(1 for g, n in zip(gains, UNITS)
                  if g > 0 and float(observation.charge_now(
                      squads[n], nearest_foe(squads[n], squads)
                  )["chance_to_reach_it_this_turn"].rstrip("%")) < 50
                  and observation.charge_chance_after_advancing(
                      squads[n], nearest_foe(squads[n], squads)) >= 50)
    print(f"   coin-flip or worse turned into a favourite: {crossed} of {len(UNITS)}")


if __name__ == "__main__":
    section_1()
    section_2()
