""""Nekrosor Ammentar's four printed abilities (Necrons).

One module for one datasheet, the arrangement game/cryptothralls.py and
game/tomb_blade_wargear.py already use: these four are not a family, they are
one model's page, and splitting them into four files would put four one-idea
modules next to each other with nothing shared.

RULES (printed, word for word):

  Protective Disciples: "While this model is within 3" of one or more other
  friendly DESTROYER CULT units, this model has the Lone Operative ability."

  Infectious Murder-madness (Aura): "While a friendly NECRONS unit (excluding
  MONSTER and TITANIC units) is within 6" of this model, each time a model in
  that unit makes an attack, if that model has the DESTROYER CULT keyword or
  that enemy unit is the closest eligible target, that attack has the
  [SUSTAINED HITS 1] ability."

  Prophet of Destruction: "Each time this model destroys an enemy unit, select
  one other friendly DESTROYER CULT unit within 9" of it. Until the end of the
  phase, each time a model in that unit makes an attack, re-roll a Wound roll
  of 1."

  Nullstone Field Generator (Aura, Wargear): "While a friendly NECRONS unit is
  within 6" of the bearer, models in that unit have the Feel No Pain 5+
  ability against mortal wounds and Psychic Attacks."

THREE OF THE FOUR MEASURE FROM THIS MODEL, NOT FROM ITS UNIT, and that is the
printed word in each case ("of this model", "of it", "of the bearer"). Today he
is a one-model unit with no LEADER line at all, so model and unit are the same
distance - which is exactly why it is worth writing the measurement the printed
way rather than reaching for Squad.min_distance_to(): the shortcut is invisible
until something can join him, and then it is silently wrong.
"""

import copy

from game import ai_mode, titanic
from game.attached_units import (model_has_datasheet_keyword,
                                 unit_has_datasheet_keyword, unit_has_keyword)
from game.squad import edge_distance

DESTROYER_CULT_KEYWORD = "DESTROYER CULT"

# --- Protective Disciples ---------------------------------------------------

PROTECTIVE_DISCIPLES_RANGE_IN = 3.0
#: Rule 24.24's default X for a granted Lone Operative with no printed number -
#: the same number game/illuminor.py's identical sentence uses.
PROTECTIVE_DISCIPLES_LONE_OPERATIVE_RANGE_IN = 12

# --- Infectious Murder-madness ----------------------------------------------

MURDER_MADNESS_RANGE_IN = 6.0
MURDER_MADNESS_SUSTAINED_HITS = 1
MURDER_MADNESS_LABEL = "Infectious Murder-madness"

# --- Prophet of Destruction -------------------------------------------------

PROPHET_RANGE_IN = 9.0
PROPHET_LABEL = "Prophet of Destruction"

# --- Nullstone Field Generator ----------------------------------------------

NULLSTONE_RANGE_IN = 6.0
NULLSTONE_FEEL_NO_PAIN = "5+"


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def _is_necron_unit(squad):
    """"a friendly NECRONS unit". The army rule is printed on every Necron
    datasheet, so its flag IS the faction test - the same reading
    game/illuminor.py uses for the identical phrase."""
    return bool(squad) and any(getattr(m.profile, "reanimation_protocols", False)
                               for m in _living(squad))


def _is_destroyer_cult_unit(squad):
    return unit_has_datasheet_keyword(squad, DESTROYER_CULT_KEYWORD)


def _model_range_to_squad(model, squad):
    """Base-edge distance from ONE model to the nearest living model of
    `squad`, or None when there is nothing to measure to.

    Rule 19.03's pooling does not enter into it: these are DISTANCES, and every
    other range test in this engine measures base edge to base edge."""
    others = _living(squad)
    if model is None or not others:
        return None
    return min(edge_distance(model, other) for other in others)


def bearer_models(squad, flag):
    """The living models of `squad` that carry `flag`."""
    return [m for m in _living(squad) if getattr(m.profile, flag, False)]


def _carriers(all_tokens, owner, flag):
    """Every living model on `owner`'s side carrying `flag`, read off the
    board - the arrangement game/mechanical_augmentation.py uses for the only
    other datasheet aura here."""
    return [t for t in all_tokens or ()
            if getattr(t, "squad", None) is not None
            and t.squad.owner == owner
            and not t.is_dead()
            and getattr(t.profile, flag, False)]


