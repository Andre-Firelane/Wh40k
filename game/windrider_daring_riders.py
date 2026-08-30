"""Windrider Host Stratagem: Daring Riders (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Windrider Host.md):
  WHEN:   The Reinforcements step of your Movement phase.
  TARGET: One ASURYANI MOUNTED or VYPER unit from your army in Reserves.
  EFFECT: Until the end of the phase, when setting up your unit on the
          battlefield from Reserves, it can be set up anywhere on the
          battlefield that is more than 6" horizontally away from all enemy
          units. When doing so, if your unit is set up within 8" horizontally
          of one or more enemy units, until the end of the turn, it is not
          eligible to declare a charge.
  RESTRICTIONS: none printed.

THE THIRD SOURCE OF ONE PLACEMENT RULE. game/ingress.py already carries
"anywhere on the battlefield, more than 6" from all enemy models" for The
Shortened Blade and Baharroth's Cloudstrider, and its own comment says the
slot is "named after what it DOES rather than after either of them". This is
the third, so the method that enforces it stops being named after the first
one - the rename this repo makes at the second carrier, made one carrier late
here only because the earlier two arrived before it existed.

BUT IT IS ARMED ON A DIFFERENT CLOCK, and that is why it does not simply reuse
IngressController.relaxed_arrival_squad:

  * that slot is ONE ARRIVAL. It is armed while a placement is already open
    (The Shortened Blade's TARGET is a unit "arriving ... this phase") and
    cleared the moment that placement is confirmed or cancelled.
  * this Stratagem's TARGET is a unit still IN RESERVES, and its grant lasts
    "until the end of the PHASE". Cancelling a drag half way through must not
    spend it.

So the rule has one definition and two lifetimes, each owned by its own
source - the arrangement Time to Strike's two clocks and Sudden Storm's two
clocks already use, rather than one slot pretending to mean both.

WHAT IT ACTUALLY BUYS IS MORE THAN THE SHORTENED BLADE BUYS. That Stratagem's
TARGET clause guarantees a [DEEP STRIKE] unit, for which rule 24.09 had
already waived the board-edge band and the before-round-3 deployment-zone
rule - so "anywhere on the battlefield" was already true and only 8" -> 6"
changed. This one names no such keyword: an ASURYANI MOUNTED unit arriving
under Ride the Wind uses the ORDINARY Ingress move, so here "anywhere on the
battlefield" genuinely removes two constraints as well as relaxing the third.
Measured rather than assumed, and its own test line.

THE CHARGE LOCK IS CONDITIONAL ON WHERE THE UNIT LANDS - the one genuinely new
piece. The Shortened Blade's lock is unconditional and so is applied when the
Stratagem is bought; this one reads "if your unit IS SET UP within 8"", which
cannot be answered until the models are on the board. It is therefore
evaluated at confirm time, from the arrival itself, and only then does
Squad.charge_locked_until_end_of_turn get set. Bought-time application would
punish a player who then landed far away, and skipping it entirely would be
free reach - both are wrong in a way no predicate test would show.

The two distances are DIFFERENT and both are printed: you may arrive outside
6", and you lose the charge inside 8". The band between them is the whole
decision the Stratagem offers, so it has its own test.

"HORIZONTALLY" is the full distance on this flat board - no verticality is
modelled (CLAUDE.md's Spaeter-Liste), the same reading The Shortened Blade
writes out for its own copy of the word.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import ride_the_wind
from game.squad import edge_distance
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

DARING_RIDERS_NAME = "Daring Riders"
DARING_RIDERS_CP = 1

#: "more than 6" horizontally away from all enemy units" - the same number
#: game/ingress.py already defines for the other two sources of this rule, and
#: imported from there rather than written again.
from game.ingress import SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN as DARING_RIDERS_MIN_ENEMY_DISTANCE_IN

#: "if your unit is set up within 8" horizontally of one or more enemy units".
#: NOT the same number as the one above, and the gap between them is the point.
DARING_RIDERS_CHARGE_LOCK_RANGE_IN = 8.0


def is_active(squad):
    """"Until the end of the phase" - read by game/ingress.py's placement
    check and by this module's own arrival hook."""
    return bool(getattr(squad, "daring_riders_active", False))


