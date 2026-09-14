"""The Orks' "riled up" state - the second bullet of the army rule Waaagh!.

PRINTED (rules/orks/army_rules.md, 2026-09 codex):

    Friendly ORKS units with this ability can:
    - Re-roll advance rolls.
    - Become riled up, as stated in other rules.
    While a unit is riled up:
    - That unit has 5+ InSv.
    - That unit's ranged attacks have [ASSAULT].
    - When that unit is selected to make an advance move, that advance move
      does not prevent that unit from being eligible to declare a charge.

WHAT IT REPLACED. The user-supplied Waaagh! this engine played until then was a
live state per PLAYER ("until the start of your next Command phase", +1 S and
+1 A in melee, a 5+ invulnerable save, charge after Advancing), held by a
WaaaghController and threaded as a `waaagh=` argument through the damage
sessions, the Feel No Pain roll and both attack controllers. The new rule is a
state per UNIT: War Cry (game/war_cry.py) makes the whole army riled up at once,
and other rules - War Horde's Da Boss is Watchin', the Warbosses' datasheet
abilities - make ONE unit riled up for their own duration. So the state lives on
the Squad, and nothing is threaded any more.

A STORED DEADLINE AND A STAMPED FLAG, the arrangement Mont'ka's Killing Blow
already uses (game/montka.py). The readers - game/invulnerable_save.py,
game/coldstar.py's weapon_has_assault(), game/move_exceptions.py - are handed a
model or a squad and nothing else, so they cannot ask the turn tracker whether a
deadline has passed. Instead:

  * Squad.riled_up_expires_turn is the DEADLINE, a turn serial (see
    turn_serial()). It is what a grant writes and what a save keeps
    (activation_state.SQUAD_FLAGS) - a War Cry is a once-per-battle spend, and a
    mid-turn save that dropped it would take the army's riled up away.
  * Squad.riled_up is the DERIVED answer every reader asks. refresh() stamps it
    at the start of every phase (main.py, beside the Power Matrix stamp) and
    grant() stamps it at once, so a unit is riled up in the same frame the
    ability is used. In activation_state.SQUAD_FLAGS_EXCLUDED, because the next
    stamp overwrites it.

Both deadlines the printed rules use land on a turn BOUNDARY - "until the end of
the next turn" and "until the start of your next turn" - and a turn boundary is
always a phase boundary, so a per-phase stamp can never read a stale answer.

ONLY A UNIT WITH THE ABILITY CAN BE RILED UP. The bullet list is what "Friendly
ORKS units with this ability can" do, so grant() refuses anything else - a
Necron unit next to a Warboss is not riled up by a rule that names "this unit".
"""

import copy

#: "That unit has 5+ InSv."
RILED_UP_INVULNERABLE_SAVE = "5+"


def turn_serial(turn_tracker):
    """Every player turn of the battle, numbered: round 1's first turn is 0,
    its second is 1, round 2's first is 2, and so on.

    One number per TURN rather than per round, because both printed deadlines
    are turn deadlines and a battle round holds two turns (rule 07.03). A
    tracker that has not started the battle (round 0) numbers below zero, which
    keeps every comparison below meaningful instead of special-casing it."""
    battle_round = getattr(turn_tracker, "battle_round", 1) or 0
    index = getattr(turn_tracker, "turn_index_in_round", 0) or 0
    return (battle_round - 1) * 2 + index


def until_end_of_next_turn(turn_tracker):
    """War Cry's duration: the current turn and the one after it. The deadline
    is the serial of the turn after THAT, so the unit stops being riled up the
    moment that turn begins."""
    return turn_serial(turn_tracker) + 2


def until_start_of_your_next_turn(turn_tracker, player):
    """The Warbosses' and Da Boss is Watchin's duration. From inside your own
    turn your next turn is two away; from inside your opponent's it is the very
    next one - the difference a single "+2" would get wrong."""
    serial = turn_serial(turn_tracker)
    owner = getattr(turn_tracker, "turn_owner", None)
    return serial + (2 if owner == player else 1)


def has_ability(squad):
    """Whether this unit has the Waaagh! ability at all - see game/waaagh.py,
    which owns the question."""
    from game.waaagh import has_waaagh
    return has_waaagh(squad)


def grant(squad, expires_turn, turn_tracker=None):
    """Make `squad` riled up until turn serial `expires_turn` begins.

    Returns whether it took. A second grant never SHORTENS a first: the later
    deadline wins, because two rules that each say "riled up until X" leave the
    unit riled up until the later X. Stamps the flag at once, so the unit is
    riled up in the frame the ability was used rather than at the next phase."""
    if squad is None or not has_ability(squad):
        return False
    current = getattr(squad, "riled_up_expires_turn", None)
    squad.riled_up_expires_turn = (expires_turn if current is None
                                   else max(current, expires_turn))
    if turn_tracker is not None:
        refresh((squad,), turn_tracker)
    else:
        squad.riled_up = True
    return True


def refresh(squads, turn_tracker):
    """Re-derive Squad.riled_up for every unit in `squads` from its stored
    deadline. A deadline that has passed is also CLEARED, so an expired grant
    is not carried through every later save."""
    serial = turn_serial(turn_tracker)
    for squad in squads or ():
        if squad is None:
            continue
        deadline = getattr(squad, "riled_up_expires_turn", None)
        active = deadline is not None and serial < deadline and has_ability(squad)
        if deadline is not None and serial >= deadline:
            squad.riled_up_expires_turn = None
        squad.riled_up = bool(active)


def is_riled_up(squad):
    """The one question every reader asks."""
    return bool(squad is not None and getattr(squad, "riled_up", False))


def grants_assault(squad):
    """"That unit's ranged attacks have [ASSAULT]" - read by
    game/coldstar.py's weapon_has_assault(), which is the only thing that
    decides whether a unit that Advanced may still shoot (rule 10.05). The
    adjuster chain's copy below is the other reader; a grant wired to only one
    of the two is the bug test_event_chain_wiring.py section 7 exists for."""
    return is_riled_up(squad)


def adjusted_weapon(weapon, squad):
    """[ASSAULT] on this unit's ranged weapons while it is riled up. A copy, so
    the shared WeaponProfile instance is never mutated."""
    from game.weapons import RANGED
    if weapon is None or not is_riled_up(squad):
        return weapon
    if getattr(weapon, "weapon_type", None) != RANGED or weapon.assault:
        return weapon
    granted = copy.copy(weapon)
    granted.assault = True
    return granted
