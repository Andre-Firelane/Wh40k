"""Are the fourteen T'au panel Stratagems really OFFERED, and at the right
moment? - measured by drawing the real ActionPanel.

WHY THIS FILE EXISTS
--------------------
The T'au detachments are where the "the rule is right, the controller is right,
and the button is never on the screen" class was first reported - "wird nie
angeboten", "funktioniert auch nicht", "in der falschen Phase". CLAUDE.md's
chapter on those eleven reports is the taxonomy, and the Aeldari audit that
followed found five more of the same shape.

Nothing here could have caught it for the T'au either, because
test_tau_detachment_stratagems.py - the rules suite, 384 checks - proves the
panel mechanism with a FAKE registry (`ProactiveStratagems([yes, no])`) and
proves the wiring with `"proactive_stratagems.add(X(" in main_src`. Both hold
perfectly while the panel draws nothing at all.

So this file renders. Real registry, real controllers, real ActionPanel, once
per phase, then asks which Stratagem names came out of the button funnel.

THE PHASE MATRIX IS THE POINT (section 2). Every Stratagem is rendered in all
FIVE phases and has to appear in exactly the ones its printed WHEN names -
four negatives per Stratagem. A test that renders only the right phase cannot
tell "offered correctly" from "offered always", and "in der falschen Phase"
was one of the reported failures.

TWO THINGS MAKE THE NEGATIVES MEAN SOMETHING, each with its own section:
section 0 proves the render produced a panel at all (a draw that fell into
another _draw_dispatch branch draws ZERO buttons and satisfies every absence
check by inspecting nothing), and section 3 proves the buttons appear because
the detachment gate opened rather than because the panel draws them regardless.

THREE THINGS DIFFER FROM THE AELDARI MIRROR, all of them measured rather than
assumed, and each is a place a copied suite would quietly measure nothing:

  * TWO SCREENS. Fourteen of the fifteen button draws happen in
    _draw_movement_ui() - the registry, plus arrokon_controller and
    torchstar_controller as their own keyword arguments, since those two
    predate the registry. THE SHORTENED BLADE IS DRAWN IN _draw_setup_ui()
    instead (action_panel.py:1365), during a Deep Strike arrival, and the
    movement rig never reaches it. Rendered through the movement form it would
    be absent in all five phases, which reads as a bug where in fact only the
    wrong screen was measured.

  * ONE NAME, TWO BUTTONS. Experimental Ammunition is two controller instances
    - one per printed mode - sharing a single Stratagem object so rule 15.01
    binds them together. Both panel_label()s open with the same printed name,
    so the matrix compares NAMES while section 6 presses full LABELS.

  * ALL ELEVEN registry Stratagems read turn_tracker.active_player, not
    turn_owner. Section 4 therefore asks the owner clause at can_use(), not at
    the panel - rendered with the turn flipped, the panel draws nothing at all
    in most phases because MovementController.select() refuses a unit outside
    its own turn, and an absence measured there is about the selection.

WHY A SEPARATE FILE from test_tau_detachment_stratagems.py: that one is cut by
detachment and owns the RULES, with no pygame anywhere in its 1702 lines. This
is one matrix across all fourteen and needs a display mode from its first line.
Same split as test_aeldari_stratagem_ui.py, for the same reason.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import ast                                                           # noqa: E402
import io                                                            # noqa: E402

import pygame                                                        # noqa: E402

import testkit as tk                                                 # noqa: E402
from testkit import Checks, settings_as                              # noqa: E402
from game import config, setup                                       # noqa: E402
from game import rules_text                                          # noqa: E402
from game.command_points import CommandPointManager                  # noqa: E402
from game.decision import DecisionManager                            # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.movement import MovementController                         # noqa: E402
from game.proactive_stratagems import ProactiveStratagems            # noqa: E402
from game.shooting import ShootingController                         # noqa: E402
from game.stratagems import StratagemController                      # noqa: E402
from game.turn import (PHASES, PHASE_CHARGE, PHASE_COMMAND,          # noqa: E402
                       PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING,
                       TurnTracker)
from game.ui import action_panel                                     # noqa: E402
from game.ui.action_panel import ActionPanel                         # noqa: E402

from game import aac_microdrone_support as ams                       # noqa: E402
from game import arrokon_protocol as arro                            # noqa: E402
from game import aux_alien_expertise as alien                        # noqa: E402
from game import aux_experimental_modifications as mods              # noqa: E402
from game import aux_guided_fire as guided                           # noqa: E402
from game import epc_experimental_ammunition as ammo                 # noqa: E402
from game import kauyon_coordinate_to_engage as cte                  # noqa: E402
from game import kauyon_point_blank_ambush as pba                    # noqa: E402
from game import kauyon_tempting_trap as trap                        # noqa: E402
from game import montka_aggressive_mobility as aggro                 # noqa: E402
from game import montka_combat_debarkation as debark                 # noqa: E402
from game import montka_focused_fire as focus                        # noqa: E402
from game import shortened_blade as blade                            # noqa: E402
from game import torchstar_gambit as torch                           # noqa: E402

from game.factions.tau_empire import (COMMANDER_IN_COLDSTAR_BATTLESUIT,  # noqa: E402
                                      KROOT_CARNIVORES, STEALTH_BATTLESUITS,
                                      STRIKE_TEAM)
from game.factions.orks import BOYZ                                  # noqa: E402

c = Checks("T'au Stratagem buttons")

pygame.init()
pygame.display.set_mode((1200, 900))

HUMAN = "Player 1"
FOE = "Player 2"

# Battle round 3 satisfies every printed round clause at once: Point-Blank
# Ambush and A Tempting Trap are "third battle round onwards", Focused Fire is
# "up to and including the third". Chosen rather than defaulted, because a
# tracker built at round 0 makes three of the fourteen absent in every phase
# for a reason that has nothing to do with the panel.
ROUND = 3


def turn_at(phase, owner=HUMAN, battle_round=ROUND):
    tracker = TurnTracker(first_player=owner)
    tracker.phase_index = PHASES.index(phase)
    tracker.turn_owner = owner
    tracker.active_player = owner
    tracker.battle_round = battle_round
    return tracker


def strat(cp=10):
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=tk.Log())


# ------------------------------------------------------------------- the board
# REBUILT PER SECTION, and that is not tidiness: buying a Stratagem APPLIES it,
# and most of the fourteen leave a mark on the squad they were bought for (a
# grant, a target restriction, a spent activation). A section that clicks
# therefore poisons every later section that renders the same squad - which
# surfaces as "the button is gone" somewhere with nothing to do with the click.

BEARERS = (("strike", STRIKE_TEAM, HUMAN, 10.0),
           ("kroot", KROOT_CARNIVORES, HUMAN, 16.0),
           ("stealth", STEALTH_BATTLESUITS, HUMAN, 22.0),
           ("commander", COMMANDER_IN_COLDSTAR_BATTLESUIT, HUMAN, 28.0))

B = {}
ALL_TOKENS = []


def build_bearers():
    """A fresh board. ALL_TOKENS is mutated IN PLACE, because controllers and
    stubs are handed the list itself and have to keep seeing the live one.

    The foe sits 8" away: inside the 12" Arro'kon Protocol measures its tier
    over, and outside Engagement Range, so nothing here is accidentally locked
    out of shooting."""
    B.clear()
    for key, sheet, owner, x in BEARERS:
        B[key] = tk.line_up(tk.build(sheet, owner, name="1 %s 1" % key.title()),
                            x, 20.0, spacing=1.2)
    B["foe"] = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 1"), 16.0, 28.0,
                          spacing=1.2)
    ALL_TOKENS[:] = [m for s in B.values() for m in s.models]
    return B


build_bearers()


class _ShootStub:
    """ShootingController as these controllers ask it: three questions.

    A real ShootingController would answer them too, but it also refuses on a
    dozen grounds that have nothing to do with a Stratagem's WHEN - and an
    absence caused by one of those is exactly the "measured nothing" failure
    this file exists to avoid. The panel is still handed a REAL one.
    """

    def __init__(self, can=True, active=None, shot=()):
        self.can = can
        self.active_squad = active
        self.shot_squad_ids = set(shot)

    def can_shoot(self, squad):
        return self.can

    def has_valid_target(self, *a, **kw):
        # Arro'kon's tier is measured over the enemy units this unit could
        # actually shoot. True here, so the tier comes from the board geometry
        # the bearers were laid out for rather than from a target filter that
        # has nothing to do with any Stratagem's WHEN.
        return True


class _FightStub:
    def __init__(self, eligible=True):
        self.eligible = eligible
        self.fought_squad_ids = set()

    def is_eligible_to_fight(self, squad):
        return self.eligible


class _ActionStub:
    """Microdrone Support lifts rule 16.01's shooting ban, so it is only on
    offer while an action is imposing one - "without this the Stratagem would
    be on offer to buy nothing", as its own comment puts it."""

    def __init__(self, blocked=True):
        self.blocked = blocked

    def blocks_shooting(self, squad):
        return self.blocked


