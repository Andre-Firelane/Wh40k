"""The Orks army rules of the 2026-09 codex: Waaagh!, riled up, War Cry, Da Boss,
Unstable Energies, Special Move Types.

PRINTED (rules/orks/army_rules.md) - see game/waaagh.py, game/riled_up.py,
game/war_cry.py and game/unstable_energies.py for the text and the reasoning.

WHAT THIS SUITE HAS TO PROVE, and why each part is its own section:

  1. who has the ability - against EVERY printed FACTION line, not a list;
  2. riled up's two deadlines on the turn serial;
  3. the three riled-up effects through the REAL readers (the save, the
     [ASSAULT] gate a unit that Advanced asks, the charge gate) - a grant that
     reached only the adjuster chain is the bug this repo has shipped three times;
  4. that the old user-supplied Waaagh! (+1 S/+1 A, Krumpin' Time) is gone;
  5. War Cry: offered in EVERY Command phase, to Ork armies only, once per battle,
     reaching reserves too, surviving a save, expiring on the right turn;
  6. the AI's War Cry verdict at its decision boundaries;
  7. the Advance re-roll on the shared machinery;
  8. Unstable Energies' budget (dormant until the Kill Rig stage);
  9. Da Boss and the Special Move Types as documented no-ops, measured;
 10. what the planner is told;
 11. the wiring in main.py and the retired `waaagh=` threading, at the source.

Run: python test_ork_army_rules.py
"""
import ast
import importlib
import inspect
import io
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import testkit as tk  # noqa: E402
from testkit import Checks, GameState, TurnTracker, build_squad  # noqa: E402

from ai import agent_driver, observation  # noqa: E402
from game import (activation_state, coldstar, damage_resolution, decline_option,  # noqa: E402
                  feel_no_pain, invulnerable_save, maps, move_exceptions, riled_up,
                  rules_text, shooting, unstable_energies, waaagh, war_cry)
from game.charge import ChargeController  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.dice import ADVANCE_ROLL, DiceManager  # noqa: E402
from game.factions.faction import FACTIONS  # noqa: E402
from game.fight import FightController  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.shooting import ShootingController  # noqa: E402
from game.superlative_strategist import SuperlativeStrategistController  # noqa: E402
from game.turn import PHASES, PHASE_CHARGE, PHASE_COMMAND  # noqa: E402
from game.units import UnitProfile  # noqa: E402
from game.weapons import MELEE, RANGED  # noqa: E402

for _faction_module in ("aeldari", "death_guard", "necrons", "orks", "tau_empire"):
    importlib.import_module("game.factions." + _faction_module)

maps.apply_to_config(maps.get("map2"))
c = Checks("Orks army rules (Waaagh!, riled up, War Cry)")

ORK, FOE = "Player 2", "Player 1"
ORKS = FACTIONS["ORKS"]
NECRONS = FACTIONS["NECRONS"]


def sheet(name, faction=ORKS):
    return faction.datasheets[name]


def unit(name, owner=ORK, faction=ORKS, **kw):
    return build_squad(sheet(name, faction), owner, name="%s %s" % (owner[-1], name), **kw)


def tracker(phase=PHASE_COMMAND, owner=ORK, battle_round=1, first=ORK):
    t = TurnTracker(first_player=first)
    t.battle_round = battle_round
    t.turn_index_in_round = 0 if owner == first else 1
    t.phase_index = PHASES.index(phase)
    t.turn_owner = owner
    t.set_active(owner)
    return t


def advance(t, phases):
    for _ in range(phases):
        t.advance_phase()
    return t


def on_board(state, squad, x, y):
    tk.line_up(squad, x, y)
    for model in squad.models:
        state.add_token(model)
    return squad


# ===========================================================================
print("\n1. who has the Waaagh! ability")
# ===========================================================================
boyz = unit("Boyz")
warriors = unit("Necron Warriors", owner=FOE, faction=NECRONS, composition_index=0)
c.true("Boyz have the Waaagh! ability", waaagh.has_waaagh(boyz))
c.true("Necron Warriors do not", not waaagh.has_waaagh(warriors))
c.true("no squad has nothing", not waaagh.has_waaagh(None))
c.eq("qualifying_players() reads the armies", sorted(waaagh.qualifying_players([boyz, warriors])), [ORK])

