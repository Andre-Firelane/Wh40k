"""Green Tide Stratagem: Mob Mentality (1CP, Mecha Orks stage G3).

RULE (verbatim, rules/orks/detachments/Green Tide.md):
  WHEN:   Start of the Battle-shock step of your Command phase.
  TARGET: One friendly ORKS INFANTRY unit of 13+ models.
  EFFECT: Select one visible friendly ORKS unit within 12" of your unit. That
          unit's battle-shock rolls are automatically successful.

THE TARGET AND THE BENEFICIARY ARE DIFFERENT UNITS. The Stratagem targets the
big mob (rule 15.01's one-target-per-phase lands on it, and a battle-shocked mob
cannot be targeted - 01.07); the auto-success goes to the unit SELECTED in the
effect, which may be the mob itself ("a friendly ORKS unit within 12" of your
unit" - a unit is at distance 0 of itself, the reading Ghazghkull's Prophet aura
and game/grand_warlords_ladz.py take). So the button stands on the 13+ mob, and
pressing it opens the pick; the CP is paid when a unit is picked, and
cancelling costs nothing.

"START OF THE BATTLE-SHOCK STEP". This engine runs the Command phase without
sub-steps: the Command step's CP arrives automatically as the phase opens, and
the Battle-shock step IS the rolls. So the window is "before any Battle-shock
roll of yours has been made (or is being made) this Command phase" - read off
BattleShockController.rolled_squad_ids / rolling_squad, the same ledgers rule
08.03 is enforced with.

"THAT UNIT'S BATTLE-SHOCK ROLLS ARE AUTOMATICALLY SUCCESSFUL" names no end, so
it lasts the phase it is bought in (this engine's reading of an effect without a
printed duration) - which covers the 08.03 test and any forced test that
lands later in the same phase. game/battle_shock.py asks auto_passes() at each
of its three roll entries. Insane Bravery is refused for such a unit: it would
buy nothing (error class 5).

NAMED LIMITATION: the Psychomancer's Nightmare Shroud throws its tests while
main() opens the Command phase, before any button can be pressed - and its
first roll closes this window ("step has begun"). As printed, Mob Mentality
("START of the Battle-shock step") would come first; this engine's Command
phase has no sub-steps both sides could queue into.

ONLY A UNIT THAT OWES A ROLL IS OFFERED - a unit that is neither battle-shocked
nor below half strength would gain nothing from the pick (error class 5), and
the whole Stratagem is refused when no unit in reach owes one.

"VISIBLE" is a real line-of-sight test, injected as `visible(observer_squad,
other_squad)` like Guiding Presence's; no callable means "every candidate counts
as visible", which is what a headless harness gets. "WITHIN 12"" is edge to edge
(Squad.min_distance_to()).

THE AI (ai/agent_driver.py's _handle_mob_mentality(), 0 API calls) picks
through use_on() without a prompt.
"""

from game import green_tide
from game.stratagems import Stratagem
from game.turn import PHASE_COMMAND

MOB_MENTALITY_NAME = "Mob Mentality"
MOB_MENTALITY_CP = 1
#: "One friendly ORKS INFANTRY unit of 13+ models".
MOB_MENTALITY_MIN_MODELS = 13
#: "within 12" of your unit".
MOB_MENTALITY_RANGE_IN = 12.0
CANCEL_LABEL = "Cancel"


def auto_passes(squad):
    """Whether this unit's Battle-shock rolls are automatically successful -
    game/battle_shock.py's question."""
    return bool(getattr(squad, "mob_mentality_active", False))


def reset_phase(squads=()):
    for squad in squads or ():
        if getattr(squad, "mob_mentality_active", False):
            squad.mob_mentality_active = False


def is_eligible_target(squad):
    """TARGET: a friendly ORKS INFANTRY unit of 13+ (living) models, of a player
    fielding Green Tide."""
    return (squad is not None and green_tide.fields_green_tide(getattr(squad, "owner", None))
            and green_tide.is_orks_infantry_unit(squad)
            and green_tide.living_model_count(squad) >= MOB_MENTALITY_MIN_MODELS)


