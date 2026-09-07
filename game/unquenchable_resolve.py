"""Fuegan's "Unquenchable Resolve".

RULE (printed, word for word):
  "The first time this model is destroyed, at the end of the phase, roll one D6:
   on a 2+, set this model back up on the battlefield as close as possible to
   where it was destroyed and not within Engagement Range of one or more enemy
   units, with its full wounds remaining."

PUTTING A MODEL BACK is a concept this engine already has exactly once - the
Painboy's Grot Orderly (game/grot_orderly.py) - and both pieces it needed are
therefore already in place:

  * Squad.destroyed_models. GameState.remove_dead_models() takes a dead Token
    out of Squad.models but keeps the object, so the model that has to come back
    is still there to be found - and, because nothing resets its coordinates, so
    is "where it was destroyed".
  * a placement that is not a drag. formation_layout.ring_candidates() walks
    outwards from a point in concentric rings, which is precisely "as close as
    possible to where it was destroyed".

WHERE IT DIFFERS FROM GROT ORDERLY, and each difference is in the printed text:

  * The placement rule is DISTANCE, not coherency. Grot Orderly returns
    bodyguards into a standing unit, so it uses returning_positions() to keep
    09.02 by construction. This one names one spot - as close as possible to
    where the model fell - and the unit's shape has no say in it. A unit left
    incoherent by his return is repaired the ordinary way, on its next move;
    09.02 is checked when a unit moves, not continuously.
  * "not within Engagement Range of one or more enemy units" is a CONDITION ON
    THE SPOT, and it has to be tested here. SetupController.position_valid()
    deliberately does NOT check engagement (its docstring says so: engagement
    and coherency depend on a whole squad's final positions, not one point), so
    relying on it alone would put him straight into combat - the same trap that
    once cost a whole unit in the Emergency Disembark.
  * "the first time this model is destroyed" is once per BATTLE and per MODEL,
    so the ledger is keyed on the model, not on the unit or the player.
  * It is not optional and there is nobody to ask. The text has no "you can" -
    it says roll, and on a 2+ he comes back. So no DecisionManager prompt: the
    D6 goes through the dice manager (the human sees the roll that decides it)
    and the placement is deterministic.

HE COMES BACK INTO HIS OWN UNIT. Under 19.01 this engine MERGES an attached
leader into one Squad, so the model that died was a model of that Squad, and the
printed text says only "set this model back up on the battlefield" - nothing
about leaving. Returning him to the same Squad is therefore the reading that
adds nothing: if the unit still stands he is leading it again (and Burning Lance
resumes with him), and if the unit was wiped out he is the sole model of a Squad
that is once again on the battlefield, which is exactly what "set this model back
up" describes.

END OF THE PHASE, not the moment of death, and that matters for more than
tidiness: remove_dead_models() runs once per frame and every trigger before it
still sees corpses (CLAUDE.md's error class 12). Resolving at the phase boundary
means the sweep has finished, the enemy positions his Engagement Range test
reads are settled, and a model destroyed by the same attack that killed the rest
of his unit is handled after all of them.
"""

import math

from game import formation_layout, model_return

UNQUENCHABLE_RESOLVE_THRESHOLD = 2  # "on a 2+"

# How finely the outward search steps, and how far it is allowed to look. The
# step is a base diameter's worth of ground, so consecutive candidates cannot
# both be blocked by the same model; the ring count is generous because the
# alternative to finding a spot is losing the model permanently, and this runs
# at most once per battle.
_SEARCH_RINGS = 24


def has_unquenchable_resolve(model):
    return bool(getattr(model.profile, "unquenchable_resolve", False))


def _enemy_tokens(model, all_tokens):
    """Kept as a thin alias so this module's own readers still find it under
    the name they know; the definition lives in game/model_return.py now."""
    return model_return.enemy_tokens(model, all_tokens)


