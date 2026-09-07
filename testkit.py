"""Shared harness for the datasheet/ability test suites.

WHY THIS EXISTS
---------------
Every new-unit suite before this one re-derived the same handful of facts
about how to drive this engine headless, and got several of them wrong on
the first try each time - which is most of what adding a datasheet actually
cost. The traps, all of which look like engine bugs and are not:

  * Dice are generated through ``game.dice.random.randint``. Overriding
    ``DiceManager.roll`` or writing ``pending_values`` yourself does NOT
    script anything - the real values are drawn elsewhere, so the test
    silently runs on random dice. Use ``script()`` below.
  * ``TurnTracker(first_player="Player 1")`` takes a NAME, not a list of
    players.
  * ``TurnTracker.phase`` is a read-only property; reach a phase with
    ``advance_phase()`` or by setting ``phase_index`` from ``PHASES``.
  * ``DecisionManager`` lives in ``game.decision`` (singular), ``GameState``
    in ``game.game_state``.
  * ``DecisionManager.options`` holds DICTS (``{"label", "callback"}``), not
    tuples - iterating ``for label, _ in options`` silently walks dict keys.
  * ``build_squad(datasheet, owner, composition_index=0, choices=..., ...)``
    - ``owner`` is the second POSITIONAL argument, and ``choices`` is a dict
    of ``{model_line_name: {option_name: count}}``, not a list.
  * ``MovementController.select()`` takes a TOKEN, not a squad.
  * A damage allocation must go through ``ShootingController.
    choose_damage_model()``, never ``damage_session.choose_model()`` - only
    the controller path runs the follow-up checks.
  * ``DiceNotation`` has no readable ``__str__``; use
    ``game.dice_notation.describe()``.

Import what you need from here rather than rebuilding it. Everything below
uses REAL engine objects - the only thing faked is the random number source.
"""

import sys

from game import config as _config
from game import dice as _dice_mod
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.game_state import GameState
from game.turn import PHASES, PHASE_FIGHT, PHASE_SHOOTING, TurnTracker

__all__ = [
    "Checks", "script", "scripted", "Log", "build", "fight_scene",
    "shooting_scene", "options_of", "pick_option", "DecisionManager",
    "DiceManager", "GameState", "TurnTracker", "PHASES", "PHASE_FIGHT",
    "PHASE_SHOOTING", "build_squad",
]


# ------------------------------------------------------------------ checks

class Checks:
    """Counter + reporter. ``finish()`` prints and exits non-zero on any
    failure, which is the convention every suite in this repo follows."""

    def __init__(self, title=""):
        self.title = title
        self.count = 0
        self.failures = []

    def eq(self, label, got, want):
        self.count += 1
        if got != want:
            self.failures.append(f"{label}: got {got!r}, want {want!r}")
        return got == want

    def true(self, label, got):
        return self.eq(label, bool(got), True)

    def finish(self):
        print(f"{self.count - len(self.failures)}/{self.count} checks passed"
              + (f"  ({self.title})" if self.title else ""))
        for f in self.failures:
            print("  FAIL:", f)
        sys.exit(1 if self.failures else 0)


# ------------------------------------------------------------------- dice

_scripted = []
_default = [1]


def _scripted_randint(low, high):
    return _scripted.pop(0) if _scripted else _default[0]


_dice_mod.random.randint = _scripted_randint


def script(*values, default=1):
    """Queue the next dice faces. Anything past the script comes up
    `default` (1 by default - a miss/failure, so only the dice a test
    actually cares about matter)."""
    _scripted[:] = list(values)
    _default[0] = default


def scripted():
    """The still-unconsumed script, for a test that wants to assert the
    engine drew exactly as many dice as expected."""
    return list(_scripted)


class RecordingDice(DiceManager):
    """Real DiceManager that also keeps (label, values) per roll, so a check
    can assert on what the ENGINE threw rather than on injected values."""

    def __init__(self):
        super().__init__()
        self.rolled = []

    def roll(self, count, sides=6, **kwargs):
        values = super().roll(count, sides, **kwargs)
        self.rolled.append((kwargs.get("label", ""), list(self.pending_values or values or [])))
        return values

    @property
    def last_roll(self):
        return self.rolled[-1] if self.rolled else ("", [])


# -------------------------------------------------------------------- log

class Log:
    def __init__(self):
        self.lines = []

    def add(self, message, file_only=False):
        self.lines.append(message)

    def find(self, needle):
        return next((l for l in self.lines if needle.lower() in l.lower()), "")

    def has(self, needle):
        return bool(self.find(needle))


# ------------------------------------------------------------- config flags

class settings_as:
    """Set game.config constants for one block and put them back.

    EIGHT COPIES OF THIS EXISTED before it moved here - one per detachment
    suite - and a ninth was about to be written for the Aeldari panel tests.
    config is a module, so a suite that leaves one set changes what every
    later suite measures; a detachment flag is exactly the kind of global a
    test has to switch on and cannot afford to forget.

    __enter__ returns self, which one of the eight did not do. Nothing used
    the `as` form, so delegating is behaviour-neutral for all eight."""

    def __init__(self, **values):
        self.values = values

    def __enter__(self):
        self.old = {k: getattr(_config, k) for k in self.values}
        for key, value in self.values.items():
            setattr(_config, key, value)
        return self

    def __exit__(self, *exc):
        for key, value in self.old.items():
            setattr(_config, key, value)
        return False


