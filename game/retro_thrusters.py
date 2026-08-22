"""The Twin Lance's own "Retro-thrusters" ability, as supplied by the user
(not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/exemplars_of_montka.py and
game/neocapacitor_shields.py for this datasheet's other two).

RULE: At the end of the Fight phase, if this unit was eligible to fight this
phase, this unit can either make a Normal move of up to 6" or a Fall Back
move.

WHY BOTH HALVES MATTER
----------------------
They are not two flavours of the same thing. A Normal move must end
unengaged (confirm_move()'s generic branch), which a unit standing in combat
usually cannot manage - so for the case this ability is actually FOR
(disengaging after a fight), the Fall Back half is the one that works. The
Normal-move half is what a unit that fought and then had its opponent wiped
out uses to reposition. Offering only one would quietly remove half the
ability.

"ELIGIBLE TO FIGHT THIS PHASE"
------------------------------
Read off FightController, which already owns that question (12.04) -
is_eligible_to_fight() was made public for War Horde's Unbridled Carnage and
answers exactly this, independent of whose sub-turn it is. Deliberately NOT
"actually fought": the text says eligible, and a unit can be eligible and
still end up passing (the Appendix's "Eligible to Fight, But Unable").

Because eligibility is evaluated per model position and combat resolution
changes those positions, the answer is latched the moment the Fight phase's
last activation ends rather than recomputed afterwards - by then the enemy
may be dead and the unit no longer "eligible" by inspection, which is
precisely the case the ability is meant to cover.

WHEN IT IS OFFERED
------------------
"At the end of the Fight phase" is the window that opens once no unit on
either side can still fight - FightController.state == DONE. That is the
same instant game/consolidate.py's own "after the Fight step" already uses,
and this is offered the same way: as an Action-panel button on the selected
unit, not as a modal interruption.

A panel button rather than a DecisionManager prompt because this is the
owner's own optional move, like Consolidate - not a reaction to something
the opponent did (Stim Injectors, Grav-Inhibitor Field) where the game has
to stop and ask. The Fight phase is shared (12.04), so a qualifying unit on
either side gets the button during its owner's own selection.

...WHICH IS WHY THE TURN HAS TO WAIT FOR IT
-------------------------------------------
Fight is the last phase (07.02), so "the end of the Fight phase" and "the
end of the turn" are the same instant - and the turn-taker is the one who
closes it. With auto-play on, the AI ended its turn the moment
FightController reached DONE, which is exactly when this offer opens, so a
human unit on the receiving end never got a single frame to use it. User
report: "das spiel muss mir die möglichkeit lassen bei meinen twin lance am
ende des gegnerischen zuges noch ihre bewegung zu machen. das wurde jetzt
einfach übersprungen." (Verified from a real log: the Twin Lance fought in
Player 2's Fight phase and "Player 2's turn ends." followed with no offer in
between. The same window was already known to be one-or-two frames wide for
Consolidate.)

pending_squads()/has_pending_for_opponent_of() below are what
ai/agent_driver.py holds its turn-end on. That wait terminates because
every offer has an explicit answer: take one of the two moves, or press the
Skip button that calls decline(). It is not an open-ended "wait until the
opponent is finished" - the bounded-ness is the whole reason decline() got
a button of its own here, and announce_wait_once() says out loud that the
turn is waiting, since the button itself is only visible once the unit is
selected.
"""


def unit_has_retro_thrusters(squad):
    """True while at least one live model with the ability is in the unit -
    the same rule 19.04 reading every other datasheet ability here uses."""
    if squad is None:
        return False
    return any(m.profile.retro_thrusters for m in squad.models if not m.is_dead())


