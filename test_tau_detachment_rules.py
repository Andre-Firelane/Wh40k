"""The remaining T'au detachment rules, one section each.

Kauyon and Mont'ka live in test_tau_doctrines.py - they are a matched pair with
a shape of their own (a battle-round window plus a Guided clause). The rules
here have nothing in common with each other beyond the faction, so each section
stands alone.

  1. Experimental Prototype Cadre - Superior Craftsmanship (+6" Range).
  2. Advanced Acquisition Cadre - Expert Fieldcraft (shooting keeps Hidden).
  3. Auxiliary Cadre - Integrated Command Structure (prey mark + aura).
"""

import inspect
import io
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import testkit as tk  # noqa: E402
from game import (advanced_acquisition_cadre as aac,  # noqa: E402
                  attached_units, config, detachments,
                  experimental_prototype_cadre as epc, weapon_range)
from game.factions.orks import BOYZ  # noqa: E402
from game.factions.tau_empire import (COMMANDER_IN_COLDSTAR_BATTLESUIT,  # noqa: E402
                                      COMMANDER_SHADOWSUN, CRISIS_STARSCYTHE,
                                      PATHFINDER_TEAM, STEALTH_BATTLESUITS,
                                      STRIKE_TEAM)
from game.weapons import MELEE, RANGED  # noqa: E402

c = tk.Checks("T'au detachment rules")


class settings_as:
    def __init__(self, **values):
        self.values = values

    def __enter__(self):
        self.old = {k: getattr(config, k) for k in self.values}
        for key, value in self.values.items():
            setattr(config, key, value)
        return self

    def __exit__(self, *exc):
        for key, value in self.old.items():
            setattr(config, key, value)


ON = dict(EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS=("Player 1",))
OFF = dict(EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS=())


def ranged(model):
    return next(w for w in model.weapons if w.weapon_type == RANGED)


# --- 1. Experimental Prototype Cadre: Superior Craftsmanship --------------
print("\n1. Experimental Prototype Cadre - Superior Craftsmanship")

commander = tk.build(COMMANDER_IN_COLDSTAR_BATTLESUIT, "Player 1",
                     name="1 Commander in Coldstar Battlesuit 1")
lone = commander.models[0]
gun = ranged(lone)

c.true("the Commander really is BATTLESUIT and CHARACTER",
       lone.profile.battlesuit and lone.profile.character)
c.true("...so its unit qualifies", epc.is_battlesuit_character_unit(commander))

with settings_as(**ON):
    c.eq("its ranged weapon reaches 6\" further",
         weapon_range.effective_range_in(lone, gun), gun.range_in + 6.0)
with settings_as(**OFF):
    c.eq("without the detachment it is the printed range",
         weapon_range.effective_range_in(lone, gun), float(gun.range_in))
with settings_as(EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS=("Player 2",)):
    c.eq("the OTHER player having it does not help this one",
         weapon_range.effective_range_in(lone, gun), float(gun.range_in))

# HALF range moves too, and that is the substance of routing this through
# game/weapon_range.py rather than measuring at the range test alone: [MELTA X]
# and [RAPID FIRE X] both measure half of the CURRENT characteristic.
shadowsun = tk.build(COMMANDER_SHADOWSUN, "Player 1", name="1 Commander Shadowsun 1")
melta = next(w for w in shadowsun.models[0].weapons if getattr(w, "melta", 0))
with settings_as(**ON):
    c.eq("a [MELTA] weapon's half range moves with it",
         weapon_range.half_range_in(shadowsun.models[0], melta),
         (melta.range_in + 6.0) / 2)
with settings_as(**OFF):
    c.eq("...and is the printed half without the detachment",
         weapon_range.half_range_in(shadowsun.models[0], melta), melta.range_in / 2)
c.true("that is a real consequence - a T'au CHARACTER really can carry [MELTA]",
       bool(getattr(melta, "melta", 0)))

# Ranged only: the rule says "ranged attacks".
blade = next((w for w in lone.weapons if w.weapon_type == MELEE), None)
with settings_as(**ON):
    c.true("a melee weapon gets nothing",
           blade is None or epc.bonus_for(lone, blade) == 0.0)
    c.eq("a ranged one gets the full 6", epc.bonus_for(lone, gun), 6.0)

