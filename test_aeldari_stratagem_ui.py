"""Are the nineteen Aeldari panel Stratagems really OFFERED, and at the right
moment? - measured by drawing the real ActionPanel.

WHY THIS FILE EXISTS
--------------------
The T'au detachments shipped with a batch of defects that every unit test
missed, and they were all the same shape: the rule was right, the controller
was right, and the button was never on the screen. "wird nie angeboten",
"funktioniert auch nicht", "in der falschen Phase". CLAUDE.md's chapter on
those eleven reports is the taxonomy.

Nothing in this repo could have caught that for the Aeldari, because NO TEST
ANYWHERE passed `proactive_stratagems=` to ActionPanel.draw(). The nineteen
Aeldari buttons - the largest group of them in the game - were proved by
`"proactive_stratagems.add(X(" in main_src` and by driving can_use() straight.
Both of those hold perfectly while the panel draws nothing at all.

So this file renders. It builds the real registry with the real controllers,
selects a legal bearer, and draws the real ActionPanel once per phase, then
asks which Stratagem names came out of the button funnel.

THE PHASE MATRIX IS THE POINT (section 2). Every Stratagem is rendered in all
FIVE phases and has to appear in exactly the ones its printed WHEN names -
which means four negatives per Stratagem. A test that only renders the right
phase cannot tell "offered correctly" from "offered always", and "offered in
the wrong phase" was one of the three reported T'au failures.

TWO THINGS MAKE THE NEGATIVES MEAN SOMETHING, and both have their own section:
section 0 proves the render produced a panel at all (a draw that fell into
some other branch draws ZERO buttons and passes every absence check by
inspecting nothing), and section 3 proves the buttons are there because the
detachment gate opened rather than because the panel draws them regardless.

WHY A SEPARATE FILE from test_aeldari_detachment_stratagems.py: that one is
cut by detachment, seven chapters each with its own squads and stubs, and it
owns the RULES. This is one matrix across all nineteen at once and needs a
different stage from its first line - a display mode, a real ActionPanel, a
real MovementController with select() called. Same split as
test_unmodified_six_ui.py.

SIX OF THE EIGHT DETACHMENTS CANNOT BE FIELDED by any shipped list (the
Aeldari ArmyList declares Seer Council and Path of the Outcast, and
game/detachments.py writes every other setting blank), so each section
switches its own flag on with testkit's settings_as. That is a fact about the
roster, not about the code, and section 8 pins it as a measured number.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import io                                                            # noqa: E402
import re                                                            # noqa: E402

import pygame                                                        # noqa: E402

import testkit as tk                                                 # noqa: E402
from testkit import Checks, settings_as                              # noqa: E402
from game import config                                              # noqa: E402
from game.command_points import CommandPointManager                  # noqa: E402
from game.decision import DecisionManager                            # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.factions import aeldari as ae                              # noqa: E402
from game.movement import MovementController                         # noqa: E402
from game.proactive_stratagems import ProactiveStratagems            # noqa: E402
from game.shooting import ShootingController                         # noqa: E402
from game.stratagems import StratagemController                      # noqa: E402
from game.turn import (PHASES, PHASE_CHARGE, PHASE_COMMAND,          # noqa: E402
                       PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING,
                       TurnTracker)
from game import rules_text                                          # noqa: E402
from game.ui import action_panel                                     # noqa: E402
from game.ui.action_panel import ActionPanel                         # noqa: E402

# The nineteen modules, imported under the same short names the rules suite
# uses so the two files read alike.
from game import armoured_soulsight as aso                           # noqa: E402
from game import aspect_doom_inescapable as adi                      # noqa: E402
from game import aspect_preternatural_precision as app               # noqa: E402
from game import aspect_warrior_focus as awf                         # noqa: E402
from game import conclave_blades_from_beyond as cbb                  # noqa: E402
from game import conclave_seers_eye as cse                           # noqa: E402
from game import conclave_soul_bridge as csb                         # noqa: E402
from game import conclave_spirit_token as cst                        # noqa: E402
from game import fate_inescapable as fate                            # noqa: E402
from game import guardian_blades_of_asuryan as gba                   # noqa: E402
from game import guardian_time_to_strike as gts                      # noqa: E402
from game import guardian_warding_salvoes as gws                     # noqa: E402
from game import presentiment_of_dread as pod                        # noqa: E402
from game import unshrouded_truth as ut                              # noqa: E402
from game import warhost_blitzing_firepower as wbf                   # noqa: E402
from game import windrider_daring_riders as wdr                      # noqa: E402
from game import windrider_death_from_on_high as wdh                 # noqa: E402
from game import windrider_focused_firepower as wff                  # noqa: E402
from game import windrider_wind_of_blades as wwb                     # noqa: E402

c = Checks("Aeldari Stratagem buttons")

pygame.init()
pygame.display.set_mode((1200, 900))

D = ae.AELDARI.datasheets
HUMAN = "Player 1"
FOE = "Player 2"


def sq(name, owner=HUMAN):
    return tk.build(D[name], owner, name="%s %s 1" % (owner[-1], name))


def turn_at(phase, owner=HUMAN):
    tracker = TurnTracker(first_player=owner)
    tracker.phase_index = PHASES.index(phase)
    tracker.turn_owner = owner
    tracker.active_player = owner
    return tracker


def strat(cp=10):
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=tk.Log())


class _ShootStub:
    def __init__(self, active=None):
        self.active_squad = active


class _IngressStub:
    def __init__(self, arrived=()):
        self.ingressed_this_turn = set(arrived)


class _ReservesState:
    def __init__(self, reserves=()):
        self.reserves = list(reserves)
        self.embarked_squads = {}
        self.tokens = ALL_TOKENS
        self.objectives = []


class _BattleShockStub:
    def start_forced_roll(self, *a, **kw):
        return True


# --------------------------------------------------------------- the bearers
# One legal target per detachment, positioned so the geometric clauses hold.
#
# REBUILT PER SECTION, and that is not tidiness: buying a Stratagem APPLIES it,
# and several of the nineteen leave a mark on the squad they were bought for
# (a grant, a spent token, a secured objective). Sections that click therefore
# poison every later section that renders the same squad - which showed up as
# "the button is gone" three sections further down, in a place that had
# nothing to do with the click. One stage per section, so a section can only
# ever measure its own doing.

BEARERS = (("falcon", "Falcon", HUMAN, 10.0),          # Armoured Warhost: VEHICLE
           ("guards", "Guardian Defenders", HUMAN, 14.0),
           ("storm", "Storm Guardians", HUMAN, 18.0),
           ("riders", "Windriders", HUMAN, 22.0),
           ("avengers", "Dire Avengers", HUMAN, 26.0),
           ("wguard", "Wraithguard", HUMAN, 30.0),
           ("warlocks", "Warlock Conclave", HUMAN, 31.0),   # Seer Council psyker
           ("wblades", "Wraithblades", HUMAN, 32.0),
           ("banshees", "Howling Banshees", HUMAN, 36.0),
           ("reapers", "Dark Reapers", HUMAN, 40.0),
           ("avatar", "Avatar of Khaine", HUMAN, 44.0))

B = {}
ALL_TOKENS = []


def build_bearers():
    """A fresh board. ALL_TOKENS is mutated IN PLACE, because controllers and
    stubs are handed the list itself and have to keep seeing the live one."""
    B.clear()
    for key, sheet, owner, x in BEARERS:
        B[key] = tk.line_up(sq(sheet, owner), x, 20.0, spacing=1.2)
    B["foe"] = tk.line_up(sq("Guardian Defenders", FOE), 20.0, 28.0, spacing=1.2)
    ALL_TOKENS[:] = [m for s in B.values() for m in s.models]
    return B


build_bearers()


class _Area:
    """An objective is asked for range through its terrain_area, never its
    own coordinates - the same shape the rules suite uses."""

    def __init__(self, x, y):
        self.x, self.y = x, y

    def distance_to_model(self, m):
        return ((m.x_in - self.x) ** 2 + (m.y_in - self.y) ** 2) ** 0.5


class _Objective:
    """Spirit Token's target: one this unit controls AND stands on."""

    def __init__(self, squad):
        self.name = "Central Objective"
        self.controlled_by = squad.owner
        self.terrain_area = _Area(squad.models[0].x_in, squad.models[0].y_in)
        self.secured_by = None

    def secure_for(self, player):
        self.secured_by = player