# Against the PRINTED FACTION line of every built datasheet of every faction:
# a flag set on a sheet that does not print the rule, or missing from one that
# does, is the Battle Focus bug the Aeldari had - a rule silently widened or
# silently absent.
_waaagh_wrong, _ue_wrong, _checked, _ork_printed = [], [], 0, []
for _keyword, _faction in sorted(FACTIONS.items()):
    for _name, _ds in sorted(_faction.datasheets.items()):
        _path = rules_text.rules_path(_ds)
        if not _path or not os.path.exists(_path):
            continue
        _m = re.search(r"^FACTION: \*\*(.+?)\*\*", io.open(_path, encoding="utf-8").read(), re.M)
        _line = _m.group(1) if _m else ""
        _profiles = {line.profile_cls for option in (_ds.composition_options or [_ds.model_lines])
                     for line in option}
        _checked += 1
        _flags = [bool(getattr(p, "waaagh", False)) for p in _profiles]
        if ("Waaagh!" in _line) != (bool(_flags) and all(_flags)) or ("Waaagh!" not in _line and any(_flags)):
            _waaagh_wrong.append(_name)
        if _keyword == "ORKS":
            if "Waaagh!" in _line:
                _ork_printed.append(_name)
            _levels = [getattr(p, "psyker_level", 0) or 0 for p in _profiles]
            if ("Unstable Energies" in _line) != any(level > 0 for level in _levels):
                _ue_wrong.append(_name)
c.true("the sweep read every faction's sheets (%d)" % _checked, _checked > 100)
c.eq("every datasheet's waaagh flag matches its printed FACTION line", _waaagh_wrong, [])
c.eq("all 17 built Ork sheets print Waaagh!", len(_ork_printed), 17)
c.eq("...and every Ork psyker level matches a printed Unstable Energies", _ue_wrong, [])


# ===========================================================================
print("\n2. the turn serial and riled up's two deadlines")
# ===========================================================================
_t = TurnTracker(first_player=FOE)
c.eq("round 1's first turn is serial 0", riled_up.turn_serial(_t), 0)
advance(_t, len(PHASES))
c.eq("...its second turn is serial 1", riled_up.turn_serial(_t), 1)
advance(_t, len(PHASES))
c.eq("...and round 2's first turn is serial 2", riled_up.turn_serial(_t), 2)

_own = tracker(owner=ORK, battle_round=2, first=ORK)          # serial 2, Ork's turn
_theirs = tracker(owner=FOE, battle_round=2, first=ORK)       # serial 3, the foe's turn
c.eq("until the end of the NEXT turn is two turns out", riled_up.until_end_of_next_turn(_own), 4)
c.eq("until the start of YOUR next turn, from your own turn: two", riled_up.until_start_of_your_next_turn(_own, ORK), 4)
c.eq("...from your opponent's turn: ONE - the difference a flat +2 gets wrong",
     riled_up.until_start_of_your_next_turn(_theirs, ORK), 4)


# ===========================================================================
print("\n3. grant and refresh")
# ===========================================================================
_t = tracker(owner=ORK, battle_round=1, first=ORK)
_b = unit("Boyz")
c.true("a Necron unit cannot become riled up", not riled_up.grant(warriors, 2, _t))
c.true("...and is not", not riled_up.is_riled_up(warriors))
c.true("a Boyz mob can", riled_up.grant(_b, riled_up.until_end_of_next_turn(_t), _t))
c.true("...and is riled up in the same frame, before any phase change", riled_up.is_riled_up(_b))
advance(_t, len(PHASES))
riled_up.refresh([_b], _t)
c.true("still riled up through the next turn", riled_up.is_riled_up(_b))
advance(_t, len(PHASES))
riled_up.refresh([_b], _t)
c.true("...and not the turn after that", not riled_up.is_riled_up(_b))
c.eq("an expired deadline is cleared, not carried through every save", _b.riled_up_expires_turn, None)
_b2 = unit("Boyz")
riled_up.grant(_b2, 5)
riled_up.grant(_b2, 3)
c.eq("a second, shorter grant never shortens the first", _b2.riled_up_expires_turn, 5)
_w2 = unit("Necron Warriors", owner=FOE, faction=NECRONS, composition_index=0)
_w2.riled_up_expires_turn = 9
riled_up.refresh([_w2], tracker(owner=ORK, battle_round=1, first=ORK))
c.true("a deadline on a unit WITHOUT the ability (a load, a bug) is still not riled up",
       not riled_up.is_riled_up(_w2))


