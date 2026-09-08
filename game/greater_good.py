"""T'au Empire army rule: For The Greater Good, as supplied by the user (not
a rule from the generic 40k core rulebook this engine otherwise implements,
so it lives in its own module rather than alongside e.g. game/stratagems.py's
Core Stratagems).

RULE: at the start of your Shooting phase you can select units with this
ability to become Observer units. During your Shooting phase, each Observer
unit that hasn't been selected to shoot yet and is eligible to shoot
(excluding battle-shocked units - we have no Fortification keyword to
exclude, since nothing in this engine has ever needed one) can mark one
visible enemy unit as Spotted, until the end of the phase; each enemy unit
can only be marked once per phase, by any Observer. Units with this ability
(excluding Observer units themselves) are Guided while targeting one or
more Spotted units: their attacks against a Spotted unit get +1 BS (a -1
hit-threshold Modifier, see game/modifiers.py's "negative = improvement"
convention - wired into ShootingController._hit_modifiers()), and, if the
Spotted unit was marked by an Observer with the MARKERLIGHT keyword, also
[IGNORES COVER] for that attack.

Simplification: the rule text separates "become an Observer" (declared
once per unit, a standing status for the rest of the phase) from "mark a
Spotted unit" (something only an Observer with an eligible target can then
do). Observer status has no other effect in this engine besides unlocking
marking and excluding the unit from Guided - so there's nothing to gain
from declaring it without an eligible target in hand, and this collapses
both into one action (can_use() only offers it when eligible_targets() is
non-empty), mirroring how e.g. ExplosivesController offers its whole
target-selection flow as a single button rather than a separate "opt in"
step first. Marking doesn't consume the unit's own shooting activation -
it can (and normally will) still shoot normally afterward, same as
Explosives."""

from game import board_epoch, line_of_sight, status_effects
from game.shooting import available_shooting_types
from game.squad import squad_has_forward_observers, squad_has_greater_good, squad_has_markerlight
from game.turn import PHASE_SHOOTING

IDLE = "idle"
CHOOSING_TARGET = "choosing_target"  # pick a visible, not-yet-Spotted enemy unit for this Observer to mark


