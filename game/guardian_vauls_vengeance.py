"""Guardian Battlehost Stratagem: Vaul's Vengeance (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Guardian Battlehost.md):
  WHEN:   Your opponent's Shooting phase or the Fight phase, just after an
          enemy unit destroys a DIRE AVENGERS or GUARDIANS unit from your army.
  TARGET: One WAR WALKERS unit from your army.
  EFFECT: After that enemy unit has finished making its attacks, your unit can
          shoot as if it were your Shooting phase, but when resolving those
          attacks, it can only target that enemy unit (and only if it is an
          eligible target).
  RESTRICTIONS: You can only use this Stratagem once per battle round.

STRUCTURALLY PROTOCOL OF THE VENGEFUL STARS, and it takes that module's shape:
the trigger is a whole UNIT dying, and the effect is
ShootingController.start_reactive_shooting(squad, restrict_to=[killer]) - a
FULL activation, not rule 15.09's deliberately weaker Snap Shooting, because
the printed text says "as if it were your Shooting phase". `restrict_to` is
enforced in _is_valid_target_squad(), the one place that decides what may be
shot at, so no second filter can drift from it.

"ONCE PER BATTLE ROUND" IS NOT max_per_battle. Stratagem's `max_per_battle` is
a whole-battle cap; this is per ROUND, so it needs its own counter keyed on the
battle round. Getting that wrong in either direction is a real change: as
max_per_battle=1 it would fire once in five rounds, and without any counter,
every time a Guardian unit died.

THE TRIGGER IS A DEATH, so it is fed from main.py's death sweep like Vengeful
Stars - and for the same reason it must be fed per WIPED-OUT SQUAD rather than
per corpse: "an enemy unit DESTROYS a unit" happens once however many models
were in it.

"AFTER THAT ENEMY UNIT HAS FINISHED MAKING ITS ATTACKS" is why the shot is not
fired at the moment of death: the killer is still mid-activation. The offer is
recorded on the death and resolved when that unit finishes, which is the two-
step Vengeful Stars already uses.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, defend_at_all_costs
from game.stratagems import Stratagem

VAULS_VENGEANCE_NAME = "Vaul's Vengeance"
VAULS_VENGEANCE_CP = 1

#: The unit that may shoot.
VAULS_VENGEANCE_SHOOTER_KEYWORD = "WAR WALKERS"

#: The units whose death triggers it.
VAULS_VENGEANCE_TRIGGER_KEYWORDS = ("DIRE AVENGERS", "GUARDIANS")


def is_war_walkers(squad):
    from game.attached_units import unit_has_datasheet_keyword
    return unit_has_datasheet_keyword(squad, VAULS_VENGEANCE_SHOOTER_KEYWORD)


def triggered_by(squad):
    """"an enemy unit destroys a DIRE AVENGERS or GUARDIANS unit from your
    army"."""
    if squad is None:
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, k)
               for k in VAULS_VENGEANCE_TRIGGER_KEYWORDS)


class VaulsVengeanceController:
    """The death trigger, the once-per-ROUND counter, and the reactive shot."""

    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, game_state=None, decision_manager=None,
                 game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        #: (player, battle round) for each use. The printed restriction is per
        #: ROUND, which Stratagem's own max_per_battle cannot express.
        self._used_rounds = set()
        #: The killer to shoot at, once it has finished its attacks.
        self._pending = {}
        self._stratagem = Stratagem(
            name=VAULS_VENGEANCE_NAME, cp_cost=VAULS_VENGEANCE_CP, effect=self._shoot,
            # Two Guardian units can die to two different enemies in one phase,
            # and each is its own trigger.
            allow_repeat_target=True,
        )

    def _round(self):
        return getattr(self.turn_tracker, "battle_round", None)

    def used_this_round(self, player):
        return (player, self._round()) in self._used_rounds

    def _squads(self):
        seen = []
        for token in (getattr(self.game_state, "tokens", None) or ()):
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in seen:
                seen.append(squad)
        return seen

    def avengers_for(self, player):
        """The WAR WALKERS units that could take the shot."""
        return sorted((s for s in self._squads()
                       if s.owner == player and is_war_walkers(s)
                       and any(not m.is_dead() for m in s.models)),
                      key=lambda s: s.name)

    def can_use(self, player, killer):
        if killer is None or self.stratagem_controller is None:
            return False
        if not defend_at_all_costs.has_detachment(player):
            return False
        if self.used_this_round(player):
            return False
        walkers = self.avengers_for(player)
        if not walkers:
            return False
        return self.stratagem_controller.can_use(player, self._stratagem, [walkers[0]])

    def notify_unit_destroyed(self, dead_squad, killer_squad):
        """Fed once per wiped-out squad from main.py's death sweep."""
        if dead_squad is None or killer_squad is None:
            return False
        if killer_squad.owner == dead_squad.owner:
            return False
        if not aeldari_detachments.is_aeldari_unit(dead_squad):
            return False
        if not triggered_by(dead_squad):
            return False
        player = dead_squad.owner
        if not self.can_use(player, killer_squad):
            return False
        if player in self.auto_players or self.decision_manager is None:
            return False               # no AI path
        self.decision_manager.request(
            player,
            "%s (%d CP): %s destroyed %s - have a War Walkers unit shoot it "
            "once it has finished attacking?"
            % (VAULS_VENGEANCE_NAME, VAULS_VENGEANCE_CP, killer_squad.name,
               dead_squad.name),
            [("Use (%d CP)" % VAULS_VENGEANCE_CP,
              (lambda: self.use(player, killer_squad))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, player, killer_squad):
        if not self.can_use(player, killer_squad):
            return False
        walkers = self.avengers_for(player)
        self._pending[player] = (walkers[0], killer_squad)
        used = self.stratagem_controller.use(player, self._stratagem, [walkers[0]])
        if used:
            self._used_rounds.add((player, self._round()))
        return used

    def _shoot(self, controller, player, targets):
        """Recorded now, fired when the killer has finished its attacks."""
        if self.game_log is not None and player in self._pending:
            walker, killer = self._pending[player]
            self.game_log.add(
                "%s: %s will shoot %s once it has finished attacking."
                % (VAULS_VENGEANCE_NAME, walker.name, killer.name))

    def on_attacker_finished(self, attacker):
        """"After that enemy unit has finished making its attacks."" """
        for player, (walker, killer) in list(self._pending.items()):
            if killer is not attacker:
                continue
            del self._pending[player]
            if self.shooting_controller is None:
                continue
            if not any(not m.is_dead() for m in walker.models):
                continue
            self.shooting_controller.start_reactive_shooting(
                walker, restrict_to=[killer])
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s shoots %s." % (VAULS_VENGEANCE_NAME, walker.name,
                                           killer.name))
            return True
        return False
