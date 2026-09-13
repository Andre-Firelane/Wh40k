"""Windrider Host's "Ride the Wind" - the detachment rule.

RULE (printed, word for word):
  "In the Declare Battle Formations step you can set up ASURYANI MOUNTED and
  VYPER units from your army in Reserves. During the battle, such units can be
  set up on the battlefield as if they were arriving from Strategic Reserves.
  For the purposes of setting up ASURYANI MOUNTED or VYPER units from your army
  on the battlefield, treat the current battle round number as being one higher
  than it actually is.

  In addition, at the end of your opponent's turn, you can select a number of
  ASURYANI MOUNTED or VYPER units from your army (excluding units within
  Engagement Range of one or more enemy units), then remove those units from
  the battlefield and place them into Strategic Reserves. The maximum number of
  units you can select depends on the battle size: Incursion 1, Strike Force 2,
  Onslaught 3.

  KEYWORDS: WINDRIDERS units from your army gain the BATTLELINE keyword."

FOUR CLAUSES, AND TWO OF THEM ARE MEASURED NO-OPS. Both are written out rather
than dropped, because "already true" and "forgotten" look identical from the
code:

  * "you CAN set up ... in Reserves" grants nothing here. Rule 20.01 already
    lets ANY unit start in Strategic Reserves, and both the human's Formations
    screen and ai/deployment_ai.py already offer it to every unit under the
    cap - the AI's own comment says so in as many words. What the printed
    clause buys at a real table is permission this engine never withheld.
  * "WINDRIDERS units gain BATTLELINE" reaches nothing. Measured: no Aeldari
    rule reads that keyword (only game/mechanical_augmentation.py does, for
    Necrons). It is descriptive here, like MOB and GROTS.

THE ROUND CLAUSE IS THE ONE THAT PAYS, and it is also the one easiest to put in
the wrong place. "For the purposes of SETTING UP ... on the battlefield" scopes
it to arrival and to nothing else - not to the round counter itself. Victory
points, mission timing and rule 20.03's destruction of units still in Reserves
at the end of round 3 all keep reading the real number. So this module offers an
ADJUSTED round to the two places that gate an arrival, and touches no counter:

  * IngressController.can_ingress()      - rule 20.03's "not before round 2",
    so a Windrider unit may arrive in round 1.
  * IngressController._forbidden_zone_arrival() - the near-the-enemy-zone
    restriction that lifts from round 3, so for these units it lifts in round 2.

Both are "setting up on the battlefield", so both take the adjusted number; a
version that changed only the first would look complete from the first.

THE WITHDRAWAL CLAUSE is Airborne Agility with a cap, so it takes that module's
shape: offered at the end of the OPPONENT'S turn (the timing that is easiest to
get backwards), refused for a unit in Engagement Range, and resolved through
game/strategic_reserves.py's withdraw_to_reserves(), which also re-evaluates
objective control - a unit that leaves the board must stop holding what it
stood on.

THE CAP COMES FROM THE BATTLE SIZE, as a table beside the one
game/battle_focus.py keeps for the same reason, and with the same fallback: an
unknown size reads as Strike Force rather than as zero, because zero would make
the clause silently inert, which reads like a broken rule instead of a typo in
a setting.
"""

from game import aeldari_detachments, battle_size as battle_size_module
from game.end_of_turn_withdrawal import EndOfTurnWithdrawalController

RIDE_THE_WIND_LABEL = "Ride the Wind"

#: "treat the current battle round number as being one higher".
RIDE_THE_WIND_ROUND_BONUS = 1

#: "The maximum number of units you can select depends on the battle size."
WITHDRAWALS_BY_BATTLE_SIZE = {
    "incursion": 1,
    "strike_force": 2,
    "onslaught": 3,
}

#: The datasheet keyword line spelling. The rule says "VYPER" (singular, as a
#: model); the keyword line says VYPERS.
RIDE_THE_WIND_KEYWORD = "VYPERS"

#: The config constant game/detachments.py writes for Windrider Host.
SETTING = "WINDRIDER_HOST_PLAYERS"


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def withdrawal_limit(battle_size=None):
    """How many units may be pulled back at the end of one opponent turn. The
    reading of the setting is game/battle_size.py's; the table is this rule's."""
    return battle_size_module.lookup(WITHDRAWALS_BY_BATTLE_SIZE, battle_size)


def applies(squad):
    """"ASURYANI MOUNTED and VYPER units from your army".

    MOUNTED and VYPERS both live on the datasheet keyword line; ASURYANI is the
    faction line, which is why game/factions/datasheet.py grew a second field.
    THE ASURYANI HALF IS INERT ON THE BUILT ROSTER, measured: no datasheet here
    is MOUNTED without also being ASURYANI, so every unit that passes the second
    test passes the first. It is written because it is printed, and pinned with
    a hand-built unit - a probe against a real one would fail on the MOUNTED
    half and prove nothing about this half at all."""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    if unit_has_datasheet_keyword(squad, RIDE_THE_WIND_KEYWORD):
        return True
    return (aeldari_detachments.is_asuryani_unit(squad)
            and unit_has_datasheet_keyword(squad, "MOUNTED"))


def arrival_battle_round(squad, battle_round):
    """The round number to use when SETTING THIS UNIT UP, and only then.

    Returns `battle_round` untouched for anything else, so a caller may use it
    unconditionally in place of turn_tracker.battle_round at an arrival gate -
    and only at an arrival gate."""
    if battle_round is None or not applies(squad):
        return battle_round
    return battle_round + RIDE_THE_WIND_ROUND_BONUS


def is_engaged(squad, all_tokens=()):
    """"excluding units within Engagement Range of one or more enemy units"."""
    from game.squad import ENGAGEMENT_RANGE_IN, edge_distance
    mine = [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]
    if not mine:
        return False
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other.owner == squad.owner or token.is_dead():
            continue
        if any(edge_distance(a, token) <= ENGAGEMENT_RANGE_IN for a in mine):
            return True
    return False


class RideTheWindController(EndOfTurnWithdrawalController):
    """The end-of-opponent-turn withdrawal and its per-turn cap.

    Everything but the unit filter, the cap table and the words lives in
    game/end_of_turn_withdrawal.py since Hypercrypt Legion's Hyperphasing printed
    the same paragraph for NECRONS units - the chained one-prompt-per-unit offer,
    the counter reset, the Engagement Range exclusion and the withdrawal itself.

    No AI path (standing Aeldari instruction): main.py hands this controller no
    `choose`, so an `auto_players` owner is filtered out of the candidates and
    stays put - pulling a unit off the board is a whole-army judgement this
    engine does not make for Aeldari."""

    LABEL = RIDE_THE_WIND_LABEL

    def applies(self, squad):
        return applies(squad)

    def limit(self, player=None):
        return withdrawal_limit(self.battle_size)

    def prompt_for(self, squad):
        return ("%s: %s - pull it back into Strategic Reserves? (%d of %d left this turn)"
                % (RIDE_THE_WIND_LABEL, squad.name, self.remaining(), self.limit()))

    def withdraw_message(self, squad):
        return ("%s: %s rides the wind back into Strategic Reserves."
                % (RIDE_THE_WIND_LABEL, squad.name))
