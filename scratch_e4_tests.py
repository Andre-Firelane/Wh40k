"""Appends section 4 (Etappe 4) to test_aeldari_enhancements.py."""
import io

SECTION = '''

# =========================================================================
# 4. Defence and concealment
#    Runes of Warding, Rune of Mists, Camouflaged Snipers,
#    Spirit Stone of Raelyth.
# =========================================================================
print("\\n4. Defence and concealment")

_dr_src = io.open("game/damage_resolution.py", encoding="utf-8").read()

from game import conditional_lone_operative as clo  # noqa: E402
from game import enh_camouflaged_snipers as ecs  # noqa: E402
from game import enh_rune_of_mists as erm  # noqa: E402
from game import enh_runes_of_warding as erw  # noqa: E402
from game import enh_spirit_stone_of_raelyth as essr  # noqa: E402
from game import feel_no_pain as fnp_mod  # noqa: E402
from game import hidden_after_shooting as has_mod  # noqa: E402
from game.decision import DecisionManager  # noqa: E402


# --- 4a. Runes of Warding: THREE conditions, one 4+ -----------------------
_rw_unit = _led("Farseer", "Guardian Defenders")
E.grant(_rw_unit, "Runes of Warding", model=_leader_model(_rw_unit, "Farseer"))
_rw_model = _rw_unit.models[-1]          # a BODYGUARD: "models in the bearer's unit"

with only("SEER_COUNCIL_PLAYERS"):
    # Each condition ALONE is enough - they are alternatives, not a
    # conjunction. Read as "and" the card would be nearly unreachable.
    c.eq("a MORTAL wound gets the 4+", erw.feel_no_pain(_rw_model, mortal=True), "4+")
    c.eq("a PSYCHIC attack gets it too", erw.feel_no_pain(_rw_model, psychic=True), "4+")
    c.eq("...and a DEVASTATING critical wound", erw.feel_no_pain(_rw_model, devastating=True), "4+")
    # ...and an ordinary wound gets NOTHING, which is the whole point of a
    # conditional source.
    c.eq("an ordinary wound gets nothing", erw.feel_no_pain(_rw_model), "-")
    # The bearer's WHOLE UNIT, not just the bearer.
    c.true("it reaches a bodyguard, not only the bearer",
           _rw_model not in E.bearer_models(_rw_unit, "Runes of Warding"))
with none_fielded():
    c.eq("no detachment, nothing", erw.feel_no_pain(_rw_model, mortal=True), "-")

# NEVER None: the fold parses these strings, and None collapses it.
c.true("it never returns None", erw.feel_no_pain(None, mortal=True) == "-")

# ...end to end, through the REAL fold.
with only("SEER_COUNCIL_PLAYERS"):
    c.eq("the real fold resolves a psychic wound to 4+",
         fnp_mod.current_feel_no_pain(_rw_model, psychic=True), "4+")
    c.eq("...a devastating one likewise",
         fnp_mod.current_feel_no_pain(_rw_model, devastating=True), "4+")
    _rw_plain = fnp_mod.current_feel_no_pain(_rw_model)
    c.true("...and an ordinary wound is left as the model printed it",
           _rw_plain in (None, "-"))
    # NEVER WORSE THAN PRINTED: a model with a better printed FNP keeps it.
    _rw_better = _rw_unit.models[-2]
    setattr(_rw_better.profile, "feel_no_pain", "3+")
    c.eq("a printed 3+ survives the granted 4+",
         fnp_mod.current_feel_no_pain(_rw_better, mortal=True), "3+")
    setattr(_rw_better.profile, "feel_no_pain", None)

# ...and through the REAL sessions, which is where the three flags are set.
c.true("the mortal-wound session sets mortal=True",
       "mortal=True" in _dr_src.split("class MortalWoundAllocationSession")[1])
c.true("the devastating session sets devastating=True",
       "devastating=True" in _dr_src.split("class DevastatingWoundAllocationSession")[1])
c.true("...and the damage session reads the WEAPON for psychic",
       'psychic=bool(getattr(self.weapon, "psychic", False))' in _dr_src)

# THE NAMED, UNCHANGED GAP: the devastating session still does NOT pass
# mortal=True, so Advanced Armour and Layered Wards do not apply there. That
# is pre-existing and a deliberate non-change (user decision) - pinned so it
# cannot drift silently in either direction.
c.true("the devastating session still does not claim to be a mortal wound",
       "mortal=True" not in _dr_src.split("class DevastatingWoundAllocationSession")[1])


# --- 4b. Rune of Mists: an INVERTED range --------------------------------
_rm_seer = sq("Spiritseer")
_rm_wraiths = sq("Wraithguard")
with only("SPIRIT_CONCLAVE_PLAYERS"):
    c.true("a WRAITH CONSTRUCT unit is a legal target", erm.eligible_target(_rm_wraiths))
    c.true("...and an ordinary unit is not", not erm.eligible_target(sq("Dire Avengers")))

# NO TITANIC EXCLUSION - this card does not print one, its neighbour does.
c.true("Stave of Kurnous excludes TITANIC", "is_non_titanic" in
       io.open("game/enh_stave_of_kurnous.py", encoding="utf-8").read())
c.true("...and Rune of Mists deliberately does not", "is_non_titanic" not in
       io.open("game/enh_rune_of_mists.py", encoding="utf-8").read())

# THE INVERTED DISTANCE, measured on BOTH sides of the line. Written the usual
# way round it would hand cover to exactly the enemies it means to exclude.
_rm_shooter = sq("Dire Avengers", "Player 2").models[0]
tk.line_up(_rm_wraiths, 20.0, 20.0, spacing=1.4)
setattr(_rm_wraiths, erm.FLAG_ATTR, True)
_rm_shooter.x_in, _rm_shooter.y_in = 20.0, 30.0        # 10" away: INSIDE 18"
c.true("an attacker within 18\\" grants NO cover",
       not erm.grants_cover(_rm_shooter, _rm_wraiths))
_rm_shooter.x_in, _rm_shooter.y_in = 20.0, 45.0        # 25" away: OUTSIDE 18"
c.true("...and one outside 18\\" does grant it",
       erm.grants_cover(_rm_shooter, _rm_wraiths))
setattr(_rm_wraiths, erm.FLAG_ATTR, False)
c.true("...and an unmarked unit gets nothing either way",
       not erm.grants_cover(_rm_shooter, _rm_wraiths))

# ...end to end, through the REAL cover computation.
_rm_scene = tk.shooting_scene(D["Dire Avengers"], D["Wraithguard"], attacker_owner="Player 2")
tk.line_up(_rm_scene["attacker"], 20.0, 50.0, spacing=1.2)   # far away
tk.line_up(_rm_scene["target"], 20.0, 20.0, spacing=1.4)
_rm_shoot = _rm_scene["shooting"]
_rm_before = _rm_shoot._compute_benefit_of_cover(
    _rm_scene["attacker"].models[0], _rm_scene["target"])
setattr(_rm_scene["target"], erm.FLAG_ATTR, True)
_rm_after = _rm_shoot._compute_benefit_of_cover(
    _rm_scene["attacker"].models[0], _rm_scene["target"])
c.true("the real cover step grants it to a distant attacker's target",
       _rm_after and not _rm_before)
setattr(_rm_scene["target"], erm.FLAG_ATTR, False)

# WIRING.
c.true("main.py builds the Rune of Mists controller",
       "rune_of_mists_controller = RuneOfMistsController(" in _main_src2)
c.true("...and drives it from the Command phase",
       "rune_of_mists_controller.begin_command_phase(turn_tracker.turn_owner)" in _main_src2)


# --- 4c. Camouflaged Snipers: the THIRD shared-question source ------------
_cs_rangers = sq("Rangers")
E.grant(_cs_rangers, "Camouflaged Snipers")
with only("PATH_OF_THE_OUTCAST_PLAYERS"):
    c.true("its own shooting no longer breaks Hidden", ecs.applies(_cs_rangers))
    # ...and through the SHARED question, which is what game/shooting.py asks.
    c.true("the shared question says so too", has_mod.keeps_hidden(_cs_rangers))
    # "IN YOUR Shooting phase" is handled once, in the shared module: a
    # REACTIVE shot (Fire Overwatch, in the opponent's turn) still reveals.
    c.true("...but a reactive shot still breaks Hidden",
           not has_mod.keeps_hidden(_cs_rangers, reactive=True))
with none_fielded():
    c.true("no detachment, nothing", not has_mod.keeps_hidden(_cs_rangers))

# UNIT-LEVEL: every model carries it, so "a living model still has it" means
# "the unit still exists".
c.true("every Ranger carries it",
       all(m.profile.camouflaged_snipers for m in _cs_rangers.models))

# game/shooting.py still asks exactly ONCE - which is the point of the shared
# module, and what a third source must not change.
c.eq("shooting.py asks the shared question once",
     _shoot_src.count("hidden_after_shooting.keeps_hidden("), 1)


# --- 4d. Spirit Stone of Raelyth: two clauses, two seams ------------------
_ss_unit = _led("Farseer", "Guardian Defenders")
E.grant(_ss_unit, "Spirit Stone of Raelyth",
        model=_leader_model(_ss_unit, "Farseer"))
_ss_falcon = sq("Falcon")
_ss_banshees = sq("Howling Banshees")
tk.line_up(_ss_unit, 20.0, 20.0, spacing=1.2)
tk.line_up(_ss_falcon, 20.0, 22.0, spacing=1.2)          # inside 3"
tk.line_up(_ss_banshees, 20.0, 22.0, spacing=1.2)
_ss_tokens = list(_ss_unit.models) + list(_ss_falcon.models) + list(_ss_banshees.models)

# CLAUSE 1: the fourth conditional Lone Operative.
with only("ARMOURED_WARHOST_PLAYERS"):
    c.true("near a friendly AELDARI VEHICLE, the bearer is a Lone Operative",
           essr.grants_lone_operative(_ss_unit, _ss_tokens))
    # ...and a non-VEHICLE friendly unit does not count.
    c.true("a friendly NON-vehicle does not grant it",
           not essr.grants_lone_operative(
               _ss_unit, list(_ss_unit.models) + list(_ss_banshees.models)))
    tk.line_up(_ss_falcon, 20.0, 40.0, spacing=1.2)      # far away
    c.true("...nor one out of 3\\"",
           not essr.grants_lone_operative(_ss_unit, _ss_tokens))
    tk.line_up(_ss_falcon, 20.0, 22.0, spacing=1.2)
with none_fielded():
    c.true("no detachment, nothing", not essr.grants_lone_operative(_ss_unit, _ss_tokens))

# It joins the SHARED list rather than a fourth hand-written block in
# game/status_effects.py - which is what that extraction was for.
c.eq("conditional_lone_operative now has four sources", len(clo.SOURCES), 4)
with only("ARMOURED_WARHOST_PLAYERS"):
    c.true("...and the shared reader returns this one's range",
           essr.SPIRIT_STONE_RANGE_IN in clo.granted_ranges(_ss_unit, _ss_tokens))

# CLAUSE 2: the heal, and its TWO moments.
_ss_ctrl = essr.SpiritStoneOfRaelythController(
    game_state=_E3State(_ss_unit, _ss_falcon), auto_players=(HUMAN,))
_ss_hull = _ss_falcon.models[0]
with only("ARMOURED_WARHOST_PLAYERS"):
    # A FULL-strength vehicle is not offered a heal that would do nothing.
    c.eq("an undamaged vehicle is not a heal target",
         essr.heal_targets(_ss_unit, _ss_tokens), [])
    _ss_hull.current_wounds = _ss_hull.profile.wounds - 3
    c.true("a damaged one is",
           _ss_hull in essr.heal_targets(_ss_unit, _ss_tokens))

    # AT THE START of the move.
    _ss_ctrl.on_move_started(_ss_unit)
    c.true("the heal is offered at the START of the move",
           _ss_hull.current_wounds > _ss_falcon.models[0].profile.wounds - 3)
    # ...and ONCE per move: the end no longer offers it.
    _ss_before_end = _ss_hull.current_wounds
    _ss_ctrl.on_move_finished(_ss_unit)
    c.eq("...and not a second time at the end of the same move",
         _ss_hull.current_wounds, _ss_before_end)

    # A NEW move re-opens it.
    _ss_hull.current_wounds = _ss_hull.profile.wounds - 3
    _ss_ctrl.on_move_started(_ss_unit)
    c.true("a new move opens it again",
           _ss_hull.current_wounds > _ss_falcon.models[0].profile.wounds - 3)

    # DECLINING at the start must NOT spend it - "start OR end" is a choice of
    # timing. Driven through a real DecisionManager so the decline is real.
    _ss_hull.current_wounds = _ss_hull.profile.wounds - 3
    _ss_dm = DecisionManager()
    _ss_human = essr.SpiritStoneOfRaelythController(
        game_state=_E3State(_ss_unit, _ss_falcon), decision_manager=_ss_dm)
    _ss_human.on_move_started(_ss_unit)
    tk.pick_option(_ss_dm, "Do not heal")
    c.eq("declining at the start heals nothing",
         _ss_hull.current_wounds, _ss_hull.profile.wounds - 3)
    c.true("...and the end of the move still offers it",
           _ss_human.offer(_ss_unit))

    # The heal never overshoots the printed wounds.
    _ss_hull.current_wounds = _ss_hull.profile.wounds - 1
    _ss_ctrl._used_this_move.clear()
    _ss_ctrl.offer(_ss_unit)
    c.eq("a heal is capped at the model's printed wounds",
         _ss_hull.current_wounds, _ss_hull.profile.wounds)

# THE NEW HOOK is the mirror of the existing one, and fired from the ONE
# shared entry - so it cannot be wired to some move types and not others.
_move_src = io.open("game/movement.py", encoding="utf-8").read()
c.true("MovementController declares on_move_started",
       "self.on_move_started = []" in _move_src)
c.true("...fired from _begin_move, the shared entry",
       "for listener in (self.on_move_started or ()):" in
       _move_src.split("def _begin_move")[1].split("def start_move")[0])
c.eq("...which every move type goes through", _move_src.count("self._begin_move("), 10)

# WIRING - both hooks, or the card only half works.
c.true("main.py builds the Spirit Stone controller",
       "spirit_stone_controller = SpiritStoneOfRaelythController(" in _main_src2)
c.true("...and listens on the START of a move",
       "movement_controller.on_move_started.append(spirit_stone_controller.on_move_started)"
       in _main_src2)
c.true("...and on the END of one",
       "movement_controller.on_move_finished.append(spirit_stone_controller.on_move_finished)"
       in _main_src2)
'''

p = "test_aeldari_enhancements.py"
s = io.open(p, encoding="utf-8").read()
old = "\n\nc.finish()"
assert s.count(old) == 1
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, SECTION + "\n\nc.finish()"))
print("appended")
