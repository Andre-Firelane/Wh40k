"""Krootox Riders' "Kroot Packmates".

RULE (printed, word for word):
  "Once per turn, in your opponent's Shooting phase, when a friendly KROOT
   INFANTRY unit within 6" of this unit is selected as the target of an attack,
   one unit from your army with this ability can use it. If it does, after that
   enemy unit has finished making its attacks, that unit with this ability can
   shoot as if it were your Shooting phase, but when resolving those attacks it
   can only target that enemy unit (and only if it is an eligible target)."

AWAKENED DYNASTY'S PROTOCOL OF THE VENGEFUL STARS WITHOUT THE CP. Word for word
the same second half - "can shoot as if it were your Shooting phase, but ...
can only target that enemy unit" - so it uses the same machinery:
ShootingController.start_reactive_shooting(restrict_to=...), which grants the
ORDINARY activation rather than 15.09's deliberately weaker Snap Shooting, and
whose `restrict_to` is enforced in the one place that decides what may be shot
at (_is_valid_target_squad).

WHAT DIFFERS IS THE TRIGGER, and it is a mouthful with four separate conditions:

  * "IN YOUR OPPONENT'S SHOOTING PHASE" - so it hangs off ShootingController's
    target_reactions list, the same "just after an enemy unit has selected its
    targets" instant Stim Injectors and 'Ard as Nails use.
  * "A FRIENDLY KROOT INFANTRY UNIT WITHIN 6" OF THIS UNIT" is the unit being
    SHOT AT, not the Krootox - the Krootox react on someone else's behalf. Both
    keywords, and INFANTRY is the half that does the work: another Krootox unit
    (MOUNTED) does not qualify, which is the printed reading and the reason the
    predicate is not simply "a KROOT unit".
  * "ONE UNIT FROM YOUR ARMY WITH THIS ABILITY" - so the once-per-turn ledger
    is keyed by PLAYER, not by squad: two Krootox units share one use. Same
    reading My Will Be Done and War Leader take of the same sentence.
  * "AFTER THAT ENEMY UNIT HAS FINISHED MAKING ITS ATTACKS" - so the shooting
    is deferred to on_squad_finished_shooting rather than fired at the trigger,
    which is what keeps it from interrupting the attack it is reacting to.
"""

from game.squad import edge_distance

KROOT_PACKMATES_RANGE_IN = 6.0
KROOT_PACKMATES_LABEL = "Kroot Packmates"


def unit_has_kroot_packmates(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "kroot_packmates", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def is_kroot_infantry(squad):
    """Both keywords on the same model - a MOUNTED Krootox does not qualify."""
    if squad is None:
        return False
    return any(getattr(m.profile, "kroot", False) and getattr(m.profile, "infantry", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def within_range(squad, other):
    for mine in getattr(squad, "models", ()) or ():
        if mine.is_dead():
            continue
        for theirs in getattr(other, "models", ()) or ():
            if not theirs.is_dead() and edge_distance(mine, theirs) <= KROOT_PACKMATES_RANGE_IN:
                return True
    return False


class KrootPackmatesController:
    """Registered in ShootingController.target_reactions."""

    def __init__(self, shooting_controller=None, decision_manager=None,
                 game_state=None, turn_tracker=None, game_log=None, auto_players=()):
        self.shooting_controller = shooting_controller
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self._used_this_turn = {}   # player -> the turn number it was spent on
        self._owed = None           # (reacting squad, the enemy that shot)

    # -- eligibility ------------------------------------------------------
    def _turn_key(self):
        tracker = self.turn_tracker
        if tracker is None:
            return None
        return (getattr(tracker, "battle_round", 0), getattr(tracker, "turn_owner", None))

    def available(self, player):
        """"Once per turn" - per ARMY, not per Krootox unit."""
        return self._used_this_turn.get(player) != self._turn_key()

    def _squads(self):
        if self.game_state is None:
            return []
        return [t.squad for t in self.game_state.tokens if t.squad is not None]

    def reactors_for(self, target_squad):
        """Friendly Krootox units that may react to `target_squad` being shot.

        `target_squad` must itself be a friendly KROOT INFANTRY unit within 6"
        of the reactor - which is what makes this a bodyguard reaction rather
        than a self-defence one."""
        if target_squad is None or not is_kroot_infantry(target_squad):
            return []
        seen = []
        for squad in self._squads():
            if squad in seen or squad.owner != target_squad.owner:
                continue
            if not unit_has_kroot_packmates(squad) or not self.available(squad.owner):
                continue
            if within_range(squad, target_squad):
                seen.append(squad)
        return sorted(seen, key=lambda s: s.name)

    # -- the reaction -----------------------------------------------------
    def maybe_offer(self, attacking_squad, target_squad, melee=False):
        """ShootingController.target_reactions' ACTUAL contract.

        The protocol is one target at a time plus a `melee` flag - see
        game/shooting.py's `for reaction in self.target_reactions` loop and
        game/stim_injectors.py, its other implementer. This class shipped with
        only on_targets_selected() below, whose docstring claimed to BE that
        contract; nothing called it, and every game died with
        `AttributeError: 'KrootPackmatesController' object has no attribute
        'maybe_offer'` the first time any unit selected a shooting target.

        Melee is declined outright: the printed WHEN is "your opponent's
        Shooting phase". The controller is only registered in the shooting
        tuple today, so the flag is never True - checked anyway rather than
        ignored, because the two tuples are one edit apart.
        """
        if melee:
            return False
        return self.on_targets_selected(attacking_squad, [target_squad])

    def on_targets_selected(self, attacking_squad, target_squads):
        """The plural form, kept as the implementation: it is the shape Split
        Fire would want if this ever needs to see a whole activation's targets
        at once."""
        for target in target_squads or ():
            reactors = self.reactors_for(target)
            if not reactors:
                continue
            reactor = reactors[0]
            if reactor.owner in self.auto_players or self.decision_manager is None:
                return self._accept(reactor, attacking_squad)
            self.decision_manager.request(
                reactor.owner,
                f"{reactor.name}: Kroot Packmates - shoot back at {attacking_squad.name} "
                f"after it finishes attacking {target.name}?",
                [("Shoot back", lambda r=reactor, a=attacking_squad: self._accept(r, a)),
                 ("Decline", lambda: None)],
            )
            return True
        return False

    def _accept(self, reactor, attacking_squad):
        """"If it does" - the use is spent here, and the SHOOTING waits for the
        enemy to finish its attacks."""
        self._used_this_turn[reactor.owner] = self._turn_key()
        self._owed = (reactor, attacking_squad)
        if self.game_log:
            self.game_log.add(
                f"{reactor.name} uses Kroot Packmates and will shoot back at "
                f"{attacking_squad.name}.")
        return True

    def on_squad_finished_shooting(self, squad, hit_squads=None):
        """"after that enemy unit has finished making its attacks"."""
        if self._owed is None:
            return False
        reactor, attacker = self._owed
        if squad is not attacker:
            return False
        self._owed = None
        if self.shooting_controller is None:
            return False
        if not any(not m.is_dead() for m in reactor.models):
            return False  # the reaction died to the very attack it answered
        return self.shooting_controller.start_reactive_shooting(
            reactor, restrict_to=attacker)

    def reset_turn(self):
        """The ledger is keyed by turn, so nothing has to be cleared - but an
        owed reaction must not survive into the next turn."""
        self._owed = None
