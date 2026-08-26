"""Shroud Runners' "Target Acquisition".

RULE (printed, word for word):
  "In your Shooting phase, after this unit has shot, select one enemy unit hit
   by one or more of those attacks made with a long rifle. Until the end of the
   phase, that enemy unit cannot have the Benefit of Cover."

THE TRIGGER ALREADY EXISTED - twice over. ShootingController's
on_squad_finished_shooting fires with exactly the enemy units this activation
HIT (not merely targeted), which is the sixth ability to use it after
Suppression Volley, Fade Back, Fire Support, Tactical Acumen and Whispering
Web. And "in your Shooting phase" is enforced by that same hook, which is
deliberately skipped for a reactive Snap Shot (15.08/15.09).

WHAT WAS NEW is the qualifier "made with A LONG RIFLE". The hook reports which
UNITS were hit, not which weapon hit them, so shooting.py now also records the
weapon NAMES alongside - and this module, not shooting.py, decides that "Long
Rifle" is what counts. That keeps the datasheet knowledge here, and it is the
rule's own way of naming the weapon too.

THE EFFECT IS A MARK ON THE TARGET, not a grant on the shooter, which is the
opposite of every other cover-bypassing source in _cover_ignored_for_group():
"that enemy unit cannot have the Benefit of Cover" applies to attacks from
ANYONE for the rest of the phase, not just from the Shroud Runners. So it is
held per marked squad and read there.

OFFERED rather than automatic when more than one unit qualifies - only the
player knows which of them the rest of the army intends to shoot. With exactly
one there is nothing to decide and no reason to interrupt, so it is taken
silently, the same call Fire Support makes for the same reason.
"""

LONG_RIFLE_NAME = "Long Rifle"
TARGET_ACQUISITION_LABEL = "Target Acquisition"


def applies(squad):
    """Whether this unit has the ability. Per 19.03 a merged unit counts if any
    component brought it, which reading it off the models gives for free."""
    if squad is None:
        return False
    return any(getattr(m.profile, "target_acquisition", False)
               for m in squad.models if not m.is_dead())


class TargetAcquisitionController:
    """Wired into ShootingController.on_squad_finished_shooting in main.py, and
    read back by ShootingController._cover_ignored_for_group()."""

    def __init__(self, decision_manager=None, game_log=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        # Marked enemy squads, by id() - "until the end of the phase", so
        # reset_phase() clears it. Keyed by id rather than holding the squad so
        # a destroyed unit cannot be kept alive by this.
        self._marked = set()

    # -- the mark ---------------------------------------------------------
    def is_marked(self, squad):
        return squad is not None and id(squad) in self._marked

    def reset_phase(self):
        """"Until the end of the phase"."""
        self._marked = set()

    # -- the trigger ------------------------------------------------------
    def offer_after_shooting(self, squad, hit_squads, long_rifle_hits=()):
        """`hit_squads` is what the hook passes every listener; `long_rifle_hits`
        is the subset this ability actually cares about, supplied by the caller
        in main.py from the shooting controller's own per-weapon record."""
        if not applies(squad):
            return
        candidates = [s for s in hit_squads if s in long_rifle_hits]
        if not candidates:
            return
        if len(candidates) == 1 or self.decision_manager is None:
            self._mark(candidates[0], squad)
            return
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: {TARGET_ACQUISITION_LABEL} - which unit loses the Benefit of Cover?",
            [(target.name, (lambda t=target: self._mark(t, squad))) for target in candidates],
        )

    def _mark(self, target, squad):
        self._marked.add(id(target))
        if self.game_log is not None:
            self.game_log.add(
                f"{squad.owner}: {TARGET_ACQUISITION_LABEL} - {target.name} cannot have the "
                "Benefit of Cover until the end of the phase."
            )
