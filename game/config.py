# Which battlefield main() sets up (game/maps.py). "map1" is the original
# 44"x60" portrait board, "map2" the 60"x44" landscape one. Starting main.py
# with no arguments (the normal way to launch it) uses whatever is set here;
# `python main.py --map 1` overrides it for one run without editing this.
MAP = "map2"

# WHICH BIOME the battlefield is painted in: "city", "desert" or "forest"
# (game/biomes.py). Purely cosmetic - it swaps the ground picture and the two
# terrain cover textures and nothing else; no rule reads any of them, and the
# board, zones, terrain and objectives are identical whichever one is set.
#
# This is the DEFAULT the map selection screen opens on, not the final answer:
# the three buttons at the top of that screen (game/ui/map_select.py) write
# whatever is clicked back over it, the same way ARMY_SELECT's screen writes
# PLAYER1_ARMY/PLAYER2_ARMY. `python main.py --biome forest` sets it for one
# run without editing this, and with MAP_SELECT off it is the whole answer.
#
# "desert" is the default because its three files are byte-identical to the
# three that used to sit loose in Sprites/ - so an untouched setup renders
# exactly what it rendered before biomes existed.
BIOME = "desert"

# WHICH ARMY LIST EACH PLAYER FIELDS: "aeldari", "orks", "necrons" or "tau" (see
# game/army_lists.py, which holds all four and can build any of them for
# either player). `python main.py --army1 orks --army2 aeldari` overrides both
# for one run without editing this.
#
# These are the DEFAULTS the selection screen opens on, not the final answer:
# with ARMY_SELECT below on, whatever the player picks there is written back
# over them at startup (army_lists.apply_to_config()).
#
# A per-player setting rather than something derived from the units, for the
# same reason SEER_COUNCIL_PLAYERS below is: this decides which units get
# BUILT, so there is nothing on the board to infer it from yet.
#
# No list is ever deleted - every datasheet, ability and stratagem of all
# four is still built and still tested. Only who turns up by default moves.
PLAYER1_ARMY = "aeldari"
PLAYER2_ARMY = "necrons"

# Whether the battle opens with the map selection screen
# (game/ui/map_select.py): the battlefield picked from large tiles showing each
# map's own rendered picture, before the army lists and long before rule
# 03.01's pre-game sequence.
#
# It runs FIRST because everything downstream depends on it - board size,
# deployment zones and terrain (User:
# "Vor der Fraktion würde ich jetzt allerdings gerne noch die Map auswählen").
#
# Turned OFF by the headless harnesses for the same reason ARMY_SELECT below
# is: nothing there answers a click. `python main.py --no-map-select` does the
# same for one run, and naming a map with `--map` skips it too.
MAP_SELECT = True

# Whether the battle opens with the army selection screen
# (game/ui/army_select.py): each player's list picked from large tiles, one
# player after the other, before rule 03.01's pre-game sequence starts.
#
# THE HUMAN PICKS BOTH. User: "Aber ich wähle für die KI. Die KI soll nicht
# selber wählen." - so this is two steps of one screen, not a player step and
# an AI step; Player 2's list is assigned to the AI, never chosen by it.
#
# The lists themselves stay PREDEFINED (user: "Die Listen sollen auch erstmal
# predefined sein. Also, wir brauchen noch keine Listenbaukosten. Das kommt
# erst viel später"). This screen chooses WHO PLAYS WHICH of the predefined
# lists in game/army_lists.py; it is not the army-building flow on CLAUDE.md's
# Später-Liste, and it costs nothing.
#
# Turned OFF by the headless harnesses (selfplay.py, smoke_*.py), which drive
# main()'s real loop with synthetic input and have no one to answer a screen
# that waits for a click - they run on the settings above instead.
# `python main.py --no-army-select` does the same for one run.
ARMY_SELECT = True

# Whose army is an AWAKENED DYNASTY detachment (the Necron detachment this
# build implements). Like SEER_COUNCIL_PLAYERS below, this CANNOT be derived
# from the units: a detachment is a list-building declaration, and a Necron
# unit looks identical whichever detachment it was taken in.
#
# Player 2 by default, because that is who fields the Necron list when
# PLAYER2_ARMY is "necrons" - it is inert for an Ork army, since every gate
# also checks that the unit is actually a NECRONS one.
AWAKENED_DYNASTY_PLAYERS = ("Player 2",)

# Which players field the Death Guard detachment "Death Lord's Chosen", whose
# rule is Deadly Vectors (game/deadly_vectors.py) and whose six Stratagems all
# gate on game/death_lords_chosen.py's stratagem_target_ok().
#
# Empty by default, unlike the two settings around it: Death Guard is not
# either player's default army, so nobody has this detachment until
# army_lists.apply_to_config() writes it from the chosen lists. Note the
# contrast with the ARMY rule next door - Nurgle's Gift is derived from the
# UNITS (nurgles_gift.qualifying_players()), because an army rule is a
# property of the army, while a detachment is a list-building declaration that
# no amount of looking at the board can recover.
DEATH_LORDS_CHOSEN_PLAYERS = ()

