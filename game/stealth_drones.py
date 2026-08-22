"""Ghostkeel Battlesuit's own "Stealth Drones" ability, as supplied by the
user (not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/retaliation_cadre.py etc. for the other
user-supplied T'au abilities).

RULE: Twice per battle, after an attack has been allocated to this model,
you can change the Damage characteristic of that attack to 0. Designer's
Note: place two Stealth Drone tokens next to the unit, removing one each
time this ability has been used - modeled here as a plain per-model integer
counter instead of literal tokens, since nothing else in this engine tracks
physical markers like that.

Scope: "an attack has been allocated to this model" is rule 05.04's normal
Allocate Attack step, i.e. game/damage_resolution.py's DamageAllocationSession
- NOT the separate Mortal Wounds allocation (06.02), which uses different
wording and isn't literally "an attack" being allocated. So this is wired
into DamageAllocationSession only (used identically by both shooting.py's
and fight.py's normal combat resolution - the ability isn't restricted to
ranged attacks either), not MortalWoundAllocationSession/
DevastatingWoundAllocationSession.

Runs BEFORE Feel No Pain in the allocation order (see DamageAllocationSession.
_apply()): if this reduces the attack's Damage to 0, there's nothing left
for Feel No Pain to roll against anyway.

A genuine "you can" choice - not automatic, and not a dice roll - so it's
offered via game.decision.DecisionManager, exactly like [LETHAL HITS]/
[PRECISION]/[TWIN-LINKED] already are. Requesting through DecisionManager is
also what makes this automatically resolvable by the AI with no extra
wiring: ai/agent_driver.py's _maybe_resolve_decision() already generically
resolves ANY pending DecisionManager break point that belongs to the
current player - it doesn't know or care which ability opened it."""


class StealthDronesController:
    def __init__(self, decision_manager=None, game_log=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self._uses_remaining = {}  # model.id -> int, lazily seeded from profile.stealth_drones on first use

    def _remaining(self, model):
        if model.id not in self._uses_remaining:
            self._uses_remaining[model.id] = model.profile.stealth_drones
        return self._uses_remaining[model.id]

    def available(self, model):
        return model.profile.stealth_drones > 0 and self._remaining(model) > 0

    def maybe_offer(self, model, amount, on_resolved):
        """Called with the model that has just been allocated an attack
        dealing `amount` damage. If the choice is worth offering (ability
        available, a non-zero amount to actually reduce, a DecisionManager
        to ask through), requests it and returns True - the caller must
        wait for `on_resolved(final_amount)` instead of continuing
        synchronously (DecisionManager.request() never resolves inline, see
        its own docstring). Returns False otherwise - nothing to wait for,
        the caller should proceed immediately with the unmodified amount."""
        if amount <= 0 or not self.available(model) or self.decision_manager is None:
            return False
        owner = model.squad.owner if model.squad is not None else None
        remaining = self._remaining(model)
        self.decision_manager.request(
            owner,
            f"{model.profile.name}: Stealth Drones ({remaining} remaining) - "
            f"reduce this attack's Damage characteristic to 0?",
            [
                ("Use a Stealth Drone (Damage -> 0)", lambda: self._use(model, on_resolved)),
                ("Don't use it", lambda: on_resolved(amount)),
            ],
        )
        return True

    def _use(self, model, on_resolved):
        self._uses_remaining[model.id] -= 1
        if self.game_log is not None:
            self.game_log.add(
                f"{model.profile.name}: Stealth Drone used - this attack's Damage is reduced to 0 "
                f"({self._uses_remaining[model.id]} remaining)."
            )
        on_resolved(0)
