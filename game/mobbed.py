"""Beast Snagga Boyz' Mobbed (2026-09 Ork codex).

RULE (verbatim, rules/orks/Beast Snagga Boyz.md):
  "Mobbed: When this unit ends a charge move, each enemy MONSTER/VEHICLE unit
   engaged with this unit makes a battle-shock roll:
   - With -1 to that battle-shock roll.
   - Or: With -2 to that battle-shock roll if this unit has 13+ models."

WHERE IT HANGS: ChargeController.on_charge_move_finished - rule 11.04's "ends a
Charge move", fired after the charge is concluded (the hook Crimson Harvest and
Kroot Linebreakers use). A charge that fell short engages nothing, so it simply
finds no target.

THE TESTS ARE FORCED: BattleShockController.start_forced_roll() with a penalty,
the entry every out-of-turn test in this engine uses (so, like its eleven
siblings, it bypasses Insane Bravery's Command-phase offer - pinned by name in
test_event_chain_wiring.py section 21).

"-2 IF THIS UNIT HAS 13+ MODELS" REPLACES the -1 (the "Or:" bullet), counted
in living models of the whole unit at the moment the charge ends - an attached
Beastboss counts, as the unit is one unit (rule 19.01).

A QUEUE: a charge can end engaged with several MONSTER/VEHICLE units, and a
BattleShockController holds one test at a time. The queue itself is
game/forced_shock_queue.py - written here first, and moved there when Blitz
Brigade's Impending Krunch became its second user (Mecha Orks G4). main.py's dice
acknowledgement releases the next test, after battle_shock_controller's own.

Mandatory - no choice, no AI path needed.
"""

from game.engagement import units_are_engaged
from game.forced_shock_queue import ForcedShockQueue
from game.squad import is_monster_or_vehicle_unit, unit_wide_ability

MOBBED_NAME = "Mobbed"
MOBBED_PENALTY = 1
MOBBED_BIG_MOB_PENALTY = 2
#: "if this unit has 13+ models"
MOBBED_BIG_MOB_MODELS = 13


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "mobbed"))


def living_models(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def penalty_for(squad):
    return MOBBED_BIG_MOB_PENALTY if len(living_models(squad)) >= MOBBED_BIG_MOB_MODELS else MOBBED_PENALTY


def targets_for(squad, all_tokens):
    """Each enemy MONSTER/VEHICLE unit engaged with `squad`, by name."""
    if squad is None:
        return []
    enemies = {t.squad for t in all_tokens or ()
               if t.squad is not None and t.squad.owner != squad.owner and not t.is_dead()}
    return sorted(
        (e for e in enemies
         if living_models(e) and is_monster_or_vehicle_unit(e) and units_are_engaged(squad, e)),
        key=lambda s: s.name)


class MobbedController:
    def __init__(self, battle_shock_controller=None, all_tokens=None, game_log=None):
        self.battle_shock_controller = battle_shock_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self.queue = ForcedShockQueue(battle_shock_controller, game_log)

    def on_charge_move_finished(self, squad):
        if not has_ability(squad):
            return False
        targets = targets_for(squad, self.all_tokens)
        if not targets:
            return False
        penalty = penalty_for(squad)
        for target in targets:
            self.queue.enqueue(
                target, penalty, MOBBED_NAME,
                f"{MOBBED_NAME}: {squad.name} ended its charge engaged with "
                f"{target.name}, which takes a Battle-Shock test at -{penalty}.")
        return self.queue.drain()

    def on_dice_acknowledged(self):
        """The queue's re-entry point - one more test per acknowledged roll."""
        return self.queue.on_dice_acknowledged()

    @property
    def is_busy(self):
        return self.queue.is_busy
