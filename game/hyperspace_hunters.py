""""Hyperspace Hunters" - the Deathmarks' own ability (Necrons).

RULE (printed, word for word):
  "Once per turn, in the Reinforcements step of your opponent's Movement
   phase, when an enemy unit is set up on the battlefield from Reserves within
   18" of and visible to this unit, this unit can shoot as if it were your
   Shooting phase, but must only target that enemy unit when doing so, and can
   only do so if that enemy unit is an eligible target."

NOTHING NEW IS BUILT HERE, and both halves already existed:

  * "shoot as if it were your Shooting phase ... but must only target that
    enemy unit" is ShootingController.start_reactive_shooting(restrict_to=),
    written for Awakened Dynasty's Protocol of the Vengeful Stars and reused
    by the Krootox Rampagers' Kroot Packmates. The restriction is enforced in
    _is_valid_target_squad(), the ONE place that decides what may be shot at,
    so no second filter can drift from it.
  * "when an enemy unit is set up on the battlefield from Reserves" is
    IngressController.on_ingress_resolved, the listener list Rapid Ingress and
    the Grenade Pack already hang off.

THE ONE TRAP IN THAT SECOND HOOK: on_ingress_resolved fires on CANCEL as well
as on arrival - it is "the ingress attempt is over", not "a unit arrived". A
cancelled placement would otherwise hand the Deathmarks a free volley at a
unit that is not on the board. `ingressed_this_turn` is what separates them:
confirm_ingress() adds to it, cancel_ingress() does not.

"YOUR OPPONENT'S Movement phase" AND "an ENEMY unit" say the same thing twice
from two directions, and both are checked - not because either is redundant
today, but because a future rule that lets a unit arrive in its own owner's
phase would otherwise let a Deathmark squad shoot its own reinforcements.

VISIBILITY IS INJECTED (`visible_to`), so this module owns no line-of-sight
opinion of its own - the same arrangement game/elemental_ensnarement.py uses.
Without it every unit in range qualifies, which is what a headless test wants.
"""

from game import ai_mode
from game.attached_units import unit_has_keyword
from game.squad import edge_distance

HYPERSPACE_HUNTERS_RANGE_IN = 18.0

LABEL = "Hyperspace Hunters"


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def unit_has_hyperspace_hunters(squad):
    """Rule 19.03's any-model pooling. Deathmarks print no LEADER line and are
    on nobody's LED BY list today, so this is their own models - written the
    pooled way so it keeps meaning "this unit" if that changes."""
    if squad is None:
        return False
    return unit_has_keyword(squad, lambda m: getattr(m.profile, "hyperspace_hunters", False))


def in_range(hunters, arrival):
    """"within 18 inches of ... this unit" - unit to unit, measured edge to
    edge like every other range in this engine."""
    mine, theirs = _living(hunters), _living(arrival)
    if not mine or not theirs:
        return False
    return any(edge_distance(a, b) <= HYPERSPACE_HUNTERS_RANGE_IN
               for a in mine for b in theirs)


class HyperspaceHuntersController:
    """One offer per arriving unit, capped at once per turn per hunting unit."""

    def __init__(self, shooting_controller=None, decision_manager=None,
                 ingress_controller=None, all_tokens=None, game_log=None,
                 visible_to=None, auto_players=()):
        self.shooting_controller = shooting_controller
        self.decision_manager = decision_manager
        self.ingress_controller = ingress_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        #: visible_to(watcher_squad, target_squad) -> bool. None = no opinion.
        self.visible_to = visible_to
        self.auto_players = ai_mode.players(auto_players)
        self._used_this_turn = set()

    def reset_turn(self):
        """"Once per turn", per hunting unit."""
        self._used_this_turn = set()

    def _really_arrived(self, squad):
        """on_ingress_resolved also fires on cancel - see the module docstring."""
        if self.ingress_controller is None:
            return True
        return squad in getattr(self.ingress_controller, "ingressed_this_turn", ())

    def hunters_for(self, arrival):
        """Every eligible Deathmark unit, nearest first."""
        if arrival is None or not self._really_arrived(arrival):
            return []
        seen, out = set(), []
        for token in self.all_tokens or ():
            squad = getattr(token, "squad", None)
            if squad is None or id(squad) in seen:
                continue
            if squad.owner == arrival.owner:          # "an ENEMY unit"
                continue
            if not unit_has_hyperspace_hunters(squad) or not _living(squad):
                continue
            if id(squad) in self._used_this_turn:
                continue
            if not in_range(squad, arrival):
                continue
            if self.visible_to is not None and not self.visible_to(squad, arrival):
                continue
            seen.add(id(squad))
            out.append(squad)
        out.sort(key=lambda s: s.name)
        return out

    def offer_on_arrival(self, arrival, phase_owner=None):
        """Wired into IngressController.on_ingress_resolved.

        `phase_owner` is whose Movement phase it is. The printed clause says
        "your OPPONENT'S", so a hunter may not be the one moving; it is
        optional so a caller that has none simply skips that half rather than
        guessing."""
        for squad in self.hunters_for(arrival):
            if phase_owner is not None and squad.owner == phase_owner:
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                # Deterministic for the AI: a free shooting activation costs
                # nothing at all - the unit still shoots normally in its own
                # phase, because this is not its activation.
                return self._use(squad, arrival)
            self.decision_manager.request(
                squad.owner,
                "%s: Hyperspace Hunters - shoot %s as it arrives from Reserves?"
                % (squad.name, arrival.name),
                [("Shoot it", lambda s=squad, a=arrival: self._use(s, a)),
                 ("Hold fire", lambda: None)],
            )
            return True
        return False

    def _use(self, squad, arrival):
        self._used_this_turn.add(id(squad))
        started = False
        if self.shooting_controller is not None:
            started = self.shooting_controller.start_reactive_shooting(
                squad, restrict_to=arrival)
        if self.game_log:
            self.game_log.add(
                "%s uses Hyperspace Hunters against %s as it arrives from Reserves."
                % (squad.name, arrival.name))
        return started
