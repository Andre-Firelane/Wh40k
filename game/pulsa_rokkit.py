"""The Tankbustas' Pulsa Rokkit (2026-09 Ork codex) - a WARGEAR ability.

RULE (verbatim, rules/orks/Tankbustas.md):
  "Pulsa Rokkit: In your Shooting phase, when this unit is selected to shoot,
   you can select one enemy MONSTER/VEHICLE unit within 24" of this unit. If you
   do. this unit's attacks that target that unit have:
   - +1 AP
   - [LETHAL HITS]"

IT IS WARGEAR. Wahapedia's new layout prints it inside ABILITIES with the
wargear icon (class dsWargearAbility), and the WARGEAR OPTIONS offer it to one
Tankbusta ("1 Tankbusta model can be equipped with one of the following: 1 Busta
Rokkit Launcha, 1 Pulsa Rokkit"). So a unit has the ability while a living model
carries the item (Token.pulsa_rokkit, set by the datasheet's Gear effect) - the
bearer dies, the ability goes.

WHERE IT HANGS. "When this unit is selected to shoot" is
ShootingController.start_shooting(), the instant Nova Charge and Ammo Runts are
offered at; "in YOUR Shooting phase" is read off the live clock, so a reactive
shot is never offered it. The choice is held here as a MARK - {id(unit): target}
- and read by _adjusted_weapon() for every attack of that unit against that
target: "+1 AP" (the AP goes one more negative) and [LETHAL HITS]. In the chain,
not at the wound step, because the Save roll reads the AP and _crit_note() reads
[LETHAL HITS] off the weapon the chain returns. The mark lasts the phase (a unit
is selected to shoot once per phase) and ignores a reactive activation.

"YOU CAN SELECT" - a human is asked (a board pick, with Decline); nothing is
spent, but a mark on the wrong unit buys nothing, so it stays a choice. The AI
always marks, the unit its Tankbustas can hurt most by the shared damage-value
ranking (main.py's _best_damage_target) - 0 API calls.
"""

import copy

from game import ai_mode
from game.mortal_wound_abilities import enemy_squads, gap_to
from game.squad import is_monster_or_vehicle_unit
from game.turn import PHASE_SHOOTING
from game.weapons import RANGED

PULSA_ROKKIT_NAME = "Pulsa Rokkit"
#: "within 24\" of this unit".
PULSA_ROKKIT_RANGE_IN = 24
#: "+1 AP".
PULSA_ROKKIT_AP_BONUS = 1


def bearers(squad):
    return [m for m in getattr(squad, "models", ()) or ()
            if not m.is_dead() and getattr(m, "pulsa_rokkit", False)]


def has_ability(squad):
    return squad is not None and bool(bearers(squad))


def targets(squad, all_tokens):
    """Enemy MONSTER/VEHICLE units within 24" of some living model of this unit."""
    models = [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]
    return [enemy for enemy in enemy_squads(squad, all_tokens)
            if is_monster_or_vehicle_unit(enemy)
            and any(gap_to(m, enemy) <= PULSA_ROKKIT_RANGE_IN for m in models)]


class PulsaRokkitController:
    def __init__(self, decision_manager=None, turn_tracker=None, game_log=None,
                 game_state=None, auto_players=(), target_pick=None):
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.game_state = game_state
        self.auto_players = ai_mode.players(auto_players)
        self.target_pick = target_pick
        self._marks = {}   # id(unit) -> the marked enemy unit, this phase

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    def why_not(self, squad):
        if squad is None:
            return "no unit"
        if not has_ability(squad):
            return "no model carries a Pulsa Rokkit"
        tt = self.turn_tracker
        if tt is not None and (tt.phase != PHASE_SHOOTING or tt.turn_owner != squad.owner):
            return "not your Shooting phase"
        if id(squad) in self._marks:
            return "already marked a unit this phase"
        if not targets(squad, self._tokens()):
            return "no enemy MONSTER/VEHICLE unit within 24\""
        return None

    def can_use(self, squad):
        return self.why_not(squad) is None

    def offer(self, squad):
        """Called from start_shooting(). True when anything was marked or asked."""
        if not self.can_use(squad):
            return False
        candidates = targets(squad, self._tokens())
        if squad.owner in self.auto_players or self.decision_manager is None:
            return self.mark(squad, self._pick(squad, candidates))
        options = [("%s: %s" % (PULSA_ROKKIT_NAME, t.name), (lambda target=t: self.mark(squad, target)), t)
                   for t in candidates]
        options.append(("Decline", None))
        self.decision_manager.request(
            squad.owner,
            "%s: %s - +1 AP and [LETHAL HITS] against which MONSTER/VEHICLE unit?"
            % (squad.name, PULSA_ROKKIT_NAME),
            options)
        return True

    def _pick(self, squad, candidates):
        if self.target_pick is not None:
            chosen = self.target_pick(squad, candidates)
            if chosen is not None:
                return chosen
        return sorted(candidates, key=lambda s: s.name)[0] if candidates else None

    def mark(self, squad, target):
        if squad is None or target is None or not self.can_use(squad):
            return False
        if target not in targets(squad, self._tokens()):
            return False
        self._marks[id(squad)] = target
        self._log("%s: %s - its attacks against %s have +1 AP and [LETHAL HITS] this phase."
                  % (squad.name, PULSA_ROKKIT_NAME, target.name))
        return True

    def marked_target(self, squad):
        return self._marks.get(id(squad)) if squad is not None else None

    def adjusted_weapon(self, weapon, squad, target_squad, reactive=False):
        """The chain link read by ShootingController._adjusted_weapon()."""
        if reactive or weapon is None or getattr(weapon, "weapon_type", None) != RANGED:
            return weapon
        if target_squad is None or self.marked_target(squad) is not target_squad:
            return weapon
        granted = copy.copy(weapon)
        granted.ap = weapon.ap - PULSA_ROKKIT_AP_BONUS
        granted.lethal_hits = True
        return granted

    def reset_phase(self):
        self._marks.clear()
