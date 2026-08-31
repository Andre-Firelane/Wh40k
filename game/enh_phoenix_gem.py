"""Warhost Enhancement: Phoenix Gem (35 pts).

RULE (verbatim, rules/aeldari/detachments/Warhost.md):
  "ASURYANI model only. The first time the bearer is destroyed, remove it from
  play, then, at the end of the phase, roll one D6: on a 2+, set the bearer
  back up on the battlefield as close as possible to where it was destroyed and
  not within Engagement Range of one or more enemy units, with its full wounds
  remaining."

THE MOST EXPENSIVE OF THE 28, and structurally Fuegan's Unquenchable Resolve
with a different roll - so it reuses that shape rather than inventing one:

  * Squad.destroyed_models keeps the token after remove_dead_models(), and
    nobody resets its coordinates, so "where it was destroyed" survives.
  * formation_layout.ring_candidates() walks outward from that point, which is
    literally "as close as possible".
  * game/model_return.py owns all four halves of putting a model back (the
    token list, the squad, off destroyed_models, and its wounds), and its
    clear_of_engagement() owns the Engagement Range test.

FOUR CLAUSES, AND EACH IS A SEPARATE WAY TO GET IT WRONG:

  1. "THE FIRST TIME" - once per battle, per bearer. A second death is final,
     and the ledger is NOT cleared by any phase or turn reset.
  2. "AT THE END OF THE PHASE", not at the moment of death. main.py's
     remove_dead_models() runs once per frame, so a trigger at death time sees
     a board still full of corpses and enemy positions that are about to
     change. The phase boundary is where the sweep is finished.
  3. "NOT WITHIN ENGAGEMENT RANGE" has to be checked HERE.
     SetupController.position_valid() says in its own docstring that it does
     NOT cover engagement - that omission once cost a whole squad in an
     Emergency Disembark, and it would put this model straight back into the
     combat that killed it.
  4. "WITH ITS FULL WOUNDS REMAINING" - set_up_model()'s DEFAULT, so no
     wounds= is passed. That argument exists for Eternal Revenant, which is
     the one that comes back at HALF.

NOT OPTIONAL AND NOBODY IS ASKED. The text has no "you can", so there is no
prompt: the D6 goes through the DiceManager labelled and with its threshold, so
the human sees the roll that decides it, and the placement is deterministic.
"""
import math

from game import enhancements, formation_layout, model_return

PHOENIX_GEM = "Phoenix Gem"

PHOENIX_GEM_LABEL = "Phoenix Gem"

#: "roll one D6: on a 2+".
PHOENIX_GEM_THRESHOLD = 2
PHOENIX_GEM_SIDES = 6

#: How far out to look for a legal spot - the same depth Unquenchable Resolve
#: searches.
SEARCH_RINGS = 12


def is_bearer(model):
    """Reads the FLAG rather than the registry's living-bearer list: by the
    time this is asked the model is DEAD, which is the whole point."""
    if model is None:
        return False
    return bool(getattr(model.profile, "phoenix_gem", False))


def detachment_active(squad):
    """The detachment half of the usual gate, WITHOUT the living-bearer half.

    enhancements.is_active() asks both, and its bearer half is
    bearer_models() - which filters the dead. That is right for every other
    Enhancement and exactly wrong here: this one only ever fires ABOUT a dead
    bearer, so is_active() would be False precisely when the ability is
    supposed to trigger and the card could never work in a real game. Found by
    the suite, not by reading.

    So the two halves are asked separately: is_bearer() off the flag, and the
    detachment off the owner."""
    if squad is None:
        return False
    spec = enhancements.get(PHOENIX_GEM)
    return enhancements.player_has_detachment(
        getattr(squad, "owner", None), spec.setting)


