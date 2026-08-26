from game import attached_units
from game import awakened_dynasty, destroyer_cult, guardian_protocols, protocol_hungry_void, implacable_eradication, mechanical_augmentation, monster_hunters, plasmacyte, reroll_scope
from game import way_of_the_short_blade
from game.ard_as_nails import ARD_AS_NAILS_WOUND_PENALTY, ard_as_nails_wound_modifier_applies
from game.damage_resolution import DamageAllocationSession, DevastatingWoundAllocationSession, MortalWoundAllocationSession, displayed_save_threshold
from game.dice import ATTACKS_ROLL, HIT_ROLL, SAVE_ROLL, WOUND_ROLL
from game.dice_notation import DiceNotationRoll, describe as describe_dice_notation
from game.ferocious_rage import ferocious_rage_adjusted_weapon
from game.spirit_of_gork import spirit_of_gork_adjusted_weapon
from game.hazard import hazard_failures, hazard_mortal_wounds
from game import hold_still as hold_still_rule
from game.modifiers import Modifier, apply_modifiers, describe_modifiers
from game.shooting import (
    _damaged_modifier, _group_label, _resolve_roll, _threshold_note, _wound_crit_threshold, _wound_threshold,
    extra_attack_dice, melta_adjusted_weapon,
)
from game.squad import allocation_target_model, allocation_target_profile, attached_unit_toughness, model_engaged_with, squad_has_fights_first, squad_has_might_is_right, tank_hunters_modifiers
from game.thresholds import parse_threshold as _parse_threshold
from game.turn import PHASE_FIGHT
from game import aspect_shrine
from game import branching_fates
from game import forewarned
from game import protect
from game.doom import DOOM_WOUND_BONUS
from game import psychic_guidance
from game import storm_of_silence
from game.crit_hit import crit_hit_threshold
from game.waaagh import waaagh_extra_attacks, waaagh_melee_adjusted_weapon
from game.war_horde import get_stuck_in_adjusted_weapon
from game.weapons import MELEE

# The abilities that can turn one die of a roll into an unmodified 6. Both
# expose the same four names, so the offer below is built from whichever one
# actually applies rather than duplicated per ability - the same "second
# consumer turns a field into a list" move made for target_reactions,
# cost_discounts and on_squad_finished_shooting.
_UNMODIFIED_SIX_SOURCES = (aspect_shrine, branching_fates)


def _unmodified_six_source(method, squad, model, *args):
    """The first source that would buy something here, and what it buys."""
    for source in _UNMODIFIED_SIX_SOURCES:
        change = getattr(source, method)(squad, model, *args)
        if change is not None:
            return source, change
    return None, None


NOT_STARTED = "not_started"          # Pile In is still available; the Fight step hasn't begun
SELECTING = "selecting"              # alternating fight-selection is in progress
CHOOSING_TARGET = "choosing_target"  # the selected unit must pick which engaged enemy unit to fight
CHOOSING_WEAPON = "choosing_weapon"  # pick a melee attack group to fight with (also used while a group resolves)
ASSIGNING = "assigning"              # split-fire: assign each model+weapon its own engaged target
DONE = "done"                        # no unit is eligible to fight anymore

FIGHTS_FIRST = "fights_first"
REMAINING = "remaining"

FIGHT_PASS_DISTANCE_IN = 5.0  # Appendix "Eligible to Fight, But Unable to Fight"


def effective_weapon_skill(model, weapon):
    """Almost every melee weapon's accuracy is purely the wielding model's
    own WS (see WeaponProfile's own docstring). Power Klaw prints its own,
    worse WS than its wielder's instead - weapon.weapon_skill, when set,
    overrides the model's. Mirrors shooting.py's effective_ballistic_skill()
    exactly, just melee-side (WS instead of BS) - lives here rather than
    shooting.py since nothing there ever needs WS."""
    return weapon.weapon_skill if weapon.weapon_skill is not None else model.profile.weapon_skill


def _melee_attack_key(model, weapon):
    """Rule 04.03 'identical attacks', adapted for melee: share WS, S, AP, D.
    [EXTRA ATTACKS] is also part of the key (rule 24.11): those weapons are
    unrestricted ("in addition to any others"), while a model's other melee
    weapons are capped at one selected type per fight activation - keeping
    them in separate groups even if stats coincide lets that restriction be
    enforced per group (see _used_other_melee_weapon), mirroring the
    [CLOSE-QUARTERS] fix to shooting.py's _attack_key."""
    return (effective_weapon_skill(model, weapon), weapon.strength, weapon.ap, weapon.damage, weapon.extra_attacks)


def _melee_locked_out(model, weapon, used_other_weapon):
    """Rule 24.11: once a model has fought with one of its non-[EXTRA
    ATTACKS] melee weapons this fight activation, none of its other
    non-[EXTRA ATTACKS] weapons may also be used - [EXTRA ATTACKS] weapons
    themselves are never restricted ("in addition to any others")."""
    if weapon.extra_attacks:
        return False
    return model in used_other_weapon


def _melee_attack_groups(squad, used_other_weapon=None, one_shot_used=None):
    """{attack_key: [(model, weapon), ...]} for every *melee* weapon every
    model in the squad carries (unfiltered by target - rule 12.02's
    Engagement Range check happens per model against the chosen target in
    weapon_eligibility()/choose_weapon()/assign_current(), the same split
    shooting.py uses between _attack_groups and _model_can_reach), filtered
    by rule 24.11's [EXTRA ATTACKS] lock if a used_other_weapon set is given
    (only meaningful within a single already-started fight activation -
    callers checking bare eligibility pass none), and by rule 24.26's
    [ONE SHOT] the same way shooting.py's _attack_groups does."""
    groups = {}
    for model in squad.models:
        for weapon in model.weapons:
            if weapon.weapon_type != MELEE:
                continue
            if used_other_weapon is not None and _melee_locked_out(model, weapon, used_other_weapon):
                continue
            if one_shot_used is not None and weapon.one_shot and (model.id, id(weapon)) in one_shot_used:
                continue
            groups.setdefault(_melee_attack_key(model, weapon), []).append((model, weapon))
    return groups


