"""T'au Strike Team ability: Suppression Volley, as supplied by the user
(datasheet-specific, not a rule from the generic 40k core rulebook).

RULE: In your Shooting phase, after this unit has shot, select one enemy
INFANTRY unit hit by one or more of those attacks. Until the start of your
next turn, while this unit is on the battlefield, that enemy unit is
suppressed. While a unit is suppressed, each time a model in that unit
makes an attack, subtract 1 from the Hit roll.

"Subtract 1 from the Hit roll" is modeled as a +1 to the hit THRESHOLD -
this engine's existing convention for "X to the hit roll" phrasing (see
rule 24.16's [HEAVY], the "add 1 to the hit roll" precedent handled the
same way in shooting.py/fight.py's own _hit_modifiers()) - not an actual
change to the rolled die value, so it correctly leaves the "natural 1
always fails, natural 6 always critical" rule (05.01) untouched, exactly
like every other hit-roll modifier already in this engine.

Applies to BOTH ranged and melee attacks ("each time a model in that unit
makes an attack" - no "ranged" qualifier, unlike e.g. Retaliation Cadre's
Bonded Heroes) - see ShootingController/FightController's own
_hit_modifiers() for where this is actually consumed.

TWO ABILITIES APPLY THIS STATUS, and they differ in two printed clauses:

  SUPPRESSION VOLLEY (T'au Strike Team)  "one enemy INFANTRY unit hit ...
      while THIS UNIT IS ON THE BATTLEFIELD, that enemy unit is suppressed"
  HARASSMENT FIRE (Aeldari Vypers)       "one enemy unit hit ... until the
      start of your next turn, that enemy unit is suppressed"

So Harassment Fire has no INFANTRY restriction and no "while the source
survives" clause - a Vyper squadron that is wiped out leaves its suppression
standing, where a dead Strike Team's lifts. Both are stored in the SAME ledger
because "is this unit suppressed" must have one answer that the two
_hit_modifiers() read once; what differs is recorded per ENTRY, not per
controller. Adding a second controller would mean the hit step asking twice
and the two disagreeing the first time one of them was forgotten."""

from game.squad import squad_has_suppression_volley


HARASSMENT_FIRE_LABEL = "Harassment Fire"


def unit_has_harassment_fire(squad):
    """The Vypers' flag, read live off the living models."""
    if squad is None:
        return False
    return any(getattr(m.profile, "harassment_fire", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def _is_infantry_unit(squad):
    """"Enemy INFANTRY unit" - any() rather than all(), the same convention
    shooting.py's _unit_has_keyword() uses for keyword-presence checks
    (rule 19.03: an attached unit has the keywords of all its component
    units)."""
    return any(m.profile.infantry for m in squad.models)


class SuppressionController:
    def __init__(self, all_tokens=None, turn_tracker=None, decision_manager=None, game_log=None):
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        # enemy Squad -> (source Squad, applying player, turn_number_for(applying
        # player) when applied, requires_source_on_battlefield). The last field is
        # the printed difference between the two abilities that write here.
        self.suppressed = {}

    def _is_on_battlefield(self, squad):
        """"While this unit is on the battlefield" - the source unit's
        models must still be present in state.tokens (destroyed, embarked,
        or returned-to-reserves squads all fail this)."""
        return any(t.squad is squad for t in self.all_tokens)

    def is_suppressed(self, squad):
        if squad is None:
            return False
        entry = self.suppressed.get(squad)
        if entry is None:
            return False
        source_squad, applying_player, applied_turn, requires_source = entry
        if requires_source and not self._is_on_battlefield(source_squad):
            del self.suppressed[squad]
            return False
        if self.turn_tracker is not None and self.turn_tracker.turn_number_for(applying_player) > applied_turn:
            del self.suppressed[squad]
            return False
        return True

    def offer_after_shooting(self, squad, hit_squads):
        """Called once a Suppression-Volley-capable unit finishes its OWN
        Shooting-phase activation (see ShootingController.
        on_squad_finished_shooting, wired in main.py) - `hit_squads` is
        every enemy unit hit by one or more of its attacks this activation,
        of any keyword; only INFANTRY ones are eligible here. Auto-picks
        the sole eligible target (no DecisionManager call) the same way
        e.g. ExplosivesController does for a single qualifying model/target -
        a real choice only exists with 2+ candidates."""
        if not squad_has_suppression_volley(squad):
            return
        targets = sorted((s for s in hit_squads if _is_infantry_unit(s)), key=lambda s: s.name)
        if not targets:
            return
        if len(targets) == 1 or self.decision_manager is None:
            self._suppress(squad, targets[0])
            return
        options = [(f"Suppress {t.name}", lambda t=t: self._suppress(squad, t)) for t in targets]
        self.decision_manager.request(
            squad.owner, f"{squad.name}: Suppression Volley - which enemy INFANTRY unit becomes suppressed?", options,
        )

    def _suppress(self, source_squad, target_squad, requires_source=True,
                  label="Suppression Volley"):
        turn_number = self.turn_tracker.turn_number_for(source_squad.owner) if self.turn_tracker is not None else 0
        self.suppressed[target_squad] = (
            source_squad, source_squad.owner, turn_number, requires_source)
        if self.game_log is not None:
            self.game_log.add(
                f"{source_squad.owner}: {target_squad.name} is suppressed by {source_squad.name} ({label})."
            )

    # --- the Vypers' Harassment Fire -------------------------------------

    def offer_harassment_fire(self, squad, hit_squads):
        """The Vypers' own ability, writing the SAME status.

        "In your Shooting phase, after this unit has shot, select one enemy
        unit hit by one or more of those attacks. Until the start of your next
        turn, that enemy unit is suppressed."

        No INFANTRY filter (any hit unit is eligible) and no "while this unit
        is on the battlefield" clause - so it is applied with
        requires_source=False and outlives its Vypers."""
        if not unit_has_harassment_fire(squad):
            return
        targets = sorted(hit_squads, key=lambda s: s.name)
        if not targets:
            return
        if len(targets) == 1 or self.decision_manager is None:
            self._suppress(squad, targets[0], requires_source=False,
                           label=HARASSMENT_FIRE_LABEL)
            return
        options = [(f"Suppress {t.name}",
                    lambda t=t: self._suppress(squad, t, requires_source=False,
                                               label=HARASSMENT_FIRE_LABEL))
                   for t in targets]
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: {HARASSMENT_FIRE_LABEL} - which enemy unit becomes suppressed?",
            options,
        )
