"""The Cryptothralls' three printed rules (Necrons).

RULES (printed, word for word):

  BOUND CREATION: "While this unit is in the same unit as a CRYPTEK model,
    that CRYPTEK model has the Feel No Pain 4+ ability."

  SYSTEMATIC VIGOUR: "Each time a CRYPTOTHRALL model in this unit is destroyed
    by a melee attack, if that model has not fought this phase, roll one D6:
    on a 2+, do not remove it from play. The destroyed model can fight after
    the attacking model's unit has finished making its attacks, and it is then
    removed from play."

  CRYPTEK RETINUE: "At the start of the Declare Battle Formations step, this
    unit can join one other unit from your army that is being led by a CRYPTEK
    INFANTRY model (a unit cannot have more than one CRYPTOTHRALLS unit joined
    to it). If it does, until the end of the battle, every model in this unit
    counts as being part of that Bodyguard unit, and that Bodyguard unit's
    Starting Strength is increased accordingly."

BOUND CREATION POINTS BODYGUARD -> LEADER, which is the SECOND of that shape
here and not the first: Death Guard's Silent Bodyguard (game/silent_bodyguard.py)
is printed on the Deathshroud Terminators and protects the character leading
them. So this is one more fold in feel_no_pain.current_feel_no_pain(), and it
returns a threshold STRING with "-" for none, exactly as that one does.

WHERE THE TWO DIFFER, and it is not decoration:
  * Silent Bodyguard requires EVERY surviving bodyguard to print it, and picks
    out "the CHARACTER model leading this unit".
  * Bound Creation asks only that a Cryptothrall is in the unit at all ("while
    this unit is in the same unit as"), and names "that CRYPTEK MODEL" - not
    the leader, and not the unit. So it is a per-MODEL question keyed on the
    CRYPTEK keyword: in Necron Warriors led by a Technomancer and joined by
    Cryptothralls, the Technomancer gets the 4+ and the twenty Warriors do
    not - and neither do the Cryptothralls themselves.

SYSTEMATIC VIGOUR IS THE THIRD CONSUMER of game/fight_after_death.py, after
Death Guard's Undying Spite (4+) and Aspect Host's Malevolent Souls (3+). Same
ledger, same "kept on the board, owed an activation" bookkeeping; only the
threshold (2+) and the eligibility differ, and the eligibility is the rule's
own business, which is why that class takes the models rather than deciding
them.

  ITS EXTRA CLAUSE: "if that model has not fought this phase". Neither of the
  two earlier rules prints one, so it is checked here rather than folded into
  the shared class - a model that already swung does not get to swing again.

CRYPTEK RETINUE IS A THIRD ATTACHMENT FORM, and the only one in this engine
where a whole non-character UNIT joins a bodyguard unit. Almost all of it was
already built:

  * attached_units.attach() merges models, sums points AND sums
    starting_model_count from the components - which is exactly the printed
    "that Bodyguard unit's Starting Strength is increased accordingly", and it
    matters far beyond bookkeeping: starting_model_count is what 01.02.03 caps
    Reanimation Protocols at and what Below Half-strength reads.
  * pregame.py's JOIN destination and its resolution loop are generic - they
    call attach() and nothing about SUPPORT WEAPON.
  * 19.01's one-unit-per-ROLE check gives the printed "a unit cannot have more
    than one CRYPTOTHRALLS unit joined to it" for free, which is why RETINUE is
    its own role rather than a second kind of SUPPORT.

What is added here is the one condition none of that knows: the host must be
"being led by a CRYPTEK INFANTRY model". Kept out of can_attach() on purpose -
that function owns rule 19.01 and has no business knowing what a Cryptek is;
this is a condition of the Declare Battle Formations STEP, the same split
game/formations.py's support_join_errors() already draws for Support Artillery.
"""

from game.attached_units import (RETINUE, attachment_role, can_attach,
                                 components, leader_components)
from game.fight_after_death import FightAfterDeath
from game.turn import PHASE_FIGHT

#: "roll one D6: on a 2+".
SYSTEMATIC_VIGOUR_THRESHOLD = 2
SYSTEMATIC_VIGOUR_LABEL = "Systematic Vigour"

