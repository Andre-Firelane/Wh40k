"""Riptide Battlesuit's own "Nova Charge" ability, as supplied by the user
(not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/stealth_drones.py for the Ghostkeel's own
datasheet ability and game/retaliation_cadre.py for that detachment's rule).

RULE: Once per battle, when this unit is selected to shoot in your Shooting
phase, select one ranged weapon equipped by this model. Until the end of the
phase, that weapon has the [DEVASTATING WOUNDS] ability.

WHEN IT IS OFFERED
------------------
"When this unit is selected to shoot" is ShootingController.start_shooting()
- the moment the activation opens, before a target has been chosen and long
before any die is rolled. Deliberately NOT start_snap_shooting(): a reactive
Snap Shot (Fire Overwatch, 15.08/15.09) happens at the end of the OPPONENT's
Movement phase, and this ability's WHEN names your own Shooting phase.

Offering it at that moment is also what makes the choice meaningful: the
grant lasts the whole phase, so it is worth spending on the activation where
the good target is - not automatically on the first unit that happens to
shoot. That is why it is a real "you can" choice with a decline option and
not an automatic effect, even though the ability text reads as mandatory
once triggered ("select one ranged weapon"): a once-per-battle resource the
player cannot decline to spend would be worse than no ability at all in
every turn where nothing worth shooting is in range.

A genuine choice, so it is offered via game.decision.DecisionManager, exactly
like [LETHAL HITS]/[PRECISION]/[TWIN-LINKED] and Stealth Drones already are.
Requesting through DecisionManager is also what makes this automatically
resolvable by the AI with no extra wiring: ai/agent_driver.py's
_maybe_resolve_decision() generically resolves ANY pending break point
belonging to the current player, without knowing which ability opened it.
DecisionManager.request() never resolves inline, and main.py's event chain
treats a pending decision as modal (it is checked before board clicks), so
the activation cannot advance to target selection until the player has
answered.

HOW A "WEAPON" IS IDENTIFIED
----------------------------
By the identity of the weapon INSTANCE sitting in model.weapons - the exact
same key rule 24.26's [ONE SHOT] ledger uses (`weapon.overcharge_of_id or
id(weapon)`, see shooting.py's _overcharge_instance()/_finish_group()).

That indirection is the whole point rather than incidental: a weapon with
two firing modes (this datasheet's own Ion Accelerator, Standard/Overcharge)
is ONE weapon in the datasheet's sense, but resolution hands the adjuster a
freshly built Overcharge instance with a different name and a different
id(). Matching on the name would silently drop the grant the moment the
player overcharged the very weapon they spent the ability on; matching on
`overcharge_of_id` follows it back to the real instance and keeps it.

Matching on the name would be wrong in the other direction too - two copies
of the same weapon on one model would both be granted by a single use.
Selecting an option therefore grants every instance that SHARES the chosen
name on that model (they are one datasheet weapon line, and they resolve in
one attack group anyway), but the stored grant is still a set of instance
ids, so nothing else on the board can collide with it.
"""

import copy


def _ranged_weapons(model):
    from game.weapons import RANGED

    return [w for w in getattr(model, "weapons", ()) if w.weapon_type == RANGED]


def weapon_instance_key(weapon):
    """The id of the real weapon instance this attack is being made with -
    following an alternate-firing-mode instance back to the Standard-mode
    weapon in model.weapons it stands for. Same key rule 24.26's [ONE SHOT]
    ledger uses; see the module docstring for why the indirection matters
    here."""
    return getattr(weapon, "overcharge_of_id", None) or id(weapon)


def nova_charge_adjusted_weapon(weapon, pairs):
    """"That weapon has the [DEVASTATING WOUNDS] ability" (24.10) modeled as
    an actual characteristic change (shallow copy, same reasoning as
    arrokon_adjusted_weapon()/bonded_heroes_adjusted_weapon() - the shared
    WeaponProfile instance is never mutated).

    Whether this group is the granted weapon is decided from its
    representative pair (pairs[0]), the same simplification every other
    adjuster in this codebase uses. Here it is exact on both halves: a group
    IS one weapon by construction (_attack_key()), and the only datasheet
    carrying this ability is a one-model unit, so the representative model
    is the only model.

    GRANTS the ability rather than overwriting it: a weapon that already has
    [DEVASTATING WOUNDS] printed keeps it and the two never stack (same
    reading, and same code shape, as game/war_horde.py's Get Stuck In)."""
    if not pairs:
        return weapon
    model, group_weapon = pairs[0]
    squad = getattr(model, "squad", None)
    if squad is None:
        return weapon
    grants = getattr(squad, "nova_charge_grants", None)
    if not grants:
        return weapon
    if weapon_instance_key(group_weapon) not in grants.get(model.id, ()):
        return weapon
    if weapon.devastating_wounds:
        return weapon
    boosted = copy.copy(weapon)
    boosted.devastating_wounds = True
    return boosted