class _Observer:
    """Coordinate to Engage names an Observer unit AND its Spotted unit - the
    T'au army rule's own two terms, so both questions go to the controller
    that owns them. `spotted_by` is {target -> observer}, which is the shape
    the real GreaterGoodController keeps and the one spotted_unit_of() reads
    by value.

    An observer that marked nothing is refused by the rule, so a stub that
    answers only is_observer() leaves the Stratagem absent for a reason that
    has nothing to do with the panel."""

    def __init__(self, observing=True, spotted=None, observer=None):
        self.observing = observing
        self.spotted_by = {spotted: observer} if spotted is not None else {}

    def is_observer(self, squad):
        return self.observing


class _IngressStub:
    """The Shortened Blade is bought DURING a Deep Strike arrival, so its three
    questions are about an arrival that is open right now."""

    def __init__(self, arriving=None):
        self.arriving = arriving
        self.relaxed_arrival_squad = None

    def is_ingressing(self, squad):
        return squad is self.arriving

    def deep_striking(self, squad):
        return squad is self.arriving

    # _draw_setup_ui() routes Confirm/Cancel through whichever controller owns
    # the arrival, so an ingressing squad needs these two to be drawable at all.
    def confirm_ingress(self):
        pass

    def cancel_ingress(self):
        pass


class _SetupStub:
    """_draw_dispatch() routes to _draw_setup_ui() on exactly these two
    attributes - the second screen the fifteenth button lives on."""

    def __init__(self, squad=None):
        self.state = setup.PLACING
        self.setting_up_squad = squad
        self.errors = []
        self.block_placement_enabled = False

    def confirm_setup(self):
        pass

    def cancel_setup(self):
        pass


class _Objective:
    """A Tempting Trap picks "one objective marker that is not in your
    opponent's deployment zone". With no deployment zones on the table every
    objective qualifies, which is the condition the printed TARGET describes
    and not a shortcut around it."""

    def __init__(self, name="Central Objective"):
        self.name = name
        self.terrain_area = _Area()
        self.controlled_by = None


class _Area:
    def __init__(self, x=16.0, y=24.0):
        self.center_x_in, self.center_y_in = x, y
        self.x, self.y = x, y

    def distance_to_model(self, m):
        return ((m.x_in - self.x) ** 2 + (m.y_in - self.y) ** 2) ** 0.5


def _move_stub():
    """A real MovementController over the live board. Torchstar refuses
    outright without one, and its own move opens through it."""
    return MovementController([], tk.Log(), HUMAN, DiceManager(),
                              turn_at(PHASE_SHOOTING), ALL_TOKENS)


# ---------------------------------------------------------------- the settings
KA = dict(KAUYON_PLAYERS=(HUMAN,))
MO = dict(MONTKA_PLAYERS=(HUMAN,))
AA = dict(ADVANCED_ACQUISITION_CADRE_PLAYERS=(HUMAN,))
AU = dict(AUXILIARY_CADRE_PLAYERS=(HUMAN,))
EP = dict(EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS=(HUMAN,))
RE = dict(RETALIATION_CADRE_PLAYERS=(HUMAN,))

