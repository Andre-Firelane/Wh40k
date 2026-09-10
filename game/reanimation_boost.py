"""The two Canoptek abilities that make Reanimation Protocols recover MORE.

RULES (printed, word for word):

  NANOSCARAB REANIMATION BEAM (Aura) - Canoptek Reanimator:
    "While a friendly NECRONS unit is within 3" of this model, each time that
     unit's Reanimation Protocols activate, that unit heals an additional D3
     wounds."

  NANOSCARAB PROJECTOR - Canoptek Macrocytes wargear:
    "Once per battle round, when a friendly NECRONS unit within 3" of the
     bearer activates its Reanimation Protocols, the bearer can use this
     ability. If it does, that unit reanimates 1 additional wound."

ONE MODULE FOR TWO ABILITIES because they add to the SAME number at the SAME
moment, and the order they are asked in has to be one decision rather than two.
Splitting them would be two modules that both have to know about the other's
existence to agree on that.

THREE PRINTED DIFFERENCES, and each one is load-bearing:

  * THE AMOUNT. The beam is D3, so it is ROLLED; the projector is a flat 1 and
    rolls nothing. The beam's die is thrown IN-MODULE rather than through the
    DiceManager - a deliberate exception to this engine's "every die is
    visible" habit, with its reasoning at beam_wounds() below.
  * THE ENTITLEMENT. The beam has none: "each time that unit's Reanimation
    Protocols activate" holds for every unit in range, every Command phase.
    The projector is "once per BATTLE ROUND" - not once per turn and not once
    per unit, so the bearer spends it on the first unit it is offered for
    unless a player says otherwise.
  * "CAN USE". The projector says the bearer "can use this ability", which is
    a real choice; the beam has no such word and simply applies. So the
    projector is offered and the beam is not, and an owner in `auto_players`
    answers the projector deterministically.

BOTH ADD TO THE WOUNDS BEFORE THEY ARE SPENT, not afterwards - rule 01.02.03's
Starting Strength cap and 02.02.04's heal-then-revive order both operate on the
TOTAL, so an extra wound handed over after the fact would be spent under
different rules than the ones it was granted under.
"""

from game import ai_mode
from game.attached_units import model_has_datasheet_keyword  # noqa: F401  (kept for symmetry with the other Canoptek modules)

REANIMATION_BEAM_LABEL = "Nanoscarab Reanimation Beam"
NANOSCARAB_PROJECTOR_LABEL = "Nanoscarab Projector"

#: "within 3" of this model" / "within 3" of the bearer" - the same distance on
#: both, which is why one constant serves.
NANOSCARAB_RANGE_IN = 3.0
#: "that unit reanimates 1 additional wound".
NANOSCARAB_PROJECTOR_WOUNDS = 1


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def is_necron_unit(squad):
    """"a friendly NECRONS unit" - the army rule's flag IS the faction test,
    the reading every other Necron aura here uses."""
    return bool(squad) and any(
        getattr(m.profile, "reanimation_protocols", False) for m in _living(squad))


def _edge_distance(a, b):
    dx, dy = a.x_in - b.x_in, a.y_in - b.y_in
    return max(0.0, (dx * dx + dy * dy) ** 0.5 - a.radius_in - b.radius_in)


def bearers_in_range(squad, all_tokens, flag):
    """Every living friendly model carrying `flag` within 3" of `squad`."""
    if squad is None:
        return []
    owner = getattr(squad, "owner", None)
    mine = _living(squad)
    if not mine:
        return []
    out = []
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other.owner != owner or token.is_dead():
            continue
        if not getattr(token.profile, flag, False):
            continue
        if any(_edge_distance(token, m) <= NANOSCARAB_RANGE_IN for m in mine):
            out.append(token)
    return out


# ------------------------------------------------- Nanoscarab Reanimation Beam

def beam_applies(squad, all_tokens=()):
    """Whether this unit is inside a Reanimator's 3" aura.

    NOT stamped as a squad flag, unlike the Feel No Pain auras: this is read
    ONCE per unit per Command phase, at the point Reanimation Protocols
    activate, rather than a dozen times per wound - so a live measurement costs
    nothing and cannot go stale."""
    return (is_necron_unit(squad)
            and bool(bearers_in_range(squad, all_tokens, "nanoscarab_reanimation_beam")))


