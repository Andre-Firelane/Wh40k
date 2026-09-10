"""Canoptek Scarab Swarms' "Self-destruction" (Necrons).

RULE (printed, word for word):
  "At the start of the Fight phase, if this unit is within Engagement Range of
   one or more enemy units, you can select one model in this unit to destroy.
   If you do, select one enemy unit within Engagement Range of that model and
   roll one D6, adding 1 to the result if that unit is a VEHICLE. On a 2-5,
   that unit suffers D3 mortal wounds; on a 6+, that unit suffers 3 mortal
   wounds."

THE ONLY ABILITY IN THIS ENGINE THAT SPENDS ONE OF YOUR OWN MODELS, which is
what makes it a real decision rather than a free trigger: "you CAN select one
model in this unit to destroy". So it is offered, never auto-resolved for a
human, and an owner in `auto_players` answers it deterministically.

THE ROLL HAS THREE OUTCOMES, NOT TWO, and the middle one is itself a die:
  1 (or 1 with the +1, which is impossible - the bonus makes the floor 2)  nothing
  2-5   D3 mortal wounds
  6+    3 mortal wounds, a FLAT number rather than a bigger die
"+1 IF THAT UNIT IS A VEHICLE" is added to the RESULT, so against a vehicle a
rolled 5 becomes a 6 and pays 3 flat. That is why the bonus is applied before
the bands are read rather than folded into the threshold.

TWO DICE STEPS, and they cannot share one: the D6 decides which band, and the
D3 is only rolled if the band says so. DiceManager holds one roll at a time,
so the second is queued from the first's acknowledgement - the arrangement
game/deadly_vectors.py and game/kroot_linebreakers.py both use.

THE DESTROYED MODEL IS SPENT BEFORE THE WOUNDS LAND, which is the printed
order ("select one model in this unit to destroy. IF YOU DO, select one enemy
unit..."). It matters: a Scarab unit reduced to nothing by its own last model
still deals its wounds.

"WITHIN ENGAGEMENT RANGE OF THAT MODEL" narrows twice - the UNIT must be
engaged for the ability to be available at all, and then the TARGET must be
engaged with the specific model being spent. On a spread-out swarm those are
different sets, which is why the second test is per model.
"""

from game import ai_mode, per_unit_offer
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance

SELF_DESTRUCTION_LABEL = "Self-destruction"

#: "On a 2-5, that unit suffers D3 mortal wounds; on a 6+, ... 3 mortal wounds."
SELF_DESTRUCTION_LOW_BAND = 2
SELF_DESTRUCTION_HIGH_BAND = 6
SELF_DESTRUCTION_HIGH_WOUNDS = 3
#: "adding 1 to the result if that unit is a VEHICLE".
SELF_DESTRUCTION_VEHICLE_BONUS = 1


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def unit_has_ability(squad):
    return squad is not None and any(
        getattr(m.profile, "self_destruction", False) for m in _living(squad))


def is_vehicle_unit(squad):
    """Pooled per rule 19.03 - "that unit is a VEHICLE"."""
    return any(getattr(m.profile, "vehicle", False) for m in _living(squad))


def engaged_enemies_of(model, squad, all_tokens=()):
    """"one enemy unit within Engagement Range of THAT MODEL" - per model, not
    per unit, because a spread-out swarm touches different enemies with
    different models."""
    owner = getattr(squad, "owner", None)
    out = {}
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other.owner == owner or token.is_dead():
            continue
        if edge_distance(model, token) <= ENGAGEMENT_RANGE_IN:
            out[id(other)] = other
    return sorted(out.values(), key=lambda s: s.name)


def wounds_for(roll, target_squad):
    """The band this roll lands in, as (flat_wounds, rolls_a_d3).

    Returns (0, False) for a result below the low band - a printed outcome
    that costs the model and pays nothing."""
    total = roll + (SELF_DESTRUCTION_VEHICLE_BONUS if is_vehicle_unit(target_squad) else 0)
    if total >= SELF_DESTRUCTION_HIGH_BAND:
        return SELF_DESTRUCTION_HIGH_WOUNDS, False
    if total >= SELF_DESTRUCTION_LOW_BAND:
        return 0, True
    return 0, False