# ----------------------------------------------------------------- the table
# key -> (module, factory, bearer, {phases it is printed for}, owner-sensitive,
#         settings dict). The phases are transcribed from the printed WHEN and
#         are the whole assertion of section 2.

AW = dict(ARMOURED_WARHOST_PLAYERS=(HUMAN,))
GB = dict(GUARDIAN_BATTLEHOST_PLAYERS=(HUMAN,))
WH = dict(WINDRIDER_HOST_PLAYERS=(HUMAN,))
WA = dict(WARHOST_PLAYERS=(HUMAN,))
SC = dict(SPIRIT_CONCLAVE_PLAYERS=(HUMAN,))
AH = dict(ASPECT_HOST_PLAYERS=(HUMAN,))
SE = dict(SEER_COUNCIL_PLAYERS=(HUMAN,))


def _spec(mod, name_const, make, bearer, phases, owner_phases, flags):
    """`owner_phases` is a SUBSET of `phases`, not a flag on the Stratagem.

    The printed WHEN says "your <phase>" or "the <phase>", and the four
    Stratagems that name two phases say ONE OF EACH: "your Shooting phase or
    the Fight phase". A single owner boolean per Stratagem gets those four
    wrong in whichever half it does not describe."""
    assert set(owner_phases) <= set(phases), name_const
    return dict(module=mod, name=getattr(mod, name_const), make=make,
                bearer=bearer, phases=frozenset(phases),
                owner_phases=frozenset(owner_phases), flags=flags)