ALL_FLAGS = ("KAUYON_PLAYERS", "MONTKA_PLAYERS",
             "ADVANCED_ACQUISITION_CADRE_PLAYERS", "AUXILIARY_CADRE_PLAYERS",
             "EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS", "RETALIATION_CADRE_PLAYERS")

MOVEMENT_SCREEN = "movement"
SETUP_SCREEN = "setup"


def _spec(name, make, bearer, phases, owner_phases, flags,
          screen=MOVEMENT_SCREEN, stage=None, buttons=1):
    """`owner_phases` is a SUBSET of `phases`, not a flag on the Stratagem.

    The printed WHEN says "your <phase>" or "the <phase>", and the one
    Stratagem here that names two phases says ONE OF EACH: Experimental
    Modifications is "your Shooting phase or THE Fight phase". A single owner
    boolean per Stratagem gets that one wrong in whichever half it does not
    describe.

    `stage` prepares whatever the printed TARGET line needs beyond a legal
    bearer (a unit that disembarked, a unit that has already shot). It runs
    against the freshly built board, so it cannot leak between specs.
    """
    assert set(owner_phases) <= set(phases), name
    return dict(name=name, make=make, bearer=bearer, phases=frozenset(phases),
                owner_phases=frozenset(owner_phases), flags=flags,
                screen=screen, stage=stage or (lambda ctrl, squad: None),
                buttons=buttons)


def _mark_disembarked(ctrl, squad):
    # disembarked_this_turn() reads Squad.disembarked_from_this_turn, which
    # holds the TRANSPORT it left - not a bool. A flag named after the
    # predicate would leave the Stratagem absent for a staging reason.
    squad.disembarked_from_this_turn = B["foe"]


def _mark_shot(ctrl, squad):
    ctrl.shooting_controller.shot_squad_ids.add(squad)


# The three that predate the registry carry their printed name as a literal
# here, because their modules define no NAME constant the way the other eleven
# do - they build the Stratagem with the string inline. Section 7 pins all
# fourteen against the printed corpus, so a literal that drifts is caught
# there rather than being trusted here.
# MEASURED, not transcribed: the panel's label for this one drops the leading
# "The" that its own Stratagem object and the printed corpus heading both
# carry ("Arro'kon Protocol (1 CP) - ..."), while its two neighbours keep
# theirs. So the DRAWN name is what the matrix can look for, and section 7
# checks that the tooltip lookup still finds the printed rule from it - which
# it does, through rules_text.stratagem_named()'s unique-suffix match.
ARROKON_NAME = "Arro'kon Protocol"
ARROKON_STRATAGEM_NAME = "The Arro'kon Protocol"
TORCHSTAR_NAME = "The Torchstar Gambit"
SHORTENED_BLADE_NAME = "The Shortened Blade"

SPECS = [
    # --- Experimental Prototype Cadre (1) --------------------------------
    # TWO buttons, ONE printed name: the two printed modes are two controller
    # instances sharing one Stratagem object, so 15.01 binds them.
    _spec(ammo.EXPERIMENTAL_AMMUNITION_NAME,
          lambda s: [ammo.ExperimentalAmmunitionController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              game_log=tk.Log(), mode=m)
              for m in (ammo.MODE_STRENGTH, ammo.MODE_STRENGTH_AP_HAZARDOUS)],
          "commander", {PHASE_SHOOTING}, {PHASE_SHOOTING}, EP, buttons=2),

    # --- Auxiliary Cadre (3) ----------------------------------------------
    _spec(alien.ALIEN_EXPERTISE_NAME,
          lambda s: alien.AlienExpertiseController(
              s, movement_controller=None, turn_tracker=None, game_log=tk.Log()),
          "kroot", {PHASE_MOVEMENT}, {PHASE_MOVEMENT}, AU),
    _spec(mods.EXPERIMENTAL_MODIFICATIONS_NAME,
          lambda s: mods.ExperimentalModificationsController(
              s, shooting_controller=_ShootStub(), fight_controller=_FightStub(),
              turn_tracker=None, game_log=tk.Log()),
          "kroot", {PHASE_SHOOTING, PHASE_FIGHT}, {PHASE_SHOOTING}, AU),
    _spec(guided.GUIDED_FIRE_NAME,
          lambda s: guided.GuidedFireController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              game_log=tk.Log()),
          "strike", {PHASE_SHOOTING}, {PHASE_SHOOTING}, AU),

    # --- Kauyon (3 of its six; the other three are reactive) --------------
    _spec(pba.POINT_BLANK_AMBUSH_NAME,
          lambda s: pba.PointBlankAmbushController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              game_log=tk.Log()),
          "strike", {PHASE_SHOOTING}, {PHASE_SHOOTING}, KA),
    _spec(cte.COORDINATE_TO_ENGAGE_NAME,
          lambda s: cte.CoordinateToEngageController(
              s, shooting_controller=_ShootStub(),
              greater_good=_Observer(spotted=B["foe"], observer=B["strike"]),
              turn_tracker=None, game_log=tk.Log()),
          "strike", {PHASE_SHOOTING}, {PHASE_SHOOTING}, KA),
    _spec(trap.TEMPTING_TRAP_NAME,
          lambda s: trap.TemptingTrapController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              objectives=(_Objective(),), deployment_zones={},
              decision_manager=DecisionManager(), game_log=tk.Log()),
          "strike", {PHASE_SHOOTING}, {PHASE_SHOOTING}, KA),

    # --- Mont'ka (3 of its six) -------------------------------------------
    _spec(aggro.AGGRESSIVE_MOBILITY_NAME,
          lambda s: aggro.AggressiveMobilityController(
              s, movement_controller=None, turn_tracker=None, game_log=tk.Log()),
          "strike", {PHASE_MOVEMENT}, {PHASE_MOVEMENT}, MO),
    _spec(debark.COMBAT_DEBARKATION_NAME,
          lambda s: debark.CombatDebarkationController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              game_log=tk.Log()),
          "strike", {PHASE_SHOOTING}, {PHASE_SHOOTING}, MO,
          stage=_mark_disembarked),
    _spec(focus.FOCUSED_FIRE_NAME,
          lambda s: focus.FocusedFireController(
              s, shooting_controller=_ShootStub(), turn_tracker=None,
              all_tokens=ALL_TOKENS, decision_manager=DecisionManager(),
              game_log=tk.Log()),
          "strike", {PHASE_SHOOTING}, {PHASE_SHOOTING}, MO),

    # --- Advanced Acquisition Cadre (1 of its three) ----------------------
    _spec(ams.MICRODRONE_SUPPORT_NAME,
          lambda s: ams.MicrodroneSupportController(
              s, action_controller=_ActionStub(), turn_tracker=None,
              game_log=tk.Log()),
          "stealth", {PHASE_SHOOTING}, {PHASE_SHOOTING}, AA),

    # --- Retaliation Cadre: the two that predate the registry --------------
    # Threaded through ActionPanel.draw() as their own keyword arguments, so
    # they exercise a DIFFERENT panel path from the eleven above - one the
    # registry's single parameter was introduced to stop growing.
    _spec(ARROKON_NAME,
          lambda s: arro.ArrokonProtocolController(
              s, shooting_controller=_ShootStub(), movement_controller=None,
              all_tokens=ALL_TOKENS, turn_tracker=None, game_log=tk.Log()),
          "commander", {PHASE_SHOOTING}, {PHASE_SHOOTING}, RE),
    _spec(TORCHSTAR_NAME,
          lambda s: torch.TorchstarGambitController(
              s, movement_controller=_move_stub(),
              shooting_controller=_ShootStub(),
              all_tokens=ALL_TOKENS, turn_tracker=None, game_log=tk.Log()),
          "commander", {PHASE_SHOOTING}, {PHASE_SHOOTING}, RE,
          stage=_mark_shot),

    # --- Retaliation Cadre: the one on the OTHER screen ---------------------
    _spec(SHORTENED_BLADE_NAME,
          lambda s: blade.ShortenedBladeController(
              s, ingress_controller=_IngressStub(B["commander"]),
              setup_controller=None, turn_tracker=None, game_log=tk.Log()),
          "commander", {PHASE_MOVEMENT}, {PHASE_MOVEMENT}, RE,
          screen=SETUP_SCREEN),
]

