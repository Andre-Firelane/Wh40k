# Which battlefield main() sets up (game/maps.py). "map1" is the original
# 44"x60" portrait board, "map2" the 60"x44" landscape one. Starting main.py
# with no arguments (the normal way to launch it) uses whatever is set here;
# `python main.py --map 1` overrides it for one run without editing this.
MAP = "map2"

# Whether the battle opens with rule 03.01's real pre-game sequence
# (game/pregame.py): Declare Battle Formations -> roll-off -> alternating
# deployment -> roll-off for the first turn -> Resolve Pre-battle Abilities.
#
# False falls back to the legacy instant scene: every unit starts already
# deployed on the hand-tuned per-model coordinates in game/maps.py, embarked
# and reserved exactly as main.py's army build declares. That path is kept
# deliberately - every A/B measurement recorded in CLAUDE.md was taken against
# precisely that layout, selfplay.py's long-running baseline depends on it, and
# it is the quality benchmark the AI's own deployment gets compared against.
# `python main.py --no-deployment` overrides this for one run.
PREGAME_DEPLOYMENT = True

# A board position saved with F9 (game/scene_io.py) to open instead of setting
# up a fresh battle. Set by `python main.py --load scenes/<file>.json`; leave
# None for a normal start. Skips the pre-game sequence entirely - the snapshot
# already says where everything stands and whose turn it is.
#
# The point of it is the debugging loop: a reported failure is saved once and
# re-opened as often as needed, instead of being rebuilt by hand from the
# coordinates in the log - which is how every such bug has been reproduced so
# far, and which reliably leaves out the other units that were in the way.
LOAD_SCENE = None

# The board size of whichever map is selected. These two are WRITTEN at
# startup by game/maps.py's apply_to_config() - the values here are just
# map 1's, so that anything importing config without going through main()
# (tests, tools) still sees a sane board rather than None. Everything in the
# engine and the AI reads them as config.BOARD_WIDTH_IN at call time, which is
# what makes that late write work; don't rebind them with `from game.config
# import BOARD_WIDTH_IN`.
BOARD_WIDTH_IN = 44.0
BOARD_HEIGHT_IN = 60.0  # standard 2,000pt Strike Force table (44"x60"), 10th/11th edition
PIXELS_PER_INCH = 18  # lower than before (was 28, for the old 44"x30" board) so the taller window still fits on-screen

# Fullscreen is now the default display mode (User: "es wird zeit, einen
# vollbild modus einzuführen (default)") - the window fills the actual
# desktop resolution instead of a size computed from the board's own pixel
# dimensions; ESC quits while it's active (main.py). The board area's size
# no longer depends on PIXELS_PER_INCH at all (see main.py's letterboxing
# math) - only the ratio between BOARD_WIDTH_IN/HEIGHT_IN, LEFT_PANEL_WIDTH/
# RIGHT_PANEL_WIDTH/RESERVES_PANEL_HEIGHT below, and whatever the actual
# screen resolution turns out to be.
FULLSCREEN = True

# Später-Liste (Kamera-Scrolling/Viewport): the on-screen board area stays
# sized to PIXELS_PER_INCH (so the window itself doesn't change size), but
# main.py renders the board's own offscreen Surface at PIXELS_PER_INCH *
# RENDER_SUPERSAMPLE instead - extra detail for Camera to zoom into before
# it starts looking blocky (User report: "alles ist total verpixelt, wenn
# ich reinzoome"). Deliberately set equal to game.camera.MAX_ZOOM (2.5): at
# the camera's own maximum zoom, the native render resolution then exactly
# equals the screen's displayed resolution - genuinely crisp detail across
# the WHOLE 1x-2.5x zoom range, never just an upscaled blur/blocky guess
# beyond what's actually there. Raising this further only pays off if
# MAX_ZOOM also goes up - past that point it's wasted render cost for
# resolution the camera can never actually show.
#
# Profiled directly against the ~140-model demo army, worst case (a squad
# actively selected/moving, all range overlays active at once): 2.5x costs
# ~12ms/frame just for board rendering - more than 2x's ~8ms, but the
# game's overall per-frame cost turned out to already be dominated by
# unrelated, pre-existing per-frame recomputation elsewhere (~12ms on its
# own even with rendering stubbed out entirely - several controllers'
# eligible-target/choosable-model checks run unconditionally every frame,
# not just when their state is actually active) - i.e. this game was
# already well below a strict 60fps in this scene before touching
# RENDER_SUPERSAMPLE at all. Against that baseline, 2.5x's extra cost is a
# comparatively small fraction, and this is a turn-based tactics game, not
# an action game - occasional real-world framerates in the 35-45fps range
# for a full 140-model army remain entirely playable. Not fixing that
# separate, pre-existing overhead here - out of scope for a resolution bump.
RENDER_SUPERSAMPLE = 2.5

