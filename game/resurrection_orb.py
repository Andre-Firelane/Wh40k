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


def _carries_orb(model):
    """TWO sources, and the second arrived with the Overlord with translocation
    shroud. For the Overlord, the Lokhust Lord and the Catacomb Command Barge
    the orb is a printed OPTION, so a Gear item in game/factions/necrons.py
    sets a TOKEN flag. The shroud Overlord's line reads "This model is equipped
    with: Overlord's blade; resurrection orb" - it is not a choice, so it is a
    PROFILE flag, the arrangement the Ghostkeel's unconditional Battlesuit
    Support System already uses.

    Asked in one place so the two can never disagree about what carrying an orb
    means."""
    if getattr(model, "resurrection_orb", False):
        return True
    return bool(getattr(getattr(model, "profile", None), "resurrection_orb", False))


def bearers(squad):
    """The models carrying an orb - bought as wargear or printed as part of the
    model. See _carries_orb()."""
    return [m for m in getattr(squad, "models", ()) or ()
            if _carries_orb(m) and not m.is_dead()]


def has_orb(squad):
    return bool(bearers(squad))


class ResurrectionOrbController:
    """Offered at every phase boundary - "at the end of any phase"."""

    prompt = "Use the Resurrection Orb? (reanimates D6 instead of D3)"

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

    def bearer_ready(self, squad):
        """Whether this unit's orb is available at all - the three limits that
        are about the BEARER rather than about who it would resurrect."""
        if self._pending is not None or squad is None or not has_orb(squad):
            return False
        return (id(squad) not in self._used_squads
                and squad.owner not in self._used_this_turn)

    def targets_for(self, squad):
        """Which units THIS bearer's orb can resurrect.

        "If you do, THIS UNIT resurrects" - so for the Overlord, the Lokhust
        Lord and the shroud Overlord the bearer is its own and only target.
        The Catacomb Command Barge prints a different sentence and overrides
        this; see RangedResurrectionOrbController below. Splitting the two
        apart is what lets one machine serve both printings, and for the three
        original carriers it is the same answer they always gave."""
        if squad is None or reanimation_protocols.recoverable_wounds(squad) <= 0:
            return []
        return [squad]

    def can_use(self, squad):
        """Whether `squad` can use its orb right now - bearer limits AND at
        least one unit worth resurrecting."""
        return self.bearer_ready(squad) and bool(self.targets_for(squad))

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
        """The AI's deterministic gate - see this module's docstring. Asked of
        the BEARER, answered off its best available target (which for the three
        original carriers is the bearer itself)."""
        return any(reanimation_protocols.recoverable_wounds(t) >= RESURRECTION_ORB_MIN_RECOVERABLE
                   for t in self.targets_for(squad)) and self.can_use(squad)

    def offer_at_end_of_phase(self, squads, player):
        """Returns True if anything was used or prompted. One unit at a time:
        the per-turn limit means a second offer could never be taken anyway.

        The options are (BEARER, TARGET) pairs, because the two are no longer
        always the same unit - see targets_for(). For the three original
        carriers every pair is (s, s) and this reads exactly as it always did."""
        candidates = sorted((s for s in squads if s.owner == player and self.can_use(s)),
                            key=lambda s: s.name)
        pairs = [(bearer, target) for bearer in candidates
                 for target in self.targets_for(bearer)
                 if not self.declined_unchanged(target)]
        if not pairs:
            return False
        if player in self.auto_players or self.decision_manager is None:
            worth = [(b, t) for b, t in pairs
                     if reanimation_protocols.recoverable_wounds(t) >= RESURRECTION_ORB_MIN_RECOVERABLE]
            if not worth:
                return False
            best = max(worth, key=lambda bt: (reanimation_protocols.recoverable_wounds(bt[1]), bt[1].name))
            return self._use(best[0], best[1])
        # EVERY candidate, one option each - not candidates[0] as a bare
        # yes/no. The AI ranks by recoverable_wounds a few lines up and takes
        # the best unit; the human used to be shown the ALPHABETICALLY FIRST
        # one and given no way to pick another, so the two sides were not
        # playing the same rule (user: "die Funktion selbst soll nicht
        # deterministisch sein"). The wound count rides along in each label,
        # because it is the number the choice turns on and a squad name does
        # not carry it.
        options = [
            (f"{t.name} ({reanimation_protocols.recoverable_wounds(t)} wound(s) to recover)",
             (lambda b=bearer, t=t: self._use(b, t)), t)
            for bearer, t in pairs
        ]
        # The decline is RECORDED, not dropped - see declined_unchanged().
        # The TARGETS are captured so refusing the prompt refuses it for every
        # unit it offered, which is what the player just said.
        options.append(("Decline", (lambda group=tuple(t for _b, t in pairs): [
            self._decline(s) for s in group] and True)))
        self.decision_manager.request(
            player,
            self.prompt,
            options,
        )
        return True

    def _use(self, squad, target=None):
        """`squad` is the BEARER; `target` the unit that resurrects. They are
        the same for the three carriers that print "this unit resurrects"."""
        target = squad if target is None else target
        if not self.bearer_ready(squad) or target not in self.targets_for(squad):
            return False
        # KEYED ON THE BEARER. "(Once per battle, PER UNIT)" heads a WARGEAR
        # ability, so the unit it is once per is the one carrying the orb.
        # Behaviour-neutral for the three original carriers, where bearer and
        # target are the same unit - pinned in the suite in both directions.
        self._used_squads.add(id(squad))
        self._used_this_turn.add(squad.owner)
        self._pending = target
        squad = target
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