# --- T'au Empire detachments ---------------------------------------------
# One tuple per detachment, same owner-keyed shape as the two settings above,
# all written by game/detachments.py's apply_to_config() from the DETACHMENTS
# THE CHOSEN ARMY LISTS DECLARE. There is no detachment-selection screen: a
# detachment is part of a written list, not something picked at the table.
#
# These did not exist while Retaliation Cadre was the faction's only modelled
# detachment: its Bonded Heroes gated on the BATTLESUIT keyword alone and its
# six Stratagems on T'AU EMPIRE, so - like War Horde - there was nothing to
# declare, and both game/retaliation_cadre.py and game/army_lists.py said so
# explicitly, the former ending "Revisit once a real detachment-selection
# system exists". Adding Kauyon and the rest is that moment: without a flag
# per detachment, Bonded Heroes would keep applying to EVERY Battlesuit of
# EVERY owner, including both sides of a T'au mirror.
#
# ALL EMPTY by default, and that is not a placeholder: neither default army is
# T'au, so nobody holds a T'au detachment until apply_to_config() writes one
# from the lists. It rewrites every one of these from scratch, so switching
# list really takes the old detachments away. An army may hold SEVERAL of them
# at once - see game/detachments.py's Detachment Points budget.
RETALIATION_CADRE_PLAYERS = ()
KAUYON_PLAYERS = ()
MONTKA_PLAYERS = ()
EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS = ()
ADVANCED_ACQUISITION_CADRE_PLAYERS = ()
AUXILIARY_CADRE_PLAYERS = ()


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

# How sharp the board looks when zoomed in. The board is drawn onto its own
# offscreen Surface and Camera scales the visible part of it to fill the
# on-screen board area (see game/camera.py), so that Surface's resolution is
# what decides whether zooming in shows real detail or an upscaled guess.
#
# This used to be a hand-tuned RENDER_SUPERSAMPLE = 2.5 multiplier on
# PIXELS_PER_INCH, from when there was one fixed board size. It is now
# DERIVED per map and per screen instead - see game/render_resolution.py for
# why a single constant cannot be right for more than one map (measured: the
# same 2.5 left 27% of the shown pixels invented on map2, 46% on map1 and
# 64% on the old 30x30 test board, because a smaller board gets magnified more).
#
# What stays configurable is the ceiling. The per-FRAME cost follows the
# visible screen area (main.py clips the board draw to the camera's visible
# rect), but MEMORY follows the full board: the board Surface, the cached
# static terrain layer and the placement overlay are each board-sized at 4
# bytes a pixel, so this budget is worth ~3x itself in RAM at peak. 20 MP
# renders 1920x1200 with zero upscaling at max zoom on all three maps;
# lowering it trades some max-zoom sharpness back for memory.
RENDER_MAX_PIXELS = 20_000_000

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
# Force/Onslaught (see game/battle_focus.py). Strike Force is the bracket every
# list in this project falls in - they run 1890 to 2030 pts (game/army_lists.py)
# and Strike Force is the 2000-pt game. There is no army-building flow to derive it
# from (CLAUDE.md's deferred list), so it is a setting rather than a
# consequence; anything unrecognised falls back to strike_force rather than to
# zero tokens, so a typo cannot silently switch the army rule off.
BATTLE_SIZE = "strike_force"

# Which players field the Aeldari Seer Council detachment, whose rule Strands
# of Fate gives them a Fate dice pool (see game/strands_of_fate.py).
#
# Set to Player 1 when its roster became Aeldari. The supplied list did not
# name a detachment, so this is a judgement call rather than a transcription -
# but the army is two Warlock Conclaves, a Farseer and Eldrad Ulthran, which is
# what Seer Council is for, and with it empty all six of its stratagems plus
# the Fate dice pool stay unreachable. One line to revert if the list turns out
# to be a different detachment.
#
# Unlike the ASURYANI army rule next door, this genuinely CANNOT be derived: a
# detachment is a list-building declaration, and there is nothing on a unit to
# infer it from (game/factions/detachment.py is deliberately pure data). Same
# owner-keyed shape as WALL_CROSSING_PLAYERS and SPREAD_LIMIT_PLAYERS above.
SEER_COUNCIL_PLAYERS = ("Player 1",)

# The seven further Aeldari detachments whose RULES are modelled. Same shape
# and same reason as SEER_COUNCIL_PLAYERS above: a detachment is a
# list-building declaration and cannot be inferred from any unit.
#
# All empty, and that is the whole story - the predefined Aeldari list fields
# Seer Council and nothing here changes that. Each rule is verified by fielding
# its detachment for one run, the same way the six T'au detachments are. Only
# game/detachments.py ever writes these, from scratch on every army choice, so
# switching list cannot leave a stale detachment live.
ASPECT_HOST_PLAYERS = ()
GUARDIAN_BATTLEHOST_PLAYERS = ()
WARHOST_PLAYERS = ()
WINDRIDER_HOST_PLAYERS = ()
SPIRIT_CONCLAVE_PLAYERS = ()
ARMOURED_WARHOST_PLAYERS = ()
PATH_OF_THE_OUTCAST_PLAYERS = ()

# Which players run the Tactical Secondary Mission card deck
# (game/secondary_missions.py) INSTEAD of the standard "No Mercy" Secondary.
# The Primary is untouched and stays the same for everyone.
#
# User: "Die Missionen sollen nur fuer mich gelten, fuer den menschlichen
# Spieler. Die KI soll ihre Standard-Mission erstmal behalten." So exactly one
# entry, the human. Same owner-keyed shape and the same justification as
# SEER_COUNCIL_PLAYERS above: which missions a player brought is a
# list-building declaration, and there is nothing on the board to infer it
# from - two identical armies can be running entirely different missions.
#
# THE HEADLESS HARNESSES SET THIS TO () - smoke_pregame.py, smoke_log_input.py,
# smoke_setup_screens.py, smoke_measure_tool.py and selfplay.py. The deck asks
# the human a question at the end of every one of their turns, and none of
# those harnesses answers a prompt that belongs to the human outside the
# pre-game (a documented limit, see CLAUDE.md) - so leaving it on would stall
# them on a decision nobody is there to make. test_secondary_missions.py has a
# source guard requiring all five, so a new harness cannot quietly forget.
SECONDARY_MISSION_CARD_PLAYERS = ("Player 1",)

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