def _friendly_squads(all_tokens, owner, exclude=None):
    """Every friendly unit currently on the board, deduplicated. `exclude` is
    the caller's own unit where the printed text says "other"."""
    seen = {}
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other is exclude or token.is_dead():
            continue
        if getattr(other, "owner", None) != owner:
            continue
        seen[id(other)] = other
    return list(seen.values())


# ---------------------------------------------------------- Protective Disciples

def has_protective_disciples(squad):
    return bool(bearer_models(squad, "protective_disciples"))


def grants_lone_operative(squad, all_tokens=()):
    """Registered in game/conditional_lone_operative.py as the FIFTH source of
    that shape.

    "ONE OR MORE OTHER FRIENDLY DESTROYER CULT UNITS" - the word doing the work
    is OTHER, exactly as in Illuminor Szeras's sentence: his own unit does not
    count, and for a single-model unit that would otherwise make the condition
    trivially true and the ability unconditional.

    NARROWER THAN ILLUMINOR'S, and that is the whole difference between the
    two: Szeras asks for any friendly NECRONS unit, this one asks for a
    DESTROYER CULT one. Standing next to Necron Warriors does nothing here."""
    if not has_protective_disciples(squad):
        return False
    owner = getattr(squad, "owner", None)
    for model in bearer_models(squad, "protective_disciples"):
        for other in _friendly_squads(all_tokens, owner, exclude=squad):
            if not _is_destroyer_cult_unit(other):
                continue
            gap = _model_range_to_squad(model, other)
            if gap is not None and gap <= PROTECTIVE_DISCIPLES_RANGE_IN:
                return True
    return False


# ----------------------------------------------------- Infectious Murder-madness

def _excluded_from_murder_madness(squad):
    """"(excluding MONSTER and TITANIC units)".

    MONSTER is a UnitProfile flag and is pooled per rule 19.03 (any model);
    TITANIC is a datasheet keyword and goes through game/titanic.py, which is
    the ONE reader of that question - the four sites that used to read a
    profile field that does not exist are exactly why that module exists."""
    if unit_has_keyword(squad, lambda m: getattr(m.profile, "monster", False)):
        return True
    return titanic.is_titanic_unit(squad)


def unit_in_murder_madness_aura(squad, all_tokens=()):
    """Whether `squad` is a friendly NECRONS unit inside a living bearer's 6".

    THE BEARER'S OWN UNIT IS NOT EXCLUDED, and that is the printed text rather
    than an oversight: it says "a friendly NECRONS unit", not "another". So
    Nekrosor Ammentar sits inside his own aura at distance 0 - which matters,
    because he is DESTROYER CULT and therefore always meets the attack-level
    clause below. Contrast Protective Disciples one section up, whose sentence
    DOES say "other"; the two are three lines apart on the same page."""
    if squad is None or not _is_necron_unit(squad):
        return False
    if _excluded_from_murder_madness(squad):
        return False
    for token in _carriers(all_tokens, getattr(squad, "owner", None),
                           "infectious_murder_madness"):
        gap = _model_range_to_squad(token, squad)
        if gap is not None and gap <= MURDER_MADNESS_RANGE_IN:
            return True
    return False


def murder_madness_applies(attacking_squad, attacking_model, target_is_closest,
                           all_tokens=()):
    """The whole ability, in one predicate.

    TWO CLAUSES JOINED BY "OR", and they are asked at different granularities -
    which is the part that is easy to flatten by accident:

      * "if THAT MODEL has the DESTROYER CULT keyword" is per MODEL, answered
        through attached_units.model_has_datasheet_keyword() because a model
        does not know its own datasheet once 19.01 has merged it;
      * "or that ENEMY UNIT is the closest eligible target" is a property of
        the ATTACK, so the caller measures it - each attack step already knows
        what its own eligible targets are, and re-deriving that here would be
        a second opinion on rule 10.02.

    MEASURED, not assumed: on every datasheet this engine builds, DESTROYER
    CULT units are led only by DESTROYER CULT characters (the Skorpekh Lord
    leads Skorpekh Destroyers, the Lokhust Lord leads the two Lokhust sheets),
    so no unit can hold both a DESTROYER CULT model and a non-DESTROYER-CULT
    one. That is what makes rule 04.03's one-representative attack grouping
    exact here rather than a shortcut - and it is pinned in the suite, so a
    future pairing that breaks it shows up as a red line instead of as a
    quietly wrong grant."""
    if not unit_in_murder_madness_aura(attacking_squad, all_tokens):
        return False
    if target_is_closest:
        return True
    return model_has_datasheet_keyword(attacking_squad, attacking_model,
                                       DESTROYER_CULT_KEYWORD)


