"""Annihilation Barge: "Malevolent Arcing".

RULE (verbatim, rules/necrons/Annihilation Barge.md):
  "In your Shooting phase, each time you select a target for this model's twin
   tesla destructor, roll one D6 for the target unit and one D6 for every other
   enemy unit within 3" of the target unit. On a 5+, the unit being rolled for
   is struck by arcing energies; after resolving all of this model's attacks
   against the target unit, each unit struck by arcing energies suffers D3
   mortal wounds."

THE THIRD CARRIER of game/mortal_wound_sweep.py - which transcribed this
ability verbatim when it was written, labelled it "(stage 8)", and grew its
`start(squad, candidates=None)` parameter FOR it. That parameter had no caller
at all until this module; this is the one it was built for, and the sweep's own
docstring says why it exists:

    "`candidates` lets a carrier whose set was decided at another moment hand
     it in - Malevolent Arcing picks its units when the target is SELECTED and
     pays them after the attacks are resolved, so re-deriving them here would
     measure the wrong board."

`range_in` IS NOT USED, and that is the one knob this carrier does not share:
the base measures its 3"/6"/12" from the BEARER, and this measures 3" from the
TARGET. candidates() and can_use() are overridden for exactly that reason.

TWO MOMENTS, AND NEITHER IS THE OBVIOUS ONE
============================================

1. ARMING - "each time you select a target". That is rule 10.02's
   select-targets step, which in this engine is ShootingController's
   _offer_target_reactions(): called from choose_target_squad() and from split
   fire's assign_current(), beside _snapshot_target_state() which freezes
   10.02's own answers at the same instant. This module rides the
   `on_target_selected` list rather than `target_reactions` - see that list's
   own note; all five of the latter are defender-side reactions, and this is
   the attacker's own ability.

   THE SET IS FROZEN HERE AND THE DICE ARE ROLLED LATER, which is a stated
   deviation rather than an oversight. What the printed text pins to this
   instant is WHICH UNITS are rolled for, and that is what is captured; the
   dice themselves are rolled at payment because (a) this engine has never put
   a die on the table inside the select-targets step, (b) a reaction may still
   undo the selection that triggered it (error class 9b), and a handful
   belonging to an undone selection would have to be un-rolled, and (c)
   nothing between the two moments can change a die's meaning - the set is
   frozen and the threshold is a constant.

2. PAYING - "after resolving all of this model's attacks against the target
   unit", i.e. on_squad_finished_shooting, once per activation. NOT
   _finish_group(), and three reasons in order of weight:

     * The DiceManager holds ONE roll. _finish_group() is reached with weapon
       groups still pending and returns straight into CHOOSING_WEAPON; opening
       a gate handful plus a wound roll plus a 06.02 allocation there would
       interleave with the next group's hit roll.
     * In the common case _finish_group() is EARLY. Without split fire a unit
       picks ONE target for the whole activation, so "all of this model's
       attacks against the target unit" includes the gauss cannon that has not
       fired yet.
     * Late can only be safe; early can be wrong. Mortal wounds landing
       mid-activation can wipe out a unit the Barge is still shooting at.

   THE PRICE, NAMED: with SPLIT FIRE at two different targets, the second
   target's arcing is paid at the end of the activation rather than the moment
   the destructor finishes with it. Later than printed, never earlier.

"FOR THIS MODEL'S TWIN TESLA DESTRUCTOR" NEEDS A THIRD TOUCH
=============================================================
In this engine a unit selects its TARGET before its WEAPON, so at arming time
nothing yet knows whether the destructor will fire at that target. The answer
is ShootingController._resolved_weapon_names_this_activation, read through
resolved_weapon_against(): at payment, an armed target pays only if a weapon of
that printed name actually resolved attacks against it. A unit that picked a
target and then chose not to fire the destructor at it pays nothing, which is
what the printed text says.

"IN YOUR SHOOTING PHASE" excludes Fire Overwatch (15.08/15.09), so a reactive
activation never arms. It could not pay either - on_squad_finished_shooting
only fires for real activations - but arming anyway would leave a stale entry
behind, and the honest place to answer a printed clause is where it is printed.

NO PROMPT, NO auto_players SPLIT: there is no "you can" anywhere in the text
and no target choice, so this is an event and not an offer - Drain Life's
reading, for the same absent two words.
"""

