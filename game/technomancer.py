"""The Technomancer's own named ability.

RULE (printed, word for word):
  "At the end of your Movement phase, you can select one friendly NECRONS
   model within 6" of the bearer. That model regains up to D3 lost wounds.
   Each model can only be selected for this ability once per turn."

A MODEL, NOT A UNIT, and that is the whole reason it does not simply call
game/reanimation_protocols.py's reanimate(). Reanimation heals a UNIT and
spills surplus into reviving destroyed models; this names one model and stops
there. "Regains up to D3 lost wounds" also cannot revive anything - a destroyed
model has no wounds to regain.

So the two abilities are deliberately NOT merged: they answer different
questions, and folding them would make the Technomancer able to raise the dead,
which his text does not say.

"EACH MODEL CAN ONLY BE SELECTED ... ONCE PER TURN" is a ledger on the TARGET,
not on the Technomancer - two Technomancers may not both top up the same model,
but either may heal a different one. Keyed on id(model) and cleared each turn.

The AI answers deterministically: the eligible model that has lost the most
wounds, which is the only ranking that cannot waste the dice. A model at full
wounds is never eligible at all, so a unit in perfect health simply gets no
offer rather than a wasted roll.
"""

TECHNOMANCER_RANGE_IN = 6.0
TECHNOMANCER_DICE_SIDES = 3


def has_technomancer(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "technomancer_repair", False)
               for m in squad.models if not m.is_dead())


def bearers(squad):
    return [m for m in getattr(squad, "models", ()) or ()
            if getattr(m.profile, "technomancer_repair", False) and not m.is_dead()]


class TechnomancerController:
    """Resolved at the end of its owner's Movement phase, driven from main.py's
    own phase-change block - the same seam Grot Orderly uses for its Command
    phase."""

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, auto_players=()):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.auto_players = set(auto_players)
        self._used_this_turn = set()   # id(target model)
        self._pending = None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    @property
    def is_busy(self):
        return self._pending is not None

    def reset_turn(self):
        """"once per turn"."""
        self._used_this_turn.clear()

    def eligible_targets(self, squad):
        """Friendly NECRONS models within 6" of a bearer that have actually
        lost wounds and have not been picked this turn."""
        out = []
        sources = bearers(squad)
        if not sources:
            return out
        for token in self._tokens():
            other = getattr(token, "squad", None)
            if other is None or other.owner != squad.owner or token.is_dead():
                continue
            if not getattr(token.profile, "reanimation_protocols", False):
                continue  # "friendly NECRONS model" - the army rule is on every Necron datasheet
            if token.current_wounds >= token.profile.wounds:
                continue  # nothing to regain
            if id(token) in self._used_this_turn:
                continue
            gap = min(((token.x_in - b.x_in) ** 2 + (token.y_in - b.y_in) ** 2) ** 0.5
                      - token.radius_in - b.radius_in for b in sources)
            if gap <= TECHNOMANCER_RANGE_IN:
                out.append(token)
        return out

    def can_use(self, squad):
        return (self._pending is None
                and has_technomancer(squad)
                and bool(self.eligible_targets(squad)))

    def offer_at_end_of_movement(self, squads, player):
        for squad in sorted((s for s in squads if s.owner == player), key=lambda s: s.name):
            if self.can_use(squad):
                return self.offer(squad)
        return False

    def offer(self, squad):
        if not self.can_use(squad):
            return False
        targets = self.eligible_targets(squad)
        if squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad, self._pick(targets))
        options = [
            (f"Repair {t.profile.name} ({t.current_wounds}/{t.profile.wounds} wounds)",
             (lambda target=t: self._use(squad, target)))
            for t in targets
        ]
        options.append(("Decline", None))
        self.decision_manager.request(
            squad.owner, f"{squad.name}: Technomancer - repair a model?", options)
        return True

    def _pick(self, targets):
        """The model missing the most wounds; name breaks ties so a replay and
        a test agree."""
        return max(targets, key=lambda m: (m.profile.wounds - m.current_wounds, m.profile.name))

    def _use(self, squad, target):
        if target is None:
            return False
        self._used_this_turn.add(id(target))
        self._pending = {"squad": squad, "target": target}
        if self.dice_manager is None:
            self._resolve(TECHNOMANCER_DICE_SIDES)
            return True
        self.dice_manager.roll(
            1, TECHNOMANCER_DICE_SIDES, label="Technomancer",
            target_name=target.profile.name, target_squad=target.squad,
            subject_label="Repairing")
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            return False
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or [1]
        self._resolve(values[0])
        return True

    def _resolve(self, rolled):
        ctx, self._pending = self._pending, None
        target = ctx["target"]
        missing = target.profile.wounds - target.current_wounds
        healed = max(0, min(int(rolled), missing))   # "up to D3"
        target.current_wounds += healed
        self._log(f"Technomancer ({ctx['squad'].name}): rolled a {rolled} - "
                  f"{target.profile.name} regains {healed} lost wound(s) "
                  f"({target.current_wounds}/{target.profile.wounds}).")
