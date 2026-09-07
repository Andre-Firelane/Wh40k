"""The Twin Lance's own "Neocapacitor Shields" ability, as supplied by the
user (not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/exemplars_of_montka.py and
game/retro_thrusters.py for this datasheet's other two).

RULE: At the start of your opponent's Charge phase, you can select one enemy
unit (excluding Monster and Vehicle units) within 12" of this unit. That unit
must take a Battle-shock test and, until the end of the turn, subtract 1 from
Charge rolls made for that unit.

REACTIVE, BUT AT A PHASE BOUNDARY
---------------------------------
"At the start of your opponent's Charge phase" is a phase boundary, so this
is wired where every other phase-start trigger already is - main.py's
advance_turn_phase(), on entering PHASE_CHARGE - rather than needing the
kind of mid-sequence hook Stim Injectors or Grav-Inhibitor Field required.
The player who owns the ability is the one NOT taking the turn, so the
prompt goes to turn_tracker's non-active player.

"You can", so it is a real choice offered through DecisionManager - which
is also what makes it AI-resolvable with no extra wiring, since
ai/agent_driver.py's _maybe_resolve_decision() generically answers any
pending break point belonging to the current player.

WHERE THE -1 LANDS
------------------
On the CHARGING unit, not on a target - "Charge rolls made for that unit" -
so unlike the Grav-inhibitor Drone (game/grav_inhibitor_drone.py, whose -2
depends on WHO is being charged) this one is a plain flag on the affected
squad, read wherever the Charge roll becomes a distance. That is
game/charge.py's _capped_roll(), the same single place War Horde's 'Ere We
Go adds its +2 - which also gets rule 15.11's "if the result is greater than
6 AFTER MODIFIERS" right for free.

The two negative sources interact, and deliberately: the Grav-inhibitor
Drone's own text says its -2 "is not cumulative with any other negative
modifiers to that Charge roll", so a unit under both suffers -2 in total,
not -3. That combination is resolved in game/charge.py, where both are
known; each module keeps its own value.

"UNTIL THE END OF THE TURN"
---------------------------
A unit-level flag cleared in main.py's end-of-turn block, alongside
fights_first / set_up_this_turn / charge_locked_until_end_of_turn /
ere_we_go_active - the other flags with exactly this lifetime.
expire_for_turn() below is the one definition of that, so it stays testable
without the game loop.
"""

from game.squad import is_monster_or_vehicle_unit

NEOCAPACITOR_RANGE_IN = 12.0
NEOCAPACITOR_CHARGE_PENALTY = 1


def unit_has_neocapacitor_shields(squad):
    """True while at least one live model with the ability is in the unit -
    the same rule 19.04 reading every other datasheet ability here uses."""
    if squad is None:
        return False
    return any(m.profile.neocapacitor_shields for m in squad.models if not m.is_dead())


def charge_penalty_for(squad):
    """The -1 this ability imposes on `squad`'s own Charge rolls, or 0."""
    if squad is None:
        return 0
    return NEOCAPACITOR_CHARGE_PENALTY if squad.neocapacitor_shielded else 0


def expire_for_turn(squads=()):
    """End of turn: "until the end of the turn" is up."""
    for squad in squads:
        squad.neocapacitor_shielded = False


class NeocapacitorShieldsController:
    def __init__(self, battle_shock=None, decision_manager=None, turn_tracker=None, all_tokens=None, game_log=None):
        self.battle_shock = battle_shock
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log

    def _owners_with_ability(self):
        owners = {}
        for token in self.all_tokens:
            squad = token.squad
            if squad is None or not unit_has_neocapacitor_shields(squad):
                continue
            owners.setdefault(squad.owner, []).append(squad)
        return {owner: list(dict.fromkeys(squads)) for owner, squads in owners.items()}

    def eligible_targets(self, shielding_squad):
        """"one enemy unit (excluding Monster and Vehicle units) within 12"
        of this unit" - measured edge to edge like every other range check
        here, and excluding units with nothing left alive."""
        if shielding_squad is None:
            return []
        candidates = {
            t.squad for t in self.all_tokens
            if t.squad is not None and t.squad.owner != shielding_squad.owner
            and any(not m.is_dead() for m in t.squad.models)
            and not is_monster_or_vehicle_unit(t.squad)
        }
        return sorted(
            (s for s in candidates if shielding_squad.min_distance_to(s) <= NEOCAPACITOR_RANGE_IN),
            key=lambda s: s.name,
        )

    def offer_at_charge_phase_start(self, active_player):
        """Called as the Charge phase begins. `active_player` is whose turn
        it is - so the ability belongs to anybody ELSE.

        Returns whether a choice was requested. Offers for one shielding
        unit at a time (the first with any eligible target); with two such
        units on the board the second would need its own trigger, which no
        current army composition can produce - a single Epic Hero unit."""
        if self.decision_manager is None:
            return False
        for owner, squads in self._owners_with_ability().items():
            if owner == active_player:
                continue  # "your OPPONENT's Charge phase" - not your own
            for squad in squads:
                targets = self.eligible_targets(squad)
                if not targets:
                    continue
                options = [
                    (f"Neocapacitor Shields: {t.name}", self._make_effect(squad, t), t) for t in targets
                ]
                options.append(("Decline", lambda: None))
                self.decision_manager.request(
                    owner,
                    f"{squad.name} - Neocapacitor Shields: force a Battle-shock test and -1 to "
                    'Charge rolls on one enemy unit within 12"?',
                    options,
                )
                return True
        return False

    def _make_effect(self, shielding_squad, target):
        def effect():
            target.neocapacitor_shielded = True
            if self.game_log is not None:
                self.game_log.add(
                    f"{shielding_squad.owner}: Neocapacitor Shields - {target.name} takes a "
                    "Battle-shock test and suffers -1 to Charge rolls until the end of the turn."
                )
            # Sequenced after the flag, not before: the Battle-shock test is
            # a dice step that resolves later, and the -1 applies regardless
            # of how it turns out.
            if self.battle_shock is not None:
                self.battle_shock.start_forced_roll(target, "Neocapacitor Shields")

        return effect