# ------------------------------------------------------- Nanoscarab Projector

class NanoscarabProjectorController:
    """"Once per battle round" - so the entitlement is per BEARER and per
    round, and it is held here rather than on the Squad because a battle round
    is not a Squad-shaped clock."""

    def __init__(self, decision_manager=None, game_log=None, turn_tracker=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.turn_tracker = turn_tracker
        self.auto_players = ai_mode.players(auto_players)
        self._used = {}     # id(bearer model) -> battle round it was used in

    def _round(self):
        return getattr(self.turn_tracker, "battle_round", None)

    def available_bearers(self, squad, all_tokens=()):
        """Bearers in range that have not yet spent this battle round."""
        if not is_necron_unit(squad):
            return []
        this_round = self._round()
        return [t for t in bearers_in_range(squad, all_tokens, "nanoscarab_projector")
                if self._used.get(id(t)) != this_round]

    def extra_wounds(self, squad, all_tokens=()):
        """How many additional wounds the projector adds to THIS activation.

        Resolved without a prompt for an `auto_players` owner and for a
        headless caller; a human is asked, because "the bearer CAN use this
        ability" is a real choice about a once-per-round resource. Returns the
        number to add now - a prompt cannot be waited for inside a
        reanimation, so the human answer is taken from `decision_manager` on
        the NEXT activation rather than blocking this one."""
        bearers = self.available_bearers(squad, all_tokens)
        if not bearers:
            return 0
        owner = getattr(squad, "owner", None)
        if owner in self.auto_players or self.decision_manager is None:
            return self._spend(bearers[0], squad)
        # A human is asked, and the ability is not spent unless they accept.
        self.decision_manager.request(
            owner,
            "%s: %s - spend this battle round's use to reanimate 1 additional "
            "wound?" % (squad.name, NANOSCARAB_PROJECTOR_LABEL),
            [("Use the Nanoscarab Projector",
              lambda b=bearers[0], s=squad: self._spend(b, s)),
             ("Save it", None)])
        return 0

    def _spend(self, bearer, squad):
        self._used[id(bearer)] = self._round()
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s reanimates %d additional wound."
                % (NANOSCARAB_PROJECTOR_LABEL, squad.name,
                   NANOSCARAB_PROJECTOR_WOUNDS))
        return NANOSCARAB_PROJECTOR_WOUNDS


def beam_wounds(squad, all_tokens=(), log=None):
    """The Reanimator's additional D3, rolled and reported.

    ROLLED IN-MODULE rather than through the DiceManager, and that is a
    deliberate exception to this engine's "every die is visible" habit - the
    same one game/deadly_vectors.py records for Ethereal Form. Reanimation
    Protocols already owns ONE dice window per unit per Command phase, and the
    user has already reported that queue being too long ("nur triggern, wenn
    die Einheit auch schon Schaden erlitten hat. Jetzt feuert das jedes Mal");
    a second visible roll per unit would double it for every Necron unit on
    the board. The roll and its total are LOGGED instead, which is what makes
    it readable back."""
    if not beam_applies(squad, all_tokens):
        return 0
    from game import dice
    rolled = dice.random.randint(1, 3)
    if log is not None:
        log("%s: %s reanimates an additional D3 (%d)."
            % (REANIMATION_BEAM_LABEL, squad.name, rolled))
    return rolled


class ReanimationBoost:
    """Both sources behind one question, so the army rule asks once.

    ORDER IS NOT A DECISION HERE - they ADD, and addition commutes. The
    projector is asked second only so a human prompt it may raise does not sit
    in front of the beam's silent roll.
    """

    def __init__(self, projector=None):
        self.projector = projector

    def extra_wounds(self, squad, all_tokens=(), log=None):
        total = beam_wounds(squad, all_tokens, log=log)
        if self.projector is not None:
            total += self.projector.extra_wounds(squad, all_tokens)
        return total