ALL_PHASES = (PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE,
              PHASE_FIGHT)


def primary(spec):
    """The phase a spec is exercised in outside the matrix - the FIRST one its
    WHEN names in game order, so the two-phase Stratagem is driven in Shooting
    (where its owner clause lives) rather than alphabetically."""
    return next(p for p in ALL_PHASES if p in spec["phases"])


# ------------------------------------------------------------- the render rig

_panel = ActionPanel()
_surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
_rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900)
_labels = []
_drawn = []          # (label, rect) in draw order - the only handle that can
                     # tell two buttons apart when they share a printed name
_real_button = ActionPanel._draw_button


def _spy_button(self, surface, rect, label, *a, **kw):
    out = _real_button(self, surface, rect, label, *a, **kw)
    _labels.append(label)
    _drawn.append((label, out))
    return out


ActionPanel._draw_button = _spy_button


def render(spec, squad, phase, registry, built, owner=HUMAN, tracker=None):
    """Draw the real panel for `squad` in `phase` and report what came out.

    Returns (labels, stratagem_names, buttons).

    TWO FORMS, because the fifteen buttons live on two screens.

    The MOVEMENT form is the ordinary unit screen. mover.select() is not
    optional there: _draw_movement_ui() opens with
    `squad = movement_controller.selected_squad` and asks the registry about
    that squad and no other, so a render without it draws the no-selection
    screen and every absence check would pass by measuring nothing.

    The SETUP form is the arrival screen _draw_dispatch() routes to when
    setup_controller.state is PLACING, which is the only place The Shortened
    Blade is ever drawn. It keys on setting_up_squad rather than on the
    movement selection, so the two forms cannot be merged.

    The two controllers that predate the registry are handed to the panel as
    their own keyword arguments, which is the second panel path this file
    exists to cover - the registry parameter was introduced to stop that list
    growing, and these two are what it grew to first.
    """
    tracker = tracker or turn_at(phase, owner)
    mover = MovementController([], tk.Log(), owner, DiceManager(), tracker,
                               ALL_TOKENS)
    # BY KEYWORD: ShootingController's first positional is `obstacles`, not
    # the token list, so a positional call quietly hands it the models as
    # terrain - harmless until something asks for line of sight.
    shooter = ShootingController(obstacles=[], game_log=tk.Log(),
                                 player_name=owner, dice_manager=DiceManager(),
                                 turn_tracker=tracker, all_tokens=ALL_TOKENS,
                                 decision_manager=DecisionManager())
    _labels.clear()
    _drawn.clear()
    _surface.fill((0, 0, 0))

    if spec["screen"] == SETUP_SCREEN:
        _panel.draw(_surface, _rect, mover, shooter,
                    dice_manager=DiceManager(),
                    setup_controller=_SetupStub(squad),
                    ingress_controller=built.get("_ingress"),
                    shortened_blade_controller=built.get(SHORTENED_BLADE_NAME),
                    proactive_stratagems=registry)
    else:
        mover.select(squad.models[0])
        _panel.draw(_surface, _rect, mover, shooter,
                    dice_manager=DiceManager(),
                    arrokon_controller=built.get(ARROKON_NAME),
                    torchstar_controller=built.get(TORCHSTAR_NAME),
                    proactive_stratagems=registry)
    return (list(_labels), [n for _, n in _panel._stratagem_buttons],
            list(_panel._buttons))


def build_for(spec, sc):
    """The controller(s) one spec needs, plus the registry that carries them.

    A spec's `make` may return a LIST - Experimental Ammunition is two
    instances of one Stratagem - so both go on the registry while `built` keys
    them under the single printed name they share.

    The two pre-registry controllers are built but NOT registered: the panel
    takes them by keyword. Putting them on the registry as well would draw them
    twice and quietly prove the wrong path.
    """
    made = spec["make"](sc)
    controllers = made if isinstance(made, list) else [made]
    reg = ProactiveStratagems()
    if spec["name"] not in (ARROKON_NAME, TORCHSTAR_NAME, SHORTENED_BLADE_NAME):
        for ctrl in controllers:
            reg.add(ctrl)
    built = {spec["name"]: controllers[0], "_all": controllers}
    if spec["name"] == SHORTENED_BLADE_NAME:
        built["_ingress"] = controllers[0].ingress_controller
    return reg, built


