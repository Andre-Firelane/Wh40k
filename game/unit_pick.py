"""ONE definition of "this decision is answered by CLICKING A UNIT ON THE
BATTLEFIELD" - 28th extraction, and the first that generalises a mechanism the
project already shipped for exactly one ability.

User: "Immer wenn man eine einheit auf dem schlachtfeld wählen muss (zb wall of
mirrors) will ich die einheit nicht aus einer liste wählen, sondern auf dem
schlachtfeld. Wie bei overwatch."

WHY THIS IS NOT A SECOND PENDING SYSTEM
---------------------------------------
The obvious build is a UnitPickController with its own queue. It was rejected:
game/decision.py's DecisionManager is already THE queue every rule in this
engine interrupts through, and a second one would immediately owe answers to
questions the first has already settled - who blocks the phase change
(_has_unresolved_declaration), which overlay owns the click when two are open
(_front_notice's ordering), and how ai/agent_driver.py's
_maybe_resolve_decision() reaches an option (by INDEX, so a pick living outside
the manager would be invisible to it and the AI would stall on a prompt it
cannot see).

So a board pick is not a new kind of pending thing. It is a pending DECISION
whose options happen to name UNITS, and this module is the one place that
answers "can this one be clicked, and which unit is behind which option".
Everything downstream - the left panel's screen, main.py's click branch, the
board highlight, the decision overlay's decision to stay out of the way - reads
`pending()` and nothing else.

THE TAG RIDES IN THE OPTION TUPLE, NOT IN A PARALLEL LIST
--------------------------------------------------------
A call site writes

    [(sq.name, lambda s=sq: self.use(s), sq) for sq in candidates]
    + [("Decline", lambda: None)]

- a THREE-tuple, the unit sitting next to its own callback. A parallel
`squads=[...]` argument was the first design and is the more dangerous one by a
wide margin: ~55 call sites would each have to keep two lists aligned by hand,
and a misalignment does not crash, it silently resolves a click on one unit
into the callback of another. In the tuple there is nothing to align.

TWO REFUSALS, AND BOTH OF THEM ARE THE SAFE DIRECTION
-----------------------------------------------------
pending() returns None - i.e. the prompt stays the ordinary list overlay -
when either guarantee fails:

1. A TAGGED UNIT IS NOT ON THE BOARD. Rapid Ingress (15.07) offers units in
   Strategic Reserves; Solid-image Projection offers a redeploy. Those have no
   token to click, so turning their prompt into a board pick would leave the
   game waiting for a click that can never happen - CLAUDE.md's Fehlerklasse 25
   (blockiert auf, nie anklickbar), the one class of bug here that is a hard
   deadlock rather than a silent no-op. Measured rather than assumed at each
   call site: this guard is generic, so a future ability that offers an
   off-board unit degrades to the list by itself.

2. THE SAME UNIT IS OFFERED TWICE. A click says "this unit", not "this option",
   so two options on one unit have no answer. Real: Rapid Ingress lists a unit
   once at 1 CP and again free under a Homing Beacon.

Falling back to the list is always answerable, so both refusals cost a nicer
interaction and never an unplayable prompt.

WHAT COUNTS AS CLICKABLE is a LIVING model in `tokens`. Not `squad.models`:
remove_dead_models() runs once per frame, so a squad wiped out this frame still
has models in it (Fehlerklasse 12) - and its rings are exactly what a player
would try to click.

"ON THE BOARD" IS ENOUGH, "ON SCREEN" IS NOT REQUIRED - checked, not assumed.
main.py's chain swallows every other click while a decision is open, so the
camera cannot be panned during a pick, and an eligible unit outside the current
crop would otherwise be unreachable. The mouse WHEEL is the escape: it is one
of the deliberately early branches (ahead of every state gate, for the reason
Fehlerklasse 15 records five times over), and camera.min_zoom is defined as the
zoom at which the WHOLE board fits. So zooming out always brings every ringed
unit into view.
"""


class UnitPick:
    """The pending board pick, already resolved against the board.

    It resolves through DecisionManager.choose(index) and nothing else - the
    same call the overlay's click handler makes - so a board click and an
    overlay click cannot drift into two different resolution paths. `choose` is
    that bound method, which is also why the panel needs no second collaborator
    just to draw a "Decline" button.
    """

    __slots__ = ("prompt", "subject", "squads", "indices", "skip_options", "choose")

    def __init__(self, prompt, subject, squads, indices, skip_options, choose):
        self.prompt = prompt
        self.subject = subject
        # The clickable units, in the order the call site offered them - the
        # panel lists them by name in this order too, so the list and the
        # highlight cannot disagree about who is eligible.
        self.squads = squads
        self.indices = indices            # id(squad) -> option index
        # The options that are NOT a unit ("Decline", "Cancel", "No more"):
        # [(label, option index)]. They become panel buttons, because the
        # overlay that used to carry them is not drawn during a pick.
        self.skip_options = skip_options
        self.choose = choose

    def index_for(self, squad):
        """The option index a click on `squad` resolves to, or None."""
        return self.indices.get(id(squad))

    def is_eligible(self, squad):
        return squad is not None and id(squad) in self.indices

    def pick(self, squad):
        """Resolve a board click. A click on an ineligible unit is IGNORED
        rather than guessed at - the established behaviour of every
        board-click branch in main.py's chain. Returns whether it took."""
        index = self.index_for(squad)
        if index is None:
            return False
        self.choose(index)
        return True


def option_squads(decision_manager):
    """The squad tagged on each pending option (None where untagged), or []."""
    if not decision_manager.is_pending:
        return []
    return [option.get("squad") for option in decision_manager.options]


def pending(decision_manager, tokens):
    """The pending decision as a board pick, or None if it is an ordinary list.

    `tokens` is the board's model list (GameState.tokens) - the ONLY thing that
    can answer "is this unit clickable", which is why the guard lives here and
    not at the ~55 call sites.
    """
    if not decision_manager.is_pending:
        return None
    options = decision_manager.options
    tagged = [(i, option.get("squad")) for i, option in enumerate(options)
              if option.get("squad") is not None]
    if not tagged:
        return None

    on_board = set()
    for token in tokens or ():
        squad = getattr(token, "squad", None)
        if squad is None:
            continue
        if getattr(token, "is_dead", None) is not None and token.is_dead():
            continue
        on_board.add(id(squad))

    indices = {}
    squads = []
    for index, squad in tagged:
        if id(squad) in indices:
            return None                    # same unit twice - see the docstring
        if id(squad) not in on_board:
            return None                    # nothing to click - Fehlerklasse 25
        indices[id(squad)] = index
        squads.append(squad)

    skip_options = [(option["label"], i) for i, option in enumerate(options)
                    if option.get("squad") is None]
    return UnitPick(
        prompt=decision_manager.prompt,
        subject=decision_manager.subject,
        squads=squads,
        indices=indices,
        skip_options=skip_options,
        choose=decision_manager.choose,
    )


def target_models(pick, tokens):
    """The models to ring on the board - "wie bei overwatch", so this feeds
    Renderer.draw_shoot_targets() and reuses that exact visual language rather
    than inventing a second "you may click this" look."""
    if pick is None:
        return set()
    return {token for token in tokens or ()
            if pick.is_eligible(getattr(token, "squad", None))}