class PhoenixGemController:
    """The death note, the end-of-phase roll, and the return."""

    def __init__(self, game_state=None, dice_manager=None, game_log=None,
                 position_valid=None, all_tokens=None):
        self.game_state = game_state
        self.dice_manager = dice_manager
        self.game_log = game_log
        self.position_valid = position_valid
        self.all_tokens = all_tokens
        #: (squad, model) pairs owed a roll at the end of this phase.
        self._pending = []
        #: id(model) of every bearer that has already used its one return.
        self._used = set()

    def _tokens(self):
        if self.all_tokens is not None:
            return self.all_tokens
        return getattr(self.game_state, "tokens", ()) or ()

    # --- the death note ---------------------------------------------------

    def notify_model_destroyed(self, squad, model):
        """Called from main.py's death sweep - the same seam Fuegan's
        Unquenchable Resolve uses, and for the same reason: the PHASE the death
        happened in is not reconstructable afterwards."""
        if not is_bearer(model) or not detachment_active(squad):
            return False
        if id(model) in self._used:
            return False              # "the FIRST time" - once per battle
        self._used.add(id(model))
        self._pending.append((squad, model))
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s is destroyed - it will roll to return at the end of the "
                "phase." % (PHOENIX_GEM_LABEL, model.profile.name))
        return True

    # --- the end-of-phase roll -------------------------------------------

    def resolve_end_of_phase(self):
        """"at the end of the phase, roll one D6: on a 2+"."""
        pending, self._pending = self._pending, []
        returned = []
        for squad, model in pending:
            if self._roll_for(squad, model):
                returned.append(model)
        return returned

    def _roll_for(self, squad, model):
        roll = self._roll()
        if roll < PHOENIX_GEM_THRESHOLD:
            if self.game_log is not None:
                self.game_log.add("%s: rolled %d - %s does not return."
                                  % (PHOENIX_GEM_LABEL, roll, model.profile.name))
            return False
        spot = self._spot_for(model)
        if spot is None:
            if self.game_log is not None:
                self.game_log.add(
                    "%s: rolled %d, but %s has nowhere legal to return."
                    % (PHOENIX_GEM_LABEL, roll, model.profile.name))
            return False
        # "with its FULL wounds remaining" - set_up_model()'s DEFAULT, which
        # is why no wounds= is passed. Eternal Revenant is the one that needs
        # the argument, coming back at half.
        model_return.set_up_model(model, spot, game_state=self.game_state)
        if self.game_log is not None:
            self.game_log.add(
                "%s: rolled %d - %s returns with its full wounds."
                % (PHOENIX_GEM_LABEL, roll, model.profile.name))
        return True

    def _roll(self):
        """A real, LABELLED dice step with its threshold on it - the roll IS
        the ability, and an unlabelled die at a phase boundary is exactly the
        diagnosis-from-raw-numbers this project keeps paying for. Falls back to
        a plain roll without a dice manager, as every other such ability does."""
        if self.dice_manager is None:
            from game.dice import random as dice_random
            return dice_random.randint(1, PHOENIX_GEM_SIDES)
        values = self.dice_manager.roll(
            1, PHOENIX_GEM_SIDES, label=PHOENIX_GEM_LABEL,
            success_threshold=PHOENIX_GEM_THRESHOLD)
        return values[0] if values else PHOENIX_GEM_SIDES

    def _spot_for(self, model):
        """"as close as possible to where it was destroyed and NOT within
        Engagement Range of one or more enemy units".

        The same walk and the same two legality halves Fuegan's Unquenchable
        Resolve uses - including the engagement test, which lives in
        game/model_return.py because SetupController.position_valid()
        explicitly does not cover it."""
        owner = getattr(getattr(model, "squad", None), "owner", None)
        enemies = [t for t in self._tokens()
                   if getattr(t, "squad", None) is not None
                   and t.squad.owner != owner and not t.is_dead()]
        step = max(model.radius_in * 2, 0.5)
        for x_in, y_in in formation_layout.ring_candidates(
                model.x_in, model.y_in, step, -math.pi / 2, rings=SEARCH_RINGS):
            if self.position_valid is not None and not self.position_valid(model, x_in, y_in):
                continue
            if not model_return.clear_of_engagement(model, x_in, y_in, enemies):
                continue
            return (x_in, y_in)
        return None
