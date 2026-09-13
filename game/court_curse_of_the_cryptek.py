"""Canoptek Court Stratagem: Curse of the Cryptek (1CP).

RULE (verbatim, rules/necrons/detachments/Canoptek Court.md):
  WHEN:   Your opponent's Shooting phase or the Fight phase, just after an enemy
          unit has shot or fought.
  TARGET: One CRYPTEK model from your army that was destroyed by one of the
          attacking unit's attacks. You can use this Stratagem on that model even
          though it was just destroyed.
  EFFECT: Until the end of the battle, each time a friendly CANOPTEK model makes
          an attack that targets the attacking unit, add 1 to the Hit roll and
          add 1 to the Wound roll.

TWO MOMENTS, AND THEY ARRIVE IN EITHER ORDER
--------------------------------------------
A CRYPTEK model dies mid-activation; the Stratagem is offered "just after an enemy
unit has shot or fought". The death is NOTED in main.py's death sweep - per MODEL,
because a Cryptek is one model of an attached unit and a unit need not be wiped
for it to have died - and the attacker is known at the after-activation hooks.
game/montka_pinpoint_counter_offensive.py is the template, with one addition:

  * a death seen WHILE an attacker is still resolving names that attacker, and is
    owed until its hook fires (maybe_offer());
  * a death seen with NOBODY attacking is the last weapon group of an activation
    that has already closed - remove_dead_models() runs once per frame, after the
    frame's event handling, so the attacker's own hook can fire BEFORE the sweep
    sees the corpse. That attacker is remembered (_last_attacker) and the offer is
    made on the spot, which is "just after it has shot" in the only sense this
    engine can give.

NAMED LIMITATION, Pinpoint's: a Cryptek killed by something that is not an attack
(Deadly Demise, a mortal-wound ability between activations) is blamed on the last
attacker to finish in the same phase. Nothing here records who caused a wound.

WHO THE MARK HELPS IS PER MODEL. "A friendly CANOPTEK model makes an attack" - a
Warrior shooting beside a Canoptek Wraith gets nothing. game/necron_detachments.
py's attack_key() keeps CANOPTEK and non-CANOPTEK models out of one 04.03 group
for a Canoptek Court player, so the representative model is exact.

BATTLE-LONG AND HELD PER PLAYER, like Pinpoint's mark: never cleared, and it marks
the ENEMY unit, so every CANOPTEK model of the army benefits.

NEVER OFFERED WHEN IT BUYS NOTHING: an army with no living CANOPTEK unit anywhere
(battlefield, reserves or transports) cannot use the mark, and an enemy unit this
player has already marked gains nothing from a second one. And ONE question per
attacker per phase - two Crypteks lost to one volley are one Stratagem's worth.

THE AI ANSWERS AT ONCE (auto_players): it buys the mark whenever it is offered,
which the gate above already means is worth something.
"""

from game import ai_mode, necron_detachments
from game.modifiers import Modifier
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

CURSE_OF_THE_CRYPTEK_NAME = "Curse of the Cryptek"
CURSE_OF_THE_CRYPTEK_CP = 1
SETTING = "CANOPTEK_COURT_PLAYERS"
#: "add 1 to the Hit roll and add 1 to the Wound roll" - bonuses, so NEGATIVE
#: under game/modifiers.py's threshold convention.
CURSE_HIT_BONUS = -1
CURSE_WOUND_BONUS = -1


def _alive(squad):
    return any(not m.is_dead() for m in getattr(squad, "models", ()) or ())


