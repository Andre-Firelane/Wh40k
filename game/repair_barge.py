"""Ghost Ark: "Repair Barge".

RULE (verbatim, rules/necrons/Ghost Ark.md):
  "Once per turn, just after an enemy unit finishes making its attacks, if one
   or more friendly NECRON WARRIORS units within 3" of this model lost one or
   more wounds as a result of those attacks, this model can use this ability.
   If it does, select one of those NECRON WARRIORS units; that unit's
   Reanimation Protocols activate. The same NECRON WARRIORS unit cannot be
   selected for this ability more than once per turn."

THE FOURTH DOOR INTO reanimate(), after the army rule's own controller, the
Resurrection Orb and Protocol of the Undying Legions. Every door needs its own
`placer` (rule 01.02.03's "set up" half) or a human watches the engine seat
their returning models - test_return_placement.py section 7 is a set difference
over exactly that and will name this module if the wiring is missed.

"LOST ONE OR MORE WOUNDS AS A RESULT OF THOSE ATTACKS" IS A DELTA
==================================================================
And that is the clause a convenient proxy would quietly drop. Neither of the
two things already on hand answers it:

  * ShootingController._hit_target_squads_this_activation is about HITS. An
    attack that hit and was saved cost no wounds.
  * reanimation_protocols.recoverable_wounds() > 0 is "has EVER lost wounds".
    A Warriors unit damaged two turns ago and standing near the Ark would
    trigger this on every enemy activation for the rest of the game.

So the wound total of every nearby Warriors unit is SNAPSHOT when the enemy
selects its targets and compared when it finishes. recoverable_wounds() is
still used, but for the other question - whether there is anything left to
reanimate at all, the shared eligibility measure the Orb and Undying Legions
read too. Trigger and eligibility are different questions asked of different
things, on purpose.

EVERY NEARBY WARRIORS UNIT IS SNAPSHOT, not just the one being shot at: mortal
wounds and blast splash can cost a unit wounds without it ever being the
selected target, and "as a result of those attacks" covers that.

TWO PHASES, BECAUSE "AN ENEMY UNIT FINISHES MAKING ITS ATTACKS" IS BOTH. The
arm rides both target_reactions tuples and the payment rides
on_squad_finished_shooting and FightController.on_unit_finished_fighting - the
pair game/protocol_undying_legions.py already uses for the same phrase.

maybe_offer() IS USED AS A RECORDER HERE, and that is deliberate rather than a
half-built reactor: _offer_target_reactions()'s own docstring says "each
controller decides for itself whether it wants to act at all", and this one
decides to look and say nothing. It always returns False.

TWO LEDGERS, BOTH PER TURN, AND THEY ARE NOT THE SAME QUESTION:

  * _used_this_turn, keyed by the ARK MODEL - "Once per turn ... THIS MODEL
    can use this ability". Two Ghost Arks may each repair in the same turn.
  * _selected_this_turn, keyed by the WARRIORS SQUAD - "The same NECRON
    WARRIORS unit cannot be selected for this ability more than once per
    turn". One Ark may not repair the same unit twice, and neither may two.

Folded into one they would each break the other's case.

"FRIENDLY NECRON WARRIORS UNITS" is read as the DATASHEET keyword through
attached_units.unit_has_datasheet_keyword(), so a Warriors unit with an
Overlord attached is still one (19.03's component-wise reading) - the same
vocabulary the Ghost Ark's own transport pools use, so the two cannot end up
disagreeing about what a NECRON WARRIORS model is.

THE REANIMATOR'S BOOST IS NOT APPLIED, and that is a NAMED decision rather than
an oversight. The printed words here - "that unit's Reanimation Protocols
activate" - are exactly the words game/reanimation_boost.py keys on, but
reanimation_protocols.py asserts "ONLY THIS DOOR" for the Canoptek Reanimator's
beam, and the Resurrection Orb and Undying Legions print those same words and
do not get it either. Answering otherwise would change SHIPPED behaviour on two
abilities, which is not a datasheet stage's job. This is built to the same
reading as the other three doors and the suite pins that all four agree, so a
later decision is one edit in one place.
"""

from game import ai_mode, attached_units, reanimation_protocols
from game.squad import edge_distance

REPAIR_BARGE_RANGE_IN = 3.0
REPAIR_BARGE_NAME = "Repair Barge"
REPAIR_BARGE_KEYWORD = "NECRON WARRIORS"
REPAIR_BARGE_DICE_SIDES = reanimation_protocols.REANIMATION_DICE_SIDES  # "Reanimation Protocols activate" - the army rule's own D3


def _alive(squad):
    return [m for m in squad.models if not m.is_dead()] if squad else []


def bearers(squad):
    """Living Ghost Ark models in this unit."""
    return [m for m in _alive(squad) if getattr(m.profile, "repair_barge", False)]


def is_warriors_unit(squad):
    """"NECRON WARRIORS unit" - the DATASHEET keyword, 19.03's reading."""
    return bool(squad) and attached_units.unit_has_datasheet_keyword(
        squad, REPAIR_BARGE_KEYWORD)


