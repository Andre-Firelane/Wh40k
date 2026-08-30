"""T'au Empire detachment rule: Auxiliary Cadre's Integrated Command Structure.

RULE (verbatim, rules/tau_empire/detachments/Auxiliary Cadre.md):
  Friendly KROOT/VESPID STINGWINGS units have the following ability:
    Harnessed Alien Instincts: In your Shooting phase, this unit can select one
    visible enemy unit within 12". That enemy unit is prey-marked:
      - While a unit is prey-marked, that unit has +3" detection range
  Friendly GHOSTKEEL BATTLESUIT/STEALTH BATTLESUITS units have the following
  ability:
    Localised Stealth Projectors (Aura): When a friendly KROOT/VESPID
    STINGWINGS unit within 6" of this unit has shot, those attacks do not
    prevent that unit from being hidden.
  This detachment has the AUXILIARIES tag and cannot be taken with another
  AUXILIARIES detachment.

TWO ABILITIES, TWO SEAMS
------------------------
Harnessed Alien Instincts is a MARK ON AN ENEMY UNIT - the fifth in this engine
after Guide, Doom, Whispering Web and Advanced Scouting, and like them it is
held per player in a controller rather than as a flag on the marked unit,
because it belongs to the marked unit's OPPONENT.

Localised Stealth Projectors is the same question Advanced Acquisition Cadre's
Expert Fieldcraft asks - "does this unit's shooting leave its Hidden alone" -
only reached through an aura instead of a keyword. It is therefore the SECOND
consumer, and the fold lives in game/hidden_after_shooting.py rather than
either detachment growing a copy.

WHICH DIRECTION "+3" DETECTION RANGE" GOES
-------------------------------------------
Detection range in this engine belongs to the HIDDEN model: rule 13.09's
is_detectable() asks whether an observer is within the hidden model's own
detection range (15", or the 12" house rule when a wall sits on its footprint).
So giving a prey-marked ENEMY +3" makes it visible from FURTHER AWAY - a
penalty on the marked unit, which is what marking prey is for. Read the other
way round it would protect the enemy, which is why this is written out.

It only bites while the marked unit is actually Hidden; is_detectable() short-
circuits to True for anything that is not. Marking a visible unit is therefore
legal and simply does nothing, which the printed text also permits.

HOW LONG THE MARK LASTS - A DECISION, NOT A TRANSCRIPTION
---------------------------------------------------------
The printed text gives NO duration. User's call, asked and answered: until the
end of the turn - the same lifetime the engine's four existing marks already
have (Guide, Doom, Whispering Web, Advanced Scouting), so there is one story
about how long a mark lives rather than five.

WHEN THE OFFER HAPPENS
----------------------
"In your Shooting phase" - not "after this unit has shot", so it is offered at
the START of the phase, once per eligible unit, exactly like the For The
Greater Good army rule picks its Observers. A unit that never fires can still
mark. Measured on the predefined T'au list: one KROOT unit, so this is one
prompt per Shooting phase, not a nag.
"""

from game import tau_detachments
from game.attached_units import unit_has_datasheet_keyword
from game.squad import edge_distance

SETTING = "AUXILIARY_CADRE_PLAYERS"
LABEL = "Integrated Command Structure"

# The datasheet keywords the printed text names. STEALTH stands in for
# "STEALTH BATTLESUITS" for the reason game/advanced_acquisition_cadre.py
# records: it picks out exactly that one datasheet.
HARNESSED_KEYWORDS = ("KROOT", "VESPID STINGWINGS")
PROJECTOR_KEYWORDS = ("GHOSTKEEL", "STEALTH")

PREY_MARK_SELECT_RANGE_IN = 12.0
PREY_MARK_DETECTION_BONUS_IN = 3.0
PROJECTOR_AURA_RANGE_IN = 6.0


def _has_any_keyword(squad, keywords):
    if squad is None:
        return False
    return any(unit_has_datasheet_keyword(squad, keyword) for keyword in keywords)


def is_harnessed_unit(squad):
    """"a friendly KROOT/VESPID STINGWINGS unit" - the ones that may mark, and
    the ones the aura protects."""
    return _has_any_keyword(squad, HARNESSED_KEYWORDS)


def is_projector_unit(squad):
    """"a friendly GHOSTKEEL BATTLESUIT/STEALTH BATTLESUITS unit" - the aura's
    source."""
    return _has_any_keyword(squad, PROJECTOR_KEYWORDS)


def has_detachment(player):
    return tau_detachments.has_detachment(player, SETTING)


def _alive(squad):
    return [m for m in getattr(squad, "models", None) or () if not m.is_dead()]


def units_within(squad, others, distance_in):
    """Friendly units of `others` with a live model within `distance_in` of a
    live model of `squad`. Edge to edge, like every other range check here."""
    mine = _alive(squad)
    if not mine:
        return []
    found = []
    for other in others:
        if other is squad or getattr(other, "owner", None) != squad.owner:
            continue
        if any(edge_distance(a, b) <= distance_in for a in mine for b in _alive(other)):
            found.append(other)
    return found


