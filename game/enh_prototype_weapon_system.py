"""Retaliation Cadre Enhancement: Prototype Weapon System (15 pts).

RULE (verbatim, rules/tau_empire/detachments/Retaliation Cadre.md):
  T'AU EMPIRE BATTLESUIT model only. Each time the bearer is selected to shoot,
  select either the [LETHAL HITS] or [SUSTAINED HITS 1] ability. Until those
  attacks are resolved, ranged weapons equipped by the bearer have the selected
  ability.

A REAL CHOICE, SO IT IS ASKED
-----------------------------
Unlike Kauyon's "you can ignore any or all modifiers" - resolved automatically
because one answer is always better - this is a genuine fork with no dominant
side: [LETHAL HITS] is worth more against high Toughness, [SUSTAINED HITS 1]
against a target the bearer already wounds easily. So it goes through
DecisionManager, once per shooting activation of the bearer's unit.

Once per ACTIVATION, not once per weapon group: "each time the bearer is
SELECTED TO SHOOT" names ShootingController.start_shooting(), and "until those
attacks are resolved" names the end of that same activation. Those are exactly
the two seams game/targeting_array.py already opens and closes its own ledger
on (begin_activation/end_activation), so this uses them rather than inventing a
third notion of "an activation".

WHERE THE CHOICE IS KEPT, AND WHY ON THE TOKEN
-----------------------------------------------
On the bearer TOKEN, not in a dict inside this controller, for the same reason
game/psychic_communion.py keeps its per-model bonus there:
ShootingController._attack_key() is a module-level function with no controller
in scope, and this grant HAS to be part of that key. The key is what makes a
weapon group homogeneous, and several per-model things are read off
`group["pairs"][0]` - the one-representative shortcut, which is exact only for
things in the key. After a rule 19.01 merge the bearer is one model among ten,
so without it a Commander's chosen keyword would be handed to every Crisis suit
that happened to share his BS/S/AP/D, or lost to one that did not.

PER MODEL, NOT PER UNIT. "ranged weapons equipped by THE BEARER" - the
bodyguards get nothing. That is the difference from Mont'ka's own [LETHAL HITS]
clause, which covers the whole Guided unit, and it has its own test line
because the two are otherwise the same keyword arriving at the same place.

NEVER DOWNGRADES, the same two guards game/kauyon.py carries for the same
keyword: a weapon already printing [SUSTAINED HITS 2], or a dice X, is left
alone - "have the ability" grants it, it does not set the value.

NO AI PATH IS NEEDED, AND NONE IS ADDED (the standing T'au rule). The engine
must not hang on a prompt nobody answers, so an owner in `auto_players` gets a
deterministic answer instead: [LETHAL HITS] when the bearer's best ranged
weapon would otherwise fail to wound on better than a 5+, [SUSTAINED HITS 1]
otherwise. That is the same shape 'Ard as Nails and the six Awakened Dynasty
protocols use - a rule answering its own prompt, not a decision routed through
ai/agent_driver.py.
"""

import copy

from game import ai_mode, enhancements
from game.weapons import RANGED

PROTOTYPE_WEAPON_SYSTEM = "Prototype Weapon System"
LETHAL_HITS = "lethal_hits"
SUSTAINED_HITS = "sustained_hits"
SUSTAINED_HITS_GRANTED = 1

# The transient attribute on the bearer's token - see the module docstring for
# why it lives there and not in the controller.
CHOICE_ATTR = "prototype_weapon_choice"


def bearer_models(squad):
    """Every live bearer in `squad`, with the detachment checked."""
    if not enhancements.is_active(squad, PROTOTYPE_WEAPON_SYSTEM):
        return []
    return [m for m in enhancements.bearer_models(squad, PROTOTYPE_WEAPON_SYSTEM)]


def choice_for(model):
    """The ability chosen for this model's current activation, or None.

    Read straight off the token so ShootingController._attack_key() can ask it
    without a controller in scope."""
    if model is None:
        return None
    return getattr(model, CHOICE_ATTR, None)


