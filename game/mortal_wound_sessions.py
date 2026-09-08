"""Draining a LIST of open MortalWoundAllocationSessions - rule 06.02 for the
abilities that can open several at once.

WHY THIS EXISTS
---------------
Sixteen modules in game/ open exactly one MortalWoundAllocationSession at a
time, keep it in `self.mortal_wound_session`, and answer main.py's three
questions with the same three members (see
game/enh_internal_grenade_racks.py's, which is the canonical copy). That shape
has sixteen instances and consolidating all of them is behaviour-neutral work
that must be measured on its own; it is not smuggled in here.

TWO modules keep a LIST instead, because their printed rules fire against
several units in one go:

  * game/drakolithe.py      - one session per bearer that spends a token
  * game/harvester_of_souls.py - one per unit struck by explosive debris

That is the SECOND consumer of a shape with no copy anywhere, which is where
this repo extracts. And it is worth extracting rather than writing twice,
because the list version has an ordering obligation the singular one does not:

  ORDER IS PART OF THE ANSWER. pending_choice() must return the FIRST parked
  session in insertion order and choose() must route into that SAME one. A
  set, a dict or a `next(... )` over an unordered source would let two replays
  of one battle allocate the same wounds to different models, which is exactly
  the kind of non-determinism this repo hunts.

WHAT WENT WRONG WITHOUT IT
--------------------------
Neither module had ANY drain. MortalWoundAllocationSession parks on
`pending_choice` whenever the target has more than one eligible model, so
against every multi-model unit the wounds were rolled, written to the log and
never applied. Against a one-model unit they resolved - which is why it
survived, and why test_event_chain_wiring.py's section 17 is a set difference
at the source rather than a behaviour test.
"""


def pending_choice(sessions):
    """The candidates the defender must choose between, or None.

    The FIRST parked session in insertion order - see the ordering note in the
    module docstring. Tolerates a None slot so a caller need not prune first.
    """
    for session in sessions or ():
        if session is None:
            continue
        choice = getattr(session, "pending_choice", None)
        if choice:
            return choice
    return None


def choose(sessions, model):
    """Answer the session `pending_choice()` just offered - the same one.

    Returns True if a session took the model. Reads the list live rather than
    caching an index, because a session may finish between the two calls.
    """
    for session in sessions or ():
        if session is None:
            continue
        if getattr(session, "pending_choice", None):
            session.choose_model(model)
            return True
    return False


def acknowledge_fnp(sessions):
    """Rule 24.12: hand a Feel No Pain roll back to whichever session is
    waiting on one. Returns True if any was."""
    for session in sessions or ():
        if session is None:
            continue
        if getattr(session, "pending_fnp", None) is not None:
            session.on_fnp_acknowledged()
            return True
    return False


def prune(sessions):
    """Drop the finished ones IN PLACE, preserving insertion order.

    In place because the controllers hand the very list to `pending_choice()`
    and `choose()`; rebinding it would leave a caller holding the old one.
    """
    if sessions is None:
        return sessions
    sessions[:] = [s for s in sessions if s is not None and not getattr(s, "done", True)]
    return sessions


def any_open(sessions):
    """Whether anything here still owes the defender a choice or a roll."""
    return any(s is not None and not getattr(s, "done", True)
               for s in sessions or ())
