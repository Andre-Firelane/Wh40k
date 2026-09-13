"""A reactive shooting activation has to OPEN - and has to survive opening.

User report, crash in a real game (necrons_hypercrypt, the Hexmark Destroyer's
Multi-threat Eliminator answering an AI unit that shot a friendly unit):

    reactive_bodyguard_shooting.py, on_squad_finished_shooting
        return self.shooting_controller.start_reactive_shooting(reactor, restrict_to=attacker)
    shooting.py, start_reactive_shooting
        self._restrict_targets_to = list(restrict_to) if restrict_to else None
    TypeError: 'Squad' object is not iterable

TWO DEFECTS, the second hidden behind the first.

  1. ONE CONTRACT, TWO READINGS, BOTH SHIPPED. Vengeful Stars and Vaul's
     Vengeance pass restrict_to=[killer]; Kroot Packmates, Multi-threat
     Eliminator and Hyperspace Hunters pass the unit itself. The driver now
     honours both (pregame.Resume's precedent: a contract only a comment
     holds is not one).

  2. STARTED INSIDE THE LOOP THAT CLOSES THE ATTACKER'S ACTIVATION, THE NEW
     ACTIVATION WAS WIPED. "After that enemy unit has finished making its
     attacks" is answered from on_squad_finished_shooting, i.e. from inside
     _actually_finish_squad() - which clears active_squad/state right after
     the loop. Reproduced with the TypeError bypassed: the Hexmark's
     activation was gone the instant it opened, and the NEXT listener was
     handed the Hexmark as "the unit that just shot". That hit Vaul's
     Vengeance (a list caller) exactly as hard.

WHY NO SUITE SAW EITHER. test_necron_destroyer_cult.py,
test_necron_rank_and_file.py and test_tau_kroot_and_vespid.py drive the three
callers against STUBS that accept whatever restrict_to they are given, and no
suite ran a reactive start through _actually_finish_squad(). Everything below
therefore uses the REAL ShootingController, and sections 2-4 go through the
real funnel the traceback went through.

Every controller call is wrapped (`safe`): with a fix removed, a check has to
go RED and name what broke - an aborted run says nothing about which assurance
failed.
"""

import testkit as tk
from testkit import Checks

from game import multi_threat_eliminator
from game.decision import DecisionManager
from game.factions import aeldari
from game.factions import necrons as nec
from game.factions import tau_empire as tau
from game.game_state import GameState
from game.guardian_vauls_vengeance import VaulsVengeanceController
from game.hyperspace_hunters import HyperspaceHuntersController
from game.kroot_packmates import KrootPackmatesController
from game import shooting as shooting_mod
from game.turn import PHASE_SHOOTING

checks = Checks("reactive shooting start")


def safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:                      # noqa: BLE001 - see docstring
        return None, "%s: %s" % (type(exc).__name__, exc)


def name_of(squad):
    return getattr(squad, "name", None)


def restrict_names(sc):
    return [getattr(s, "name", repr(s)) for s in (sc._restrict_targets_to or [])]


def board(*placed):
    """placed: (datasheet, owner, name, x, y). Returns (state, squads...)."""
    state = GameState()
    squads = []
    for sheet, owner, name, x, y in placed:
        squad = tk.build(sheet, owner, name=name)
        tk.line_up(squad, x=x, y=y)
        for model in squad.models:
            state.add_token(model)
        squads.append(squad)
    return (state, *squads)


def controller(state, owner="Player 2"):
    return shooting_mod.ShootingController(
        dice_manager=tk.RecordingDice(), turn_tracker=tk._tracker(PHASE_SHOOTING, owner),
        all_tokens=state.tokens, decision_manager=DecisionManager(),
        game_log=tk.Log(), obstacles=[])


def valid_target_names(sc, state):
    got, err = safe(sc.valid_target_models, state.tokens)
    if err:
        return ["<%s>" % err]
    return sorted({t.squad.name for t in got if t.squad is not None})


def open_and_close_attacker(sc, attacker):
    """The attacker's activation, opened for real and closed through the
    funnel the traceback went through."""
    safe(sc.start_shooting, attacker)
    staged = sc.active_squad is attacker
    _, err = safe(sc._actually_finish_squad)
    return staged, err


# =========================================================================
# 1. The driver accepts BOTH readings - outside any closing activation
# =========================================================================
print("--- 1. one unit or a list ---")

