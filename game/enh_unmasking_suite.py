"""Advanced Acquisition Cadre Enhancement: Unmasking Suite (15 pts).

RULE (verbatim, rules/tau_empire/detachments/Advanced Acquisition Cadre.md):
  GHOSTKEEL BATTLESUIT/PATHFINDER TEAM/STEALTH BATTLESUITS unit only. When this
  unit is selected to shoot, you can select one enemy unit within 24" of this
  unit. That enemy unit has +9" detection range until this unit has shot.

THE SIXTH MARK ON AN ENEMY UNIT
--------------------------------
After Guide, Doom, Whispering Web, Advanced Scouting and Auxiliary Cadre's
Harnessed Alien Instincts. Like all five it is held per player in a controller
rather than as a flag on the marked unit, because it belongs to the marked
unit's OPPONENT - the same arrangement and the same reason.

Its DURATION is the shortest of the six, and it is printed rather than chosen:
"until this unit has shot". Not "until the end of the phase" and not "until the
end of the turn". So the mark is cleared on the same activation-end seam
game/enh_prototype_weapon_system.py uses, and it can never survive into another
unit's shooting - which matters, because +9" is enormous next to a 15" base and
a mark that outlived its window would light up the board.

WHY IT IS WORTH ANYTHING AT ALL
--------------------------------
Rule 13.09: a hidden model can only be seen by enemy models within ITS OWN
detection range. +9" on the target therefore means this unit can see - and so
shoot - a hidden enemy from 24" where it could only manage 15". That is the
whole purpose, and it is why the sign is positive here where Negation Emitters'
is negative: this one EXPOSES someone else, that one hides its own unit. Both
directions are measured.

"WITHIN 24" OF THIS UNIT" is measured from the unit's models to the target's,
edge to edge, the same distance every other range in this engine uses.

A UNIT-LEVEL ENHANCEMENT, like Negation Emitters beside it - see that module
for why, and for how game/enhancements.py's `unit_level` handles it.

OPTIONAL ("you can"), so it is offered rather than applied - and it is offered
only when there is something to mark, since a prompt whose only answer is
"none" is the Fehlerklasse-5 mistake this repo keeps out. An owner in
`auto_players` answers deterministically (the nearest eligible enemy, ties
broken by name so a self-play run is reproducible), which is a rule answering
its own prompt rather than an AI path - the standing T'au rule.
"""

from game import ai_mode, enhancements
from game.squad import edge_distance

UNMASKING_SUITE = "Unmasking Suite"
UNMASKING_RANGE_IN = 24.0            # "one enemy unit within 24" of this unit"
UNMASKING_DETECTION_BONUS_IN = 9.0   # "+9" detection range"


def applies(squad):
    """A living model of the unit still carries it, and the owner really
    fields Advanced Acquisition Cadre."""
    return enhancements.is_active(squad, UNMASKING_SUITE)


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def within_range(squad, other):
    """"within 24" of this unit" - closest model to closest model."""
    for model in _living(squad):
        for enemy in _living(other):
            if edge_distance(model, enemy) <= UNMASKING_RANGE_IN:
                return True
    return False


class UnmaskingSuiteController:
    """Holds the mark for the length of one shooting activation.

    Wired to ShootingController's begin/end-of-activation seams in main.py -
    the same pair game/targeting_array.py and
    game/enh_prototype_weapon_system.py use, and the pair whose two halves
    ARE the printed window ("when this unit is selected to shoot" / "until this
    unit has shot").
    """

    def __init__(self, game_state=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self.marked = None          # the enemy Squad currently lit up, or None
        self.marked_by = None       # the unit whose activation lit it

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _squads(self):
        """Every distinct squad on the board. Deduplicated: game_state.tokens
        is one entry per MODEL, and a ten-model unit listed ten times would be
        offered ten times - the bug game/auxiliary_cadre.py hit on exactly this
        list."""
        seen = []
        for token in (getattr(self.game_state, "tokens", None) or ()):
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in seen:
                seen.append(squad)
        return seen

    def eligible_targets(self, squad):
        """"one enemy unit within 24" of this unit"."""
        if not applies(squad):
            return []
        return [s for s in self._squads()
                if s.owner != squad.owner and _living(s) and within_range(squad, s)]

    def detection_bonus_in(self, squad):
        """This Enhancement's contribution to game/detection_range.py's fold."""
        return UNMASKING_DETECTION_BONUS_IN if squad is not None and squad is self.marked else 0.0

    def begin_activation(self, squad):
        """"When this unit is selected to shoot" - offer the mark. Returns True
        if anything was asked or marked."""
        if not applies(squad):
            return False
        targets = self.eligible_targets(squad)
        if not targets:
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return self.mark(squad, self._pick(squad, targets))
        options = [(f"{UNMASKING_SUITE}: {t.name}", (lambda target=t: self.mark(squad, target)), t)
                   for t in targets]
        options.append(("Do not use it", None))
        self.decision_manager.request(
            squad.owner,
            f"{UNMASKING_SUITE}: reveal one enemy unit within "
            f'{UNMASKING_RANGE_IN:.0f}" of {squad.name}?',
            options)
        return True

    def _pick(self, squad, targets):
        """The deterministic answer for a non-human owner: the nearest, ties
        broken by name so a self-play run is reproducible. Nearest rather than
        most valuable, because what this buys is the ability to SEE something -
        a target already visible gains nothing, and the closest hidden unit is
        the one +9" is most likely to actually reveal."""
        def distance(other):
            return min((edge_distance(m, e) for m in _living(squad) for e in _living(other)),
                       default=UNMASKING_RANGE_IN)
        return sorted(targets, key=lambda s: (distance(s), s.name))[0]

    def mark(self, squad, target):
        if target is None or not applies(squad):
            return False
        self.marked = target
        self.marked_by = squad
        self._log(f"{squad.owner}: {squad.name}'s {UNMASKING_SUITE} reveals {target.name} "
                  f'(+{UNMASKING_DETECTION_BONUS_IN:.0f}" detection range until it has shot).')
        return True

    def end_activation(self, squad):
        """"Until this unit has shot" - the mark dies with the activation.

        Cleared whenever the activation that set it ends, and also when the
        activation of ANY unit ends while a mark is standing: a mark whose
        owner was destroyed mid-activation would otherwise have no end."""
        if self.marked is None:
            return
        if squad is None or self.marked_by is None or squad is self.marked_by:
            self.marked = None
            self.marked_by = None