def eligible_unit(squad):
    """"One ASURYANI MOUNTED or VYPER unit from your army"."""
    if squad is None or not ride_the_wind.has_detachment(getattr(squad, "owner", None)):
        return False
    return ride_the_wind.applies(squad)


def within_charge_lock_range(squad, enemy_models=()):
    """"if your unit is set up within 8" horizontally of one or more enemy
    units" - measured on the placed models, which is why it cannot be answered
    when the Stratagem is bought."""
    mine = [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]
    if not mine:
        return False
    for enemy in enemy_models or ():
        if enemy.is_dead():
            continue
        if any(edge_distance(m, enemy) <= DARING_RIDERS_CHARGE_LOCK_RANGE_IN
               for m in mine):
            return True
    return False


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.daring_riders_active = False


class DaringRidersController:
    """A Movement-phase panel button plus the arrival hook that resolves the
    conditional charge lock."""

    def __init__(self, stratagem_controller, ingress_controller=None,
                 game_state=None, all_tokens=None, setup_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.ingress_controller = ingress_controller
        self.game_state = game_state
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.setup_controller = setup_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=DARING_RIDERS_NAME, cp_cost=DARING_RIDERS_CP, effect=self._grant,
        )

    def panel_label(self, squad):
        return ('%s (%d CP) - arrive anywhere more than %g" from enemies'
                % (DARING_RIDERS_NAME, DARING_RIDERS_CP,
                   DARING_RIDERS_MIN_ENEMY_DISTANCE_IN))

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False               # "YOUR Movement phase"
        if is_active(squad):
            return False
        if not eligible_unit(squad):
            return False
        # "One ... unit from your army IN RESERVES" - unlike The Shortened
        # Blade, whose target's placement is already open.
        reserves = getattr(self.game_state, "reserves", None) or ()
        if squad not in reserves:
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.daring_riders_active = True
            # The overlay caches its legality mask per placement, and the
            # answer this Stratagem changes is exactly what that mask holds -
            # without this the board would keep painting the old ring. The
            # same line The Shortened Blade needs, for the same reason.
            if self.setup_controller is not None:
                self.setup_controller.invalidate_placement()
            if self.game_log is not None:
                self.game_log.add(
                    '%s: %s can arrive anywhere more than %g" from all enemy '
                    "units this phase."
                    % (DARING_RIDERS_NAME, squad.name,
                       DARING_RIDERS_MIN_ENEMY_DISTANCE_IN))

    def _enemy_models_of(self, squad):
        return [t for t in (self.all_tokens or ())
                if t.squad is not None and t.squad.owner != squad.owner
                and not t.is_dead()]

    def notify_arrival(self, squad):
        """Fed from IngressController.on_ingress_resolved - "when doing so, IF
        your unit is set up within 8" ... it is not eligible to declare a
        charge".

        Resolved here rather than when the Stratagem is bought because the
        condition is about where the models ended up. Uses the same
        Squad.charge_locked_until_end_of_turn field rules 18.04/18.05 already
        use, so ChargeController needs no new case and main.py's end-of-turn
        cleanup already clears it."""
        if squad is None or not is_active(squad):
            return False
        if not within_charge_lock_range(squad, self._enemy_models_of(squad)):
            return False
        squad.charge_locked_until_end_of_turn = True
        if self.game_log is not None:
            self.game_log.add(
                '%s: %s arrived within %g" of an enemy unit and cannot declare '
                "a charge this turn."
                % (DARING_RIDERS_NAME, squad.name,
                   DARING_RIDERS_CHARGE_LOCK_RANGE_IN))
        return True
