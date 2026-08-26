"""Rangers - statline, weapons, and Path of the Outcast.

TWO PRINTED VALUES HERE LOOK LIKE TRANSCRIPTION ERRORS AND ARE NOT, which is
why both were confirmed with a second targeted lookup and are pinned here:

  * the Shuriken Pistol is BS2+ while the model and its Long Rifle are 3+ - a
    pistol more accurate than a sniper rifle;
  * the invulnerable save applies against RANGED attacks only, so there is no
    save at all against melee ones.

Path of the Outcast is a reactive Normal move in the OPPONENT's Movement phase,
so it is checked through the real MovementController - including the turn-owner
flip, which is the trap Battle Focus' own reactive moves documented.
"""

import io

import testkit as tk
from game import invulnerable_save as inv
from game import path_of_the_outcast as poto
from game import status_effects
from game.factions import aeldari as ae
from game.factions import orks as ork
from game.factions import tau_empire as tau
from game.turn import PHASE_MOVEMENT
from game.units import RangerProfile

checks = tk.Checks("Rangers")


def rangers(composition_index=0, name="1 Rangers 1"):
    return tk.build(ae.RANGERS, "Player 1", name=name, composition_index=composition_index)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

five = rangers()
ten = rangers(composition_index=1)
checks.eq("5 models", len(five.models), 5)
checks.eq("10 models", len(ten.models), 10)
checks.eq("...cost 60", five.points, 60)
checks.eq("...and 110", ten.points, 110)

p = RangerProfile()
checks.eq("M7\"", p.movement_in, 7)
checks.eq("T3", p.toughness, 3)
checks.eq("Sv5+", p.armor_save, "5+")
checks.eq("W1", p.wounds, 1)
checks.eq("Ld7+", p.leadership, "7+")
checks.eq("OC1", p.oc, 1)
checks.eq("BS3+ / WS3+", (p.ballistic_skill, p.weapon_skill), ("3+", "3+"))
checks.eq("28.5 mm base -> 0.561\"", p.base_radius_in, round(28.5 / 2 / 25.4, 3))
checks.true("INFANTRY", p.infantry)
checks.true("Battle Focus", p.battle_focus)
checks.true("CORE: Infiltrators (24.20)", p.infiltrators)
checks.true("CORE: Stealth (24.33)", p.stealth)
checks.eq("no Scouts", p.scouts, None)
checks.eq("no LEADER ability", getattr(p, "leader", False), False)
checks.eq("no wargear options at all", list(ae.RANGERS.wargear_options), [])


# --- 2. the invulnerable save is RANGED-ONLY -------------------------------
print("--- 2. ranged-only invulnerable save ---")

# Measured through the real effective_invulnerable_save(), which takes the
# attack type from the weapon the Save roll is being made against.
model = five.models[0]
checks.eq("no plain invulnerable save is printed", p.invulnerable_save, "-")
checks.eq("...but 5+ against a RANGED attack",
          inv.effective_invulnerable_save(model, melee=False), "5+")
checks.eq("...and nothing against a MELEE one",
          inv.effective_invulnerable_save(model, melee=True), "-")
# The mirror clause it was built from still works the other way round.
banshee = tk.build(ae.HOWLING_BANSHEES, "Player 1", name="1 Howling Banshees 1").models[1]
checks.eq("A/B: the Banshees' melee-only clause is unaffected - 5+ ranged",
          inv.effective_invulnerable_save(banshee, melee=False), "5+")
checks.eq("...4+ melee", inv.effective_invulnerable_save(banshee, melee=True), "4+")


# --- 3. weapons -------------------------------------------------------------
print("--- 3. weapons ---")


def weapon(squad, name):
    return next(w for w in squad.models[0].weapons if w.name == name)


checks.eq("three weapons, no options",
          sorted(w.name for w in five.models[0].weapons),
          ["Close Combat Weapon", "Long Rifle", "Shuriken Pistol"])

rifle = weapon(five, "Long Rifle")
checks.eq("Long Rifle: 36\"/A1/S4/AP-1/D2",
          (rifle.range_in, rifle.attacks, rifle.strength, rifle.ap, rifle.damage),
          (36, 1, 4, -1, 2))
checks.true("...[HEAVY] (24.16)", rifle.heavy)
checks.true("...[PRECISION] (24.28)", rifle.precision)
checks.eq("...BS3+", rifle.ballistic_skill, "3+")