for label, form in (("a bare unit", lambda a: a), ("a list", lambda a: [a]),
                    ("a tuple", lambda a: (a,))):
    state, hexmark, target, other = board(
        (nec.HEXMARK_DESTROYER, "Player 1", "1 Hexmark", 20.0, 20.0),
        (nec.IMMORTALS, "Player 2", "2 Target", 20.0, 26.0),
        (nec.IMMORTALS, "Player 2", "2 Other", 27.0, 26.0))
    sc = controller(state)
    started, err = safe(sc.start_reactive_shooting, hexmark, restrict_to=form(target))
    checks.eq("restrict_to as %s does not raise" % label, err, None)
    checks.eq("...it opens (returns True)", started, True)
    checks.eq("...on the reactor", name_of(sc.active_squad), hexmark.name)
    checks.eq("...waiting for a target", sc.state, shooting_mod.CHOOSING_TARGET)
    checks.eq("...restricted to exactly that unit", restrict_names(sc), [target.name])
    checks.eq("...so only it is offered on the board", valid_target_names(sc, state),
              [target.name])

# Liveness for the line above: unrestricted, BOTH are legal targets - so the
# restriction, not range or sight, is what removed "2 Other".
state, hexmark, target, other = board(
    (nec.HEXMARK_DESTROYER, "Player 1", "1 Hexmark", 20.0, 20.0),
    (nec.IMMORTALS, "Player 2", "2 Target", 20.0, 26.0),
    (nec.IMMORTALS, "Player 2", "2 Other", 27.0, 26.0))
sc = controller(state)
started, err = safe(sc.start_reactive_shooting, hexmark)
checks.eq("unrestricted (None) opens too", (started, err), (True, None))
checks.eq("...with no restriction", sc._restrict_targets_to, None)
checks.eq("...and then both enemy units are legal targets (liveness)",
          valid_target_names(sc, state), [other.name, target.name])

empty = tk.build(nec.IMMORTALS, "Player 1", name="1 Unarmed")
for m in empty.models:
    m.weapons = []
sc = controller(GameState())
checks.eq("a unit with nothing to shoot with does not open (returns False)",
          safe(sc.start_reactive_shooting, empty, restrict_to=target), (False, None))
checks.eq("...and leaves the controller idle", sc.active_squad, None)

# Weapons, but no shooting TYPE open right now (engaged without a pistol, say):
# refused AND left idle. A unit left in active_squad reads as a foreign
# activation to ai/agent_driver.py's gate, which would wait on it forever, and a
# queued start failing there would stop the queue behind it.
# available_shooting_types is stubbed for this one call - what is measured is
# the refusal, not the rule that produced it.
state, hexmark, target = board(
    (nec.HEXMARK_DESTROYER, "Player 1", "1 Hexmark", 20.0, 20.0),
    (nec.IMMORTALS, "Player 2", "2 Target", 20.0, 26.0))
sc = controller(state)
_real_types = shooting_mod.available_shooting_types
shooting_mod.available_shooting_types = lambda *a, **k: []
try:
    got = safe(sc.start_reactive_shooting, hexmark, restrict_to=target)
finally:
    shooting_mod.available_shooting_types = _real_types
checks.eq("a unit with no shooting type open does not open (returns False)",
          got, (False, None))
checks.eq("...and leaves NO unit in active_squad (the AI's gate would wait on it)",
          name_of(sc.active_squad), None)
checks.true("...nor a reactive flag or a restriction behind",
            not sc._reactive and sc._restrict_targets_to is None)


# =========================================================================
# 2. THE REPORT: Multi-threat Eliminator through _actually_finish_squad()
# =========================================================================
print("--- 2. Multi-threat Eliminator, end to end ---")

state, hexmark, friend, enemy = board(
    (nec.HEXMARK_DESTROYER, "Player 1", "1 Hexmark", 20.0, 20.0),
    (nec.IMMORTALS, "Player 1", "1 Friend", 22.0, 20.0),
    (nec.IMMORTALS, "Player 2", "2 Shooter", 20.0, 28.0))
sc = controller(state)
mte = multi_threat_eliminator.MultiThreatEliminatorController(
    shooting_controller=sc, game_state=state, turn_tracker=sc.turn_tracker,
    auto_players=("Player 1",))
seen = []
sc.on_squad_finished_shooting.append(mte.on_squad_finished_shooting)
sc.on_squad_finished_shooting.append(lambda sq, hits: seen.append(name_of(sq)))

offered, _ = safe(mte.maybe_offer, enemy, friend)
checks.true("stage: the Hexmark reacts to its friend being shot", offered)
staged, err = open_and_close_attacker(sc, enemy)
checks.true("stage: the shooter's activation really was open", staged)
checks.eq("closing the shooter's activation does NOT crash (the report)", err, None)
checks.eq("...the Hexmark's activation is OPEN afterwards, not wiped",
          name_of(sc.active_squad), hexmark.name)