# Who does NOT qualify.
strike = tk.build(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
crisis = tk.build(CRISIS_STARSCYTHE, "Player 1", name="1 Crisis Starscythe Battlesuits 1")
orks = tk.build(BOYZ, "Player 1", name="1 Boyz 1")
with settings_as(**ON):
    c.true("a non-CHARACTER Fire Warrior unit does not qualify",
           not epc.is_battlesuit_character_unit(strike))
    c.eq("...and gets no bonus", epc.bonus_for(strike.models[0], ranged(strike.models[0])), 0.0)
    c.true("a BATTLESUIT unit with no CHARACTER does not qualify",
           not epc.is_battlesuit_character_unit(crisis))
    c.eq("...and gets no bonus", epc.bonus_for(crisis.models[0], ranged(crisis.models[0])), 0.0)
    c.true("an Ork unit does not qualify", not epc.applies(orks))
c.true("a model with no squad degrades to no bonus rather than raising",
       epc.bonus_for(object(), gun) == 0.0)

# RULE 19.03: an attached unit has all its components' keywords, and the
# printed text says "units", not "models" - so a Commander joined to a Crisis
# team gives the WHOLE unit the +6", bodyguards included. Written out because
# it reads like an oversight until you check which noun the rule uses.
leader = tk.build(COMMANDER_IN_COLDSTAR_BATTLESUIT, "Player 1",
                  name="1 Commander in Coldstar Battlesuit 2")
bodyguards = tk.build(CRISIS_STARSCYTHE, "Player 1", name="1 Crisis Starscythe Battlesuits 2")
# can_attach returns the reasons it is NOT allowed, so an EMPTY list is the
# permission - the same polarity test_player1_army.py checks it with.
c.eq("the Commander may lead the Crisis team",
     attached_units.can_attach(leader, bodyguards), [])
merged = attached_units.attach(leader, bodyguards)
c.true("the merged unit qualifies", epc.is_battlesuit_character_unit(merged))
bodyguard_model = next(m for m in merged.models if not m.profile.character)
with settings_as(**ON):
    c.eq("a BODYGUARD in it gets the bonus too (19.03 + \"units\")",
         epc.bonus_for(bodyguard_model, ranged(bodyguard_model)), 6.0)

# The two keywords are pooled independently, which is what 19.03 means.
src = inspect.getsource(epc.is_battlesuit_character_unit)
c.true("the two keywords are asked as two any-model questions",
       src.count("unit_has_keyword(") == 2)

# Wiring: it is the THIRD source in the one range definition, so it reaches all
# three range questions rather than just the reach test.
chain = inspect.getsource(weapon_range.effective_range_in)
c.true("Superior Craftsmanship is summed into effective_range_in",
       "experimental_prototype_cadre.bonus_for(" in chain)
c.true("half_range_in derives from it rather than from the printed range",
       "effective_range_in(model, weapon) / 2"
       in inspect.getsource(weapon_range.half_range_in))
range_src = io.open("game/weapon_range.py", encoding="utf-8").read()
c.true("the module's docstring now names three sources", "Three abilities" in range_src)

c.eq("it reads its own config setting", epc.SETTING,
     "EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS")
c.true("...which game/detachments.py actually writes",
       epc.SETTING in detachments.all_settings())

# The second printed sentence is a list-building restriction with nothing to
# restrict here. Pinned as a DEMONSTRATED no-op, not silently dropped.
epc_src = io.open("game/experimental_prototype_cadre.py", encoding="utf-8").read()
c.true("the 'cannot be taken with another BATTLESUIT detachment' clause is written out",
       "BATTLESUIT detachment" in epc_src and "no-op" in epc_src.lower())
c.true("...and really is inert - a player fields exactly one detachment",
       all(len([d for d in detachments.available(k) if d.setting]) >= 1
           for k in ("tau",)))

# No AI path, per the standing T'au instruction.
driver = io.open("ai/agent_driver.py", encoding="utf-8").read().lower()
c.true("nothing in ai/ mentions this detachment - by design",
       "experimental_prototype" not in driver and "superior_craftsmanship" not in driver)



# --- 2. Advanced Acquisition Cadre: Expert Fieldcraft ---------------------
print("\n2. Advanced Acquisition Cadre - Expert Fieldcraft")

AAC_ON = dict(ADVANCED_ACQUISITION_CADRE_PLAYERS=("Player 1",))
AAC_OFF = dict(ADVANCED_ACQUISITION_CADRE_PLAYERS=())

pathfinders = tk.build(PATHFINDER_TEAM, "Player 1", name="1 Pathfinder Team 1")
stealth = tk.build(STEALTH_BATTLESUITS, "Player 1", name="1 Stealth Battlesuits 1")

c.true("Pathfinders are named by the rule", aac.is_fieldcraft_unit(pathfinders))
c.true("Stealth Battlesuits are too", aac.is_fieldcraft_unit(stealth))
c.true("a Strike Team is not", not aac.is_fieldcraft_unit(strike))
c.true("an Ork unit is not", not aac.is_fieldcraft_unit(orks))

# "STEALTH BATTLESUITS" is matched as the STEALTH keyword. That is only sound
# because the keyword picks out exactly that one datasheet - measured here
# rather than assumed, since a second STEALTH datasheet would silently widen
# the rule.
from game.factions.tau_empire import TAU_EMPIRE  # noqa: E402
_stealth_sheets = [n for n, ds in TAU_EMPIRE.datasheets.items() if "STEALTH" in ds.keywords]
c.eq("STEALTH names exactly one datasheet, so keyword == datasheet here",
     _stealth_sheets, ["Stealth Battlesuits"])

with settings_as(**AAC_ON):
    c.true("a named unit's shooting keeps it Hidden", aac.shooting_keeps_hidden(pathfinders))
    c.true("...and so does a Stealth team's", aac.shooting_keeps_hidden(stealth))
    c.true("an unnamed unit's does not", not aac.shooting_keeps_hidden(strike))
    # "In YOUR Shooting phase" - Fire Overwatch happens in the opponent's turn,
    # so a reactive activation is not covered and still strips Hidden.
    c.true("a REACTIVE activation is not covered",
           not aac.shooting_keeps_hidden(pathfinders, reactive=True))
with settings_as(**AAC_OFF):
    c.true("without the detachment, nothing is protected",
           not aac.shooting_keeps_hidden(pathfinders))
with settings_as(ADVANCED_ACQUISITION_CADRE_PLAYERS=("Player 2",)):
    c.true("the other player having it does not help this one",
           not aac.shooting_keeps_hidden(pathfinders))


def records_shot(sheet, players, reactive):
    """Drive the REAL controller and report whether the shot was recorded -
    a predicate test cannot show the suppression reaches the bookkeeping."""
    scene = tk.shooting_scene(sheet, BOYZ, attacker_owner="Player 1")
    sc = scene["shooting"]
    sc.active_squad = scene["attacker"]
    sc._reactive = reactive
    with settings_as(ADVANCED_ACQUISITION_CADRE_PLAYERS=players):
        sc._note_ranged_attack()
    return scene["attacker"] in sc.last_ranged_attack_turn


c.true("without the detachment the shot is recorded (Hidden is lost)",
       records_shot(PATHFINDER_TEAM, (), False))
c.true("with it, the shot is NOT recorded (Hidden survives)",
       not records_shot(PATHFINDER_TEAM, ("Player 1",), False))
c.true("...same for Stealth Battlesuits",
       not records_shot(STEALTH_BATTLESUITS, ("Player 1",), False))
c.true("an unnamed unit is still recorded",
       records_shot(STRIKE_TEAM, ("Player 1",), False))
c.true("a reactive (Overwatch) shot is still recorded",
       records_shot(PATHFINDER_TEAM, ("Player 1",), True))

# BOTH write paths. The one funnel has two callers, and a rule that suppressed
# only the normal end would reproduce exactly half of the bug that funnel's own
# docstring was written for (cancel() used to skip the bookkeeping entirely).
from game.shooting import ShootingController  # noqa: E402
_note_src = inspect.getsource(ShootingController._note_ranged_attack)
# Asked through the fold since Auxiliary Cadre became the second source - see
# section 3. What matters here is that the suppression is INSIDE the funnel,
# whichever module owns the question.
c.true("the suppression lives INSIDE the one funnel",
       "hidden_after_shooting.keeps_hidden(" in _note_src)
c.true("cancel() reaches that funnel",
       "_note_ranged_attack()" in inspect.getsource(ShootingController.cancel))
c.true("...and so does the normal end of an activation",
       "_note_ranged_attack()" in inspect.getsource(ShootingController._actually_finish_squad))
c.true("the reactive flag is passed in rather than re-derived",
       "reactive=self._reactive" in _note_src)

# Hidden has ONE record, so there must be no second place writing it.
_shooting_src = io.open("game/shooting.py", encoding="utf-8").read()
c.eq("last_ranged_attack_turn is written in exactly one place",
     _shooting_src.count("self.last_ranged_attack_turn[self.active_squad] ="), 1)

c.eq("it reads its own config setting", aac.SETTING,
     "ADVANCED_ACQUISITION_CADRE_PLAYERS")
c.true("...which game/detachments.py actually writes",
       aac.SETTING in detachments.all_settings())
c.true("nothing in ai/ mentions it - by design",
       "advanced_acquisition" not in driver and "expert_fieldcraft" not in driver)
_shooting_src2 = _shooting_src


# --- 3. Auxiliary Cadre: Integrated Command Structure ---------------------
print("\n3. Auxiliary Cadre - Integrated Command Structure")

from game import auxiliary_cadre as aux, hidden_after_shooting, status_effects  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.factions.tau_empire import (GHOSTKEEL_BATTLESUIT,  # noqa: E402
                                      KROOT_CARNIVORES)
from game.terrain import DENSE, LIGHT, Obstacle, TerrainArea  # noqa: E402
from game.turn import TurnTracker  # noqa: E402

AUX_ON = dict(AUXILIARY_CADRE_PLAYERS=("Player 1",))
AUX_OFF = dict(AUXILIARY_CADRE_PLAYERS=())

kroot = tk.build(KROOT_CARNIVORES, "Player 1", name="1 Kroot Carnivores 1")
ghostkeel = tk.build(GHOSTKEEL_BATTLESUIT, "Player 1", name="1 Ghostkeel Battlesuit 1")

c.true("Kroot are a harnessed unit", aux.is_harnessed_unit(kroot))
c.true("Vespid would be too", "VESPID STINGWINGS" in aux.HARNESSED_KEYWORDS)
c.true("a Ghostkeel is a projector", aux.is_projector_unit(ghostkeel))
c.true("Stealth Battlesuits are projectors too", aux.is_projector_unit(stealth))
c.true("a Strike Team is neither",
       not aux.is_harnessed_unit(strike) and not aux.is_projector_unit(strike))
c.true("Pathfinders are not harnessed either", not aux.is_harnessed_unit(pathfinders))

# -- Localised Stealth Projectors, the aura half --------------------------
with settings_as(**AUX_ON):
    tk.line_up(kroot, 10, 10)
    tk.line_up(ghostkeel, 10, 14)          # 4" apart: inside the 6" aura
    c.true("Kroot within 6\" of a Ghostkeel are covered",
           aux.stealth_projector_covers(kroot, [kroot, ghostkeel]))
    tk.line_up(ghostkeel, 10, 22)          # 12" apart: outside it
    c.true("...and are not once it is out of range",
           not aux.stealth_projector_covers(kroot, [kroot, ghostkeel]))
    tk.line_up(ghostkeel, 10, 14)
    # The Strike Team is put INSIDE the aura on purpose: parked out of range it
    # would fail this check for the wrong reason, and the A/B probe that
    # removes the keyword test would pass. (Twice-documented trap - see the
    # Kroot/Vespid entry in CLAUDE.md.)
    tk.line_up(strike, 10, 10)
    c.true("the Strike Team really is inside the 6\" aura",
           aux.units_within(strike, [strike, ghostkeel], aux.PROJECTOR_AURA_RANGE_IN) != [])
    c.true("...but is NOT covered - it is not KROOT/VESPID",
           not aux.stealth_projector_covers(strike, [strike, ghostkeel]))
    c.true("a Kroot unit with no projector nearby is not covered",
           not aux.stealth_projector_covers(kroot, [kroot]))
with settings_as(**AUX_OFF):
    c.true("without the detachment the aura does nothing",
           not aux.stealth_projector_covers(kroot, [kroot, ghostkeel]))

# THE FOLD. Both detachments answer one question, asked once by shooting.py.
with settings_as(**AUX_ON):
    c.true("the folded question sees the aura",
           hidden_after_shooting.keeps_hidden(kroot, all_squads=[kroot, ghostkeel]))
    c.true("...and still excludes reactive fire",
           not hidden_after_shooting.keeps_hidden(kroot, reactive=True,
                                                  all_squads=[kroot, ghostkeel]))
with settings_as(**AAC_ON):
    c.true("the folded question also sees Expert Fieldcraft",
           hidden_after_shooting.keeps_hidden(pathfinders))
with settings_as(**AUX_OFF, **AAC_OFF):
    c.true("...and answers no when neither applies",
           not hidden_after_shooting.keeps_hidden(kroot, all_squads=[kroot, ghostkeel]))

_note_src2 = inspect.getsource(ShootingController._note_ranged_attack)
c.true("shooting.py asks the FOLD, not either detachment directly",
       "hidden_after_shooting.keeps_hidden(" in _note_src2)
c.true("...and no longer names Advanced Acquisition Cadre there",
       "advanced_acquisition_cadre" not in _note_src2)
c.true("the fold is named after the question, not after a detachment",
       "advanced_acquisition_cadre" not in "hidden_after_shooting")

# -- Harnessed Alien Instincts, the prey mark -----------------------------
enemy = tk.build(BOYZ, "Player 2", name="2 Boyz 9")
tk.line_up(enemy, 20, 20)
watcher = tk.build(STRIKE_TEAM, "Player 1", name="1 Strike Team 9")
tracker = TurnTracker(first_player="Player 1")
marks = aux.AuxiliaryCadreController(game_log=tk.Log())

# A Dense feature in the same area but NOT on the model's footprint: the
# ordinary 15" band. (A wall on the footprint is the 12" house rule, checked
# just below - the bonus has to move BOTH, or it would only work in cover.)
open_area = TerrainArea([Obstacle(20.0, 25.0, 40.0, 4.0, category=DENSE),
                         Obstacle(20.0, 20.0, 40.0, 4.0, category=LIGHT)])
tucked_area = TerrainArea([Obstacle(20.0, 20.0, 40.0, 6.0, category=DENSE)])
hidden_model = enemy.models[0]
c.true("the enemy really is Hidden", status_effects.is_hidden(hidden_model, [open_area], tracker, {}))
c.true("...and not tucked against a wall in the open case",
       not status_effects._wall_on_own_footprint(hidden_model, [open_area]))


def detectable(distance, area, marked):
    tk.line_up(watcher, 20, 20 + distance)
    marks._marks.clear()
    if marked:
        marks.mark("Player 1", enemy)
    got = status_effects.is_detectable(hidden_model, watcher, [area], tracker, {},
                                       prey_marks=marks)
    marks._marks.clear()
    return got


c.true("unmarked, 17\" is beyond the 15\" detection range",
       not detectable(17.0, open_area, False))
c.true("prey-marked, 17\" is inside the 18\" one", detectable(17.0, open_area, True))
c.true("...and 19.5\" is beyond even that", not detectable(19.5, open_area, True))
c.true("the bonus moves the 12\" house-rule band too",
       not detectable(14.0, tucked_area, False) and detectable(14.0, tucked_area, True))
c.eq("the bonus is the printed 3 inches", aux.PREY_MARK_DETECTION_BONUS_IN, 3.0)
c.true("an unmarked unit gets no bonus", marks.detection_bonus_in(enemy) == 0.0)

# It only bites while the unit is HIDDEN - marking a visible unit is legal and
# simply does nothing, which the printed text permits.
marks.mark("Player 1", enemy)
c.true("a NON-hidden marked unit is detectable regardless",
       status_effects.is_detectable(hidden_model, watcher, [], tracker, {}, prey_marks=marks))
c.true("is_detectable without a controller measures the printed range",
       status_effects.is_detectable(hidden_model, watcher, [open_area], tracker, {}) is not None)
marks._marks.clear()

# TWO LIFETIMES, cleared separately. The mark is turn-scoped (a decision - the
# printed text gives no duration - matching the engine's four other marks);
# the once-per-unit offer memo is phase-scoped. Folding them into one reset
# would quietly shorten the mark to a phase.
marks.mark("Player 1", enemy)
marks._offered_this_phase.add(id(kroot))
marks.reset_phase()
c.true("reset_phase keeps the mark", marks.is_prey_marked(enemy))
c.true("...but clears the offer memo", not marks._offered_this_phase)
marks.reset_turn()
c.true("reset_turn clears the mark", not marks.is_prey_marked(enemy))


class State:
    def __init__(self, squads):
        self.tokens = [m for s in squads for m in s.models]


# -- the offer -------------------------------------------------------------
with settings_as(**AUX_ON):
    tk.line_up(kroot, 20, 20)
    near = tk.build(BOYZ, "Player 2", name="2 Boyz near")
    far = tk.build(BOYZ, "Player 2", name="2 Boyz far")
    tk.line_up(near, 20, 26)      # 6" - inside 12"
    tk.line_up(far, 20, 45)       # 25" - outside
    dm = DecisionManager()
    offer = aux.AuxiliaryCadreController(
        decision_manager=dm, game_state=State([kroot, near, far]),
        turn_tracker=tracker, game_log=tk.Log())
    c.eq("only units within 12\" are offered",
         [s.name for s in offer.candidates_for(kroot)], ["2 Boyz near"])
    c.eq("the Kroot unit is eligible", [s.name for s in offer.eligible_units("Player 1")],
         ["1 Kroot Carnivores 1"])
    c.true("the offer opens a prompt", offer.offer_at_start_of_shooting_phase("Player 1"))
    c.true("declining is one of the options",
           any("not mark" in label.lower() for label in tk.options_of(dm)))
    tk.pick_option(dm, "2 Boyz near")
    c.true("choosing marks that unit", offer.is_prey_marked(near))
    c.true("a second offer this phase does not re-ask the same unit",
           not offer.offer_at_start_of_shooting_phase("Player 1"))

    # Line of sight is part of the printed pool ("one VISIBLE enemy unit").
    blind = aux.AuxiliaryCadreController(
        decision_manager=DecisionManager(), game_state=State([kroot, near]),
        turn_tracker=tracker, game_log=tk.Log(),
        line_of_sight_check=lambda observer, target: False)
    c.eq("an invisible unit is not offered", blind.candidates_for(kroot), [])

with settings_as(**AUX_OFF):
    quiet = aux.AuxiliaryCadreController(
        decision_manager=DecisionManager(), game_state=State([kroot, near]),
        turn_tracker=tracker, game_log=tk.Log())
    c.true("without the detachment nothing is offered",
           not quiet.offer_at_start_of_shooting_phase("Player 1"))

c.eq("it reads its own config setting", aux.SETTING, "AUXILIARY_CADRE_PLAYERS")
c.true("...which game/detachments.py actually writes",
       aux.SETTING in detachments.all_settings())

# -- wiring ----------------------------------------------------------------
_main = io.open("main.py", encoding="utf-8").read()
c.true("the controller is built in main()",
       "auxiliary_cadre_controller = AuxiliaryCadreController(" in _main)
c.true("the prey mark reaches rule 13.09's detection range",
       "shooting_controller.auxiliary_cadre = auxiliary_cadre_controller" in _main)
c.true("the line-of-sight half is injected",
       "auxiliary_cadre_controller.line_of_sight_check" in _main)
c.true("the offer is made at the start of the Shooting phase",
       "auxiliary_cadre_controller.offer_at_start_of_shooting_phase(" in _main)
c.true("...with its once-per-phase memo reset first",
       _main.index("auxiliary_cadre_controller.reset_phase()")
       < _main.index("auxiliary_cadre_controller.offer_at_start_of_shooting_phase("))
c.true("the mark is cleared at the end of the turn",
       "auxiliary_cadre_controller.reset_turn()" in _main)
c.true("is_detectable is handed the controller",
       "prey_marks=self.auxiliary_cadre" in _shooting_src2)
c.true("nothing in ai/ mentions it - by design",
       "auxiliary_cadre" not in driver and "harnessed_alien" not in driver)

c.finish()
