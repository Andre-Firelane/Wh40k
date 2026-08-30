"""Spirit Conclave's "Shepherds of the Dead" - the detachment rule.

RULE (printed, word for word):
  "Each time an ASURYANI PSYKER model from your army is destroyed by an enemy
  unit, that enemy unit gains a Vengeful Dead token. Each time a WRAITH
  CONSTRUCT model from your army makes an attack that targets a unit with one
  or more Vengeful Dead tokens, add 1 to the Hit roll and add 1 to the Wound
  roll.

  ASURYANI PSYKER models from your army have the following ability:
  Spirit Guides (Aura): While a WRAITHBLADES, WRAITHGUARD or WRAITHLORD unit
  from your army is within 12" of this model, that unit has the Battle Focus
  ability.

  KEYWORDS: WRAITHBLADES and WRAITHGUARD units from your army gain the
  BATTLELINE keyword."

THE NINTH ENEMY MARK, AND THE FIRST SET BY A DEATH. Guide, Doom, Whispering
Web, Advanced Scouting, Spotted, prey marks, Kharseth's riven mark and Herald
of Ynnead are all placed by a CHOICE at a named moment, so each has an offer_*
method hung on that moment. This one has none: it is placed by the death sweep,
which makes the trigger a fact rather than a decision.

TWO THINGS FOLLOW FROM THAT, and both are unlike every other mark here:

  * IT IS CUMULATIVE. "one or MORE Vengeful Dead tokens" - the count is
    printed, so the count is kept, even though the effect does not scale. A set
    of marked units would read identically today and lose the printed noun.
  * IT NEVER EXPIRES. Every other mark names a duration ("until the end of the
    phase", "of the turn", "of your next Command phase"); this one names none,
    so it has no reset_turn()/reset_phase() at all. That absence is the thing
    most likely to be "fixed" by a later reader, so it is pinned.

+1 HIT AND +1 WOUND ARE TWO MODIFIERS AT TWO SEAMS, in both phases: "makes an
attack", not "a ranged attack". Both negative, because game/modifiers.py
adjusts the THRESHOLD.

"ASURYANI PSYKER" IS WHERE THE FACTION KEYWORD EARNS ITS KEEP. Measured, this
roster has 11 PSYKER datasheets and two of them - Yvraine and The Yncarne - are
YNNARI rather than ASURYANI, so reading it as "any Aeldari psyker" would put
tokens on the board for the wrong deaths. That is the one place the whole
faction_keywords field pays for itself.

SPIRIT GUIDES grants the ARMY RULE, so it folds into
battle_focus.has_battle_focus() - the one place that answers "does this unit
have Battle Focus". A near-no-op on the built roster, measured: all three named
datasheets already print the ability, so the aura can only re-grant what they
have. Built anyway, because it is printed, and pinned with a hand-built unit
that does not print it - a probe against a real Wraithguard would pass either
way and prove nothing.

THE BATTLELINE CLAUSE IS A MEASURED NO-OP: no Aeldari rule reads that keyword.
Named rather than dropped.
"""

from game import aeldari_detachments
from game.modifiers import Modifier

SHEPHERDS_OF_THE_DEAD_LABEL = "Shepherds of the Dead"
VENGEFUL_DEAD_LABEL = "Vengeful Dead"
SPIRIT_GUIDES_LABEL = "Spirit Guides"

#: "add 1 to the Hit roll and add 1 to the Wound roll" - negative, because
#: modifiers adjust the THRESHOLD.
VENGEFUL_DEAD_BONUS = -1

#: 'While a ... unit is within 12" of this model'.
SPIRIT_GUIDES_RANGE_IN = 12.0

#: The datasheets Spirit Guides names, as their keyword lines spell them.
SPIRIT_GUIDES_KEYWORDS = ("WRAITHBLADES", "WRAITHGUARD", "WRAITHLORD")

#: "a WRAITH CONSTRUCT model from your army".
WRAITH_CONSTRUCT_KEYWORD = "WRAITH CONSTRUCT"

#: The config constant game/detachments.py writes for Spirit Conclave.
SETTING = "SPIRIT_CONCLAVE_PLAYERS"


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def is_asuryani_psyker_model(model, squad):
    """"an ASURYANI PSYKER model from your army".

    PSYKER is a real per-model profile flag; ASURYANI is the datasheet's
    faction line, which is a per-unit fact. Both are asked, and the second is
    the one that discriminates - two of this roster's eleven PSYKER datasheets
    are YNNARI."""
    if model is None or not getattr(model.profile, "psyker", False):
        return False
    return aeldari_detachments.is_asuryani_unit(squad)