SPECS = [
    # --- Seer Council ------------------------------------------------------
    _spec(pod, "PRESENTIMENT_NAME",
          lambda s: pod.PresentimentOfDreadController(
              s, battle_shock=_BattleShockStub(), turn_tracker=None,
              decision_manager=DecisionManager(), game_log=tk.Log(),
              all_tokens=ALL_TOKENS),
          "warlocks", {PHASE_COMMAND}, set(), SE),
    _spec(fate, "FATE_INESCAPABLE_NAME",
          lambda s: fate.FateInescapableController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              game_log=tk.Log(), all_tokens=ALL_TOKENS),
          "warlocks", {PHASE_SHOOTING}, {PHASE_SHOOTING}, SE),
    _spec(ut, "UNSHROUDED_TRUTH_NAME",
          lambda s: ut.UnshroudedTruthController(
              s, game_state=_ReservesState(), movement_controller=None,
              turn_tracker=None, game_log=tk.Log(), all_tokens=ALL_TOKENS),
          "warlocks", {PHASE_MOVEMENT}, {PHASE_MOVEMENT}, SE),

    # --- Armoured Warhost --------------------------------------------------
    _spec(aso, "SOULSIGHT_NAME",
          lambda s: aso.SoulsightController(
              s, shooting_controller=_ShootStub(B["falcon"]), turn_tracker=None,
              game_log=tk.Log()),
          "falcon", {PHASE_SHOOTING}, {PHASE_SHOOTING}, AW),

    # --- Guardian Battlehost -----------------------------------------------
    _spec(gws, "WARDING_SALVOES_NAME",
          lambda s: gws.WardingSalvoesController(s, turn_tracker=None,
                                                 game_log=tk.Log()),
          "guards", {PHASE_SHOOTING, PHASE_FIGHT}, {PHASE_SHOOTING}, GB),
    _spec(gts, "TIME_TO_STRIKE_NAME",
          lambda s: gts.TimeToStrikeController(s, turn_tracker=None,
                                               game_log=tk.Log()),
          "storm", {PHASE_MOVEMENT}, {PHASE_MOVEMENT}, GB),
    _spec(gba, "BLADES_OF_ASURYAN_NAME",
          lambda s: gba.BladesOfAsuryanController(s, turn_tracker=None,
                                                  game_log=tk.Log()),
          "guards", {PHASE_SHOOTING}, {PHASE_SHOOTING}, GB),

    # --- Windrider Host ----------------------------------------------------
    _spec(wwb, "WIND_OF_BLADES_NAME",
          lambda s: wwb.WindOfBladesController(s, turn_tracker=None,
                                               game_log=tk.Log()),
          "riders", {PHASE_MOVEMENT}, {PHASE_MOVEMENT}, WH),
    _spec(wff, "FOCUSED_FIREPOWER_NAME",
          lambda s: wff.FocusedFirepowerController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              game_log=tk.Log()),
          "riders", {PHASE_SHOOTING}, {PHASE_SHOOTING}, WH),
    _spec(wdh, "DEATH_FROM_ON_HIGH_NAME",
          lambda s: wdh.DeathFromOnHighController(
              s, ingress_controller=_IngressStub([B["riders"]]),
              shooting_controller=_ShootStub(), turn_tracker=None,
              game_log=tk.Log()),
          "riders", {PHASE_SHOOTING, PHASE_FIGHT}, {PHASE_SHOOTING}, WH),
    _spec(wdr, "DARING_RIDERS_NAME",
          lambda s: wdr.DaringRidersController(
              s, game_state=_ReservesState([B["riders"]]), turn_tracker=None,
              game_log=tk.Log()),
          "riders", {PHASE_MOVEMENT}, {PHASE_MOVEMENT}, WH),

    # --- Warhost -----------------------------------------------------------
    _spec(wbf, "BLITZING_FIREPOWER_NAME",
          lambda s: wbf.BlitzingFirepowerController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              game_log=tk.Log()),
          "avengers", {PHASE_SHOOTING}, {PHASE_SHOOTING}, WA),

    # --- Spirit Conclave ---------------------------------------------------
    _spec(cse, "SEERS_EYE_NAME",
          lambda s: cse.SeersEyeController(
              s, all_tokens=ALL_TOKENS, shooting_controller=_ShootStub(),
              turn_tracker=None, decision_manager=DecisionManager(),
              game_log=tk.Log()),
          "wguard", {PHASE_SHOOTING, PHASE_FIGHT}, {PHASE_SHOOTING}, SC),
    _spec(cbb, "BLADES_FROM_BEYOND_NAME",
          lambda s: cbb.BladesFromBeyondController(s, turn_tracker=None,
                                                   game_log=tk.Log()),
          "wblades", {PHASE_FIGHT}, set(), SC),
    _spec(csb, "SOUL_BRIDGE_NAME",
          lambda s: csb.SoulBridgeController(
              s, all_tokens=ALL_TOKENS, turn_tracker=None,
              decision_manager=DecisionManager(), game_log=tk.Log()),
          "wguard", {PHASE_COMMAND}, {PHASE_COMMAND}, SC),
    _spec(cst, "SPIRIT_TOKEN_NAME",
          lambda s: cst.SpiritTokenController(
              s, objectives=[_Objective(B["wguard"])], turn_tracker=None,
              decision_manager=DecisionManager(), game_log=tk.Log()),
          "wguard", {PHASE_MOVEMENT}, {PHASE_MOVEMENT}, SC),

    # --- Aspect Host -------------------------------------------------------
    _spec(awf, "WARRIOR_FOCUS_NAME",
          lambda s: awf.WarriorFocusController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              game_log=tk.Log()),
          "banshees", {PHASE_SHOOTING, PHASE_FIGHT}, {PHASE_SHOOTING}, AH),
    _spec(adi, "DOOM_INESCAPABLE_NAME",
          lambda s: adi.DoomInescapableController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              game_log=tk.Log()),
          "avatar", {PHASE_SHOOTING}, {PHASE_SHOOTING}, AH),
    _spec(app, "PRETERNATURAL_PRECISION_NAME",
          lambda s: app.PreternaturalPrecisionController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              decision_manager=DecisionManager(), game_log=tk.Log()),
          "reapers", {PHASE_SHOOTING}, {PHASE_SHOOTING}, AH),
]