def at_phase(spec, built, phase, owner=HUMAN):
    """Point every controller of a spec at `phase`. The table builds them with
    turn_tracker=None so one tracker can be shared by a whole render."""
    tracker = turn_at(phase, owner)
    for ctrl in built["_all"]:
        ctrl.turn_tracker = tracker
    return tracker


def stage(spec, built, squad):
    for ctrl in built["_all"]:
        spec["stage"](ctrl, squad)


def press(label_or_name, buttons, exact_label=False):
    """Click the drawn button; True if there was one.

    RETURNS rather than raises when there is none. A probe that removes the
    buttons has to turn this file RED, not crash it - a crash hides which check
    broke, and this repo has been caught by that trap more than a dozen times.

    `exact_label` matches the full button text rather than the printed name,
    which is the only thing that tells Experimental Ammunition's two modes
    apart: they share one printed name and differ only in the summary after the
    cost. Matching on the name there would press the same mode twice and report
    both as bought.
    """
    if exact_label:
        rect = next((r for lab, r in _drawn if lab == label_or_name), None)
    else:
        rect = next((r for r, n in _panel._stratagem_buttons
                     if n == label_or_name), None)
    if rect is None:
        return False
    callback = next((cb for r, cb in buttons if r == rect), None)
    if callback is None:
        return False
    callback()
    return True


def drain(built, limit=6):
    """Answer the follow-up questions a Stratagem asks AFTER its button.

    Three of the fourteen open a DecisionManager prompt of their own before
    they charge - Focused Fire asks twice (a partner, then an enemy), A
    Tempting Trap and Marker Beacon once each. A test that stops at the click
    therefore sees "bought and did nothing", which is indistinguishable from
    one of the reported failures. Always the FIRST option, which is the acting
    one; declining is a different question and belongs to the rules suite.
    """
    steps = 0
    for ctrl in built["_all"]:
        dm = getattr(ctrl, "decision_manager", None)
        while dm is not None and dm.is_pending and steps < limit:
            dm.choose(0)
            steps += 1
    return steps


# ---------------------------------------------------------------------------
print("--- 0. the rig ---")

# THE MOST IMPORTANT LINES IN THIS FILE. Every negative below is "this name is
# not among the drawn buttons", and a render that fell into some other branch
# of _draw_dispatch() - or into _draw_movement_ui()'s no-selection screen -
# draws no buttons at all and satisfies all of them by inspecting nothing.
_movement_spec = next(s for s in SPECS if s["screen"] == MOVEMENT_SCREEN)
_setup_spec = next(s for s in SPECS if s["screen"] == SETUP_SCREEN)

_sc0 = strat()
_reg0, _built0 = build_for(_movement_spec, _sc0)
_reg0 = ProactiveStratagems()          # empty: nothing of ours may be drawn
_l0, _s0, _b0 = render(_movement_spec, B["strike"], PHASE_MOVEMENT, _reg0, {})
c.true("the movement screen really draws its ordinary buttons", len(_l0) >= 2)
c.true("...including one this file does not own", any("Move" in l for l in _l0))
c.eq("...and with an empty registry, no Stratagem button at all", _s0, [])
c.true("...while the ordinary buttons are still clickable", len(_b0) >= 2)

# The SETUP screen is a different branch of _draw_dispatch() and needs its own
# liveness proof: it has its own Confirm/Cancel and none of Movement's.
_l0s, _s0s, _b0s = render(_setup_spec, B["commander"], PHASE_MOVEMENT,
                          ProactiveStratagems(), {})
c.true("the setup screen really draws its own buttons", len(_l0s) >= 1)
c.true("...and it is a DIFFERENT screen from the movement one",
       set(_l0s) != set(_l0))
c.eq("...with no Stratagem button of ours on it either", _s0s, [])

# _stratagem_buttons is filled ONLY for accent="stratagem" (action_panel.py's
# _draw_button), so membership IS the violet-accent assertion - no pixel scan
# needed, and the two handles are independent.
_panel_src = io.open(os.path.join("game", "ui", "action_panel.py"),
                     encoding="utf-8").read()
c.true("_stratagem_buttons records exactly the accent='stratagem' draws",
       'if accent == "stratagem":' in _panel_src
       and "self._stratagem_buttons.append(" in _panel_src)


# ---------------------------------------------------------------------------
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


_yes, _no = _Fake("Yes"), _Fake("No", usable=False)
_l1, _s1, _b1 = render(_movement_spec, B["strike"], PHASE_MOVEMENT,
                       ProactiveStratagems([_yes, _no]), {})
c.true("a usable registry entry is drawn", "Yes" in _s1)
c.true("...with its cost on the label", any(l.startswith("Yes (1 CP)") for l in _l1))
c.true("an unusable one is drawn nowhere", "No" not in _s1)
c.true("pressing it calls THAT controller", press("Yes", _b1))
c.eq("...for the squad the panel was drawn for", [s.name for s in _yes.used],
     [B["strike"].name])
c.eq("...and the unusable one was never called", _no.used, [])


# ---------------------------------------------------------------------------
print("--- 2. the phase matrix ---")

_matrix_rows = 0
for _spec in SPECS:
    with settings_as(**_spec["flags"]):
        build_bearers()
        _sc = strat()
        _reg, _built = build_for(_spec, _sc)
        _bearer = B[_spec["bearer"]]
        _seen = set()
        for _phase in ALL_PHASES:
            at_phase(_spec, _built, _phase)
            stage(_spec, _built, _bearer)
            _, _names, _ = render(_spec, _bearer, _phase, _reg, _built)
            if _spec["name"] in _names:
                _seen.add(_phase)
            _matrix_rows += 1
        c.eq("%s is offered in exactly the phases its WHEN names" % _spec["name"],
             sorted(_seen), sorted(_spec["phases"]))

c.eq("...and the matrix really rendered 14 x 5 panels", _matrix_rows,
     len(SPECS) * len(ALL_PHASES))