# ===========================================================================
print("\n4. the three riled-up effects, through the real readers")
# ===========================================================================
# --- (a) 5+ InSv
_model = _b2.models[0]
_b2.riled_up = False
_before = invulnerable_save.effective_invulnerable_save(_model)
_b2.riled_up = True
c.eq("riled up grants a 5+ invulnerable save", invulnerable_save.effective_invulnerable_save(_model), "5+")
c.true("...where the unit had none (%r)" % _before, _before in (None, "-"))


class _AP0Gun:
    ap = 0
    weapon_type = RANGED


c.eq("...and the Save roll resolves against it (save_thresholds)",
     damage_resolution.save_thresholds(_model, _AP0Gun())[1], 5)
_b2.riled_up = False
c.eq("...and not while it is not riled up",
     damage_resolution.save_thresholds(_model, _AP0Gun())[1], None)

# --- (b) [ASSAULT]: a unit whose ranged weapons carry NO printed [ASSAULT], so
# the gate cannot pass for any other reason.
_shooter = None
for _name in sorted(ORKS.datasheets):
    _candidate = unit(_name)
    _ranged = [w for m in _candidate.models for w in m.weapons if w.weapon_type == RANGED]
    if _ranged and not any(w.assault for w in _ranged) and len(_candidate.models) > 1:
        _shooter = _candidate
        break
c.true("the scene found an Ork unit with only non-[ASSAULT] ranged weapons (%s)"
       % (_shooter.name if _shooter else None), _shooter is not None)
_gun = next(w for m in _shooter.models for w in m.weapons if w.weapon_type == RANGED)
_melee = next((w for m in _shooter.models for w in m.weapons if w.weapon_type == MELEE), None)

c.true("not riled up: the gate says no [ASSAULT]", not coldstar.weapon_has_assault(_gun, _shooter))
riled_up.grant(_shooter, 9)
c.true("riled up: the gate says [ASSAULT]", coldstar.weapon_has_assault(_gun, _shooter))
_granted = riled_up.adjusted_weapon(_gun, _shooter)
c.true("the adjuster chain's copy has it too", _granted.assault and _granted is not _gun)
c.true("...and the shared weapon instance was not mutated", not _gun.assault)
if _melee is not None:
    c.true("a MELEE weapon is left exactly as it was", riled_up.adjusted_weapon(_melee, _shooter) is _melee)
_shooting_src = inspect.getsource(ShootingController._adjusted_weapon)
c.true("ShootingController._adjusted_weapon() chains it",
       "riled_up.adjusted_weapon(weapon, self.active_squad)" in _shooting_src)

_state = GameState()
on_board(_state, _shooter, 20.0, 20.0)
_foe = on_board(_state, unit("Necron Warriors", owner=FOE, faction=NECRONS, composition_index=0), 20.0, 28.0)
_mover = MovementController(obstacles=_state.obstacles, turn_tracker=tracker(phase=PHASE_CHARGE),
                            all_tokens=_state.tokens, dice_manager=DiceManager())
_mover.advanced_squad_ids.add(_shooter)
_shooter.riled_up = False
_types_plain = shooting.available_shooting_types(_shooter, _state.tokens, _mover)
_shooter.riled_up = True
_types_riled = shooting.available_shooting_types(_shooter, _state.tokens, _mover)
c.true("after an Advance, not riled up: no Assault shooting (%r)" % (_types_plain,),
       shooting.ASSAULT_SHOOTING not in _types_plain)
c.true("...riled up: Assault shooting is offered (%r)" % (_types_riled,),
       shooting.ASSAULT_SHOOTING in _types_riled)

# --- (c) an Advance does not stop a charge
_gap = _shooter.min_distance_to(_foe)
c.true("the charge scene is 2-12\" apart (%.1f)" % _gap, 2.0 < _gap < 12.0)
_charge = ChargeController(dice_manager=DiceManager(), turn_tracker=tracker(phase=PHASE_CHARGE),
                           all_tokens=_state.tokens, movement_controller=_mover)
_shooter.riled_up = False
c.true("not riled up: an Advanced unit may not charge", not _charge.can_declare_charge(_shooter))
_shooter.riled_up = True
c.true("riled up: it may", _charge.can_declare_charge(_shooter))
c.true("...answered by the shared exception", move_exceptions.may_charge_after_advancing(_shooter))