ALL_PHASES = (PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE,
              PHASE_FIGHT)

#: Blades from Beyond is the one owner-BLIND Stratagem in a phase where a
#: unit can still be picked, so it is the only one whose "the <phase>"
#: half is reachable through the panel at all.
_BLADES_SPEC = next(s for s in SPECS if s["name"] == cbb.BLADES_FROM_BEYOND_NAME)
SC_ON_UI = SC


def primary(spec):
    """The phase a spec is exercised in outside the matrix - the FIRST one
    its WHEN names in game order, so the two-phase Stratagems are driven in
    Shooting (where their owner clause lives) rather than alphabetically."""
    return next(p for p in ALL_PHASES if p in spec["phases"])


# ------------------------------------------------------------- the render rig

_panel = ActionPanel()
_surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
_rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900)
_labels = []
_real_button = ActionPanel._draw_button


def _spy_button(self, surface, rect, label, *a, **kw):
    _labels.append(label)
    return _real_button(self, surface, rect, label, *a, **kw)


ActionPanel._draw_button = _spy_button


def render(squad, phase, registry, owner=HUMAN, tracker=None):
    """Draw the real panel for `squad` in `phase` and report what came out.

    Returns (labels, stratagem_names, buttons). `mover.select()` is not
    optional: _draw_movement_ui() keys on movement_controller.selected_squad
    and on nothing else, so a render without it draws the no-selection screen
    and every absence check below would pass by measuring nothing. That exact
    omission is why the T'au suite could not see Aggressive Mobility."""
    tracker = tracker or turn_at(phase, owner)
    mover = MovementController([], tk.Log(), owner, DiceManager(), tracker,
                               ALL_TOKENS)
    mover.select(squad.models[0])
    shooter = ShootingController(ALL_TOKENS, DiceManager(), tk.Log(),
                                 turn_tracker=tracker,
                                 decision_manager=DecisionManager())
    _labels.clear()
    _surface.fill((0, 0, 0))
    _panel.draw(_surface, _rect, mover, shooter,
                dice_manager=DiceManager(), proactive_stratagems=registry)
    return (list(_labels), [n for _, n in _panel._stratagem_buttons],
            list(_panel._buttons))


def registry_for(specs, sc):
    reg = ProactiveStratagems()
    built = {}
    for spec in specs:
        ctrl = spec["make"](sc)
        built[spec["name"]] = ctrl
        reg.add(ctrl)
    return reg, built


def drain(ctrl, limit=6):
    """Answer the follow-up questions a Stratagem asks after its button.

    Three of the nineteen open a DecisionManager prompt of their own before
    they charge (which abilities, which unit, spend an Aspect Shrine token) -
    so a test that stops at the click sees "bought and did nothing", which is
    exactly one of the reported T'au failures and would be indistinguishable
    from it. Always the FIRST option, which is the acting one; declining is a
    different question and has its own line in the rules suite."""
    dm = getattr(ctrl, "decision_manager", None)
    steps = 0
    while dm is not None and dm.is_pending and steps < limit:
        dm.choose(0)
        steps += 1
    return steps


