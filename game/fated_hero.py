"""The Wraithlord's "Fated Hero" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "At the start of the battle, select one of the following keywords: INFANTRY;
  MONSTER; MOUNTED; VEHICLE. Each time this model makes an attack that targets
  a unit with the selected keyword, re-roll a Hit roll of 1 and re-roll a
  Wound roll of 1."

STRUCTURALLY THIS IS DRIVEN BY HATRED WITH A DIFFERENT CONDITION
----------------------------------------------------------------
game/destroyer_cult.py's Lokhust Lord ability is the same shape and the same
four wiring points, and the notes there apply here unchanged:

  * BOTH ROLLS. "re-roll a Hit roll of 1 AND re-roll a Wound roll of 1" is two
    effects, so the predicate is read at FOUR places - _hit_reroll_reason and
    _wound_reroll_reason in BOTH game/shooting.py and game/fight.py. A wiring
    that reaches only two of them looks complete from any one of them, which is
    why the test counts the call sites per file rather than trusting a spot
    check.
  * PER MODEL. "each time THIS MODEL makes an attack", so the predicate takes a
    MODEL. The group-level form grants only when EVERY model in the group
    carries it - conservative on purpose, exactly as Driven by Hatred argues:
    the other way round would re-roll someone else's dice on the Wraithlord's
    entitlement. A Wraithlord is a one-model unit today, so the two readings
    cannot currently diverge; the strict one is still what is written.
  * NOT A reroll_scope ENTRY. The printed text has no "instead" and no "you
    can" - it is a plain, mandatory re-roll of 1s, the ordinary automatic kind.
    Listing it in game/reroll_scope.py would offer the player a "1s only"
    choice the datasheet never gives. Pinned as an ABSENCE in the test, since
    that is the only place it shows.

THE CHOICE LIVES ON THE TOKEN, NEVER ON THE PROFILE
---------------------------------------------------
UnitProfile subclasses are shared class objects - writing the chosen keyword
onto one would set it for every Wraithlord built from that datasheet, in this
battle and in every other. Same trap Illuminor Szeras' growing aura records.
So the selection is stored per model, keyed by id(), in the controller.

"AT THE START OF THE BATTLE" is one of PregameController's pre-battle steps.
It has no ordering constraint against the others (it grants nothing another
step reads), unlike Strike Swiftly, which must precede ScoutsStep.

THE AI ANSWERS IT DETERMINISTICALLY, so there is no path in ai/ and no API
call: it picks the keyword carried by the most enemy MODELS on the board, ties
broken by keyword order. That is a real reading of the board rather than a
constant, and it cannot flicker, which a prompt nobody answers would.
"""
from game import attached_units

#: The four printed choices, in printed order. Order is load-bearing only as
#: the AI's tie-break.
FATED_HERO_KEYWORDS = ("INFANTRY", "MONSTER", "MOUNTED", "VEHICLE")

FATED_HERO_LABEL = "Fated Hero"

#: keyword -> the UnitProfile flag that carries it. MOUNTED is the odd one:
#: it is a descriptive datasheet keyword rather than a profile flag in this
#: engine, so it is answered from the datasheet's own keyword line.
_KEYWORD_FLAGS = {
    "INFANTRY": "infantry",
    "MONSTER": "monster",
    "VEHICLE": "vehicle",
}


def unit_has_keyword(squad, keyword):
    """Rule 19.03's pooling: a unit has a keyword if ANY of its models does.

    MOUNTED has no profile flag (game/units.py says so explicitly - it is
    descriptive, like BATTLELINE), so it is read off the datasheet keyword
    line, which is where this engine keeps such keywords."""
    if squad is None or not keyword:
        return False
    flag = _KEYWORD_FLAGS.get(keyword)
    if flag is not None:
        models = getattr(squad, "models", None) or ()
        if any(getattr(m.profile, flag, False) and not m.is_dead() for m in models):
            return True
    return bool(attached_units.unit_has_datasheet_keyword(squad, keyword))