c.eq("...for all fourteen T'au panel Stratagems", len(SPECS), 14)
c.eq("...covering both screens", len({s["screen"] for s in SPECS}), 2)


# ---------------------------------------------------------------------------
print("--- 3. the gate ---")

# Without this, section 2 proves only that the buttons appear - not that they
# appear BECAUSE the detachment is fielded. Every flag off, every spec, every
# phase: nothing of ours may be drawn anywhere.
_off_sightings = []
for _spec in SPECS:
    with settings_as(**{k: () for k in ALL_FLAGS}):
        build_bearers()
        _sc = strat()
        _reg, _built = build_for(_spec, _sc)
        _bearer = B[_spec["bearer"]]
        for _phase in ALL_PHASES:
            at_phase(_spec, _built, _phase)
            stage(_spec, _built, _bearer)
            _, _names, _ = render(_spec, _bearer, _phase, _reg, _built)
            if _spec["name"] in _names:
                _off_sightings.append((_spec["name"], _phase))
c.eq("with no T'au detachment fielded, none of the fourteen is ever drawn",
     _off_sightings, [])


# ---------------------------------------------------------------------------
print("--- 4. whose phase ---")

# MEASURED AT can_use(), NOT AT THE PANEL, and that is a finding rather than a
# convenience. Rendered with the turn flipped, the panel draws NOTHING AT ALL
# for most phases, because MovementController.select() refuses a unit outside
# its own turn and _draw_movement_ui() then shows the no-selection screen. An
# absence measured there is a fact about the selection, not about the WHEN.
_selectable = []
for _phase in ALL_PHASES:
    _tracker = turn_at(_phase, FOE)
    _mv = MovementController([], tk.Log(), HUMAN, DiceManager(), _tracker,
                             ALL_TOKENS)
    _mv.select(B["strike"].models[0])
    if _mv.selected_squad is not None:
        _selectable.append(_phase)
c.true("a unit cannot even be picked in most of the opponent's phases",
       len(_selectable) < len(ALL_PHASES))

# THE OWNER CLAUSE IS PER PHASE, not per Stratagem. Experimental Modifications
# prints "your Shooting phase or THE Fight phase" - one of each - so a single
# owner boolean would describe whichever half it was written for and get the
# other backwards. owner_phases is therefore a SUBSET of phases.
_owner_rows = 0
for _spec in SPECS:
    with settings_as(**_spec["flags"]):
        build_bearers()
        _sc = strat()
        _reg, _built = build_for(_spec, _sc)
        _bearer = B[_spec["bearer"]]
        for _phase in sorted(_spec["phases"]):
            # Same board, same staging, ONLY the turn owner flipped.
            at_phase(_spec, _built, _phase, owner=HUMAN)
            stage(_spec, _built, _bearer)
            _mine = _built["_all"][0].can_use(_bearer)
            at_phase(_spec, _built, _phase, owner=FOE)
            _theirs = _built["_all"][0].can_use(_bearer)
            _owner_rows += 1
            if _phase in _spec["owner_phases"]:
                c.true("%s in %s is refused in the opponent's turn"
                       % (_spec["name"], _phase), _mine and not _theirs)
            else:
                c.true("%s in %s is offered in either turn"
                       % (_spec["name"], _phase), _mine and _theirs)
c.eq("...and every printed phase of every spec was asked", _owner_rows,
     sum(len(s["phases"]) for s in SPECS))
c.true("at least one spec really is owner-blind in one of its phases",
       any(s["phases"] - s["owner_phases"] for s in SPECS))


# ---------------------------------------------------------------------------
print("--- 5. once per phase ---")

# Rule 15.01: one use per phase. The button has to VANISH after the purchase,
# because a Stratagem still on the panel that can no longer be bought is the
# same lie as one that never appears.
for _spec in SPECS[:4]:
    with settings_as(**_spec["flags"]):
        build_bearers()
        _sc = strat()
        _reg, _built = build_for(_spec, _sc)
        _bearer = B[_spec["bearer"]]
        _phase = primary(_spec)
        at_phase(_spec, _built, _phase)
        stage(_spec, _built, _bearer)

        # BEFORE the purchase: the ledger frees it again next phase. Asked
        # here rather than after, because after a purchase rule 15.01 refuses
        # for its own reason and would mask a reset that never happened.
        _sc.reset_phase()
        _, _names, _ = render(_spec, _bearer, _phase, _reg, _built)
        c.true("%s is on the panel to begin with" % _spec["name"],
               _spec["name"] in _names)

        _, _names, _buttons = render(_spec, _bearer, _phase, _reg, _built)
        c.true("...and pressing it works", press(_spec["name"], _buttons))
        drain(_built)
        _, _after, _ = render(_spec, _bearer, _phase, _reg, _built)
        c.true("...after which it is gone from the panel" % (),
               _spec["name"] not in _after)


# ---------------------------------------------------------------------------
print("--- 6. the click ---")

# The whole point: a button that is drawn, pressed, and REALLY SPENDS THE CP.
# drain() answers the follow-up prompts three of the fourteen open before they
# charge - without it those three report "bought and did nothing", which is
# indistinguishable from one of the reported failures.
_undrawn, _unbought, _bought = [], [], 0
for _spec in SPECS:
    with settings_as(**_spec["flags"]):
        build_bearers()
        _sc = strat()
        _reg, _built = build_for(_spec, _sc)
        _bearer = B[_spec["bearer"]]
        _phase = primary(_spec)
        at_phase(_spec, _built, _phase)
        stage(_spec, _built, _bearer)
        _, _names, _buttons = render(_spec, _bearer, _phase, _reg, _built)
        if _spec["name"] not in _names:
            _undrawn.append(_spec["name"])
            continue
        _before = _sc.command_points.cp[HUMAN]
        press(_spec["name"], _buttons)
        drain(_built)
        if _sc.command_points.cp[HUMAN] < _before:
            _bought += 1
        else:
            _unbought.append(_spec["name"])
c.eq("every one of the fourteen is drawn in a phase its WHEN names", _undrawn, [])
c.eq("...and pressing it really spends CP", _unbought, [])
c.eq("...for all fourteen", _bought, len(SPECS))

