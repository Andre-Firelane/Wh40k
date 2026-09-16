"""A printed keyword condition on a weapon ability - rules 24.01 and 04.01.03.

Two printed shapes read the same way, and both are here:

  * Rule 24.01: "If a weapon ability is followed by one or more keywords, when
    making attacks with that weapon, that ability only applies if the target
    unit has one or more of those keywords." Example from the rule itself:
    [LETHAL HITS: VEHICLE]. The core-rules FAQ adds the NEGATED form:
    "ANTI-NON-(any keyword) will trigger on any unit that does not have the
    specified keyword" - which is how "[LETHAL HITS: non-MONSTER/VEHICLE]",
    printed on nearly every Ork gun, is read.
  * Rule 04.01.03: "Hunter profiles can only target units with the specified
    keywords" - the "HUNTER: MONSTER/VEHICLE" row above a weapon profile.

"MONSTER/VEHICLE" is ONE OR MORE of those keywords ("has one or more of those
keywords"), so a condition is an any() over its keywords, and "non-" is the
complement of that whole any() - a unit that is a MONSTER is not a
non-MONSTER/VEHICLE unit, whatever else it is.

DELIBERATELY STORE-ONLY at import time: game/weapons.py builds these as class
attributes, and weapons.py must not import game/squad.py (it is imported by
nearly everything). matches() imports game/unit_keywords.py lazily.
"""


class KeywordCondition:
    """`keywords` is a tuple of printed keywords; `negated` is the "non-"
    prefix. Immutable and hashable, so a weapon class can hold one."""

    __slots__ = ("keywords", "negated")

    def __init__(self, keywords, negated=False):
        object.__setattr__(self, "keywords", tuple(k.upper() for k in keywords))
        object.__setattr__(self, "negated", bool(negated))

    def __setattr__(self, name, value):
        raise AttributeError("KeywordCondition is immutable")

    @classmethod
    def parse(cls, text):
        """'non-MONSTER/VEHICLE' -> KeywordCondition(('MONSTER', 'VEHICLE'), negated=True)."""
        text = text.strip()
        negated = text.lower().startswith("non-")
        if negated:
            text = text[4:]
        return cls([part.strip() for part in text.split("/") if part.strip()], negated)

    @property
    def spelled(self):
        """The printed spelling: 'non-MONSTER/VEHICLE', 'MONSTER/VEHICLE'."""
        return ("non-" if self.negated else "") + "/".join(self.keywords)

    def matches(self, target_squad):
        """Whether an attack against `target_squad` meets this condition. No
        target at all never does - a conditional ability with nothing to test
        against grants nothing."""
        if target_squad is None:
            return False
        from game.unit_keywords import unit_has_keyword
        has_one = any(unit_has_keyword(target_squad, keyword) for keyword in self.keywords)
        return has_one != self.negated

    def __eq__(self, other):
        return (isinstance(other, KeywordCondition)
                and self.keywords == other.keywords and self.negated == other.negated)

    def __hash__(self):
        return hash((self.keywords, self.negated))

    def __repr__(self):
        return "KeywordCondition(%r)" % self.spelled


#: The conditions the 2026-09 Ork codex prints on its weapons.
MONSTER_OR_VEHICLE_TARGETS = KeywordCondition(("MONSTER", "VEHICLE"))
NON_MONSTER_VEHICLE_TARGETS = KeywordCondition(("MONSTER", "VEHICLE"), negated=True)
#: The Painboy's 'Urty Syringe: "DEVASTATING WOUNDS: INFANTRY".
INFANTRY_TARGETS = KeywordCondition(("INFANTRY",))