pistol = weapon(five, "Shuriken Pistol")
checks.eq("the Shuriken Pistol is BS2+ - better than the model and the rifle",
          pistol.ballistic_skill, "2+")
checks.true("...which is why it needed its own class, not the shared profile",
            type(pistol).__name__ == "RangerShurikenPistolProfile")
checks.eq("...with the shared numbers otherwise",
          (pistol.range_in, pistol.strength, pistol.ap, pistol.damage), (12, 4, -1, 1))
checks.true("...still [ASSAULT] + [PISTOL]", pistol.assault and pistol.pistol)

ccw = weapon(five, "Close Combat Weapon")
checks.eq("the close combat weapon is the shared A1/S3 Aeldari row",
          type(ccw).__name__, "AeldariCloseCombatWeaponProfile")

# THE two long rifles are not the same weapon - pinned as a comparison,
# because two weapons sharing a name is where a keyword gets copied across.
runner_rifle = next(w for w in tk.build(ae.SHROUD_RUNNERS, "Player 1",
                                        name="1 Shroud Runners 1").models[0].weapons
                    if w.name == "Long Rifle")
checks.true("the Shroud Runners' Long Rifle has the same name...",
            runner_rifle.name == rifle.name)
checks.eq("...and the same S/AP/D",
          (runner_rifle.strength, runner_rifle.ap, runner_rifle.damage),
          (rifle.strength, rifle.ap, rifle.damage))
checks.eq("...but NOT [HEAVY], which this one has", runner_rifle.heavy, False)
checks.true("...and a better BS", runner_rifle.ballistic_skill == "2+")


# --- 4. Path of the Outcast -------------------------------------------------
print("--- 4. Path of the Outcast ---")

from game.decision import DecisionManager  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.movement import MovementController  # noqa: E402


def outcast_scene(gap=6.0, engaged=False):
    """Rangers of Player 1, an Ork mob of Player 2 - and it is PLAYER 2's
    Movement phase, because that is when this ability fires."""
    state = GameState()
    squad = rangers()
    mover = tk.build(ork.BOYZ, "Player 2", name="2 Boyz 1")
    tk.line_up(squad, y=20.0)
    tk.line_up(mover, y=20.0 + (1.0 if engaged else gap))
    for s in (squad, mover):
        for m in s.models:
            state.add_token(m)
    tt = tk._tracker(PHASE_MOVEMENT, owner="Player 2")
    log, dice, dec = tk.Log(), tk.RecordingDice(), DecisionManager()
    mv = MovementController([], log, "Player 2", dice, tt, state.tokens)
    ctrl = poto.PathOfTheOutcastController(
        movement_controller=mv, decision_manager=dec, dice_manager=dice,
        turn_tracker=tt, game_log=log, all_squads=lambda: [squad, mover],
    )
    return dict(state=state, squad=squad, mover=mover, ctrl=ctrl, mv=mv,
                dice=dice, decision=dec, turn=tt, log=log)


checks.true("the profile carries the ability", p.path_of_the_outcast)
checks.eq("...and nothing else does",
          poto.applies(tk.build(tau.KROOT_CARNIVORES, "Player 2", name="K")), False)

near = outcast_scene(gap=6.0)
checks.eq("an enemy ending a move within 9\" makes this unit a candidate",
          [s.name for s in near["ctrl"].reacting_squads(near["mover"])], [near["squad"].name])
far = outcast_scene(gap=20.0)
checks.eq("...beyond 9\" it is not",
          far["ctrl"].reacting_squads(far["mover"]), [])
stuck = outcast_scene(engaged=True)
checks.eq("...and neither is one within Engagement Range",
          stuck["ctrl"].reacting_squads(stuck["mover"]), [])

# The trigger raises a decision, and it belongs to the REACTING player even
# though it is the opponent's turn.
near["ctrl"].offer_after_move(near["mover"], "normal")
checks.true("the trigger raises a decision", near["decision"].is_pending)
checks.eq("...owned by the reacting player", near["decision"].player, "Player 1")
labels = tk.options_of(near["decision"])
checks.true("...offering the move", any("D6" in l for l in labels))
checks.true("...and declining it", any("Stay" in l for l in labels))

