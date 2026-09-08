'''"TARGET: One <X> unit from your army" - ONE prompt, one TAGGED option per
candidate, answered by CLICKING THE UNIT.

REPORTED: "cost of victory wird mir pauschal angeboten, aber ich habe 3 guardian
squads. ich kann nicht waehlen welchen squad zurueck in reserve schicken will.
es muss auf dem feld angeklickt werden."

Measured before anything was changed: with three eligible Guardian Defenders on
the board the offer opened a prompt naming ONE of them - the first in sort order
- with the options `['Use (1 CP)', 'Decline']`, none of them tagged with a
squad, so unit_pick.pending() returned None and it could never be a board click.
The player was asked to confirm a choice the engine had already made for them.

FOUR STRATAGEMS HAD THIS SHAPE, and they all print the same TARGET line:

    Cost of Victory      One GUARDIANS unit from your army
    Webway Tunnel        One ASURYANI INFANTRY unit from your army ...
    Skyborne Sanctuary   One unengaged ASURYANI unit from your army ...
    Overflight           One ASURYANI MOUNTED unit from your army ...

"One <X> unit from your army" is a CHOICE THE PLAYER MAKES. Each of the four
looped over the eligible units, raised a prompt for the first, and `return`ed -
so the other two were never mentioned, and the one that was could only be
accepted or declined. The fifth Stratagem with that same printed line, Kauyon's
Wall of Mirrors, was already built correctly (one request, `[(s.name, cb, s)
for s in candidates]`), which is what made the four legible as a defect rather
than a design.

WHY THIS IS NOT game/per_unit_offer.py
--------------------------------------
That module answers a DIFFERENT question and the two are easy to confuse,
because the wrong code for both looks the same. `offer_each()` is "EACH
eligible unit gets its OWN offer" - an ABILITY that triggers per unit (Airborne
Agility, Ride the Wind, Cloudstrider), N prompts, chained so a running count
stays accurate. This is "the player picks ONE of them" - a STRATAGEM, ONE
prompt, N options.

The four broken controllers were not written to either shape: they raised one
prompt about one arbitrarily-chosen unit, which answers neither question.

WHY ONE REQUEST AND NOT A CHAIN
-------------------------------
per_unit_offer chains deliberately, because eligibility can change between
answers and Ride the Wind prints a running count. Neither applies to a single
choice: the player picks once, and every candidate has to be visible AT THE SAME
TIME for a board pick to mean anything - the rings are the prompt.

THE WINDOW STAYS WITH THE CALLER, and that is on purpose. Arming a PhaseWindow
before testing can_use() is two lines, but WHO is offered a boundary reaction is
the printed WHEN ("your opponent's Fight phase" offers the other side; "the end
of THE Fight phase" belongs to nobody and offers both), and that differs per
Stratagem. Folding it in here would mean a flag per WHEN clause, and this module
would be answering a question it cannot see.
'''


def offer_one_of(decision_manager, player, candidates, prompt, action,
                 auto_players=(), decline_label="Decline", is_stratagem=False,
                 label_for=None, subject=None):
    """Raise ONE prompt offering `candidates`, each tagged with its own squad.

    `candidates` is offered in the order given - the caller decides who is
    listed first, and the board highlight uses the same order.
    `action(squad)` is what accepting that option does.

    Returns True if a prompt was raised. False - so the caller can close its
    window - when there is nothing to offer, nobody to ask, or the player is
    the AI: taking a unit off the board (or moving it) unasked is a real cost,
    and none of the four callers has an AI path (standing Aeldari instruction).

    The third slot in each tuple is what makes this answerable on the board;
    game/unit_pick.py decides whether it really can be clicked and falls back
    to the ordinary list if not (a candidate that is off the board, or named
    twice). Every caller here offers units that are ON the board by
    construction - each one's can_use() requires a living model - so the
    fallback is a net, not the expected path.
    """
    if not candidates or decision_manager is None:
        return False
    if player in (auto_players or ()):
        return False
    label = label_for or (lambda squad: squad.name)
    decision_manager.request(
        player,
        prompt,
        [(label(squad), (lambda s=squad: action(s)), squad) for squad in candidates]
        + [(decline_label, lambda: None)],
        is_stratagem=is_stratagem,
        subject=subject,
    )
    return True
