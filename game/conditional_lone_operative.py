"""Rule 24.24's LONE OPERATIVE, where it is CONDITIONAL rather than printed -
the 25th extraction, one carrier late.

WHY IT EXISTS
-------------
Three abilities already grant Lone Operative on a condition instead of printing
a range on the profile, and all three print the SAME sentence with a different
keyword and a different distance:

    Illuminor Szeras      within 3" of one or more OTHER friendly NECRONS units
    the Spiritseer        within 3" of one or more friendly WRAITH CONSTRUCT units
    Death Guard Defenders within 3" of one or more friendly DEATH GUARD units

Each is a module-level `grants_lone_operative(squad, all_tokens)` plus a named
range constant, and each was folded into status_effects.lone_operative_range()
as its own hand-written `if`. The comments there tell the story on their own:
the Spiritseer's says "Second such grant", and Death Guard Defenders' also says
"the SECOND conditional granter" - two blocks both claiming to be the second,
which is what three copies of one shape look like from the inside.

Armoured Warhost's Spirit Stone of Raelyth is the fourth ("while this model is
within 3" of a friendly AELDARI VEHICLE unit, this model has Lone Operative"),
and a fourth hand-written block is one past defensible.

WHAT IS SHARED AND WHAT IS NOT. Only the FOLD is shared - "ask every
conditional source, and take the longest range it grants". Each source keeps
its own module, its own predicate and its own printed distance, because those
are the parts that differ. A source registers here instead of being appended to
a chain in whichever file happened to need it first, which is the same move
game/move_exceptions.py and game/hidden_after_shooting.py both make.

THE COMPOSITION IS max(), NOT first-wins, and that is inherited rather than
invented: lone_operative_range() already returned max() over the printed values,
because a model with two sources of the ability keeps the better one - the same
reading rule 05.04 gives armour and invulnerable saves. Nothing here changes it.

`all_tokens` IS STILL OPTIONAL IN THE SIGNATURE, AND THAT WAS NOT "THE SAFE
DIRECTION" - corrected 2026-09-21. This paragraph used to argue that a caller
which does not pass the board "simply never sees a conditional grant, which is
the safe direction and is what keeps every existing call site meaning what it
did". Both halves were wrong in the same way: the ONLY place in the engine that
enforces rule 24.24 is status_effects.targeting_range_limit(), it took no
all_tokens at all, and so every one of the six sources granted nothing where it
counts. A unit that should have been untargetable beyond 12" was shot at from
20", and every suite stayed green because each source is pinned against
granted_ranges() with the board in hand and none of them goes through the gate
(user, about the sixth: "Ghazkhull hat eigentlich Lone Op durch seine Fähigkeit.
die kommt wahrscheinlich nirgends an").

The default stays - dozens of harnesses and tests call these with a squad alone -
but it is a CONVENIENCE, not a safety property, and test_event_chain_wiring.py
section 33 now names any reader in game/, ai/ or main.py that leaves the board
out.
"""

from game import death_guard_defenders, illuminor, spiritseer
from game import enh_spirit_stone_of_raelyth
from game import nekrosor_ammentar
from game import grand_warlords_ladz

#: (predicate, range) for every CONDITIONAL grant. A source is a pair, not a
#: subclass: what it shares is the question, not any behaviour.
#:
#: Order is irrelevant - the fold takes max() - so this is in the order the
#: three arrived, which is also the order their own comments reference.
SOURCES = (
    (illuminor.grants_lone_operative,
     illuminor.ILLUMINOR_LONE_OPERATIVE_RANGE_IN),
    (spiritseer.grants_lone_operative,
     spiritseer.SPIRITSEER_LONE_OPERATIVE_RANGE_IN),
    (death_guard_defenders.grants_lone_operative,
     death_guard_defenders.DEATH_GUARD_DEFENDERS_LONE_OPERATIVE_RANGE_IN),
    # Armoured Warhost's Spirit Stone of Raelyth - the FOURTH, and the first
    # that is an Enhancement rather than a printed datasheet ability. Same
    # sentence, same signature, one more entry.
    (enh_spirit_stone_of_raelyth.grants_lone_operative,
     enh_spirit_stone_of_raelyth.SPIRIT_STONE_RANGE_IN),
    # Nekrosor Ammentar's Protective Disciples - the FIFTH, and the narrowest:
    # Illuminor Szeras's identical sentence asks for any friendly NECRONS unit,
    # this one for a DESTROYER CULT one. Same signature, one more entry, which
    # is the whole point of the fold.
    (nekrosor_ammentar.grants_lone_operative,
     nekrosor_ammentar.PROTECTIVE_DISCIPLES_LONE_OPERATIVE_RANGE_IN),
    # Ghazghkull Thraka's Da Grand Warlord's Ladz - the SIXTH: within 3" of
    # another friendly ORKS INFANTRY unit. See game/grand_warlords_ladz.py.
    (grand_warlords_ladz.grants_lone_operative,
     grand_warlords_ladz.GRAND_WARLORDS_LADZ_LONE_OPERATIVE_RANGE_IN),
)


def granted_ranges(squad, all_tokens=()):
    """Every conditional LONE OPERATIVE range that currently applies to this
    unit, as a list. Empty when none does."""
    return [range_in for applies, range_in in SOURCES
            if applies(squad, all_tokens)]


def would_grant_at(squad, x_in, y_in, all_tokens=()):
    """Whether any source would be ON if this unit stood at (x_in, y_in).

    For ai/deployment_ai.py, which has to score a drop point BEFORE the unit is
    on the table: Ghazghkull's whole case for standing at the front is that Da
    Grand Warlord's Ladz makes him untargetable beyond 12", and that is only
    true beside an ORKS INFANTRY unit - so the scorer has to be able to ask the
    question of a POINT, not of the unit's current position.

    Implemented by translating the unit there, asking the real predicates, and
    putting it back, rather than by re-deriving "within 3" of a friendly X" in
    ai/. The six predicates differ in exactly the part that would have to be
    re-derived (which keyword, which distance, and Ghazghkull's "ANOTHER"), and
    a seventh source must not need a second implementation of itself - the same
    argument that made this module a fold in the first place. The translation is
    safe precisely where it is used: during deployment scoring the unit is not
    on the table yet, so its models are in no other structure, and the restore
    is in a finally.

    Every predicate tests a cheap ability flag first and returns False, so this
    costs nothing for the units - almost all of them - that have no source."""
    if squad is None or not getattr(squad, "models", None):
        return False
    models = squad.models
    n = len(models)
    dx = x_in - sum(m.x_in for m in models) / n
    dy = y_in - sum(m.y_in for m in models) / n
    saved = [(m.x_in, m.y_in) for m in models]
    try:
        for m in models:
            m.x_in += dx
            m.y_in += dy
        return bool(granted_ranges(squad, all_tokens))
    finally:
        for m, (sx, sy) in zip(models, saved):
            m.x_in, m.y_in = sx, sy