# ===========================================================================
print("\n5. the old user-supplied Waaagh! is gone")
# ===========================================================================
for _field in ("waaagh_biggest_and_best", "krumpin_time", "waaagh_dead_brutal_damage"):
    c.true("UnitProfile no longer carries %s" % _field, not hasattr(UnitProfile, _field))
_mega = unit("Meganobz")
riled_up.grant(_mega, 9)
c.eq("a riled-up Meganob has no Feel No Pain of the old Krumpin' Time",
     feel_no_pain.current_feel_no_pain(_mega.models[0]), _mega.models[0].profile.feel_no_pain)
for _cls in (ShootingController, FightController, ChargeController):
    c.true("%s takes no waaagh= argument" % _cls.__name__,
           "waaagh" not in inspect.signature(_cls.__init__).parameters)
c.true("the old controller is gone", not hasattr(waaagh, "WaaaghController"))
c.true("...and so are its melee riders",
       not any(hasattr(waaagh, n) for n in ("waaagh_extra_attacks", "waaagh_melee_adjusted_weapon",
                                             "effective_feel_no_pain", "squad_waaagh_active")))


# ===========================================================================
print("\n6. War Cry")
# ===========================================================================
def war_cry_scene(auto_players=(), verdict=None, owner=ORK, battle_round=1):
    state = GameState()
    mob = on_board(state, unit("Boyz"), 10.0, 10.0)
    reserve = unit("Stormboyz")                    # NOT on the board
    foe = on_board(state, unit("Necron Warriors", owner=FOE, faction=NECRONS, composition_index=0), 40.0, 40.0)
    squads = [mob, reserve, foe]
    t = tracker(owner=owner, battle_round=battle_round, first=ORK)
    decisions = DecisionManager()
    used = []
    ctrl = war_cry.WarCryController(turn_tracker=t, decision_manager=decisions,
                                    auto_players=auto_players, squads_provider=lambda: squads,
                                    verdict=verdict)
    ctrl.orks_players = waaagh.qualifying_players(squads)
    ctrl.on_used = used.append
    return dict(state=state, mob=mob, reserve=reserve, foe=foe, squads=squads, t=t,
                decisions=decisions, ctrl=ctrl, used=used)


_s = war_cry_scene()
c.eq("the Ork army's own Command phase: one prompt", _s["ctrl"].offer_at_start_of_command_phase(_s["t"]), 1)
c.eq("...to the Ork player", _s["decisions"].player, ORK)
_labels = [o["label"] for o in _s["decisions"].options]
c.eq("...Use or Decline", _labels, [war_cry.USE_LABEL, war_cry.DECLINE_LABEL])
c.true("...and Decline is drawn red, Use is not",
       decline_option.is_decline(_labels[1]) and not decline_option.is_decline(_labels[0]))
c.true("...and the prompt names War Cry", "War Cry" in _s["decisions"].prompt)
_s["decisions"].choose(1)
c.true("declining changes nothing", not riled_up.is_riled_up(_s["mob"]) and not _s["ctrl"].is_used(ORK))
c.eq("...and the next Command phase asks again", _s["ctrl"].offer_at_start_of_command_phase(_s["t"]), 1)
_s["decisions"].choose(0)
c.true("using it: the mob on the board is riled up", riled_up.is_riled_up(_s["mob"]))
c.true("...the unit in Strategic Reserves too", riled_up.is_riled_up(_s["reserve"]))
c.true("...the enemy is not", not riled_up.is_riled_up(_s["foe"]))
c.eq("on_used named the player", _s["used"], [ORK])
c.eq("once per battle: no further prompt", _s["ctrl"].offer_at_start_of_command_phase(_s["t"]), 0)
c.true("...and use() refuses a second time", not _s["ctrl"].use(ORK))

# None means "nobody told me" and lifts the gate; an EMPTY set is a real answer.
_s = war_cry_scene()
_s["ctrl"].orks_players = frozenset()
c.eq("an EMPTY set of Ork players is an answer, not 'unknown': nobody is asked",
     _s["ctrl"].offer_at_start_of_command_phase(_s["t"]), 0)
c.true("...and nobody can use it", not _s["ctrl"].use(ORK))