class CurseOfTheCryptekController:
    def __init__(self, stratagem_controller, turn_tracker=None, decision_manager=None,
                 game_state=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._marks = {}           # player -> set of marked enemy Squads, for the battle
        self._owed = []            # (dead Cryptek's squad, killer squad), this phase
        self._last_attacker = None # whose activation finished last, this phase
        self._asked = set()        # (player, id(attacker)) already offered this phase
        self._pending = None       # (player, attacker) for the purchase in flight
        self._stratagem = Stratagem(
            name=CURSE_OF_THE_CRYPTEK_NAME, cp_cost=CURSE_OF_THE_CRYPTEK_CP,
            effect=self._mark,
            # Every death is its own window, and the target "was just destroyed".
            allow_repeat_target=True,
        )

    # ------------------------------------------------------------- reading
    def marked_by(self, player):
        return set(self._marks.get(player, ()))

    def applies(self, attacking_model, attacking_squad, target_squad):
        if attacking_squad is None or target_squad is None:
            return False
        if target_squad not in self._marks.get(attacking_squad.owner, ()):
            return False
        return necron_detachments.model_is_canoptek(attacking_squad, attacking_model)

    def hit_modifiers(self, attacking_model, attacking_squad, target_squad):
        if self.applies(attacking_model, attacking_squad, target_squad):
            return [Modifier(CURSE_HIT_BONUS, CURSE_OF_THE_CRYPTEK_NAME)]
        return []

    def wound_modifiers(self, attacking_model, attacking_squad, target_squad):
        if self.applies(attacking_model, attacking_squad, target_squad):
            return [Modifier(CURSE_WOUND_BONUS, CURSE_OF_THE_CRYPTEK_NAME)]
        return []

    # --------------------------------------------------------------- noting
    def notify_model_destroyed(self, dead_model, killer_squad=None):
        """Fed per MODEL from main.py's death sweep, with whoever was attacking
        at the time (None between activations - see the module docstring)."""
        squad = getattr(dead_model, "squad", None)
        if squad is None:
            return False
        if not necron_detachments.has_detachment(squad.owner, SETTING):
            return False
        if not necron_detachments.model_is_cryptek(squad, dead_model):
            return False
        if killer_squad is None and self._last_attacker is not None:
            return self._offer(squad, self._last_attacker)
        self._owed.append((squad, killer_squad))
        return True

    def reset_phase(self):
        """An owed death, the last attacker and the asked-set do not outlive
        the phase they belong to. The MARKS do - "until the end of the battle"."""
        self._owed = []
        self._last_attacker = None
        self._asked = set()

    # -------------------------------------------------------------- offering
    def _phase_allows(self, attacker):
        tt = self.turn_tracker
        if tt is None:
            return True
        if tt.phase == PHASE_FIGHT:
            return True
        # "Your OPPONENT'S Shooting phase" - the attacker's own turn.
        return tt.phase == PHASE_SHOOTING and tt.turn_owner == attacker.owner

    def _army_has_canoptek_unit(self, player):
        state = self.game_state
        if state is None:
            return True
        squads = list(state.all_squads()) if hasattr(state, "all_squads") else []
        return any(s.owner == player and _alive(s) and necron_detachments.is_canoptek_unit(s)
                   for s in squads)

    def could_offer(self, player, attacker):
        if attacker is None or player is None or attacker.owner == player:
            return False
        if not necron_detachments.has_detachment(player, SETTING):
            return False
        if attacker in self._marks.get(player, ()):
            return False       # already marked - a second mark buys nothing
        if not self._army_has_canoptek_unit(player):
            return False       # nobody who could ever use it
        return True

    def maybe_offer(self, attacker):
        """Called from the after-activation hooks with the unit that just shot
        or fought. Remembers it, and drains the deaths it answers for."""
        if attacker is None or not self._phase_allows(attacker):
            return False
        self._last_attacker = attacker
        if not self._owed:
            return False
        mine = [sq for sq, k in self._owed if k is None or k is attacker]
        self._owed = [(sq, k) for sq, k in self._owed if not (k is None or k is attacker)]
        offered = False
        for dead_squad in mine:
            if self._offer(dead_squad, attacker):
                offered = True
        return offered

    def _offer(self, dead_squad, attacker):
        player = dead_squad.owner
        key = (player, id(attacker))
        if key in self._asked:
            return False
        if not self.could_offer(player, attacker):
            return False
        if not self.stratagem_controller.can_use(player, self._stratagem, [dead_squad]):
            return False
        self._asked.add(key)
        if player in self.auto_players:
            return self._buy(player, dead_squad, attacker)
        if self.decision_manager is None:
            return False

        def buy(p=player, dead=dead_squad, killer=attacker):
            # Bound HERE, in the option's own closure, for Pinpoint's reason:
            # two prompts queued at once must not share one pending slot.
            return self._buy(p, dead, killer)

        self.decision_manager.request(
            player,
            f"{CURSE_OF_THE_CRYPTEK_NAME} ({CURSE_OF_THE_CRYPTEK_CP} CP): a CRYPTEK model of "
            f"{dead_squad.name} was destroyed by {attacker.name} - curse it? Friendly "
            "CANOPTEK models add 1 to Hit and Wound rolls against it for the rest of the battle.",
            [(f"Use ({CURSE_OF_THE_CRYPTEK_CP} CP)", buy),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def _buy(self, player, dead_squad, attacker):
        self._pending = (player, attacker)
        used = self.stratagem_controller.use(player, self._stratagem, [dead_squad])
        if not used:
            self._pending = None
        return used

    def _mark(self, controller, player, targets):
        pending, self._pending = self._pending, None
        if pending is None:
            return
        _player, attacker = pending
        self._marks.setdefault(player, set()).add(attacker)
        if self.game_log is not None:
            self.game_log.add(
                f"{CURSE_OF_THE_CRYPTEK_NAME}: {player}'s CANOPTEK models add 1 to Hit and "
                f"Wound rolls against {attacker.name} for the rest of the battle.")
