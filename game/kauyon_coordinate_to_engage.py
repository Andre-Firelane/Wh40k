"""Kauyon Stratagem: Coordinate to Engage (1CP).

RULE (verbatim, rules/tau_empire/detachments/Kauyon.md):
  WHEN:   Your Shooting phase.
  TARGET: One T'AU EMPIRE unit from your army that has just been selected as an
          Observer unit (see For the Greater Good).
  EFFECT: Until the end of the phase, each time a model in your unit makes an
          attack that targets their Spotted unit, improve the Ballistic Skill
          characteristic of that attack by 1 and, if your unit has the
          MARKERLIGHT keyword, that attack has the [IGNORES COVER] ability.

IT BUYS BACK EXACTLY WHAT THE ARMY RULE TAKES AWAY
---------------------------------------------------
For The Greater Good says Guided units are "units with this ability EXCLUDING
Observer units" - an Observer marks a target for everyone else and gets nothing
itself. This Stratagem is the Observer buying its own bonus against the unit it
marked, which is why the TARGET line names an Observer rather than a Guided
unit. game/target_uploaded.py is the datasheet ability that does the same
thing, and this reuses its reading rather than inventing a second one.

"THEIR Spotted unit" - not any Spotted unit. GreaterGoodController already
records which Observer marked which target (`spotted_by`), so the pairing is
read from there rather than re-derived.

TWO EFFECTS, TWO SEAMS: the Ballistic Skill half is a hit modifier
(_hit_modifiers), and [IGNORES COVER] is asked at _cover_ignored_for_group().
The second is CONDITIONAL on MARKERLIGHT, so a unit without it gets the BS half
alone - checked separately rather than assumed to travel together.
"""

from game import kauyon, tau_detachments
from game.attached_units import unit_has_datasheet_keyword
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

COORDINATE_TO_ENGAGE_CP = 1
COORDINATE_TO_ENGAGE_NAME = "Coordinate to Engage"
MARKERLIGHT_KEYWORD = "MARKERLIGHT"


def is_active(squad):
    return bool(getattr(squad, "coordinate_to_engage_active", False))


def spotted_unit_of(greater_good, observer_squad):
    """The unit THIS observer marked this phase, or None.

    GreaterGoodController keeps `spotted_by` as {target -> observer}, so the
    lookup is by value. One observer marks at most one unit per phase, so
    there is no ambiguity to resolve."""
    if greater_good is None or observer_squad is None:
        return None
    for target, observer in getattr(greater_good, "spotted_by", {}).items():
        if observer is observer_squad:
            return target
    return None


def applies(greater_good, attacking_squad, target_squad):
    """Whether this attack is the bought one: an active unit shooting the very
    unit it Spotted."""
    if not is_active(attacking_squad) or target_squad is None:
        return False
    return spotted_unit_of(greater_good, attacking_squad) is target_squad


def ignores_cover(greater_good, attacking_squad, target_squad):
    """The second half, which needs the MARKERLIGHT keyword as well."""
    if not applies(greater_good, attacking_squad, target_squad):
        return False
    return unit_has_datasheet_keyword(attacking_squad, MARKERLIGHT_KEYWORD)


class CoordinateToEngageController:
    def __init__(self, stratagem_controller, shooting_controller=None,
                 greater_good=None, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.greater_good = greater_good
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=COORDINATE_TO_ENGAGE_NAME, cp_cost=COORDINATE_TO_ENGAGE_CP,
            effect=self._grant,
        )

    def reset_phase(self, squads=()):
        for squad in squads or ():
            squad.coordinate_to_engage_active = False

    def panel_label(self, squad):
        extra = (" and [IGNORES COVER]"
                 if unit_has_datasheet_keyword(squad, MARKERLIGHT_KEYWORD) else "")
        return (f"{COORDINATE_TO_ENGAGE_NAME} ({COORDINATE_TO_ENGAGE_CP} CP) - "
                f"+1 BS vs your Spotted unit{extra}")

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False
        if is_active(squad):
            return False
        if not tau_detachments.has_detachment(squad.owner, kauyon.SETTING):
            return False
        if not tau_detachments.is_tau_unit(squad):
            return False
        # "has just been selected as an OBSERVER unit" - and it must actually
        # have marked something, or the effect has nothing to apply to.
        if self.greater_good is None or not self.greater_good.is_observer(squad):
            return False
        if spotted_unit_of(self.greater_good, squad) is None:
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.coordinate_to_engage_active = True
            if self.game_log is not None:
                marked = spotted_unit_of(self.greater_good, squad)
                self.game_log.add(
                    f"{COORDINATE_TO_ENGAGE_NAME}: {squad.name} improves its Ballistic Skill "
                    f"by 1 against {marked.name if marked else 'its Spotted unit'} this phase."
                )
