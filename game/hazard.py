from game.damage_resolution import MortalWoundAllocationSession, resolve_mortal_wounds
from game.squad import is_monster_or_vehicle_unit

MORTAL_WOUNDS_ON_FAIL = 1
MORTAL_WOUNDS_ON_FAIL_MONSTER_VEHICLE = 3


def hazard_failures(rolls):
    """Rule 06.03: each roll of 1-2 (out of a batch made simultaneously) is
    a failure."""
    return sum(1 for roll in rolls if roll <= 2)


def hazard_mortal_wounds(squad, rolls):
    """Rule 06.03: how many mortal wounds a batch of hazard rolls inflicts -
    1 per failure, or 3 instead if every model in the unit is a
    MONSTER/VEHICLE model."""
    failures = hazard_failures(rolls)
    if failures == 0:
        return 0
    per_failure = (
        MORTAL_WOUNDS_ON_FAIL_MONSTER_VEHICLE if is_monster_or_vehicle_unit(squad)
        else MORTAL_WOUNDS_ON_FAIL
    )
    return failures * per_failure


def resolve_hazard_rolls(squad, rolls, log=None):
    """Rule 06.03: one D6 per required hazard roll, all made simultaneously
    (the caller rolls them all at once and passes every result here).
    Non-interactive convenience wrapper (auto-picks casualties, no Feel No
    Pain) - useful for tests and other non-interactive callers. The live
    game (rule 24.15's [HAZARDOUS], in shooting.py/fight.py) computes
    hazard_mortal_wounds() itself and applies them via
    MortalWoundAllocationSession directly, so the owning player actually
    gets to pick and Feel No Pain gets its real dice step."""
    total_mortal_wounds = hazard_mortal_wounds(squad, rolls)
    if total_mortal_wounds == 0:
        return 0
    if log is not None:
        log(f"Hazard Rolls: {hazard_failures(rolls)}/{len(rolls)} failed -> {total_mortal_wounds} mortal wound(s).")
    return resolve_mortal_wounds(squad, total_mortal_wounds, log=log)


class HazardRollStep:
    """Rule 06.03: rolls one D6 per required hazard check (all at once),
    computes how many mortal wounds that inflicts, and applies them via an
    interactive MortalWoundAllocationSession (the owning player picks
    casualties; Feel No Pain gets its real dice step) - a reusable version
    of the same hazard-roll-then-mortal-wounds flow already wired directly
    into ShootingController/FightController for [HAZARDOUS] (24.15), for
    callers that aren't themselves a hit/wound/save state machine (rules
    18.04's Combat Disembark and 18.05's Emergency Disembark)."""

    def __init__(self, squad, count, dice_manager, log=None):
        self.squad = squad
        self.dice_manager = dice_manager
        self.log = log
        self.mortal_wound_session = None
        self._rolled = False
        dice_manager.roll(count=count, sides=6, label=f"Hazard Rolls: {squad.name} ({count} model(s))")

    @property
    def done(self):
        return self._rolled and self.mortal_wound_session is None

    @property
    def pending_damage_choice(self):
        return self.mortal_wound_session.pending_choice if self.mortal_wound_session is not None else None

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_session_done()

    def on_dice_acknowledged(self):
        # A dice acknowledgement while a mortal-wound session is mid-Feel-No-
        # Pain-roll belongs to that session's own step, not the original
        # hazard batch - same pattern as ExplosivesController/DeadlyDemiseController.
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_session_done()
            return
        if self._rolled:
            return
        self._rolled = True
        rolls = self.dice_manager.last_values
        total = hazard_mortal_wounds(self.squad, rolls)
        if self.log is not None:
            self.log(
                f"Hazard Rolls {rolls}: {hazard_failures(rolls)}/{len(rolls)} failed -> {total} mortal wound(s)."
            )
        if total > 0:
            self.mortal_wound_session = MortalWoundAllocationSession(
                self.squad, total, dice_manager=self.dice_manager, log=self.log,
            )
            self._check_session_done()

    def _check_session_done(self):
        if self.mortal_wound_session is not None and self.mortal_wound_session.done:
            self.mortal_wound_session = None
