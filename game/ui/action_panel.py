import pygame

from game import warhost_fire_and_fade
from game import enh_higher_duty
from game import windrider_overflight
from game import aura_ruler
from game import base_contact
from game import charge, config, consolidate, crushing_impact, epic_challenge, explosives, fall_back, fight, chronometron, fire_and_fade, firing_deck, formations, greater_good, loadout, movement, overwatch, path_of_the_outcast, pregame, setup, shooting, sprites
from game.ingress import SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN
from game.squad import is_at_half_strength
from game.turn import PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE, PHASE_FIGHT
from game.ui import button_style
from game.ui.rules_body import RulesBody
from game.ui.text_utils import draw_wrapped_text, wrap_text

BUTTON_HEIGHT = 32
BUTTON_MARGIN = 10
BUTTON_GAP = 8
TEXT_MARGIN = 10          # left inset for panel text (buttons use BUTTON_MARGIN)
ERROR_LINE_HEIGHT = 18

# The range ruler's radius radio (see game/aura_ruler.py). Four columns fits
# the eight radii into two rows inside a 220px panel: measured, the widest
# label ("36" at the button font) is 23px and a 4-column cell leaves 31px of
# text room, so nothing wraps. Rows are DERIVED from the list rather than
# written down, so a ninth radius cannot silently fall off the bottom.
RADIO_COLUMNS = 4
RADIO_HEIGHT = 26
RADIO_GAP = 4


