"""A destroyed model that stays on the board, strikes back, and is THEN removed.

EIGHTEENTH EXTRACTION, at the second consumer, as the convention requires.

Death Lord's Chosen's UNDYING SPITE (game/dlc_undying_spite.py) was the first
rule in this engine to need the state "dead, still on the battlefield, owed one
activation". The Wraithblades' MALEVOLENT SOULS (game/malevolent_souls.py) is
the second, and prints almost the same sentence:

  UNDYING SPITE    "each time a model in your unit is destroyed, if that model
                   has not fought this phase, roll one D6. On a 4+, do not
                   remove the destroyed model from play; it can fight after the
                   attacking unit has finished making its attacks, and is then
                   removed from play."

  MALEVOLENT SOULS "Each time a model in this unit is destroyed by a melee
                   attack, if that model has not fought this phase, roll one
                   D6. On a 3+, do not remove it from play; that destroyed
                   model can fight after the attacking unit has finished making
                   its attacks, and is then removed from play."

WHAT DIFFERS is only the threshold (4+ vs 3+), what makes a model eligible (a
Stratagem bought this phase vs a printed datasheet ability), and Malevolent
Souls' extra "by a MELEE attack" clause. What is IDENTICAL is the fiddly part,
and it is fiddly in a way that has already cost this repo once elsewhere:
putting a model BACK is four separate halves - into Squad.models, off
Squad.destroyed_models, into GameState.tokens, and onto the owed-activation
ledger - and taking it away again is the same four in reverse. Fuegan's
Unquenchable Resolve records what omitting one of them produces: "a half-alive
model", and only some of those omissions are obvious.

So the LEDGER lives here and both rules hold one. Crucially the RE-ADD half
lives here too. It used to sit in main.py's death-sweep loop, which meant the
second consumer would have had to duplicate it in the same loop - the exact
shape of error class 10, two places answering one question.

WHY THE DEATH IS INTERCEPTED IN THE SWEEP: GameState.remove_dead_models() runs
once per frame and is what takes the model off the board. Noticing the death
later would be reading a board the sweep has already changed - error class 12.

WHY THE D6 IS NOT A DICE-PANEL STEP: there is one per destroyed model and no
decision attached to any of them, so showing each would stop the game a dozen
times for nothing. The result is REPORTED in the log instead.
"""


class FightAfterDeath:
    """The shared ledger. One per rule, not one per unit.

    `threshold` and `label` are the rule's; `game_state` and `game_log` are the
    usual collaborators. The rule itself decides WHICH models are eligible - it
    passes them in - so this class holds no rule of its own beyond the dice.
    """

    def __init__(self, threshold, label, game_state=None, game_log=None,
                 bonus_for=None):
        self.threshold = threshold
        self.label = label
        self.game_state = game_state
        self.game_log = game_log
        #: Optional bonus_for(model) -> int, ADDED TO THE ROLL. Its third
        #: consumer needed it: Aspect Host's To Their Final Breath prints
        #: "adding 1 to the result if you removed an Aspect Shrine token",
        #: which varies per UNIT within one phase, so it cannot be folded into
        #: the fixed threshold above. The two earlier rules pass nothing and
        #: are unchanged. Added to the RESULT rather than subtracted from the
        #: threshold so the logged number is the one that fell, which is what
        #: makes the line readable when the bonus is in play.
        self.bonus_for = bonus_for
        self._owed = []      # models kept on the board, owed an activation

    # ------------------------------------------------------------- helpers

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    @property
    def is_busy(self):
        return bool(self._owed)

    def models_owed_an_activation(self):
        return list(self._owed)

    # --------------------------------------------------- intercepting death

    def roll_for(self, models, eligible):
        """Roll for each of `models` that `eligible(model)` accepts, put the
        survivors back on the board, and return them.

        Called from the death sweep with the models it was about to remove.
        The caller does NOT need to re-add anything - that is done here, so the
        four halves of "back on the board" have exactly one implementation."""
        kept = []
        for model in models or ():
            if not eligible(model):
                continue
            rolled = self._roll_one()
            bonus = self.bonus_for(model) if self.bonus_for is not None else 0
            if rolled + bonus >= self.threshold:
                self._keep_up(model)
                kept.append(model)
                self._log("[%s] %s rolled a %d%s - it stays up to strike back."
                          % (self.label.lower(), model.profile.name, rolled,
                             " +%d" % bonus if bonus else ""),
                          file_only=True)
            else:
                self._log("[%s] %s rolled a %d%s - it falls."
                          % (self.label.lower(), model.profile.name, rolled,
                             " +%d" % bonus if bonus else ""),
                          file_only=True)
        return kept

    def _keep_up(self, model):
        """The four halves of putting a model back, in one place."""
        squad = getattr(model, "squad", None)
        if squad is not None:
            if model not in squad.models:
                squad.models.append(model)
            destroyed = getattr(squad, "destroyed_models", None)
            if destroyed is not None and model in destroyed:
                destroyed.remove(model)
        if self.game_state is not None and model not in self.game_state.tokens:
            self.game_state.tokens.append(model)
        self._owed.append(model)

    def _roll_one(self):
        from game.dice import random as dice_random
        return dice_random.randint(1, 6)

    # ------------------------------------------------------ and then removed

    def resolve_after_attacks(self, attacking_squad=None):
        """"...is then removed from play."

        The activation itself is driven by main.py through the ordinary fight
        step; this owns only the removal half, so a model cannot linger.
        Returns the models finally removed."""
        removed = list(self._owed)
        self._owed = []
        for model in removed:
            squad = getattr(model, "squad", None)
            if squad is not None and model in squad.models:
                squad.models.remove(model)
                destroyed = getattr(squad, "destroyed_models", None)
                if destroyed is not None and model not in destroyed:
                    destroyed.append(model)
            if self.game_state is not None and model in self.game_state.tokens:
                self.game_state.tokens.remove(model)
        if removed:
            self._log("%s: %d model(s) struck back and are removed from play."
                      % (self.label, len(removed)))
        return removed
