"""The Overlord's "Resurrection Orb" wargear.

RULE (printed, word for word):
  "Once per battle, per unit. At the end of any phase, you can use this
   ability. If you do, this unit resurrects: When a unit resurrects, that
   unit's Reanimation Protocols activate, but that unit heals D6 wounds
   (instead of D3 wounds). You cannot resurrect more than one unit per turn."

THIS IS THE ARMY RULE WITH A BIGGER DIE, and it is written that way: the whole
effect is game/reanimation_protocols.py's reanimate(), handed a D6 instead of a
D3. Nothing about healing, reviving, placement or the starting-strength cap is
restated here - a second copy of that arithmetic is exactly the drift this repo
keeps consolidating away.

THREE SEPARATE LEDGERS, because the printed text really does impose three
different limits, and collapsing them would be wrong in both directions:

  * "once per battle, PER UNIT" - keyed on the unit, never cleared;
  * "not more than one unit per TURN" - keyed on the player, cleared each turn;
  * "at the end of ANY phase" - so it is offered at every phase boundary, not
    only in the Command phase like the army rule itself.

THE AI'S ANSWER IS DETERMINISTIC and gated on the shared recoverable_wounds()
measure: use it once the unit could actually turn at least
RESURRECTION_ORB_MIN_RECOVERABLE wounds into something. A D6 averages 3.5, so
spending a once-per-battle orb on a unit that can only use one wound wastes it,
and waiting for a bigger loss is the whole point of holding it.
"""

from game import ai_mode, reanimation_protocols

RESURRECTION_ORB_DICE_SIDES = 6
#: How much a unit must be able to recover before the AI spends the orb on it.
#: Deliberately below the D6's 3.5 average - the orb is worth using on a real
#: loss, not only on a catastrophic one.
RESURRECTION_ORB_MIN_RECOVERABLE = 4


def bearers(squad):
    """The models carrying an orb. Set by the Gear item in
    game/factions/necrons.py, so it is a token flag, not a profile one."""
    return [m for m in getattr(squad, "models", ()) or ()
            if getattr(m, "resurrection_orb", False) and not m.is_dead()]


def has_orb(squad):
    return bool(bearers(squad))


