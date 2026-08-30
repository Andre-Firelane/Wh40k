"""Auxiliary Cadre Enhancement: Admired Leader (20 pts).

RULE (verbatim, rules/tau_empire/detachments/Auxiliary Cadre.md):
  T'AU EMPIRE model only (excluding KROOT models). In your Command phase, you
  can select one KROOT/VESPID STINGWINGS unit within 12" of this model. If you
  do, that unit has +1 Ld and OC until the start of your next Command phase.

A SQUAD FLAG, NOT A CONTROLLER LOOKUP - THE ESTABLISHED ARRANGEMENT
--------------------------------------------------------------------
The two characteristics it touches are read through
game/leadership.py's leadership_threshold() and
game/objective_control.py's effective_oc(). Between them those have well over a
dozen call sites, and neither takes a controller.

game/plagues.py already faced exactly this and wrote down the answer: the
Death Guard's "Afflicted" state is stamped onto the SQUAD, and the funnels read
the unit rather than growing a parameter. This does the same, with
Squad.admired_leader_active. The flag is written by exactly one place - the
controller below - so there is still one source of truth; what is avoided is
threading it through a dozen signatures for one Enhancement.

THE DURATION IS ONE CLAUSE THAT NEEDS TWO ACTS AT ONE SEAM
-----------------------------------------------------------
"until the start of your next Command phase" and "in your Command phase" are
the SAME moment one round apart, so begin_command_phase() does both, in this
order: clear what the previous round set, THEN offer. Written the other way
round it would clear the mark it had just made. That ordering is its own test
line, because the two lines look independent.

WHY A UNIT IS OFFERED AT ALL, AND ONLY THEN
--------------------------------------------
"You can" makes it optional, so it is a prompt. It is raised only when there is
an eligible unit in range: a prompt whose only answer is "none" is the
Fehlerklasse-5 mistake this repo keeps out. An owner in `auto_players` answers
deterministically (the unit with most living models - OC and Ld both scale with
bodies, so that is where a flat +1 to each buys most), which is a rule answering
its own prompt rather than an AI path; the standing T'au rule stands.

"+1 Ld" IS A BETTER CHARACTERISTIC, SO A LOWER THRESHOLD. Ld is printed as an
N+ threshold in this engine, and leadership_threshold() returns that number, so
an improvement SUBTRACTS. Written the other way round a 20-point Enhancement
would make its target's Battle-shock tests harder - and it would look right,
because "+1" and "+1" are the same word for the two characteristics that move
in opposite directions here. Its own test line for that reason.

"KROOT/VESPID STINGWINGS unit" is read off the model keywords the datasheets
already carry (`kroot`, `vespid_stingwings`), asked of any living model - which
is 19.03's keyword pooling, so a Kroot unit with a T'au character attached is
still a KROOT unit.

THE BEARER MAY NOT BE A KROOT MODEL ("excluding KROOT models"), enforced in
game/enhancements.py's registry where every bearer restriction lives - so a
Kroot Shaper cannot take this one, and takes Student of Kauyon instead.
"""

from game import enhancements
from game.command_phase_mark import CommandPhaseMark
from game.squad import edge_distance

ADMIRED_LEADER = "Admired Leader"
ADMIRED_LEADER_RANGE_IN = 12.0
ADMIRED_LEADER_OC_BONUS = 1
ADMIRED_LEADER_LEADERSHIP_BONUS = -1   # a BETTER Ld is a LOWER threshold
FLAG_ATTR = "admired_leader_active"


def is_marked(squad):
    return bool(getattr(squad, FLAG_ATTR, False))


def oc_bonus(model):
    """+1 OC while the model's unit is marked. Read by
    game/objective_control.py's fold."""
    if model is None:
        return 0
    return ADMIRED_LEADER_OC_BONUS if is_marked(getattr(model, "squad", None)) else 0


def leadership_bonus(squad):
    """The adjustment to the unit's Ld THRESHOLD - negative, because a better
    characteristic is a lower number here. Read by game/leadership.py's
    leadership_threshold()."""
    return ADMIRED_LEADER_LEADERSHIP_BONUS if is_marked(squad) else 0


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def is_kroot_or_vespid(squad):
    """"one KROOT/VESPID STINGWINGS unit" - 19.03 keyword pooling, so any
    living model carrying either keyword answers for the unit."""
    return any(m.profile.kroot or m.profile.vespid_stingwings for m in _living(squad))


class AdmiredLeaderController(CommandPhaseMark):
    """Driven from main.py's Command-phase block, the same seam Reanimation
    Protocols and Coordinated Leadership use.

    The machine itself is game/command_phase_mark.py, extracted when the three
    Spirit Conclave marks turned this printed sentence into a fourth carrier.
    Everything this class still says is what its own card says and the others'
    do not:

      * the KROOT/VESPID keyword clause,
      * `exclude_own_unit=True`. That skip is NOT printed on this card either,
        but it is the behaviour this Enhancement has always had, so it is kept
        exactly and pinned - the three new marks pass False, and the extraction
        must not quietly move either of them. See the shared module's docstring.
    """

    def __init__(self, game_state=None, decision_manager=None, game_log=None,
                 auto_players=()):
        super().__init__(
            ADMIRED_LEADER, ADMIRED_LEADER_RANGE_IN, FLAG_ATTR,
            is_kroot_or_vespid,
            "gets +1 Ld and OC",
            game_state=game_state, decision_manager=decision_manager,
            game_log=game_log, auto_players=auto_players,
            exclude_own_unit=True,
        )
