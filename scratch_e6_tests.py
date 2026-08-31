"""Appends section 6 (Etappe 6) to test_aeldari_enhancements.py."""
import io

SECTION = '''

# =========================================================================
# 6. Pre-game, movement and return
#    Firstdrawn Blade, Ethereal Pathway, Higher Duty, Phoenix Gem
#    - plus the SpiritMarkController repair.
# =========================================================================
print("\\n6. Pre-game, movement and return")

from game import enh_ethereal_pathway as eep  # noqa: E402
from game import enh_firstdrawn_blade as efb  # noqa: E402
from game import enh_higher_duty as ehd  # noqa: E402
from game import enh_phoenix_gem as epg  # noqa: E402
from game import spiritseer as ss_mod  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.squad import squad_has_infiltrators  # noqa: E402

_pregame_src = io.open("game/pregame.py", encoding="utf-8").read()
_panel_src = io.open("game/ui/action_panel.py", encoding="utf-8").read()
_move_src6 = io.open("game/movement.py", encoding="utf-8").read()


# --- 6a. Firstdrawn Blade: Scouts, and the ordering that makes it real -----
_fb_unit = sq("Windriders")
E.grant(_fb_unit, "Firstdrawn Blade", model=_fb_unit.models[0])
with only("WINDRIDER_HOST_PLAYERS"):
    c.true("the bearer's unit qualifies", efb.applies(_fb_unit))
    efb.grant_scouts(_fb_unit)
    c.true("...and every model gets the Scouts range",
           all(m.profile.scouts == efb.FIRSTDRAWN_BLADE_SCOUTS_IN
               for m in _fb_unit.models))
c.eq("...which is the printed 9\\"", efb.FIRSTDRAWN_BLADE_SCOUTS_IN, 9.0)
with none_fielded():
    c.true("no detachment, nothing", not efb.applies(sq("Windriders")))

# NEVER A DOWNGRADE. This card has NO "that do not have the Scouts ability"
# clause (its T'au cousin does), so it can land on a unit that already scouts -
# and shortening that unit's move would be a 10-point penalty.
_fb_ranger = sq("Rangers")
_fb_printed = _fb_ranger.models[0].profile.scouts
efb.grant_scouts(_fb_ranger)
c.true("a longer printed Scouts range survives the grant",
       _fb_ranger.models[0].profile.scouts >= efb.FIRSTDRAWN_BLADE_SCOUTS_IN
       and _fb_ranger.models[0].profile.scouts >= (_fb_printed or 0))

# THE ORDERING, which is the whole reason this is a pre-battle STEP: a Scouts
# grant made AFTER the Scout move step is carried and never used.
c.true("its step is registered BEFORE the Scouts step",
       "pregame_controller.prebattle_steps.insert(0, FirstdrawnBladeStep(" in _main_src2)
c.true("...and the queue really drains in order",
       "while self._prebattle_queue:" in _pregame_src
       and before(_pregame_src, "self._prebattle_queue.pop(0)", "self.scouts_step.start(self)"))
# It asks nothing, so it never stalls the sequence.
c.true("it resolves inline rather than prompting",
       efb.FirstdrawnBladeStep(game_state=_E3State(_fb_unit)).start(None) is False)


# --- 6b. Ethereal Pathway: one step EARLIER -------------------------------
_ep_seer = sq("Farseer")
E.grant(_ep_seer, "Ethereal Pathway")
_ep_guardians = sq("Guardian Defenders")
_ep_banshees = sq("Howling Banshees")

with only("ARMOURED_WARHOST_PLAYERS"):
    c.true("a GUARDIANS unit is a legal target",
           eep.is_eligible_target(_ep_guardians, HUMAN))
    c.true("...and a non-GUARDIANS unit is not",
           not eep.is_eligible_target(_ep_banshees, HUMAN))
    c.true("...nor an enemy one",
           not eep.is_eligible_target(sq("Guardian Defenders", "Player 2"), HUMAN))

    # 24.20 IS AN EVERY-MODEL ABILITY, so the grant has to mark all of them -
    # marking some would satisfy squad_has_infiltrators() not at all.
    c.true("before the grant the unit has no Infiltrators",
           not squad_has_infiltrators(_ep_guardians))
    eep.grant_infiltrators(_ep_guardians)
    c.true("every model is marked",
           all(m.profile.infiltrators for m in _ep_guardians.models))
    c.true("...so rule 24.20's every-model gate is satisfied",
           squad_has_infiltrators(_ep_guardians))
    # ...and a unit that already has it is not offered one that buys nothing.
    c.true("a unit that already has Infiltrators is not offered the grant",
           not eep.is_eligible_target(_ep_guardians, HUMAN))
c.eq("up to TWO units", eep.ETHEREAL_PATHWAY_MAX_UNITS, 2)

# THE ORDERING, and it is a step EARLIER than Firstdrawn Blade's: rule 24.20
# decides both WHERE a unit may be placed and WHEN, and the Deploy Armies step
# reads both. A grant made after it is carried and never used.
c.true("its step goes in deploy_armies_steps, not prebattle_steps",
       "pregame_controller.deploy_armies_steps.append(EtherealPathwayStep(" in _main_src2)
c.true("...which PregameController runs at the top of _set_deploy_order()",
       before(_pregame_src, "for step in self.deploy_armies_steps:",
              "self.state = DEPLOYING"))
# ...and that really is before deployment reads either half of 24.20.
c.true("...i.e. before the deployment order is set",
       before(_pregame_src, "for step in self.deploy_armies_steps:",
              "self.active_player = first_to_place"))


# --- 6c. Higher Duty: a REACTIVE move, with all four parts ----------------
_hd_unit = sq("Spiritseer")
E.grant(_hd_unit, "Higher Duty")
_hd_enemy = sq("Dire Avengers", "Player 2")
tk.line_up(_hd_unit, 20.0, 20.0, spacing=1.2)
tk.line_up(_hd_enemy, 20.0, 25.0, spacing=1.2)          # 5" away: inside 8"
_hd_tokens = list(_hd_unit.models) + list(_hd_enemy.models)
_hd_ctrl = ehd.HigherDutyController(
    game_state=_E3State(_hd_unit, _hd_enemy), all_tokens=_hd_tokens)

with only("SPIRIT_CONCLAVE_PLAYERS"):
    c.true("an enemy ending a move within 8\\" lets it react",
           _hd_ctrl.can_react(_hd_unit, _hd_enemy))
    # THE SECOND CLAUSE IS ABOUT THE REACTOR, not the mover: a unit already in
    # Engagement Range cannot use this to walk away - that is Fall Back's job.
    tk.line_up(_hd_enemy, 20.0, 21.0, spacing=1.2)      # inside engagement
    c.true("...but not while IT is within Engagement Range of an enemy",
           not _hd_ctrl.can_react(_hd_unit, _hd_enemy))
    tk.line_up(_hd_enemy, 20.0, 40.0, spacing=1.2)      # 20" away
    c.true("...and not for an enemy that ended far away",
           not _hd_ctrl.can_react(_hd_unit, _hd_enemy))
    tk.line_up(_hd_enemy, 20.0, 25.0, spacing=1.2)
    # "YOUR OPPONENT'S Movement phase" - it never reacts to its own side.
    c.true("...and never to a FRIENDLY unit's move",
           not _hd_ctrl.can_react(_hd_unit, sq("Dire Avengers", HUMAN)))
with none_fielded():
    c.true("no detachment, no reaction", not _hd_ctrl.can_react(_hd_unit, _hd_enemy))

c.eq("the trigger is 8\\"", ehd.HIGHER_DUTY_TRIGGER_RANGE_IN, 8.0)
c.eq("...and the move is 6\\"", ehd.HIGHER_DUTY_MOVE_IN, 6.0)

# THE FOUR PARTS OF A REACTIVE MOVE. CLAUDE.md records this exact failure being
# reported THREE times, so each is pinned rather than assumed.
c.true("1. its mode is registered in REACTIVE_MOVE_MODES",
       ehd.HIGHER_DUTY_MOVE_MODE in MovementController.REACTIVE_MOVE_MODES)
c.true("2. it hands active_player over and back",
       "self.turn_tracker.set_active(squad.owner)" in
       io.open("game/enh_higher_duty.py", encoding="utf-8").read()
       and "self.turn_tracker.set_active(self._restore_active)" in
       io.open("game/enh_higher_duty.py", encoding="utf-8").read())
c.true("3. the panel routes Confirm back to it",
       "confirm_callback = higher_duty_controller.confirm_move" in _panel_src)
c.true("...and Cancel too",
       "cancel_callback = higher_duty_controller.cancel_move" in _panel_src)
c.true("4. an open move blocks the phase change",
       "or higher_duty_controller.is_busy" in _main_src2)
# ...and it goes through the ONE door that reactive moves use.
c.true("it starts the move through start_battle_focus_move",
       "self.movement_controller.start_battle_focus_move(" in
       io.open("game/enh_higher_duty.py", encoding="utf-8").read())
c.true("main.py feeds it from on_move_finished",
       "movement_controller.on_move_finished.append(higher_duty_controller.on_move_finished)"
       in _main_src2)


# --- 6d. Phoenix Gem: once, at the end of the phase ------------------------
_pg_unit = sq("Guardian Defenders")
E.grant(_pg_unit, "Phoenix Gem", model=_pg_unit.models[0])
_pg_model = _pg_unit.models[0]
tk.line_up(_pg_unit, 30.0, 30.0, spacing=1.2)
_pg_ctrl = epg.PhoenixGemController(game_state=_E3State(_pg_unit), all_tokens=[])

with only("WARHOST_PLAYERS"):
    c.true("the bearer is recognised", epg.is_bearer(_pg_model))
    c.true("...and a squadmate is not", not epg.is_bearer(_pg_unit.models[1]))

    # "THE FIRST TIME" - once per battle, and NOT cleared by any reset.
    c.true("its death is noted", _pg_ctrl.notify_model_destroyed(_pg_unit, _pg_model))
    c.true("...but a second death is not",
           not _pg_ctrl.notify_model_destroyed(_pg_unit, _pg_model))

    # "AT THE END OF THE PHASE", on a 2+. Scripted, so both bands are measured
    # rather than whichever the die happened to give.
    _pg_model.current_wounds = 0
    tk.script(1)
    c.eq("a rolled 1 returns nothing", _pg_ctrl.resolve_end_of_phase(), [])
    _pg_ctrl._used.clear()
    _pg_ctrl.notify_model_destroyed(_pg_unit, _pg_model)
    tk.script(2)
    c.eq("...and a 2 returns it", len(_pg_ctrl.resolve_end_of_phase()), 1)
    c.eq("...with its FULL wounds", _pg_model.current_wounds, _pg_model.profile.wounds)
    tk.script()
c.eq("the threshold is the printed 2+", epg.PHOENIX_GEM_THRESHOLD, 2)

# "NOT WITHIN ENGAGEMENT RANGE" - the half position_valid() explicitly does not
# cover, and without it the model returns into the combat that killed it.
with only("WARHOST_PLAYERS"):
    _pg_enemy = sq("Dire Avengers", "Player 2")
    tk.line_up(_pg_enemy, 30.0, 30.5, spacing=1.2)       # right on top of it
    _pg_ctrl2 = epg.PhoenixGemController(
        game_state=_E3State(_pg_unit, _pg_enemy),
        all_tokens=list(_pg_unit.models) + list(_pg_enemy.models))
    _pg_spot = _pg_ctrl2._spot_for(_pg_model)
    c.true("a returning model is placed clear of Engagement Range",
           _pg_spot is None
           or all(((_pg_spot[0] - e.x_in) ** 2 + (_pg_spot[1] - e.y_in) ** 2) ** 0.5
                  - _pg_model.radius_in - e.radius_in > 2.0
                  for e in _pg_enemy.models))

# WIRING - the same two seams as its twin.
c.true("main.py notes the death in the sweep",
       "phoenix_gem_controller.notify_model_destroyed(" in _main_src2)
c.true("...and rolls at the end of the phase",
       "phoenix_gem_controller.resolve_end_of_phase()" in _main_src2)


# --- 6e. the SpiritMarkController repair ----------------------------------
# BUILT AND NEVER FED: mark(), available(), both candidate lists and
# start_of_movement_phase() all existed and were unit-tested, and nothing in
# main.py ever called any of them - so the mark could never be placed and the
# [SUSTAINED HITS 1] half above it was dead code.
c.true("main.py now feeds it at the START of a move",
       "movement_controller.on_move_started.append(spirit_mark_controller.on_move_started)"
       in _main_src2)
c.true("...and at the END of one",
       "movement_controller.on_move_finished.append(spirit_mark_controller.on_move_finished)"
       in _main_src2)
c.true("...which is what its printed text says",
       "starts or ends a move" in io.open("game/spiritseer.py", encoding="utf-8").read())
c.true("...and its own reset point is driven too",
       "spirit_mark_controller.start_of_movement_phase(turn_tracker.turn_owner)"
       in _main_src2)

# ...and the offer itself works end to end.
_sm_seer = sq("Spiritseer")
setattr(_sm_seer.models[0].profile, "spirit_mark", True)
_sm_wraiths = sq("Wraithguard")
_sm_enemy = sq("Dire Avengers", "Player 2")
tk.line_up(_sm_seer, 20.0, 20.0, spacing=1.2)
tk.line_up(_sm_wraiths, 20.0, 22.0, spacing=1.4)
tk.line_up(_sm_enemy, 20.0, 30.0, spacing=1.2)
_sm_dm = DecisionManager()
_sm_ctrl = ss_mod.SpiritMarkController(
    decision_manager=_sm_dm, all_tokens=list(_sm_seer.models) + list(_sm_wraiths.models)
    + list(_sm_enemy.models))
c.true("the mark is available before it is used", _sm_ctrl.available(_sm_seer))
c.true("a move offers it", _sm_ctrl.on_move_started(_sm_seer))
tk.pick_option(_sm_dm, _sm_wraiths.name)
if _sm_dm.is_pending:
    tk.pick_option(_sm_dm, _sm_enemy.name)
c.true("...and the pair is marked", _sm_ctrl.applies_to(_sm_wraiths, _sm_enemy))
# ONCE PER TURN, per army.
c.true("...once per turn", not _sm_ctrl.available(_sm_seer))
# "UNTIL THE START OF YOUR NEXT MOVEMENT PHASE" - its own, later reset point.
_sm_ctrl.start_of_movement_phase(HUMAN)
c.true("...and the mark is gone at the next Movement phase",
       not _sm_ctrl.applies_to(_sm_wraiths, _sm_enemy))
c.true("...and it is available again", _sm_ctrl.available(_sm_seer))


# --- 6f. all 28 are built -------------------------------------------------
_MODULE_FOR = {
    "Craftworld's Champion": "enh_craftworlds_champion",
    "Strategic Savant": "enh_strategic_savant",
    "Light of Clarity": "enh_light_of_clarity",
    "Assassins' Eye": "enh_assassins_eye",
    "Seersight Strike": "enh_psychic_weapons",
    "Psychic Destroyer": "enh_psychic_weapons",
    "Stone of Eldritch Fury": "enh_psychic_weapons",
    "Aspect of Murder": "enh_aspect_of_murder",
    "Stave of Kurnous": "enh_stave_of_kurnous",
    "Mirage Field": "enh_mirage_field",
    "Shimmerstone": "enh_shimmerstone",
    "Guiding Presence": "enh_guiding_presence",
    "Breath of Vaul": "enh_breath_of_vaul",
    "Mantle of Wisdom": "enh_mantle_of_wisdom",
    "Runes of Warding": "enh_runes_of_warding",
    "Rune of Mists": "enh_rune_of_mists",
    "Camouflaged Snipers": "enh_camouflaged_snipers",
    "Spirit Stone of Raelyth": "enh_spirit_stone_of_raelyth",
    "Protector of the Paths": "enh_protector_of_the_paths",
    "Gift of Foresight": "enh_gift_of_foresight",
    "Echoes of Ulthanesh": "enh_echoes_of_ulthanesh",
    "Torc of Morai-Heg": "enh_torc_of_morai_heg",
    "Timeless Strategist": "enh_timeless_strategist",
    "Lucid Eye": "enh_lucid_eye",
    "Firstdrawn Blade": "enh_firstdrawn_blade",
    "Ethereal Pathway": "enh_ethereal_pathway",
    "Higher Duty": "enh_higher_duty",
    "Phoenix Gem": "enh_phoenix_gem",
}
c.eq("every one of the 28 names a module", sorted(_MODULE_FOR), sorted(SPECS))
import importlib  # noqa: E402
for _name, _mod in sorted(_MODULE_FOR.items()):
    _m = importlib.import_module("game.%s" % _mod)
    # Each module QUOTES its own printed rule, so a card cannot be built from
    # memory of what it probably said.
    c.true("%s quotes its printed text" % _name,
           _name in (_m.__doc__ or "") or _name.replace("'", "\\u2019") in (_m.__doc__ or ""))

# NEGATIVE SPACE: no AI path for any of the 28 (standing Aeldari rule).
_ai_src = io.open("ai/agent_driver.py", encoding="utf-8").read()
c.eq("no Enhancement module is imported by the AI",
     [m for m in set(_MODULE_FOR.values()) if m in _ai_src], [])
'''

p = "test_aeldari_enhancements.py"
s = io.open(p, encoding="utf-8").read()
old = "\n\nc.finish()"
assert s.count(old) == 1
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, SECTION + "\n\nc.finish()"))
print("appended")