def attack_key(model):
    """What _attack_key() adds for this Enhancement.

    A string (or "") rather than the raw None so the key stays hashable and
    comparable; "" for every model without a choice, so no group that already
    exists splits."""
    return choice_for(model) or ""


def adjusted_weapon(weapon, model):
    """Grant the chosen keyword to one of the BEARER's ranged weapons.

    Takes the MODEL rather than the squad, because that is what the rule names
    - and because game/shooting.py measures per shooter on the hot path anyway.
    Returns the weapon unchanged when nothing applies, and a COPY when it does;
    the shared WeaponProfile instance is never mutated.
    """
    if weapon is None or weapon.weapon_type != RANGED:
        return weapon
    chosen = choice_for(model)
    if chosen == LETHAL_HITS and not weapon.lethal_hits:
        granted = copy.copy(weapon)
        granted.lethal_hits = True
        return granted
    if chosen == SUSTAINED_HITS:
        if getattr(weapon, "sustained_hits", 0) >= SUSTAINED_HITS_GRANTED:
            return weapon
        if getattr(weapon, "sustained_hits_notation", None) is not None:
            return weapon
        granted = copy.copy(weapon)
        granted.sustained_hits = SUSTAINED_HITS_GRANTED
        return granted
    return weapon


class PrototypeWeaponSystemController:
    """Wired to ShootingController's begin/end-of-activation seams in main.py,
    the same pair game/targeting_array.py uses."""

    def __init__(self, decision_manager=None, game_log=None, auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def begin_activation(self, squad):
        """"Each time the bearer is selected to shoot" - offer the choice.

        Returns True if anything was asked or decided, so a caller (and a test)
        can tell the no-bearer case from the answered one."""
        bearers = bearer_models(squad)
        if not bearers:
            return False
        asked = False
        for model in bearers:
            if self._offer(squad, model):
                asked = True
        return asked

    def _offer(self, squad, model):
        if squad.owner in self.auto_players or self.decision_manager is None:
            self.choose(model, self._auto_choice(model))
            return True
        self.decision_manager.request(
            squad.owner,
            f"{PROTOTYPE_WEAPON_SYSTEM}: which ability for {model.profile.name}'s "
            f"ranged weapons this activation?",
            [
                ("[LETHAL HITS]", lambda m=model: self.choose(m, LETHAL_HITS)),
                ("[SUSTAINED HITS 1]", lambda m=model: self.choose(m, SUSTAINED_HITS)),
            ],
        )
        return True

    def _auto_choice(self, model):
        """The deterministic answer for a non-human owner - see the module
        docstring. Deliberately blind to the target: "selected to shoot"
        happens BEFORE targets are chosen, so there is no target to measure
        against, and pretending otherwise would be measuring the wrong board.

        [LETHAL HITS] converts critical hits straight into wounds, which is
        worth most on a weapon whose Strength is modest; [SUSTAINED HITS 1]
        adds hits, which is worth most when those hits convert. With no target
        in hand, Strength is the only signal available, so the split is on it.
        """
        strengths = [w.strength for w in model.weapons if w.weapon_type == RANGED]
        if strengths and max(strengths) <= 5:
            return LETHAL_HITS
        return SUSTAINED_HITS

    def choose(self, model, ability):
        if ability not in (LETHAL_HITS, SUSTAINED_HITS):
            return False
        setattr(model, CHOICE_ATTR, ability)
        label = "[LETHAL HITS]" if ability == LETHAL_HITS else "[SUSTAINED HITS 1]"
        squad = getattr(model, "squad", None)
        owner = getattr(squad, "owner", "?")
        self._log(f"{owner}: {model.profile.name}'s {PROTOTYPE_WEAPON_SYSTEM} grants "
                  f"{label} to its ranged weapons this activation.")
        return True

    def end_activation(self, squad):
        """"Until those attacks are resolved" - the grant ends with the
        activation. Cleared for EVERY model of the unit, not only for models
        that still have a choice recorded, so a bearer that died mid-activation
        cannot leave one behind for a rule 19.01 merge to inherit."""
        if squad is None:
            return
        for model in squad.models:
            if hasattr(model, CHOICE_ATTR):
                delattr(model, CHOICE_ATTR)
