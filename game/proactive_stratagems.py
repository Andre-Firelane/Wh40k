"""One panel parameter for every proactive detachment Stratagem.

WHY THIS EXISTS
---------------
ActionPanel.draw() already takes forty-odd controllers, through a THREE-STAGE
chain (draw -> _draw_dispatch -> _draw_movement_ui) that is positional for most
of its length - the file carries a scar comment about a parameter added to two
of the three signatures and not the third, which crashed every frame. The T'au
detachments add nineteen more Stratagems. Threading nineteen parameters through
that chain would be nineteen chances to make exactly that mistake, and the next
detachment would make it twenty.

So the panel takes ONE list instead. A controller joins it by exposing three
methods, and the panel needs no edit at all:

    can_use(squad) -> bool      the WHEN/TARGET lines, already required of
                                every Stratagem controller here
    use(squad) -> bool          spends the CP and applies the effect
    panel_label(squad) -> str   what the button says

The phase gate lives in can_use(), as it already does for every existing
Stratagem, so one loop in one place renders the right buttons in the right
phase without the panel knowing which phase anything belongs to.

WHY NOT A BASE CLASS
--------------------
Nothing here is shared BEHAVIOUR - each Stratagem's can_use() is its own
printed WHEN and TARGET, and its use() its own effect. What is shared is only
the shape of the call, so this is a registry over a duck-typed protocol rather
than an inheritance root that would tempt someone to put a rule in it.
"""


class ProactiveStratagems:
    """The proactive detachment Stratagems a human can buy from the panel."""

    def __init__(self, controllers=()):
        self.controllers = [c for c in controllers if c is not None]

    def add(self, controller):
        """Register one. Returns it, so main.py can build and register in one
        expression without naming the controller twice."""
        if controller is not None:
            self.controllers.append(controller)
        return controller

    def usable_for(self, squad):
        """Every registered Stratagem this unit could buy right now.

        Order is registration order, which is the order they appear on the
        panel - stable, so a button does not move under the cursor between
        frames because a dict reordered."""
        if squad is None:
            return []
        return [c for c in self.controllers if c.can_use(squad)]

    def buttons_for(self, squad):
        """[(label, callback)] for the panel. The callback closes over THIS
        controller and squad, so a caller cannot accidentally bind the loop
        variable - the classic late-binding bug in a button loop."""
        return [(c.panel_label(squad), (lambda c=c, s=squad: c.use(s)))
                for c in self.usable_for(squad)]

    def any_usable(self, squad):
        """For the panel's "nothing to do here" hint, which must not claim
        there is nothing to do while one of these is on offer."""
        return bool(self.usable_for(squad))