def press(name, buttons):
    """Click the drawn Stratagem button called `name`; True if there was one.

    RETURNS rather than raises when there is none. A probe that removes the
    buttons has to turn this file RED, not crash it - a crash hides which
    check broke, and this repo has been caught by that trap more than a dozen
    times."""
    rect = next((r for r, n in _panel._stratagem_buttons if n == name), None)
    if rect is None:
        return False
    callback = next((cb for r, cb in buttons if r == rect), None)
    if callback is None:
        return False
    callback()
    return True


def at_phase(ctrl, phase, owner=HUMAN):
    """Point a controller's clock at `phase`. Every one of the nineteen takes
    a turn_tracker; the table builds them with None so one tracker can be
    shared by a whole render."""
    ctrl.turn_tracker = turn_at(phase, owner)
    return ctrl


# --- 0. the rig is live ----------------------------------------------------
print("--- 0. the rig ---")

_sc0 = strat()
_reg0, _built0 = registry_for([], _sc0)
_l0, _s0, _b0 = render(B["guards"], PHASE_MOVEMENT, _reg0)

# THE MOST IMPORTANT LINE IN THIS FILE. Every negative below is "this name is
# not among the drawn buttons", and a render that fell into some other branch
# of _draw_dispatch() - or into _draw_movement_ui()'s no-selection screen -
# draws no buttons at all and satisfies all of them by inspecting nothing.
c.true("the panel really draws its ordinary movement buttons", len(_l0) >= 2)
c.true("...including one this file does not own", any("Move" in l for l in _l0))
c.eq("...and with an empty registry, no Stratagem button at all", _s0, [])
c.true("...while the ordinary buttons are still clickable", len(_b0) >= 2)

# _stratagem_buttons is filled ONLY for accent="stratagem" (action_panel.py's
# _draw_button), so membership IS the violet-accent assertion - no pixel scan
# needed, and the two handles are independent.
_panel_src = io.open("game/ui/action_panel.py", encoding="utf-8").read()
c.true("_stratagem_buttons records exactly the accent='stratagem' draws",
       'if accent == "stratagem":' in _panel_src
       and "self._stratagem_buttons.append(" in _panel_src)


# --- 1. the registry -> panel contract -------------------------------------
print("--- 1. the contract ---")


class _Fake:
    def __init__(self, name, usable=True):
        self.name, self.usable, self.used = name, usable, []

    def can_use(self, squad):
        return self.usable

    def use(self, squad):
        self.used.append(squad)
        return True

    def panel_label(self, squad):
        return "%s (1 CP)" % self.name


_yes, _no = _Fake("Yes Stratagem"), _Fake("No Stratagem", usable=False)
_reg1 = ProactiveStratagems()
_reg1.add(_yes)
_reg1.add(_no)
_l1, _s1, _b1 = render(B["guards"], PHASE_MOVEMENT, _reg1)
c.true("a usable Stratagem is drawn", "Yes Stratagem" in _s1)
c.true("...and its label carries the cost",
       any("Yes Stratagem (1 CP)" in l for l in _l1))
c.true("an unusable one is drawn nowhere",
       "No Stratagem" not in _s1
       and not any("No Stratagem" in l for l in _l1))

# The button really reaches use() - the registry binds the squad with a
# default argument, which is what stops the late-binding loop bug.
c.true("...and its button can be pressed", press("Yes Stratagem", _b1))
c.eq("...and clicking it reaches use() with the selected squad",
     [s.name for s in _yes.used], [B["guards"].name])


# --- 2. the phase matrix ---------------------------------------------------
print("--- 2. the phase matrix ---")

_matrix_rows = 0
for spec in SPECS:
    with settings_as(**spec["flags"]):
        build_bearers()
        _sc = strat()
        _reg, _built = registry_for([spec], _sc)
        _ctrl = _built[spec["name"]]
        _seen = set()
        for _phase in ALL_PHASES:
            at_phase(_ctrl, _phase)
            _, _names, _ = render(B[spec["bearer"]], _phase, _reg)
            if spec["name"] in _names:
                _seen.add(_phase)
            _matrix_rows += 1
        c.eq("%s is offered in exactly the phases its WHEN names" % spec["name"],
             sorted(_seen), sorted(spec["phases"]))

c.eq("...and the matrix really rendered 19 x 5 panels", _matrix_rows,
     len(SPECS) * len(ALL_PHASES))
c.eq("...for all nineteen Aeldari panel Stratagems", len(SPECS), 19)


# --- 3. the detachment gate, at the panel ----------------------------------
print("--- 3. the gate ---")

