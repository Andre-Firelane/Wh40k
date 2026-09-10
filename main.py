import argparse
import os
import sys
import time

import pygame

from ai import deployment_ai
from ai import observation as ai_observation
from ai.agent_driver import AIMemory, take_one_action
from ai.claude_agent import ClaudeAgent
# from ai.mock_agent import MockAgent  # free/offline alternative - no API key or network needed
from game import attached_units, battle_focus, biomes, charge, config, consolidate, crushing_impact, enhancements, epic_challenge, explosives, fall_back, fight, firing_deck, greater_good, line_of_sight, maps, movement, overwatch, pregame, setup, shooting, starflare_ignition, status_effects, strands_of_fate
from game import base_contact
from game import damage_pick, montka, prompt_rule, unit_pick
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
from game.unmodified_six_controller import UnmodifiedSixController
from game.env import load_dotenv
from game.explosives import ExplosivesController
from game.fall_back import FallBackController
from game.fieldcraft import apply_fieldcraft
from game.grot_riggers import apply_grot_riggers
from game.thievin_scavengers import ThievinScavengersController
from game import waaagh as waaagh_module
from game.waaagh import WaaaghController
from game.stratagems import StratagemController
from game.consolidate import ConsolidateController
from game.counteroffensive import CounteroffensiveController
from game.deadly_demise import DeadlyDemiseController
from game.decision import DecisionManager
from game.dice import ADVANCE_ROLL, DiceManager
from game.crushing_impact import CrushingImpactController
from game.epic_challenge import EpicChallengeController
from game.fight import FightController
from game.insane_bravery import InsaneBraveryController
from game.game_log import GameLog
from game.missions import MissionController
from game.battle_stats import BattleStats
from game.secondary_missions import SecondaryMissionController
from game.primary_missions import PrimaryMissionController
from game.actions import ActionController
from game.ingress import IngressController
from game.firing_deck import FiringDeckController
from game.game_state import GameState
from game.greater_good import GreaterGoodController
from game.heroic_intervention import HeroicInterventionController
from game.homing_beacon import HomingBeaconController
from game.movement import MovementController
from game import neocapacitor_shields, render_resolution, rites_of_feasting, scene_io
from game import ynnari_abilities
from game.ynnari_abilities import HeraldOfYnneadController
from game.enh_echoes_of_ulthanesh import EchoesOfUlthaneshController
from game.enh_ethereal_pathway import EtherealPathwayStep
from game.enh_firstdrawn_blade import FirstdrawnBladeStep
from game.enh_higher_duty import HigherDutyController
from game.enh_phoenix_gem import PhoenixGemController
from game.enh_gift_of_foresight import GiftOfForesightDiscount
from game.enh_guiding_presence import GuidingPresenceController
from game.enh_lucid_eye import LucidEyeController
from game.enh_protector_of_the_paths import ProtectorOfThePathsDiscount
from game.enh_torc_of_morai_heg import TorcOfMoraiHegSurcharge
from game.enh_rune_of_mists import RuneOfMistsController
from game.enh_spirit_stone_of_raelyth import SpiritStoneOfRaelythController
from game.path_of_the_warrior import PathOfTheWarriorController
from game.shepherds_of_the_dead import ShepherdsOfTheDeadController
from game.word_of_the_phoenix import WordOfThePhoenixController
from game.inevitable_death import InevitableDeathController
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
from game.reanimation_protocols import ReanimationProtocolsController
from game.return_placement import ReturnPlacementController
from game.technomancer import TechnomancerController
from game.resurrection_orb import ResurrectionOrbController
from game.mortal_wound_abilities import (
    CrimsonHarvestController, KrootLinebreakersController, LivingLightningController, MatterAbsorptionController,
)
from game.wraith_form import WraithFormController
from game.mechanical_augmentation import AtomicEnergyManipulatorController
from game.nurgles_gift import NurglesGiftController
from game.deadly_vectors import DeadlyVectorsController
from game.barrage_of_filth import BarrageOfFilthController
from game.curse_of_the_walking_pox import CurseOfTheWalkingPoxController
from game.fevered_strategist import FeveredStrategistDiscount
from game.lethal_ichor import LethalIchorController
from game.mortal_wound_abilities import EaterPlagueController
from game.pestilent_fallout import PestilentFalloutController
from game.spore_laced_shock_waves import SporeLacedShockWavesController
from game.dlc_blooming_pestilence import BloomingPestilenceController
from game.dlc_grim_reapers import GrimReapersController
from game.dlc_mortarions_teachings import MortarionsTeachingsController
from game.dlc_sickening_impact import SickeningImpactController
from game.dlc_signal_pox import SignalPoxController
from game.dlc_undying_spite import UndyingSpiteController
from game.fated_hero import FatedHeroController
from game.malevolent_souls import MalevolentSoulsController
from game import plagues
from game.my_will_be_done import MyWillBeDoneDiscount
from game.advanced_scouting import AdvancedScoutingController
from game.drone_harassment import DroneHarassmentController
from game.targeting_array import TargetingArrayController
# The T'au detachment Enhancements that need a per-battle controller or a
# pre-battle step. game/enhancements.py is the registry that says who bears one
# and gates each on the detachment actually fielded; these are the rules.
from game import enh_prototype_weapons, enh_strategic_conqueror
from game.enh_admired_leader import AdmiredLeaderController
from game.enh_light_of_clarity import LightOfClarityController
from game.enh_stave_of_kurnous import StaveOfKurnousController
from game.enh_internal_grenade_racks import InternalGrenadeRacksController
from game.enh_prototype_weapon_system import PrototypeWeaponSystemController
from game.enh_puretide_neurochip import PuretideNeurochipController
from game.enh_solid_image_projection import SolidImageProjectionStep
from game.enh_strike_swiftly import StrikeSwiftlyStep
from game.enh_student_of_kauyon import StudentOfKauyonStep
from game.enh_unmasking_suite import UnmaskingSuiteController
from game.airborne_agility import AirborneAgilityController
from game.ride_the_wind import RideTheWindController
from game.bounty_hunters import BountyHuntersController
from game.kroot_packmates import KrootPackmatesController
from game.oversight_drone import OversightDroneController
from game import loping_pounce
from game import move_exceptions
from game.coordinated_leadership import CoordinatedLeadershipController
from game.fire_and_fade import FireAndFadeController
from game.chronometron import ChronometronController
from game.evasion_engrams import EvasionEngramsController
from game.hyperspace_hunters import HyperspaceHuntersController
from game.cryptothralls import SystematicVigourController
from game.psychomancer import (HarbingerOfDespairController,
                               NightmareShroudController)
from game.the_stars_are_right import TheStarsAreRightController
from game.root_of_honour import RootOfHonourController
from game.war_leader import WarLeaderDiscount
from game import overwhelming_obliteration, plasmacyte
from game.protocol_hungry_void import HungryVoidController
from game.protocol_sudden_storm import SuddenStormController
from game.protocol_conquering_tyrant import ConqueringTyrantController
from game.protocol_undying_legions import UndyingLegionsController
from game.protocol_eternal_revenant import EternalRevenantController
from game.protocol_vengeful_stars import VengefulStarsController
from game import protocol_sudden_storm
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
from game import unshrouded_truth as unshrouded_truth_mod
from game.unshrouded_truth import UnshroudedTruthController
from game.path_of_the_outcast import PathOfTheOutcastController
from game import target_acquisition
from game.target_acquisition import TargetAcquisitionController
from game.crystalline_targeting import CrystallineTargetingController
from game.monofilament_snare import MonofilamentSnareController, SHADOW_WEAVER_NAME
from game.monofilament_web import MonofilamentWebController, DOOMWEAVER_NAME
from game.misfortune import MisfortuneController
from game.face_of_death import FaceOfDeathController
from game.panicked_quarry import PanickedQuarryController
from game import corsair_abilities
from game.corsair_abilities import PiraticalRaidersController
from game.fury_of_the_void import FuryOfTheVoidController, DREAD_OF_THE_DEEP_VOID_NAME
from game.hallucinogen_grenades import HallucinogenGrenadesController
from game.prince_of_corsairs import PrinceOfCorsairsStep
from game.raid_and_run import RaidAndRunController
from game.drakolithe import DrakolitheController
from game.elemental_ensnarement import ElementalEnsnarementController
from game.harvester_of_souls import HarvesterOfSoulsController
from game.indomitable_strength_of_will import IndomitableStrengthOfWillController
from game.path_of_command import PathOfCommandDiscount
from game.superlative_strategist import SuperlativeStrategistController
from game.spiritseer import SpiritMarkController, TearsOfIshaController
from game.sonic_destruction import SonicDestructionController
from game.unquenchable_resolve import UnquenchableResolveController
from game.cloudstrider import CloudstriderController
from game.grenade_pack_flyover import GrenadePackFlyoverController
from game.psychic_shield import PsychicShieldController
from game.tactical_acumen import TacticalAcumenController
from game.flickerjump import FlickerjumpController
from game.stim_injectors import StimInjectorsController
from game.support_turret import SupportTurretController
from game.transport import TransportController
from game.squad import Squad
from game.token import Token
from game import army_lists
from game import pestilent_fallout
from game.factions.faction import player_factions as derive_player_factions
from game.input_handler import InputManager
from game.renderer import Renderer
from game.shooting import ShootingController
from game.turn import TurnTracker, PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE, PHASE_FIGHT
from game.unbridled_carnage import UnbridledCarnageController
from game.ui.action_panel import ActionPanel
from game.ui.army_select import ArmySelectScreen
from game.auxiliary_cadre import AuxiliaryCadreController
from game.proactive_stratagems import ProactiveStratagems
from game import windrider_daring_riders, windrider_death_from_on_high
from game import windrider_focused_firepower, windrider_overflight
from game import windrider_spiralling_evasion, windrider_wind_of_blades
from game.windrider_daring_riders import DaringRidersController
from game.windrider_death_from_on_high import DeathFromOnHighController
from game.windrider_focused_firepower import FocusedFirepowerController
from game.windrider_overflight import OverflightController
from game.windrider_spiralling_evasion import SpirallingEvasionController
from game.windrider_wind_of_blades import WindOfBladesController
from game import martial_grace
from game import warhost_blitzing_firepower, warhost_feigned_retreat
from game import warhost_fire_and_fade, warhost_lightning_fast_reactions
from game import warhost_webway_tunnel
from game.skyborne_sanctuary import SkyborneSanctuaryController
from game.warhost_blitzing_firepower import BlitzingFirepowerController
from game.warhost_feigned_retreat import FeignedRetreatController
from game.warhost_fire_and_fade import WarhostFireAndFadeController
from game.warhost_lightning_fast_reactions import LightningFastReactionsController
from game.warhost_webway_tunnel import WebwayTunnelController
from game import conclave_blades_from_beyond, conclave_seers_eye
from game import conclave_soul_bridge, conclave_wraithbone_armour
from game.conclave_blades_from_beyond import BladesFromBeyondController
from game.conclave_crushing_strides import CrushingStridesController
from game.conclave_seers_eye import SeersEyeController
from game.conclave_soul_bridge import SoulBridgeController
from game.conclave_spirit_token import SpiritTokenController
from game.conclave_wraithbone_armour import WraithboneArmourController
from game import aspect_doom_inescapable, aspect_preternatural_precision
from game import aspect_warrior_focus
from game.aspect_doom_inescapable import DoomInescapableController
from game.aspect_khaines_vengeance import KhainesVengeanceController
from game.aspect_preternatural_precision import PreternaturalPrecisionController
from game.aspect_to_their_final_breath import ToTheirFinalBreathController
from game.aspect_warrior_focus import WarriorFocusController
from game.damage_resolution import MortalWoundAllocationSession
from game.armoured_layered_wards import LayeredWardsController
from game import armoured_layered_wards, armoured_soulsight
from game.armoured_soulsight import SoulsightController
from game.armoured_vectored_engines import VectoredEnginesController
from game import outcast_casting_back_the_veil
from game.outcast_casting_back_the_veil import CastingBackTheVeilController
from game.outcast_eldritch_suppression import EldritchSuppressionController
from game.outcast_nomads_of_the_hidden_way import NomadsOfTheHiddenWayController
from game import (guardian_blades_of_asuryan, guardian_shield_nodes,
                  guardian_time_to_strike, guardian_warding_salvoes)
from game.guardian_blades_of_asuryan import BladesOfAsuryanController
from game.guardian_cost_of_victory import CostOfVictoryController
from game.guardian_shield_nodes import ShieldNodesController
from game.guardian_time_to_strike import TimeToStrikeController
from game.guardian_vauls_vengeance import VaulsVengeanceController
from game.guardian_warding_salvoes import WardingSalvoesController
from game.kauyon_coordinate_to_engage import CoordinateToEngageController
from game.kauyon_point_blank_ambush import PointBlankAmbushController
from game.kauyon_tempting_trap import TemptingTrapController
from game.kauyon_wall_of_mirrors import WallOfMirrorsController
from game.kauyon_photon_grenades import PhotonGrenadesController
from game.kauyon_combat_embarkation import CombatEmbarkationController
from game.montka_aggressive_mobility import AggressiveMobilityController
from game.montka_combat_debarkation import CombatDebarkationController
from game.montka_counterfire_defence import CounterfireDefenceController
from game.montka_focused_fire import FocusedFireController
from game.montka_pinpoint_counter_offensive import PinpointCounterOffensiveController
from game.montka_pulse_onslaught import PulseOnslaughtController
from game.aac_autoreactive_camouflage import AutoreactiveCamouflageController
from game.aac_marker_beacon import MarkerBeaconController
from game.aac_microdrone_support import MicrodroneSupportController
from game.aux_alien_expertise import AlienExpertiseController
from game.aux_experimental_modifications import ExperimentalModificationsController
from game.aux_guided_fire import GuidedFireController
from game.epc_experimental_ammunition import (
    MODE_STRENGTH, MODE_STRENGTH_AP_HAZARDOUS, ExperimentalAmmunitionController)
from game import detachments
from game import aura_ruler
from game.ui.map_select import MapSelectScreen
# The module AND the class, aliased apart on purpose: main() holds a local
# called `game_menu`, and a local shadowing its own module inside a
# 4000-line function is exactly CLAUDE.md's error class 23 waiting to happen.
from game.ui import game_menu as game_menu_module
from game.ui.game_menu import GameMenu
from game import ai_mode
from game import battle_stats as battle_stats_module
from game.ui.ai_busy_badge import AiBusyBadge, ai_mode_toggle_rect, draw_ai_mode_toggle
from game.ui import round_progress_bar
from game.ui.decision_overlay import DecisionOverlay
from game.ui.stratagem_notice_overlay import StratagemNoticeOverlay
from game.ui.waaagh_notice_overlay import WaaaghNoticeOverlay
from game.ui.turn_start_overlay import TurnStartOverlay
from game.ui.fight_warning_overlay import FightWarningOverlay
from game.ui.turn_plan_overlay import TurnPlanOverlay
from game.ui.dice_panel import DicePanel
from game.ui.army_rules_overlay import ArmyRulesOverlay
from game.ui.unit_stats_overlay import UnitStatsOverlay
from game.ui import unit_stats_overlay
from game.ui.game_status_panel import GameStatusPanel
from game.ui.log_panel import LogPanel
from game.ui.mission_cards import MissionCardsOverlay
from game.ui.mission_draw_overlay import MissionDrawOverlay
from game.ui.battle_end_overlay import BattleEndOverlay
from game.ui.player_banner import PlayerBanner
from game.ui.reserves_panel import ReservesPanel
from ai import connection as ai_connection
from game.ui.ai_offline_overlay import AIOfflineOverlay
from game.ui.stratagem_tooltip import StratagemTooltip
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


def _all_squads(state, pregame_controller=None):
    """Every unit in the battle, wherever it currently is - including the
    ones the pre-game sequence (rule 03.01) has not deployed yet, which are
    in neither state.tokens nor state.reserves until they are placed.
    _player_squads() alone would therefore see an empty board for the whole
    of deployment."""
    squads = _player_squads(state, "Player 1") + _player_squads(state, "Player 2")
    if pregame_controller is not None:
        for owner in ("Player 1", "Player 2"):
            for squad in pregame_controller.army(owner):
                if squad not in squads:
                    squads.append(squad)
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
        # Every engine-wired Enhancement, off the registry rather than the one
        # named module this used to know about: nineteen are wired now, and a
        # startup log that mentions only the first one is worse than none.
        for name in enhancements.granted_names(squad):
            spec = enhancements.get(name)
            bearers = enhancements.enhancement_models(squad, name)
            # A unit-level Enhancement ("STEALTH BATTLESUITS unit only") marks
            # every model, so it is reported as the UNIT rather than as one
            # line per model - which would otherwise print ten identical lines.
            who = (squad.name if spec.unit_level
                   else f"{bearers[0].profile.name} in {squad.name}")
            lines.append(f"{owner}: {who} carries the {name} Enhancement "
                         f"({spec.points} pts).")
    return lines


def run(map_key=None):
    """The APPLICATION: a menu, a battle, and back around again.

    main() is ONE BATTLE - it builds a board, an army pair and forty-odd
    controllers as its own locals, and they die with it. That is what makes
    "Start New Game" from the in-game menu cheap: a genuinely new map and new
    armies is only reachable by LEAVING main() and calling it again, and there
    is no teardown to write because there is no state to tear down.

    WHY THE MENU LIVES HERE AND NOT IN main(). All ten headless harnesses call
    main.main() directly. Putting the menu one level up means a screen that
    waits for a click is simply not on their path - so unlike MAP_SELECT and
    ARMY_SELECT, START_MENU needs no opt-out in ten files and no source guard
    to make sure a future harness remembers one.

    What has to be reset between battles is short, and this is the whole list:
    config.LOAD_SCENE (else "new game" would reopen the same save for ever) and
    the map key (else --map's answer would be re-applied to a battle that was
    supposed to ask). Everything else is either a main() local or is rewritten
    from scratch each run by maps/army_lists/detachments.apply_to_config().
    config.BIOME and the two army settings deliberately survive: they are the
    defaults the pickers open on, so the second battle opens on the first
    battle's choices."""
    load_dotenv()
    pygame.init()

    # The one window, opened once. See main()'s own note on why it must not be
    # re-created per battle.
    fullscreen = config.FULLSCREEN
    pygame.display.set_mode((0, 0), pygame.FULLSCREEN if fullscreen else 0)
    pygame.display.set_caption("WH40k Board - Step 4")
    screen = pygame.display.get_surface()

    cli_map_key = map_key
    while True:
        # Skipped when --load named a file: that is already an answer to the
        # question this screen asks, the same way --map answers the map picker.
        if config.START_MENU and not config.LOAD_SCENE:
            path = scene_io.newest()
            answer = GameMenu(save_path=path,
                              save_note=scene_io.summary(path) if path else None).run(screen)
            if answer == game_menu_module.QUIT:
                break
            if answer == game_menu_module.RESUME:
                config.LOAD_SCENE = path
                map_key = scene_io.map_key_in(path)

        outcome = main(map_key=map_key)

        if outcome != game_menu_module.NEW_GAME:
            break
        # A restart is a NEW battle: never the same save again, and back to
        # asking unless the command line already answered.
        config.LOAD_SCENE = None
        map_key = cli_map_key

    pygame.quit()


