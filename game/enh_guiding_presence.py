"""Armoured Warhost Enhancement: Guiding Presence (25 pts).

RULE (verbatim, rules/aeldari/detachments/Armoured Warhost.md):
  "AELDARI PSYKER model only. At the start of your Shooting phase, select one
  **visible** friendly AELDARI VEHICLE unit within 6" of this model. That
  VEHICLE unit's ranged attacks have +1 to **hit rolls**."

A MARK ON A FRIENDLY UNIT - the first in this batch, and the opposite side
from its two Etappe-3 neighbours. Mirage Field and Shimmerstone are
DEFENDER-side (they worsen attacks aimed at the bearer's unit); this one is
ATTACKER-side and does not touch the bearer's own unit at all. It is the
Farseer's Guide with the sign and the recipient changed: a mark, set at a
phase boundary, read by whoever is shooting.

Held per PLAYER in this controller rather than as a flag on the squad, the
same arrangement game/guide.py, game/doom.py and the other marks use.

FOUR CLAUSES, EACH OF WHICH CAN BE MISSED ON ITS OWN:

  1. "AELDARI VEHICLE" - two keywords, pooled per rule 19.03. VEHICLE is a
     UnitProfile flag; AELDARI is a FACTION keyword, and this engine reads
     those off the DATASHEET (see game/aeldari_detachments.py), which is why
     the two halves are asked differently.
  2. "friendly" - same owner as the bearer. Marking an enemy vehicle would be
     a 25-point gift, and nothing else in the predicate would notice.
  3. 'within 6" of this MODEL' - measured from the bearer, not from its unit.
     One word, and the difference is a whole squad's footprint.
  4. "visible" - a real line-of-sight test, which only Seer's Eye has needed
     before. Optional collaborator, exactly as game/conclave_seers_eye.py
     takes it: when no `visible` callable is supplied every candidate counts
     as visible, which is what a headless harness gets.

"RANGED ATTACKS" - so the Shooting phase only, and the absence from
game/fight.py is asserted at the source.

"+1 TO HIT ROLLS" is a BONUS, so a NEGATIVE threshold adjustment under
game/modifiers.py's convention - the opposite sign from both its neighbours in
this batch, which is precisely why each of the three says so in its own words.

LIFETIME: it is re-selected at the start of every Shooting phase, so the mark
is cleared there and set again. Nothing else clears it, and nothing else
should: a phase-scoped mark that also had a turn reset would be two clocks for
one lifetime, the mistake game/protocol_sudden_storm.py records having to keep
apart.
"""
from game import aeldari_detachments, attached_units, enhancements
from game.squad import edge_distance

GUIDING_PRESENCE = "Guiding Presence"

GUIDING_PRESENCE_LABEL = "Guiding Presence"

#: 'within 6" of this model'.
GUIDING_PRESENCE_RANGE_IN = 6.0

#: "+1 to hit rolls" - BETTER, so a negative threshold adjustment.
GUIDING_PRESENCE_BONUS = -1


def is_eligible_target(squad, owner):
    """"one visible friendly AELDARI VEHICLE unit" - everything except the
    distance and the line of sight, which need positions."""
    if squad is None or squad.owner != owner:
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    return attached_units.unit_has_keyword(
        squad, lambda m: getattr(m.profile, "vehicle", False))


def bearer_models(squad):
    """The models carrying it - rule 19.04's reading, so a model that died
    this frame no longer counts (remove_dead_models() runs once per frame)."""
    return enhancements.bearer_models(squad, GUIDING_PRESENCE)


class GuidingPresenceController:
    """The start-of-Shooting-phase selection, and the mark it leaves."""

    def __init__(self, game_state=None, decision_manager=None, game_log=None,
                 auto_players=(), visible=None):
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        #: visible(observer_model, target_model) -> bool. Optional, like every
        #: other line-of-sight collaborator here; None means "everything
        #: counts as visible", which is what a headless harness gets.
        self.visible = visible
        #: player -> the marked squad, for this Shooting phase.
        self._marked = {}

    # --- what the hit step reads -----------------------------------------

    def applies(self, attacking_squad):
        """Whether THIS unit's ranged attacks carry the bonus."""
        if attacking_squad is None:
            return False
        return self._marked.get(attacking_squad.owner) is attacking_squad

    # --- the offer --------------------------------------------------------

    def _squads(self):
        seen, out = set(), []
        for token in getattr(self.game_state, "tokens", ()) or ():
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen.add(id(squad))
                out.append(squad)
        return out

    def _bearer_squads(self, player):
        return [s for s in self._squads()
                if s.owner == player and bearer_models(s)]

    def candidates(self, player):
        """The eligible targets, measured from the nearest bearer model."""
        bearers = [(s, m) for s in self._bearer_squads(player) for m in bearer_models(s)]
        if not bearers:
            return []
        out = []
        for squad in self._squads():
            if not is_eligible_target(squad, player):
                continue
            if any(self._reaches(model, squad) for _s, model in bearers):
                out.append(squad)
        return out

    def _reaches(self, bearer_model, squad):
        """Within 6" of the BEARER MODEL, and visible to it."""
        for other in getattr(squad, "models", ()) or ():
            if other.is_dead():
                continue
            if edge_distance(bearer_model, other) > GUIDING_PRESENCE_RANGE_IN:
                continue
            if self.visible is None or self.visible(bearer_model, other):
                return True
        return False

    def reset_phase(self):
        """Re-selected every Shooting phase, so the previous mark goes first."""
        self._marked.clear()

    def offer_at_start_of_shooting_phase(self, player):
        """"At the start of your Shooting phase, select one ..." - offered
        once, to the player whose phase it is."""
        options = self.candidates(player)
        if not options:
            return False
        if player in self.auto_players or self.decision_manager is None:
            self._choose(player, options[0])
            return True
        self.decision_manager.request(
            player,
            "%s: which friendly AELDARI VEHICLE unit gains +1 to hit this phase?"
            % GUIDING_PRESENCE_LABEL,
            [(squad.name, (lambda s=squad: self._choose(player, s))) for squad in options],
        )
        return True

    def _choose(self, player, squad):
        self._marked[player] = squad
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s has +1 to hit with its ranged attacks this phase."
                % (GUIDING_PRESENCE_LABEL, squad.name))
        return True