def adjusted_weapon(weapon, attacking_squad, attacking_model, target_is_closest,
                    all_tokens=()):
    """[SUSTAINED HITS 1] on the attack, as a COPY.

    Both no-downgrade guards its twin game/ritual_butchery.py carries, and for
    the same reasons: a weapon that already prints an equal or better flat X
    keeps it, and one with a printed DICE X is left alone because a rolled
    value is at least as good as a flat 1 in every outcome."""
    if weapon is None:
        return weapon
    if not murder_madness_applies(attacking_squad, attacking_model,
                                  target_is_closest, all_tokens):
        return weapon
    if getattr(weapon, "sustained_hits", 0) >= MURDER_MADNESS_SUSTAINED_HITS:
        return weapon
    if getattr(weapon, "sustained_hits_notation", None) is not None:
        return weapon
    granted = copy.copy(weapon)
    granted.sustained_hits = MURDER_MADNESS_SUSTAINED_HITS
    return granted


# ------------------------------------------------------- Prophet of Destruction

def prophet_applies(squad):
    """Whether this unit is currently under a Prophet of Destruction grant.

    A phase-scoped flag on the Squad, read by both attack steps' automatic
    ones-re-roll block - the shape every "until the end of the phase" grant
    here uses."""
    return squad is not None and bool(getattr(squad, "prophet_of_destruction", False))


def prophet_reset_phase(squads=()):
    """"Until the end of the phase"."""
    for squad in squads or ():
        squad.prophet_of_destruction = False


def prophet_candidates(killer_squad, all_tokens=()):
    """"one OTHER friendly DESTROYER CULT unit within 9" of it" - measured from
    the BEARER MODEL, which is what "of it" refers to.

    Sorted by name so a replayed battle offers the same list in the same order;
    the underlying token sweep is insertion-ordered but the dedupe is not."""
    if not bearer_models(killer_squad, "prophet_of_destruction"):
        return []
    owner = getattr(killer_squad, "owner", None)
    out = []
    for other in _friendly_squads(all_tokens, owner, exclude=killer_squad):
        if not _is_destroyer_cult_unit(other):
            continue
        if not _living(other):
            continue
        gap = min((_model_range_to_squad(m, other)
                   for m in bearer_models(killer_squad, "prophet_of_destruction")),
                  default=None)
        if gap is not None and gap <= PROPHET_RANGE_IN:
            out.append(other)
    return sorted(out, key=lambda s: getattr(s, "name", ""))


def grant_prophet(squad):
    if squad is None:
        return False
    squad.prophet_of_destruction = True
    return True


