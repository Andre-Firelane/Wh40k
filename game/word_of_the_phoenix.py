"""Yvraine's "Word of the Phoenix" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "While this model is leading a unit, in your Command phase, you can roll one
  D6: on a 2+, you can return up to D3+1 destroyed Bodyguard models to that
  unit (excluding SUPPORT WEAPON models). Those models are returned with their
  full wounds remaining."

THE SIXTH MODEL-RETURN, AND THE ONE WITH THE MOST WAYS TO GET IT WRONG
----------------------------------------------------------------------
game/model_return.py already owns the four halves of "back on the battlefield",
and formation_layout.returning_positions() already owns "where, without
breaking rule 09.02" - because these models go back INTO a standing unit, which
is Grot Orderly's problem and not Fuegan's. So neither of those is re-derived
here. What is genuinely new is the set of qualifiers, and all four of them are
restrictions, which means every single one of them widens the ability if it is
dropped:

  * "while this model is LEADING a unit" - 24.22 again. Yvraine alone returns
    nothing, and she is not returning herself.
  * "BODYGUARD models" - the models the unit had before she joined it, NOT the
    unit's whole death toll. attached_units records that provenance
    (19.02/19.04 need the starting composition anyway), so it is read from
    there rather than guessed at from what happens to be dead.
  * "excluding SUPPORT WEAPON models" - the SECOND reader of that clause after
    game/branching_fates.py, and finding it here is what showed that neither
    could fire: Etappe 2 put the SUPPORT WEAPON keyword on the three platform
    DATASHEETS but never on their profiles, so UnitProfile.support_weapon was
    False everywhere. It is set now. Whether a unit Yvraine leads can actually
    contain one is a separate question and the answer today is no - measured,
    not assumed - so the clause is a BELIEVED NO-OP on this roster, wired
    because it is printed rather than because it currently bites.
  * "up to D3+1" - TWO dice, and the second one is a CEILING rather than an
    amount. Fewer eligible corpses than the roll returns fewer models, and a
    model that finds nowhere legal to stand costs one model rather than the
    whole return - which is exactly what returning_positions() promises when it
    hands back None for a slot.

TWO ROLLS, TWO STEPS. The D6 gate and the D3+1 count are separate throws and
the second only happens if the first passes, so they cannot share one dice
window: DiceManager holds ONE roll at a time. The controller is therefore a
small two-state machine rather than a single call, the same arrangement
game/protocol_undying_legions.py uses for its gated D3+1.

THE AI ANSWERS IT ITSELF, so there is no path in ai/ and no API call: "you can
roll" is only ever declined when there is nothing to gain, and eligible_count()
already reports that, so an owner in auto_players takes it whenever it is worth
anything. A prompt nobody answers would stall the loop.
"""
from game import attached_units, model_return
from game.dice_notation import D3, DiceNotationRoll
from game.formation_layout import returning_positions

WORD_OF_THE_PHOENIX_LABEL = "Word of the Phoenix"

#: "on a 2+" - the gate roll.
WORD_OF_THE_PHOENIX_THRESHOLD = 2

#: "up to D3+1" - the count roll's flat bonus.
WORD_OF_THE_PHOENIX_BONUS = 1


def applies(squad):
    """"While this model is LEADING a unit" - so a lone Yvraine grants
    nothing, and no bodyguard carries it."""
    return bool(squad is not None
                and attached_units.leader_ability(squad, "word_of_the_phoenix"))


def eligible_models(squad):
    """The destroyed models this ability may bring back, in death order.

    "BODYGUARD models" is the load-bearing word. Under rule 19.01 attach()
    MERGES the leader into the squad, so Squad.destroyed_models holds everyone
    who has died in this unit - Yvraine and any other attached character
    included. The bodyguards are the models that came from the component that
    is not a leader, and attached_units keeps that provenance precisely because
    19.02 and 19.04 need the starting composition.

    "EXCLUDING SUPPORT WEAPON models" is filtered on top of that, and it is not
    decoration: a Guardian Defenders unit can field a D-cannon Platform."""
    if squad is None:
        return []
    dead = [m for m in (getattr(squad, "destroyed_models", ()) or ())]
    if not dead:
        return []
    bodyguards = _bodyguard_models(squad)
    out = []
    for model in dead:
        if getattr(model.profile, "support_weapon", False):
            continue
        if bodyguards is None:
            # Never attached, so there is no recorded provenance. "Bodyguard"
            # then means "not the leader", which is the honest reading of a
            # squad that was assembled by hand.
            if getattr(model.profile, "leader", False)                     or getattr(model.profile, "support", False):
                continue
        elif id(model) not in bodyguards:
            continue
        out.append(model)
    return out


def _bodyguard_models(squad):
    """The models that came from the BODYGUARD component, or None when this
    squad was never built by attach() (a hand-built test squad), in which case
    eligible_models() falls back to "everything that is not a leader".

    Read off AttachedComponent.role rather than by inspecting profiles: that
    field IS the provenance attach() records, and re-deriving it from what the
    models look like is the second opinion this module exists to avoid.
    starting_models is the right list because a bodyguard that is DEAD is
    exactly what this ability is asked about."""
    components = getattr(squad, "attached_components", None)
    if not components:
        return None
    ids = set()
    for component in components:
        if getattr(component, "is_leader_or_support", False):
            continue
        ids.update(id(m) for m in (getattr(component, "starting_models", None) or ()))
    return ids or None