#: "that CRYPTEK model has the Feel No Pain 4+ ability".
BOUND_CREATION_FEEL_NO_PAIN = "4+"

CRYPTEK_KEYWORD = "CRYPTEK"
#: Both words of "a CRYPTEK INFANTRY model" are checked - the phrase names two
#: keywords, and every Cryptek here is INFANTRY today, so the second half is a
#: measured no-op that is written anyway rather than assumed away.
INFANTRY_KEYWORD = "INFANTRY"


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def is_cryptothrall(model):
    return bool(getattr(model, "profile", None)
                and getattr(model.profile, "systematic_vigour", False))


def unit_has_cryptothralls(squad):
    """Any living Cryptothrall in the unit - the subject of Bound Creation is
    "while this unit is in the SAME UNIT as", so it is asked after 19.01 has
    merged them."""
    return squad is not None and any(is_cryptothrall(m) for m in _living(squad))


# --------------------------------------------------------------- Bound Creation

def bound_creation_feel_no_pain(model):
    """This model's Feel No Pain threshold from Bound Creation, or "-".

    Returns a threshold STRING, matching UnitProfile.feel_no_pain's own
    convention, so current_feel_no_pain() folds it like every other source.

    Read per MODEL because the printed subject is "that CRYPTEK model", not
    the unit: in a Necron Warriors squad led by a Technomancer and joined by
    Cryptothralls, the Technomancer gets it and the twenty Warriors do not.

    A model is a CRYPTEK by its DATASHEET keyword line, which is where the
    word is printed - the same route game/titanic.py and Spirit Conclave's
    clauses take, and the one that keeps working for a datasheet added without
    someone remembering a profile flag."""
    if model is None:
        return "-"
    squad = getattr(model, "squad", None)
    if not unit_has_cryptothralls(squad):
        return "-"
    if not _model_is_cryptek(model, squad):
        return "-"
    return BOUND_CREATION_FEEL_NO_PAIN


def _model_is_cryptek(model, squad):
    """Whether THIS model is a CRYPTEK, asked of the component it came from.

    19.01 merges the models but keeps each component's datasheet on its
    AttachedComponent, which is the only granularity at which "that CRYPTEK
    MODEL" can be answered once a unit is merged - squad.datasheet alone would
    answer for the bodyguard and never for the leader."""
    for component in components(squad) or ():
        sheet = getattr(component, "datasheet", None)
        if sheet is None:
            continue
        if CRYPTEK_KEYWORD not in (getattr(sheet, "keywords", None) or ()):
            continue
        if any(m is model for m in getattr(component, "starting_models", ()) or ()):
            return True
    return False


# ----------------------------------------------------------- Systematic Vigour

class SystematicVigourController:
    """Fed by main.py's death sweep; drained at on_unit_finished_fighting.

    Structurally game/malevolent_souls.py, which is structurally
    game/dlc_undying_spite.py - the three are deliberate twins over one shared
    ledger, and differ only in threshold and eligibility.

    "IF THAT MODEL HAS NOT FOUGHT THIS PHASE" is the one clause that reads
    differently from its two siblings, which both say UNIT. It is answered at
    the SQUAD, and that is the available granularity rather than a shortcut: a
    unit fights as a whole in this engine (12.02 picks the unit, and
    fought_squad_ids records units), so "this model has fought" and "this
    model's unit has fought" cannot come apart. Written down because the
    printed word is MODEL, and the day a rule lets half a unit swing the two
    stop agreeing."""

    def __init__(self, game_state=None, game_log=None, turn_tracker=None,
                 fight_controller=None):
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.fight_controller = fight_controller
        self._ledger = FightAfterDeath(
            SYSTEMATIC_VIGOUR_THRESHOLD, SYSTEMATIC_VIGOUR_LABEL,
            game_state=game_state, game_log=game_log)

    def _has_fought(self, squad):
        ledger = getattr(self.fight_controller, "fought_squad_ids", None) or ()
        return squad in ledger or id(squad) in {id(s) for s in ledger}

    def _in_fight_phase(self):
        """"destroyed by a MELEE attack" - the phase is the exact test here for
        the same reason it is in game/malevolent_souls.py."""
        if self.turn_tracker is None:
            return True
        return self.turn_tracker.phase == PHASE_FIGHT

    def is_eligible(self, model):
        """Whether THIS destroyed model stays up on a 2+.

        The CRYPTOTHRALL test is per MODEL, not per unit: once the retinue has
        joined a Cryptek's bodyguard unit its models sit beside Immortals or
        Necron Warriors, and only the Cryptothralls come back."""
        if not is_cryptothrall(model):
            return False
        squad = getattr(model, "squad", None)
        if squad is None or not self._in_fight_phase():
            return False
        return not self._has_fought(squad)

    @property
    def is_busy(self):
        return self._ledger.is_busy

    def models_owed_an_activation(self):
        return self._ledger.models_owed_an_activation()

    def intercept_destroyed(self, models):
        """From the death sweep. Returns the models that stayed up."""
        return self._ledger.roll_for(models, self.is_eligible)

    def resolve_after_attacks(self, attacking_squad=None):
        return self._ledger.resolve_after_attacks(attacking_squad)

    def reset_phase(self):
        """Anything still owed an activation when the phase ends is removed, so
        no model survives into a phase in which it has no right to strike."""
        return self._ledger.resolve_after_attacks()