from game.dice_notation import D3
from game.mortal_wound_sweep import MortalWoundSweepController
from game.squad import edge_distance

MALEVOLENT_ARCING_RANGE_IN = 3.0      # "within 3" of the target unit"
MALEVOLENT_ARCING_THRESHOLD = 5       # "on a 5+"
MALEVOLENT_ARCING_SIDES = 3           # "D3 mortal wounds"
MALEVOLENT_ARCING_WEAPON = "Twin Tesla Destructor"


def _alive(squad):
    return [m for m in squad.models if not m.is_dead()] if squad else []


def has_malevolent_arcing(squad):
    """Whether this unit contains a living Annihilation Barge."""
    from game.mortal_wound_abilities import bearers
    return bool(bearers(squad, "malevolent_arcing"))


class MalevolentArcingController(MortalWoundSweepController):
    label = "Malevolent Arcing"
    flag = "malevolent_arcing"
    threshold = MALEVOLENT_ARCING_THRESHOLD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # id(attacking_squad) -> [(target_squad, [candidate, ...]), ...],
        # frozen at target selection and spent at the end of the activation.
        self._armed = {}

    def wounds_for(self, roll):
        """One band. `roll` only ever reaches here having met the 5+."""
        return D3()

    def can_use(self, squad):
        """This carrier is never started from the board - its candidates come
        from a moment that has already passed, so there is nothing to derive
        and nothing to offer. start_all() is its only entry point."""
        return False

    def candidates(self, squad):
        """Never derived. See can_use()."""
        return []

    # ------------------------------------------------------------ 1. arming
    def arcing_candidates(self, attacking_squad, target_squad):
        """"the target unit and every OTHER enemy unit within 3" of the target
        unit" - measured from the TARGET, unit to unit.

        "Enemy" is an enemy of the Barge, so a friendly unit standing next to
        the target is never struck. The target itself is always a candidate,
        whatever its distance from anything."""
        if target_squad is None or attacking_squad is None:
            return []
        out = [target_squad]
        for other in self._enemy_squads_of(attacking_squad):
            if other is target_squad:
                continue
            # Unit to unit, model edge to model edge - the house idiom for a
            # "within N of that unit" clause (game/aux_guided_fire.py's).
            if any(edge_distance(a, b) <= MALEVOLENT_ARCING_RANGE_IN
                   for a in _alive(other) for b in _alive(target_squad)):
                out.append(other)
        return out

    def _enemy_squads_of(self, squad):
        from game.mortal_wound_abilities import enemy_squads
        return enemy_squads(squad, self._tokens())

    def on_target_selected(self, attacking_squad, target_squad, reactive=False):
        """ShootingController's select-targets hook. Records and returns
        nothing - it never interrupts the attacker."""
        if reactive:
            return False        # "In YOUR Shooting phase" - not Fire Overwatch
        if not has_malevolent_arcing(attacking_squad) or target_squad is None:
            return False
        # A different unit is shooting now, so any activation this list still
        # remembers is over - cancel() and a reactive activation both leave
        # without reaching the payment hook.
        for key in [k for k in self._armed if k != id(attacking_squad)]:
            del self._armed[key]
        armed = self._armed.setdefault(id(attacking_squad), [])
        if any(t is target_squad for t, _c in armed):
            return False        # the same target selected twice in one activation
        armed.append((target_squad, self.arcing_candidates(attacking_squad, target_squad)))
        return True

    # ------------------------------------------------------------ 2. paying
    def on_squad_finished_shooting(self, squad, hit_squads=None, shooting=None):
        """"after resolving all of this model's attacks against the target
        unit". `shooting` is the ShootingController, which is the only thing
        that knows WHICH weapons resolved against which target."""
        armed = self._armed.pop(id(squad), [])
        if not armed:
            return False
        owed = []
        for target_squad, candidates in armed:
            if shooting is not None and not shooting.resolved_weapon_against(
                    MALEVOLENT_ARCING_WEAPON, target_squad):
                # A target the destructor never fired at - the printed clause
                # "for this model's twin tesla destructor".
                self._log("%s (%s): the twin tesla destructor did not fire at "
                          "%s, so nothing arcs." % (self.label, squad.name,
                                                    target_squad.name))
                continue
            owed.append((squad, candidates))
        if not owed:
            return False
        return self.start_all(owed)
