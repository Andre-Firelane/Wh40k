"""Hypercrypt Legion Stratagem: Quantum Deflection (1CP).

RULE (verbatim, rules/necrons/detachments/Hypercrypt Legion.md):
  WHEN:   Your opponent's Shooting phase or the Fight phase, just after an enemy
          unit has selected its targets.
  TARGET: One NECRONS VEHICLE unit from your army that was selected as the target
          of one or more of the attacking unit's attacks.
  EFFECT: Until the end of the phase, models in your unit have a 4+ invulnerable
          save.

THE EFFECT IS WINDRIDER HOST'S SPIRALLING EVASION word for word
(game/windrider_spiralling_evasion.py), and it is read in the same place: a squad
flag folded into game/invulnerable_save.py's effective_invulnerable_save() through
_better(), rule 05.04's own "take whichever is better". So a Monolith that
already prints a 4+ cannot be made worse by it - and, below, is not offered it.

THE ONE PRINTED DIFFERENCE IS THE WHEN: "your opponent's Shooting phase OR THE
FIGHT PHASE". So this controller sits in BOTH of main.py's target-reaction
tuples, where Spiralling Evasion sits in the shooting one only. The Fight phase
is shared (rule 12.04) and belongs to nobody, so in melee it is offered whoever's
turn it is; in the Shooting phase only in the opponent's.

"MODELS IN YOUR UNIT" - every model of the unit, a VEHICLE unit being asked by
rule 19.03's keyword pooling (any living model).

NEVER OFFERED WHEN IT BUYS NOTHING: a unit already under it this phase, or one
whose every living model already has an invulnerable save of 4+ or better
against this kind of attack. The printed save is measured with the grant itself
still off, so the test cannot see its own answer.

THE AI (user decision: full use) buys it when the attack would otherwise be
saved on worse than a 4+: the best AP among the attacker's weapons of this
attack type, through damage_resolution.save_thresholds() - the one definition
of what a save roll turns on - for the unit's first living model.
"""

from game import ai_mode, attached_units, necron_detachments
from game.stratagems import Stratagem
from game.thresholds import parse_threshold
from game.turn import PHASE_FIGHT, PHASE_SHOOTING
from game.weapons import MELEE, RANGED

QUANTUM_DEFLECTION_NAME = "Quantum Deflection"
QUANTUM_DEFLECTION_CP = 1
#: "models in your unit have a 4+ invulnerable save".
QUANTUM_DEFLECTION_SAVE = "4+"
SETTING = "HYPERCRYPT_LEGION_PLAYERS"


def is_active(squad):
    return bool(getattr(squad, "quantum_deflection_active", False))


def invulnerable_save_for(squad):
    """Read by game/invulnerable_save.py's fold. None means "no grant"."""
    return QUANTUM_DEFLECTION_SAVE if is_active(squad) else None


def reset_phase(squads=()):
    """"Until the end of the phase"."""
    for squad in squads or ():
        if is_active(squad):
            squad.quantum_deflection_active = False


def is_necrons_vehicle_unit(squad):
    """"One NECRONS VEHICLE unit" - both keywords, rule 19.03's pooling."""
    if squad is None or not necron_detachments.is_necrons_unit(squad):
        return False
    return attached_units.unit_has_keyword(squad, lambda m: getattr(m.profile, "vehicle", False))


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def grant_changes_anything(squad, melee=False):
    """Whether a 4+ invulnerable save is better than what at least one living
    model of the unit already has against this kind of attack."""
    from game.invulnerable_save import effective_invulnerable_save
    granted = parse_threshold(QUANTUM_DEFLECTION_SAVE)
    for model in _living(squad):
        current = parse_threshold(effective_invulnerable_save(model, melee=melee))
        if current is None or current > granted:
            return True
    return False


def worth_for_ai(attacker, target, melee=False):
    """The AI's answer: would this attack be saved on worse than a 4+?"""
    from game.damage_resolution import save_thresholds
    weapon_type = MELEE if melee else RANGED
    weapons = [w for m in _living(attacker) for w in m.weapons
               if getattr(w, "weapon_type", None) == weapon_type]
    models = _living(target)
    if not weapons or not models:
        return False
    worst = min(weapons, key=lambda w: (getattr(w, "ap", 0), w.name))
    sv, insv, ap = save_thresholds(models[0], worst)
    options = [t for t in ((sv - ap) if sv is not None else None, insv) if t is not None]
    best = min(options) if options else None
    return best is None or best > parse_threshold(QUANTUM_DEFLECTION_SAVE)


class QuantumDeflectionController:
    """In BOTH of main.py's target-reaction tuples - maybe_offer(attacker,
    target, melee=False)."""

    def __init__(self, stratagem_controller, turn_tracker=None, decision_manager=None,
                 game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._offered_this_phase = set()
        self._stratagem = Stratagem(name=QUANTUM_DEFLECTION_NAME, cp_cost=QUANTUM_DEFLECTION_CP,
                                    effect=self._grant)

    def reset_phase(self):
        self._offered_this_phase.clear()

    def _phase_allows(self, attacker, melee):
        tt = self.turn_tracker
        if tt is None:
            return False
        if melee:
            return tt.phase == PHASE_FIGHT          # "the Fight phase" - nobody's
        # "your OPPONENT'S Shooting phase" - the attacker's own turn.
        return tt.phase == PHASE_SHOOTING and tt.turn_owner == attacker.owner

    def can_use(self, attacker, target, melee=False):
        if self.stratagem_controller is None or attacker is None or target is None:
            return False
        if attacker.owner == target.owner:
            return False
        if not self._phase_allows(attacker, melee):
            return False
        if not necron_detachments.has_detachment(target.owner, SETTING):
            return False
        if not is_necrons_vehicle_unit(target):
            return False
        if is_active(target) or not grant_changes_anything(target, melee):
            return False
        return self.stratagem_controller.can_use(target.owner, self._stratagem, [target])

    def maybe_offer(self, attacker, target, melee=False):
        key = (id(attacker), id(target))
        if key in self._offered_this_phase:
            return False
        if not self.can_use(attacker, target, melee):
            return False
        self._offered_this_phase.add(key)
        if target.owner in self.auto_players:
            if worth_for_ai(attacker, target, melee):
                self.use(target, melee)
            return False
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            target.owner,
            f"{QUANTUM_DEFLECTION_NAME} ({QUANTUM_DEFLECTION_CP} CP): {attacker.name} has targeted "
            f"{target.name} - give it a {QUANTUM_DEFLECTION_SAVE} invulnerable save until the end "
            "of the phase?",
            [(f"Use ({QUANTUM_DEFLECTION_CP} CP)", lambda: self.use(target, melee)),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, target, melee=False):
        if self.stratagem_controller is None or target is None:
            return False
        if is_active(target) or not is_necrons_vehicle_unit(target):
            return False
        return self.stratagem_controller.use(target.owner, self._stratagem, [target])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.quantum_deflection_active = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{QUANTUM_DEFLECTION_NAME}: models in {squad.name} have a "
                    f"{QUANTUM_DEFLECTION_SAVE} invulnerable save until the end of the phase.")
