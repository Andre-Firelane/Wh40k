"""HOUSE RULE (user-supplied): a model already in base contact with an enemy
may not be MOVED by a Pile-In (12.03) or a Consolidation (12.07/12.08).

  User: "Modelle in Base contact duerfen weder Pile in noch consolidate moves
   durchfuehren. das muesste auch in den Grundregeln so stehen. als Base
   contact wuerde ich weniger als 0,2 Zoll Abstand definieren."

NOT A TRANSCRIPTION, and that is written down here rather than left for the
next reader to go looking for. There is no core-rules text in this repo (see
rules/README.md - only datasheets, army rules and detachments), and the ONE
transcription of 12.03 anywhere in it is a comment above _charge_per_model in
ai/agent_driver.py which reads "Each model THAT IS MOVED must end its move
closer to the closest pile-in target". That sentence permits standing still
and forbids nothing. So this enforces a CONSEQUENCE the user reads out of the
rule, and it is a house rule with a house rule's name on it.

RETREATS ARE UNAFFECTED, and this is the clause to keep an eye on. The user
raised it directly: "denke aber daran, dass bei einem rueckzug models
natuerlich den base contact verlassen koennen." A Fall Back (09.07) is its own
move mode - two of them, in fact, "fall_back" and
"retro_thrusters_fall_back" - and so are "charge", "surge", "scout", every
Battle Focus mode, and the ordinary Movement-phase move (mode None). Only the
two named below freeze anything. A version of this that gated on "is engaged"
instead of on the MOVE MODE would trap a bound unit on the table forever,
which is why FROZEN_MOVE_MODES is a named set and why the test walks every
other mode as a counter-check.

WHAT IT REPLACES was an OPTIMISATION, not a rule gate, and it covered a
fraction of this: one `continue` inside ai/agent_driver.py's phase-2 spreading
loop - AI only, pile-in only, measured against the ONE aimed target squad, at
an effective 0.15" (PILE_IN_CLEARANCE_IN 0.1 plus a bare 0.05 literal that the
same line uses for a CHARGE at 1.05"). The human side had nothing at all:
clamp_move() carried no contact term and Squad.disallowed_enemy_squads_for_move()
returns an empty set for both modes on purpose. So a player could drag any
model its full 3" in either move - which is the report.

ANY ENEMY, NOT THE AIMED TARGET. This is the one place the rule is STRICTER
than the optimisation it replaces. "In base contact with an enemy" names no
unit, and a model wedged against a non-target enemy is as physically stuck as
one against the target. The consequence is measured rather than assumed: it
can REDUCE how many models a pile-in moves, and that is the point of it.
"""

from game.squad import edge_distance

#: The user's definition, and a NEW concept here: 0.2" appears nowhere else in
#: the codebase. The nearest neighbours are PILE_IN_CLEARANCE_IN (0.1, the
#: AI's "as close as possible" aim point) and LINE_GAP_IN (0.1, shoulder to
#: shoulder in a drag formation). edge_distance() clamps at 0.0, so "< 0.2"
#: covers touching and overlapping bases alike.
BASE_CONTACT_GAP_IN = 0.2

#: The only two moves this freezes. Everything else - a Fall Back (either
#: mode), a charge, a Surge, a Scout move, a Battle Focus move, and the
#: ordinary Movement-phase move (mode None) - is untouched, so a model in base
#: contact can always retreat out of it.
FROZEN_MOVE_MODES = ("pile_in", "consolidate")


def enemy_models(squad, all_tokens):
    """Living enemy models on the board.

    `not m.is_dead()` rather than a squad-emptiness test: remove_dead_models()
    runs once per frame, so a model killed this frame is still standing in
    every list (Fehlerklasse 12) - and a corpse should not pin a model in
    place for the rest of the phase."""
    if squad is None or not all_tokens:
        return []
    return [t for t in all_tokens
            if t.squad is not None and t.squad.owner != squad.owner and not t.is_dead()]


def in_base_contact(model, enemies):
    """Is this model touching (or overlapping) any enemy base?"""
    if model is None:
        return False
    return any(edge_distance(model, enemy) < BASE_CONTACT_GAP_IN for enemy in enemies)


def is_frozen(model, squad, all_tokens, move_mode):
    """Whether the house rule forbids MOVING this model right now.

    The move-mode test comes FIRST and is the whole safety of this: outside a
    Pile-In or a Consolidation nothing is ever frozen, so no retreat, charge or
    ordinary move can be trapped by it."""
    if move_mode not in FROZEN_MOVE_MODES:
        return False
    if model is None or squad is None:
        return False
    return in_base_contact(model, enemy_models(squad, all_tokens))


def frozen_models(squad, all_tokens, move_mode):
    """Every model of `squad` the rule currently freezes - for the renderer,
    the panel hint and the log line, which all have to name the same set the
    clamp enforces."""
    if move_mode not in FROZEN_MOVE_MODES or squad is None:
        return []
    enemies = enemy_models(squad, all_tokens)
    if not enemies:
        return []
    return [m for m in squad.models
            if not m.is_dead() and in_base_contact(m, enemies)]
