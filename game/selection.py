"""Which unit the player currently has picked, and which of its models the
click landed on.

WHY THIS IS ITS OWN MODULE. The pair lived on MovementController as
`selected_squad`/`selected_model`, and the name lied: almost nothing that reads
it is a movement concern. game/ui/action_panel.py's `_draw_movement_ui` takes
`squad = movement_controller.selected_squad` and hangs the ENTIRE panel off it -
Shoot, Charge, Fight, Pile In, Consolidate, Fall Back, Battle-Shock, Explosives,
Firing Deck and every stratagem button. Six controllers additionally refuse to
act unless `movement_controller.selected_squad is <their own squad>`
(game/charge.py, game/consolidate.py, game/pile_in.py, game/fall_back.py,
game/torchstar_gambit.py, game/retro_thrusters.py). And
MovementController.can_select() carries an explicit PHASE_FIGHT special case,
which is only there because both players pick units during the Fight phase -
proof the field was already doing cross-phase duty.

So this is a rename with a home attached, not a tenth rival concept: the repo's
standing treatment for a name that acquired a second carrier (see
game/detachment_gate.py, which took has_detachment() out of a T'au module, and
game/hidden_after_shooting.py, named after the QUESTION rather than after the
first ability that asked it).

WHY MovementController STILL OWNS select(). Picking a unit also has to reset the
movement state - `_clear_move_state()` and `errors = []` - and both of those ARE
movement concerns. The AI in particular reads `movement_controller.errors` as
its success test (ai/agent_driver.py's "leave movement_controller.errors set on
failure"), and every one of its entry points calls `select(squad.models[0])`
first, so that clear is what stops a PREVIOUS unit's stale errors from being
read as THIS unit's failure. Splitting it off would be a false-success bug
(Fehlerklasse 6) in the AI, not a tidier design. This module answers only "who
is picked"; the reset stays where it belongs.

WHAT IS DELIBERATELY NOT ABSORBED, both measured rivals:

  * PregameController.selected_unit - "which card the player picked out of the
    reserves pool, awaiting a board click". A different question: that unit is
    not on the board yet. Folding the two would make `selection.squad` mean two
    things depending on the phase.
  * FiringDeckController.selected_models - the only model MULTI-select in the
    repo (which passengers lend a weapon, rule 18.06). A squad-shaped
    abstraction must not swallow it.
"""


class Selection:
    """The player's current pick. Held by MovementController, which exposes it
    through forwarding `selected_squad`/`selected_model` properties so that
    every existing reader is unchanged BY CONSTRUCTION rather than by being
    edited - roughly 25 call sites across game/, ai/ and main.py.

    That forwarding also catches the two places that write the field directly,
    bypassing select() entirely: MovementController.start_scout_move() (whose
    docstring says it deliberately isn't gated on selected_squad) and
    game/torchstar_gambit.py (which sets it so the panel draws the button for
    the right squad). Any invariant put inside select() was already not
    universal because of those two; a property is."""

    def __init__(self):
        self.squad = None
        self.model = None  # the exact model clicked; anchor for the LOS check

    @property
    def is_empty(self):
        return self.squad is None

    def holds(self, squad):
        """Is this exactly the squad that is picked? Identity, not equality -
        the same comparison the six controller preconditions already make, and
        for the same reason input_handler.py documents: two squads built from
        one datasheet are different units that can compare equal on nothing
        useful."""
        return squad is not None and self.squad is squad

    def set(self, token):
        """Pick `token`'s unit, anchored on that model. `None` clears.

        The squad-from-token derivation mirrors what select() did inline, edge
        case included: a token whose `.squad` is None leaves the squad empty
        while still recording the model, so a stray token cannot make the panel
        believe a unit is picked."""
        self.squad = token.squad if token is not None else None
        self.model = token

    def clear(self):
        self.squad = None
        self.model = None

    def reanchor(self):
        """The anchor model just died: move to a surviving squadmate, or clear
        if the whole unit is gone. Returns True if anything changed.

        Before there was a unit-wide highlight, main.py's death sweep answered
        this with a flat `select(None)` - losing the whole selection because one
        model of it died. With the unit drawn as a unit, that reads as the
        player's pick vanishing mid-turn for no reason they can see; and keeping
        the dead model as the anchor is worse still, since the line-of-sight
        highlight is measured FROM the anchor and would then be measured from a
        corpse.

        The liveness test is `not m.is_dead()`, NOT `squad.models` being empty:
        remove_dead_models() runs once per frame, so every trigger ahead of it -
        this one included - still sees the corpses in squad.models. That is
        Fehlerklasse 12, and `not squad.models` is the exact wrong test for it;
        it only becomes true a frame later."""
        if self.model is None or not self.model.is_dead():
            return False
        survivor = None
        if self.squad is not None:
            survivor = next((m for m in self.squad.models if not m.is_dead()), None)
        if survivor is None:
            self.clear()
        else:
            self.model = survivor
        return True