class MobMentalityController:
    """A panel button (game/proactive_stratagems.py) that opens a unit pick."""

    def __init__(self, stratagem_controller, battle_shock_controller=None, turn_tracker=None,
                 decision_manager=None, all_tokens=None, game_log=None, visible=None):
        self.stratagem_controller = stratagem_controller
        self.battle_shock_controller = battle_shock_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        # The board - a live list (main.py passes state.tokens), so "visible
        # ... within 12"" only ever sees units that are on it.
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        #: visible(observer_squad, other_squad) -> bool, or None for "all".
        self.visible = visible
        self._picking = None   # the targeted 13+ mob while a human is choosing
        self._chosen = None    # the unit the effect goes to, while the CP is paid
        self._stratagem = Stratagem(MOB_MENTALITY_NAME, MOB_MENTALITY_CP, self._grant)

    # ------------------------------------------------------------ questions

    def panel_label(self, squad):
        return f"{MOB_MENTALITY_NAME} ({MOB_MENTALITY_CP} CP) - a unit in 12\" auto-passes Battle-shock"

    def reset_phase(self, squads=()):
        reset_phase(squads)

    def _board_squads(self):
        out = []
        for token in self.all_tokens:
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in out:
                out.append(squad)
        return out

    def step_has_begun(self, player):
        """Whether the Battle-shock step is under way for `player` - a roll of
        theirs made or open this Command phase."""
        bsc = self.battle_shock_controller
        if bsc is None:
            return False
        if bsc.rolling_squad is not None and getattr(bsc.rolling_squad, "owner", None) == player:
            return True
        return any(getattr(s, "owner", None) == player for s in bsc.rolled_squad_ids)

    def owes_roll(self, squad):
        bsc = self.battle_shock_controller
        return bsc is not None and bsc.can_roll(squad)

    def candidates(self, mob):
        """"one visible friendly ORKS unit within 12" of your unit" that owes a
        Battle-shock roll and is not already covered - the mob itself included."""
        out = []
        for other in self._board_squads():
            if other.owner != mob.owner or not green_tide.is_orks_unit(other):
                continue
            if not any(not m.is_dead() for m in other.models):
                continue
            if auto_passes(other) or not self.owes_roll(other):
                continue
            if other is not mob:
                if mob.min_distance_to(other) > MOB_MENTALITY_RANGE_IN:
                    continue
                if self.visible is not None and not self.visible(mob, other):
                    continue
            out.append(other)
        return sorted(out, key=lambda s: s.name)

    def can_use(self, squad):
        tt = self.turn_tracker
        if squad is None or tt is None or self.battle_shock_controller is None:
            return False
        if tt.phase != PHASE_COMMAND or squad.owner != tt.turn_owner:
            return False
        if self._picking is not None or not is_eligible_target(squad):
            return False
        if self.step_has_begun(squad.owner):
            return False
        if not self.candidates(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    # ------------------------------------------------------------ the human

    def use(self, squad):
        """The panel button: pick the unit. A sole candidate is taken without a
        prompt (the shortcut every "select one unit" ability here takes).
        Returns True if the Stratagem was bought or the pick opened."""
        if not self.can_use(squad):
            return False
        options = self.candidates(squad)
        if len(options) == 1 or self.decision_manager is None:
            return self.use_on(squad, options[0])
        self._picking = squad
        choices = [("%s: %s" % (MOB_MENTALITY_NAME, other.name), (lambda o=other: self.pick(o)), other)
                   for other in options]
        choices.append((CANCEL_LABEL, self._cancel))
        self.decision_manager.request(
            squad.owner,
            "%s: select a visible friendly ORKS unit within 12\" of %s - its Battle-shock "
            "rolls are automatically successful this phase." % (MOB_MENTALITY_NAME, squad.name),
            choices,
        )
        return True

    def pick(self, other):
        mob, self._picking = self._picking, None
        if mob is None:
            return False
        return self.use_on(mob, other)

    def _cancel(self):
        self._picking = None

    # ----------------------------------------------------------- both sides

    def use_on(self, mob, other):
        """Buy it for `mob` and give the effect to `other` - the AI's path, and
        where the human's pick lands. Returns whether it was bought."""
        if not self.can_use(mob) or other not in self.candidates(mob):
            return False
        self._chosen = other
        try:
            return bool(self.stratagem_controller.use(mob.owner, self._stratagem, [mob]))
        finally:
            self._chosen = None

    def _grant(self, controller, player, targets):
        other = self._chosen
        if other is None:
            return False
        other.mob_mentality_active = True
        if self.game_log is not None:
            mob = targets[0].name if targets else "?"
            self.game_log.add(f"{MOB_MENTALITY_NAME}: {other.name}'s Battle-shock rolls are "
                              f"automatically successful this phase (from {mob}).")
        return True
