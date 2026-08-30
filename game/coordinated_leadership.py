"""The Ethereal's "Coordinated Leadership".

RULE (printed, word for word):
  "At the end of your Command phase, roll one D6: on a 4+, you gain 1CP."

A REAL, VISIBLE DICE STEP, not a silent computation - the standing instruction
in this repo for anything that rolls. It is queued at the same seam Reanimation
Protocols uses (the END of the Command phase, driven from main.py's own
phase-change block), and like that one it is a QUEUE: an army with two
Ethereals rolls twice, because the printed text is per model.

THE CP CAP IS NOT RE-IMPLEMENTED HERE. CommandPointManager.gain_cp() already
enforces BONUS_CP_PER_ROUND_CAP across every bonus source, and
bonus_cp_remaining() is the one definition of what is left - so this rolls only
while there is headroom, on the same "never offer what buys nothing" principle
the Secondary Missions' CP discard already follows. Rolling a die that could
not pay out would be worse than not rolling: it looks like a bug.

NO DECISION AND NO auto_players SPLIT. There is nothing to choose - the roll is
mandatory and its effect is automatic - so a human and the AI take exactly the
same path, and the AI needs no entry in ai/ at all.
"""

COORDINATED_LEADERSHIP_THRESHOLD = 4
COORDINATED_LEADERSHIP_DICE_SIDES = 6
COORDINATED_LEADERSHIP_CP = 1
COORDINATED_LEADERSHIP_LABEL = "Coordinated Leadership"


def unit_has_coordinated_leadership(squad):
    """Read live off the living models, so it ends with the Ethereal."""
    if squad is None:
        return False
    return any(getattr(m.profile, "coordinated_leadership", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


class CoordinatedLeadershipController:
    """Queued at the end of its owner's Command phase from main.py's own
    phase-change block - the same seam Reanimation Protocols uses."""

    def __init__(self, dice_manager=None, command_points=None, turn_tracker=None,
                 game_log=None):
        self.dice_manager = dice_manager
        self.command_points = command_points
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._queue = []
        self._rolling = None

    @property
    def is_busy(self):
        return self._rolling is not None or bool(self._queue)

    def _round(self):
        return getattr(self.turn_tracker, "battle_round", 1)

    def _has_headroom(self, player):
        """Whether a CP gained now would actually arrive - see the module
        docstring on why a roll that cannot pay out is not offered."""
        if self.command_points is None:
            return True
        remaining = self.command_points.bonus_cp_remaining(player, self._round())
        return remaining is None or remaining > 0

    def eligible_squads(self, squads, player):
        return sorted((s for s in squads
                       if s.owner == player and unit_has_coordinated_leadership(s)),
                      key=lambda s: s.name)

    def begin_command_phase(self, squads, player):
        """Queue one roll per Ethereal. Returns True if anything was queued."""
        if self.is_busy or not self._has_headroom(player):
            return False
        self._queue = [(s, player) for s in self.eligible_squads(squads, player)]
        if not self._queue:
            return False
        return self._roll_next()

    def _roll_next(self):
        if not self._queue:
            self._rolling = None
            return False
        squad, player = self._queue.pop(0)
        self._rolling = (squad, player)
        if self.dice_manager is None:
            self._resolve(COORDINATED_LEADERSHIP_THRESHOLD)
            return True
        self.dice_manager.roll(
            1, COORDINATED_LEADERSHIP_DICE_SIDES,
            label=COORDINATED_LEADERSHIP_LABEL,
            success_threshold=COORDINATED_LEADERSHIP_THRESHOLD,
            target_name=squad.name, target_squad=squad, subject_label="Rolling")
        return True

    def on_dice_acknowledged(self):
        """Called from main.py's dice-acknowledgement chain. Returns True if
        this controller owned the roll."""
        if self._rolling is None:
            return False
        values = getattr(self.dice_manager, "last_values", None) or [1]
        self._resolve(values[0])
        return True

    def _resolve(self, value):
        squad, player = self._rolling
        self._rolling = None
        if value >= COORDINATED_LEADERSHIP_THRESHOLD:
            if self.command_points is not None:
                self.command_points.gain_cp(
                    player, self._round(), COORDINATED_LEADERSHIP_CP,
                    reason=f"{COORDINATED_LEADERSHIP_LABEL} ({squad.name})")
            elif self.game_log:
                self.game_log.add(
                    f"[coordinated leadership] {squad.name} rolled {value}: +1 CP")
        elif self.game_log:
            self.game_log.add(
                f"[coordinated leadership] {squad.name} rolled {value}: no CP "
                f"(needed {COORDINATED_LEADERSHIP_THRESHOLD}+)", file_only=True)
        self._roll_next()