class GreaterGoodController:
    def __init__(
        self, all_tokens=None, obstacles=None, terrain_areas=None,
        movement_controller=None, turn_tracker=None, game_log=None, shooting_controller=None,
    ):
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.obstacles = obstacles if obstacles is not None else []
        self.terrain_areas = terrain_areas if terrain_areas is not None else []
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        # Rule 13.09 (Hidden): eligible_targets() needs each candidate's
        # detectability, which needs to know when its unit last made a
        # ranged attack - that bookkeeping only exists on ShootingController
        # (last_ranged_attack_turn), constructed AFTER this controller
        # (ShootingController takes THIS controller as its own `greater_good`
        # dependency) - so main.py wires it in with a plain attribute
        # assignment after both exist, same pattern as e.g.
        # movement_controller.on_remain_stationary. Optional/None-safe: see
        # eligible_targets()'s own fallback.
        self.shooting_controller = shooting_controller

        self.spotted_by = {}             # enemy Squad -> the Observer Squad that marked it, this phase
        self.observer_squad_ids = set()  # friendly Squads that have used their Observer action this phase

        self.state = IDLE
        self.acting_squad = None

        # Perf, not rules: can_use()'s last clause is a full line-of-sight
        # sweep, and the left panel asks it EVERY FRAME while a T'au unit is
        # selected in its own Shooting phase (game/ui/action_panel.py's
        # _draw_movement_ui). Measured at 4732 ms per call on a 179-model
        # map2 board - the game is all but frozen for as long as the unit
        # stays selected. Same shape and the same reason as
        # ShootingController.weapon_eligibility()'s cache ("called every frame
        # to render"); see any_eligible_target() for what the key has to cover.
        self._any_target_cache_key = None
        self._any_target_cache_result = False

    def reset_shooting_phase(self):
        """A new Shooting phase means a fresh set of Spotted/Observer units -
        "until the end of the phase" (Spotted) and the once-per-phase
        Observer action both start over."""
        self.spotted_by = {}
        self.observer_squad_ids = set()
        self.state = IDLE
        self.acting_squad = None

    def is_spotted(self, squad):
        return squad in self.spotted_by

    def is_observer(self, squad):
        return squad in self.observer_squad_ids

    def marked_by_markerlight(self, target_squad):
        observer = self.spotted_by.get(target_squad)
        return observer is not None and squad_has_markerlight(observer)

    def has_forward_observers(self, attacking_squad, target_squad):
        """Stealth Battlesuits' "Forward Observers" ability (user-supplied,
        not a core rule): "each time this unit is an Observer unit...
        each time a ranged attack is made by a model in a Guided unit that
        targets their Spotted unit, re-roll a Hit roll of 1 and re-roll a
        Wound roll of 1" - true only while the Guided-attack condition
        already holds (is_guided_attack) AND the SPECIFIC Observer that
        marked target_squad ("their Spotted unit") is the one with this
        ability, not just any Observer that happens to have it."""
        if not self.is_guided_attack(attacking_squad, target_squad):
            return False
        observer = self.spotted_by.get(target_squad)
        return observer is not None and squad_has_forward_observers(observer)

    def is_guided_attack(self, attacking_squad, target_squad):
        """"Units from your army with the For the Greater Good ability
        (excluding Observer units) are Guided units while targeting one or
        more Spotted units" - a STANDING exclusion for the phase: a unit
        that became an Observer is not Guided at all, not even against a
        target some OTHER Observer marked.

        Briefly changed to a per-target exclusion after a game report (a
        Crisis Sunforge unit had marked a Deff Dread, then shot a Battlewagon
        that a MARKERLIGHT Strike Team had marked, and the Battlewagon kept
        its Benefit of Cover) and reverted the moment the user supplied the
        printed army-rule text quoted above: "du hattest recht. observer
        units profitieren nicht. da habe ich quatsch erzählt." Recorded
        because the reported behaviour was CORRECT - anyone re-reading that
        report should not re-fix it.

        That standing exclusion is exactly what Pathfinder Team's Target
        Uploaded exists to buy back (see game/target_uploaded.py), and the
        two are mutually exclusive by construction."""
        if attacking_squad is None or target_squad is None:
            return False
        if self.is_observer(attacking_squad):
            return False
        if not squad_has_greater_good(attacking_squad):
            return False
        return self.is_spotted(target_squad)

    def eligible_targets(self, squad):
        """TARGET: "an enemy unit that is visible" to the Observer unit (any
        one of its models seeing any one enemy model), not already Spotted
        this phase by anyone.

        Real bug, found via user report ("marker + hidden intagiert nicht
        richtig. um etwas zu markieren muss man das ziel auch sehen
        können"): raw line-of-sight alone isn't the whole "visible" story -
        rule 13.09 (Hidden) makes an INFANTRY/BEASTS/SWARM unit in Dense
        terrain undetectable beyond its detection range even when a clear
        LoS exists between individual models (that's exactly what
        ShootingController._is_valid_target_squad() already checks for
        normal targeting via status_effects.is_detectable() - this used to
        skip that check entirely, so a Hidden unit far outside its
        detection range could still be marked as Spotted just because some
        model somewhere had technical LoS to it)."""
        return list(self._eligible_targets(squad))

    def any_eligible_target(self, squad):
        """Whether _eligible_targets() would yield ANYTHING - the same question
        can_use() used to answer by building the whole list.

        A second VIEW on one definition, not a second copy of the rule (same
        shape as rules_text.army_rule_text()/army_rule_blocks()): both go
        through the generator, so there is no version that could drift.

        CACHED, because this is the per-frame path. The key has to cover
        everything _eligible_targets() reads:
          * the squad asking (a one-slot cache; the panel asks about exactly
            one unit per frame);
          * board_epoch.fingerprint(), i.e. every position and every wound
            total - see that module for why len(all_tokens) is not enough here;
          * len(spotted_by), since a marked unit is skipped. Within a phase
            entries are only ever ADDED; reset_shooting_phase() empties it, and
            that is covered by the round/turn term below;
          * battle_round and turn_owner, which also carry is_hidden()'s own
            turn-number term;
          * len(last_ranged_attack_turn), because shooting ends Hidden (13.09).
            NAMED BLIND SPOT: updating the VALUE for a squad already in that
            dict does not move len(). Harmless here - is_hidden() is asked
            about DEFENDER models, and during your own Shooting phase the only
            entries being written are the active player's own.

        Deliberately NOT keyed on: shot_squad_ids, observer_squad_ids or
        self.state. All three are read by can_use()'s cheap gates, which stay
        live OUTSIDE this memo - so the button still disappears the instant the
        unit marks or shoots."""
        if squad is None:
            return False
        key = (
            squad,
            board_epoch.fingerprint(self.all_tokens),
            len(self.spotted_by),
            getattr(self.turn_tracker, "battle_round", None),
            getattr(self.turn_tracker, "turn_owner", None),
            len(self.shooting_controller.last_ranged_attack_turn) if self.shooting_controller is not None else 0,
        )
        if key != self._any_target_cache_key:
            self._any_target_cache_key = key
            self._any_target_cache_result = next(self._eligible_targets(squad), None) is not None
        return self._any_target_cache_result

    def _eligible_targets(self, squad):
        """The ONE definition, as a generator so can_use() can stop at the
        first hit. Two orderings changed here, both lossless:

        DETECTABILITY FIRST, AND ONCE PER DEFENDER. is_detectable() depends on
        the defender and the OBSERVING SQUAD, never on which friendly model is
        looking - so it used to be recomputed for every (friendly, defender)
        pair, and only when line of sight had already been paid for. Both are
        side-effect-free, so `A and B` may be reordered freely. Measured:
        0.0023 ms per model against 4.52 ms for a sight check, i.e. 2000x
        cheaper, and a unit that is Hidden beyond its detection range now costs
        its model count instead of models x observers sight checks.

        NEAREST ENEMY UNITS FIRST. For a generator whose first consumer stops
        at the first hit, order is free to choose, and the nearest units are
        the ones most likely to be visible. It also makes the order TOTAL: this
        used to iterate a set, so eligible_targets() returned its list in an
        order that varied between runs. Nothing depended on it (main.py makes a
        set of it, ai/agent_driver.py sorts by name, choose_target() only tests
        membership), which is exactly why it could sit there unnoticed."""
        if squad is None:
            return
        enemy_squads = {
            token.squad for token in self.all_tokens
            if token.squad is not None and token.squad.owner != squad.owner
        }
        last_ranged_attack_turn = (
            self.shooting_controller.last_ranged_attack_turn if self.shooting_controller is not None else {}
        )
        for enemy in sorted(enemy_squads, key=lambda e: self._closeness(squad, e)):
            if self.is_spotted(enemy):
                continue
            # NOTE: called WITHOUT prey_marks/unmasking, and that stays that
            # way - game/detection_range.py's own docstring records this as a
            # known, deliberately open divergence from shooting.py's
            # _detectable_models(), which the line below now otherwise
            # resembles closely enough to invite a "fix". Closing it is a rules
            # decision, not something to do while making this faster.
            detectable = [
                defender for defender in enemy.models
                if status_effects.is_detectable(
                    defender, squad, self.terrain_areas, self.turn_tracker, last_ranged_attack_turn)
            ]
            if not detectable:
                continue
            if any(
                line_of_sight.has_line_of_sight(friendly, defender, self.obstacles, self.all_tokens, self.terrain_areas)
                for friendly in squad.models
                for defender in detectable
            ):
                yield enemy

    def _closeness(self, squad, enemy):
        """Sort key: squared distance from the observing squad's centroid to
        the nearest model of `enemy`, with the NAME as tiebreak so the order is
        total and the same on every run. Squared, because only the ordering is
        used; centroid-to-model rather than every pair, because this is a
        heuristic for the short-circuit and changes no answer."""
        if not squad.models or not enemy.models:
            return (float("inf"), enemy.name)
        cx = sum(m.x_in for m in squad.models) / len(squad.models)
        cy = sum(m.y_in for m in squad.models) / len(squad.models)
        nearest = min((m.x_in - cx) ** 2 + (m.y_in - cy) ** 2 for m in enemy.models)
        return (nearest, enemy.name)

    def can_use(self, squad, shooting_controller):
        if squad is None or self.state != IDLE:
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_SHOOTING:
                return False
            if squad.owner != self.turn_tracker.active_player:
                return False
        # "...that has not been selected to shoot this phase and is eligible
        # to shoot (excluding Fortification and Battle-shocked units)". The
        # exclusion is printed in the army rule's OWN text, so it does not
        # depend on what Battle Shock (01.07/08.03) does in general.
        #
        # This gate was removed once, on the reasoning that Battle Shock only
        # blocks friendly STRATAGEMS and this is an army rule - which is true
        # of 01.07 and beside the point, because the army rule excludes
        # Battle-shocked units by name. Restored when the user supplied the
        # printed text: "außerdem dürfen battle shocked units keine observer
        # sein. das muss auch wieder rein." Kept as a comment rather than
        # deleted history: the earlier removal answered a real report ("mein
        # stealth squad konnte in runde 3 nicht for the greater good
        # einsetzen"), and that report was simply the rule working.
        #
        # Fortification is not checked - no keyword for it exists in this
        # engine, and nothing has ever needed one.
        if squad.battle_shocked:
            return False
        if self.is_observer(squad):
            return False
        if squad in shooting_controller.shot_squad_ids:
            return False
        if not squad_has_greater_good(squad):
            return False
        if not available_shooting_types(squad, self.all_tokens, self.movement_controller):
            return False
        return self.any_eligible_target(squad)

    def start(self, squad):
        self.acting_squad = squad
        self.state = CHOOSING_TARGET

    def cancel(self):
        self.state = IDLE
        self.acting_squad = None

    def choose_target(self, target_squad):
        if self.state != CHOOSING_TARGET or target_squad not in self.eligible_targets(self.acting_squad):
            return
        self.spotted_by[target_squad] = self.acting_squad
        self.observer_squad_ids.add(self.acting_squad)
        if self.game_log is not None:
            self.game_log.add(
                f"{self.acting_squad.owner}: {self.acting_squad.name} marks {target_squad.name} "
                f"as Spotted (For the Greater Good)."
            )
        self.state = IDLE
        self.acting_squad = None
