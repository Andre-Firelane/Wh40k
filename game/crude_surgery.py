"""The Painboy's Crude Surgery and Catch Dat Red Bit (2026-09 Ork codex).

RULES (verbatim, rules/orks/Painboy.md):
  "Crude Surgery: In your Command phase, this unit heals 3 wounds."
  "Catch Dat Red Bit (Once per battle, per unit): When this model uses its
   Crude Surgery ability, you can add D3 to the number of wounds healed."

THE PRE-CODEX GROT ORDERLY IS GONE (a user-supplied wargear rule that returned
up to D3 destroyed Bodyguard models once per battle), and with it
game/grot_orderly.py. What replaces it is a CORE-RULE heal: 02.02.04 tops the
unit's damaged models up first and only then revives destroyed non-CHARACTER
models, capped by 01.02.03's Starting Strength. That rule lives in
game/heal.py, extracted from the Necron army rule at this second consumer.

"IN YOUR COMMAND PHASE" is resolved at its START, automatically: the heal costs
nothing and has no downside, so it is not asked (Fehlerklasse 5 - never offer a
choice whose "no" is never the better answer). A unit with nothing to heal is
skipped rather than logged.

"THIS UNIT" is the unit the Painboy supports (19.04 confers his ability on it
while he lives, which is unit_wide_ability()'s component-wise reading) - and a
Painboy on his own heals himself. He is a CHARACTER, so he can be topped up but
never revived; a dead Painboy heals nobody. A unit in Strategic Reserves or
embarked still heals: "in your Command phase" is not "on the battlefield", so
it is healed off the board and its revived models arrive with the rest of it
(heal(off_board=True)).

CATCH DAT RED BIT is the one real choice: a once-per-battle bonus that is worth
more the more the unit has lost. So it is only OFFERED when a heal of more than
3 could land at all - healable_wounds() > 3 - and a human gets "Catch Dat Red
Bit" / "Save it for later". The D3 is a visible roll. The AI answers through an
injected verdict (ai/agent_driver.py's catch_dat_red_bit_verdict()), 0 API
calls. The spend is Squad.catch_dat_red_bit_used, saved with the scene.

A HUMAN PLACES REVIVED MODELS (rule 01.02.03's "set up") through the shared
ReturnPlacementController, which queues its own placements - so several Painboy
units in one Command phase each get theirs in turn, and none is seated by the
engine because another was still open.
"""

from game import ai_mode, heal as heal_rule
from game.squad import unit_wide_ability

CRUDE_SURGERY_NAME = "Crude Surgery"
CATCH_DAT_RED_BIT_NAME = "Catch Dat Red Bit"
#: "this unit heals 3 wounds".
CRUDE_SURGERY_WOUNDS = 3
#: "add D3 to the number of wounds healed".
CATCH_DAT_RED_BIT_SIDES = 3
USE_RED_BIT_LABEL = "Catch Dat Red Bit (+D3 wounds healed)"
SAVE_RED_BIT_LABEL = "Save it for later"