# Declining does nothing at all.
skip = outcast_scene()
skip["ctrl"].offer_after_move(skip["mover"], "normal")
tk.pick_option(skip["decision"], "Stay")
checks.eq("declining opens no move", skip["mv"].move_mode, None)

# Accepting rolls a D6 and then opens a Normal move of that many inches.
go = outcast_scene()
before = [(m.x_in, m.y_in) for m in go["squad"].models]
go["ctrl"].offer_after_move(go["mover"], "normal")
tk.script(4, default=4)
tk.pick_option(go["decision"], "D6")
checks.true("accepting rolls a die first", go["dice"].is_pending)
go["dice"].acknowledge()
go["ctrl"].on_dice_acknowledged()
checks.eq("...and then opens the move", go["mv"].move_mode, poto.PATH_OF_THE_OUTCAST_MOVE_MODE)
checks.eq("...for exactly the rolled distance",
          round(go["mv"].remaining_range[go["squad"].models[0].id], 3), 4.0)
# THE TRAP: select() refuses a unit whose owner is not active_player outside
# the Fight phase, and this happens in the opponent's turn.
checks.eq("active_player is flipped to the reacting player",
          go["turn"].active_player, "Player 1")
checks.eq("...while the turn OWNER is untouched", go["turn"].turn_owner, "Player 2")

# The move really moves, and confirming hands the turn back.
# Every model moves the same 3", which is a rigid translation and so keeps
# rule 09.02's coherency intact - a single model would break it and the
# confirm would (correctly) refuse.
for model in go["squad"].models:
    model.x_in, model.y_in = go["mv"].clamp_move(model, model.x_in, model.y_in - 3.0)
    go["mv"].try_commit_segment(model)
go["ctrl"].confirm_move()
checks.eq("...and the move confirms cleanly", go["mv"].errors, [])
after = [(m.x_in, m.y_in) for m in go["squad"].models]
checks.true("the unit actually moved", before != after)
checks.eq("confirming hands active_player back", go["turn"].active_player, "Player 2")
checks.eq("...and closes the move", go["mv"].move_mode, None)

# Cancelling hands it back too.
back = outcast_scene()
back["ctrl"].offer_after_move(back["mover"], "normal")
tk.script(3, default=3)
tk.pick_option(back["decision"], "D6")
back["dice"].acknowledge()
back["ctrl"].on_dice_acknowledged()
back["ctrl"].cancel_move()
checks.eq("cancelling hands active_player back", back["turn"].active_player, "Player 2")

# It is NOT a Movement-phase move, so it must not be booked as one.
checks.eq("the reactive move is not recorded as this turn's Movement-phase move",
          go["squad"] in go["mv"].moved_squad_ids, False)


# --- 4b. the supplied rule text: 9", once per turn ---------------------------
print('--- 4b. 9" and once per turn ---')

# User-supplied wording (this project's source of truth): "Once per turn, when
# an enemy unit ends a Normal, Advance or Fall Back move within 9" of this
# unit, it can make a Normal move of up to D6"." The module used to say 8" and
# had no once-per-turn limit at all.
checks.eq("the range is the supplied 9 inches", poto.PATH_OF_THE_OUTCAST_RANGE_IN, 9.0)

# The band the correction actually opened up, measured rather than assumed:
# an enemy that ends its move between 8" and 9" away used to be ignored.
band = outcast_scene(gap=9.6)
edge = band["squad"].min_distance_to(band["mover"])
checks.true(f"the probe really sits in the 8-9 inch band (edge {edge:.2f}\")",
            8.0 < edge <= 9.0)
checks.eq("...and an enemy there now triggers the ability",
          [sq.name for sq in band["ctrl"].reacting_squads(band["mover"])],
          [band["squad"].name])

# "Once per turn" - spent on ACCEPTING, not on being asked.
once = outcast_scene()
once["ctrl"].offer_after_move(once["mover"], "normal")
tk.script(3, default=3)
tk.pick_option(once["decision"], "D6")
once["dice"].acknowledge()
once["ctrl"].on_dice_acknowledged()
once["ctrl"].cancel_move()
checks.eq("a unit that used it is no longer a candidate this turn",
          once["ctrl"].reacting_squads(once["mover"]), [])