checks.eq("...waiting for its target", sc.state, shooting_mod.CHOOSING_TARGET)
checks.true("...as a reactive activation", sc._reactive)
checks.eq("...restricted to the unit that shot", restrict_names(sc), [enemy.name])
checks.eq("...which is the one unit offered", valid_target_names(sc, state), [enemy.name])
checks.eq("a LATER listener was handed the SHOOTER, not the reactor", seen, [enemy.name])
checks.true("the shooter's own activation was booked as shot",
            enemy in sc.shot_squad_ids)
checks.true("...the Hexmark's was not (it has not shot yet)",
            hexmark not in sc.shot_squad_ids)
checks.true("rule 13.09's ranged-attack record names the shooter",
            enemy in sc.last_ranged_attack_turn)
checks.true("...and not the reactor", hexmark not in sc.last_ranged_attack_turn)

safe(sc.cancel)
checks.eq("ending the Hexmark's activation leaves the controller idle",
          sc.active_squad, None)
checks.eq("...and, being reactive, fires no after-shooting listener", seen, [enemy.name])


# =========================================================================
# 3. Kroot Packmates - the other carrier of the same base class
# =========================================================================
print("--- 3. Kroot Packmates, end to end ---")

state, krootox, carnivores, strike = board(
    (tau.KROOTOX_RIDERS, "Player 1", "1 Krootox", 20.0, 20.0),
    (tau.KROOT_CARNIVORES, "Player 1", "1 Carnivores", 23.0, 20.0),
    (tau.STRIKE_TEAM, "Player 2", "2 Strike Team", 20.0, 30.0))
sc = controller(state)
packmates = KrootPackmatesController(
    shooting_controller=sc, game_state=state, turn_tracker=sc.turn_tracker,
    auto_players=("Player 1",))
seen = []
sc.on_squad_finished_shooting.append(packmates.on_squad_finished_shooting)
sc.on_squad_finished_shooting.append(lambda sq, hits: seen.append(name_of(sq)))

offered, _ = safe(packmates.maybe_offer, strike, carnivores)
checks.true("stage: the Krootox react to the Carnivores being shot", offered)
staged, err = open_and_close_attacker(sc, strike)
checks.true("stage: the Strike Team's activation really was open", staged)
checks.eq("closing it does not crash", err, None)
checks.eq("...the Krootox activation is open", name_of(sc.active_squad), krootox.name)
checks.eq("...restricted to the Strike Team", restrict_names(sc), [strike.name])
checks.eq("...and the later listener saw the Strike Team", seen, [strike.name])


# =========================================================================
# 4. Vaul's Vengeance - a LIST caller, and it was wiped just the same
# =========================================================================
print("--- 4. Vaul's Vengeance, end to end ---")

state, walkers, killer = board(
    (aeldari.WAR_WALKERS, "Player 1", "1 War Walkers", 20.0, 20.0),
    (nec.IMMORTALS, "Player 2", "2 Killer", 20.0, 30.0))
sc = controller(state)
vv = VaulsVengeanceController(None, shooting_controller=sc, game_state=state,
                              turn_tracker=sc.turn_tracker)
vv._pending["Player 1"] = (walkers, killer)
sc.on_squad_finished_shooting.append(lambda sq, hits: vv.on_attacker_finished(sq))
staged, err = open_and_close_attacker(sc, killer)
checks.true("stage: the killer's activation really was open", staged)
checks.eq("closing it does not crash", err, None)
checks.eq("...the War Walkers activation is OPEN, not wiped",
          name_of(sc.active_squad), walkers.name)
checks.eq("...restricted to the killer", restrict_names(sc), [killer.name])


# =========================================================================
# 5. Hyperspace Hunters - the third bare-unit caller, OUTSIDE the loop
# =========================================================================
print("--- 5. Hyperspace Hunters opens at once ---")


class _Ingress:
    def __init__(self, arrived):
        self.ingressed_this_turn = set(arrived)


state, deathmarks, arrival = board(
    (nec.DEATHMARKS, "Player 1", "1 Deathmarks", 20.0, 20.0),
    (nec.IMMORTALS, "Player 2", "2 Arrival", 20.0, 32.0))
sc = controller(state)
hh = HyperspaceHuntersController(shooting_controller=sc,
                                 ingress_controller=_Ingress([arrival]),
                                 all_tokens=state.tokens, auto_players=("Player 1",))
got, err = safe(hh.offer_on_arrival, arrival, phase_owner="Player 2")
checks.eq("an arrival hunted by Deathmarks does not crash", err, None)
checks.true("...and reports that it fired", got)
checks.eq("...the Deathmarks activation is open", name_of(sc.active_squad), deathmarks.name)
checks.eq("...restricted to the arriving unit", restrict_names(sc), [arrival.name])