def _alive(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def has_crude_surgery(squad):
    return squad is not None and bool(_alive(squad)) and bool(unit_wide_ability(squad, "crude_surgery"))


def has_catch_dat_red_bit(squad):
    return squad is not None and bool(_alive(squad)) and bool(unit_wide_ability(squad, "catch_dat_red_bit"))


def red_bit_offerable(squad):
    """Catch Dat Red Bit is worth asking about: unused, and a heal of more than
    3 wounds would not be wasted."""
    return (has_catch_dat_red_bit(squad)
            and not getattr(squad, "catch_dat_red_bit_used", False)
            and heal_rule.healable_wounds(squad) > CRUDE_SURGERY_WOUNDS)


class CrudeSurgeryController:
    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, position_valid=None, auto_players=(),
                 placer=None, verdict=None):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        # SetupController's own predicate - "somewhere legal" means what it
        # means everywhere else; heal.placement_validator() adds the 01.02.03
        # Engagement Range half.
        self.position_valid = position_valid
        self.auto_players = ai_mode.players(auto_players)
        self.placer = placer
        # verdict(squad) -> bool: the AI's Catch Dat Red Bit rule, injected
        # (game/ must not import ai/). None: an auto player uses it outright.
        self.verdict = verdict
        self._queue = []
        self._current = None   # the unit whose prompt or D3 is open
        self._rolling = False  # True while that is the D3, not the prompt

    # ---------------------------------------------------------------- state

    @property
    def is_busy(self):
        return self._current is not None or bool(self._queue)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    def can_heal(self, squad, player=None):
        if squad is None or not has_crude_surgery(squad):
            return False
        if player is not None and squad.owner != player:
            return False
        return heal_rule.healable_wounds(squad) > 0

    def eligible_squads(self, squads, player=None):
        return [s for s in squads or () if self.can_heal(s, player)]

    # ------------------------------------------------------------ the cycle

    def begin_command_phase(self, squads, player):
        """The start of `player`'s Command phase. Sorted by name so a replay
        and a test see the same order."""
        if self.is_busy:
            return False
        self._queue = sorted(self.eligible_squads(squads, player), key=lambda s: s.name)
        if not self._queue:
            return False
        self._advance()
        return True

    def _advance(self):
        while self._queue and self._current is None:
            squad = self._queue.pop(0)
            if not self.can_heal(squad, squad.owner):
                continue
            if not red_bit_offerable(squad) or self.dice_manager is None:
                self._heal(squad, CRUDE_SURGERY_WOUNDS)
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                if self.verdict is None or self.verdict(squad):
                    self._roll_red_bit(squad)
                else:
                    self._heal(squad, CRUDE_SURGERY_WOUNDS)
                continue
            self._current = squad
            self.decision_manager.request(
                squad.owner,
                "%s: %s heals %d wound(s) (%d to recover). %s (once per battle) - add D3?"
                % (squad.name, CRUDE_SURGERY_NAME, CRUDE_SURGERY_WOUNDS,
                   heal_rule.healable_wounds(squad), CATCH_DAT_RED_BIT_NAME),
                [
                    (USE_RED_BIT_LABEL, lambda s=squad: self._answer(s, True)),
                    (SAVE_RED_BIT_LABEL, lambda s=squad: self._answer(s, False)),
                ],
            )
            return

    def _answer(self, squad, use):
        if self._current is not squad:
            return
        self._current = None
        if use and red_bit_offerable(squad):
            self._roll_red_bit(squad)
        else:
            self._heal(squad, CRUDE_SURGERY_WOUNDS)
        self._advance()

    def _roll_red_bit(self, squad):
        squad.catch_dat_red_bit_used = True
        self._current = squad
        self._rolling = True
        self.dice_manager.roll(
            1, CATCH_DAT_RED_BIT_SIDES, label="%s (+D3 wounds healed)" % CATCH_DAT_RED_BIT_NAME,
            target_name=squad.name, target_squad=squad, subject_label="Healing")

    def on_dice_acknowledged(self):
        """The Catch Dat Red Bit D3 - only while that roll is ours."""
        squad = self._current
        if squad is None or not self._rolling or self.dice_manager is None:
            return False
        rolled = (self.dice_manager.last_values or [1])[0]
        self._current = None
        self._rolling = False
        self._heal(squad, CRUDE_SURGERY_WOUNDS + rolled, bonus=rolled)
        self._advance()
        return True

    # ------------------------------------------------------------- the work

    def _on_board(self, squad):
        tokens = {id(t) for t in self._tokens()}
        return any(id(m) in tokens for m in _alive(squad))

    def _heal(self, squad, wounds, bonus=None):
        off_board = not self._on_board(squad)
        # A unit off the battlefield has nowhere to set a model up, so no placer.
        placer = None if off_board else self.placer
        spent, revived = heal_rule.heal(
            squad, wounds,
            all_tokens=self._tokens(),
            position_valid=self.position_valid,
            game_state=self.game_state,
            placer=placer,
            off_board=off_board,
        )
        extra = "" if bonus is None else " (%s: +%d)" % (CATCH_DAT_RED_BIT_NAME, bonus)
        detail = "%d wound(s)" % spent
        if revived:
            detail += ", %d model(s) back%s" % (len(revived), " in the unit" if off_board else " on the battlefield")
        self._log("%s (%s): heals %d%s - %s." % (CRUDE_SURGERY_NAME, squad.name, wounds, extra, detail))
        return spent, revived