# What makes section 2 non-vacuous: with the flag off, not one of the nineteen
# appears in ANY phase. If they were drawn regardless of can_use(), section 2
# would pass just as well.
_off_sightings = []
for spec in SPECS:
    _off = {k: () for k in spec["flags"]}
    with settings_as(**_off):
        build_bearers()
        _sc = strat()
        _reg, _built = registry_for([spec], _sc)
        _ctrl = _built[spec["name"]]
        for _phase in ALL_PHASES:
            at_phase(_ctrl, _phase)
            _, _names, _ = render(B[spec["bearer"]], _phase, _reg)
            if spec["name"] in _names:
                _off_sightings.append((spec["name"], _phase))
c.eq("with the detachment off, none of the nineteen is ever drawn",
     _off_sightings, [])


# --- 4. "your" phase versus "the" phase ------------------------------------
print("--- 4. whose phase ---")

# The printed WHEN is either "your <phase>" or "the <phase>", one word apart,
# and the four two-phase Stratagems say ONE OF EACH.
#
# MEASURED AT can_use(), NOT AT THE PANEL, and that is a finding rather than a
# convenience: rendered with the turn flipped, the panel draws NOTHING AT ALL
# for most phases, because MovementController.select() refuses a unit outside
# its own turn and _draw_movement_ui() then shows "No unit selected.". An
# absence measured there would be the selection refusing, not the Stratagem -
# so both halves would pass with the owner clause deleted. The panel-level
# consequence is pinned separately just below.
for spec in SPECS:
    with settings_as(**spec["flags"]):
        build_bearers()
        _sc = strat()
        _reg, _built = registry_for([spec], _sc)
        _ctrl = _built[spec["name"]]
        for _phase in sorted(spec["phases"]):
            _ctrl.turn_tracker = turn_at(_phase, FOE)
            _own = _phase in spec["owner_phases"]
            c.eq("%s in the opponent's %s phase: %s"
                 % (spec["name"], _phase, "'your', so no" if _own else "'the', so yes"),
                 bool(_ctrl.can_use(B[spec["bearer"]])), not _own)

# THE PANEL-LEVEL CONSEQUENCE, measured rather than assumed. A unit cannot be
# picked at all in most of the opponent's phases, so an owner-blind Stratagem's
# button is unreachable there even though its can_use() says yes - the reactive
# window, not this panel, is where those are answered. Pinned because it is the
# reason section 4 does not test the owner clause through a render.
_selectable = []
for _phase in ALL_PHASES:
    _tracker = turn_at(_phase, FOE)
    _mv = MovementController([], tk.Log(), HUMAN, DiceManager(), _tracker, ALL_TOKENS)
    _mv.select(B["wblades"].models[0])
    if _mv.selected_squad is not None:
        _selectable.append(_phase)
c.true("a unit cannot even be picked in most of the opponent's phases",
       len(_selectable) < len(ALL_PHASES))
c.true("...so the Fight phase, where it can, is where the owner-blind ones live",
       PHASE_FIGHT in _selectable)
with settings_as(**SC_ON_UI):
    _sc4 = strat()
    _reg4, _built4 = registry_for([_BLADES_SPEC], _sc4)
    _built4[_BLADES_SPEC["name"]].turn_tracker = turn_at(PHASE_FIGHT, FOE)
    _, _n4, _ = render(B["wblades"], PHASE_FIGHT, _reg4, owner=HUMAN,
                       tracker=turn_at(PHASE_FIGHT, FOE))
    c.true("...and Blades from Beyond really is on the panel there",
           _BLADES_SPEC["name"] in _n4)


# --- 5. rule 15.01, at the panel -------------------------------------------
print("--- 5. once per phase ---")

# One Stratagem per phase (15.01). The button has to GO once it is bought.
#
# THAT IT COMES BACK IS ASKED OF THE LEDGER, NOT OF THE PANEL, and that is a
# finding rather than a shortcut: several of the nineteen also mark the squad
# they were bought for, and those marks outlive a phase reset on purpose (Fate
# Inescapable refuses a unit that already carries its grant). Asserting the
# BUTTON returns would be asserting the effect had expired, which is a
# different rule and not this one.
_15_specs = [s for s in SPECS if PHASE_SHOOTING in s["phases"]][:3]
for spec in _15_specs:
    with settings_as(**spec["flags"]):
        build_bearers()
        _sc = strat()
        _reg, _built = registry_for([spec], _sc)
        _ctrl = at_phase(_built[spec["name"]], PHASE_SHOOTING)
        _squad = B[spec["bearer"]]
        _, _names, _buttons = render(_squad, PHASE_SHOOTING, _reg)
        c.true("%s is on the panel before it is bought" % spec["name"],
               spec["name"] in _names)
        c.true("...and its button can be pressed", press(spec["name"], _buttons))
        drain(_ctrl)
        _, _names2, _ = render(_squad, PHASE_SHOOTING, _reg)
        c.true("...and gone from it once bought", spec["name"] not in _names2)
        c.true("...because 15.01 refuses a second use this phase",
               not _sc.can_use(HUMAN, _ctrl._stratagem, [_squad]))
        _sc.reset_phase()
        c.true("...and the ledger frees it again next phase",
               _sc.can_use(HUMAN, _ctrl._stratagem, [_squad]))


