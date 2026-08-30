"""The Ynnari triumvirate's abilities that are one predicate each.

Yvraine, The Visarch and The Yncarne bring seven rules between them. Two of
them carry real state and have their own modules (Word of the Phoenix,
Inevitable Death). The rest are a predicate apiece hanging on a seam that
already exists, so they live together here - the same call
game/corsair_abilities.py records for its six, and for the same reason: six
modules would be six docstrings repeating "this is a Ynnari ability".

RULES (printed, word for word):

  Way of the Blade      "While this model is leading a unit, models in that
      unit have the Fights First ability."

  Yvraine's Champion    "While this model is leading a unit, other CHARACTER
      models attached to that unit have the Feel No Pain 4+ ability."

  Ethereal Form         "Each time this model destroys an enemy unit, this
      model regains up to D3 lost wounds."

  Herald of Ynnead      "At the start of the Fight phase, select one enemy unit
      within Engagement Range of this model's unit. Until the end of the phase,
      each time a friendly AELDARI model makes an attack that targets that
      unit, you can re-roll a Wound roll of 1."

  Servant Of The        "Your army cannot include any EPIC HERO units that do
  Whispering God         not have the YNNARI keyword."

SERVANT OF THE WHISPERING GOD IS A DOCUMENTED NO-OP, and the reason is the
same one game/starflare_ignition.py used to carry: this engine has no
army-building step. It is a LIST-BUILDING restriction - it constrains which
datasheets may be written down together, and by the time a battle starts the
list is already fixed. There is no moment at which it could fire and nothing
for it to refuse. Named rather than quietly dropped, and pinned in the test, so
that adding an army builder makes this a visible one-line change.

All three of them print it, which is what makes it a triumvirate rather than
three characters: they come as a set or not at all.
"""
import random

from game.attached_units import leader_ability

WAY_OF_THE_BLADE_LABEL = "Way of the Blade"
YVRAINES_CHAMPION_LABEL = "Yvraine's Champion"
ETHEREAL_FORM_LABEL = "Ethereal Form"
HERALD_OF_YNNEAD_LABEL = "Herald of Ynnead"
SERVANT_OF_THE_WHISPERING_GOD_LABEL = "Servant Of The Whispering God"

#: "other CHARACTER models attached to that unit have the Feel No Pain 4+".
YVRAINES_CHAMPION_FEEL_NO_PAIN = "4+"

#: The no-Feel-No-Pain sentinel game/feel_no_pain.py folds on. NOT None: every
#: other source returns this, and returning None instead made _better_threshold()
#: collapse an absent FNP from "-" to None across eight unrelated suites.
NO_FEEL_NO_PAIN = "-"


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


# --- Way of the Blade -------------------------------------------------------

def way_of_the_blade_applies(squad):
    """"While this model is LEADING a unit" - rule 24.22's question, so
    leader_ability() and not unit_wide_ability(): no bodyguard prints it, and
    the Visarch standing alone leads nothing and grants nothing.

    THE THIRD SOURCE OF FIGHTS FIRST, and the first that is neither the unit's
    own printed 24.13 ability nor rule 11.04's post-charge grant. It therefore
    folds into squad_has_fights_first(), the one place that answers "is this a
    Fights First unit right now" - putting it anywhere else would give
    FightController's activation ORDER a second opinion about which units go
    first, and that order is the entire content of 24.13."""
    return bool(squad is not None and leader_ability(squad, "way_of_the_blade"))


# --- Yvraine's Champion -----------------------------------------------------

