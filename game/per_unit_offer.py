"""ONE PROMPT PER UNIT, chained - "each eligible unit gets its own offer".

WHY THIS EXISTS. Three abilities offer the same shape of end-of-turn choice to
every eligible unit in an army - Airborne Agility (Vespid Stingwings), Ride the
Wind's withdrawal clause (Windrider Host) and Cloudstrider (Aeldari) - and all
three wrote the same loop, and all three got it wrong the same way: they raised
a prompt for the FIRST eligible unit and then `return`ed, so a second unit was
never asked. main.py's own comment beside the call claimed the opposite
("unlike Airborne Agility, which is per unit"), and Cloudstrider wrote the
excuse out loud ("one at a time; the next end of turn offers again") - but the
next end of turn is a DIFFERENT instant of the same ability, not a second bite
at this one. A comment promising behaviour no code delivers, three times over.

REPORTED: "ich habe 2 vespiden, aber die rueckkehr in reserve wurde mir immer
nur von einem der beiden squads angeboten."

WHY CHAINED RATHER THAN ALL AT ONCE. DecisionManager is already a queue, so
simply calling request() once per unit would show them all in order and would
be shorter. It is wrong for two reasons, and both are live today:

  - Ride the Wind is CAPPED by battle size and prints the remaining count in
    its own prompt ("2 of 2 left this turn"). Built up front, every prompt in
    the batch would read the same stale number, and the ones past the cap would
    be offered and then silently do nothing - "the engine must not offer what
    it does not want chosen" (CLAUDE.md's error class 5).
  - Eligibility is re-asked before each prompt, so a unit that stopped
    qualifying because of an earlier answer is skipped instead of asked.

Chaining costs one closure and gets both for free: the next unit is offered
only once the current answer has landed, from inside DecisionManager.choose(),
which pops its entry BEFORE calling the callback - so the new request appends
behind the queue rather than recursing into it.
"""


def offer_each(decision_manager, squads, still_eligible, prompt_for, options_for):
    """Raise a prompt for the first eligible unit; the answer offers the next.

    `squads` is already in the order the prompts should appear in - this does
    not sort, because who is asked first is the caller's decision.
    `still_eligible(squad)` is re-asked immediately before each prompt.
    `prompt_for(squad)` is likewise built at that moment, so a label carrying a
    running count is accurate.
    `options_for(squad)` returns the plain (label, callback) pairs; every one of
    them continues the chain, including the decline.

    Returns True if a prompt was raised.
    """
    if decision_manager is None:
        return False
    remaining = list(squads)
    while remaining:
        squad = remaining.pop(0)
        if not still_eligible(squad):
            continue
        rest = list(remaining)

        def _chain(callback):
            def _answer():
                if callback is not None:
                    callback()
                offer_each(decision_manager, rest, still_eligible,
                           prompt_for, options_for)
            return _answer

        decision_manager.request(
            squad.owner,
            prompt_for(squad),
            [(label, _chain(callback)) for label, callback in options_for(squad)],
        )
        return True
    return False