# --- 6. clicking really spends the CP --------------------------------------
print("--- 6. the click ---")

# THE WHOLE PATH, button to payment. Three of the nineteen answer a follow-up
# question first (which abilities, which unit, spend a token?) and only charge
# once it is answered - so a test that stops at the click reports them as
# "bought and did nothing", which is one of the reported T'au failures and
# would be indistinguishable from the real thing. drain() answers the chain.
_bought, _undrawn, _unbought = 0, [], []
for spec in SPECS:
    with settings_as(**spec["flags"]):
        build_bearers()
        _sc = strat(cp=10)
        _reg, _built = registry_for([spec], _sc)
        _phase = primary(spec)
        _ctrl = at_phase(_built[spec["name"]], _phase)
        _, _names, _buttons = render(B[spec["bearer"]], _phase, _reg)
        if spec["name"] not in _names:
            _undrawn.append(spec["name"])
            continue
        _before = _sc.command_points.cp[HUMAN]
        press(spec["name"], _buttons)
        _steps = drain(_ctrl)
        if _sc.command_points.cp[HUMAN] < _before:
            _bought += 1
        else:
            _unbought.append((spec["name"], _steps))
c.eq("every one of the nineteen is drawn in the phase its WHEN names",
     _undrawn, [])
c.eq("...and every one really spends CP when its button is clicked through",
     _unbought, [])
c.eq("...all nineteen of them", _bought, len(SPECS))

# The counter-proof: a phase it does not name draws nothing and charges
# nothing. Presentiment of Dread is a Command-phase Stratagem, so Shooting is
# a phase it never names.
with settings_as(**SPECS[0]["flags"]):
    build_bearers()
    _sc6 = strat(cp=10)
    _reg6, _built6 = registry_for([SPECS[0]], _sc6)
    at_phase(_built6[SPECS[0]["name"]], PHASE_SHOOTING)   # not its WHEN
    _, _names6, _ = render(B[SPECS[0]["bearer"]], PHASE_SHOOTING, _reg6)
    c.true("...and a phase where it is not drawn spends nothing",
           SPECS[0]["name"] not in _names6
           and _sc6.command_points.cp[HUMAN] == 10)


# --- 7. the label the tooltip has to resolve -------------------------------
print("--- 7. the label ---")

# The drawn label is "<name> (<cost>)", and action_panel._stratagem_name_in()
# strips the cost back off for the hover tooltip, which then looks the name up
# in the printed corpus. A name that does not survive that round trip is a
# button whose rules never come up on screen - so it is asked of
# rules_text.stratagem_named(), the tooltip's OWN lookup, rather than by
# searching the .md text (which reports a false miss on the one name the
# corpus prints with a typographic apostrophe: SEER'S EYE).
_DETACHMENT_OF = {
    "SEER_COUNCIL_PLAYERS": "Seer Council",
    "ARMOURED_WARHOST_PLAYERS": "Armoured Warhost",
    "GUARDIAN_BATTLEHOST_PLAYERS": "Guardian Battlehost",
    "WINDRIDER_HOST_PLAYERS": "Windrider Host",
    "WARHOST_PLAYERS": "Warhost",
    "SPIRIT_CONCLAVE_PLAYERS": "Spirit Conclave",
    "ASPECT_HOST_PLAYERS": "Aspect Host",
}
_unresolved = []
for spec in SPECS:
    with settings_as(**spec["flags"]):
        build_bearers()
        _sc = strat()
        _reg, _built = registry_for([spec], _sc)
        _phase = primary(spec)
        at_phase(_built[spec["name"]], _phase)
        _l, _names, _ = render(B[spec["bearer"]], _phase, _reg)
        _drawn = [l for l in _l if l.startswith(spec["name"])]
        if not _drawn:
            _unresolved.append(spec["name"] + " (never drawn)")
            continue
        if action_panel._stratagem_name_in(_drawn[0]) != spec["name"]:
            _unresolved.append(spec["name"] + " (label does not round-trip)")
        _det = _DETACHMENT_OF[list(spec["flags"])[0]]
        if rules_text.stratagem_named("AELDARI", [_det], spec["name"]) is None:
            _unresolved.append(spec["name"] + " (no printed rules)")
c.eq("every drawn label round-trips and finds its printed rules", _unresolved, [])


# --- 8. the twenty-third, and the six unreachable detachments --------------
print("--- 8. absence ---")

