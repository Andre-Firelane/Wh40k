"""ONE definition of "which controller is waiting for a model to be CLICKED,
and for WHOM" - the fourth place that question is asked and the first that
answers it once.

User: "das overwatch panel links scheint manchmal noch Fähigkeiten zu
verdecken. manchmal muss ich Einheiten für die Verteilung irgendwelcher Mortal
wounds auswählen, links steht aber overwatch. das ist sehr verwirrend."

THE OVERWATCH SCREEN WAS NOT THE CAUSE, and that matters for the fix. It is
branch #29 of 30 in ActionPanel._draw_dispatch(), BELOW both damage branches -
it cannot hide them. What it hid was the TWENTY-FIVE controllers that had no
branch at all: main.py draws draw_damage_choice_highlight() 28 times and lists
27 controllers in _any_pending_damage_choice(), and the panel asked TWO of them
(shooting and fight). Everything else fell through the whole chain and drew
whatever matched next - for a mortal wound raised at the end of the Movement
phase, that is very often Fire Overwatch, 22 branches later.

The reproduced path is one pair of lines in main.py's advance_turn_phase():
flickerjump_controller.end_of_phase() starts an ASYNCHRONOUS D6 roll, and two
lines below it fire_overwatch_controller.offer() sets CHOOSING_UNIT
synchronously. By the time the dice are acknowledged and the mortal-wound
session opens, the overwatch screen is already the panel's answer.

THE LIST IS NOT NEW
-------------------
It is _any_pending_damage_choice()'s existing tuple, lifted one level so the
panel can read the same one. Deliberately NOT a second registry - that is the
drift this module exists to remove. Modelled on game/unit_pick.py rather than
on game/proactive_stratagems.py, and the difference is real: a registry is a
list of things a player MIGHT buy, while what is needed here is a RECORD of
the one question that is open right now, already resolved against the board -
which is exactly unit_pick.pending()'s shape, with exactly the same four
readers (main.py's click branch, the left panel, the board highlight, and the
AI's own pause).

WHOSE CHOICE IT IS is why this takes owners. The AI pause's filter was written
as `owner != "Player 2"` for a starvation bug it fixed (main.py records it at
length), and that literal is wrong the moment config.AI_PLAYERS puts the human
on Player 2 - while main() already knows the answer, ai_mode.humans().

ORDER IS PART OF THE ANSWER, not an accident - the same rule
game/mortal_wound_sessions.py had to make: two replays of one battle must be
offered the same allocation first, or they allocate the same wounds
differently. So `pending()` returns the first open choice in LIST order, and
the list order is main.py's, which is construction order.

NAMED GAP: the panel says which UNIT the wound is being allocated in, not
which ABILITY raised it. Measured: of the 27 controllers only SIX expose a
name constant in their own module (isha's fury, drakolithe, harvester of
souls, monofilament snare, deadly vectors, and battle_shock_after_shooting's
per-subclass label); the other 21 live in modules with no printed name at all,
several of them shared modules serving more than one ability. Typing 21 labels
into main.py would create a second source for a name the module owns
(Fehlerklasse 10/11) for one line of panel prose. game/prompt_rule.py cannot
help either - CLAUDE.md already names the damage-allocation path as that
mechanism's benannte Grenze, because there is no PROMPT here to read a rule
name out of.
"""


class DamagePick:
    """The open allocation, already resolved against the board.

    It resolves through the controller's own choose_damage_model() and nothing
    else - the same call main.py's click branches make - so a click routed
    through the panel and a click routed through the chain cannot drift into
    two different resolution paths.
    """

    __slots__ = ("controller", "models", "squad", "owner")

    def __init__(self, controller, models, squad):
        self.controller = controller
        # The clickable models, exactly as the controller offered them. Not
        # squad.models: remove_dead_models() runs once per frame, so a model
        # that died this frame is still in the squad (Fehlerklasse 12) while
        # the controller's own list is the eligible set.
        self.models = models
        self.squad = squad
        self.owner = getattr(squad, "owner", None)

    def is_eligible(self, model):
        return model is not None and model in self.models

    def pick(self, model):
        """Resolve a click, or ignore it.

        A click on an ineligible model is IGNORED rather than guessed at -
        the established behaviour of every board-click branch in main.py."""
        if not self.is_eligible(model):
            return False
        self.controller.choose_damage_model(model)
        return True


def _choice(controller):
    """A controller's open allocation as (models, squad), or None.

    Both guards are inherited from _any_pending_damage_choice() and both are
    load-bearing: a controller can be None during construction, and a choice
    whose first model has no squad cannot name an owner."""
    if controller is None:
        return None
    choice = getattr(controller, "pending_damage_choice", None)
    if not choice:
        return None
    squad = getattr(choice[0], "squad", None)
    if squad is None:
        return None
    return choice, squad


def pending(controllers, owners=None):
    """The first open allocation belonging to `owners`, in LIST order, or None.

    `owners` None means "any owner" - the board highlight wants all of them.
    Pass a set of players (main() passes ai_mode.humans()) to get only the
    choices a human is expected to answer with a board click.
    """
    for controller in controllers:
        found = _choice(controller)
        if found is None:
            continue
        choice, squad = found
        if owners is not None and squad.owner not in owners:
            continue
        return DamagePick(controller, choice, squad)
    return None


def all_pending(controllers, owners=None):
    """Every open allocation - for the board highlight, which rings all of
    them, and for a caller that needs to know whether ANY is open."""
    out = []
    for controller in controllers:
        found = _choice(controller)
        if found is None:
            continue
        choice, squad = found
        if owners is not None and squad.owner not in owners:
            continue
        out.append(DamagePick(controller, choice, squad))
    return out
