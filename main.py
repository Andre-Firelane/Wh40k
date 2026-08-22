import argparse
import os
import sys
import time

import pygame

from ai import deployment_ai
from ai.agent_driver import AIMemory, take_one_action
from ai.claude_agent import ClaudeAgent
# from ai.mock_agent import MockAgent  # free/offline alternative - no API key or network needed
from game import attached_units, battle_focus, charge, config, consolidate, crushing_impact, epic_challenge, explosives, fall_back, fight, firing_deck, greater_good, line_of_sight, maps, movement, overwatch, pregame, setup, shooting, starflare_ignition, status_effects, strands_of_fate
from game.arrokon_protocol import ArrokonProtocolController
from game.shortened_blade import ShortenedBladeController
from game.torchstar_gambit import TorchstarGambitController
from game.grav_inhibitor_field import GravInhibitorFieldController
from game.fail_safe_detonator import FailSafeDetonatorController
from game.pregame import PregameController
from game.scouts import ScoutsStep
from game.battle_shock import BattleShockController
from game.board import Board
from game.camera import Camera, WHEEL_ZOOM_STEP
from game.charge import ChargeController
from game.coherency import CoherencyEnforcer
from game.command_points import CommandPointManager
from game.command_reroll import CommandRerollController
from game.env import load_dotenv
from game.explosives import ExplosivesController
from game.fall_back import FallBackController
from game.fieldcraft import apply_fieldcraft
from game.grot_riggers import apply_grot_riggers
from game.thievin_scavengers import ThievinScavengersController
from game.waaagh import WaaaghController
from game.stratagems import StratagemController
from game.consolidate import ConsolidateController
from game.counteroffensive import CounteroffensiveController
from game.deadly_demise import DeadlyDemiseController
from game.decision import DecisionManager
from game.dice import DiceManager
from game.crushing_impact import CrushingImpactController
from game.epic_challenge import EpicChallengeController
from game.fight import FightController
from game.insane_bravery import InsaneBraveryController
from game.game_log import GameLog
from game.missions import MissionController
from game.ingress import IngressController
from game.firing_deck import FiringDeckController
from game.game_state import GameState
from game.greater_good import GreaterGoodController
from game.heroic_intervention import HeroicInterventionController
from game.homing_beacon import HomingBeaconController
from game.movement import MovementController
from game import neocapacitor_shields, scene_io
from game.neocapacitor_shields import NeocapacitorShieldsController
from game.nova_charge import NovaChargeController
from game.overwatch import FireOverwatchController
from game.retro_thrusters import RetroThrustersController
from game.pile_in import PileInController
from game.puretide import PuretideController
from game.rapid_ingress import RapidIngressController
from game.setup import SetupController
from game.suppression import SuppressionController
from game.stealth_drones import StealthDronesController
from game.starflare_ignition import StarflareIgnitionController
from game.ard_as_nails import ArdAsNailsController
from game.ammo_runt import AmmoRuntController
from game.grot_orderly import GrotOrderlyController, unit_has_grot_orderly
from game.spirit_of_gork import SpiritOfGorkController, unit_has_spirit_of_gork
from game.ere_we_go import EreWeGoController
from game import hand_of_asuryan
from game import branching_fates
from game import psychic_communion
from game import whirling_death
from game.hand_of_asuryan import HandOfAsuryanController
from game.fire_support import FireSupportController
from game.guide import GuideController
from game.doom import DoomController
from game.diviner_of_futures import DivinerOfFuturesController
from game.whispering_web import WhisperingWebController
from game import fate_inescapable as fate_inescapable_mod
from game import forewarned as forewarned_mod
from game import psychic_shield as psychic_shield_mod
from game.fate_inescapable import FateInescapableController
from game.forewarned import ForewarnedController
from game.ishas_fury import IshasFuryController
from game.presentiment_of_dread import PresentimentOfDreadController
from game.psychic_shield import PsychicShieldController
from game.tactical_acumen import TacticalAcumenController
from game.flickerjump import FlickerjumpController
from game.stim_injectors import StimInjectorsController
from game.support_turret import SupportTurretController
from game.transport import TransportController
from game.squad import Squad
from game.token import Token
from game.factions import build_squad
from game.factions.orks import (
    BATTLEWAGON, BATTLEWAGON_ADD_BIG_SHOOTAS, BATTLEWAGON_ADD_ZZAP_GUN, BATTLEWAGON_ARD_CASE,
    BEAST_SNAGGA_BOYZ, BEASTBOSS, BOYZ, BOYZ_BIG_CHOPPA_TO_POWER_KLAW, DEFF_DREAD, DEFFKOPTAS,
    FLASH_GITZ, FLASH_GITZ_AMMO_RUNT, GRETCHIN, KILL_RIG, MEGANOBZ, PAINBOY,
    PAINBOY_GROT_ORDERLY, STORMBOYZ,
    STORMBOYZ_CHOPPA_TO_POWER_KLAW, TANKBUSTAS, TANKBUSTAS_ADD_ROKKIT_LAUNCHA, TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER,
    WARBIKERS, WARBIKERS_ADD_POWER_KLAW, WARBOSS, WARBOSS_ADD_ATTACK_SQUIG, WARBOSS_MEGA_ARMOUR,
)
from game.factions.tau_empire import (
    BREACHER_TEAM, CADRE_FIREBLADE, COLDSTAR_ADD_2X_BURST_CANNON, COLDSTAR_ADD_CYCLIC_ION_BLASTER,
    COMMANDER_FARSIGHT, COMMANDER_IN_COLDSTAR_BATTLESUIT, CRISIS_STARSCYTHE, CRISIS_SUNFORGE,
    DEVILFISH, DEVILFISH_SEEKER_MISSILE_OPTION,
    GHOSTKEEL_BATTLESUIT, GHOSTKEEL_FLAMER_TO_FUSION_BLASTER, GHOSTKEEL_FUSION_TO_ION_RAKER,
    KROOT_CARNIVORES, PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER,
    PATHFINDER_CARBINE_TO_RAIL_RIFLE, PATHFINDER_TEAM,
    RIPTIDE_BATTLESUIT, RIPTIDE_BURST_TO_ION_ACCELERATOR, RIPTIDE_PLASMA_TO_TWIN_FUSION,
    STARSCYTHE_FLAMER_TO_BURST, STEALTH_BATTLESUITS, STRIKE_TEAM, THE_TWIN_LANCE,
)
from game.input_handler import InputManager
from game.renderer import Renderer
from game.shooting import ShootingController
from game.turn import TurnTracker, PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE, PHASE_FIGHT
from game.unbridled_carnage import UnbridledCarnageController
from game.ui.action_panel import ActionPanel
from game.ui.decision_overlay import DecisionOverlay
from game.ui.stratagem_notice_overlay import StratagemNoticeOverlay
from game.ui.waaagh_notice_overlay import WaaaghNoticeOverlay
from game.ui.turn_start_overlay import TurnStartOverlay
from game.ui.turn_plan_overlay import TurnPlanOverlay
from game.ui.dice_panel import DicePanel
from game.ui.game_status_panel import GameStatusPanel
from game.ui.log_panel import LogPanel
from game.ui.mission_cards import MissionCardsOverlay
from game.ui.player_banner import PlayerBanner
from game.ui.reserves_panel import ReservesPanel
from game.ui.unit_datacard import UnitDatacardOverlay

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


def _new_game_log_file_path():
    """One timestamped, append-only text file per run, under logs/ next to
    main.py - see GameLog's own docstring for why this exists. Never
    cleaned up automatically (that's a manual/user decision - these are
    diagnostic artifacts, not game data)."""
    os.makedirs(LOG_DIR, exist_ok=True)
    return os.path.join(LOG_DIR, f"game_{time.strftime('%Y%m%d_%H%M%S')}.log")


def _player_squads(state, owner):
    """Every unit one player fields, wherever it currently is: on the board
    (reached through its models, since GameState only tracks Tokens there),
    embarked in a TRANSPORT (rule 18.02), or still in reserves (rule 03.02) -
    the last two never appear in state.tokens at all."""
    squads = []
    for candidate in [t.squad for t in state.tokens] + state.embarked_squads + state.reserves:
        if candidate is not None and candidate.owner == owner and candidate not in squads:
            squads.append(candidate)
    return squads


def _army_points_line(state, owner):
    """What this player's deployed list costs, per its faction's published
    points list (Squad.points, computed by build_squad()). Logged once at
    startup because that number is otherwise only visible one model at a time
    via Ctrl+hover. Unpriced units are named rather than silently counted as
    0 - the Orks have no points list transcribed yet, and a total that quietly
    omitted five units would be worse than no total."""
    squads = _player_squads(state, owner)
    priced = [s for s in squads if s.points is not None]
    unpriced = [s for s in squads if s.points is None]
    if not priced:
        return f"{owner} fields {len(squads)} units, points unknown (no points list transcribed for their faction yet)."
    line = f"{owner} fields {len(squads)} units, {sum(s.points for s in priced)} pts"
    if unpriced:
        line += f" (plus {len(unpriced)} unpriced: {', '.join(s.name for s in unpriced)})"
    return line + "."


def _attached_unit_lines(state, owner):
    """One line per attached unit (19.01) this player fields, naming its
    components.

    Logged at startup next to the points total, for the same reason: an
    attachment is decided while the scene is built - long before the
    GameLog exists - and is otherwise only discoverable by hovering a model.
    It also materially changes what is on the board (two units became one),
    so a log that never mentions it makes the unit count look wrong."""
    lines = []
    for squad in _player_squads(state, owner):
        if not attached_units.is_attached_unit(squad):
            continue
        parts = ", ".join(
            f"{c.name}{'' if c.role == attached_units.BODYGUARD else f' ({c.role})'}"
            for c in attached_units.components(squad)
        )
        lines.append(f"{owner}: {squad.name} is one attached unit (19.01) - {parts}.")
    return lines


def _enhancement_lines(state, owner):
    """One line per Enhancement this player fields, naming the bearer model.

    Logged at startup for exactly the reason _attached_unit_lines() above is:
    an Enhancement is given during army building, long before the GameLog
    exists, and it changes both what the army costs and what one model can
    do - a log that never mentions it leaves a 20-point upgrade invisible
    until it fires."""
    lines = []
    for squad in _player_squads(state, owner):
        for model in starflare_ignition.bearer_models(squad):
            lines.append(
                f"{owner}: {model.profile.name} in {squad.name} carries the "
                f"{starflare_ignition.STARFLARE_IGNITION_SYSTEM_NAME} Enhancement "
                f"({starflare_ignition.STARFLARE_IGNITION_SYSTEM_POINTS} pts)."
            )
    return lines


