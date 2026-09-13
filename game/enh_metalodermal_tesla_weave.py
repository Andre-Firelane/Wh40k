"""Canoptek Court Enhancement: Metalodermal Tesla Weave (10 pts).

RULE (verbatim, rules/necrons/detachments/Canoptek Court.md):
  "CRYPTEK model only. Once per phase, when an enemy unit selects the bearer's
   unit as a target of a charge, roll one D6: on a 2-5, that enemy unit suffers
   D3 mortal wounds; on a 6, that enemy unit suffers 3 mortal wounds."

THE MOMENT IS THE CHARGE DECLARATION, and this engine has a chain for exactly it:
ChargeController.charge_declaration_reactions. Retaliation Cadre's Grav-Inhibitor
Field (game/grav_inhibitor_field.py) is the template - a reactor that returns True
to take ownership of `resume` and starts the charge move only once its own dice
and allocation are done. Deferred for that template's reason: the mortal wounds
can destroy the charging unit, and a charge move opened underneath two rolls would
be half-state on a unit that may no longer exist.

NOT OPTIONAL. There is no "you can" - the bearer rolls. So nothing is prompted and
the AI needs no answer of its own; the only choice in the whole sequence is rule
06.02's allocation, which belongs to the CHARGING player (the unit taking the
wounds), and turn_tracker.set_active() flips for exactly that, as Grav-Inhibitor's
does.

THREE BANDS OF ONE DIE: 1 does nothing, 2-5 rolls a D3, 6 is a flat 3. Two dice
windows at most, one at a time - DiceManager holds one pending roll.

"ONCE PER PHASE" IS PER BEARER, cleared by reset_phase() at every phase boundary.
Two charges into the bearer's unit in one phase fire it once.

A MortalWoundAllocationSession this module opens, it can drain: pending_damage_
choice, choose_damage_model() and the Feel No Pain leg ahead of the step checks -
test_event_chain_wiring.py section 17 requires all three of every module that
opens one, and main.py wires the click, the highlight, the AI pause and the phase
gate for it.
"""

from game import enhancements
from game.damage_resolution import MortalWoundAllocationSession

METALODERMAL_TESLA_WEAVE = "Metalodermal Tesla Weave"

#: "on a 2-5 ... D3 mortal wounds; on a 6 ... 3 mortal wounds".
TESLA_WEAVE_D3_BAND_MIN = 2
TESLA_WEAVE_FLAT_ON = 6
TESLA_WEAVE_FLAT_WOUNDS = 3

AWAITING_BAND = "awaiting_band"
AWAITING_D3 = "awaiting_d3"