# =========================================================================
# 6. Several reactions owed to ONE attack: one at a time, none lost
# =========================================================================
print("--- 6. queued in the order owed ---")

state, r1, r2, r3, shooter = board(
    (nec.HEXMARK_DESTROYER, "Player 1", "1 First", 20.0, 20.0),
    (nec.HEXMARK_DESTROYER, "Player 1", "1 Second", 24.0, 20.0),
    (nec.HEXMARK_DESTROYER, "Player 1", "1 Third", 28.0, 20.0),
    (nec.IMMORTALS, "Player 2", "2 Shooter", 20.0, 28.0))
sc = controller(state)
finished = []
for reactor in (r1, r2, r3):
    sc.on_squad_finished_shooting.append(
        lambda sq, hits, r=reactor: sc.start_reactive_shooting(
            r, restrict_to=[sq], on_finished=lambda r=r: finished.append(r.name)))
staged, err = open_and_close_attacker(sc, shooter)
checks.eq("three reactions in one loop do not crash", err, None)
checks.eq("...the FIRST owed opens first", name_of(sc.active_squad), r1.name)
checks.eq("...the rest wait", [name_of(s) for s, _, _ in sc._deferred_reactive],
          [r2.name, r3.name])
for m in r2.models:
    m.current_wounds = 0                      # dies before its turn comes
safe(sc.cancel)
checks.eq("the first one's own completion callback fired", finished, [r1.name])
checks.eq("a queued unit with no living model is SKIPPED, not left blocking",
          name_of(sc.active_squad), r3.name)
checks.eq("...and the next opens with its own restriction", restrict_names(sc),
          [shooter.name])
safe(sc.cancel)
checks.eq("the last closes cleanly", (name_of(sc.active_squad), finished),
          (None, [r1.name, r3.name]))
checks.eq("...leaving nothing queued", sc._deferred_reactive, [])
checks.true("...and the closing flag down", not sc._closing_activation)


# =========================================================================
# 7. The closing flag cannot stick
# =========================================================================
print("--- 7. the flag always comes down ---")

state, shooter, hexmark = board(
    (nec.IMMORTALS, "Player 2", "2 Shooter", 20.0, 28.0),
    (nec.HEXMARK_DESTROYER, "Player 1", "1 Hexmark", 20.0, 20.0))
sc = controller(state)


def _boom(sq, hits):
    raise RuntimeError("a listener that raises")


sc.on_squad_finished_shooting.append(_boom)
_, err = open_and_close_attacker(sc, shooter)
checks.true("stage: the raising listener really raised", err is not None)
checks.true("...and the closing flag still came down", not sc._closing_activation)
started, err = safe(sc.start_reactive_shooting, hexmark, restrict_to=shooter)
checks.eq("...so a later reactive start opens at once instead of queueing forever",
          (started, err, name_of(sc.active_squad)), (True, None, hexmark.name))


# =========================================================================
# 7b. An activation ENDED from inside the loop must not spin the queue
# =========================================================================
# Found by this suite's own A/B run, which HUNG: a listener that ends the
# closing activation itself (cancel() from inside the walk) reaches
# _finish_activation() while _closing_activation is still up, so the drain
# popped a queued start, the start re-queued it - the flag being up - and the
# while loop never ended. No listener does that today; the guard costs one
# line and a hang has no error message. Run in a DAEMON thread with a join
# timeout, so the regression goes red here instead of hanging the suite.
print("--- 7b. no drain while the loop is still walking ---")

import threading                                             # noqa: E402

state, shooter, hexmark = board(
    (nec.IMMORTALS, "Player 2", "2 Shooter", 20.0, 28.0),
    (nec.HEXMARK_DESTROYER, "Player 1", "1 Hexmark", 20.0, 20.0))
sc = controller(state)
sc.on_squad_finished_shooting.append(
    lambda sq, hits: sc.start_reactive_shooting(hexmark, restrict_to=[sq]))
sc.on_squad_finished_shooting.append(lambda sq, hits: sc.cancel())
outcome = {}


def _close():
    outcome["result"] = open_and_close_attacker(sc, shooter)


worker = threading.Thread(target=_close, daemon=True)
worker.start()
worker.join(timeout=10.0)
checks.true("closing an activation that a listener cancels mid-walk RETURNS (no endless drain)",
            not worker.is_alive())
if not worker.is_alive():
    checks.eq("...without an error", outcome["result"][1], None)
    checks.eq("...and the reaction owed during the walk still opens afterwards",
              name_of(sc.active_squad), hexmark.name)

checks.finish()