class FightController:
    """Rules 12.01-12.06: once Pile In is done, both players alternate
    selecting units to fight (rule 12.04), Fights First units getting
    priority. When a unit is selected, it picks one engaged enemy unit to
    target (auto-picked if there's only one) and then makes attacks with
    its melee weapons exactly as in Making Attacks (04) - reusing the same
    hit/wound/save/damage engine as shooting (_resolve_roll, _wound_threshold,
    DamageAllocationSession are all weapon-agnostic), just keyed off WS
    instead of BS. Only models within Engagement Range of the specific
    target squad get to attack it (rule 12.02) - a squad can be engaged
    overall while some of its models are too far from a given enemy unit to
    reach it. Split Fire (assigning different models to different engaged
    enemies) is supported via the same toggle/assignment-queue pattern as
    ShootingController, since melee's short range routinely puts different
    models of a spread-out squad in contact with different enemy units."""

    def __init__(
        self, game_log=None, dice_manager=None, turn_tracker=None, all_tokens=None,
        pile_in_controller=None, charge_controller=None, decision_manager=None, suppression=None, stealth_drones=None,
        waaagh=None, target_reactions=(), guide=None, doom=None, whispering_web=None,
        objectives=None,
    ):
        self.game_log = game_log
        self.dice_manager = dice_manager
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.pile_in_controller = pile_in_controller
        self.charge_controller = charge_controller  # rule 24.21's [LANCE]: "if the attacking model's unit made a charge move this turn"
        self.decision_manager = decision_manager  # rule 24.23's [LETHAL HITS]: "you can choose"
        self.suppression = suppression  # Strike Team's Suppression Volley ability - optional, like decision_manager; see game/suppression.py
        self.stealth_drones = stealth_drones  # Ghostkeel Battlesuit's Stealth Drones ability - optional, like suppression; see game/stealth_drones.py
        self.guide = guide  # the Farseer's Guide mark - optional; read by _hit_modifiers() (see game/guide.py)
        # Immortals' Implacable Eradication upgrades its re-roll when the
        # target is within range of an objective marker, so the melee side
        # needs the markers too - ShootingController has carried them since
        # Breach and Clear. Optional, so every existing caller is unchanged.
        self.objectives = objectives if objectives is not None else []
        self.doom = doom  # Eldrad Ulthran's Doom mark - optional; read by _wound_modifiers() (see game/doom.py)
        self.whispering_web = whispering_web  # Lhykhis' Whispering Web mark - optional; read by the hit step's crit threshold (see game/whispering_web.py)
        self.waaagh = waaagh  # Orks army rule "Waaagh!" - optional, like suppression/stealth_drones; see game/waaagh.py
        # Reactive stratagems whose WHEN is "just after an enemy unit has
        # selected its targets" - see ShootingController's identical field.
        # Both of the ones that exist name "the Fight phase" as well as the
        # opponent's Shooting phase, which is why this controller carries them
        # too: game/stim_injectors.py, game/ard_as_nails.py.
        self.target_reactions = [r for r in target_reactions if r is not None]

        self.state = NOT_STARTED
        self.sub_step = None
        self.whose_turn = None
        self.fought_squad_ids = set()
        self._attacked_squads_this_activation = set()  # rule 19.04's grace window - squads this fight activation has attacked, so _actually_finish_current_fight() can close it on each (see _begin_resolution())
        self._announced_turn = None  # see _announce_whose_turn()
        self.engaged_at_start = set()  # squads engaged when the Fight step began (rule 12.04)
        self._passed_in_a_row = 0  # Appendix "Eligible to Fight, But Unable to Fight" - consecutive passes end the Fight step

        # Rule 15.12 (Counteroffensive): player -> the specific squad that
        # "must be the next unit you select to fight" - narrows
        # eligible_to_select_now() for that player until it's actually
        # selected (see _start_fighting()). game/counteroffensive.py sets
        # this; on_unit_finished_fighting is how it hears "a unit's fight
        # activation just ended" to offer the reaction in the first place.
        self.forced_next_fighter = {}
        self.on_unit_finished_fighting = None

        self.split_fire = False

        # current unit's fight resolution
        self.fighting_squad = None
        self.target_squad = None
        self.remaining_weapon_types = []
        self.current_group = None
        self.pending_step = None     # "attacks" | "hit" | "wound" | "save" | "allocate" | None
        self.damage_session = None
        self.devastating_wound_session = None  # DevastatingWoundAllocationSession, rule 24.10
        self._devastating_crits = 0  # crits pulled out of the current wound roll for [DEVASTATING WOUNDS]
        self._used_other_melee_weapon = set()  # rule 24.11: models locked out of further non-[EXTRA ATTACKS] weapons
        self._hazardous_count = 0  # distinct [HAZARDOUS] weapon groups used this activation, rule 24.15
        self._lethal_hits_auto_wounds = 0  # rule 24.23: hits chosen to auto-wound, folded into normal_wounds once the (possibly skipped) wound roll resolves
        self._twin_linked_used = False  # rule 24.38: whether this group's one-time re-roll offer has already been made/used
        self._hit_reroll_used = False  # Monster Hunters (user-supplied): whether this group's one-time Hit-roll re-roll offer has already been made/used - the hit-step twin of _twin_linked_used
        self._pending_attacks_roll = None  # DiceNotationRoll while pending_step == "attacks" - see shooting.py's identical field
        self._pending_sustained = None       # hit-step context while pending_step == "sustained_hits" - see shooting.py's identical field
        self._pending_sustained_roll = None  # DiceNotationRoll while pending_step == "sustained_hits" (a dice-notation [SUSTAINED HITS X])
        self._pending_twin_linked_reroll = None  # rule 24.38: context dict while pending_step == "wound_twin_linked_reroll"
        self._pending_hit_reroll = None  # Monster Hunters: context dict while pending_step == "hit_monster_hunters_reroll"
        self._pending_ones_reroll = None  # a two-clause source's automatic re-roll of 1s: context dict while pending_step == "hit_reroll_ones"/"wound_reroll_ones"
        self.one_shot_used = set()  # rule 24.26: (model.id, id(weapon)) pairs already fought with - persists for the whole battle, never reset
        self.mortal_wound_session = None  # MortalWoundAllocationSession while pending_step == "hazard_wounds"
        self.hold_still_session = None  # MortalWoundAllocationSession while pending_step == "hold_still_wounds" - Painboy's "Hold Still and Say 'Aargh!'", see game/hold_still.py
        self._hold_still_crits = 0  # critical WOUNDS of the current group that trigger that ability. Kept separate from _devastating_crits because they are NOT removed from the normal wound pool - see game/hold_still.py's own note on how the two differ.

        # split-fire
        self.assignment_queue = []   # [(model, weapon), ...] still needing a target
        self.assignments = {}        # (attack_key, target_squad) -> [(model, weapon), ...]
        self.resolved_groups = []    # queued {"weapon_key", "weapon_label", "target_squad", "pairs"} dicts

    def reset_fight_phase(self):
        """Rule 12.04: a new Fight phase comes around every battle round."""
        self.state = NOT_STARTED
        self.sub_step = None
        self.whose_turn = None
        self.fought_squad_ids = set()
        self.engaged_at_start = set()
        self._announced_turn = None
        self._passed_in_a_row = 0
        self.forced_next_fighter = {}  # rule 15.12: "until the end of the phase"
        self.fighting_squad = None
        self.target_squad = None
        self.remaining_weapon_types = []
        self.current_group = None
        self.pending_step = None
        self.damage_session = None
        self.devastating_wound_session = None
        self._devastating_crits = 0
        self._used_other_melee_weapon = set()
        self._hazardous_count = 0
        self._lethal_hits_auto_wounds = 0
        self._pending_attacks_roll = None
        self._pending_sustained_roll = None
        self._pending_sustained = None
        self._pending_twin_linked_reroll = None
        self._pending_hit_reroll = None
        self.mortal_wound_session = None
        self.hold_still_session = None
        self._hold_still_crits = 0
        self.assignment_queue = []
        self.assignments = {}
        self.resolved_groups = []

    def _all_squads(self):
        return {token.squad for token in self.all_tokens if token.squad is not None}

    def _other_player(self, player):
        return "Player 2" if player == "Player 1" else "Player 1"

    def engaged_enemy_squads(self, squad):
        """Enemy squads this squad is engaged with - the valid melee
        targets. Public: also used by main.py to validate a board click."""
        return [s for s in self._all_squads() if s.owner != squad.owner and squad.is_engaged_with(s)]

    def toggle_split_fire(self):
        self.split_fire = not self.split_fire

    def begin_fight_step(self):
        """Rule 12.04: only once Pile In is resolved (moved or skipped) for
        every eligible unit on both sides - neither player starts selecting
        units to fight while the other still has a pending Pile In."""
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_FIGHT:
            return
        if self.state != NOT_STARTED:
            return
        if self.pile_in_controller is not None and self.pile_in_controller.has_pending_squads():
            return
        self.engaged_at_start = {squad for squad in self._all_squads() if squad.is_engaged(self.all_tokens)}
        self.whose_turn = self.turn_tracker.active_player if self.turn_tracker is not None else "Player 1"
        self.sub_step = FIGHTS_FIRST
        self.state = SELECTING
        self._settle_turn_state()

    def _is_eligible_to_fight(self, squad):
        """Rule 12.04 eligibility.

        A DESTROYED unit is never eligible, which needs stating explicitly
        for two reasons. First, `engaged_at_start` and `fights_first` are
        both sticky flags recorded earlier in the phase, so neither notices
        that the unit has since been wiped out. Second, dead models are only
        stripped from squad.models/all_tokens once per frame by main.py's
        remove_dead_models() - so within the very frame a unit is wiped out
        it is still fully present here, dead tokens and all.

        Real stall, reported from a game (a charge wiped a unit outright):
        the destroyed unit stayed "eligible", so game/counteroffensive.py
        offered its owner the Counteroffensive stratagem (15.12) for it, and
        eligible_to_select_now() went on demanding that they select a unit to
        fight when nothing of theirs was left in combat - a squad with no
        models can never fight, never lands in fought_squad_ids, and so never
        clears. Taking Counteroffensive made it permanent: forced_next_fighter
        then pinned selection to exactly that dead squad, and the AI waited
        forever for a choice the player could not make."""
        if squad in self.fought_squad_ids:
            return False
        if not any(not m.is_dead() for m in squad.models):
            return False
        # Rule 12.04's own two conditions and nothing else: in Engagement
        # Range now, or engaged when the Fight step began (so a unit whose
        # only nearby enemy has since died still gets to swing).
        #
        # Fights First (24.13) is deliberately NOT a third one. It decides
        # the ORDER eligible units fight in - which is what
        # _eligible_fighters(fights_first_only=True) uses it for - not who
        # is eligible. Reading it as eligibility made every Howling Banshees
        # / Jain Zar unit on the board eligible every Fight phase no matter
        # where it stood, which is the "was ist diese meldung immer am ende
        # des gegnerischen zugs? irgendeine aeldari trigger?" report: the
        # phase then refused to settle and demanded a unit be selected (or
        # the Appendix's Pass be clicked) with nothing of the player's
        # anywhere near an enemy. Measured at the time: Banshees 18.8" from
        # the nearest enemy came back eligible, an otherwise identical Boyz
        # mob at the same distance did not.
        #
        # Nothing legitimate is lost: every other source of Squad.fights_first
        # (a completed charge 11.04, Heroic Intervention 15.11,
        # Counteroffensive 15.12) leaves the unit in Engagement Range anyway,
        # so it stays eligible through the first condition.
        return squad.is_engaged(self.all_tokens) or squad in self.engaged_at_start

    def is_eligible_to_fight(self, squad):
        """Public reading of rule 12.04 eligibility, for callers outside this
        controller that need to know whether a unit can still fight at all
        this phase - independent of whose sub-turn it currently is, which is
        what eligible_to_select_now() adds on top.

        Exists for War Horde's Unbridled Carnage (game/unbridled_carnage.py),
        whose window is BEFORE a unit is selected to fight: a unit that
        cannot fight this phase can never make the melee attack the stratagem
        buffs, so offering it there would be offering to burn 1 CP for
        nothing."""
        return self._is_eligible_to_fight(squad)

    def _eligible_fighters(self, player, fights_first_only):
        return [
            squad for squad in self._all_squads()
            if squad.owner == player and self._is_eligible_to_fight(squad)
            and (not fights_first_only or squad_has_fights_first(squad))
        ]

    def eligible_to_select_now(self):
        """Squads the current selecting player can pick from right now.
        Rule 15.12 (Counteroffensive): if that player has an outstanding
        forced_next_fighter, selection is narrowed to exactly that squad -
        unless it's no longer eligible (e.g. destroyed before its turn came
        up), in which case the constraint simply lapses and normal
        selection resumes."""
        if self.state != SELECTING:
            return []
        forced = self.forced_next_fighter.get(self.whose_turn)
        if forced is not None:
            if self._is_eligible_to_fight(forced):
                return [forced]
            del self.forced_next_fighter[self.whose_turn]
        return self._eligible_fighters(self.whose_turn, self.sub_step == FIGHTS_FIRST)

    def can_pass(self):
        """Appendix "Eligible to Fight, But Unable to Fight": the selecting
        player may pass instead of picking a unit if every one of their
        currently eligible fighters is more than 5" from every enemy unit -
        i.e. formally "eligible" (rule 12.04) but with nothing left in reach
        (e.g. its only nearby enemies died or fell back in other combats).
        Reads eligible_to_select_now() (not _eligible_fighters() directly)
        so a rule 15.12 forced_next_fighter correctly narrows this to just
        that squad's own distance, not every Fights-First unit the player
        might otherwise have."""
        if self.state != SELECTING:
            return False
        fighters = self.eligible_to_select_now()
        if not fighters:
            return False  # nothing eligible at all is handled by _settle_turn_state(), not a "pass"
        enemies = [s for s in self._all_squads() if s.owner != self.whose_turn]
        return all(
            squad.min_distance_to(enemy) > FIGHT_PASS_DISTANCE_IN
            for squad in fighters for enemy in enemies
        )

    def pass_fighting(self):
        """"If both players pass in succession... the Fight step ends."
        Simplification: the Appendix's OTHER end condition - "one player
        passes when their opponent has no remaining units that are eligible
        to fight" - isn't special-cased separately; in that situation
        _settle_turn_state() just hands the turn straight back (the
        opponent has nothing to select), so the same player passes again
        immediately afterwards and the second-pass-in-a-row path below
        still ends it, just one harmless extra Pass click later than a
        fully literal reading would."""
        if not self.can_pass():
            return
        self._passed_in_a_row += 1
        self._log(f"{self.whose_turn}: passes (no eligible unit is within {FIGHT_PASS_DISTANCE_IN:.0f}\" of an enemy).")
        if self._passed_in_a_row >= 2:
            self.state = DONE
            return
        self.whose_turn = self._other_player(self.whose_turn)
        self._settle_turn_state()

    def _announce_whose_turn(self):
        """Say out loud whose fight it is now.

        Rule 12.04 alternates the Fight step between both players, so after the
        AI's unit has fought, control legitimately passes to the human's engaged
        unit and the AI must NOT end the turn - it has to wait. Nothing on screen
        said so, which is why that wait was reported as an AI bug ("nach dem die
        ki mit ihrem nahkampf fertig ist beendet sie nicht sebstständig ihren
        zug"): the game was waiting for the player, not stuck. Reproduced and
        measured before changing anything - state was SELECTING with whose_turn
        on the human and one eligible fighter, which is exactly correct, so the
        fix belongs here in the announcement rather than in the state machine.

        Announced only when it CHANGES, so a per-frame caller cannot spam it."""
        if self.state != SELECTING:
            return
        eligible = self._eligible_fighters(self.whose_turn, self.sub_step == FIGHTS_FIRST)
        if not eligible:
            return
        key = (self.whose_turn, self.sub_step, tuple(sorted(s.name for s in eligible)))
        if key == self._announced_turn:
            return
        self._announced_turn = key
        names = ", ".join(sorted(s.name for s in eligible))
        self._log(f"{self.whose_turn}: it is your turn to fight - select a unit ({names}).")

    def _settle_turn_state(self):
        """Rule 12.04's alternation: figure out whose turn it is and which
        sub-step, skipping a side with nothing to do, dropping from Fights
        First to Remaining Combats once neither player has one, and ending
        the Fight step once neither player has anything left at all."""
        if self.state != SELECTING:
            return
        while True:
            if self.sub_step == FIGHTS_FIRST:
                if self._eligible_fighters(self.whose_turn, True):
                    self._announce_whose_turn()
                    return
                if not self._eligible_fighters("Player 1", True) and not self._eligible_fighters("Player 2", True):
                    self.sub_step = REMAINING
                    continue
                self.whose_turn = self._other_player(self.whose_turn)
                continue
            else:
                if self._eligible_fighters(self.whose_turn, False):
                    self._announce_whose_turn()
                    return
                if not self._eligible_fighters("Player 1", False) and not self._eligible_fighters("Player 2", False):
                    self.state = DONE
                    return
                self.whose_turn = self._other_player(self.whose_turn)
                continue

    def can_select_to_fight(self, squad):
        if self.state != SELECTING or squad is None:
            return False
        return squad in self.eligible_to_select_now()

    def select_to_fight(self, squad):
        """Rule 12.04 'when a unit is selected to fight': pick a fight type
        (Normal 12.05 / Overrun 12.06 - the type itself doesn't change how
        attacks resolve, only whether an extra pile-in happens first, which
        we don't wire up - see CLAUDE.md) then make attacks."""
        if not self.can_select_to_fight(squad):
            return
        self._start_fighting(squad)

    def force_fight(self, squad):
        """Rule 12.08 (Engaging Consolidation consequence): an enemy unit
        dragged into engagement by an opponent's consolidation move, that
        hasn't fought yet this phase, is immediately selected to fight -
        bypassing normal turn alternation entirely, since this isn't the
        consolidating player's choice to make. Only valid once the normal
        Fight step has finished (state == DONE), which is always true by
        the time Consolidate runs.

        Skips a destroyed unit for the same reason _is_eligible_to_fight()
        does: consolidation runs right after the Fight step, so a unit wiped
        out during that step can still be sitting there with its dead models
        un-stripped (remove_dead_models() runs once per frame) and within
        engagement range of the consolidating unit."""
        if squad in self.fought_squad_ids or self.fighting_squad is not None:
            return
        if not any(not m.is_dead() for m in squad.models):
            return
        self._log(f"{squad.owner}: {squad.name} is forced to fight (engaged via opponent's consolidation, rule 12.08).")
        self._start_fighting(squad)

    def _start_fighting(self, squad):
        # Rule 15.12: this squad was "the next unit you select to fight" -
        # constraint satisfied, whether reached via normal selection or
        # force_fight() (rule 12.08's Engaging Consolidation).
        if self.forced_next_fighter.get(squad.owner) is squad:
            del self.forced_next_fighter[squad.owner]
        self.fighting_squad = squad
        self._used_other_melee_weapon = set()
        self._hazardous_count = 0
        self._lethal_hits_auto_wounds = 0
        self._passed_in_a_row = 0  # a real selection breaks any "passes in a row" streak
        targets = self.engaged_enemy_squads(squad)
        if not targets:
            self._finish_current_fight()
            return
        if not self.split_fire and len(targets) == 1:
            self.target_squad = targets[0]
            # "Just after an enemy unit has selected its targets" - this
            # auto-pick IS that step (there is only one legal target, so no
            # choice is offered), and it used to be the one target-selection
            # path with no reaction hook on it. That made the Fight-phase half
            # of every reactive stratagem unreachable in the ordinary case:
            # a unit engaged with exactly one enemy - which is most of them -
            # never reached choose_target_squad() at all. Pre-existing, found
            # while adding the second entry to target_reactions.
            self._offer_target_reactions(targets[0])
            self._enter_choosing_weapon()
        else:
            self.target_squad = None
            self.state = CHOOSING_TARGET

    def cancel(self):
        """Back out of a not-yet-rolled fight resolution (e.g. a mis-click)
        without consuming the unit's turn to fight - it stays eligible and
        can be selected again later, exactly like ShootingController.cancel()."""
        if self.current_group is not None:
            return  # can't back out mid dice-roll/resolution
        self.fighting_squad = None
        self.target_squad = None
        self.remaining_weapon_types = []
        self._used_other_melee_weapon = set()
        self._hazardous_count = 0
        self._lethal_hits_auto_wounds = 0
        self.mortal_wound_session = None
        self.hold_still_session = None
        self._hold_still_crits = 0
        self.assignment_queue = []
        self.assignments = {}
        self.resolved_groups = []
        self.state = SELECTING

    def _offer_target_reactions(self, target_squad):
        """Retaliation Cadre's Stim Injectors: "just after an enemy unit has
        selected its targets", whose WHEN names the Fight phase alongside the
        opponent's Shooting phase. Called from both places that constitute the
        target-selection step here, mirroring ShootingController's own
        _offer_target_reactions(); each controller decides for itself whether
        it wants to act - see game/stim_injectors.py, game/ard_as_nails.py."""
        if self.fighting_squad is None:
            return
        for reaction in self.target_reactions:
            reaction.maybe_offer(self.fighting_squad, target_squad, melee=True)

    def choose_target_squad(self, target_squad):
        if self.state != CHOOSING_TARGET or self.split_fire or self.fighting_squad is None:
            return
        if target_squad not in self.engaged_enemy_squads(self.fighting_squad):
            return
        self.target_squad = target_squad
        self._offer_target_reactions(target_squad)
        self._enter_choosing_weapon()

    def begin_assignment(self):
        """Split-fire only: leave target-picking behind and start assigning
        every melee model+weapon its own engaged target individually."""
        if self.state != CHOOSING_TARGET or not self.split_fire or self.fighting_squad is None:
            return
        groups = _melee_attack_groups(self.fighting_squad, self._used_other_melee_weapon, self.one_shot_used)
        self.assignment_queue = [pair for plist in groups.values() for pair in plist]
        self.assignments = {}
        self.state = ASSIGNING
        # Drops the models that are out of Engagement Range before the player
        # is ever asked about them, and ends the activation outright if that
        # leaves nothing to assign - see _advance_assignment().
        self._advance_assignment()

    def current_assignment(self):
        """(model, weapon) awaiting a target during split-fire assignment, or None."""
        return self.assignment_queue[0] if self.assignment_queue else None

    def assign_current(self, target_squad):
        if self.state != ASSIGNING or not self.assignment_queue or target_squad is None:
            return
        model, weapon = self.assignment_queue.pop(0)
        if not model_engaged_with(model, target_squad):
            self.assignment_queue.insert(0, (model, weapon))
            return

        key = (_melee_attack_key(model, weapon), target_squad)
        self.assignments.setdefault(key, []).append((model, weapon))
        # Offered only once the assignment has actually landed (the engagement
        # check above can bounce it) - see _offer_target_reactions().
        self._offer_target_reactions(target_squad)
        self._lock_other_melee_weapon(model, weapon)
        # Rule 24.11: that lock may now rule out other still-queued pairs
        # for the same model (its other non-[EXTRA ATTACKS] weapons) - drop
        # them instead of letting the player assign a target for a weapon
        # it can no longer use.
        self.assignment_queue = [
            (m, w) for m, w in self.assignment_queue
            if not _melee_locked_out(m, w, self._used_other_melee_weapon)
        ]

        self._advance_assignment()

    def skip_current(self):
        """Leave the model+weapon at the front of the assignment queue
        unused and move on to the next one - game/shooting.py's
        skip_current() with the same rule 04.01 basis ("one or more"
        weapons, not all of them), for the identically shaped melee
        assignment step.

        The dead end it escapes is worse here than in shooting:
        _melee_attack_groups() is deliberately unfiltered by target (see its
        docstring - rule 12.02's Engagement Range check happens per model
        against the CHOSEN target), so a charging mob queues every model it
        has while only the front rank is within Engagement Range of
        anything. Reproduced with a 10-model mob: 4 models assignable, the
        queue then frozen forever on the 5th. _advance_assignment() drops
        those on its own now, so this is the deliberate "this model holds
        back" choice."""
        if self.state != ASSIGNING or not self.assignment_queue:
            return
        model, weapon = self.assignment_queue.pop(0)
        self._log(f"{self.fighting_squad.name}: {model.profile.name} does not attack with its {weapon.name}.")
        self._advance_assignment()

    def finish_assignment(self):
        """Stop assigning and resolve whatever has a target already - the
        split-fire counterpart of stop_fighting()."""
        if self.state != ASSIGNING:
            return
        skipped = len(self.assignment_queue)
        self.assignment_queue = []
        if skipped:
            self._log(f"{self.fighting_squad.name}: {skipped} weapon(s) left unused.")
        self._advance_assignment()

    def _prune_unassignable(self):
        """Drop pairs from the FRONT of the queue whose model is not within
        Engagement Range of ANY of this unit's melee targets, so the player
        is never asked to pick a target that does not exist.

        Rule 12.05 is why this is a correctness fix and not a convenience:
        only models within Engagement Range make attacks at all, so a
        trailing model was never an option to begin with. Pure geometry
        here (no line of sight), so unlike shooting.py's counterpart the
        sweep is cheap; front-only all the same, to keep the two flows the
        same shape."""
        targets = self.engaged_enemy_squads(self.fighting_squad) if self.fighting_squad else []
        dropped = []
        while self.assignment_queue:
            model, weapon = self.assignment_queue[0]
            if any(model_engaged_with(model, squad) for squad in targets):
                break
            self.assignment_queue.pop(0)
            dropped.append(weapon.name)
        if dropped and self.fighting_squad is not None:
            names = ", ".join(sorted(set(dropped)))
            self._log(
                f"{self.fighting_squad.name}: {len(dropped)} weapon(s) belong to models out of "
                f"Engagement Range and do not attack ({names})."
            )

    def _advance_assignment(self):
        """Shared tail of every split-fire assignment step (assign, skip,
        finish, begin): make sure the pair now at the front is one the player
        can answer for, and once nothing is left to assign, resolve what was
        assigned. Nothing assigned at all ends the activation through
        _begin_next_split_group() -> _finish_current_fight()."""
        self._prune_unassignable()
        if self.assignment_queue:
            return

        self.resolved_groups = [
            {
                "weapon_key": key[0],
                "weapon_label": _group_label(pairs),
                "target_squad": key[1],
                "pairs": pairs,
            }
            for key, pairs in self.assignments.items()
        ]
        self._begin_next_split_group()

    def _begin_next_split_group(self):
        """Same crash as game/shooting.py's own _begin_next_split_group()
        (see its docstring): Split Fire locks in every model+weapon's
        target up front, so two queued groups can legally share a target -
        if the first one wipes it out entirely, the second one's
        target_squad.models is now empty by the time this runs. Skip any
        further queued group whose target has since been destroyed rather
        than starting a resolution (and eventually reading
        target_squad.models[0]) against nothing."""
        while self.resolved_groups:
            group = self.resolved_groups[0]
            if group["target_squad"].models:
                break
            self.resolved_groups.pop(0)
            self._log(f"{group['target_squad'].name} was destroyed before {group['weapon_label']} could fight - skipped.")
        if not self.resolved_groups:
            self._finish_current_fight()
            return
        group = self.resolved_groups.pop(0)
        self.state = CHOOSING_WEAPON
        self._begin_resolution(group["weapon_key"], group["weapon_label"], group["pairs"], group["target_squad"])

    def _enter_choosing_weapon(self):
        groups = _melee_attack_groups(self.fighting_squad, self._used_other_melee_weapon, self.one_shot_used)
        self.remaining_weapon_types = list(groups.keys())
        self.state = CHOOSING_WEAPON
        if not self.remaining_weapon_types:
            self._finish_current_fight()

    def valid_target_models(self):
        """Board-highlight helper: enemy tokens belonging to squads currently
        valid to pick as a target (CHOOSING_TARGET, non-split-fire), or valid
        for the model+weapon at the front of the assignment queue (ASSIGNING,
        split-fire) - mirrors shooting.py's valid_target_models."""
        if self.fighting_squad is None:
            return set()

        if self.state == CHOOSING_TARGET and not self.split_fire:
            targets = self.engaged_enemy_squads(self.fighting_squad)
            return {token for token in self.all_tokens if token.squad in targets}

        if self.state == ASSIGNING and self.assignment_queue:
            model, _weapon = self.assignment_queue[0]
            return {
                token for token in self.all_tokens
                if token.squad is not None and token.squad.owner != self.fighting_squad.owner
                and model_engaged_with(model, token.squad)
            }

        return set()

    def weapon_eligibility(self):
        """[(attack_key, label, eligible_count, total_count), ...] against
        the chosen target - eligible counts only models within Engagement
        Range of that specific target (rule 12.02), mirroring shooting.py's
        range/LoS eligibility split."""
        if self.fighting_squad is None or self.target_squad is None:
            return []
        groups = _melee_attack_groups(self.fighting_squad, self._used_other_melee_weapon, self.one_shot_used)
        result = []
        for key in self.remaining_weapon_types:
            pairs = groups.get(key, [])
            eligible = sum(1 for m, w in pairs if model_engaged_with(m, self.target_squad))
            result.append((key, _group_label(pairs), eligible, len(pairs)))
        return result

    def stop_fighting(self):
        """Rule 04.01 allows selecting 'one or more' melee weapons, not all
        of them - deliberately leave remaining weapon types unused."""
        if self.state != CHOOSING_WEAPON or self.current_group is not None:
            return
        self._finish_current_fight()

    def choose_weapon(self, weapon_key):
        if self.state != CHOOSING_WEAPON or weapon_key not in self.remaining_weapon_types:
            return
        groups = _melee_attack_groups(self.fighting_squad, self._used_other_melee_weapon, self.one_shot_used)
        pairs = [
            (m, w) for m, w in groups.get(weapon_key, [])
            if model_engaged_with(m, self.target_squad)
        ]
        for model, weapon in pairs:
            self._lock_other_melee_weapon(model, weapon)
        self._begin_resolution(weapon_key, _group_label(pairs), pairs, self.target_squad)

    def _lock_other_melee_weapon(self, model, weapon):
        if not weapon.extra_attacks:
            self._used_other_melee_weapon.add(model)

    def _begin_resolution(self, weapon_key, weapon_label, pairs, target_squad):
        # Rule 19.04: open the "applies until the attacking unit has
        # resolved all of its attacks" window on this target before any
        # damage lands, and remember it so
        # _actually_finish_current_fight() can close it - the melee
        # counterpart of ShootingController's own bracket. Split Fire means
        # one fight activation can attack several units, hence a set.
        self._attacked_squads_this_activation.add(target_squad)
        attached_units.begin_attack_sequence(target_squad)
        self.current_group = {
            "weapon_key": weapon_key,
            "weapon_label": weapon_label,
            "pairs": pairs,
            "target_squad": target_squad,
        }
        self._twin_linked_used = False  # rule 24.38: fresh chance to re-roll for each new weapon group's attacks
        # ASPECT WARRIORS wargear - see shooting.py's identical pair and
        # game/aspect_shrine.py for why the dice COUNT is what gets kept.
        self._hit_dice_count = None
        self._wound_dice_count = None
        self._aspect_shrine_hit_offered = False
        self._aspect_shrine_wound_offered = False
        self._hit_reroll_used = False  # Monster Hunters: likewise a fresh chance per weapon group

        if not pairs or not target_squad.models:
            self._finish_group()
            return

        fighter_model = pairs[0][0]
        if self.turn_tracker is not None:
            self.turn_tracker.set_active(fighter_model.squad.owner)

        weapon = pairs[0][1]
        if weapon.attacks_notation is not None:
            # See shooting.py's identical branch - a dice-notation Attacks
            # characteristic (e.g. a printed "D6") has to be rolled, once
            # per attacking model, before the Hit roll can even start.
            self._pending_attacks_roll = DiceNotationRoll(
                weapon.attacks_notation, count=len(pairs), dice_manager=self.dice_manager,
                label=f"Attacks: {weapon_label} ({len(pairs)} model(s), {describe_dice_notation(weapon.attacks_notation)} each)",
                roll_kind=ATTACKS_ROLL, log=self._log,
                target_name=target_squad.name,
                attacker_squad=self.fighting_squad, target_squad=target_squad,
            )
            if self._pending_attacks_roll.is_pending:
                self.pending_step = "attacks"
                return
            total = self._pending_attacks_roll.total
            self._pending_attacks_roll = None
            total_attacks = total + extra_attack_dice(weapon, target_squad, weapon_key, self.split_fire, self.assignments, pairs)
            total_attacks += waaagh_extra_attacks(pairs, self.waaagh)
            self._continue_resolution_with_attacks(weapon, total_attacks)
            return

        total_attacks = sum(w.attacks for _, w in pairs)
        total_attacks += extra_attack_dice(weapon, target_squad, weapon_key, self.split_fire, self.assignments, pairs)
        total_attacks += waaagh_extra_attacks(pairs, self.waaagh)  # Orks army rule "Waaagh!" (user-supplied): +1 A to melee weapons of models with this ability, while active
        self._continue_resolution_with_attacks(weapon, total_attacks)

    def _continue_resolution_with_attacks(self, weapon, total_attacks):
        """See shooting.py's identical method - shared tail of
        _begin_resolution(), reached directly (a plain fixed-int Attacks
        characteristic) or after a dice-notation Attacks roll has been
        acknowledged."""
        group = self.current_group
        weapon_label, target_squad = group["weapon_label"], group["target_squad"]
        fighter_model = group["pairs"][0][0]
        # Rule 24.37 ([TORRENT]): "that attack automatically hits the
        # target" - no hit roll, so no die can come up a natural 6: every
        # attack becomes an ordinary (non-critical) hit.
        if weapon.torrent:
            # Orks army rule "Waaagh!" (user-supplied): +1 S to melee
            # weapons of models with this ability, while active - applied
            # here too (not just on_dice_acknowledged()'s own "wound" step
            # below) for the same reason melta_adjusted_weapon()/bonded_
            # heroes_adjusted_weapon() are chained at shooting.py's own
            # [TORRENT] shortcut: this path skips straight to
            # _handle_hit_results() without ever reaching that step. No
            # current Ork melee weapon actually has [TORRENT], but the
            # adjustment function is a no-op unless its own condition
            # applies, so this stays correct if one ever does.
            torrent_weapon = self._adjusted_weapon(group["pairs"], target_squad)
            # War Horde's Unbridled Carnage needs no equivalent hook here:
            # it only lowers the hit roll's CRITICAL threshold, and [TORRENT]
            # means there is no hit roll at all - no die exists to come up an
            # unmodified 5, exactly as none can come up a 6 (crits=0 below).
            self._log(f"{weapon_label} automatically hits ({total_attacks} attack(s)) - [TORRENT].")
            self._handle_hit_results(total_attacks, 0, torrent_weapon, target_squad, weapon_label)
            return
        hit_modifiers = self._hit_modifiers(fighter_model, target_squad)
        threshold = apply_modifiers(_parse_threshold(effective_weapon_skill(fighter_model, weapon)), hit_modifiers)
        label = f"Hit Roll: {weapon_label} ({total_attacks} attack(s))"
        if hit_modifiers:
            label += f" [{describe_modifiers(hit_modifiers)}]"
        self.dice_manager.roll(
            count=total_attacks, sides=6,
            label=label,
            success_threshold=threshold if threshold is not None else 7,
            target_name=target_squad.name, attacker_squad=self.fighting_squad, target_squad=target_squad, roll_kind=HIT_ROLL,
            # `weapon` here is the printed profile; the conditional grants
            # (Get Stuck In, Spirit of Gork) are only applied at resolution
            # time, so the note has to ask for the adjusted one itself.
            **self._crit_note("hit", self._adjusted_weapon(group["pairs"], target_squad), target_squad),
        )
        self.pending_step = "hit"

    def on_dice_acknowledged(self):
        # Rule 24.15 ([HAZARDOUS]): these two steps run after the unit's
        # last weapon group has already finished (current_group is None by
        # then) - handled up front, before the "no current_group" guard
        # below that every other pending_step relies on.
        if self.pending_step == "hazard":
            if self.dice_manager is None:
                return
            rolls = self.dice_manager.last_values
            total_mortal_wounds = hazard_mortal_wounds(self.fighting_squad, rolls)
            self._log(
                f"Hazard Rolls {rolls}: {hazard_failures(rolls)}/{len(rolls)} failed -> "
                f"{total_mortal_wounds} mortal wound(s)."
            )
            if total_mortal_wounds > 0:
                self.mortal_wound_session = MortalWoundAllocationSession(
                    self.fighting_squad, total_mortal_wounds, dice_manager=self.dice_manager, log=self._log,
                    waaagh=self.waaagh,
                )
                self.pending_step = "hazard_wounds"
                self._check_hazard_wounds_done()
            else:
                self._actually_finish_current_fight()
            return

        if self.pending_step == "hazard_wounds":
            if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
                self.mortal_wound_session.on_fnp_acknowledged()
                self._check_hazard_wounds_done()
            return

        if self.pending_step is None or self.dice_manager is None or self.current_group is None:
            return

        rolls = self.dice_manager.last_values
        group = self.current_group
        weapon_label = group["weapon_label"]
        weapon = group["pairs"][0][1]
        target_squad = group["target_squad"]
        if not any(not m.is_dead() for m in target_squad.models):
            # Same crash/fix as game/shooting.py's on_dice_acknowledged() -
            # see its comment for the full explanation (Split Fire locks in
            # targets before any group resolves, so a later queued group can
            # find its target already wiped out by an earlier one in the
            # same activation, before main.py's once-per-frame
            # state.remove_dead_models() even gets a chance to run).
            self._log(f'{target_squad.name} was destroyed before {weapon_label} could finish resolving - abandoned.')
            self._finish_group()
            return
        target_profile = allocation_target_profile(target_squad)

        if self.pending_step == "hold_still":
            # Painboy's "Hold Still and Say 'Aargh!'" - one D6 per critical
            # wound, summed, then allocated as ordinary mortal wounds (06.02).
            total = hold_still_rule.mortal_wounds(rolls)
            self._log(
                f"{hold_still_rule.HOLD_STILL_LABEL} {rolls}: {target_squad.name} suffers "
                f"{total} mortal wound(s)."
            )
            if total > 0:
                self.hold_still_session = MortalWoundAllocationSession(
                    target_squad, total, dice_manager=self.dice_manager, log=self._log,
                    waaagh=self.waaagh,
                )
                self.pending_step = "hold_still_wounds"
                self._check_hold_still_done()
            else:
                self._finish_group()
            return

        if self.pending_step == "hold_still_wounds":
            if self.hold_still_session is not None and self.hold_still_session.pending_fnp is not None:
                self.hold_still_session.on_fnp_acknowledged()
                self._check_hold_still_done()
            return

        if self.pending_step == "sustained_hits":
            # A dice-notation [SUSTAINED HITS X] (the Avatar of Khaine's
            # "d3"), acknowledged between the Hit roll and the Wound roll it
            # feeds - same shape as the "strength"/"attacks" branches.
            if self._pending_sustained_roll is None:
                return
            self._pending_sustained_roll.on_dice_acknowledged()
            if self._pending_sustained_roll.is_pending:
                return
            self._finish_sustained_hits_roll()
            return

        if self.pending_step == "attacks":
            # See shooting.py's identical branch - acknowledging a dice-
            # notation Attacks roll (weapon.attacks_notation) before the
            # real Hit roll can start. The RAW (un-adjusted) `weapon` is
            # used here, matching _begin_resolution()'s own synchronous
            # path exactly - see shooting.py's identical comment: Waaagh!'s
            # Strength bonus is applied once, below, only for the "hit"
            # step onward; using an already-adjusted weapon here would
            # double it once _continue_resolution_with_attacks()'s own
            # [TORRENT] check (if ever reached) re-applies it.
            if self._pending_attacks_roll is None:
                return
            self._pending_attacks_roll.on_dice_acknowledged()
            total = self._pending_attacks_roll.total
            self._pending_attacks_roll = None
            total_attacks = total + extra_attack_dice(
                weapon, target_squad, group["weapon_key"], self.split_fire, self.assignments, group["pairs"],
            )
            total_attacks += waaagh_extra_attacks(group["pairs"], self.waaagh)
            self._continue_resolution_with_attacks(weapon, total_attacks)
            return

        # Orks army rule "Waaagh!" (user-supplied): +1 S to melee weapons of
        # models with this ability, while active - applied once here so it
        # flows through every downstream use of `weapon` this call (wound
        # threshold, and - chained via melta_adjusted_weapon() - damage),
        # same reasoning/placement as shooting.py's own Bonded Heroes/
        # Starscythe/Drive-by Dakka chain. War Horde's Get Stuck In
        # (user-supplied): [SUSTAINED HITS 1] on Orks models' melee weapons,
        # chained right after for the same reason - it has to be in place
        # BEFORE the "hit" step below reads weapon.sustained_hits, not just
        # at the wound step (Waaagh!'s own S/AP-only adjustment could wait
        # either way, since neither touches sustained_hits - so ordering
        # between the two doesn't matter here).
        weapon = self._adjusted_weapon(group["pairs"], group["target_squad"])
        if self.pending_step == "hit":
            threshold = apply_modifiers(
                _parse_threshold(effective_weapon_skill(group["pairs"][0][0], weapon)),
                self._hit_modifiers(group["pairs"][0][0], target_squad),
            )
            # Unbridled Carnage, Mandiblasters and Whispering Web all say
            # "an unmodified hit roll of 5+ scores a Critical Hit" - i.e.
            # purely a change to _resolve_roll's crit threshold, which is
            # already compared against the RAW die (so "unmodified" is
            # satisfied by construction, a -1 to hit still misses on a 4).
            # Default 6 otherwise, per rule 05.02. melee_only=True admits the
            # two melee-worded sources; see game/crit_hit.py.
            crit_threshold = crit_hit_threshold(
                group["pairs"][0][0], target_squad, self.whispering_web, melee_only=True,
            )
            results = [_resolve_roll(r, threshold, crit_threshold) for r in rolls]
            hits = sum(1 for r in results if r != "fail")
            crits = sum(1 for r in results if r == "critical")
            misses = len(rolls) - hits
            self._hit_dice_count = len(rolls)
            self._log(
                f"{weapon_label} hit roll {rolls}"
                f"{_threshold_note(threshold, _parse_threshold(effective_weapon_skill(group['pairs'][0][0], weapon)), self._hit_modifiers(group['pairs'][0][0], target_squad))}: "
                f"{hits} hit(s) (of which {crits} critical), {misses} miss(es)."
            )
            # Beast Snagga Boyz' Monster Hunters (user-supplied): its text
            # says "makes an attack", not "makes a ranged attack", so it
            # applies here as well as in shooting.py - the same both-phases
            # reasoning as Tank Hunters. A dice can never be re-rolled more
            # than once, so only the still-free share may be thrown again
            # (see shooting.py's identical split).
            spent = self.dice_manager.already_rerolled if self.dice_manager is not None else set()
            free = [i for i in range(len(rolls)) if i not in spent]
            rerollable = (
                sum(1 for i in free if results[i] != "fail"),
                sum(1 for i in free if results[i] == "critical"),
                len(free),
            )
            ones = sum(1 for i in free if rolls[i] == 1)
            self._finish_hit_roll(hits, crits, weapon, target_squad, weapon_label, rerollable, threshold,
                                  ones=ones)

        elif self.pending_step == "hit_reroll_ones":
            ctx = self._pending_ones_reroll
            self._pending_ones_reroll = None
            crit_threshold = crit_hit_threshold(
                group["pairs"][0][0], target_squad, self.whispering_web, melee_only=True,
            )
            results = [_resolve_roll(r, ctx["threshold"], crit_threshold) for r in rolls]
            extra_hits = sum(1 for r in results if r != "fail")
            extra_crits = sum(1 for r in results if r == "critical")
            self._log(
                f"{ctx['weapon_label']}: {ctx.get('reason', 'ability')} re-roll of 1s {rolls} -> "
                f"{extra_hits} additional hit(s) (of which {extra_crits} critical)."
            )
            self._apply_sustained_hits(
                ctx["hits"] + extra_hits, ctx["crits"] + extra_crits, ctx["weapon"],
                ctx["target_squad"], ctx["weapon_label"],
            )

        elif self.pending_step == "wound_reroll_ones":
            ctx = self._pending_ones_reroll
            self._pending_ones_reroll = None
            crit_threshold = _wound_crit_threshold(ctx["weapon"], ctx["target_squad"])
            results = [_resolve_roll(r, ctx["threshold"], crit_threshold) for r in rolls]
            extra_wounds = sum(1 for r in results if r != "fail")
            extra_crits = sum(1 for r in results if r == "critical")
            self._log(
                f"{ctx['weapon_label']}: {ctx.get('reason', 'ability')} re-roll of 1s {rolls} -> "
                f"{extra_wounds} additional wound(s) (of which {extra_crits} critical)."
            )
            self._resolve_wounds(
                ctx["weapon"], ctx["target_squad"], ctx["target_profile"], ctx["weapon_label"],
                ctx["wounds"] + extra_wounds, ctx["crits"] + extra_crits,
            )

        elif self.pending_step == "hit_monster_hunters_reroll":
            # Which scope the player picked arrives purely as "how many
            # hits/crits are carried over" - see shooting.py's identical
            # branch.
            ctx = self._pending_hit_reroll
            self._pending_hit_reroll = None
            crit_threshold = crit_hit_threshold(
                group["pairs"][0][0], target_squad, self.whispering_web, melee_only=True,
            )
            results = [_resolve_roll(r, ctx["hit_threshold"], crit_threshold) for r in rolls]
            extra_hits = sum(1 for r in results if r != "fail")
            extra_crits = sum(1 for r in results if r == "critical")
            if ctx.get("full"):
                self._log(
                    f"{ctx['weapon_label']}: re-rolled the whole Hit roll {rolls} ({ctx['reason']}) -> "
                    f"{extra_hits} hit(s) (of which {extra_crits} critical); the previous roll is discarded."
                )
            else:
                self._log(
                    f"{ctx['weapon_label']}: re-rolled failed hit rolls {rolls} ({ctx['reason']}) -> "
                    f"{extra_hits} additional hit(s) (of which {extra_crits} critical)."
                )
            self._apply_sustained_hits(
                ctx["hits"] + extra_hits, ctx["crits"] + extra_crits, ctx["weapon"], ctx["target_squad"],
                ctx["weapon_label"],
            )

        elif self.pending_step == "wound":
            wound_threshold = _wound_threshold(weapon.strength, attached_unit_toughness(target_squad))
            wound_threshold = apply_modifiers(wound_threshold, self._wound_modifiers(weapon, target_squad))
            crit_threshold = _wound_crit_threshold(weapon, target_squad)
            results = [_resolve_roll(r, wound_threshold, crit_threshold) for r in rolls]
            wounds = sum(1 for r in results if r != "fail")
            crits = sum(1 for r in results if r == "critical")
            no_effect = len(rolls) - wounds
            self._wound_dice_count = len(rolls)
            # A dice can never be re-rolled more than once, so a failure a
            # Command Re-roll (15.02) already threw is not [TWIN-LINKED]'s to
            # throw again - DiceManager.already_rerolled is where that memory
            # lives (see shooting.py's identical split).
            spent = self.dice_manager.already_rerolled if self.dice_manager is not None else set()
            free_no_effect = sum(1 for i, r in enumerate(results) if r == "fail" and i not in spent)
            # ...and the rest of the breakdown, needed once a source offers a
            # WHOLE-roll re-roll rather than only its failures (Storm of
            # Silence) - the same split shooting.py already makes.
            free_wounds = sum(1 for i, r in enumerate(results) if r != "fail" and i not in spent)
            free_crits = sum(1 for i, r in enumerate(results) if r == "critical" and i not in spent)
            rerollable = (free_wounds, free_crits, free_no_effect)
            self._log(
                f"{weapon_label} wound roll {rolls}"
                f"{_threshold_note(wound_threshold, _wound_threshold(weapon.strength, attached_unit_toughness(target_squad)), self._wound_modifiers(weapon, target_squad))}: "
                f"{wounds} wound(s) (of which {crits} critical), {no_effect} no effect."
            )
            ones = sum(1 for i, r in enumerate(rolls) if r == 1 and i not in spent)
            if self._twin_linked_choice_needed(weapon, free_no_effect, target_squad):
                self._offer_twin_linked_choice(
                    free_no_effect, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold,
                    self.fighting_squad.owner, rerollable, ones=ones,
                )
            elif ones and implacable_eradication.applies(self.fighting_squad):
                # The base clause, fired only when its whole-roll alternative
                # was NOT offered above - "instead" makes the two exclusive.
                self._begin_ones_reroll(
                    "wound", ones, wound_threshold, weapon, target_squad, weapon_label,
                    wounds=wounds, crits=crits, target_profile=target_profile,
                    reason=implacable_eradication.IMPLACABLE_ERADICATION_LABEL,
                )
            else:
                self._resolve_wounds(weapon, target_squad, target_profile, weapon_label, wounds, crits)

        elif self.pending_step == "wound_twin_linked_reroll":
            # Rule 24.38 ([TWIN-LINKED]): only the FAILED wound dice get
            # re-rolled (user correction: "es sollten nur fails sein") -
            # the wounds/crits already rolled are kept as-is (stashed in
            # _pending_twin_linked_reroll by _reroll_wound()).
            ctx = self._pending_twin_linked_reroll
            self._pending_twin_linked_reroll = None
            crit_threshold = _wound_crit_threshold(ctx["weapon"], ctx["target_squad"])
            results = [_resolve_roll(r, ctx["wound_threshold"], crit_threshold) for r in rolls]
            extra_wounds = sum(1 for r in results if r != "fail")
            extra_crits = sum(1 for r in results if r == "critical")
            self._log(
                f"{ctx['weapon_label']}: re-rolled failed wounds {rolls} [TWIN-LINKED] -> "
                f"{extra_wounds} additional wound(s) (of which {extra_crits} critical)."
            )
            self._resolve_wounds(
                ctx["weapon"], ctx["target_squad"], ctx["target_profile"], ctx["weapon_label"],
                ctx["wounds"] + extra_wounds, ctx["crits"] + extra_crits,
            )

        elif self.pending_step == "save":
            damage_weapon = melta_adjusted_weapon(weapon, group["pairs"], target_squad)
            if self._precision_choice_needed(weapon, target_squad):
                self._offer_precision_choice(rolls, damage_weapon, target_squad, weapon_label, self.fighting_squad.owner)
            else:
                self._begin_damage_allocation(rolls, damage_weapon, target_squad, priority_group=None)

        elif self.pending_step == "allocate":
            # See shooting.py's identical branch: routes to whichever of
            # DamageAllocationSession's own dice steps is actually pending -
            # its dice-notation Damage roll or (rule 24.12) Feel No Pain.
            if self.damage_session is not None:
                if self.damage_session.pending_damage_roll is not None:
                    self.damage_session.on_damage_roll_acknowledged()
                else:
                    self.damage_session.on_fnp_acknowledged()
                self._check_allocation_done()

        elif self.pending_step == "devastating":
            if self.devastating_wound_session is not None:
                self.devastating_wound_session.on_fnp_acknowledged()
                self._check_devastating_wounds_done()

    def _adjusted_weapon(self, pairs, target_squad=None):
        """This weapon group's melee profile with every conditional grant
        applied, in one place - game/shooting.py's own _adjusted_weapon() for
        the ranged side.

        Waaagh! (+1 S), War Horde's Get Stuck In ([SUSTAINED HITS 1]),
        Ferocious Rage ([DEVASTATING WOUNDS]) and Spirit of Gork (+1 S and
        [LETHAL HITS]). Order matters for the last three: the hit and wound
        steps read those keywords straight off the returned weapon, so they
        have to be in place before those steps run. Waaagh! only touches
        Strength/AP, so where it sits among them does not matter.

        Extracted because three callers need the same answer and must not
        disagree: the [TORRENT] shortcut (which skips straight to
        _handle_hit_results without ever reaching the hit step),
        on_dice_acknowledged()'s own resolution, and _crit_note(), which has
        to know at ROLL time whether a critical die is a [LETHAL HITS] or
        [DEVASTATING WOUNDS] one - the grants are what decide that, and they
        are conditional. Unbridled Carnage needs no place here: it lowers the
        hit roll's CRITICAL threshold rather than granting a keyword, and
        _crit_note()/the hit step both read that from crit_hit_threshold()."""
        weapon = waaagh_melee_adjusted_weapon(pairs[0][1], pairs, self.waaagh)
        weapon = get_stuck_in_adjusted_weapon(weapon, pairs)
        weapon = ferocious_rage_adjusted_weapon(
            weapon, pairs, self.charge_controller, self.fighting_squad,
        )
        weapon = spirit_of_gork_adjusted_weapon(weapon, self.fighting_squad)
        # Illuminor Szeras's Mechanical Augmentation. Its printed text says
        # "makes an attack", not "a ranged attack", so it reaches this phase
        # too. `target_squad` falls back to the controller's current one for
        # any caller that has none in hand - the defender half is the only
        # part that needs it, and it is simply skipped when it is unknown.
        weapon = mechanical_augmentation.adjusted_weapon(
            weapon, self.fighting_squad,
            target_squad if target_squad is not None else self.target_squad,
            self.all_tokens)
        # Skorpekh Destroyers' Plasmacyte: [DEVASTATING WOUNDS] on melee
        # weapons until the end of the phase - the same shape as Ferocious
        # Rage above, and in the chain for the same reason: _crit_note()
        # must know at ROLL time that a critical die is a devastating one.
        weapon = plasmacyte.adjusted_weapon(weapon, self.fighting_squad)
        # Awakened Dynasty's Protocol of the Hungry Void: +1 Strength on melee
        # weapons, and +1 AP as well while a CHARACTER leads the unit. Last in
        # the chain because it changes S/AP only - nothing downstream reads a
        # keyword it might have granted.
        return protocol_hungry_void.adjusted_weapon(weapon, self.fighting_squad)

    def _crit_note(self, kind, weapon, target_squad):
        """See game/shooting.py's _crit_note - identical purpose, with
        melee_only=True on the hit threshold (Unbridled Carnage and
        Mandiblasters are both worded "melee attack"; see game/crit_hit.py)
        and `weapon` expected to be _adjusted_weapon()'s result."""
        if kind == "hit":
            model = self.current_group["pairs"][0][0] if self.current_group else None
            threshold = crit_hit_threshold(model, target_squad, self.whispering_web, melee_only=True)
            labels = []
            if weapon.lethal_hits:
                labels.append("LETHAL HIT")
            if weapon.sustained_hits or weapon.sustained_hits_notation is not None:
                labels.append("SUSTAINED HIT")
        else:
            threshold = _wound_crit_threshold(weapon, target_squad)
            labels = ["DEVASTATING WOUND"] if weapon.devastating_wounds else []
        return {"crit_threshold": threshold, "crit_labels": tuple(labels)}

    def _handle_hit_results(self, hits, crits, weapon, target_squad, weapon_label):
        """See shooting.py's identical method - shared continuation after
        the hit count is known, whether from an actual hit roll or (rule
        24.37, [TORRENT]) with no roll at all."""
        if hits > 0:
            # Rule 24.23 ([LETHAL HITS]) is taken for every critical hit
            # without asking - see shooting.py's identical branch for the
            # user report and the trade it accepts.
            self._continue_after_hit_roll(
                hits, crits if weapon.lethal_hits else 0, weapon, target_squad, weapon_label,
            )
        else:
            self._finish_group()

    def _continue_after_hit_roll(self, hits, auto_wounds, weapon, target_squad, weapon_label):
        """See shooting.py's _continue_after_hit_roll. Also where the
        [LANCE] (24.21) wound-roll modifier gets applied to the actual
        wound dice's success_threshold, when there's a roll left to make."""
        self._lethal_hits_auto_wounds = auto_wounds
        remaining = hits - auto_wounds
        if remaining > 0:
            wound_threshold = _wound_threshold(weapon.strength, attached_unit_toughness(target_squad))
            wound_modifiers = self._wound_modifiers(weapon, target_squad)
            wound_threshold = apply_modifiers(wound_threshold, wound_modifiers)
            label = f"Wound Roll: {weapon_label} ({remaining} hit(s))"
            if wound_modifiers:
                label += f" [{describe_modifiers(wound_modifiers)}]"
            self.dice_manager.roll(
                count=remaining, sides=6,
                label=label,
                success_threshold=wound_threshold,
                target_name=target_squad.name, attacker_squad=self.fighting_squad, target_squad=target_squad, roll_kind=WOUND_ROLL,
                **self._crit_note("wound", weapon, target_squad),
            )
            self.pending_step = "wound"
        else:
            target_profile = allocation_target_profile(target_squad)
            self._resolve_wounds(weapon, target_squad, target_profile, weapon_label, wounds=0, crits=0)

    def _resolve_wounds(self, weapon, target_squad, target_profile, weapon_label, wounds, crits):
        """The wound step's funnel, and so where an Aspect Shrine token is
        offered - see shooting.py's identical pair."""
        if self._offer_aspect_shrine_wound(weapon, target_squad, target_profile, weapon_label, wounds, crits):
            return
        self._resolve_wounds_now(weapon, target_squad, target_profile, weapon_label, wounds, crits)

    def _offer_aspect_shrine_wound(self, weapon, target_squad, target_profile, weapon_label, wounds, crits):
        """See shooting.py's method of the same name."""
        if self.decision_manager is None or self.current_group is None or self._aspect_shrine_wound_offered:
            return False
        squad = self.fighting_squad
        pairs = self.current_group.get("pairs") or ()
        model = pairs[0][0] if pairs else None
        no_effect = 0 if self._wound_dice_count is None else max(0, self._wound_dice_count - wounds)
        source, change = _unmodified_six_source(
            "wound_change", squad, model, weapon, wounds, crits, no_effect)
        if change is None:
            return False
        self._aspect_shrine_wound_offered = True
        new_wounds, new_crits, _new_no_effect, what = change

        def spend():
            source.spend(squad)
            self._log(
                f"{weapon_label}: {source.ACCEPT_LABEL} - one wound roll counts as an unmodified 6 "
                f"({wounds} wound(s) of which {crits} critical -> {new_wounds} of which {new_crits})."
            )
            self._resolve_wounds_now(weapon, target_squad, target_profile, weapon_label, new_wounds, new_crits)

        def keep():
            self._resolve_wounds_now(weapon, target_squad, target_profile, weapon_label, wounds, crits)

        self.decision_manager.request(
            squad.owner, source.prompt_for(squad, weapon_label, what, "wound"),
            [(source.ACCEPT_LABEL, spend), ("Keep the roll", keep)],
        )
        return True

    def _resolve_wounds_now(self, weapon, target_squad, target_profile, weapon_label, wounds, crits):
        """See shooting.py's _resolve_wounds_now - identical shared tail end of
        wound resolution (Devastating Wounds routing, Lethal Hits auto-wound
        pool, save roll)."""
        self._devastating_crits = crits if weapon.devastating_wounds else 0
        # Painboy's "Hold Still and Say 'Aargh!'" - note these crits are NOT
        # subtracted from normal_wounds below, unlike [DEVASTATING WOUNDS]'
        # own: that rule replaces the rest of the attack sequence for the
        # wound, this one leaves it alone and adds mortal wounds on top. See
        # game/hold_still.py.
        self._hold_still_crits = crits if hold_still_rule.applies(weapon, target_squad) else 0
        normal_wounds = wounds - self._devastating_crits + self._lethal_hits_auto_wounds
        self._lethal_hits_auto_wounds = 0

        if normal_wounds > 0:
            if self.turn_tracker is not None:
                # Rule 05.03/05.04: save rolls and damage allocation are the
                # *defending* player's decisions, not the attacker's.
                self.turn_tracker.set_active(target_squad.owner)

            # The number a die must REACH, from the same definition
            # game/damage_resolution.py resolves the save with - so a die
            # saved by the INVULNERABLE save (or under Ramshackle's worsened
            # AP) is no longer coloured red and counted as a failure. User
            # report: "oft werden bestandene rettungswuerfe rot angezeigt".
            save_threshold = displayed_save_threshold(
                allocation_target_model(target_squad), weapon, self.waaagh,
            )
            # Melta-adjusted damage preview (rule 24.25) - positions don't
            # change between kicking off this roll and its acknowledgement,
            # so this is the same value _begin_damage_allocation() will use.
            # See shooting.py's identical spot: None whenever Damage is
            # dice-notation, suppressing the preview line entirely.
            melta_weapon = melta_adjusted_weapon(weapon, self.current_group["pairs"], target_squad)
            damage_preview = None if melta_weapon.damage_notation is not None else melta_weapon.damage
            self.dice_manager.roll(
                count=normal_wounds, sides=6,
                label=f"Save Roll: {weapon_label} ({normal_wounds} wound(s))",
                success_threshold=save_threshold if save_threshold is not None else 7,
                target_name=target_squad.name, attacker_squad=self.fighting_squad, target_squad=target_squad, roll_kind=SAVE_ROLL,
                damage_per_failure=damage_preview,
            )
            self.pending_step = "save"
        elif self._devastating_crits > 0:
            self._begin_devastating_wounds(weapon, target_squad)
        else:
            self._finish_group_after_wounds()

    def _finish_group_after_wounds(self):
        """The shared tail of every path that has finished a weapon group's
        wound/save resolution. Painboy's "Hold Still and Say 'Aargh!'" runs
        here - after the attack itself has been fully resolved, because the
        mortal wounds it inflicts are in ADDITION to that attack, not instead
        of it (see game/hold_still.py). Anything else goes straight on to
        _finish_group() as before."""
        if self._hold_still_crits > 0 and self.current_group is not None and self.dice_manager is not None:
            self._begin_hold_still_wounds()
        else:
            self._finish_group()

    def _begin_hold_still_wounds(self):
        crits = self._hold_still_crits
        self._hold_still_crits = 0
        target_squad = self.current_group["target_squad"]
        if self.turn_tracker is not None:
            # Rule 06.02: the mortal wounds land on the TARGET unit, so which
            # of its models take them is the DEFENDING player's choice - the
            # same flip _resolve_wounds() makes before a save roll.
            self.turn_tracker.set_active(target_squad.owner)
        self.dice_manager.roll(
            count=hold_still_rule.dice_count(crits), sides=hold_still_rule.HOLD_STILL_DICE_SIDES,
            label=hold_still_rule.roll_label(crits, target_squad),
            target_name=target_squad.name, attacker_squad=self.fighting_squad, target_squad=target_squad,
        )
        self.pending_step = "hold_still"

    def _check_hold_still_done(self):
        if self.hold_still_session is None or not self.hold_still_session.done:
            return
        self.hold_still_session = None
        self._finish_group()

    @property
    def pending_damage_choice(self):
        """Board-highlight helper: candidate models the (defending, or -
        rule 24.15's [HAZARDOUS] - fighting) player must pick from to
        receive the current failed save's wound, Devastating Wounds mortal
        wound, or Hazardous mortal wound, or None."""
        if self.damage_session is not None:
            return self.damage_session.pending_choice
        if self.devastating_wound_session is not None:
            return self.devastating_wound_session.pending_choice
        if self.mortal_wound_session is not None:
            return self.mortal_wound_session.pending_choice
        if self.hold_still_session is not None:
            return self.hold_still_session.pending_choice
        return None

    def choose_damage_model(self, model):
        """Rule 05.04/24.10/24.15: the defending (or, for Hazardous,
        fighting) player's choice of which model takes a wound (normal
        damage), a Devastating Wounds mortal wound, or a Hazardous mortal
        wound, when more than one model in the group qualifies."""
        if self.damage_session is not None:
            self.damage_session.choose_model(model)
            self._check_allocation_done()
        elif self.devastating_wound_session is not None:
            self.devastating_wound_session.choose_model(model)
            self._check_devastating_wounds_done()
        elif self.mortal_wound_session is not None:
            self.mortal_wound_session.choose_model(model)
            self._check_hazard_wounds_done()
        elif self.hold_still_session is not None:
            self.hold_still_session.choose_model(model)
            self._check_hold_still_done()

    def _check_allocation_done(self, rolls=None):
        if not self.damage_session.done:
            return
        saved, failed = self.damage_session.saved, self.damage_session.failed
        weapon_label = self.current_group["weapon_label"]
        summary = f"{weapon_label} save roll"
        if rolls is not None:
            summary += f" {rolls}"
        self._log(f"{summary}: {saved} saved, {failed} failed.")
        self.damage_session = None
        if self._devastating_crits > 0:
            weapon = self.current_group["pairs"][0][1]
            target_squad = self.current_group["target_squad"]
            self._begin_devastating_wounds(weapon, target_squad)
        else:
            self._finish_group_after_wounds()

    def _begin_devastating_wounds(self, weapon, target_squad):
        damage_weapon = melta_adjusted_weapon(weapon, self.current_group["pairs"], target_squad)
        self.devastating_wound_session = DevastatingWoundAllocationSession(
            target_squad, damage_weapon.damage, self._devastating_crits, dice_manager=self.dice_manager, log=self._log,
            waaagh=self.waaagh,
        )
        self._devastating_crits = 0
        self.pending_step = "devastating"
        self._check_devastating_wounds_done()

    def _check_devastating_wounds_done(self):
        if self.devastating_wound_session is None or not self.devastating_wound_session.done:
            return
        self.devastating_wound_session = None
        self._finish_group_after_wounds()

    def _hit_reroll_reason(self, target_squad):
        """Which ability grants a re-roll of THIS group's Hit roll, as a label.

        The melee twin of shooting.py's method of the same name. Skorpekh
        Destroyers' Whirling Onslaught is a two-clause source, so - exactly as
        Swift Demise is on the ranged side - it counts as a "reason" only when
        its WHOLE-roll half is live; its base clause is the automatic 1s."""
        if monster_hunters.applies(self.fighting_squad, target_squad):
            return monster_hunters.MONSTER_HUNTERS_REROLL_LABEL
        if destroyer_cult.whirling_onslaught_offers_full_reroll(self.fighting_squad):
            return destroyer_cult.WHIRLING_ONSLAUGHT_LABEL
        return None

    def _begin_ones_reroll(self, kind, ones, threshold, weapon, target_squad, weapon_label, **ctx):
        """The automatic "re-roll a Hit/Wound roll of 1" half of a two-clause
        source, as a real visible dice step - see shooting.py's method of the
        same name, which this mirrors so the two phases behave alike.

        Not optional ("re-roll", not "you can"), so nothing is prompted.
        is_reroll=True marks the dice thrown here as spent, which is what stops
        anything throwing them a second time."""
        self._pending_ones_reroll = {
            "kind": kind, "ones": ones, "threshold": threshold, "weapon": weapon,
            "target_squad": target_squad, "weapon_label": weapon_label, **ctx,
        }
        self.dice_manager.roll(
            count=ones, sides=6,
            label=f"{weapon_label}: {'Hit' if kind == 'hit' else 'Wound'} Roll re-roll of 1s "
                  f"({ctx.get('reason', 'ability')})",
            success_threshold=threshold, target_name=target_squad.name,
            attacker_squad=self.fighting_squad, target_squad=target_squad,
            is_reroll=True,
        )
        self.pending_step = f"{kind}_reroll_ones"

    def _finish_hit_roll(self, hits, crits, weapon, target_squad, weapon_label, rerollable, hit_threshold, ones=0):
        """Tail of the hit-roll step - offers Monster Hunters' optional
        re-roll of the whole Hit roll BEFORE [SUSTAINED HITS] is applied,
        since the extra hits a critical grants have to be computed from
        whichever roll actually stands. See shooting.py's identical method
        and game/monster_hunters.py's own docstring for why this re-rolls
        the whole roll rather than just the misses."""
        if self._hit_reroll_choice_needed(target_squad, rerollable[2]):
            self._offer_hit_reroll_choice(
                hits, crits, weapon, target_squad, weapon_label, hit_threshold, rerollable,
                self.fighting_squad.owner, ones=ones,
            )
            return
        # Whirling Onslaught's base clause. Held back above while its
        # whole-roll alternative is actually on offer, because "instead" makes
        # the two exclusive - the same arrangement shooting.py uses.
        if ones and destroyer_cult.whirling_onslaught_applies(self.fighting_squad):
            free_hits, free_crits, free_count = rerollable
            self._begin_ones_reroll(
                "hit", ones, hit_threshold, weapon, target_squad, weapon_label,
                hits=hits, crits=crits, reason=destroyer_cult.WHIRLING_ONSLAUGHT_LABEL,
                rerollable=(free_hits, free_crits, free_count - ones),
            )
            return
        self._apply_sustained_hits(hits, crits, weapon, target_squad, weapon_label)

    def _apply_sustained_hits(self, hits, crits, weapon, target_squad, weapon_label):
        """The funnel every path through the hit step reaches, and therefore
        where an Aspect Shrine token is offered - see shooting.py's identical
        pair of methods."""
        if self._offer_aspect_shrine_hit(hits, crits, weapon, target_squad, weapon_label):
            return
        self._apply_sustained_hits_now(hits, crits, weapon, target_squad, weapon_label)

    def _offer_aspect_shrine_hit(self, hits, crits, weapon, target_squad, weapon_label):
        """See shooting.py's method of the same name."""
        if self.decision_manager is None or self.current_group is None or self._aspect_shrine_hit_offered:
            return False
        squad = self.fighting_squad
        pairs = self.current_group.get("pairs") or ()
        model = pairs[0][0] if pairs else None
        misses = 0 if self._hit_dice_count is None else max(0, self._hit_dice_count - hits)
        source, change = _unmodified_six_source(
            "hit_change", squad, model, weapon, hits, crits, misses)
        if change is None:
            return False
        self._aspect_shrine_hit_offered = True
        new_hits, new_crits, what = change

        def spend():
            source.spend(squad)
            self._log(
                f"{weapon_label}: {source.ACCEPT_LABEL} - one hit roll counts as an unmodified 6 "
                f"({hits} hit(s) of which {crits} critical -> {new_hits} of which {new_crits})."
            )
            self._apply_sustained_hits_now(new_hits, new_crits, weapon, target_squad, weapon_label)

        def keep():
            self._apply_sustained_hits_now(hits, crits, weapon, target_squad, weapon_label)

        self.decision_manager.request(
            squad.owner, source.prompt_for(squad, weapon_label, what, "hit"),
            [(source.ACCEPT_LABEL, spend), ("Keep the roll", keep)],
        )
        return True

    def _apply_sustained_hits_now(self, hits, crits, weapon, target_squad, weapon_label):
        """Rule 24.36 ([SUSTAINED HITS X]): see shooting.py's identical
        method - extra hits are ordinary (non-critical), so `crits` stays
        untouched for [LETHAL HITS]'s purposes downstream."""
        if crits and weapon.sustained_hits_notation is not None:
            self._begin_sustained_hits_roll(hits, crits, weapon, target_squad, weapon_label)
            return
        self._add_sustained_hits(
            hits, crits, crits * weapon.sustained_hits, weapon, target_squad, weapon_label,
        )

    def _begin_sustained_hits_roll(self, hits, crits, weapon, target_squad, weapon_label):
        """[SUSTAINED HITS X] where X is itself a die (the Avatar of Khaine's
        printed "d3"). One die PER CRITICAL HIT, thrown as a single visible
        roll and summed - which is the fast-dice equivalent of rolling each
        critical hit's own X and adds up to the same distribution.

        Same shape as _begin_strength_roll()/the "attacks" step: a real
        dice_manager step rather than the "use the die's maximum as a fixed
        value" simplification, with the hit step's context stashed so it can
        carry on once the roll resolves."""
        self._pending_sustained = {
            "hits": hits, "crits": crits, "weapon": weapon,
            "target_squad": target_squad, "weapon_label": weapon_label,
        }
        self._pending_sustained_roll = DiceNotationRoll(
            weapon.sustained_hits_notation, count=crits, dice_manager=self.dice_manager,
            label=(f"[SUSTAINED HITS {describe_dice_notation(weapon.sustained_hits_notation)}]: "
                   f"{weapon_label} ({crits} critical hit(s))"),
            log=self._log, target_name=target_squad.name,
            attacker_squad=self.fighting_squad, target_squad=target_squad,
        )
        if self._pending_sustained_roll.is_pending:
            self.pending_step = "sustained_hits"
            return
        # No dice_manager (the non-interactive test wrappers): resolved
        # immediately, same convenience path DiceNotationRoll documents.
        self._finish_sustained_hits_roll()

    def _finish_sustained_hits_roll(self):
        ctx = self._pending_sustained
        total = self._pending_sustained_roll.total
        self._pending_sustained = None
        self._pending_sustained_roll = None
        self._add_sustained_hits(
            ctx["hits"], ctx["crits"], total, ctx["weapon"], ctx["target_squad"], ctx["weapon_label"],
        )

    def _add_sustained_hits(self, hits, crits, sustained, weapon, target_squad, weapon_label):
        """The shared tail: fold the extra hits in and carry on. `crits` is
        deliberately NOT increased - rule 24.36's extra hits are ordinary
        hits, which is what [LETHAL HITS] downstream depends on."""
        hits += sustained
        if sustained:
            self._log(f"{weapon_label}: [SUSTAINED HITS] adds {sustained} extra hit(s).")
        self._handle_hit_results(hits, crits, weapon, target_squad, weapon_label)

    def _hit_reroll_choice_needed(self, target_squad, free_count):
        """Beast Snagga Boyz' Monster Hunters: see shooting.py's identical
        method. Once per weapon group's attack sequence, and pointless with
        no re-rollable dice left."""
        if self.decision_manager is None or self._hit_reroll_used:
            return False
        return free_count > 0 and self._hit_reroll_reason(target_squad) is not None

    def _offer_hit_reroll_choice(self, hits, crits, weapon, target_squad, weapon_label, hit_threshold, rerollable, owner, ones=0):
        """Both scopes are offered as real choices - failures only (never a
        loss) or the whole roll (can lose hits, but can improve a roll whose
        failures are few). See shooting.py's identical method for the full
        reasoning and the user instruction behind it."""
        reason = self._hit_reroll_reason(target_squad)
        free_hits, free_crits, free_count = rerollable
        free_misses = free_count - free_hits
        kept_hits, kept_crits = hits - free_hits, crits - free_crits
        # A two-clause source (Whirling Onslaught) grants the 1s OR the whole
        # roll - "failures only" is not among its options, since that would
        # allow re-rolling a 2 that missed. See game/reroll_scope.py.
        ones_or_whole = reroll_scope.is_ones_or_whole(reason)
        options = []
        if free_misses > 0 and not ones_or_whole:
            options.append((
                f"Re-roll failed hit rolls ({free_misses} dice)",
                lambda: self._reroll_hit(
                    free_misses, hits, crits, weapon, target_squad, weapon_label, hit_threshold, reason,
                ),
            ))
        options.append((
            f"Re-roll the whole Hit roll ({free_count} dice)",
            lambda: self._reroll_hit(
                free_count, kept_hits, kept_crits, weapon, target_squad, weapon_label, hit_threshold, reason,
                full=True,
            ),
        ))
        # With 1s on the table a two-clause source's base clause is
        # MANDATORY, so "keep result" is not a legal answer - the player picks
        # which of the two re-rolls to take.
        if ones_or_whole and ones > 0:
            options.append((
                f"Re-roll the 1s only ({ones} dice)",
                lambda: self._begin_ones_reroll(
                    "hit", ones, hit_threshold, weapon, target_squad, weapon_label,
                    hits=hits, crits=crits, reason=reason,
                    rerollable=(free_hits, free_crits, free_count - ones),
                ),
            ))
        else:
            options.append(
                ("Keep result", lambda: self._apply_sustained_hits(hits, crits, weapon, target_squad, weapon_label))
            )
        self._hit_reroll_used = True
        self.decision_manager.request(owner, f"{weapon_label}: {reason} - re-roll the Hit roll?", options)

    def _reroll_hit(self, count, hits, crits, weapon, target_squad, weapon_label, hit_threshold, reason, full=False):
        """See shooting.py's identical method - `hits`/`crits` are only what
        the caller carries over, which is what distinguishes the two scopes."""
        self._hit_reroll_used = True
        self._pending_hit_reroll = {
            "hits": hits, "crits": crits, "weapon": weapon, "target_squad": target_squad,
            "weapon_label": weapon_label, "hit_threshold": hit_threshold, "reason": reason, "full": full,
        }
        scope = f"re-rolling all {count}" if full else f"re-rolling {count} failed"
        self.dice_manager.roll(
            count=count, sides=6, label=f"Hit Roll ({scope}): {weapon_label} {reason}",
            success_threshold=hit_threshold, target_name=target_squad.name, attacker_squad=self.fighting_squad, target_squad=target_squad, roll_kind=HIT_ROLL,
            is_reroll=True,  # these dice have now used their one re-roll
            **self._crit_note("hit", weapon, target_squad),
        )
        self.pending_step = "hit_monster_hunters_reroll"

    def _wound_reroll_reason(self, weapon, target_squad):
        """Which ability, if any, grants a re-roll of THIS group's Wound roll -
        the melee twin of shooting.py's method of the same name, which this
        side did not have until a second source needed it.

        Rule 24.38 ([TWIN-LINKED]) is listed first so that a [TWIN-LINKED]
        weapon keeps that label and its failures-only scope, which is the
        stricter of the two and cannot lose a wound already rolled - the same
        precedence, for the same reason, as on the shooting side."""
        if weapon.twin_linked:
            return "[TWIN-LINKED]"
        model = self.current_group["pairs"][0][0] if self.current_group and self.current_group.get("pairs") else None
        if storm_of_silence.applies(model, target_squad):
            return storm_of_silence.STORM_OF_SILENCE_LABEL
        # Immortals' Implacable Eradication says "makes an attack", not "a
        # melee attack", so it reaches this phase too - and like the hit side's
        # Whirling Onslaught it is a "reason" only when its whole-roll half is
        # live; the base clause is the automatic 1s.
        if implacable_eradication.offers_full_reroll(self.fighting_squad, target_squad, self.objectives):
            return implacable_eradication.IMPLACABLE_ERADICATION_LABEL
        return None

    def _wound_reroll_is_full(self, weapon, target_squad):
        """Whether the re-roll on offer covers the WHOLE roll or only its
        failures. Jain Zar's Storm of Silence reads "you can re-roll the Wound
        roll" with no "failed", the wording that settled every full source on
        the shooting side."""
        reason = self._wound_reroll_reason(weapon, target_squad)
        return reason in (storm_of_silence.STORM_OF_SILENCE_LABEL,
                          implacable_eradication.IMPLACABLE_ERADICATION_LABEL)

    def _twin_linked_choice_needed(self, weapon, no_effect, target_squad):
        """Pointless with zero failures, and once per weapon group - see
        shooting.py's identical method (including its own note that this
        no-failures gate also suppresses a whole-roll source, which is
        pre-existing behaviour shared by both sides)."""
        return (self._wound_reroll_reason(weapon, target_squad) is not None
                and no_effect > 0 and self.decision_manager is not None
                and not self._twin_linked_used)

    def _offer_twin_linked_choice(self, no_effect, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold, owner, rerollable=None, ones=0):
        """`no_effect` is the number of FAILED wound dice that may still be
        re-rolled - see shooting.py's identical method and the user correction
        that scoped [TWIN-LINKED] to failures only ("es sollten nur fails
        sein").

        A source that re-rolls the WHOLE roll (Storm of Silence) also gets that
        option, plus the failures-only subset of it: "you can re-roll the Wound
        roll" permits re-rolling fewer of its dice than all."""
        reason = self._wound_reroll_reason(weapon, target_squad)
        # A two-clause source grants the 1s OR the whole roll, never the
        # failures - see game/reroll_scope.py and shooting.py's twin.
        if reroll_scope.is_ones_or_whole(reason) and rerollable is not None:
            free_wounds, free_crits, free_no_effect = rerollable
            free_count = free_wounds + free_no_effect
            kept_wounds, kept_crits = wounds - free_wounds, crits - free_crits
            options = [(
                f"Re-roll the whole Wound roll ({free_count} dice)",
                lambda: self._reroll_wound(free_count, kept_wounds, kept_crits, weapon, target_squad, target_profile, weapon_label, wound_threshold),
            )]
            if ones > 0:
                options.append((
                    f"Re-roll the 1s only ({ones} dice)",
                    lambda: self._begin_ones_reroll(
                        "wound", ones, wound_threshold, weapon, target_squad, weapon_label,
                        wounds=wounds, crits=crits, target_profile=target_profile, reason=reason,
                    ),
                ))
            else:
                options.append(
                    ("Keep result", lambda: self._resolve_wounds(weapon, target_squad, target_profile, weapon_label, wounds, crits))
                )
            self._twin_linked_used = True
            self.decision_manager.request(
                owner, f"{weapon_label}: {reason} - re-roll the Wound roll?", options)
            return
        options = [(
            f"Re-roll failed wound rolls ({no_effect} dice)",
            lambda: self._reroll_wound(no_effect, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold),
        )]
        if self._wound_reroll_is_full(weapon, target_squad) and rerollable is not None:
            free_wounds, free_crits, free_no_effect = rerollable
            free_count = free_wounds + free_no_effect
            # A full re-roll DISCARDS what the free dice rolled; whatever a
            # previous re-roll already spent its one chance on is carried over.
            kept_wounds, kept_crits = wounds - free_wounds, crits - free_crits
            options.append((
                f"Re-roll the whole Wound roll ({free_count} dice)",
                lambda: self._reroll_wound(free_count, kept_wounds, kept_crits, weapon, target_squad, target_profile, weapon_label, wound_threshold),
            ))
        options.append(
            ("Keep result", lambda: self._resolve_wounds(weapon, target_squad, target_profile, weapon_label, wounds, crits))
        )
        self.decision_manager.request(
            owner, f"{weapon_label}: {reason} - re-roll the Wound roll?", options,
        )

    def _reroll_wound(self, no_effect, wounds, crits, weapon, target_squad, target_profile, weapon_label, wound_threshold):
        """Only the `no_effect` FAILED dice get rolled again - see
        shooting.py's identical method."""
        self._twin_linked_used = True
        self._pending_twin_linked_reroll = {
            "wounds": wounds, "crits": crits, "weapon": weapon, "target_squad": target_squad,
            "target_profile": target_profile, "weapon_label": weapon_label, "wound_threshold": wound_threshold,
        }
        self.dice_manager.roll(
            count=no_effect, sides=6,
            label=f"Wound Roll (re-rolling {no_effect} failed): {weapon_label} [TWIN-LINKED]",
            success_threshold=wound_threshold,
            target_name=target_squad.name, attacker_squad=self.fighting_squad, target_squad=target_squad, roll_kind=WOUND_ROLL,
            is_reroll=True,  # these dice have now used their one re-roll
            **self._crit_note("wound", weapon, target_squad),
        )
        self.pending_step = "wound_twin_linked_reroll"

    def _precision_choice_needed(self, weapon, target_squad):
        """Rule 24.28 ([PRECISION]): see shooting.py's identical-in-spirit
        method. Simplified here - fight.py has no line-of-sight/cover
        concept at all (melee is point-blank, rule 12.02's Engagement Range
        gates targeting instead), so every CHARACTER model in the target
        unit counts as "visible" rather than running a real LoS check."""
        if not weapon.precision or self.decision_manager is None:
            return False
        return any(c.profile.character for c in target_squad.models)

    def _offer_precision_choice(self, rolls, weapon, target_squad, weapon_label, owner):
        """See shooting.py's _offer_precision_choice - identical logic
        (including the "active player", not defending player, choosing
        this specific override), duplicated because each controller owns
        its own dice/decision state machine."""
        characters = [c for c in target_squad.models if c.profile.character]
        options = [
            (
                f"Prioritize {c.profile.name}",
                lambda c=c: self._begin_damage_allocation(rolls, weapon, target_squad, priority_group=[c]),
            )
            for c in characters
        ]
        options.append((
            "Resolve normally",
            lambda: self._begin_damage_allocation(rolls, weapon, target_squad, priority_group=None),
        ))
        self.decision_manager.request(
            owner, f"{weapon_label}: [PRECISION] - prioritize a visible CHARACTER for allocation?", options,
        )

    def _begin_damage_allocation(self, rolls, weapon, target_squad, priority_group):
        self.damage_session = DamageAllocationSession(
            rolls, weapon, target_squad, dice_manager=self.dice_manager, log=self._log, priority_group=priority_group,
            stealth_drones=self.stealth_drones, waaagh=self.waaagh,
        )
        # Same resume hook as game/shooting.py's - see
        # DamageAllocationSession.on_resumed. No damage_reroll is passed here
        # (Sunforge is ranged-only), but Stealth Drones is, and it opens the
        # very same kind of DecisionManager prompt, so a melee session can
        # be finished off by a callback just as a ranged one can.
        session = self.damage_session
        def _resume():
            if self.damage_session is session:
                self._check_allocation_done(rolls)
        session.on_resumed = _resume
        self.pending_step = "allocate"
        self._check_allocation_done(rolls)

    def _hit_modifiers(self, fighter_model, target_squad):
        """Strike Team's Suppression Volley ability (user-supplied, not a
        core rule - game/suppression.py): "each time a model in that
        [suppressed] unit makes an attack, subtract 1 from the Hit roll" -
        applies here exactly as in shooting.py's own _hit_modifiers(), since
        the ability isn't restricted to ranged attacks - depends only on
        which unit is attacking, not on the weapon or target, unlike
        Ghostkeel Battlesuit's own "Damaged" ability (also user-supplied),
        which needs the specific attacking MODEL (its own current wounds),
        hence the new `fighter_model` parameter this function didn't
        previously need.

        Tankbustas' own "Tank Hunters" (user-supplied, not a core rule)
        needs `target_squad` too, for the same reason it does in
        shooting.py's own _hit_modifiers() - a new parameter this function
        didn't previously need either."""
        modifiers = list(_damaged_modifier(fighter_model))
        # Wraithguard's Psychic Guidance: "each time a model in this unit
        # makes an attack, add 1 to the Hit roll" while near a friendly
        # AELDARI PSYKER. "Makes an attack", not "makes a ranged attack",
        # so it is in BOTH phases' hit modifiers - see
        # game/psychic_guidance.py.
        if psychic_guidance.applies(self.fighting_squad, self.all_tokens):
            modifiers.append(Modifier(-1, "Psychic Guidance"))
        # The Farseer's Guide: "each time a friendly AELDARI model makes an
        # attack that targets that enemy unit, add 1 to the Hit roll" - a
        # bonus, so a -1 on the threshold. Army-wide, not unit-wide, which
        # is why the mark is held per player. See game/guide.py.
        # The other half of Forewarned - see _wound_modifiers().
        if forewarned.applies(target_squad):
            modifiers.append(Modifier(forewarned.FOREWARNED_PENALTY, "Forewarned"))
        if self.guide is not None and self.guide.applies(fighter_model, target_squad):
            modifiers.append(Modifier(-1, "Guide"))
        if self.suppression is not None and self.fighting_squad is not None and self.suppression.is_suppressed(self.fighting_squad):
            modifiers.append(Modifier(1, "Suppressed"))
        modifiers.extend(tank_hunters_modifiers(fighter_model, target_squad))
        # Warboss's own "Might is Right" (user-supplied): "while this model is
        # leading a unit, each time a model in that unit makes a MELEE attack,
        # add 1 to the Hit roll". Melee-only, so it lives here and not in the
        # shared helper tank_hunters_modifiers() sits in. A bonus, so -1 under
        # this engine's Modifier sign convention (positive worsens).
        if self.fighting_squad is not None and squad_has_might_is_right(self.fighting_squad):
            modifiers.append(Modifier(-1, "Might is Right"))
        # Awakened Dynasty's Command Protocols - the same shape as Might is
        # Right above (a leader granting his whole unit +1 to hit), differing
        # only in reaching BOTH phases: its text says "an attack", not "a melee
        # attack", so game/shooting.py reads it too.
        modifiers.extend(awakened_dynasty.hit_modifiers(self.fighting_squad))
        return modifiers

    def _wound_modifiers(self, weapon, target_squad):
        """Rule 24.21 ([LANCE]): "add 1 to the wound roll" if the attacking
        model's unit made a charge move this turn - a bonus, so per the
        Modifier sign convention (positive worsens, negative improves) this
        is a -1. Only meaningful here in fight.py: Charge always resolves
        after Shooting in the same turn, so a unit can never have "made a
        charge move this turn" yet during its own Shooting phase.

        Tankbustas' own "Tank Hunters" (user-supplied, not a core rule) is
        checked against fighting_squad's representative model, same "read
        it off model 0" simplification as e.g. squad_waaagh_active()."""
        modifiers = []
        # War Horde's 'Ard as Nails (user-supplied): its WHEN names the Fight
        # phase as well as the opponent's Shooting phase, and its EFFECT says
        # "each time an ATTACK targets your unit" - not "ranged attack" - so
        # it applies here too. See game/ard_as_nails.py.
        if ard_as_nails_wound_modifier_applies(target_squad):
            modifiers.append(Modifier(ARD_AS_NAILS_WOUND_PENALTY, "'Ard as Nails"))
        # Warlock Conclave's Protect: "while a FARSEER model is leading this
        # unit, each time an attack targets this unit, subtract 1 from the
        # Wound roll" - the same defender-side malus, from a datasheet
        # ability. See game/protect.py.
        if protect.applies(target_squad):
            modifiers.append(Modifier(1, "Protect"))
        # Seer Council's Forewarned: "subtract 1 from the Hit roll and subtract
        # 1 from the Wound roll" for attacks targeting the unit - so it appears
        # in BOTH hooks. Fight phase only, which is its WHEN, not a shortcut.
        if forewarned.applies(target_squad):
            modifiers.append(Modifier(forewarned.FOREWARNED_PENALTY, "Forewarned"))
        # Eldrad Ulthran's Doom: Guide's twin one word apart - a mark set at the
        # end of his Movement phase that lasts until the start of his next
        # Command phase, so it is live through the opponent's whole turn. The
        # bonus is army-wide ("each time a friendly AELDARI model makes an
        # attack"), which is why the mark is held per player, and it is a bonus
        # rather than a malus, so a NEGATIVE amount. See game/doom.py.
        if self.doom is not None and self.doom.applies_to_squad(self.fighting_squad, target_squad):
            modifiers.append(Modifier(DOOM_WOUND_BONUS, "Doom"))
        if weapon.lance and self.charge_controller is not None and self.fighting_squad is not None and self.fighting_squad in self.charge_controller.charged_squad_ids:
            modifiers.append(Modifier(-1, "[LANCE] (charged)"))
        if self.fighting_squad is not None and self.fighting_squad.models:
            modifiers.extend(tank_hunters_modifiers(self.fighting_squad.models[0], target_squad))
        # Commander Farsight's Way of the Short Blade: "+1 to the Wound
        # roll" for a unit he is LEADING, against a target within 9".
        # Hooked into both phases because its text says "makes an
        # attack", not "makes a ranged attack" - see
        # game/way_of_the_short_blade.py.
        modifiers.extend(way_of_the_short_blade.wound_modifiers(self.fighting_squad, target_squad))
        # Lychguard's Guardian Protocols. Wired HERE as well as in shooting.py
        # because its printed text says "each time an attack targets this
        # unit", not "a ranged attack" - the Wave Serpent Shield, which is
        # otherwise the same rule, does say ranged and is shooting-only.
        # `weapon` is already the adjusted profile at this point, so a melee
        # Strength raised by something else is compared at its real value.
        if guardian_protocols.applies(target_squad, weapon.strength):
            modifiers.append(Modifier(
                guardian_protocols.GUARDIAN_PROTOCOLS_PENALTY,
                guardian_protocols.GUARDIAN_PROTOCOLS_LABEL))
        return modifiers

    def _finish_group(self):
        self.pending_step = None
        # Safety net for the paths that reach here WITHOUT going through
        # _finish_group_after_wounds() - notably the "target was destroyed
        # before this group finished resolving" abandon branch. Mortal wounds
        # owed to a unit that no longer exists are wasted either way; what
        # must not happen is them leaking into the next weapon group.
        self._hold_still_crits = 0
        weapon_key = self.current_group["weapon_key"] if self.current_group else None
        pairs = self.current_group["pairs"] if self.current_group else None
        # Rule 24.15 ([HAZARDOUS]): count this as one of the "[HAZARDOUS]
        # weapons you selected in the Select Weapons step" - once per group
        # actually fought with (i.e. with eligible pairs), not per model.
        if pairs and pairs[0][1].hazardous:
            self._hazardous_count += 1
        # Rule 24.26 ([ONE SHOT]): mark every model+weapon pair that just
        # fought so _melee_attack_groups() never offers them again, for the
        # rest of the game (never reset, unlike _used_other_melee_weapon).
        if pairs:
            for model, weapon in pairs:
                if weapon.one_shot:
                    self.one_shot_used.add((model.id, id(weapon)))
        self.current_group = None

        # Back to the fighting player's decisions (pick the next weapon, or stop fighting).
        if self.turn_tracker is not None and self.fighting_squad is not None:
            self.turn_tracker.set_active(self.fighting_squad.owner)

        if self.split_fire:
            self._begin_next_split_group()
        else:
            if weapon_key in self.remaining_weapon_types:
                self.remaining_weapon_types.remove(weapon_key)
            if self.remaining_weapon_types:
                self.state = CHOOSING_WEAPON
            else:
                self._finish_current_fight()

    def _finish_current_fight(self):
        """Rule 24.15 ([HAZARDOUS]): "after that unit has resolved all of
        its attacks" - the unit's whole fight activation genuinely ends
        here, whichever of the several call sites reached it - so this is
        exactly the point to make any owed hazard rolls first."""
        if self._hazardous_count > 0:
            self._begin_hazard_rolls()
        else:
            self._actually_finish_current_fight()

    def _begin_hazard_rolls(self):
        count = self._hazardous_count
        self._hazardous_count = 0
        self.dice_manager.roll(
            count=count, sides=6,
            label=f"Hazard Rolls: {self.fighting_squad.name} ({count} [HAZARDOUS] weapon(s))",
        )
        self.pending_step = "hazard"

    def _check_hazard_wounds_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None
        self._actually_finish_current_fight()

    def _actually_finish_current_fight(self):
        squad = self.fighting_squad
        if squad is not None:
            self.fought_squad_ids.add(squad)
        # Rule 19.04: the attacking unit has now resolved all of its
        # attacks, so a wiped-out component stops conferring its abilities.
        for attacked in self._attacked_squads_this_activation:
            attached_units.end_attack_sequence(attacked)
        self._attacked_squads_this_activation = set()
        self.fighting_squad = None
        self.target_squad = None
        self.remaining_weapon_types = []
        self._used_other_melee_weapon = set()
        self._hazardous_count = 0
        self._lethal_hits_auto_wounds = 0
        self.mortal_wound_session = None
        self.hold_still_session = None
        self._hold_still_crits = 0
        self.pending_step = None
        self.assignment_queue = []
        self.assignments = {}
        self.resolved_groups = []
        self.state = SELECTING
        if self.whose_turn is not None:
            self.whose_turn = self._other_player(self.whose_turn)
        self.sub_step = FIGHTS_FIRST
        self._settle_turn_state()
        # Rule 15.12 (Counteroffensive): "just after an enemy unit has
        # resolved its attacks" - exactly here, the one place every fight
        # activation (however it started) funnels through when it ends.
        if squad is not None and self.on_unit_finished_fighting is not None:
            self.on_unit_finished_fighting(squad)

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