class ProphetOfDestructionController:
    """Fed by main.py's per-SQUAD death sweep, beside Protocol of the Vengeful
    Stars and Mont'ka's Pinpoint Counter-Offensive.

    WHO KILLED IT is the same question those two answer, and the same answer:
    this engine has no general kill attribution, only "who was attacking at the
    time", which the death sweep already carries. The phase is widened like
    Pinpoint's - "each time this model destroys an enemy unit" names no phase,
    so the Fight phase's attacker counts too.

    "THIS MODEL DESTROYS" IS READ AS "HIS UNIT DESTROYED", and that is exact
    rather than a shortcut here for the reason game/mechanical_augmentation.py
    records for Szeras: Nekrosor Ammentar prints no LEADER line, so his unit is
    always exactly one model and the two statements cannot differ. Written down
    because the shortcut stops being valid the moment something can join him.

    THE 9" IS MEASURED FROM THE LIVING BEARER, not from the corpses - which is
    the opposite of Vengeful Stars, whose 6" has to be measured from where the
    DEAD unit stood because that is what its printed text names. Here the
    subject is "of it", the killer, who is still on the board.

    A REAL CHOICE, so a prompt: "select one other friendly DESTROYER CULT unit"
    with more than one in range is a decision the player makes, and the options
    are TAGGED with their squads so game/unit_pick.py turns it into a board
    click rather than a list of names."""

    def __init__(self, decision_manager=None, game_state=None, game_log=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)

    def _tokens(self):
        if self.game_state is None:
            return []
        return list(getattr(self.game_state, "tokens", []) or [])

    def notify_unit_destroyed(self, wiped_squad, killer_squad):
        """One wiped-out enemy unit, plus whoever was attacking at the time."""
        if killer_squad is None or wiped_squad is None:
            return False
        if getattr(killer_squad, "owner", None) == getattr(wiped_squad, "owner", None):
            return False
        if not bearer_models(killer_squad, "prophet_of_destruction"):
            return False
        candidates = prophet_candidates(killer_squad, self._tokens())
        if not candidates:
            return False
        if killer_squad.owner in self.auto_players or self.decision_manager is None:
            # Deterministic for the AI, and the pick is not arbitrary: the
            # grant is a re-roll of 1s on ATTACKS, so it is worth most to
            # whichever candidate throws the most dice. Measured off the
            # models rather than guessed at, and ties break by name so a
            # replayed battle grants it to the same unit.
            best = max(candidates,
                       key=lambda s: (len(_living(s)), getattr(s, "name", "")))
            return self._grant(killer_squad, best)
        self.decision_manager.request(
            killer_squad.owner,
            "%s: %s - which DESTROYER CULT unit re-rolls Wound rolls of 1 this phase?"
            % (killer_squad.name, PROPHET_LABEL),
            [(s.name, (lambda t=s: self._grant(killer_squad, t)), s) for s in candidates],
        )
        return True

    def _grant(self, killer_squad, squad):
        grant_prophet(squad)
        if self.game_log is not None:
            self.game_log.add(
                "%s destroyed a unit: %s re-rolls Wound rolls of 1 until the end "
                "of the phase (%s)." % (killer_squad.name, squad.name, PROPHET_LABEL))
        return True


# --------------------------------------------------- Nullstone Field Generator

def unit_in_nullstone_aura(squad, all_tokens=()):
    """Whether `squad` is a friendly NECRONS unit within 6" of a living bearer.

    NO KEYWORD EXCLUSIONS on this one - its sentence names none, unlike
    Infectious Murder-madness three lines above it on the same page. Written
    separately rather than sharing that predicate for exactly that reason."""
    if squad is None or not _is_necron_unit(squad):
        return False
    for token in _carriers(all_tokens, getattr(squad, "owner", None),
                           "nullstone_field_generator"):
        gap = _model_range_to_squad(token, squad)
        if gap is not None and gap <= NULLSTONE_RANGE_IN:
            return True
    return False


def refresh_nullstone(all_tokens=()):
    """Stamp Squad.nullstone_field_generator for every unit on the board, once
    per frame.

    A SQUAD FLAG rather than a live measurement, and the reason is the reader:
    feel_no_pain.current_feel_no_pain() takes a MODEL and nothing else, and it
    has roughly a dozen call sites. Threading `all_tokens` through all of them
    to re-derive the same geometry per wound is what game/nurgles_gift.py
    already decided against for the identical shape - so this is stamped beside
    it in main.py's per-frame aura block, for the same two reasons its
    docstring gives: positions change every frame, and a wiped-out bearer must
    stop projecting the aura in the same frame it dies."""
    squads = {}
    for token in all_tokens or ():
        squad = getattr(token, "squad", None)
        if squad is not None:
            squads[id(squad)] = squad
    for squad in squads.values():
        squad.nullstone_field_generator = unit_in_nullstone_aura(squad, all_tokens)


def nullstone_feel_no_pain(model, mortal=False, psychic=False):
    """This model's granted Feel No Pain threshold against THIS wound, or "-".

    Same return convention as every other conditional source in that fold
    (advanced_armour_feel_no_pain, layered_wards_feel_no_pain,
    enh_runes_of_warding.feel_no_pain): a threshold STRING, and "-" rather than
    None for a wound this does not cover - None collapses the fold, which cost
    eight foreign suites once already.

    "AGAINST MORTAL WOUNDS AND PSYCHIC ATTACKS" is an OR, not an AND: either
    kind of wound is covered. Each flag is set by exactly one caller, so every
    other caller keeps the defaults and keeps meaning what it did."""
    if model is None or not (mortal or psychic):
        return "-"
    squad = getattr(model, "squad", None)
    if squad is None or not getattr(squad, "nullstone_field_generator", False):
        return "-"
    return NULLSTONE_FEEL_NO_PAIN