class RepairBargeController:
    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, position_valid=None, auto_players=(),
                 placer=None):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.position_valid = position_valid
        self.auto_players = ai_mode.players(auto_players)
        # The FOURTH door into reanimate() - see the module docstring. Assigned
        # in main.py rather than passed in, because this controller is built
        # long before the placer exists.
        self.placer = placer
        self._used_this_turn = set()      # id(ark model) - "once per turn ... this model"
        self._selected_this_turn = set()  # id(squad)     - "the same unit ... not more than once per turn"
        self._snapshot = {}               # id(squad) -> total wounds before this enemy activation
        self._pending = None

    # ------------------------------------------------------------- plumbing
    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    def _squads(self):
        seen, out = set(), []
        for token in self._tokens():
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen.add(id(squad))
                out.append(squad)
        return out

    @property
    def is_busy(self):
        return self._pending is not None

    def reset_turn(self):
        """Both printed limits are per TURN, so both clear at the same edge."""
        self._used_this_turn.clear()
        self._selected_this_turn.clear()
        self._snapshot.clear()

    # -------------------------------------------------------------- 1. arm
    @staticmethod
    def _wound_total(squad):
        return sum(max(0, m.current_wounds) for m in _alive(squad))

    def nearby_warriors(self, ark_squad):
        """Friendly NECRON WARRIORS units with a model within 3" of a living
        Ghost Ark model in `ark_squad`."""
        arks = bearers(ark_squad)
        if not arks:
            return []
        out = []
        for squad in self._squads():
            if squad is ark_squad or squad.owner != ark_squad.owner:
                continue
            if not is_warriors_unit(squad):
                continue
            if any(edge_distance(m, ark) <= REPAIR_BARGE_RANGE_IN
                   for m in _alive(squad) for ark in arks):
                out.append(squad)
        return out

    def _ark_squads(self):
        return [s for s in self._squads() if bearers(s)]

    def maybe_offer(self, attacking_squad, target_squad, melee=False):
        """A target_reactions member, used as a RECORDER - see the module
        docstring. Snapshots every nearby Warriors unit's wound total so the
        payment hook can tell what THOSE attacks cost. Never offers, never
        interrupts, always returns False."""
        for ark in self._ark_squads():
            if attacking_squad is not None and ark.owner == attacking_squad.owner:
                continue    # "an ENEMY unit finishes making its attacks"
            for squad in self.nearby_warriors(ark):
                self._snapshot.setdefault(id(squad), self._wound_total(squad))
        return False

    # ------------------------------------------------------------- 2. pay
    def on_squad_finished_shooting(self, squad, hit_squads=None):
        """The shooting half of "just after an enemy unit finishes making its
        attacks"."""
        return self.resolve_after_attacks(squad)

    def on_unit_finished_fighting(self, squad):
        """The fight half. Same sentence, other phase."""
        return self.resolve_after_attacks(squad)

    def wounded_candidates(self, ark_squad):
        """The Warriors units this Ark may repair right now: nearby, they lost
        wounds to the attacks that just resolved, they have something to
        reanimate, and they have not been picked yet this turn."""
        out = []
        for squad in self.nearby_warriors(ark_squad):
            before = self._snapshot.get(id(squad))
            if before is None or self._wound_total(squad) >= before:
                continue        # lost nothing to THOSE attacks
            if id(squad) in self._selected_this_turn:
                continue
            if reanimation_protocols.recoverable_wounds(squad) <= 0:
                continue        # nothing to reanimate - never offer what buys nothing
            out.append(squad)
        return out

    def can_use(self, ark_squad):
        if self._pending is not None or ark_squad is None:
            return False
        if not self._available_ark(ark_squad):
            return False
        return bool(self.wounded_candidates(ark_squad))

    def _available_ark(self, ark_squad):
        """The first living Ghost Ark model in this unit that has not used the
        ability this turn - "once per turn ... THIS MODEL"."""
        for ark in bearers(ark_squad):
            if id(ark) not in self._used_this_turn:
                return ark
        return None

    def resolve_after_attacks(self, attacking_squad):
        """Offer to every Ark that qualifies, then drop the snapshot: the next
        enemy activation takes its own."""
        used = False
        for ark_squad in self._ark_squads():
            if attacking_squad is not None and ark_squad.owner == attacking_squad.owner:
                continue
            if self.can_use(ark_squad):
                used = self._offer(ark_squad) or used
        self._snapshot.clear()
        return used

    def _offer(self, ark_squad):
        candidates = self.wounded_candidates(ark_squad)
        if not candidates:
            return False
        player = ark_squad.owner
        if player in self.auto_players or self.decision_manager is None:
            # Deterministic and free for the AI: the unit with the most to
            # recover, which is what a D3 of reanimated wounds buys most on.
            # A human is asked, because "this model CAN use this ability" is a
            # choice and the ability is once per turn.
            return self._use(ark_squad, max(
                candidates, key=lambda s: (reanimation_protocols.recoverable_wounds(s), s.name)))
        options = [
            (f"{s.name} ({reanimation_protocols.recoverable_wounds(s)} wound(s) to recover)",
             (lambda t=s: self._use(ark_squad, t)), s)
            for s in sorted(candidates, key=lambda s: s.name)
        ]
        options.append(("Decline", lambda: True))
        self.decision_manager.request(
            player,
            f"{REPAIR_BARGE_NAME} ({ark_squad.name}): repair which NECRON WARRIORS unit?",
            options,
        )
        return True

    def _use(self, ark_squad, squad):
        ark = self._available_ark(ark_squad)
        if ark is None or squad is None:
            return False
        self._used_this_turn.add(id(ark))
        self._selected_this_turn.add(id(squad))
        self._pending = squad
        if self.dice_manager is None:
            self._resolve(REPAIR_BARGE_DICE_SIDES)
            return True
        self.dice_manager.roll(
            1, REPAIR_BARGE_DICE_SIDES, label=REPAIR_BARGE_NAME,
            target_name=squad.name, target_squad=squad, subject_label="Reanimating")
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
        self._log(f"{REPAIR_BARGE_NAME} ({squad.name}): rolled a {rolled} - reanimated {detail}.")
