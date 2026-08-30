"""Aspect Host Stratagem: To Their Final Breath (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Aspect Host.md):
  WHEN:   Fight phase, just after an enemy unit has selected its targets.
  TARGET: One ASPECT WARRIORS or AVATAR OF KHAINE unit from your army that was
          selected as the target of one or more of the attacking unit's
          attacks.
  EFFECT: Each time you use this Stratagem, you can remove one Aspect Shrine
          token your unit has (see datasheets). Then, until the end of the
          phase, each time a model in your unit is destroyed, if that model has
          not fought this phase, roll one D6, adding 1 to the result if you
          removed an Aspect Shrine token during this usage of this Stratagem.
          On a 4+, do not remove the destroyed model from play; it can fight
          after the attacking unit has finished making its attacks, and is then
          removed from play.
  RESTRICTIONS: none printed.

UNDYING SPITE, WORD FOR WORD, PLUS A TOKEN. Death Lord's Chosen prints the same
sentence with the same 4+, which is why game/fight_after_death.py exists; this
is its THIRD consumer and takes that module's whole flow - intercept in the
death sweep, keep the model up, owe it an activation, remove it after the
attacker has finished.

WHAT IS ACTUALLY NEW IS THE +1, and it is why that ledger grew a `bonus_for`
hook. "Adding 1 to the result if you removed an Aspect Shrine token during this
usage" varies per UNIT within one phase - two Aspect Warrior units can each buy
this, one spending a token and one not - so it cannot be folded into the fixed
threshold the ledger already had. It is added to the RESULT rather than
subtracted from the threshold so the logged number is the one that fell.

"FIGHT PHASE", WITH NO "YOUR" - so it can be bought in either player's turn.
Same as Blades from Beyond, and the opposite of most of this batch.

"YOU CAN REMOVE ONE TOKEN" IS OPTIONAL and the choice is real: the token is a
once-per-battle die change (game/aspect_shrine.py), so spending it here trades
a certain future 6 for a better chance now. Asked, not auto-resolved - the same
call Preternatural Precision makes about the same resource, and the opposite of
Warrior Focus's "any or all", where no branch was ever worse.

THE AVATAR HAS NO TOKENS, and is still a legal target: the card names it, and
the token clause is a "you can" that simply finds nothing to remove. So the
Avatar gets the plain 4+. Its own test line, because "eligible but cannot use
half the card" reads like a bug until the two clauses are read separately.

"IF THAT MODEL HAS NOT FOUGHT THIS PHASE" is checked against
FightController.fought_squad_ids, exactly as Undying Spite checks it - a unit
that already swung does not get to swing again by dying.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, aspect_shrine, detachment_gate
from game.fight_after_death import FightAfterDeath
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT

TO_THEIR_FINAL_BREATH_NAME = "To Their Final Breath"
TO_THEIR_FINAL_BREATH_CP = 1

#: "On a 4+" - the same number Undying Spite prints.
TO_THEIR_FINAL_BREATH_THRESHOLD = 4

#: "adding 1 to the result if you removed an Aspect Shrine token".
TO_THEIR_FINAL_BREATH_TOKEN_BONUS = 1

TO_THEIR_FINAL_BREATH_KEYWORDS = ("ASPECT WARRIORS", "AVATAR OF KHAINE")

SETTING = "ASPECT_HOST_PLAYERS"


def has_detachment(player):
    return detachment_gate.has_detachment(player, SETTING)


def eligible_unit(squad):
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, k)
               for k in TO_THEIR_FINAL_BREATH_KEYWORDS)


class ToTheirFinalBreathController:
    """Sits in FightController.target_reactions; fed by the death sweep."""

    def __init__(self, stratagem_controller, fight_controller=None,
                 game_state=None, turn_tracker=None, decision_manager=None,
                 game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.fight_controller = fight_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        #: id(squad) -> whether a token was spent on THIS usage. The value is
        #: what the +1 reads, so it cannot be a plain set.
        self._active = {}
        self._handled = set()
        self._pending = {}
        self._ledger = FightAfterDeath(
            TO_THEIR_FINAL_BREATH_THRESHOLD, TO_THEIR_FINAL_BREATH_NAME,
            game_state=game_state, game_log=game_log,
            bonus_for=self._bonus_for_model)
        self._stratagem = Stratagem(
            name=TO_THEIR_FINAL_BREATH_NAME, cp_cost=TO_THEIR_FINAL_BREATH_CP,
            effect=self._grant,
        )

    # ------------------------------------------------------------- state

    def is_active(self, squad):
        return squad is not None and id(squad) in self._active

    def spent_token(self, squad):
        return bool(self._active.get(id(squad), False))

    @property
    def is_busy(self):
        return self._ledger.is_busy

    def _bonus_for_model(self, model):
        squad = getattr(model, "squad", None)
        if squad is None or not self.is_active(squad):
            return 0
        return TO_THEIR_FINAL_BREATH_TOKEN_BONUS if self.spent_token(squad) else 0

    def _has_fought(self, squad):
        ledger = getattr(self.fight_controller, "fought_squad_ids", None) or ()
        return squad in ledger or id(squad) in {id(s) for s in ledger}

    def has_token(self, squad):
        """The UNIT's resource. aspect_shrine.usable() is deliberately not
        asked: that adds the per-MODEL CHARACTER exclusion the die-changing
        rule needs, and this clause has no model."""
        return aspect_shrine.unspent_tokens(squad) > 0

    # -------------------------------------------------------- eligibility

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None:
            return False
        if self.is_active(squad):
            return False
        # "FIGHT PHASE" with no "your" - no owner check at all.
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_FIGHT:
            return False
        if not eligible_unit(squad):
            return False
        if self._has_fought(squad):
            return False               # "if that model has not fought this phase"
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    # ------------------------------------------------------------ the offer

    def maybe_offer(self, attacking_squad, target_squad, melee=False):
        """FightController.target_reactions' protocol. THE ARGUMENT ORDER IS
        THE LIST'S: the protected unit is the TARGET."""
        if not melee:
            return False               # "Fight phase"
        if not self.can_use(target_squad):
            return False
        key = (id(target_squad), id(attacking_squad))
        if key in self._handled:
            return False
        self._handled.add(key)
        if target_squad.owner in self.auto_players or self.decision_manager is None:
            return False               # no AI path
        self.decision_manager.request(
            target_squad.owner,
            "%s (%d CP): %s is attacking %s - let its dying models strike back?"
            % (TO_THEIR_FINAL_BREATH_NAME, TO_THEIR_FINAL_BREATH_CP,
               attacking_squad.name, target_squad.name),
            [("Use (%d CP)" % TO_THEIR_FINAL_BREATH_CP,
              (lambda s=target_squad: self.use(s))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, squad, spend_token=None):
        """`spend_token` None means "ask" - the trade is real, so it is never
        auto-resolved for a human."""
        if not self.can_use(squad):
            return False
        if spend_token is None:
            if self.has_token(squad) and squad.owner not in self.auto_players \
                    and self.decision_manager is not None:
                self.decision_manager.request(
                    squad.owner,
                    "%s: spend an Aspect Shrine token for +%d on those rolls? "
                    "(%d left)"
                    % (TO_THEIR_FINAL_BREATH_NAME,
                       TO_THEIR_FINAL_BREATH_TOKEN_BONUS,
                       aspect_shrine.unspent_tokens(squad)),
                    [("Spend a token (+%d)" % TO_THEIR_FINAL_BREATH_TOKEN_BONUS,
                      (lambda s=squad: self.use(s, spend_token=True))),
                     ("Keep the token",
                      (lambda s=squad: self.use(s, spend_token=False)))],
                    is_stratagem=True,
                )
                return True
            spend_token = False
        self._pending[squad.owner] = (squad, bool(spend_token))
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        squad, spend_token = self._pending.pop(player, (None, False))
        if squad is None:
            return
        # The Avatar has no tokens: the clause is a "you can" that simply finds
        # nothing to remove, so it gets the plain 4+.
        if spend_token and self.has_token(squad):
            aspect_shrine.spend(squad)
        else:
            spend_token = False
        self._active[id(squad)] = spend_token
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s's dying models strike back on a %d+%s."
                % (TO_THEIR_FINAL_BREATH_NAME, squad.name,
                   TO_THEIR_FINAL_BREATH_THRESHOLD,
                   " (+%d, a token spent)" % TO_THEIR_FINAL_BREATH_TOKEN_BONUS
                   if spend_token else ""))

    # --------------------------------------------------- death and removal

    def _model_is_protected(self, model):
        squad = getattr(model, "squad", None)
        if squad is None or not self.is_active(squad):
            return False
        return not self._has_fought(squad)

    def intercept_destroyed(self, models):
        """Called from main.py's death sweep with the models it is about to
        remove. Returns those that SURVIVE - already put back by the shared
        ledger, so the caller has nothing to re-add."""
        return self._ledger.roll_for(models, self._model_is_protected)

    def models_owed_an_activation(self):
        return self._ledger.models_owed_an_activation()

    def resolve_after_attacks(self, attacking_squad=None):
        """"it can fight after the attacking unit has finished making its
        attacks, and is then removed from play"."""
        return self._ledger.resolve_after_attacks(attacking_squad)

    def reset_phase(self):
        self._active = {}
        self._handled = set()
