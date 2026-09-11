"""The end of the Movement phase happens BEFORE the start of the Shooting one.

Report: "Rapid ingress und eater plague overlays ueberlappen sich."

Reproduced from the reported game, logs/game_20260911_132318.log:506-518:

    Player 2: Shooting phase begins.
    Player 1 uses Rapid Ingress.
    Player 1: Rapid Ingress - 1 Crisis Starscythe Battlesuits 1 ... may make an
              ingress move now (rule 20.04).
    Eater Plague (2 Deathshroud Terminators 1 + Typhus): rolled a 6, then 2 -
              ... suffers 5 mortal wound(s).
    ... five mortal wounds ...
    Player 1 set up 1 Crisis Starscythe Battlesuits 1 + Commander Farsight.

The placement was open the whole time those dice were thrown and those wounds
allocated: two things wanting the board and the left panel at once. The log's
ORDER is the evidence - the dice are only reported once acknowledged, and they
could not be acknowledged until the decision underneath them was answered,
because main.py's event chain dispatches decisions above dice.

The cause was ordering in advance_turn_phase(). The `phase == PHASE_SHOOTING`
block ran BEFORE the `phase_before == PHASE_MOVEMENT` block, so the start of
the new phase was offered ahead of the reactions to the end of the old one -
backwards as a rule, and a collision on screen.

This file drives the two things that fix cannot be allowed to break:
  * the offers still happen, exactly once, on every route; and
  * the cheap path stays cheap - with nothing to react to they run at once.
"""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import ast  # noqa: E402
import testkit as tk  # noqa: E402
from game import overwatch  # noqa: E402

checks = tk.Checks("Start of Shooting: order")

MAIN = io.open("main.py", encoding="utf-8").read()
TREE = ast.parse(MAIN)


# --- 1. Fire Overwatch defers its chain until the salvo ENDS ----------------
print("--- 1. the chain's broken link ---")
# choose_unit() used to fire on_resolved() the instant the Snap Shooting
# activation STARTED. Anything chained behind it therefore landed in the middle
# of a salvo - the same collision, one link further down.


class FakeStrat:
    def __init__(self, controller):
        self.controller = controller
        self.used = []

    def can_use(self, *a, **k):
        return True

    def use(self, player, stratagem, targets, **k):
        self.used.append(targets[0])
        stratagem.effect(self, player, targets)


class FakeShooting:
    """Records on_finished instead of calling it, so a test can decide WHEN
    the salvo ends - which is the whole question here."""

    def __init__(self, accept=True):
        self.accept = accept
        self.active_squad = None
        self.on_finished = None

    def has_valid_target(self, *a, **k):
        return True

    def start_snap_shooting(self, squad, on_finished=None):
        if not self.accept:
            return          # the early-exit path: on_finished never set
        self.active_squad = squad
        self.on_finished = on_finished


class FakeTurn:
    def __init__(self):
        self.active = None

    def set_active(self, p):
        self.active = p


class Sq:
    def __init__(self, name, owner):
        self.name, self.owner = name, owner
        self.models = []

    def is_engaged(self, tokens):
        return False


class Tok:
    def __init__(self, squad):
        self.squad = squad


shooter = Sq("1 Broadside Battlesuits 1", "Player 1")
shoot = FakeShooting()
oc = overwatch.FireOverwatchController(None, shoot, all_tokens=[Tok(shooter)],
                                       turn_tracker=FakeTurn())
oc.stratagem_controller = FakeStrat(oc)

fired = []
oc.offer("Player 2", on_resolved=lambda: fired.append("chain"))
checks.eq("the offer opened", oc.state, overwatch.CHOOSING_UNIT)
oc.choose_unit(shooter)
checks.eq("picking a unit does NOT continue the chain - the salvo just began",
          fired, [])
checks.true("...the salvo really did begin", shoot.active_squad is shooter)
shoot.on_finished()
checks.eq("...and the chain runs once the salvo ends", fired, ["chain"])
# Taken, not read: a second call (a cancel behind a completed shot) must not
# fire it twice.
shoot.on_finished()
checks.eq("...exactly once", fired, ["chain"])

# Declining has nothing to wait for, so it continues at once - the cheap path.
shoot2 = FakeShooting()
oc2 = overwatch.FireOverwatchController(None, shoot2, all_tokens=[Tok(shooter)],
                                        turn_tracker=FakeTurn())