class RetroThrustersController:
    """Tracks which units were eligible to fight this phase, then offers the
    move at the end of it.

    The eligibility latch is the whole reason this is a controller rather
    than a function: nothing else in the engine remembers, after the Fight
    phase has resolved, who was eligible when it began."""

    def __init__(
        self, fight_controller=None, movement_controller=None, decision_manager=None,
        turn_tracker=None, all_tokens=None, game_log=None,
    ):
        self.fight_controller = fight_controller
        self.movement_controller = movement_controller
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self._eligible_this_phase = set()  # id(squad) latched while the phase runs
        self._used_this_phase = set()
        self.active_squad = None          # the unit whose Retro-thrusters move is open, if any
        self._fall_back = False
        self._wait_announced = set()      # owners already told the turn is being held for them

    def reset_fight_phase(self):
        """A new Fight phase: nothing latched, nothing used yet."""
        self._eligible_this_phase = set()
        self._used_this_phase = set()
        self.active_squad = None
        self._fall_back = False
        self._wait_announced = set()

    def note_eligibility(self):
        """Latch which units with this ability are eligible to fight right
        now. Called every frame during the Fight phase - cheap, and it has
        to be sampled while the phase is still running (see the module
        docstring on why it cannot be recomputed at the end)."""
        if self.fight_controller is None:
            return
        for token in self.all_tokens:
            squad = token.squad
            if squad is None or not unit_has_retro_thrusters(squad):
                continue
            if self.fight_controller.is_eligible_to_fight(squad):
                self._eligible_this_phase.add(id(squad))

    def _squads_with_ability(self):
        seen = []
        for token in self.all_tokens:
            squad = token.squad
            if squad is not None and unit_has_retro_thrusters(squad) and squad not in seen:
                seen.append(squad)
        return seen

    def can_use(self, squad):
        if squad is None or self.movement_controller is None:
            return False
        if not unit_has_retro_thrusters(squad):
            return False
        if id(squad) not in self._eligible_this_phase:
            return False  # "if this unit was eligible to fight this phase"
        if id(squad) in self._used_this_phase:
            return False
        return any(not m.is_dead() for m in squad.models)

    def available_moves(self, squad):
        """Which of the two halves are on offer for this unit right now.

        A Normal move has to END unengaged (confirm_move()'s generic
        branch), so it is not offered to a unit still in combat - listing a
        choice that can never be confirmed is the kind of dead option this
        project has removed elsewhere. Fall Back is the half that works
        there, and is exactly why the ability offers two."""
        if not self.can_use(squad):
            return []
        moves = []
        if not squad.is_engaged(self.all_tokens):
            moves.append("normal")
        moves.append("fall_back")
        return moves

    def pending_squads(self, owner=None):
        """Units that still have an unanswered Retro-thrusters offer right
        now - either the button is still on the table (can_use) or the move
        is already open and not yet confirmed/cancelled.

        This is the "end of the Fight phase" window seen from the outside,
        and it exists because Fight is the LAST phase (07.02): whoever ends
        the turn closes this window for BOTH players. See
        ai/agent_driver.py's take_one_action(), which holds its own turn-end
        while the opponent still has one of these open."""
        out = []
        for squad in self._squads_with_ability():
            if owner is not None and squad.owner != owner:
                continue
            if self.can_use(squad) or squad is self.active_squad:
                out.append(squad)
        return out

    def has_pending_for_opponent_of(self, player):
        """Whether anyone OTHER than `player` still has an offer open."""
        return any(s.owner != player for s in self.pending_squads())

    def announce_wait_once(self, player):
        """Log, once per owner per Fight phase, that the turn is being held
        open for them - without it the game just looks stalled, since the
        button only shows once they select the unit."""
        if self.game_log is None:
            return
        for squad in self.pending_squads():
            if squad.owner == player or squad.owner in self._wait_announced:
                continue
            self._wait_announced.add(squad.owner)
            self.game_log.add(
                f"{squad.owner}: {squad.name} can still use Retro-thrusters - "
                f"select it to move or skip; the turn ends once you do."
            )

    def start(self, squad, fall_back=False):
        """Opens the move. Returns whether it actually opened."""
        if not self.can_use(squad):
            return False
        wanted = "fall_back" if fall_back else "normal"
        if wanted not in self.available_moves(squad):
            return False
        self._make_start(squad, fall_back)()
        return self.active_squad is squad

    def decline(self, squad):
        """Explicitly pass on the move, so the button stops being offered."""
        if self.can_use(squad):
            self._used_this_phase.add(id(squad))

    def _make_start(self, squad, fall_back):
        def start():
            self._used_this_phase.add(id(squad))
            # select() takes a TOKEN, not a squad - any live model of the
            # unit selects the whole unit.
            token = next((m for m in squad.models if not m.is_dead()), None)
            self.movement_controller.select(token)
            if self.movement_controller.selected_squad is not squad:
                return  # selection refused (not this player's, already moving) - nothing opened
            self.movement_controller.start_retro_thruster_move(squad, fall_back=fall_back)
            self.active_squad = squad
            self._fall_back = fall_back
            if self.game_log is not None:
                kind = "Fall Back move" if fall_back else 'Normal move (up to 6")'
                self.game_log.add(f"{squad.owner}: {squad.name} uses Retro-thrusters - {kind}.")

        return start

    def _make_decline(self, squad):
        def decline():
            self._used_this_phase.add(id(squad))

        return decline

    def confirm(self):
        """Wraps MovementController.confirm_move(): the move only counts as
        finished once it confirms without errors, exactly like every other
        move in this engine - a rejected one stays open so the player can
        reposition."""
        if self.active_squad is None or self.movement_controller is None:
            return False
        self.movement_controller.confirm_move()
        if self.movement_controller.move_mode is None:
            self.active_squad = None
            return True
        return False

    def cancel(self):
        if self.active_squad is None or self.movement_controller is None:
            return
        self.movement_controller.cancel_move()
        self.active_squad = None
