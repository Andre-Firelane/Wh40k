""""While a friendly <X> unit is within N inches of the bearer, that unit has
the Feel No Pain Y+ ability" - the shape three pieces of Necron wargear print.

THE 43rd EXTRACTION, at the SECOND and THIRD source at once - the same
situation game/detection_range.py was extracted in:

  Nullstone Field Generator (Nekrosor Ammentar)
    "friendly NECRONS units within 6" ... Feel No Pain 5+ against mortal
     wounds and Psychic Attacks"
  Gloom Prism (Canoptek Spyders)
    the SAME sentence, word for word, on another datasheet
  Fabricator Claw Array (Canoptek Spyders)
    "friendly NECRONS VEHICLE unit within 6" ... Feel No Pain 6+" - no wound
    qualifier at all

So the differences are exactly four knobs: the bearer's profile flag, the range,
the threshold, and WHICH WOUNDS it covers. Everything else - the geometry, the
per-frame stamp and the fold's return convention - is one implementation.

WHY IT IS A SQUAD FLAG STAMPED ONCE PER FRAME rather than a live measurement,
and this is the reason all three do it the same way:
feel_no_pain.current_feel_no_pain() takes a MODEL and nothing else, and it has
roughly a dozen call sites. Threading `all_tokens` through all of them to
re-derive the same geometry per wound is what game/nurgles_gift.py already
decided against for the identical shape. Two things follow, both of which the
stamp gets right and a cached answer would not: positions change every frame,
and a wiped-out bearer must stop projecting its aura in the same frame it dies.

THE RETURN CONVENTION IS A THRESHOLD STRING, with "-" for a wound this source
does not cover - never None. None collapses _better_threshold()'s fold, which
cost eight foreign suites once already.

"AGAINST MORTAL WOUNDS AND PSYCHIC ATTACKS" IS AN OR, not an AND: either kind
of wound is covered. An aura with `mortal_or_psychic_only = False` covers every
wound instead, which is what the Fabricator Claw Array prints.
"""


class FeelNoPainAura:
    """One printed aura. Instances are module-level constants in the ability's
    own module, not built per battle - they hold no state."""

    def __init__(self, flag, threshold, range_in, squad_flag, label,
                 unit_predicate=None, mortal_or_psychic_only=False):
        #: The bearer's UnitProfile attribute.
        self.flag = flag
        #: The granted Feel No Pain threshold, as a printed string ("5+").
        self.threshold = threshold
        self.range_in = range_in
        #: The Squad attribute this aura stamps. Its own, so two auras on one
        #: board cannot overwrite each other.
        self.squad_flag = squad_flag
        self.label = label
        #: Which friendly units it covers. None = every friendly unit.
        self.unit_predicate = unit_predicate
        #: True for "against mortal wounds and Psychic Attacks" - False grants
        #: against every wound, which is a genuinely different rule.
        self.mortal_or_psychic_only = mortal_or_psychic_only

    # -- geometry ------------------------------------------------------------

    def carriers(self, all_tokens, owner):
        """Living bearer MODELS on `owner`'s side, read off the board - the
        arrangement game/mechanical_augmentation.py uses for the only other
        datasheet aura here."""
        return [t for t in all_tokens or ()
                if getattr(t, "squad", None) is not None
                and t.squad.owner == owner
                and not t.is_dead()
                and getattr(t.profile, self.flag, False)]

    def covers(self, squad, all_tokens=()):
        """Whether `squad` is a friendly unit of the right kind within range of
        a living bearer."""
        if squad is None:
            return False
        if self.unit_predicate is not None and not self.unit_predicate(squad):
            return False
        owner = getattr(squad, "owner", None)
        for token in self.carriers(all_tokens, owner):
            for model in getattr(squad, "models", ()) or ():
                if model.is_dead():
                    continue
                if _edge_distance(token, model) <= self.range_in:
                    return True
        return False

    # -- the per-frame stamp -------------------------------------------------

    def refresh(self, all_tokens=()):
        """Stamp `squad_flag` on every unit on the board, once per frame."""
        squads = {}
        for token in all_tokens or ():
            squad = getattr(token, "squad", None)
            if squad is not None:
                squads[id(squad)] = squad
        for squad in squads.values():
            setattr(squad, self.squad_flag, self.covers(squad, all_tokens))

    # -- the reader ----------------------------------------------------------

    def feel_no_pain(self, model, mortal=False, psychic=False):
        """This model's granted threshold against THIS wound, or "-"."""
        if model is None:
            return "-"
        if self.mortal_or_psychic_only and not (mortal or psychic):
            return "-"
        squad = getattr(model, "squad", None)
        if squad is None or not getattr(squad, self.squad_flag, False):
            return "-"
        return self.threshold


def _edge_distance(model, other):
    """Base edge to base edge, the way every other range test in this engine
    measures."""
    dx = model.x_in - other.x_in
    dy = model.y_in - other.y_in
    gap = (dx * dx + dy * dy) ** 0.5
    return max(0.0, gap - model.radius_in - other.radius_in)


def refresh_all(auras, all_tokens=()):
    """Stamp several auras in one pass over the board - what main.py's
    per-frame aura block calls."""
    for aura in auras or ():
        aura.refresh(all_tokens)


def best_threshold(auras, model, mortal=False, psychic=False):
    """The best threshold any of these auras grants this model, or "-".

    Folded here rather than at each call site so feel_no_pain.py asks ONE
    question however many auras exist, and a fourth is one entry in the list
    the ability modules register."""
    best = "-"
    for aura in auras or ():
        got = aura.feel_no_pain(model, mortal=mortal, psychic=psychic)
        if got == "-":
            continue
        if best == "-" or int(got.rstrip("+")) < int(best.rstrip("+")):
            best = got
    return best
