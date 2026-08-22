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

from game import line_of_sight, status_effects
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
        if squad is None:
            return []
        enemy_squads = {
            token.squad for token in self.all_tokens
            if token.squad is not None and token.squad.owner != squad.owner
        }
        last_ranged_attack_turn = (
            self.shooting_controller.last_ranged_attack_turn if self.shooting_controller is not None else {}
        )
        result = []
        for enemy in enemy_squads:
            if self.is_spotted(enemy):
                continue
            if any(
                line_of_sight.has_line_of_sight(friendly, defender, self.obstacles, self.all_tokens, self.terrain_areas)
                and status_effects.is_detectable(defender, squad, self.terrain_areas, self.turn_tracker, last_ranged_attack_turn)
                for friendly in squad.models
                for defender in enemy.models
            ):
                result.append(enemy)
        return result

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
        return bool(self.eligible_targets(squad))

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