def yvraines_champion_feel_no_pain(model):
    """Feel No Pain 4+ for the OTHER characters in the Visarch's unit.

    THREE WORDS DO REAL WORK HERE, and dropping any one of them widens the
    rule past what is printed:

      * "OTHER" - the Visarch himself is excluded. He has a 2+ save and a 4++
        already; this is what he does for the people he escorts.
      * "CHARACTER models" - not the bodyguards. A Guardian Defender in the
        same unit gets nothing, which is exactly the difference between this
        and the Deathshroud's Silent Bodyguard that folds in beside it.
      * "while this model is LEADING" - 24.22 again, read from the same
        leader_ability() as Way of the Blade above.

    Returns "-" when it does not apply, the no-Feel-No-Pain sentinel every
    other source here uses - _better_threshold() folds "-" away, so a character
    that already prints a better FNP keeps it and one with none stays at "-"
    rather than collapsing to None."""
    if model is None or model.is_dead():
        return NO_FEEL_NO_PAIN
    if not getattr(model.profile, "character", False):
        return NO_FEEL_NO_PAIN
    if getattr(model.profile, "yvraines_champion", False):
        return NO_FEEL_NO_PAIN          # "OTHER" - never the Visarch himself
    squad = getattr(model, "squad", None)
    if squad is None or not leader_ability(squad, "yvraines_champion"):
        return NO_FEEL_NO_PAIN
    return YVRAINES_CHAMPION_FEEL_NO_PAIN


# --- Ethereal Form ----------------------------------------------------------

def ethereal_form_applies(squad):
    return any(getattr(m.profile, "ethereal_form", False) for m in _living(squad))


def roll_ethereal_form(squad, game_log=None):
    """Rolls the D3 and heals in one go.

    NOT a dice_manager step, and that is a deliberate exception to this
    engine's "a roll the human can see" habit. It fires inside main.py's death
    SWEEP, where Deadly Demise and the emergency-disembark queue are already
    contending for DiceManager's single roll window - the exact collision
    game/deadly_vectors.py records between Reanimation Protocols and its own
    queue, and it was solved there by moving to a different seam. There is no
    different seam here: "each time this model destroys an enemy unit" is this
    instant. So the roll is resolved immediately and the LOG carries both
    numbers, which is what makes it checkable after the fact.

    Returns (rolled, healed) so a caller can report the die as well as the
    effect - they are different facts, and only the second changed the board."""
    if not ethereal_form_applies(squad):
        return (0, 0)
    rolled = random.randint(1, 3)
    return (rolled, heal_ethereal_form(squad, rolled, game_log, rolled=rolled))


def heal_ethereal_form(squad, healed, game_log=None, rolled=None):
    """"Regains UP TO D3 lost wounds" - so the roll is a ceiling, not an
    amount, and healing is capped at what was actually lost. A model at full
    wounds gains nothing from a 3.

    Returns how many wounds were really restored, which is the number worth
    logging: "rolled a 3" and "healed 1" are different facts, and only the
    second one changed the board."""
    # A pure early-out. The filter inside the loop is the real enforcement -
    # "each time THIS MODEL destroys" is per model - and today the two can
    # never disagree, because no datasheet can put the Yncarne in a unit with
    # anything else. Kept so the cheap case stays cheap, not as a second rule.
    if healed <= 0 or not ethereal_form_applies(squad):
        return 0
    total = 0
    for model in _living(squad):
        if not getattr(model.profile, "ethereal_form", False):
            continue
        missing = model.profile.wounds - model.current_wounds
        gained = max(0, min(healed, missing))
        model.current_wounds += gained
        total += gained
    if total and game_log is not None:
        game_log.add("%s: %s regains %d lost wound%s%s."
                     % (ETHEREAL_FORM_LABEL, squad.name, total,
                        "" if total == 1 else "s",
                        "" if rolled is None else " (rolled %d)" % rolled))
    return total


# --- Herald of Ynnead -------------------------------------------------------