def eligible_count(squad):
    return len(eligible_models(squad))


def can_use(squad):
    """Never offered when it would return nothing - error class 5, and the
    reason the count is checked before the D6 rather than after it: rolling a
    die that cannot pay anything looks like a bug from the table."""
    return applies(squad) and eligible_count(squad) > 0


class WordOfThePhoenixController:
    """The two-roll Command phase step."""

    def __init__(self, dice_manager=None, game_state=None, game_log=None,
                 setup_controller=None, all_tokens=None, decision_manager=None,
                 auto_players=()):
        self.dice_manager = dice_manager
        self.game_state = game_state
        self.game_log = game_log
        self.setup_controller = setup_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.decision_manager = decision_manager
        self.auto_players = set(auto_players)
        #: The squad whose gate roll is on the table, if any.
        self.pending_squad = None
        #: The D3+1 count roll, once the gate has passed.
        self._count_roll = None
        self._returning_squad = None

    @property
    def is_busy(self):
        return (self.pending_squad is not None or self._count_roll is not None
                or self._returning_squad is not None)

    def can_use(self, squad):
        return can_use(squad)

    # ------------------------------------------------------------ the rolls

    def start(self, squad):
        """Throws the 2+ gate."""
        if not self.can_use(squad) or self.dice_manager is None:
            return False
        self.pending_squad = squad
        self.dice_manager.roll(
            1,
            label="%s (%s)" % (WORD_OF_THE_PHOENIX_LABEL, squad.name),
            roll_kind="ability",
            success_threshold=WORD_OF_THE_PHOENIX_THRESHOLD,
            target_squad=squad,
            subject_label="Reviving",
        )
        return True

    def on_dice_acknowledged(self):
        """Reads the gate roll and, on a 2+, throws the D3 for the count.

        TWO acknowledgements, therefore two visits, and the order matters: the
        count roll is drained FIRST, because by the time it is on the table the
        gate roll is long gone and a single combined branch would read the D3
        as if it were the D6."""
        if self._count_roll is not None:
            self._count_roll.on_dice_acknowledged()
            if self._count_roll.done:
                total, self._count_roll = self._count_roll.total, None
                squad, self._returning_squad = self._returning_squad, None
                self.return_models(squad, total + WORD_OF_THE_PHOENIX_BONUS)
            return True
        squad, self.pending_squad = self.pending_squad, None
        if squad is None or self.dice_manager is None:
            return False
        values = list(getattr(self.dice_manager, "last_values", ()) or ())
        if not values or values[0] < WORD_OF_THE_PHOENIX_THRESHOLD:
            if self.game_log is not None:
                self.game_log.add("%s: %s - rolled %s, the dead stay dead."
                                  % (WORD_OF_THE_PHOENIX_LABEL, squad.name,
                                     values[0] if values else "nothing"))
            return False
        return self._roll_count(squad)

    def _roll_count(self, squad):
        """"up to D3+1". The bonus is added to the TOTAL rather than rolled,
        which is what "D3+1" means and what keeps the die itself a plain D3 for
        anything that later wants to change the result of that roll."""
        self._returning_squad = squad
        self._count_roll = DiceNotationRoll(
            D3(), count=1, dice_manager=self.dice_manager,
            label="%s: %s - how many return (D3+%d)"
                  % (WORD_OF_THE_PHOENIX_LABEL, squad.name, WORD_OF_THE_PHOENIX_BONUS),
            log=(self.game_log.add if self.game_log is not None else None),
        )
        if self._count_roll.done:               # no dice_manager (tests)
            total, self._count_roll = self._count_roll.total, None
            self._returning_squad = None
            self.return_models(squad, total + WORD_OF_THE_PHOENIX_BONUS)
        return True

    # --------------------------------------------------------- the returns

    def return_models(self, squad, count):
        """"Up to D3+1 ... with their full wounds remaining".

        The count is a CEILING three times over: by the roll, by how many
        eligible corpses there are, and by how many of them find a legal spot.
        Placement failure costs that one model, never the whole return - the
        contract returning_positions() states."""
        candidates = eligible_models(squad)[:max(0, count)]
        if not candidates:
            return 0
        position_valid = None
        if self.setup_controller is not None:
            position_valid = self.setup_controller.position_valid
        spots = returning_positions(squad, candidates, position_valid=position_valid)
        enemies = model_return.enemy_tokens(candidates[0], self.all_tokens)
        returned = 0
        for model, spot in zip(candidates, spots):
            if spot is None:
                continue
            x_in, y_in = spot
            # position_valid() deliberately does NOT check Engagement Range -
            # its own docstring says so - and a model set up in combat is the
            # mistake that once cost a whole unit in the Emergency Disembark.
            if not model_return.clear_of_engagement(model, x_in, y_in, enemies):
                continue
            # wounds=None is "its full wounds", which is what this rule prints.
            model_return.set_up_model(model, (x_in, y_in), game_state=self.game_state)
            returned += 1
        if self.game_log is not None:
            self.game_log.add(
                "%s: %d model%s return%s to %s with full wounds (rolled %d)."
                % (WORD_OF_THE_PHOENIX_LABEL, returned,
                   "" if returned == 1 else "s",
                   "s" if returned == 1 else "", squad.name, count))
        return returned
