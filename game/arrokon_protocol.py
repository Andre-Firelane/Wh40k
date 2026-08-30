"""T'au Empire detachment stratagem: Retaliation Cadre's The Arro'kon
Protocol, as supplied by the user (not a rule from the generic 40k core
rulebook, so it lives in its own module - same reasoning as
game/retaliation_cadre.py for that detachment's Bonded Heroes rule and
game/stim_injectors.py for its other stratagem).

RULE (The Arro'kon Protocol, 1CP, Retaliation Cadre Battle Tactic Stratagem):
  WHEN:   Your Shooting phase.
  TARGET: One T'AU EMPIRE BATTLESUIT unit from your army that has not been
          selected to shoot this phase.
  EFFECT: Until the end of the phase, each time a model in your unit makes
          an attack that targets an enemy unit that contains 6 or more
          models, that attack has the [SUSTAINED HITS 1] ability. If that
          attack targets an enemy unit that contains 11 or more models, it
          has the [SUSTAINED HITS 2] ability instead.

WHY THIS IS SHOOTING-ONLY
------------------------
The EFFECT says "makes an attack", not "makes a ranged attack" - but the
WHEN is your own Shooting phase and the duration is "until the end of the
phase", and no melee attack can happen inside your own Shooting phase. So
wiring the adjuster into game/shooting.py alone is complete, not a
simplification: the grant is cleared on every phase change (see
ArrokonProtocolController.reset_phase(), called from main.py's
advance_turn_phase() alongside StratagemController.reset_phase()), so
game/fight.py can never see an active one. A reactive Snap Shot (Fire
Overwatch, 15.08/15.09) is likewise out of reach - it happens at the end of
the OPPONENT's Movement phase, by which time this has expired.

WHEN THE MODEL COUNT IS READ
----------------------------
Per attack, at the moment the attack is made - i.e. live, not snapshotted at
target selection. Deliberately NOT folded into ShootingController's rule
10.02 snapshot (_snapshot_target_state()): that snapshot exists because
range, line of sight and Benefit of Cover are TARGET-SELECTION criteria, and
10.02 freezes those for the whole activation. Model count is not one of
them - this stratagem's EFFECT clause is evaluated "each time a model...
makes an attack", so a target unit that drops from 11 models to 10 partway
through an activation gives [SUSTAINED HITS 1] to the weapon groups fired
after that point, not 2. Attacks within one weapon group are resolved
together (one hit roll, rule 04.03's fast dice rolling), so the count is
read once per group, which is as fine-grained as this engine's resolution
gets.

Rule 19.01: an attached unit is a single unit, so its model count is the
merged total - a 10-model Boyz mob with a Warboss joined is an 11-model
unit and hits the second tier.

DETACHMENT GATE
---------------
The T'AU EMPIRE half of the TARGET clause, and "from your army", are checked
through game/retaliation_cadre.py's stratagem_target_ok() - the shared
predicate all six of this detachment's Stratagems use, in the same shape as
game/awakened_dynasty.py's and game/death_lords_chosen.py's.

This module used to say the opposite: that the check was skipped because
"Retaliation Cadre is currently the only detachment that exists". That
assumption expired the moment a T'au army could be a Kauyon or Mont'ka one
instead, and in a T'au mirror match it was wrong for both players at once.

The BATTLESUIT half
IS checked, via is_battlesuit_unit()'s rule 19.03 keyword pooling.
"""

import copy

from game.retaliation_cadre import is_battlesuit_unit, stratagem_target_ok
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

ARROKON_CP_COST = 1

# The two tiers, straight from the rule text: "6 or more models" -> 1,
# "11 or more models" -> 2 instead.
ARROKON_TIERS = ((11, 2), (6, 1))


def alive_model_count(squad):
    """How many models the unit "contains" right now.

    Dead models are only stripped from Squad.models once per frame (see
    GameState.remove_dead_models()), so within the very activation that
    kills them they are still in the list - counting them would keep a unit
    on the higher tier for the rest of an activation that has already wiped
    most of it out. Same `[m for m in squad.models if not m.is_dead()]`
    idiom every other live-count site in this codebase uses."""
    return len([m for m in squad.models if not m.is_dead()])


def sustained_hits_for_target(target_squad):
    """The [SUSTAINED HITS X] value this stratagem grants against this
    target, or 0 if the target is too small to trigger either tier."""
    if target_squad is None:
        return 0
    count = alive_model_count(target_squad)
    for minimum, value in ARROKON_TIERS:
        if count >= minimum:
            return value
    return 0


def arrokon_adjusted_weapon(weapon, pairs, target_squad):
    """"That attack has the [SUSTAINED HITS X] ability" modeled as an actual
    characteristic change (shallow copy, same reasoning as
    get_stuck_in_adjusted_weapon()/bonded_heroes_adjusted_weapon() - the
    shared WeaponProfile instance is never mutated).

    Whether the group counts as an attack by a unit under this stratagem is
    decided from its representative shooter (pairs[0][0]) and that model's
    own unit, the same simplification every other adjuster in this codebase
    uses - and an exact one here, since the flag is unit-level and a group's
    models all belong to one unit.

    GRANTS the ability rather than overwriting it: a weapon that already has
    a higher [SUSTAINED HITS] from some other source keeps its better value,
    and the two never add up (two sources of the same ability don't stack -
    same reading, and same code shape, as game/war_horde.py's Get Stuck In)."""
    shooter_model = pairs[0][0] if pairs else None
    if shooter_model is None:
        return weapon
    squad = getattr(shooter_model, "squad", None)
    if squad is None or not getattr(squad, "arrokon_protocol_active", False):
        return weapon
    granted = sustained_hits_for_target(target_squad)
    if granted <= weapon.sustained_hits:
        return weapon
    boosted = copy.copy(weapon)
    boosted.sustained_hits = granted
    return boosted


