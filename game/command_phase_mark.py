"""'In your Command phase, select one friendly <X> unit within N" of the
bearer. Until the start of your next Command phase, …' - the 26th extraction,
at its fourth carrier.

WHY IT EXISTS
-------------
Four Enhancements print that sentence, differing only in the keyword, the
distance and what the mark then DOES:

    Admired Leader     (Auxiliary Cadre)  KROOT/VESPID STINGWINGS   12"
    Light of Clarity   (Spirit Conclave)  WRAITH CONSTRUCT          12"
    Stave of Kurnous   (Spirit Conclave)  WRAITH CONSTRUCT          12"
    Rune of Mists      (Spirit Conclave)  WRAITH CONSTRUCT          12"

Admired Leader was built first and owns the whole machine: find the bearers,
clear last round's mark, offer this round's, auto-pick for the AI, stamp a flag
on the Squad. The three new ones would be three copies of it.

AND ONE HALF OF THAT MACHINE IS THE PART THAT IS EASY TO GET WRONG:
begin_command_phase() CLEARS before it OFFERS. Written the other way round, a
mark re-issued to the same unit is stamped and then immediately wiped, and the
Enhancement silently does nothing every round after the first. Admired Leader's
own docstring flags that ordering; sharing it means the three new ones cannot
get it wrong separately.

`exclude_own_unit` IS A PARAMETER, AND THAT IS NOT TIDINESS. Admired Leader's
eligible_targets() skips `squad is bearer_squad`, which its printed text does
not say and which the three Spirit Conclave ones definitely do not ("select one
friendly WRAITH CONSTRUCT unit within 12" of the bearer" - the bearer's own unit
is a friendly unit). Folding that line into the base unconditionally would
either widen Admired Leader or narrow the other three, and both directions are
silent. So it is a flag, True for Admired Leader and False for the rest, and
both settings are pinned. (Measured: a Spiritseer prints no LEADER line, so it
is always its own unit and the difference does not bite on the built roster -
which is exactly why it needs writing down rather than leaving to luck.)

THE RANGE IS MEASURED FROM THE BEARER MODEL, not from its unit. After a 19.01
merge those are different circles, and every one of the four prints "of this
model" / "of the bearer".

NOT MERGED WITH game/psychic_mark.py, and the reasons are all printed rather
than stylistic: that one marks an ENEMY unit, at the end of the MOVEMENT phase,
requires visibility, and its effect is read on the ATTACKER's side rather than
on the marked unit. Only the ledger and the expiry coincide, which is about ten
lines. Sibling, not parent.

TEARS OF ISHA IS DELIBERATELY OUT even though its selection is the same
sentence at 6" (game/spiritseer.py). Its resolution returns a model or heals
one - it leaves no mark behind and has nothing to expire, so the half it would
share is the half this module does not own.
"""

from game import ai_mode, enhancements
from game.squad import edge_distance


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


class CommandPhaseMark:
    """The shared machine. One instance per Enhancement, because the flag, the
    keyword test and the prompt text are all its own.

    `target_ok(squad)` is the printed keyword clause. `flag_attr` is the Squad
    attribute the effect reads. `effect_text` is what the prompt and the log
    call the bonus - the only place the wording differs once the machine is
    shared."""

    def __init__(self, name, range_in, flag_attr, target_ok, effect_text,
                 game_state=None, decision_manager=None, game_log=None,
                 auto_players=(), exclude_own_unit=False, decline_label=None):
        self.name = name
        self.range_in = range_in
        self.flag_attr = flag_attr
        self.target_ok = target_ok
        self.effect_text = effect_text
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        #: See the module docstring - printed, not stylistic.
        self.exclude_own_unit = exclude_own_unit
        self.decline_label = decline_label or "Nobody this round"

    # ------------------------------------------------------------- helpers

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _squads(self):
        """Every distinct squad on the board - deduplicated, because
        game_state.tokens is one entry per MODEL."""
        seen = []
        for token in (getattr(self.game_state, "tokens", None) or ()):
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in seen:
                seen.append(squad)
        return seen

    def is_marked(self, squad):
        return bool(getattr(squad, self.flag_attr, False))

    def bearer_units(self, player):
        return enhancements.bearer_units(self._squads(), self.name, player=player)

    def _bearer_models(self, squad):
        return enhancements.bearer_models(squad, self.name)

    # --------------------------------------------------------- eligibility

    def eligible_targets(self, bearer_squad):
        """The printed clause, measured from the BEARER MODEL."""
        bearers = self._bearer_models(bearer_squad)
        if not bearers:
            return []
        out = []
        for squad in self._squads():
            if squad.owner != bearer_squad.owner:
                continue
            if self.exclude_own_unit and squad is bearer_squad:
                continue
            if not self.target_ok(squad):
                continue
            if any(edge_distance(b, m) <= self.range_in
                   for b in bearers for m in _living(squad)):
                out.append(squad)
        return out

    # ------------------------------------------------------ the two halves

    def clear(self, player):
        """"until the start of your next Command phase" - the previous round's
        mark ends here."""
        for squad in self._squads():
            if squad.owner == player and self.is_marked(squad):
                setattr(squad, self.flag_attr, False)
                self._log("%s: %s no longer has the %s bonus."
                          % (player, squad.name, self.name), file_only=True)

    def begin_command_phase(self, player):
        """Clear last round's mark, THEN offer this round's. Returns True if
        anything was asked or marked.

        The order is the printed one and is the half worth sharing - see the
        module docstring."""
        self.clear(player)
        asked = False
        for bearer_squad in self.bearer_units(player):
            targets = self.eligible_targets(bearer_squad)
            if not targets:
                continue
            if player in self.auto_players or self.decision_manager is None:
                self.mark(self._pick(targets))
                asked = True
                continue
            options = [("%s: %s" % (self.name, t.name), (lambda target=t: self.mark(target)), t)
                       for t in targets]
            options.append((self.decline_label, None))
            self.decision_manager.request(
                player,
                '%s: which unit within %.0f" %s?'
                % (self.name, self.range_in, self.effect_text),
                options)
            asked = True
        return asked

    def _pick(self, targets):
        """Most living models, ties broken by name so a self-play run is
        reproducible."""
        return sorted(targets, key=lambda s: (-len(_living(s)), s.name))[0]

    def mark(self, squad):
        if squad is None:
            return False
        setattr(squad, self.flag_attr, True)
        self._log("%s: %s %s (until the start of its next Command phase)."
                  % (squad.owner, squad.name, self.effect_text))
        return True