FPS = 60
BACKGROUND_COLOR = (22, 24, 28)  # dark battlefield background, subtle board guide lines drawn on top (see Renderer)

# --- House rule: crossing walls ------------------------------------------
# Rule 13.06 lets INFANTRY/BEASTS/SWARM/MOBILE models move horizontally
# through Dense terrain and nothing else. With this on, EVERY model may cross
# it, at a cost - a vehicle grinding over a low ruin wall rather than driving
# round the whole ruin.
#
# Who it applies to. The user's explicit decision after being asked: "die
# regeln die wir jetzt spielen sollen nur für die ki gelten. ich darf
# weiterhin nicht durch wände durch mit meinen fahrzeugen." So this is an AI
# handicap-remover, not a change to the game both sides play.
#
# The case for symmetry was put and turned down, and is recorded here because
# it is the thing to re-read if the balance ever looks off: every Dense feature
# on both maps is exactly 0.60" thick (measured, not assumed - min 0.60",
# median 0.60", max 0.60" across map 1's 28 and map 2's 14), so these are low
# walls rather than solid blocks and a vehicle grinding over one is not
# far-fetched for either side; and an asymmetric rule makes later balance
# observations harder to read, because a win or loss can always be attributed
# to the handicap. Set this to ("Player 1", "Player 2") to make it symmetric.
WALL_CROSSING_PLAYERS = ("Player 2",)
#
# Why it is worth having, measured over 1200 movement attempts on map 2 with
# identical start points (measure_wall_houserule.py): units that could not
# cross walls stalled on 4% of attempts, and the two 2.10"-based models
# (Kill Rig, Battlewagon) on 12%. With crossing allowed that goes to 0%, and
# - the genuinely surprising part - per-model "ended on top of another model"
# rejections fell from 4260 to 229, a 95% drop. Walls funnel a whole army
# through the same few gaps, and the pile-up at those gaps was most of the
# "models get in each other's way" problem rather than a separate one.
#
# NOT lifted: rule 13.05's "may not END its move on Dense terrain"
# (game/squad.py's model_terrain_violation), which stays in force for
# everyone. Measured separately and it buys almost nothing on its own -
# lifting it alone left the stall rate at 4% and the median move unchanged,
# because the AI's retry ladder was already finding another endpoint. It is
# the crossing that pays.
VEHICLES_CROSS_WALLS = True
# What crossing costs, deducted from the model's remaining move the moment a
# committed segment actually crosses (game/movement.py's _finalize_segment).
# Charged per crossing segment, and only to models rule 13.06 would otherwise
# have stopped - INFANTRY already cross for free and must not be billed.
#
# The user's own figure. Worth knowing what it costs: over the same 1200
# attempts, total progress toward the goal ran 9023" under current rules,
# 8407" with this toll and 10388" with no toll at all. That measurement
# charged pessimistically (whenever the straight line to the goal crossed a
# wall, whether or not the path taken did), so the real figure sits between
# the two - but the toll is the expensive half of the rule, not the cheap one.
WALL_CROSSING_COST_IN = 3.0

# --- House rule: the 9" spread limit -------------------------------------
# Rule 09.02's coherency has two halves in this engine: every model within 2"
# of another in a SINGLE connected group, and no two models more than
# MAX_SPREAD_IN apart. This names who the second half applies to; the first
# half applies to everyone and is not configurable, because it is the half
# that actually stops a unit being used as a board-wide screen.
#
# The user's decision, asked for explicitly: "ich würde die 9\" regel für die
# KI aufheben. sie ist wichtig, damit menschen sie nicht ausnutzen, um screens
# über die ganze map zu ziehen, aber die ki würde sowas ja nicht machen." Same
# shape and same reasoning as WALL_CROSSING_PLAYERS above - an AI
# handicap-remover, not a change to the game the human plays. Set this to
# ("Player 1", "Player 2") to make it symmetric again.
#
# Why it was worth doing, measured before the change. Across four real games,
# EVERY rejected AI Normal Move failed on coherency and nothing else - not one
# on terrain, model overlap or the board edge - and this half was in a good
# share of them. The 20-strong Boyz mob is why: it deployed at 8.82" of the
# 9.0" limit (98%), while every other unit sat at 24-74%, so it had no slack
# at all and any per-model movement broke the limit immediately. In the
# crowded harness it made 21% of the progress it could have made, the worst
# figure of the whole roster.
#
# What stops the AI sprawling once the limit is gone, since that is the real
# question: nothing about the limit was doing that work in the first place.
# ai/agent_driver.py's _tightening_factor() actively pulls a stretched
# formation back in, and formation_layout.pack_positions() builds blobs rather
# than lines - compactness comes from the generators, and it is a goal in its
# own right (small footprints conceal better and leave room for the
# neighbours), not a side effect of a prohibition.
SPREAD_LIMIT_PLAYERS = ("Player 1",)