# ----------------------------------------------------------------- squads

def build(datasheet, owner="Player 2", name=None, choices=None, gear=None,
          composition_index=0, x=0.0, y=0.0):
    """build_squad() with the argument order this repo actually uses."""
    return build_squad(
        datasheet, owner, composition_index=composition_index, choices=choices,
        gear=gear, name=name or datasheet.name, x_in=x, y_in=y,
    )


def line_up(squad, x=20.0, y=20.0, spacing=1.4):
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = x + i * spacing, y
    return squad


# ----------------------------------------------------------------- scenes

def _tracker(phase, owner="Player 2"):
    tt = TurnTracker()
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = owner
    tt.set_active(owner)
    return tt


def fight_scene(attacker_sheet, target_sheet, attacker_owner="Player 2",
                attacker_choices=None, engaged=True, **controller_kwargs):
    """Two squads in the Fight phase, engaged, with the Fight step begun.

    Returns a dict with the squads, the controllers and a Log. Extra kwargs
    go straight to FightController (e.g. charge_controller=...)."""
    from game.fight import FightController

    state = GameState()
    defender_owner = "Player 1" if attacker_owner == "Player 2" else "Player 2"
    attacker = build(attacker_sheet, attacker_owner, name=f"{attacker_sheet.name} A",
                     choices=attacker_choices)
    target = build(target_sheet, defender_owner, name=f"{target_sheet.name} B")
    line_up(attacker, y=20.0)
    line_up(target, y=21.2 if engaged else 40.0)
    for squad in (attacker, target):
        for model in squad.models:
            state.add_token(model)

    tt = _tracker(PHASE_FIGHT, attacker_owner)
    log, dice, dec = Log(), RecordingDice(), DecisionManager()
    fc = FightController(
        dice_manager=dice, turn_tracker=tt, all_tokens=state.tokens,
        decision_manager=dec, game_log=log, **controller_kwargs,
    )
    fc.begin_fight_step()
    return dict(state=state, attacker=attacker, target=target, fight=fc,
                dice=dice, decision=dec, log=log, turn=tt)


def shooting_scene(attacker_sheet, target_sheet, attacker_owner="Player 2",
                   attacker_choices=None, gap=6.0, **controller_kwargs):
    """Two squads in the Shooting phase, `gap` inches apart."""
    from game.shooting import ShootingController

    state = GameState()
    defender_owner = "Player 1" if attacker_owner == "Player 2" else "Player 2"
    attacker = build(attacker_sheet, attacker_owner, name=f"{attacker_sheet.name} A",
                     choices=attacker_choices)
    target = build(target_sheet, defender_owner, name=f"{target_sheet.name} B")
    line_up(attacker, y=20.0)
    line_up(target, y=20.0 + gap)
    for squad in (attacker, target):
        for model in squad.models:
            state.add_token(model)

    tt = _tracker(PHASE_SHOOTING, attacker_owner)
    log, dice, dec = Log(), RecordingDice(), DecisionManager()
    sc = ShootingController(
        dice_manager=dice, turn_tracker=tt, all_tokens=state.tokens,
        decision_manager=dec, game_log=log, obstacles=[], **controller_kwargs,
    )
    return dict(state=state, attacker=attacker, target=target, shooting=sc,
                dice=dice, decision=dec, log=log, turn=tt)


# ------------------------------------------------------------- decisions

def options_of(decision_manager):
    """Option LABELS of the pending decision ([] if none) - remember the
    options themselves are dicts."""
    return [o["label"] for o in decision_manager.options] if decision_manager.is_pending else []


def pick_option(decision_manager, needle):
    """Choose the first pending option whose label contains `needle`
    (case-insensitive). Returns True if something was chosen - a caller that
    expects an option to exist should assert on that, since a missing option
    is exactly what a regression looks like."""
    if not decision_manager.is_pending:
        return False
    for i, option in enumerate(decision_manager.options):
        if needle.lower() in option["label"].lower():
            decision_manager.choose(i)
            return True
    return False


# ------------------------------------------------------- army lists by faction

def list_key(faction_keyword):
    """The key of a shipped army list for this faction, for a suite that needs
    ONE to stage a scene with.

    Ask for a faction, do not name a key. A suite that says "death_guard"
    breaks when that list is renamed, retired or replaced - and it breaks as a
    SystemExit out of army_lists.get(), which is a crash rather than a
    diagnosable red line. Measured when the Prototypes list was retired: ten
    suites went red, and most of them did not care WHICH list they got, only
    that it was of the right faction.

    A faction with no list at all raises here, loudly and by name: that is a
    real change to what the build ships, and it should stop the suite rather
    than let it quietly measure nothing.
    """
    from game import army_lists
    lists = army_lists.lists_for(faction_keyword)
    if not lists:
        known = sorted({e.faction_keyword for e in army_lists.ARMY_LISTS})
        raise SystemExit(
            "no shipped army list for %r - this build fields %s"
            % (faction_keyword, ", ".join(known))
        )
    return lists[0].key