# The counter-proof: rendered in a phase it does not name, the same Stratagem
# is neither drawn nor bought. Without this the section above would pass on a
# panel that drew everything always.
_spec = SPECS[0]
with settings_as(**_spec["flags"]):
    build_bearers()
    _sc = strat()
    _reg, _built = build_for(_spec, _sc)
    _bearer = B[_spec["bearer"]]
    _wrong = next(p for p in ALL_PHASES if p not in _spec["phases"])
    at_phase(_spec, _built, _wrong)
    stage(_spec, _built, _bearer)
    _, _names, _buttons = render(_spec, _bearer, _wrong, _reg, _built)
    c.true("in a phase its WHEN does not name it is not drawn",
           _spec["name"] not in _names)
    c.eq("...and no CP was spent", _sc.command_points.cp[HUMAN], 10)

# ONE NAME, TWO BUTTONS. Experimental Ammunition's two printed modes are two
# controllers sharing one Stratagem object, so 15.01 binds them: buying either
# takes BOTH off the panel. Pressed by full LABEL, because matching on the
# printed name would press the same mode twice and report both as bought.
_ammo_spec = next(s for s in SPECS if s["name"] == ammo.EXPERIMENTAL_AMMUNITION_NAME)
with settings_as(**_ammo_spec["flags"]):
    build_bearers()
    _sc = strat()
    _reg, _built = build_for(_ammo_spec, _sc)
    _bearer = B[_ammo_spec["bearer"]]
    at_phase(_ammo_spec, _built, PHASE_SHOOTING)
    _labels_a, _names_a, _btns_a = render(_ammo_spec, _bearer, PHASE_SHOOTING,
                                          _reg, _built)
    _ammo_labels = [l for l in _labels_a
                    if action_panel._stratagem_name_in(l) == _ammo_spec["name"]]
    c.eq("both printed modes are drawn", len(_ammo_labels), 2)
    c.eq("...under one printed name",
         len({action_panel._stratagem_name_in(l) for l in _ammo_labels}), 1)
    c.true("...and the two labels really differ",
           _ammo_labels[0] != _ammo_labels[1])
    c.true("pressing one mode by its full label works",
           press(_ammo_labels[1], _btns_a, exact_label=True))
    drain(_built)
    _, _names_b, _ = render(_ammo_spec, _bearer, PHASE_SHOOTING, _reg, _built)
    c.true("...and rule 15.01 takes BOTH modes off the panel",
           _ammo_spec["name"] not in _names_b)


# ---------------------------------------------------------------------------
print("--- 7. the label ---")

# The label has to round-trip through the panel's own extractor and land on a
# rule that is actually printed. Asked through rules_text.stratagem_named()
# rather than by grepping the .md, because that is the lookup the in-game
# tooltip uses - so this measures what a player would really see.
_DETACHMENT_OF = {"KAUYON_PLAYERS": "Kauyon",
                  "MONTKA_PLAYERS": "Mont'ka",
                  "ADVANCED_ACQUISITION_CADRE_PLAYERS": "Advanced Acquisition Cadre",
                  "AUXILIARY_CADRE_PLAYERS": "Auxiliary Cadre",
                  "EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS": "Experimental Prototype Cadre",
                  "RETALIATION_CADRE_PLAYERS": "Retaliation Cadre"}

for _spec in SPECS:
    with settings_as(**_spec["flags"]):
        build_bearers()
        _sc = strat()
        _reg, _built = build_for(_spec, _sc)
        _bearer = B[_spec["bearer"]]
        _phase = primary(_spec)
        at_phase(_spec, _built, _phase)
        stage(_spec, _built, _bearer)
        _l, _names, _ = render(_spec, _bearer, _phase, _reg, _built)
        _drawn_labels = [l for l in _l
                         if action_panel._stratagem_name_in(l) == _spec["name"]]
        c.true("%s draws a label the panel can name" % _spec["name"],
               bool(_drawn_labels))
        if not _drawn_labels:
            continue
        c.true("...carrying its CP cost", " CP)" in _drawn_labels[0])
        _det = _DETACHMENT_OF[list(_spec["flags"])[0]]
        c.true("...and the tooltip finds its printed rule",
               rules_text.stratagem_named("T'AU EMPIRE", [_det],
                                          _spec["name"]) is not None)

# THE ONE THAT DIFFERS, pinned rather than smoothed over: the Arro'kon
# Protocol's button drops the leading "The" its Stratagem object and the corpus
# heading both carry. Harmless today only because stratagem_named() falls back
# to a unique SUFFIX match - so both halves are pinned, and a rename that broke
# the fallback would show up here rather than as an empty tooltip in a game.
c.true("the Arro'kon button really drops the 'The' its Stratagem carries",
       ARROKON_NAME != ARROKON_STRATAGEM_NAME
       and ARROKON_STRATAGEM_NAME.endswith(ARROKON_NAME))
c.true("...and the printed name it drops is the one the corpus prints",
       rules_text.stratagem_named("T'AU EMPIRE", ["Retaliation Cadre"],
                                  ARROKON_STRATAGEM_NAME) is not None)
c.true("...while its two neighbours keep theirs",
       TORCHSTAR_NAME.startswith("The") and SHORTENED_BLADE_NAME.startswith("The"))


# ---------------------------------------------------------------------------
print("--- 8. absence ---")

# A source sweep, because a behaviour test cannot see a FIFTEENTH button that
# does not exist yet. The registry half is read by AST rather than by counting
# a substring: main.py both registers `add(SomeController(...))` and
# `add(existing_controller)`, and a docstring that mentions either form would
# satisfy a count.
_main = io.open("main.py", encoding="utf-8").read()
_main_tree = ast.parse(_main)
_registered = set()
for _node in ast.walk(_main_tree):
    if not (isinstance(_node, ast.Call) and isinstance(_node.func, ast.Attribute)
            and _node.func.attr == "add"
            and isinstance(_node.func.value, ast.Name)
            and _node.func.value.id == "proactive_stratagems"):
        continue
    if not _node.args:
        continue
    _arg = _node.args[0]
    if isinstance(_arg, ast.Call) and isinstance(_arg.func, ast.Name):
        _registered.add(_arg.func.id)
    elif isinstance(_arg, ast.Name):
        _registered.add(_arg.id)

