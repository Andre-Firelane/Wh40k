"""The Big Mek in Mega Armour's Fix Dat Armour Up (2026-09 Ork codex, Mecha Orks
stage G2).

RULE (verbatim, rules/orks/Big Mek In Mega Armour.md):
  "Fix Dat Armour Up (Once per battle, per unit): In your Command phase, this unit
   heals 3 wounds."

THE HEAL IS CRUDE SURGERY'S: core rule 02.02.04 through game/heal.py - damaged
models topped up first, then destroyed non-CHARACTER models revived (01.02.03's
Starting Strength caps it), a human places revived models through the shared
ReturnPlacementController, and a unit off the battlefield heals where it is.

WHAT IS NOT CRUDE SURGERY'S is "once per battle". Crude Surgery heals every
Command phase for nothing, so it is never asked (Fehlerklasse 5); this one is a
single use, and WHEN to spend it is the whole decision. So it is OFFERED at the
start of the owner's Command phase - only when there is something to heal, since
a heal of nothing would spend the use for no gain - with "Fix Dat Armour Up" /
"Save it for later". The AI answers through an injected verdict
(ai/agent_driver.py's fix_dat_armour_up_verdict(), 0 API calls).

"THIS UNIT" is the Big Mek's unit - the Meganobz he leads while he lives (rule
19.04, unit_wide_ability()). He is a CHARACTER: he can be topped up but never
revived, and a dead Big Mek fixes nobody. The spend is
Squad.fix_dat_armour_up_used (saved) on the unit that used it.
"""

from game import ai_mode, heal as heal_rule
from game.squad import unit_wide_ability

FIX_DAT_ARMOUR_UP_NAME = "Fix Dat Armour Up"
#: "this unit heals 3 wounds".
FIX_DAT_WOUNDS = 3
USE_LABEL = "Fix Dat Armour Up (heal 3 wounds)"
SAVE_LABEL = "Save it for later"


def _alive(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def has_ability(squad):
    return squad is not None and bool(_alive(squad)) and bool(unit_wide_ability(squad, "fix_dat_armour_up"))


def offerable(squad, player=None):
    """Unused, owned by `player` (when given), and with something to heal."""
    if not has_ability(squad) or getattr(squad, "fix_dat_armour_up_used", False):
        return False
    if player is not None and squad.owner != player:
        return False
    return heal_rule.healable_wounds(squad) > 0


class FixDatArmourUpController:
    def __init__(self, decision_manager=None, game_log=None, game_state=None, position_valid=None,
                 auto_players=(), placer=None, verdict=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.position_valid = position_valid  # SetupController's own predicate, as Crude Surgery's
        self.auto_players = ai_mode.players(auto_players)
        self.placer = placer
        # verdict(squad) -> bool: the AI's rule, injected (game/ must not import
        # ai/). None: an auto player uses it at the first chance.
        self.verdict = verdict
        self._queue = []
        self._current = None

    @property
    def is_busy(self):
        return self._current is not None or bool(self._queue)

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    def begin_command_phase(self, squads, player):
        """The start of `player`'s Command phase. Sorted by name so a replay and
        a test see the same order."""
        if self.is_busy:
            return False
        self._queue = sorted((s for s in squads or () if offerable(s, player)), key=lambda s: s.name)
        if not self._queue:
            return False
        self._advance()
        return True

    def _advance(self):
        while self._queue and self._current is None:
            squad = self._queue.pop(0)
            if not offerable(squad, squad.owner):
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                if self.verdict is None or self.verdict(squad):
                    self.use(squad)
                continue
            self._current = squad
            self.decision_manager.request(
                squad.owner,
                "%s: %s (once per battle) - heal %d wound(s) now (%d to recover)?"
                % (squad.name, FIX_DAT_ARMOUR_UP_NAME, FIX_DAT_WOUNDS, heal_rule.healable_wounds(squad)),
                [(USE_LABEL, lambda s=squad: self._answer(s, True)),
                 (SAVE_LABEL, lambda s=squad: self._answer(s, False))],
            )
            return

    def _answer(self, squad, use):
        if self._current is not squad:
            return
        self._current = None
        if use:
            self.use(squad)
        self._advance()

    def _on_board(self, squad):
        tokens = {id(t) for t in self._tokens()}
        return any(id(m) in tokens for m in _alive(squad))

    def use(self, squad):
        """Spend the use and heal. Returns (healed, revived) or None when refused."""
        if not offerable(squad):
            return None
        squad.fix_dat_armour_up_used = True
        off_board = not self._on_board(squad)
        spent, revived = heal_rule.heal(
            squad, FIX_DAT_WOUNDS,
            all_tokens=self._tokens(),
            position_valid=self.position_valid,
            game_state=self.game_state,
            placer=None if off_board else self.placer,
            off_board=off_board,
        )
        detail = "%d wound(s)" % spent
        if revived:
            detail += ", %d model(s) back%s" % (len(revived), " in the unit" if off_board else " on the battlefield")
        self._log("%s (%s): heals %d - %s." % (FIX_DAT_ARMOUR_UP_NAME, squad.name, FIX_DAT_WOUNDS, detail))
        return spent, revived