# THE Command phase - the opponent's too.
_s = war_cry_scene(owner=FOE)
c.eq("the OPPONENT'S Command phase still asks the Ork army",
     _s["ctrl"].offer_at_start_of_command_phase(_s["t"]), 1)
c.eq("...and asks nobody else", _s["decisions"].player, ORK)
_s["decisions"].choose(0)
_t = _s["t"]
advance(_t, len(PHASES)); riled_up.refresh(_s["squads"], _t)
c.true("used in the enemy's turn, the army is riled up into its own", riled_up.is_riled_up(_s["mob"]))
advance(_t, len(PHASES)); riled_up.refresh(_s["squads"], _t)
c.true("...and no longer the turn after", not riled_up.is_riled_up(_s["mob"]))

# Used at the start of its own Command phase: its own turn and the enemy's.
_s = war_cry_scene(owner=ORK)
_s["ctrl"].use(ORK, _s["t"])
_t = _s["t"]
advance(_t, len(PHASES)); riled_up.refresh(_s["squads"], _t)
c.true("used in its own turn: still riled up in the enemy's", riled_up.is_riled_up(_s["mob"]))
advance(_t, len(PHASES)); riled_up.refresh(_s["squads"], _t)
c.true("...and not in its own next turn", not riled_up.is_riled_up(_s["mob"]))

# A Necron army is never asked, and cannot use it.
_s = war_cry_scene()
_s["ctrl"].offer_at_start_of_command_phase(_s["t"])
c.true("the Necron player is never asked",
       all(entry["player"] == ORK for entry in _s["decisions"]._queue))
c.true("...and cannot use it", not _s["ctrl"].use(FOE))

# Saved: the spend comes back with the units.
_s = war_cry_scene()
_s["ctrl"].use(ORK, _s["t"])
_data = activation_state.capture(_s["squads"])
_fresh = [unit("Boyz"), unit("Stormboyz"),
          unit("Necron Warriors", owner=FOE, faction=NECRONS, composition_index=0)]
for _old, _new in zip(_s["squads"], _fresh):
    _new.name = _old.name
activation_state.restore(_data, _fresh)
_loaded = war_cry.WarCryController(squads_provider=lambda: _fresh)
c.true("after a load, War Cry is still spent", _loaded.is_used(ORK))
c.true("...the derived flag is not saved", not riled_up.is_riled_up(_fresh[0]))
riled_up.refresh(_fresh, _s["t"])
c.true("...and a refresh puts it back from the saved deadline", riled_up.is_riled_up(_fresh[0]))

# The AI answers in the controller, through the injected verdict.
_calls = []
_s = war_cry_scene(auto_players=(ORK,), verdict=lambda p, t: _calls.append((p, t)) or False)
c.eq("an AI player gets no prompt", _s["ctrl"].offer_at_start_of_command_phase(_s["t"]), 0)
c.eq("...its verdict is asked with (player, tracker)", _calls, [(ORK, _s["t"])])
c.true("...and a 'no' spends nothing", not _s["ctrl"].is_used(ORK))
_s = war_cry_scene(auto_players=(ORK,), verdict=lambda p, t: True)
_s["ctrl"].offer_at_start_of_command_phase(_s["t"])
c.true("a 'yes' uses it, still without a prompt",
       _s["ctrl"].is_used(ORK) and not _s["decisions"].is_pending and riled_up.is_riled_up(_s["mob"]))


# ===========================================================================
print("\n7. the AI's War Cry verdict")
# ===========================================================================
def verdict_scene(close_units, far_units, gap_in, owner=ORK, battle_round=1):
    state = GameState()
    foe = on_board(state, unit("Necron Warriors", owner=FOE, faction=NECRONS, composition_index=0), 10.0, 40.0)
    top = min(m.y_in for m in foe.models)
    for i in range(close_units):
        mob = unit("Boyz")
        mob.name = "2 Boyz close %d" % i
        on_board(state, mob, 10.0 + i * 16.0, 0.0)
        shift = (top - gap_in) - max(m.y_in for m in mob.models)
        for m in mob.models:
            m.y_in += shift
    for i in range(far_units):
        mob = unit("Boyz")
        mob.name = "2 Boyz far %d" % i
        on_board(state, mob, 10.0 + i * 16.0, -60.0)
    return state, tracker(owner=owner, battle_round=battle_round, first=ORK)