def _alive(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def mortal_wounds_for(band_roll, d3_roll=None):
    """The printed table, as one function the controller and the suite share."""
    if band_roll < TESLA_WEAVE_D3_BAND_MIN:
        return 0
    if band_roll >= TESLA_WEAVE_FLAT_ON:
        return TESLA_WEAVE_FLAT_WOUNDS
    return int(d3_roll or 0)


class MetalodermalTeslaWeaveController:
    def __init__(self, dice_manager=None, turn_tracker=None, game_log=None):
        self.dice_manager = dice_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._fired_this_phase = set()     # id(bearer model)
        self._offered_key = None
        self._charging = None
        self._bearer_squad = None
        self._step = None
        self._band = None
        self._resume = None
        self.mortal_wound_session = None

    # ------------------------------------------------------------ plumbing
    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)

    @property
    def is_busy(self):
        return self._step is not None or self.mortal_wound_session is not None

    def reset_phase(self):
        """"Once per phase"."""
        self._fired_this_phase.clear()

    def unfired_bearers(self, squad):
        return [m for m in enhancements.bearer_models(squad, METALODERMAL_TESLA_WEAVE)
                if id(m) not in self._fired_this_phase]

    def can_fire(self, charging_squad, target_squad):
        if charging_squad is None or target_squad is None:
            return False
        if target_squad.owner == charging_squad.owner:
            return False
        if not _alive(charging_squad):
            return False
        if not enhancements.is_active(target_squad, METALODERMAL_TESLA_WEAVE):
            return False
        return bool(self.unfired_bearers(target_squad))

    def _declaration_key(self, charging_squad, targets):
        battle_round = getattr(self.turn_tracker, "battle_round", None)
        return (battle_round, id(charging_squad), tuple(sorted(id(t) for t in targets)))

    # ------------------------------------------------------------ the chain
    def maybe_offer(self, charging_squad, targets, on_resolved=None):
        """charge_declaration_reactions' contract: True means this controller
        now owns `on_resolved` and calls it when its dice and allocation are
        done. Named maybe_offer() for that contract, though nothing is offered -
        the bearer simply rolls."""
        key = self._declaration_key(charging_squad, targets)
        if key == self._offered_key or self.is_busy:
            return False
        target = next((t for t in sorted(targets or (), key=lambda s: s.name)
                       if self.can_fire(charging_squad, t)), None)
        if target is None:
            return False
        self._offered_key = key
        bearer = self.unfired_bearers(target)[0]
        self._fired_this_phase.add(id(bearer))
        self._charging = charging_squad
        self._bearer_squad = target
        self._log(f"{METALODERMAL_TESLA_WEAVE}: {charging_squad.name} charges {target.name} - "
                  "the tesla weave discharges.")
        if self.dice_manager is None:
            from game import dice
            band = dice.random.randint(1, 6)
            d3 = dice.random.randint(1, 3) if TESLA_WEAVE_D3_BAND_MIN <= band < TESLA_WEAVE_FLAT_ON else None
            self._inflict(mortal_wounds_for(band, d3), band)
            if self.mortal_wound_session is None:
                # Resolved in one go: the chain carries on by itself.
                self._clear()
                return False
            self._resume = on_resolved
            return True
        self._resume = on_resolved
        self._step = AWAITING_BAND
        self.dice_manager.roll(
            count=1, sides=6, label=METALODERMAL_TESLA_WEAVE,
            target_name=charging_squad.name, target_squad=charging_squad,
            rolled_for=target, subject_label="Tesla weave",
        )
        return True

    def on_dice_acknowledged(self):
        if self.dice_manager is None:
            return False
        # Rule 24.12: this acknowledgement may be Feel No Pain's dice step
        # inside the allocation - drained BEFORE the step checks below, or the
        # session parks for ever (test_event_chain_wiring.py section 17).
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_mortal_wounds_done()
            return True
        if self._step == AWAITING_BAND:
            self._step = None
            band = (self.dice_manager.last_values or [1])[0]
            self._band = band
            if TESLA_WEAVE_D3_BAND_MIN <= band < TESLA_WEAVE_FLAT_ON:
                self._step = AWAITING_D3
                self.dice_manager.roll(
                    count=1, sides=3, label=f"{METALODERMAL_TESLA_WEAVE}: D3 mortal wounds",
                    target_name=self._charging.name, target_squad=self._charging,
                    rolled_for=self._bearer_squad,
                )
                return True
            self._inflict(mortal_wounds_for(band), band)
            return True
        if self._step == AWAITING_D3:
            self._step = None
            d3 = (self.dice_manager.last_values or [1])[0]
            self._inflict(mortal_wounds_for(self._band or TESLA_WEAVE_D3_BAND_MIN, d3), self._band)
            return True
        return False

    def _inflict(self, wounds, band):
        charging = self._charging
        if wounds <= 0 or charging is None or not _alive(charging):
            self._log(f"{METALODERMAL_TESLA_WEAVE}: rolled a {band} - no mortal wounds.")
            self._finish()
            return
        self._log(f"{METALODERMAL_TESLA_WEAVE}: rolled a {band} - {charging.name} suffers "
                  f"{wounds} mortal wound(s).")
        if self.turn_tracker is not None:
            # Rule 06.02: the unit taking the wounds is the CHARGING one, so its
            # owner picks which model takes each.
            self.turn_tracker.set_active(charging.owner)
        self.mortal_wound_session = MortalWoundAllocationSession(
            charging, wounds, dice_manager=self.dice_manager, log=self._log,
        )
        self._check_mortal_wounds_done()

    @property
    def pending_damage_choice(self):
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_mortal_wounds_done()

    def _check_mortal_wounds_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None
        self._finish()

    def _clear(self):
        self._step = None
        self._band = None
        self._charging = None
        self._bearer_squad = None

    def _finish(self):
        """Hand control back to the charge. _start_declared_move() re-checks its
        own preconditions, including whether the charging unit survived."""
        if self.turn_tracker is not None and self._charging is not None:
            self.turn_tracker.set_active(self._charging.owner)
        self._clear()
        resume, self._resume = self._resume, None
        if resume is not None:
            resume()