once["ctrl"].offer_after_move(once["mover"], "normal")
checks.eq("...so a second enemy move raises nothing", once["decision"].is_pending, False)
once["ctrl"].reset_for_new_turn()
checks.eq("...and the next turn gives it back",
          [sq.name for sq in once["ctrl"].reacting_squads(once["mover"])],
          [once["squad"].name])

# Declining is an answer, not a use: the unit must still be able to react to
# the NEXT enemy that ends a move nearby.
nope = outcast_scene()
nope["ctrl"].offer_after_move(nope["mover"], "normal")
tk.pick_option(nope["decision"], "Stay")
checks.eq("declining does not burn the once-per-turn use",
          [sq.name for sq in nope["ctrl"].reacting_squads(nope["mover"])],
          [nope["squad"].name])


# --- 4c. WIRING: main.py has to actually feed this controller ---------------
print("--- 4c. wiring in main.py ---")

# THE BUG THIS SECTION EXISTS FOR, user-reported: "die KI laesst mich mit den
# Rangern immer noch nicht bewegen."
#
# Every check in section 4 above passed while the ability was unusable in the
# real game, because they call ctrl.on_dice_acknowledged() themselves. main.py
# did not. The offer appeared, the D6 was rolled and acknowledged, and nobody
# told the controller - so _start_move() was never reached and the Rangers
# never became movable. A controller that is constructed and never FED is
# invisible to every test that drives it directly; this project has now hit
# that exact class three times (see CLAUDE.md and verify_mark_wiring.py).
main_src = io.open("main.py", encoding="utf-8").read()

# 1. the D6 acknowledgement - the missing call itself.
ack_block = main_src[main_src.index("movement_controller.on_dice_acknowledged()"):]
ack_block = ack_block[:ack_block.index("pregame_controller.on_dice_acknowledged()")]
checks.true("main.py notifies the controller when the D6 is acknowledged",
            "path_of_the_outcast_controller.on_dice_acknowledged()" in ack_block)

# 2. Confirm/Cancel have to reach the controller that owns the consequences
#    (handing turn_tracker.active_player back), not the bare movement one.
checks.eq("main.py hands the controller to the action panel",
          main_src.count("path_of_the_outcast_controller=path_of_the_outcast_controller"), 1)
panel_src = io.open("game/ui/action_panel.py", encoding="utf-8").read()
checks.true("the panel routes Confirm to it",
            "confirm_callback = path_of_the_outcast_controller.confirm_move" in panel_src)
checks.true("...and Cancel too",
            "cancel_callback = path_of_the_outcast_controller.cancel_move" in panel_src)

# 3. the phase must not advance out from under an open offer/move, or
#    active_player stays stranded on the reacting player.
checks.true("an open Path of the Outcast blocks the phase from advancing",
            "or path_of_the_outcast_controller.is_busy" in main_src)

# 4. "once per turn" needs a turn boundary to reset at.
checks.true("main.py resets the once-per-turn use each turn",
            "path_of_the_outcast_controller.reset_for_new_turn()" in main_src)


# --- 5. A/B probe -----------------------------------------------------------
print("--- 5. A/B probe ---")

original = poto.applies
poto.applies = lambda squad: False
probe = outcast_scene()
probe["ctrl"].offer_after_move(probe["mover"], "normal")
checks.eq("A/B: unwired, the same move raises nothing", probe["decision"].is_pending, False)
poto.applies = original
restored = outcast_scene()
restored["ctrl"].offer_after_move(restored["mover"], "normal")
checks.true("A/B: restored", restored["decision"].is_pending)


# --- 5b. the AI must hold still while this move is open ---------------------
print("--- 5b. the AI waits for the human's move ---")

# USER REPORT, and the second time in the same words: "ranger / gleiches
# problem, wie damals bei fade back. die ki laesst mich nicht bewegen und macht
# gleich weiter."
#
# The shape is the one Battle Focus already documented. The DecisionManager
# window that offers this manoeuvre closes the instant it is accepted; all that
# leaves behind is an OPEN move the human still has to drag and confirm, during
# the AI's own turn. So decision_manager.is_pending is already False,
# turn_owner is already the AI, and unless something looks at the open move
# itself the AI simply carries on.
#
# ai/agent_driver.py's _is_blocked() DID look - and compared move_mode to the
# single string "battle_focus", which this ability is not. Hence
# MovementController.REACTIVE_MOVE_MODES: one definition, on the one method
# both manoeuvres come through.
from ai.agent_driver import _is_blocked  # noqa: E402