class ArrokonProtocolController:
    """WHEN/TARGET bookkeeping plus the "until the end of the phase" grant.
    The EFFECT itself is arrokon_adjusted_weapon() above, chained into
    game/shooting.py's resolution the same way Bonded Heroes/Starscythe/
    Drive-by Dakka already are.

    Proactive, unlike its detachment sibling: Stim Injectors reacts to the
    opponent selecting targets and therefore needs a relevance gate to keep
    from interrupting the game (see that module's docstring). This one is
    used by the active player at a moment of their own choosing, so there is
    no interruption to gate - what can_use() adds beyond the printed clauses
    is a CERTAINTY check, not an estimate: if nothing this unit could
    legally shoot at right now has 6+ models, the stratagem grants literally
    nothing, and offering it would be offering to burn 1 CP for no effect.
    Same kind of honest eligibility as ExplosivesController's own
    _has_reachable_target() and game/overwatch.py's _eligible_squads()."""

    def __init__(
        self, stratagem_controller, shooting_controller=None, movement_controller=None,
        all_tokens=None, turn_tracker=None, game_log=None,
    ):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.movement_controller = movement_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(name="The Arro'kon Protocol", cp_cost=ARROKON_CP_COST, effect=self._grant)

    def reset_phase(self, squads=()):
        """End of phase: the grant expires ("until the end of the phase").

        Lives here rather than in main.py's phase loop so "when does this
        stratagem stop applying" has exactly one answer, and so it is
        testable without standing up the whole game loop - same shape as
        StimInjectorsController.reset_phase(). Callers pass every squad on
        the board; only the active player can ever hold this grant, but
        clearing both armies costs nothing and cannot leave one stranded."""
        for squad in squads:
            squad.arrokon_protocol_active = False

    def qualifying_target_squads(self, squad):
        """The enemy units this squad could legally shoot right now that are
        big enough to trigger a tier - i.e. exactly what the stratagem would
        buy if used on this unit this instant.

        Reuses ShootingController.has_valid_target()'s eligibility probe
        (_is_valid_target_squad + _model_can_reach, the same logic real
        targeting enforces) rather than re-deriving range/line of sight/
        Hidden/LONE OPERATIVE here - see that method's own docstring for the
        user-reported bug that came from a hand-rolled second opinion."""
        if self.shooting_controller is None or squad is None:
            return []
        # Local import: game/shooting.py imports arrokon_adjusted_weapon()
        # from this module at module level, so a module-level import back the
        # other way would be a cycle. Only this method (never the adjuster
        # itself, which is on the hot resolution path) needs it.
        from game.shooting import available_shooting_types

        types = available_shooting_types(squad, self.all_tokens, self.movement_controller)
        if not types:
            return []
        candidates = sorted(
            {
                t.squad for t in self.all_tokens
                if t.squad is not None and t.squad.owner != squad.owner and sustained_hits_for_target(t.squad) > 0
            },
            key=lambda s: s.name,
        )
        return [
            target for target in candidates
            if any(
                self.shooting_controller.has_valid_target(
                    squad, shooting_type, self.all_tokens, target_filter=lambda s, t=target: s is t,
                )
                for shooting_type in types
            )
        ]

    def best_available_tier(self, squad):
        """The highest [SUSTAINED HITS X] this unit could currently get, or 0
        if none - the number the button/prompt quotes, so the choice is made
        against a value rather than a bare yes/no (same reasoning as
        _matchup_hint() and the charge odds elsewhere in this project)."""
        targets = self.qualifying_target_squads(squad)
        return max((sustained_hits_for_target(t) for t in targets), default=0)

    def can_use(self, squad):
        if squad is None or self.shooting_controller is None:
            return False
        if self.turn_tracker is not None:
            # WHEN: "Your Shooting phase" - the user's own, not the opponent's.
            if self.turn_tracker.phase != PHASE_SHOOTING:
                return False
            if squad.owner != self.turn_tracker.active_player:
                return False
        if getattr(squad, "arrokon_protocol_active", False):
            return False  # already up on this unit - nothing left to buy
        if not stratagem_target_ok(squad):
            return False
        if not is_battlesuit_unit(squad):
            return False
        # TARGET: "has not been selected to shoot this phase". can_shoot()
        # carries that (shot_squad_ids) plus the phase check and "has some
        # weapon group left to fire"; active_squad is the one case it can't
        # see - a unit mid-activation HAS been selected to shoot, but only
        # lands in shot_squad_ids once that activation finishes.
        if self.shooting_controller.active_squad is squad:
            return False
        if not self.shooting_controller.can_shoot(squad):
            return False
        if not self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad]):
            return False  # rule 15.01's once-per-phase/one-target-per-phase, CP, and 01.07's battle-shock block
        return self.best_available_tier(squad) > 0

    def use(self, squad):
        """Spends the CP and puts the grant up. TARGET is trivial (always
        this one unit), so there is no separate selection step to cancel out
        of - the CP is committed right here, exactly like
        CrushingImpactController's own start()."""
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        squad = targets[0]
        squad.arrokon_protocol_active = True
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: The Arro'kon Protocol - {squad.name}'s attacks have [SUSTAINED HITS 1] against "
                "enemy units of 6+ models ([SUSTAINED HITS 2] against 11+) until the end of the phase."
            )