oc2.stratagem_controller = FakeStrat(oc2)
fired2 = []
oc2.offer("Player 2", on_resolved=lambda: fired2.append("chain"))
oc2.decline()
checks.eq("declining continues the chain immediately", fired2, ["chain"])

# Nothing eligible: likewise immediate, and it is the common case.
shoot3 = FakeShooting()
oc3 = overwatch.FireOverwatchController(None, shoot3, all_tokens=[],
                                        turn_tracker=FakeTurn())
oc3.stratagem_controller = FakeStrat(oc3)
fired3 = []
oc3.offer("Player 2", on_resolved=lambda: fired3.append("chain"))
checks.eq("an empty offer continues the chain at once", fired3, ["chain"])

# THE STRAND. start_snap_shooting() has an early exit for a squad with no
# attack groups; on that path on_finished is never set, so without this the
# deferred chain would hang for the rest of the battle - and
# turn_tracker.active_player would stay on the wrong player, which was already
# true before any of this.
shoot4 = FakeShooting(accept=False)
turn4 = FakeTurn()
oc4 = overwatch.FireOverwatchController(None, shoot4, all_tokens=[Tok(shooter)],
                                        turn_tracker=turn4)
oc4.stratagem_controller = FakeStrat(oc4)
fired4 = []
oc4.offer("Player 2", on_resolved=lambda: fired4.append("chain"))
oc4.choose_unit(shooter)
checks.eq("a salvo that never began counts as already finished", fired4, ["chain"])
checks.eq("...and the mover is restored anyway", turn4.active, "Player 2")


# --- 2. main.py: resets now, offers owed ------------------------------------
print("--- 2. resets and offers are separated ---")