class _NotPending:
    is_pending = False


def _ai_blocked(mover, turn_tracker):
    return _is_blocked(turn_tracker, _NotPending(), _NotPending(), None, "Player 2",
                       movement_controller=mover)


react = outcast_scene(gap=6.0)
checks.eq("nothing open: the AI acts", _ai_blocked(react["mv"], react["turn"]), False)

# What PathOfTheOutcastController._begin() does: hand the active-player flag to
# the reacting player, then open the move.
react["turn"].set_active("Player 1")
react["mv"].select(react["squad"].models[0])
react["mv"].start_battle_focus_move(react["squad"], 4.0,
                                    move_mode=poto.PATH_OF_THE_OUTCAST_MOVE_MODE)
checks.eq("the granted move is open", react["mv"].move_mode, "path_of_the_outcast")
checks.eq("so the AI waits for the human to make it",
          _ai_blocked(react["mv"], react["turn"]), True)
# A/B: this is exactly what the AI used to see - a mode the gate did not know.
checks.eq("A/B: the gate used to compare against \"battle_focus\" alone, and missed this",
          poto.PATH_OF_THE_OUTCAST_MOVE_MODE == "battle_focus", False)
react["mv"].cancel_move()
react["turn"].set_active("Player 2")
checks.eq("released once the move is resolved",
          _ai_blocked(react["mv"], react["turn"]), False)

# The AI's OWN reactive move must NOT block it - it is the thing driving it.
own = tk.build(ae.RANGERS, "Player 2", name="2 Rangers W")
tk.line_up(own, y=30.0)
for _m in own.models:
    react["state"].add_token(_m)
react["mv"].select(own.models[0])
react["mv"].start_battle_focus_move(own, 4.0,
                                    move_mode=poto.PATH_OF_THE_OUTCAST_MOVE_MODE)
checks.eq("its own reactive move does not deadlock it",
          _ai_blocked(react["mv"], react["turn"]), False)
react["mv"].cancel_move()

# THE GUARD AGAINST A THIRD REPORT. Checked at the SOURCE rather than by
# simulating each ability: every move_mode handed to start_battle_focus_move()
# anywhere in game/ has to be in the set, because that method is by definition
# the door reactive moves come through. A future third ability that forgets to
# register its mode fails here, rather than in a game.
import glob  # noqa: E402
import io  # noqa: E402
import re  # noqa: E402

from game.movement import MovementController as _MC  # noqa: E402

_modes, _unregistered = set(), []
for _path in glob.glob("game/*.py"):
    _src = io.open(_path, encoding="utf-8").read()
    for _call in re.findall(r"start_battle_focus_move\(([^)]*)\)", _src, re.S):
        _m = re.search(r"move_mode\s*=\s*([A-Za-z_][A-Za-z_0-9]*|\"[^\"]*\")", _call)
        if _m is None:
            _modes.add("battle_focus")  # the parameter's own default
            continue
        _token = _m.group(1)
        if _token.startswith('"'):
            _modes.add(_token.strip('"'))
        else:
            # a named constant - resolve it out of the module it was found in
            _mod = __import__("game." + _path.replace("\\", "/").split("/")[-1][:-3],
                              fromlist=["x"])
            _modes.add(getattr(_mod, _token))
checks.true("the source sweep found both reactive abilities", len(_modes) >= 2)
for _mode in sorted(_modes):
    if _mode not in _MC.REACTIVE_MOVE_MODES:
        _unregistered.append(_mode)
checks.eq("every move_mode passed to start_battle_focus_move() is registered",
          _unregistered, [])


# --- 6. sprite --------------------------------------------------------------
print("--- 6. sprite ---")

from game import sprites  # noqa: E402

# Art arrived after the datasheet was built. Checked at the model, not at the
# mapping table: a key that resolves to no file on disk is exactly the failure
# this is here to catch.
checks.true("Rangers resolve a sprite", sprites.sprite_for(five.models[0]))
checks.true("...and it is the Ranger file (singular on disk)",
            "Ranger" in (sprites.sprite_for(five.models[0]) or ""))
checks.eq("13.09: Rangers CAN be Hidden - they are INFANTRY, unlike Shroud Runners",
          p.infantry, True)


checks.finish()