class HeraldOfYnneadController:
    """Yvraine's start-of-Fight-phase mark.

    THE EIGHTH ENEMY MARK, and the shortest-lived: Guide and Doom run to the
    start of the next Command phase, Kharseth's riven mark to the end of the
    turn, this one only to the end of the PHASE it was set in. So it is
    cleared on the phase boundary, not in main.py's end-of-turn block.

    NOT A reroll_scope ENTRY, and this is the one decision worth writing down.
    The text says "you CAN re-roll a Wound roll of 1" - optional, and ONES
    ONLY. There is no "or re-roll the whole roll instead", so the ones-or-whole
    offer game/reroll_scope.py names does not apply here. And a bare optional
    re-roll of 1s has no downside at all: a 1 always fails, so re-rolling it
    can only gain. Offering it would be a prompt whose every answer but one is
    wrong - error class 5, the same reasoning [LETHAL HITS] and Kauyon's
    "ignore any or all" already carry. It resolves automatically, exactly like
    the Wraithlord's Fated Hero, which prints the same mandatory-in-effect
    shape. Pinned as an ABSENCE in the test, because that is the only place it
    shows.

    ARMY-WIDE: "a friendly AELDARI model", not "a model in this unit". Held per
    PLAYER like Guide and Doom, and read by every Aeldari unit that player
    owns.
    """

    def __init__(self, decision_manager=None, game_log=None, all_tokens=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.auto_players = set(auto_players)
        self._marked = {}          # player -> the enemy Squad chosen this phase

    def applies(self, squad):
        return any(getattr(m.profile, "herald_of_ynnead", False) for m in _living(squad))

    def is_marked(self, target_squad, by_player=None):
        if by_player is not None:
            return self._marked.get(by_player) is target_squad
        return any(m is target_squad for m in self._marked.values())

    def candidates(self, squad):
        """"one enemy unit within ENGAGEMENT RANGE of this model's unit" - so
        the whole unit's reach, not just Yvraine's own base."""
        from game.squad import ENGAGEMENT_RANGE_IN, edge_distance
        mine = _living(squad)
        out = []
        for token in self.all_tokens or ():
            other = getattr(token, "squad", None)
            if other is None or other.owner == squad.owner or other in out:
                continue
            living = _living(other)
            if any(edge_distance(a, b) <= ENGAGEMENT_RANGE_IN
                   for a in mine for b in living):
                out.append(other)
        return out

    def mark(self, bearer_squad, target):
        if bearer_squad is None or target is None:
            return False
        self._marked[bearer_squad.owner] = target
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s calls the dead down on %s - friendly AELDARI attacks "
                "against it re-roll a Wound roll of 1 until the end of the phase."
                % (HERALD_OF_YNNEAD_LABEL, bearer_squad.name, target.name))
        return True

    def offer_at_fight_phase(self, squad):
        """One prompt at the start of the Fight phase, and only when there is
        something to choose between - a single engaged enemy is not a choice."""
        if not self.applies(squad) or self._marked.get(squad.owner) is not None:
            return False
        options = self.candidates(squad)
        if not options:
            return False
        if len(options) == 1 or squad.owner in self.auto_players \
                or self.decision_manager is None:
            return self.mark(squad, self._pick(options))
        self.decision_manager.request(
            squad.owner,
            "%s: %s - which unit does Ynnead mark?"
            % (HERALD_OF_YNNEAD_LABEL, squad.name),
            [(t.name, (lambda t=t: self.mark(squad, t))) for t in options])
        return True

    def _pick(self, options):
        """Deterministic for the AI: the biggest engaged unit, ties broken by
        name - most dice re-rolled, and nothing that can flicker."""
        return max(options, key=lambda s: (len(_living(s)), s.name))

    def grants(self, attacking_squad, target_squad):
        """Every AELDARI unit of the marking player, not just Yvraine's."""
        from game import psychic_guidance
        if attacking_squad is None or target_squad is None:
            return False
        if not psychic_guidance._is_aeldari(attacking_squad):
            return False
        return self.is_marked(target_squad, attacking_squad.owner)

    def reset_phase(self):
        """"Until the end of the phase" - the shortest-lived mark here."""
        self._marked.clear()
