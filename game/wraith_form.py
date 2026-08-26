"""Canoptek Wraiths' "Wraith Form".

RULE (printed, word for word):
  "Each time this unit ends a Normal move, you can select one enemy unit it
   moved over during that move and roll one D6 for each model in this unit:
   for each 4+, that enemy unit suffers 1 mortal wound."

"MOVED OVER" IS THE PART THAT NEEDED A DECISION, because this engine does not
record a movement PATH - it records where each model started and where it
ended (MovementController.move_start), and the drag in between is not kept.

So "moved over" is read as: the straight segment from a model's start point to
its end point passes within that model's base radius of an enemy model's base.
That is exact for the ordinary case (a unit ordered to a destination travels
essentially straight) and it is the only reading the recorded data supports.
The alternative - a real swept path - would mean recording every intermediate
waypoint for every model of every unit, all game, to serve one datasheet.
Stated here rather than left to be discovered, because a player who drags a
Wraith in a deliberate arc around a unit will still be offered it.

THE SNAPSHOT. on_move_finished fires AFTER MovementController._clear_move_state()
has emptied move_start, so the start points are read from `last_move_start`,
which exists for this ability - see the comment at its assignment.

NORMAL MOVES ONLY. The hook passes the move KIND, and the printed text names
"a Normal move" specifically: an Advance, a Fall Back, a charge or a pile-in
does not trigger it.

OPTIONAL ("you can"), so a human is asked which enemy unit - or none - and the
AI answers deterministically: the unit it can hurt most, by the shared
game/damage_estimate.py measure of value.
"""

MORTAL_WOUND_THRESHOLD = 4      # "for each 4+"
WRAITH_FORM_MOVE_KIND = "normal"


def has_wraith_form(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "wraith_form", False)
               for m in squad.models if not m.is_dead())


def _segment_hits_model(start, end, mover_radius, target):
    """Whether the straight segment start->end passes within touching distance
    of `target`'s base."""
    (x1, y1), (x2, y2) = start, end
    px, py = target.x_in, target.y_in
    reach = mover_radius + target.radius_in
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5 <= reach
    # Closest approach of the point to the segment, clamped to its ends.
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    cx, cy = x1 + t * dx, y1 + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5 <= reach


def units_moved_over(squad, starts, all_tokens):
    """Every enemy unit at least one model of `squad` passed over.

    `starts` is {token.id: (x, y)} - MovementController.last_move_start."""
    if squad is None:
        return []
    found = {}
    for model in squad.models:
        if model.is_dead():
            continue
        start = (starts or {}).get(model.id)
        if start is None:
            continue
        end = (model.x_in, model.y_in)
        for token in all_tokens or ():
            other = getattr(token, "squad", None)
            if other is None or other.owner == squad.owner or token.is_dead():
                continue
            if id(other) in found:
                continue
            if _segment_hits_model(start, end, model.radius_in, token):
                found[id(other)] = other
    return list(found.values())


def dice_count(squad):
    """"roll one D6 for each model in this unit" - the models still standing
    when the ability resolves."""
    if squad is None:
        return 0
    return sum(1 for m in squad.models if not m.is_dead())


class WraithFormController:
    """Offers the ability when a Wraith unit finishes a Normal move.

    Wired in main.py as an on_move_finished listener, the same seam Isha's Fury
    already uses."""

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, movement_controller=None, auto_players=(),
                 target_pick=None):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.movement_controller = movement_controller
        self.auto_players = set(auto_players)
        # target_pick(attacker, candidates) -> chosen squad. main.py passes the shared
        # damage-value ranking so the AI's answer is the same measure every
        # other deterministic target choice uses; None falls back to the first
        # candidate by name, which keeps tests reproducible.
        self.target_pick = target_pick
        self._pending = None
        self.mortal_wound_session = None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    @property
    def is_busy(self):
        return self._pending is not None

    def candidates(self, squad):
        starts = getattr(self.movement_controller, "last_move_start", {}) if self.movement_controller else {}
        return units_moved_over(squad, starts, self._tokens())

    def on_move_finished(self, squad, kind):
        """The listener. Returns True if anything was offered or used."""
        if kind != WRAITH_FORM_MOVE_KIND or not has_wraith_form(squad):
            return False
        if self._pending is not None or not dice_count(squad):
            return False
        targets = self.candidates(squad)
        if not targets:
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad, self._pick(squad, targets))
        options = [
            (f"Wraith Form: {t.name} ({dice_count(squad)} D6, 1 mortal wound per 4+)",
             (lambda target=t: self._use(squad, target)))
            for t in targets
        ]
        options.append(("Decline", None))
        self.decision_manager.request(
            squad.owner, f"{squad.name} moved over an enemy unit - use Wraith Form?", options)
        return True

    def _pick(self, squad, targets):
        """Which enemy unit to hit. `squad` is passed so the ranking can use
        the shared damage estimate, which needs an attacker to mean anything -
        without it the measure collapses to "biggest unit", the exact bias
        game/damage_estimate.py exists to avoid."""
        if self.target_pick is not None:
            chosen = self.target_pick(squad, targets)
            if chosen is not None:
                return chosen
        return sorted(targets, key=lambda s: s.name)[0]

    def _use(self, squad, target):
        count = dice_count(squad)
        if not count or target is None:
            return False
        self._pending = {"squad": squad, "target": target}
        self.dice_manager.roll(
            count, 6, label="Wraith Form", success_threshold=MORTAL_WOUND_THRESHOLD,
            target_name=target.name, attacker_squad=squad, target_squad=target)
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            return False
        ctx, self._pending = self._pending, None
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or []
        wounds = sum(1 for v in values if v >= MORTAL_WOUND_THRESHOLD)
        target = ctx["target"]
        if not wounds:
            self._log(f"Wraith Form ({ctx['squad'].name}): {values} - no mortal wounds.")
            return True
        self._log(f"Wraith Form ({ctx['squad'].name}): {values} - {target.name} suffers "
                  f"{wounds} mortal wound(s).")
        from game.damage_resolution import MortalWoundAllocationSession
        self.mortal_wound_session = MortalWoundAllocationSession(
            target, wounds, dice_manager=self.dice_manager,
            log=(lambda m: self._log(m)) if self.game_log is not None else None)
        return True