class FatedHeroController:
    """Holds each Wraithlord's chosen keyword and answers the re-roll question.

    One controller for the battle, not one per model: the selection is a small
    dict keyed by id(model), and a per-model controller would have to be
    created by whatever built the model."""

    def __init__(self, game_state=None, game_log=None, decision_manager=None,
                 auto_players=()):
        self.game_state = game_state
        self.game_log = game_log
        self.decision_manager = decision_manager
        self.auto_players = set(auto_players)
        self._chosen = {}          # id(model) -> keyword
        self._pending = []
        self._on_done = None

    # ------------------------------------------------------------ the rule

    def chosen_keyword(self, model):
        return self._chosen.get(id(model))

    def choose(self, model, keyword):
        if model is None or keyword not in FATED_HERO_KEYWORDS:
            return False
        self._chosen[id(model)] = keyword
        if self.game_log is not None:
            squad = getattr(model, "squad", None)
            name = getattr(squad, "name", None) or model.profile.name
            self.game_log.add("%s: %s hates %s units this battle."
                              % (FATED_HERO_LABEL, name, keyword))
        return True

    def applies(self, model, target_squad):
        """Does THIS model re-roll both of its 1s against this target?"""
        if model is None or target_squad is None:
            return False
        if not getattr(model.profile, "fated_hero", False) or model.is_dead():
            return False
        keyword = self.chosen_keyword(model)
        if keyword is None:
            return False
        return unit_has_keyword(target_squad, keyword)

    def applies_to_group(self, pairs, target_squad):
        """The group-level form the two attack steps need - see the module
        docstring for why it is all() and not any()."""
        if not pairs:
            return False
        return all(self.applies(model, target_squad) for model, _ in pairs)

    # ------------------------------------------------- the pre-battle step

    def _squads(self):
        seen = []
        for token in (getattr(self.game_state, "tokens", None) or ()):
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in seen:
                seen.append(squad)
        return seen

    def eligible_models(self, player=None):
        out = []
        for squad in self._squads():
            if player is not None and squad.owner != player:
                continue
            for model in squad.models:
                if getattr(model.profile, "fated_hero", False) and not model.is_dead():
                    if id(model) not in self._chosen:
                        out.append(model)
        return out

    def _auto_pick(self, model):
        """The most numerous enemy keyword on the board, ties broken by printed
        order. A real reading of the board, and stable within a battle."""
        owner = getattr(getattr(model, "squad", None), "owner", None)
        counts = dict.fromkeys(FATED_HERO_KEYWORDS, 0)
        for squad in self._squads():
            if owner is not None and squad.owner == owner:
                continue
            living = [m for m in squad.models if not m.is_dead()]
            if not living:
                continue
            for keyword in FATED_HERO_KEYWORDS:
                if unit_has_keyword(squad, keyword):
                    counts[keyword] += len(living)
        best = max(FATED_HERO_KEYWORDS, key=lambda k: (counts[k], -FATED_HERO_KEYWORDS.index(k)))
        return best

    def start(self, pregame_controller=None, on_done=None):
        """PregameController's pre-battle step protocol: return True if a
        prompt is on screen, False if there was nothing to do."""
        self._on_done = on_done
        self._pending = self.eligible_models()
        return self._next()

    def _next(self):
        while self._pending:
            model = self._pending.pop(0)
            if id(model) in self._chosen:
                continue
            owner = getattr(getattr(model, "squad", None), "owner", None)
            if owner in self.auto_players or self.decision_manager is None:
                self.choose(model, self._auto_pick(model))
                continue
            squad = getattr(model, "squad", None)
            name = getattr(squad, "name", None) or model.profile.name
            self.decision_manager.request(
                owner,
                "%s: which keyword does %s hate this battle?" % (FATED_HERO_LABEL, name),
                [("%s" % k, (lambda m=model, k=k: self._answer(m, k)))
                 for k in FATED_HERO_KEYWORDS])
            return True
        if self._on_done is not None:
            done, self._on_done = self._on_done, None
            done()
        return False

    def _answer(self, model, keyword):
        self.choose(model, keyword)
        # Keep draining: a second Wraithlord asks its own question, and the
        # step must reach on_done or the pregame stalls on an answered prompt.
        self._next()
        return True