_main = io.open("main.py", encoding="utf-8").read()
_registered = set(re.findall(r"proactive_stratagems\.add\(\s*(\w+)\(", _main))
_registered |= set(re.findall(r"proactive_stratagems\.add\((\w+_controller)\)", _main))

# A twentieth Aeldari button cannot appear without moving this line. The T'au
# names in the same registry are listed so the difference is Aeldari-only.
_AELDARI_BUTTONS = {
    "presentiment_controller", "fate_inescapable_controller",
    "unshrouded_truth_controller", "SoulsightController",
    "WardingSalvoesController", "TimeToStrikeController",
    "BladesOfAsuryanController", "WindOfBladesController",
    "FocusedFirepowerController", "DeathFromOnHighController",
    "DaringRidersController", "BlitzingFirepowerController",
    "SeersEyeController", "BladesFromBeyondController", "SoulBridgeController",
    "SpiritTokenController", "WarriorFocusController",
    "DoomInescapableController", "PreternaturalPrecisionController",
}
c.eq("main.py registers exactly these nineteen Aeldari panel buttons",
     sorted(_AELDARI_BUTTONS - _registered), [])

# AND THE REGISTRY REACHES THE PANEL. Registering nineteen controllers on a
# registry the draw call never receives is the "built but never fed" defect
# this repo has met seven times - overflight_controller was passed to the
# panel by a parameter nobody filled for two whole batches. Everything above
# renders with a registry this file hands over itself, so only the source can
# say that main.py hands one over too.
c.eq("...and main.py hands that registry to the panel exactly once",
     _main.count("proactive_stratagems=proactive_stratagems"), 1)
c.eq("...and this file renders one spec per registered button",
     len(SPECS), len(_AELDARI_BUTTONS))

# The reactive twenty-three are NOT buttons - each answers a moment instead.
_REACTIVE = ("ForewarnedController", "PsychicShieldController",
             "IshasFuryController", "LayeredWardsController",
             "VectoredEnginesController", "EldritchSuppressionController",
             "CastingBackTheVeilController", "NomadsOfTheHiddenWayController",
             "ShieldNodesController", "VaulsVengeanceController",
             "CostOfVictoryController", "SpirallingEvasionController",
             "OverflightController", "LightningFastReactionsController",
             "FeignedRetreatController", "WarhostFireAndFadeController",
             "WebwayTunnelController", "SkyborneSanctuaryController",
             "CrushingStridesController", "WraithboneArmourController",
             "ToTheirFinalBreathController", "KhainesVengeanceController")
c.eq("...and not one reactive Aeldari controller is on the registry",
     sorted(n for n in _REACTIVE if n in _registered), [])

# THE ROSTER FACT. Three of the eight detachments cannot be fielded by any
# shipped list, so a good part of the forty-two controllers is unreachable in a
# real game. Named as a measured number rather than left to be rediscovered - and it
# is why every section above sets its own flag.
#
# Swept over EVERY shipped Aeldari list, not just the first one. Scoped to a
# single key, this stayed green when a second list arrived declaring Warhost:
# the assertion held while its own explanation went stale, which is the Mont'ka
# failure shape. The flag names are derived from the declared detachments here,
# so a third list moves this line instead of silently widening the reach.
from game import army_lists                                          # noqa: E402
from game.factions import aeldari as _ae                             # noqa: E402

_aeldari_lists = [e for e in army_lists.ARMY_LISTS
                  if e.faction_keyword == "AELDARI"]
c.eq("three shipped lists field the Aeldari",
     [e.key for e in _aeldari_lists], ["aeldari", "aeldari_warhost", "aeldari_guardian_battlehost"])
_declared = {d for e in _aeldari_lists for d in e.detachments}
_all_dets = set(_ae.AELDARI.detachments)
c.eq("between them they declare five of the eight detachments",
     (len(_declared), len(_all_dets)), (5, 8))
c.eq("...namely these", sorted(_declared),
     ["Armoured Warhost", "Guardian Battlehost", "Path of the Outcast",
      "Seer Council", "Warhost"])
_declared_flags = {_ae.AELDARI.detachments[d].setting for d in _declared}
_reachable = {s["name"] for s in SPECS if set(s["flags"]) & _declared_flags}
# Eight of the nineteen. The reach has moved twice and by very different
# amounts, which is why it is derived from the declared detachments rather than
# written down: Warhost added exactly ONE button (most of what it prints is
# reactive, and a reactive stratagem never reaches this registry at all - the
# claim the _REACTIVE sweep above makes), while Armoured Warhost plus Guardian
# Battlehost doubled it.
c.eq("...so only eight of the nineteen panel buttons can appear in a shipped "
     "game, and the suite switches the rest on itself", len(_reachable), 8)


ActionPanel._draw_button = _real_button
c.finish()