class ResurrectionOrbController:
    """Offered at every phase boundary - "at the end of any phase"."""

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, position_valid=None, auto_players=(),
                 placer=None):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.position_valid = position_valid
        self.auto_players = ai_mode.players(auto_players)
        # ReturnPlacementController - rule 01.02.03's "set up" half. This is
        # the OTHER door into reanimate() besides the army rule's own
        # controller; each door needs its own placer, or a human watches the
        # engine seat their models. Assigned in main.py rather than passed in,
        # because this controller is built ~600 lines before the placer exists.
        self.placer = placer
        self._used_squads = set()    # id(squad) - once per battle, per unit
        self._used_this_turn = set()  # player - one unit per turn
        # id(squad) -> the recoverable-wound count when the player last said
        # no. See declined_unchanged() - this is what stops the prompt
        # coming back at every single phase boundary.
        self._declined_at = {}
        self._pending = None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    @property
    def is_busy(self):
        return self._pending is not None

    def reset_turn(self):
        """"You cannot resurrect more than one unit per turn"."""
        self._used_this_turn.clear()

    def can_use(self, squad):
        if self._pending is not None or squad is None or not has_orb(squad):
            return False
        if id(squad) in self._used_squads or squad.owner in self._used_this_turn:
            return False
        return reanimation_protocols.recoverable_wounds(squad) > 0

    def declined_unchanged(self, squad):
        """Has the player already said no to THIS unit on THIS board?

        The printed WHEN is "at the end of any phase", and main.py duly offers
        it at every phase boundary - five times per turn, each one taking over
        the whole left panel as a board pick. With no memory of a refusal that
        is a prompt after very nearly every action, which is how it was
        reported: "ich werde nach jeder aktion wiederholt nach ressurrection
        orb gefragt".

        So a decline is remembered against the number the choice actually
        turns on. The offer comes back as soon as there is MORE to recover
        than there was when it was turned down - i.e. after new losses, which
        is the only thing that can change the answer. Nothing is lost: at an
        unchanged board the question has an unchanged answer.

        Deliberately NOT cleared in reset_turn(): a new turn on an unchanged
        board is still an unchanged board, and asking again there is the
        behaviour that was reported.
        """
        if squad is None:
            return False
        was = self._declined_at.get(id(squad))
        if was is None:
            return False
        return reanimation_protocols.recoverable_wounds(squad) <= was

    def _decline(self, squad):
        self._declined_at[id(squad)] = reanimation_protocols.recoverable_wounds(squad)
        return True

    def is_worth_using(self, squad):
        """The AI's deterministic gate - see this module's docstring."""
        return (self.can_use(squad)
                and reanimation_protocols.recoverable_wounds(squad) >= RESURRECTION_ORB_MIN_RECOVERABLE)

    def offer_at_end_of_phase(self, squads, player):
        """Returns True if anything was used or prompted. One unit at a time:
        the per-turn limit means a second offer could never be taken anyway."""
        candidates = sorted((s for s in squads if s.owner == player and self.can_use(s)
                             and not self.declined_unchanged(s)),
                            key=lambda s: s.name)
        if not candidates:
            return False
        if player in self.auto_players or self.decision_manager is None:
            worth = [s for s in candidates if self.is_worth_using(s)]
            if not worth:
                return False
            best = max(worth, key=lambda s: (reanimation_protocols.recoverable_wounds(s), s.name))
            return self._use(best)
        # EVERY candidate, one option each - not candidates[0] as a bare
        # yes/no. The AI ranks by recoverable_wounds a few lines up and takes
        # the best unit; the human used to be shown the ALPHABETICALLY FIRST
        # one and given no way to pick another, so the two sides were not
        # playing the same rule (user: "die Funktion selbst soll nicht
        # deterministisch sein"). The wound count rides along in each label,
        # because it is the number the choice turns on and a squad name does
        # not carry it.
        options = [
            (f"{s.name} ({reanimation_protocols.recoverable_wounds(s)} wound(s) to recover)",
             (lambda target=s: self._use(target)), s)
            for s in candidates
        ]
        # The decline is RECORDED, not dropped - see declined_unchanged().
        # `candidates` is captured so refusing the prompt refuses it for every
        # unit it offered, which is what the player just said.
        options.append(("Decline", (lambda group=tuple(candidates): [
            self._decline(s) for s in group] and True)))
        self.decision_manager.request(
            player,
            "Use the Resurrection Orb? (reanimates D6 instead of D3)",
            options,
        )
        return True

    def _use(self, squad):
        if not self.can_use(squad):
            return False
        self._used_squads.add(id(squad))
        self._used_this_turn.add(squad.owner)
        self._pending = squad
        if self.dice_manager is None:
            self._resolve(RESURRECTION_ORB_DICE_SIDES)
            return True
        self.dice_manager.roll(
            1, RESURRECTION_ORB_DICE_SIDES, label="Resurrection Orb",
            target_name=squad.name, target_squad=squad, subject_label="Resurrecting")
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            return False
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or [1]
        self._resolve(values[0])
        return True

    def _resolve(self, rolled):
        squad, self._pending = self._pending, None
        spent, revived = reanimation_protocols.reanimate(
            squad, rolled,
            all_tokens=self._tokens(),
            position_valid=self.position_valid,
            game_state=self.game_state,
            placer=self.placer,
        )
        detail = f"{spent} wound(s)"
        if revived:
            detail += f", {len(revived)} model(s) back on the battlefield"
        self._log(f"Resurrection Orb ({squad.name}): rolled a {rolled} - reanimated {detail}.")
