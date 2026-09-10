"""The NECRONS army rule, Reanimation Protocols.

RULE (printed, word for word):
  "If your Army Faction is NECRONS, at the end of your Command phase, each
   friendly unit with this ability that is on the battlefield activates its
   Reanimation Protocols: When a unit's Reanimation Protocols activate, that
   unit heals D3 wounds."

THE DATASHEET IS ONLY HALF THE RULE. What "heals D3 wounds" actually does is
defined in the core rules, and it is the interesting half:

  02.02.04 Healing Or Regaining Lost Wounds - per wound healed: "If that unit
  has one or more models that does not have its full wounds remaining, select
  one of those models; that model regains one lost wound." Once every living
  model is at full wounds and one or more models are destroyed, "revive one of
  those destroyed models (excluding CHARACTER models), with one wound
  remaining."

  01.02.03 Revived and Adding Models to a Unit - revived models come back with
  their original equipment, "This cannot expand a unit beyond its starting
  strength", they must be set up in coherency with the models that started the
  phase on the battlefield, and they may only be set up engaged with enemy
  units that were ALREADY engaged with the unit they rejoin.

Two consequences worth stating because they are easy to get backwards:

  * HEALING COMES FIRST, ALWAYS. A unit with one wounded model and four dead
    ones spends its first wound topping the wounded model up, not raising a
    corpse. That is why reanimate() below drains the damaged models to full
    before it looks at destroyed_models at all.
  * THE CHARACTER EXCLUSION IS WHY A STRATAGEM EXISTS. Awakened Dynasty's
    "Protocol of the Eternal Revenant" is the only way a Necron CHARACTER
    comes back, precisely because 02.02.04 refuses to revive one.

WHY THIS ISN'T grot_orderly.py WITH A DIFFERENT NAME. Grot Orderly returns
models to ONE unit, once per battle, as a visible one-off. This is the army
rule: every unit, every Command phase, for the whole game. That is what makes
the controller below a QUEUE rather than a single pending slot - and, on the
user's explicit instruction, each unit gets its OWN labelled roll rather than
one pooled handful of dice, because that is what the printed text describes.

The four-part "put the model back" sequence and the Engagement Range test are
NOT here - they are shared with three other abilities and live in
game/model_return.py.
"""

from game import ai_mode, model_return
from game.formation_layout import returning_positions
from game.squad import ENGAGEMENT_RANGE_IN

REANIMATION_DICE_SIDES = 3          # "heals D3 wounds"
RESURRECTION_ORB_DICE_SIDES = 6     # the Overlord's orb heals D6 instead - rule text on his datasheet
REANIMATION_REROLL_FLOOR = 2        # Necron Warriors re-roll a result below this; see should_reroll()


def has_reanimation_protocols(squad):
    """True when any surviving model of this unit prints the army rule.

    Read LIVE off the models rather than baked on at build time, for the reason
    game/pulse_accelerator.py gives: an attached unit (19.01) is a merge, and
    the answer has to follow whoever is actually still standing."""
    return any(getattr(m.profile, "reanimation_protocols", False)
               for m in getattr(squad, "models", ()) or ())