def main(map_key=None):
    load_dotenv()  # picks up ANTHROPIC_API_KEY from the project's local .env, if present
    pygame.init()

    # Which battlefield this run is played on (User: "ich hätte gerne eine 2te
    # map ... es soll zusätzlich existieren"). Board size, deployment zones,
    # terrain and both armies' deployment positions all come from it - see
    # game/maps.py. apply_to_config() has to happen here, before ANY of the
    # board dimensions below are read: the whole engine and the AI read
    # config.BOARD_WIDTH_IN/BOARD_HEIGHT_IN directly.
    battle_map = maps.apply_to_config(maps.get(map_key if map_key is not None else config.MAP))

    # Fullscreen is now the default display mode (User: "es wird zeit, einen
    # vollbild modus einzuführen (default)"). The window is sized to
    # whatever the desktop resolution actually is - (0, 0) tells SDL to use
    # the current display mode - instead of a size computed ahead of time
    # from the board's own pixel dimensions like the old fixed-window layout
    # did. `board` is still built at RENDER_SUPERSAMPLE times
    # config.PIXELS_PER_INCH (see config.RENDER_SUPERSAMPLE's own comment for
    # why) - its pixel size is now used only to work out the board area's
    # aspect ratio below, never to size the window itself.
    board = Board(config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN, config.PIXELS_PER_INCH * config.RENDER_SUPERSAMPLE)
    fullscreen = config.FULLSCREEN
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN if fullscreen else 0)
    pygame.display.set_caption("WH40k Board - Step 4")
    window_width, window_height = screen.get_size()

    # UI overlay stays fixed (User: "das ui overlay soll fixed sein"): the
    # left/right side panels and the bottom Reserves strip are always
    # exactly config.LEFT_PANEL_WIDTH/RIGHT_PANEL_WIDTH/RESERVES_PANEL_HEIGHT
    # pixels, pinned to their own screen edge, regardless of actual screen
    # resolution. The board area is simply whatever's left over in the
    # middle - and, per User feedback ("der gesamte platz in der mitte
    # sollte natürlich auch ausgenutzt werden, wenn ich ranzoome"), it
    # ALWAYS fills that entire leftover rect, at every zoom level - no
    # letterbox bars sitting there unused. Camera's own _fit_scale (see
    # game/camera.py) is what makes that possible without distorting every
    # model's circular base into an ellipse: it picks whichever axis needs
    # the LARGER scale to cover this rect (not the smaller, "whole board
    # visible" one an earlier version of this used), so the same uniform
    # scale factor applies to both axes - covering the screen exactly,
    # cropping a bit of whichever axis has "extra" board at zoom==min (reach
    # it by panning), same as any further zoom-in already worked.
    top_row_height = window_height - config.RESERVES_PANEL_HEIGHT
    available_width = window_width - config.LEFT_PANEL_WIDTH - config.RIGHT_PANEL_WIDTH
    board_rect_screen = pygame.Rect(config.LEFT_PANEL_WIDTH, 0, available_width, top_row_height)
    left_panel_rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, top_row_height)
    right_panel_rect = pygame.Rect(window_width - config.RIGHT_PANEL_WIDTH, 0, config.RIGHT_PANEL_WIDTH, top_row_height)

    # Später-Liste (Kamera-Scrolling/Viewport): board_surface used to be a
    # direct subsurface of `screen` (drawing onto it WAS drawing onto the
    # screen, 1:1, no scaling). It's now a standalone offscreen Surface,
    # always rendered at full (supersampled) resolution - the final display
    # step (see the render loop below) scales whichever Camera-chosen
    # sub-rect of it is currently visible down/up to fill board_rect_screen.
    # Every renderer.draw_*(board_surface, ...) call and every board-inch/
    # pixel conversion elsewhere is unaffected by any of this - only the
    # camera's own to_native_px()/visible_rect() know zoom/pan even exists.
    board_surface = pygame.Surface((board.width_px, board.height_px))
    camera = Camera(board_rect_screen.width, board_rect_screen.height, board.width_px, board.height_px)
    reserves_panel_rect = pygame.Rect(0, top_row_height, window_width, config.RESERVES_PANEL_HEIGHT)
    log_rect = pygame.Rect(
        right_panel_rect.x,
        right_panel_rect.bottom - config.LOG_HEIGHT,
        right_panel_rect.width,
        config.LOG_HEIGHT,
    )

    state = GameState()

    # Every unit the scene builds is registered here rather than being put
    # straight onto the battlefield, so the same army list can start two
    # different ways:
    #
    #   config.PREGAME_DEPLOYMENT = True  - nothing is placed. The units go to
    #     game/pregame.py's PregameController, which runs rule 03.01's real
    #     opening sequence (Declare Battle Formations -> roll-off -> alternating
    #     deployment -> roll-off for the first turn -> pre-battle abilities).
    #     The `destination`/`transport` recorded below become the AI's
    #     preference hints, not the answer - both players re-declare them.
    #
    #   config.PREGAME_DEPLOYMENT = False - the legacy instant scene: applied
    #     immediately, exactly as before, using the hand-tuned per-model
    #     positions in game/maps.py. Kept because every A/B measurement in
    #     CLAUDE.md was taken against precisely this layout, because
    #     selfplay.py's long-running baseline depends on it, and because it is
    #     the quality benchmark the AI's own deployment is compared against.
    scene_units = []

    def register_unit(squad, destination=pregame.DEPLOY, transport=None):
        """Record a built unit and, in legacy mode, put it where it belongs.

        A map may field only part of the roster (BattleMap.roster - map 3 uses
        it for a four-a-side board). The filtering happens HERE, at the one
        point every built unit passes through, so the army lists above stay a
        single definition and a map only says who turns up. A unit the map does
        not field is simply never registered: it was built and is then dropped
        on the floor, which costs a few milliseconds and keeps the roster code
        free of per-map conditionals."""
        if not battle_map.fields(squad):
            return squad
        scene_units.append({"squad": squad, "destination": destination, "transport": transport})
        if config.PREGAME_DEPLOYMENT:
            return squad
        if destination == pregame.RESERVES:
            state.add_reserve_squad(squad)
        elif destination == pregame.EMBARK:
            squad.embarked_in = transport
            state.embarked_squads.append(squad)
        else:
            for model in squad.models:
                state.add_token(model)
        return squad

    # Player 1 fields the T'au Empire (Retaliation Cadre) list the user
    # supplied (2026-07-31, replacing the previous 550pt/6-unit roster
    # wholesale): Char1 Cadre Fireblade, Char2 Commander in Coldstar
    # Battlesuit, 1x Breacher Team, 2x Strike Team, 1x Crisis Starscythe
    # Battlesuits, 1x Devilfish, 1x Ghostkeel Battlesuit, 2x Kroot
    # Carnivores, 1x Stealth Battlesuits - built via the game.factions
    # scaffold (build_squad()) rather than hand-placed Tokens. Each
    # Fire-Warrior-type Shas'ui gets whatever gear the list actually lists
    # for THAT specific model line (Strike Team 2's own Shas'ui gets none
    # this time, unlike Strike Team 1's); Kroot take no gear (none listed).
    # User instruction: a 10-model squad forms 2 ranks of 5, not one
    # spread-out line.
    #
    # Deployment (user instruction, this session): "den fireblade zu den
    # breachern im devilfish" - Cadre Fireblade embarks in the SAME Devilfish
    # as the Breacher Team instead of deploying separately (Attached Units
    # isn't a live mechanic in this engine - same gap as every Leader
    # ability here, e.g. Ork Tankbustas' own note in game/factions/orks.py -
    # so "joins them" just means "embarked in the same TRANSPORT", same
    # convention already used for the Ork Warboss riding along with Boyz 2).
    # Capacity check: 10 Breacher Fire Warriors + 1 Cadre Fireblade
    # (INFANTRY, not BATTLESUIT/KROOT/VESPID STINGWINGS, so
    # transport-eligible) = 11 of the Devilfish's 12-model capacity.
    # "den coldstar zu den starsythe in reserve" - Commander in Coldstar
    # Battlesuit and Crisis Starscythe Battlesuits both start in Strategic
    # Reserves (rule 03.02) TOGETHER instead of the Coldstar deploying on the
    # board - same "arrives from reserves alongside them" reading of
    # "joins them", built further below, after the main on-board roster.
    #
    # Player 2 remains the full Ork army list (unaffected by this change,
    # see its own build further down) - a slow-shooting T'au gunline
    # (Player 1) facing a pure fast-melee Ork army (Player 2) exercises the
    # charge/pile-in/consolidate paths this scene is meant to stress.
    #
    # Deployment: every position, on either map, is verified clear of the
    # board edge at the model's own base radius, of every Dense terrain
    # feature, of every other deployed model, and of rule 09.02's coherency
    # and 9" spread - see game/maps.py, which is where the positions live and
    # where each one's provenance is recorded.
    GUARDIAN_SHIELD_GEAR = ["Guardian Drone", "Shield Drone"]
    # Real datasheet default (official app screenshot) for Ghostkeel
    # Battlesuit is Fusion Collider + Twin T'au Flamer (see
    # game/factions/tau_empire.py's _GHOSTKEEL_LOADOUT) - this squad's own
    # build ("Battlesuit support system, Ghostkeel fists, Cyclic ion raker,
    # Twin fusion blaster", user-supplied separately from the datasheet
    # itself) is reproduced explicitly via these two wargear choices instead
    # of relying on the coded default to match it. Note: as this army's only
    # Ghostkeel (unit_index=1), the real list prices this build at 165 pts
    # (150 base + 15 for the Cyclic Ion Raker) - the list's own stated
    # "160 pts" doesn't match that arithmetic (same kind of stale/
    # differently-sequenced number as the Devilfish's own "85 pts" below),
    # so it's left as an informational mismatch rather than forced to match.
    GHOSTKEEL_CHOICES = {"Ghostkeel Battlesuit": {GHOSTKEEL_FUSION_TO_ION_RAKER: 1, GHOSTKEEL_FLAMER_TO_FUSION_BLASTER: 1}}
    # Pathfinder Team (user-supplied list): Shas'ui with 2x Shield Drone +
    # Grav-inhibitor Drone and a Semi-automatic grenade launcher in place of
    # his Pulse carbine, plus 3 rank-and-file on Rail rifles - each of those
    # swaps out that model's own Pulse carbine, exactly as the list has it
    # ("3 with Close combat weapon, Pulse pistol, Rail rifle"). The Rail
    # rifle's stat line arrived after the datasheet itself, which is why
    # these three were briefly built on carbines instead.
    PATHFINDER_GEAR = ["Shield Drone", "Shield Drone", "Grav-inhibitor Drone"]
    PATHFINDER_CHOICES = {
        "Pathfinder Shas'ui": {PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER: 1},
        "Pathfinder": {PATHFINDER_CARBINE_TO_RAIL_RIFLE: 3},
    }
    # Riptide (user-supplied list): "Ion accelerator, 2x Missile pod, Twin
    # fusion blaster" - the Ion accelerator replaces the Heavy burst cannon,
    # the Twin fusion blaster the Twin plasma rifle, and the two Missile pods
    # are the datasheet's own baseline Missile Drones.
    RIPTIDE_CHOICES = {
        "Riptide Battlesuit": {RIPTIDE_BURST_TO_ION_ACCELERATOR: 1, RIPTIDE_PLASMA_TO_TWIN_FUSION: 1},
    }
    ARMY = [
        # (datasheet, gear-slot model line name (or None), gear list, color, wargear choices (or None))
        (BREACHER_TEAM, "Breacher Fire Warrior Shas'ui", GUARDIAN_SHIELD_GEAR, (220, 150, 70), None),
        (STRIKE_TEAM, "Fire Warrior Shas'ui", GUARDIAN_SHIELD_GEAR, (60, 140, 200), None),
        (KROOT_CARNIVORES, None, None, (120, 90, 40), None),
        (PATHFINDER_TEAM, "Pathfinder Shas'ui", PATHFINDER_GEAR, (90, 180, 140), PATHFINDER_CHOICES),
        (STEALTH_BATTLESUITS, None, None, (100, 100, 150), None),
        (GHOSTKEEL_BATTLESUIT, None, None, (130, 130, 170), GHOSTKEEL_CHOICES),
        (RIPTIDE_BATTLESUIT, None, None, (150, 150, 195), RIPTIDE_CHOICES),
        (THE_TWIN_LANCE, None, None, (210, 190, 120), None),
    ]
    # Hand-placed starting positions, one per-model list per ARMY entry, in
    # the same order - a property of the MAP rather than of the army list
    # (the two maps have differently shaped zones on different board edges,
    # so a position from one would be off-board on the other), which is why
    # both tables live in game/maps.py.
    #
    # ONLY used by the legacy --no-deployment mode. With the Pre-game
    # Sequence (03.01) on - the default - the player deploys this army
    # himself and these are never read, which is why the roster above was
    # changed without re-searching them (user: "nicht aufstellen, wir haben
    # ja jetzt die spieler aufstellung drin").
    #
    # They no longer cover the current roster, and that is checked rather
    # than left to zip() - zip() would silently truncate the army to the
    # table's length and quietly drop whichever units fell off the end.
    PLAYER1_MODEL_POSITIONS = battle_map.player1.squads
    if not config.PREGAME_DEPLOYMENT and len(PLAYER1_MODEL_POSITIONS) != len(ARMY):
        raise SystemExit(
            "--no-deployment needs one hand-placed position list per unit, and neither army "
            f"has them any more: {battle_map.key} carries {len(PLAYER1_MODEL_POSITIONS)} Player 1 "
            f"lists for {len(ARMY)} units, and Player 2's roster was replaced without positions "
            "at all. Both army lists were changed on the understanding that the Pre-game Sequence "
            "(rule 03.01) places them - user: \"deployment kannst du ueberspringen, dafuer haben "
            "wir jetzt die player aufstellung am anfang\". Run without --no-deployment, or add "
            "the missing entries to game/maps.py."
        )

    # Player 1's Devilfish (user instruction, from back when both players
    # still fielded T'au: "gib jedem spieler einen devilfish und packe einen
    # der breacher squads da rein" - Player 2's own copy is gone now along
    # with the rest of its T'au roster, see the Boyz build below), carrying
    # Breacher Team embarked inside it instead of deploying it on the board
    # directly - and now Cadre Fireblade alongside it (see above).
    # User-supplied build: "1x Devilfish (85 pts): Accelerator burst cannon,
    # Armoured hull, 2x Seeker missile, 2x Twin pulse carbine" -
    # DEVILFISH_SEEKER_MISSILE_OPTION on top of _DEVILFISH_LOADOUT's own
    # baseline (see game/factions/tau_empire.py). As this army's only
    # Devilfish (unit_index=1) the real list prices this build at 75 pts,
    # not the list's own stated "85 pts" (that's the 4th+ unit price) - same
    # kind of informational mismatch as the Ghostkeel's own note above.
    #
    # Placement is per-map (see game/maps.py), like every other position here.
    DEVILFISH_X, DEVILFISH_Y = battle_map.player1.devilfish
    DEVILFISH_CHOICES = {"Devilfish": {DEVILFISH_SEEKER_MISSILE_OPTION: 1}}
    CADRE_FIREBLADE_GEAR = ["Gun Drone", "Gun Drone"]

    # (This used to be wrapped in `for owner, mirror in (("Player 1", False),)`
    # - a one-element loop with `mirror` hardwired False, left over from the
    # original T'au-vs-T'au scene where Player 2's army was Player 1's mirrored
    # across the board. Player 2 has been Orks with its own position tables for
    # a long time, so both the loop and the flag were dead.)
    owner = "Player 1"
    unit_counts = {}
    for index, (datasheet, leader_line_name, gear_list, color, choices) in enumerate(ARMY):
        # Empty in Pre-game mode (nothing is hand-placed) - see the guard above.
        model_positions = PLAYER1_MODEL_POSITIONS[index] if index < len(PLAYER1_MODEL_POSITIONS) else []
        unit_counts[datasheet.name] = unit_counts.get(datasheet.name, 0) + 1
        gear = {leader_line_name: gear_list} if leader_line_name is not None else None
        first_x, first_y = model_positions[0] if model_positions else (0.0, 0.0)
        squad = build_squad(
            datasheet, owner=owner, gear=gear, choices=choices,
            name=f"{owner[-1]} {datasheet.name} {unit_counts[datasheet.name]}",
            x_in=first_x, y_in=first_y, color=color,
            # Which copy of this datasheet the list is buying - the same
            # running count that already names the squad. The official
            # points list charges more for later copies of some units
            # (see game/factions/points.py), so this is what makes
            # Squad.points come out right rather than always quoting the
            # 1st-unit price.
            unit_index=unit_counts[datasheet.name],
        )
        for model, (x_in, y_in) in zip(squad.models, model_positions):
            model.x_in, model.y_in = x_in, y_in

        if datasheet is BREACHER_TEAM:
            # This squad rides in the Devilfish instead - its models
            # above still got real x_in/y_in (harmless, never read once
            # embarked - same "inert" note as the Crisis Starscythe/
            # Commander in Coldstar Battlesuit reserve squads below) but
            # never reach state.tokens; they live only in
            # state.embarked_squads, exactly like the old hand-built
            # Space-Marine demo scene's "Embarked Squad" did, just
            # reached through a real embark-shaped assignment instead of
            # constructing it by hand.
            devilfish_x, devilfish_y = DEVILFISH_X, DEVILFISH_Y
            devilfish_squad = build_squad(
                DEVILFISH, owner=owner, choices=DEVILFISH_CHOICES,
                name=f"{owner[-1]} Devilfish", x_in=devilfish_x, y_in=devilfish_y, color=color,
            )
            devilfish_token = devilfish_squad.models[0]
            register_unit(devilfish_squad)

            # Cadre Fireblade JOINS the Breacher Team as an attached unit
            # (19.01) - "den fireblade zu den breachern im devilfish".
            # This used to be approximated as "embarked in the same
            # TRANSPORT", because attaching wasn't implemented; now it is,
            # so the Fireblade's Leader ability (24.22) is used for what it
            # actually says. Attached BEFORE embarking, so the transport
            # sees one 11-model unit and checks its capacity once against
            # the real number (12 capacity, so it fits) rather than
            # admitting two units and being over capacity afterwards.
            fireblade_squad = build_squad(
                CADRE_FIREBLADE, owner=owner, gear={"Cadre Fireblade": CADRE_FIREBLADE_GEAR},
                name=f"{owner[-1]} Cadre Fireblade", x_in=devilfish_x, y_in=devilfish_y, color=color,
            )
            squad = attached_units.attach(fireblade_squad, squad, game_state=state)

            register_unit(squad, pregame.EMBARK, transport=devilfish_token)
        else:
            register_unit(squad)

    # Commander in Coldstar Battlesuit + Crisis Starscythe Battlesuits: both
    # in Strategic Reserves (rule 03.02) TOGETHER (user instruction: "den
    # coldstar zu den starsythe in reserve" - Attached Units isn't live here
    # either, so "joins them" means "arrives from reserves alongside them",
    # same reading as Cadre Fireblade/Breacher Team above). Reserve squads
    # skip the x_in/y_in/lay-out dance every on-board squad above needs -
    # their models never enter state.tokens until SetupController actually
    # sets them up (see GameState.add_reserve_squad's own docstring), so
    # where they're "stacked" beforehand is inert.
    #
    # Coldstar Commander's own build ("2x Shield Drone, 2x Burst cannon,
    # Cyclic ion blaster, High-output burst cannon, Battlesuit fists") -
    # user clarification: a Coldstar Battlesuit freely fills 4 slots with
    # weapons or support systems, unlike the single-hardpoint-with-swap
    # model this engine's other T'au Battlesuit datasheets have - modeled as
    # the printed default (High-output Burst Cannon + Battlesuit Fists) plus
    # two pure wargear ADDITIONS (COLDSTAR_ADD_2X_BURST_CANNON,
    # COLDSTAR_ADD_CYCLIC_ION_BLASTER - see game/factions/tau_empire.py's own
    # note on both) rather than a real generic N-slot system.
    COLDSTAR_GEAR = ["Shield Drone", "Shield Drone"]
    COLDSTAR_CHOICES = {
        "Commander in Coldstar Battlesuit": {COLDSTAR_ADD_2X_BURST_CANNON: 1, COLDSTAR_ADD_CYCLIC_ION_BLASTER: 1},
    }
    coldstar_squad = build_squad(
        COMMANDER_IN_COLDSTAR_BATTLESUIT, owner="Player 1", gear={"Commander in Coldstar Battlesuit": COLDSTAR_GEAR},
        choices=COLDSTAR_CHOICES, name="1 Commander in Coldstar Battlesuit 1", color=(200, 170, 90),
    )
    # Starflare Ignition System Enhancement (user-supplied, 20 pts,
    # game/starflare_ignition.py). This army's only BATTLESUIT CHARACTER that
    # is not an EPIC HERO, so the only legal bearer it has - grant() refuses
    # anything else.
    #
    # The rebuilt army list ("ersetzt die aktuelle") prices this Commander at
    # a bare 95 pts with no Enhancement, so it was dropped when the roster was
    # replaced and then explicitly asked back ("gib bitte dem coldstar noch
    # starflare ignition system") - the army therefore comes to 20 pts more
    # than the list's own total, on purpose.
    #
    # Granted BEFORE the attach() below: attach() re-derives the attached
    # unit's points from its components' own (game/attached_units.py), so the
    # 20 pts only reach the army total if they are already on this squad when
    # the component record is taken.
    # (No game_log yet - it is created long after the scene is built, so this
    # is reported alongside the army points total instead, the same way an
    # attached unit is - see _enhancement_lines().)
    starflare_ignition.grant(coldstar_squad)
    # Not added to Reserves on its own: it is attached to the Crisis
    # Starscythe Battlesuits below (19.01), and only the resulting single
    # attached unit goes into Reserves - which is what "den coldstar zu den
    # starsythe in reserve" asks for, and now literally rather than as the
    # old "two separate units that happen to arrive the same turn"
    # approximation. Arriving together is no longer a coincidence to
    # maintain; it is one unit.

    # Crisis Starscythe Battlesuits: user-supplied build - 2x Shas'ui each
    # with Gun Drone + Shield Drone, 1x Shas'vre with Marker Drone + Shield
    # Drone, all three with 2x Burst Cannon (Battlesuit fists is the fixed
    # baseline melee weapon, never swapped). The datasheet's own real
    # default (official app screenshot) is 1 Burst Cannon + 1 T'au Flamer
    # per model (see game/factions/tau_empire.py's _STARSCYTHE_LOADOUT) -
    # this squad's own "2x Burst Cannon" build is reproduced explicitly via
    # STARSCYTHE_FLAMER_TO_BURST on every model instead of relying on the
    # coded default to match it (same pattern as GHOSTKEEL_CHOICES above).
    # gear is keyed by the datasheet's own internal line names (the 2
    # Shas'ui are modeled as two separate count=1 ModelLines so each can
    # take its own independent pair of drones - see CRISIS_STARSCYTHE's own
    # definition for why). Note: as this army's only Crisis Starscythe unit
    # (unit_index=1), the real list prices this build at 90 pts (all flamer
    # swaps are free) - the list's own stated "110 pts" doesn't match that
    # arithmetic, same kind of informational mismatch as the Ghostkeel's own
    # note above.
    STARSCYTHE_SHAS_VRE_GEAR = ["Marker Drone", "Shield Drone"]
    STARSCYTHE_SHAS_UI_GEAR = ["Gun Drone", "Shield Drone"]
    STARSCYTHE_LINES = ("Crisis Starscythe Shas'vre", "Crisis Starscythe Shas'ui (1)", "Crisis Starscythe Shas'ui (2)")
    STARSCYTHE_GEAR = {
        "Crisis Starscythe Shas'vre": STARSCYTHE_SHAS_VRE_GEAR,
        "Crisis Starscythe Shas'ui (1)": STARSCYTHE_SHAS_UI_GEAR,
        "Crisis Starscythe Shas'ui (2)": STARSCYTHE_SHAS_UI_GEAR,
    }
    STARSCYTHE_CHOICES = {line: {STARSCYTHE_FLAMER_TO_BURST: 1} for line in STARSCYTHE_LINES}
    starscythe_squad = build_squad(
        CRISIS_STARSCYTHE, owner="Player 1", gear=STARSCYTHE_GEAR, choices=STARSCYTHE_CHOICES,
        name="1 Crisis Starscythe Battlesuits 1", color=(170, 130, 200),
    )
    # The Commander in Coldstar Battlesuit built above leads this unit
    # (19.01) - the points list's own "LEADER: ... Crisis Starscythe
    # Battlesuits" line makes the pairing legal, which attach() checks.
    starscythe_squad = attached_units.attach(coldstar_squad, starscythe_squad, game_state=state)
    register_unit(starscythe_squad, pregame.RESERVES)

    # Crisis Sunforge Battlesuits + Commander Farsight (user instruction:
    # "farsight in die sunforge"). Built here rather than in ARMY above for
    # the same reason Crisis Starscythe is: its drones are per MODEL LINE
    # (the two Shas'ui are separate count=1 ModelLines so each can take its
    # own pair), which the single gear-slot name an ARMY entry carries
    # cannot express.
    #
    # User-supplied build: both Shas'ui with Gun Drone + Shield Drone, the
    # Shas'vre with Marker Drone + Shield Drone; every model keeps the
    # printed 2x Fusion blaster + Battlesuit fists, so there are no wargear
    # choices to make.
    SUNFORGE_GEAR = {
        "Crisis Sunforge Shas'vre": ["Marker Drone", "Shield Drone"],
        "Crisis Sunforge Shas'ui (1)": ["Gun Drone", "Shield Drone"],
        "Crisis Sunforge Shas'ui (2)": ["Gun Drone", "Shield Drone"],
    }
    sunforge_squad = build_squad(
        CRISIS_SUNFORGE, owner="Player 1", gear=SUNFORGE_GEAR,
        name="1 Crisis Sunforge Battlesuits 1", color=(200, 120, 90),
    )
    farsight_squad = build_squad(
        COMMANDER_FARSIGHT, owner="Player 1", name="1 Commander Farsight 1", color=(220, 140, 80),
    )
    # The points list's own "LEADER: ... Crisis Sunforge Battlesuits" line
    # makes this pairing legal, which attach() checks.
    sunforge_squad = attached_units.attach(farsight_squad, sunforge_squad, game_state=state)
    register_unit(sunforge_squad)

    # Player 2 fields the Ork army list the user supplied (replacing the
    # previous roster wholesale, the same way Player 1's was replaced):
    #
    #   Char1 Beastboss              -> attached to Beast Snagga Boyz
    #   Char2 Warboss                -> attached to Boyz 1
    #   Char3 Warboss in Mega Armour -> attached to Meganobz
    #   1x Beast Snagga Boyz (10), 2x Boyz (10, Boss Nob w/ Power Klaw),
    #   1x Battlewagon ('Ard Case + 4x Big Shoota), 1x Deff Dread,
    #   6x Deffkoptas, 1x Flash Gitz (10), 2x Gretchin (11), 1x Kill Rig,
    #   6x Meganobz, 1x Stormboyz (10, Boss Nob w/ Power Klaw),
    #   6x Tankbustas, 2x Trukk, 2x Warbikers (3 each, + Power Klaw)
    #
    # Every item on that list is now modeled. The three that were missing -
    # the Warboss's Attack squig, the Battlewagon's Zzap gun and the Flash
    # Gitz' Ammo Runt - had their stat lines/rules text supplied afterwards
    # and are built here. The Zzap gun in particular is the first weapon in
    # this engine with a dice-rolled Strength ("S D6+6"), see
    # WeaponProfile.strength_notation.
    #
    # Points: the list's own per-unit numbers run consistently above this
    # project's transcribed published list (e.g. Trukk 70 vs 55, Tankbustas
    # 140 vs 125, Kill Rig 155 vs 145, Deffkoptas 160 vs 140) - a newer
    # revision. Same treatment as Player 1's own list: named as an
    # informative mismatch, with the transcribed data left as the single
    # source of truth (see game/factions/orks_points.py).
    #
    # Transports (user instruction): "die ki soll die beast boyz + beast boss
    # bevorzugt in den kill rig packen und die meganobs + megaboss in
    # megaarmor in den battle wagon" - declared below as EMBARK hints, which
    # ai/deployment_ai.py's own _transport_affinity() honours as the scene's
    # answer AND, since this instruction, treats as exclusive (a hinted unit
    # is never loaded into some other transport that happens to be processed
    # first). Both fit: Beast Snagga Boyz + Beastboss = 11 models against the
    # Kill Rig's capacity 11, all BEAST SNAGGA INFANTRY as that datasheet
    # requires; Meganobz + Warboss in Mega Armour = 7 MEGA ARMOUR models = 14
    # capacity against the Battlewagon's 22.
    #
    # The two Trukks carry nobody by declaration - the AI fills them from
    # whatever short-ranged infantry is left, which is what its own
    # _transport_affinity() is for.
    #
    # No hand-placed positions: with the Pre-game Sequence (rule 03.01) the
    # AI deploys this army itself, exactly as Player 1's roster is handled.
    GRETCHIN_COLOR = (140, 110, 70)
    STORMBOYZ_COLOR = (110, 150, 70)
    WARBIKERS_COLOR = (150, 130, 60)
    BOYZ_COLOR = (70, 140, 60)
    PAINBOY_COLOR = (150, 65, 105)
    WARBOSS_COLOR = (170, 60, 60)
    MEGANOBZ_COLOR = (120, 100, 130)
    DEFF_DREAD_COLOR = (80, 80, 90)
    DEFFKOPTAS_COLOR = (130, 145, 165)
    TANKBUSTAS_COLOR = (160, 110, 40)
    BEAST_SNAGGA_COLOR = (120, 145, 55)
    BEASTBOSS_COLOR = (185, 80, 45)
    KILL_RIG_COLOR = (100, 85, 65)
    BATTLEWAGON_COLOR = (75, 95, 55)
    FLASH_GITZ_COLOR = (170, 150, 55)

    # --- Kill Rig, and the Beast Snagga Boyz + Beastboss that ride in it ---
    kill_rig_squad = build_squad(
        KILL_RIG, owner="Player 2", name="2 Kill Rig 1", color=KILL_RIG_COLOR,
    )
    kill_rig_token = kill_rig_squad.models[0]
    register_unit(kill_rig_squad)

    beast_snagga_squad = build_squad(
        BEAST_SNAGGA_BOYZ, owner="Player 2", name="2 Beast Snagga Boyz 1", color=BEAST_SNAGGA_COLOR,
    )
    beastboss_squad = build_squad(
        BEASTBOSS, owner="Player 2", name="2 Beastboss 1", color=BEASTBOSS_COLOR,
    )
    # The Beastboss's own Leader ability (24.22) lists Beast Snagga Boyz, so
    # attach() accepts the pairing. Attached BEFORE the transport hint so the
    # capacity check sees the finished 11-model unit.
    beast_snagga_squad = attached_units.attach(beastboss_squad, beast_snagga_squad, game_state=state)
    register_unit(beast_snagga_squad, pregame.EMBARK, transport=kill_rig_token)

    # --- Battlewagon, and the Meganobz + Warboss in Mega Armour inside ---
    battlewagon_squad = build_squad(
        BATTLEWAGON, owner="Player 2", name="2 Battlewagon 1", color=BATTLEWAGON_COLOR,
        gear={"Battlewagon": [BATTLEWAGON_ARD_CASE]},
        choices={"Battlewagon": {BATTLEWAGON_ADD_BIG_SHOOTAS: 1, BATTLEWAGON_ADD_ZZAP_GUN: 1}},
    )
    battlewagon_token = battlewagon_squad.models[0]
    register_unit(battlewagon_squad)

    meganobz_squad = build_squad(
        MEGANOBZ, owner="Player 2", composition_index=1, name="2 Meganobz 1", color=MEGANOBZ_COLOR,
    )
    warboss_mega_squad = build_squad(
        WARBOSS_MEGA_ARMOUR, owner="Player 2", name="2 Warboss in Mega Armour 1", color=WARBOSS_COLOR,
    )
    # Its Leader ability lists Meganobz. Unlike the old Trukk arrangement -
    # where 6 MEGA ARMOUR Meganobz alone already filled a Trukk's capacity 12
    # and the leader had to be left out entirely - the Battlewagon's 22 has
    # room for all 14 capacity this attached unit costs.
    meganobz_squad = attached_units.attach(warboss_mega_squad, meganobz_squad, game_state=state)
    register_unit(meganobz_squad, pregame.EMBARK, transport=battlewagon_token)

    # --- One 20-strong Boyz mob, led by BOTH the Warboss and the Painboy ---
    # composition_index=1 is the 20-model build, and it is load-bearing here
    # rather than just bigger: Boyz' own "Bodyguard" ability only allows a
    # SECOND Leader on a unit with a Starting Strength of 20, and only if one
    # of the two is a WARBOSS. Both conditions are checked for real - see
    # game/attached_units.py's _bodyguard_allows_second_leader().
    boyz_squad = build_squad(
        BOYZ, owner="Player 2", composition_index=1,
        choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}},
        name="2 Boyz 1", color=BOYZ_COLOR, unit_index=1,
    )
    warboss_squad = build_squad(
        WARBOSS, owner="Player 2", name="2 Warboss 1", color=WARBOSS_COLOR,
        choices={"Warboss": {WARBOSS_ADD_ATTACK_SQUIG: 1}},
    )
    painboy_squad = build_squad(
        PAINBOY, owner="Player 2", name="2 Painboy 1", color=PAINBOY_COLOR,
        gear={"Painboy": [PAINBOY_GROT_ORDERLY]},
    )
    # Warboss FIRST: the exception needs a WARBOSS among the two, and
    # attaching him first means the Painboy's own check finds one already
    # there rather than depending on the order the pair happens to arrive in
    # (it accepts either, but this is the order the rule text reads in).
    boyz_squad = attached_units.attach(warboss_squad, boyz_squad, game_state=state)
    boyz_squad = attached_units.attach(painboy_squad, boyz_squad, game_state=state)
    register_unit(boyz_squad)

    # --- The rest of the roster ---
    for index in (1, 2):
        register_unit(build_squad(
            GRETCHIN, owner="Player 2", name=f"2 Gretchin {index}", color=GRETCHIN_COLOR, unit_index=index,
        ))

    # composition_index=0 is the 3-model composition (1 Boss Nob on Warbike +
    # 2 Warbikers), which is what this list fields twice.
    for index in (1, 2):
        register_unit(build_squad(
            WARBIKERS, owner="Player 2", composition_index=0,
            choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}},
            name=f"2 Warbikers {index}", color=WARBIKERS_COLOR, unit_index=index,
        ))

    register_unit(build_squad(
        STORMBOYZ, owner="Player 2", composition_index=1,
        choices={"Boss Nob": {STORMBOYZ_CHOPPA_TO_POWER_KLAW: 1}},
        name="2 Stormboyz 1", color=STORMBOYZ_COLOR,
    ))

    register_unit(build_squad(
        DEFF_DREAD, owner="Player 2", name="2 Deff Dread 1", color=DEFF_DREAD_COLOR,
    ))

    # composition_index=1 is the 6-model build this list fields; every model
    # keeps the printed Kopta rokkits + Slugga + Spinnin' blades, so there
    # are no wargear choices to make. DEEP STRIKE (24.09), so the deployment
    # AI is free to hold it in Strategic Reserves.
    register_unit(build_squad(
        DEFFKOPTAS, owner="Player 2", composition_index=1,
        name="2 Deffkoptas 1", color=DEFFKOPTAS_COLOR,
    ))

    # composition_index=1 is the 10-model build this list fields.
    register_unit(build_squad(
        FLASH_GITZ, owner="Player 2", composition_index=1, name="2 Flash Gitz 1", color=FLASH_GITZ_COLOR,
        gear={"Kaptin": [FLASH_GITZ_AMMO_RUNT]},
    ))

    # This list's own custom Tankbusta loadout - Boss Nob w/ Smash Hammer
    # instead of a 2nd Rokkit Pistol, one Tankbusta w/ an extra Rokkit
    # Launcha (see TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER/
    # TANKBUSTAS_ADD_ROKKIT_LAUNCHA's own notes).
    register_unit(build_squad(
        TANKBUSTAS, owner="Player 2", name="2 Tankbustas 1", color=TANKBUSTAS_COLOR,
        choices={
            "Boss Nob": {TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER: 1},
            "Tankbusta": {TANKBUSTAS_ADD_ROKKIT_LAUNCHA: 1},
        },
    ))

    # A partial roster (BattleMap.roster) has to be self-consistent, and the
    # two ways it can fail are both silent otherwise: a name that matches no
    # unit quietly fields one fewer than intended, and a passenger whose
    # transport was left out would be declared into a vehicle that is not in
    # the game. Refused loudly instead - the same lesson as the
    # --no-deployment guard below, where a zip() over mismatched lists used to
    # drop a unit without a word.
    if battle_map.roster is not None:
        fielded = {entry["squad"].name for entry in scene_units}
        unknown = sorted(battle_map.roster - fielded)
        if unknown:
            raise SystemExit(
                f"{battle_map.key}'s roster names {len(unknown)} unit(s) this scene does not "
                f"build: {', '.join(unknown)}. Fix the names in game/maps.py - they must match "
                "the squad names main.py gives them exactly (an attached unit is named after "
                "the merge, e.g. \"2 Boyz 1 + Warboss + Painboy\")."
            )
        for entry in scene_units:
            carrier = entry["transport"]
            carrier_squad = getattr(carrier, "squad", None) if carrier is not None else None
            if carrier_squad is not None and carrier_squad.name not in fielded:
                raise SystemExit(
                    f"{battle_map.key}'s roster fields {entry['squad'].name!r} but not its "
                    f"transport {carrier_squad.name!r}. Add the transport, or drop the "
                    "passenger too."
                )

    # Deployment zones (rule 03.01), terrain areas and objectives - all three
    # belong to the selected map, see game/maps.py.
    battle_map.build(state)

    game_log = GameLog(file_path=_new_game_log_file_path())
    dice_manager = DiceManager()
    decision_manager = DecisionManager()
    # With a pre-game sequence, who takes the first turn isn't known until
    # after deployment (rule 03.01's Determine First Turn) - so the tracker is
    # built held at battle round 0 and started by begin_battle() below. The
    # tracker itself has to exist NOW regardless, because ~35 controllers take
    # it as a constructor argument.
    turn_tracker = TurnTracker(game_log=game_log, deferred_start=config.PREGAME_DEPLOYMENT)
    command_points = CommandPointManager(game_log=game_log)
    mission_controller = MissionController(game_log=game_log)
    if turn_tracker.started:
        # The legacy instant scene starts mid-Command-phase; the pre-game path
        # does all of this in begin_battle() instead, once there is actually an
        # army on the table to score and a first player to give CP to.
        for owner in ("Player 1", "Player 2"):
            game_log.add(_army_points_line(state, owner))
            for line in _attached_unit_lines(state, owner):
                game_log.add(line)
            for line in _enhancement_lines(state, owner):
                game_log.add(line)
        command_points.gain_core_cp()  # rule 08.02: the battle's very first phase is already Command
        # Same "the battle's very first phase is already Command" case as
        # gain_core_cp() above - update_control() itself only ever runs
        # inside advance_turn_phase(), so it's never seen this initial
        # deployment at all yet; run it once here too, otherwise Primary
        # scoring for turn 1's Command phase would score 0 regardless of
        # what either player's deployment happens to already be standing on.
        for objective in state.objectives:
            objective.update_control(state.tokens)
        mission_controller.score_primary(state.objectives, turn_tracker.active_player)
    stratagem_controller = StratagemController(game_log=game_log, command_points=command_points)
    thievin_scavengers_controller = ThievinScavengersController(
        dice_manager=dice_manager, command_points=command_points, all_tokens=state.tokens,
        objectives=state.objectives, turn_tracker=turn_tracker, game_log=game_log,
    )
    command_reroll_controller = CommandRerollController(stratagem_controller, dice_manager, turn_tracker=turn_tracker)

    input_manager = InputManager(board_offset=board_rect_screen.topleft, camera=camera)
    battle_shock_controller = BattleShockController(
        game_log=game_log, dice_manager=dice_manager, turn_tracker=turn_tracker,
        all_tokens=state.tokens,
    )
    insane_bravery_controller = InsaneBraveryController(
        stratagem_controller, battle_shock_controller, turn_tracker=turn_tracker, game_log=game_log,
    )
    movement_controller = MovementController(
        obstacles=state.obstacles, game_log=game_log, dice_manager=dice_manager, turn_tracker=turn_tracker,
        all_tokens=state.tokens, board_width_in=board.width_in, board_height_in=board.height_in,
    )
    fall_back_controller = FallBackController(
        movement_controller, battle_shock_controller, dice_manager=dice_manager, game_log=game_log,
    )
    greater_good_controller = GreaterGoodController(
        all_tokens=state.tokens, obstacles=state.obstacles, terrain_areas=state.terrain_areas,
        movement_controller=movement_controller, turn_tracker=turn_tracker, game_log=game_log,
    )
    suppression_controller = SuppressionController(
        all_tokens=state.tokens, turn_tracker=turn_tracker, decision_manager=decision_manager, game_log=game_log,
    )
    # Ghostkeel Battlesuit's own "Stealth Drones" ability (user-supplied,
    # not a core rule) - shared by shooting_controller/fight_controller
    # below, same as greater_good_controller/suppression_controller;
    # requesting through decision_manager is also what makes this
    # automatically resolvable by the AI, no extra wiring needed there
    # (see game/stealth_drones.py's own docstring).
    stealth_drones_controller = StealthDronesController(decision_manager=decision_manager, game_log=game_log)
    # Riptide Battlesuit's own "Nova Charge" ability (user-supplied, not a
    # core rule) - shooting-only, so unlike stealth_drones_controller it goes
    # to shooting_controller alone; requesting through decision_manager makes
    # it AI-resolvable with no extra wiring, same as that one.
    nova_charge_controller = NovaChargeController(decision_manager=decision_manager, game_log=game_log)
    # The Twin Lance's Neocapacitor Shields - fires at the start of the
    # OPPONENT's Charge phase (see game/neocapacitor_shields.py), so it is
    # triggered from advance_turn_phase() rather than from any controller.
    # Commander Farsight's Puretide's Teachings - plugged into the
    # StratagemController's cost hook, so every Stratagem in the game gets
    # the discount without knowing about it (see game/puretide.py).
    puretide_controller = PuretideController(turn_tracker=turn_tracker, game_log=game_log)
    stratagem_controller.cost_discounts.append(puretide_controller)
    neocapacitor_controller = NeocapacitorShieldsController(
        decision_manager=decision_manager, turn_tracker=turn_tracker,
        all_tokens=state.tokens, game_log=game_log,
    )
    support_turret_controller = SupportTurretController(game_log=game_log)
    # Rule (Strike Team's DS8 Support Turret, user-supplied): MovementController
    # can't take a SupportTurretController constructor dependency the other
    # way around without an import cycle risk - wired as a plain callback,
    # same pattern as fight_controller.on_unit_finished_fighting below.
    movement_controller.on_remain_stationary = support_turret_controller.on_remain_stationary
    waaagh_controller = WaaaghController(game_log=game_log)
    # Retaliation Cadre's Stim Injectors (1 CP): a reactive Stratagem offered
    # at rule 10.02's "select targets" step, so it's shared by
    # shooting_controller and fight_controller below the same way
    # stealth_drones_controller is. Requesting through decision_manager is also
    # what makes it resolvable by the AI with no extra wiring
    # (_maybe_resolve_decision()), same as Stealth Drones. Its own relevance
    # gate is what keeps "just after an enemy unit has selected its targets"
    # from interrupting the game on every enemy attack - see
    # game/stim_injectors.py's docstring.
    stim_injectors_controller = StimInjectorsController(
        stratagem_controller, decision_manager=decision_manager, turn_tracker=turn_tracker, game_log=game_log,
    )
    # War Horde's 'Ard as Nails - the same "just after an enemy unit has
    # selected its targets" trigger, but answered DETERMINISTICALLY for the AI
    # side rather than asked about (user: "hier auch deterministisch"). Player 2
    # is this project's AI player throughout main.py, so it is the one whose
    # answer the controller gives itself; a human running Orks still gets a
    # DecisionManager prompt, gated on the same three conditions. See
    # game/ard_as_nails.py.
    ard_as_nails_controller = ArdAsNailsController(
        stratagem_controller, decision_manager=decision_manager, turn_tracker=turn_tracker, game_log=game_log,
        auto_players=("Player 2",),
    )
    # Flash Gitz' Ammo Runt (user-supplied): offered when the unit is
    # selected to shoot, once per battle. Handed to ShootingController the
    # same way the Riptide's Nova Charge is - see game/ammo_runt.py. Same
    # auto_players shape as 'Ard as Nails above: per explicit user
    # instruction the AI uses it at the first opportunity instead of being
    # asked, while a human running Orks keeps the choice.
    ammo_runt_controller = AmmoRuntController(
        decision_manager=decision_manager, game_log=game_log, auto_players=("Player 2",),
    )
    # Kill Rig's Spirit of Gork (user-supplied): resolved at the start of
    # each Fight phase. Same auto_players shape as 'Ard as Nails above -
    # Player 2 is this project's AI throughout main.py, and per explicit
    # user instruction it picks the highest-points eligible unit itself
    # rather than being asked; a human keeps the DecisionManager prompt.
    spirit_of_gork_controller = SpiritOfGorkController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        all_tokens=state.tokens, auto_players=("Player 2",),
    )
    # Painboy's Grot Orderly (user-supplied wargear): resolved in its owner's
    # Command phase. Same auto_players shape again - per explicit user
    # instruction the AI uses it deterministically at the first opportunity.
    # It is handed SetupController's own position_valid() so "somewhere legal
    # to put the returning models" means exactly what it means for a
    # disembark or an ingress, rather than a second opinion that could drift.
    grot_orderly_controller = GrotOrderlyController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, auto_players=("Player 2",),
        position_valid=lambda model, x, y: setup_controller.position_valid(
            model, x, y, squad=model.squad,
        ),
    )
    # Both reactive stratagems above fire at the same moment in the sequence,
    # so both controllers go into the one target_reactions list that
    # ShootingController/FightController iterate at that point.
    # Seer Council's two reactive stratagems share Stim Injectors' and 'Ard as
    # Nails' "just after an enemy unit has selected its targets" trigger, but
    # each belongs to ONE phase: Forewarned's WHEN is the Fight phase, Psychic
    # Shield's the opponent's Shooting phase. So the single shared list becomes
    # two - the two phase-agnostic entries appear in both.
    forewarned_controller = ForewarnedController(
        stratagem_controller, decision_manager=decision_manager, game_log=game_log,
        all_tokens=state.tokens, turn_tracker=turn_tracker,
    )
    # on_activated is filled in once shooting_controller exists below: unlike
    # every other target reaction this one can invalidate the selection that
    # triggered it, and only the attacker's controller can undo that.
    psychic_shield_controller = PsychicShieldController(
        stratagem_controller, decision_manager=decision_manager, game_log=game_log,
        all_tokens=state.tokens, turn_tracker=turn_tracker,
    )
    shooting_target_reactions = (
        stim_injectors_controller, ard_as_nails_controller, psychic_shield_controller,
    )
    fight_target_reactions = (
        stim_injectors_controller, ard_as_nails_controller, forewarned_controller,
    )
    # The Falcon's Fire Support - constructed before the shooting controller
    # because that one reads its mark when deciding whether a Wound roll may
    # be re-rolled (see game/fire_support.py).
    fire_support_controller = FireSupportController(
        decision_manager=decision_manager, game_log=game_log,
    )
    # Asurmen's once-per-battle weapon grant - offered from start_shooting(),
    # the same hook Nova Charge and Ammo Runt use.
    hand_of_asuryan_controller = HandOfAsuryanController(
        decision_manager=decision_manager, game_log=game_log,
    )
    # The Farseer's Guide - the longest-lived mark here: set at the end of his
    # Movement phase and cleared when his NEXT Command phase begins, so it is
    # live through the opponent's whole turn (see game/guide.py).
    guide_controller = GuideController(
        decision_manager=decision_manager, game_log=game_log, all_tokens=state.tokens,
        obstacles=state.obstacles, terrain_areas=state.terrain_areas,
    )
    # Eldrad Ulthran's Doom - the same mark one word apart (game/psychic_mark.py
    # holds what the two share), except it improves the WOUND roll and prints no
    # once-per-turn cap. Its own controller rather than a mode of the one above,
    # because a player can legitimately have both marks live at once.
    doom_controller = DoomController(
        decision_manager=decision_manager, game_log=game_log, all_tokens=state.tokens,
        obstacles=state.obstacles, terrain_areas=state.terrain_areas,
    )
    # Eldrad Ulthran's Diviner of Futures - a flat +1 CP at the start of his
    # controller's Command phase, routed through gain_cp() so the user's
    # +1-bonus-CP-per-battle-round house rule applies (see game/command_points.py).
    diviner_controller = DivinerOfFuturesController(
        command_points=command_points, all_tokens=state.tokens,
        turn_tracker=turn_tracker, game_log=game_log,
    )
    # Lhykhis' Whispering Web - the same after-shooting trigger and end-of-turn
    # life as the Falcon's Fire Support, but army-wide, so the mark is held per
    # player. Its effect is a crit threshold, read from BOTH hit steps via
    # game/crit_hit.py.
    whispering_web_controller = WhisperingWebController(
        decision_manager=decision_manager, game_log=game_log,
    )
    # Seer Council's Presentiment of Dread - a forced Battle-shock test at -1,
    # so it needs battle_shock_controller. Third consumer of start_forced_roll()
    # after Grav-inhibitor Field and Neocapacitor Shields.
    presentiment_controller = PresentimentOfDreadController(
        stratagem_controller, battle_shock=battle_shock_controller, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log, all_tokens=state.tokens,
        obstacles=state.obstacles, terrain_areas=state.terrain_areas,
    )
    # Seer Council's Isha's Fury - six D6 at 3+ after an enemy Normal, Advance
    # or Fall Back move. The roll and the mortal-wound allocation are Explosives'
    # shape; the trigger is movement_controller.on_move_finished, wired below.
    ishas_fury_controller = IshasFuryController(
        stratagem_controller, dice_manager=dice_manager, decision_manager=decision_manager,
        turn_tracker=turn_tracker, game_log=game_log, all_tokens=state.tokens,
    )
    # Asurmen's Tactical Acumen - a post-shooting Normal move, so it owns the
    # move's consequence (the charge lock) and therefore its Confirm button,
    # exactly like The Torchstar Gambit does for its own.
    tactical_acumen_controller = TacticalAcumenController(
        movement_controller=movement_controller, decision_manager=decision_manager,
        game_log=game_log,
    )
    shooting_controller = ShootingController(
        obstacles=state.obstacles, game_log=game_log, dice_manager=dice_manager, turn_tracker=turn_tracker,
        all_tokens=state.tokens, movement_controller=movement_controller, terrain_areas=state.terrain_areas,
        decision_manager=decision_manager, greater_good=greater_good_controller, suppression=suppression_controller,
        ammo_runt=ammo_runt_controller,
        objectives=state.objectives, stealth_drones=stealth_drones_controller, waaagh=waaagh_controller,
        target_reactions=shooting_target_reactions, nova_charge=nova_charge_controller,
        fire_support=fire_support_controller, hand_of_asuryan=hand_of_asuryan_controller,
        guide=guide_controller, doom=doom_controller,
        whispering_web=whispering_web_controller,
    )
    # Rule 13.09 (Hidden): GreaterGoodController.eligible_targets() needs
    # last_ranged_attack_turn for its own is_detectable() check - can't be a
    # constructor dependency the other way around, since ShootingController
    # itself already depends on greater_good_controller (see its own
    # constructor call just above).
    greater_good_controller.shooting_controller = shooting_controller
    # Rule (Strike Team's Suppression Volley, user-supplied): "after this
    # unit has shot" - fires for every one of the unit's own (non-reactive)
    # Shooting-phase activations, not just ones a specific caller happens to
    # pass on_finished for (that's the separate, per-call _on_activation_finished).
    # Seer Council's Psychic Shield restricts what may be SELECTED as a target,
    # and its WHEN is just after a selection happened - so accepting it can make
    # that selection illegal and the attacker has to pick again. See
    # game/psychic_shield.py; a plain callback, like on_fall_back_finished.
    psychic_shield_controller.on_activated = shooting_controller.revalidate_target_selection
    # Seer Council's Fate Inescapable - proactive ("your Shooting phase", and the
    # unit must not have shot yet), so an ActionPanel button rather than a break
    # point, and it needs shooting_controller for that "has not shot" test.
    fate_inescapable_controller = FateInescapableController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, game_log=game_log, all_tokens=state.tokens,
    )
    shooting_controller.on_squad_finished_shooting.append(suppression_controller.offer_after_shooting)
    # The Falcon's Fire Support marks one unit it just hit - the same
    # "after this model has shot" moment Suppression Volley uses.
    shooting_controller.on_squad_finished_shooting.append(fire_support_controller.offer_after_shooting)
    # Asurmen's Tactical Acumen - the fourth consumer of this list, and the
    # one that does not care WHAT was hit, only that the unit shot.
    shooting_controller.on_squad_finished_shooting.append(tactical_acumen_controller.offer_after_shooting)
    # Lhykhis' Whispering Web - fifth consumer, and back to caring WHICH units
    # were hit, like Fire Support. Differs from it in scope: the mark benefits
    # every friendly AELDARI model, not just one transport's passengers.
    shooting_controller.on_squad_finished_shooting.append(whispering_web_controller.offer_after_shooting)
    explosives_controller = ExplosivesController(
        stratagem_controller, dice_manager, movement_controller=movement_controller, all_tokens=state.tokens,
        obstacles=state.obstacles, terrain_areas=state.terrain_areas, turn_tracker=turn_tracker, game_log=game_log,
    )
    # Retaliation Cadre's other stratagem, The Arro'kon Protocol - proactive
    # (your own Shooting phase, chosen by the active player), so unlike Stim
    # Injectors above it needs no DecisionManager hook: it's a plain
    # ActionPanel button for a human and an ai/agent_driver.py option for the
    # AI, exactly like Explosives. Built after shooting_controller because
    # its eligibility reuses that controller's own targeting probe - see
    # game/arrokon_protocol.py.
    # Retaliation Cadre's fourth stratagem, The Torchstar Gambit - a Normal
    # move in the Shooting phase, so it needs both controllers: shooting to
    # know the unit's attacks are resolved, movement to make the move. See
    # game/torchstar_gambit.py.
    torchstar_controller = TorchstarGambitController(
        stratagem_controller, movement_controller=movement_controller,
        shooting_controller=shooting_controller, all_tokens=state.tokens,
        turn_tracker=turn_tracker, game_log=game_log,
    )
    arrokon_controller = ArrokonProtocolController(
        stratagem_controller, shooting_controller=shooting_controller, movement_controller=movement_controller,
        all_tokens=state.tokens, turn_tracker=turn_tracker, game_log=game_log,
    )
    # The Starflare Ignition System Enhancement (user-supplied, 20 pts) - the
    # only Enhancement this engine implements. Takes just the GameState: it
    # both reads state.tokens (Engagement Range) and removes from it (the
    # withdrawal itself), and those must not be two separate references - see
    # game/starflare_ignition.py.
    starflare_controller = StarflareIgnitionController(state, game_log=game_log)
    deadly_demise_controller = DeadlyDemiseController(
        dice_manager, state.tokens, turn_tracker=turn_tracker, game_log=game_log,
    )
    # Retaliation Cadre's sixth stratagem, Fail-Safe Detonator - reactive, on
    # the destruction of a BATTLESUIT model that has Deadly Demise, so it hangs
    # off main.py's own dead-model loop. It resolves nothing itself: it only
    # chooses that ability's result and lets deadly_demise_controller run.
    # See game/fail_safe_detonator.py.
    fail_safe_controller = FailSafeDetonatorController(
        stratagem_controller, deadly_demise_controller=deadly_demise_controller,
        decision_manager=decision_manager, game_log=game_log,
    )
    setup_controller = SetupController(
        state, obstacles=state.obstacles, all_tokens=state.tokens, game_log=game_log,
        board_width_in=board.width_in, board_height_in=board.height_in,
    )
    # Rule 03.01's pre-game sequence. Built even when disabled (it just stays
    # IDLE) so every gate below can read it unconditionally.
    pregame_controller = PregameController(
        state, setup_controller, dice_manager, decision_manager,
        turn_tracker=turn_tracker, game_log=game_log,
        on_battle_start=lambda first_player: begin_battle(first_player),
    )
    ingress_controller = IngressController(
        setup_controller, state, state.tokens, game_log=game_log, turn_tracker=turn_tracker,
        board_width_in=board.width_in, board_height_in=board.height_in,
    )
    rapid_ingress_controller = RapidIngressController(
        stratagem_controller, state, turn_tracker=turn_tracker, game_log=game_log,
    )
    # Retaliation Cadre's third stratagem, The Shortened Blade - bought during a
    # Deep Strike arrival, so it hangs off ingress_controller (whose placement
    # rule it relaxes) and setup_controller (whose cached overlay mask it has to
    # invalidate). See game/shortened_blade.py.
    shortened_blade_controller = ShortenedBladeController(
        stratagem_controller, ingress_controller=ingress_controller, setup_controller=setup_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    )
    # See RapidIngressController.consume()/notify_placement_resolved()'s own
    # docstrings: without this, a Rapid-Ingress-chained Fire Overwatch offer
    # fired the instant a human dropped the reserves card, hijacking every
    # further click before the models could even be dragged apart.
    ingress_controller.on_ingress_resolved = rapid_ingress_controller.notify_placement_resolved
    homing_beacon_controller = HomingBeaconController(all_tokens=state.tokens, game_log=game_log)
    fire_overwatch_controller = FireOverwatchController(
        stratagem_controller, shooting_controller, all_tokens=state.tokens, turn_tracker=turn_tracker, game_log=game_log,
    )
    transport_controller = TransportController(
        setup_controller, state, state.tokens, movement_controller, ingress_controller, dice_manager,
        game_log=game_log, turn_tracker=turn_tracker, board_width_in=board.width_in, board_height_in=board.height_in,
    )
    firing_deck_controller = FiringDeckController(shooting_controller, transport_controller, game_log=game_log)
    reserves_panel = ReservesPanel()
    charge_controller = ChargeController(
        game_log=game_log, dice_manager=dice_manager, turn_tracker=turn_tracker,
        all_tokens=state.tokens, movement_controller=movement_controller, waaagh=waaagh_controller,
    )
    # Retaliation Cadre's fifth stratagem, Grav-Inhibitor Field - reactive, in
    # the OPPONENT's Charge phase, so it is offered through decision_manager
    # (which is also what makes it AI-resolvable with no extra wiring) and
    # hangs off charge_controller's declaration hook. See
    # game/grav_inhibitor_field.py for why the charge move is deferred behind
    # it rather than started alongside.
    grav_inhibitor_controller = GravInhibitorFieldController(
        stratagem_controller, dice_manager=dice_manager,
        battle_shock_controller=battle_shock_controller, decision_manager=decision_manager,
        turn_tracker=turn_tracker, game_log=game_log,
    )
    charge_controller.on_charge_declared = grav_inhibitor_controller.maybe_offer
    crushing_impact_controller = CrushingImpactController(
        stratagem_controller, dice_manager, charge_controller, all_tokens=state.tokens,
        turn_tracker=turn_tracker, game_log=game_log,
    )
    heroic_intervention_controller = HeroicInterventionController(
        stratagem_controller, charge_controller, movement_controller, decision_manager,
        all_tokens=state.tokens, turn_tracker=turn_tracker, game_log=game_log,
    )
    pile_in_controller = PileInController(
        game_log=game_log, turn_tracker=turn_tracker, all_tokens=state.tokens,
        movement_controller=movement_controller,
    )
    fight_controller = FightController(
        game_log=game_log, dice_manager=dice_manager, turn_tracker=turn_tracker, all_tokens=state.tokens,
        pile_in_controller=pile_in_controller, charge_controller=charge_controller, decision_manager=decision_manager,
        suppression=suppression_controller, stealth_drones=stealth_drones_controller, waaagh=waaagh_controller,
        target_reactions=fight_target_reactions,
        # Both psychic marks say "makes an attack", not "makes a ranged attack",
        # so they are read here as well as in the Shooting phase. Guide was
        # wired into fight.py's _hit_modifiers() when the Farseer was added but
        # never actually passed in here, so its melee half was dead - caught by
        # Doom needing the same seam.
        guide=guide_controller, doom=doom_controller,
        whispering_web=whispering_web_controller,
    )
    # War Horde's 'Ere We Go - proactive (start of your own Movement phase),
    # so like Unbridled Carnage it needs no DecisionManager hook: an
    # ActionPanel button for a human, and a deterministic call for the AI (see
    # ai/agent_driver.py's _handle_ere_we_go()). Needs movement_controller for
    # its "start of the phase" check - see game/ere_we_go.py.
    ere_we_go_controller = EreWeGoController(
        stratagem_controller, movement_controller=movement_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    )
    # Warp Spiders' Flickerjump - a datasheet ability, not a stratagem, so no
    # CP and no 15.01 ledger. Offered as an ActionPanel button above "Move",
    # for the same reason 'Ere We Go's is: the Move characteristic is read once
    # when the move starts. Aeldari is human-only, so there is no AI path.
    flickerjump_controller = FlickerjumpController(
        turn_tracker=turn_tracker, movement_controller=movement_controller,
        dice_manager=dice_manager, game_log=game_log,
    )
    epic_challenge_controller = EpicChallengeController(
        stratagem_controller, fight_controller, turn_tracker=turn_tracker, game_log=game_log,
    )
    # Aeldari army rule Battle Focus - its own token account, not CP, and not
    # the 15.01 ledger (see game/battle_focus.py for why those are two
    # different shapes). Human-only faction, so there is deliberately no
    # ai/agent_driver.py path. The squads provider lets it work out whose army
    # is ASURYANI on its own, which is the only thing that survives the
    # pre-game sequence: at this point nothing is on the board yet.
    battle_focus_pool = battle_focus.BattleFocusPool(
        battle_size=config.BATTLE_SIZE, game_log=game_log,
        movement_controller=movement_controller,
        turn_tracker=turn_tracker, dice_manager=dice_manager,
        decision_manager=decision_manager, fight_controller=fight_controller,
        all_tokens=state.tokens,
        squads_provider=lambda: (
            _player_squads(state, "Player 1") + _player_squads(state, "Player 2")
        ),
    )
    # The two reactive Agile Manoeuvres fire in the OPPONENT's turn, from two
    # triggers that already existed. Fade Back rides the same
    # "squad finished shooting, here is what it hit" callback Suppression
    # Volley uses - which is why that one is now a list. Opportunity Seized
    # needed a new hook, fired at the very end of confirm_move() so the fall
    # back is fully settled before the other player gets a break point.
    shooting_controller.on_squad_finished_shooting.append(battle_focus_pool.offer_fade_back)
    movement_controller.on_fall_back_finished = battle_focus_pool.offer_opportunity_seized
    # Seer Council's Isha's Fury: "just after an enemy unit ends a Normal,
    # Advance or Fall Back move" - broader than the Fall-Back-only hook above,
    # and fired at the same point for the same reason.
    movement_controller.on_move_finished = ishas_fury_controller.offer_after_move
    # Aeldari Seer Council detachment rule Strands of Fate: a Fate dice pool
    # rolled ONCE for the whole battle, where each die's FACE decides which one
    # stratagem it can discount. Plugged into the same cost-discount hook
    # Puretide's Teachings uses, so StratagemController never learns this rule
    # exists. Whose army has the detachment is a setting, not a derivation -
    # see config.SEER_COUNCIL_PLAYERS.
    fate_dice_pool = strands_of_fate.FateDicePool(game_log=game_log)
    stratagem_controller.cost_discounts.append(fate_dice_pool)
    # War Horde's Unbridled Carnage - proactive (Fight phase, bought before a
    # unit is selected to fight), so like The Arro'kon Protocol it needs no
    # DecisionManager hook: a plain ActionPanel button for a human, and a
    # deterministic call for the AI (see ai/agent_driver.py's
    # _unbridled_carnage_verdict()). Built after fight_controller because its
    # eligibility reads that controller's own rule 12.04 answer - see
    # game/unbridled_carnage.py.
    unbridled_carnage_controller = UnbridledCarnageController(
        stratagem_controller, fight_controller=fight_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    )
    # The Twin Lance's Retro-thrusters - built after fight_controller because
    # its "was eligible to fight this phase" latch reads that controller's own
    # rule 12.04 answer; see game/retro_thrusters.py.
    retro_thrusters_controller = RetroThrustersController(
        fight_controller=fight_controller, movement_controller=movement_controller,
        turn_tracker=turn_tracker, all_tokens=state.tokens, game_log=game_log,
    )
    neocapacitor_controller.battle_shock = battle_shock_controller
    counteroffensive_controller = CounteroffensiveController(
        stratagem_controller, fight_controller, all_tokens=state.tokens, turn_tracker=turn_tracker, game_log=game_log,
    )
    # Rule 15.12: fight_controller can't take a CounteroffensiveController
    # constructor dependency (this controller needs a FightController
    # reference itself) - wired as a plain callback instead.
    fight_controller.on_unit_finished_fighting = lambda squad: counteroffensive_controller.offer_after(squad, decision_manager)
    consolidate_controller = ConsolidateController(
        game_log=game_log, turn_tracker=turn_tracker, all_tokens=state.tokens,
        movement_controller=movement_controller, fight_controller=fight_controller, objectives=state.objectives,
    )
    coherency_enforcer = CoherencyEnforcer(all_tokens=state.tokens, game_log=game_log)
    renderer = Renderer(render_scale=config.RENDER_SUPERSAMPLE)
    action_panel = ActionPanel()
    game_status_panel = GameStatusPanel()
    mission_cards_overlay = MissionCardsOverlay()
    log_panel = LogPanel()
    dice_panel = DicePanel()
    decision_overlay = DecisionOverlay()
    stratagem_notice_overlay = StratagemNoticeOverlay()
    waaagh_notice_overlay = WaaaghNoticeOverlay()
    turn_start_overlay = TurnStartOverlay()
    turn_plan_overlay = TurnPlanOverlay()
    # User: "immer wenn die KI ein Stratagem benutzt will ich ein prompt
    # haben... das ich wegklicken muss" - only when the ACTING player is
    # Player 2 (the AI); a human already knows when they themselves spend a
    # Stratagem, they just clicked its button.
    stratagem_controller.on_stratagem_used = (
        lambda player, stratagem: stratagem_notice_overlay.enqueue(player, stratagem) if player == "Player 2" else None
    )
    # User: "ich will außerdem, dass ein prompt erscheint, das ich weg
    # klicken muss, wenn ein waagh ausgerufen wird" - same "only for the AI"
    # reasoning as the Stratagem notice above (no UI button exists yet for
    # a human to call one themselves, so this is Player 2-only in practice
    # today, but the check is here for when that changes).
    waaagh_controller.on_called = (
        lambda player: waaagh_notice_overlay.enqueue(player) if player == "Player 2" else None
    )
    player_banner = PlayerBanner()
    unit_datacard = UnitDatacardOverlay()
    agent = ClaudeAgent(model=config.AI_MODEL, planning_model=config.AI_PLANNING_MODEL)  # swap for MockAgent() for a free/offline smoke test
    ai_memory = AIMemory()
    last_shown_turn_plan = None  # object identity of the AIMemory.turn_plan last shown via turn_plan_overlay - see run_ai_action()
    thinking_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 10, bold=True)
    auto_play_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
    clock = pygame.time.Clock()

    # Cache for the "visible to the selected model" highlight: has_line_of_sight
    # is expensive (a sample_points^2 sweep per token pair, PLUS an O(all
    # tokens) blocking-model scan inside every single one of those calls -
    # see line_of_sight.py's _blocking_models()), and recomputing it for
    # every token on the board every single frame made dragging feel
    # sluggish - worse still with a full army's worth of models on the
    # board (User-Report: laggy movement at ~130 models) than with the
    # smaller old demo scene. Skip the recompute unless the anchor actually
    # moved (rounded to avoid re-triggering on floating-point noise) or the
    # token set changed.
    visibility_cache = {"key": None, "result": set()}
    VISIBILITY_SAMPLE_POINTS = 6  # cosmetic highlight only - full precision isn't needed here
    # User-request (follow-up after the enemies-only filter above still felt
    # laggy at ~130 models): trade responsiveness for raw check count during
    # a drag - snapping the anchor's position to a coarse 0.5" grid before
    # building the cache key means the highlight only recomputes once the
    # dragged model has moved a noticeable distance, not on every pixel of
    # mouse movement, at the cost of the highlight visibly "stepping"
    # instead of updating continuously while dragging.
    VISIBILITY_RECOMPUTE_STEP_IN = 0.5

    def _visibility_grid_snap(value):
        return round(value / VISIBILITY_RECOMPUTE_STEP_IN) * VISIBILITY_RECOMPUTE_STEP_IN

    # Cache for the "valid shooting targets" set: valid_target_models() runs a
    # full-precision has_line_of_sight() (now also checking obscuring terrain
    # areas) per candidate model+weapon pair - with nothing actually moving
    # while a player is just choosing a shooting type/target, recomputing it
    # every frame (for the board highlight) *and* on every click attempt (to
    # validate it) is pure waste. get_shoot_targets() is used by both the
    # render loop and the click handlers below, so a click never re-triggers
    # the expensive path unless the shooting state actually changed since the
    # last frame's render.
    shoot_targets_cache = {"key": None, "result": set()}

    def get_shoot_targets():
        current_assignment = (
            shooting_controller.assignment_queue[0]
            if shooting_controller.state == shooting.ASSIGNING and shooting_controller.assignment_queue
            else None
        )
        key = (
            shooting_controller.state, shooting_controller.active_squad, shooting_controller.shooting_type,
            shooting_controller.split_fire, current_assignment, shooting_controller.target_squad, len(state.tokens),
        )
        if key != shoot_targets_cache["key"]:
            # User report: it takes a noticeable moment after clicking a squad
            # in the Shooting phase before anything can be done - that's this
            # recompute (valid_target_models() does a full has_line_of_sight()
            # sweep per enemy squad, see _squad_qualifies()'s docstring) running
            # synchronously with nothing on screen to explain the pause. Only
            # CHOOSING_TARGET/ASSIGNING actually do that expensive work (every
            # other state falls through to a plain `set()` in
            # valid_target_models() - see its final `return set()`), so the
            # overlay only flashes for the states where there's really
            # something worth waiting for, not on every trivial cache miss.
            if shooting_controller.state in (shooting.CHOOSING_TARGET, shooting.ASSIGNING):
                show_loading_overlay("Calculating valid targets...")
            shoot_targets_cache["key"] = key
            shoot_targets_cache["result"] = shooting_controller.valid_target_models(state.tokens)
        return shoot_targets_cache["result"]

    # Cache for "For The Greater Good"'s Mark Spotted Target board highlight
    # (rule, game/greater_good.py): GreaterGoodController.eligible_targets()
    # does a full has_line_of_sight() sweep between every one of the acting
    # squad's models and every model of every enemy squad on the board, with
    # no caching of its own - unlike get_shoot_targets() above, nothing
    # guarded this from being recomputed both every single rendered frame
    # AND a second time on every click attempt while the "Mark Spotted
    # Target" screen was up. Real user report ("the game crashed when I
    # clicked Mark Spotted Target with the Stealth Battlesuits" - actually a
    # multi-second-per-frame freeze, not a crash, on this scene's ~130-model
    # board): measured ~0.8s per eligible_targets() call in an equivalent
    # stress scenario - at that cost per frame the game is all but frozen
    # for as long as the screen stays open. Same fix as get_shoot_targets():
    # one cached computation per actual state change, shared between
    # rendering and click validation.
    greater_good_targets_cache = {"key": None, "result": set()}

    def get_greater_good_eligible_squads():
        """The set of enemy Squads eligible_targets() would return right
        now, membership-testable in O(1) via `squad in ...` - mirrors
        eligible_targets()'s own return value, just cached and as a set
        instead of a list."""
        key = (greater_good_controller.state, greater_good_controller.acting_squad, len(state.tokens))
        if key != greater_good_targets_cache["key"]:
            greater_good_targets_cache["key"] = key
            if greater_good_controller.state == greater_good.CHOOSING_TARGET:
                # Same "explain the pause" fix as get_shoot_targets() above -
                # eligible_targets() does its own full has_line_of_sight()
                # sweep (measured ~0.8s on this scene's board, see its own
                # comment further up).
                show_loading_overlay("Calculating valid targets...")
                greater_good_targets_cache["result"] = set(
                    greater_good_controller.eligible_targets(greater_good_controller.acting_squad)
                )
            else:
                greater_good_targets_cache["result"] = set()
        return greater_good_targets_cache["result"]

    # Same caching fix as get_greater_good_eligible_squads() above, for the
    # same reason: FireOverwatchController.eligible_squads() (redesigned
    # from a DecisionManager text-button list into this board-click-a-unit
    # screen - see that module's docstring) calls ShootingController.
    # has_valid_target() per candidate squad, itself a full LOS/range sweep
    # - uncached, that would re-run every rendered frame the screen stays
    # open AND a second time per click attempt.
    fire_overwatch_targets_cache = {"key": None, "result": set()}

    def get_fire_overwatch_eligible_squads():
        key = (fire_overwatch_controller.state, fire_overwatch_controller.player, len(state.tokens))
        if key != fire_overwatch_targets_cache["key"]:
            fire_overwatch_targets_cache["key"] = key
            if fire_overwatch_controller.state == overwatch.CHOOSING_UNIT:
                show_loading_overlay("Calculating valid targets...")
                fire_overwatch_targets_cache["result"] = set(fire_overwatch_controller.eligible_squads())
            else:
                fire_overwatch_targets_cache["result"] = set()
        return fire_overwatch_targets_cache["result"]

    def begin_battle(first_player):
        """Everything the battle proper needs once rule 03.01's pre-game
        sequence has finished and Determine First Turn has an answer.

        In the legacy (no-pre-game) path this same work happens inline at
        construction time - see the `if turn_tracker.started` block above."""
        # SetupController.confirm_setup() sets set_up_this_turn on EVERY unit
        # it places (rule 18.02), and nothing clears it until the end of a
        # turn. Deployment places the entire army through that path, so
        # without this the whole army would spend battle round 1 unable to
        # embark (game/transport.py) and stripped of the [HEAVY] hit bonus
        # (rule 24.16, game/shooting.py).
        for owner in ("Player 1", "Player 2"):
            for squad in _player_squads(state, owner):
                squad.set_up_this_turn = False

        turn_tracker.start_battle(first_player)

        # Battle round 1's tokens. advance_turn_phase() would hand them out at
        # the first phase change anyway (sync_battle_round() is idempotent),
        # but that is one phase late, and this is the moment the armies are
        # complete - the same reason the points lines below are logged here.
        battle_focus_pool.sync_battle_round(turn_tracker.battle_round)
        fate_dice_pool.sync_battle_round(turn_tracker.battle_round)

        # Logged here rather than at construction because _player_squads()
        # walks tokens + embarked_squads + reserves, and with a pre-game all
        # three are still empty when the log file is opened. This is also the
        # more accurate moment: it reports the reserve split the players
        # actually declared.
        for owner in ("Player 1", "Player 2"):
            game_log.add(_army_points_line(state, owner))
            for line in _attached_unit_lines(state, owner):
                game_log.add(line)
            for line in _enhancement_lines(state, owner):
                game_log.add(line)

        # Rule 08.02 plus the "the battle's very first phase is already
        # Command" case: advance_turn_phase() never runs for it, so Primary
        # scoring would otherwise miss whatever deployment is already standing
        # on an objective.
        command_points.gain_core_cp()
        for objective in state.objectives:
            objective.update_control(state.tokens)
        mission_controller.score_primary(state.objectives, turn_tracker.active_player)

    def advance_turn_phase():
        # Rule 15.07 (Rapid Ingress): any pending offer from a PREVIOUS
        # Movement-phase-end has now had its one phase's window to be
        # dragged onto the board - forfeit it before possibly opening a
        # new one below.
        rapid_ingress_controller.expire_if_unused()
        phase_before = turn_tracker.phase
        # turn_owner, not active_player: the latter is a transient "whose
        # decision is this right now" flag (flipped by e.g. a defending
        # save roll or a reactive Stratagem's decision window) that isn't
        # guaranteed to still equal the actual player whose phase is ending
        # right now - same bug class already fixed in ai/agent_driver.py's
        # _is_blocked()/main.py's ai_advance_phase() (see their own
        # comments). Everything below that means "the player whose turn
        # this phase-transition actually belongs to" (Fieldcraft, the Fights
        # First/set-up/charge-lock/fell-back resets, secondary mission
        # scoring, and the Rapid Ingress/Fire Overwatch/Heroic Intervention
        # reactive offers further down) needs that stable value, not
        # whatever active_player happens to be at this exact instant.
        mover_before = turn_tracker.turn_owner
        ending_player = turn_tracker.turn_owner if turn_tracker.is_last_phase else None
        battle_round_before = turn_tracker.battle_round
        # Kroot Carnivores' Fieldcraft ability (user-supplied): "at the end
        # of your Command phase" literally means only that one phase - but
        # checking ONLY there missed the overwhelmingly common case (bug
        # report: "Kroot secured the central objective, got shot off it, but
        # it should still have been mine"): a unit usually reaches/starts
        # controlling an objective mid-turn (its own Movement/Shooting/
        # Charge/Fight phase), i.e. AFTER that round's one Command-phase
        # checkpoint has already passed - so it never got armed before the
        # opponent's very next turn could kill it. Checked at the end of
        # EVERY phase of the unit owner's own turn instead (mover_before is
        # stable across all 5 of one player's phases, so this still never
        # fires during the opponent's phases) - the moment the unit takes
        # and holds an objective through any point in its controller's own
        # turn, it's secured before the opponent gets a turn to contest it.
        # Checked (and, if it applies, secured) BEFORE the Level of Control
        # recompute below, so the same recomputation that closes out this
        # phase already honors it.
        apply_fieldcraft(state.objectives, state.tokens, mover_before)
        turn_tracker.advance_phase()
        # Rule 14.02: Level of Control is recomputed "at the end of each
        # phase and turn" - advancing IS that boundary.
        for objective in state.objectives:
            objective.update_control(state.tokens)
        # Diagnostic only (file-only, debounced - see game/coherency.py's
        # log_coherency_state()): a unit that enters a phase already out of
        # coherency behaves differently everywhere downstream (ai/agent_
        # driver.py's charge/pile-in rollback measures against that inherited
        # baseline rather than against zero, and end of turn it costs models)
        # - but nothing said so, which left "it should have regained
        # coherency and didn't" to be read out of raw coordinates. Both
        # players, because either army can be the one standing broken.
        for side in dict.fromkeys((mover_before, turn_tracker.turn_owner)):
            coherency_enforcer.log_state(side, f"entering the {turn_tracker.phase} phase")
        # Rule 15.01: both "not the same stratagem twice" and "not the same
        # unit targeted twice" reset every phase - stratagems can be used in
        # any phase, so this isn't gated to one specific phase like the
        # other reset_*_phase() calls below.
        stratagem_controller.reset_phase()
        # Seer Council: three "until the end of the phase" grants plus the two
        # reactive controllers' own once-per-pair memos. Reset unconditionally on
        # every phase change, like stratagem_controller itself.
        _seer_squads = {t.squad for t in state.tokens if t.squad is not None}
        forewarned_mod.reset_phase(_seer_squads)
        psychic_shield_mod.reset_phase(_seer_squads)
        fate_inescapable_mod.reset_phase(_seer_squads)
        forewarned_controller.reset_phase()
        psychic_shield_controller.reset_phase()
        # Fail-Safe Detonator's "already asked about this unit" memo is scoped
        # to a phase, like the 15.01 bookkeeping right above it.
        fail_safe_controller.reset_phase()
        # Retaliation Cadre's Stim Injectors: "until the end of the phase".
        # Expired here, next to the 15.01 bookkeeping it runs out with, and for
        # BOTH armies - the Fight phase is shared (12.04), so either side can
        # be holding the grant when a phase ends.
        stim_injectors_controller.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        # War Horde's 'Ard as Nails: likewise "until the end of the phase",
        # and it also clears its own per-attack de-duplication here.
        ard_as_nails_controller.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        # The Arro'kon Protocol: likewise "until the end of the phase", and
        # expired in the same place for the same reason.
        arrokon_controller.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        # Asurmen's Hand of Asuryan grant is "until the end of the phase" too.
        # The once-per-battle SPEND is deliberately not reset here - two
        # lifetimes, see game/hand_of_asuryan.py.
        hand_of_asuryan.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        # Jain Zar's Whirling Death grants its +6" Move "until the end of the
        # phase" too.
        whirling_death.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        # Warlock Conclave's Psychic Communion is likewise "until the end of
        # the phase", and is stored per MODEL rather than per squad.
        psychic_communion.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        # The Farseer's Branching Fates is "once per phase".
        branching_fates.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        # Aeldari Battle Focus: both per-phase restrictions ("this unit has
        # already performed an Agile Manoeuvre", "this manoeuvre has already
        # been triggered") plus Swift as the Wind's own "until the end of the
        # phase" grant. Then the round accounting: sync_battle_round() is
        # idempotent, so calling it on every phase change is what guarantees
        # the grant/expiry never depends on catching one exact moment.
        battle_focus_pool.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        battle_focus_pool.sync_battle_round(turn_tracker.battle_round)
        # Strands of Fate rolls its pool at the start of the FIRST battle round
        # and never again - nothing refills a Fate dice pool, so this call goes
        # inert after the first time rather than refreshing anything. No
        # reset_phase() counterpart for the same reason: the dice are the whole
        # state, and they last the battle.
        fate_dice_pool.sync_battle_round(turn_tracker.battle_round)
        # War Horde's Unbridled Carnage: likewise "until the end of the phase",
        # and expired in the same place for the same reason.
        unbridled_carnage_controller.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        # Riptide's Nova Charge: the [DEVASTATING WOUNDS] grant is likewise
        # "until the end of the phase". Its once-per-BATTLE counter lives in
        # the controller and is deliberately not touched here - a spent use
        # stays spent.
        nova_charge_controller.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        # Kill Rig's Spirit of Gork: "until the end of the phase".
        spirit_of_gork_controller.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        # Flash Gitz' Ammo Runt: same "until the end of the phase" grant. Its
        # once-per-BATTLE record is deliberately not touched here.
        ammo_runt_controller.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        if ending_player is not None:
            # Rule 11.04: "Until the end of the turn" - Fights First from a
            # charge made this turn expires once the turn actually ends.
            # Rules 18.02/18.04/18.05: "not set up this turn" and the
            # Rapid/Combat/Emergency Disembark no-charge lock are likewise
            # this-turn-only.
            ending_squads = {t.squad for t in state.tokens if t.squad is not None and t.squad.owner == ending_player}
            # War Horde's 'Ere We Go: "until the end of the turn", the same
            # lifetime as the three flags cleared in the loop right below.
            ere_we_go_controller.expire_for_turn(ending_squads)
            # Warp Spiders' Flickerjump grants its 24" Move "until the end of
            # the turn" too. Its other half (no charge) rides on
            # charge_locked_until_end_of_turn, cleared in the loop right below.
            flickerjump_controller.expire_for_turn(ending_squads)
            # Fire Support's mark is "until the end of the turn" too. Not
            # per-squad, so it takes no ending_squads: the mark belongs to
            # a Falcon token, not to the units that benefit from it.
            fire_support_controller.reset_turn()
            # Whispering Web's mark is "until the end of the turn" as well, and
            # likewise not per-squad: it is held per player, because every
            # friendly AELDARI unit reads it.
            whispering_web_controller.reset_turn()
            # The Twin Lance's Neocapacitor Shields: likewise "until the end
            # of the turn", and on the turn-taker's own units (the ones that
            # would have been charging), so ending_squads is exactly right.
            neocapacitor_shields.expire_for_turn(ending_squads)
            # Aeldari Battle Focus: Star Engines and Flitting Shadows are both
            # "until the end of the turn". ending_squads is right for the same
            # reason - only the turn-taker can trigger either of them, both
            # being their own Movement phase manoeuvres.
            battle_focus_pool.expire_for_turn(ending_squads)
            for squad in ending_squads:
                squad.fights_first = False
                squad.charged_this_turn = False  # rule 11.04's own marker, see Squad.charged_this_turn
                squad.set_up_this_turn = False
                squad.charge_locked_until_end_of_turn = False
                squad.fell_back_this_turn = False  # rule 09.07: "until the end of the turn"
            # Secondary mission ("No Mercy", user-supplied): 1 point per
            # enemy unit destroyed, scored at the end of the destroying
            # player's own turn - see MissionController.record_destroyed_squad()
            # for when a kill actually gets queued (the dead-model-removal
            # loop below).
            mission_controller.score_secondary_end_of_turn(ending_player)
            # Starflare Ignition System Enhancement (user-supplied, 20 pts):
            # WHEN is "at the end of your opponent's turn" - this IS that
            # instant, and offer() sends the prompt to whoever is NOT
            # ending_player. Optional ("you can"), so it goes through
            # decision_manager rather than firing automatically; see
            # game/starflare_ignition.py for the one ordering deviation that
            # asynchronous resolution costs here (this same call also opens
            # the next player's Command phase, Primary scoring included).
            starflare_controller.offer(ending_player, decision_manager)
        if turn_tracker.phase == PHASE_COMMAND:
            command_points.gain_core_cp()
            battle_shock_controller.reset_command_phase()
            # Primary mission ("Hold the Line", user-supplied): 3 points per
            # objective controlled at the start of your own Command phase -
            # objective.controlled_by was already recomputed for this exact
            # boundary a few lines up.
            mission_controller.score_primary(state.objectives, turn_tracker.active_player)
            # Strike Team's DS8 Support Turret ability (user-supplied):
            # "until the start of your next turn" - this IS that instant,
            # for the player whose turn is beginning.
            support_turret_controller.expire_for(turn_tracker.active_player)
            # Trukk's Grot Riggers ability (user-supplied): "at the start
            # of your Command phase" - same instant, same active-player
            # argument as the Support Turret expiry right above.
            apply_grot_riggers(state.tokens, turn_tracker.active_player)
            # Orks army rule "Waaagh!" (user-supplied): "until the start of
            # your next Command phase" - same instant/argument again. Must
            # run BEFORE the player is offered a chance to call a fresh one
            # this same Command phase (see the "Call Waaagh!" button/AI
            # policy further down) - expiring first, then calling, is what
            # makes "start of your next Command phase" a real boundary
            # instead of a Waaagh! call immediately cancelling itself.
            waaagh_controller.expire_for(turn_tracker.active_player)
            # The Farseer's Guide: "until the start of YOUR next Command
            # phase" - so it ends here, for the player whose Command phase
            # this is, rather than in the end-of-turn block with every other
            # duration. That is also where its "once per turn" resets.
            guide_controller.start_of_command_phase(turn_tracker.turn_owner)
            # Eldrad Ulthran's Doom: the same duration, so the same instant.
            doom_controller.start_of_command_phase(turn_tracker.turn_owner)
            # Eldrad Ulthran's Diviner of Futures: "at the start of your
            # Command phase, if this model is on the battlefield, you gain
            # 1CP" - this IS that instant. Grants 0 without complaint if he
            # is not on the board, or if this round's bonus-CP cap is spent.
            diviner_controller.start_of_command_phase(turn_tracker.turn_owner)
            # Painboy's Grot Orderly (user-supplied): "once per battle, in
            # your Command phase". Offered to the phase's own turn owner
            # only, like every other start-of-phase effect here.
            grot_orderly_controller.offer_at_command_phase(
                [
                    sq for sq in {t.squad for t in state.tokens if t.squad is not None}
                    if sq.owner == turn_tracker.turn_owner and unit_has_grot_orderly(sq)
                ],
                turn_tracker,
            )
        if turn_tracker.phase == PHASE_MOVEMENT:
            movement_controller.reset_movement_phase()
            ingress_controller.reset_movement_phase()
            transport_controller.reset_movement_phase()
            # Gretchin's Thievin' Scavengers ability (user-supplied): "at
            # the start of your Movement phase" - this IS that instant, for
            # the player whose turn is beginning (same active_player
            # argument as every other phase-start trigger above).
            thievin_scavengers_controller.start_check(turn_tracker.active_player)
        if turn_tracker.phase == PHASE_SHOOTING:
            shooting_controller.reset_shooting_phase()
        if turn_tracker.phase == PHASE_CHARGE:
            charge_controller.reset_charge_phase()
            # The Twin Lance's Neocapacitor Shields: "at the start of your
            # opponent's Charge phase" - offered to whoever is NOT taking
            # this turn (see game/neocapacitor_shields.py).
            neocapacitor_controller.offer_at_charge_phase_start(turn_tracker.active_player)
            # Rule 20.04: "not eligible to make any other type of move
            # until the start of the next Charge phase" - we just reached it.
            for squad in {t.squad for t in state.tokens if t.squad is not None}:
                squad.ingress_locked = False
        if turn_tracker.phase == PHASE_FIGHT:
            retro_thrusters_controller.reset_fight_phase()
            # Kill Rig's Spirit of Gork: "at the start of the Fight phase".
            # Offered for the phase's own turn owner only - the ability
            # belongs to its controller's turn, like every other
            # start-of-phase effect here.
            spirit_of_gork_controller.start_of_fight_phase([
                sq for sq in {t.squad for t in state.tokens if t.squad is not None}
                if sq.owner == turn_tracker.turn_owner and unit_has_spirit_of_gork(sq)
            ])
            pile_in_controller.reset_fight_phase()
            fight_controller.reset_fight_phase()
            consolidate_controller.reset_fight_phase()
            epic_challenge_controller.reset_fight_phase()
        # Rule 20.03: "At the end of the third battle round... all
        # strategic reserves units that have not made one or more ingress
        # moves are destroyed."
        if turn_tracker.battle_round == battle_round_before + 1 and battle_round_before == 3:
            ingress_controller.destroy_remaining_reserves()
        # T'au "For The Greater Good" army rule (user-supplied): Spotted/
        # Observer status is "until the end of the phase" - the phase that
        # just ended (phase_before), not whichever phase happens to be
        # PHASE_SHOOTING next. Real user report: "der Status war in meinem
        # Zug immer noch an meinen Modellen" - this used to reset on
        # `turn_tracker.phase == PHASE_SHOOTING` (entering the NEXT Shooting
        # phase) instead, which - since only one player's Shooting phase
        # happens per turn - left a Spotted mark hanging around for the
        # OPPONENT's entire following turn (Command/Movement/etc.) until
        # the marking player's own next Shooting phase finally rolled
        # around, a full round later, instead of clearing the instant the
        # Shooting phase that created it actually ended.
        if phase_before == PHASE_SHOOTING:
            greater_good_controller.reset_shooting_phase()
        # Rules 15.07/15.08 (Rapid Ingress / Fire Overwatch): WHEN is "end
        # of your opponent's Movement phase" - `phase_before` is whichever
        # phase we just left, so this only fires the instant Movement
        # itself ends, offering mover_before's OPPONENT both reactive
        # stratagems in turn. Chained via on_resolved rather than two
        # independent calls: both react to this same instant, and showing
        # Rapid Ingress's decision-overlay choice and Fire Overwatch's
        # board-click-a-unit screen at once would be confusing - so Fire
        # Overwatch is only offered once Rapid Ingress's own decision
        # (accept, decline, or "nothing was eligible") has resolved. Fire
        # Overwatch itself no longer takes decision_manager (see game/
        # overwatch.py's redesign) - it's its own board-click-driven state
        # now, not a DecisionManager text-button list.
        if phase_before == PHASE_MOVEMENT:
            # The Farseer's Guide: "at the end of your Movement phase, select
            # one enemy unit". Before the Flickerjump roll below for the same
            # reason that one goes before Rapid Ingress - a decision already
            # taken owes its dice first, and this is a new decision.
            guide_controller.offer_at_end_of_movement(
                mover_before, {t.squad for t in state.tokens if t.squad is not None},
            )
            # Eldrad Ulthran's Doom: same trigger, same instant. Two separate
            # offers rather than one combined prompt - they are two abilities
            # with two independent marks, and a player owning both should be
            # able to point them at different units.
            doom_controller.offer_at_end_of_movement(
                mover_before, {t.squad for t in state.tokens if t.squad is not None},
            )
            # Warp Spiders' Flickerjump: "at the end of the phase, roll one D6
            # for each model in this unit". Before the Rapid Ingress offer
            # below because DiceManager holds a single pending roll and this
            # one is owed by a decision already taken, where that offer is a
            # new decision still to be made.
            flickerjump_controller.end_of_phase()
            rapid_ingress_controller.offer(
                mover_before, decision_manager,
                on_resolved=lambda: fire_overwatch_controller.offer(mover_before),
                homing_beacon_controller=homing_beacon_controller,
            )
        # Rule 15.11 (Heroic Intervention): WHEN is "end of your opponent's
        # Charge phase" - a separate instant from Movement's, so no
        # chaining needed against the pair above (see
        # HeroicInterventionController's docstring).
        if phase_before == PHASE_CHARGE:
            heroic_intervention_controller.offer(mover_before, decision_manager)

    dragging_reserve_squad = None  # rule 03.02: squad being dragged from the Reserves panel onto the board

    def show_loading_overlay(message):
        """Same look as show_thinking_overlay()'s full-window branch below,
        but for a synchronous ENGINE computation (line-of-sight/valid-target
        sweeps) rather than a Claude API call - flashed right before a cache
        miss is about to run one of those expensive sweeps (see
        get_shoot_targets()/get_greater_good_eligible_squads() above), so the
        window shows *something* instead of just sitting there for the
        fraction of a second to ~1s the sweep can take on a full board."""
        overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))
        text_surf = thinking_font.render(message, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(window_width // 2, window_height // 2))
        screen.blit(text_surf, text_rect)
        pygame.display.flip()

    def show_thinking_overlay():
        """Flashed just before ai/agent_driver.py calls agent.decide() - a
        real Claude round-trip takes a couple of seconds, during which the
        whole loop is blocked (it's a synchronous network call), so without
        this the window would just look frozen.

        User report + screenshot: the full-window dark overlay (designed for
        "picking a squad action", where nothing else is on screen yet) reads
        as confusing/overlapping when ai/agent_driver.py's
        _maybe_command_reroll() is what's asking - that one deliberately
        fires WHILE a dice roll is already visible and awaiting
        acknowledgement (rule 15.02 has to react to the roll before it's
        confirmed), so dimming/covering that roll while also displaying a
        generic "thinking" message reads as two unrelated, conflicting
        prompts at once instead of one coherent "Claude is looking at this
        roll" moment. When a roll is pending, use the same small corner
        badge as the "AUTO-PLAY" indicator instead - leaves the roll fully
        legible and names what's actually being decided."""
        if dice_manager.is_pending:
            badge_surf = auto_play_font.render("Claude is considering a Command Re-roll...", True, (20, 20, 20))
            badge_rect = badge_surf.get_rect(topleft=(config.LEFT_PANEL_WIDTH + 12, 12))
            pygame.draw.rect(screen, (255, 210, 90), badge_rect.inflate(16, 10), border_radius=6)
            screen.blit(badge_surf, badge_rect)
        else:
            overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            text_surf = thinking_font.render("Claude is thinking...", True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(window_width // 2, window_height // 2))
            screen.blit(text_surf, text_rect)
        pygame.display.flip()

    def _any_pending_damage_choice():
        """Whether any controller is currently waiting for the HUMAN
        (clicking which of THEIR OWN models takes a wound/mortal wound -
        see renderer.draw_damage_choice_highlight()'s call sites below for
        the full list) to pick a model on the board.

        User report: removing a model this way used to sometimes "hang" -
        the click resolves the choice, but the AI (ai_auto_play) can still
        fire its next action in that very same frame, before this frame's
        own render call ever shows the model actually gone (same underlying
        race as ai_action_paused_this_frame's other cases, just reached via
        a board click instead of an overlay button). Snapshotting this at
        the very top of the loop - BEFORE this frame's events are processed -
        and using that snapshot (not a fresh re-check afterward) to seed
        ai_action_paused_this_frame is what makes the AI wait the one frame
        needed: a choice that was already pending before this frame stays
        "paused" for this frame even if a click just resolved it, so the
        render always gets to catch up first.

        Real, severe regression found via user report ("die KI entfernt
        selbstaendig keine getoeteten Modelle mehr... ich muss es quasi fuer
        die KI machen"): this used to count EVERY controller's pending
        choice, including Player 2's own (e.g. Player 1 shoots one of the
        AI's squads, the resulting save-fail damage allocation belongs to
        Player 2 - see _resolve_own_damage_choice() in ai/agent_driver.py,
        the ONLY thing that ever resolves it, since there's no human click
        path for the AI's own models at all). DicePanel.is_busy stays True
        for PANEL_SLIDE_OUT_DURATION (~0.18s, several frames) right as that
        choice becomes pending - run_ai_action() is skipped on every one of
        those frames for that unrelated reason, and on EACH of them this
        flag was ALSO recomputed fresh as True (the choice is still pending,
        nothing has run to resolve it yet) - once is_busy finally clears,
        this flag is STILL True on that very frame (recomputed from the
        still-pending choice, not from "did a click just resolve it"), so
        run_ai_action() gets skipped yet again, and the next frame sees the
        exact same still-pending state and repeats forever: a genuine
        deadlock, not a one-frame pause, entirely self-inflicted since
        nothing but the very call this flag blocks could ever clear it.
        Fixed by only counting choices belonging to the HUMAN (Player 1) -
        those are the only ones an actual same-frame board click could
        resolve, which is the one real race this snapshot exists to guard
        against; a Player-2-owned choice is never touched by any board
        click, so pausing the AI over one achieves nothing but starves it of
        the only call that could ever resolve it."""
        return any(
            c.pending_damage_choice and c.pending_damage_choice[0].squad is not None
            and c.pending_damage_choice[0].squad.owner != "Player 2"
            for c in (
                shooting_controller, fight_controller, explosives_controller,
                deadly_demise_controller, crushing_impact_controller,
                transport_controller, fall_back_controller,
            )
        )

    def _has_unresolved_declaration():
        """Real user report: "decline charge button blieb links stehen,
        obwohl die KI schon einige Phasen weiter war" - reproduced: the
        right panel's "Next Phase"/"End Turn" click handler only ever
        checked coherency-at-end-of-turn and battle-shock-at-Command-phase
        before letting advance_turn_phase() run. Every OTHER controller's
        own "declaring"/"choosing" sub-state (charge_controller.
        DECLARING_TARGETS - the "Decline Charge" screen itself - and the
        structurally identical states on consolidate/fall_back/explosives/
        epic_challenge/greater_good/firing_deck/fire_overwatch/shooting/
        fight/setup) is
        each only otherwise gated by its OWN elif branch further down in
        the event loop - and every one of those is checked STRICTLY AFTER
        this "Next Phase" branch, so a click on the right panel's button
        always won the race regardless of whether one of those screens was
        still open. That orphaned the controller mid-declaration (active_
        squad/state left exactly as they were) while turn_tracker.phase
        kept advancing underneath it - the left panel kept rendering that
        stale screen (see game/ui/action_panel.py's _draw_dispatch(), which
        renders purely off controller state, not off the current phase)
        for however many further phases passed before anyone happened to
        interact with that controller again (e.g. Player 2's own charge
        eventually self-resolving via ai/agent_driver.py's take_one_action()
        priority check for its OWN squad - but only once take_one_action()
        actually got called again, which might be many phases later if
        ai_auto_play was off or a human kept clicking Next Phase in the
        meantime instead).

        Deliberately does NOT include shooting_controller: unlike every
        other controller here, it already gets an unconditional, genuinely
        comprehensive shooting_controller.cancel() call right below (reset
        by this same "Next Phase" click, long before this bug report,
        clearing damage_session/mortal_wound_session/devastating_wound_
        session and everything else right along with state/active_squad) -
        that's an intentional, pre-existing "abandon and move on" design
        for shooting specifically, not the gap this fixes, and treating it
        as one more thing to block on would change that existing behavior.
        explosives_controller's own cancel() (only ever wired to its own
        panel button, never called from here) is deliberately NOT reused
        as a substitute fix, for the same reason it's blocked on here
        instead: it only resets state/acting_squad/target_squad, not
        mortal_wound_session - calling it while pending_damage_choice is
        still open (a real, reachable window: the 6D6 roll already
        acknowledged, dice_manager.is_pending back to False, waiting on a
        board click for which model takes each mortal wound) would leave a
        stale session dangling with no owner, a strictly worse half-reset
        than just blocking here and leaving its own Cancel path to do the
        job correctly.

        One shared check, used by both this branch's own `blocked` below
        and ai_advance_phase()'s (mirroring it exactly, same reasoning as
        their existing coherency/battle-shock checks) - a single place to
        extend if a future controller adds another such sub-state, instead
        of two lists that could drift apart."""
        return (
            pregame_controller.is_active  # rule 03.01: the battle hasn't started yet
            or setup_controller.state == setup.PLACING
            or fight_controller.state in (fight.CHOOSING_TARGET, fight.CHOOSING_WEAPON, fight.ASSIGNING)
            or fight_controller.current_group is not None
            or fight_controller.pending_damage_choice is not None
            or charge_controller.state == charge.DECLARING_TARGETS
            or consolidate_controller.state != consolidate.IDLE
            or fall_back_controller.state != fall_back.IDLE
            or fall_back_controller.pending_damage_choice is not None
            or explosives_controller.state != explosives.IDLE
            or explosives_controller.pending_damage_choice is not None
        or ishas_fury_controller.is_busy
            or ishas_fury_controller.is_busy
            or grav_inhibitor_controller.is_busy
            or flickerjump_controller.is_busy
            or epic_challenge_controller.state != epic_challenge.IDLE
            or greater_good_controller.state != greater_good.IDLE
            or crushing_impact_controller.state != crushing_impact.IDLE
            or crushing_impact_controller.pending_damage_choice is not None
            or firing_deck_controller.state != firing_deck.IDLE
            or fire_overwatch_controller.state != overwatch.IDLE
            or transport_controller.pending_damage_choice is not None
            or deadly_demise_controller.pending_damage_choice is not None
        )

    def run_ai_pregame_action():
        """Player 2's side of rule 03.01's opening sequence - one action per
        frame, same contract as run_ai_action().

        Deliberately API-call-free (see ai/deployment_ai.py's module
        docstring), so starting a game costs nothing."""
        deployment_ai.take_pregame_action(
            pregame_controller, setup_controller, "Player 2",
            board.width_in, board.height_in,
            objectives=state.objectives, game_log=game_log,
        )

    def run_ai_action():
        """The one call every "A" keypress (and, while ai_auto_play is on,
        every single frame - see the main loop below) makes: resolve
        exactly ONE pending decision for Player 2 and return."""
        nonlocal last_shown_turn_plan
        take_one_action(
            agent, ai_memory, state, turn_tracker, movement_controller, shooting_controller,
            charge_controller, fight_controller, battle_shock_controller, pile_in_controller,
            decision_manager, dice_manager, game_log, coherency_enforcer=coherency_enforcer,
            mission_controller=mission_controller,
            on_thinking=show_thinking_overlay, advance_phase_fn=ai_advance_phase,
            command_reroll_controller=command_reroll_controller, explosives_controller=explosives_controller,
            insane_bravery_controller=insane_bravery_controller,
            transport_controller=transport_controller, setup_controller=setup_controller,
            ingress_controller=ingress_controller, rapid_ingress_controller=rapid_ingress_controller,
            greater_good_controller=greater_good_controller, fall_back_controller=fall_back_controller,
            crushing_impact_controller=crushing_impact_controller, deadly_demise_controller=deadly_demise_controller,
            consolidate_controller=consolidate_controller,
            fire_overwatch_controller=fire_overwatch_controller,
            waaagh_controller=waaagh_controller, arrokon_controller=arrokon_controller,
            unbridled_carnage_controller=unbridled_carnage_controller,
            ere_we_go_controller=ere_we_go_controller,
            retro_thrusters_controller=retro_thrusters_controller,
        )
        # User: "ich würde den plan gerne ausführlicher in einem großen text
        # prompt sehen am anfang des gegnerischen zuges nachdem er erstellt
        # wurde" - ai_memory.turn_plan is a NEW dict object every time
        # ai/agent_driver.py's _maybe_generate_turn_plan() actually
        # regenerates it (once per Player 2 own turn); comparing identity
        # against the last one shown needs no changes to ai/agent_driver.py
        # at all. Skip the trivial "no own squads at all" sentinel plan
        # (empty turn_intent AND no unit_plans).
        plan = ai_memory.turn_plan
        if plan is not None and plan is not last_shown_turn_plan and (plan["turn_intent"] or plan["unit_plans"]):
            turn_plan_overlay.show(plan)
            last_shown_turn_plan = plan

    def ai_advance_phase():
        """Lets ai/agent_driver.py's take_one_action() decide for itself
        when Player 2's part of a phase is over - "remain stationary for
        every unit" is a deliberate choice, not the absence of one, so
        Player 1 shouldn't have to click Next Phase on Player 2's behalf.
        Mirrors the human "Next Phase" click handler above exactly (same
        coherency/battle-shock gating, same movement/shooting cleanup).

        User report: "ich habe dadurch versehentlich meine Charge-Phase
        übersprungen" - this (and ai/agent_driver.py's _is_blocked(), which
        gates whether take_one_action() ever reaches this call at all) used
        to check turn_tracker.active_player here - a transient "whose
        decision is this right now" flag that a defending save roll or a
        reactive Stratagem's decision window can leave pointing at "Player
        2" well after it's actually back to being Player 1's own turn (see
        TurnTracker's own docstring). That stale value could make this fire
        during the HUMAN's turn - _is_blocked() has since been fixed to
        compare against turn_owner (the stable value TurnTracker itself
        only ever changes in advance_phase()) instead, so by the time this
        function is even reached, turn_owner == "Player 2" is already
        guaranteed (or it's the shared Fight phase) - but the coherency/
        battle-shock checks right here read turn_tracker.active_player too,
        for the same "whose units are these rules about" reason, so they
        get the same turn_owner fix for consistency."""
        blocked = (
            (turn_tracker.is_last_phase and not coherency_enforcer.check_end_of_turn(turn_tracker.turn_owner))
            or (
                turn_tracker.phase == PHASE_COMMAND
                and battle_shock_controller.has_pending_required_rolls(state.tokens, turn_tracker.turn_owner)
            )
            or _has_unresolved_declaration()
        )
        if blocked:
            return
        movement_controller.select(None)
        shooting_controller.cancel()
        advance_turn_phase()

    ai_auto_play = False  # Shift+A toggles this - while on, Player 2 acts on its own every frame, no keypress needed
    if fullscreen:
        game_log.add("Fullscreen mode - press ESC to quit.")

    # User: "wenn die KI am Zug ist, zoome bitte automatisch auf die
    # maximale Entfernung, damit ich sehen kann, was sie macht" (+ "also im
    # Player 2 Zug" - confirming this means Player 2's whole turn, not just
    # while ai_auto_play happens to be on). Snapped once, right when
    # turn_tracker.turn_owner actually changes to "Player 2" - not
    # re-applied every frame, so the human can still zoom back in to watch
    # something specific without the camera fighting them for the rest of
    # that turn. Compared against turn_owner (see its own docstring), not
    # active_player - the latter also flips to "Player 2" for the length of
    # a single defending save roll during PLAYER 1's OWN shooting phase,
    # which would otherwise snap the camera out on every shot the human
    # takes at a Player 2 unit.
    #
    # None (not turn_tracker.turn_owner) so the very first frame ALSO counts
    # as a transition - the "Player 1 Turn 1" banner (see turn_start_overlay
    # below) should greet the very start of the game too, not just every
    # turn after it.
    previous_turn_owner = None

    if config.LOAD_SCENE:
        # A saved board position replaces the opening sequence outright: it
        # already says where every model stands, who is in reserve or aboard a
        # transport, and whose turn it is. See game/scene_io.py for why the
        # snapshot carries positions only and the army itself is the one built
        # above - the roster has exactly one correct source and a second copy
        # inside a save file would drift from it silently.
        loaded = scene_io.read(config.LOAD_SCENE)
        if loaded.get("map") != battle_map.key:
            raise SystemExit(
                f"{config.LOAD_SCENE} was saved on {loaded.get('map')!r}, but this "
                f"run is on {battle_map.key!r}. Start it with --map "
                f"{str(loaded.get('map')).replace('map', '')}."
            )
        complaints = scene_io.restore(loaded, state, squads=[e["squad"] for e in scene_units])
        # begin_battle() FIRST, then the turn state: start_battle() resets the
        # round to 1 and the phase to Command, so restoring them before it runs
        # would be silently thrown away.
        begin_battle((loaded.get("turn") or {}).get("turn_owner") or "Player 1")
        complaints += scene_io.restore_turn(loaded, turn_tracker, command_points)
        game_log.add(
            f"Loaded {os.path.basename(config.LOAD_SCENE)}: battle round "
            f"{turn_tracker.battle_round}, {turn_tracker.phase} phase, "
            f"{turn_tracker.turn_owner}'s turn."
        )
        for complaint in complaints:
            game_log.add(f"  [scene] {complaint}", file_only=True)
        if complaints:
            game_log.add(
                f"  [scene] {len(complaints)} mismatch(es) between the snapshot and this "
                "scene's roster - see the log file.", file_only=True,
            )
    elif config.PREGAME_DEPLOYMENT:
        # Rule 03.01. Nothing is on the battlefield yet - scene_units holds the
        # whole of both armies, and PregameController runs the real opening
        # sequence from here. The scene's own destination/transport hints stay
        # available to the AI's formation planner as preferences; both players
        # re-declare them in the Declare Battle Formations step.
        pregame_controller.start(
            {
                owner: [e["squad"] for e in scene_units if e["squad"].owner == owner]
                for owner in ("Player 1", "Player 2")
            },
            transport_tokens=[
                e["squad"].models[0] for e in scene_units
                if e["squad"].models and e["squad"].models[0].profile.transport
            ],
        )
        pregame_controller.scene_hints = {
            id(e["squad"]): (e["destination"], e["transport"]) for e in scene_units
        }
        # "Auto-place this unit" on the human's side runs the AI's own placer.
        pregame_controller.on_auto_place = lambda squad: deployment_ai.auto_deploy_squad(
            pregame_controller, setup_controller, squad, board.width_in, board.height_in,
            objectives=state.objectives, game_log=game_log,
        )
        # Rule 24.31 (SCOUTS), resolved in the Pre-battle Abilities step.
        pregame_controller.scouts_step = ScoutsStep(
            movement_controller, game_log=game_log,
            on_resolve=lambda pre, squad, branch, distance: deployment_ai.resolve_scouts(
                pre, squad, branch, distance,
                movement_controller=movement_controller, setup_controller=setup_controller,
                board_w_in=board.width_in, board_h_in=board.height_in,
                objectives=state.objectives, game_log=game_log,
            ),
        )

    running = True
    while running:
        # User report: dismissing a prompt (a DecisionManager choice, or a
        # "Player 2 uses X" Stratagem notice) used to let the AI act in that
        # very same frame - none of DecisionOverlay/StratagemNoticeOverlay
        # have a multi-frame close animation like DicePanel's slide-out
        # (dice_panel.is_busy), so the moment a click resolves one, its
        # is_pending flag drops to False instantly, and the run_ai_action()
        # guards below (which only check "is something currently pending",
        # not "did we just dismiss something this very frame") let the AI's
        # next action fire before this frame's own render call ever gets to
        # show the prompt actually gone. If that next action takes a while
        # (a real agent.decide() round-trip, or just an expensive
        # computation), the screen sits on last frame's stale render -
        # looking exactly like the just-dismissed prompt "got stuck" until
        # the AI finishes. Seeded from _any_pending_damage_choice()'s own
        # snapshot (see its docstring) instead of a flat False, so the same
        # protection covers a human removing one of their own models via a
        # board click, not just an overlay button; also set True below
        # wherever a click resolves one of the instant-dismiss overlays, so
        # run_ai_action() simply waits one frame - by which point the
        # render has already caught up to "prompt gone"/"model gone" -
        # before resuming.
        ai_action_paused_this_frame = _any_pending_damage_choice()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif fullscreen and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # User: "im vollbild modus beendet ESC das spiel" - same
                # priority as the window's own close button (QUIT, right
                # above), deliberately checked before any of the
                # controller-state gates below (same reasoning as "A"/mouse
                # wheel further down: those gate on STATE, not event type, so
                # ESC could otherwise get silently swallowed whenever a dice
                # roll/decision/etc. happened to be pending).
                running = False
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_F9, pygame.K_p):
                # Save the whole board position, so whatever just went wrong can
                # be re-opened with `python main.py --load <file>` and turned
                # into a test fixture, instead of being rebuilt by hand from the
                # coordinates in the log. See game/scene_io.py.
                #
                # Replaces an older P-key helper that wrote every model's x/y to
                # squad_positions.txt and could only be read by a human - its own
                # comment asked for it to go once something better existed. P
                # still works so the habit is not broken.
                stamp = time.strftime("%Y%m%d_%H%M%S")
                path = scene_io.write(
                    scene_io.capture(state, battle_map.key, turn_tracker, command_points),
                    os.path.join("scenes", f"scene_{stamp}.json"),
                )
                game_log.add(f"Board position saved to {path} (reload it with --load {path})")
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_a:
                # Rule-agnostic AI trigger (see CLAUDE.md, "Schritt 3"): resolves
                # exactly ONE pending decision for Player 2 and stops - press
                # again to let it take its next action, one at a time. Shift+A
                # instead toggles ai_auto_play (see below) - Player 2 then just
                # keeps acting on its own, one action per frame, with no
                # keypress needed at all until a human decision (dice ack,
                # damage allocation, decision prompt, coherency removal) blocks
                # it, exactly like take_one_action() already gates every single
                # call, whether triggered by a key or by auto-play.
                #
                # Deliberately checked FIRST, before any of the controller-STATE
                # gates below (e.g. "fight_controller.current_group is not
                # None", "explosives_controller.pending_damage_choice is not
                # None", "charge_controller.state == DECLARING_TARGETS") - those
                # gate on state, not event type, so a KEYDOWN would otherwise
                # silently fall into one of them (whose body only handles
                # MOUSEBUTTONDOWN) and be swallowed before ever reaching this
                # branch. That was a real bug: exactly the moments Player 2
                # most needs to act - distributing a wound after a failed fight
                # or Explosives save, or picking/declining a charge target once
                # the roll is known - are exactly when one of those state gates
                # is active, so "A" did nothing at the moments that mattered.
                if getattr(event, "mod", 0) & pygame.KMOD_SHIFT:
                    ai_auto_play = not ai_auto_play
                    game_log.add(f"Player 2: auto-play {'ON' if ai_auto_play else 'OFF'} (Shift+A).")
                elif (
                    not dice_panel.is_busy and not stratagem_notice_overlay.is_pending
                    and not waaagh_notice_overlay.is_pending
                    and not turn_start_overlay.is_pending and not turn_plan_overlay.is_pending
                    and not ai_action_paused_this_frame
                ):
                    # User report: the AI used to fire its next action the
                    # instant a roll was acknowledged, in the very same frame
                    # the dice panel still had to slide out - the panel then
                    # visually got stuck mid-animation until whatever the AI
                    # did next happened to touch it again. dice_panel.is_busy
                    # stays true for the whole slide-out (see its own
                    # docstring), so this simply waits the animation out
                    # before letting the AI act, same as a pending dice roll
                    # itself already blocks it (see _is_blocked()). Likewise,
                    # a still-unread "Player 2 used X" notice, or an unread
                    # turn plan overlay, must be dismissed before the AI is
                    # allowed to act again.
                    run_ai_action()
            elif event.type == pygame.MOUSEWHEEL:
                # Später-Liste (Kamera-Scrolling/Viewport): zoom with the
                # mouse wheel, centered on the cursor - deliberately its own
                # very early branch (same reasoning as "A" above: every
                # other branch below gates on CONTROLLER STATE, not event
                # type, so a wheel event reaching one of those would just be
                # silently swallowed the instant any dice roll/decision/etc.
                # was pending, exactly the "A" bug from before). Zooming
                # itself never resolves a game decision, so there's no
                # reason it should ever be blocked by one.
                mouse_pos = pygame.mouse.get_pos()
                if board_rect_screen.collidepoint(mouse_pos):
                    local = (mouse_pos[0] - board_rect_screen.x, mouse_pos[1] - board_rect_screen.y)
                    camera.zoom_at(local, WHEEL_ZOOM_STEP ** event.y)
                elif log_rect.collidepoint(mouse_pos):
                    # Scrolling back through the log, for the same reason zoom
                    # is here: it is a view control, it resolves no decision, and
                    # putting it in the state-gated chain below would mean the
                    # log froze the moment anything was pending.
                    log_panel.handle_scroll(event.y)
            elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and log_rect.collidepoint(event.pos)):
                # The log's filter chips - same argument as the wheel above, and
                # nothing else on screen wants clicks inside this rect, so a
                # miss is simply swallowed rather than falling through to the
                # board dispatch.
                log_panel.handle_click(event.pos)
            elif turn_start_overlay.is_pending:
                # User: the "Player X Turn Y" banner takes priority over
                # everything else, even a Stratagem-use notice or a pending
                # decision/dice roll left over from the previous turn's very
                # last moment (e.g. a reactive Stratagem offered right as the
                # phase/turn rolled over) - the human should see whose turn
                # it now is before anything else. Any click dismisses it.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    turn_start_overlay.dismiss()
                    ai_action_paused_this_frame = True
            elif turn_plan_overlay.is_pending:
                # See run_ai_action()'s own comment - shown once, right when
                # a fresh strategic turn plan is generated. Same "any click
                # dismisses it" priority as the turn-start banner, just one
                # tier below it (a plan is only ever generated once the AI's
                # own turn/Movement phase has already begun, well after
                # "Player 2 Turn N" would already have been shown/dismissed).
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    turn_plan_overlay.dismiss()
                    ai_action_paused_this_frame = True
            elif stratagem_notice_overlay.is_pending:
                # User: a "Player 2 uses X" notice takes priority over
                # everything else - even a pending decision/dice roll from
                # the very same Stratagem's own effect (e.g. Explosives'
                # 6D6, or a chained Rapid Ingress -> Fire Overwatch reactive
                # offer) - the human should see WHICH Stratagem just got
                # spent before whatever it triggers next. Any click
                # dismisses it (there's nothing to choose, just acknowledge).
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    stratagem_notice_overlay.dismiss()
                    ai_action_paused_this_frame = True
            elif waaagh_notice_overlay.is_pending:
                # User: "ich will... ein prompt... das ich weg klicken muss,
                # wenn ein waagh ausgerufen wird" - same "must-click-away,
                # nothing to choose" priority as the Stratagem notice above.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    waaagh_notice_overlay.dismiss()
                    ai_action_paused_this_frame = True
            elif decision_manager.is_pending:
                # A decision break point takes priority over everything else -
                # even a pending dice roll - until the player picks an option.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    index = decision_overlay.handle_click(event.pos)
                    if index is not None:
                        decision_manager.choose(index)
                        ai_action_paused_this_frame = True
            elif dice_manager.is_pending:
                # Game is paused until the pending dice roll is clicked away -
                # except rule 15.02's Command Re-roll, offered in the left
                # panel, and (while picking which die) a click on the dice
                # display itself.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if command_reroll_controller.selecting_die:
                        die_index = dice_panel.die_index_at(event.pos)
                        if die_index is not None:
                            command_reroll_controller.choose_die(die_index)
                    elif left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    else:
                        dice_manager.acknowledge()
                        movement_controller.on_dice_acknowledged()
                        shooting_controller.on_dice_acknowledged()
                        charge_controller.on_dice_acknowledged()
                        fight_controller.on_dice_acknowledged()
                        battle_shock_controller.on_dice_acknowledged()
                        # After battle_shock's: the Grav-Inhibitor Field's own
                        # first step IS a Battle-Shock test, and its second roll
                        # is queued only once that outcome has been applied.
                        grav_inhibitor_controller.on_dice_acknowledged()
                        flickerjump_controller.on_dice_acknowledged()
                        explosives_controller.on_dice_acknowledged()
                        ishas_fury_controller.on_dice_acknowledged()
                        deadly_demise_controller.on_dice_acknowledged()
                        transport_controller.on_dice_acknowledged()
                        crushing_impact_controller.on_dice_acknowledged()
                        fall_back_controller.on_dice_acknowledged()
                        thievin_scavengers_controller.on_dice_acknowledged()
                        spirit_of_gork_controller.on_dice_acknowledged()
                        grot_orderly_controller.on_dice_acknowledged()
                        pregame_controller.on_dice_acknowledged()  # rule 03.01 roll-offs
            elif crushing_impact_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in crushing_impact_controller.pending_damage_choice:
                        crushing_impact_controller.choose_damage_model(clicked)
            elif crushing_impact_controller.state == crushing_impact.CHOOSING_ENEMY:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked.squad in crushing_impact_controller.eligible_enemy_squads():
                            crushing_impact_controller.choose_enemy(clicked.squad)
            elif crushing_impact_controller.state == crushing_impact.CHOOSING_MODEL:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked in crushing_impact_controller.choosable_models():
                            crushing_impact_controller.choose_model(clicked)
            elif transport_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in transport_controller.pending_damage_choice:
                        transport_controller.choose_damage_model(clicked)
            elif deadly_demise_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in deadly_demise_controller.pending_damage_choice:
                        deadly_demise_controller.choose_damage_model(clicked)
            elif fall_back_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in fall_back_controller.pending_damage_choice:
                        fall_back_controller.choose_damage_model(clicked)
            elif (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and right_panel_rect.collidepoint(event.pos)
                and game_status_panel.handle_click(event.pos)
            ):
                # "Regaining Coherency": the turn can't end while one of the
                # turn owner's own units is out of coherency - but that only
                # applies when this click would actually end the turn (rule
                # 07.02/07.03), not every intermediate phase change. Rule
                # 08.03: can't leave the Command phase while any of the turn
                # owner's units still has a mandatory Battle-Shock roll
                # pending. Checked against turn_tracker.turn_owner, not
                # active_player - the latter is a transient "whose decision
                # is this right now" flag (flipped by a defending save roll
                # or a reactive Stratagem's decision window) that isn't
                # guaranteed to still equal the actual turn owner at the
                # moment this button is clicked (same bug class already
                # fixed in ai/agent_driver.py's _is_blocked() and
                # ai_advance_phase() above - see their own comments).
                #
                # _has_unresolved_declaration(): real user report ("decline
                # charge button blieb links stehen, obwohl die KI schon
                # einige Phasen weiter war") - this click's own condition
                # above is checked BEFORE every one of the other controller-
                # state elif branches further down in this same event loop
                # (charge_controller.DECLARING_TARGETS/consolidate/
                # fall_back/explosives/epic_challenge/greater_good/
                # firing_deck/shooting/fight/setup), so it always won the
                # race and silently orphaned whichever one of those was
                # still open - see that function's own docstring for the
                # full reproduction.
                blocked = (
                    (turn_tracker.is_last_phase and not coherency_enforcer.check_end_of_turn(turn_tracker.turn_owner))
                    or (
                        turn_tracker.phase == PHASE_COMMAND
                        and battle_shock_controller.has_pending_required_rolls(state.tokens, turn_tracker.turn_owner)
                    )
                    or _has_unresolved_declaration()
                )
                if not blocked:
                    movement_controller.select(None)
                    shooting_controller.cancel()
                    advance_turn_phase()
            elif coherency_enforcer.pending_squad is not None:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and board_rect_screen.collidepoint(event.pos):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in coherency_enforcer.pending_squad.models:
                        coherency_enforcer.remove_model(clicked)
                        if coherency_enforcer.pending_squad is None:
                            movement_controller.select(None)
                            shooting_controller.cancel()
                            advance_turn_phase()
            elif (
                shooting_controller.current_group is not None
                or shooting_controller.pending_damage_choice is not None
            ):
                # `or pending_damage_choice is not None` - real hard lock,
                # found via user report ("ich konnte gerade nichts mehr
                # machen als ich Wunden verteilen musste auf meine
                # Starscythe... ich konnte dann nur eine Phase
                # weiterspringen, um aus dem Lock rauszukommen"). Rule
                # 24.15 ([HAZARDOUS]) resolves "after that unit has
                # resolved all of its attacks" - i.e. AFTER the last weapon
                # group is finished, so current_group is None by then (see
                # ShootingController.on_dice_acknowledged()'s own note on
                # its "hazard"/"hazard_wounds" steps). A failed hazard roll
                # on a multi-model unit then needs its OWNER to pick which
                # of their own models takes each mortal wound (rule 06.02),
                # but keying this branch on current_group alone meant the
                # chain fell through to the CHOOSING_WEAPON branch below,
                # which only routes left-panel clicks: the models were
                # highlighted on the board and completely unclickable, with
                # no dice and no prompt left either - escapable only via
                # the Next Phase button (which sits EARLIER in this chain,
                # which is exactly the escape the user found).
                if (
                    shooting_controller.pending_damage_choice is not None
                    and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in shooting_controller.pending_damage_choice:
                        shooting_controller.choose_damage_model(clicked)
                # else: a dice roll is pending or resolving; ignore other input
            elif shooting_controller.state == shooting.CHOOSING_SHOOTING_TYPE:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
            elif shooting_controller.state == shooting.CHOOSING_WEAPON:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
            elif shooting_controller.state == shooting.CHOOSING_TARGET:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked in get_shoot_targets():
                            shooting_controller.choose_target_squad(clicked.squad)
            elif shooting_controller.state == shooting.ASSIGNING:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked in get_shoot_targets():
                            shooting_controller.assign_current(clicked.squad)
            elif (
                fight_controller.current_group is not None
                or fight_controller.pending_damage_choice is not None
            ):
                # Same [HAZARDOUS] hard lock as the shooting branch above -
                # game/fight.py runs the identical "hazard"/"hazard_wounds"
                # steps after its own current_group is already None.
                if (
                    fight_controller.pending_damage_choice is not None
                    and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in fight_controller.pending_damage_choice:
                        fight_controller.choose_damage_model(clicked)
                # else: a dice roll is pending or resolving; ignore other input
            elif epic_challenge_controller.state == epic_challenge.CHOOSING_MODEL:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked in epic_challenge_controller.choosable_models():
                            epic_challenge_controller.choose_model(clicked)
            elif fight_controller.state == fight.CHOOSING_TARGET:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked in fight_controller.valid_target_models():
                            fight_controller.choose_target_squad(clicked.squad)
            elif fight_controller.state == fight.CHOOSING_WEAPON:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
            elif fight_controller.state == fight.ASSIGNING:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked in fight_controller.valid_target_models():
                            fight_controller.assign_current(clicked.squad)
            elif flickerjump_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in flickerjump_controller.pending_damage_choice:
                        flickerjump_controller.choose_damage_model(clicked)
            elif grav_inhibitor_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in grav_inhibitor_controller.pending_damage_choice:
                        grav_inhibitor_controller.choose_damage_model(clicked)
            elif ishas_fury_controller.pending_damage_choice is not None:
                # Rule 06.02 again: the moving player picks which of their own
                # models takes each mortal wound.
                if board_rect.collidepoint(event.pos):
                    clicked = input_manager.token_at_event(state.tokens, event, board, board_rect)
                    if clicked is not None and clicked in ishas_fury_controller.pending_damage_choice:
                        ishas_fury_controller.choose_damage_model(clicked)
            elif explosives_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in explosives_controller.pending_damage_choice:
                        explosives_controller.choose_damage_model(clicked)
            elif explosives_controller.state == explosives.CHOOSING_MODEL:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked in explosives_controller.choosable_models():
                            explosives_controller.choose_model(clicked)
            elif explosives_controller.state == explosives.CHOOSING_TARGET:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked.squad in explosives_controller.eligible_target_squads():
                            explosives_controller.choose_target(clicked.squad)
            elif greater_good_controller.state == greater_good.CHOOSING_TARGET:
                # T'au Empire army rule (For The Greater Good): pick a
                # visible, not-yet-Spotted enemy unit for this Observer to mark.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked.squad in get_greater_good_eligible_squads():
                            greater_good_controller.choose_target(clicked.squad)
            elif charge_controller.state == charge.DECLARING_TARGETS and movement_controller.state != movement.MOVING:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked.squad in charge_controller.eligible_charge_target_squads():
                            charge_controller.toggle_charge_target(clicked.squad)
            elif (
                consolidate_controller.state == consolidate.CHOOSING_ENGAGING_TARGETS
                and movement_controller.state != movement.MOVING
            ):
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if (
                            clicked is not None
                            and clicked.squad in consolidate_controller.eligible_engaging_targets(consolidate_controller.active_squad)
                        ):
                            consolidate_controller.toggle_engaging_target(clicked.squad)
            elif (
                consolidate_controller.state == consolidate.CHOOSING_OBJECTIVE
                and movement_controller.state != movement.MOVING
            ):
                # Rule 12.08 (Objective Consolidation): objectives aren't
                # board tokens, so this is panel-button-only - no board
                # click branch needed here, unlike Engaging's target list.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and left_panel_rect.collidepoint(event.pos):
                    action_panel.handle_click(event.pos)
            elif (
                fall_back_controller.state == fall_back.CHOOSING_MODE
                and movement_controller.state != movement.MOVING
            ):
                # Rule 09.07: Ordered Retreat vs Desperate Escape has no
                # board target to click either - panel-button-only, same as
                # Objective Consolidation/Firing Deck above.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and left_panel_rect.collidepoint(event.pos):
                    action_panel.handle_click(event.pos)
            elif firing_deck_controller.state in (firing_deck.CHOOSING_MODELS, firing_deck.CHOOSING_WEAPON):
                # Rule 24.14 (Firing Deck): embarked candidate models/weapons
                # aren't board tokens either - panel-button-only, same as
                # Objective Consolidation above.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and left_panel_rect.collidepoint(event.pos):
                    action_panel.handle_click(event.pos)
            elif fire_overwatch_controller.state == overwatch.CHOOSING_UNIT:
                # Rule 15.08 (Fire Overwatch): redesigned from a
                # DecisionManager text-button list into this board-click-a-
                # unit screen (see game/overwatch.py's docstring) - click
                # one of your own highlighted units on the battlefield to
                # shoot with it, or Decline in the left panel.
                #
                # User report: "wenn ich auf decline drücke, dann bleibt es
                # stehen weil claude direkt weitermacht" - Decline (and
                # choose_unit) flip fire_overwatch_controller.state back to
                # IDLE synchronously, right here in event handling, same as
                # a decision_manager.choose() click a few branches above -
                # but unlike that branch, this one never set
                # ai_action_paused_this_frame, so run_ai_action() (further
                # down, still this same frame) saw an already-idle
                # controller and fired immediately, before this frame's own
                # render ever caught up to "the overwatch screen is gone" -
                # looking exactly like it "got stuck" until Claude's action
                # finished. Same one-frame pause as every other instant-
                # dismiss click above.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                        ai_action_paused_this_frame = True
                    elif board_rect_screen.collidepoint(event.pos):
                        clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                        if clicked is not None and clicked.squad in get_fire_overwatch_eligible_squads():
                            fire_overwatch_controller.choose_unit(clicked.squad)
                            ai_action_paused_this_frame = True
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_LALT, pygame.K_RALT):
                input_manager.start_measuring()
            elif event.type == pygame.KEYUP and event.key in (pygame.K_LALT, pygame.K_RALT):
                input_manager.stop_measuring()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if reserves_panel_rect.collidepoint(event.pos):
                    # The Player 1/Player 2 tabs and the pagination arrows live
                    # inside this same rect - a hit on either changes which
                    # cards are shown instead of picking one up.
                    if not reserves_panel.handle_click(event.pos):
                        clicked_squad = reserves_panel.squad_at(event.pos)
                        if clicked_squad is not None and pregame_controller.state == pregame.DEPLOYING:
                            # Rule 03.01: click-to-select, then click the board
                            # to place. A drag would work too, but a plain
                            # click pair is what a headless harness can
                            # synthesise (selfplay.py emits no MOUSEMOTION),
                            # and clicking twelve units out of a strip in a row
                            # is less tiring than dragging them.
                            pregame_controller.select_unit(clicked_squad)
                        elif clicked_squad is not None:
                            dragging_reserve_squad = clicked_squad
                            # Homing Beacon (user-supplied wargear item): set the
                            # placement rule for the WHOLE drag (not just after
                            # the drop) so the green/red overlay is accurate from
                            # the moment the card starts moving - see
                            # IngressController.homing_beacon_bearer's docstring.
                            ingress_controller.homing_beacon_bearer = (
                                rapid_ingress_controller.pending_homing_beacon_bearer
                                if rapid_ingress_controller.pending_squad is clicked_squad
                                else None
                            )
                elif left_panel_rect.collidepoint(event.pos):
                    action_panel.handle_click(event.pos)
                elif board_rect_screen.collidepoint(event.pos) and pregame_controller.awaiting_drop:
                    # Rule 03.01: a unit is selected from the pre-game pool and
                    # this click says where it goes. Intercepted ahead of the
                    # normal board handling, which would otherwise read it as a
                    # selection/move gesture.
                    local = camera.to_native_px(
                        (event.pos[0] - board_rect_screen.x, event.pos[1] - board_rect_screen.y)
                    )
                    drop_x_in, drop_y_in = board.to_in(*local)
                    pregame_controller.start_deployment(
                        pregame_controller.selected_unit, drop_x_in, drop_y_in,
                    )
                elif board_rect_screen.collidepoint(event.pos):
                    input_manager.handle_event(event, state.tokens, board, movement_controller, setup_controller)
                    # Später-Liste (Kamera-Scrolling/Viewport): left-drag to
                    # pan, but only once it's established this click didn't
                    # just grab a model to move/place - handle_event() above
                    # already sets dragging_token in that case, and letting
                    # BOTH interpretations fire on the same drag would move
                    # the model and the camera underneath it at once. This
                    # is a deliberately narrow hook: nothing else in this
                    # branch's state (idle browsing, or a click on empty
                    # board space while moving/placing) ever did anything
                    # with the drag that follows a plain left-click here
                    # before, so there's no existing gesture to collide with.
                    # pending_move_token covers the QoL auto-move-on-drag
                    # gesture, which can't have set dragging_token yet: at
                    # press time it isn't known whether this is a drag or a
                    # plain selection click, so the model is only armed here
                    # and picked up on the first motion. Panning would
                    # otherwise start underneath it and both would run at once.
                    if input_manager.dragging_token is None and input_manager.pending_move_token is None:
                        camera.begin_pan(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and dragging_reserve_squad is not None:
                # Rule 20.04: drop the dragged reserves-panel card - if it
                # lands on the board, start an Ingress move there (checks
                # battle round eligibility and, at confirm time, the extra
                # set-up-distance/enemy-proximity constraints on top of
                # plain Set Up); otherwise it's simply not picked up (still
                # in reserves).
                if board_rect_screen.collidepoint(event.pos):
                    local = (event.pos[0] - board_rect_screen.x, event.pos[1] - board_rect_screen.y)
                    x_in, y_in = board.to_in(*camera.to_native_px(local))
                    ingress_controller.start_ingress(dragging_reserve_squad, x_in, y_in)
                    # Rule 15.07: this was the one attempt the Rapid Ingress
                    # window bought - used up the instant it's dropped on
                    # the board, whether or not IngressController accepts it.
                    # setup_controller is passed here (unlike ai/agent_driver.
                    # py's own auto-ingress call) so a chained Fire Overwatch
                    # offer defers until this placement actually concludes
                    # instead of hijacking it mid-drag - see consume()'s own
                    # docstring for the full bug report this fixes.
                    rapid_ingress_controller.consume(dragging_reserve_squad, setup_controller=setup_controller)
                dragging_reserve_squad = None
            elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
                # Später-Liste (Kamera-Scrolling/Viewport): update the pan
                # BEFORE input_manager sees this same motion event, so its
                # own hover/drag math (which goes through the same camera,
                # see InputManager._local_pos()) already reflects where the
                # view just moved to, instead of lagging a frame behind.
                if event.type == pygame.MOUSEMOTION and camera.is_panning:
                    camera.update_pan(event.pos)
                input_manager.handle_event(event, state.tokens, board, movement_controller, setup_controller)
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    camera.end_pan()

        # `turn_tracker.started` gates the whole block: during the pre-game
        # sequence (rule 03.01) nobody has a turn yet, and without this the
        # "Player 1 Turn 1" banner would greet frame 1, before deployment.
        if turn_tracker.started and turn_tracker.turn_owner != previous_turn_owner:
            # User: "ich will ein overlay, wenn ein neuer zug beginnt, das
            # man wegklicken muss. einfach mit 'Player X Turn Y'." - every
            # new turn, both players, including the game's very first one
            # (see previous_turn_owner's init above).
            #
            # Deliberately checked BEFORE the ai_auto_play gate right below,
            # not after it (as it used to be) - real user report: "zu
            # beginn der runde überlagern sich oft noch meldungen. Waagh /
            # Turn notification / würfelwurf für cp generierung. das soll
            # alles nacheinander abgespielt werden." Reproduced: a human's
            # own "End Turn" click flips turn_tracker.turn_owner to "Player
            # 2" from inside the event loop above, in THIS SAME frame - but
            # this check used to run AFTER the ai_auto_play block further
            # down, so on that exact frame turn_start_overlay.is_pending was
            # still False when that block's gate was evaluated, letting
            # run_ai_action() fire immediately (Player 2's very first
            # Command-phase decision is often _maybe_call_waaagh() - see
            # ai/agent_driver.py's take_one_action() - which enqueues
            # waaagh_notice_overlay right then). Both the turn banner and
            # the WAAAGH notice ended up pending by the time this frame
            # rendered, instead of one after the other. Showing the banner
            # first means the ai_auto_play gate below (which already checks
            # turn_start_overlay.is_pending) correctly withholds this same
            # frame's AI action until the banner is dismissed - WAAAGH, and
            # anything after it (e.g. Thievin' Scavengers' CP roll at the
            # start of the Movement phase), only ever gets a chance to
            # become pending on a later frame, once the human has clicked
            # through everything queued ahead of it. Nothing else needed:
            # stratagem_notice_overlay/waaagh_notice_overlay/dice_manager
            # already gate every further AI action the exact same way, so
            # this one reordering serializes the whole chain.
            turn_start_overlay.show(turn_tracker.turn_owner, turn_tracker.turn_number_for(turn_tracker.turn_owner))
            if turn_tracker.turn_owner == "Player 2":
                camera.zoom = camera.min_zoom
                camera.pan_x = 0.0
                camera.pan_y = 0.0
            previous_turn_owner = turn_tracker.turn_owner

        if (
            ai_auto_play and not dice_panel.is_busy and not stratagem_notice_overlay.is_pending
            and not waaagh_notice_overlay.is_pending
            and not turn_start_overlay.is_pending and not turn_plan_overlay.is_pending
            and not ai_action_paused_this_frame
        ):
            # Shift+A was used to turn this on - Player 2 just keeps acting,
            # one action per frame, with no keypress needed. take_one_action()
            # itself is what actually stops this from running away: it's a
            # no-op whenever something needs the human first (dice ack,
            # damage allocation, decision prompt, coherency removal, or it
            # simply isn't Player 2's turn), so this is exactly as safe to
            # call every frame as pressing "A" that often would be. The
            # dice_panel.is_busy check on top of that is what makes the AI
            # actually wait for the dice panel's slide-in/out animation
            # (see DicePanel.is_busy's docstring) instead of queuing its next
            # action mid-animation - real user report: clicking a roll away
            # used to let the AI act in that same frame, leaving the panel
            # visually stuck sliding out until whatever the AI did next
            # happened to touch dice again. stratagem_notice_overlay.is_pending
            # is the same idea for a still-unread "Player 2 used X" notice -
            # the AI shouldn't be allowed to spend another Stratagem (or do
            # anything else) before that one's even been acknowledged.
            # ai_action_paused_this_frame covers the same race for
            # DecisionOverlay/StratagemNoticeOverlay specifically (see its
            # own reset at the top of this loop) - unlike the dice panel,
            # neither has a multi-frame close animation, so without this
            # flag the AI's next action could still fire in the exact frame
            # a prompt was just dismissed, before the render ever shows it
            # gone - making the prompt look "stuck" for however long that
            # next action takes.
            #
            # During the pre-game (rule 03.01) there is no turn to play yet -
            # take_one_action() would be asked to act in a Command phase that
            # hasn't begun. The AI's own opening sequence runs instead.
            if pregame_controller.is_active:
                run_ai_pregame_action()
            else:
                run_ai_action()

        # The Twin Lance's Retro-thrusters: sample "was eligible to fight
        # this phase" while the phase is still running - it cannot be
        # recomputed afterwards (see game/retro_thrusters.py).
        if turn_tracker.phase == PHASE_FIGHT:
            retro_thrusters_controller.note_eligibility()
        for dead in state.remove_dead_models():
            game_log.add(f"{dead.profile.name} was destroyed.")
            state.add_blood_decal(dead.x_in, dead.y_in, dead.radius_in)
            if movement_controller.selected_model is dead:
                movement_controller.select(None)
            if input_manager.hovered_token is dead:
                input_manager.hovered_token = None
            # Rule 18.03/18.05: a destroyed TRANSPORT's passengers must
            # emergency disembark BEFORE Deadly Demise resolves for it
            # (24.08's "after the units embarked within it have made their
            # emergency disembark moves") - queued here, resolved via the
            # transport_controller.is_busy gate below.
            if dead.profile.transport:
                transport_controller.queue_transport_destroyed(dead)
            deadly_demise_controller.queue_death(dead)
            # Retaliation Cadre's Fail-Safe Detonator: offered AFTER
            # queue_death() so has_queued_death() can see the detonation it may
            # replace, and answered before that roll ever starts - the gate
            # below that lets deadly_demise_controller begin is blocked while a
            # decision is pending.
            fail_safe_controller.notify_destroyed(dead)
            # Secondary mission ("No Mercy", user-supplied): a unit counts as
            # "destroyed" once its last model is gone - remove_dead_models()
            # (called just above, at the top of this loop) already stripped
            # every dead token out of its squad's own models list, so this
            # simply checks whether that just emptied it out.
            #
            # Rule 19.02 ("rules that are triggered when a unit is destroyed
            # are only triggered when the last model that STARTED the battle
            # in an attached unit is destroyed") needs no special case here:
            # forming an attached unit merges every component's models into
            # this one Squad (see game/attached_units.py), so an emptied
            # models list already means every component is gone - killing
            # just the attached Character, or just the bodyguards, correctly
            # scores nothing. unit_is_destroyed() states that rather than
            # leaving it as a coincidence of the representation.
            if dead.squad is not None and attached_units.unit_is_destroyed(dead.squad):
                mission_controller.record_destroyed_squad(dead.squad)

        # Only start a new Deadly Demise roll or Emergency Disembark once
        # nothing else is already waiting on the player (another dice
        # roll, or a normal/mortal-wound allocation choice) - otherwise two
        # unrelated prompts could appear at once (e.g. a multi-casualty
        # volley that both kills a Deadly Demise model and still owes a
        # damage-allocation pick).
        if not (
            decision_manager.is_pending
            or dice_manager.is_pending
            or shooting_controller.pending_damage_choice is not None
            or fight_controller.pending_damage_choice is not None
            or explosives_controller.pending_damage_choice is not None
            or grav_inhibitor_controller.pending_damage_choice is not None
            or flickerjump_controller.pending_damage_choice is not None
        ):
            transport_controller.maybe_start_next_emergency()
            if not transport_controller.is_busy:
                deadly_demise_controller.maybe_start_next()

        anchor = movement_controller.selected_model
        if anchor is None or movement_controller.group_move_enabled or not movement_controller.live_los_highlight_enabled:
            # QoL "Move Whole Squad" drag (game/movement.py's
            # apply_group_drag()) moves every model in the squad on every
            # single mouse-motion event - skip the live LOS highlight
            # entirely while it's on, rather than adding its own per-frame
            # cost (already an identified hot path, see VISIBILITY_SAMPLE_POINTS
            # above) on top of that. User follow-up request: the same cost
            # exists for a normal single-model drag too, so it's now its own
            # persistent toggle (movement_controller.live_los_highlight_enabled,
            # game/movement.py's toggle_live_los_highlight()) - off by
            # default, same as Move Whole Squad's own LOS skip above.
            visibility_cache["key"] = None
            visible_models = set()
        else:
            cache_key = (anchor.id, _visibility_grid_snap(anchor.x_in), _visibility_grid_snap(anchor.y_in), len(state.tokens))
            if cache_key != visibility_cache["key"]:
                visibility_cache["key"] = cache_key
                # User-report: only enemy models are ever relevant for this
                # highlight in practice (it's meant to answer "can this
                # model see the enemy," not "can it see its own squadmates")
                # - filtering the candidate set to enemies BEFORE the
                # expensive has_line_of_sight() call roughly halves how many
                # of those calls happen per recompute (skips the anchor's
                # whole own army, not just its own squad).
                visibility_cache["result"] = {
                    other for other in state.tokens
                    if other.squad is not None and anchor.squad is not None
                    and other.squad.owner != anchor.squad.owner
                    and line_of_sight.has_line_of_sight(
                        anchor, other, state.obstacles, state.tokens, state.terrain_areas,
                        sample_points=VISIBILITY_SAMPLE_POINTS,
                    )
                }
            visible_models = visibility_cache["result"]

        shoot_targets = get_shoot_targets()
        attack_pair = shooting_controller.active_attack_pair()
        charge_target_models = {
            token for token in state.tokens
            if token.squad in charge_controller.eligible_charge_target_squads()
        }
        consolidate_target_models = set()
        if consolidate_controller.state == consolidate.CHOOSING_ENGAGING_TARGETS:
            eligible_consolidate_squads = consolidate_controller.eligible_engaging_targets(consolidate_controller.active_squad)
            consolidate_target_models = {token for token in state.tokens if token.squad in eligible_consolidate_squads}
        fight_target_models = fight_controller.valid_target_models()
        fight_assigning_model = None
        if fight_controller.state == fight.ASSIGNING and fight_controller.current_assignment() is not None:
            fight_assigning_model = fight_controller.current_assignment()[0]
        shoot_assigning_model = None
        if shooting_controller.state == shooting.ASSIGNING and shooting_controller.current_assignment() is not None:
            shoot_assigning_model = shooting_controller.current_assignment()[0]
        fight_attack_pair = None
        if fight_controller.target_squad is not None and fight_controller.fighting_squad is not None:
            fight_attack_pair = (fight_controller.fighting_squad, fight_controller.target_squad)

        explosives_choosable_models = set(explosives_controller.choosable_models())
        explosives_target_models = {
            token for token in state.tokens
            if token.squad in explosives_controller.eligible_target_squads()
        }
        epic_challenge_choosable_models = set(epic_challenge_controller.choosable_models())
        crushing_impact_target_models = {
            token for token in state.tokens
            if token.squad in crushing_impact_controller.eligible_enemy_squads()
        }
        crushing_impact_choosable_models = set(crushing_impact_controller.choosable_models())

        status_by_token = {}
        for token in state.tokens:
            effects = status_effects.active_effects(
                token, state.terrain_areas, turn_tracker, shooting_controller.last_ranged_attack_turn,
                greater_good=greater_good_controller,
                guide=guide_controller, doom=doom_controller,
                whispering_web=whispering_web_controller,
            )
            if effects:
                status_by_token[token] = effects

        greater_good_eligible_squads = get_greater_good_eligible_squads()
        greater_good_target_models = {token for token in state.tokens if token.squad in greater_good_eligible_squads}

        fire_overwatch_eligible_squads = get_fire_overwatch_eligible_squads()
        fire_overwatch_target_models = {token for token in state.tokens if token.squad in fire_overwatch_eligible_squads}

        # Defensive full clear: board_rect_screen/left_panel_rect/
        # right_panel_rect/reserves_panel_rect are sized to exactly tile the
        # whole window with no gaps, so nothing should ever actually show
        # through this - cheap enough to not be worth relying on that
        # holding exactly (e.g. across integer rounding) instead.
        screen.fill(config.BACKGROUND_COLOR)

        renderer.draw(
            board_surface, board, state.tokens, state.obstacles, turn_tracker.active_player,
            deployment_zones=state.deployment_zones, blood_decals=state.blood_decals,
            terrain_areas=state.terrain_areas,
        )
        # User request: always show what a TRANSPORT (18.02) is carrying,
        # not just while actively disembarking it - see
        # Renderer.draw_embarked_passengers()'s own docstring.
        renderer.draw_embarked_passengers(
            board_surface, board, state.tokens, state.embarked_squads, turn_tracker.active_player,
        )
        # Rules 03.02/20.04: show where the unit being placed could legally
        # end up (green) or not (red) - already while it's still being
        # dragged out of the Reserves panel (before it's even dropped), and
        # while fine-adjusting its models afterward. One representative
        # model of the squad, since they all share the same base size.
        placement_squad = (
            dragging_reserve_squad if dragging_reserve_squad is not None
            else setup_controller.setting_up_squad if setup_controller.state == setup.PLACING
            # Rule 03.01: a unit picked from the pre-game pool but not yet
            # dropped - same "show me where this may go before I commit"
            # window a reserves-panel drag has.
            else pregame_controller.selected_unit if pregame_controller.awaiting_drop
            else None
        )
        if placement_squad is not None:
            if placement_squad is pregame_controller.selected_unit and pregame_controller.awaiting_drop:
                position_valid_fn = lambda token, x_in, y_in: pregame_controller.position_valid(
                    placement_squad, token, x_in, y_in,
                )
                session_key = ("pregame-select", id(placement_squad))
            elif placement_squad is setup_controller.setting_up_squad:
                # Once PLACING has begun, the overlay paints the exact same
                # predicate SetupController.clamp_position() holds the drag
                # inside - one source of truth, so "green" and "the model is
                # allowed to stop here" cannot drift apart.
                position_valid_fn = setup_controller.placement_validator(placement_squad)
                session_key = ("setup", setup_controller.placement_generation)
            else:
                # Still being dragged out of the Reserves panel - nothing has
                # been dropped yet, so there is no placement to ask.
                position_valid_fn = lambda token, x_in, y_in: ingress_controller.position_valid(
                    placement_squad, token, x_in, y_in,
                )
                session_key = ("reserve-drag", id(placement_squad))
            # Which model to show it for matters now that a unit can have
            # mixed base sizes (an attached unit, rule 19.01): whichever one
            # is actually being dragged, else the largest base, whose legal
            # ground is a subset of every other model's and is therefore the
            # safe thing to show before you have picked one up.
            overlay_token = (
                input_manager.dragging_token
                if input_manager.dragging_token in placement_squad.models
                else max(placement_squad.models, key=lambda m: m.radius_in)
            )
            renderer.draw_placement_overlay(
                board_surface, board, overlay_token, position_valid_fn,
                (session_key, len(state.tokens)),
            )
        # User report: the objective label used to be drawn permanently and
        # constantly covered the terrain/models under it - now it only
        # slides out on hover over a small "i" icon, so the current mouse
        # position needs converting from window coords into the same
        # board-surface-native pixel space draw_objectives() draws in
        # (mirrors InputManager._local_pos()'s own board_offset+Camera
        # conversion), same as usual only while the mouse is actually over
        # the board.
        mouse_screen_pos = pygame.mouse.get_pos()
        if board_rect_screen.collidepoint(mouse_screen_pos):
            hover_local = (
                mouse_screen_pos[0] - board_rect_screen.x, mouse_screen_pos[1] - board_rect_screen.y,
            )
            objective_hover_native_px = camera.to_native_px(hover_local)
        else:
            objective_hover_native_px = None
        renderer.draw_objectives(
            board_surface, board, state.objectives, state.tokens, hover_native_px=objective_hover_native_px,
        )
        renderer.draw_visibility_highlight(board_surface, board, visible_models)
        renderer.draw_shoot_targets(board_surface, board, shoot_targets)
        renderer.draw_shoot_targets(board_surface, board, charge_target_models)
        renderer.draw_shoot_targets(board_surface, board, consolidate_target_models)
        renderer.draw_shoot_targets(board_surface, board, fight_target_models)
        renderer.draw_shoot_targets(board_surface, board, explosives_choosable_models)
        renderer.draw_shoot_targets(board_surface, board, explosives_target_models)
        renderer.draw_shoot_targets(board_surface, board, epic_challenge_choosable_models)
        renderer.draw_shoot_targets(board_surface, board, crushing_impact_target_models)
        renderer.draw_shoot_targets(board_surface, board, crushing_impact_choosable_models)
        renderer.draw_shoot_targets(board_surface, board, greater_good_target_models)
        renderer.draw_shoot_targets(board_surface, board, fire_overwatch_target_models)
        renderer.draw_assigning_model_highlight(board_surface, board, explosives_controller.acting_model)
        if attack_pair is not None:
            renderer.draw_attack_arrow(board_surface, board, attack_pair[0], attack_pair[1])
        if fight_attack_pair is not None:
            renderer.draw_attack_arrow(board_surface, board, fight_attack_pair[0], fight_attack_pair[1])
        renderer.draw_coherency_removal_highlight(board_surface, board, coherency_enforcer.pending_squad)
        renderer.draw_damage_choice_highlight(board_surface, board, shooting_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, fight_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, explosives_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, ishas_fury_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, grav_inhibitor_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, flickerjump_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, deadly_demise_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, transport_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, crushing_impact_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, fall_back_controller.pending_damage_choice)
        renderer.draw_assigning_model_highlight(board_surface, board, fight_assigning_model)
        renderer.draw_assigning_model_highlight(board_surface, board, shoot_assigning_model)
        renderer.draw_status_labels(board_surface, board, status_by_token)
        renderer.draw_selected_model(board_surface, board, movement_controller.selected_model)
        renderer.draw_forbidden_engagement_ranges(board_surface, board, movement_controller, state.tokens)
        renderer.draw_move_range(board_surface, board, movement_controller)
        renderer.draw_move_feedback(board_surface, board, movement_controller, input_manager.dragging_token)
        renderer.draw_measure_tool(board_surface, board, input_manager)

        # Später-Liste (Kamera-Scrolling/Viewport): board_surface itself was
        # just drawn at full (supersampled) native resolution, completely
        # unaware of zoom/pan (see the comment where it's created, above) -
        # this is the one place that actually applies the camera, by scaling
        # whichever native sub-rect it currently selects into the screen's
        # board area. smoothscale() (not the faster nearest-neighbor
        # scale()) is deliberate - User report ("alles ist total verpixelt,
        # wenn ich reinzoome"): once zoom pushes past what RENDER_SUPERSAMPLE
        # actually has real detail for, this turns the remainder into a soft
        # blur instead of hard blocky squares - profiled as costing no more
        # than scale() would here, so there's no performance tradeoff in
        # preferring it.
        #
        # camera.dest_rect() (not board_rect_screen's own full size) is the
        # actual destination - User follow-up ("ich würde gerne noch weiter
        # rauszoomen können, sodass ich das ganze Spielfeld sehen kann"):
        # zooming out past DEFAULT_ZOOM reveals a crop whose own aspect
        # ratio no longer matches the screen's, so it's letterboxed
        # (dest_rect() shrinks/centers within board_rect_screen) rather than
        # non-uniformly stretched to fill it, exactly as camera.py's
        # dest_rect() docstring lays out; at DEFAULT_ZOOM and above it's
        # simply the full board_rect_screen, unchanged from before.
        camera_view = board_surface.subsurface(camera.visible_rect())
        dest = camera.dest_rect()
        scaled = pygame.transform.smoothscale(camera_view, (dest.width, dest.height))
        screen.blit(scaled, (board_rect_screen.x + dest.x, board_rect_screen.y + dest.y))

        action_panel.draw(
            screen, left_panel_rect, movement_controller, shooting_controller, coherency_enforcer,
            charge_controller, pile_in_controller, fight_controller, consolidate_controller,
            retro_thrusters_controller,
            battle_shock_controller, dice_manager, command_reroll_controller, explosives_controller,
            setup_controller, ingress_controller, transport_controller, epic_challenge_controller,
            insane_bravery_controller, crushing_impact_controller, firing_deck_controller,
            greater_good_controller, fall_back_controller, fire_overwatch_controller,
            pregame_controller, arrokon_controller, shortened_blade_controller,
            torchstar_controller, unbridled_carnage_controller, ere_we_go_controller,
            tactical_acumen_controller,
            flickerjump_controller,
            battle_focus_pool,
            # By keyword on purpose: every argument above is POSITIONAL, so a new
            # one added mid-signature silently shifts them all - a mistake this
            # call site has already caused once (see CLAUDE.md).
            presentiment_controller=presentiment_controller,
            fate_inescapable_controller=fate_inescapable_controller,
        )
        # Drawn after the left panel itself (so their expanded/slid-out
        # state renders on top of the board, not underneath the panel) but
        # anchored off left_panel_rect - see MissionCardsOverlay's docstring.
        mission_cards_overlay.draw(screen, left_panel_rect, mission_controller)
        game_status_panel.draw(screen, right_panel_rect, turn_tracker, command_points, mission_controller,
                               battle_focus_pool, fate_dice_pool)
        # config.LOG_HEIGHT is what the log wants; the Game Status panel above
        # it gets the room it needs first. Clamped against that panel's real
        # button rect (drawn one line above, so it is this frame's) rather than
        # against a measured constant - the panel grows with its content, and a
        # log that covers the "Next Phase" button leaves no way to advance the
        # phase at all. Shrinking only: on a tall screen nothing is clamped.
        button = game_status_panel.button_rect
        log_top = right_panel_rect.bottom - config.LOG_HEIGHT
        if button is not None:
            log_top = max(log_top, button.bottom + config.LOG_GAP_BELOW_STATUS_PANEL)
        log_rect.update(right_panel_rect.x, log_top, right_panel_rect.width,
                        right_panel_rect.bottom - log_top)
        log_panel.draw(screen, log_rect, game_log)
        # Rule 20.03/20.04 (Ingress) and 18.03/18.04 (Disembark) both only
        # ever happen in the Movement phase - the panel's visibility is a
        # TIMING question (is this even the right moment to place a unit?),
        # not an availability one (whether reserves happen to be empty
        # right now) - it stays visible while a placement is still actively
        # in progress as a safety net, e.g. if the phase somehow changed
        # mid-drag.
        reserves_panel_visible = (
            turn_tracker.phase == PHASE_MOVEMENT
            or setup_controller.state == setup.PLACING
            or dragging_reserve_squad is not None
            or rapid_ingress_controller.pending_squad is not None
            # Rule 03.01: during the pre-game the same strip is the pool of
            # units still waiting to be deployed.
            or pregame_controller.is_active
        )
        # Rule 15.07: outside the Movement phase, the panel would otherwise
        # have no business being draggable at all - showing every reserves
        # squad here (not just the one CP was just spent on) would let
        # either player sneak in an ordinary Ingress move for some
        # unrelated unit, since IngressController.can_ingress() only checks
        # battle round, never phase. Restrict to exactly the squad this
        # window is actually for.
        if pregame_controller.state == pregame.DEPLOYING:
            # The undeployed pool, NOT state.reserves - Strategic Reserves
            # (20.01) is a different thing that these units were explicitly
            # not declared into. Pinned to whoever is currently placing, so
            # the human cannot pick up the AI's units.
            reserves_to_show = pregame_controller.pending_units(pregame_controller.active_player)
            reserves_panel.active_owner = pregame_controller.active_player
        else:
            reserves_to_show = (
                [rapid_ingress_controller.pending_squad] if rapid_ingress_controller.pending_squad is not None
                else state.reserves
            )
        reserves_panel.draw(
            screen, reserves_panel_rect, reserves_to_show,
            dragging_squad=dragging_reserve_squad, visible=reserves_panel_visible,
            # Rule 15.07: reserves_to_show is already narrowed down to the
            # ONE squad this Rapid Ingress window is for in that case - it
            # must stay visible/draggable regardless of which Player 1/
            # Player 2 tab happens to be selected, so the panel's own
            # owner filter is switched off for exactly that case.
            filter_by_owner=rapid_ingress_controller.pending_squad is None,
        )
        if dragging_reserve_squad is not None:
            renderer.draw_reserve_drag_ghost(screen, dragging_reserve_squad, pygame.mouse.get_pos())
        player_banner.draw(
            screen, coherency_enforcer, battle_shock_controller=battle_shock_controller,
            turn_tracker=turn_tracker, all_tokens=state.tokens,
        )
        # User: "meldung, dass ki ein stratagem benutzt und der roll dafür
        # kommen gleichzeitig, sollen aber eigentlich hintereinander kommen.
        # erst meldung, dann roll." - a Stratagem's own roll (Explosives' 6D6
        # in the reported case) is the CONSEQUENCE of the notice, so it may
        # not share the screen with it. Gated on exactly the overlays that
        # already outrank a pending roll in the event chain above (turn
        # banner, turn plan, Stratagem notice, WAAAGH! notice): while any of
        # them is up the dice can't be clicked away anyway, so drawing them
        # underneath only ever showed a roll the human wasn't allowed to
        # answer yet. DicePanel.draw() holds its animation clocks for the
        # duration, so the roll still plays its full slide-in/tumble
        # afterwards instead of jumping straight to the result.
        dice_panel.draw(
            screen, dice_manager, selecting_die=command_reroll_controller.selecting_die,
            bounds_rect=board_rect_screen,
            suppressed=(
                stratagem_notice_overlay.is_pending or waaagh_notice_overlay.is_pending
                or turn_start_overlay.is_pending or turn_plan_overlay.is_pending
            ),
        )
        decision_overlay.draw(screen, decision_manager)
        # Drawn last (on top of everything else, including the decision
        # overlay) - matches its own top input priority above.
        stratagem_notice_overlay.draw(screen)
        waaagh_notice_overlay.draw(screen)
        turn_plan_overlay.draw(screen)
        turn_start_overlay.draw(screen)

        ctrl_held = pygame.key.get_mods() & (pygame.KMOD_LCTRL | pygame.KMOD_RCTRL)
        if (
            ctrl_held and input_manager.hovered_token is not None
            and not decision_manager.is_pending and not stratagem_notice_overlay.is_pending
            and not waaagh_notice_overlay.is_pending
            and not turn_start_overlay.is_pending and not turn_plan_overlay.is_pending
        ):
            unit_datacard.draw(
                screen, input_manager.hovered_token, pygame.mouse.get_pos(),
                transport_controller=transport_controller,
            )

        try:
            pygame.mouse.set_cursor(
                pygame.SYSTEM_CURSOR_HAND if input_manager.hovered_token is not None else pygame.SYSTEM_CURSOR_ARROW
            )
        except pygame.error:
            pass  # e.g. the headless "dummy" video driver doesn't support system cursors

        if ai_memory.is_planning:
            # The planning call runs on its own thread now (see ai/agent_driver.
            # py's _maybe_generate_turn_plan()), so this frame is still being
            # drawn while it's in flight - which is exactly why it needs an
            # indicator that visibly moves. A static badge during a 30-second
            # wait is what a hung game looks like; animated dots are the signal
            # that the window is alive and something is still happening.
            dots = "." * (1 + int(time.monotonic() * 2) % 3)
            badge_surf = auto_play_font.render(f"Player 2 is planning its turn{dots}", True, (20, 20, 20))
            badge_rect = badge_surf.get_rect(topleft=(config.LEFT_PANEL_WIDTH + 12, 12))
            pygame.draw.rect(screen, (255, 210, 90), badge_rect.inflate(16, 10), border_radius=6)
            screen.blit(badge_surf, badge_rect)
        elif ai_auto_play:
            # Persistent reminder that Player 2 is driving itself right now
            # (Shift+A toggles it) - easy to lose track of otherwise, since
            # unlike the "Claude is thinking..." overlay this has no single
            # moment it flashes at.
            badge_surf = auto_play_font.render("Player 2: AUTO-PLAY (Shift+A to stop)", True, (20, 20, 20))
            badge_rect = badge_surf.get_rect(topleft=(config.LEFT_PANEL_WIDTH + 12, 12))
            pygame.draw.rect(screen, (255, 210, 90), badge_rect.inflate(16, 10), border_radius=6)
            screen.blit(badge_surf, badge_rect)

        pygame.display.flip()
        clock.tick(config.FPS)

    game_log.close()
    pygame.quit()


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="WH40k board")
    parser.add_argument(
        "--map", dest="map_key", default=None,
        help='which battlefield to play on: "map1" (44"x60" portrait, the default) '
             'or "map2" (60"x44" landscape). The bare number works too ("--map 2"). '
             "Without this, config.MAP decides.",
    )
    parser.add_argument(
        "--no-deployment", dest="pregame", action="store_false", default=None,
        help="skip rule 03.01's pre-game sequence and start from the legacy "
             "already-deployed scene (the hand-tuned positions in game/maps.py). "
             "Without this, config.PREGAME_DEPLOYMENT decides.",
    )
    parser.add_argument(
        "--load", dest="load_scene", default=None, metavar="FILE",
        help="open a board position saved with F9 instead of setting up a new "
             "battle - every model back where it stood, same round, same phase, "
             "same turn. Skips the pre-game sequence.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    _args = _parse_args(sys.argv[1:])
    if _args.pregame is not None:
        config.PREGAME_DEPLOYMENT = _args.pregame
    _map_key = _args.map_key
    if _args.load_scene is not None:
        config.LOAD_SCENE = _args.load_scene
        # The snapshot knows which board it was taken on, so --load does not
        # also need --map. An explicit --map still wins, and main() then
        # refuses the mismatch rather than placing the army on the wrong board.
        if _map_key is None:
            _map_key = scene_io.read(_args.load_scene).get("map")
    main(map_key=_map_key)