_st, _tt = verdict_scene(close_units=2, far_units=1, gap_in=20.0)
_close = [s for s in {t.squad for t in _st.tokens} if "close" in s.name]
_enemy = next(s for s in {t.squad for t in _st.tokens} if s.owner == FOE)
c.true("the verdict scene puts the close mobs 18-21.5\" away",
       all(18.0 < s.min_distance_to(_enemy) < observation.advance_reach_in(s) + 12.0 for s in _close))
c.true("own Command phase: 2 of 3 Waaagh! units within Move+Advance+12\" - use it",
       agent_driver.war_cry_verdict(ORK, _tt, _st.tokens))
_st, _tt = verdict_scene(close_units=2, far_units=1, gap_in=20.0, owner=FOE)
c.true("the SAME board in the enemy's Command phase: outside 18\" - keep it",
       not agent_driver.war_cry_verdict(ORK, _tt, _st.tokens))
_st, _tt = verdict_scene(close_units=2, far_units=1, gap_in=15.0, owner=FOE)
c.true("...within 18\" in the enemy's Command phase - use it",
       agent_driver.war_cry_verdict(ORK, _tt, _st.tokens))
_st, _tt = verdict_scene(close_units=1, far_units=4, gap_in=15.0)
c.true("one unit of five is not enough", not agent_driver.war_cry_verdict(ORK, _tt, _st.tokens))
_st, _tt = verdict_scene(close_units=2, far_units=4, gap_in=20.0)
c.true("two of six is below the 40% share (three are needed) - keep it",
       not agent_driver.war_cry_verdict(ORK, _tt, _st.tokens))
_st, _tt = verdict_scene(close_units=1, far_units=0, gap_in=15.0)
c.true("...but an army down to that one unit is", agent_driver.war_cry_verdict(ORK, _tt, _st.tokens))
_st, _tt = verdict_scene(close_units=0, far_units=3, gap_in=15.0, battle_round=2)
c.true("nothing in reach in round 2: keep it", not agent_driver.war_cry_verdict(ORK, _tt, _st.tokens))
_st, _tt = verdict_scene(close_units=0, far_units=3, gap_in=15.0, battle_round=3)
c.true("...in round 3 it is used anyway, never simply left unused",
       agent_driver.war_cry_verdict(ORK, _tt, _st.tokens))
_st, _tt = verdict_scene(close_units=0, far_units=3, gap_in=15.0, battle_round=3, owner=FOE)
c.true("...but only in its OWN Command phase", not agent_driver.war_cry_verdict(ORK, _tt, _st.tokens))
c.eq("the verdict takes no agent - 0 API calls by construction",
     list(inspect.signature(agent_driver.war_cry_verdict).parameters), ["player", "turn_tracker", "all_tokens"])


# ===========================================================================
print("\n8. the Advance re-roll")
# ===========================================================================
_dice = tk.RecordingDice()
_ai = waaagh.WaaaghAdvanceRerollController(dice_manager=_dice, game_log=tk.Log(), auto_players=(ORK,))
tk.script(2, 5)
_dice.roll(1, label="Advance", roll_kind=ADVANCE_ROLL)
c.true("the AI re-rolls a 2", _ai.maybe_offer_advance_reroll(boyz))
c.eq("...and the die really changed", _dice.pending_values, [5])
_dice = tk.RecordingDice()
_ai = waaagh.WaaaghAdvanceRerollController(dice_manager=_dice, game_log=tk.Log(), auto_players=(ORK,))
tk.script(5, 1)
_dice.roll(1, label="Advance", roll_kind=ADVANCE_ROLL)
c.true("...and keeps a 5", not _ai.maybe_offer_advance_reroll(boyz))
c.eq("...untouched", _dice.pending_values, [5])
_dice = tk.RecordingDice()
_human = waaagh.WaaaghAdvanceRerollController(dice_manager=_dice, decision_manager=DecisionManager())
tk.script(1)
_dice.roll(1, label="Advance", roll_kind=ADVANCE_ROLL)
c.eq("a Necron unit is offered nothing", _human.pending_roll_choice(warriors), None)
_choice = _human.pending_roll_choice(boyz)
c.true("a human's Ork unit gets a Re-roll Advance button",
       _choice is not None and any(o.label == "Re-roll Advance" for o in _choice.options))