def eligible_models(squad, all_tokens=()):
    """Models of this unit that could be spent: alive, and with at least one
    enemy unit in Engagement Range of them."""
    if not unit_has_ability(squad):
        return []
    return [m for m in _living(squad) if engaged_enemies_of(m, squad, all_tokens)]


class SelfDestructionController:
    """Offered at the start of every Fight phase, to whoever owns a Scarab
    unit that is engaged."""

    def __init__(self, decision_manager=None, game_state=None, game_log=None,
                 dice_manager=None, auto_players=(), target_pick=None):
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.game_log = game_log
        self.dice_manager = dice_manager
        self.auto_players = ai_mode.players(auto_players)
        self.target_pick = target_pick
        self._offered = set()
        #: The pending (spent model, target) while its D6 is on the table.
        self.pending = None
        #: The target owed a D3, while that second die is on the table.
        self._d3_for = None
        self.mortal_wound_session = None

    def _tokens(self):
        return getattr(self.game_state, "tokens", None) or []

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def eligible_squads(self, player):
        seen, out = set(), []
        for token in self._tokens():
            squad = getattr(token, "squad", None)
            if squad is None or squad.owner != player or id(squad) in seen:
                continue
            seen.add(id(squad))
            if eligible_models(squad, self._tokens()):
                out.append(squad)
        return sorted(out, key=lambda s: s.name)

    def offer_at_start_of_fight(self, player):
        """"At the start of the Fight phase" - the Fight phase belongs to
        nobody in this engine's sense, so BOTH players are offered in turn by
        main.py; this is asked once per owner.

        EVERY eligible unit is asked, one prompt at a time, through
        game/per_unit_offer.py. The rule is written per unit ("if THIS UNIT is
        within Engagement Range"), and the bug that chain exists for is exactly
        an army with two Scarab units being asked about only one of them - the
        reported Vespid case, one faction over. Raising N prompts at once would
        also put N untagged yes/no boxes on the screen, which
        test_event_chain_wiring.py section 18 refuses on sight."""
        candidates = [s for s in self.eligible_squads(player)
                      if id(s) not in self._offered]
        for squad in candidates:
            self._offered.add(id(squad))
        if player in self.auto_players or self.decision_manager is None:
            for squad in candidates:
                models = eligible_models(squad, self._tokens())
                if models:
                    self._detonate(squad, models[0])
            return False
        return per_unit_offer.offer_each(
            self.decision_manager, candidates,
            lambda s: bool(eligible_models(s, self._tokens())),
            lambda s: ("%s: destroy one model of %s to deal mortal wounds to "
                       "an engaged enemy unit?" % (SELF_DESTRUCTION_LABEL, s.name)),
            lambda s: [("Destroy one model", lambda t=s: self._offer_target(t)),
                       ("Keep the model", lambda: None)])

    def _offer_target(self, squad):
        models = eligible_models(squad, self._tokens())
        if not models:
            return False
        model = models[0]
        targets = engaged_enemies_of(model, squad, self._tokens())
        if not targets:
            return False
        if len(targets) == 1 or squad.owner in self.auto_players \
                or self.decision_manager is None:
            return self._detonate(squad, model, self._pick(squad, targets))
        options = [("%s: %s" % (SELF_DESTRUCTION_LABEL, t.name),
                    (lambda target=t, m=model, s=squad: self._detonate(s, m, target)), t)
                   for t in targets]
        self.decision_manager.request(
            squad.owner,
            "%s: which enemy unit?" % SELF_DESTRUCTION_LABEL, options)
        return True

    def _pick(self, squad, candidates):
        if self.target_pick is not None:
            chosen = self.target_pick(squad, candidates)
            if chosen is not None:
                return chosen
        return candidates[0]

    def _detonate(self, squad, model, target=None):
        """Spend the model, then roll. The printed order - "select one model
        ... to destroy. If you do, select one enemy unit ... and roll"."""
        if target is None:
            targets = engaged_enemies_of(model, squad, self._tokens())
            if not targets:
                return False
            target = self._pick(squad, targets)
        model.current_wounds = 0
        self._log("%s: %s destroys one model to strike %s."
                  % (SELF_DESTRUCTION_LABEL, squad.name, target.name))
        self.pending = (squad, target)
        if self.dice_manager is not None:
            self.dice_manager.roll(count=1, sides=6,
                                   label="%s (%s)" % (SELF_DESTRUCTION_LABEL, target.name),
                                   target_name=target.name, target_squad=target)
        return True

    def on_dice_acknowledged(self):
        """The D6, then - if the band says so - a D3, then the wounds.

        TWO DICE STEPS THAT CANNOT SHARE ONE: DiceManager holds one roll at a
        time, so the D3 is queued from the D6's acknowledgement. The Feel No
        Pain branch comes FIRST, before the "nothing pending" guard, because a
        FNP roll inside the allocation is acknowledged here too - the shape
        every other mortal-wound holder in this engine opens with, and the
        reason this method cannot simply return False on an empty ledger."""
        if (self.pending is None and self._d3_for is None
                and self.mortal_wound_session is not None
                and self.mortal_wound_session.pending_fnp is not None):
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_allocation_done()
            return True
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or []
        if self._d3_for is not None:
            target, self._d3_for = self._d3_for, None
            wounds = values[0] if values else 0
            self._inflict(target, wounds)
            return True
        if self.pending is None:
            return False
        outcome = self.resolve(values[0] if values else 0)
        if outcome is None:
            return False
        target, flat, rolls_a_d3 = outcome
        if rolls_a_d3:
            self._d3_for = target
            if self.dice_manager is not None:
                self.dice_manager.roll(
                    count=1, sides=3,
                    label="%s (D3 mortal wounds)" % SELF_DESTRUCTION_LABEL,
                    target_name=target.name, target_squad=target)
            return True
        if flat:
            self._inflict(target, flat)
        return True

    def _inflict(self, target, wounds):
        if wounds <= 0:
            return False
        from game.damage_resolution import MortalWoundAllocationSession
        self._log("%s: %s suffers %d mortal wound(s)."
                  % (SELF_DESTRUCTION_LABEL, target.name, wounds))
        self.mortal_wound_session = MortalWoundAllocationSession(
            target, wounds, dice_manager=self.dice_manager,
            log=(lambda m: self._log(m)) if self.game_log is not None else None)
        return True

    @property
    def pending_damage_choice(self):
        """Rule 06.02: the DEFENDER allocates. Shaped exactly like every other
        holder's, so main.py's damage-choice list can hold this controller
        beside them without a special case."""
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_allocation_done()

    def _check_allocation_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None

    @property
    def is_busy(self):
        return (self.pending is not None or self._d3_for is not None
                or self.mortal_wound_session is not None)

    def resolve(self, roll):
        """Turn an acknowledged D6 into (target, flat_wounds, rolls_a_d3)."""
        if self.pending is None:
            return None
        squad, target = self.pending
        self.pending = None
        flat, d3 = wounds_for(roll, target)
        total = roll + (SELF_DESTRUCTION_VEHICLE_BONUS if is_vehicle_unit(target) else 0)
        self._log("%s: D6 %d%s -> %s."
                  % (SELF_DESTRUCTION_LABEL, roll,
                     " (+1, VEHICLE) = %d" % total if total != roll else "",
                     "3 mortal wounds" if flat else
                     ("D3 mortal wounds" if d3 else "no effect")))
        return target, flat, d3

    def reset_phase(self):
        self._offered.clear()
        self.pending = None
        self._d3_for = None
