"""The Yncarne's "Inevitable Death" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "Once in each opponent's turn, when another friendly AELDARI unit is
  destroyed, if this model is on the battlefield, you can remove it from the
  battlefield and set it back up as close as possible to where a destroyed
  model from that unit was, outside of Engagement Range of enemy units. This
  model can still move this turn."

THIS IS FUEGAN'S UNQUENCHABLE RESOLVE WITH THE ARROW REVERSED
--------------------------------------------------------------
Both name a POINT rather than a formation ("as close as possible to where that
model died"), so both walk formation_layout.ring_candidates() outwards, and
both owe the Engagement Range test that SetupController.position_valid()
deliberately does not do. game/model_return.py owns that half already and is
not re-derived here.

What is different is WHOSE death it is. Fuegan comes back from his OWN death.
The Yncarne is alive the whole time - it is somebody ELSE dying that moves it -
so this is not a model-return at all: nothing goes on or off the destroyed
list, only coordinates change. That is why it does not call set_up_model().

FOUR QUALIFIERS, EACH ONE A RESTRICTION
---------------------------------------
  * "ONCE IN EACH OPPONENT'S TURN". Not once per turn and not once per battle:
    the ledger is keyed by the turn owner, and it is the OPPONENT'S turn, so
    the Yncarne's own turn never offers it. Reading this as "once per turn"
    would hand it a second teleport every round.
  * "ANOTHER friendly AELDARI unit". Not the Yncarne itself (it would have to
    be alive to use the ability that its own death triggered), and not an
    enemy's.
  * "IF THIS MODEL IS ON THE BATTLEFIELD". A Yncarne in Reserves does not
    teleport - it arrives by Deep Strike like anything else.
  * "OUTSIDE OF ENGAGEMENT RANGE OF ENEMY UNITS". The reason a landing spot can
    fail at all, and the reason the search walks outwards instead of taking the
    corpse's exact square: a unit that was just wiped out was very often in
    combat, so the nearest legal spot is usually not the nearest spot.

"CAN STILL MOVE THIS TURN" is the clause that needs nothing built: it fires in
the OPPONENT'S turn, and this engine's per-turn movement ledger belongs to the
moving player's own turn. Written out rather than silently skipped, and pinned
in the test, because "it is already true" and "it was forgotten" look identical
from the code.

THE AI ANSWERS IT ITSELF, so no path in ai/ and no API call: an owner in
auto_players takes the teleport whenever a legal spot exists. Declining is only
correct when the Yncarne is already where it wants to be, which is a judgement
this engine has no way to make and which a prompt nobody answers would stall on.
"""
import math

from game import ai_mode, model_return
from game.formation_layout import ring_candidates

INEVITABLE_DEATH_LABEL = "Inevitable Death"

#: How far out the ring walk is allowed to look for a legal landing spot,
#: in rings. Generous on purpose: "as close as possible" has no printed cap,
#: and the whole point is that the nearest squares are usually the ones inside
#: the combat that just killed the unit.
INEVITABLE_DEATH_RINGS = 12


def applies(squad):
    return any(getattr(m.profile, "inevitable_death", False)
               for m in (getattr(squad, "models", ()) or ()) if not m.is_dead())