c.true("the prompt path asks once per roll", _human.maybe_offer_advance_reroll(boyz))
c.true("...and not twice", not _human.maybe_offer_advance_reroll(boyz))
c.eq("the Autarch's offer is the same machine under its own label",
     (issubclass(SuperlativeStrategistController, type(_human).__mro__[1]),
      SuperlativeStrategistController.LABEL), (True, "Superlative Strategist"))


# ===========================================================================
print("\n9. Unstable Energies")
# ===========================================================================
_rig = unit("Kill Rig")
c.eq("the Kill Rig prints psyker level 1", unstable_energies.psyker_level(_rig), 1)
c.eq("a Boyz mob has none", unstable_energies.psyker_level(boyz), 0)
c.true("a level-1 ability fits the budget", unstable_energies.can_use(_rig, 1, 1))
c.true("...is spent", unstable_energies.spend(_rig, 1, 1))
c.true("...and a second one does not fit that round", not unstable_energies.spend(_rig, 1, 1))
c.true("the next battle round starts the count again", unstable_energies.can_use(_rig, 1, 2))
c.true("no psyker, no budget", not unstable_energies.can_use(boyz, 1, 1))


# ===========================================================================
print("\n10. Da Boss and the Special Move Types: documented no-ops, measured")
# ===========================================================================
_warlord_names = []
for _root in ("game", "ai"):
    for _dp, _dirs, _files in os.walk(_root):
        for _f in _files:
            if not _f.endswith(".py"):
                continue
            for _n in ast.walk(ast.parse(io.open(os.path.join(_dp, _f), encoding="utf-8").read())):
                _ident = (getattr(_n, "id", None) or getattr(_n, "attr", None) or getattr(_n, "arg", None)
                          or (_n.name if isinstance(_n, (ast.FunctionDef, ast.ClassDef)) else None))
                if isinstance(_ident, str) and "warlord" in _ident.lower():
                    _warlord_names.append("%s:%s" % (_f, _ident))
c.eq("Da Boss: this engine has no Warlord to gain a CP for", _warlord_names, [])
_army_text = io.open(os.path.join("rules", "orks", "army_rules.md"), encoding="utf-8").read().lower()
c.true("the army rules really print both Special Move Types",
       "pulse jet move" in _army_text and "assault disembark move" in _army_text)
_movers = [n for n in sorted(ORKS.datasheets)
           if re.search(r"pulse jet move|assault disembark",
                        io.open(rules_text.rules_path(ORKS.datasheets[n]), encoding="utf-8").read(), re.I)]
c.eq("...and no built Ork datasheet points at either, so there is nothing to build", _movers, [])


# ===========================================================================
print("\n11. what the planner is told")
# ===========================================================================
_b3 = unit("Boyz")
c.true("a unit that is not riled up carries no key", "riled_up" not in observation.squad_summary(_b3))
riled_up.grant(_b3, 9)
c.true("a riled-up unit says so", "riled_up" in observation.squad_summary(_b3))
c.eq("no controller, no War Cry field", observation.war_cry_summary(ORK, None), None)
_s = war_cry_scene()
c.eq("a non-Ork army gets no War Cry field", observation.war_cry_summary(FOE, _s["ctrl"]), None)
c.eq("an unused War Cry is still available",
     observation.war_cry_summary(ORK, _s["ctrl"])["riled_up_now"], False)
_s["ctrl"].use(ORK, _s["t"])
c.eq("the riled-up turn is flagged", observation.war_cry_summary(ORK, _s["ctrl"])["riled_up_now"], True)


# ===========================================================================
print("\n12. wiring, at the source")
# ===========================================================================
MAIN_SRC = io.open("main.py", encoding="utf-8").read()
MAIN_TREE = ast.parse(MAIN_SRC)


def statement_calls(tree, src):
    """Every call that is a whole STATEMENT - so a call hidden behind
    `False and ...` or in a comment does not count."""
    return [ast.get_source_segment(src, n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)]


_calls_main = statement_calls(MAIN_TREE, MAIN_SRC)
c.true("riled up is re-stamped at every phase start, at battle start and after a load (%d)"
       % _calls_main.count("riled_up.refresh(state.all_squads(), turn_tracker)"),
       _calls_main.count("riled_up.refresh(state.all_squads(), turn_tracker)") >= 3)