def main(map_key=None):
    load_dotenv()  # picks up ANTHROPIC_API_KEY from the project's local .env, if present
    pygame.init()

    # Fullscreen is now the default display mode (User: "es wird zeit, einen
    # vollbild modus einzuführen (default)"). The window is sized to
    # whatever the desktop resolution actually is - (0, 0) tells SDL to use
    # the current display mode - instead of a size computed ahead of time
    # from the board's own pixel dimensions like the old fixed-window layout
    # did. `board` is built further down, once board_rect_screen is known -
    # its render resolution is DERIVED from that rect (see
    # game/render_resolution.py), so it cannot be created before the window
    # exists any more.
    #
    # THIS NOW COMES FIRST, ahead of the map. It used to sit below
    # apply_to_config(), which was fine while the map was a setting - but the
    # map is picked on a screen now (User: "Vor der Fraktion würde ich jetzt
    # allerdings gerne noch die Map auswählen"), and a screen needs a window to
    # be drawn on. Nothing between here and apply_to_config() reads a board
    # dimension, which is what makes the swap safe.
    # ONE WINDOW FOR THE WHOLE APPLICATION. run() opens it before the menu, so
    # by the time a battle starts there already is one; a harness that calls
    # main() directly still gets one here. Calling set_mode() again per battle
    # would re-create the display surface underneath every convert_alpha()'d
    # sprite game/sprites.py has cached at module level - those caches are
    # keyed by path and are meant to outlive a battle, so the display they
    # were converted against has to outlive it too.
    fullscreen = config.FULLSCREEN
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN if fullscreen else 0)
        pygame.display.set_caption("WH40k Board - Step 4")

    # WHICH BATTLEFIELD this run is played on (User: "ich hätte gerne eine 2te
    # map ... es soll zusätzlich existieren"). Board size, deployment zones,
    # terrain, and on a small board even WHICH units are fielded
    # (BattleMap.army_roster) all come from it - see game/maps.py - so it is
    # asked before anything else, and its tiles show the board itself, rendered
    # (see game/ui/map_preview.py).
    #
    # Skipped when --map named one, and when a saved scene is being opened:
    # that snapshot records the board it was taken on, and offering a choice
    # that would then be overruled is worse than not offering one.
    if map_key is None and config.MAP_SELECT and not config.LOAD_SCENE:
        map_key = MapSelectScreen(default=config.MAP).run(screen)
        if map_key is None:
            # Abandoning a pre-battle screen answers the MENU, not the process:
            # run() owns the window's lifetime now, so main() never calls
            # pygame.quit() itself.
            return game_menu_module.QUIT

    # apply_to_config() has to happen before ANY of the board dimensions below
    # are read: the whole engine and the AI read config.BOARD_WIDTH_IN/
    # BOARD_HEIGHT_IN directly.
    battle_map = maps.apply_to_config(maps.get(map_key if map_key is not None else config.MAP))
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
    # WHO PLAYS WHICH LIST, asked before anything else is built - the units,
    # the deployment zones' occupants, the detachment settings and every
    # controller below all follow from it (User: "ich hätte gerne noch, bevor
    # das Pre game losgeht, eine Auswahlmöglichkeit für die Völker/listen").
    #
    # ONE HUMAN ANSWERS BOTH STEPS. User: "Aber ich wähle für die KI. Die KI
    # soll nicht selber wählen." - Player 2's list is assigned to the AI here,
    # never picked by it, which is also why this runs before the agent exists
    # at all.
    #
    # Skipped when a saved scene is being opened: that snapshot's squad names
    # already say which lists were on the table, and offering a choice that
    # would then be overruled is worse than not offering one (see the armies=
    # note in game/scene_io.py).
    armies = army_lists.configured_choices()
    if config.LOAD_SCENE:
        # A snapshot records which lists were on the table (see
        # scene_io.armies_in()); without adopting them, every unit name in it
        # would miss and the restore would place nothing. A file written before
        # that was recorded returns None and falls back to the settings, which
        # is what it always did.
        armies = scene_io.armies_in(config.LOAD_SCENE) or armies
    if config.ARMY_SELECT and not config.LOAD_SCENE:
        chosen = ArmySelectScreen(defaults=armies).run(screen)
        if chosen is None:
            return game_menu_module.QUIT
        armies = chosen
    # Writes the army keys, and each list's DEFAULT detachment through
    # game/detachments.py - the one part of a list that genuinely cannot be
    # derived from the units on the board. Has to happen before ANY unit is
    # built, same as maps.apply_to_config() above.
    army_lists.apply_to_config(armies)

    # Which detachments each player fields comes from the LIST - it is part of
    # how the army was written down, not a choice made at the table. A
    # selection screen was built here and taken back out: you cannot swap
    # detachment before a game, and an army may field several at once out of a
    # shared Detachment Points budget, which is a list-building matter rather
    # than a pre-battle one. Still written into config, because a detachment
    # cannot be derived from the units - see game/detachments.py.
    detachments.apply_to_config(armies)

    # The round progress bar owns a full-width row at the very top, and the
    # three columns start underneath it (user: "fuer die Anzeige der aktuellen
    # runde haette ich gerne anstatt der Zahl einen schoenen Fortschrittsbalken
    # am oberen Bildschirmrand"). A ROW rather than chrome drawn over the
    # board, which was the first attempt and drew two reports: "der balken
    # ueberdeckt die map" and "die map schliesst jetzt nicht mehr links und
    # rechts mit den 2 seiten panels ab" - overlaying the board moved the map's
    # top edge below the panels' and cost map instead of taking space.
    top_bar_height = round_progress_bar.BAR_HEIGHT
    top_row_height = window_height - config.RESERVES_PANEL_HEIGHT - top_bar_height
    available_width = window_width - config.LEFT_PANEL_WIDTH - config.RIGHT_PANEL_WIDTH
    board_rect_screen = pygame.Rect(config.LEFT_PANEL_WIDTH, top_bar_height, available_width, top_row_height)
    left_panel_rect = pygame.Rect(0, top_bar_height, config.LEFT_PANEL_WIDTH, top_row_height)
    right_panel_rect = pygame.Rect(window_width - config.RIGHT_PANEL_WIDTH, top_bar_height, config.RIGHT_PANEL_WIDTH, top_row_height)

    # Später-Liste (Kamera-Scrolling/Viewport): board_surface used to be a
    # direct subsurface of `screen` (drawing onto it WAS drawing onto the
    # screen, 1:1, no scaling). It's now a standalone offscreen Surface,
    # always rendered at full (supersampled) resolution - the final display
    # step (see the render loop below) scales whichever Camera-chosen
    # sub-rect of it is currently visible down/up to fill board_rect_screen.
    # Every renderer.draw_*(board_surface, ...) call and every board-inch/
    # pixel conversion elsewhere is unaffected by any of this - only the
    # camera's own to_native_px()/visible_rect() know zoom/pan even exists.
    #
    # The resolution it is rendered at is derived from board_rect_screen and
    # the map's own size rather than configured - see
    # game/render_resolution.py (User: "kannst du die auflösung der sprites
    # noch erhöhen. das ist momentan alles noch sehr pixelig"). At this
    # resolution the camera never has to invent a pixel: at MAX_ZOOM one
    # rendered pixel is exactly one screen pixel.
    render_ppi = render_resolution.board_pixels_per_inch(
        board_rect_screen.width, board_rect_screen.height,
        config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN,
    )
    board = Board(config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN, render_ppi)
    board_surface = pygame.Surface((board.width_px, board.height_px))
    camera = Camera(board_rect_screen.width, board_rect_screen.height, board.width_px, board.height_px)
    reserves_panel_rect = pygame.Rect(0, top_bar_height + top_row_height, window_width, config.RESERVES_PANEL_HEIGHT)
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
        if not battle_map.fields(squad, armies):
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

    # WHO FIELDS WHICH LIST is a per-player choice now, made on the army
    # selection screen before any of this runs (see game/ui/army_select.py) and
    # resolved into `armies` above. The three lists themselves live in
    # game/army_lists.py, one builder each, and every one of them can be built
    # for EITHER player - which is the whole reason they had to leave main().
    #
    # Nothing else in this function knows which army is which: the units carry
    # their own faction keyword, and every army rule in this engine derives its
    # owner from that (game/battle_focus.py's and game/waaagh.py's
    # qualifying_players()). The two things that genuinely cannot be derived -
    # who is running Seer Council and who Awakened Dynasty, because a
    # detachment is a list-building declaration - were written into config by
    # army_lists.apply_to_config() at startup.
    #
    # `model_positions` is the legacy --no-deployment path's hand-placed table
    # and is passed only for Player 1, exactly as before; in the normal
    # Pre-game (03.01) path both get None and nothing is hand-placed. The
    # tables in game/maps.py have not covered a full roster for two list
    # revisions, so the builder refuses loudly rather than leaving units piled
    # on (0, 0) - see army_lists._check_positions().
    for owner in ("Player 1", "Player 2"):
        army_lists.get(armies[owner]).build(
            owner, register_unit, state=state,
            model_positions=(
                None if config.PREGAME_DEPLOYMENT or owner != "Player 1"
                else battle_map.player1.squads
            ),
        )

    # A partial roster (BattleMap.roster) has to be self-consistent, and the
    # two ways it can fail are both silent otherwise: a name that matches no
    # unit quietly fields one fewer than intended, and a passenger whose
    # transport was left out would be declared into a vehicle that is not in
    # the game. Refused loudly instead - the same lesson as the
    # --no-deployment guard below, where a zip() over mismatched lists used to
    # drop a unit without a word.
    map_roster = battle_map.roster_for(armies)
    if map_roster is not None:
        fielded = {entry["squad"].name for entry in scene_units}
        unknown = sorted(map_roster - fielded)
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
    # Which map and which BIOME, on the log's first line. The map has always
    # been reconstructible from the terrain coordinates in the log; the biome
    # is not reconstructible from anything, because it changes nothing except
    # what the table is painted in - so a screenshot in a bug report cannot be
    # matched to a run without this. file_only: it is provenance, not play.
    game_log.add(f"[setup] {battle_map.name} | biome: {biomes.current().name}",
                 file_only=True)
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
    # The Unit Statistics ledger (user: "wie jede einheit performt hat als
    # resumee"). Built HERE, before the three controllers that report into
    # it, and published on its own module so the seams that record - the
    # three sessions in game/damage_resolution.py, game/feel_no_pain.py and
    # confirm_move() - reach it without 25 call sites learning that
    # statistics exist. Cleared when this battle ends so a second main()
    # in the same process starts from zero.
    battle_stats = BattleStats()
    battle_stats_module.CURRENT = battle_stats
    # The human's Tactical Secondary Mission deck (user-supplied - the AI
    # keeps its standard Secondary; see game/secondary_missions.py). Built
    # here, next to the ledger it credits, so both battle-start paths below
    # can already draw round 1's two cards. Its draw_overlay is attached
    # later, once the UI exists - the same deferred-field pattern
    # neocapacitor_controller.battle_shock uses further down.
    secondary_mission_controller = SecondaryMissionController(
        player=(config.SECONDARY_MISSION_CARD_PLAYERS[0]
                if config.SECONDARY_MISSION_CARD_PLAYERS else "Player 1"),
        mission_controller=mission_controller, command_points=command_points,
        decision_manager=decision_manager, turn_tracker=turn_tracker,
        game_log=game_log,
    )
    # A CALLABLE, not a snapshot: state.tokens is rebuilt as models die, and
    # a card measured against a stale list would score off a board that no
    # longer exists (same reasoning as path_of_the_outcast's all_squads).
    secondary_mission_controller.set_tokens_source(lambda: state.tokens)
    # Board + Strategic Reserves + embarked. "Assassination" asks whether any
    # enemy CHARACTER is left ANYWHERE, and state.tokens is the board only -
    # a character waiting in reserves is off the board and very much alive.
    secondary_mission_controller.set_squads_source(state.all_squads)
    # Board furniture, for cards that name a place. "A Tempting Target" reads
    # objective control (14.02) and needs the deployment zones to tell No
    # Man's Land from a home objective.
    secondary_mission_controller.set_objectives_source(lambda: state.objectives)
    secondary_mission_controller.set_zones_source(lambda: state.deployment_zones)
    # Units inside a transport (18.02): Beacon's setup offers them alongside
    # the board units, and neither the token nor the all-squads source can
    # tell an embarked squad from one in Strategic Reserves.
    secondary_mission_controller.set_embarked_source(lambda: state.embarked_squads)
    # Terrain areas (13.01) - the Plunder action's targets.
    secondary_mission_controller.set_terrain_source(lambda: state.terrain_areas)
    # Rule 16.01's Actions (game/actions.py). One controller for every action
    # there will ever be: its eligibility, its two locks and its
    # move-cancellation are shared, and "started another action this turn" is a
    # question across all of them at once.
    action_controller = ActionController(
        tokens_source=lambda: state.tokens, game_log=game_log,
    )
    secondary_mission_controller.set_action_controller(action_controller)
    # The human's FORCE DISPOSITION Primary Mission (user-supplied - the AI
    # keeps "Hold the Line"; see game/primary_missions.py). WHICH mission it is
    # follows from the Force Disposition the chosen army list declares, so
    # nothing is passed in here.
    #
    # Built AFTER action_controller, not before: two of the five missions carry
    # an Objective Action and this controller is handed that collaborator on
    # the next line. Constructor order in main() is load-bearing and no suite
    # can see it - see test_event_chain_wiring.py's AST guard, written after
    # three UnboundLocalErrors of exactly this shape.
    primary_mission_controller = PrimaryMissionController(
        player=(config.PRIMARY_MISSION_CARD_PLAYERS[0]
                if config.PRIMARY_MISSION_CARD_PLAYERS else "Player 1"),
        mission_controller=mission_controller, turn_tracker=turn_tracker,
        game_log=game_log, action_controller=action_controller,
    )
    # The same callables the Secondary deck takes, and for the same reason:
    # a board measured once is a board that no longer exists by scoring time.
    primary_mission_controller.set_tokens_source(lambda: state.tokens)
    primary_mission_controller.set_squads_source(state.all_squads)
    primary_mission_controller.set_objectives_source(lambda: state.objectives)
    primary_mission_controller.set_zones_source(lambda: state.deployment_zones)
    # Terrain areas (13.01) - Death Trap's Booby Trap action traps them, and
    # its turn-start snapshot records which enemies were standing in which.
    primary_mission_controller.set_terrain_source(lambda: state.terrain_areas)
    # Which Primary each side is on, once, file_only - the same provenance the
    # [setup] line above records for the map and biome. A Force Disposition is
    # a list-building declaration and appears NOWHERE on the board, so without
    # this a log cannot be matched to the mission that was being played.
    primary_mission_controller.announce()
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
        # The three Experimental Prototype Cadre weapon upgrades. Their printed
        # timing is Declare Battle Formations, which this path does not have -
        # and without this line a legacy or --load scene would carry the
        # Enhancement, and its points, with none of its effect. Idempotent, so
        # a scene that somehow reached both paths is still upgraded once.
        enh_prototype_weapons.apply_all(state.all_squads(), game_log=game_log)
        command_points.gain_core_cp()  # rule 08.02: the battle's very first phase is already Command
        # Same "the battle's very first phase is already Command" case as
        # gain_core_cp() above - update_control() itself only ever runs
        # inside advance_turn_phase(), so it's never seen this initial
        # deployment at all yet; run it once here too, otherwise Primary
        # scoring for turn 1's Command phase would score 0 regardless of
        # what either player's deployment happens to already be standing on.
        for objective in state.objectives:
            objective.update_control(state.tokens)
        mission_controller.score_primary(state.objectives, turn_tracker.active_player,
                                         turn_tracker.battle_round)
        # Round 1's two Secondary Mission cards. Idempotent by battle
        # round, so the Command-phase hook in advance_turn_phase() cannot
        # draw a second pair for the same round.
        secondary_mission_controller.sync_battle_round(turn_tracker.battle_round)
        secondary_mission_controller.draw_at_command_phase(
            turn_tracker.turn_owner, turn_tracker.battle_round)
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
    # Rule 16.01's two ends, now that both objects exist: the ActionController
    # needs the movement controller for "Advanced this turn", and the movement
    # controller reports every confirmed move back so a move cancels an action
    # in progress. Same deferred-field pattern as
    # neocapacitor_controller.battle_shock further down.
    action_controller.movement_controller = movement_controller
    movement_controller.action_controller = action_controller
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
    # Both Autarchs' Path of Command - the FOURTH datasheet to print the same
    # sentence, and the one that paid for extracting it. All four now share
    # game/cp_discount.py; only the flag, the discount and the label differ.
    path_of_command_discount = PathOfCommandDiscount(
        turn_tracker=turn_tracker, game_log=game_log)
    stratagem_controller.cost_discounts.append(path_of_command_discount)
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
    # WHOSE army rule this is, derived from the built armies exactly the way
    # Battle Focus derives its own. Set once, here, because the armies are
    # complete by this point and an army's faction does not change mid-battle.
    #
    # Without it the AI called a Waaagh! for whatever army it happened to be
    # playing (user: "die necrons haben soeben einen waagh ausgerufen. das
    # koennen nur orks") - can_call() checked the phase and once-per-battle and
    # nothing about the army, which was invisible while Player 2 was always
    # Orks.
    waaagh_controller.orks_players = waaagh_module.qualifying_players(
        entry["squad"] for entry in scene_units)
    # WHO THE ENGINE ANSWERS FOR, read ONCE and frozen for this whole battle.
    #
    # This is the switch (user: "es muss also eine weiche geben. je nachdem ob
    # KI aktiv ist oder nicht"). It used to be the literal ("Player 2",),
    # written out at 82 call sites below, with four more spellings of the same
    # fact elsewhere - game/scouts.py's human_players, game/pregame.py's and
    # game/plagues.py's singular human_player, and ai/deployment_ai.py's
    # ai_players. One fact, five places, is how the two halves drift apart.
    #
    # FROZEN IS THE POINT, not a shortcut: every controller below normalises
    # what it is handed in its own __init__, so nothing can change under a
    # controller mid-battle - which is exactly why the question is asked before
    # main() runs at all (see run() and game/ui/ai_mode_select.py) rather than
    # from a toggle during play.
    #
    # A player NOT listed here is a human and gets a DecisionManager prompt for
    # every choice the printed rule gives them. A player listed here gets the
    # rule's own deterministic answer, free and with no API call - see
    # config.AI_PLAYERS for why the determinism has to live on this side and
    # never inside the rule.
    # `armies` is {player -> army key}, so its keys ARE the players in this
    # battle - derived rather than a second pair of literals.
    # LIVE, not a tuple, and that is the whole of the "one switch" fix: this
    # single object is handed to all ~83 gates below, and its membership test
    # asks game/ai_mode.py whether the mode is on. Frozen members, live
    # membership - so the switch reaches gates that are built once, here, and
    # never rebuilt.
    #
    # It also gates the OTHER channel for free: both AI entry points already
    # open with `if not ai_players: return`, and this reads as empty while the
    # mode is off - so the frame tick and the single-step "A" key stop too,
    # without either of them having to learn about the mode.
    ai_players = ai_mode.players(p for p in sorted(armies) if p in config.AI_PLAYERS)
    human_players = ai_mode.humans(sorted(armies), ai_players)

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
    # selected its targets" trigger, but answered DETERMINISTICALLY for a side
    # the engine plays rather than asked about (user: "hier auch
    # deterministisch"). `ai_players` above is the one place that says which
    # side that is; a human running Orks gets a DecisionManager prompt instead.
    # See game/ard_as_nails.py.
    ard_as_nails_controller = ArdAsNailsController(
        stratagem_controller, decision_manager=decision_manager, turn_tracker=turn_tracker, game_log=game_log,
        auto_players=ai_players,
    )
    # Flash Gitz' Ammo Runt (user-supplied): offered when the unit is
    # selected to shoot, once per battle. Handed to ShootingController the
    # same way the Riptide's Nova Charge is - see game/ammo_runt.py. Same
    # auto_players shape as 'Ard as Nails above: per explicit user
    # instruction the AI uses it at the first opportunity instead of being
    # asked, while a human running Orks keeps the choice.
    ammo_runt_controller = AmmoRuntController(
        decision_manager=decision_manager, game_log=game_log, auto_players=ai_players,
    )
    # Kill Rig's Spirit of Gork (user-supplied): resolved at the start of
    # each Fight phase. Same auto_players shape as 'Ard as Nails above -
    # Player 2 is this project's AI throughout main.py, and per explicit
    # user instruction it picks the highest-points eligible unit itself
    # rather than being asked; a human keeps the DecisionManager prompt.
    spirit_of_gork_controller = SpiritOfGorkController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        all_tokens=state.tokens, auto_players=ai_players,
    )
    # Painboy's Grot Orderly (user-supplied wargear): resolved in its owner's
    # Command phase. Same auto_players shape again - per explicit user
    # instruction the AI uses it deterministically at the first opportunity.
    # It is handed SetupController's own position_valid() so "somewhere legal
    # to put the returning models" means exactly what it means for a
    # disembark or an ingress, rather than a second opinion that could drift.
    # Fuegan's Unquenchable Resolve - the second ability in this engine that puts
    # a destroyed model back (Grot Orderly below is the first), and it borrows
    # that one's position_valid wiring for the same reason: the placement has to
    # judge real ground. Its own Engagement Range clause is NOT in there and is
    # checked inside the module - position_valid() says outright that it does not
    # cover engagement.
    unquenchable_resolve_controller = UnquenchableResolveController(
        dice_manager=dice_manager, game_state=state, game_log=game_log,
        position_valid=lambda model, x, y: setup_controller.position_valid(
            model, x, y, squad=model.squad,
        ),
    )
    # Warhost's Phoenix Gem is the same shape with a different roll - built
    # beside its twin and given the same placement predicate for the same
    # reason (position_valid() does not cover Engagement Range; the module
    # checks that half itself).
    phoenix_gem_controller = PhoenixGemController(
        game_state=state, dice_manager=dice_manager, game_log=game_log,
        all_tokens=state.tokens,
        position_valid=lambda model, x, y: setup_controller.position_valid(
            model, x, y, squad=model.squad,
        ),
    )
    grot_orderly_controller = GrotOrderlyController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, auto_players=ai_players,
        position_valid=lambda model, x, y: setup_controller.position_valid(
            model, x, y, squad=model.squad,
        ),
    )
    # --- Necrons -----------------------------------------------------------
    # All of these are built unconditionally rather than only when the Necrons
    # are fielded: every one of them is inert without a Necron unit on the
    # board (their can_use()/has_*() tests read the models), and building them
    # conditionally would mean every call site needed a None check as well.
    # The same reasoning the Ork and T'au controllers already follow.
    def _necron_position_valid(model, x, y):
        return setup_controller.position_valid(model, x, y, squad=model.squad)

    def _best_damage_target(attacker, candidates):
        """The AI's shared deterministic target pick for the Necron mortal-wound
        abilities: the unit worth the most to remove, by the SAME
        game/damage_estimate.py measure every other deterministic choice in
        this engine uses rather than a second opinion about what a good target
        is.

        Sorted by name first so ties resolve identically on a replay."""
        if not candidates:
            return None
        return max(sorted(candidates, key=lambda s: s.name),
                   key=lambda s: ai_observation.damage_value(attacker, s) or 0.0)

    reanimation_controller = ReanimationProtocolsController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, auto_players=ai_players,
        position_valid=_necron_position_valid,
    )
    technomancer_controller = TechnomancerController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, auto_players=ai_players,
    )
    resurrection_orb_controller = ResurrectionOrbController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, auto_players=ai_players,
        position_valid=_necron_position_valid,
    )
    # The Kroot War Shaper's Root of Honour. Offered at the start of EVERY
    # phase (see the call in advance_turn_phase), so no dice and no CP - it
    # only ever flips Squad.battle_shocked off. `all_squads` is passed as a
    # CALLABLE so the controller can never hold a unit list that has gone
    # stale as models died.
    # The Ethereal's Coordinated Leadership - a D6 at the end of its owner's
    # Command phase. It reads command_points directly rather than gaining CP
    # itself, so CommandPointManager stays the one place the per-round bonus
    # cap is enforced.
    coordinated_leadership_controller = CoordinatedLeadershipController(
        dice_manager=dice_manager, command_points=command_points,
        turn_tracker=turn_tracker, game_log=game_log,
    )
    root_of_honour_controller = RootOfHonourController(
        decision_manager=decision_manager, game_log=game_log,
        all_squads=lambda: [t.squad for t in state.tokens if t.squad is not None],
        auto_players=ai_players,
    )
    # The real line-of-sight test, so "visible to this model" means what it
    # means everywhere else rather than a second approximation of it. Named
    # rather than inlined because Typhus' Eater Plague asks the identical
    # question further down, and two copies is how two answers start.
    def _psychic_visible(model, squad):
        return any(
            line_of_sight.has_line_of_sight(
                model, t, state.obstacles, state.tokens, state.terrain_areas)
            for t in squad.models if not t.is_dead()
        )

    living_lightning_controller = LivingLightningController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, auto_players=ai_players,
        target_pick=_best_damage_target,
        visible=_psychic_visible,
    )
    matter_absorption_controller = MatterAbsorptionController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, auto_players=ai_players, target_pick=_best_damage_target,
    )
    crimson_harvest_controller = CrimsonHarvestController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, auto_players=ai_players, target_pick=_best_damage_target,
    )
    # Krootox Rampagers' Kroot Linebreakers - Crimson Harvest's sibling in
    # game/mortal_wound_abilities.py, on the same charge hook. It is the
    # only one that also owes a Battle-shock test, hence battle_shock.
    kroot_linebreakers_controller = KrootLinebreakersController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, auto_players=ai_players, target_pick=_best_damage_target,
        battle_shock=battle_shock_controller,
    )
    wraith_form_controller = WraithFormController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, movement_controller=movement_controller,
        auto_players=ai_players, target_pick=_best_damage_target,
    )
    # Retaliation Cadre's Internal Grenade Racks: Wraith Form's own trigger and
    # geometry (see game/enh_internal_grenade_racks.py), but per BEARER MODEL
    # and six flat D6. Built right beside it so the two stay comparable.
    internal_grenade_racks_controller = InternalGrenadeRacksController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, movement_controller=movement_controller,
        auto_players=ai_players, target_pick=_best_damage_target,
    )
    # Retaliation Cadre's Puretide Engram Neurochip - NOT Commander Farsight's
    # "Puretide's Teachings" discount registered further down; two rules under
    # similar printed names, one module each.
    puretide_neurochip_controller = PuretideNeurochipController(
        dice_manager=dice_manager, command_points=command_points,
        turn_tracker=turn_tracker, game_log=game_log)
    stratagem_controller.on_targets_chosen.append(
        puretide_neurochip_controller.on_targets_chosen)
    # Auxiliary Cadre's Admired Leader - driven from the Command-phase block,
    # where it first clears last round's mark and then offers this round's.
    admired_leader_controller = AdmiredLeaderController(
        game_state=state, decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players)
    # Spirit Conclave's Light of Clarity prints the SAME Command-phase sentence,
    # so it is the same machine with its own keyword clause and its own flag -
    # see game/command_phase_mark.py for why that is four carriers, not two.
    light_of_clarity_controller = LightOfClarityController(
        game_state=state, decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players)
    # Stave of Kurnous - the same Command-phase sentence again, with the
    # TITANIC exclusion that only IT prints.
    stave_of_kurnous_controller = StaveOfKurnousController(
        game_state=state, decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players)
    # Rune of Mists - the THIRD carrier of that same Command-phase sentence,
    # and the one that does NOT print the TITANIC exclusion above.
    rune_of_mists_controller = RuneOfMistsController(
        game_state=state, decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players)
    # The two "target the bearer's unit with <NAMED> for 0CP" Enhancements -
    # one shared class, two names. Protector of the Paths is kept in a local
    # because its SECOND clause (the Snap Shooting threshold) reads the latch
    # this object holds.
    protector_of_the_paths_discount = ProtectorOfThePathsDiscount(
        turn_tracker=turn_tracker, game_log=game_log)
    stratagem_controller.cost_discounts.append(protector_of_the_paths_discount)
    stratagem_controller.cost_discounts.append(
        GiftOfForesightDiscount(turn_tracker=turn_tracker, game_log=game_log))
    # The FIRST surcharge - the mirror list, for making an OPPONENT's
    # Stratagem dearer. See game/enh_torc_of_morai_heg.py.
    stratagem_controller.cost_surcharges.append(
        TorcOfMoraiHegSurcharge(game_state=state, turn_tracker=turn_tracker,
                                game_log=game_log))
    atomic_energy_controller = AtomicEnergyManipulatorController(game_log=game_log)
    # The third cost_discounts collaborator, after Puretide and Strands of Fate.
    stratagem_controller.cost_discounts.append(
        MyWillBeDoneDiscount(turn_tracker=turn_tracker, game_log=game_log))
    # The fifth (Fevered Strategist below is the fourth). Word for word the
    # same rule as My Will Be Done above, in a different faction's typeface -
    # see game/war_leader.py. Registering it unconditionally is safe: its own
    # predicate finds no War Shaper unless one is on the table.
    stratagem_controller.cost_discounts.append(
        WarLeaderDiscount(turn_tracker=turn_tracker, game_log=game_log))
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
    # Krootox Riders' Kroot Packmates reacts at exactly the same instant the
    # two stratagems do - "just after an enemy unit has selected its targets".
    kroot_packmates_controller = KrootPackmatesController(
        decision_manager=decision_manager, game_state=state, turn_tracker=turn_tracker,
        game_log=game_log, auto_players=ai_players,
    )
    shooting_target_reactions = (
        stim_injectors_controller, ard_as_nails_controller, psychic_shield_controller,
        kroot_packmates_controller,
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
    # The Farseer Skyrunner's Misfortune - the THIRD mark of this shape, and
    # the first read from the ATTACKER's side: it penalises the marked unit's
    # own Wound rolls rather than helping attacks against it. Same machinery,
    # different question, so a subclass rather than a third copy.
    misfortune_controller = MisfortuneController(
        decision_manager=decision_manager, game_log=game_log, all_tokens=state.tokens,
        obstacles=state.obstacles, terrain_areas=state.terrain_areas,
    )
    # The Spiritseer's Spirit Mark and Tears of Isha. Two abilities, one
    # datasheet, and both reach WRAITH CONSTRUCT units by range.
    spirit_mark_controller = SpiritMarkController(
        decision_manager=decision_manager, game_log=game_log, all_tokens=state.tokens,
        auto_players=ai_players)
    tears_of_isha_controller = TearsOfIshaController(
        dice_manager=dice_manager, decision_manager=decision_manager,
        game_log=game_log, game_state=state, all_tokens=state.tokens,
        auto_players=ai_players)
    # The Voidscarred's Piratical Raiders (a battle-long mark chosen before the
    # first turn) and Kharseth's Fury of the Void (a turn-long one placed by a
    # hit). Both ride the adjuster chain, so both are built before the attack
    # controllers that take them.
    piratical_raiders_controller = PiraticalRaidersController(
        game_log=game_log, decision_manager=decision_manager,
        auto_players=ai_players)
    fury_of_the_void_controller = FuryOfTheVoidController(
        decision_manager=decision_manager, game_log=game_log)
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
    # Auxiliary Cadre's Harnessed Alien Instincts - the fifth enemy mark in this
    # engine, and the only one whose effect is a DETECTION RANGE. Built here
    # with the other marks; line_of_sight_check is filled in below, once the
    # obstacles and the terrain the check needs are in scope.
    auxiliary_cadre_controller = AuxiliaryCadreController(
        decision_manager=decision_manager, game_state=state,
        turn_tracker=turn_tracker, game_log=game_log,
    )
    # Seer Council's Presentiment of Dread - a forced Battle-shock test at -1,
    # so it needs battle_shock_controller. Third consumer of start_forced_roll()
    # after Grav-inhibitor Field and Neocapacitor Shields.
    presentiment_controller = PresentimentOfDreadController(
        stratagem_controller, battle_shock=battle_shock_controller, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log, all_tokens=state.tokens,
        obstacles=state.obstacles, terrain_areas=state.terrain_areas,
    )
    # Seer Council's Unshrouded Truth - board -> Strategic Reserves and straight
    # back on, so it needs the GameState (whose tokens/reserves lists it moves
    # the unit between) and the MovementController (for "has not been selected
    # to move this phase"). Second consumer of the board->reserves move that
    # game/starflare_ignition.py had already built - see
    # game/strategic_reserves.py.
    unshrouded_truth_controller = UnshroudedTruthController(
        stratagem_controller, game_state=state, movement_controller=movement_controller,
        turn_tracker=turn_tracker, game_log=game_log, all_tokens=state.tokens,
    )
    # Seer Council's Isha's Fury - six D6 at 3+ after an enemy Normal, Advance
    # or Fall Back move. The roll and the mortal-wound allocation are Explosives'
    # shape; the trigger is movement_controller.on_move_finished, wired below.
    # Swooping Hawks' Grenade Pack Flyover - the THIRD consumer of
    # on_move_finished and the SECOND of on_ingress_resolved, which is why both
    # of those hooks are lists now.
    # Spirit Stone of Raelyth's heal is "at the START or end of this unit's
    # move", so it is the first listener on BOTH hooks. on_move_started is new
    # and exists for exactly this - see game/movement.py's _begin_move().
    spirit_stone_controller = SpiritStoneOfRaelythController(
        game_state=state, decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players)
    movement_controller.on_move_started.append(spirit_stone_controller.on_move_started)
    movement_controller.on_move_finished.append(spirit_stone_controller.on_move_finished)
    # The Spiritseer's Spirit Mark: "when this model STARTS OR ENDS a move" -
    # the same pair of moments, and the half of that controller that was built
    # but never fed until now.
    movement_controller.on_move_started.append(spirit_mark_controller.on_move_started)
    movement_controller.on_move_finished.append(spirit_mark_controller.on_move_finished)
    # Spirit Conclave's Higher Duty reacts to an ENEMY ending a move - the
    # first enemy-side consumer of this hook, and what closes the Trail Finding
    # trigger gap CLAUDE.md records.
    higher_duty_controller = HigherDutyController(
        game_state=state, movement_controller=movement_controller,
        decision_manager=decision_manager, turn_tracker=turn_tracker,
        game_log=game_log, auto_players=ai_players, all_tokens=state.tokens)
    movement_controller.on_move_finished.append(higher_duty_controller.on_move_finished)
    movement_controller.on_move_finished.append(wraith_form_controller.on_move_finished)
    movement_controller.on_move_finished.append(
        internal_grenade_racks_controller.on_move_finished)
    # Overwhelming Obliteration is not a decision - it simply follows the move
    # type the unit already chose, so it hangs off the Remain Stationary hook
    # rather than prompting anything.
    _previous_remain_stationary = movement_controller.on_remain_stationary
    def _on_remain_stationary(squad):
        overwhelming_obliteration.on_remain_stationary(squad, game_log)
        if _previous_remain_stationary is not None:
            _previous_remain_stationary(squad)
    movement_controller.on_remain_stationary = _on_remain_stationary

    grenade_pack_controller = GrenadePackFlyoverController(
        game_state=state, decision_manager=decision_manager, dice_manager=dice_manager,
        turn_tracker=turn_tracker, game_log=game_log,
        line_of_sight=lambda squad, target: any(
            line_of_sight.has_line_of_sight(
                m, t, state.obstacles, state.tokens, state.terrain_areas)
            for m in squad.models if not m.is_dead()
            for t in target.models if not t.is_dead()
        ),
    )
    def _note_set_up_on_battlefield(squad):
        """Baharroth's Cry of the Wind: "each time this model is SET UP on the
        battlefield, until the end of the turn...". Per MODEL, because the
        printed text says "this model" and he may be leading a unit."""
        for model in getattr(squad, "models", ()):
            if getattr(model.profile, "cry_of_the_wind", False):
                model.cry_of_the_wind_active = True

    # Rangers' Path of the Outcast - the second consumer of
    # MovementController.on_move_finished, which is why that became a list.
    path_of_the_outcast_controller = PathOfTheOutcastController(
        movement_controller=movement_controller, decision_manager=decision_manager,
        dice_manager=dice_manager, turn_tracker=turn_tracker, game_log=game_log,
        all_squads=lambda: _player_squads(state, "Player 1") + _player_squads(state, "Player 2"),
    )
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
    # The Kroot Lone-Spear's Fire and Fade - Tactical Acumen's twin, built
    # here for the same reason and immediately after it, so the two post-
    # shooting movers stay next to each other.
    fire_and_fade_controller = FireAndFadeController(
        movement_controller=movement_controller, decision_manager=decision_manager,
        all_tokens=state.tokens, game_log=game_log, auto_players=ai_players,
    )
    # The Chronomancer's Chronometron - the third of the same shape, built
    # beside its two twins so the construction order is obvious rather than
    # inferred (error class 23: main() is one long function and no suite
    # drives it).
    chronometron_controller = ChronometronController(
        movement_controller=movement_controller, decision_manager=decision_manager,
        all_tokens=state.tokens, game_log=game_log, auto_players=ai_players,
    )
    # The Tomb Blades' Evasion Engrams - the fifth of this shape. See that
    # module's docstring for why the family is not yet one class.
    evasion_engrams_controller = EvasionEngramsController(
        movement_controller=movement_controller, decision_manager=decision_manager,
        all_tokens=state.tokens, game_log=game_log, auto_players=ai_players,
    )
    # The Psychomancer's two forced Battle-Shock tests, and Orikan's
    # once-per-battle. battle_shock_controller is built far above, so both
    # of the first two have their dependency in hand here.
    nightmare_shroud_controller = NightmareShroudController(
        battle_shock_controller=battle_shock_controller,
        all_tokens=state.tokens, game_log=game_log,
    )
    harbinger_of_despair_controller = HarbingerOfDespairController(
        battle_shock_controller=battle_shock_controller,
        decision_manager=decision_manager, all_tokens=state.tokens,
        game_log=game_log, auto_players=ai_players,
    )
    the_stars_are_right_controller = TheStarsAreRightController(
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    # His OTHER ability: a mark placed on the unit he HIT, read by every
    # other KROOT unit in the army until the end of the turn.
    advanced_scouting_controller = AdvancedScoutingController(game_log=game_log)
    # The two gunships' Targeting Array. Its shooting_controller back-reference
    # is filled in after that controller exists (it needs to know which unit is
    # shooting to spend the right unit's once-per-activation use).
    targeting_array_controller = TargetingArrayController(
        dice_manager=dice_manager, game_log=game_log)
    # The Piranhas' Drone Harassment Tactics - it orders a Battle-shock test
    # out of turn, which BattleShockController.start_forced_roll() already
    # exists for (added for Neocapacitor Shields).
    drone_harassment_controller = DroneHarassmentController(
        battle_shock=battle_shock_controller, decision_manager=decision_manager,
        game_log=game_log, auto_players=ai_players, target_pick=_best_damage_target,
    )
    # Kroot Farstalkers' Bounty Hunters: chosen once before the battle and
    # read by BOTH attack steps, since its text says "an attack".
    bounty_hunters_controller = BountyHuntersController(
        game_log=game_log, target_pick=_best_damage_target,
        # target_pick stays the AI's ranking; decision_manager is what lets a
        # HUMAN name their own bounty instead of having one estimated for them.
        # This controller had neither and picked for both sides.
        decision_manager=decision_manager, auto_players=ai_players)
    # The Vespid Strain Leader's Oversight Drone - offered from
    # ShootingController.start_shooting() only, like Nova Charge.
    oversight_drone_controller = OversightDroneController(
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players)
    # Vespid Stingwings' Airborne Agility - offered at the END of a turn, to
    # whoever's turn it is NOT.
    ride_the_wind_controller = RideTheWindController(
        decision_manager=decision_manager, game_state=state, game_log=game_log,
        all_tokens=state.tokens, auto_players=ai_players)
    airborne_agility_controller = AirborneAgilityController(
        decision_manager=decision_manager, game_state=state, game_log=game_log,
        auto_players=ai_players)
    # Retaliation Cadre's Prototype Weapon System and Advanced Acquisition
    # Cadre's Unmasking Suite: both open on "selected to shoot" and close on
    # "until those attacks are resolved"/"until this unit has shot", which is
    # the same pair of ShootingController seams game/targeting_array.py uses -
    # so both are passed in and driven from there, not from this loop.
    prototype_weapon_system_controller = PrototypeWeaponSystemController(
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players)
    unmasking_suite_controller = UnmaskingSuiteController(
        game_state=state, decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players)
    shooting_controller = ShootingController(
        obstacles=state.obstacles, game_log=game_log, dice_manager=dice_manager, turn_tracker=turn_tracker,
        all_tokens=state.tokens, movement_controller=movement_controller, terrain_areas=state.terrain_areas,
        decision_manager=decision_manager, greater_good=greater_good_controller, suppression=suppression_controller,
        ammo_runt=ammo_runt_controller, advanced_scouting=advanced_scouting_controller,
        bounty_hunters=bounty_hunters_controller, oversight_drone=oversight_drone_controller,
        targeting_array=targeting_array_controller,
        prototype_weapon_system=prototype_weapon_system_controller,
        unmasking_suite=unmasking_suite_controller,
        objectives=state.objectives, stealth_drones=stealth_drones_controller, waaagh=waaagh_controller,
        target_reactions=shooting_target_reactions, nova_charge=nova_charge_controller,
        fire_support=fire_support_controller, hand_of_asuryan=hand_of_asuryan_controller,
        guide=guide_controller, doom=doom_controller,
        misfortune=misfortune_controller, spirit_mark=spirit_mark_controller,
        piratical_raiders=piratical_raiders_controller,
        fury_of_the_void=fury_of_the_void_controller,
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
    # Shroud Runners' Target Acquisition - the sixth listener on
    # on_squad_finished_shooting, and the only one whose effect is a mark on
    # the TARGET rather than a grant on the shooter, which is why
    # shooting_controller reads it back (see _cover_ignored_for_group()).
    target_acquisition_controller = TargetAcquisitionController(
        decision_manager=decision_manager, game_log=game_log,
    )
    shooting_controller.target_acquisition = target_acquisition_controller
    shooting_controller.on_squad_finished_shooting.append(
        lambda squad, hit_squads: target_acquisition_controller.offer_after_shooting(
            squad, hit_squads,
            shooting_controller.squads_hit_by_weapon(target_acquisition.LONG_RIFLE_NAME),
        )
    )
    # War Walkers' Crystalline Targeting - the seventh listener, and the
    # second whose effect is a mark on the TARGET (Target Acquisition above
    # is the first), so shooting_controller reads this one back too - in
    # the AP adjuster chain rather than in the cover test.
    crystalline_targeting_controller = CrystallineTargetingController(
        decision_manager=decision_manager, game_log=game_log,
    )
    shooting_controller.crystalline_targeting = crystalline_targeting_controller
    shooting_controller.on_squad_finished_shooting.append(
        crystalline_targeting_controller.offer_after_shooting)
    # The Shadow Weaver Platform's Monofilament Snare - the same
    # "after this model has shot, select one enemy unit hit" moment, but with
    # the per-WEAPON subset, because a unit hit only by the platform's shuriken
    # catapult is not a legal choice. Same split Target Acquisition uses above.
    monofilament_snare_controller = MonofilamentSnareController(
        dice_manager=dice_manager, game_log=game_log,
        decision_manager=decision_manager, game_state=state,
        turn_tracker=turn_tracker)
    shooting_controller.monofilament_snare = monofilament_snare_controller
    shooting_controller.on_squad_finished_shooting.append(
        lambda squad, hit_squads: monofilament_snare_controller.offer_after_shooting(
            squad, hit_squads,
            shooting_controller.squads_hit_by_weapon(SHADOW_WEAVER_NAME),
        )
    )
    # The Vibro Cannon Platforms' Sonic Destruction ledger. Read back inside
    # the AP/S/D adjuster chain, and fed from _begin_resolution().
    sonic_destruction_controller = SonicDestructionController(game_log=game_log)
    shooting_controller.sonic_destruction = sonic_destruction_controller
    # Maugan Ra's Face of Death: after he shoots, one enemy unit he hit takes a
    # FORCED Battle-shock test at -1. No per-weapon subset - he carries one
    # weapon and the printed text names none.
    # The Autarch's Superlative Strategist, and the seam it needed - see below.
    superlative_strategist_controller = SuperlativeStrategistController(
        dice_manager=dice_manager, decision_manager=decision_manager,
        game_log=game_log, auto_players=ai_players)
    face_of_death_controller = FaceOfDeathController(
        battle_shock_controller=battle_shock_controller,
        decision_manager=decision_manager, game_log=game_log)
    shooting_controller.on_squad_finished_shooting.append(
        face_of_death_controller.offer_after_shooting)
    # The Leystalker's Panicked Quarry - the same sentence one clause longer,
    # sharing game/battle_shock_after_shooting.py with the line above.
    panicked_quarry_controller = PanickedQuarryController(
        battle_shock_controller=battle_shock_controller,
        decision_manager=decision_manager, game_log=game_log)
    shooting_controller.on_squad_finished_shooting.append(
        panicked_quarry_controller.offer_after_shooting)
    # Kharseth's Fury of the Void - the per-WEAPON subset again, because only a
    # unit his Dread of the Deep Void hit is a legal choice.
    shooting_controller.on_squad_finished_shooting.append(
        lambda squad, hit_squads: fury_of_the_void_controller.offer_after_shooting(
            squad, hit_squads,
            shooting_controller.squads_hit_by_weapon(DREAD_OF_THE_DEEP_VOID_NAME),
        )
    )
    # ...and his Harvester of Souls, which needs the TARGETED set rather than
    # the hit set: "every attack targets the same unit" is about selection, and
    # a group that targeted a second unit and missed still split the fire.
    harvester_of_souls_controller = HarvesterOfSoulsController(
        dice_manager=dice_manager, game_log=game_log, game_state=state,
        all_tokens=state.tokens)
    shooting_controller.on_squad_finished_shooting.append(
        lambda squad, hit_squads: harvester_of_souls_controller.after_shooting(
            squad, hit_squads,
            set(shooting_controller._targeted_squads_this_activation),
        )
    )
    # The Night Spinner's Monofilament Web. No prompt: the printed text has no
    # "select", so every unit its doomweaver hit is pinned - which is why this
    # is a plain listener rather than an offer. The per-WEAPON subset again,
    # because a unit hit only by the twin shuriken catapult is not pinned.
    monofilament_web_controller = MonofilamentWebController(
        game_log=game_log, game_state=state)
    shooting_controller.on_squad_finished_shooting.append(
        lambda squad, hit_squads: monofilament_web_controller.after_shooting(
            squad, hit_squads,
            shooting_controller.squads_hit_by_weapon(DOOMWEAVER_NAME),
        )
    )
    # The Vypers' Harassment Fire writes the SAME `suppressed` status as the
    # Strike Team's Suppression Volley, so it goes into that controller rather
    # than a second one - the hit step must have one answer to ask.
    shooting_controller.on_squad_finished_shooting.append(
        suppression_controller.offer_harassment_fire)
    # The snare is READ at confirm_move(), so the movement controller needs it
    # too. A class-attribute slot like action_controller's, set here.
    movement_controller.monofilament_snare = monofilament_snare_controller
    # The Exodites' Drakolithe reacts to the SAME seam - an enemy unit ending a
    # move - but to ANY move, where the snare names three kinds. Its own slot
    # rather than a second entry in the snare's, since the two share nothing
    # but the moment.
    drakolithe_controller = DrakolitheController(
        dice_manager=dice_manager, decision_manager=decision_manager,
        game_log=game_log, game_state=state, all_tokens=state.tokens,
        auto_players=ai_players)
    movement_controller.drakolithe = drakolithe_controller
    # Corsair Skyreavers' Raid and Run. Its eligibility is SAMPLED during the
    # Fight phase - the same problem Retro-thrusters has and the same answer -
    # and the move it grants goes through the reactive-move door.
    raid_and_run_controller = RaidAndRunController(
        movement_controller=movement_controller, dice_manager=dice_manager,
        decision_manager=decision_manager, game_log=game_log,
        all_tokens=state.tokens, auto_players=ai_players)
    # The Starfangs' Hallucinogen Grenades fire at the start of the OPPONENT'S
    # Shooting phase, so the offer goes to the other player.
    hallucinogen_grenades_controller = HallucinogenGrenadesController(
        decision_manager=decision_manager, game_log=game_log,
        all_tokens=state.tokens, auto_players=ai_players)
    # The Clanblade's Cornered Prey is the only thing in the Fall Back flow
    # that needs the board; without it that controller degrades to "no bearer
    # nearby", which is what every harness gets.
    fall_back_controller.all_tokens = state.tokens
    # The Stonesinger's Elemental Ensnarement fires at the END of the Fight
    # phase, so it is offered from the phase change rather than from a hook.
    elemental_ensnarement_controller = ElementalEnsnarementController(
        dice_manager=dice_manager, decision_manager=decision_manager,
        game_log=game_log, all_tokens=state.tokens, auto_players=ai_players)
    shooting_controller.on_squad_finished_shooting.append(suppression_controller.offer_after_shooting)
    # The Falcon's Fire Support marks one unit it just hit - the same
    # "after this model has shot" moment Suppression Volley uses.
    shooting_controller.on_squad_finished_shooting.append(fire_support_controller.offer_after_shooting)
    # Asurmen's Tactical Acumen - the fourth consumer of this list, and the
    # one that does not care WHAT was hit, only that the unit shot.
    shooting_controller.on_squad_finished_shooting.append(tactical_acumen_controller.offer_after_shooting)
    # Kroot Packmates fires its own shot only once the attacker has FINISHED -
    # "after that enemy unit has finished making its attacks".
    kroot_packmates_controller.shooting_controller = shooting_controller
    # Rule 13.09's detection range reads the prey mark through the shooting
    # controller; assigned after construction because the mark controller is
    # built with the other marks, ~100 lines before ShootingController exists
    # (error class 23 - construction order in main()).
    shooting_controller.auxiliary_cadre = auxiliary_cadre_controller
    # "one VISIBLE enemy unit within 12"" - the line-of-sight half, injected so
    # game/auxiliary_cadre.py needs no dependency on the LoS engine.
    auxiliary_cadre_controller.line_of_sight_check = lambda observer, target: any(
        line_of_sight.has_line_of_sight(a, b, state.obstacles, state.tokens, state.terrain_areas)
        for a in observer.models if not a.is_dead()
        for b in target.models if not b.is_dead()
    )
    targeting_array_controller.shooting_controller = shooting_controller
    shooting_controller.on_squad_finished_shooting.append(
        kroot_packmates_controller.on_squad_finished_shooting)
    shooting_controller.on_squad_finished_shooting.append(fire_and_fade_controller.offer_after_shooting)
    shooting_controller.on_squad_finished_shooting.append(chronometron_controller.offer_after_shooting)
    shooting_controller.on_squad_finished_shooting.append(evasion_engrams_controller.offer_after_shooting)
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
    # Rule 01.02.03: a model put back on the battlefield is SET UP, so a human
    # sets it up. One controller for all eight abilities that return a model -
    # see game/return_placement.py. It forks on auto_players: the AI lands on
    # the spots the ability computed, exactly as before, and a human gets those
    # spots as a starting point inside an ordinary SetupController placement.
    #
    # Built HERE because it needs setup_controller, which is constructed a few
    # lines up - and assigned onto the abilities below rather than passed into
    # their constructors, because those run ~600 lines earlier. main() is a
    # 4000-line function in which construction order is real (Fehlerklasse 23),
    # and test_event_chain_wiring.py section 4 checks exactly this shape.
    return_placement_controller = ReturnPlacementController(
        setup_controller=setup_controller, game_state=state, game_log=game_log,
        auto_players=ai_players,
    )
    reanimation_controller.placer = return_placement_controller
    grot_orderly_controller.placer = return_placement_controller
    unquenchable_resolve_controller.placer = return_placement_controller
    # The Resurrection Orb is a SECOND DOOR into reanimation_protocols.reanimate()
    # - the army rule's own controller is not the only funnel (Fehlerklasse 9).
    # Undying Legions is the third and is built AFTER this line, so it takes its
    # placer as a constructor argument instead.
    resurrection_orb_controller.placer = return_placement_controller

    # Rule 03.01's pre-game sequence. Built even when disabled (it just stays
    # IDLE) so every gate below can read it unconditionally.
    pregame_controller = PregameController(
        state, setup_controller, dice_manager, decision_manager,
        turn_tracker=turn_tracker, game_log=game_log,
        on_battle_start=lambda first_player: begin_battle(first_player),
        # THE SAME live view every rule gate gets. It used to take the default
        # ("Player 1"), so the pre-game believed in one human whatever
        # config.AI_PLAYERS said - and with the AI mode off it waited forever
        # for an opponent that no longer existed.
        human_players=human_players,
    )
    # The DEATH GUARD army rule, Nurgle's Gift (game/nurgles_gift.py). Built
    # unconditionally, like the Awakened Dynasty protocols further down: with
    # no Death Guard on the table qualifying_players() is empty, no Plague is
    # ever chosen, and refresh() sets every Squad.afflicted to False - so the
    # whole rule costs one flag write per unit per frame and changes nothing.
    plague_choice = plagues.PlagueChoice(game_log=game_log)
    plague_selection = plagues.PlagueSelectionStep(
        plague_choice, decision_manager=decision_manager,
        # The same single fact PregameController itself was constructed with,
        # read off it rather than repeated - a second literal "Player 1" here
        # is exactly how the two would drift apart.
        human_players=pregame_controller.human_players, game_log=game_log,
    )
    nurgles_gift_controller = NurglesGiftController(
        turn_tracker=turn_tracker, game_log=game_log, plague_choice=plague_choice,
    )
    # The Death Lord's Chosen detachment rule, Deadly Vectors. Built
    # unconditionally like the six Awakened Dynasty protocols: every gate
    # re-checks config.DEATH_LORDS_CHOSEN_PLAYERS, so it is inert in a game
    # nobody plays that detachment in.
    #
    # No decision_manager and no auto_players, and that is the rule rather than
    # an omission: the printed text has no "you can", so there is nothing to
    # ask and the human and the AI are treated identically. It therefore cannot
    # cost an API call by construction.
    deadly_vectors_controller = DeadlyVectorsController(
        dice_manager=dice_manager, game_log=game_log, game_state=state,
    )
    # The Death Guard datasheet abilities that need a controller. Built
    # unconditionally like everything else in this block: each one's own gate
    # asks about a profile flag no other faction carries, so they are inert in
    # a game with no Death Guard in it.
    barrage_of_filth_controller = BarrageOfFilthController(
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players, target_pick=_best_damage_target,
    )
    shooting_controller.barrage_of_filth = barrage_of_filth_controller
    pestilent_fallout_controller = PestilentFalloutController(
        turn_tracker=turn_tracker, game_log=game_log,
        auto_players=ai_players, target_pick=_best_damage_target,
        # target_pick is the AI's ranking and stays that; decision_manager is
        # what lets a HUMAN pick instead of having it applied to them. This
        # controller had auto_players and no way to ask - see its own comment.
        decision_manager=decision_manager,
    )
    lethal_ichor_controller = LethalIchorController(
        dice_manager=dice_manager, game_log=game_log,
    )
    curse_of_the_walking_pox_controller = CurseOfTheWalkingPoxController(
        game_log=game_log, game_state=state, position_valid=_necron_position_valid,
        # Built after setup_controller, so this one can take the placer
        # directly - the two above are constructed ~700 lines earlier and get
        # it assigned instead (Fehlerklasse 23).
        placer=return_placement_controller,
    )
    spore_laced_controller = SporeLacedShockWavesController(
        dice_manager=dice_manager, game_log=game_log, game_state=state,
    )
    # Fed at TARGET SELECTION, not at the end of the activation: the D6s freeze
    # the set of units at risk before the Crawler's own shooting can rearrange
    # the board. Assigned rather than passed at construction because
    # shooting_controller was built ~160 lines above - and assigned AFTER the
    # controller exists, which is error class 23 and the third time this block
    # has caught me.
    shooting_controller.spore_laced = spore_laced_controller
    eater_plague_controller = EaterPlagueController(
        dice_manager=dice_manager, decision_manager=decision_manager, game_log=game_log,
        game_state=state, auto_players=ai_players, target_pick=_best_damage_target,
        visible=_psychic_visible,
        # The printed TYPHUS clause of Curse of the Walking Pox: models killed
        # by this psychic power count as killed by a POXWALKER attack. Wired
        # here because that is the only place both abilities meet.
        on_kills=curse_of_the_walking_pox_controller.notify_eater_plague_kills,
    )
    # The FOURTH cost_discounts collaborator, after Puretide, Strands of Fate
    # and My Will Be Done. `all_tokens` is a LIVE reference, not a copy: its
    # 12" has to be measured wherever the models are when the Stratagem is
    # bought.
    fevered_strategist_discount = FeveredStrategistDiscount(
        turn_tracker=turn_tracker, game_log=game_log, all_tokens=state.tokens,
    )
    stratagem_controller.cost_discounts.append(fevered_strategist_discount)


    # The Defiler's Barrage of Filth - eighth consumer, third whose effect is a
    # mark on the TARGET, and the only one that REMOVES cover rather than
    # granting it (shooting_controller reads it back in the cover test).
    shooting_controller.on_squad_finished_shooting.append(
        barrage_of_filth_controller.on_squad_finished_shooting)
    # The Malignant Plaguecaster's Pestilent Fallout - ninth, and the only one
    # that names a WEAPON as well as a target, so it is handed what was fired.
    shooting_controller.on_squad_finished_shooting.append(
        lambda squad, hit_squads: pestilent_fallout_controller.on_squad_finished_shooting(
            squad, hit_squads,
            weapon_names=[name for name in pestilent_fallout.PLAGUE_WIND_NAMES
                          if shooting_controller.squads_hit_by_weapon(name)],
        )
    )
    # The Plagueburst Crawler's Spore-laced Shock Waves resolves its D3s "after
    # this model has resolved all of its attacks" - the same instant, but it
    # needs no target list, only the shooter.
    shooting_controller.on_squad_finished_shooting.append(
        lambda squad, hit_squads: spore_laced_controller.resolve_after_attacks(squad))
    # "During the Declare Battle Formations step, select one of the Plagues."
    # A hook rather than a pregame state, for the reason PregameController's
    # own on_formations_started comment gives. The lambda re-derives the army
    # from the units the pregame was handed, so only a player actually
    # fielding Death Guard is ever asked.
    pregame_controller.on_formations_started = lambda owners: plague_selection.begin(
        [squad for owner in owners for squad in pregame_controller.army(owner)]
    )
    # Which faction each player fields, for the Game Status panel's badges.
    # Derived from the units themselves rather than configured (see
    # faction.player_factions) and re-derived while still incomplete, for the
    # same reason BattleFocusPool takes a squads_provider: the pre-game
    # sequence's own units only become reachable once it has been handed the
    # armies, so an empty first look is not final. Settles on the first frame
    # that can see both armies and is never recomputed after that.
    player_factions = {}

    def current_player_factions():
        """{player: faction keyword}, derived once and then reused.

        TWO readers, which is why it is a function and not two copies of the
        same three lines: the Game Status panel's badge row, and the turn-start
        banner's own badge (user: "baue dort bitte auch das fraktions Logo
        ein"). A second copy is how one of them ends up answering with a
        half-built pre-game roster while the other has settled."""
        nonlocal player_factions
        if len(player_factions) < 2:
            player_factions = derive_player_factions(_all_squads(state, pregame_controller))
        return player_factions

    def _stats_players():
        """[(player, faction keyword)] in board order, for the Unit Statistics
        overlay's badge row - which doubles as its player switch.

        The THIRD reader of current_player_factions() above, and deliberately
        not a fourth derivation of the same fact: a screen that names an army
        has to name the same one the panel and the turn banner do."""
        factions = current_player_factions()
        return [(player, factions.get(player)) for player in sorted(armies)]

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
    ingress_controller.on_ingress_resolved = [rapid_ingress_controller.notify_placement_resolved]
    # Baharroth's Cloudstrider - both halves are mechanisms that already
    # existed; see game/cloudstrider.py.
    cloudstrider_controller = CloudstriderController(
        game_state=state, decision_manager=decision_manager,
        ingress_controller=ingress_controller, game_log=game_log,
    )
    # "when this unit is SET UP on the battlefield" - the second trigger of
    # Swooping Hawks' Grenade Pack Flyover, and where Baharroth's Cry of the
    # Wind switches on.
    ingress_controller.on_ingress_resolved.append(grenade_pack_controller.offer_after_setup)
    ingress_controller.on_ingress_resolved.append(_note_set_up_on_battlefield)

    # The Deathmarks' Hyperspace Hunters: "when an enemy unit is set up on the
    # battlefield from Reserves within 18" of and visible to this unit". Built
    # HERE rather than beside the other Necron controllers because it needs
    # both shooting_controller (far above) and ingress_controller (just above)
    # - error class 23, and no suite drives main() to find that out.
    #
    # Visibility is the real test, reusing the same line_of_sight call every
    # other "visible to" clause makes - unit to unit, so any living model of
    # the watcher seeing any living model of the arrival.
    def _hunters_can_see(watcher, arrival):
        return any(
            line_of_sight.has_line_of_sight(
                m, t, state.obstacles, state.tokens, state.terrain_areas)
            for m in watcher.models if not m.is_dead()
            for t in arrival.models if not t.is_dead()
        )

    hyperspace_hunters_controller = HyperspaceHuntersController(
        shooting_controller=shooting_controller, decision_manager=decision_manager,
        ingress_controller=ingress_controller, all_tokens=state.tokens,
        game_log=game_log, visible_to=_hunters_can_see, auto_players=ai_players,
    )
    # The arriving unit is set up in the MOVING player's Reinforcements step,
    # so turn_owner is whose Movement phase it is - the printed "your
    # OPPONENT'S" is then the controller's own test.
    ingress_controller.on_ingress_resolved.append(
        lambda squad: hyperspace_hunters_controller.offer_on_arrival(
            squad, turn_tracker.turn_owner))
    homing_beacon_controller = HomingBeaconController(all_tokens=state.tokens, game_log=game_log)
    fire_overwatch_controller = FireOverwatchController(
        stratagem_controller, shooting_controller, all_tokens=state.tokens, turn_tracker=turn_tracker, game_log=game_log,
    )
    # Protector of the Paths' better Snap Shooting threshold lasts only "while
    # resolving that Stratagem", and this is what ends it.
    fire_overwatch_controller.protector_of_the_paths = protector_of_the_paths_discount
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
    # Rule 16.01's two locks: a unit that started an action this turn is not
    # eligible to shoot (excluding TITANIC) and not eligible to declare a
    # charge. Asked of the one ActionController rather than mirrored into
    # per-squad flags, so there is a single record of who is performing what.
    shooting_controller.action_controller = action_controller
    charge_controller.action_controller = action_controller
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
    # Rule 11.04's "ends a Charge move" - the Skorpekh Lord's Crimson Harvest.
    # Fed from ChargeController rather than from a phase hook, because that
    # moment exists nowhere else; and it has to be HERE rather than beside the
    # controller's own construction, since charge_controller is built several
    # hundred lines further down. This is exactly the "built but never fed"
    # wiring that has bitten this project three times (VengefulStarsController,
    # the marks, Path of the Outcast), so test_skorpekh_lord.py's source guard
    # checks for this line by name.
    charge_controller.on_charge_move_finished.append(
        crimson_harvest_controller.on_charge_move_finished)
    # Krootox Rampagers' Kroot Linebreakers - the same hook and the same
    # module as Crimson Harvest above.
    charge_controller.on_charge_move_finished.append(
        kroot_linebreakers_controller.on_charge_move_finished)
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
        # The Kroot Lone-Spear's Advanced Scouting mark. The SAME ledger the
        # shooting controller writes: his ranged hit places it, and his
        # ability's text says "an attack", so a KROOT melee attack reads it too.
        advanced_scouting=advanced_scouting_controller,
        # The SAME bounty ledger the shooting controller holds - one mark,
        # read by both steps.
        bounty_hunters=bounty_hunters_controller,
        # Immortals' Implacable Eradication upgrades its re-roll when the target
        # is within range of an objective marker, and its text says "makes an
        # attack" - so the melee side needs the markers too. ShootingController
        # has carried them since Breach and Clear.
        objectives=state.objectives,
        # Both psychic marks say "makes an attack", not "makes a ranged attack",
        # so they are read here as well as in the Shooting phase. Guide was
        # wired into fight.py's _hit_modifiers() when the Farseer was added but
        # never actually passed in here, so its melee half was dead - caught by
        # Doom needing the same seam.
        guide=guide_controller, doom=doom_controller,
        misfortune=misfortune_controller, spirit_mark=spirit_mark_controller,
        piratical_raiders=piratical_raiders_controller,
        fury_of_the_void=fury_of_the_void_controller,
        whispering_web=whispering_web_controller,
    )

    # Placed AFTER fight_controller: Experimental Modifications takes it for
    # the Fight-phase half of its WHEN, and main() is a 4600-line function in
    # which construction ORDER is the bug (error class 23). Caught here by a
    # smoke run, not by any suite - none of them drives main().
    # --- The T'au detachment Stratagems a human buys proactively -----------
    # Registered in ONE list rather than threaded through ActionPanel.draw()'s
    # forty-parameter, three-stage signature chain one at a time - see
    # game/proactive_stratagems.py. Built unconditionally like every other
    # detachment's: each can_use() gates on its own config setting, so they are
    # inert in a battle nobody plays that detachment in.
    proactive_stratagems = ProactiveStratagems()
    # Seer Council's three proactive Stratagems join the SAME registry. They
    # predate it - each used to be its own parameter through ActionPanel.draw()'s
    # three-stage chain, which is exactly the shape this registry exists to
    # stop, and which also kept the panel's "nothing to do here" hint unaware
    # that one of their buttons was on offer. All three are constructed far
    # above, so they are registered rather than built here.
    proactive_stratagems.add(presentiment_controller)
    proactive_stratagems.add(fate_inescapable_controller)
    proactive_stratagems.add(unshrouded_truth_controller)

    # --- Armoured Warhost's three -----------------------------------------
    # One is a panel button (bought during the unit's own shooting
    # activation); the other two react to a moment - a mortal wound landing,
    # and a fall-back move being made - so they are driven from those hooks
    # and are NOT registered as buttons.
    soulsight_controller = proactive_stratagems.add(SoulsightController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    layered_wards_controller = LayeredWardsController(
        stratagem_controller, decision_manager=decision_manager,
        game_log=game_log, auto_players=ai_players,
    )
    # "Any phase, when a friendly AELDARI VEHICLE unit suffers a mortal wound."
    # MortalWoundAllocationSession is built at a dozen call sites and rolls
    # Feel No Pain for the first wound in its constructor, so the offer hangs
    # on the session itself rather than on any one of those callers - and it
    # PAUSES the session, because a Feel No Pain granted after that first roll
    # would arrive too late for the wound that triggered it.
    MortalWoundAllocationSession.on_mortal_wounds = layered_wards_controller.maybe_offer
    vectored_engines_controller = VectoredEnginesController(
        stratagem_controller, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )

    # --- Path of the Outcast's three --------------------------------------
    # All three print the SAME WHEN - "when a friendly RANGERS/SHROUD RUNNERS
    # unit has shot" - so all three hang on
    # ShootingController.on_squad_finished_shooting rather than on the panel.
    # None is a button: the moment is not one the player picks.
    eldritch_suppression_controller = EldritchSuppressionController(
        stratagem_controller, battle_shock_controller=battle_shock_controller,
        shooting_controller=shooting_controller, decision_manager=decision_manager,
        game_log=game_log, auto_players=ai_players,
    )
    casting_back_the_veil_controller = CastingBackTheVeilController(
        stratagem_controller, decision_manager=decision_manager,
        game_log=game_log, auto_players=ai_players,
    )
    nomads_controller = NomadsOfTheHiddenWayController(
        stratagem_controller, movement_controller=movement_controller,
        dice_manager=dice_manager, decision_manager=decision_manager,
        game_log=game_log, auto_players=ai_players,
    )
    for _outcast in (eldritch_suppression_controller, casting_back_the_veil_controller,
                     nomads_controller):
        shooting_controller.on_squad_finished_shooting.append(
            _outcast.offer_after_shooting)

    # --- Guardian Battlehost's six ----------------------------------------
    # Three are panel buttons; Shield Nodes reacts to a target selection,
    # Vaul's Vengeance to a unit dying, and Cost of Victory to the end of the
    # opponent's Fight phase - so those three are driven from their own hooks.
    warding_salvoes_controller = proactive_stratagems.add(WardingSalvoesController(
        stratagem_controller, shooting_controller=shooting_controller,
        fight_controller=fight_controller, turn_tracker=turn_tracker,
        game_log=game_log,
    ))
    time_to_strike_controller = proactive_stratagems.add(TimeToStrikeController(
        stratagem_controller, movement_controller=movement_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    blades_of_asuryan_controller = proactive_stratagems.add(BladesOfAsuryanController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    shield_nodes_controller = ShieldNodesController(
        stratagem_controller, turn_tracker=turn_tracker, objectives=state.objectives,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    # "just after an enemy unit has selected its targets" - the same instant
    # Stim Injectors and Psychic Shield react at, in BOTH phases because its
    # printed WHEN names both.
    shooting_controller.target_reactions = tuple(shooting_controller.target_reactions) + (
        shield_nodes_controller,)
    fight_controller.target_reactions.append(shield_nodes_controller)
    vauls_vengeance_controller = VaulsVengeanceController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, game_state=state,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    cost_of_victory_controller = CostOfVictoryController(
        stratagem_controller, game_state=state, turn_tracker=turn_tracker,
        all_tokens=state.tokens, decision_manager=decision_manager,
        game_log=game_log, auto_players=ai_players,
    )
    # --- Windrider Host's six -------------------------------------------
    # Four panel buttons, one reactive save and one end-of-phase move. All
    # four buttons register on the shared registry, so the panel needs no
    # parameter for any of them - the whole reason that registry exists.
    wind_of_blades_controller = proactive_stratagems.add(WindOfBladesController(
        stratagem_controller, movement_controller=movement_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    focused_firepower_controller = proactive_stratagems.add(FocusedFirepowerController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    death_from_on_high_controller = proactive_stratagems.add(DeathFromOnHighController(
        stratagem_controller, ingress_controller=ingress_controller,
        shooting_controller=shooting_controller, fight_controller=fight_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    daring_riders_controller = proactive_stratagems.add(DaringRidersController(
        stratagem_controller, ingress_controller=ingress_controller,
        game_state=state, all_tokens=state.tokens,
        setup_controller=setup_controller, turn_tracker=turn_tracker,
        game_log=game_log,
    ))
    # "when doing so, IF your unit is set up within 8"" - answered from the
    # arrival itself, because it is about where the models ended up.
    ingress_controller.on_ingress_resolved.append(
        daring_riders_controller.notify_arrival)
    # Spiralling Evasion reacts to target selection in the opponent's SHOOTING
    # phase only, so it joins that one list and deliberately not the Fight
    # phase's twin.
    spiralling_evasion_controller = SpirallingEvasionController(
        stratagem_controller, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    # A TUPLE on this controller and a list on the fight one - the two
    # were built differently, so appending here is the wrong verb.
    shooting_controller.target_reactions = tuple(
        shooting_controller.target_reactions) + (spiralling_evasion_controller,)
    overflight_controller = OverflightController(
        stratagem_controller, movement_controller=movement_controller,
        turn_tracker=turn_tracker, decision_manager=decision_manager,
        game_log=game_log, auto_players=ai_players,
    )
    # --- Warhost's six ---------------------------------------------------
    blitzing_firepower_controller = proactive_stratagems.add(BlitzingFirepowerController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    # Lightning-Fast Reactions prints "your opponent's Shooting phase OR the
    # Fight phase", so unlike Spiralling Evasion beside it, it joins BOTH
    # reaction lists.
    lightning_fast_reactions_controller = LightningFastReactionsController(
        stratagem_controller, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    shooting_controller.target_reactions = tuple(
        shooting_controller.target_reactions) + (lightning_fast_reactions_controller,)
    fight_controller.target_reactions.append(lightning_fast_reactions_controller)
    feigned_retreat_controller = FeignedRetreatController(
        stratagem_controller, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    # "Just after an ASURYANI unit Falls Back" - a moment this engine did not
    # publish until now. ASSIGNED rather than appended to: the controller's
    # default is an empty TUPLE, a class attribute so every existing
    # FallBackController keeps working without a constructor change.
    fall_back_controller.on_fall_back_finished = [
        feigned_retreat_controller.notify_fell_back]
    warhost_fire_and_fade_controller = WarhostFireAndFadeController(
        stratagem_controller, movement_controller=movement_controller,
        turn_tracker=turn_tracker, dice_manager=dice_manager,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    shooting_controller.on_squad_finished_shooting.append(
        warhost_fire_and_fade_controller.offer_after_shooting)
    webway_tunnel_controller = WebwayTunnelController(
        stratagem_controller, game_state=state, turn_tracker=turn_tracker,
        all_tokens=state.tokens, board_width_in=config.BOARD_WIDTH_IN,
        board_height_in=config.BOARD_HEIGHT_IN,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    # Skyborne Sanctuary is printed by TWO detachments, word for word - one
    # module, one instance per printing, each with its own gate. Aspect Host's
    # copy joins this list in its own stage.
    skyborne_sanctuary_controllers = [
        SkyborneSanctuaryController(
            stratagem_controller, setting, transport_controller=transport_controller,
            fight_controller=fight_controller, game_state=state,
            all_tokens=state.tokens, turn_tracker=turn_tracker,
            decision_manager=decision_manager, game_log=game_log,
            auto_players=ai_players,
        )
        for setting in (martial_grace.SETTING,)
    ]
    # --- Spirit Conclave's six -------------------------------------------
    seers_eye_controller = proactive_stratagems.add(SeersEyeController(
        stratagem_controller, all_tokens=state.tokens,
        visible=(lambda observer, target: line_of_sight.has_line_of_sight(
            observer, target, state.obstacles, state.tokens)),
        shooting_controller=shooting_controller, fight_controller=fight_controller,
        turn_tracker=turn_tracker, decision_manager=decision_manager,
        game_log=game_log, auto_players=ai_players,
    ))
    blades_from_beyond_controller = proactive_stratagems.add(BladesFromBeyondController(
        stratagem_controller, fight_controller=fight_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    soul_bridge_controller = proactive_stratagems.add(SoulBridgeController(
        stratagem_controller, all_tokens=state.tokens, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    ))
    spirit_token_controller = proactive_stratagems.add(SpiritTokenController(
        stratagem_controller, objectives=state.objectives,
        movement_controller=movement_controller, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    ))
    # Wraithbone Armour reacts in BOTH attack phases, like Lightning-Fast
    # Reactions above.
    wraithbone_armour_controller = WraithboneArmourController(
        stratagem_controller, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    shooting_controller.target_reactions = tuple(
        shooting_controller.target_reactions) + (wraithbone_armour_controller,)
    fight_controller.target_reactions.append(wraithbone_armour_controller)
    crushing_strides_controller = CrushingStridesController(
        dice_manager=dice_manager, decision_manager=decision_manager,
        game_log=game_log, game_state=state, auto_players=ai_players,
        target_pick=_best_damage_target,
        stratagem_controller=stratagem_controller, turn_tracker=turn_tracker,
    )
    charge_controller.on_charge_move_finished.append(
        crushing_strides_controller.on_charge_move_finished)
    # --- Aspect Host's six -----------------------------------------------
    warrior_focus_controller = proactive_stratagems.add(WarriorFocusController(
        stratagem_controller, shooting_controller=shooting_controller,
        fight_controller=fight_controller, turn_tracker=turn_tracker,
        game_log=game_log,
    ))
    doom_inescapable_controller = proactive_stratagems.add(DoomInescapableController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    preternatural_precision_controller = proactive_stratagems.add(
        PreternaturalPrecisionController(
            stratagem_controller, shooting_controller=shooting_controller,
            turn_tracker=turn_tracker, decision_manager=decision_manager,
            game_log=game_log, auto_players=ai_players,
        ))
    # To Their Final Breath is Undying Spite's twin, so it takes the same three
    # seams: the Fight-phase reaction list, the death sweep, and the
    # after-the-attacker-has-finished resolution.
    to_their_final_breath_controller = ToTheirFinalBreathController(
        stratagem_controller, fight_controller=fight_controller, game_state=state,
        turn_tracker=turn_tracker, decision_manager=decision_manager,
        game_log=game_log, auto_players=ai_players,
    )
    fight_controller.target_reactions.append(to_their_final_breath_controller)
    khaines_vengeance_controller = KhainesVengeanceController(
        stratagem_controller, dice_manager=dice_manager, all_tokens=state.tokens,
        turn_tracker=turn_tracker, decision_manager=decision_manager,
        game_log=game_log, auto_players=ai_players,
    )
    # "Just after an enemy unit IS SELECTED to Fall Back" - the OTHER Fall Back
    # instant, one word apart from Feigned Retreat's.
    fall_back_controller.on_fall_back_declared = [
        khaines_vengeance_controller.notify_selected_to_fall_back]
    # Skyborne Sanctuary's SECOND printing - one module, one instance per
    # detachment that prints it, each with its own gate.
    skyborne_sanctuary_controllers.append(SkyborneSanctuaryController(
        stratagem_controller, aspect_warrior_focus.SETTING,
        transport_controller=transport_controller, fight_controller=fight_controller,
        game_state=state, all_tokens=state.tokens, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    ))
    # Vaul's Vengeance fires "after that enemy unit has finished making its
    # attacks", which is one instant in each attack phase.
    shooting_controller.on_squad_finished_shooting.append(
        lambda squad, hits: vauls_vengeance_controller.on_attacker_finished(squad))
    # Experimental Ammunition prints two modes joined by "OR", so it is two
    # buttons over one Stratagem - buying either spends the once-per-phase
    # allowance, because they share a name in rule 15.01's ledger.
    experimental_ammunition_controllers = [
        proactive_stratagems.add(ExperimentalAmmunitionController(
            stratagem_controller, shooting_controller=shooting_controller,
            turn_tracker=turn_tracker, game_log=game_log, mode=mode,
        ))
        for mode in (MODE_STRENGTH, MODE_STRENGTH_AP_HAZARDOUS)
    ]
    experimental_modifications_controller = proactive_stratagems.add(
        ExperimentalModificationsController(
            stratagem_controller, shooting_controller=shooting_controller,
            fight_controller=fight_controller, turn_tracker=turn_tracker,
            game_log=game_log,
        ))
    alien_expertise_controller = proactive_stratagems.add(AlienExpertiseController(
        stratagem_controller, movement_controller=movement_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    guided_fire_controller = proactive_stratagems.add(GuidedFireController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))

    # --- Kauyon's six -----------------------------------------------------
    # The three proactive ones join the panel registry; the three that react to
    # something (a charge declaration, the end of a Fight phase) are driven
    # from their own hooks instead and are NOT registered as buttons.
    point_blank_ambush_controller = proactive_stratagems.add(PointBlankAmbushController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    coordinate_to_engage_controller = proactive_stratagems.add(CoordinateToEngageController(
        stratagem_controller, shooting_controller=shooting_controller,
        greater_good=greater_good_controller, turn_tracker=turn_tracker,
        game_log=game_log,
    ))
    tempting_trap_controller = proactive_stratagems.add(TemptingTrapController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, objectives=state.objectives,
        deployment_zones={z.owner: z for z in getattr(state, "deployment_zones", []) or []},
        decision_manager=decision_manager, game_log=game_log,
    ))
    # A Tempting Trap is read at the WOUND step, so the shooting controller
    # needs it - assigned after construction, like the prey mark above.
    shooting_controller.tempting_trap = tempting_trap_controller
    wall_of_mirrors_controller = WallOfMirrorsController(
        stratagem_controller, game_state=state, turn_tracker=turn_tracker,
        all_tokens=state.tokens, decision_manager=decision_manager, game_log=game_log,
        # auto_players, like every other reactive Stratagem: this controller
        # READS it and never used to be given it, so the AI fell through to
        # _maybe_resolve_decision() and paid a real API call. Inert until now
        # only because no shipped list fields this detachment.
        auto_players=ai_players,
    )
    photon_grenades_controller = PhotonGrenadesController(
        stratagem_controller, turn_tracker=turn_tracker, all_tokens=state.tokens,
        battle_shock_controller=battle_shock_controller,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    combat_embarkation_controller = CombatEmbarkationController(
        stratagem_controller, transport_controller=transport_controller,
        turn_tracker=turn_tracker, all_tokens=state.tokens,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players, charge_controller=charge_controller,
    )
    # Both react to "an enemy unit has declared a charge". The list is CHAINED
    # (see game/charge.py), so each gets its own window instead of the first
    # one swallowing the second - which is why on_charge_declared could not
    # simply take a third owner.
    charge_controller.charge_declaration_reactions.extend([
        photon_grenades_controller.maybe_offer,
        combat_embarkation_controller.maybe_offer,
    ])

    # --- Mont'ka's six ----------------------------------------------------
    aggressive_mobility_controller = proactive_stratagems.add(AggressiveMobilityController(
        stratagem_controller, movement_controller=movement_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    combat_debarkation_controller = proactive_stratagems.add(CombatDebarkationController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    focused_fire_controller = proactive_stratagems.add(FocusedFireController(
        stratagem_controller, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, all_tokens=state.tokens,
        decision_manager=decision_manager, game_log=game_log,
    ))
    # Reactive, so no panel button: they answer their own hooks.
    pinpoint_controller = PinpointCounterOffensiveController(
        stratagem_controller, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    # Read by BOTH attack steps - "an attack", not "a ranged attack".
    shooting_controller.pinpoint_counter_offensive = pinpoint_controller
    fight_controller.pinpoint_counter_offensive = pinpoint_controller
    pulse_onslaught_controller = PulseOnslaughtController(
        stratagem_controller, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    shooting_controller.on_squad_finished_shooting.append(
        pulse_onslaught_controller.offer_after_shooting)
    counterfire_defence_controller = CounterfireDefenceController(
        stratagem_controller, turn_tracker=turn_tracker,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    # "just after an enemy unit has selected its targets" - the same instant
    # Stim Injectors and Kroot Packmates react at.
    shooting_controller.target_reactions = tuple(shooting_controller.target_reactions) + (
        counterfire_defence_controller,)

    # --- Advanced Acquisition Cadre's three -------------------------------
    # NOT on the proactive registry: its printed WHEN is "End of your Movement
    # phase", and Objective.controlled_by is only recomputed at a phase
    # boundary (14.02) - so a mid-phase button could only ever see the board as
    # it stood BEFORE anything moved, which is the one case the Stratagem is
    # not for. Offered from the end-of-Movement-phase block instead, right
    # after update_control(). Reported: "Stratagem marker beacon wird nie
    # angeboten".
    marker_beacon_controller = MarkerBeaconController(
        stratagem_controller, turn_tracker=turn_tracker, objectives=state.objectives,
        all_tokens=state.tokens, decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    microdrone_support_controller = proactive_stratagems.add(MicrodroneSupportController(
        stratagem_controller, action_controller=action_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    ))
    # Reactive. Its "if that friendly unit is hidden" clause needs the terrain,
    # the tracker and the shooting record, so it is handed a callable that
    # answers rule 13.09 rather than reaching for that state itself.
    autoreactive_camouflage_controller = AutoreactiveCamouflageController(
        stratagem_controller, turn_tracker=turn_tracker,
        is_hidden_check=lambda squad: any(
            status_effects.is_hidden(m, state.terrain_areas, turn_tracker,
                                     shooting_controller.last_ranged_attack_turn)
            for m in squad.models if not m.is_dead()),
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )
    shooting_controller.target_reactions = tuple(shooting_controller.target_reactions) + (
        autoreactive_camouflage_controller,)
    # "Change one die to an unmodified 6" (Aspect Shrine tokens, the Farseer's
    # Branching Fates). Built here rather than inside either attack controller
    # because it spans both of them - it reads whichever one has a weapon group
    # open. User: "kann das nicht eine option im linken panel sein, statt eines
    # overlays? command reroll funktioniert ja auch so."
    unmodified_six_controller = UnmodifiedSixController(
        dice_manager, attack_controllers=(shooting_controller, fight_controller),
        game_log=game_log,
    )

    # --- Awakened Dynasty, the six protocols ------------------------------
    # Built unconditionally, like the Necron datasheet controllers above:
    # every gate also checks awakened_dynasty.stratagem_target_ok(), which is
    # False for a non-Necron unit and for a player without the detachment, so
    # they are inert for an Ork game rather than needing a None check at each
    # call site.
    hungry_void_controller = HungryVoidController(
        stratagem_controller, turn_tracker=turn_tracker,
        fight_controller=fight_controller, game_log=game_log,
    )
    sudden_storm_controller = SuddenStormController(
        stratagem_controller, turn_tracker=turn_tracker, game_log=game_log,
        dice_manager=dice_manager, decision_manager=decision_manager,
        auto_players=ai_players,
    )
    conquering_tyrant_controller = ConqueringTyrantController(
        stratagem_controller, turn_tracker=turn_tracker,
        shooting_controller=shooting_controller, game_log=game_log,
    )
    undying_legions_controller = UndyingLegionsController(
        stratagem_controller, dice_manager=dice_manager,
        decision_manager=decision_manager, game_log=game_log, game_state=state,
        position_valid=_necron_position_valid, auto_players=ai_players,
        # Rule 01.02.03: the models this Stratagem brings back are SET UP, so a
        # human sets them up. Built after return_placement_controller, hence a
        # constructor argument rather than an assignment.
        placer=return_placement_controller,
    )
    eternal_revenant_controller = EternalRevenantController(
        stratagem_controller, decision_manager=decision_manager, game_log=game_log,
        game_state=state, position_valid=_necron_position_valid,
        auto_players=ai_players,
    )

    def _vengeful_stars_worth_it(avenger, killer):
        """2 CP is the most expensive protocol, so the AI only takes the shot
        when it is worth something - measured with the SAME
        game/damage_estimate.py value every other deterministic CP decision
        here uses, rather than a second opinion."""
        return (ai_observation.damage_value(avenger, killer) or 0.0) > 0.0

    vengeful_stars_controller = VengefulStarsController(
        stratagem_controller, decision_manager=decision_manager, game_log=game_log,
        game_state=state, shooting_controller=shooting_controller,
        turn_tracker=turn_tracker, auto_players=ai_players,
        worth_using=_vengeful_stars_worth_it,
    )

    # --- The six Death Lord's Chosen Stratagems -------------------------------
    # Built unconditionally like every other detachment's: each one's can_use()
    # goes through death_lords_chosen.stratagem_target_ok(), which reads
    # config.DEATH_LORDS_CHOSEN_PLAYERS, so they are inert in a game nobody
    # plays that detachment in.
    #
    # THREE get an AI path and three deliberately do not (user instruction:
    # "GRIM REAPERS - erste Gelegenheit / UNDYING SPITE - wenn rechnerisch ein
    # Terminator im Nahkampf sterben wuerde / SICKENING IMPACT - erste
    # Gelegenheit; der Rest ist irrelevant fuer die KI"). The two REACTIVE ones
    # answer inside their own controllers via auto_players and need nothing in
    # ai/; Grim Reapers is proactive and gets a handler there instead.
    blooming_pestilence_controller = BloomingPestilenceController(
        stratagem_controller, nurgles_gift_controller=nurgles_gift_controller,
        turn_tracker=turn_tracker, game_log=game_log,
    )
    grim_reapers_controller = GrimReapersController(
        stratagem_controller, turn_tracker=turn_tracker,
        fight_controller=fight_controller, game_log=game_log,
    )
    mortarions_teachings_controller = MortarionsTeachingsController(
        stratagem_controller, turn_tracker=turn_tracker,
        shooting_controller=shooting_controller, game_log=game_log,
    )
    signal_pox_controller = SignalPoxController(
        stratagem_controller, nurgles_gift_controller=nurgles_gift_controller,
        decision_manager=decision_manager, turn_tracker=turn_tracker,
        game_log=game_log, game_state=state,
    )
    sickening_impact_controller = SickeningImpactController(
        stratagem_controller, dice_manager=dice_manager,
        decision_manager=decision_manager, turn_tracker=turn_tracker,
        game_log=game_log, game_state=state, auto_players=ai_players,
    )

    def _undying_spite_worth_it(attacker, defender):
        """The user's rule: buy it when, computationally, at least one
        Terminator would die to this melee attack.

        Measured with the SAME game/damage_estimate.py value every other
        deterministic CP decision here uses, rather than a second opinion - and
        injected rather than imported, because game/ does not depend on ai/."""
        estimate = ai_observation.expected_kills(attacker, defender, melee=True)
        if not estimate:
            return False
        return (estimate.get("models") or 0.0) >= UndyingSpiteController.MIN_EXPECTED_KILLS

    undying_spite_controller = UndyingSpiteController(
        stratagem_controller, dice_manager=dice_manager,
        decision_manager=decision_manager, turn_tracker=turn_tracker,
        fight_controller=fight_controller, game_log=game_log, game_state=state,
        auto_players=ai_players, worth_using=_undying_spite_worth_it,
    )
    # "Just after an enemy unit has selected its targets" - the list every
    # reaction of that timing sits in. Appended rather than passed at
    # construction because fight_controller was built above; FightController
    # turns the field into a list for exactly this.
    fight_controller.target_reactions.append(undying_spite_controller)
    # Wraithblades' Malevolent Souls - the same "dead model strikes back"
    # mechanism as Undying Spite (they share game/fight_after_death.py), but a
    # printed datasheet ability rather than a Stratagem: always on, 3+ instead
    # of 4+, and restricted to deaths caused by a MELEE attack. Nothing to
    # offer, so no DecisionManager and no auto_players. Constructed HERE, after
    # fight_controller, because it reads that controller's fought_squad_ids.
    malevolent_souls_controller = MalevolentSoulsController(
        game_state=state, game_log=game_log, turn_tracker=turn_tracker,
        fight_controller=fight_controller)
    # The Cryptothralls' Systematic Vigour - the third consumer of the same
    # shared ledger, built beside the second for the same reason.
    systematic_vigour_controller = SystematicVigourController(
        game_state=state, game_log=game_log, turn_tracker=turn_tracker,
        fight_controller=fight_controller)
    # The Wraithlord's Fated Hero picks its hated keyword in the pre-battle
    # step registered further down; the controller has to exist before both
    # attack controllers are handed it.
    fated_hero_controller = FatedHeroController(
        game_state=state, game_log=game_log, decision_manager=decision_manager,
        auto_players=ai_players)
    # Yvraine's Herald of Ynnead marks an enemy unit at the start of the
    # Fight phase and BOTH attack steps read it - "makes an attack", not
    # "a melee attack" - so it is built here beside Fated Hero, which has
    # the same two readers for the same reason.
    herald_of_ynnead_controller = HeraldOfYnneadController(
        decision_manager=decision_manager, game_log=game_log,
        all_tokens=state.tokens, auto_players=ai_players)
    fight_controller.herald_of_ynnead = herald_of_ynnead_controller
    shooting_controller.herald_of_ynnead = herald_of_ynnead_controller
    # Aspect Host's Path of the Warrior: one choice per unit per phase, made
    # when it is selected to shoot or to fight, so BOTH attack controllers
    # offer it and both read it. Built beside Herald of Ynnead for the same
    # reason - two readers, so it has to exist before either is finished.
    path_of_the_warrior_controller = PathOfTheWarriorController(
        decision_manager=decision_manager, game_log=game_log,
        turn_tracker=turn_tracker, auto_players=ai_players)
    fight_controller.path_of_the_warrior = path_of_the_warrior_controller
    shooting_controller.path_of_the_warrior = path_of_the_warrior_controller
    # Armoured Warhost's Guiding Presence: chosen at the start of its owner's
    # Shooting phase and read by the hit step, so it is built here beside the
    # other Aeldari detachment collaborators - after shooting_controller,
    # which it is assigned onto. `visible` is the real line-of-sight test the
    # card prints ("select one VISIBLE friendly ... unit"); the same callable
    # Seer's Eye takes.
    guiding_presence_controller = GuidingPresenceController(
        game_state=state, decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
        visible=lambda observer, other: line_of_sight.has_line_of_sight(
            observer, other, state.obstacles, state.tokens, state.terrain_areas),
    )
    shooting_controller.guiding_presence = guiding_presence_controller
    shooting_controller.protector_of_the_paths = protector_of_the_paths_discount
    # Spirit Conclave's Shepherds of the Dead: Vengeful Dead tokens, read by
    # BOTH roll steps in BOTH attack controllers, plus a Battle Focus aura.
    shepherds_of_the_dead_controller = ShepherdsOfTheDeadController(
        game_log=game_log, all_tokens=state.tokens)
    fight_controller.shepherds_of_the_dead = shepherds_of_the_dead_controller
    shooting_controller.shepherds_of_the_dead = shepherds_of_the_dead_controller
    # Word of the Phoenix returns destroyed bodyguards INTO a standing
    # unit, so it needs the setup controller's position_valid() for the
    # placement and the token list for the Engagement Range test that
    # position_valid() deliberately does not do.
    word_of_the_phoenix_controller = WordOfThePhoenixController(
        dice_manager=dice_manager, game_state=state, game_log=game_log,
        setup_controller=setup_controller, all_tokens=state.tokens,
        decision_manager=decision_manager, auto_players=ai_players)
    # Inevitable Death moves a LIVING model to where somebody else died,
    # so unlike every other user of this shape it returns nothing to the
    # board and only needs the spot search.
    inevitable_death_controller = InevitableDeathController(
        game_state=state, game_log=game_log, decision_manager=decision_manager,
        setup_controller=setup_controller, all_tokens=state.tokens,
        turn_tracker=turn_tracker, auto_players=ai_players)
    fight_controller.fated_hero = fated_hero_controller
    # Raid and Run samples "was eligible to fight this phase" off the fight
    # controller, which is built after it - so the back-reference is filled in
    # here, the same shape targeting_array's is.
    raid_and_run_controller.fight_controller = fight_controller
    shooting_controller.fated_hero = fated_hero_controller
    # "Just after a TERMINATOR unit ends a Charge move" - the hook the Skorpekh
    # Lord's Crimson Harvest introduced, and deliberately not _finish_charge().
    charge_controller.on_charge_move_finished.append(
        sickening_impact_controller.on_charge_move_finished)

    # Undying Legions' WHEN is "just after an enemy unit has RESOLVED its
    # attacks", which is a different instant from the target_reactions list
    # ('Ard as Nails et al. fire at "just after it has SELECTED its targets").
    # So it hangs off the after-resolution hooks instead.
    def _necron_after_enemy_shooting(shooter_squad, target_squads=()):
        for target in target_squads or ():
            if undying_legions_controller.maybe_offer(target):
                break
        vengeful_stars_controller.maybe_offer()
        # Mont'ka's Pinpoint Counter-Offensive: the death sweep regularly
        # cannot name the killer (active_squad is already None once the
        # activation has closed, which is exactly the case where a unit was
        # wiped out), so it stashes the death and is answered HERE, where the
        # attacker arrives as an argument. Same deferral as Vengeful Stars
        # directly above, and for the same reason.
        pinpoint_controller.maybe_offer(shooter_squad)
        # Overflight's kill ledger has the same hole and is settled the same
        # way: the sweep hands it killer_squad=None whenever the last weapon
        # group of an activation wipes a unit, which is the ordinary way a
        # Windrider unit destroys something.
        overflight_controller.credit_owed_kills(shooter_squad)

    shooting_controller.on_squad_finished_shooting.append(_necron_after_enemy_shooting)

    # The Chaos Spawn's Lethal Ichor is counted per melee attack ALLOCATED to
    # its unit, which only FightController sees - a SAVED attack still counts,
    # so it cannot be reconstructed from casualties afterwards. Assigned here
    # rather than at the controller's own construction because that block runs
    # ~150 lines before FightController exists (error class 23).
    fight_controller.lethal_ichor = lethal_ichor_controller

    _previous_finished_fighting = fight_controller.on_unit_finished_fighting

    def _necron_after_enemy_fight(*args):
        # Vengeful Stars is Shooting-phase only ("your opponent's SHOOTING
        # phase"), so only Undying Legions is offered here.
        for squad in {t.squad for t in state.tokens if t.squad is not None}:
            if undying_legions_controller.maybe_offer(squad):
                break
        # Two Death Guard abilities share this exact instant, and both are
        # written as "after the attacking unit has finished making its
        # attacks": the Chaos Spawn's Lethal Ichor (which hurts the ATTACKER)
        # and the Poxwalkers' Curse of the Walking Pox (which brings a model
        # back to the attacker's own unit, when the attacker is the Poxwalkers).
        _fighter = args[0] if args else None
        if _fighter is not None:
            curse_of_the_walking_pox_controller.resolve_after_attacks(_fighter)
            lethal_ichor_controller.on_unit_finished_fighting(_fighter)
            # "...it can fight after the attacking unit has finished making its
            # attacks, and is THEN removed from play." The activation itself
            # runs through the ordinary fight step; this is the removal half.
            undying_spite_controller.resolve_after_attacks(_fighter)
            to_their_final_breath_controller.resolve_after_attacks(_fighter)
            malevolent_souls_controller.resolve_after_attacks(_fighter)
            systematic_vigour_controller.resolve_after_attacks(_fighter)
            # Vaul's Vengeance: "after that enemy unit has finished making its
            # attacks" - the melee half of the same instant.
            vauls_vengeance_controller.on_attacker_finished(_fighter)
            # Pinpoint Counter-Offensive's WHEN is "any phase", so the melee
            # attacker answers the same owed deaths the shooting hook does.
            pinpoint_controller.maybe_offer(_fighter)
            # Overflight's Fight-phase half needs the same settlement - it is
            # the half that belongs to nobody, so it fires in the opponent's
            # turn too.
            overflight_controller.credit_owed_kills(_fighter)
        if _previous_finished_fighting is not None:
            _previous_finished_fighting(*args)

    fight_controller.on_unit_finished_fighting = _necron_after_enemy_fight

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
    # The Autarch Wayleaper's Indomitable Strength of Will refunds a Battle
    # Focus token on a 3+, and is read from the POOL's own spend - so it is
    # attached here, after the pool exists.
    indomitable_controller = IndomitableStrengthOfWillController(
        battle_focus=battle_focus_pool, game_log=game_log)
    battle_focus_pool.indomitable = indomitable_controller
    # Timeless Strategist counts a bearer riding in a transport that is on the
    # battlefield - the same source game/secondary_missions.py takes for the
    # same question.
    battle_focus_pool.set_embarked_source(lambda: state.embarked_squads)
    shooting_controller.on_squad_finished_shooting.append(battle_focus_pool.offer_fade_back)
    # TWO reactors on one slot now, so it becomes an ordered pair rather than
    # a single callable. The squad is captured ONCE and handed to both - the
    # lesson the charge-declaration chain taught, where a per-step re-read of
    # active_squad handed None to the second reactor after the first ended the
    # charge. Battle Focus goes first because it was here first and may open a
    # reactive move; a Stratagem prompt queued behind it is answered after,
    # which DecisionManager's queue handles.
    def _on_fall_back_finished(squad, *args, **kwargs):
        battle_focus_pool.offer_opportunity_seized(squad, *args, **kwargs)
        vectored_engines_controller.offer_after_fall_back(squad)

    movement_controller.on_fall_back_finished = _on_fall_back_finished
    # Seer Council's Isha's Fury: "just after an enemy unit ends a Normal,
    # Advance or Fall Back move" - broader than the Fall-Back-only hook above,
    # and fired at the same point for the same reason.
    movement_controller.on_move_finished = [
        ishas_fury_controller.offer_after_move,
        path_of_the_outcast_controller.offer_after_move,
        grenade_pack_controller.offer_after_move,
    ]
    # Aeldari Seer Council detachment rule Strands of Fate: a Fate dice pool
    # rolled ONCE for the whole battle, where each die's FACE decides which one
    # stratagem it can discount. Plugged into the same cost-discount hook
    # Puretide's Teachings uses, so StratagemController never learns this rule
    # exists. Whose army has the detachment is a setting, not a derivation -
    # see config.SEER_COUNCIL_PLAYERS.
    fate_dice_pool = strands_of_fate.FateDicePool(game_log=game_log)
    # Seer Council's Lucid Eye edits that pool directly - a Fate die's FACE is
    # which Stratagem it pays for, so +-1 REPLACES an entry rather than adding
    # a bonus on top. Built here, after the pool it reads.
    lucid_eye_controller = LucidEyeController(
        game_state=state, fate_pool=fate_dice_pool,
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players)
    # Windrider Host's Echoes of Ulthanesh - the deployment ZONES are the real
    # condition, so it gets the shapes rather than a board half.
    echoes_of_ulthanesh_controller = EchoesOfUlthaneshController(
        game_state=state, command_points=command_points, turn_tracker=turn_tracker,
        game_log=game_log,
        zones={z.owner: (z, next((o for o in state.deployment_zones if o.owner != z.owner), None))
               for z in getattr(state, "deployment_zones", []) or []})
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
    #
    # CHAINED, not assigned. on_unit_finished_fighting is a single SLOT, and a
    # plain assignment here silently threw away the seven abilities the block
    # ~120 lines above hangs off the same instant (Undying Legions, Curse of
    # the Walking Pox, Lethal Ichor, Undying Spite, To Their Final Breaths,
    # Malevolent Souls, Vaul's Vengeance). Every one of them had a green suite,
    # because those drive the controllers directly - only the source shows a
    # slot being written twice. test_event_chain_wiring.py section 9 now
    # refuses a second bare assignment to any single-slot callback in main().
    #
    # ORDER: the after-attack abilities resolve first and the Counteroffensive
    # offer last - 15.12 reacts to a fight that is over, so everything that
    # fight still owes has to have happened by then.
    _fight_finished_before_counteroffensive = fight_controller.on_unit_finished_fighting

    def _after_unit_finished_fighting(squad):
        if _fight_finished_before_counteroffensive is not None:
            _fight_finished_before_counteroffensive(squad)
        counteroffensive_controller.offer_after(squad, decision_manager)

    fight_controller.on_unit_finished_fighting = _after_unit_finished_fighting
    consolidate_controller = ConsolidateController(
        game_log=game_log, turn_tracker=turn_tracker, all_tokens=state.tokens,
        movement_controller=movement_controller, fight_controller=fight_controller, objectives=state.objectives,
    )
    # Battle Focus' Sudden Strike is offered in a second window, just before
    # the unit makes its Consolidation move - see can_sudden_strike(). Wired
    # HERE and not at the pool's constructor ~100 lines up, because this
    # controller does not exist yet up there.
    battle_focus_pool.consolidate_controller = consolidate_controller
    coherency_enforcer = CoherencyEnforcer(all_tokens=state.tokens, game_log=game_log)
    renderer = Renderer(render_scale=render_ppi / config.PIXELS_PER_INCH)
    action_panel = ActionPanel()
    game_status_panel = GameStatusPanel()
    mission_cards_overlay = MissionCardsOverlay()
    # The click-away "you drew these" notice. Attached to the deck now that
    # the UI exists - the deck itself was built ~700 lines up, next to the
    # ledger it credits.
    mission_draw_overlay = MissionDrawOverlay()
    # Rule 07.01: shown once the last battle round has been played out.
    battle_end_overlay = BattleEndOverlay()
    secondary_mission_controller.draw_overlay = mission_draw_overlay
    secondary_mission_controller.flush_announcements()
    log_panel = LogPanel()
    dice_panel = DicePanel()
    decision_overlay = DecisionOverlay()
    stratagem_notice_overlay = StratagemNoticeOverlay()
    waaagh_notice_overlay = WaaaghNoticeOverlay()
    ai_offline_overlay = AIOfflineOverlay()
    turn_start_overlay = TurnStartOverlay()
    fight_warning_overlay = FightWarningOverlay()
    army_rules_overlay = ArmyRulesOverlay()
    unit_stats_overlay_view = UnitStatsOverlay()
    # The in-game half of the game menu (user: "im spiel öffnet ein druck auf
    # ESC das menü"). Same object as the startup screen, different host - see
    # game/ui/game_menu.py for why the two are one class.
    game_menu = GameMenu(in_game=True)
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
    stratagem_tooltip = StratagemTooltip()
    agent = ClaudeAgent(model=config.AI_MODEL, planning_model=config.AI_PLANNING_MODEL)  # swap for MockAgent() for a free/offline smoke test
    ai_memory = AIMemory()
    last_shown_turn_plan = None  # object identity of the AIMemory.turn_plan last shown via turn_plan_overlay - see run_ai_action()
    loading_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 10, bold=True)
    # Every "Player 2 is busy" corner badge - the flashed pause before a
    # blocking Claude call, the threaded planning wait, the AUTO-PLAY
    # reminder - goes through this one object, so the three read as the same
    # HUD element instead of three hand-drawn rects that drift apart.
    ai_busy_badge = AiBusyBadge()
    ai_toggle_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
    # Where the switch was drawn LAST frame. The rect is produced by drawing,
    # and the click arrives before the next draw, so the hit-test reads this
    # rather than recomputing the geometry - two computations of one rect is
    # how a control ends up clickable somewhere it is not drawn.
    ai_toggle_rect = None
    # Same story for the Unit Statistics button that sits beside it - it is
    # placed FROM the switch's drawn rect, so it only exists once the switch
    # has been drawn.
    stats_button_rect = None

    def _set_ai_mode(on, source):
        """The one place the mode changes, so every route logs it the same.

        The log line is what made the reported bug legible in the first place
        ("Player 2: auto-play OFF" at line 17, a CP spent at line 175), so it
        keeps its shape and gains the source that flipped it."""
        ai_mode.set_enabled(on)
        game_log.add(f"Player 2: AI mode {'ON' if on else 'OFF'} ({source}).")
        return on
    # The side panels are the only things covered while the AI is busy (User:
    # "damit man nicht in die Versuchung kommt, irgendwelche Knoepfe druecken
    # zu wollen") - the board itself stays fully legible, which was the whole
    # point of dropping the old full-window dim.
    ai_busy_dim_rects = (left_panel_rect, right_panel_rect)
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
    # squad's models and every model of every enemy squad on the board -
    # unlike get_shoot_targets() above, nothing guarded this from being
    # recomputed both every single rendered frame AND a second time on every
    # click attempt while the "Mark Spotted Target" screen was up. Real user
    # report ("the game crashed when I clicked Mark Spotted Target with the
    # Stealth Battlesuits" - actually a multi-second-per-frame freeze, not a
    # crash). Same fix as get_shoot_targets(): one cached computation per
    # actual state change, shared between rendering and click validation.
    #
    # THIS CACHE ONLY EVER COVERED HALF THE PROBLEM, and the other half was
    # the whole of a second report ("wenn man tau spielt ist die shooting
    # phase sehr laggy"). It is keyed on state == CHOOSING_TARGET, i.e. the
    # highlight AFTER the button is pressed; the panel calls can_use() every
    # frame BEFORE that, in state IDLE, where this returns an empty set and
    # helps not at all. Measured on a 179-model map2 board: 4732 ms per
    # eligible_targets() call, every frame a T'au unit was selected.
    # can_use() now goes through GreaterGoodController.any_eligible_target(),
    # which has a cache of its own with a stricter key (positions included,
    # see game/board_epoch.py) - so this one is no longer the only guard, and
    # its own key deliberately stays as it is: acting_squad is only ever set
    # while a marking flow is open, which is a moment when nothing moves.
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
    def board_unit_pick():
        """The pending decision as a CLICK-A-UNIT-ON-THE-BOARD pick, or None.

        Derived fresh rather than cached in a frame local, because resolving one
        pick can enqueue the next decision inside the very same event (Burden of
        Trust walks one objective at a time), and a record captured at the top
        of the frame would then be answering for a question that is already
        gone. game/unit_pick.pending() is the ONE definition; the event branch,
        the left panel, the board highlight and the decision overlay all read
        this and nothing else, so they cannot disagree about who is eligible."""
        return unit_pick.pending(decision_manager, state.tokens)

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

        # Kroot Farstalkers' Bounty Hunters: "at the start of the battle,
        # select one unit from your opponent's army". Here rather than in the
        # pre-game sequence because this is the first moment BOTH armies are
        # fully on the table - the same reason the points lines are logged here.
        bounty_hunters_controller.select_at_start_of_battle(state.all_squads())

        # Mont'ka's Strategic Conqueror: "at the start of the first battle
        # round, before the first turn begins, select one objective marker" -
        # the same instant Bounty Hunters uses just above, and for the same
        # reason (the first moment both armies are fully on the table).
        enh_strategic_conqueror.offer(
            state.all_squads(), state.objectives, decision_manager=decision_manager,
            game_log=game_log, auto_players=ai_players)

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
        mission_controller.score_primary(state.objectives, turn_tracker.active_player,
                                         turn_tracker.battle_round)
        # Round 1's two Secondary Mission cards, for the same reason the three
        # lines above run here: advance_turn_phase() never runs for the battle's
        # very first Command phase, so the draw would otherwise be a round late.
        # Idempotent by battle round.
        secondary_mission_controller.sync_battle_round(turn_tracker.battle_round)
        secondary_mission_controller.draw_at_command_phase(
            turn_tracker.turn_owner, turn_tracker.battle_round)

    # The must-click-away modal notices, in the SAME priority order the event
    # chain below dispatches them in. One definition, read by both the chain's
    # own ordering (which it mirrors by hand, being an if/elif) and by the
    # renderer, which draws only the front-most - see the draw block near the
    # bottom of the frame. A new notice belongs in this tuple AND in the chain.
    def _front_notice():
        """The one notice that currently owns the screen, or None."""
        # fight_warning_overlay first: it is the direct answer to a click the
        # human just made, and the only one of these raised BY the "End Turn"
        # button rather than by something the game did on its own. In practice
        # the set is disjoint - every other notice here is produced by
        # advance_turn_phase() or by an AI action, and this warning exists
        # precisely to stop advance_turn_phase() from running while the AI is
        # gated on it - so the order decides nothing today; it is written this
        # way so that if that ever changes, an answer beats an announcement.
        # battle_end_overlay ahead of all of them: once the battle is over
        # nothing else is worth reading, and nothing behind it can be acted on.
        # ai_offline_overlay right behind battle_end: it does not announce
        # something that happened IN the battle, it announces that the AI has
        # stopped playing it - so every notice behind it is about a game whose
        # rules of engagement just changed, and reading them first would be
        # reading them under a false assumption.
        for overlay in (battle_end_overlay, ai_offline_overlay,
                        fight_warning_overlay, turn_start_overlay, turn_plan_overlay,
                        mission_draw_overlay, stratagem_notice_overlay, waaagh_notice_overlay):
            if overlay.is_pending:
                return overlay
        return None

    def _check_battle_end():
        """Rule 07.01: raise the result once the last round has been played.
        Idempotent - BattleEndOverlay.show() only ever fires once.

        HELD BACK WHILE A DECISION IS STILL OPEN, and that is not politeness.
        The battle ends at a TURN END, and a turn end is also when the Tactical
        Secondary deck offers its achieved cards - as a PROMPT, because nothing
        in that deck is credited automatically. Three of its cards
        (Defend Stronghold, Beacon, Burden of Trust) score at exactly one
        instant, "the end of your opponent's turn in the final battle round",
        which IS the last turn end whenever the card player takes the first
        turn of the round. Raising the result in the same advance_turn_phase()
        that opened the prompt cost that card twice over: show() FREEZES the
        score it displays, so the VP were missing from it; and _front_notice()
        puts this overlay ahead of the decision box, so the prompt behind it
        could never be answered either. Measured: the card complete for 5 VP,
        the prompt open, and a frozen final score of 0.

        So the result waits for the answer and is raised by the per-frame call
        near the bottom of the loop, the frame after the last question lands.
        decision_manager rather than the deck's own flag because it is one
        condition instead of two that could disagree - and anything else still
        open at that instant (Starflare's offer sits on the same seam) has the
        same claim to be answered before the battle is called."""
        if turn_tracker.battle_over and not decision_manager.is_pending:
            # The Primary's "FINAL SCORING" box (Unstoppable Force's central
            # objectives) pays here, BEFORE the overlay reads the ledger -
            # scoring after it would show a final score missing its last 5 VP.
            # Idempotent on its own, exactly like show() below, because this
            # runs on every frame once the battle is over.
            primary_mission_controller.score_end_of_battle()
            battle_end_overlay.show(mission_controller)

    def advance_turn_phase():
        # Rule 15.07 (Rapid Ingress): any pending offer from a PREVIOUS
        # Movement-phase-end has now had its one phase's window to be
        # dragged onto the board - forfeit it before possibly opening a
        # new one below.
        rapid_ingress_controller.expire_if_unused()
        # The "you can still fight" warning is once per PHASE, and this is the
        # one place a phase ever changes (ai_advance_phase() routes through
        # here too), so this is its point of re-offer. Without it the warning
        # would fire once per battle: after the first time it was dismissed
        # every later Fight phase would end silently again, which is exactly
        # the bug it was built to fix.
        fight_warning_overlay.reset()
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
        # Aspect Host's Path of the Warrior lasts "until the end of the phase",
        # and its ledger keys on (unit, phase) - so it is cleared on every
        # phase change, unconditionally, like stratagem_controller above.
        path_of_the_warrior_controller.reset_phase()
        # Orikan's The Stars Are Right lasts "until the end of the phase".
        # The ACTIVE mark is what clears here; the once-per-battle ledger
        # inside the controller deliberately does not - "once per battle" is
        # the one duration that outlives every boundary.
        the_stars_are_right_controller.reset_phase(
            {t.squad for t in state.tokens if t.squad is not None})
        # Soulsight lasts one activation, but its latch is cleared on the
        # phase boundary too - the activation ledger in
        # game/activation_reroll.py forgets per squad, and this makes sure
        # a unit that never finished an activation does not carry it.
        _detachment_squads_now = {t.squad for t in state.tokens if t.squad is not None}
        armoured_soulsight.reset_phase(_detachment_squads_now)
        # Guardian Battlehost's three phase-long grants. Time to Strike's
        # SECOND half is turn-long and is cleared by game/move_exceptions.py's
        # own sweep instead - two clocks, two sweeps.
        guardian_warding_salvoes.reset_phase(_detachment_squads_now)
        guardian_blades_of_asuryan.reset_phase(_detachment_squads_now)
        guardian_time_to_strike.reset_phase(_detachment_squads_now)
        shield_nodes_controller.reset_phase(_detachment_squads_now)
        # Windrider Host's three phase-long grants plus the two per-phase
        # ledgers. Wind of Blades is turn-long and is cleared with the other
        # move exemptions at end of turn instead - two clocks, two sweeps.
        windrider_focused_firepower.reset_phase(_detachment_squads_now)
        windrider_death_from_on_high.reset_phase(_detachment_squads_now)
        windrider_daring_riders.reset_phase(_detachment_squads_now)
        spiralling_evasion_controller.reset_phase(_detachment_squads_now)
        overflight_controller.reset_phase()
        # Warhost's two phase-long grants. Feigned Retreat is turn-long and is
        # cleared with the other move exemptions at end of turn instead.
        warhost_blitzing_firepower.reset_phase(_detachment_squads_now)
        lightning_fast_reactions_controller.reset_phase(_detachment_squads_now)
        # Spirit Conclave's three phase-long grants. Soul Bridge is on the
        # Command-phase clock instead - "until the START of your next Command
        # phase" - and is cleared with Guide and Doom.
        conclave_seers_eye.reset_phase(_detachment_squads_now)
        conclave_blades_from_beyond.reset_phase(_detachment_squads_now)
        wraithbone_armour_controller.reset_phase(_detachment_squads_now)
        # Aspect Host's three phase-long grants plus its fight-after-death
        # ledger.
        aspect_warrior_focus.reset_phase(_detachment_squads_now)
        aspect_doom_inescapable.reset_phase(_detachment_squads_now)
        aspect_preternatural_precision.reset_phase(_detachment_squads_now)
        to_their_final_breath_controller.reset_phase()
        # Seer Council: three "until the end of the phase" grants plus the two
        # reactive controllers' own once-per-pair memos. Reset unconditionally on
        # every phase change, like stratagem_controller itself.
        _seer_squads = {t.squad for t in state.tokens if t.squad is not None}
        forewarned_mod.reset_phase(_seer_squads)
        psychic_shield_mod.reset_phase(_seer_squads)
        fate_inescapable_mod.reset_phase(_seer_squads)
        # Also the squads that are OFF the board right now: a unit that used
        # Unshrouded Truth and has not arrived yet is in reserves, so it is not
        # in _seer_squads at all, and its grant has to expire too.
        unshrouded_truth_mod.reset_phase(list(_seer_squads) + list(state.reserves))
        # Fuegan's Unquenchable Resolve: "at the end of the phase, roll one
        # D6". Resolved before the expiries below rather than after, so that a
        # returning model is on the battlefield for anything that reads the
        # board at this boundary.
        unquenchable_resolve_controller.resolve_end_of_phase()
        phoenix_gem_controller.resolve_end_of_phase()
        # Shroud Runners' Target Acquisition: "until the end of the phase".
        target_acquisition_controller.reset_phase()
        # War Walkers' Crystalline Targeting: its AP effect is "until the end
        # of the phase" as well. Its "once per turn" selection limit is a
        # SEPARATE, longer lifetime and is cleared at the end of the turn -
        # the two are deliberately not the same clock.
        crystalline_targeting_controller.reset_phase()
        # Sonic Destruction counts platforms that fired "this phase", so its
        # ledger clears on the same seam - not on the turn, which would let a
        # second phase inherit the first one's stacking.
        sonic_destruction_controller.reset_shooting_phase()
        # Hallucinogen Grenades grant Stealth "until the end of the phase".
        hallucinogen_grenades_controller.reset_phase()
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
        # The T'au detachment Stratagem grants that last "this phase". Alien
        # Expertise is NOT here: the ban it lifts (09.06) lasts the whole turn,
        # so it expires with the turn instead - see below.
        _detachment_squads = {t.squad for t in state.tokens if t.squad is not None}
        for _ctrl in experimental_ammunition_controllers:
            _ctrl.reset_phase(_detachment_squads)
        experimental_modifications_controller.reset_phase(_detachment_squads)
        guided_fire_controller.reset_phase(_detachment_squads)
        point_blank_ambush_controller.reset_phase(_detachment_squads)
        coordinate_to_engage_controller.reset_phase(_detachment_squads)
        # A Tempting Trap's GRANT is phase-scoped; its Trap objective is
        # chosen once and lasts the battle, so it is not touched here.
        tempting_trap_controller.reset_phase(_detachment_squads)
        photon_grenades_controller.reset_phase(_detachment_squads)
        # The end-of-phase reaction windows (see game/phase_window.py).
        # Cleared HERE, which runs before this boundary's own offers further
        # down, so the previous window is gone before a new one is armed.
        wall_of_mirrors_controller.reset_phase()
        cost_of_victory_controller.reset_phase()
        webway_tunnel_controller.reset_phase()
        marker_beacon_controller.reset_phase()
        # Both printings of Skyborne Sanctuary. They used to read the live
        # clock instead, which at this seam has already rolled past Fight all
        # the way to Command - so neither was ever offered.
        for _skyborne in skyborne_sanctuary_controllers:
            _skyborne.reset_phase()
        # An unattributed death does not outlive the phase it happened in.
        pinpoint_controller.reset_phase()
        # Mont'ka's Killing Blow is not a Stratagem and expires nothing - this
        # RE-DERIVES Squad.montka_killing_blow, which is how the detachment
        # rule reaches game/coldstar.py's weapon_has_assault() (rule 10.05)
        # without threading a turn_tracker through _attack_groups()'s eleven
        # call sites on the hottest shooting path.
        #
        # HERE rather than per-frame because nothing it reads is geometric,
        # which is the whole reason game/nurgles_gift.py sweeps every frame:
        # the detachment setting is written once by detachments.apply_to_config()
        # before the battle, the faction keyword is a datasheet reference, and
        # the only input that moves at all is turn_tracker.battle_round - which
        # moves inside the advance_phase() call at the top of this function.
        # Every phase change rather than only a round change, for the reason
        # battle_focus_pool.sync_battle_round() gives below: an idempotent
        # refresh must not depend on catching one exact moment.
        #
        # On-board units only, like every reset around it. That cannot go
        # stale: the flag is read from available_shooting_types() during a
        # Shooting phase, and a unit arriving from Reserves cannot move again
        # that phase, so rule 10.05 never asks about one that missed a stamp.
        montka.refresh_killing_blow(_detachment_squads, turn_tracker)
        aggressive_mobility_controller.reset_phase(_detachment_squads)
        combat_debarkation_controller.reset_phase(_detachment_squads)
        focused_fire_controller.reset_phase(_detachment_squads)
        counterfire_defence_controller.reset_phase(_detachment_squads)
        microdrone_support_controller.reset_phase(_detachment_squads)
        autoreactive_camouflage_controller.reset_phase(_detachment_squads)
        # Pulse Onslaught's `shaken` runs to the end of the victim's NEXT
        # turn, so it is not cleared on a boundary - expire() compares each
        # mark against its own deadline instead.
        pulse_onslaught_controller.expire(_detachment_squads)
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
        # The Secondary Mission deck's 15 VP-per-battle-round ledger, reset on
        # the same idempotent every-phase-change schedule and for the same
        # reason: the reset must not depend on catching one exact moment.
        secondary_mission_controller.sync_battle_round(turn_tracker.battle_round)
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
        # Skorpekh Destroyers' Plasmacyte: "until the end of the phase". Its
        # once-per-battle-per-Plasmacyte spend count deliberately survives.
        plasmacyte.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        # Awakened Dynasty's three phase-scoped protocols. Sudden Storm's
        # reset_phase() clears only its ADVANCE re-roll half - its [ASSAULT]
        # grant lasts until the end of the TURN and expires further down.
        hungry_void_controller.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        conquering_tyrant_controller.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        sudden_storm_controller.reset_phase({t.squad for t in state.tokens if t.squad is not None})
        vengeful_stars_controller.reset_phase()
        # Nurgle's Gift has TWO clocks and only one of them is a phase. The
        # Contagion Range bonuses (Blooming Pestilence, "until the end of the
        # phase") clear here; the sticky Afflicted marks do NOT - they run to
        # the start of a turn and are cleared in begin_battle_round_turn()
        # below. Named after their lifetimes and cleared in two places, the
        # same care game/protocol_sudden_storm.py takes with its own pair.
        nurgles_gift_controller.expire_phase()
        # The Defiler's Barrage of Filth is "until the end of the phase"; the
        # Chaos Spawn's Lethal Ichor tally and the Poxwalkers' unspent kill
        # credit are per Fight phase. All three clear on the same boundary.
        barrage_of_filth_controller.reset_phase()
        lethal_ichor_controller.reset_phase()
        curse_of_the_walking_pox_controller.reset_phase()
        # The Death Lord's Chosen grants are all "until the end of the phase".
        # Blooming Pestilence's RANGE bonus is cleared by
        # nurgles_gift_controller.expire_phase() above, which owns the table;
        # its own reset_phase() only forgets that the unit was granted one.
        _phase_squads = {t.squad for t in state.tokens if t.squad is not None}
        blooming_pestilence_controller.reset_phase(_phase_squads)
        grim_reapers_controller.reset_phase(_phase_squads)
        mortarions_teachings_controller.reset_phase(_phase_squads)
        # Undying Spite's reset also REMOVES anything still owed an activation,
        # so no model survives on a Stratagem that has expired.
        undying_spite_controller.reset_phase()
        malevolent_souls_controller.reset_phase()
        systematic_vigour_controller.reset_phase()
        # "At the end of the phase, set up the destroyed model" - ANY phase,
        # so this is resolved at every boundary, exactly like Fuegan's.
        eternal_revenant_controller.resolve_end_of_phase()
        # Illuminor Szeras's Atomic Energy Manipulator is credited per PHASE,
        # so the credit clears even when nothing grew - the growth itself is
        # resolved at the end of the Fight phase below and is permanent.
        # The Overlord's Resurrection Orb is "at the end of ANY phase", which
        # is why it is offered here rather than in one phase's own branch.
        if mover_before is not None:
            resurrection_orb_controller.offer_at_end_of_phase({t.squad for t in state.tokens if t.squad is not None}, mover_before)
        # Overflight: "End of your Shooting phase or the end of the Fight
        # phase". One offer covering both, and the controller now owns which
        # side of the table each half belongs to - so it is handed the two
        # facts it cannot read here any more: `phase_before` and
        # `mover_before`, both captured BEFORE advance_phase(). It used to
        # read turn_tracker.phase and turn_tracker.turn_owner itself, and by
        # this point both have already moved on, so it was never offered.
        overflight_controller.offer_at_end_of_phase(
            {t.squad for t in state.tokens if t.squad is not None},
            phase_before, mover_before)
        if phase_before == PHASE_FIGHT:
            atomic_energy_controller.resolve_end_of_fight_phase({t.squad for t in state.tokens if t.squad is not None})
            # EVERY end-of-Fight-phase offer below takes `mover_before`, NOT
            # turn_tracker.turn_owner. Fight is the last phase, so
            # advance_phase() up at the top of this function has ALREADY
            # flipped turn_owner to the next player - reading it here named
            # exactly the wrong side for all four of these. Reported for Wall
            # of Mirrors: "Frage kam am Anfang der Gegner Runde". mover_before
            # is the player whose Fight phase actually just ended, and it is
            # what the Resurrection Orb offer above already uses.
            #
            # Kauyon's Wall of Mirrors: "End of your opponent's Fight phase",
            # so the offer goes to whoever is NOT the player whose phase just
            # ended. A phase boundary, not a turn one - it fires even when the
            # turn continues.
            wall_of_mirrors_controller.offer_at_end_of_fight_phase(mover_before)
            # Cost of Victory: "end of your OPPONENT'S Fight phase", so the
            # same side as Wall of Mirrors above - whoever is NOT the player
            # whose phase just ended.
            cost_of_victory_controller.offer_at_end_of_fight_phase(
                {t.squad for t in state.tokens if t.squad is not None},
                mover_before)
            # Webway Tunnel: the same "end of your OPPONENT'S Fight phase" as
            # Cost of Victory above, and the same withdrawal minus the dead
            # models that one brings back.
            webway_tunnel_controller.offer_at_end_of_fight_phase(
                {t.squad for t in state.tokens if t.squad is not None},
                mover_before)
            # Skyborne Sanctuary says "End of THE Fight phase" - it belongs to
            # nobody, so both players are offered it and no owner is passed.
            for _skyborne in skyborne_sanctuary_controllers:
                _skyborne.offer_at_end_of_fight_phase(
                    {t.squad for t in state.tokens if t.squad is not None})
            # The Stonesinger's Elemental Ensnarement: "at the end of YOUR Fight
            # phase", so it is offered to the player whose phase just ended -
            # the opposite side from Wall of Mirrors directly above it. Its
            # first argument is the RECIPIENT, not an `ending_player`, and the
            # two happen to be the same value here for exactly that reason.
            # Raid and Run's own end-of-Fight-phase window, before the
            # ensnarement offer so the two prompts cannot collide.
            raid_and_run_controller.reset_phase()
            elemental_ensnarement_controller.offer_at_end_of_fight(
                mover_before,
                {t.squad for t in state.tokens if t.squad is not None})
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
            # Vespid Stingwings' Airborne Agility: "at the end of YOUR
            # OPPONENT'S turn" - so it is offered to whoever's turn just
            # ENDED is not, which is what the controller's own argument
            # name says. The one ability in this batch whose timing is
            # easiest to get backwards.
            airborne_agility_controller.offer_at_end_of_turn(
                {t.squad for t in state.tokens if t.squad is not None}, ending_player)
            # Windrider Host's Ride the Wind, second clause - the same instant
            # and the same trap: "at the end of your OPPONENT'S turn", so the
            # offer goes to whoever is NOT ending_player. Capped by battle size,
            # unlike Airborne Agility, which is per unit.
            ride_the_wind_controller.offer_at_end_of_turn(
                {t.squad for t in state.tokens if t.squad is not None}, ending_player)
            # Doomsday Ark's Overwhelming Obliteration: "until the end of the
            # turn", so it expires with the other one-turn grants rather than
            # at the phase boundary above.
            overwhelming_obliteration.expire_for_turn(ending_squads)
            # Sudden Storm's [ASSAULT] grant - "until the end of the turn".
            sudden_storm_controller.expire_for_turn(ending_squads)
            # Alien Expertise lifts rule 09.06's "Advanced, so no charge" for
            # the whole TURN - the Charge phase is where it is read, so a
            # phase-scoped reset would buy nothing at all.
            alien_expertise_controller.expire_for_turn(ending_squads)
            # The Malignant Plaguecaster's Pestilent Fallout runs "until the
            # end of your opponent's next turn" - nearly two full turns, the
            # longest lifetime in this faction - so it expires on the VICTIM's
            # turn ending, not the caster's.
            pestilent_fallout_controller.expire_for_turn(ending_player)
            # Signal Pox's objective is chosen "until the start of your next
            # turn" - the sticky Afflicted marks themselves are dropped by
            # nurgles_gift_controller.expire_marks_for(), which owns them.
            signal_pox_controller.expire_for_turn(ending_player)
            # "Each model can only be selected for this ability once per turn"
            # (Technomancer) and "you cannot resurrect more than one unit per
            # turn" (Resurrection Orb) - both per-TURN ledgers, cleared here.
            technomancer_controller.reset_turn()
            resurrection_orb_controller.reset_turn()
            # The Psychomancer's Harbinger of Despair is "once per TURN",
            # per bearer unit - the same shape as the two above it.
            harbinger_of_despair_controller.reset_turn()
            # Hyperspace Hunters is "once per turn" per hunting unit.
            hyperspace_hunters_controller.reset_turn()
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
            # Harnessed Alien Instincts' prey mark is "until the end of the
            # turn" too - a decision, since the printed text gives no duration;
            # matching the four marks around it. reset_turn() also clears the
            # once-per-phase offer memo, which reset_phase() clears on its own
            # at every phase boundary - two lifetimes, cleared separately so
            # the mark cannot be quietly shortened to a phase.
            auxiliary_cadre_controller.reset_turn()
            # Crystalline Targeting's "each unit can only be selected for this
            # ability once per turn" - a limit on the TARGET, so likewise not
            # per-squad and not tied to ending_squads. Its AP effect expired a
            # phase boundary ago; only the selection ledger lives this long.
            crystalline_targeting_controller.reset_turn()
            # The Kroot Lone-Spear's Advanced Scouting mark: "until the end
            # of the turn" - a turn, not a phase and not a battle round, so
            # it clears on the same seam as every other end-of-turn state.
            advanced_scouting_controller.reset_turn()
            # Loping Pounce is "until the end of the turn", and an owed Kroot
            # Packmates reaction must not survive into the next one either.
            loping_pounce.reset_turn(
                {t.squad for t in state.tokens if t.squad is not None})
            kroot_packmates_controller.reset_turn()
            # The Twin Lance's Neocapacitor Shields: likewise "until the end
            # of the turn", and on the turn-taker's own units (the ones that
            # would have been charging), so ending_squads is exactly right.
            neocapacitor_shields.expire_for_turn(ending_squads)
            # Aeldari Battle Focus: Star Engines and Flitting Shadows are both
            # "until the end of the turn". ending_squads is right for the same
            # reason - only the turn-taker can trigger either of them, both
            # being their own Movement phase manoeuvres.
            battle_focus_pool.expire_for_turn(ending_squads)
            # Rangers' Path of the Outcast is "once per turn" (user-supplied
            # wording). Cleared wholesale rather than per ending_squad: the
            # ability fires in the OPPONENT's Movement phase, so the unit that
            # used it is never the one whose turn is ending.
            path_of_the_outcast_controller.reset_for_new_turn()
            # Rule 09.06/09.07's Stratagem exemptions - Vectored Engines,
            # Time to Strike, Feigned Retreat, Wind of Blades. Every latch in
            # game/move_exceptions.py is "until the end of the turn", so they
            # end together, here, at the one place a turn ends.
            #
            # Swept over EVERY squad on the board rather than over
            # ending_squads: a turn is one player's turn, so the end of any
            # turn ends an "until the end of the turn" grant, whichever turn
            # it was bought in. ending_squads would have left a latch bought
            # in the opponent's turn running for the rest of the battle.
            move_exceptions.clear_turn_flags(
                {t.squad for t in state.tokens if t.squad is not None})
            # Rule 20.04 arrivals, read by Death from on High's "set upon the
            # battlefield from Reserves THIS TURN". Kept apart from
            # SetupController's own Squad.set_up_this_turn, which every
            # placement sets - deployment included - and so cannot answer a
            # question about Reserves.
            ingress_controller.reset_turn()
            for squad in ending_squads:
                squad.fights_first = False
                squad.charged_this_turn = False  # rule 11.04's own marker, see Squad.charged_this_turn
                squad.set_up_this_turn = False
                squad.charge_locked_until_end_of_turn = False
                # Swooping Hawks' Grenade Pack Flyover locks the unit out of
                # the Explosives Stratagem "until the end of the turn".
                squad.explosives_locked_until_end_of_turn = False
                # Baharroth's Cry of the Wind: "until the end of the turn".
                for _m in squad.models:
                    _m.cry_of_the_wind_active = False
                squad.fell_back_this_turn = False  # rule 09.07: "until the end of the turn"
            # Secondary mission ("No Mercy", user-supplied): 1 point per
            # enemy unit destroyed, scored at the end of the destroying
            # player's own turn - see MissionController.record_destroyed_squad()
            # for when a kill actually gets queued (the dead-model-removal
            # loop below).
            mission_controller.score_secondary_end_of_turn(ending_player)
            # The human's Tactical Secondary cards. Their scoring instants are
            # "end of your turn" (Centre Ground) and "end of A turn" (Bring It
            # Down), so this runs for BOTH players' turn ends and the cards
            # themselves decide which of them applies. Nothing is scored
            # automatically - each achieved card opens a prompt asking whether to
            # cash it in now or keep it, and the discard-for-CP offer follows once
            # those are answered. Resolves asynchronously, exactly like
            # starflare_controller.offer() a few lines down.
            # battle_round_before, NOT turn_tracker.battle_round: advance_phase()
            # has already run, and when the SECOND player's turn ends it has
            # incremented the counter. A card asking "is this round 5" (Beacon)
            # would otherwise see 6 at exactly the instant it should fire.
            secondary_mission_controller.begin_end_of_turn(
                ending_player, battle_round=battle_round_before)
            # The human's Force Disposition Primary. Its "END OF YOUR TURN"
            # boxes score here, automatically - a Primary offers no "cash in or
            # keep" choice, so unlike the deck above nothing is asked.
            #
            # Called for BOTH players' turn ends, like the deck: the boxes
            # themselves decide which applies, and this is also where the
            # per-turn bookkeeping resets. battle_round_before for the same
            # reason it is used above - advance_phase() has already run.
            #
            # BEFORE action_controller.reset_for_turn() below, because this is
            # what completes and reads this turn's Secure Asset action.
            primary_mission_controller.begin_end_of_turn(
                ending_player, battle_round=battle_round_before)
            # Rule 16.01's bookkeeping is per TURN ("it started another action
            # this turn", and both locks last "until the end of the turn").
            # AFTER begin_end_of_turn(), which is what completes this turn's
            # actions and reads the result - clearing first would throw them
            # away unresolved.
            action_controller.reset_for_turn()
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
            # The Psychomancer's Nightmare Shroud: "in the Battle-Shock step
            # of your OPPONENT'S Command phase". The owner test lives in the
            # controller, so this passes whose phase it is rather than
            # deciding here who the Necrons are.
            nightmare_shroud_controller.begin_battle_shock_step(
                {t.squad for t in state.tokens if t.squad is not None},
                turn_tracker.turn_owner)
            # Primary mission ("Hold the Line", user-supplied):
            # PRIMARY_POINTS_PER_OBJECTIVE per objective controlled at the
            # start of your own Command phase, from battle round
            # PRIMARY_FIRST_SCORING_ROUND onward - objective.controlled_by was
            # already recomputed for this exact boundary a few lines up. Both
            # the rate and the round band live in game/missions.py; this is the
            # hook, not the rule.
            mission_controller.score_primary(state.objectives, turn_tracker.active_player,
                                             turn_tracker.battle_round)
            # "Am Anfang jeder Runde zieht man zwei neue Missionen" - resolved as
            # the start of the card player's OWN Command phase, which happens
            # exactly once per battle round. turn_owner, not active_player: this
            # is about whose turn it is, not whose decision is open right now.
            # Idempotent by battle round, so the battle-start paths that already
            # drew round 1's pair cannot be doubled up here.
            # Overwhelming Force asks about enemy units that "started the turn"
            # within range of an objective - a fact that cannot be recovered
            # once they are dead. Snapshotted at the top of EVERY turn, either
            # player's, because that card scores at the end of a turn.
            secondary_mission_controller.snapshot_turn_start()
            # The Primary's own three turn-start snapshots (which enemies stood
            # in which terrain area, which stood on a central objective, which
            # objectives I held). Same instant, same reason as the line above:
            # all three are facts that are gone by the time a box asks.
            primary_mission_controller.snapshot_turn_start()
            # "Burden of Trust" offers its guards both WHEN DRAWN and at the
            # start of each of your turns. Run BEFORE the draw deliberately: on
            # the turn the card is drawn this finds it not yet in hand and does
            # nothing, so only the draw window fires instead of both.
            secondary_mission_controller.start_of_turn(turn_tracker.turn_owner)
            # Monofilament Snare is "until the start of YOUR next turn", so a
            # mark expires as the player who placed it begins a turn - one
            # boundary further out than a Guide/Doom mark, which is why it is
            # keyed on the owner instead of being flat-reset with the phase.
            monofilament_snare_controller.clear_for_turn_of(turn_tracker.turn_owner)
            # Monofilament Web is "until the start of YOUR next turn" too, and
            # the pin lives on the squad (like `shaken`), so expiry walks the
            # board rather than a registry.
            monofilament_web_controller.clear_for_turn_of(turn_tracker.turn_owner)
            # Fury of the Void is "until the end of the TURN" - one boundary
            # shorter than Guide and Doom, so it clears here rather than at a
            # Command phase.
            fury_of_the_void_controller.reset_turn()
            # Channeller Stones is a per-TURN resource on the squad.
            corsair_abilities.reset_channeller_stones(
                {t.squad for t in state.tokens if t.squad is not None})
            # ENSNARED is "until the start of YOUR next turn" as well, and lives
            # on the squad like `pinned`, so it expires on the same seam.
            elemental_ensnarement_controller.clear_for_turn_of(
                turn_tracker.turn_owner,
                {t.squad for t in state.tokens if t.squad is not None})
            secondary_mission_controller.draw_at_command_phase(
                turn_tracker.turn_owner, turn_tracker.battle_round)
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
            # Misfortune shares Guide's "until the start of your next Command
            # phase" lifetime, so it clears on the same seam.
            misfortune_controller.start_of_command_phase(turn_tracker.turn_owner)
            # Tears of Isha is once per unit per TURN, so its ledger clears here.
            tears_of_isha_controller.reset_turn()
            # Belt and braces: the per-MOVE ledger is already cleared by
            # on_move_started, so this only matters if a move was abandoned
            # without ever starting another.
            spirit_stone_controller.reset_turn()
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
            # The NECRONS army rule. At the END of the Command phase, so it is
            # driven from the phase_before branch further down - this comment
            # sits here only because it is the sibling of the offer below.
            grot_orderly_controller.offer_at_command_phase(
                [
                    sq for sq in {t.squad for t in state.tokens if t.squad is not None}
                    if sq.owner == turn_tracker.turn_owner and unit_has_grot_orderly(sq)
                ],
                turn_tracker,
            )
        if turn_tracker.phase == PHASE_MOVEMENT:
            # "Until the start of your next Movement phase" - Spirit Mark's own
            # reset, one phase later than a Guide/Doom mark.
            spirit_mark_controller.start_of_movement_phase(turn_tracker.turn_owner)
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
            # Orikan The Diviner's The Stars Are Right: "at the start of THE
            # Fight phase" - bare, not "your", and the Fight phase is shared
            # (12.04), so it is offered to whoever owns a bearer rather than
            # to the turn owner. Its own once-per-battle ledger keeps it
            # silent after the first use.
            the_stars_are_right_controller.offer_at_start_of_fight_phase(
                {t.squad for t in state.tokens if t.squad is not None})
            # Kill Rig's Spirit of Gork: "at the start of the Fight phase".
            # Offered for the phase's own turn owner only - the ability
            # belongs to its controller's turn, like every other
            # start-of-phase effect here.
            spirit_of_gork_controller.start_of_fight_phase([
                sq for sq in {t.squad for t in state.tokens if t.squad is not None}
                if sq.owner == turn_tracker.turn_owner and unit_has_spirit_of_gork(sq)
            ])
            # Yvraine's Herald of Ynnead: "at the START of the Fight phase".
            # Cleared FIRST and offered second - the mark lasts only until the
            # end of the phase it was set in, so a stale one from last turn
            # must not survive into this offer.
            herald_of_ynnead_controller.reset_phase()
            for _sq in sorted({t.squad for t in state.tokens if t.squad is not None},
                              key=lambda q: q.name):
                if _sq.owner == turn_tracker.turn_owner:
                    herald_of_ynnead_controller.offer_at_fight_phase(_sq)
            pile_in_controller.reset_fight_phase()
            fight_controller.reset_fight_phase()
            consolidate_controller.reset_fight_phase()
            epic_challenge_controller.reset_fight_phase()
        # Rule 20.03: "At the end of the third battle round... all
        # strategic reserves units that have not made one or more ingress
        # moves are destroyed."
        # Rule 07.01: did that turn end the battle?
        _check_battle_end()
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
        # Nurgle's Gift's sticky half: "until the START of your next turn,
        # that enemy unit is Afflicted". A turn has just started for whoever
        # turn_owner now is, whenever that differs from who owned the phase
        # that just ended - which is exactly the mirror of `ending_player`
        # computed above. Everything THAT player marked stops being marked.
        if mover_before is not None and turn_tracker.turn_owner != mover_before:
            nurgles_gift_controller.expire_marks_for(turn_tracker.turn_owner)
        # The Kroot War Shaper's Root of Honour: "once per battle, AT THE START
        # OF ANY PHASE". Any phase means any - including the opponent's - so
        # this sits above every phase-specific block below and is offered to
        # BOTH players rather than to turn_owner. Its own predicate keeps it
        # silent unless a War Shaper is on the table with a Battle-shocked
        # KROOT unit in range, so the unconditional call costs nothing.
        root_of_honour_controller.offer_at_start_of_phase(
            {t.squad for t in state.tokens if t.squad is not None})
        # The Psychomancer's Harbinger of Despair: "once per turn, at the
        # start of your Command, Movement, Shooting, Charge or Fight phase".
        # All five of the bearer's own phases, so it sits beside Root of
        # Honour above rather than in any one phase block - but unlike that
        # one it is "YOUR" phase, so it is offered to the turn owner only.
        harbinger_of_despair_controller.offer_at_start_of_phase(
            {t.squad for t in state.tokens if t.squad is not None},
            turn_tracker.turn_owner)
        if turn_tracker.phase == PHASE_COMMAND:
            # Kroot Hounds' Loping Pounce: "AT THE START of your Command
            # phase" - checked once and latched for the turn, which is what
            # separates it from the two live advance-then-charge sources it
            # joins in game/charge.py.
            loping_pounce.begin_command_phase(
                {t.squad for t in state.tokens if t.squad is not None},
                turn_tracker.turn_owner, game_log=game_log)
            # Deadly Vectors: "IN YOUR OPPONENT'S Command phase". Fired at the
            # START of a Command phase and handed the player whose phase it is
            # - the controller then rolls for every OTHER player holding the
            # detachment, which is what makes "your opponent's" mean what it
            # says without this line having to know who the Death Guard is.
            #
            # The START rather than the end, and that is not cosmetic: rule
            # 02.02.04's Reanimation Protocols fires at the END of the same
            # phase and drains its own dice queue there. Two queues starting on
            # the same seam would fight over DiceManager.pending_values, and a
            # Necrons-versus-Death-Guard game is a perfectly ordinary pairing.
            # The printed text says only "in", so the start satisfies it and
            # costs nothing.
            deadly_vectors_controller.begin_opponent_command_phase(
                {t.squad for t in state.tokens if t.squad is not None},
                turn_tracker.turn_owner,
            )
            # Auxiliary Cadre's Admired Leader: "IN your Command phase, you can
            # select one KROOT/VESPID STINGWINGS unit within 12"", lasting
            # "until the start of your next Command phase". Those are the same
            # instant a round apart, so this one call clears last round's mark
            # and then offers this round's - in that order, which is its own
            # test line because the two lines look independent.
            admired_leader_controller.begin_command_phase(turn_tracker.turn_owner)
            # ...and Light of Clarity, on the same clock and through the same
            # shared machine.
            light_of_clarity_controller.begin_command_phase(turn_tracker.turn_owner)
            echoes_of_ulthanesh_controller.begin_command_phase(turn_tracker.turn_owner)
            lucid_eye_controller.begin_command_phase(turn_tracker.turn_owner)
            stave_of_kurnous_controller.begin_command_phase(turn_tracker.turn_owner)
            rune_of_mists_controller.begin_command_phase(turn_tracker.turn_owner)
        if phase_before == PHASE_COMMAND:
            # The Force Disposition Primary's "END OF CMD PHASE" boxes, for the
            # player whose Command phase just ended (mover_before).
            #
            # THE END, not the start, and that is not the same instant "Hold the
            # Line" scores at a few hundred lines up: Battle Shock is resolved
            # in this phase, a battle-shocked unit's OC becomes a dash
            # (01.07/02.02), and objective control is recomputed on the way out
            # - so who controls what can genuinely differ between the two.
            # battle_round_before, because advance_phase() has already run.
            primary_mission_controller.end_of_command_phase(
                mover_before, battle_round=battle_round_before)
            # Reanimation Protocols: "at the end of your Command phase, each
            # friendly unit with this ability that is on the battlefield
            # activates". A QUEUE - every eligible unit gets its own labelled
            # roll, one at a time; see game/reanimation_protocols.py.
            reanimation_controller.begin_command_phase({t.squad for t in state.tokens if t.squad is not None}, mover_before)
            # The Ethereal's Coordinated Leadership: "at the end of your
            # Command phase, roll one D6". Same seam, and after Reanimation
            # Protocols on purpose - both drain a dice queue, and a queue
            # already started owes its dice first.
            coordinated_leadership_controller.begin_command_phase(
                {t.squad for t in state.tokens if t.squad is not None}, mover_before)
            # Yvraine's Word of the Phoenix: "in your Command phase, you can
            # roll one D6". LAST of the three for the same reason the second
            # is after the first - each one holds the dice window until it is
            # answered, and this one needs TWO of them.
            for _sq in sorted({t.squad for t in state.tokens if t.squad is not None},
                              key=lambda q: q.name):
                if _sq.owner == mover_before and word_of_the_phoenix_controller.can_use(_sq):
                    if word_of_the_phoenix_controller.start(_sq):
                        break
        if turn_tracker.phase == PHASE_SHOOTING:
            # The Void Dragon's Matter Absorption is "at the START of your
            # Shooting phase"; the Plasmancer's Living Lightning is "in your
            # Shooting phase", which this instant also satisfies. Both reset
            # their once-per-phase ledgers first.
            living_lightning_controller.reset_phase()
            matter_absorption_controller.reset_phase()
            matter_absorption_controller.offer_at_shooting_phase(
                {t.squad for t in state.tokens if t.squad is not None}, turn_tracker.turn_owner)
            living_lightning_controller.offer_at_shooting_phase(
                {t.squad for t in state.tokens if t.squad is not None}, turn_tracker.turn_owner)
            # Typhus' Eater Plague is "in your Shooting phase" too, and shares
            # Living Lightning's 18"-and-visible targeting - so it is offered
            # at the same instant and resets the same way.
            eater_plague_controller.reset_phase()
            eater_plague_controller.offer_at_shooting_phase(
                {t.squad for t in state.tokens if t.squad is not None}, turn_tracker.turn_owner)
            # Auxiliary Cadre's Harnessed Alien Instincts is "IN your Shooting
            # phase" - not "after this unit has shot" - so it is offered at the
            # start, once per eligible KROOT/VESPID unit, the same instant the
            # For The Greater Good army rule picks its Observers. A unit that
            # never fires can still mark. reset_phase() clears only the
            # once-per-unit memo; the mark itself is turn-scoped.
            auxiliary_cadre_controller.reset_phase()
            auxiliary_cadre_controller.offer_at_start_of_shooting_phase(turn_tracker.turn_owner)
            # Guiding Presence is re-selected every Shooting phase, so the
            # previous mark is cleared and a new one offered in the same
            # breath - the same instant, and for the same printed reason, as
            # the two above.
            guiding_presence_controller.reset_phase()
            guiding_presence_controller.offer_at_start_of_shooting_phase(turn_tracker.turn_owner)
        if phase_before == PHASE_SHOOTING:
            greater_good_controller.reset_shooting_phase()
            # The Vespid Oversight Drone's grant is "until the end of the
            # phase" - the GRANT only; its once-per-battle ledger is never
            # cleared.
            oversight_drone_controller.reset_phase(
                {t.squad for t in state.tokens if t.squad is not None})
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
            # Marker Beacon: "End of your Movement phase". This block runs
            # AFTER update_control() at the top of advance_turn_phase(), which
            # is exactly what it needs - an objective taken by the move that
            # just happened is controlled_by this player only from that
            # recompute onwards.
            marker_beacon_controller.offer_at_end_of_movement_phase(mover_before)
            # The Farseer's Guide: "at the end of your Movement phase, select
            # one enemy unit". Before the Flickerjump roll below for the same
            # reason that one goes before Rapid Ingress - a decision already
            # taken owes its dice first, and this is a new decision.
            guide_controller.offer_at_end_of_movement(
                mover_before, {t.squad for t in state.tokens if t.squad is not None},
            )
            # Misfortune fires at the same instant as Guide ("at the end of your
            # Movement phase") and is offered to the same player.
            misfortune_controller.offer_at_end_of_movement(
                mover_before, {t.squad for t in state.tokens if t.squad is not None},
            )
            # The Technomancer's own ability: "at the end of your Movement
            # phase". Same instant as Guide above, and likewise offered to the
            # player whose Movement phase just ended.
            technomancer_controller.offer_at_end_of_movement({t.squad for t in state.tokens if t.squad is not None}, mover_before)
            # The Piranhas' Drone Harassment Tactics: "at the end of your
            # Movement phase". Same instant as the two above, and offered to
            # the player whose Movement phase just ended.
            drone_harassment_controller.offer_at_end_of_movement(
                {t.squad for t in state.tokens if t.squad is not None}, mover_before)
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

    # Rule 03.02: the unit the player has PICKED out of the Reserves strip and
    # is now carrying to the board. Renamed from dragging_reserve_squad because
    # "being dragged" stopped being true: a plain click on a card now keeps the
    # unit carried (the ghost follows the cursor and the card leaves the strip,
    # so the state is impossible to miss), which is what lets the line-formation
    # right-drag place it in ONE gesture instead of two. The left button's own
    # press-drag-release still works exactly as it did.
    #
    # One flag deliberately, not "picked" plus "held": all three gestures that
    # can put the unit down go through _place_picked_unit(), so "where does the
    # carried unit go" has one answer rather than three.
    picked_reserve_squad = None

    def show_loading_overlay(message):
        """Full-window dim + centered message, for a synchronous ENGINE
        computation (line-of-sight/valid-target sweeps) rather than a Claude
        API call - flashed right before a cache miss is about to run one of
        those expensive sweeps (see get_shoot_targets()/
        get_greater_good_eligible_squads() above), so the window shows
        *something* instead of just sitting there for the fraction of a
        second to ~1s the sweep can take on a full board.

        This one KEEPS the full-window look that show_thinking_overlay()
        below has dropped, and the difference is the point: these sweeps are
        the direct answer to a click the human just made and last a moment,
        so there is nothing to watch and nothing to be locked out of. The
        AI's waits are the opposite - they are someone else's turn playing
        out on the board, which is exactly what you want to keep watching."""
        overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))
        text_surf = loading_font.render(message, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(window_width // 2, window_height // 2))
        screen.blit(text_surf, text_rect)
        pygame.display.flip()

    def show_thinking_overlay():
        """Flashed just before ai/agent_driver.py calls agent.decide() - a
        real Claude round-trip takes a couple of seconds, during which the
        whole loop is blocked (it's a synchronous network call), so without
        this the window would just look frozen.

        No full-window dim any more (User: "das nervt ein bisschen, weil man
        dann nicht so gut verfolgen kann, was grade passiert"). The board -
        the thing you actually want to watch while the AI acts - stays fully
        legible, and what gets covered instead is the two side panels, i.e.
        exactly the buttons you must not press during someone else's turn.
        The message carries the signal on its own from the corner, in the
        same badge the planning wait uses.

        That also folds in an older report that the dim used to fight with a
        VISIBLE dice roll: ai/agent_driver.py's _maybe_command_reroll()
        deliberately fires while a roll awaits acknowledgement (rule 15.02
        has to react before it is confirmed), and covering that roll read as
        two conflicting prompts at once. Only the wording still branches on
        it now - the roll stays untouched either way, so naming what is
        being decided is all that is left to do.

        A single flashed frame, so no pulse: the badge would freeze at
        whatever phase it happened to catch and sit there for the whole
        call.

        Skipped entirely while the planning badge is up: that one occupies
        this very corner and is already saying "the AI is busy", and this
        flash draws on top of a finished frame - a narrower badge over a wider
        one leaves the wider one's tail sticking out, which is the overlap the
        AUTO-PLAY dot below was reported for."""
        if ai_memory.is_planning:
            return
        ai_busy_badge.draw(
            screen,
            "Claude is considering a Command Re-roll..." if dice_manager.is_pending else "Claude is thinking...",
            board_rect_screen, dim_rects=ai_busy_dim_rects, pulse=False,
            avoid_rects=(dice_panel.last_backdrop_rect,),
        )
        pygame.display.flip()

    def _mission_slots():
        """Everything carrying mission state, by the name the snapshot files
        it under. ONE definition, read by the writer and by the --load path -
        a saver and a loader that disagreed about which slot is which would
        restore a Primary's latches into the Secondary's deck."""
        return {
            "ledger": mission_controller,
            "secondary": secondary_mission_controller,
            "primary": primary_mission_controller,
        }

    def _activation_slots():
        """Everything holding "this unit has already acted this turn", by the
        slot game/activation_state.py files it under. ONE definition, read by
        the writer and by the --load path, for exactly the reason
        _mission_slots() above is one: a saver and a loader that disagreed
        about which slot is which would restore the Charge ledger into the
        Shooting one."""
        return {
            "movement": movement_controller,
            "shooting": shooting_controller,
            "charge": charge_controller,
            "fight": fight_controller,
            "pile_in": pile_in_controller,
            "consolidate": consolidate_controller,
            "battle_shock": battle_shock_controller,
            "greater_good": greater_good_controller,
        }

    def _save_scene(reason, path=None, quiet=False):
        """Write the board position, and say where it went.

        ONE writer, because there are now three callers with three reasons -
        F9 (turn a reported failure into a fixture), the menu's Save Game
        entry, and the per-round autosave - and every one of them has to pass
        the same five things to capture(). Three copies of that argument list
        is three chances for one of them to quietly stop recording the armies,
        which is the line that makes a snapshot restorable at all.

        `path` names the file; the default is a timestamped one, so a manual
        save is never overwritten by the next autosave. `quiet` keeps the line
        out of the on-screen log - the autosave fires every battle round and
        would otherwise push five notices of its own past whatever the player
        was reading."""
        if path is None:
            path = os.path.join(scene_io.SCENES_DIR,
                                f"scene_{time.strftime('%Y%m%d_%H%M%S')}.json")
        written = scene_io.write(
            scene_io.capture(state, battle_map.key, turn_tracker, command_points,
                             armies=armies, missions=_mission_slots(),
                             activation=_activation_slots(), stats=battle_stats),
            path,
        )
        game_log.add(f"Board position {reason} to {written} "
                     f"(reload it with --load {written})", file_only=quiet)
        return written

    def _open_game_menu():
        """Raise the in-game menu. Two callers: ESC, and the MENU button.

        The line drag is ended first because it is POLLED outside the event
        loop (update_line_drag, below) and so is not covered by the menu's
        `continue` - a right button held down when the menu opened would keep
        dragging models around under the scrim, and its release would be
        swallowed. end_line_drag() is idempotent, so calling it when nothing is
        dragging costs nothing."""
        input_manager.end_line_drag()
        game_menu.show()

    # THE ONE LIST of controllers that can be waiting for a model click. It
    # used to live inside _any_pending_damage_choice() below, where only the AI
    # pause could see it - so the left panel kept its own answer for TWO of
    # these 27 and drew whatever branch matched next for the other 25 (reported
    # as the Fire Overwatch screen appearing over a mortal-wound allocation).
    # Lifted here, unchanged, so the panel, the board highlight, the AI pause
    # and the click branch all read one list. See game/damage_pick.py.
    damage_choice_controllers = (
        shooting_controller, fight_controller, explosives_controller,
        deadly_demise_controller, crushing_impact_controller,
        transport_controller, fall_back_controller,
        deadly_vectors_controller, lethal_ichor_controller,
        spore_laced_controller, sickening_impact_controller,
        internal_grenade_racks_controller,
        # Aspect Host's Khaine's Vengeance runs a Desperate Escape test on the
        # falling-back unit, which belongs to the TURN OWNER - so a human
        # victim's allocation is a genuine board click.
        khaines_vengeance_controller,
        # The six mortal-wound carriers: rule 06.02 hands the pick to the
        # TARGET's owner, so a human target is the same board click.
        living_lightning_controller, matter_absorption_controller,
        crimson_harvest_controller, eater_plague_controller,
        kroot_linebreakers_controller, crushing_strides_controller,
        # Isha's Fury, the Grenade Pack Flyover, the Grav-inhibitor Field and
        # Flickerjump - four more allocations belonging to the TARGET's owner.
        ishas_fury_controller, grenade_pack_controller,
        grav_inhibitor_controller, flickerjump_controller,
        # Four abilities that OPEN a rule 06.02 allocation and could not answer
        # it. See test_event_chain_wiring.py section 17.
        wraith_form_controller, drakolithe_controller,
        harvester_of_souls_controller, monofilament_snare_controller,
    )

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
        # Reads the ONE list above, through game/damage_pick.py - the same
        # question the panel, the board highlight and the click branch ask.
        #
        # human_players REPLACES a hardcoded `!= "Player 2"`, and that is a
        # BEHAVIOUR FIX rather than a refactor: with config.AI_PLAYERS set to
        # {"Player 1"} the old literal made this fire on the AI's OWN
        # allocations, which is precisely the starvation deadlock the
        # docstring above describes.
        return damage_pick.pending(damage_choice_controllers, human_players) is not None

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
            # Rule 07.01: the battle is over - nothing advances, for either side.
            turn_tracker.battle_over
            or pregame_controller.is_active  # rule 03.01: the battle hasn't started yet
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
            or grenade_pack_controller.is_busy
            # Rangers' Path of the Outcast: its D6 or its open reactive move
            # belongs to the OTHER player, mid-phase - advancing the phase out
            # from under it would strand turn_tracker.active_player on the
            # reacting player (only _finish() hands it back).
            or path_of_the_outcast_controller.is_busy
            # Spirit Conclave's Higher Duty holds active_player exactly the
            # same way while its reactive move is open, so it needs the same
            # guard - the third report of this class was a move the phase
            # change walked straight over.
            or higher_duty_controller.is_busy
            # An out-of-phase move that is still OPEN. ONE term for all twelve
            # modes rather than one per owning controller: this gate had no
            # movement_controller term at all, and the eleven abilities that
            # grant such a move would otherwise each have to remember to add
            # themselves here - the hand-maintained list game/ui/action_panel.py
            # already records growing wrong once ("scout" was missing from it).
            # The two above are in this gate for an unrelated reason (they hold
            # active_player); the other ten had nothing waiting on them, so a
            # "Next Phase" click orphaned a paid-for move - select(None) clears
            # the state but neither move_mode nor the model positions.
            #
            # AND state == MOVING, and that half is load-bearing rather than
            # defensive: select(None) leaves move_mode set while clearing the
            # state, so without it a finished move would block the phase for
            # ever with nothing on screen to clear it - the deadlock section 10
            # of test_event_chain_wiring.py exists to prevent. Nothing here can
            # deadlock the other way either: action_panel.py's
            # `if movement_controller.state == movement.MOVING:` appends a
            # Confirm and a Cancel unconditionally, so every mode this term can
            # see has a resolution routed from the panel.
            or (movement_controller.state == movement.MOVING
                and movement_controller.move_mode
                in movement.MovementController.OUT_OF_PHASE_MOVE_MODES)
            # The Secondary Mission deck still owes the human a prompt (cash a
            # completed card in, or discard one for CP). Opened at the end of a
            # turn, so without this the next phase could roll over the top of a
            # decision that is still on screen.
            or secondary_mission_controller.is_busy
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
            or deadly_vectors_controller.pending_damage_choice is not None
            # Deadly Vectors drains a QUEUE - one 2D6 per Afflicted enemy unit,
            # then a D3 and an allocation for each that triggered. Advancing the
            # phase mid-queue would silently drop the units still owed a roll.
            or deadly_vectors_controller.is_busy
            # Lethal Ichor and Spore-laced Shock Waves each drain their own
            # dice-then-allocation cycle; advancing the phase mid-cycle would
            # drop the mortal wounds they still owe.
            or lethal_ichor_controller.is_busy
            or spore_laced_controller.is_busy
            or lethal_ichor_controller.pending_damage_choice is not None
            or spore_laced_controller.pending_damage_choice is not None
            # Sickening Impact owes a dice-then-allocation cycle, and Undying
            # Spite may be holding destroyed models on the board that still
            # owe an activation. Neither may be rolled over by a phase change.
            or sickening_impact_controller.is_busy
            or sickening_impact_controller.pending_damage_choice is not None
            or undying_spite_controller.is_busy
            or to_their_final_breath_controller.is_busy
            or khaines_vengeance_controller.is_busy
            # Both halves, or this gate is a deadlock rather than a guard:
            # is_busy alone blocked the phase while NOTHING in the event
            # chain could resolve the hazard step it was waiting on.
            or khaines_vengeance_controller.pending_damage_choice is not None
            # The six mortal-wound carriers. An allocation that is still open
            # must not be rolled over by a phase change - and with the click
            # branches above they are now resolvable, so this is a guard
            # rather than the deadlock the Khaine's line above used to be.
            or living_lightning_controller.pending_damage_choice is not None
            or matter_absorption_controller.pending_damage_choice is not None
            or crimson_harvest_controller.pending_damage_choice is not None
            or eater_plague_controller.pending_damage_choice is not None
            or kroot_linebreakers_controller.pending_damage_choice is not None
            or crushing_strides_controller.pending_damage_choice is not None
            or malevolent_souls_controller.is_busy
            or systematic_vigour_controller.is_busy
            # Retaliation Cadre's Internal Grenade Racks owes a
            # dice-then-allocation cycle, and its Puretide Engram Neurochip
            # drains a QUEUE of D6s (one per Stratagem that targeted a bearer's
            # unit). Neither may be rolled over by a phase change.
            or internal_grenade_racks_controller.is_busy
            or internal_grenade_racks_controller.pending_damage_choice is not None
            or wraith_form_controller.is_busy
            or wraith_form_controller.pending_damage_choice is not None
            or drakolithe_controller.is_busy
            or drakolithe_controller.pending_damage_choice is not None
            or harvester_of_souls_controller.is_busy
            or harvester_of_souls_controller.pending_damage_choice is not None
            or monofilament_snare_controller.is_busy
            or monofilament_snare_controller.pending_damage_choice is not None
            or puretide_neurochip_controller.is_busy
        )

    def _fight_warning_intercepts_end_turn():
        """True if this "End Turn" click was spent raising the "you still
        have units that could fight" warning instead of ending the turn.

        User: "gib mal bitte ine warnung aus, die ich wegklicken muss, wenn
        ich auf end turn klicke, obwohl ich noch mit einheiten im nahkampf
        kaempfen koennte." Reproduced before changing anything: with a human
        unit eligible under rule 12.04 and an engaged enemy in front of it,
        NOTHING stopped the click - _has_unresolved_declaration() above
        covers fight_controller's CHOOSING_*/ASSIGNING sub-states (a
        half-finished activation) but deliberately not SELECTING, which is
        the ordinary "it is your turn to fight, pick a unit" state. So the
        turn ended and those attacks were simply gone, with a game_log line
        as the only trace.

        A warning, not a lock: this engine never forces a player to fight,
        so the click is spent on the warning and the next one goes through
        (see FightWarningOverlay.warn_once()).

        Asked for "Player 1" - the human throughout this engine, the same
        single fact as the ScoutsStep human_players wiring below - and not
        for turn_owner: rule 12.04's Fight step is SHARED, so the human can
        still owe attacks during the AI's own turn, and it is always the
        human doing the clicking here.

        One shared check with two callers, for the same reason
        _has_unresolved_declaration() is one: the right panel's button is not
        the only route into advance_turn_phase() from a human click - a click
        blocked by "Regaining Coherency" (09.02) resumes into the very same
        call once the model is removed, and a warning that one of the two
        routes walks straight past is not a warning."""
        if not turn_tracker.is_last_phase:
            return False
        return fight_warning_overlay.warn_once(
            [s.name for s in fight_controller.squads_that_could_still_fight("Player 1")])

    def run_ai_pregame_action():
        """Player 2's side of rule 03.01's opening sequence - one action per
        frame, same contract as run_ai_action().

        Deliberately API-call-free (see ai/deployment_ai.py's module
        docstring), so starting a game costs nothing.

        A no-op when nobody is automatic: with config.AI_PLAYERS empty both
        sides are played by hand, and there is no side for this to act for."""
        if not ai_players:
            return
        deployment_ai.take_pregame_action(
            pregame_controller, setup_controller, ai_players[0],
            board.width_in, board.height_in,
            objectives=state.objectives, game_log=game_log,
        )

    def run_ai_action():
        """The one call every "A" keypress (and, while ai_auto_play is on,
        every single frame - see the main loop below) makes: resolve
        exactly ONE pending decision for the AI's own side and return.

        A no-op when nobody is automatic: with config.AI_PLAYERS empty there is
        no side for the agent to play, and calling it would have it spend a
        human's CP - and a real API call doing it."""
        nonlocal last_shown_turn_plan
        if not ai_players:
            return
        # The agent stopped answering at some point: say so ONCE and stop
        # asking. take_one_action() is already a no-op in this state, so this
        # is only the announcement - but it has to be raised from somewhere
        # that runs every frame the AI would have acted, and this is that
        # place. See ai/connection.py.
        if not ai_connection.is_online():
            if ai_offline_overlay.show(ai_connection.reason()):
                game_log.add(f"The AI stopped playing: {ai_connection.reason()}. "
                             "The battle continues without it.")
            return
        take_one_action(
            agent, ai_memory, state, turn_tracker, movement_controller, shooting_controller,
            charge_controller, fight_controller, battle_shock_controller, pile_in_controller,
            decision_manager, dice_manager, game_log, coherency_enforcer=coherency_enforcer,
            # WHICH side the agent plays, from the one place that says so.
            # take_one_action() still defaults to "Player 2" for its other
            # callers; naming it here means this call cannot disagree with the
            # auto_players every controller above was built with. Appended as a
            # KEYWORD and the leading arguments left positional - this chain is
            # thirteen positional parameters long, and rewriting it was how a
            # wrong name (ai_memory for memory) got in on the first attempt.
            player=ai_players[0],
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
            # Awakened Dynasty's three proactive protocols. The reactive three
            # (Undying Legions, Eternal Revenant, Vengeful Stars) are NOT here
            # on purpose: they answer inside their own controllers through
            # auto_players, so the AI needs no ai/ path for them at all.
            hungry_void_controller=hungry_void_controller,
            conquering_tyrant_controller=conquering_tyrant_controller,
            sudden_storm_controller=sudden_storm_controller,
            # Not a handler - Deadly Vectors asks nothing. Passed so the AI can
            # answer its OWN mortal-wound allocation when it is the victim; see
            # take_one_action()'s own note on this parameter.
            deadly_vectors_controller=deadly_vectors_controller,
            # Death Lord's Chosen: only Grim Reapers needs a handler. Undying
            # Spite and Sickening Impact are reactive and answer inside their
            # own controllers via auto_players; the other three are irrelevant
            # to the AI by user instruction.
            grim_reapers_controller=grim_reapers_controller,
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
            turn_plan_overlay.show(plan, state.all_squads())
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

    # THE ONE AI SWITCH. Shift+A and the board's AI toggle both flip it, and
    # it governs BOTH channels the AI ever acts through: this frame tick, and
    # the ~83 `auto_players` gates inside the ability and Stratagem
    # controllers. Those gates used to ignore it entirely - see game/ai_mode.py
    # for the reported game where that spent a CP with the dot off.
    #
    # Set here rather than left at the module default, in the same place and
    # to the same value the `ai_auto_play` local it replaces used to start
    # at: a battle opens with the AI idle until it is switched on.
    ai_mode.set_enabled(False)
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
    # The AUTOSAVE's edge (user: "Auto save pro Schlachtrunde"). Seeded with
    # the round the battle actually starts on, NOT None: a loaded scene resumes
    # mid-battle, and a None here would write a fresh autosave over the very
    # file that was just opened before a single frame had been played.
    previous_battle_round = turn_tracker.battle_round

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
        # AFTER begin_battle() for the same reason the turn state is: starting
        # the battle draws round 1's Secondary cards and zeroes the score, so a
        # ledger put back before it would be silently overwritten.
        complaints += scene_io.restore_missions(loaded, _mission_slots())
        # AFTER begin_battle() as well, and here the ordering has teeth: it
        # clears set_up_this_turn on every unit it can find (rule 18.02), so a
        # restore that ran first would have the flag wiped straight back off.
        complaints += scene_io.restore_activation(
            loaded, [e["squad"] for e in scene_units], _activation_slots())
        # Same ordering rule again: begin_battle() built a fresh ledger above,
        # so the resume goes back on after it, never before.
        complaints += scene_io.restore_stats(loaded, battle_stats)
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
        # Two T'au Enhancements whose printed timing is the Declare Battle
        # Formations step, run right after start() puts the controller into it.
        # Student of Kauyon MUST be before the reserve declarations are
        # answered - Deep Strike granted afterwards would be worth nothing this
        # battle, which is why its own printed text names this step.
        _student_of_kauyon_step = StudentOfKauyonStep(
            decision_manager=decision_manager, game_log=game_log,
            auto_players=ai_players)
        # _all_squads(), NOT _player_squads()/state.all_squads(): this is the
        # Declare Battle Formations step, and register_unit() deliberately puts
        # NOTHING into state.tokens/reserves/embarked_squads while
        # PREGAME_DEPLOYMENT is on - so all three containers those two read are
        # EMPTY here and both steps below were silently handed nothing.
        # Reported: "experimental cadre waffen upgrades greifen alle nicht".
        # _all_squads()'s own docstring names this exact trap; the units live in
        # pregame_controller.army(owner) until they are placed.
        for _owner in ("Player 1", "Player 2"):
            _student_of_kauyon_step.start(
                [s for s in _all_squads(state, pregame_controller) if s.owner == _owner],
                _owner)
        # The three Experimental Prototype Cadre weapon upgrades - permanent
        # changes to one named weapon, applied once and idempotent.
        enh_prototype_weapons.apply_all(
            _all_squads(state, pregame_controller), game_log=game_log)
        # Mont'ka's Strike Swiftly runs in Resolve Pre-battle Abilities and
        # MUST come before the Scouts step it feeds - hence the ordered list
        # rather than another named attribute. See game/enh_strike_swiftly.py.
        pregame_controller.prebattle_steps.append(StrikeSwiftlyStep(
            decision_manager=decision_manager, game_log=game_log,
            auto_players=ai_players, game_state=state))
        # The Wraithlord's Fated Hero also runs in Resolve Pre-battle Abilities.
        # Unlike Strike Swiftly it has NO ordering constraint - it grants nothing
        # another step reads - so it simply joins the list. The AI answers it
        # deterministically (see game/fated_hero.py), so there is no ai/ path and
        # no prompt that could stall the pregame.
        pregame_controller.prebattle_steps.append(fated_hero_controller)
        # Windrider Host's Firstdrawn Blade grants Scouts, so it has Strike
        # Swiftly's ordering constraint exactly: it must precede the Scouts
        # step it feeds. Nothing is asked - the card names the bearer's own
        # unit - so it resolves inline.
        pregame_controller.prebattle_steps.insert(0, FirstdrawnBladeStep(
            game_state=state, game_log=game_log))
        # Armoured Warhost's Ethereal Pathway grants INFILTRATORS, whose timing
        # is a step EARLIER: rule 24.20 decides both where a unit may be placed
        # and when, and both are read from the Deploy Armies step on. So it
        # goes in deploy_armies_steps, not here.
        pregame_controller.deploy_armies_steps.append(EtherealPathwayStep(
            game_state=state, decision_manager=decision_manager,
            game_log=game_log, auto_players=ai_players))
        # Kauyon's Solid-image Projection Unit fires "after both players have
        # deployed", which is EARLIER than Resolve Pre-battle Abilities - so it
        # is its own hook rather than a member of the list above.
        # Prince Yriel's Prince of Corsairs fires at the SAME instant as
        # Kauyon's Solid-image Projection Unit - "after both players have
        # deployed" - so the two share the hook and are chained: whichever is
        # live runs, and the second is handed the first's on_done.
        prince_of_corsairs_step = PrinceOfCorsairsStep(
            game_state=state, decision_manager=decision_manager, game_log=game_log,
            auto_players=ai_players)
        _solid_image_step = SolidImageProjectionStep(
            game_state=state, decision_manager=decision_manager, game_log=game_log,
            auto_players=ai_players)

        class _RedeployChain:
            """Both redeployment abilities fire at the same instant, and
            PregameController has ONE redeploy_step slot. Chained rather than
            made a list: the slot's protocol is start(controller, on_done) ->
            "did I take over", which composes by handing the second step the
            first's on_done - and a list would need the same composition
            written into the pregame controller instead."""

            def __init__(self, *steps):
                self.steps = list(steps)

            def start(self, pregame_controller=None, on_done=None):
                return self._run(0, pregame_controller, on_done)

            def _run(self, index, pregame_controller, on_done):
                if index >= len(self.steps):
                    if on_done is not None:
                        on_done()
                    return False
                # One-shot, and asked afterwards whether it fired: a link may
                # hand control back by CALLING nxt and still answer "nothing to
                # do" (prince_of_corsairs.py does exactly that), and falling
                # through would then run the rest of the chain a second time.
                # Same enforcement, same reason as PregameController's own two
                # hand-offs - see game/pregame.py's Resume.
                nxt = pregame.Resume(
                    lambda: self._run(index + 1, pregame_controller, on_done))
                if self.steps[index].start(pregame_controller, nxt) or nxt.fired:
                    return True
                return self._run(index + 1, pregame_controller, on_done)

        pregame_controller.redeploy_step = _RedeployChain(
            _solid_image_step, prince_of_corsairs_step)
        # "Auto-place this unit" on the human's side runs the AI's own placer.
        pregame_controller.on_auto_place = lambda squad: deployment_ai.auto_deploy_squad(
            pregame_controller, setup_controller, squad, board.width_in, board.height_in,
            objectives=state.objectives, game_log=game_log,
        )
        # Rule 24.31 (SCOUTS), resolved in the Pre-battle Abilities step.
        pregame_controller.scouts_step = ScoutsStep(
            movement_controller, game_log=game_log,
            # ai_players passed EXPLICITLY: its default in
            # ai/deployment_ai.py used to be ("Player 2",), so a caller that
            # forgot it silently handed the AI somebody else's Scouts move.
            on_resolve=lambda pre, squad, branch, distance: deployment_ai.resolve_scouts(
                pre, squad, branch, distance, ai_players=ai_players,
                movement_controller=movement_controller, setup_controller=setup_controller,
                board_w_in=board.width_in, board_h_in=board.height_in,
                objectives=state.objectives, game_log=game_log,
            ),
            # The human's half. resolve_scouts() above returns False for a unit
            # it does not own, and until now that was read as "declined" and
            # the unit was popped - so a human's Scouts move was never offered
            # at all (user report). These two lines are what actually open it.
            decision_manager=decision_manager,
            # The same single fact as ai_players above, read from the one
            # place that holds it - this used to be its own literal
            # ("Player 1",), which is a second list to keep in sync with the
            # first and the reason a rule and its switch can drift apart.
            human_players=human_players,
        )
        # A confirmed OR cancelled scout move resumes the SCOUTS queue; without
        # the cancel half a declined drag would strand the pre-game.
        movement_controller.on_scout_move_finished = (
            pregame_controller.scouts_step.on_scout_move_finished)

    def _carrying_a_unit():
        """Whether a board click means "put the carried unit HERE" rather than
        what it normally means.

        Not simply "is something picked": a unit that cannot actually be placed
        right now (another placement still open, an arrival not yet eligible)
        must NOT make the branch match, because a branch that matches and then
        does nothing swallows the click - this repo's error class 15 in
        miniature, and the clicks it would swallow are the ones that adjust the
        placement already in progress."""
        if pregame_controller.awaiting_drop:
            return pregame_controller.can_deploy(pregame_controller.selected_unit)
        return (picked_reserve_squad is not None
                and setup_controller.can_start_setup(picked_reserve_squad))

    def _place_picked_unit(x_in, y_in):
        """Set the unit the player is CARRYING down at (x_in, y_in) - a card
        picked out of the pre-game pool (rule 03.01) or out of the Reserves
        strip (20.04). True if a placement really opened.

        THE ONE ANSWER to "where does the carried unit go", read by all three
        gestures that can put it down: a plain left click on the board, the
        left-drag's release, and the line-formation right-drag. Three copies of
        this would be three chances for one of them to skip
        rapid_ingress_controller.consume() or to leave the card carried after
        it had been placed.

        Order matters and is not arbitrary: a pre-game pick wins, because the
        Reserves strip during 03.01 IS the undeployed pool (main.py's
        reserves_to_show swaps it out) - so the two can never actually both be
        set, and stating the precedence keeps that from being an accident.

        Success is read off setup_controller, not off a return value:
        start_ingress() refuses silently for a unit that is not eligible yet
        (rule 20.03) and start_deployment() for one that is not in the active
        player's pool, and in both cases nothing is placed. The line drag has
        to know the difference - it must not open a gesture over a unit that is
        still in reserve."""
        nonlocal picked_reserve_squad
        if pregame_controller.awaiting_drop:
            pregame_controller.start_deployment(
                pregame_controller.selected_unit, x_in, y_in)
            return setup_controller.state == setup.PLACING
        squad = picked_reserve_squad
        if squad is None or not setup_controller.can_start_setup(squad):
            # SetupController is single-slot: with another placement still open
            # start_ingress() would take the unit OUT of state.reserves and
            # then find start_setup() a no-op, leaving it on neither the board
            # nor the reserve list. The card simply stays carried until the
            # placement in progress is confirmed or cancelled.
            return False
        # The card stops being carried whether or not IngressController accepts
        # it - a refused arrival was never removed from state.reserves, so it
        # is simply back in the strip, and leaving it stuck to the cursor would
        # hide the log line that says why.
        picked_reserve_squad = None
        ingress_controller.start_ingress(squad, x_in, y_in)
        # Rule 15.07: this was the one attempt the Rapid Ingress window bought
        # - used up the instant it is dropped on the board, whether or not
        # IngressController accepts it. setup_controller is passed here (unlike
        # ai/agent_driver.py's own auto-ingress call) so a chained Fire
        # Overwatch offer defers until this placement actually concludes
        # instead of hijacking it mid-drag - see consume()'s own docstring for
        # the full bug report this fixes.
        rapid_ingress_controller.consume(squad, setup_controller=setup_controller)
        return setup_controller.state == setup.PLACING

    def _board_gesture_blocked():
        """Modal state that owns the board's clicks: a line-formation drag may
        not START underneath one.

        A NAMED predicate, read once ahead of the event chain - not the chain
        doing this by accident, which is the failure this whole gesture is
        wired to avoid. The distinction worth writing down: a VIEW may never be
        gated (that is why pointer tracking and the ALT ruler sit outside the
        chain), but an ACTION may, and this one mutates model positions.
        "Never gate" was never the lesson; "never gate ACCIDENTALLY, by falling
        into the elif chain" is.

        Reuses _front_notice() rather than re-listing seven overlays, because
        that helper is already the single home of the notice set - a second
        list here is exactly the kind of copy that goes stale the next time an
        overlay is added.

        Only the START is gated. update_line_drag() and end_line_drag() never
        are: if something becomes pending mid-drag, the gesture still has to
        run to its release, or it strands half-written positions with no route
        to a commit."""
        return (
            _front_notice() is not None
            or decision_manager.is_pending
            or dice_manager.is_pending
            or coherency_enforcer.pending_squad is not None
            or _any_pending_damage_choice()
        )

    # Bound BEFORE the loop so every natural exit (the window's close box, the
    # battle ending) already answers QUIT, and only the menu ever changes it.
    outcome = game_menu_module.QUIT
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
        # ...and while the game menu is up. Seeded here rather than tested at
        # the AI's call sites because this one flag is ALREADY read by both of
        # them - the "A" key branch and the auto-play tick - and the auto-play
        # tick runs OUTSIDE the event loop, so the menu's own `continue` does
        # not cover it. One term here, instead of two copies of the question.
        ai_action_paused_this_frame = _any_pending_damage_choice() or game_menu.is_pending
        for event in pygame.event.get():
            # Where the cursor is and what it hovers is a VIEW fact, never a
            # decision - so it is tracked here, before the state-gated chain
            # below, rather than in its very LAST branch (same argument the
            # "A" key, the mouse wheel and ESC already make further down).
            #
            # User report: "ich kann oft keine entfernungen messen. zb bei
            # overwatch". InputManager.handle_event() is that last branch, so
            # any pending Fire Overwatch offer / damage choice / decision
            # prompt matched earlier and swallowed the motion - mouse_pos_in
            # and hovered_token then froze, and the ALT ruler is drawn from
            # exactly those two. Deliberately a plain `if` ahead of the chain,
            # not a branch inside it: consuming the motion here would freeze
            # dragging in every state where the chain DOES want it.
            # track_pointer() is idempotent, so the later call is harmless.
            if event.type == pygame.MOUSEMOTION:
                input_manager.track_pointer(event.pos, state.tokens, board)

            # The army-rules reader owns every event while it is open, and it
            # is asked HERE - ahead of the state-gated chain - for the reason
            # that chain has swallowed five controls already (error class 15).
            # It is a VIEW: it resolves no decision, so it must not be reachable
            # only when nothing else is pending. `continue` because it really
            # does consume the event: the click that dismisses it must not also
            # land on the board underneath.
            # The GAME MENU owns every event while it is open, and it is asked
            # FIRST - ahead of the state-gated chain for the same reason the
            # reader below is (error class 15), and ahead of the reader because
            # it is drawn over it. Its answer is picked up by take_action()
            # after the loop rather than acted on here: an overlay cannot write
            # main()'s locals, and reading it in one place is what stops one
            # press being served twice.
            if game_menu.is_pending:
                game_menu.handle_event(event, screen.get_rect())
                continue

            # The MENU button, now beside the "Game Status" heading in the
            # right panel, its own pre-chain `if` for exactly the reason above:
            # roughly forty of the chain's branches gate on CONTROLLER STATE
            # with no event.type term, so this press would be matched and
            # dropped by the first pending one - and a stuck prompt is
            # precisely the state a player most wants to reach the menu from.
            # Below the reader's block, so that while the reader is open the
            # click dismisses the reader instead; that falls out of the order
            # rather than needing a test.
            #
            # It reads right_panel_rect, the same rectangle the panel is drawn
            # from, so the button is hit-tested exactly where it was DRAWN.
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and not army_rules_overlay.is_pending
                    and not unit_stats_overlay_view.is_pending
                    and game_menu.button_rect(right_panel_rect).collidepoint(event.pos)):
                _open_game_menu()
                continue

            # The AI switch, which since the MENU button moved into the right
            # panel is the ONLY thing left over the map (user: "dann liegt nur
            # noch der AI Schalter ueber der Map"). Its own pre-chain `if` for
            # the same reason: it sits ON the board, so without it up here the
            # press would either be eaten by one of the ~40 state-gated
            # branches or fall through to the board and start a camera pan.
            # `continue`, so the click that flips the mode cannot also do
            # something to the board underneath it.
            #
            # Hit-tested against the rect the last frame DREW (ai_toggle_rect),
            # not a freshly computed one: draw_ai_mode_toggle() can still step
            # down past a blocker, and a second computation of that geometry is
            # how a control ends up clickable somewhere it is not drawn.
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and not army_rules_overlay.is_pending
                    and not unit_stats_overlay_view.is_pending
                    and ai_toggle_rect is not None
                    and ai_toggle_rect.collidepoint(event.pos)):
                _set_ai_mode(not ai_mode.enabled(), "AI toggle")
                continue

            # The Unit Statistics button, sitting beside the AI switch (user:
            # "der knopf fuer das overlay soll nebn dem schalter fuer die KI
            # sein"). Same pre-chain placement and the same reason: it is drawn
            # ON the board, so without this the press is either eaten by one of
            # the ~40 state-gated branches below or falls through to the board
            # and starts a camera pan. Hit-tested against the rect the last
            # frame DREW, never a freshly computed one.
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and not army_rules_overlay.is_pending
                    and not unit_stats_overlay_view.is_pending
                    and stats_button_rect is not None
                    and stats_button_rect.collidepoint(event.pos)):
                unit_stats_overlay_view.show(
                    battle_stats, _stats_players(), state.all_squads())
                continue

            if unit_stats_overlay_view.is_pending:
                unit_stats_overlay_view.handle_event(event)
                continue

            if army_rules_overlay.is_pending:
                army_rules_overlay.handle_event(event)
                continue

            # The line-formation drag (right button), and deliberately its OWN
            # top-level `if` rather than a branch of the chain below. The chain
            # is ~48 if/elif branches and roughly forty of them gate on
            # CONTROLLER STATE with no event.type term at all - so a button-3
            # press matches the first pending one, that branch's body wants
            # button == 1, and the event is gone. Exactly the states a player
            # most wants to re-form a unit in (a decision prompt, a dice roll,
            # Fire Overwatch) are the ones that would swallow it. Same lesson,
            # and the same shape, as the ALT ruler two entry points above and
            # below this one.
            #
            # No `continue` after this: both events still fall through into the
            # chain, harmlessly (every event.button/event.pos read in it is
            # behind button == 1). Skipping the rest would drop
            # camera.update_pan and re-introduce a swallow of its own.
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3
                    and board_rect_screen.collidepoint(event.pos)):
                if input_manager.begin_line_drag(
                    event.pos, state.tokens, board, movement_controller,
                    setup_controller, blocked=_board_gesture_blocked(),
                    # ...and if the player is CARRYING a unit, the press point
                    # is where it lands: one gesture sets it down AND forms it
                    # up, instead of "drop it, then re-form it" (user: "ohne
                    # zwischen step?"). Exactly the same call the left button's
                    # own board branch makes, so both buttons put a carried
                    # unit in the same place.
                    start_placement=_place_picked_unit,
                ):
                    # A left press may already have started a pan; if it did,
                    # the view would slide under the gesture and the far end of
                    # the line would run away from the cursor at double rate.
                    camera.end_pan()
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                # NOT gated on the board rect: a gesture released over the left
                # panel still has to finish cleanly.
                input_manager.end_line_drag()
            elif event.type == pygame.WINDOWFOCUSLOST:
                # Belt and braces over the poll's own held-button failsafe. The
                # poll rests on pygame.mouse.get_pressed() going False when the
                # window loses focus, and that is an ASSUMPTION about this SDL
                # build which cannot be measured under the dummy video driver
                # the harnesses use. This costs three lines and removes the
                # dependency: whichever notices first ends the drag, and
                # end_line_drag() is idempotent so both noticing is harmless.
                input_manager.end_line_drag()

            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # ESC is a LADDER, innermost rung first: put down a carried
                # reserves card, else let go of the selected unit, else quit in
                # fullscreen.
                #
                # User: "im vollbild modus beendet ESC das spiel" - that
                # decision is intact, it just sits one rung lower now, so in
                # fullscreen quitting takes two presses while a unit is
                # selected. Named rather than done quietly, because it changes
                # a recorded choice.
                #
                # The deselect half is the keyboard counterpart of clicking
                # into the void (game/input_handler.py's _void_press_px): the
                # selection now survives a camera pan, so it needs a
                # deliberate way to be let go of.
                #
                # Still checked before any of the controller-state gates below
                # (same reasoning as "A"/mouse wheel further down: those gate
                # on STATE, not event type, so ESC could otherwise get silently
                # swallowed whenever a dice roll/decision/etc. happened to be
                # pending). Same priority as the window's own close button
                # (QUIT, right above).
                #
                # The carried-card rung is the escape hatch for the pick that
                # now OUTLIVES its release: while a reserves card is carried,
                # every board click sets it down, so without a way to let go of
                # it a stray pick would have to be placed and then cancelled.
                # Only the Reserves pick, not the pre-game pool's: that one is
                # consumed by the very next board click and cannot linger.
                if picked_reserve_squad is not None:
                    picked_reserve_squad = None
                elif movement_controller.selected_squad is not None:
                    movement_controller.select(None)
                else:
                    # THE BOTTOM RUNG CHANGED, and it changes a recorded
                    # decision (user: "im vollbild modus beendet ESC das
                    # spiel"). ESC no longer ends the process; it opens a menu
                    # that CONTAINS Quit - which is what the user asked for
                    # ("im spiel öffnet ein druck auf ESC das menü"). Two
                    # differences worth naming: quitting now takes one press
                    # more, and it works in a WINDOW as well, where ESC used to
                    # do nothing at all. One behaviour instead of two.
                    _open_game_menu()
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
                _save_scene("saved with F9")
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
                    _set_ai_mode(ai_mode.toggle(), "Shift+A")
                elif (
                    not dice_panel.is_busy and not stratagem_notice_overlay.is_pending and not mission_draw_overlay.is_pending
                    and not waaagh_notice_overlay.is_pending
                    and not turn_start_overlay.is_pending and not turn_plan_overlay.is_pending
                    and not fight_warning_overlay.is_pending
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
                if action_panel.handle_rule_scroll(mouse_pos, event.y):
                    # "WHY YOU ARE CHOOSING" in the left panel scrolls. It only
                    # claims the wheel while the cursor is over its box AND
                    # there is something to scroll, so every other wheel use -
                    # board zoom, the log, the datacard - is untouched.
                    pass
                elif unit_datacard.handle_scroll(event.y):
                    # An open datacard owns the wheel: it is drawn OVER the
                    # board, so zooming the board under it is not what the
                    # cursor is pointing at. It only claims the wheel while it
                    # is both visible and actually scrollable, so a short card
                    # still zooms as before.
                    pass
                elif board_rect_screen.collidepoint(mouse_pos):
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
            elif fight_warning_overlay.is_pending:
                # The "you still have units that could fight" warning raised by
                # this same frame's own "End Turn" click (see that branch
                # below). It sits here, above every other notice and far above
                # the button that raised it, for the same reason they all do:
                # the chain is a state-gated if/elif, so a branch further down
                # would be swallowed the moment anything else was pending, and
                # this one in particular MUST outrank the End Turn button - a
                # single click may not both dismiss the warning and end the
                # turn it warned about. Any click dismisses it; there is
                # nothing to choose, and clicking End Turn again is the
                # "anyway" answer.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    fight_warning_overlay.dismiss()
                    ai_action_paused_this_frame = True
            elif battle_end_overlay.is_pending:
                # The battle is over; a click only puts the box aside so the
                # final board can be looked at. Nothing resumes either way.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    battle_end_overlay.dismiss()
                    ai_action_paused_this_frame = True
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
            elif mission_draw_overlay.is_pending:
                # User: "Ich moechte, dass diese Missionen einmal in einem
                # Overlay angezeigt werden, zum Wegklicken, und dann der Link
                # zur linken Leiste hinzugefuegt werden." Same
                # "must-click-away, nothing to choose" priority as the
                # Stratagem notice below it, and above it in the chain because
                # the draw happens first: the cards are in hand from the
                # instant they are drawn, so the player should see WHAT they
                # drew before anything those cards make them decide.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mission_draw_overlay.dismiss()
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
            elif ai_offline_overlay.is_pending:
                # "Connection lost" - nothing to choose, so the same
                # must-click-away handling as the two notices above. It is
                # ABOVE them in the chain for the same reason it leads
                # _front_notice(): it changes who is playing.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    ai_offline_overlay.dismiss()
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
                #
                # TWO WAYS TO ANSWER ONE QUEUE. When the options name UNITS that
                # are all standing on the board, the decision is answered by
                # CLICKING one of them (user: "Immer wenn man eine einheit auf
                # dem schlachtfeld waehlen muss (zb wall of mirrors) will ich
                # die einheit nicht aus einer liste waehlen, sondern auf dem
                # schlachtfeld. Wie bei overwatch."); otherwise the modal
                # overlay carries it exactly as before. Both go through
                # decision_manager.choose(index), so there is one resolution
                # path and not two that could drift.
                #
                # It stays INSIDE this branch on purpose. The branch swallows
                # every other click while a decision is open, which is what
                # keeps a non-modal pick from letting "Next Phase" be clicked
                # out from under an unanswered question - the hazard the modal
                # box used to cover by simply being in the way.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pick = board_unit_pick()
                    if pick is not None:
                        # Left panel first: that is where the rule's own way out
                        # ("Decline"/"Cancel") is drawn now that the overlay is
                        # not. Same shape as crushing_impact's CHOOSING_ENEMY.
                        # A click on an ineligible unit is IGNORED rather than
                        # guessed at - pick.pick() checks eligibility itself.
                        if left_panel_rect.collidepoint(event.pos):
                            action_panel.handle_click(event.pos)
                            ai_action_paused_this_frame = True
                        elif board_rect_screen.collidepoint(event.pos):
                            clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                            if clicked is not None and pick.pick(clicked.squad):
                                ai_action_paused_this_frame = True
                    else:
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
                    elif targeting_array_controller.selecting_die:
                        # A third selection mode, and a separate branch for the
                        # same reason the two below are separate: each takes
                        # over the whole panel, so only one can be open, and
                        # folding them together would let one controller answer
                        # a click meant for another.
                        die_index = dice_panel.die_index_at(event.pos)
                        if die_index is not None:
                            targeting_array_controller.choose_die(die_index)
                    elif unmodified_six_controller.selecting_die:
                        # Same shape as the branch above, and deliberately a
                        # separate one: the two selections can never be open at
                        # once (each takes over the whole panel), and folding
                        # them together would mean one controller answering a
                        # click meant for the other.
                        die_index = dice_panel.die_index_at(event.pos)
                        if die_index is not None:
                            unmodified_six_controller.choose_die(die_index)
                    elif left_panel_rect.collidepoint(event.pos):
                        action_panel.handle_click(event.pos)
                    else:
                        # An Advance roll can still be RE-ROLLED at this instant,
                        # and only at this instant: acknowledge() clears
                        # pending_values and DiceManager.reroll_die() refuses a
                        # roll with none. Two abilities want it - the Autarch's
                        # Superlative Strategist and Protocol of the Sudden Storm
                        # - and the second had been built, unit-tested and never
                        # called from here at all, so its half of that Stratagem
                        # could not fire in a real game. Both are offered from
                        # this one place. A human prompt means the roll must NOT
                        # be acknowledged yet: its callback re-rolls the die.
                        if dice_manager.roll_kind == ADVANCE_ROLL:
                            _adv_squad = movement_controller.selected_squad
                            superlative_strategist_controller.maybe_offer_advance_reroll(_adv_squad)
                            sudden_storm_controller.maybe_offer_advance_reroll(_adv_squad)
                            if decision_manager.is_pending:
                                continue
                        dice_manager.acknowledge()
                        # Before every on_dice_acknowledged(): the roll this
                        # selection belonged to is gone, so an open one would
                        # strand the panel in a mode with nothing to click.
                        unmodified_six_controller.reset()
                        movement_controller.on_dice_acknowledged()
                        shooting_controller.on_dice_acknowledged()
                        charge_controller.on_dice_acknowledged()
                        fight_controller.on_dice_acknowledged()
                        battle_shock_controller.on_dice_acknowledged()
                        # Nightmare Shroud can have queued more than one
                        # test; start_forced_roll() takes one at a time, so
                        # each acknowledged roll releases the next.
                        nightmare_shroud_controller.on_dice_acknowledged()
                        # After battle_shock's: the Grav-Inhibitor Field's own
                        # first step IS a Battle-Shock test, and its second roll
                        # is queued only once that outcome has been applied.
                        grav_inhibitor_controller.on_dice_acknowledged()
                        # Kauyon's Photon Grenades, for the same reason and in
                        # the same place: its one roll IS a Battle-Shock test,
                        # and the charge it interrupted resumes once that
                        # outcome has been applied.
                        photon_grenades_controller.on_dice_acknowledged()
                        flickerjump_controller.on_dice_acknowledged()
                        explosives_controller.on_dice_acknowledged()
                        ishas_fury_controller.on_dice_acknowledged()
                        # Rangers' Path of the Outcast. THIS LINE WAS MISSING,
                        # and it is the whole of the user's report ("die KI
                        # laesst mich mit den Rangern immer noch nicht
                        # bewegen"): the offer appeared, the D6 was rolled and
                        # acknowledged, and nobody told the controller - so
                        # _start_move() was never reached and the unit never
                        # became movable. A controller that is constructed and
                        # never FED is invisible to every test that drives it
                        # directly, which is exactly how test_rangers.py stayed
                        # green (it calls ctrl.on_dice_acknowledged() itself).
                        # Third time this project has hit that class; hence the
                        # source-level wiring guard in test_rangers.py.
                        path_of_the_outcast_controller.on_dice_acknowledged()
                        # Word of the Phoenix is TWO rolls - the 2+ gate and
                        # then the D3+1 count - so it visits this seam twice
                        # and drains the count roll first; see its own
                        # on_dice_acknowledged().
                        word_of_the_phoenix_controller.on_dice_acknowledged()
                        # Nomads of the Hidden Way rolls its D6 for the
                        # move distance, then opens the move on the
                        # acknowledgement - Raid and Run's arrangement.
                        nomads_controller.on_dice_acknowledged()
                        grenade_pack_controller.on_dice_acknowledged()
                        deadly_demise_controller.on_dice_acknowledged()
                        transport_controller.on_dice_acknowledged()
                        crushing_impact_controller.on_dice_acknowledged()
                        fall_back_controller.on_dice_acknowledged()
                        thievin_scavengers_controller.on_dice_acknowledged()
                        spirit_of_gork_controller.on_dice_acknowledged()
                        grot_orderly_controller.on_dice_acknowledged()
                        reanimation_controller.on_dice_acknowledged()
                        coordinated_leadership_controller.on_dice_acknowledged()
                        undying_legions_controller.on_dice_acknowledged()
                        technomancer_controller.on_dice_acknowledged()
                        resurrection_orb_controller.on_dice_acknowledged()
                        living_lightning_controller.on_dice_acknowledged()
                        matter_absorption_controller.on_dice_acknowledged()
                        crimson_harvest_controller.on_dice_acknowledged()
                        kroot_linebreakers_controller.on_dice_acknowledged()
                        kroot_linebreakers_controller.resolve_pending_battle_shock()
                        wraith_form_controller.on_dice_acknowledged()
                        internal_grenade_racks_controller.on_dice_acknowledged()
                        # The three list-holding abilities answer only the
                        # Feel No Pain leg - they roll their own dice inline.
                        drakolithe_controller.on_dice_acknowledged()
                        harvester_of_souls_controller.on_dice_acknowledged()
                        monofilament_snare_controller.on_dice_acknowledged()
                        puretide_neurochip_controller.on_dice_acknowledged()
                        deadly_vectors_controller.on_dice_acknowledged()
                        lethal_ichor_controller.on_dice_acknowledged()
                        spore_laced_controller.on_dice_acknowledged()
                        eater_plague_controller.on_dice_acknowledged()
                        sickening_impact_controller.on_dice_acknowledged()
                        # Spirit Conclave's Crushing Strides. THIS LINE WAS
                        # MISSING: the D6s were rolled, nobody told the
                        # controller, so the mortal wounds were never inflicted
                        # AND its own _pending latch turned the Stratagem off
                        # for the rest of the battle.
                        crushing_strides_controller.on_dice_acknowledged()
                        # Aspect Host's Khaine's Vengeance. Also missing, and
                        # worse: its is_busy sits in the phase-advance gate, so
                        # an unresolved hazard step froze the phase for good.
                        khaines_vengeance_controller.on_dice_acknowledged()
                        pregame_controller.on_dice_acknowledged()  # rule 03.01 roll-offs
            # THE LEFT PANEL STAYS USABLE while an allocation is open, and it
            # goes ABOVE the ~27 damage branches below because those are the
            # ones that were swallowing the click.
            #
            # User: the whole left column - including the global toolbar
            # toggles - went dead during a mortal-wound allocation. The reason
            # is structural: every damage branch below requires
            # board_rect_screen.collidepoint(event.pos) in its BODY, so a click
            # on the panel matched the branch and then did nothing at all.
            # _draw_global_toolbar()'s own docstring promises the opposite
            # ("every left-panel click in main.py's event loop already routes
            # to handle_click() regardless of the current phase/controller
            # state") - a comment describing behaviour no code delivered.
            #
            # This is the minimal safe insertion into a ~48-branch chain
            # (Fehlerklasse 15): its condition names left_panel_rect, so it can
            # only ever take an event a damage branch would have matched and
            # then ignored. A BOARD click does not match it and falls through
            # untouched; event.type short-circuits before event.pos is read
            # (KEYDOWN has none); button == 1 keeps the wheel out, per the
            # documented "eine Radrastung ist ZWEI Events" trap. None of the
            # branches below move.
            #
            # No ai_action_paused_this_frame here: the allocation is still
            # open, so this frame's snapshot already paused the AI.
            elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                  and left_panel_rect.collidepoint(event.pos)
                  and damage_pick.pending(damage_choice_controllers, human_players) is not None):
                action_panel.handle_click(event.pos)
            elif crushing_impact_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in crushing_impact_controller.pending_damage_choice:
                        crushing_impact_controller.choose_damage_model(clicked)
            elif internal_grenade_racks_controller.pending_damage_choice is not None:
                # Retaliation Cadre's Internal Grenade Racks - rule 06.02, the
                # DEFENDER allocates. The canonical form of this branch: event
                # type and button, then the board rect, then token_at_event()'s
                # three-argument call. Four mortal-wound branches were once
                # built against older signatures and crashed the moment they
                # were finally reached (see test_event_chain_wiring.py).
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in internal_grenade_racks_controller.pending_damage_choice:
                        internal_grenade_racks_controller.choose_damage_model(clicked)
            elif wraith_form_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in wraith_form_controller.pending_damage_choice:
                        wraith_form_controller.choose_damage_model(clicked)
            elif drakolithe_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in drakolithe_controller.pending_damage_choice:
                        drakolithe_controller.choose_damage_model(clicked)
            elif harvester_of_souls_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in harvester_of_souls_controller.pending_damage_choice:
                        harvester_of_souls_controller.choose_damage_model(clicked)
            elif monofilament_snare_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in monofilament_snare_controller.pending_damage_choice:
                        monofilament_snare_controller.choose_damage_model(clicked)
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
            elif deadly_vectors_controller.pending_damage_choice is not None:
                # Deadly Vectors' mortal wounds land on a whole enemy unit, so a
                # multi-model target pauses on the defender's allocation choice -
                # which is the COMMON case, not the exception. Canonical form,
                # letter for letter like its siblings above: the MOUSEBUTTONDOWN
                # guard, the board_rect_screen test, then the three-argument
                # token_at_event(). test_event_chain_wiring.py checks all three.
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in deadly_vectors_controller.pending_damage_choice:
                        deadly_vectors_controller.choose_damage_model(clicked)
            elif lethal_ichor_controller.pending_damage_choice is not None:
                # Real user report: "die ki hat nach der schussphase in ihrem
                # zug 2 einfach aufgehört zu agieren". Reproduced from the log:
                # it ended on "Spore-laced Shock Waves: <unit> suffers 3 mortal
                # wound(s)" and nothing after it.
                #
                # These three controllers were asked about their
                # pending_damage_choice in TWO places - _blocked() (so the
                # phase cannot advance) and _any_pending_damage_choice() (so
                # run_ai_action() is skipped) - and had no click branch here at
                # all, so no input could ever clear the choice they were being
                # blocked on. A total deadlock, and one only a Death Guard
                # opponent reaches, which is why it survived until now: all
                # three abilities belong to that faction.
                #
                # The "built, never fed" class again (VengefulStarsController,
                # Path of the Outcast's dice acknowledgement, Sudden Storm's
                # advance re-roll), in the one variant no behaviour test sees:
                # built, blocked ON, never made clickable. Section 6 of
                # test_event_chain_wiring.py is the guard against a fourth.
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in lethal_ichor_controller.pending_damage_choice:
                        lethal_ichor_controller.choose_damage_model(clicked)
            elif spore_laced_controller.pending_damage_choice is not None:
                # The branch the reported hang sat on.
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in spore_laced_controller.pending_damage_choice:
                        spore_laced_controller.choose_damage_model(clicked)
            elif sickening_impact_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in sickening_impact_controller.pending_damage_choice:
                        sickening_impact_controller.choose_damage_model(clicked)
            elif (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and right_panel_rect.collidepoint(event.pos)
                and (rules_player := game_status_panel.army_rules_player_at(event.pos))
            ):
                # The "see rules" links, ONE PER PLAYER. Their own branch ABOVE
                # the Next Phase button's, because both live in the right panel
                # and the first matching branch wins - and reading a rule must
                # never be able to advance the phase. It resolves no decision,
                # so it is not gated on anything being pending.
                #
                # The panel answers WHICH player's link was hit, so the reader
                # opens on that army alone rather than on both.
                army_rules_overlay.show(armies, rules_player)
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
                # _fight_warning_intercepts_end_turn(): see its own
                # docstring - ending the turn while rule 12.04 still owes the
                # human melee attacks used to happen silently.
                if not blocked and not _fight_warning_intercepts_end_turn():
                    movement_controller.select(None)
                    shooting_controller.cancel()
                    advance_turn_phase()
            elif coherency_enforcer.pending_squad is not None:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and board_rect_screen.collidepoint(event.pos):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in coherency_enforcer.pending_squad.models:
                        coherency_enforcer.remove_model(clicked)
                        # The second route into advance_turn_phase() from a
                        # human click: this IS the "End Turn" click above,
                        # resumed once 09.02's coherency removal is answered.
                        # Without the same guard here the warning would be
                        # skipped by exactly the turns that took the long way
                        # round.
                        if coherency_enforcer.pending_squad is None and not _fight_warning_intercepts_end_turn():
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
            elif grenade_pack_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in grenade_pack_controller.pending_damage_choice:
                        grenade_pack_controller.choose_damage_model(clicked)
            elif ishas_fury_controller.pending_damage_choice is not None:
                # Rule 06.02 again: the moving player picks which of their own
                # models takes each mortal wound.
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in ishas_fury_controller.pending_damage_choice:
                        ishas_fury_controller.choose_damage_model(clicked)
            elif khaines_vengeance_controller.pending_damage_choice is not None:
                # Aspect Host's Khaine's Vengeance: a Desperate Escape test on
                # every model of the falling-back unit, so its owner picks who
                # falls. THIS BRANCH WAS MISSING while the controller's is_busy
                # already blocked the phase advance - built, blocking, and not
                # clickable, which is a hard hang rather than a silent no-op.
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in khaines_vengeance_controller.pending_damage_choice:
                        khaines_vengeance_controller.choose_damage_model(clicked)
            # The six carriers of game/mortal_wound_abilities.py's shared
            # allocation session. NONE of them had a branch here, so against
            # any multi-model target the session parked on pending_choice and
            # the mortal wounds were never applied at all - see that module's
            # rule 06.02 note. One branch each, in the canonical form, because
            # that is what test_event_chain_wiring.py sections 3 and 6 read.
            elif living_lightning_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in living_lightning_controller.pending_damage_choice:
                        living_lightning_controller.choose_damage_model(clicked)
            elif matter_absorption_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in matter_absorption_controller.pending_damage_choice:
                        matter_absorption_controller.choose_damage_model(clicked)
            elif crimson_harvest_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in crimson_harvest_controller.pending_damage_choice:
                        crimson_harvest_controller.choose_damage_model(clicked)
            elif eater_plague_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in eater_plague_controller.pending_damage_choice:
                        eater_plague_controller.choose_damage_model(clicked)
            elif kroot_linebreakers_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in kroot_linebreakers_controller.pending_damage_choice:
                        kroot_linebreakers_controller.choose_damage_model(clicked)
            elif crushing_strides_controller.pending_damage_choice is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and board_rect_screen.collidepoint(event.pos)
                ):
                    clicked = input_manager.token_at_event(state.tokens, board, event.pos)
                    if clicked is not None and clicked in crushing_strides_controller.pending_damage_choice:
                        crushing_strides_controller.choose_damage_model(clicked)
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
                            picked_reserve_squad = clicked_squad
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
                elif board_rect_screen.collidepoint(event.pos) and _carrying_a_unit():
                    # Rules 03.01/20.04: a unit is being CARRIED - picked out of
                    # the pre-game pool or out of the Reserves strip - and this
                    # click says where it goes. Intercepted ahead of the normal
                    # board handling, which would otherwise read it as a
                    # selection/move gesture.
                    #
                    # The reserves half is new: a card used to be placeable only
                    # by a held left-drag, so a plain click on one did nothing
                    # visible and the pick was thrown away on release. Now the
                    # strip answers a click the way the pre-game pool always
                    # has, which is also what gives the right-drag a carried
                    # unit to work with.
                    local = camera.to_native_px(
                        (event.pos[0] - board_rect_screen.x, event.pos[1] - board_rect_screen.y)
                    )
                    _place_picked_unit(*board.to_in(*local))
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
                    # ...and not while a line-formation drag is live either:
                    # that gesture is already writing this squad's positions,
                    # and panning under it moves the frame the line's far end
                    # is measured in.
                    if (input_manager.dragging_token is None
                            and input_manager.pending_move_token is None
                            and not input_manager.line_drag_active):
                        camera.begin_pan(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and picked_reserve_squad is not None:
                # Rule 20.04: the end of a left-DRAG out of the Reserves strip -
                # if it lands on the board the card goes down there (Ingress
                # checks battle round eligibility, and at confirm time the extra
                # set-up-distance/enemy-proximity constraints on top of plain
                # Set Up).
                #
                # A release anywhere ELSE no longer throws the pick away: the
                # unit stays carried, so a plain click on a card is a pick
                # rather than a flicker, and the line-formation right-drag has
                # something to place. Putting it back down is the same click it
                # always was, and Cancel in the left panel returns it to
                # reserves if the spot turns out to be wrong.
                if board_rect_screen.collidepoint(event.pos):
                    local = (event.pos[0] - board_rect_screen.x, event.pos[1] - board_rect_screen.y)
                    _place_picked_unit(*board.to_in(*camera.to_native_px(local)))
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

        # What the game menu was pressed for, read ONCE per frame. Polled here
        # rather than acted on inside the event branch because an overlay
        # cannot write main()'s locals, and take_action() clears the answer as
        # it hands it over - the same idiom as
        # unshrouded_truth_controller.take_pending_placement() below.
        _menu_answer = game_menu.take_action() if game_menu.is_pending else None
        if _menu_answer == game_menu_module.RESUME:
            game_menu.dismiss()
        elif _menu_answer == game_menu_module.SAVE:
            _save_scene("saved from the menu")
        elif _menu_answer is not None:
            # NEW_GAME or QUIT: both END this battle. run() reads the answer
            # and either comes back round for a new one or closes the window.
            game_menu.dismiss()
            outcome = _menu_answer
            running = False

        # The ALT ruler (User: "sorge bitte dafür, dass ich immer entfernungen
        # messen kann. mit alt"). Polled from the modifier's live state instead
        # of the KEYDOWN/KEYUP pair this used to be, because that pair lived
        # inside the state-gated chain above and was swallowed by whichever
        # branch happened to be active - see InputManager.update_measuring().
        # Once per frame and AFTER the events, so this frame's own motion is
        # already tracked and the origin snaps to whatever the cursor really
        # sits on.
        input_manager.update_measuring(bool(pygame.key.get_mods() & pygame.KMOD_ALT))

        # Same argument as the line above, and the same shape. The gesture's
        # CONTINUATION is polled so no branch can lose it, and a lost
        # MOUSEBUTTONUP (ALT+TAB, focus loss) cannot strand a drag that is
        # actively rewriting model positions - worse than the ruler's version
        # of that bug, which only stranded a drawing.
        input_manager.update_line_drag(bool(pygame.mouse.get_pressed()[2]))

        # Seer Council's Unshrouded Truth ends with "your unit must make an
        # ingress move this phase", and the user read that as immediate ("der
        # unterschied ist nur, dass ich sie sofort wieder platzieren muss"). So
        # rather than leaving a card to pick up later, the owed arrival arms the
        # very drag a reserves card would - the next board click sets the unit
        # down. Polled once per frame, after the events, because the stratagem
        # is bought from an ActionPanel callback and there are several of those
        # dispatch sites; taking it (rather than reading it) means a second frame
        # cannot re-arm a placement already in progress.
        _owed_arrival = unshrouded_truth_controller.take_pending_placement()
        if _owed_arrival is not None:
            picked_reserve_squad = _owed_arrival
            ingress_controller.homing_beacon_bearer = None

        # A carried card now OUTLIVES the release that picked it up, so it also
        # needs an expiry - without one it would survive into the Shooting
        # phase, and IngressController.can_ingress() checks the battle round
        # but never the PHASE (see reserves_panel_visible's own note), so the
        # next board click would sneak an out-of-phase arrival. Polled once a
        # frame rather than hooked onto the phase change, because the pick can
        # also lapse for reasons that are not a phase boundary: the unit was
        # placed by something else, destroyed with its transport, or arrived
        # via the AI's own path. Deliberately AFTER the arming above, so an
        # owed arrival gets its frame.
        #
        # ...EXCEPT for the one squad a Rapid Ingress window is open for, and
        # that exception is the whole of rule 15.07: its window opens as the
        # opponent's Movement phase ENDS (see the offer site above - it fires
        # after advance_phase(), so the clock already reads Shooting), so the
        # phase test below matched EVERY Rapid Ingress. A human who bought it
        # picked the card up and the very next frame took it away again.
        #
        # Reported: "Ich habe im letzten spiel als player 2 rapid ingress fuer
        # den shard of the voiddragen verwendet, konnte aber danach keine
        # einheit platzieren" - and in that game's log the window opens at line
        # 259, one line after "Player 1: Shooting phase begins", and closes
        # unused at line 313. Nothing to do with who the AI is: the AI reaches
        # its reserves through ai/deployment_ai.py and never through this pick,
        # which is why only a human could meet it.
        #
        # Narrowed to that ONE squad rather than "any pending window", so the
        # guard keeps doing its job: every other reserve unit still cannot be
        # walked in out of phase on the back of somebody else's Stratagem.
        if picked_reserve_squad is not None and (
                picked_reserve_squad not in state.reserves
                or (turn_tracker.phase != PHASE_MOVEMENT
                    and picked_reserve_squad is not rapid_ingress_controller.pending_squad)):
            picked_reserve_squad = None

        # Rule 07.01 again, once per frame. The battle becomes over inside
        # advance_turn_phase(), but the last turn end is also when the deck's
        # final-round cards open their scoring prompt, so _check_battle_end()
        # holds the result back while any decision is still open (see its own
        # docstring). This is where it is raised once that answer lands - the
        # frame after, not another turn later.
        #
        # POLLED and outside the event loop, for the reason CLAUDE.md's error
        # class 15 records five times over: the chain is a long if/elif over
        # controller state, and a result that only appeared when no branch
        # happened to claim the frame would appear late or not at all.
        # Idempotent, exactly like the call in advance_turn_phase().
        _check_battle_end()

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
            turn_start_overlay.show(
                turn_tracker.turn_owner,
                turn_tracker.turn_number_for(turn_tracker.turn_owner),
                faction_keyword=current_player_factions().get(turn_tracker.turn_owner),
            )
            if turn_tracker.turn_owner == "Player 2":
                camera.zoom = camera.min_zoom
                camera.pan_x = 0.0
                camera.pan_y = 0.0
            previous_turn_owner = turn_tracker.turn_owner

        # THE AUTOSAVE (user: "Auto save pro Schlachtrunde"), so the menu's
        # Resume entry has something to offer without anyone having learned
        # about F9.
        #
        # A ROUND boundary, and that is not just what was asked for - it is the
        # only instant at which the snapshot is complete BY CONSTRUCTION rather
        # than by serialising a dozen more things. Everything the mission
        # controllers keep that cannot go into JSON at all - live squad
        # references, id()-keyed sets, an open board pick's callbacks - is
        # turn-scoped and therefore empty here.
        #
        # Outside the event loop for the same reason the block above is: it
        # must not be reachable only when no branch happened to claim the
        # frame. Held back while anything is pending, so the file is written
        # from a settled board rather than from the middle of a dice roll.
        if turn_tracker.started and turn_tracker.battle_round != previous_battle_round:
            if (not decision_manager.is_pending and not dice_manager.is_pending
                    and _front_notice() is None
                    and coherency_enforcer.pending_squad is None
                    and not _any_pending_damage_choice()):
                previous_battle_round = turn_tracker.battle_round
                _save_scene(f"autosaved at the start of battle round {turn_tracker.battle_round}",
                            path=os.path.join(scene_io.SCENES_DIR, scene_io.AUTOSAVE_NAME),
                            quiet=True)

        if (
            ai_mode.enabled() and not dice_panel.is_busy and not stratagem_notice_overlay.is_pending and not mission_draw_overlay.is_pending
            and not waaagh_notice_overlay.is_pending
            and not turn_start_overlay.is_pending and not turn_plan_overlay.is_pending
            and not fight_warning_overlay.is_pending
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
            # Raid and Run needs the same sample for the same reason: "was
            # eligible to fight this phase" cannot be recomputed once the phase
            # has ended.
            raid_and_run_controller.note_eligibility()
        _swept = state.remove_dead_models()
        # Undying Spite: destroyed models that have not fought roll a D6 and,
        # on a 4+, are put straight back so they can strike after the attacker
        # finishes. Intercepted HERE because remove_dead_models() is what takes
        # them off the board - noticing it later would be reading a board that
        # has already changed (error class 12). Putting the model BACK is the
        # shared ledger's job (game/fight_after_death.py), not this loop's -
        # which is what let the second consumer below join in one line.
        undying_spite_controller.intercept_destroyed(_swept)
        to_their_final_breath_controller.intercept_destroyed(_swept)
        # Wraithblades' Malevolent Souls, fed from the same sweep and for the
        # same reason. It needs no re-add loop of its own: the shared ledger in
        # game/fight_after_death.py puts the model back itself, which is why the
        # second consumer of this mechanism did not have to copy the four halves
        # of "back on the board" into this loop.
        malevolent_souls_controller.intercept_destroyed(_swept)
        systematic_vigour_controller.intercept_destroyed(_swept)
        # Nurgle's Gift: re-derive Squad.afflicted / Squad.afflicted_plague for
        # every unit, once per frame. Here, right AFTER the sweep, because the
        # aura is measured against LIVING Death Guard models and a unit wiped
        # out this frame must stop projecting it in the same frame it dies -
        # the recurring "remove_dead_models() runs once per frame" ordering
        # trap. Positions change every frame, so once per frame is genuinely
        # the rate this has to run at; the alternative is re-deriving the same
        # geometry once per weapon group inside attached_unit_toughness(),
        # which has nine callers. See game/nurgles_gift.py's docstring.
        # Signal Pox re-marks whatever is standing on its chosen objective
        # RIGHT NOW - the objective is fixed for the duration, the units on it
        # are not. BEFORE the aura refresh, so the marks it sets are part of
        # the same frame's answer rather than one frame late.
        signal_pox_controller.refresh(state.tokens)
        nurgles_gift_controller.refresh(state.tokens)
        # Spirit Conclave's Spirit Guides aura is read from the squad by
        # game/battle_focus.py, which cannot import a controller (it is
        # reached from game/squad.py's own import chain). So every squad is
        # stamped with a back-reference here, beside the other per-frame aura
        # refreshes - the arrangement Nurgle's Gift already uses.
        shepherds_of_the_dead_controller.attach_to(
            {t.squad for t in state.tokens if t.squad is not None})
        # The Poxwalkers' Curse of the Walking Pox counts enemy models a
        # POXWALKER killed. Counted in the sweep, spent when the unit finishes
        # its attacks - the printed text separates those two moments and so
        # does this.
        if _swept:
            curse_of_the_walking_pox_controller.notify_kills(
                getattr(fight_controller, "fighting_squad", None), _swept)
        # Protocol of the Vengeful Stars reacts to a whole UNIT dying, not to
        # individual models, and its 6" is measured from where that unit stood
        # - so it is fed once per wiped-out squad, here, with whoever was
        # shooting at the time. Done BEFORE the per-model loop below so the
        # capture happens exactly once per squad rather than once per corpse.
        for _wiped in {t.squad for t in _swept
                       if t.squad is not None and not any(not m.is_dead() for m in t.squad.models)}:
            vengeful_stars_controller.notify_unit_destroyed(
                _wiped, getattr(shooting_controller, "active_squad", None))
            # Mont'ka's Pinpoint Counter-Offensive reacts to the same
            # instant, but its WHEN is "any phase" rather than the Shooting
            # phase - so the Fight phase's attacker counts too. Same "who was
            # attacking at the time" answer; this engine has no other.
            pinpoint_controller.notify_unit_destroyed(
                _wiped,
                getattr(shooting_controller, "active_squad", None)
                or getattr(fight_controller, "fighting_squad", None))
            # The Yncarne's Inevitable Death teleports to where a friendly
            # AELDARI unit fell, so it is fed from the same per-SQUAD loop -
            # the corpses' coordinates survive the sweep, which is the whole
            # reason it can be answered here and not later.
            inevitable_death_controller.notify_unit_destroyed(
                _wiped, [t for t in _swept if t.squad is _wiped])
            # Vaul's Vengeance: "just after an enemy unit DESTROYS a DIRE
            # AVENGERS or GUARDIANS unit". Fed per wiped-out SQUAD, not per
            # corpse - a unit is destroyed once however many models it had.
            vauls_vengeance_controller.notify_unit_destroyed(
                _wiped,
                getattr(shooting_controller, "active_squad", None)
                or getattr(fight_controller, "fighting_squad", None))
            # Overflight: "destroyed one or more enemy units this phase". Fed
            # from the same per-SQUAD loop and for the same reason - the fact
            # is unrecoverable once the dead unit is gone, and nothing on the
            # killer remembers it.
            overflight_controller.notify_unit_destroyed(
                _wiped,
                getattr(shooting_controller, "active_squad", None)
                or getattr(fight_controller, "fighting_squad", None))
            # Its Ethereal Form heals it for destroying one. Same "whoever was
            # attacking at the time" answer as the line above - this engine has
            # no other, as Szeras' own note records - and only for an ENEMY of
            # the killer, which the owner test is.
            _killer = (getattr(shooting_controller, "active_squad", None)
                       or getattr(fight_controller, "fighting_squad", None))
            if (_killer is not None and _killer.owner != _wiped.owner
                    and ynnari_abilities.ethereal_form_applies(_killer)):
                ynnari_abilities.roll_ethereal_form(_killer, game_log)
        for dead in _swept:
            game_log.add(f"{dead.profile.name} was destroyed.")
            # Fuegan's Unquenchable Resolve only NOTES the death here; the roll
            # is "at the end of the phase" and happens at the phase boundary.
            # Noting it here rather than there is what keeps "the first time this
            # model is destroyed" honest about which phase the death was in.
            unquenchable_resolve_controller.notify_destroyed([dead])
            # Phoenix Gem, noted in the same sweep and for the same reason -
            # which phase the death happened in is not reconstructable later.
            phoenix_gem_controller.notify_model_destroyed(
                getattr(dead, "squad", None), dead)
            # Shepherds of the Dead: "each time an ASURYANI PSYKER model from
            # your army is destroyed BY AN ENEMY UNIT, that enemy unit gains a
            # Vengeful Dead token". Per MODEL, so it is fed from this loop
            # rather than the per-squad one above - a unit can lose two psykers
            # and hand out two tokens. The killer is whoever was attacking at
            # the time, this engine's only answer to that question.
            shepherds_of_the_dead_controller.notify_psyker_destroyed(
                dead, dead.squad,
                getattr(shooting_controller, "active_squad", None)
                or getattr(fight_controller, "fighting_squad", None))
            # Atomic Energy Manipulator: "if this model destroyed one or more
            # models this phase". Credited to the unit that was fighting, which
            # is exact for Szeras - he has no LEADER line, so his unit is always
            # just him. See game/mechanical_augmentation.py.
            atomic_energy_controller.notify_destroyed(
                [dead], getattr(fight_controller, "fighting_squad", None))
            # Protocol of the Eternal Revenant: noted as the model is swept, so
            # "was JUST destroyed" stays honest about which phase it died in;
            # bought and resolved at the phase boundary. Fuegan's arrangement.
            eternal_revenant_controller.notify_destroyed([dead])
            state.add_blood_decal(dead.x_in, dead.y_in)
            if movement_controller.selected_model is dead:
                # Re-anchor onto a surviving squadmate instead of dropping the
                # whole pick. Now that the selection is drawn as a UNIT, losing
                # it because one model of it died reads as the pick vanishing
                # for no reason the player can see - and the line-of-sight
                # highlight is measured FROM the anchor (see the anchor block
                # further down), so leaving a corpse as the anchor would measure
                # sight lines from a dead model. See game/selection.py.
                movement_controller.selection.reanchor()
                if movement_controller.selected_squad is None:
                    # Whole unit wiped: fall through to the full select(None),
                    # which is what also resets the move state and errors -
                    # reanchor() only answers "who is picked".
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
                # Same instant, second consumer: the Secondary Mission card
                # "A Grievous Blow" counts destroyed UNITS (Starting Strength
                # 13+) where "Bring It Down" counts destroyed MODELS, so it
                # hangs off this branch's own unit_is_destroyed() judgement
                # rather than re-deriving one.
                secondary_mission_controller.record_destroyed_squad(dead.squad)
                # ...and a third: four of the five Force Disposition Primary
                # Missions have a box that counts or asks about destroyed enemy
                # UNITS. There is deliberately no model-level twin - not one of
                # those boxes counts models.
                primary_mission_controller.record_destroyed_squad(dead.squad)
                # Fourth consumer of the same judgement: the Kroot Flesh
                # Shaper's Rites of Feasting upgrades its unit's Feel No Pain
                # from 6+ to 5+ for the rest of the battle once that unit has
                # "destroyed one or more enemy units in the Fight phase".
                #
                # THE KILLER IS TAKEN FROM fight_controller.fighting_squad,
                # which is this engine's only available answer to "who did
                # that" - there is no kill attribution here (the same gap
                # Illuminor Szeras' own note records). It is still set while
                # the sweep runs, because deaths are removed in the same frame
                # the damage is applied. The module itself re-checks that the
                # phase really is Fight rather than trusting this call site.
                if fight_controller.fighting_squad is not None \
                        and fight_controller.fighting_squad.owner != dead.squad.owner:
                    rites_of_feasting.record_fight_phase_kill(
                        fight_controller.fighting_squad, turn_tracker)
            # Per MODEL, not per unit, and unconditionally: the Secondary
            # Mission card "Bring It Down" counts enemy MODELS with a Wounds
            # characteristic of 10+ destroyed this turn, so a squadron losing
            # two hulls out of three scores twice while its unit lives on and
            # record_destroyed_squad() above never fires at all.
            secondary_mission_controller.record_destroyed_model(dead)

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
        if anchor is None or input_manager.dragging_group or input_manager.dragging_setup_group:
            # A whole-unit drag (game/movement.py's apply_group_drag(),
            # game/setup.py's block placement) moves every model in the unit on
            # every single mouse-motion event - skip the live LOS highlight
            # while one is IN PROGRESS rather than adding its own cost
            # (measured at 8.3 ms per recompute on a 142-model map2 board, i.e.
            # half a frame; already an identified hot path, see
            # VISIBILITY_SAMPLE_POINTS above) on top of that.
            #
            # IN PROGRESS, not "the preference is on", and that distinction is
            # load-bearing: the highlight itself no longer has a toggle at all
            # (user decision - "den LOS Check Knopf brauch ich nicht mehr. der
            # soll immer aktiviert sein"), and the whole-unit-drag preference
            # now defaults to ON since it absorbed block placement's default.
            # Gated on the preference, those two decisions would cancel out -
            # the highlight would be off by default, which is exactly what the
            # user asked to stop. input_manager sets these two on mouse-down
            # and clears them on mouse-up, so this pays the cost of nothing
            # while the player is merely hovering with a model selected.
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
        # With an allocation open the panel says ALLOCATE, so the overwatch
        # rings have to stand down - otherwise the board offers two different
        # clicks for one question, which is half of what made the reported
        # situation "sehr verwirrend". Gated on the DERIVED set rather than on
        # get_fire_overwatch_eligible_squads(), whose cache miss runs
        # show_loading_overlay() and a full sweep.
        fire_overwatch_target_models = (
            set() if damage_pick.pending(damage_choice_controllers, human_players) is not None
            else {token for token in state.tokens if token.squad in fire_overwatch_eligible_squads})

        # Defensive full clear: board_rect_screen/left_panel_rect/
        # right_panel_rect/reserves_panel_rect are sized to exactly tile the
        # whole window with no gaps, so nothing should ever actually show
        # through this - cheap enough to not be worth relying on that
        # holding exactly (e.g. across integer rounding) instead.
        screen.fill(config.BACKGROUND_COLOR)

        # Everything below draws onto board_surface in full-board
        # coordinates, unaware of zoom/pan - but only the camera's visible
        # rect is ever shown, so clip to it. This is what pays for the
        # derived render resolution (game/render_resolution.py): the
        # per-frame cost then follows the SCREEN area instead of the board's
        # full pixel count, which is why rendering ~3x as many pixels per
        # inch came out FASTER than the old fixed resolution did (measured
        # on the real army: map1 9.2ms -> 7.3ms, map2 9.9ms -> 6.3ms).
        # Nothing outside the clip can go stale: the static terrain layer is
        # re-blitted over the whole visible rect every frame, so a region
        # that a pan brings into view is drawn fresh that same frame.
        board_clip = camera.visible_rect()
        board_surface.set_clip(board_clip)

        renderer.draw(
            board_surface, board, state.tokens, state.obstacles,
            deployment_zones=state.deployment_zones, blood_decals=state.blood_decals,
            terrain_areas=state.terrain_areas,
        )
        # The DEATH GUARD Contagion aura, as a faint green layer. Drawn
        # immediately after the board and BEFORE the models, so the models sit
        # on top of it rather than under a green wash - it is a property of the
        # ground they stand on, not a tint on the miniatures.
        #
        # reach_of is the CONTROLLER's own answer, so the circle drawn is the
        # circle the rule reads: Blooming Pestilence's +3" and the 12" cap
        # included. A renderer that computed the range itself would be a
        # second, quietly diverging answer.
        renderer.draw_contagion_aura(
            board_surface, board, state.tokens,
            reach_of=nurgles_gift_controller.reach_of,
        )
        # The RANGE RULER (game/aura_ruler.py), drawn right after the aura it
        # is modelled on so the two share a place in the stack: under the
        # models, over the ground, because both are facts about the ground
        # rather than a tint on the miniatures.
        #
        # ONLY the model that was clicked - "wenn ich ein spezifisches Modell
        # anklicke soll nur die Aura dieses Modells angezeigt werden" - and
        # active_radius() is the single question that answers both "is the
        # ruler on" and "how big", so the toolbar and this cannot disagree
        # about what is on screen.
        #
        # The anchor is passed rather than re-derived: selection.py owns which
        # model the click landed on, and it is the same anchor the
        # line-of-sight highlight is measured from, so the ruler and that
        # highlight cannot end up pointing at different models.
        renderer.draw_range_aura(
            board_surface, board, movement_controller.selected_squad,
            aura_ruler.active_radius(), model=movement_controller.selected_model,
        )
        # User request: always show what a TRANSPORT (18.02) is carrying,
        # not just while actively disembarking it - see
        # Renderer.draw_embarked_passengers()'s own docstring.
        renderer.draw_embarked_passengers(
            board_surface, board, state.tokens, state.embarked_squads,
        )
        # Rules 03.02/20.04: show where the unit being placed could legally
        # end up (green) or not (red) - already while it's still being
        # dragged out of the Reserves panel (before it's even dropped), and
        # while fine-adjusting its models afterward. One representative
        # model of the squad, since they all share the same base size.
        placement_squad = (
            picked_reserve_squad if picked_reserve_squad is not None
            else setup_controller.setting_up_squad if setup_controller.state == setup.PLACING
            # Rule 03.01: a unit picked from the pre-game pool but not yet
            # dropped - same "show me where this may go before I commit"
            # window a reserves-panel drag has.
            else pregame_controller.selected_unit if pregame_controller.awaiting_drop
            else None
        )
        if placement_squad is not None:
            if placement_squad is pregame_controller.selected_unit and pregame_controller.awaiting_drop:
                position_valid_fn = lambda token, x_in, y_in: pregame_controller.overlay_position_valid(
                    placement_squad, token, x_in, y_in,
                )
                session_key = ("pregame-select", id(placement_squad))
            elif pregame_controller.is_deploying(placement_squad):
                # Rule 03.01's own placement. Same predicate the drag is held
                # inside EXCEPT the other-models term, which the deployment
                # overlay deliberately does not paint - see
                # PregameController.overlay_position_valid(). Must be tested
                # before the generic PLACING branch below, which this one is a
                # special case of.
                position_valid_fn = lambda token, x_in, y_in: pregame_controller.overlay_position_valid(
                    placement_squad, token, x_in, y_in,
                )
                session_key = ("pregame-place", setup_controller.placement_generation)
            elif placement_squad is setup_controller.setting_up_squad:
                # Once PLACING has begun, the overlay paints the exact same
                # predicate SetupController.clamp_position() holds the drag
                # inside - one source of truth, so "green" and "the model is
                # allowed to stop here" cannot drift apart.
                position_valid_fn = setup_controller.placement_validator(placement_squad)
                # Not placement_generation directly: for a model RETURN the
                # legal ground is drawn from where the squadmates stand, and
                # they move while the player positions them - see
                # SetupController.overlay_cache_key(). Completed below, once
                # the model the band belongs to is known.
                session_key = ("setup", None)
            else:
                # Still being dragged out of the Reserves panel - nothing has
                # been dropped yet, so there is no placement to ask.
                position_valid_fn = lambda token, x_in, y_in: ingress_controller.position_valid(
                    placement_squad, token, x_in, y_in,
                )
                session_key = ("reserve-drag", id(placement_squad))
            # ONE PICTURE FOR THE WHOLE UNIT. The overlay used to draw legal
            # CENTRES, which is a different curve per base size, so a model had
            # to be nominated to draw for - the biggest, on the claim that its
            # legal ground is a subset of every other model's. Coherency broke
            # that claim (it GROWS with the radius while terrain and edges
            # shrink with it): measured on Warriors + Overlord, 8.6 sq.in were
            # legal for the big model only and 9.3 for the small one only, so
            # neither mask was safe for the other.
            #
            # Base-edge zones have no such problem - they are evaluated for a
            # point-sized base, so the red half is the same for everyone. Only
            # the coherency band still depends on which model is being placed,
            # because "the others" is a different set for each; it gets its own
            # cache key.
            placing_now = (
                setup_controller.placing_models
                if placement_squad is setup_controller.setting_up_squad
                and setup_controller.placing_models
                else placement_squad.models
            )
            band_token = (
                input_manager.dragging_token
                if input_manager.dragging_token in placing_now
                else (placing_now[0] if placing_now else None)
            )
            if placement_squad is setup_controller.setting_up_squad:
                keep_out_fn, band_fn = setup_controller.base_edge_zones(
                    placement_squad, band_token)
                band_key = ("band", setup_controller.overlay_cache_key(band_token))
            else:
                # Not a SetupController placement yet (a reserves drag, an
                # undropped pool pick): the owning controller answers per
                # position, so the keep-out zone is that predicate asked for a
                # point-sized base. Nothing to stay coherent with yet.
                def keep_out_fn(x_in, y_in, _fn=position_valid_fn, _t=band_token):
                    if _t is None:
                        return False
                    real = _t.radius_in
                    _t.radius_in = 0.0
                    try:
                        return not _fn(_t, x_in, y_in)
                    finally:
                        _t.radius_in = real
                band_fn = None
                band_key = None
            if session_key == ("setup", None):
                session_key = ("setup", setup_controller.overlay_cache_key(None))
            renderer.draw_placement_overlay(
                board_surface, board, keep_out_fn, band_fn,
                (session_key, len(state.tokens)),
                band_key=(band_key, len(state.tokens)) if band_key else None,
            )
            # ...and say WHICH unit that legal ground belongs to. Only for a
            # unit whose models are actually standing on the board: a reserves
            # drag and an undropped pool pick are not placed yet, so outlining
            # them would ring stale positions they are not on. The pool pick
            # gets its answer in the reserves strip instead (selected_squad
            # there), and the drag gets the ghost that follows the cursor.
            if (placement_squad is setup_controller.setting_up_squad
                    and setup_controller.state == setup.PLACING):
                # ...and, for a PARTIAL placement (rule 01.02.03's model
                # return), WHICH models are the new ones: the unit outline is
                # equally true of the survivors standing beside them.
                renderer.draw_placement_identity(
                    board_surface, board, placement_squad,
                    placing_models=(setup_controller.placing_models
                                    if setup_controller.is_partial else None),
                )
        # WHICH MODELS THE BASE-CONTACT HOUSE RULE HAS FROZEN. Drawn
        # unconditionally at frame-body indent, the pinned pattern for a
        # view-level control (Fehlerklasse 15): it self-gates on the move mode,
        # so no state branch can get between the rule and its own feedback. A
        # model that simply will not pick up is indistinguishable from a stuck
        # drag without this.
        renderer.draw_frozen_models(
            board_surface, board,
            base_contact.frozen_models(movement_controller.selected_squad,
                                       state.tokens, movement_controller.move_mode))

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
        # Death Trap's operation markers. Drawn HERE, in the live pass, rather
        # than on the cached static terrain layer: that layer is keyed on the
        # identity and length of the terrain list, so an area becoming trapped
        # mid-battle would never invalidate it. Without a marker the board
        # simply does not say which ruins are trapped, and the mission is
        # unplayable by eye.
        renderer.draw_terrain_markers(
            board_surface, board,
            primary_mission_controller.trapped_areas_on_board(), label="TRAPPED",
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
        # The units a pending decision can be answered by clicking. Same rings
        # as Fire Overwatch's, because that is the look the request named.
        # Derived ONCE for the whole frame's drawing: the rings here, the left
        # panel's screen and the decision overlay's stand-aside are three views
        # of one fact and must not be able to disagree.
        frame_unit_pick = board_unit_pick()
        # Derived fresh each frame for the same reason board_unit_pick() is:
        # resolving one allocation can open the next within a single event.
        frame_damage_pick = damage_pick.pending(damage_choice_controllers, human_players)
        # WHAT the rule being answered actually says, for the right panel.
        # User: "immer wenn ich aufgefordert werde durch eine Fähigkeit etwas
        # auf dem Spielfeld auszuwählen... schreibe die Fähigkeit Regel mit in
        # die rechte Spalte, sonst weiß ich gar nicht was ich da auswähle."
        #
        # Only for a BOARD pick, which is the one prompt shape that draws no
        # overlay at all (it would cover the units being clicked) - every other
        # decision already puts its full text on screen in the overlay.
        #
        # The candidate rules are the DECIDING player's own units plus the ones
        # being offered: the ability doing the asking is nearly always the
        # asker's (Living Lightning is the Plasmancer's), but a couple read off
        # the target instead. game/prompt_rule.py caches, so this costs one
        # lookup per prompt rather than one per frame.
        frame_decision_rule = None
        if frame_unit_pick is not None:
            _rule_owner = decision_manager.player
            _rule_entry = (army_lists.get(armies[_rule_owner])
                           if armies.get(_rule_owner) else None)
            if _rule_entry is not None:
                _rule_squads = [s for s in state.all_squads() if s.owner == _rule_owner]
                _rule_squads.extend(frame_unit_pick.squads)
                _rule = prompt_rule.for_prompt(
                    frame_unit_pick.prompt, _rule_squads,
                    _rule_entry.faction_keyword, _rule_entry.detachments)
                if _rule.blocks:
                    frame_decision_rule = _rule
        renderer.draw_shoot_targets(
            board_surface, board, unit_pick.target_models(frame_unit_pick, state.tokens))
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
        renderer.draw_damage_choice_highlight(board_surface, board, khaines_vengeance_controller.pending_damage_choice)
        # The six mortal-wound carriers - see their branches in the event
        # chain. A blocked-on choice that is never drawn is the same hang with
        # a better ending: the board would not say which models are pickable.
        renderer.draw_damage_choice_highlight(board_surface, board, living_lightning_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, matter_absorption_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, crimson_harvest_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, eater_plague_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, kroot_linebreakers_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, crushing_strides_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, grenade_pack_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, grav_inhibitor_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, flickerjump_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, deadly_demise_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, transport_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, crushing_impact_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, fall_back_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, deadly_vectors_controller.pending_damage_choice)
        # Without these four the choice is pending, the AI is paused on it and
        # the board shows nothing - the human is being waited on with no way to
        # tell. Same list as the click branches above; section 6 of
        # test_event_chain_wiring.py requires the two lists to agree.
        renderer.draw_damage_choice_highlight(board_surface, board, lethal_ichor_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, spore_laced_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, sickening_impact_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, internal_grenade_racks_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, wraith_form_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, drakolithe_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, harvester_of_souls_controller.pending_damage_choice)
        renderer.draw_damage_choice_highlight(board_surface, board, monofilament_snare_controller.pending_damage_choice)
        renderer.draw_assigning_model_highlight(board_surface, board, fight_assigning_model)
        renderer.draw_assigning_model_highlight(board_surface, board, shoot_assigning_model)
        renderer.draw_status_labels(board_surface, board, status_by_token)
        renderer.draw_selection(board_surface, board, movement_controller.selection)
        renderer.draw_forbidden_engagement_ranges(board_surface, board, movement_controller, state.tokens)
        renderer.draw_move_range(board_surface, board, movement_controller)
        renderer.draw_move_feedback(board_surface, board, movement_controller, input_manager.dragging_token)
        renderer.draw_measure_tool(board_surface, board, input_manager)
        # Unconditionally per frame, at frame-body indent - the pinned pattern
        # for a view-level control in this chain. The method self-gates on
        # line_drag_active, so there is nothing here for a state branch to get
        # between.
        renderer.draw_line_drag(board_surface, board, input_manager)

        # Später-Liste (Kamera-Scrolling/Viewport): board_surface itself was
        # just drawn at full (supersampled) native resolution, completely
        # unaware of zoom/pan (see the comment where it's created, above) -
        # this is the one place that actually applies the camera, by scaling
        # whichever native sub-rect it currently selects into the screen's
        # board area. smoothscale() (not the faster nearest-neighbor
        # scale()) is deliberate - User report ("alles ist total verpixelt,
        # wenn ich reinzoome"): if zoom ever pushes past what the render
        # resolution actually has real detail for, this turns the remainder
        # into a soft blur instead of hard blocky squares - profiled as
        # costing no more than scale() would here, so there's no performance
        # tradeoff in preferring it. Since the resolution became derived
        # (game/render_resolution.py) that case no longer arises within the
        # camera's own zoom range at all; this only still runs when zooming
        # OUT, where it is a downscale.
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
        board_surface.set_clip(None)
        camera_view = board_surface.subsurface(board_clip)
        dest = camera.dest_rect()
        if camera_view.get_size() == (dest.width, dest.height):
            # Exactly 1:1 - the normal case at MAX_ZOOM now that the render
            # resolution is derived for it. smoothscale() at 1:1 is not free
            # (~1.8ms on a full-screen board area), and it is pure cost:
            # there is nothing to resample.
            screen.blit(camera_view, (board_rect_screen.x + dest.x, board_rect_screen.y + dest.y))
        else:
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
            # Appended BY KEYWORD: this call is POSITIONAL up to
            # battle_focus_pool, and inserting a parameter mid-signature
            # has silently shifted every argument after it before.
            sudden_storm_controller=sudden_storm_controller,
            conquering_tyrant_controller=conquering_tyrant_controller,
            hungry_void_controller=hungry_void_controller,
            # Death Lord's Chosen - the three a human buys proactively.
            blooming_pestilence_controller=blooming_pestilence_controller,
            grim_reapers_controller=grim_reapers_controller,
            mortarions_teachings_controller=mortarions_teachings_controller,
            proactive_stratagems=proactive_stratagems,
            # Rangers' Path of the Outcast: its reactive move needs its OWN
            # Confirm/Cancel, or the generic ones leave turn_tracker.
            # active_player stranded on the reacting player - see the branch in
            # _draw_movement_ui().
            path_of_the_outcast_controller=path_of_the_outcast_controller,
            fire_and_fade_controller=fire_and_fade_controller,
            chronometron_controller=chronometron_controller,
            evasion_engrams_controller=evasion_engrams_controller,
            overflight_controller=overflight_controller,
            higher_duty_controller=higher_duty_controller,
            warhost_fire_and_fade_controller=warhost_fire_and_fade_controller,
            targeting_array_controller=targeting_array_controller,
            # An open "click a unit on the board" request from a Secondary
            # Mission owns the panel while it lasts - it is the only place that
            # can name WHICH objective is being decided.
            secondary_mission_controller=secondary_mission_controller,
            primary_mission_controller=primary_mission_controller,
            unmodified_six_controller=unmodified_six_controller,
            # Rule 01.02.03's model return, which reuses the Set Up flow -
            # appended by keyword like everything after fate_dice_pool.
            return_placement_controller=return_placement_controller,
            unit_pick=frame_unit_pick,
            damage_pick=frame_damage_pick,
            # "WHY YOU ARE CHOOSING": the printed rule behind a board
            # pick. It lived in the right panel, which is the emptier
            # column - but the question is already in THIS one, and the
            # user asked for it to follow ("'why you are choosing' soll
            # in die linke spalte, nicht rechts").
            decision_rule=frame_decision_rule,
        )
        # Drawn after the left panel itself (so their expanded/slid-out
        # state renders on top of the board, not underneath the panel) but
        # anchored off left_panel_rect - see MissionCardsOverlay's docstring.
        mission_cards_overlay.draw(screen, left_panel_rect, mission_controller,
                                   secondary_mission_controller,
                                   primary_controller=primary_mission_controller)
        # Appended and passed by keyword: this call site is positional up to
        # fate_dice_pool, and the tests that drive this panel are too.
        game_status_panel.draw(screen, right_panel_rect, turn_tracker, command_points, mission_controller,
                               battle_focus_pool, fate_dice_pool,
                               player_factions=current_player_factions())
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
            or picked_reserve_squad is not None
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
            dragging_squad=picked_reserve_squad, visible=reserves_panel_visible,
            # Rule 15.07: reserves_to_show is already narrowed down to the
            # ONE squad this Rapid Ingress window is for in that case - it
            # must stay visible/draggable regardless of which Player 1/
            # Player 2 tab happens to be selected, so the panel's own
            # owner filter is switched off for exactly that case.
            filter_by_owner=rapid_ingress_controller.pending_squad is None,
            # Rule 03.01: which card the player picked out of the pool. This
            # strip is where that pick happens and it had no way to show it -
            # the chosen card looked exactly like its neighbours.
            selected_squad=pregame_controller.selected_unit,
        )
        if picked_reserve_squad is not None:
            renderer.draw_reserve_drag_ghost(screen, picked_reserve_squad, pygame.mouse.get_pos())
        # The battle's progress in its own full-width row at the top of the
        # window - the round number that used to be a line in the Game Status
        # panel. See game/ui/round_progress_bar.py for what it shows, and for
        # why it owns a row instead of being drawn over the board.
        round_progress_bar.draw(screen, window_width, turn_tracker,
                                current_player_factions())
        # DIRECTLY AFTER the bar, and that order is the decision: PlayerBanner
        # claims this same strip (full window width) whenever it has a blocking
        # warning to show - "Regaining Coherency", a mandatory Battle-Shock
        # roll - and draws nothing at all otherwise. Those two stop the game
        # until they are answered, so for the moment they are up they outrank a
        # progress readout and are allowed to cover it.
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
            screen, dice_manager,
            selecting_die=(command_reroll_controller.selecting_die
                           or unmodified_six_controller.selecting_die
                           or targeting_array_controller.selecting_die),
            bounds_rect=board_rect_screen,
            suppressed=bool(_front_notice()),
        )
        # ONE modal at a time. User: "momentan kommt das Overlay, dass ich jetzt
        # am Zug bin, und das Overlay mit den Missionen gleichzeitig. Ich
        # moechte keine gleichzeitigen Overlays. Das soll wieder nacheinander
        # kommen." Every one of these is a full-screen dimmed, must-click-away
        # box, and the event chain above already hands clicks to exactly one of
        # them (the first pending branch wins) - so drawing the others behind
        # it only ever showed boxes nobody could answer yet, peeking out from
        # behind the one that had focus. Drawing just the front-most makes the
        # picture match the input priority: dismiss it, and the next appears.
        _notice = _front_notice()
        if _notice is not None:
            _notice.draw(screen)
        else:
            # Same reasoning one tier down: a decision is only clickable once
            # every notice is gone, so it waits its turn too.
            decision_overlay.draw(screen, decision_manager, state.all_squads(),
                                  board_pick=frame_unit_pick is not None)

        # POLLED, never a chain branch - the card is a VIEW, and every view
        # control in this loop is polled for the reason CLAUDE.md's
        # Fehlerklasse 15 records five times over (see update_hover()).
        ctrl_held = pygame.key.get_mods() & (pygame.KMOD_LCTRL | pygame.KMOD_RCTRL)
        _datacard_token = input_manager.hovered_token
        _modal_up = (
            decision_manager.is_pending or stratagem_notice_overlay.is_pending
            or mission_draw_overlay.is_pending or waaagh_notice_overlay.is_pending
            or turn_start_overlay.is_pending or turn_plan_overlay.is_pending
            or fight_warning_overlay.is_pending or army_rules_overlay.is_pending
            or unit_stats_overlay_view.is_pending
            or game_menu.is_pending
        )
        # The Stratagem tooltip: rest on a Stratagem button and its printed
        # WHEN/TARGET/EFFECT appear. POLLED beside the datacard, never as a
        # chain branch, for the reason that card's own update_hover() writes
        # out (Fehlerklasse 15) - and drawn HERE rather than inside the panel
        # because the mission strip slides out over the panel's edge and would
        # paint across a box drawn earlier in the frame.
        _tip_name = action_panel.update_tooltip(
            pygame.mouse.get_pos(), any(pygame.mouse.get_pressed()),
            pygame.time.get_ticks(),
        ) if not _modal_up else None
        if _tip_name:
            # WHOSE Stratagem it is comes from the unit the panel is drawing
            # for, not from whose turn it is: the reactive ones (Fire Overwatch,
            # Heroic Intervention, the Aeldari Fate dice) are bought during the
            # OPPONENT's turn, and looking the text up in the wrong army's
            # detachments would find nothing exactly when it is most wanted.
            _tip_squad = movement_controller.selected_squad
            _tip_owner = _tip_squad.owner if _tip_squad is not None else turn_tracker.turn_owner
            _tip_entry = (army_lists.get(armies[_tip_owner])
                          if armies.get(_tip_owner) else None)
            if _tip_entry is not None:
                stratagem_tooltip.draw(
                    screen, _tip_entry.faction_keyword, _tip_entry.detachments,
                    _tip_name, pygame.mouse.get_pos(),
                    anchor_rect=action_panel.tooltip_rect,
                )
        if (
            decision_manager.is_pending or stratagem_notice_overlay.is_pending
            or mission_draw_overlay.is_pending or waaagh_notice_overlay.is_pending
            or turn_start_overlay.is_pending or turn_plan_overlay.is_pending
            or fight_warning_overlay.is_pending
        ):
            # A modal is up. The card is drawn over the board, so it would sit
            # on top of the very prompt that has to be answered first.
            _datacard_token = None
        if army_rules_overlay.is_pending or unit_stats_overlay_view.is_pending:
            # A reader is drawn over the board, so the hover card would sit
            # on top of the very thing that was just opened.
            _datacard_token = None
        if game_menu.is_pending:
            # Same again for the menu, which is drawn over everything.
            _datacard_token = None
        if unit_datacard.update_hover(
            _datacard_token, pygame.mouse.get_pos(), ctrl_held,
            any(pygame.mouse.get_pressed()), pygame.time.get_ticks(),
        ):
            unit_datacard.draw(
                screen, _datacard_token, pygame.mouse.get_pos(),
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
            # wait is what a hung game looks like; animated dots (plus the
            # badge's own pulse) are the signal that the window is alive and
            # something is still happening.
            #
            # Panels dimmed for the same reason as the thinking flash above:
            # this is the AI's turn starting, and nothing in either column is
            # yours to press until the plan lands.
            dots = "." * (1 + int(time.monotonic() * 2) % 3)
            ai_busy_badge.draw(
                screen, f"Player 2 is planning its turn{dots}",
                board_rect_screen, dim_rects=ai_busy_dim_rects, pulse=True,
                avoid_rects=(dice_panel.last_backdrop_rect,),
            )
        # THE AI SWITCH, drawn every frame in BOTH states - it is the control
        # as well as the indicator (user: "auesserdem waere ein toggle in der
        # oberflaeche gut fuer den KI Modus. vielleicht dort, wo jetzt der rote
        # punkt ist"). Its predecessor was a red dot that only existed while
        # the mode was ON, so there was nothing to click to turn it back on.
        #
        # Deliberately NOT inside the `if ai_memory.is_planning` chain above:
        # those are transient "the AI is busy" badges, this is a persistent
        # mode.
        #
        # NO avoid_rects any more: the MENU button used to own this corner and
        # the switch stepped down out of its way, and the button has moved into
        # the right panel's header row. So the switch takes the corner itself
        # and stops moving - measured clear of the dice panel and of every die
        # in it at 1280/1366/1600/1920 (test_game_menu.py pins the arithmetic),
        # and a control that stands still is worth more than a tight margin.
        # draw_ai_mode_toggle() keeps its avoid_rects parameter for the next
        # thing that shares this corner; the tests exercise it at a blocker of
        # their own, so it cannot rot while it ships inert.
        #
        # Drawn here, over the board and after the panels, so the rect handed
        # back is exactly what the event loop hit-tests.
        ai_toggle_rect = draw_ai_mode_toggle(
            screen, board_rect_screen, ai_mode.enabled(), ai_toggle_font,
        )
        # ...and the Unit Statistics button immediately to its left, placed
        # from the rect the switch just reported rather than measured out of
        # the board corner a second time. Drawn in the same pass so it shares
        # the switch's standing over the dice panel's backdrop padding.
        stats_button_rect = unit_stats_overlay.draw_button(
            screen, board_rect_screen, ai_toggle_font, ai_toggle_rect,
            mouse_pos=pygame.mouse.get_pos(),
        )

        # LAST, over everything including the notices: it is the one overlay the
        # player opened deliberately, and it owns every event while it is up
        # (see the branch at the top of the event loop), so nothing behind it
        # can be acted on anyway.
        army_rules_overlay.draw(screen)
        # Same standing, same reason: opened deliberately, owns every event
        # while it is up.
        unit_stats_overlay_view.draw(screen)

        # The MENU button, and then the menu itself - the very last two things
        # in the frame. The button is hidden while either overlay is up: it
        # would be drawn on top of the scrim that is covering the panel it
        # belongs to, and its click is not offered there either (see the
        # pre-chain block), so drawing it would promise a control that does
        # nothing.
        #
        # Drawn LAST also means it stays bright while the AI-busy dim covers
        # the rest of the right panel (ai_busy_dim_rects), and that is wanted
        # rather than tolerated: a stuck prompt is precisely the state a player
        # most wants to reach the menu from.
        if (not game_menu.is_pending and not army_rules_overlay.is_pending
                and not unit_stats_overlay_view.is_pending):
            game_menu.draw_button(screen, right_panel_rect, pygame.mouse.get_pos())
        # LAST of all, over every notice and both readers: it is the way out of
        # the game, so nothing may cover it.
        if game_menu.is_pending:
            game_menu.draw(screen, pygame.mouse.get_pos())

        pygame.display.flip()
        clock.tick(config.FPS)

    game_log.close()
    # This battle's statistics ledger goes with it. main() is ONE BATTLE and
    # run() may call it again in the same process (the menu's "New Game"), so
    # leaving it published would let the next battle open its resume on the
    # last one's numbers.
    battle_stats_module.CURRENT = None
    # What the APPLICATION should do next - QUIT, or NEW_GAME when the in-game
    # menu asked for a fresh battle. run() loops on this; a harness calling
    # main() directly is free to ignore it, exactly as it ignored the None
    # this used to return.
    return outcome


ORKS_ARMY = army_lists.ORKS_ARMY
NECRONS_ARMY = army_lists.NECRONS_ARMY
ARMY_KEYS = sorted(army_lists.BY_KEY)


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="WH40k board")
    parser.add_argument(
        "--map", dest="map_key", default=None,
        help='which battlefield to play on: "map1" (44"x60" portrait), "map2" '
             '(60"x44" landscape) or "map3" (60"x44", corner deployment). The bare number '
             'works too ("--map 2"). Naming one here SKIPS the map selection screen; '
             "without it, that screen decides, falling back to config.MAP.",
    )
    parser.add_argument(
        "--no-map-select", dest="map_select", action="store_false", default=None,
        help="skip the map selection screen and play on config.MAP (or --map). "
             "What the headless harnesses use.",
    )
    parser.add_argument(
        "--biome", dest="biome", default=None, choices=biomes.keys(),
        help="which biome the battlefield is painted in (game/biomes.py). Purely "
             "cosmetic - it swaps the ground picture and the two terrain cover "
             "textures and nothing else. Unlike --map this does NOT skip the map "
             "selection screen, it only seeds which biome that screen opens on; "
             "without it, config.BIOME does.",
    )
    parser.add_argument(
        "--army1", dest="player1_army", default=None, choices=ARMY_KEYS,
        help="which army list Player 1 (the human) fields. Naming BOTH --army1 and "
             "--army2 skips the army selection screen; naming one seeds it. Without "
             "either, that screen decides, falling back to config.PLAYER1_ARMY.",
    )
    parser.add_argument(
        "--army2", dest="player2_army", default=None, choices=ARMY_KEYS,
        help="which army list Player 2 (the AI) fields. The human picks this on the "
             "selection screen too - the AI never chooses its own list. Naming BOTH "
             "--army1 and --army2 skips that screen; without them it decides, falling "
             "back to config.PLAYER2_ARMY.",
    )
    parser.add_argument(
        "--no-army-select", dest="army_select", action="store_false", default=None,
        help="skip the army selection screen and field whatever config.PLAYER1_ARMY/"
             "PLAYER2_ARMY (or --army1/--army2) say. What the headless harnesses use.",
    )
    parser.add_argument(
        "--no-deployment", dest="pregame", action="store_false", default=None,
        help="skip rule 03.01's pre-game sequence and start from the legacy "
             "already-deployed scene (the hand-tuned positions in game/maps.py). "
             "Without this, config.PREGAME_DEPLOYMENT decides.",
    )
    parser.add_argument(
        "--no-menu", dest="start_menu", action="store_false", default=None,
        help="skip the game menu and go straight to picking a battlefield.",
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
    if _args.map_select is not None:
        config.MAP_SELECT = _args.map_select
    # Seeds the biome, deliberately WITHOUT skipping the map screen the way
    # --map does. The two are not the same kind of answer: --map answers that
    # screen's question, while a biome is a second, cosmetic setting the same
    # screen happens to carry - so naming one still leaves the battlefield to
    # be picked, and the buttons open on what was named.
    if _args.biome is not None:
        config.BIOME = _args.biome
    if _args.player1_army is not None:
        config.PLAYER1_ARMY = _args.player1_army
    if _args.player2_army is not None:
        config.PLAYER2_ARMY = _args.player2_army
    if _args.army_select is not None:
        config.ARMY_SELECT = _args.army_select
    # Naming BOTH lists is an answer, not a preference, so it skips the screen
    # that would ask the same question again - the same meaning --map has for
    # the map screen. Naming only one still leaves a question to ask, so the
    # screen runs and opens on what was named.
    if _args.player1_army is not None and _args.player2_army is not None and _args.army_select is None:
        config.ARMY_SELECT = False
    if _args.pregame is not None:
        config.PREGAME_DEPLOYMENT = _args.pregame
    _map_key = _args.map_key
    if _args.load_scene is not None:
        config.LOAD_SCENE = _args.load_scene
        # The snapshot knows which board it was taken on, so --load does not
        # also need --map. An explicit --map still wins, and main() then
        # refuses the mismatch rather than placing the army on the wrong board.
        if _map_key is None:
            _map_key = scene_io.map_key_in(_args.load_scene)
    if _args.start_menu is not None:
        config.START_MENU = _args.start_menu
    run(map_key=_map_key)