def _radio_rows():
    """How many rows the radii need. Derived, so the strip grows with the list
    instead of the last radius falling off the bottom of the panel."""
    return -(-len(aura_ruler.RADII_IN) // RADIO_COLUMNS)
# "WHY YOU ARE CHOOSING" - the printed rule under a board pick.
RULE_BOX_PADDING = 8
RULE_SCROLLBAR_WIDTH = 5
RULE_SCROLL_STEP = 24     # pixels per wheel notch
# A board pick whose rule is a STRATAGEM says so in its own title bar. User:
# "wenn es sich bei der faehigkeit in der linken spalte um ein stratagem
# handelt, muss schon in der ueberschrift durch violette farbe zu erkennen
# sein, dass es sich um ein stratagem handelt und die CP kosten muessen auch
# teil der ueberschrift sein."
#
# TAKEN FROM button_style's "stratagem" palette rather than mixed here, the
# same way DecisionOverlay takes its violet heading: violet means "this spends
# CP" everywhere in this HUD, and a second, slightly different violet would
# read as a different kind of thing.
#
# BOTH the fill and the text, where the overlay swaps text and border: this bar
# has no border, so those are its two levers. And the colour is not asked to
# carry the fact alone - the CP cost is printed in the heading beside it, which
# is the half that survives a greyscale screenshot.
STRATAGEM_HEADER_TEXT_COLOR = button_style.TEXT_NORMAL_STRATAGEM
STRATAGEM_HEADER_BG_COLOR = button_style.BG_NORMAL_STRATAGEM
HINT_COLOR = (135, 155, 170)  # dimmer than PANEL_TEXT_COLOR - explains a UI convention, isn't game state
ERROR_COLOR = (220, 70, 70)
ERROR_BOX_BG_COLOR = (40, 20, 20)
MESSAGE_BOX_PADDING = 8

PORTRAIT_BOX_PX = 46   # side of one thumbnail cell in a unit listing
PORTRAIT_GAP = 4
PORTRAIT_BG_COLOR = (8, 14, 22)  # a shade darker than button_style.BOX_BG_COLOR, so art reads as inset

# The SELECTED-UNIT BOX at the very top of this column (User: "Verlagere die
# info stattdessen ganz oben in die linke spalte mit Sprite + name in einen
# abgeschlossenen kasten"), replacing the name plate the renderer used to draw
# over the board.
#
# BESIDE, not above: _draw_unit_portrait() stacks art over text because it is a
# screen's main heading and full-width strings are what a 220px column is short
# of - but this box is a permanent fixture on every frame, and a stacked one
# would cost ~70px off the top of every branch below it. Beside is
# _draw_unit_row()'s layout and costs about what one thumbnail costs.
SELECTION_BOX_PORTRAIT_PX = 40
SELECTION_BOX_PAD = 7
SELECTION_BOX_GAP = 6           # between the box and whatever the dispatch draws
# The cyan of renderer.SELECTED_MODEL_COLOR, which is what the anchor ring on
# the board is drawn in. The box and the rings are the same statement in two
# places, so they share a colour rather than each picking one - that was the
# name plate's job too (it used the same constant), and it is the half of it
# worth keeping.
SELECTION_BOX_BORDER_COLOR = (0, 220, 255)   # == renderer.SELECTED_MODEL_COLOR
SELECTION_BOX_BG_COLOR = (10, 30, 36)        # == renderer.SELECTION_LABEL_BG_COLOR

ACTION_REQUIRED_BG_COLOR = (35, 20, 10)
ACTION_REQUIRED_TEXT_COLOR = (255, 255, 255)
COHERENCY_ACCENT_COLOR = (200, 20, 20)      # matches renderer.COHERENCY_REMOVAL_COLOR
DAMAGE_CHOICE_ACCENT_COLOR = (255, 210, 0)  # matches renderer.DAMAGE_CHOICE_COLOR
# Pile In still outstanding (12.03). Its own orange rather than a borrowed
# shade: it is neither an error (ERROR_COLOR red) nor a "click a highlighted
# model" prompt (DAMAGE_CHOICE yellow, which is paired with a renderer colour
# this has no counterpart for - nothing is highlighted on the board here).
PILE_IN_ACCENT_COLOR = (255, 170, 40)
# "Change a die to an unmodified 6" (Aspect Shrine / Branching Fates). Aeldari
# blue-white: it is a friendly, deliberate spend rather than a warning, and it
# must not read as the pile-in orange right above it.
UNMODIFIED_SIX_ACCENT_COLOR = (140, 210, 255)
PILE_IN_BOX_BG_COLOR = (38, 26, 10)
# Cap on how many unit names one player's line lists before it collapses to
# "+N more" - the panel is 220px wide and an engaged blob runs deep.
PILE_IN_NAMES_SHOWN = 4


#: How long the cursor must rest on a Stratagem button before its printed
#: rules appear. User: "sollte das stratagems vollständig angezeigt werden wenn
#: man ein paar Sekunden über einen stratagems Knopf hovert." Longer than the
#: datacard's 900ms on purpose: that card opens over the BOARD, where resting
#: the cursor means "tell me about this model", while the panel is full of
#: buttons a player is moving between on the way to clicking one.
STRATAGEM_TIP_DELAY_MS = 1400
#: Cursor drift this small still counts as resting - without it a hand resting
#: on a mouse never triggers the dwell at all. Same allowance the datacard
#: makes, and for the same reason.
STRATAGEM_TIP_JITTER_PX = 6


def _stratagem_name_in(label):
    """The Stratagem's printed name out of its button label.

    Every one of the seventeen labels is "<name> (<cost>)" optionally followed
    by " - <summary>" ("Sudden Storm (1 CP) - ranged weapons gain [ASSAULT]
    this turn"), so the name is what stands before the cost. Split on " (" and
    not on "(" because a name may legitimately contain a bracket, and the cost
    is always preceded by a space.

    The COST is deliberately dropped rather than parsed: the corpus prints its
    own, and two sources for one number is how they come to disagree."""
    return (label or "").split(" (")[0].strip()


class ActionPanel:
    def __init__(self):
        self.header_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
        self.big_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE + 10, bold=True)
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
        self.button_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE - 1, bold=True)
        self._buttons = []  # list of (rect, callback)
        self._mouse_pos = (-1, -1)
        self._mouse_down = False
        # Stratagem buttons drawn this frame, as (rect, printed name) - the
        # tooltip's subjects. Parallel to _buttons rather than part of it,
        # because handle_click() destructures that one as a 2-tuple.
        self._stratagem_buttons = []
        # Dwell-to-open state for that tooltip, driven by update_tooltip().
        self._tip_name = None
        self._tip_since = None
        self._tip_pos = (0, 0)
        self._tip_rect = None
        self.tooltip_name = None
        # "WHY YOU ARE CHOOSING": the printed rule behind a board pick.
        # Typeset by game/ui/rules_body.py - the same one the army-rules
        # reader and the Stratagem tooltip use, so "how are printed rules
        # set" keeps one answer.
        self._rules_body = RulesBody()
        self._rule_scroll = 0
        self._rule_scroll_max = 0
        self._rule_view = None    # the clipped body rect, or None
        self._rule_key = None     # which rule the scroll offset belongs to
        self._rule_bottom = None  # where the box ended last frame, for tests

    def draw(
        self, surface, rect, movement_controller, shooting_controller, coherency_enforcer=None,
        charge_controller=None, pile_in_controller=None, fight_controller=None, consolidate_controller=None,
        retro_thrusters_controller=None,
        battle_shock_controller=None, dice_manager=None, command_reroll_controller=None, explosives_controller=None,
        setup_controller=None, ingress_controller=None, transport_controller=None, epic_challenge_controller=None,
        insane_bravery_controller=None, crushing_impact_controller=None, firing_deck_controller=None,
        greater_good_controller=None, fall_back_controller=None, fire_overwatch_controller=None,
        pregame_controller=None, arrokon_controller=None, shortened_blade_controller=None,
        torchstar_controller=None, unbridled_carnage_controller=None, ere_we_go_controller=None,
        tactical_acumen_controller=None,
        flickerjump_controller=None,
        battle_focus_pool=None,
        # Appended rather than slotted in beside arrokon_controller: main.py's
        # draw() call passes everything above POSITIONALLY.
        sudden_storm_controller=None,
        conquering_tyrant_controller=None,
        hungry_void_controller=None,
        path_of_the_outcast_controller=None,
        fire_and_fade_controller=None,
        chronometron_controller=None,
        overflight_controller=None,
        higher_duty_controller=None,
        warhost_fire_and_fade_controller=None,
        targeting_array_controller=None,
        secondary_mission_controller=None,
        primary_mission_controller=None,
        unmodified_six_controller=None,
        # Death Lord's Chosen - the three a human buys proactively. Appended
        # BY KEYWORD: this chain is positional up to battle_focus_pool, and
        # inserting a parameter mid-signature has silently shifted every
        # argument after it before.
        blooming_pestilence_controller=None,
        grim_reapers_controller=None,
        mortarions_teachings_controller=None,
        # ONE parameter for every proactive detachment Stratagem, instead of one
        # per Stratagem. See game/proactive_stratagems.py: the T'au detachments
        # alone add nineteen, and this chain is positional for most of its
        # length. A controller joins the list and needs no edit here.
        proactive_stratagems=None,
        # Rule 01.02.03's model return, which rides the Set Up flow - appended
        # by keyword for the same reason everything above it is.
        return_placement_controller=None,
        # The pending "click a unit on the battlefield" decision, already
        # resolved against the board by game/unit_pick.pending() - a RECORD,
        # not a controller, because this panel is the only place that can say
        # what is being asked while the board carries the answer. Appended by
        # keyword like everything above it.
        unit_pick=None,
        damage_pick=None,
        # The printed rule behind a board pick, drawn by _draw_unit_pick_ui().
        decision_rule=None,
    ):
        surface.fill(config.PANEL_BG_COLOR, rect)
        pygame.draw.rect(surface, config.PANEL_BORDER_COLOR, rect, width=2)
        self._buttons = []
        self._stratagem_buttons = []
        self._mouse_pos = pygame.mouse.get_pos()
        self._mouse_down = pygame.mouse.get_pressed()[0]

        # WHO IS SELECTED, at the very top, before anything else gets a say.
        # Drawn here rather than inside _draw_dispatch() for the same reason
        # _draw_global_toolbar() is: that method is ~40 early-returning
        # branches, and a fact that holds across all of them must not depend on
        # which one ran. The selection is exactly such a fact -
        # movement_controller.selected_squad is this game's phase-crossing
        # "which unit is the subject" (see game/selection.py), read by every
        # branch below and by the board's own rings.
        #
        # The dispatch is then handed a SHORTER rect. Every branch lays itself
        # out from rect.y (mostly `rect.y + 40`), so moving that one edge moves
        # all forty at once - the alternative was editing forty call sites into
        # agreeing on a new origin, which is how this file earned its scar
        # about positional call chains.
        full_rect = rect
        rect = self._draw_selection_header(surface, rect, movement_controller)

        self._draw_dispatch(
            surface, rect, movement_controller, shooting_controller, coherency_enforcer,
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
            sudden_storm_controller=sudden_storm_controller,
            conquering_tyrant_controller=conquering_tyrant_controller,
            hungry_void_controller=hungry_void_controller,
            blooming_pestilence_controller=blooming_pestilence_controller,
            grim_reapers_controller=grim_reapers_controller,
            mortarions_teachings_controller=mortarions_teachings_controller,
            proactive_stratagems=proactive_stratagems,
            path_of_the_outcast_controller=path_of_the_outcast_controller,
            fire_and_fade_controller=fire_and_fade_controller,
            chronometron_controller=chronometron_controller,
            overflight_controller=overflight_controller,
            higher_duty_controller=higher_duty_controller,
            warhost_fire_and_fade_controller=warhost_fire_and_fade_controller,
            targeting_array_controller=targeting_array_controller,
            secondary_mission_controller=secondary_mission_controller,
            primary_mission_controller=primary_mission_controller,
            unmodified_six_controller=unmodified_six_controller,
            return_placement_controller=return_placement_controller,
            unit_pick=unit_pick,
            damage_pick=damage_pick,
            decision_rule=decision_rule,
        )
        # The FULL rect, not the shortened one: this strip is pinned to the
        # BOTTOM edge, which the selection box does not move.
        self._draw_global_toolbar(surface, full_rect, movement_controller)

    def _draw_dispatch(
        self, surface, rect, movement_controller, shooting_controller, coherency_enforcer=None,
        charge_controller=None, pile_in_controller=None, fight_controller=None, consolidate_controller=None,
        retro_thrusters_controller=None,
        battle_shock_controller=None, dice_manager=None, command_reroll_controller=None, explosives_controller=None,
        setup_controller=None, ingress_controller=None, transport_controller=None, epic_challenge_controller=None,
        insane_bravery_controller=None, crushing_impact_controller=None, firing_deck_controller=None,
        greater_good_controller=None, fall_back_controller=None, fire_overwatch_controller=None,
        pregame_controller=None, arrokon_controller=None, shortened_blade_controller=None,
        torchstar_controller=None, unbridled_carnage_controller=None, ere_we_go_controller=None,
        tactical_acumen_controller=None,
        flickerjump_controller=None,
        battle_focus_pool=None,
        # Appended: draw() passes everything above positionally.
        sudden_storm_controller=None,
        conquering_tyrant_controller=None,
        hungry_void_controller=None,
        # Completed here by another session's edit: this parameter was added to
        # draw() and _draw_movement_ui() and forwarded through both, but not to
        # THIS signature - the three-stage chain half-wired, which crashes every
        # frame. See main.py's own warning about this call chain.
        path_of_the_outcast_controller=None,
        fire_and_fade_controller=None,
        chronometron_controller=None,
        overflight_controller=None,
        higher_duty_controller=None,
        warhost_fire_and_fade_controller=None,
        targeting_array_controller=None,
        # Appended BY KEYWORD like everything above it - this three-stage call
        # chain is positional up to battle_focus_pool, and inserting a
        # parameter mid-signature has silently shifted every later one before.
        secondary_mission_controller=None,
        primary_mission_controller=None,
        unmodified_six_controller=None,
        # Death Lord's Chosen - the three a human buys proactively. Appended
        # BY KEYWORD: this chain is positional up to battle_focus_pool, and
        # inserting a parameter mid-signature has silently shifted every
        # argument after it before.
        blooming_pestilence_controller=None,
        grim_reapers_controller=None,
        mortarions_teachings_controller=None,
        # ONE parameter for every proactive detachment Stratagem, instead of one
        # per Stratagem. See game/proactive_stratagems.py: the T'au detachments
        # alone add nineteen, and this chain is positional for most of its
        # length. A controller joins the list and needs no edit here.
        proactive_stratagems=None,
        return_placement_controller=None,
        unit_pick=None,
        damage_pick=None,
        # The printed rule behind a board pick, drawn by _draw_unit_pick_ui().
        decision_rule=None,
    ):
        """The old draw() body, verbatim - one big state dispatch with an
        early return per screen (setup/firing-deck/damage-choice/dice-roll/
        every controller's own sub-state, ending in _draw_movement_ui() as
        the default). Split out so draw() can unconditionally render the
        always-visible toolbar (see _draw_global_toolbar()) AFTER whichever
        one of these branches ran, instead of it needing to be duplicated
        into every single return point."""
        # An open "click a unit on the board" decision owns the panel. Its
        # answer is a click on the BOARD, so the panel is the only place that
        # can say what is being asked - and, where a subject is given, about
        # WHICH objective.
        #
        # User: "Immer wenn man eine einheit auf dem schlachtfeld waehlen muss
        # (zb wall of mirrors) will ich die einheit nicht aus einer liste
        # waehlen, sondern auf dem schlachtfeld. Wie bei overwatch." - and,
        # earlier, for the one ability that already worked this way: "Bei
        # Burden of Trust muss immer links in der Spalte das Objective genannt
        # werden, um das es gerade geht, und ich muss auf der Map mein Einheit
        # anklicken."
        #
        # First in the dispatch because it is modal in the same sense the
        # damage-allocation screens are: any branch placed above it could hide
        # it, and then the board would be waiting for a click the panel never
        # explained.
        if unit_pick is not None:
            self._draw_unit_pick_ui(surface, rect, unit_pick, decision_rule=decision_rule)
            return

        # Rule 03.01: the pre-game sequence owns the whole panel while it runs -
        # ahead of every other screen, since none of them can be reached before
        # the battle has even started.
        #
        # ...EXCEPT while it has handed the human off to another controller's
        # screen, which is not hypothetical: rule 24.31's SCOUTS step offers a
        # Scout Move (24.32) and starts it on MovementController, whose Confirm
        # and Cancel buttons live in _draw_movement_ui(), far below this return.
        #
        # User report: "nach meinem scout move kann ich nicht bestaetigen. es
        # gibt keinen knopf." Exactly that, and only that - the move itself
        # worked (dragging goes through InputManager, which this gate never
        # sees, and main.py's event chain already routes left-panel clicks to
        # handle_click()); the panel simply drew "Resolving pre-battle
        # abilities..." and no buttons, so there was nothing to click and the
        # pre-game could not be resumed at all.
        #
        # Written as "the pre-game yields while a move is in progress" rather
        # than as a case inside _draw_pregame_ui()'s PREBATTLE_ABILITIES branch,
        # so a future pre-game step that starts a move is covered by
        # construction. The deploying step sets the same precedent from the
        # other side: it delegates to _draw_setup_ui() instead of
        # reimplementing placement.
        if (
            pregame_controller is not None and pregame_controller.is_active
            and movement_controller.state != movement.MOVING
        ):
            self._draw_pregame_ui(
                surface, rect, pregame_controller, setup_controller,
                ingress_controller, transport_controller,
                return_placement_controller=return_placement_controller,
            )
            return

        if setup_controller is not None and setup_controller.state == setup.PLACING:
            self._draw_setup_ui(surface, rect, setup_controller, ingress_controller, transport_controller,
                                shortened_blade_controller=shortened_blade_controller,
                                return_placement_controller=return_placement_controller)
            return

        if firing_deck_controller is not None and firing_deck_controller.state == firing_deck.CHOOSING_MODELS:
            self._draw_firing_deck_choose_models(surface, rect, firing_deck_controller)
            return

        if firing_deck_controller is not None and firing_deck_controller.state == firing_deck.CHOOSING_WEAPON:
            self._draw_firing_deck_choose_weapon(surface, rect, firing_deck_controller)
            return

        if coherency_enforcer is not None and coherency_enforcer.pending_squad is not None:
            self._draw_action_required(
                surface, rect, COHERENCY_ACCENT_COLOR,
                f'Remove a model from "{coherency_enforcer.pending_squad.name}" to regain coherency. '
                f"Click a highlighted model on the battlefield."
            )
            return

        # ONE branch for all 27 controllers that can be waiting for a model
        # click, where there used to be two - shooting and fight - and 25
        # controllers with no branch at all. Reported as the Fire Overwatch
        # screen appearing over a mortal-wound allocation: overwatch is branch
        # #29, BELOW this one, so it never hid anything; what it filled was the
        # hole left by a controller that had no screen and fell through the
        # whole chain. See game/damage_pick.py.
        #
        # KEPT IN THIS SLOT deliberately, not moved above unit_pick(#1). In
        # main.py's event chain `decision_manager.is_pending` sits ~170 lines
        # ABOVE the first damage branch, so while a decision is open a board
        # click resolves the PICK, not the allocation - a panel that said
        # "click a highlighted model" there would be describing a control the
        # chain refuses, which is this same bug pointed the other way.
        if damage_pick is not None:
            # Naming the UNIT is strictly more than the old text said, at no
            # cost: the record already carries it. Naming the ABILITY is a
            # measured refusal - see game/damage_pick.py's docstring.
            self._draw_action_required(
                surface, rect, DAMAGE_CHOICE_ACCENT_COLOR,
                f'Choose which model of "{damage_pick.squad.name}" takes the wound. '
                f"Click a highlighted model on the battlefield."
            )
            return

        if dice_manager is not None and dice_manager.is_pending:
            self._draw_command_reroll(surface, rect, dice_manager, command_reroll_controller,
                                      unmodified_six_controller=unmodified_six_controller,
                                      targeting_array_controller=targeting_array_controller)
            return

        button_style.draw_panel_header(surface, rect, "Actions", self.header_font)

        button_width = rect.width - 2 * BUTTON_MARGIN

        if epic_challenge_controller is not None and epic_challenge_controller.state == epic_challenge.CHOOSING_MODEL:
            self._draw_epic_challenge_choose_model(surface, rect, button_width, epic_challenge_controller)
            return

        if shooting_controller.current_group is not None:
            self._draw_resolving(surface, rect, shooting_controller)
            return

        if fight_controller is not None and fight_controller.current_group is not None:
            self._draw_resolving(surface, rect, fight_controller)
            return

        if fight_controller is not None and fight_controller.state == fight.CHOOSING_TARGET:
            self._draw_fight_choose_target(surface, rect, button_width, fight_controller, epic_challenge_controller)
            return

        if fight_controller is not None and fight_controller.state == fight.CHOOSING_WEAPON:
            self._draw_fight_weapon_choice(surface, rect, button_width, fight_controller, epic_challenge_controller)
            return

        if fight_controller is not None and fight_controller.state == fight.ASSIGNING:
            self._draw_fight_assigning(surface, rect, button_width, fight_controller, epic_challenge_controller)
            return

        if (
            charge_controller is not None and charge_controller.state == charge.DECLARING_TARGETS
            and movement_controller.state != movement.MOVING
        ):
            self._draw_charge_declaring(surface, rect, button_width, charge_controller)
            return

        if (
            consolidate_controller is not None and consolidate_controller.state == consolidate.CHOOSING_ENGAGING_TARGETS
            and movement_controller.state != movement.MOVING
        ):
            self._draw_consolidate_declaring(surface, rect, button_width, consolidate_controller)
            return

        if (
            consolidate_controller is not None and consolidate_controller.state == consolidate.CHOOSING_OBJECTIVE
            and movement_controller.state != movement.MOVING
        ):
            self._draw_consolidate_choose_objective(surface, rect, button_width, consolidate_controller)
            return

        if (
            fall_back_controller is not None and fall_back_controller.state == fall_back.CHOOSING_MODE
            and movement_controller.state != movement.MOVING
        ):
            self._draw_fall_back_choosing_mode(surface, rect, button_width, fall_back_controller)
            return

        if shooting_controller.state == shooting.CHOOSING_SHOOTING_TYPE:
            self._draw_choose_shooting_type(surface, rect, button_width, shooting_controller)
            return

        if shooting_controller.state == shooting.CHOOSING_TARGET:
            self._draw_choose_target(surface, rect, button_width, shooting_controller)
            return

        if shooting_controller.state == shooting.CHOOSING_WEAPON:
            self._draw_weapon_choice(surface, rect, button_width, shooting_controller)
            return

        if shooting_controller.state == shooting.ASSIGNING:
            self._draw_assigning(surface, rect, button_width, shooting_controller)
            return

        if explosives_controller is not None and explosives_controller.state == explosives.CHOOSING_MODEL:
            self._draw_explosives_choose_model(surface, rect, button_width, explosives_controller)
            return

        if explosives_controller is not None and explosives_controller.state == explosives.CHOOSING_TARGET:
            self._draw_explosives_choose_target(surface, rect, button_width, explosives_controller)
            return

        if greater_good_controller is not None and greater_good_controller.state == greater_good.CHOOSING_TARGET:
            self._draw_greater_good_choose_target(surface, rect, button_width, greater_good_controller)
            return

        if crushing_impact_controller is not None and crushing_impact_controller.state == crushing_impact.CHOOSING_ENEMY:
            self._draw_crushing_impact_choose_enemy(surface, rect, button_width, crushing_impact_controller)
            return

        if crushing_impact_controller is not None and crushing_impact_controller.state == crushing_impact.CHOOSING_MODEL:
            self._draw_crushing_impact_choose_model(surface, rect, button_width, crushing_impact_controller)
            return

        if fire_overwatch_controller is not None and fire_overwatch_controller.state == overwatch.CHOOSING_UNIT:
            self._draw_fire_overwatch_choose_unit(surface, rect, button_width, fire_overwatch_controller)
            return

        self._draw_movement_ui(
            surface, rect, button_width, movement_controller, shooting_controller,
            charge_controller, pile_in_controller, fight_controller, consolidate_controller,
            retro_thrusters_controller,
            battle_shock_controller, explosives_controller, transport_controller, insane_bravery_controller,
            crushing_impact_controller, firing_deck_controller, greater_good_controller, fall_back_controller,
            arrokon_controller, torchstar_controller, unbridled_carnage_controller, ere_we_go_controller,
            tactical_acumen_controller,
            flickerjump_controller,
            battle_focus_pool,
            sudden_storm_controller=sudden_storm_controller,
            conquering_tyrant_controller=conquering_tyrant_controller,
            hungry_void_controller=hungry_void_controller,
            blooming_pestilence_controller=blooming_pestilence_controller,
            grim_reapers_controller=grim_reapers_controller,
            mortarions_teachings_controller=mortarions_teachings_controller,
            proactive_stratagems=proactive_stratagems,
            path_of_the_outcast_controller=path_of_the_outcast_controller,
            fire_and_fade_controller=fire_and_fade_controller,
            chronometron_controller=chronometron_controller,
            overflight_controller=overflight_controller,
            higher_duty_controller=higher_duty_controller,
            warhost_fire_and_fade_controller=warhost_fire_and_fade_controller,
            targeting_array_controller=targeting_array_controller,
            secondary_mission_controller=secondary_mission_controller,
            primary_mission_controller=primary_mission_controller,
            unmodified_six_controller=unmodified_six_controller,
        )

    def _draw_selection_header(self, surface, rect, movement_controller):
        """The selected unit's art and name, in a closed box at the top of this
        column. Returns the rect the rest of the panel gets.

        User: "Entferne das Label, das den Squad namen anzeigt, wenn man eine
        Einheit auswaehlt. das label stoert auf dem spielfeld. Verlagere die
        info stattdessen ganz oben in die linke spalte mit Sprite + name in
        einen abgeschlossenen kasten." The renderer used to float a name plate
        over the unit's topmost model; it is gone (see
        Renderer.draw_selection()), and this is where it went.

        WITH NOTHING SELECTED THE BOX IS NOT DRAWN AT ALL, and the rect comes
        back untouched. That is this file's standing convention - no chrome for
        a control that cannot do anything, the same rule the pager and the
        confirm button follow on the picking screens - and the alternative, an
        empty bordered box saying "no unit", would take the same ~54px off
        every branch below in order to say nothing. `_draw_movement_ui()`
        already explains the no-selection case in words, which is the branch a
        player actually reaches by clicking into the void.

        The name is the SAME STRING the movement branch prints below it
        ("{name} ({n})"), for the reason the removed plate gave: the board and
        the panel must not disagree about which unit is picked, and a squad
        name carries the owner digit plus a copy number precisely so two units
        off one datasheet can be told apart. It is drawn WRAPPED - a merged
        attached unit measures ~300px against ~130px of room here, so an
        unwrapped line would be cut off at exactly the copy number that
        distinguishes it."""
        squad = movement_controller.selected_squad
        if squad is None:
            return rect

        pad = SELECTION_BOX_PAD
        art_px = SELECTION_BOX_PORTRAIT_PX
        paths = sprites.portrait_paths(squad, limit=1)
        text_x = rect.x + TEXT_MARGIN + pad
        if paths:
            text_x += art_px + PORTRAIT_GAP + 2
        text_width = max(20, rect.right - TEXT_MARGIN - pad - text_x)

        label = f"{squad.name} ({len(squad.models)})"
        lines = wrap_text(self.font, label, text_width) or [label]
        text_height = len(lines) * ERROR_LINE_HEIGHT
        # Tall enough for whichever of the two is taller, so a three-line name
        # cannot spill out of its own box.
        inner = max(art_px if paths else 0, text_height)
        box = pygame.Rect(rect.x + TEXT_MARGIN, rect.y + pad,
                          rect.width - 2 * TEXT_MARGIN, inner + 2 * pad)
        button_style.draw_box(surface, box, chamfer=6,
                              bg_color=SELECTION_BOX_BG_COLOR,
                              border_color=SELECTION_BOX_BORDER_COLOR)
        if paths:
            cell = pygame.Rect(box.x + pad, box.centery - art_px // 2, art_px, art_px)
            button_style.draw_box(surface, cell, chamfer=5, bg_color=PORTRAIT_BG_COLOR)
            art = sprites.fitted_surface(paths[0], art_px - 6)
            surface.blit(art, art.get_rect(center=cell.center))
        text_y = box.centery - text_height // 2
        for line in lines:
            surface.blit(self.font.render(line, True, config.PANEL_TEXT_COLOR), (text_x, text_y))
            text_y += ERROR_LINE_HEIGHT

        top = box.bottom + SELECTION_BOX_GAP
        return pygame.Rect(rect.x, top, rect.width, rect.bottom - top)

    def _draw_global_toolbar(self, surface, rect, movement_controller):
        """User-Wunsch: "die beiden toggles Los check und Squad move... in
        eine art toolbar links unten... soll immer sichtbar sein und die
        toggles sollen global gelten." They used to live inside
        _draw_movement_ui() - visible only while a squad was mid-move, and
        reset to Off at the start/end of every move, so they never actually
        behaved like the persistent session preference they were framed as.
        Drawn here, in draw() AFTER _draw_dispatch() returns, so it's
        visible no matter which of that method's many early-return screens
        rendered above it - a fixed strip pinned to the bottom of the whole
        panel rect, not tied to squad selection or move state at all.
        Registered into self._buttons like any other button - every
        left-panel click in main.py's event loop already routes to
        handle_click() regardless of the current phase/controller state, so
        clicking these needs no changes there.

        THE STRIP IS DOWN TO ONE ROW, on two later user decisions:

          * the LOS-check toggle is gone - "den LOS Check Knopf brauch ich
            nicht mehr. der soll immer aktiviert sein" - so the live
            line-of-sight highlight has no state left to show (main.py now
            skips it only while a whole-unit drag is actually running);
          * the block-deployment and block-movement toggles are one - "ich
            glaube, dass man Block Deployment und Block Movement
            zusammenfassen kann. Mir faellt keine Situation ein, wo man das
            getrennt braeuchte" - so both read one value, in
            game/whole_unit_drag.py, and one switch drives it.

        What remains draws through _draw_toggle() rather than _draw_button():
        the row carries an on/off state, and spelling it out as ": On"/": Off"
        text was the ONLY difference between the two looks (measured: the
        rendered rows were otherwise pixel-identical)."""
        button_width = rect.width - 2 * BUTTON_MARGIN
        # ONE row, not two: "Move Whole Squad" and "Place as Block" were the
        # same preference asked twice, and the user retired the distinction
        # ("Block Deployment und Block Movement zusammenfassen... mir faellt
        # keine Situation ein, wo man das getrennt braeuchte"). Both flags now
        # read game/whole_unit_drag.py, so either controller can serve the row;
        # movement_controller is used because it is the one always present.
        toggles = [
            ("Drag Whole Unit", movement_controller.group_move_enabled,
             movement_controller.toggle_group_move),
            # The RANGE RULER (game/aura_ruler.py). A toggle plus, while it is
            # on, a radio of radii - the two controls the user asked for, and
            # in that order because the toggle is what answers "on or off".
            ("Aura", aura_ruler.is_enabled(), aura_ruler.toggle),
        ]

        # One shared row height for the whole strip, measured off the widest
        # label: at 200px "Move Whole Squad" wraps to two lines while "Place
        # as Block" fits on one, and rows of different heights next to each
        # other read as a layout accident rather than as one control group.
        row_height = max(
            button_style.toggle_height(button_width, label, self.button_font, min_height=BUTTON_HEIGHT)
            for label, _, _ in toggles
        )
        # The radius radio, which exists only while the ruler is on. Same
        # convention the pager and the confirm button in game/ui/tile_screen.py
        # follow: no chrome for a control that cannot do anything - eight dead
        # buttons under an off switch would be eight things to explain.
        #
        # A GRID, not eight rows: the panel is 220px wide and eight full-width
        # rows would be taller than the rest of the toolbar put together, on a
        # strip that is pinned to the bottom and has to leave room above it.
        radio_rows = (_radio_rows() if aura_ruler.is_enabled() else 0)
        radio_height = radio_rows * (RADIO_HEIGHT + BUTTON_GAP)

        toolbar_height = (len(toggles) * row_height + (len(toggles) + 1) * BUTTON_GAP
                          + radio_height)
        top_y = rect.bottom - toolbar_height
        pygame.draw.line(surface, config.PANEL_BORDER_COLOR, (rect.x, top_y), (rect.right, top_y), width=2)

        button_y = top_y + BUTTON_GAP
        for label, is_on, callback in toggles:
            toggle_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, row_height)
            toggle_rect = self._draw_toggle(surface, toggle_rect, label, is_on)
            self._buttons.append((toggle_rect, callback))
            button_y += toggle_rect.height + BUTTON_GAP
        if radio_rows:
            self._draw_aura_radio(surface, rect.x + BUTTON_MARGIN, button_y, button_width)

    def _draw_aura_radio(self, surface, x, y, width):
        """The eight radii, as a grid of radio buttons.

        Drawn with button_style's PRESSED look for the live one - the same
        thing the map screen's biome row does, and for the same reason: a
        many-way switch where one is always on is exactly what "pressed"
        already means in this HUD, so a second visual language is not invented
        for it. Nothing else in this panel has a lasting pressed state, so it
        cannot be confused with hover."""
        # self._mouse_pos, not pygame.mouse.get_pos(): draw() samples the
        # cursor ONCE per frame and every other control in this panel hovers
        # off that, so reading it again here could disagree with the row above
        # by a frame - and it is what lets a test drive hover at all.
        mouse = self._mouse_pos
        active = aura_ruler.radius_in()
        cell = (width - (RADIO_COLUMNS - 1) * RADIO_GAP) // RADIO_COLUMNS
        for index, radius in enumerate(aura_ruler.RADII_IN):
            column, row = index % RADIO_COLUMNS, index // RADIO_COLUMNS
            cell_rect = pygame.Rect(x + column * (cell + RADIO_GAP),
                                    y + row * (RADIO_HEIGHT + BUTTON_GAP),
                                    cell, RADIO_HEIGHT)
            button_style.draw_button(
                surface, cell_rect, f'{radius}"', self.button_font,
                hovered=cell_rect.collidepoint(mouse),
                pressed=(radius == active),
            )
            # Bound at definition time: the loop variable would otherwise be
            # read when the click happens, by which point it is 36 for every
            # button - the classic late-binding closure, and it would make
            # seven of these eight silently wrong.
            self._buttons.append((cell_rect, (lambda r: lambda: aura_ruler.set_radius(r))(radius)))

    def _draw_text(self, surface, rect, text, y, color=None, font=None, gap=4):
        """The only way this panel prints text: wrapped to the panel's own
        content width, returning the y just below it so the caller stacks
        the next thing off that instead of a hardcoded offset.

        Every screen in this file used to blit a one-line
        f"Fighting: {squad.name}" at rect.y + 40 and then start its buttons
        at rect.y + 65. That silently assumed unit names stay short - once
        attached units (19.01) made a name like "1 Crisis Starscythe
        Battlesuits 1 + Commander in Coldstar Battlesuit", the text ran
        300px past a 220px panel AND a wrapped version would have been
        drawn over by the first button. Flowing y fixes both at once."""
        return draw_wrapped_text(
            surface, font or self.font, text,
            color if color is not None else config.PANEL_TEXT_COLOR,
            rect.x + TEXT_MARGIN, y, rect.width - 2 * TEXT_MARGIN,
            line_height=ERROR_LINE_HEIGHT,
        ) + gap

    def _draw_action_required(self, surface, rect, accent_color, message):
        box_rect = pygame.Rect(rect.x + 6, rect.y + 6, rect.width - 12, rect.height - 12)
        button_style.draw_box(
            surface, box_rect, chamfer=16, bg_color=ACTION_REQUIRED_BG_COLOR, border_color=accent_color, border_width=4,
        )

        text_y = box_rect.y + 14
        for line in wrap_text(self.big_font, "ACTION REQUIRED", box_rect.width - 20):
            line_surf = self.big_font.render(line, True, accent_color)
            surface.blit(line_surf, (box_rect.x + 10, text_y))
            text_y += line_surf.get_height() + 4

        text_y += 10
        for line in wrap_text(self.font, message, box_rect.width - 20):
            line_surf = self.font.render(line, True, ACTION_REQUIRED_TEXT_COLOR)
            surface.blit(line_surf, (box_rect.x + 10, text_y))
            text_y += ERROR_LINE_HEIGHT

    def _draw_command_reroll(self, surface, rect, dice_manager, command_reroll_controller,
                             unmodified_six_controller=None,
                             targeting_array_controller=None):
        """Everything that can still be done to the roll on the table: rule
        15.02's Command Re-roll, and the "change a die to an unmodified 6"
        abilities (Aspect Shrine tokens, the Farseer's Branching Fates).

        The latter used to be a DecisionManager prompt raised the instant the
        roll was acknowledged - user: "momentan werde ich bei aeldari jedes mal
        gefragt... nach jedem wurf. kann das nicht eine option im linken panel
        sein, statt eines overlays? command reroll funktioniert ja auch so."
        So they live here, in exactly that shape: a button, then pick the die.

        Both die-selection modes take over the whole screen while they are
        open, because in both the only useful click is on the dice display."""
        button_style.draw_panel_header(surface, rect, "Actions", self.header_font)
        button_width = rect.width - 2 * BUTTON_MARGIN

        text_y = self._draw_message_box(
            surface, rect, button_width, rect.y + 40, [dice_manager.label or "Rolling…"],
            config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
        )

        if command_reroll_controller is not None and command_reroll_controller.selecting_die:
            text_y = self._draw_message_box(
                surface, rect, button_width, text_y,
                ["Click a highlighted die on the dice display to re-roll it."],
                config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
            )
            cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
            cancel_rect = self._draw_button(surface, cancel_rect, "Cancel Re-roll", accent="danger")
            self._buttons.append((cancel_rect, command_reroll_controller.cancel_selection))
            return

        if unmodified_six_controller is not None and unmodified_six_controller.selecting_die:
            text_y = self._draw_message_box(
                surface, rect, button_width, text_y,
                ["Click a die on the dice display to change it to an unmodified 6."],
                config.PANEL_TEXT_COLOR, UNMODIFIED_SIX_ACCENT_COLOR,
            )
            cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
            cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
            self._buttons.append((cancel_rect, unmodified_six_controller.cancel_selection))
            return

        if targeting_array_controller is not None and targeting_array_controller.selecting_die:
            text_y = self._draw_message_box(
                surface, rect, button_width, text_y,
                ["Click a highlighted die on the dice display to re-roll it."],
                config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
            )
            cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
            cancel_rect = self._draw_button(surface, cancel_rect, "Cancel Re-roll", accent="danger")
            self._buttons.append((cancel_rect, targeting_array_controller.cancel_selection))
            return

        if command_reroll_controller is not None and command_reroll_controller.can_use():
            reroll_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
            reroll_rect = self._draw_button(
                surface, reroll_rect, "Command Re-roll (1 CP)", accent="stratagem",
            )
            self._buttons.append((reroll_rect, command_reroll_controller.start))
            text_y = reroll_rect.bottom + BUTTON_GAP

        # A free single-die re-roll for the duration of a shooting
        # activation: the same shape of button as Command Re-roll above,
        # without the CP. The LABEL comes from the controller because two
        # datasheet abilities share this button - the gunships' Targeting
        # Array and the Fire Prism's Crystal Matrix - and the panel should
        # not have to know which. See game/activation_reroll.py.
        if targeting_array_controller is not None and targeting_array_controller.can_use():
            array_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
            array_rect = self._draw_button(
                surface, array_rect,
                targeting_array_controller.panel_label() or "Targeting Array",
                accent="confirm",
            )
            self._buttons.append((array_rect, targeting_array_controller.start))
            text_y = array_rect.bottom + BUTTON_GAP

        # One button per ability that could change a die of THIS roll. The
        # controller decides which those are; the panel just draws them, so a
        # third such ability needs no change here.
        if unmodified_six_controller is not None:
            for source, _squad, _model in unmodified_six_controller.available_sources():
                source_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
                source_rect = self._draw_button(
                    surface, source_rect, unmodified_six_controller.label_for(source), accent="confirm",
                )
                self._buttons.append((source_rect, lambda s=source: unmodified_six_controller.start(s)))
                text_y = source_rect.bottom + BUTTON_GAP

        self._draw_message_box(
            surface, rect, button_width, text_y, ["Click elsewhere to accept the roll."],
            config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
        )

    def _draw_message_box(self, surface, rect, button_width, y, messages, text_color, border_color, bg_color=None):
        """Renders one or more status/error messages (e.g.
        movement_controller.errors) inside a bordered box sized to fit the
        actual wrapped text, with its content clipped to that box as a
        backstop against overflow. Returns the y position just below the
        box (unchanged if there were no messages) - callers MUST use this
        return value for whatever comes next, instead of guessing a fixed
        height, so nothing can ever overlap it."""
        messages = [m for m in messages if m]
        if not messages:
            return y

        lines_per_message = [
            wrap_text(self.font, message, button_width - 2 * MESSAGE_BOX_PADDING) or [message]
            for message in messages
        ]
        total_lines = sum(len(lines) for lines in lines_per_message)
        box_height = total_lines * ERROR_LINE_HEIGHT + (len(messages) - 1) * 4 + 2 * MESSAGE_BOX_PADDING
        box_rect = pygame.Rect(rect.x + BUTTON_MARGIN, y, button_width, box_height)

        button_style.draw_box(surface, box_rect, bg_color=bg_color, border_color=border_color)

        previous_clip = surface.get_clip()
        surface.set_clip(box_rect.inflate(-2, -2))
        text_y = box_rect.y + MESSAGE_BOX_PADDING
        for lines in lines_per_message:
            for line in lines:
                line_surf = self.font.render(line, True, text_color)
                surface.blit(line_surf, (box_rect.x + MESSAGE_BOX_PADDING, text_y))
                text_y += ERROR_LINE_HEIGHT
            text_y += 4
        surface.set_clip(previous_clip)

        return box_rect.bottom + 8

    def _draw_unit_pick_ui(self, surface, rect, pick, decision_rule=None):
        """The "click a unit on the board" screen: what is being decided, who
        is eligible, and any way out the rule itself offers.

        `pick` is game/unit_pick.py's record - the ONE answer to "is this
        decision a board pick", shared with main.py's click branch and with the
        board highlight, so the three cannot disagree about who is eligible.

        The eligible units are LISTED by name as well as being ringed on the
        board. The ring alone is the faster read, but the names survive a unit
        standing behind another one and are what a player checks against.

        Every option that is NOT a unit ("Decline", "Cancel", "No more") becomes
        a button here, because the modal overlay that used to carry them is
        deliberately not drawn while the board owns the answer. A rule that
        offers no way out gets no button - that is a mandatory choice, and
        inventing an escape would change the rule.

        THE ORDER IS NAME, BUTTON, EXPLANATION - user, on being asked to pick a
        unit for Doom or Guide: "dann soll links bitte eine bessere
        einheitlichere Struktur sein. Erst als grosse ueberschrift der name der
        Ability. Dann der Knopf. Unter dem Knopf dann die Erklaerung."

        The title is therefore the PRINTED rule name where one resolved
        (game/prompt_rule.py reads it back out of the prompt), and the generic
        "CHOOSE A UNIT" only where it did not - which is not a fallback for
        rare cases: a good third of the board picks in this game are core rules
        with no corpus entry at all, and there is no name to show for those.

        The SUBJECT stays with the title rather than moving down into the
        explanation, because where a rule has one it IS the question ("which
        objective are we talking about"), not a detail of it - the reading
        game/mission_unit_pick.py's Burden of Trust was built around.

        AND WHERE THAT RULE IS A STRATAGEM THE TITLE SAYS SO TWICE OVER -
        violet, and its CP cost printed in the heading itself. User: "wenn es
        sich bei der faehigkeit in der linken spalte um ein stratagem handelt,
        muss schon in der ueberschrift durch violette farbe zu erkennen sein,
        dass es sich um ein stratagem handelt und die die CP kosten muessen
        auch teil der ueberschrift sein." Both come off the one resolved rule,
        so they cannot arrive apart."""
        heading = decision_rule.heading if decision_rule else None
        # VIOLET AND THE CP COST WHERE THE RULE IS A STRATAGEM - the heading is
        # the one line a player reads before deciding, so what the click costs
        # belongs in it. Both facts come off the ONE resolved rule
        # (game/prompt_rule.py's PromptRule), so a violet bar without a cost in
        # it is not a state this can reach.
        accent = decision_rule is not None and decision_rule.is_stratagem
        # Upper case: the two other headings on this screen ("WHY YOU ARE
        # CHOOSING", and the generic title this replaces) are shouted, and a
        # mixed-case name in the same gold bar reads as a different kind of
        # thing. The name itself is still the corpus's, verbatim.
        text_y = button_style.draw_panel_header(
            surface, rect, (heading or "CHOOSE A UNIT").upper(), self.header_font, wrap=True,
            text_color=STRATAGEM_HEADER_TEXT_COLOR if accent else None,
            bg_color=STRATAGEM_HEADER_BG_COLOR if accent else None,
        )
        if pick.subject:
            text_y = self._draw_text(
                surface, rect, pick.subject, text_y,
                color=config.PANEL_HEADER_COLOR, font=self.header_font, gap=8,
            )
        for label, index in pick.skip_options:
            r = pygame.Rect(rect.x + BUTTON_MARGIN, text_y,
                            rect.width - 2 * BUTTON_MARGIN, BUTTON_HEIGHT)
            r = self._draw_button(surface, r, label, accent="danger")
            self._buttons.append((r, lambda i=index: pick.choose(i)))
            text_y = r.bottom + BUTTON_GAP
        text_y = self._draw_text(surface, rect, pick.prompt, text_y + 2, gap=6)
        if pick.squads:
            text_y = self._draw_text(surface, rect, "Eligible units:", text_y, gap=2)
            for squad in pick.squads:
                text_y = self._draw_text(surface, rect, f"- {squad.name}", text_y, gap=2)
        else:
            text_y = self._draw_text(surface, rect, "No unit is eligible.", text_y, gap=2)
        text_y = self._draw_text(
            surface, rect, "Click one of them on the battlefield.", text_y,
            color=HINT_COLOR, gap=10,
        )
        self._draw_decision_rule(surface, rect, text_y + 4, decision_rule)

    def _draw_decision_rule(self, surface, rect, y, decision_rule):
        """The printed rule behind the choice being made on the BOARD.

        User: "immer wenn ich aufgefordert werde durch eine Faehigkeit etwas
        auf dem Spielfeld auszuwaehlen ... schreibe die Faehigkeit Regel mit in
        die rechte Spalte, sonst weiss ich gar nicht was ich da auswaehle" -
        and then, having lived with it: "'why you are choosing' soll in die
        linke spalte, nicht rechts". It was in the right panel because that
        column is the emptier one; it belongs here because this is the column
        the question is already in.

        SCROLLED, not clipped. The right panel had 336px of clear space and
        could get away with cutting a long rule off at the bottom; this column
        is already carrying the prompt, the eligible-unit list and the rule's
        own way out, so a long rule has to stay readable rather than merely
        fit. button_style.draw_scrollbar() is the same bar the army-rules
        reader and the hover datacard use.

        The scroll offset is keyed to the rule NAME: a different decision
        opens its own rule at the top, rather than inheriting an offset
        measured against something longer.

        Nothing is drawn when there is no rule: an empty framed box reads as
        something that failed to load."""
        self._rule_bottom = None
        self._rule_view = None
        self._rule_scroll_max = 0
        if not decision_rule:
            self._rule_key = None
            return
        name, blocks = decision_rule.name, decision_rule.blocks
        if not blocks:
            self._rule_key = None
            return
        if name != self._rule_key:
            self._rule_key = name
            self._rule_scroll = 0

        header = pygame.Rect(rect.x + 6, y, rect.width - 12,
                             button_style.SUBHEADER_HEIGHT)
        if header.bottom >= rect.bottom:
            return                      # no room at this window size
        button_style.draw_header_bar(surface, header, "WHY YOU ARE CHOOSING",
                                     self.header_font)
        body_top = header.bottom + RULE_BOX_PADDING

        # The scrollbar lives inside the box, so the text column loses its
        # width whether or not the bar is drawn - otherwise the wrap would
        # change the moment the content grew past the box.
        box = pygame.Rect(rect.x + 6, body_top - RULE_BOX_PADDING + 4,
                          rect.width - 12, rect.bottom - body_top - 4)
        if box.height <= RULE_BOX_PADDING * 2:
            return
        text_x = box.x + RULE_BOX_PADDING
        text_width = box.width - 2 * RULE_BOX_PADDING - RULE_SCROLLBAR_WIDTH - 4

        entries, total = self._rules_body.layout(blocks, text_width)
        # AS TALL AS THE RULE NEEDS, up to what is left of the column. It used
        # to run to the bottom edge unconditionally, which drew a mostly empty
        # framed box under a short rule - and an empty box reads as something
        # that failed to load, which is the same reason nothing at all is drawn
        # when there is no rule. Safe to decide here because the box's WIDTH is
        # already settled, so the wrap - and therefore `total` - does not
        # depend on the height being chosen from it.
        box.height = min(box.height, total + 2 * RULE_BOX_PADDING)
        view_height = box.height - 2 * RULE_BOX_PADDING
        self._rule_scroll_max = max(0, total - view_height)
        self._rule_scroll = max(0, min(self._rule_scroll, self._rule_scroll_max))

        button_style.draw_box(surface, box)
        previous_clip = surface.get_clip()
        view = pygame.Rect(box.x + 2, body_top, box.width - 4, view_height)
        surface.set_clip(view.clip(previous_clip) if previous_clip else view)
        for block, offset, height in entries:
            block_y = body_top + offset - self._rule_scroll
            if block_y + height < view.top or block_y > view.bottom:
                continue                # off-screen: skip the whole block
            self._rules_body.draw_block(surface, block, text_x, block_y,
                                        text_width, text_x + text_width)
        surface.set_clip(previous_clip)
        if self._rule_scroll_max > 0:
            track = pygame.Rect(box.right - RULE_SCROLLBAR_WIDTH - 4, view.y,
                                RULE_SCROLLBAR_WIDTH, view.height)
            button_style.draw_scrollbar(surface, track, self._rule_scroll,
                                        self._rule_scroll_max,
                                        view_height / float(total or 1))
        self._rule_view = view
        self._rule_bottom = box.bottom

    def handle_rule_scroll(self, pos, dy):
        """Mouse-wheel scrolling for the rule box. True when it was consumed.

        Takes the POSITION as well as the delta so the wheel only works over
        the box - everything else on this panel scrolls nothing, and silently
        eating a wheel event elsewhere would break the board zoom.
        """
        if self._rule_view is None or self._rule_scroll_max <= 0:
            return False
        if not self._rule_view.collidepoint(pos):
            return False
        self._rule_scroll = max(0, min(self._rule_scroll_max,
                                       self._rule_scroll - dy * RULE_SCROLL_STEP))
        return True

    def _draw_pregame_ui(self, surface, rect, pregame_controller, setup_controller=None,
                         ingress_controller=None, transport_controller=None,
                         return_placement_controller=None):
        """Rule 03.01's pre-game sequence. Sub-dispatches on the controller's
        own state, so each step shows only what it is actually asking for.

        Every choice is offered as a BUTTON rather than free input, and only
        the legal ones are drawn - the project's standing convention (the
        engine generates the options, the chooser picks one), which also means
        an illegal formation cannot be declared in the first place instead of
        being rejected afterwards."""
        button_width = rect.width - 2 * BUTTON_MARGIN
        state = pregame_controller.state

        text_y = self._draw_text(
            surface, rect, "Before the Battle", rect.y + 10,
            color=config.PANEL_HEADER_COLOR, font=self.header_font, gap=6,
        )

        if state == pregame.FORMATIONS:
            self._draw_pregame_formations(surface, rect, pregame_controller, button_width, text_y)
            return
        if state in (pregame.DEPLOY_ROLLOFF, pregame.FIRST_TURN_ROLLOFF):
            label = ("Roll-off: who deploys first?" if state == pregame.DEPLOY_ROLLOFF
                     else "Roll-off: who takes the first turn?")
            self._draw_text(surface, rect, label, text_y, gap=8)
            return
        if state == pregame.DEPLOY_ORDER_CHOICE:
            self._draw_text(surface, rect, "Choose who places the first unit.", text_y, gap=8)
            return
        if state == pregame.PREBATTLE_ABILITIES:
            self._draw_text(surface, rect, "Resolving pre-battle abilities...", text_y, gap=8)
            return
        if state == pregame.DEPLOYING:
            self._draw_pregame_deploying(
                surface, rect, pregame_controller, setup_controller,
                ingress_controller, transport_controller, button_width, text_y,
                return_placement_controller=return_placement_controller,
            )

    def _draw_unit_portrait(self, surface, rect, squad, y, gap=4):
        """The unit's own token art as thumbnail(s), drawn ABOVE its name
        wherever a unit is listed - the fastest way to recognise which unit a
        screen is talking about, since the name alone ("1 Kroot Carnivores 2")
        and even the loadout below it both have to be read.

        Above rather than beside the text on purpose: this panel is 220px
        wide, and putting a thumbnail column next to it would leave ~100px for
        data-carrying strings that are already the reason text_utils.py exists
        (a merged attached-unit name measured 300px). Full-width text stays
        full-width; the thumbnails get their own row.

        Returns the y below the row, unchanged if this unit has no art -
        callers stack off the return value, same rule as _draw_text()."""
        max_cells = max(1, (rect.width - 2 * TEXT_MARGIN + PORTRAIT_GAP) // (PORTRAIT_BOX_PX + PORTRAIT_GAP))
        paths = sprites.portrait_paths(squad, limit=min(2, max_cells))
        if not paths:
            return y
        x = rect.x + TEXT_MARGIN
        for path in paths:
            cell = pygame.Rect(x, y, PORTRAIT_BOX_PX, PORTRAIT_BOX_PX)
            button_style.draw_box(surface, cell, chamfer=6, bg_color=PORTRAIT_BG_COLOR)
            art = sprites.fitted_surface(path, PORTRAIT_BOX_PX - 8)
            surface.blit(art, art.get_rect(center=cell.center))
            x += PORTRAIT_BOX_PX + PORTRAIT_GAP
        return y + PORTRAIT_BOX_PX + gap

    def _draw_unit_row(self, surface, rect, squad, y, lines, box=38, gap=6):
        """A compact listing ENTRY: one small portrait on the left, its own
        text lines to the right of it, y advancing past whichever is taller.

        The beside-layout that _draw_unit_portrait() deliberately avoids for a
        screen's main heading, used here because this is a repeated row (the
        transport list) - stacking a portrait row above every entry would cost
        ~50px each and push the buttons below off the panel, while a row's own
        two short lines are about as tall as a small portrait anyway, so
        beside costs nothing."""
        text_x = rect.x + TEXT_MARGIN
        text_width = rect.width - 2 * TEXT_MARGIN
        bottom = y
        paths = sprites.portrait_paths(squad, limit=1)
        if paths:
            cell = pygame.Rect(text_x, y, box, box)
            button_style.draw_box(surface, cell, chamfer=5, bg_color=PORTRAIT_BG_COLOR)
            art = sprites.fitted_surface(paths[0], box - 6)
            surface.blit(art, art.get_rect(center=cell.center))
            text_x = cell.right + PORTRAIT_GAP + 2
            text_width = rect.right - TEXT_MARGIN - text_x
            bottom = cell.bottom
        text_y = y
        for text, color in lines:
            text_y = draw_wrapped_text(
                surface, self.font, text, color, text_x, text_y, text_width,
                line_height=ERROR_LINE_HEIGHT,
            ) + 2
        return max(bottom, text_y) + gap

    def _draw_loadout(self, surface, rect, squad, y, gap=10):
        """The unit's equipment, one line per model line (game/loadout.py).

        Drawn wherever a unit has to be IDENTIFIED rather than just named,
        because a scene label like "1 Strike Team 2" carries no loadout and two
        units off one datasheet are otherwise the same thing on screen. Names
        only - the full stat table is the Ctrl+hover datacard's job, and it
        would not fit in a 220px panel anyway."""
        for line in loadout.loadout_lines(squad):
            y = self._draw_text(surface, rect, line, y, color=HINT_COLOR, gap=2)
        return y + gap - 2

    def _draw_pregame_formations(self, surface, rect, pregame_controller, button_width, text_y):
        """Declare Battle Formations (03.01 / 18.01 / 20.01), one unit at a
        time, with one button per LEGAL destination."""
        # EVERY human owner, one after another - not just "the" human. With
        # the AI mode off both armies are declared at one keyboard, and this
        # panel offering only Player 1's units is what left the pre-game
        # waiting for an opponent who was never going to answer.
        pending_owners = pregame_controller.humans_with_undeclared_units()
        owner = pending_owners[0] if pending_owners else pregame_controller.first_human()
        squad = pregame_controller.current_formation_unit(owner)
        remaining = len(pregame_controller.undeclared_units(owner))

        if squad is None:
            text_y = self._draw_text(
                surface, rect, "All units declared. Waiting for your opponent...", text_y, gap=10,
            )
            return

        # The owner is NAMED whenever more than one army is being declared
        # here, or the second army's units read as a continuation of the first.
        heading = f"Declare Battle Formations ({remaining} left)"
        if len(pending_owners) > 1 or owner not in (None, "Player 1"):
            heading = f"{owner}: {heading}"
        text_y = self._draw_text(surface, rect, heading, text_y,
                                 color=HINT_COLOR, gap=6)
        text_y = self._draw_unit_portrait(surface, rect, squad, text_y)
        text_y = self._draw_text(surface, rect, squad.name, text_y, gap=4)
        # The unit's actual equipment, always - two units off the same
        # datasheet are otherwise indistinguishable here, and the name alone
        # ("1 Strike Team 1" vs "1 Strike Team 2") says nothing about which is
        # which (user: "da muss man in dem step auch irgendwie erkennen,
        # welcher trupp grade gemeint ist. also muss eigentlich die ausruestung
        # immer mit dabei stehen").
        text_y = self._draw_loadout(surface, rect, squad, text_y)

        button_y = text_y

        def _declare(destination, transport=None, join_target=None):
            def run():
                pregame_controller.declare(squad, destination, transport_token=transport,
                                           join_target=join_target)
                if pregame_controller.current_formation_unit(owner) is None:
                    pregame_controller.finish_formations_for(owner)
            return run

        deploy_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        deploy_rect = self._draw_button(surface, deploy_rect, "Deploy on the battlefield", accent="confirm")
        self._buttons.append((deploy_rect, _declare(pregame.DEPLOY)))
        button_y += deploy_rect.height + BUTTON_GAP

        # Rule 20.01's half-the-units / half-the-points cap: an option that
        # would be refused is not offered at all.
        if formations.can_add_to_reserves(
            squad, pregame_controller.army(owner), pregame_controller.reserve_units(owner)
        ):
            reserve_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            reserve_rect = self._draw_button(surface, reserve_rect, "Strategic Reserves")
            self._buttons.append((reserve_rect, _declare(pregame.RESERVES)))
            button_y += reserve_rect.height + BUTTON_GAP

        # Support Artillery: "at the start of the Declare Battle Formations
        # step, this model can join one GUARDIAN DEFENDERS unit from your
        # army". Offered here beside the transport and Reserves declarations
        # because that is where the printed text puts it - and "Deploy on the
        # battlefield" above is already the "stand alone" answer, so joining
        # needs no default of its own.
        joins = pregame_controller.joins_map(owner)
        destinations = pregame_controller.destinations_map(owner)
        join_targets = formations.eligible_join_targets(
            squad, pregame_controller.army(owner), joins, destinations)
        if join_targets:
            button_y = self._draw_text(
                surface, rect, "Support Artillery", button_y + 4, color=HINT_COLOR, gap=4,
            )
            for target in join_targets:
                # Named by its UNIT and shown with its loadout, for the reason
                # the transport rows carry: two Guardian Defenders blocks off
                # one datasheet are otherwise indistinguishable here.
                button_y = self._draw_unit_row(
                    surface, rect, target, button_y,
                    [(f"{len(target.models)} models", HINT_COLOR)], gap=4,
                )
                join_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                join_rect = self._draw_button(surface, join_rect, f"Join {target.name}")
                self._buttons.append((join_rect, _declare(pregame.JOIN, join_target=target)))
                button_y += join_rect.height + BUTTON_GAP

        transports = [t for t in pregame_controller.transports_for(owner) if t.squad is not squad]
        if not transports:
            return
        assignments = pregame_controller.assignments_map(owner)
        button_y = self._draw_text(
            surface, rect, "Transports", button_y + 4, color=HINT_COLOR, gap=4,
        )
        for transport in transports:
            assigned = assignments.get(id(transport), ())
            # Named by its UNIT ("2 Trukk 1"), not its profile ("Trukk"), and
            # with its own guns and current load - all three are needed to tell
            # two copies of the same transport apart (user: "es waere gut, wenn
            # dann alle verfuegbaren transporter in der auswahl waeren und dass
            # man direkt die ausruestung der transporter sehen kann").
            capacity = transport.profile.transport_capacity
            used = formations.transport_capacity_used(transport, assigned)
            cargo = ", ".join(s.name for s in assigned) or "empty"
            button_y = self._draw_unit_row(
                surface, rect, transport.squad, button_y,
                [
                    (loadout.transport_description(transport), config.PANEL_TEXT_COLOR),
                    (f"{used}/{capacity} capacity used - {cargo}", HINT_COLOR),
                ],
                gap=4,
            )

            problems = formations.embark_errors(
                squad, transport, assigned, joins.get(id(squad), ()))
            if problems:
                # Listed rather than silently dropped: a transport vanishing
                # from the list reads as "I have fewer transports than I
                # thought", not as "that one is full". Shown as text, not a
                # dead button, so only legal choices stay clickable - the
                # project's standing convention.
                button_y = self._draw_text(
                    surface, rect, problems[0], button_y, color=ERROR_COLOR, gap=BUTTON_GAP,
                )
                continue

            embark_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            embark_rect = self._draw_button(surface, embark_rect, f"Embark in {transport.squad.name}")
            self._buttons.append((embark_rect, _declare(pregame.EMBARK, transport)))
            button_y += embark_rect.height + BUTTON_GAP

    def _draw_pregame_deploying(self, surface, rect, pregame_controller, setup_controller,
                                ingress_controller, transport_controller, button_width, text_y,
                                return_placement_controller=None):
        """Alternating deployment (03.01). While models are actually being
        dragged into coherency this hands over to the shared Set Up screen, so
        the Confirm/Cancel behaviour is identical to Ingress and Disembark."""
        if setup_controller is not None and setup_controller.state == setup.PLACING:
            self._draw_setup_ui(surface, rect, setup_controller, ingress_controller, transport_controller,
                                pregame_controller=pregame_controller,
                                return_placement_controller=return_placement_controller)
            return

        active = pregame_controller.active_player
        pending = pregame_controller.pending_units(active)
        text_y = self._draw_text(
            surface, rect, f"{active}: place a unit ({len(pending)} left)", text_y, gap=6,
        )

        # "One of the humans", not "the human": with the AI mode off both
        # armies are deployed at one keyboard, and asking for a single name
        # here would put up "Waiting for your opponent..." in front of a player
        # who IS the opponent and is holding the mouse.
        if active not in pregame_controller.human_players:
            self._draw_text(surface, rect, "Waiting for your opponent...", text_y, color=HINT_COLOR, gap=8)
            return

        selected = pregame_controller.selected_unit
        if selected is None:
            text_y = self._draw_text(
                surface, rect,
                "Pick a unit from the strip below, then click the board to place it.",
                text_y, color=HINT_COLOR, gap=10,
            )
            return

        text_y = self._draw_unit_portrait(surface, rect, selected, text_y)
        text_y = self._draw_text(surface, rect, selected.name, text_y, gap=4)
        # Same reason as in the Formations step: the reserves strip below shows
        # names only, so this is where you confirm you picked the unit you meant.
        text_y = self._draw_loadout(surface, rect, selected, text_y, gap=6)
        text_y = self._draw_text(
            surface, rect, "Click the board to drop it. Green = legal ground for its centre.",
            text_y, color=HINT_COLOR, gap=10,
        )

        # Also useful in its own right, but load-bearing for headless testing:
        # it makes the whole sequence one-click drivable and means the AI's
        # deployment code is exercised on BOTH armies in every self-play run.
        auto_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
        auto_rect = self._draw_button(surface, auto_rect, "Auto-place this unit")
        self._buttons.append((auto_rect, lambda: pregame_controller.request_auto_place(selected)))

    def _draw_setup_ui(self, surface, rect, setup_controller, ingress_controller=None, transport_controller=None,
                       pregame_controller=None, shortened_blade_controller=None,
                       return_placement_controller=None):
        """Rule 03.02 (Set Up): a reserve unit was dropped on the board and
        is being dragged into coherency before it's confirmed - mirrors
        Movement's MOVING-state Confirm/Cancel, but with no Advance-style
        extra buttons (Set Up has no move types of its own). Rule 20.04
        (Ingress Move) / 18.04-18.05 (Disembark): if this unit arrived via
        the Reserves panel or is disembarking from a TRANSPORT, route
        Confirm/Cancel through the matching controller instead, so it can
        add its own extra checks and after-effects (Squad.ingress_locked,
        battle-shocked, no-charge, re-embarking on cancel, ...)."""
        button_width = rect.width - 2 * BUTTON_MARGIN
        squad = setup_controller.setting_up_squad
        is_ingress = ingress_controller is not None and ingress_controller.is_ingressing(squad)
        is_disembark = transport_controller is not None and transport_controller.is_disembarking(squad)
        is_deployment = pregame_controller is not None and pregame_controller.is_deploying(squad)
        # Rule 01.02.03's model return, riding the same placement flow - see
        # game/return_placement.py for why it reuses this rather than growing
        # its own pending state (Fehlerklasse 25).
        is_return = (return_placement_controller is not None
                     and return_placement_controller.pending_squad is squad)
        title_text = (
            "Disembarking" if is_disembark
            else "Ingress Move" if is_ingress
            else "Deploying" if is_deployment
            else "Returning Models" if is_return
            else "Setting Up"
        )
        text_y = self._draw_text(
            surface, rect, title_text, rect.y + 10, color=config.PANEL_HEADER_COLOR, font=self.header_font, gap=6,
        )
        text_y = self._draw_unit_portrait(surface, rect, squad, text_y)
        text_y = self._draw_text(surface, rect, squad.name, text_y, gap=4)
        text_y = self._draw_loadout(surface, rect, squad, text_y, gap=8)
        # User question: "muss der mittelpunkt von meinem modell im gruenen
        # sein oder der rand?" - the centre. The overlay's predicate is
        # evaluated at the model's centre and already subtracts its base
        # radius, so a centre on green guarantees the whole base fits. Said
        # here because nothing on the board itself can show it.
        hint = (
            "Green = where this model's CENTRE may go (its base size is already accounted for). "
            "Models snap to the edge of the legal area."
        )
        if setup_controller.block_placement_enabled:
            # Says what the toggle currently does and how to get around it for
            # one drag - the modifier is invisible otherwise.
            hint += " Dragging moves the whole block; hold SHIFT to move one model."
        text_y = self._draw_text(surface, rect, hint, text_y, color=HINT_COLOR, gap=10)

        if is_disembark:
            confirm_callback = transport_controller.confirm_disembark
            cancel_callback = transport_controller.cancel_disembark
        elif is_ingress:
            confirm_callback = ingress_controller.confirm_ingress
            cancel_callback = ingress_controller.cancel_ingress
        elif is_deployment:
            # Rule 03.01: confirming also alternates to the other player, so it
            # has to go through the pre-game controller rather than straight to
            # SetupController.
            confirm_callback = pregame_controller.confirm_deployment
            cancel_callback = pregame_controller.cancel_deployment
        elif is_return:
            # Confirming has to go through the return controller, not straight
            # to SetupController: it owns the "these models are back" half and
            # the on_done the ability is waiting on. Cancelling likewise puts
            # them back down.
            confirm_callback = return_placement_controller.confirm
            cancel_callback = return_placement_controller.cancel
        else:
            confirm_callback = setup_controller.confirm_setup
            cancel_callback = setup_controller.cancel_setup

        button_y = text_y
        # Retaliation Cadre's The Shortened Blade (2CP): bought DURING the
        # arrival, since its whole effect is on where this placement may end -
        # so it belongs on this screen and nowhere else. can_use() already
        # refuses once it is armed, so the button vanishes after one press.
        if shortened_blade_controller is not None and shortened_blade_controller.can_use(squad):
            blade_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            blade_rect = self._draw_button(
                surface, blade_rect,
                f'The Shortened Blade (2 CP) - arrive within {SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN:.0f}" of the enemy',
                accent="stratagem",
            )
            self._buttons.append((blade_rect, lambda: shortened_blade_controller.use(squad)))
            button_y += blade_rect.height + BUTTON_GAP
        elif ingress_controller is not None and ingress_controller.relaxed_arrival_squad is squad:
            text_y = self._draw_text(
                surface, rect,
                f'The Shortened Blade is active: set up more than {SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN:.0f}" '
                "from all enemy models. This unit cannot declare a charge this turn.",
                button_y, color=HINT_COLOR, gap=8,
            )
            button_y = text_y

        confirm_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        confirm_rect = self._draw_button(surface, confirm_rect, "Confirm", accent="confirm")
        self._buttons.append((confirm_rect, confirm_callback))
        button_y += confirm_rect.height + BUTTON_GAP

        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, cancel_callback))
        button_y += cancel_rect.height + BUTTON_GAP

        self._draw_message_box(
            surface, rect, button_width, button_y, setup_controller.errors,
            ERROR_COLOR, ERROR_COLOR, bg_color=ERROR_BOX_BG_COLOR,
        )

    def _draw_firing_deck_choose_models(self, surface, rect, firing_deck_controller):
        """Rule 24.14 (Firing Deck) step 1: pick up to X embarked models -
        candidates aren't board tokens (they're embarked, off the board),
        so this is a panel-only toggle list, like Fire Overwatch's squad
        list. "Confirm Selection" proceeds even with zero picked (rule
        allows "up to X", including none)."""
        button_width = rect.width - 2 * BUTTON_MARGIN
        button_style.draw_panel_header(surface, rect, "Actions", self.header_font)
        text_y = self._draw_message_box(
            surface, rect, button_width, rect.y + 40,
            [
                f"Firing Deck: {firing_deck_controller.transport_squad.name}",
                f"Select up to {firing_deck_controller.max_models} embarked model(s):",
            ],
            config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
        )
        for model in firing_deck_controller.choosable_models():
            label = f"[{'x' if model in firing_deck_controller.selected_models else ' '}] {model.profile.name}"
            model_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
            model_rect = self._draw_button(surface, model_rect, label)
            self._buttons.append((model_rect, lambda m=model: firing_deck_controller.toggle_model(m)))
            text_y = model_rect.bottom + BUTTON_GAP

        confirm_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
        confirm_rect = self._draw_button(surface, confirm_rect, "Confirm Selection", accent="confirm")
        self._buttons.append((confirm_rect, firing_deck_controller.confirm_model_selection))
        text_y = confirm_rect.bottom + BUTTON_GAP

        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, firing_deck_controller.cancel))

    def _draw_firing_deck_choose_weapon(self, surface, rect, firing_deck_controller):
        """Rule 24.14 step 2: for the current selected model, pick one of
        its ranged, non-[ONE SHOT] weapons - only reached when that model
        has 2+ eligible weapons (a single one is auto-picked)."""
        button_width = rect.width - 2 * BUTTON_MARGIN
        button_style.draw_panel_header(surface, rect, "Actions", self.header_font)
        text_y = self._draw_message_box(
            surface, rect, button_width, rect.y + 40,
            [f"Firing Deck: choose a weapon for {firing_deck_controller.acting_model.profile.name}"],
            config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
        )
        for weapon in firing_deck_controller.choosable_weapons():
            weapon_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
            weapon_rect = self._draw_button(surface, weapon_rect, weapon.name)
            self._buttons.append((weapon_rect, lambda w=weapon: firing_deck_controller.choose_weapon(w)))
            text_y = weapon_rect.bottom + BUTTON_GAP

        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, firing_deck_controller.cancel))

    def _draw_explosives_choose_model(self, surface, rect, button_width, explosives_controller):
        """Rule 15.05 (Explosives, Core Stratagem) step 1: the unit has more
        than one EXPLOSIVES/GRENADES model - pick which one throws."""
        button_style.draw_panel_header(surface, rect, "Actions", self.header_font)
        text_y = self._draw_message_box(
            surface, rect, button_width, rect.y + 40,
            [f"Explosives: {explosives_controller.acting_squad.name}", "Choose a model to throw the explosives - click it on the battlefield."],
            config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
        )
        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, explosives_controller.cancel))

    def _draw_explosives_choose_target(self, surface, rect, button_width, explosives_controller):
        """Rule 15.05 step 2: pick an unengaged enemy unit within 8" of, and
        visible to, the chosen model."""
        button_style.draw_panel_header(surface, rect, "Actions", self.header_font)
        text_y = self._draw_message_box(
            surface, rect, button_width, rect.y + 40,
            [f"Explosives: {explosives_controller.acting_model.profile.name}", "Choose an enemy unit to target - click it on the battlefield."],
            config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
        )
        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, explosives_controller.cancel))

    def _draw_greater_good_choose_target(self, surface, rect, button_width, greater_good_controller):
        """T'au Empire army rule (For The Greater Good): pick one visible,
        not-yet-Spotted enemy unit for this Observer unit to mark."""
        button_style.draw_panel_header(surface, rect, "Actions", self.header_font)
        text_y = self._draw_message_box(
            surface, rect, button_width, rect.y + 40,
            [f"Observer: {greater_good_controller.acting_squad.name}", "Choose an enemy unit to mark as Spotted - click it on the battlefield."],
            config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
        )
        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, greater_good_controller.cancel))

    def _draw_crushing_impact_choose_enemy(self, surface, rect, button_width, crushing_impact_controller):
        """Rule 15.06 (Crushing Impact) EFFECT step 1: pick an enemy unit
        engaged with your unit."""
        button_style.draw_panel_header(surface, rect, "Actions", self.header_font)
        self._draw_message_box(
            surface, rect, button_width, rect.y + 40,
            [f"Crushing Impact: {crushing_impact_controller.acting_squad.name}", "Choose an engaged enemy unit - click it on the battlefield."],
            config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
        )

    def _draw_crushing_impact_choose_model(self, surface, rect, button_width, crushing_impact_controller):
        """Rule 15.06 (Crushing Impact) EFFECT step 2: pick a model in your
        unit engaged with the chosen enemy unit."""
        button_style.draw_panel_header(surface, rect, "Actions", self.header_font)
        self._draw_message_box(
            surface, rect, button_width, rect.y + 40,
            [
                f"Crushing Impact: {crushing_impact_controller.acting_squad.name}",
                f"Target: {crushing_impact_controller.enemy_squad.name}",
                "Choose one of your models engaged with it - click it on the battlefield.",
            ],
            config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
        )

    def _draw_fire_overwatch_choose_unit(self, surface, rect, button_width, fire_overwatch_controller):
        """Rule 15.08 (Fire Overwatch, Core Stratagem) TARGET: pick one of
        this player's own eligible units to fire Snap Shooting (15.09).

        Real user report/redesign: this used to be a game.decision.
        DecisionManager text-button list, one row per eligible squad ("Fire
        Overwatch: Strike Team 1 (1 CP)") - with several same-name-but-
        numbered units on the board, there was no way to tell which button
        was which unit. Now board-click-driven instead, same shape as every
        other target picker in this file - the panel only needs the
        message and a Decline button; main.py highlights every one of
        fire_overwatch_controller.eligible_squads()'s units on the
        battlefield itself and routes a click on one of them to
        choose_unit()."""
        button_style.draw_panel_header(surface, rect, "Actions", self.header_font)
        text_y = self._draw_message_box(
            surface, rect, button_width, rect.y + 40,
            [
                "Fire Overwatch (1 CP)",
                "Choose one of your units to shoot using Snap Shooting - click it on the battlefield.",
            ],
            config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
        )
        decline_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
        decline_rect = self._draw_button(surface, decline_rect, "Decline", accent="danger")
        self._buttons.append((decline_rect, fire_overwatch_controller.decline))

    def _draw_epic_challenge_choose_model(self, surface, rect, button_width, epic_challenge_controller):
        """Rule 15.03 (Epic Challenge, Core Stratagem) EFFECT: the unit has
        more than one CHARACTER model - pick which one gains [PRECISION]."""
        button_style.draw_panel_header(surface, rect, "Actions", self.header_font)
        text_y = self._draw_message_box(
            surface, rect, button_width, rect.y + 40,
            [f"Epic Challenge: {epic_challenge_controller.acting_squad.name}", "Choose a CHARACTER model - click it on the battlefield."],
            config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
        )
        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, epic_challenge_controller.cancel))

    def _maybe_draw_epic_challenge_button(self, surface, rect, button_width, button_y, fight_controller, epic_challenge_controller):
        """Shared by the three fight-activation screens (choose target,
        choose weapon, split-fire assigning): offers "Epic Challenge (1CP)"
        for as long as that reading of rule 15.03's WHEN stays open (see
        EpicChallengeController's docstring) - returns the (possibly
        unchanged) button_y to keep stacking buttons below it."""
        if epic_challenge_controller is None or not epic_challenge_controller.can_use(fight_controller.fighting_squad):
            return button_y
        epic_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        epic_rect = self._draw_button(surface, epic_rect, "Epic Challenge (1CP)", accent="stratagem")
        self._buttons.append((epic_rect, lambda: epic_challenge_controller.start(fight_controller.fighting_squad)))
        return button_y + epic_rect.height + BUTTON_GAP

    def _draw_pile_in_pending(self, surface, rect, button_width, pile_in_controller, text_y):
        """Who the Fight step is still waiting on for Pile In (12.03), BY NAME.

        User: "ich finde es manchmal schwierig zu erkennen, dass ich noch mit
        allen einheiten pile in machen muss, bevor die KI weitermacht."
        Measured before changing anything: this spot printed exactly one
        sentence - "Both players must resolve Pile In (move or skip) for every
        eligible unit before the Fight step can begin." True, and useless: it
        names no unit, no side and no next step, so a game waiting on the
        HUMAN reads identically to one waiting on the AI. That is the whole
        report.

        Grouped by owner and listed by name rather than filtered down to "your
        units": the panel has no notion of which player is the human, and
        inventing one here would be a second copy of a fact main.py already
        owns (its human_players wiring). Squad names carry the owner's digit
        as their first character - the same identifier the turn banner, the
        turn plan and every log line use - so "Player 1: 1 Storm Guardians 1"
        answers "is it me?" without this file having to assume anything. It
        also stays correct if the human ever plays Player 2.

        In a box rather than as loose text: this is a thing to DO, and it sat
        in the same flat grey as the phase chatter around it."""
        pending = pile_in_controller.squads_pending_pile_in()
        by_owner = {}
        for squad in pending:
            by_owner.setdefault(squad.owner, []).append(squad.name)

        lines = [f"Pile In pending for {len(pending)} unit(s) - the Fight step cannot begin until "
                 f"each one has piled in or skipped (12.03)."]
        for owner in sorted(by_owner):
            names = by_owner[owner]
            # Capped, because this is a 220px column and an engaged blob can
            # be several units deep. The count above always tells the truth,
            # so a capped list never hides that something is outstanding.
            shown = names[:PILE_IN_NAMES_SHOWN]
            if len(names) > PILE_IN_NAMES_SHOWN:
                shown.append(f"+{len(names) - PILE_IN_NAMES_SHOWN} more")
            lines.append(f"{owner}: {', '.join(shown)}")
        lines.append("Select one on the battlefield, then Pile In or Skip Pile In.")

        return self._draw_message_box(
            surface, rect, button_width, text_y, lines,
            config.PANEL_TEXT_COLOR, PILE_IN_ACCENT_COLOR, bg_color=PILE_IN_BOX_BG_COLOR,
        )

    def _draw_fight_step_status(self, surface, rect, button_width, fight_controller, pile_in_controller, start_y=None):
        """Phase-wide Fight status (whose turn to select, or the Begin
        Fight Step / Pass buttons) - returns the y position right after
        whatever it drew, so a caller that also has a specific squad
        selected (see _draw_movement_ui()) can stack that squad's own UI
        below it instead of the two overlapping or one hiding the other."""
        text_y = rect.y + 40 if start_y is None else start_y
        if fight_controller.state == fight.NOT_STARTED:
            if pile_in_controller is not None and pile_in_controller.has_pending_squads():
                return self._draw_pile_in_pending(
                    surface, rect, button_width, pile_in_controller, text_y)
            text_y = self._draw_text(surface, rect, "Pile In resolved for every eligible squad.", text_y, gap=0)
            begin_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y + 10, button_width, BUTTON_HEIGHT)
            begin_rect = self._draw_button(surface, begin_rect, "Begin Fight Step", accent="confirm")
            self._buttons.append((begin_rect, fight_controller.begin_fight_step))
            return begin_rect.bottom + BUTTON_GAP
        elif fight_controller.state == fight.SELECTING:
            text = f"Fight: {fight_controller.whose_turn}'s turn to select a unit."
            text_y = self._draw_text(surface, rect, text, text_y, gap=7)
            if fight_controller.can_pass():
                pass_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
                pass_rect = self._draw_button(surface, pass_rect, "Pass (no eligible unit in range)")
                self._buttons.append((pass_rect, fight_controller.pass_fighting))
                text_y = pass_rect.bottom + BUTTON_GAP
            return text_y
        elif fight_controller.state == fight.DONE:
            return self._draw_text(surface, rect, "Fight step complete.", text_y, gap=0)
        return text_y

    def _draw_resolving(self, surface, rect, shooting_controller):
        hint = f"Resolving {shooting_controller.current_group['weapon_key']}…"
        self._draw_text(surface, rect, hint, rect.y + 40)

    def _draw_charge_declaring(self, surface, rect, button_width, charge_controller):
        button_y = self._draw_text(
            surface, rect, f"Charging: {charge_controller.active_squad.name}", rect.y + 40, gap=7,
        )
        if charge_controller.max_distance is None:
            self._draw_text(surface, rect, "Rolling charge distance…", button_y)
            return

        button_y = self._draw_text(surface, rect, f'Charge roll: {charge_controller.max_distance}"', button_y, gap=6)

        eligible = charge_controller.eligible_charge_target_squads()
        if not eligible:
            button_y = self._draw_text(
                surface, rect, "No enemy units in range - decline the charge.", button_y,
            )
        else:
            for target in eligible:
                label = f"[{'x' if target in charge_controller.charge_targets else ' '}] {target.name}"
                target_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                target_rect = self._draw_button(surface, target_rect, label)
                self._buttons.append((target_rect, lambda t=target: charge_controller.toggle_charge_target(t)))
                button_y += target_rect.height + BUTTON_GAP

            if charge_controller.charge_targets:
                begin_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                begin_rect = self._draw_button(surface, begin_rect, "Begin Charge Move", accent="confirm")
                self._buttons.append((begin_rect, charge_controller.begin_charge_move))
                button_y += begin_rect.height + BUTTON_GAP

        decline_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        decline_rect = self._draw_button(surface, decline_rect, "Decline Charge", accent="danger")
        self._buttons.append((decline_rect, charge_controller.decline_charge_move))

    def _draw_consolidate_declaring(self, surface, rect, button_width, consolidate_controller):
        button_y = self._draw_text(
            surface, rect, f"Consolidating: {consolidate_controller.active_squad.name}", rect.y + 40,
        )
        button_y = self._draw_text(
            surface, rect, "Engaging Consolidation - select target(s):", button_y, gap=8,
        )
        for target in consolidate_controller.eligible_engaging_targets(consolidate_controller.active_squad):
            label = f"[{'x' if target in consolidate_controller.targets else ' '}] {target.name}"
            target_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            target_rect = self._draw_button(surface, target_rect, label)
            self._buttons.append((target_rect, lambda t=target: consolidate_controller.toggle_engaging_target(t)))
            button_y += target_rect.height + BUTTON_GAP

        if consolidate_controller.targets:
            begin_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            begin_rect = self._draw_button(surface, begin_rect, "Begin Consolidation Move", accent="confirm")
            self._buttons.append((begin_rect, consolidate_controller.begin_engaging_move))
            button_y += begin_rect.height + BUTTON_GAP

        if consolidate_controller.can_switch_to_objective():
            # User report: "kann mich entscheiden in eine andere Einheit
            # reinzuconsolidaten, aber mir fehlt die Entscheidung das nicht
            # zu tun und mich stattdessen auf ein Objective zu bewegen" -
            # Engaging is still offered first (determine_mode()'s priority
            # order), but qualifying for it shouldn't make Objective
            # Consolidation unreachable when the squad qualifies for both.
            objective_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            objective_rect = self._draw_button(surface, objective_rect, "Move to Objective Instead")
            self._buttons.append((objective_rect, consolidate_controller.switch_to_objective_consolidation))
            button_y += objective_rect.height + BUTTON_GAP

        decline_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        decline_rect = self._draw_button(surface, decline_rect, "Decline Consolidation", accent="danger")
        self._buttons.append((decline_rect, consolidate_controller.decline_consolidate))

    def _draw_consolidate_choose_objective(self, surface, rect, button_width, consolidate_controller):
        """Rule 12.08 BEFORE MOVING (Objective Consolidation): pick exactly
        one of 2+ objectives within 3" - only reached when there's a real
        choice (start_consolidate() auto-picks a sole candidate). Objectives
        aren't board tokens, so - unlike Engaging's target list - this is a
        panel-only choice, clicking a name immediately proceeds (like
        _draw_choose_shooting_type), no separate "Begin Move" step needed
        since only one objective is ever selected."""
        button_y = self._draw_text(
            surface, rect, f"Consolidating: {consolidate_controller.active_squad.name}", rect.y + 40,
        )
        button_y = self._draw_text(
            surface, rect, "Objective Consolidation - select an objective:", button_y, gap=8,
        )
        for objective in consolidate_controller.choosable_objectives():
            obj_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            obj_rect = self._draw_button(surface, obj_rect, objective.name)
            self._buttons.append((obj_rect, lambda o=objective: consolidate_controller.choose_objective(o)))
            button_y += obj_rect.height + BUTTON_GAP

        decline_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        decline_rect = self._draw_button(surface, decline_rect, "Decline Consolidation", accent="danger")
        self._buttons.append((decline_rect, consolidate_controller.decline_consolidate))

    def _draw_fall_back_choosing_mode(self, surface, rect, button_width, fall_back_controller):
        """Rule 09.07 BEFORE MOVING: pick Ordered Retreat or Desperate
        Escape - only reached when there's a real choice (declare() skips
        straight to Desperate Escape for a battle-shocked unit, same
        pattern as _draw_consolidate_choose_objective() above). Clicking a
        name immediately starts the move, no separate "Begin Move" step."""
        button_y = self._draw_text(
            surface, rect, f"Falling Back: {fall_back_controller.acting_squad.name}", rect.y + 40,
        )
        button_y = self._draw_text(surface, rect, "Choose a Fall Back mode:", button_y, gap=8)
        retreat_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        retreat_rect = self._draw_button(surface, retreat_rect, "Ordered Retreat")
        self._buttons.append((retreat_rect, lambda: fall_back_controller.choose_mode(fall_back.ORDERED_RETREAT)))
        button_y += retreat_rect.height + BUTTON_GAP

        escape_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        escape_rect = self._draw_button(surface, escape_rect, "Desperate Escape")
        self._buttons.append((escape_rect, lambda: fall_back_controller.choose_mode(fall_back.DESPERATE_ESCAPE)))
        button_y += escape_rect.height + BUTTON_GAP

        decline_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        decline_rect = self._draw_button(surface, decline_rect, "Cancel", accent="danger")
        self._buttons.append((decline_rect, fall_back_controller.decline))

    def _draw_fight_choose_target(self, surface, rect, button_width, fight_controller, epic_challenge_controller=None):
        button_y = self._draw_text(
            surface, rect, f"Fighting: {fight_controller.fighting_squad.name}", rect.y + 40, gap=7,
        )
        button_y = self._maybe_draw_epic_challenge_button(
            surface, rect, button_width, button_y, fight_controller, epic_challenge_controller,
        )
        split_label = "Split Fire: On" if fight_controller.split_fire else "Split Fire: Off"
        split_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        split_rect = self._draw_button(surface, split_rect, split_label)
        self._buttons.append((split_rect, fight_controller.toggle_split_fire))
        button_y += split_rect.height + BUTTON_GAP

        if fight_controller.split_fire:
            start_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            start_rect = self._draw_button(surface, start_rect, "Start Assignment")
            self._buttons.append((start_rect, fight_controller.begin_assignment))
            button_y += start_rect.height + BUTTON_GAP
            hint = "Then assign each model/weapon its own engaged target individually."
            button_y = self._draw_text(surface, rect, hint, button_y + 6, gap=0)
        else:
            button_y = self._draw_text(surface, rect, "Choose an engaged enemy unit:", button_y, gap=10)
            for target in fight_controller.engaged_enemy_squads(fight_controller.fighting_squad):
                target_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                target_rect = self._draw_button(surface, target_rect, target.name)
                self._buttons.append((target_rect, lambda t=target: fight_controller.choose_target_squad(t)))
                button_y += target_rect.height + BUTTON_GAP

        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, fight_controller.cancel))

    def _draw_fight_assigning(self, surface, rect, button_width, fight_controller, epic_challenge_controller=None):
        current = fight_controller.current_assignment()
        remaining = len(fight_controller.assignment_queue)
        if current is not None:
            model, weapon = current
            hint = f"Choose a target for {model.profile.name} ({weapon.name}) - {remaining} left to assign."
        else:
            hint = "All weapons assigned."

        text_y = self._draw_text(surface, rect, hint, rect.y + 40, gap=10)
        text_y = self._maybe_draw_epic_challenge_button(
            surface, rect, button_width, text_y, fight_controller, epic_challenge_controller,
        )

        # Same rule 04.01 basis as the shooting panel's pair above.
        if current is not None:
            skip_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
            skip_rect = self._draw_button(surface, skip_rect, f"Don't attack with {current[1].name}")
            self._buttons.append((skip_rect, fight_controller.skip_current))
            text_y = skip_rect.bottom + BUTTON_GAP

            if remaining > 1:
                rest_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
                rest_rect = self._draw_button(surface, rest_rect, f"Attack assigned, skip rest ({remaining})")
                self._buttons.append((rest_rect, fight_controller.finish_assignment))
                text_y = rest_rect.bottom + BUTTON_GAP

        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, fight_controller.cancel))

    def _draw_fight_weapon_choice(self, surface, rect, button_width, fight_controller, epic_challenge_controller=None):
        button_y = self._draw_text(
            surface, rect, f"Target: {fight_controller.target_squad.name}", rect.y + 40, gap=7,
        )
        button_y = self._maybe_draw_epic_challenge_button(
            surface, rect, button_width, button_y, fight_controller, epic_challenge_controller,
        )
        for weapon_key, weapon_label, eligible, total in fight_controller.weapon_eligibility():
            label = f"{weapon_label} ({eligible}/{total})"
            weapon_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            weapon_rect = self._draw_button(surface, weapon_rect, label)
            self._buttons.append((weapon_rect, lambda w=weapon_key: fight_controller.choose_weapon(w)))
            button_y += weapon_rect.height + BUTTON_GAP

        stop_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        stop_rect = self._draw_button(surface, stop_rect, "Stop Fighting")
        self._buttons.append((stop_rect, fight_controller.stop_fighting))
        button_y += stop_rect.height + BUTTON_GAP

        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, fight_controller.cancel))

    def _draw_choose_shooting_type(self, surface, rect, button_width, shooting_controller):
        button_y = self._draw_text(
            surface, rect, f"Shooting: {shooting_controller.active_squad.name}", rect.y + 40,
        )
        button_y = self._draw_text(surface, rect, "Select a shooting type:", button_y, gap=8)
        for shooting_type in shooting_controller.available_types:
            type_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            type_rect = self._draw_button(surface, type_rect, shooting_type)
            self._buttons.append((type_rect, lambda t=shooting_type: shooting_controller.choose_shooting_type(t)))
            button_y += type_rect.height + BUTTON_GAP

        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, shooting_controller.cancel))

    def _draw_choose_target(self, surface, rect, button_width, shooting_controller):
        button_y = self._draw_text(
            surface, rect, f"Shooting: {shooting_controller.active_squad.name}", rect.y + 40, gap=7,
        )
        # Rule 15.09: Snap Shooting can only ever target one unit - no
        # split-fire toggle to offer at all (start_snap_shooting() already
        # forces split_fire off).
        if shooting_controller.shooting_type == shooting.SNAP_SHOOTING:
            hint = "Snap Shooting: click a visible enemy unit within 24\" on the battlefield."
        else:
            split_label = "Split Fire: On" if shooting_controller.split_fire else "Split Fire: Off"
            split_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            split_rect = self._draw_button(surface, split_rect, split_label)
            self._buttons.append((split_rect, shooting_controller.toggle_split_fire))
            button_y += split_rect.height + BUTTON_GAP

            if shooting_controller.split_fire:
                start_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                start_rect = self._draw_button(surface, start_rect, "Start Assignment")
                self._buttons.append((start_rect, shooting_controller.begin_assignment))
                button_y += start_rect.height + BUTTON_GAP
                hint = "Then assign each model/weapon its own target individually."
            else:
                hint = "Click a target squad on the battlefield."

        text_y = self._draw_text(surface, rect, hint, button_y + 6, gap=0)

        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y + 10, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, shooting_controller.cancel))

    def _draw_weapon_choice(self, surface, rect, button_width, shooting_controller):
        button_y = self._draw_text(
            surface, rect, f"Target: {shooting_controller.target_squad.name}", rect.y + 40, gap=7,
        )
        for weapon_key, weapon_label, eligible, total, overcharge_label in shooting_controller.weapon_eligibility():
            label = f"{weapon_label} ({eligible}/{total})"
            weapon_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            weapon_rect = self._draw_button(surface, weapon_rect, label)
            self._buttons.append((weapon_rect, lambda w=weapon_key: shooting_controller.choose_weapon(w)))
            button_y += weapon_rect.height + BUTTON_GAP

            if overcharge_label is not None:
                button_text = f"{overcharge_label} [HAZARDOUS] ({eligible}/{total})"
                overcharge_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                overcharge_rect = self._draw_button(surface, overcharge_rect, button_text, accent="danger")
                self._buttons.append((overcharge_rect, lambda w=weapon_key: shooting_controller.choose_weapon(w, overcharge=True)))
                button_y += overcharge_rect.height + BUTTON_GAP

        stop_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        stop_rect = self._draw_button(surface, stop_rect, "Stop Shooting")
        self._buttons.append((stop_rect, shooting_controller.stop_shooting))
        button_y += stop_rect.height + BUTTON_GAP

        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, shooting_controller.cancel))

    def _draw_assigning(self, surface, rect, button_width, shooting_controller):
        current = shooting_controller.current_assignment()
        remaining = len(shooting_controller.assignment_queue)
        overcharge_label = shooting_controller.current_assignment_overcharge_label()
        armed = shooting_controller.assignment_overcharge
        if current is not None:
            model, weapon = current
            mode = overcharge_label if (overcharge_label is not None and armed) else weapon.name
            hint = f"Choose a target for {model.profile.name} ({mode}) - {remaining} left to assign."
        else:
            hint = "All weapons assigned."

        text_y = self._draw_text(surface, rect, hint, rect.y + 40, gap=0)

        # This weapon has a second firing mode (e.g. Cyclic Ion Raker
        # Overcharge). The non-split flow offers it as a second weapon button,
        # but here the TARGET is clicked on the battlefield - so the mode is a
        # toggle armed before that click, and it disarms itself after every
        # assignment (see toggle_assignment_overcharge()).
        if current is not None and overcharge_label is not None:
            text_y += 6
            mode_label = f"Mode: {overcharge_label} [HAZARDOUS]" if armed else f"Mode: {current[1].name}"
            mode_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
            mode_rect = self._draw_button(
                surface, mode_rect, mode_label, accent="danger" if armed else None,
            )
            self._buttons.append((mode_rect, shooting_controller.toggle_assignment_overcharge))
            text_y = mode_rect.bottom + BUTTON_GAP

        # Rule 04.01 allows firing "one or more" weapons, not all of them.
        # The non-split flow has always had "Stop Shooting" for that; split
        # fire had nothing, so every queued weapon had to be given a target
        # and Cancel (which fires nothing at all) was the only way out.
        if current is not None:
            text_y += 6
            skip_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
            skip_rect = self._draw_button(surface, skip_rect, f"Don't fire {current[1].name}")
            self._buttons.append((skip_rect, shooting_controller.skip_current))
            text_y = skip_rect.bottom + BUTTON_GAP

            if remaining > 1:
                rest_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y, button_width, BUTTON_HEIGHT)
                rest_rect = self._draw_button(surface, rest_rect, f"Fire assigned, skip rest ({remaining})")
                self._buttons.append((rest_rect, shooting_controller.finish_assignment))
                text_y = rest_rect.bottom + BUTTON_GAP

        cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, text_y + 10, button_width, BUTTON_HEIGHT)
        cancel_rect = self._draw_button(surface, cancel_rect, "Cancel", accent="danger")
        self._buttons.append((cancel_rect, shooting_controller.cancel))

    def _draw_movement_ui(
        self, surface, rect, button_width, movement_controller, shooting_controller,
        charge_controller=None, pile_in_controller=None, fight_controller=None, consolidate_controller=None,
        retro_thrusters_controller=None,
        battle_shock_controller=None, explosives_controller=None, transport_controller=None,
        insane_bravery_controller=None, crushing_impact_controller=None, firing_deck_controller=None,
        greater_good_controller=None, fall_back_controller=None, arrokon_controller=None,
        torchstar_controller=None, unbridled_carnage_controller=None, ere_we_go_controller=None,
        tactical_acumen_controller=None,
        flickerjump_controller=None,
        battle_focus_pool=None,
        # Appended, not slotted in: draw() forwards everything above positionally.
        sudden_storm_controller=None,
        conquering_tyrant_controller=None,
        hungry_void_controller=None,
        path_of_the_outcast_controller=None,
        fire_and_fade_controller=None,
        chronometron_controller=None,
        overflight_controller=None,
        higher_duty_controller=None,
        warhost_fire_and_fade_controller=None,
        targeting_array_controller=None,
        # Appended by keyword like everything above - see draw()'s own warning.
        secondary_mission_controller=None,
        primary_mission_controller=None,
        unmodified_six_controller=None,
        # Death Lord's Chosen - the three a human buys proactively. Appended
        # BY KEYWORD: this chain is positional up to battle_focus_pool, and
        # inserting a parameter mid-signature has silently shifted every
        # argument after it before.
        blooming_pestilence_controller=None,
        grim_reapers_controller=None,
        mortarions_teachings_controller=None,
        # ONE parameter for every proactive detachment Stratagem, instead of one
        # per Stratagem. See game/proactive_stratagems.py: the T'au detachments
        # alone add nineteen, and this chain is positional for most of its
        # length. A controller joins the list and needs no edit here.
        proactive_stratagems=None,
        return_placement_controller=None,
    ):
        squad = movement_controller.selected_squad
        turn_tracker = movement_controller.turn_tracker
        in_fight_phase = fight_controller is not None and turn_tracker is not None and turn_tracker.phase == PHASE_FIGHT

        if squad is None:
            if in_fight_phase:
                self._draw_fight_step_status(surface, rect, button_width, fight_controller, pile_in_controller)
            else:
                # With nothing picked this column was completely empty except
                # for the header and the toggle strip - the same 220 px of
                # nothing the player gets after clicking into the void, which
                # reads like the game stopped rather than like a state they can
                # leave. Same reason _draw_fight_step_status exists one line
                # up, which was added after a real "the AI just froze" report.
                text_y = self._draw_text(surface, rect, "No unit selected.", rect.y + 40, gap=8)
                self._draw_text(surface, rect,
                                "Click one of your models to select its unit. "
                                "Click empty ground or press ESC to let go.",
                                text_y, gap=4)
            return

        text_y = rect.y + 40
        if in_fight_phase:
            # Real user-reported confusion ("the AI just stopped doing
            # anything"): this phase-wide "whose turn to select a unit"/Pass
            # status used to only render while NOTHING was selected - with a
            # squad still selected from an earlier Charge/Pile In (the
            # ordinary case once a unit is done acting), it was completely
            # hidden, so an entirely normal "waiting on the human's own
            # Fight-phase turn" looked exactly like the AI had silently
            # frozen. Now always shown during the Fight phase, stacked above
            # the selected squad's own status/buttons instead of one hiding
            # the other.
            text_y = self._draw_fight_step_status(surface, rect, button_width, fight_controller, pile_in_controller, start_y=text_y)
            text_y += 10

        # No portrait and no name here any more: _draw_selection_header() has
        # already drawn both, in its own box at the top of this column, and it
        # is the SAME squad - this branch's `squad` IS
        # movement_controller.selected_squad. Printing them twice was costing
        # ~70px of a 220px column to say the thing directly above it says.
        #
        # The other three _draw_unit_portrait() calls in this file stay: each
        # names a DIFFERENT unit (the Declare-Battle-Formations queue's current
        # unit, the pre-game pool's picked card, the unit being set up), none
        # of which is the selection.
        button_y = text_y + 4

        if movement_controller.state == movement.MOVING:
            is_charge = movement_controller.move_mode == "charge"
            is_pile_in = movement_controller.move_mode == "pile_in"
            is_consolidate = movement_controller.move_mode == "consolidate"
            # THE BASE-CONTACT HOUSE RULE, said out loud. Those models simply
            # will not pick up, and a control that refuses in silence is a bug
            # in itself - the board rings them, and this says why.
            if is_pile_in or is_consolidate:
                _frozen = base_contact.frozen_models(
                    movement_controller.selected_squad,
                    movement_controller.all_tokens, movement_controller.move_mode)
                if _frozen:
                    text_y = self._draw_text(
                        surface, rect,
                        "%d model(s) are in base contact and cannot be moved "
                        "(house rule)." % len(_frozen),
                        text_y, color=HINT_COLOR)
            is_surge = movement_controller.move_mode == "surge"
            is_fall_back = movement_controller.move_mode == "fall_back"
            # The Torchstar Gambit's own Normal move (1CP, Shooting phase):
            # Confirm goes through its controller because the stratagem's
            # no-charge restriction is conditional on the move actually being
            # made - see TorchstarGambitController.confirm_move().
            is_torchstar = movement_controller.move_mode == "torchstar"
            # Asurmen's Tactical Acumen, the same post-shooting Normal move with
            # its own controller - its "if it does" charge lock is likewise
            # conditional on the move actually being confirmed.
            is_tactical_acumen = movement_controller.move_mode == "tactical_acumen"
            is_battle_focus_move = movement_controller.move_mode == "battle_focus"  # Aeldari Opportunity Seized / Fade Back, granted in the opponent's turn
            # Rangers' Path of the Outcast - the OTHER reactive move (see
            # MovementController.REACTIVE_MOVE_MODES). It owns two consequences
            # the bare movement controller knows nothing about: handing
            # turn_tracker.active_player back to whoever's turn it actually is
            # (the move happens in the opponent's), and clearing its own
            # once-per-turn/busy state. Without this branch Confirm fell
            # through to the generic movement_controller.confirm_move() and
            # neither ever happened - the move looked confirmed and left the
            # active player stranded on the reacting side.
            is_path_of_the_outcast = movement_controller.move_mode == path_of_the_outcast.PATH_OF_THE_OUTCAST_MOVE_MODE
            # The Kroot Lone-Spear's Fire and Fade - Tactical Acumen's twin
            # (a post-shooting Normal move whose charge lock is likewise
            # conditional on the move actually being confirmed), so it needs
            # its own branch for exactly the same reason.
            is_fire_and_fade = movement_controller.move_mode == fire_and_fade.FIRE_AND_FADE_MOVE_MODE
            # The Chronomancer's Chronometron - Fire and Fade's third twin,
            # and here for the same reason: its charge lock is applied "if
            # it does", so only a CONFIRMED move may set it.
            is_chronometron = (movement_controller.move_mode
                               == chronometron.CHRONOMETRON_MOVE_MODE)
            # Windrider Host's Overflight - the THIRD reactive move (see
            # MovementController.REACTIVE_MOVE_MODES). Its printed WHEN says
            # "the end of THE Fight phase", which belongs to nobody, so the
            # move can be taken in the opponent's turn; like Path of the
            # Outcast it therefore holds active_player while the move is open
            # and needs its own branch to hand it back. Nothing else about it
            # is special - it locks nothing out, so without that hand-off the
            # generic confirm_move() would have done.
            is_overflight = movement_controller.move_mode == windrider_overflight.OVERFLIGHT_MOVE_MODE
            # Spirit Conclave's Higher Duty - reactive in the same way, so it
            # needs the same hand-back branch. See game/enh_higher_duty.py.
            is_higher_duty = movement_controller.move_mode == enh_higher_duty.HIGHER_DUTY_MOVE_MODE
            # Warhost's Fire and Fade - NOT reactive (its WHEN is "your
            # Shooting phase", so the mover is the turn owner and select()
            # accepts it). It needs a branch only because its two locks -
            # charge AND embark - are applied "if it does", i.e. only once the
            # move is actually confirmed. Same reason as Tactical Acumen and
            # the Kroot ability of the same printed name.
            is_warhost_fire_and_fade = (
                movement_controller.move_mode
                == warhost_fire_and_fade.WARHOST_FIRE_AND_FADE_MOVE_MODE)
            confirm_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            confirm_rect = self._draw_button(surface, confirm_rect, "Confirm", accent="confirm")
            if is_charge:
                confirm_callback = charge_controller.confirm_charge_move
            elif is_pile_in:
                confirm_callback = pile_in_controller.confirm_pile_in
            elif is_consolidate:
                confirm_callback = consolidate_controller.confirm_consolidate
            elif is_fall_back:
                confirm_callback = fall_back_controller.confirm
            elif is_battle_focus_move and battle_focus_pool is not None:
                confirm_callback = battle_focus_pool.confirm_reactive_move
            elif is_path_of_the_outcast and path_of_the_outcast_controller is not None:
                confirm_callback = path_of_the_outcast_controller.confirm_move
            elif is_torchstar and torchstar_controller is not None:
                confirm_callback = torchstar_controller.confirm_move
            elif is_tactical_acumen and tactical_acumen_controller is not None:
                confirm_callback = tactical_acumen_controller.confirm_move
            elif is_fire_and_fade and fire_and_fade_controller is not None:
                confirm_callback = fire_and_fade_controller.confirm_move
            elif is_chronometron and chronometron_controller is not None:
                confirm_callback = chronometron_controller.confirm_move
            elif is_overflight and overflight_controller is not None:
                confirm_callback = overflight_controller.confirm_move
            elif is_higher_duty and higher_duty_controller is not None:
                confirm_callback = higher_duty_controller.confirm_move
            elif is_warhost_fire_and_fade and warhost_fire_and_fade_controller is not None:
                confirm_callback = warhost_fire_and_fade_controller.confirm_move
            else:
                confirm_callback = movement_controller.confirm_move
            self._buttons.append((confirm_rect, confirm_callback))
            button_y += confirm_rect.height + BUTTON_GAP

            # One question, one answer - see MovementController.can_advance().
            # This used to be a hand-maintained list of negated move modes, and
            # a list that has to grow with every new mode grows wrong: "scout"
            # was missing from it, so the moment the pre-game gate above stopped
            # swallowing this screen, a Scout Move would have been offered an
            # Advance that rule 24.32 does not grant.
            if movement_controller.can_advance():
                run_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                run_rect = self._draw_button(surface, run_rect, "Advance")
                self._buttons.append((run_rect, movement_controller.start_run))
                button_y += run_rect.height + BUTTON_GAP

            if movement_controller.can_take_to_the_skies():
                fly_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                fly_rect = self._draw_button(surface, fly_rect, "Take to the Skies")
                self._buttons.append((fly_rect, movement_controller.take_to_the_skies))
                button_y += fly_rect.height + BUTTON_GAP

            if is_charge:
                # Real user report: a single "Cancel" used to always finish
                # the whole charge attempt (rule 11.02 - can't declare a
                # charge again this phase), even when all the player wanted
                # was to redo their positioning for the SAME roll/targets.
                # This one only undoes the drag (charge_controller.
                # reset_charge_move() - the roll/targets survive, "Begin
                # Charge Move" can be clicked again); "Decline Charge" below
                # remains the full abandon.
                reset_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                reset_rect = self._draw_button(surface, reset_rect, "Reset Movement")
                self._buttons.append((reset_rect, charge_controller.reset_charge_move))
                button_y += reset_rect.height + BUTTON_GAP

            cancel_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
            cancel_rect = self._draw_button(surface, cancel_rect, "Decline Charge" if is_charge else "Cancel", accent="danger")
            if is_charge:
                cancel_callback = charge_controller.decline_charge_move
            elif is_pile_in:
                cancel_callback = pile_in_controller.decline_pile_in
            elif is_consolidate:
                cancel_callback = consolidate_controller.decline_consolidate
            elif is_fall_back:
                cancel_callback = fall_back_controller.decline
            elif is_battle_focus_move and battle_focus_pool is not None:
                cancel_callback = battle_focus_pool.cancel_reactive_move
            elif is_path_of_the_outcast and path_of_the_outcast_controller is not None:
                cancel_callback = path_of_the_outcast_controller.cancel_move
            elif is_fire_and_fade and fire_and_fade_controller is not None:
                cancel_callback = fire_and_fade_controller.cancel_move
            elif is_chronometron and chronometron_controller is not None:
                cancel_callback = chronometron_controller.cancel_move
            elif is_overflight and overflight_controller is not None:
                cancel_callback = overflight_controller.cancel_move
            elif is_higher_duty and higher_duty_controller is not None:
                cancel_callback = higher_duty_controller.cancel_move
            elif is_warhost_fire_and_fade and warhost_fire_and_fade_controller is not None:
                cancel_callback = warhost_fire_and_fade_controller.cancel_move
            elif is_torchstar and torchstar_controller is not None:
                cancel_callback = torchstar_controller.cancel_move
            elif is_tactical_acumen and tactical_acumen_controller is not None:
                cancel_callback = tactical_acumen_controller.cancel_move
            else:
                cancel_callback = movement_controller.cancel_move
            self._buttons.append((cancel_rect, cancel_callback))
            button_y += cancel_rect.height + BUTTON_GAP
        else:
            can_remain_stationary = movement_controller.can_move(squad)
            can_normal_move = movement_controller.can_make_move(squad)
            can_fall_back_now = fall_back_controller is not None and movement_controller.can_make_fall_back_move(squad)
            can_shoot_now = shooting_controller.can_shoot(squad)
            can_charge_now = charge_controller is not None and charge_controller.can_declare_charge(squad)
            can_pile_in_now = pile_in_controller is not None and pile_in_controller.can_pile_in(squad)
            can_fight_now = fight_controller is not None and fight_controller.can_select_to_fight(squad)
            can_consolidate_now = (
                consolidate_controller is not None and consolidate_controller.can_consolidate(squad)
                and consolidate_controller.determine_mode(squad) is not None
            )
            # The Twin Lance's Retro-thrusters: "at the end of the Fight
            # phase" - can_use() enforces the "was eligible to fight this
            # phase" latch, and available_moves() drops the Normal-move half
            # for a unit still engaged (it could never end unengaged).
            retro_moves = (
                retro_thrusters_controller.available_moves(squad)
                if retro_thrusters_controller is not None else []
            )
            can_battle_shock_now = battle_shock_controller is not None and battle_shock_controller.can_roll(squad)
            can_explosives_now = explosives_controller is not None and explosives_controller.can_use(squad)
            # Retaliation Cadre's The Arro'kon Protocol. ONE call for both the
            # button and its label: can_use() ends IN best_available_tier(), so
            # asking both (as this did) ran the same has_valid_target() sweep
            # per candidate enemy unit TWICE per frame - measured at up to
            # 660 ms each on a 179-model board. offer_tier() is that one sweep;
            # a non-zero tier IS "can use", so the two can no longer disagree.
            arrokon_tier = arrokon_controller.offer_tier(squad) if arrokon_controller is not None else 0
            can_arrokon_now = arrokon_tier > 0
            # Every proactive detachment Stratagem on offer for this unit, as
            # (label, callback). Asked once here rather than per Stratagem so
            # the panel never learns their names - see
            # game/proactive_stratagems.py.
            detachment_stratagem_buttons = (
                proactive_stratagems.buttons_for(squad)
                if proactive_stratagems is not None else []
            )
            # Seer Council's three proactive Stratagems used to be three more
            # parameters here, each repeated at all three stages of this
            # signature chain - they simply predate
            # game/proactive_stratagems.py. They are on the registry now, so
            # they arrive in detachment_stratagem_buttons above like every
            # other one, and the "nothing to do here" hint below finally
            # accounts for them.
            can_crushing_impact_now = crushing_impact_controller is not None and crushing_impact_controller.can_use(squad)
            # War Horde's Unbridled Carnage: can_use() already refuses for a
            # unit that cannot fight this phase, so the button never offers a
            # CP burn that would buy nothing.
            can_unbridled_carnage_now = (
                unbridled_carnage_controller is not None and unbridled_carnage_controller.can_use(squad)
            )
            # War Horde's 'Ere We Go: can_use() enforces "start of your
            # Movement phase" itself (nothing of yours has moved yet), so the
            # button simply disappears once the phase is under way.
            can_ere_we_go_now = ere_we_go_controller is not None and ere_we_go_controller.can_use(squad)
            # Awakened Dynasty's three proactive protocols. Each can_use()
            # carries its own WHEN (the phase, whose it is, and whether the
            # unit has already shot/fought), so a button appears exactly when
            # the Stratagem is legal and vanishes otherwise.
            can_sudden_storm_now = (
                sudden_storm_controller is not None and sudden_storm_controller.can_use(squad)
            )
            can_conquering_tyrant_now = (
                conquering_tyrant_controller is not None and conquering_tyrant_controller.can_use(squad)
            )
            can_hungry_void_now = (
                hungry_void_controller is not None and hungry_void_controller.can_use(squad)
            )
            # The three Death Lord's Chosen Stratagems a human buys proactively.
            # The other three are deliberately not offered here: Undying Spite
            # and Sickening Impact are REACTIVE (they arrive as a
            # DecisionManager prompt at their own moment), and Signal Pox needs
            # a LORD OF VIRULENCE model, which no datasheet here has.
            can_blooming_pestilence_now = (
                blooming_pestilence_controller is not None
                and blooming_pestilence_controller.can_use(squad)
            )
            can_grim_reapers_now = (
                grim_reapers_controller is not None and grim_reapers_controller.can_use(squad)
            )
            can_mortarions_teachings_now = (
                mortarions_teachings_controller is not None
                and mortarions_teachings_controller.can_use(squad)
            )
            # Warp Spiders' Flickerjump: same "has to be pressed before the
            # move" reason as 'Ere We Go above - MovementController reads the
            # Move characteristic once, when the move starts.
            can_flickerjump_now = (
                flickerjump_controller is not None and flickerjump_controller.can_use(squad)
            )
            can_mark_spotted_now = (
                greater_good_controller is not None and greater_good_controller.can_use(squad, shooting_controller)
            )

            embark_transport = None
            if transport_controller is not None:
                eligible = transport_controller.eligible_transports(squad)
                embark_transport = eligible[0] if eligible else None
            disembark_passengers = []
            if transport_controller is not None and squad.models and squad.models[0].profile.transport:
                disembark_passengers = [
                    s for s in transport_controller.embarked_squads_in(squad.models[0])
                    if transport_controller.can_disembark(s)
                ]

            if can_battle_shock_now:
                shock_reasons = []
                if squad.battle_shocked:
                    shock_reasons.append("shocked")
                if is_at_half_strength(squad):
                    shock_reasons.append("half-strength")
                shock_label = "Battle-Shock Roll" + (f" ({', '.join(shock_reasons)})" if shock_reasons else "")
                shock_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                shock_rect = self._draw_button(surface, shock_rect, shock_label)
                self._buttons.append((shock_rect, lambda: battle_shock_controller.start_roll(squad)))
                button_y += shock_rect.height + BUTTON_GAP

                if insane_bravery_controller is not None:
                    # User: "Insane bravery wird manchmal nicht angeboted."
                    # It was never broken - four different clauses could each
                    # remove the button (spent, 15.01's same-squad rule, CP,
                    # or the unit no longer owing a roll) and none said so. A
                    # HINT LINE rather than a greyed-out button, deliberately:
                    # this file states the opposite convention in three places
                    # ("no chrome for a control that cannot do anything"), and
                    # button_style.draw_button() has no disabled state - adding
                    # one would be a new visual language in a module every
                    # screen reads, to say what one line of prose says better.
                    bravery_ok, bravery_why = insane_bravery_controller.why_not(squad)
                    if bravery_ok:
                        bravery_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                        bravery_rect = self._draw_button(surface, bravery_rect, "Insane Bravery (1CP)", accent="stratagem")
                        self._buttons.append((bravery_rect, lambda: insane_bravery_controller.use(squad)))
                        button_y += bravery_rect.height + BUTTON_GAP
                    elif bravery_why:
                        button_y = self._draw_text(
                            surface, rect, f"Insane Bravery (1CP): {bravery_why}",
                            button_y, color=HINT_COLOR, gap=BUTTON_GAP)

            # Drawn above "Move"/"Advance" because its WHEN is the start of
            # the phase: once anything has moved the window is shut, so the
            # buttons are offered in the order they have to be used in.
            if can_flickerjump_now:
                flicker_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                flicker_rect = self._draw_button(
                    surface, flicker_rect,
                    'Flickerjump - Move 24", no charge, D6 per model at end of phase',
                )
                self._buttons.append((flicker_rect, lambda: flickerjump_controller.use(squad)))
                button_y += flicker_rect.height + BUTTON_GAP

            if can_ere_we_go_now:
                ere_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                ere_rect = self._draw_button(
                    surface, ere_rect, "'Ere We Go (1 CP) - +2 Advance and Charge rolls", accent="stratagem",
                )
                self._buttons.append((ere_rect, lambda: ere_we_go_controller.use(squad)))
                button_y += ere_rect.height + BUTTON_GAP

            # Sudden Storm is bought in the Movement phase, so it belongs with
            # the other before-you-move buttons: its [ASSAULT] grant is what
            # makes Advancing and still shooting possible.
            if can_sudden_storm_now:
                storm_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                storm_rect = self._draw_button(
                    surface, storm_rect,
                    "Sudden Storm (1 CP) - ranged weapons gain [ASSAULT] this turn",
                    accent="stratagem",
                )
                self._buttons.append((storm_rect, lambda: sudden_storm_controller.use(squad)))
                button_y += storm_rect.height + BUTTON_GAP

            # Conquering Tyrant is bought before shooting, for the same reason.
            if can_conquering_tyrant_now:
                tyrant_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                tyrant_rect = self._draw_button(
                    surface, tyrant_rect,
                    "Conquering Tyrant (1 CP) - re-roll Hit rolls of 1 within half range",
                    accent="stratagem",
                )
                self._buttons.append((tyrant_rect, lambda: conquering_tyrant_controller.use(squad)))
                button_y += tyrant_rect.height + BUTTON_GAP

            # Aeldari Battle Focus (army rule): the Agile Manoeuvres this unit
            # could perform right now, each costing one Battle Focus token
            # rather than CP - which is why they are turquoise and not the
            # Stratagem violet (user: "colorcode fuer agile manouvers ... soll
            # aber tuerkis sein"). The pool's own can_*() methods carry each
            # manoeuvre's TRIGGER, so a button appears exactly when the rule
            # allows it - Star Engines only after the unit has really
            # Advanced, which is why it can sit below "Advance" while the
            # other two sit above it. The token count is in the label because
            # the pool is a shared, per-round resource and the decision is
            # "is this worth one of my four".
            if battle_focus_pool is not None and squad is not None:
                tokens_left = battle_focus_pool.tokens.get(squad.owner, 0)
                manoeuvres = (
                    (battle_focus_pool.can_swift_as_the_wind,
                     battle_focus_pool.use_swift_as_the_wind,
                     "Swift as the Wind - +2\" Move this phase"),
                    (battle_focus_pool.can_flitting_shadows,
                     battle_focus_pool.use_flitting_shadows,
                     "Flitting Shadows - no Fire Overwatch at this unit"),
                    (battle_focus_pool.can_star_engines,
                     battle_focus_pool.use_star_engines,
                     "Star Engines - [ASSAULT] this turn"),
                )
                for available, use, label in manoeuvres:
                    if not available(squad):
                        continue
                    bf_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                    bf_rect = self._draw_button(
                        surface, bf_rect, f"{label}  ({tokens_left} token(s))", accent="battle_focus",
                    )
                    self._buttons.append((bf_rect, (lambda u=use: u(squad))))
                    button_y += bf_rect.height + BUTTON_GAP

            if can_normal_move:
                move_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                move_rect = self._draw_button(surface, move_rect, "Move")
                self._buttons.append((move_rect, movement_controller.start_move))
                button_y += move_rect.height + BUTTON_GAP

            if can_fall_back_now:
                fall_back_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                fall_back_rect = self._draw_button(surface, fall_back_rect, "Fall Back")
                self._buttons.append((fall_back_rect, lambda: fall_back_controller.declare(squad)))
                button_y += fall_back_rect.height + BUTTON_GAP

            if can_remain_stationary:
                stationary_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                stationary_rect = self._draw_button(surface, stationary_rect, "Remain Stationary")
                self._buttons.append((stationary_rect, movement_controller.remain_stationary))
                button_y += stationary_rect.height + BUTTON_GAP

            if can_mark_spotted_now:
                observer_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                observer_rect = self._draw_button(surface, observer_rect, "Mark Spotted Target (Observer)")
                self._buttons.append((observer_rect, lambda: greater_good_controller.start(squad)))
                button_y += observer_rect.height + BUTTON_GAP

            if can_shoot_now:
                # Rule 24.14 (Firing Deck): "each time this TRANSPORT is
                # selected to shoot" - route the same "Shoot" button through
                # the borrow-a-passenger's-weapon sequence first, for a
                # Firing-Deck-capable transport with someone still embarked.
                if firing_deck_controller is not None and firing_deck_controller.can_use(squad):
                    shoot_callback = lambda: firing_deck_controller.start(squad)
                else:
                    shoot_callback = lambda: shooting_controller.start_shooting(squad)
                shoot_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                shoot_rect = self._draw_button(surface, shoot_rect, "Shoot")
                self._buttons.append((shoot_rect, shoot_callback))
                button_y += shoot_rect.height + BUTTON_GAP

            if can_explosives_now:
                explosives_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                explosives_rect = self._draw_button(surface, explosives_rect, "Explosives (1 CP)", accent="stratagem")
                self._buttons.append((explosives_rect, lambda: explosives_controller.start(squad)))
                button_y += explosives_rect.height + BUTTON_GAP

            can_torchstar_now = torchstar_controller is not None and torchstar_controller.can_use(squad)
            if can_torchstar_now:
                torchstar_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                torchstar_rect = self._draw_button(
                    surface, torchstar_rect, "The Torchstar Gambit (1 CP) - Normal move, no charge this turn",
                    accent="stratagem",
                )
                self._buttons.append((torchstar_rect, lambda: torchstar_controller.use(squad)))
                button_y += torchstar_rect.height + BUTTON_GAP

            # Rule 16.01 ACTIONS (game/actions.py). One button per action this
            # unit could start right now, one per legal target - so you pick
            # the UNIT by selecting it and the target by which button you
            # press, exactly like every other thing a unit can do.
            #
            # Deliberately NOT a DecisionManager prompt: an action is something
            # a unit does on its turn, not an interruption. The first version
            # opened a prompt chain at the start of the Shooting phase and
            # marched the player through the eligible units in name order,
            # which meant you could say whether to act but never with whom.
            # BOTH mission systems own rule-16.01 actions now - the Secondary
            # deck (Cleanse, Plunder) and the Force Disposition Primary (Secure
            # Asset, Booby Trap). Each keeps its own eligibility and its own
            # start(), and the panel simply concatenates what they offer; it
            # never learns which action belongs to which.
            _action_offers = []
            for _owner in (secondary_mission_controller, primary_mission_controller):
                if _owner is None:
                    continue
                for _entry in _owner.available_actions_for(squad):
                    _action_offers.append((_owner,) + tuple(_entry))
            for action_owner, action_label, action_def, action_target in _action_offers:
                action_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                action_rect = self._draw_button(surface, action_rect, action_label, accent="confirm")
                self._buttons.append((
                    action_rect,
                    lambda o=action_owner, a=action_def, sq=squad, t=action_target:
                        o.start_action(a, sq, t),
                ))
                button_y += action_rect.height + BUTTON_GAP

            if can_arrokon_now:
                # The tier is on the label rather than left to be worked out
                # from the target's model count - same reasoning as the
                # matchup/charge-odds hints the AI options carry.
                arrokon_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                arrokon_rect = self._draw_button(
                    surface, arrokon_rect,
                    f"Arro'kon Protocol (1 CP) - [SUSTAINED HITS {arrokon_tier}]", accent="stratagem",
                )
                self._buttons.append((arrokon_rect, lambda: arrokon_controller.use(squad)))
                button_y += arrokon_rect.height + BUTTON_GAP

            # The detachment Stratagems. Each one's own can_use() carries its
            # printed WHEN, so a Movement-phase Stratagem simply does not
            # appear here during Shooting - one loop, right phase, no phase
            # knowledge in the panel.
            for _label, _use in detachment_stratagem_buttons:
                _rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                _rect = self._draw_button(surface, _rect, _label, accent="stratagem")
                self._buttons.append((_rect, _use))
                button_y += _rect.height + BUTTON_GAP

            if can_crushing_impact_now:
                crushing_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                crushing_rect = self._draw_button(surface, crushing_rect, "Crushing Impact (1 CP)", accent="stratagem")
                self._buttons.append((crushing_rect, lambda: crushing_impact_controller.start(squad)))
                button_y += crushing_rect.height + BUTTON_GAP

            if embark_transport is not None:
                embark_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                embark_rect = self._draw_button(surface, embark_rect, f"Embark: {embark_transport.profile.name}")
                self._buttons.append((embark_rect, lambda: transport_controller.embark(squad, embark_transport)))
                button_y += embark_rect.height + BUTTON_GAP

            for passenger_squad in disembark_passengers:
                disembark_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                disembark_rect = self._draw_button(surface, disembark_rect, f"Disembark: {passenger_squad.name}")
                self._buttons.append((disembark_rect, lambda s=passenger_squad: transport_controller.start_disembark(s)))
                button_y += disembark_rect.height + BUTTON_GAP

            if can_charge_now:
                charge_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                charge_rect = self._draw_button(surface, charge_rect, "Charge")
                self._buttons.append((charge_rect, lambda: charge_controller.declare_charge(squad)))
                button_y += charge_rect.height + BUTTON_GAP

            if can_pile_in_now:
                pile_in_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                pile_in_rect = self._draw_button(surface, pile_in_rect, "Pile In")
                self._buttons.append((pile_in_rect, lambda: pile_in_controller.start_pile_in(squad)))
                button_y += pile_in_rect.height + BUTTON_GAP

                skip_pile_in_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                skip_pile_in_rect = self._draw_button(surface, skip_pile_in_rect, "Skip Pile In")
                self._buttons.append((skip_pile_in_rect, lambda: pile_in_controller.skip_pile_in(squad)))
                button_y += skip_pile_in_rect.height + BUTTON_GAP

            # War Horde's Unbridled Carnage: drawn just ABOVE "Fight" because
            # its TARGET clause is "a unit that has NOT been selected to fight
            # this phase" - once Fight is clicked the window is shut, so the
            # two buttons are offered in the order they have to be used in.
            # Hungry Void is bought before the unit fights, so it sits with
            # Unbridled Carnage above the Fight button.
            if can_hungry_void_now:
                void_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                void_rect = self._draw_button(
                    surface, void_rect,
                    "Hungry Void (1 CP) - +1 Strength to melee weapons this phase",
                    accent="stratagem",
                )
                self._buttons.append((void_rect, lambda: hungry_void_controller.use(squad)))
                button_y += void_rect.height + BUTTON_GAP

            # Grim Reapers shares Hungry Void's window exactly ("has not been
            # selected to fight this phase"), so it sits next to it.
            if can_grim_reapers_now:
                reapers_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                reapers_rect = self._draw_button(
                    surface, reapers_rect,
                    "Grim Reapers (1 CP) - re-roll Hit rolls (not vs MONSTER/VEHICLE)",
                    accent="stratagem",
                )
                self._buttons.append((reapers_rect, lambda: grim_reapers_controller.use(squad)))
                button_y += reapers_rect.height + BUTTON_GAP

            if can_mortarions_teachings_now:
                teach_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                teach_rect = self._draw_button(
                    surface, teach_rect,
                    "Mortarion's Teachings (1 CP) - ranged weapons gain [ASSAULT] and [HEAVY]",
                    accent="stratagem",
                )
                self._buttons.append(
                    (teach_rect, lambda: mortarions_teachings_controller.use(squad)))
                button_y += teach_rect.height + BUTTON_GAP

            # "Start of ANY phase", so unlike the two above it is offered in
            # every phase this panel draws a unit in.
            if can_blooming_pestilence_now:
                bloom_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                bloom_rect = self._draw_button(
                    surface, bloom_rect,
                    'Blooming Pestilence (1 CP) - +3" Contagion Range this phase',
                    accent="stratagem",
                )
                self._buttons.append(
                    (bloom_rect, lambda: blooming_pestilence_controller.use(squad)))
                button_y += bloom_rect.height + BUTTON_GAP

            if can_unbridled_carnage_now:
                carnage_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                carnage_rect = self._draw_button(
                    surface, carnage_rect,
                    "Unbridled Carnage (1 CP) - melee Critical Hits on 5+", accent="stratagem",
                )
                self._buttons.append((carnage_rect, lambda: unbridled_carnage_controller.use(squad)))
                button_y += carnage_rect.height + BUTTON_GAP

            # Aeldari Battle Focus, Sudden Strike. ONE draw site for its two
            # windows (see BattleFocusPool.can_sudden_strike): it sits above
            # "Fight" for the same reason as the button just above it - the
            # printed trigger is the unit being selected to fight, so that
            # window shuts once Fight is clicked - and, because "Fight" is
            # gone by the Consolidation step, the same button then lands
            # directly above "Consolidate", which is the second window.
            if (battle_focus_pool is not None and squad is not None
                    and battle_focus_pool.can_sudden_strike(squad)):
                tokens_left = battle_focus_pool.tokens.get(squad.owner, 0)
                strike_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                strike_rect = self._draw_button(
                    surface, strike_rect,
                    f"Sudden Strike - Pile-in/Consolidate 6\"  ({tokens_left} token(s))",
                    accent="battle_focus",
                )
                self._buttons.append(
                    (strike_rect, lambda: battle_focus_pool.use_sudden_strike(squad))
                )
                button_y += strike_rect.height + BUTTON_GAP

            if can_fight_now:
                fight_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                fight_rect = self._draw_button(surface, fight_rect, "Fight", accent="confirm")
                self._buttons.append((fight_rect, lambda: fight_controller.select_to_fight(squad)))
                button_y += fight_rect.height + BUTTON_GAP

            if can_consolidate_now:
                consolidate_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                consolidate_rect = self._draw_button(surface, consolidate_rect, "Consolidate")
                self._buttons.append((consolidate_rect, lambda: consolidate_controller.start_consolidate(squad)))
                button_y += consolidate_rect.height + BUTTON_GAP

            for kind in retro_moves:
                label = 'Retro-thrusters: Move 6"' if kind == "normal" else "Retro-thrusters: Fall Back"
                retro_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                retro_rect = self._draw_button(surface, retro_rect, label)
                self._buttons.append((
                    retro_rect,
                    lambda k=kind: retro_thrusters_controller.start(squad, fall_back=(k == "fall_back")),
                ))
                button_y += retro_rect.height + BUTTON_GAP
            if retro_moves:
                # Declining has to be clickable, not just implicit. The
                # opponent's turn-end waits on this offer (see
                # game/retro_thrusters.py), so "just don't press anything" is
                # no longer a way to pass on it - that would stall the turn.
                skip_rect = pygame.Rect(rect.x + BUTTON_MARGIN, button_y, button_width, BUTTON_HEIGHT)
                skip_rect = self._draw_button(surface, skip_rect, "Retro-thrusters: Skip")
                self._buttons.append((skip_rect, lambda: retro_thrusters_controller.decline(squad)))
                button_y += skip_rect.height + BUTTON_GAP

            hint = None
            if (
                can_remain_stationary and not can_normal_move and not can_fall_back_now
                and not can_fight_now and not can_consolidate_now
            ):
                hint = "This unit is engaged - no move type is currently eligible for it."
            elif (
                not can_remain_stationary and not can_fall_back_now and not can_shoot_now and not can_charge_now
                and not can_pile_in_now and not can_fight_now and not can_consolidate_now
                and not can_battle_shock_now and not can_explosives_now and not can_crushing_impact_now
                and not can_mark_spotted_now and not can_arrokon_now and not can_torchstar_now
                and not can_unbridled_carnage_now and not can_ere_we_go_now
                and not can_flickerjump_now
                and not can_sudden_storm_now and not can_conquering_tyrant_now
                and not can_hungry_void_now
                and not can_blooming_pestilence_now
                and not can_grim_reapers_now
                and not can_mortarions_teachings_now
                and not detachment_stratagem_buttons
                and turn_tracker is not None
            ):
                if turn_tracker.phase == PHASE_MOVEMENT and squad in movement_controller.moved_squad_ids:
                    hint = "This squad has already moved this phase."
                elif turn_tracker.phase == PHASE_SHOOTING and squad in shooting_controller.shot_squad_ids:
                    hint = "This squad has already shot this phase."
                elif (
                    turn_tracker.phase == PHASE_CHARGE and charge_controller is not None
                    and squad in charge_controller.charged_squad_ids
                ):
                    hint = "This squad has already declared a charge this phase."
                elif (
                    turn_tracker.phase == PHASE_FIGHT and consolidate_controller is not None
                    and squad in consolidate_controller.consolidated_squad_ids
                ):
                    hint = "This squad has already consolidated this phase."
                elif (
                    turn_tracker.phase == PHASE_FIGHT and fight_controller is not None
                    and squad in fight_controller.fought_squad_ids
                ):
                    hint = "This squad has already fought this phase."
                else:
                    hint = f"Nothing to do with this squad during the {turn_tracker.phase} phase."

            if hint is not None:
                button_y = self._draw_message_box(
                    surface, rect, button_width, button_y, [hint], config.PANEL_TEXT_COLOR, config.PANEL_BORDER_COLOR,
                )

        button_y += 10
        self._draw_message_box(
            surface, rect, button_width, button_y, movement_controller.errors, ERROR_COLOR, ERROR_COLOR,
            bg_color=ERROR_BOX_BG_COLOR,
        )

    def _draw_button(self, surface, rect, label, accent=None):
        """Sci-fi HUD button (see button_style.draw_button): chamfered
        outline, glowing border, brighter on hover and brighter still while
        held down. `accent` picks the color variant, per the user's color
        code - None (default blue, "everything else"), "confirm" (green,
        confirm/proceed buttons and Next Phase/End Turn), "danger" (red,
        Cancel/Decline buttons only), "stratagem" (violet, any button that
        spends CP to use a Stratagem), or "battle_focus" (turquoise, an
        Aeldari Agile Manoeuvre, which spends a Battle Focus token rather
        than CP). Returns the actual rect drawn
        (same x/y/width, but possibly taller to fit wrapped text) - callers
        use ITS height, not BUTTON_HEIGHT, both for the click hit-test area
        and when advancing to the next button below it."""
        hovered = rect.collidepoint(self._mouse_pos)
        pressed = hovered and self._mouse_down
        drawn = button_style.draw_button(
            surface, rect, label, self.button_font, hovered=hovered, pressed=pressed, accent=accent,
        )
        if accent == "stratagem":
            # RECORDED HERE, not at the seventeen call sites that pass this
            # accent. The label is the Stratagem's own name plus its cost and
            # sometimes a summary ("Sudden Storm (1 CP) - ranged weapons gain
            # [ASSAULT] this turn"), and every one of those sites already has
            # it in hand - so one line here covers all seventeen AND every
            # Stratagem button added later, which seventeen edits would not.
            #
            # A SEPARATE list from self._buttons on purpose: that one is
            # destructured as (rect, callback) by handle_click(), so widening
            # it to a 3-tuple would break every click in the panel.
            self._stratagem_buttons.append((drawn, _stratagem_name_in(label)))
        return drawn

    def _draw_toggle(self, surface, rect, label, on):
        """One on/off switch (see button_style.draw_toggle): the label
        WITHOUT an "On"/"Off" suffix, plus a sliding knob and a green/grey
        body that carry the state. Same contract as _draw_button() - the
        returned rect is the one actually drawn, and callers use ITS height
        for the hit-test and for stacking the next row.

        Kept separate from _draw_button() rather than folded in as another
        `accent`: an accent says what a press COSTS (blue free, green
        proceed, red cancel, violet spends CP), while this says what state
        the control is IN - a button that is already "on" is not a
        different kind of spend."""
        hovered = rect.collidepoint(self._mouse_pos)
        pressed = hovered and self._mouse_down
        return button_style.draw_toggle(
            surface, rect, label, on, self.button_font, hovered=hovered, pressed=pressed,
        )

    @property
    def tooltip_rect(self):
        """The button the tooltip belongs to, or None - so the box can be put
        BESIDE it rather than under the cursor. It is wider than the panel, and
        hanging it off the cursor would lay it over the buttons it describes."""
        return self._tip_rect if self.tooltip_name else None

    def stratagem_at(self, pos):
        """The printed name of the Stratagem button under `pos`, or None."""
        for rect, name in self._stratagem_buttons:
            if rect.collidepoint(pos):
                return name
        return None

    def update_tooltip(self, mouse_pos, mouse_down, now_ms):
        """Decide whether a Stratagem's rules are shown this frame; returns the
        name to show, or None.

        POLLED once per frame from main.py rather than driven off MOUSEMOTION,
        for the reason this repo has now hit six times (Fehlerklasse 15):
        main.py's event chain is a ~48-branch if/elif over CONTROLLER STATE
        whose bodies almost all handle only clicks, so anything hanging off its
        back is swallowed the moment any prompt is pending. A poll cannot be
        swallowed. Same shape as UnitDatacardOverlay.update_hover(), including
        `now_ms` being INJECTED rather than read here - that is what makes the
        dwell testable at all.

        The timer resets on a different button, on leaving the buttons, on any
        mouse button, and on cursor movement beyond STRATAGEM_TIP_JITTER_PX.

        Compared by NAME, not by rect: the panel rebuilds its rects every
        frame, so identity would reset the dwell on every single frame and the
        tooltip would never open."""
        name = self.stratagem_at(mouse_pos)
        if name is None or mouse_down:
            self._tip_name = None
            self._tip_since = None
            self.tooltip_name = None
            return None
        moved = (abs(mouse_pos[0] - self._tip_pos[0]) > STRATAGEM_TIP_JITTER_PX
                 or abs(mouse_pos[1] - self._tip_pos[1]) > STRATAGEM_TIP_JITTER_PX)
        if name != self._tip_name or moved:
            self._tip_name = name
            self._tip_since = now_ms
            self._tip_pos = mouse_pos
        dwelt = (self._tip_since is not None
                 and now_ms - self._tip_since >= STRATAGEM_TIP_DELAY_MS)
        self.tooltip_name = name if dwelt else None
        self._tip_rect = next((r for r, n in self._stratagem_buttons if n == name), None)
        return self.tooltip_name

    def handle_click(self, pos):
        for rect, callback in self._buttons:
            if rect.collidepoint(pos):
                callback()
                return