# Battle size, which today is read by exactly one rule: the Aeldari army rule
# Battle Focus hands out 2/4/6 tokens per battle round for Incursion/Strike
# Force/Onslaught (see game/battle_focus.py). Strike Force is the bracket this
# project's demo armies fall in - Player 1 is 1535 pts, Player 2 1935 pts, and
# Strike Force is the 2000-pt game. There is no army-building flow to derive it
# from (CLAUDE.md's deferred list), so it is a setting rather than a
# consequence; anything unrecognised falls back to strike_force rather than to
# zero tokens, so a typo cannot silently switch the army rule off.
BATTLE_SIZE = "strike_force"

# Which players field the Aeldari Seer Council detachment, whose rule Strands
# of Fate gives them a Fate dice pool (see game/strands_of_fate.py). Empty
# until an army is actually built with it, which is why the rule is inert
# rather than wrong today.
#
# Unlike the ASURYANI army rule next door, this genuinely CANNOT be derived: a
# detachment is a list-building declaration, and there is nothing on a unit to
# infer it from (game/factions/detachment.py is deliberately pure data). Same
# owner-keyed shape as WALL_CROSSING_PLAYERS and SPREAD_LIMIT_PLAYERS above.
SEER_COUNCIL_PLAYERS = ()

AI_MODEL = "claude-haiku-4-5"
# The strategic planning phase's model (ai/claude_agent.py's plan_turn()) -
# ONE call per the AI's own turn, against dozens of per-decision AI_MODEL
# calls, so a stronger model here costs very little and buys quality exactly
# where it turned out to matter most.
#
# Raised from AI_MODEL (Haiku) to Sonnet after the planner, not the tactical
# layer, was traced as the source of three separate user-reported problems in
# a row: units given "hold"/"screen" while standing 6.6" and 6.7" from an
# enemy they could have shot and charged, the Devilfish parked 29.7" from the
# fight, and two units garrisoning the same uncontested objective despite an
# explicit one-unit rule in the prompt. Each had already survived a
# prompt-only fix - the tactical layer was faithfully executing a plan that
# was simply too passive, which is a planning-quality problem, not an
# execution one.
AI_PLANNING_MODEL = "claude-sonnet-5"

LEFT_PANEL_WIDTH = 220
RIGHT_PANEL_WIDTH = 220

PANEL_BG_COLOR = (9, 14, 22)  # dark navy, matching the button/token sci-fi HUD theme (see game/ui/button_style.py)
PANEL_BORDER_COLOR = (55, 120, 165)  # cyan-blue, was flat gray
PANEL_TEXT_COLOR = (195, 225, 245)  # light cyan, was flat off-white
PANEL_HEADER_COLOR = (255, 215, 0)

FONT_NAME = None
FONT_SIZE = 19

# The log is a bottom-anchored strip in the right column. Raised 180 -> 240
# (a filtered log that shows ONE entry is not worth filtering, see
# game/ui/log_panel.py) and then 240 -> 480 on request.
#
# This is what the log WANTS, not what it gets: main() shrinks it whenever the
# Game Status panel above it needs the room, because the space that panel needs
# depends on what is in it (mission scores, CP) and 480 does not fit above a
# 768px-tall window at all. An earlier attempt derived the log's height from a
# one-off MEASUREMENT of the status panel - taken without a mission controller,
# so in the real game the log covered the "Next Phase" button and the phase
# could not be advanced. main() therefore clamps against that panel's ACTUAL
# button rect every frame instead of against any measured constant.
LOG_HEIGHT = 480

# Breathing room kept between the "Next Phase" button and the top of the log.
LOG_GAP_BELOW_STATUS_PANEL = 8

PLAYER_BANNER_HEIGHT = 30

# Raised from 110 (User: overhauled reserves panel now has its own header
# bar + Player 1/Player 2 tab buttons above the cards, see
# game/ui/reserves_panel.py - needs a bit more vertical room than the old
# plain title-and-cards layout to avoid squeezing the card text again).
RESERVES_PANEL_HEIGHT = 136