class RangedResurrectionOrbController(ResurrectionOrbController):
    """The Catacomb Command Barge's orb, which is a DIFFERENT printed sentence.

    RULE (verbatim, rules/necrons/Catacomb Command Barge.md):
      "Resurrection Orb: (Once per battle, per unit) At the end of any phase,
       you can use this ability. If you do, select up to one friendly NECRONS
       INFANTRY/NECRONS MOUNTED unit within 6" of this unit. That unit
       resurrects."

    THE BEARER AND THE TARGET ARE DIFFERENT UNITS, which is the whole reason
    this class exists. Every other carrier prints "this unit resurrects", so
    for them the distinction is invisible - and that is exactly why it went
    unnoticed that the base's once-per-battle ledger was keyed on the
    RESURRECTING unit. On this datasheet that would be the wrong object: one
    Barge could orb a different unit every phase for the whole battle, and a
    unit that had been orbed once could never be orbed again by anyone. The
    ledger now keys the BEARER, which is behaviour-neutral for the three units
    where the two coincide.

    ONLY THE TARGETING HALF IS NEW. The die (D6), the three limits, the decline
    memory, the deterministic AI answer and reanimate() itself are all
    inherited - and so is the GEAR half: the Barge's printed "can be equipped
    with 1 resurrection orb" is the Lokhust Lord's line, so it reuses
    game/factions/necrons.py's existing unconditional equip and _carries_orb()
    above answers it without a new flag.

    "UP TO ONE" is the printed permission to decline, which the base already
    offers and remembers.
    """

    prompt = ("Use the Resurrection Orb? "
              "(a NECRONS INFANTRY/MOUNTED unit within 6\" reanimates D6)")
    range_in = 6.0
    #: "NECRONS INFANTRY/NECRONS MOUNTED" - datasheet keywords, so read through
    #: attached_units rather than off a UnitProfile flag. Either keyword
    #: qualifies; NECRONS is required on top of whichever one it is.
    target_keywords = ("INFANTRY", "MOUNTED")

    def target_ok(self, squad):
        from game.attached_units import unit_has_datasheet_keyword
        if not unit_has_datasheet_keyword(squad, "NECRONS"):
            return False
        return any(unit_has_datasheet_keyword(squad, kw) for kw in self.target_keywords)

    def targets_for(self, squad):
        """"select up to one friendly NECRONS INFANTRY/NECRONS MOUNTED unit
        within 6" of this unit".

        Measured unit to unit, model edge to model edge - the house idiom for a
        "within N of this unit" clause. The BEARER'S OWN UNIT is not excluded
        by the printed text, but it can never qualify anyway: a Catacomb
        Command Barge is a VEHICLE, so it is neither INFANTRY nor MOUNTED.
        That is measured rather than assumed, and pinned."""
        from game.squad import edge_distance
        if squad is None or not self.bearer_ready(squad):
            return []
        mine = [m for m in squad.models if not m.is_dead()]
        out = []
        for other in self._squads():
            if other is squad or other.owner != squad.owner:
                continue
            if not self.target_ok(other):
                continue
            if reanimation_protocols.recoverable_wounds(other) <= 0:
                continue    # never offer what buys nothing
            theirs = [m for m in other.models if not m.is_dead()]
            if any(edge_distance(a, b) <= self.range_in for a in mine for b in theirs):
                out.append(other)
        return sorted(out, key=lambda s: s.name)

    def _squads(self):
        seen, out = set(), []
        for token in (list(self.game_state.tokens) if self.game_state is not None else []):
            other = getattr(token, "squad", None)
            if other is not None and id(other) not in seen:
                seen.add(id(other))
                out.append(other)
        return out