class UnquenchableResolveController:
    """Wired in main.py: fed destroyed models as they are swept, and resolved at
    every phase boundary."""

    def __init__(self, dice_manager=None, game_state=None, game_log=None,
                 position_valid=None, placer=None):
        self.dice_manager = dice_manager
        self.game_state = game_state
        self.game_log = game_log
        self.position_valid = position_valid
        # ReturnPlacementController (game/return_placement.py). Rule
        # 01.02.03 makes a returning model SET UP, so a human sets it up;
        # an owner in auto_players still lands on the spot computed here.
        self.placer = placer
        self._pending = []   # models destroyed this phase that are owed a roll
        self._used = set()   # id(model) - "the FIRST time this model is destroyed"

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    # -- collecting -------------------------------------------------------
    def notify_destroyed(self, models):
        """Called with whatever GameState.remove_dead_models() just swept.

        Filtering here rather than at the phase boundary keeps the ledger honest
        about WHEN the model died: a second death in a later phase must not
        qualify, and it would if the check only ran later."""
        for model in models:
            if not has_unquenchable_resolve(model):
                continue
            if id(model) in self._used:
                continue  # "the first time this model is destroyed" - spent
            if model in self._pending:
                continue
            self._pending.append(model)

    def is_pending(self):
        return bool(self._pending)

    # -- resolving --------------------------------------------------------
    def resolve_end_of_phase(self):
        """"at the end of the phase, roll one D6". Returns the models actually
        set back up, for tests and callers that want to report it."""
        returned = []
        while self._pending:
            model = self._pending.pop(0)
            self._used.add(id(model))
            roll = self._roll()
            name = model.profile.name
            if roll < UNQUENCHABLE_RESOLVE_THRESHOLD:
                self._log(f"{name}: Unquenchable Resolve - rolled {roll}, needed "
                          f"{UNQUENCHABLE_RESOLVE_THRESHOLD}+. He does not rise.")
                continue
            spot = self._spot_for(model)
            if spot is None:
                # Nowhere legal within the search. Reported rather than forced
                # onto illegal ground, and the roll is still spent - it was made.
                self._log(f"{name}: Unquenchable Resolve - rolled {roll}, but no legal "
                          "spot was found near where he fell.")
                continue
            if self.placer is not None and model.squad is not None:
                # The same predicate _spot_for() searched with, so what the
                # drag allows is what the search would have accepted.
                enemies = _enemy_tokens(model, list(self.game_state.tokens)
                                        if self.game_state is not None else [])
                if not self.placer.place(
                        model.squad, [model], [spot],
                        validator=lambda m, x, y, _e=enemies: self._legal(m, x, y, _e)):
                    continue
            else:
                self._set_up(model, spot)
            self._log(f"{name}: Unquenchable Resolve - rolled {roll}, back on the "
                      f"battlefield at ({spot[0]:.1f}, {spot[1]:.1f}) with full wounds.")
            returned.append(model)
        return returned

    def _roll(self):
        if self.dice_manager is None:
            return 6
        # Labelled and given its threshold so the dice panel colours it and says
        # what it is deciding - the roll is the whole ability, and an unlabelled
        # die at a phase boundary is exactly the diagnosis-from-raw-numbers this
        # project keeps paying for.
        values = self.dice_manager.roll(
            1, 6, label="Unquenchable Resolve",
            success_threshold=UNQUENCHABLE_RESOLVE_THRESHOLD)
        return values[0] if values else 6

    # -- the placement ----------------------------------------------------
    def _spot_for(self, model):
        """"as close as possible to where it was destroyed and not within
        Engagement Range of one or more enemy units"."""
        all_tokens = list(self.game_state.tokens) if self.game_state is not None else []
        enemies = _enemy_tokens(model, all_tokens)
        origin = (model.x_in, model.y_in)
        step = max(model.radius_in * 2, 0.5)
        for x_in, y_in in formation_layout.ring_candidates(
                origin[0], origin[1], step, -math.pi / 2, rings=_SEARCH_RINGS):
            if not self._legal(model, x_in, y_in, enemies):
                continue
            return (x_in, y_in)
        return None

    def _legal(self, model, x_in, y_in, enemies):
        if self.position_valid is not None and not self.position_valid(model, x_in, y_in):
            return False
        # The engagement half, which position_valid() explicitly does not cover.
        # Measured edge to edge, like every other Engagement Range test here.
        return model_return.clear_of_engagement(model, x_in, y_in, enemies)

    def _set_up(self, model, spot):
        """The four halves of "back" - see game/model_return.py, which owns
        that sequence now that four abilities perform it. He returns "with its
        full wounds remaining", which is set_up_model()'s default."""
        model_return.set_up_model(model, spot, game_state=self.game_state)