def _alive(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def revivable_models(squad):
    """The destroyed models this unit is allowed to bring back, oldest
    destruction first.

    Two filters, both printed: CHARACTER models are excluded by 02.02.04, and
    01.02.03's "cannot expand a unit beyond its starting strength" caps how
    many of them may actually stand up again."""
    room = max(0, getattr(squad, "starting_model_count", 0) - len(_alive(squad)))
    if room <= 0:
        return []
    candidates = [m for m in getattr(squad, "destroyed_models", ()) or ()
                  if not getattr(m.profile, "character", False)]
    return candidates[:room]


def recoverable_wounds(squad):
    """How many reanimated wounds this unit could still turn into something.

    The shared gate: the Resurrection Orb, Protocol of the Undying Legions and
    every deterministic AI verdict all ask this one question rather than each
    re-deriving it, so they cannot drift apart. A unit at full strength and
    full health returns 0, which is exactly "rolling for this one is wasted"."""
    missing = sum(max(0, m.profile.wounds - m.current_wounds) for m in _alive(squad))
    return missing + sum(m.profile.wounds for m in revivable_models(squad))


def can_reroll(squad, rolled):
    """Whether the Necron Warriors re-roll is available AT ALL - the printed
    permission, plus the one case where taking it would buy literally nothing.

    "You can re-roll the dice to see how many wounds are reanimated" is
    UNCONDITIONAL: the unit either has the ability or it does not. So the only
    thing filtered here is inertness - a unit that can use just one more wound
    gains nothing from a better roll, whatever it rolled, and offering that is
    the "never offer what buys nothing" mistake this repo keeps out
    (Fehlerklasse 5).

    WHAT IS DELIBERATELY NOT HERE is whether the re-roll is a good IDEA. That
    is should_reroll() below, and it is the AI's policy - see there."""
    if not any(getattr(m.profile, "reanimation_reroll", False) for m in _alive(squad)):
        return False
    if rolled >= REANIMATION_DICE_SIDES:
        return False        # already the best the die can do
    return recoverable_wounds(squad) >= REANIMATION_REROLL_FLOOR


def should_reroll(squad, rolled):
    """Whether the AI takes the re-roll. ITS POLICY, NOT THE RULE.

    Re-roll a 1 and nothing else. A D3 averages 2, so re-rolling a 2 wins
    nothing on average and risks losing a wound; re-rolling a 1 can only help.

    THIS USED TO GATE THE HUMAN'S PROMPT TOO, and that was the bug (user: "die
    KI soll das zwar deterministisch anwenden, aber die Funktion selbst soll
    nicht deterministisch sein"). A human who rolled a 2 was never offered the
    re-roll at all, because the engine had already decided for them that it was
    not worth it. "Is this a good idea" is exactly the kind of judgement that
    belongs to whoever is playing the unit; the rule's own permission is
    can_reroll() above, and that is what the offer is gated on now."""
    return can_reroll(squad, rolled) and rolled < REANIMATION_REROLL_FLOOR


def _engaged_enemy_squads(squad, all_tokens):
    """The enemy UNITS already within Engagement Range of this one.

    01.02.03 permits a returning model to be set up engaged only with enemies
    that were already engaged with its unit, and it says UNITS - so this is a
    set of squads, not of models."""
    engaged = set()
    for token in all_tokens:
        other = getattr(token, "squad", None)
        if other is None or other is squad or other.owner == squad.owner or token.is_dead():
            continue
        for mine in _alive(squad):
            gap = (((token.x_in - mine.x_in) ** 2 + (token.y_in - mine.y_in) ** 2) ** 0.5
                   - token.radius_in - mine.radius_in)
            if gap <= ENGAGEMENT_RANGE_IN:
                engaged.add(id(other))
                break
    return engaged


def placement_validator(squad, all_tokens=(), position_valid=None):
    """The `position_valid` returning_positions() should be handed.

    Two conditions, and the second is the one SetupController.position_valid()
    explicitly does not cover: terrain/board legality, AND 01.02.03's
    engagement clause - clear of every enemy unit that was not already fighting
    this one. Getting that wrong would let a wiped-out squad reanimate directly
    into a combat it was never part of."""
    tokens = list(all_tokens or ())
    already = _engaged_enemy_squads(squad, tokens)
    forbidden = [t for t in tokens
                 if getattr(t, "squad", None) is not None
                 and t.squad.owner != squad.owner
                 and not t.is_dead()
                 and id(t.squad) not in already]

    def _valid(model, x_in, y_in):
        if position_valid is not None and not position_valid(model, x_in, y_in):
            return False
        return model_return.clear_of_engagement(model, x_in, y_in, forbidden)

    return _valid


def reanimate(squad, wounds, all_tokens=(), position_valid=None, game_state=None,
              placer=None, on_placed=None):
    """Spend `wounds` reanimated wounds on `squad`, per 02.02.04 + 01.02.03.

    Returns (wounds_spent, revived_models). `wounds_spent` can be less than
    `wounds` - a unit simply may not have that much to recover, and a model
    with nowhere legal to stand does not come back at all. Both are legal
    outcomes of the printed rule, and the surplus is lost rather than banked.

    `placer`, if given, is a ReturnPlacementController: rule 01.02.03 says a
    returning model is SET UP, and setting up is the controlling player's job.
    With one, a HUMAN gets the engine's spots as a starting point and drags
    from there; an owner in its auto_players lands on them outright, which is
    what this did for everyone. None keeps that older path for every caller
    that has not been handed one.
    """
    remaining = max(0, int(wounds))
    spent = 0

    # 02.02.04, first clause: every living model back to full before anything
    # is revived. One wound at a time to the model that has lost the most, so
    # the unit never carries a nearly-dead model it could have topped up.
    while remaining > 0:
        damaged = [m for m in _alive(squad) if m.current_wounds < m.profile.wounds]
        if not damaged:
            break
        target = min(damaged, key=lambda m: (m.current_wounds, m.profile.name))
        target.current_wounds += 1
        remaining -= 1
        spent += 1

    if remaining <= 0:
        return spent, []

    # 02.02.04, second clause: revive with ONE wound, then keep healing that
    # model with whatever is left before moving to the next corpse.
    plan = []
    for model in revivable_models(squad):
        if remaining <= 0:
            break
        give = min(model.profile.wounds, remaining)
        plan.append((model, give))
        remaining -= give
    if not plan:
        return spent, []

    valid = placement_validator(squad, all_tokens, position_valid)
    spots = returning_positions(squad, [m for m, _ in plan], position_valid=valid)

    if placer is not None:
        # The spots become a STARTING POINT rather than the answer. Only the
        # models that found one are handed over; a model with nowhere legal to
        # stand still stays down, so nobody is asked to place something the
        # rule did not return.
        revived = placer.place(
            squad,
            [model for model, _give in plan],
            spots,
            wounds=[give for _model, give in plan],
            validator=valid,
            # Fires when the placement is CONFIRMED (or cancelled, with an
            # empty list) - which for a human is frames later. The army rule
            # uses it to hold its queue; every other caller passes None and
            # is unaffected.
            on_done=on_placed,
        )
        spent += sum(give for (model, give) in plan if model in revived)
        return spent, revived

    revived = []
    for (model, give), spot in zip(plan, spots):
        if spot is None:
            continue  # nowhere legal to stand - that model stays down, wounds lost
        model_return.set_up_model(model, spot, wounds=give, game_state=game_state)
        revived.append(model)
        spent += give
    return spent, revived


class ReanimationProtocolsController:
    """Runs the army rule at the end of its owner's Command phase.

    A QUEUE, not a single pending slot, and that is the whole difference from
    game/grot_orderly.py: this fires for EVERY unit with the ability, every
    Command phase, so the controller has to hold a list of units still owed a
    roll and walk it one acknowledgement at a time.

    One labelled roll per unit, on the user's explicit instruction - the
    alternative considered was a single pooled handful of D3s, which would be
    one confirmation instead of a dozen but does not read like the printed
    text.

    ONLY UNITS THAT HAVE ACTUALLY TAKEN DAMAGE ROLL - user instruction, after
    seeing it in play: "reanimationsprotokolle bitte nur triggern, wenn die
    Einheit auch schon Schaden erlitten hat. Jetzt feuert das jedes Mal auch am
    Anfang." An undamaged, full-strength unit has nothing a D3 could restore,
    so its roll was pure ceremony - thirteen confirmations on turn one, every
    one of them provably inconsequential.

    THIS CHANGES NO OUTCOME, only what the player is asked to confirm. The
    skipped roll is exactly the roll whose result reanimate() would have spent
    on nothing: recoverable_wounds() returns 0 precisely when there are no
    missing wounds and no revivable models, and reanimate() called with any
    number in that state returns (0, []). So the rule still "activates" for
    every unit in the sense that matters - it simply does not stop the game to
    show a die that cannot do anything.
    """

    #: When True, a unit that cannot recover anything is skipped instead of
    #: rolling a die whose result provably does nothing. False follows the
    #: printed text literally ("each friendly unit with this ability") and was
    #: the original behaviour; see the class docstring for why it changed.
    UNITS_MUST_HAVE_SOMETHING_TO_GAIN = True

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, position_valid=None, auto_players=(),
                 placer=None):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        # position_valid(model, x, y) -> bool; main.py passes SetupController's
        # own predicate, so "somewhere legal" means what it means everywhere
        # else. The Engagement Range half is added by placement_validator().
        self.position_valid = position_valid
        self.auto_players = ai_mode.players(auto_players)
        # ReturnPlacementController - rule 01.02.03's "set up" half. Optional,
        # so a test or a headless harness that does not hand one over keeps the
        # engine-picked positions this always used.
        self.placer = placer
        self._queue = []            # squads still owed a roll this Command phase
        self._current = None        # the squad whose die is on the table
        self._reroll_offered = False
        # The Canoptek boosts, optional like every other collaborator here -
        # None means the army rule reanimates exactly what it rolled, which is
        # what every caller before this batch meant.
        self.boost = None
        # True only while reanimate() is running, so the placer's
        # synchronous on_done (the AI path) cannot advance the queue
        # from inside _apply(). See _resume_queue().
        self._applying = False

    # ---------------------------------------------------------------- state

    @property
    def is_busy(self):
        return self._current is not None or bool(self._queue)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    # ----------------------------------------------------------- conditions

    def can_activate(self, squad, player=None):
        """"each friendly unit with this ability that is on the battlefield".

        Embarked units are excluded because they are not on the battlefield -
        the same test rule 18.x makes everywhere else in this engine."""
        if squad is None or not has_reanimation_protocols(squad):
            return False
        if player is not None and squad.owner != player:
            return False
        if getattr(squad, "embarked_in", None) is not None:
            return False
        if not _alive(squad):
            return False  # a wiped-out unit is not on the battlefield to activate
        if self.UNITS_MUST_HAVE_SOMETHING_TO_GAIN and recoverable_wounds(squad) <= 0:
            return False
        return True

    def eligible_squads(self, squads, player=None):
        return [s for s in squads if self.can_activate(s, player)]

    # ------------------------------------------------------------ the cycle

    def begin_command_phase(self, squads, player):
        """"at the end of your Command phase". Fills the queue in a fixed
        order and starts the first roll. Returns True if anything was queued.

        Sorted by name so a replay and a test see the same order - the units
        are independent of one another, but a non-deterministic order would
        make a failure hard to reproduce."""
        if self.is_busy:
            return False
        self._queue = sorted(self.eligible_squads(squads, player), key=lambda s: s.name)
        if not self._queue:
            return False
        return self._roll_next()

    def _roll_next(self):
        while self._queue:
            squad = self._queue.pop(0)
            if not self.can_activate(squad, squad.owner):
                continue  # something killed it while the queue was draining
            self._current = squad
            self._reroll_offered = False
            self._roll(squad, is_reroll=False)
            return True
        self._current = None
        return False

    def _roll(self, squad, is_reroll=False):
        if self.dice_manager is None:
            return
        label = "Reanimation Protocols"
        if is_reroll:
            label += " (re-roll)"
        # Labelled, and carrying the unit itself so the dice panel can show its
        # portrait and name the unit that is reanimating rather than a "Target".
        self.dice_manager.roll(
            1, REANIMATION_DICE_SIDES, label=label,
            target_name=squad.name, target_squad=squad,
            subject_label="Reanimating", is_reroll=is_reroll)

    def on_dice_acknowledged(self):
        """Applies the current unit's roll, then moves to the next.

        The Necron Warriors re-roll is offered BEFORE the result is applied,
        as a fresh visible roll flagged is_reroll - which is also what stops a
        die being re-rolled twice, since that flag fills DiceManager's
        already_rerolled set."""
        if self._current is None:
            return False
        squad = self._current
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or [1]
        rolled = values[0]

        # OFFERED on the printed permission, DECIDED on the AI's policy. The
        # gate used to be should_reroll() for both, so a human who rolled a 2
        # or a 3 never saw the option - the engine answered a judgement call on
        # their behalf. can_reroll() is the rule; should_reroll() is now only
        # consulted inside the auto branch.
        if not self._reroll_offered and can_reroll(squad, rolled):
            self._reroll_offered = True
            if squad.owner in self.auto_players or self.decision_manager is None:
                if not should_reroll(squad, rolled):
                    self._apply_and_advance(squad, rolled)
                    return True
                self._log(f"[reanimation] {squad.name}: rolled a {rolled}, re-rolling it.",
                          file_only=True)
                self._roll(squad, is_reroll=True)
                return True
            self.decision_manager.request(
                squad.owner,
                f"{squad.name} reanimates {rolled} wound(s). Re-roll that dice?",
                [("Re-roll", lambda: self._roll(squad, is_reroll=True)),
                 ("Keep it", lambda: self._apply_and_advance(squad, rolled))],
            )
            return True

        self._apply_and_advance(squad, rolled)
        return True

    def _apply_and_advance(self, squad, rolled):
        """Apply, then move on - but NOT while the human is still placing.

        Before this guard, _apply() opened the placement and _roll_next() put
        the NEXT unit's dice on the table in the same call stack. Acknowledging
        that die ran _apply() for unit two while unit one was still PLACING, so
        can_start_setup() said no and unit two's models were seated by the
        engine. Measured: two damaged human units, both reanimated, the
        placement opened for the FIRST one twice.
        """
        self._apply(squad, rolled)
        if self.placer is not None and self.placer.is_busy:
            return          # _resume_queue() picks it up when the human is done
        self._roll_next()

    def _resume_queue(self, _models=None):
        """The placer's on_done. Rolls the next unit once the board is free.

        RE-ENTRANCY: on the AI / no-flow path place() calls on_done
        SYNCHRONOUSLY from inside _apply(), so without the latch the queue
        would advance twice - once here and once from _apply_and_advance()'s
        tail. Fehlerklasse 9b, and it is why the latch is explicit rather than
        inferred from placer.is_busy.
        """
        if self._applying:
            return
        self._roll_next()

    def _apply(self, squad, rolled):
        self._current = None
        # The two Canoptek boosts - the Reanimator's aura (+D3) and the
        # Macrocytes' Nanoscarab Projector (+1). Added to the wound count
        # BEFORE it is spent, never afterwards: 01.02.03's Starting Strength
        # cap and 02.02.04's heal-then-revive order both operate on the TOTAL,
        # so a wound handed over after the fact would be spent under different
        # rules than the ones that granted it.
        #
        # ONLY THIS DOOR. reanimate() has three callers (this army rule,
        # Protocol of the Undying Legions and the Resurrection Orb), and the
        # printed boost says "each time that unit's REANIMATION PROTOCOLS
        # activate" - which is this one. See game/reanimation_boost.py.
        boosted = rolled
        if self.boost is not None:
            boosted += self.boost.extra_wounds(
                squad, self._tokens(), log=self._log)
        self._applying = True
        try:
            spent, revived = reanimate(
                squad, boosted,
                all_tokens=self._tokens(),
                position_valid=self.position_valid,
                game_state=self.game_state,
                placer=self.placer,
                on_placed=self._resume_queue,
            )
        finally:
            self._applying = False
        if not spent:
            self._log(f"[reanimation] {squad.name}: rolled a {rolled}, nothing to recover.",
                      file_only=True)
            return
        detail = f"{spent} wound(s)"
        if revived:
            detail += f", {len(revived)} model(s) back on the battlefield"
        self._log(f"Reanimation Protocols ({squad.name}): rolled a {rolled} - reanimated {detail}.")