# --------------------------------------------------------------- Cryptek Retinue

def host_is_led_by_cryptek(host):
    """"one other unit from your army that is being LED BY a CRYPTEK INFANTRY
    model".

    LED BY, so a component in the LEADER role - a Cryptek that merely stands
    nearby is not one, and neither is a SUPPORT component... except that every
    Cryptek in this faction prints CORE: Support, so the printed phrase and
    this engine's role would never agree if it were read strictly. It is
    therefore asked of any ATTACHED CHARACTER component that carries the
    CRYPTEK keyword, which is what "being led by" means at the table."""
    if host is None:
        return False
    for component in leader_components(host) or ():
        sheet = getattr(component, "datasheet", None)
        if sheet is None:
            continue
        keywords = getattr(sheet, "keywords", None) or ()
        if CRYPTEK_KEYWORD in keywords and INFANTRY_KEYWORD in keywords:
            return True
    return False


def retinue_join_errors(retinue, host, already_joined=()):
    """Why `retinue` cannot join `host` at Declare Battle Formations. Empty
    list = allowed.

    The PAIRING is delegated to can_attach() rather than re-derived - that is
    where rule 19.01 lives, and its one-per-role check is what enforces the
    printed "a unit cannot have more than one CRYPTOTHRALLS unit joined to
    it". Everything added here is a condition of the step itself."""
    if retinue is None or host is None:
        return ["No unit selected."]
    if attachment_role(retinue) != RETINUE:
        return ["%s is not a CRYPTOTHRALLS unit." % getattr(retinue, "name", "?")]
    if retinue is host:
        return ["A unit cannot join itself."]
    if getattr(retinue, "owner", None) != getattr(host, "owner", None):
        return ["%s is not from your army." % getattr(host, "name", "?")]
    errors = list(can_attach(retinue, host))
    # "(a unit cannot have more than one CRYPTOTHRALLS unit joined to it)".
    # 19.01's one-per-ROLE check gives this once the join has HAPPENED; while
    # declarations are still being collected nothing has attached yet, so the
    # already-declared list is what makes it checkable - the same argument
    # game/formations.py's support_join_errors() makes for its own limit.
    if already_joined and retinue not in already_joined:
        errors.append(
            "%s already has a CRYPTOTHRALLS unit joined to it." % host.name)
    if not host_is_led_by_cryptek(host):
        errors.append(
            "%s is not being led by a CRYPTEK INFANTRY model." % host.name)
    return errors


def eligible_retinue_hosts(retinue, army, joins=None):
    """Every unit in `army` this retinue could legally join.

    `joins` maps id(host) -> the units already declared into it."""
    joins = joins or {}
    return [unit for unit in (army or ())
            if not retinue_join_errors(retinue, unit, joins.get(id(unit), ()))]
