""""Once per turn, when an enemy unit shoots a friendly unit near this one,
shoot back at it after it has finished."

THE 40TH EXTRACTION, at the SECOND consumer as the convention asks:

  Kroot Packmates          (T'au, Krootox Riders)     6"  KROOT INFANTRY
  Multi-threat Eliminator  (Necrons, Hexmark)         3"  NECRONS

Both print the same four-part trigger with two words changed, and both end in
the sentence Awakened Dynasty's Protocol of the Vengeful Stars prints as well:
"can shoot as if it were your Shooting phase, but ... can only target that
enemy unit". The tail is already shared - it is
ShootingController.start_reactive_shooting(restrict_to=...) - and this class is
the HEAD, which was not.

WHAT IS SHARED, and it is the part that is easy to get subtly wrong twice:

  * THE FOUR-PART TRIGGER'S SHAPE. "In your opponent's Shooting phase" means
    ShootingController.target_reactions, whose contract is
    `maybe_offer(attacking_squad, target_squad, melee=False)` - and getting
    THAT wrong is not hypothetical: KrootPackmatesController shipped with only
    a plural on_targets_selected() whose docstring claimed to be the contract,
    and every game died with an AttributeError the first time any unit picked a
    shooting target.
  * "AFTER THAT ENEMY UNIT HAS FINISHED MAKING ITS ATTACKS" - so the shot is
    OWED at the trigger and fired from on_squad_finished_shooting, which is
    what stops it interrupting the attack it answers.
  * "ONE UNIT/MODEL FROM YOUR ARMY WITH THIS ABILITY" - a once-per-TURN ledger
    keyed by PLAYER, not by squad, so two carriers share one use. Same reading
    My Will Be Done and War Leader take of the same sentence.
  * A reactor that DIED to the very attack it answered fires nothing.

WHAT EACH SUBCLASS OWNS is the five things the two cards actually differ in:
the profile flag, the range, which friendly units it protects, the label, and
the prompt wording. Those are set as class attributes plus one method, not
passed to a constructor, so a subclass that forgets one fails loudly at
definition rather than quietly at 0".

RANGE IS MEASURED MODEL TO MODEL on both sides, which is what both printed
texts say even though they say it differently: Kroot Packmates says "within 6"
of this unit" and Multi-threat Eliminator says "within 3" of a MODEL with this
ability". Any-model-to-any-model answers both - a unit is within X of another
exactly when some pair of their models is.

THE REACTOR IS A SQUAD, and Multi-threat Eliminator is the reason to write that
down: its text says "one MODEL with this ability ... can shoot", where its twin
says "that unit". A shooting activation in this engine is per SQUAD, and the
Hexmark Destroyer is a one-model unit that prints no LEADER line, so the two
readings cannot differ for either carrier today. A future carrier with several
models in one unit would make them differ, and would need a per-model
activation that does not exist yet - named here rather than left to be
discovered.
"""

from game import ai_mode
from game.squad import edge_distance


class ReactiveBodyguardShooting:
    """Subclass and set `flag`, `range_in`, `label`, plus `protects()`.

    Registered in BOTH ShootingController.target_reactions (the trigger) and
    ShootingController.on_squad_finished_shooting (the payoff)."""

    #: The UnitProfile attribute naming a carrier.
    flag = None
    #: The printed distance, in inches.
    range_in = 0.0
    #: The ability's printed name, for prompts and the log.
    label = "reactive shooting"

    def protects(self, squad):
        """Whether `squad` being shot at is a unit this ability answers for.

        The one genuinely per-card question: "a friendly KROOT INFANTRY unit"
        against "a friendly NECRONS unit"."""
        raise NotImplementedError

    def __init__(self, shooting_controller=None, decision_manager=None,
                 game_state=None, turn_tracker=None, game_log=None, auto_players=()):
        self.shooting_controller = shooting_controller
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._used_this_turn = {}   # player -> the turn key it was spent on
        self._owed = None           # (reacting squad, the enemy that shot)

    # -- eligibility ------------------------------------------------------

    def carries(self, squad):
        """A living model of `squad` with the ability."""
        if squad is None:
            return False
        return any(getattr(m.profile, self.flag, False)
                   for m in getattr(squad, "models", ()) or () if not m.is_dead())

    def _turn_key(self):
        tracker = self.turn_tracker
        if tracker is None:
            return None
        return (getattr(tracker, "battle_round", 0), getattr(tracker, "turn_owner", None))

    def available(self, player):
        """"Once per turn" - per ARMY, not per carrier."""
        return self._used_this_turn.get(player) != self._turn_key()

    def _squads(self):
        if self.game_state is None:
            return []
        return [t.squad for t in self.game_state.tokens if t.squad is not None]

    def within_range(self, squad, other):
        for mine in getattr(squad, "models", ()) or ():
            if mine.is_dead():
                continue
            for theirs in getattr(other, "models", ()) or ():
                if not theirs.is_dead() and edge_distance(mine, theirs) <= self.range_in:
                    return True
        return False

    def reactors_for(self, target_squad):
        """Friendly carriers that may react to `target_squad` being shot.

        `target_squad` must itself be a protected friendly unit within range -
        which is what makes this a bodyguard reaction rather than a
        self-defence one. Sorted by name so a replayed battle offers the same
        reactor; the token sweep behind it is insertion-ordered, not stable
        across a rebuild."""
        if target_squad is None or not self.protects(target_squad):
            return []
        seen = []
        for squad in self._squads():
            if squad in seen or squad.owner != target_squad.owner:
                continue
            if not self.carries(squad) or not self.available(squad.owner):
                continue
            if self.within_range(squad, target_squad):
                seen.append(squad)
        return sorted(seen, key=lambda s: s.name)

    # -- the reaction -----------------------------------------------------

    def prompt(self, reactor, attacking_squad, target_squad):
        return ("%s: %s - shoot back at %s after it finishes attacking %s?"
                % (reactor.name, self.label, attacking_squad.name, target_squad.name))

    def maybe_offer(self, attacking_squad, target_squad, melee=False):
        """ShootingController.target_reactions' ACTUAL contract - one target at
        a time plus a `melee` flag.

        Melee is declined outright: the printed WHEN is "your opponent's
        Shooting phase". Neither controller is registered in the fight tuple
        today, so the flag is never True - checked anyway rather than ignored,
        because the two tuples are one edit apart."""
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
                self.prompt(reactor, attacking_squad, target),
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
                "%s uses %s and will shoot back at %s."
                % (reactor.name, self.label, attacking_squad.name))
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
            return False  # the reactor died to the very attack it answered
        return self.shooting_controller.start_reactive_shooting(
            reactor, restrict_to=attacker)

    def reset_turn(self):
        """The ledger is keyed by turn, so nothing has to be cleared - but an
        owed reaction must not survive into the next turn."""
        self._owed = None