def is_wraith_construct(squad):
    from game.attached_units import unit_has_datasheet_keyword
    return unit_has_datasheet_keyword(squad, WRAITH_CONSTRUCT_KEYWORD)


class ShepherdsOfTheDeadController:
    """The Vengeful Dead tokens and the Spirit Guides aura."""

    def __init__(self, game_log=None, all_tokens=None):
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        #: id(squad) -> how many tokens it carries. Counted, not just flagged,
        #: because the printed text says "one or more".
        self._tokens = {}
        self._named = {}

    # --- the mark ---------------------------------------------------------

    def tokens_on(self, squad):
        return self._tokens.get(id(squad), 0)

    def is_marked(self, squad):
        return self.tokens_on(squad) > 0

    def marked_squads(self):
        return [self._named[key] for key in self._tokens if key in self._named]

    def notify_psyker_destroyed(self, model, squad, killer_squad):
        """Fed from main.py's death sweep, once per destroyed model.

        "destroyed BY AN ENEMY UNIT", so the killer has to be known and has to
        be an enemy - this engine's only answer to "who did that" is whoever
        was attacking at the time, the same one Szeras' Atomic Energy
        Manipulator takes."""
        if killer_squad is None or squad is None:
            return False
        if not has_detachment(getattr(squad, "owner", None)):
            return False
        if killer_squad.owner == squad.owner:
            return False
        if not is_asuryani_psyker_model(model, squad):
            return False
        key = id(killer_squad)
        self._tokens[key] = self._tokens.get(key, 0) + 1
        self._named[key] = killer_squad
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s gains a %s token (%d) for destroying %s."
                % (SHEPHERDS_OF_THE_DEAD_LABEL, killer_squad.name,
                   VENGEFUL_DEAD_LABEL, self._tokens[key], model.profile.name))
        return True

    def grants(self, attacking_squad, target_squad):
        """"a WRAITH CONSTRUCT model from your army ... targets a unit with one
        or more Vengeful Dead tokens"."""
        if attacking_squad is None or target_squad is None:
            return False
        if not has_detachment(getattr(attacking_squad, "owner", None)):
            return False
        if not is_wraith_construct(attacking_squad):
            return False
        return self.is_marked(target_squad)

    def hit_modifiers(self, attacking_squad, target_squad):
        if self.grants(attacking_squad, target_squad):
            return [Modifier(VENGEFUL_DEAD_BONUS, VENGEFUL_DEAD_LABEL)]
        return []

    def wound_modifiers(self, attacking_squad, target_squad):
        """The same bonus on the other roll - two seams, one condition."""
        if self.grants(attacking_squad, target_squad):
            return [Modifier(VENGEFUL_DEAD_BONUS, VENGEFUL_DEAD_LABEL)]
        return []

    # --- Spirit Guides ----------------------------------------------------

    def attach_to(self, squads):
        """Stamp every squad with a back-reference to this controller.

        game/battle_focus.py's has_battle_focus() is a module-level function
        with no controller in scope - it is reached from game/coldstar.py,
        which game/squad.py imports, so it cannot import upwards. The aura is
        therefore read off the squad, the same arrangement Nurgle's Gift uses
        for its Afflicted flag and for the same reason: the alternative is
        threading a controller through a dozen call sites that have no use for
        it."""
        for squad in squads or ():
            if squad is not None:
                squad.spirit_guides_source = self

    def spirit_guides_reaches(self, squad):
        """Is this unit within 12" of a friendly ASURYANI PSYKER model?

        Measured centre to centre, like every other "within X inches of a
        model" aura in this engine."""
        if squad is None or not has_detachment(getattr(squad, "owner", None)):
            return False
        from game.attached_units import unit_has_datasheet_keyword
        if not any(unit_has_datasheet_keyword(squad, keyword)
                   for keyword in SPIRIT_GUIDES_KEYWORDS):
            return False
        mine = [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]
        if not mine:
            return False
        for token in self.all_tokens or ():
            if token.is_dead():
                continue
            other = getattr(token, "squad", None)
            if other is None or other.owner != squad.owner:
                continue
            if not is_asuryani_psyker_model(token, other):
                continue
            # Soul Bridge - the SECOND of the two predicates its printed text
            # names. See game/conclave_soul_bridge.py.
            from game import conclave_soul_bridge
            if conclave_soul_bridge.is_bridged_to(squad, token):
                return True
            for model in mine:
                dx, dy = token.x_in - model.x_in, token.y_in - model.y_in
                if (dx * dx + dy * dy) ** 0.5 <= SPIRIT_GUIDES_RANGE_IN:
                    return True
        return False