_stamp = MAIN_SRC.find("power_matrix_controller.stamp_at_start_of_phase()")
_refresh = MAIN_SRC.find("riled_up.refresh(state.all_squads(), turn_tracker)", _stamp)
_offer = MAIN_SRC.find("war_cry_controller.offer_at_start_of_command_phase(turn_tracker)", _stamp)
c.true("...at the start of a phase: stamp, then War Cry's offer", 0 <= _stamp < _refresh < _offer)
c.eq("War Cry is offered as a statement twice: the battle's first Command phase and every later one",
     _calls_main.count("war_cry_controller.offer_at_start_of_command_phase(turn_tracker)"), 2)

_begin = next(n for n in ast.walk(MAIN_TREE) if isinstance(n, ast.FunctionDef) and n.name == "begin_battle")
c.true("begin_battle() takes resuming=", "resuming" in [a.arg for a in _begin.args.args])
_guarded = [n for n in ast.walk(_begin) if isinstance(n, ast.If)
            and ast.get_source_segment(MAIN_SRC, n.test) == "not resuming"
            and "war_cry_controller.offer_at_start_of_command_phase" in ast.get_source_segment(MAIN_SRC, n)]
c.true("...and offers War Cry for the first Command phase only when not resuming", len(_guarded) == 1)
c.true("the load path resumes", "resuming=True)" in MAIN_SRC)
c.true("the Advance re-roll is offered before acknowledge()",
       "waaagh_advance_reroll_controller.maybe_offer_advance_reroll(_adv_squad)" in _calls_main)
c.true("...and the dice panel shows its button",
       "lambda: waaagh_advance_reroll_controller.pending_roll_choice(movement_controller.selected_squad)" in MAIN_SRC)
_take = [n for n in ast.walk(MAIN_TREE) if isinstance(n, ast.Call)
         and getattr(n.func, "id", None) == "take_one_action"]
c.true("take_one_action() is handed the War Cry controller",
       any(kw.arg == "war_cry_controller" for n in _take for kw in n.keywords))
_orks_assign = [n for n in ast.walk(MAIN_TREE) if isinstance(n, ast.Assign)
                and any(ast.get_source_segment(MAIN_SRC, t) == "war_cry_controller.orks_players"
                        for t in n.targets)]
c.true("War Cry learns WHOSE army rule it is from the built armies",
       len(_orks_assign) == 1 and isinstance(_orks_assign[0].value, ast.Call)
       and ast.get_source_segment(MAIN_SRC, _orks_assign[0].value.func) == "waaagh_module.qualifying_players")
_verdict_kw = [kw.value for n in ast.walk(MAIN_TREE) if isinstance(n, ast.Call)
               and getattr(n.func, "id", None) == "WarCryController"
               for kw in n.keywords if kw.arg == "verdict"]
c.true("...and the AI's answer is war_cry_verdict, injected as a lambda",
       len(_verdict_kw) == 1 and isinstance(_verdict_kw[0], ast.Lambda)
       and "war_cry_verdict(" in ast.get_source_segment(MAIN_SRC, _verdict_kw[0]))

_waaagh_threads = []
for _root in ("game", "ai"):
    for _dp, _dirs, _files in os.walk(_root):
        for _f in _files:
            if _f.endswith(".py"):
                _paths = os.path.join(_dp, _f)
                for _n in ast.walk(ast.parse(io.open(_paths, encoding="utf-8").read())):
                    if isinstance(_n, ast.keyword) and _n.arg in ("waaagh", "waaagh_controller"):
                        _waaagh_threads.append("%s: %s=" % (_f, _n.arg))
                    if isinstance(_n, ast.arg) and _n.arg in ("waaagh", "waaagh_controller"):
                        _waaagh_threads.append("%s: parameter %s" % (_f, _n.arg))
for _n in ast.walk(MAIN_TREE):
    if isinstance(_n, ast.keyword) and _n.arg in ("waaagh", "waaagh_controller"):
        _waaagh_threads.append("main.py: %s=" % _n.arg)
c.eq("no waaagh= threading survives anywhere", _waaagh_threads, [])
c.true("the AI's round-2 policy is gone", not hasattr(agent_driver, "_maybe_call_waaagh"))

for _field in ("riled_up_expires_turn", "war_cry_called", "unstable_energies_round", "unstable_energies_spent"):
    c.true("%s is saved" % _field, _field in activation_state.SQUAD_FLAGS)
c.true("riled_up is derived, not saved", "riled_up" in activation_state.SQUAD_FLAGS_EXCLUDED)

c.finish()