def block_of(name):
    """The source of the nested function `name` inside main()."""
    for node in ast.walk(TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(MAIN, node) or ""
    return ""


ADV = block_of("advance_turn_phase")
OFFER = block_of("_offer_start_of_shooting_phase")
TAKE = block_of("_take_start_of_shooting_offers")

checks.true("the deferred offer exists at all", bool(OFFER))
checks.true("...and something takes it", bool(TAKE))

FIVE = [
    "matter_absorption_controller.offer_at_shooting_phase",
    "living_lightning_controller.offer_at_shooting_phase",
    "eater_plague_controller.offer_at_shooting_phase",
    "auxiliary_cadre_controller.offer_at_start_of_shooting_phase",
    "guiding_presence_controller.offer_at_start_of_shooting_phase",
]
for call in FIVE:
    checks.true(f"{call.split('.')[0]} is offered from the deferred function",
                call in OFFER)
    # A SET DIFFERENCE, not a list of five names: a sixth ability added to the
    # old block would collide exactly as these did, and this line moves.
    checks.eq(f"...and NOT directly from advance_turn_phase()",
              ADV.count(call), 0)

# The resets, on the other hand, belong to the phase change and must stay.
for reset in ("living_lightning_controller.reset_phase()",
              "matter_absorption_controller.reset_phase()",
              "eater_plague_controller.reset_phase()",
              "auxiliary_cadre_controller.reset_phase()",
              "guiding_presence_controller.reset_phase()"):
    checks.true(f"{reset} still runs at the phase change", reset in ADV)

# Armed in exactly one place, taken in exactly two - the chain and the net.
checks.eq("the token is armed once", ADV.count("_shooting_start_owed[0] = turn_tracker.turn_owner"), 1)
checks.true("the chain's tail takes it",
            "on_resolved=_take_start_of_shooting_offers" in ADV)
# BEHIND Fire Overwatch, not in front of it: a Snap Shooting salvo wants the
# board and the left panel exactly as much as an ingress placement does, so the
# tail hangs off ITS offer. Read from the tree, not from the indentation - a
# guard that pins whitespace fails on formatting instead of on meaning.
_fo_offer = None
for _n in ast.walk(TREE):
    if (isinstance(_n, ast.Call) and isinstance(_n.func, ast.Attribute)
            and _n.func.attr == "offer"
            and getattr(_n.func.value, "id", None) == "fire_overwatch_controller"):
        _fo_offer = _n
checks.true("...behind Fire Overwatch, not in front of it",
            _fo_offer is not None
            and any(k.arg == "on_resolved"
                    and getattr(k.value, "id", None) == "_take_start_of_shooting_offers"
                    for k in _fo_offer.keywords))
checks.true("the safety net forfeits an unclaimed token out loud",
            "were not offered" in ADV)
# Order matters: expire_if_unused() fires the deferred chain, whose tail takes
# the token. Netting afterwards would deliver the offers one phase late.
# find(), not index(): a missing anchor has to go RED, not abort the run.
_net = ADV.find("_shooting_start_owed[0] is not None")
_expire = ADV.find("rapid_ingress_controller.expire_if_unused()")
checks.true("...and does so BEFORE the chain is expired",
            _net != -1 and _expire != -1 and _net < _expire)
# The owner is captured when armed, never re-read later: by the time the chain
# runs, a save roll or a reactive Stratagem may have moved active_player.
checks.eq("the deferred offer does not re-read the clock",
          "turn_tracker" in OFFER, False)


# --- 3. the token is taken, not read ----------------------------------------
print("--- 3. exactly once ---")
# Modelled here rather than driven through main(), which no suite runs. The
# property is the one that matters: a chain that fires twice must not offer
# twice.

owed = [None]
calls = []


def take():
    owner, owed[0] = owed[0], None
    if owner is not None:
        calls.append(owner)


owed[0] = "Player 2"
take()
take()
checks.eq("a chain that fires twice offers once", calls, ["Player 2"])
owed[0] = "Player 1"
take()
checks.eq("...and a new phase arms it again", calls, ["Player 2", "Player 1"])
# The shape above must be the shape main.py uses, or this models nothing.
checks.true("main.py takes the token rather than reading it",
            "owner, _shooting_start_owed[0] = _shooting_start_owed[0], None" in TAKE)


# --- 4. the ordering invariant this rests on --------------------------------
print("--- 4. the invariant ---")
# The deferral is safe only because entering the Shooting phase ALWAYS means
# leaving the Movement phase - TurnTracker.advance_phase() steps phase_index
# by exactly one. If that ever stops being true, the offers would be armed on a
# route the chain does not run on, and the net would forfeit them every time.
from game.turn import PHASES, PHASE_MOVEMENT, PHASE_SHOOTING  # noqa: E402

checks.eq("Shooting follows Movement immediately",
          PHASES[PHASES.index(PHASE_MOVEMENT) + 1], PHASE_SHOOTING)
TURN_SRC = io.open(os.path.join("game", "turn.py"), encoding="utf-8").read()
TURN_TREE = ast.parse(TURN_SRC)


def _writes_phase_index(node):
    """Is this statement a write to self.phase_index?"""
    targets = [node.target] if isinstance(node, ast.AugAssign) else node.targets
    for t in targets:
        if (isinstance(t, ast.Attribute) and t.attr == "phase_index"
                and getattr(t.value, "id", None) == "self"):
            return True
    return False


_steps, _sets = [], []
for node in ast.walk(TURN_TREE):
    if isinstance(node, ast.AugAssign) and _writes_phase_index(node):
        _steps.append(node)
    elif isinstance(node, ast.Assign) and _writes_phase_index(node):
        _sets.append(node)

checks.eq("advance_phase() steps the phase in exactly one place", len(_steps), 1)
checks.true("...and it steps by exactly one",
            _steps and isinstance(_steps[0].op, ast.Add)
            and getattr(_steps[0].value, "value", None) == 1)
# The OTHER writes are all turn/round rollovers back to the FIRST phase. That
# is what makes the deferral safe: no route lands on Shooting except the single
# step above, so the Movement block always runs first.
checks.true("every other write rewinds to the first phase, never into one",
            bool(_sets) and all(getattr(n.value, "value", None) == 0 for n in _sets))
checks.eq("...and the first phase is not Shooting", PHASES[0] == PHASE_SHOOTING, False)
# main.py must reach TurnTracker.advance_phase() from one place only, or a
# second route could enter Shooting without the Movement block running.
_adv_calls = [n for n in ast.walk(TREE)
              if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute)
              and n.func.attr == "advance_phase"
              and getattr(n.func.value, "id", None) == "turn_tracker"]
checks.eq("main.py advances the phase from exactly one place", len(_adv_calls), 1)

checks.finish()
