"""Ghazghkull Thraka's Makari, Hoist Dat Banner! (2026-09 Ork codex, Mecha Orks
stage G2).

RULE (verbatim, rules/orks/Ghazghkull Thraka.md):
  "Makari, Hoist Dat Banner! (Once per battle, per army): In your Movement phase,
   you can select a number of friendly ORKS units equal to or less than the
   current battle round number. Those units are riled up until the start of your
   next turn."

A PANEL BUTTON through game/proactive_stratagems.py, like Da Boss is Watchin': a
moment of the owner's choosing in their own Movement phase, no CP, read off the
live clock. Pressing it opens a pick - one prompt per unit, each option naming a
unit (tagged, so the board can pick it too), until the battle round's count is
reached or the player says Done. "Once per battle, per army" is spent by the
FIRST pick, written onto Ghazghkull's unit (Squad.makari_used, saved) and read
back over every unit the player has; pressing the button and cancelling before
picking anything spends nothing.

"FRIENDLY ORKS UNITS" are the ones with the Waaagh! ability (the one thing that
can be riled up - riled_up.grant() refuses anything else), wherever they are;
only units the grant would actually EXTEND are offered (Fehlerklasse 5): a unit
already riled up until at least the start of your next turn gains nothing.
"Until the start of your next turn" is riled_up.until_start_of_your_next_turn().

"A NUMBER ... EQUAL TO OR LESS THAN THE CURRENT BATTLE ROUND NUMBER": up to the
battle round, so one unit in round 1 and five in round 5.

THE AI (ai/agent_driver.py's _handle_makari(), 0 API calls) picks through
use_on() without a prompt.
"""

from game import riled_up
from game.squad import unit_wide_ability
from game.turn import PHASE_MOVEMENT

MAKARI_NAME = "Makari, Hoist Dat Banner!"
DONE_LABEL = "Done"
CANCEL_LABEL = "Cancel"


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "makari"))


class MakariController:
    def __init__(self, turn_tracker=None, decision_manager=None, squads_provider=None, game_log=None):
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        # Every unit in the game, wherever it is - "per army" means the whole army.
        self.squads_provider = squads_provider
        self.game_log = game_log
        self._picking = None   # (bearer squad, [picked squads]) while a human is choosing

    # ------------------------------------------------------------ questions

    def _squads(self):
        return [s for s in (self.squads_provider() if self.squads_provider else ()) if s is not None]

    def is_used(self, player, squad=None):
        pool = self._squads()
        if squad is not None and squad not in pool:
            pool.append(squad)
        return any(getattr(s, "makari_used", False) for s in pool if getattr(s, "owner", None) == player)

    def limit(self):
        return max(0, getattr(self.turn_tracker, "battle_round", 0) or 0)

    def deadline(self, player):
        return riled_up.until_start_of_your_next_turn(self.turn_tracker, player)

    def candidates(self, player):
        """Friendly ORKS units the grant would extend, by name. A unit already
        picked in this use drops out by itself: the grant sets its deadline to
        exactly this one, so it has nothing more to gain - which is why there is
        no separate "already picked" term (the A/B probe on one found it could
        never be the one that held)."""
        deadline = self.deadline(player)
        out = []
        for squad in self._squads():
            if squad.owner != player:
                continue
            if not any(not m.is_dead() for m in squad.models) or not riled_up.has_ability(squad):
                continue
            current = getattr(squad, "riled_up_expires_turn", None)
            if current is not None and current >= deadline:
                continue
            out.append(squad)
        return sorted(out, key=lambda s: s.name)

    def panel_label(self, squad):
        return "%s (once per battle, no CP) - rile up to %d unit(s)" % (MAKARI_NAME, self.limit())

    def can_use(self, squad):
        tt = self.turn_tracker
        if squad is None or tt is None or not has_ability(squad):
            return False
        if tt.phase != PHASE_MOVEMENT or squad.owner != tt.turn_owner:
            return False
        if self._picking is not None or self.limit() <= 0:
            return False
        if self.is_used(squad.owner, squad):
            return False
        return bool(self.candidates(squad.owner))

    # ------------------------------------------------------------ the human

    def use(self, squad):
        """The panel button: open the pick. Returns True if it opened."""
        if not self.can_use(squad) or self.decision_manager is None:
            return False
        self._picking = (squad, [])
        self._ask()
        return True

    def _ask(self):
        bearer, picked = self._picking
        remaining = self.limit() - len(picked)
        options = [("%s: %s" % (MAKARI_NAME, target.name), (lambda t=target: self.pick(t)), target)
                   for target in self.candidates(bearer.owner)]
        if remaining <= 0 or not options:
            self._picking = None
            return
        options.append((DONE_LABEL if picked else CANCEL_LABEL, self._finish))
        self.decision_manager.request(
            bearer.owner,
            "%s: select a unit to rile up until the start of your next turn (%d left)."
            % (MAKARI_NAME, remaining),
            options,
        )

    def pick(self, target):
        if self._picking is None:
            return False
        bearer, picked = self._picking
        if target not in self.candidates(bearer.owner):
            self._ask()
            return False
        self._grant(bearer, target)
        picked.append(target)
        self._ask()
        return True

    def _finish(self):
        self._picking = None

    # ----------------------------------------------------------- both sides

    def _grant(self, bearer, target):
        if not getattr(bearer, "makari_used", False):
            bearer.makari_used = True
        riled_up.grant(target, self.deadline(bearer.owner), self.turn_tracker)
        if self.game_log is not None:
            self.game_log.add("%s: %s is riled up until the start of %s's next turn."
                              % (MAKARI_NAME, target.name, bearer.owner))

    def use_on(self, bearer, targets):
        """The AI's path: rile up `targets` (at most the battle round's count)
        with no prompt. Returns the units that took."""
        if not self.can_use(bearer):
            return []
        allowed = set(id(s) for s in self.candidates(bearer.owner))
        done = []
        for target in targets:
            if len(done) >= self.limit():
                break
            if id(target) in allowed and target not in done:
                self._grant(bearer, target)
                done.append(target)
        return done