def stealth_projector_covers(squad, all_squads=()):
    """The aura half: is this unit a KROOT/VESPID one standing within 6" of a
    friendly GHOSTKEEL/STEALTH unit, in an army with this detachment?"""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    if not tau_detachments.is_tau_unit(squad) or not is_harnessed_unit(squad):
        return False
    return any(is_projector_unit(other)
               for other in units_within(squad, all_squads, PROJECTOR_AURA_RANGE_IN))


class AuxiliaryCadreController:
    """Harnessed Alien Instincts: the prey mark, and the offer that sets it.

    Shaped after game/whispering_web.py, the engine's other "mark an enemy unit
    through a DecisionManager break point" ability - which also means an AI
    would resolve it through the generic path with nothing extra here. There is
    no T'au AI path by standing instruction, so nothing in ai/ names this.
    """

    def __init__(self, decision_manager=None, game_state=None, turn_tracker=None,
                 line_of_sight_check=None, game_log=None):
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        # Injected so this module does not depend on the line-of-sight engine
        # (and so a test can drive it without obstacles): called as
        # (observer_squad, target_squad) -> bool. None means "visible".
        self.line_of_sight_check = line_of_sight_check
        self.game_log = game_log
        self._marks = {}          # player -> set of marked enemy Squads
        self._offered_this_phase = set()

    # -- state ------------------------------------------------------------
    def _log(self, message, **kwargs):
        if self.game_log is not None:
            self.game_log.add(message, **kwargs)

    def reset_turn(self):
        """"Until the end of the turn" - the duration decided for this mark,
        matching the engine's four other marks. Called from main.py's
        end-of-turn block next to theirs."""
        self._marks.clear()
        self._offered_this_phase.clear()

    def reset_phase(self):
        """Only the once-per-unit offer memo. The MARK is turn-scoped and must
        survive a phase boundary, so the two are cleared separately - folding
        them into one reset would quietly shorten the mark to a phase."""
        self._offered_this_phase.clear()

    def marked_by(self, player):
        return set(self._marks.get(player, ()))

    def is_prey_marked(self, squad):
        """Whether ANY player has this unit marked.

        Asked without a player because its one consumer - rule 13.09's
        detection range - is a property of the marked unit itself, not of who
        is looking at it. A unit can only be marked by its opponent anyway.
        """
        if squad is None:
            return False
        return any(squad in marked for marked in self._marks.values())

    def detection_bonus_in(self, squad):
        """The extra detection range a prey-marked unit has, or 0."""
        return PREY_MARK_DETECTION_BONUS_IN if self.is_prey_marked(squad) else 0.0

    # -- the offer --------------------------------------------------------
    def _squads(self):
        """Every unit with a token on the board, DEDUPLICATED.

        game_state.tokens is one entry per MODEL, so an undeduplicated read
        returns a ten-model unit ten times - which made eligible_units() list
        the same Kroot squad ten times over. Keyed by id() because a Squad is
        not hashable by value, and insertion-ordered so the result is stable.
        """
        if self.game_state is None:
            return []
        by_id = {}
        for token in self.game_state.tokens:
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in by_id:
                by_id[id(squad)] = squad
        return list(by_id.values())

    def candidates_for(self, squad):
        """"one visible enemy unit within 12"" - the selection pool."""
        seen = []
        mine = _alive(squad)
        for other in self._squads():
            if other in seen or getattr(other, "owner", None) == squad.owner:
                continue
            if not _alive(other):
                continue
            if not any(edge_distance(a, b) <= PREY_MARK_SELECT_RANGE_IN
                       for a in mine for b in _alive(other)):
                continue
            if self.line_of_sight_check is not None and not self.line_of_sight_check(squad, other):
                continue
            seen.append(other)
        return sorted(seen, key=lambda s: s.name)

    def eligible_units(self, player):
        """The player's KROOT/VESPID units that may still mark this phase."""
        return sorted(
            (s for s in self._squads()
             if getattr(s, "owner", None) == player
             and id(s) not in self._offered_this_phase
             and tau_detachments.is_tau_unit(s) and is_harnessed_unit(s) and _alive(s)),
            key=lambda s: s.name)

    def offer_at_start_of_shooting_phase(self, player):
        """Offer each eligible unit its mark. Returns True if a prompt opened.

        One unit at a time: DecisionManager holds one open question, and the
        next unit is offered when this one resolves (main.py calls this again
        on the following frame, which is how every other queued offer here
        works)."""
        if not has_detachment(player):
            return False
        for squad in self.eligible_units(player):
            candidates = self.candidates_for(squad)
            self._offered_this_phase.add(id(squad))
            if not candidates:
                continue
            if self.decision_manager is None:
                return False
            self.decision_manager.request(
                player,
                f"{squad.name}: Harnessed Alien Instincts - prey-mark one enemy unit "
                f'within 12" (+3" detection range against it until the end of the turn)?',
                [(target.name, (lambda t=target: self.mark(player, t))) for target in candidates]
                + [("Do not mark", lambda: None)],
            )
            return True
        return False

    def mark(self, player, target):
        self._marks.setdefault(player, set()).add(target)
        self._log(
            f"Harnessed Alien Instincts: {target.name} is prey-marked "
            f'(+{PREY_MARK_DETECTION_BONUS_IN:g}" detection range) until the end of the turn.'
        )
        return True