class NovaChargeController:
    """Per-battle bookkeeping plus the "until the end of the phase" grant.
    The effect itself is nova_charge_adjusted_weapon() above, chained into
    game/shooting.py's resolution the same way Bonded Heroes/Starscythe/
    Drive-by Dakka/The Arro'kon Protocol already are.

    Uses are tracked per MODEL (lazily seeded from profile.nova_charge, same
    shape as StealthDronesController), not per unit: the ability text says
    "equipped by this model", and a per-model ledger stays correct if this
    ability ever lands on a multi-model datasheet or if two Riptides are
    merged into one unit by rule 19.01."""

    def __init__(self, decision_manager=None, game_log=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self._uses_remaining = {}  # model.id -> int, lazily seeded on first use

    def _remaining(self, model):
        if model.id not in self._uses_remaining:
            self._uses_remaining[model.id] = model.profile.nova_charge
        return self._uses_remaining[model.id]

    def available(self, model):
        return (
            model.profile.nova_charge > 0
            and not model.is_dead()
            and self._remaining(model) > 0
            and bool(_ranged_weapons(model))
        )

    def reset_phase(self, squads=()):
        """End of phase: the grant expires ("until the end of the phase").
        The per-battle counter is NOT touched here - a spent use stays spent.

        Lives here rather than in main.py's phase loop so "when does this
        stop applying" has exactly one answer, and so it is testable without
        standing up the whole game loop - same shape as
        ArrokonProtocolController.reset_phase(). Callers pass every squad on
        the board; only the active player can ever hold a grant, but
        clearing both armies costs nothing and cannot strand one."""
        for squad in squads:
            squad.nova_charge_grants = {}

    def _weapon_options(self, model):
        """[(display name, [instance ids]), ...] - one entry per distinct
        ranged weapon NAME on this model, in the model's own weapon order
        (i.e. datasheet order), each carrying every instance that shares
        that name. See the module docstring on why the option is by name but
        the grant is by instance id."""
        options = []
        by_name = {}
        for weapon in _ranged_weapons(model):
            if weapon.name not in by_name:
                by_name[weapon.name] = []
                options.append(weapon.name)
            by_name[weapon.name].append(id(weapon))
        return [(name, by_name[name]) for name in options]

    def maybe_offer(self, squad):
        """Called as a unit is selected to shoot. Requests the choice if any
        model in it still has a use available, and returns True; returns
        False when there is nothing to ask (no such model, no
        DecisionManager, or the unit already holds a grant this phase).

        The caller does not have to wait for the answer - the activation
        opens into target selection either way, and main.py's modal
        decision handling is what actually keeps the player from clicking
        past it. Nothing downstream reads the grant until dice are rolled."""
        if squad is None or self.decision_manager is None:
            return False
        if getattr(squad, "nova_charge_grants", None):
            return False  # already used this phase - the grant is up
        model = next((m for m in squad.models if self.available(m)), None)
        if model is None:
            return False
        options = [
            (f"Nova Charge: {name} gains [DEVASTATING WOUNDS]", self._make_grant(squad, model, name, ids))
            for name, ids in self._weapon_options(model)
        ]
        options.append(("Save Nova Charge for later", lambda: None))
        self.decision_manager.request(
            squad.owner,
            f"{squad.name} - Nova Charge (once per battle): give one ranged weapon "
            "[DEVASTATING WOUNDS] until the end of the phase?",
            options,
        )
        return True

    def _make_grant(self, squad, model, weapon_name, instance_ids):
        def grant():
            # Re-checked at resolution time, not just at offer time: a
            # DecisionManager request is a queue entry, so an arbitrary
            # amount of game state can change between asking and answering.
            if not self.available(model):
                return
            self._uses_remaining[model.id] = self._remaining(model) - 1
            grants = getattr(squad, "nova_charge_grants", None) or {}
            grants[model.id] = set(instance_ids) | set(grants.get(model.id, ()))
            squad.nova_charge_grants = grants
            if self.game_log is not None:
                self.game_log.add(
                    f"{squad.owner}: Nova Charge - {squad.name}'s {weapon_name} has "
                    "[DEVASTATING WOUNDS] until the end of the phase."
                )

        return grant
