""""After this unit has shot, one enemy unit it hit takes a Battle-shock test."

TWENTY-FIRST EXTRACTION, at the second consumer.

Two Aeldari datasheets print the same sentence, one clause apart:

  FACE OF DEATH   (Maugan Ra)    "In your Shooting phase, after this model has
      shot, select one enemy unit hit by one or more of those attacks. That
      enemy unit must take a Battle-shock test, subtracting 1 from the result."

  PANICKED QUARRY (Leystalker)   "In your Shooting phase, when this unit has
      shot, select one enemy unit (EXCLUDING MONSTER/VEHICLE UNITS) hit by
      those attacks. That enemy unit makes a battle-shock roll, with -1 to that
      battle-shock roll."

So the trigger, the selection, the forced test and the -1 are shared, and the
only difference is which targets are eligible. That is one predicate, and it is
what each ability names here.

BOTH PIECES ALREADY EXISTED, which is why this module is small:
  * "after this unit has shot, select one enemy unit hit" is
    ShootingController.on_squad_finished_shooting - the instant Suppression
    Volley, Crystalline Targeting, Target Acquisition, the Monofilament Snare
    and the Monofilament Web all use.
  * "must take a Battle-shock test" is BattleShockController.start_forced_roll(),
    which exists for "a Battle-Shock test some rule imposes out of turn" and
    already takes a `penalty` - so the -1 needs no new arithmetic. Neocapacitor
    Shields opened that door.

THE TEST IS NOT OPTIONAL for either ("must take" / "makes"). What IS a choice is
WHICH unit, when more than one was hit - and a sole candidate is auto-picked
rather than asked about, the shortcut every other "select one enemy unit hit"
ability here takes.
"""
from game.squad import is_monster_or_vehicle_unit

#: "subtracting 1 from the result" / "-1 to that battle-shock roll".
BATTLE_SHOCK_PENALTY = 1


def any_target(_squad):
    """Face of Death names no restriction."""
    return True


def excluding_monsters_and_vehicles(squad):
    """Panicked Quarry's one extra clause. The exact complement of
    is_monster_or_vehicle_unit(), the same pair Monster Hunters and Grim
    Reapers use to divide the board between them."""
    return not is_monster_or_vehicle_unit(squad)


class BattleShockAfterShooting:
    """One ability's offer. Subclass and set `flag`, `label` and `eligible`."""

    flag = None
    label = "Battle-shock"
    penalty = BATTLE_SHOCK_PENALTY

    #: A predicate on the TARGET unit; the two abilities differ only here.
    eligible = staticmethod(any_target)

    def __init__(self, battle_shock_controller=None, decision_manager=None,
                 game_log=None):
        self.battle_shock_controller = battle_shock_controller
        self.decision_manager = decision_manager
        self.game_log = game_log

    def unit_has_ability(self, squad):
        """Whether THIS unit may offer the test.

        The two datasheet abilities read a printed UnitProfile flag. A
        STRATAGEM of the same shape cannot - it is gated on a detachment and a
        pair of datasheet names, not on anything a model carries - so it
        overrides this instead of inventing a fake profile field."""
        if squad is None:
            return False
        return any(getattr(m.profile, self.flag, False)
                   for m in getattr(squad, "models", ()) or () if not m.is_dead())

    def penalty_for(self, target):
        """The modifier on THIS test.

        A method rather than the class attribute alone, because the third
        consumer's -1 is CONDITIONAL: Eldritch Suppression subtracts 1 only if
        a model in the chosen unit was destroyed by those attacks, where the
        two datasheet abilities always subtract 1. Defaults to the flat value,
        so neither of them notices."""
        return self.penalty

    def offer_after_shooting(self, squad, hit_squads):
        if not self.unit_has_ability(squad):
            return False
        targets = sorted((s for s in hit_squads if self.eligible(s)),
                         key=lambda s: s.name)
        if not targets:
            return False
        if len(targets) == 1 or self.decision_manager is None:
            return self._test(targets[0])
        self.decision_manager.request(
            squad.owner,
            "%s: %s - which enemy unit must take a Battle-shock test?"
            % (squad.name, self.label),
            [(t.name, (lambda t=t: self._test(t))) for t in targets],
        )
        return True

    def _test(self, target):
        if self.battle_shock_controller is None:
            return False
        penalty = self.penalty_for(target)
        started = self.battle_shock_controller.start_forced_roll(
            target, self.label, penalty=penalty)
        if started and self.game_log is not None:
            self.game_log.add(
                "%s: %s must take a Battle-shock test%s."
                % (self.label, target.name,
                   " at -%d" % penalty if penalty else ""))
        return started