_TAU_REGISTERED = {
    "ExperimentalAmmunitionController", "ExperimentalModificationsController",
    "AlienExpertiseController", "GuidedFireController",
    "PointBlankAmbushController", "CoordinateToEngageController",
    "TemptingTrapController", "AggressiveMobilityController",
    "CombatDebarkationController", "FocusedFireController",
    "MicrodroneSupportController",
}
c.eq("main.py registers exactly these eleven T'au controllers on the registry",
     sorted(_TAU_REGISTERED - _registered), [])
c.eq("...and hands that registry to the panel exactly once",
     _main.count("proactive_stratagems=proactive_stratagems"), 1)

# The three that predate the registry are the second panel path, and they reach
# it POSITIONALLY - which is the hazard the registry was introduced to stop
# growing, and the one action_panel.py carries a scar comment about (a
# parameter added to two of three signatures crashed every frame). So the pin
# is on the POSITION, by AST: each must be an argument of the panel.draw() call
# at the index the three-stage signature expects, and a new parameter inserted
# before them has to show up here rather than as three silently shifted
# controllers.
_draw_call = None
for _node in ast.walk(_main_tree):
    if (isinstance(_node, ast.Call) and isinstance(_node.func, ast.Attribute)
            and _node.func.attr == "draw"
            and isinstance(_node.func.value, ast.Name)
            and _node.func.value.id == "action_panel"):
        _draw_call = _node
        break
c.true("main.py's action_panel.draw() call was found", _draw_call is not None)
_positional = [a.id for a in (_draw_call.args if _draw_call else [])
               if isinstance(a, ast.Name)]
_by_keyword = {k.arg for k in (_draw_call.keywords if _draw_call else [])}
for _name in ("arrokon_controller", "shortened_blade_controller",
              "torchstar_controller"):
    c.true("main.py hands the panel %s" % _name,
           _name in _positional or _name in _by_keyword)
# The signature's own order, read off the panel rather than restated: the three
# have to sit where draw() expects them, which is the whole risk of a
# positional call.
_panel_sig = ast.parse(_panel_src)
_draw_def = next(n for n in ast.walk(_panel_sig)
                 if isinstance(n, ast.FunctionDef) and n.name == "draw")
_sig_names = [a.arg for a in _draw_def.args.args][1:]   # drop self
for _name in ("arrokon_controller", "shortened_blade_controller",
              "torchstar_controller"):
    if _name in _positional and _name in _sig_names:
        c.eq("...at the position draw() expects for %s" % _name,
             _positional.index(_name), _sig_names.index(_name))

c.eq("...so this file renders one spec per T'au panel button",
     len(SPECS), len(_TAU_REGISTERED) + 3)

# ONE NAME, TWO REGISTRATIONS. Section 6 proves the panel draws both printed
# modes, but it builds its own pair from the spec table - so it would keep
# passing if main.py registered only one of them. The count has to come from
# main.py itself, and it is the COMPREHENSION's iterable rather than a
# substring: the registration appears once in the source and twice at runtime,
# which is exactly the shape a count of names gets wrong.
_ammo_modes = None
for _node in ast.walk(_main_tree):
    if not isinstance(_node, ast.ListComp):
        continue
    _names_in = {n.id for n in ast.walk(_node.elt) if isinstance(n, ast.Name)}
    if "ExperimentalAmmunitionController" in _names_in and _node.generators:
        _iter = _node.generators[0].iter
        if isinstance(_iter, (ast.Tuple, ast.List)):
            _ammo_modes = [e.id for e in _iter.elts if isinstance(e, ast.Name)]
c.true("main.py builds Experimental Ammunition from a list of printed modes",
       _ammo_modes is not None)
c.eq("...and registers one controller per printed mode", len(_ammo_modes or []), 2)
c.eq("...naming both of the module's modes", sorted(_ammo_modes or []),
     ["MODE_STRENGTH", "MODE_STRENGTH_AP_HAZARDOUS"])
c.eq("...which are all the modes the module defines",
     sorted(n for n in dir(ammo) if n.startswith("MODE_")),
     ["MODE_STRENGTH", "MODE_STRENGTH_AP_HAZARDOUS"])

# ...and NOT ONE reactive T'au controller is on the registry. A reactive
# Stratagem on the panel would be offered outside its own printed window, which
# is the mirror image of the bug this file exists for.
_TAU_REACTIVE = (
    "WallOfMirrorsController", "PhotonGrenadesController",
    "CombatEmbarkationController", "CounterfireDefenceController",
    "PinpointCounterOffensiveController", "PulseOnslaughtController",
    "AutoreactiveCamouflageController", "MarkerBeaconController",
    "GravInhibitorFieldController", "FailSafeDetonatorController",
    "StimInjectorsController",
)
c.eq("no reactive T'au Stratagem is on the proactive registry",
     sorted(n for n in _TAU_REACTIVE if n in _registered), [])
c.true("...and the reactive list really names controllers main.py builds",
       sum(1 for n in _TAU_REACTIVE if n in _main) >= 10)

# The roster fact behind every settings_as above: no shipped T'au list fields
# all six detachments, so most of these fourteen are unreachable in a real game
# without switching lists. Measured, not assumed.
from game import army_lists  # noqa: E402

# DERIVED rather than written down. This tuple used to name the four lists, and
# it went stale twice in one day - once when the Recon list arrived and once when
# the Prototypes list was retired. Worse, a stale key here raises SystemExit out
# of army_lists.get(), which is a crash rather than a diagnosable red line.
_tau_keys = tuple(e.key for e in army_lists.lists_for("T'AU EMPIRE"))
_declared = set()
for _key in _tau_keys:
    _declared |= set(army_lists.get(_key).detachments)
c.eq("the shipped T'au lists declare six detachments between them",
     len(_declared), 6)
# The Recon list fields THREE at once - the first anywhere to do so - which is
# why this is not "no more than two" any more.
c.true("...but no single one declares them all",
       max(len(army_lists.get(k).detachments) for k in _tau_keys) < 6)


ActionPanel._draw_button = _real_button
c.finish()