class InevitableDeathController:
    """The teleport, its once-per-opponent-turn ledger, and the spot search."""

    def __init__(self, game_state=None, game_log=None, decision_manager=None,
                 setup_controller=None, all_tokens=None, turn_tracker=None,
                 auto_players=()):
        self.game_state = game_state
        self.game_log = game_log
        self.decision_manager = decision_manager
        self.setup_controller = setup_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.auto_players = ai_mode.players(auto_players)
        #: (id(squad), turn owner) for every use so far - "once in EACH
        #: opponent's turn", so the turn owner is part of the key.
        self._used = set()

    # ------------------------------------------------------------- the gate

    def _turn_owner(self):
        return getattr(self.turn_tracker, "turn_owner", None)

    def can_use(self, squad):
        """All four printed qualifiers except "another unit died", which is the
        trigger rather than a property of the Yncarne."""
        if not applies(squad):
            return False
        owner = self._turn_owner()
        # "once in each OPPONENT'S turn" - never in its own controller's turn.
        if owner is not None and owner == squad.owner:
            return False
        if (id(squad), owner) in self._used:
            return False
        # "if this model is ON THE BATTLEFIELD" - a Yncarne in Reserves or in
        # a transport is not, and tokens is what "on the battlefield" means
        # everywhere else in this engine.
        tokens = getattr(self.game_state, "tokens", None) or self.all_tokens or ()
        return any(t.squad is squad and not t.is_dead() for t in tokens)

    # --------------------------------------------------------- the trigger

    def notify_unit_destroyed(self, destroyed_squad, dead_models=()):
        """Fed once per wiped-out squad from main.py's death sweep.

        The COORDINATES are what this needs, and they are why it is fed from
        the sweep rather than recomputed later: a destroyed model keeps its
        x/y after it dies (the same property Reanimation Protocols rests on),
        but only until something clears it."""
        if destroyed_squad is None:
            return False
        spot = self._death_spot(destroyed_squad, dead_models)
        if spot is None:
            return False
        for squad in self._yncarnes(destroyed_squad):
            if self._offer(squad, destroyed_squad, spot):
                return True
        return False

    def _yncarnes(self, destroyed_squad):
        """"ANOTHER FRIENDLY AELDARI unit" - friendly to the Yncarne, and not
        the Yncarne's own unit."""
        from game import psychic_guidance
        if not psychic_guidance._is_aeldari(destroyed_squad):
            return []
        seen = []
        for token in (getattr(self.game_state, "tokens", None) or self.all_tokens or ()):
            squad = getattr(token, "squad", None)
            if squad is None or squad in seen or squad is destroyed_squad:
                continue
            if squad.owner != destroyed_squad.owner:
                continue
            if self.can_use(squad):
                seen.append(squad)
        return seen

    def _death_spot(self, destroyed_squad, dead_models=()):
        """"where a destroyed model from that unit was". Any of them is a legal
        choice by the printed text; the first is taken so the answer cannot
        flicker between two corpses."""
        models = list(dead_models or ()) or list(
            getattr(destroyed_squad, "destroyed_models", ()) or ())
        for model in models:
            x, y = getattr(model, "x_in", None), getattr(model, "y_in", None)
            if x is not None and y is not None:
                return (x, y)
        return None

    def _offer(self, squad, destroyed_squad, spot):
        if squad.owner in self.auto_players or self.decision_manager is None:
            return self.teleport(squad, spot, destroyed_squad)
        self.decision_manager.request(
            squad.owner,
            "%s: %s was destroyed - move %s to where it fell?"
            % (INEVITABLE_DEATH_LABEL, destroyed_squad.name, squad.name),
            [("Move to where it fell",
              (lambda: self.teleport(squad, spot, destroyed_squad))),
             ("Stay put", (lambda: True))])
        return True

    # -------------------------------------------------------- the teleport

    def landing_spot(self, squad, spot):
        """The nearest point to `spot` where the Yncarne stands legally and
        outside Engagement Range of every enemy.

        Ring 0 - the corpse's own square - is tried first, because "as close as
        possible" means exactly there when it is free."""
        model = next((m for m in squad.models if not m.is_dead()), None)
        if model is None:
            return None
        enemies = model_return.enemy_tokens(model, self.all_tokens)
        step = max(1.0, 2 * model.radius_in + 0.1)
        candidates = [spot] + list(ring_candidates(
            spot[0], spot[1], step, 0.0, INEVITABLE_DEATH_RINGS))
        for x_in, y_in in candidates:
            if self.setup_controller is not None \
                    and not self.setup_controller.position_valid(model, x_in, y_in):
                continue
            if not model_return.clear_of_engagement(model, x_in, y_in, enemies):
                continue
            return (x_in, y_in)
        return None

    def teleport(self, squad, spot, destroyed_squad=None):
        if not self.can_use(squad):
            return False
        landing = self.landing_spot(squad, spot)
        if landing is None:
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s finds nowhere clear of Engagement Range to appear."
                    % (INEVITABLE_DEATH_LABEL, squad.name))
            return False
        self._used.add((id(squad), self._turn_owner()))
        moved = 0.0
        for model in squad.models:
            if model.is_dead():
                continue
            moved = math.hypot(model.x_in - landing[0], model.y_in - landing[1])
            model.x_in, model.y_in = landing
            break
        if self.game_log is not None:
            self.game_log.add(
                '%s: %s steps through the dead of %s and appears %.1f" away '
                "at (%.1f,%.1f); it can still move this turn."
                % (INEVITABLE_DEATH_LABEL, squad.name,
                   getattr(destroyed_squad, "name", "a fallen unit"),
                   moved, landing[0], landing[1]))
        return True
