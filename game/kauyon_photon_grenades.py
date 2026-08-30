"""Kauyon Stratagem: Photon Grenades (1CP).

RULE (verbatim, rules/tau_empire/detachments/Kauyon.md):
  WHEN:   Your opponent's Charge phase, just after an enemy unit has selected
          its charge target.
  TARGET: One T'AU EMPIRE GRENADES unit from your army that was selected as one
          of the targets of that charge.
  EFFECT: That enemy unit must immediately take a Battle-shock test, and until
          the end of the phase, subtract 2 from Charge rolls made for that
          enemy unit.
  RESTRICTION: You cannot target a unit that is within Engagement Range of one
          or more enemy units.

TWO EFFECTS, AND THE ORDER MATTERS
-----------------------------------
The Battle-shock test happens "immediately", i.e. before the charge roll, and
the -2 applies to the roll that follows. So the penalty is set FIRST and the
test is opened second: DiceManager holds one roll at a time, and the charge
roll must not be able to slip past while the Battle-shock test is still open.
The reaction owns the charge's resume for exactly that reason - it hands
control back only once both halves are done.

WHICH SIDE THE -2 LIVES ON
---------------------------
"Charge rolls made FOR that enemy unit" - the CHARGING unit, not the target.
That is the same side as The Twin Lance's Neocapacitor Shields, so it is folded
in at _capped_roll() beside it rather than with the Grav-inhibitor Drone's -2
(which depends on who is being CHARGED and is applied elsewhere).

The drone's own text says its -2 "is not cumulative with any other negative
modifiers to that Charge roll", and game/charge.py reconciles the two negative
sources in one place. This one joins the charger-side total, so that
reconciliation keeps working without a third rule about it.
"""

from game import kauyon, tau_detachments
from game.attached_units import unit_has_datasheet_keyword
from game.stratagems import Stratagem
from game.turn import PHASE_CHARGE

PHOTON_GRENADES_CP = 1
PHOTON_GRENADES_NAME = "Photon Grenades"
PHOTON_GRENADES_CHARGE_PENALTY = 2
GRENADES_KEYWORD = "GRENADES"


def charge_penalty_for(squad):
    """Read by game/charge.py's _capped_roll(), next to Neocapacitor Shields."""
    return PHOTON_GRENADES_CHARGE_PENALTY if getattr(
        squad, "photon_grenades_penalty", False) else 0


class PhotonGrenadesController:
    def __init__(self, stratagem_controller, turn_tracker=None, all_tokens=None,
                 battle_shock_controller=None, decision_manager=None,
                 game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.battle_shock_controller = battle_shock_controller
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = tuple(auto_players)
        self._stratagem = Stratagem(
            name=PHOTON_GRENADES_NAME, cp_cost=PHOTON_GRENADES_CP, effect=self._apply,
            # Each enemy charge is its own window, so rule 15.01's
            # "not the same unit twice this phase" would be the wrong limit -
            # the once-per-phase cap on the Stratagem itself still applies.
            allow_repeat_target=True,
        )
        self._charging_squad = None
        self._resume = None
        self._awaiting_shock = False

    def reset_phase(self, squads=()):
        """"until the end of the phase"."""
        for squad in squads or ():
            squad.photon_grenades_penalty = False

    def eligible_defenders(self, charging_squad, targets):
        """"One T'AU EMPIRE GRENADES unit that was selected as one of the
        targets of that charge", not itself in Engagement Range."""
        out = []
        for squad in targets or ():
            if squad is None or squad.owner == charging_squad.owner:
                continue
            if not tau_detachments.has_detachment(squad.owner, kauyon.SETTING):
                continue
            if not tau_detachments.is_tau_unit(squad):
                continue
            if not unit_has_datasheet_keyword(squad, GRENADES_KEYWORD):
                continue
            if squad.is_engaged(self.all_tokens):
                continue
            if not self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad]):
                continue
            out.append(squad)
        return sorted(out, key=lambda s: s.name)

    def maybe_offer(self, charging_squad, targets, on_resolved=None):
        """ChargeController's declaration-reaction protocol: return True to say
        "I opened something and own the continuation now"."""
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_CHARGE:
            return False
        candidates = self.eligible_defenders(charging_squad, targets)
        if not candidates:
            return False
        reactor = candidates[0].owner
        if reactor in self.auto_players or self.decision_manager is None:
            return False
        self._charging_squad = charging_squad
        self._resume = on_resolved
        self.decision_manager.request(
            reactor,
            f"{PHOTON_GRENADES_NAME} ({PHOTON_GRENADES_CP} CP): {charging_squad.name} is "
            f"charging - dazzle it (Battle-shock test, and -"
            f"{PHOTON_GRENADES_CHARGE_PENALTY} to its Charge roll)?",
            [(f"Use on {squad.name}", (lambda s=squad: self._accept(s)))
             for squad in candidates]
            + [("Decline", self._decline)],
        )
        return True

    def _accept(self, defender):
        used = self.stratagem_controller.use(defender.owner, self._stratagem, [defender])
        if not used:
            self._finish()
        return used

    def _decline(self):
        self._finish()
        return True

    def _apply(self, controller, player, targets):
        charging = self._charging_squad
        if charging is None:
            return
        # The PENALTY first, so it is already on the unit before any roll can
        # happen; then the test. DiceManager holds one roll at a time, so the
        # order is what keeps the charge roll from slipping past the open
        # Battle-shock test.
        charging.photon_grenades_penalty = True
        if self.game_log is not None:
            self.game_log.add(
                f"{PHOTON_GRENADES_NAME}: {charging.name} takes a Battle-shock test and "
                f"subtracts {PHOTON_GRENADES_CHARGE_PENALTY} from its Charge roll this phase."
            )
        # Rule 01.07's outcome has exactly one implementation; this only decides
        # WHEN the test happens. The charge resumes on the acknowledgement of
        # that roll, not here - the same two-step
        # (start_forced_roll -> AWAITING_SHOCK -> resume) game/
        # grav_inhibitor_field.py uses at this identical instant.
        if self.battle_shock_controller is not None and self.battle_shock_controller.start_forced_roll(
            charging, PHOTON_GRENADES_NAME,
        ):
            self._awaiting_shock = True
            return
        self._finish()

    def on_dice_acknowledged(self):
        """Wired into main.py's dice-ack chain after battle_shock_controller's,
        so the test's outcome is applied before the charge resumes."""
        if not self._awaiting_shock:
            return
        self._awaiting_shock = False
        self._finish()

    def _finish(self):
        """Hand the charge back. The active player goes back to the charging
        side first: the reaction moved it to the defender to ask the question,
        and this is still the charging player's Charge phase."""
        charging = self._charging_squad
        if self.turn_tracker is not None and charging is not None:
            self.turn_tracker.set_active(charging.owner)
        self._charging_squad = None
        resume, self._resume = self._resume, None
        if resume is not None:
            resume()
