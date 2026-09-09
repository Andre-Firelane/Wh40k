"""The charge ladder's retries re-run the declaration reaction chain - and
what that must NOT do (finding F1 of the AI-movement review, 2026-09-09).

ai/agent_driver._run_charge_attempts() re-opens a failed charge move for
every retry through ChargeController.begin_charge_move(), and that runs the
"just after an enemy unit has declared a charge" reaction chain AGAIN each
time - up to thirteen times for one declaration. Two things went wrong with
that, both reproduced at the source before a line was changed:

  1. A reactor without a memo of the declaration it already asked about
     re-prompted the human on every retry. Grav-Inhibitor Field had the memo
     (`_offered_key`); Photon Grenades and Combat Embarkation did not.
     Measured: two prompts for ONE declaration.
  2. Far worse: when a retry's begin_charge_move() was reacted to, the move
     stayed CLOSED and the ladder placed anyway. With no move open,
     clamp_move() hands the wish back and try_commit_segment() accepts
     (game/movement.py) - so all five models of the charging unit were moved
     with no validation at all, and the charge was then declined with the
     second prompt still standing, whose answer resumed a charge that was
     already over.

Both halves are now held: the reactors keep the memo, and the ladder hands
the continuation back (returns None) whenever a retry's reopen did not open
a move - for any reactor that has no memo, and for Combat Embarkation's
re-opened target selection, the one legitimate way a retry ends with no
targets to open a move for.

Real ChargeController / MovementController / StratagemController /
DecisionManager / BattleShockController objects, real datasheets, scripted
dice; the AI half drives the real _handle_charge() with MockAgent.

Run: python test_charge_retry_reactions.py
"""
import io
import os
import re
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import config, dice as dice_mod, maps  # noqa: E402
from game.battle_shock import BattleShockController  # noqa: E402
from game.charge import DECLARING_TARGETS, IDLE, ChargeController  # noqa: E402
from game.command_points import CommandPointManager  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.factions import build_squad  # noqa: E402
from game.factions.orks import BOYZ  # noqa: E402
from game.factions.tau_empire import TAU_EMPIRE  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.kauyon_combat_embarkation import CombatEmbarkationController  # noqa: E402
from game.kauyon_photon_grenades import PhotonGrenadesController  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.stratagems import StratagemController  # noqa: E402
from game.terrain import DENSE, Obstacle  # noqa: E402
from game.turn import PHASES, PHASE_CHARGE, TurnTracker  # noqa: E402
from ai import agent_driver as ad  # noqa: E402
from ai.agent_driver import AIMemory  # noqa: E402
from ai.mock_agent import MockAgent  # noqa: E402
from testkit import Checks  # noqa: E402

# Kauyon must be DECLARED for the two reactors to have a WHEN at all - the
# same precondition every T'au detachment suite sets for itself.
config.KAUYON_PLAYERS = ("Player 1",)
m = maps.get("map2")
maps.apply_to_config(m)
c = Checks("charge retries and the reaction chain")

_scripted = []


def _randint(low, high):
    return _scripted.pop(0) if _scripted else high


dice_mod.random.randint = _randint


def _decline(dec):
    """The Decline option is always the last one. A missing prompt is a RED
    check for the caller, never a crash of the suite."""
    if not dec.is_pending or not dec.options:
        return False
    dec.choose(len(dec.options) - 1)
    return True


def _last_option_is_decline(dec):
    return (dec.options[-1].get("label") or "").lower().startswith("decline")


class _Transport:
    """What Combat Embarkation asks of TransportController, doing to the
    board exactly what the real embark() does (models off the token list,
    coordinates left alone) - the shape test_tau_detachment_stratagems.py
    stages it with."""

    def __init__(self, state):
        self.state = state

    def can_embark(self, squad, token, require_move=True, range_in=None):
        return True

    def embark(self, squad, token, require_move=True, range_in=None):
        for model in list(squad.models):
            if model in self.state.tokens:
                self.state.tokens.remove(model)
        squad.embarked_in = token
        self.state.embarked_squads.append(squad)


def scene(defender_sheet="Strike Team", gap=4.0, dense_box=False, with_transport=False,
          reactors=("photon",)):
    """Player 2's Boyz declare a charge on Player 1's Kauyon unit, `gap`
    inches away. `dense_box` parks the defenders inside a Dense box so that
    every spot within Engagement Range of them has a base overlapping it -
    every approach then fails on 13.05 while the roll itself reaches."""
    st = GameState()
    charging = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
    charging.models = charging.models[:5]
    defender = build_squad(TAU_EMPIRE.datasheets[defender_sheet], "Player 1", name="1 Defender 1")
    for i, mdl in enumerate(charging.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.4, 20.0
        st.add_token(mdl)
    for i, mdl in enumerate(defender.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.2, 20.0 + gap
        st.add_token(mdl)
    ride = None
    if with_transport:
        ride = build_squad(TAU_EMPIRE.datasheets["Devilfish"], "Player 1", name="1 Devilfish 1")
        ride.models[0].x_in, ride.models[0].y_in = 30.0, 20.0 + gap + 2.5
        st.add_token(ride.models[0])
    if dense_box:
        st.obstacles.append(Obstacle(24.0, 20.0 + gap + 0.4, 20.0, 6.2, DENSE))
    tt = TurnTracker()
    tt.started = True
    tt.battle_round = 2
    tt.phase_index = PHASES.index(PHASE_CHARGE)
    tt.turn_owner = tt.active_player = "Player 2"
    cps = CommandPointManager()
    cps.cp["Player 1"] = cps.cp["Player 2"] = 3
    strat = StratagemController(command_points=cps)
    dm = DiceManager()
    dec = DecisionManager()
    mc = MovementController(all_tokens=st.tokens, obstacles=st.obstacles, turn_tracker=tt,
                            board_width_in=m.width_in, board_height_in=m.height_in)
    bs = BattleShockController(dice_manager=dm, turn_tracker=tt)
    cc = ChargeController(dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens, movement_controller=mc)
    photon = embark = None
    if "photon" in reactors:
        photon = PhotonGrenadesController(strat, turn_tracker=tt, all_tokens=st.tokens,
                                          battle_shock_controller=bs, decision_manager=dec,
                                          auto_players=("Player 2",))
        cc.charge_declaration_reactions.append(photon.maybe_offer)
    if "embark" in reactors:
        embark = CombatEmbarkationController(strat, transport_controller=_Transport(st),
                                             turn_tracker=tt, all_tokens=st.tokens,
                                             decision_manager=dec, auto_players=("Player 2",),
                                             charge_controller=cc)
        cc.charge_declaration_reactions.append(embark.maybe_offer)
    return dict(state=st, charging=charging, defender=defender, ride=ride, turn=tt, cps=cps,
                strat=strat, dice=dm, decision=dec, movement=mc, shock=bs, charge=cc,
                photon=photon, embark=embark)


def declare(sc, roll=(2, 2), charging=None, target=None):
    """A real declaration up to (not through) the move; returns max_distance."""
    charging = charging or sc["charging"]
    _scripted[:] = list(roll)
    sc["charge"].declare_charge(charging)
    sc["dice"].acknowledge()
    sc["charge"].on_dice_acknowledged()
    sc["charge"].toggle_charge_target(target or sc["defender"])
    sc["movement"].selected_squad = charging
    return sc["charge"].max_distance


def retries(sc, n=5):
    """What the ladder does between approaches: cancel, re-open. Counts the
    prompts those re-opens raise (and answers each with Decline)."""
    opened = 0
    for _ in range(n):
        sc["movement"].cancel_move()
        sc["charge"].begin_charge_move()
        if sc["decision"].is_pending:
            opened += 1
            _decline(sc["decision"])
    return opened


# ======================================================== 1. Photon Grenades
print("\n1) Photon Grenades: one declaration, one prompt")
sc = scene()
declare(sc)
sc["charge"].begin_charge_move()
c.true("the offer is opened on the first begin_charge_move()", sc["decision"].is_pending)
c.true("...to the defender", sc["decision"].player == "Player 1")
c.true("...and the last option is Decline", _last_option_is_decline(sc["decision"]))
_decline(sc["decision"])
c.eq("declining opens the charge move", sc["movement"].move_mode, "charge")
c.eq("five retries re-open the move without a single new prompt", retries(sc), 0)
c.eq("the move is open after the last re-open", sc["movement"].move_mode, "charge")

# The memo is about THIS declaration, not about the phase: a different unit
# declaring is a new question, and so is the same unit next battle round.
second = build_squad(BOYZ, "Player 2", name="2 Boyz 2")
second.models = second.models[:3]
for i, mdl in enumerate(second.models):
    mdl.x_in, mdl.y_in = 30.0 + i * 1.4, 20.0
    sc["state"].add_token(mdl)
sc["movement"].cancel_move()
sc["charge"].decline_charge_move()
declare(sc, charging=second)
sc["charge"].begin_charge_move()
c.true("another unit's declaration in the same phase is asked about", sc["decision"].is_pending)
_decline(sc["decision"])
sc["movement"].cancel_move()
sc["charge"].decline_charge_move()
# A new battle round: the phase ledgers turn over (11.01's one charge per
# phase, 15.01's once per phase) exactly as main.py turns them over.
sc["turn"].battle_round += 1
sc["charge"].reset_charge_phase()
sc["strat"].reset_phase()
declare(sc)
sc["charge"].begin_charge_move()
c.true("and the first unit again next battle round", sc["decision"].is_pending)
_decline(sc["decision"])

# USING it is held by rule 15.01, not by the memo - the memo only covers the
# declined case that 15.01's ledger cannot see.
sc = scene()
declare(sc)
sc["charge"].begin_charge_move()
_scripted[:] = [6, 6]  # the Battle-shock test passes
sc["decision"].choose(0)
c.eq("using it spends 1 CP", sc["cps"].cp["Player 1"], 2)
sc["dice"].acknowledge()
sc["shock"].on_dice_acknowledged()
if hasattr(sc["photon"], "on_dice_acknowledged"):
    sc["photon"].on_dice_acknowledged()
c.true("the charge move opens once the sequence is resolved", sc["movement"].move_mode == "charge")
c.eq("and the retries raise nothing either", retries(sc), 0)

# ===================================================== 2. Combat Embarkation
print("\n2) Combat Embarkation: one declaration, one prompt")
sc = scene(defender_sheet="Breacher Team", with_transport=True, reactors=("embark",))
declare(sc)
sc["charge"].begin_charge_move()
c.true("the offer is opened on the first begin_charge_move()", sc["decision"].is_pending)
c.true("...and names the transport", any("Devilfish" in (o.get("label") or "") for o in sc["decision"].options))
_decline(sc["decision"])
c.eq("declining opens the charge move", sc["movement"].move_mode, "charge")
c.eq("five retries re-open the move without a single new prompt", retries(sc), 0)

# Its own effect re-opens target selection, which IS a new declaration - the
# printed "your opponent can select new targets" - and is asked about again.
sc = scene(defender_sheet="Breacher Team", with_transport=True, reactors=("embark",))
declare(sc)
sc["charge"].begin_charge_move()
ei = next(i for i, o in enumerate(sc["decision"].options) if o.get("squad") is not None)
sc["decision"].choose(ei)
c.true("boarding the transport takes the unit off the board", sc["defender"].embarked_in is not None)
c.eq("...and empties the declared targets", list(sc["charge"].charge_targets), [])
c.eq("the charge move did NOT open (nothing to charge)", sc["movement"].move_mode, None)
c.eq("the declaration is still standing for new targets", sc["charge"].state, DECLARING_TARGETS)

# ====================================== 3. the AI's ladder end to end (real path)
print("\n3) the AI's charge ladder: the human is asked once, nothing moves without a move")


def spy_commits(sc):
    """Every segment committed while no charge move is open - the placement
    that must never happen."""
    hits = []
    real = sc["movement"].try_commit_segment

    def commit(model, *a, **k):
        ok = real(model, *a, **k)
        if ok and sc["movement"].move_mode != "charge":
            hits.append(model.id)
        return ok

    sc["movement"].try_commit_segment = commit
    return hits


def drive(sc, answer=True):
    """One take_one_action() worth of _handle_charge, then the human's answer
    if a prompt came up. Returns (acted, prompted)."""
    acted = ad._handle_charge(MockAgent(), AIMemory(), "Player 2", sc["state"].tokens,
                              sc["charge"], sc["movement"], None)
    prompted = sc["decision"].is_pending
    if prompted and answer:
        _decline(sc["decision"])
    return acted, prompted


sc = scene(dense_box=True)
dist = declare(sc)
origin = [(round(mo.x_in, 2), round(mo.y_in, 2)) for mo in sc["charging"].models]
hits = spy_commits(sc)
acted, prompted = drive(sc)
c.true("the first attempt defers behind the offer", acted and prompted)
c.eq("...with the charge move open once the human declined", sc["movement"].move_mode, "charge")
acted, prompted2 = drive(sc)
c.true("the retries then run to a conclusion without a second prompt", acted and not prompted2)
c.eq("no segment was committed without a charge move open", hits, [])
c.eq("no model was moved by a rejected charge", [(round(mo.x_in, 2), round(mo.y_in, 2)) for mo in sc["charging"].models], origin)
c.eq("the charge concluded (declined - every approach fails on 13.05)", sc["charge"].state, IDLE)
c.true("nothing is pending for the human afterwards", not sc["decision"].is_pending)

# ============================== 4. the ladder's guard, with a memo-LESS reactor
print("\n4) the guard alone: a reactor with no memo defers the retry instead of placing blind")


class _NoMemoReactor:
    """Prompts on its first `times` calls, like a reactor written without the
    memo would - then falls silent so the charge can conclude."""

    def __init__(self, dec, times=2):
        self.dec, self.times, self.calls = dec, times, 0

    def maybe_offer(self, charging, targets, on_resolved=None):
        self.calls += 1
        if self.calls > self.times:
            return False
        self.dec.request("Player 1", f"stub reaction #{self.calls}",
                         [("Decline", lambda: on_resolved() if on_resolved else None)])
        return True


sc = scene(dense_box=True, reactors=())
stub = _NoMemoReactor(sc["decision"], times=2)
sc["charge"].charge_declaration_reactions.append(stub.maybe_offer)
declare(sc)
origin = [(round(mo.x_in, 2), round(mo.y_in, 2)) for mo in sc["charging"].models]
hits = spy_commits(sc)
acted, prompted = drive(sc)
c.true("first attempt: deferred behind the stub's first prompt", acted and prompted)
acted, prompted = drive(sc, answer=False)
c.true("the RETRY is deferred too - the stub prompted again", acted and prompted)
c.eq("...and the declaration is still standing, not declined", sc["charge"].state, DECLARING_TARGETS)
c.eq("...with the move closed", sc["movement"].move_mode, None)
c.eq("...and no segment committed without a move", hits, [])
c.eq("...and no model displaced", [(round(mo.x_in, 2), round(mo.y_in, 2)) for mo in sc["charging"].models], origin)
_decline(sc["decision"])
c.eq("the answer re-opens the move", sc["movement"].move_mode, "charge")
acted, prompted = drive(sc)
c.true("the stub is exhausted, the ladder concludes", acted and not prompted and sc["charge"].state == IDLE)
c.eq("still no segment without a move", hits, [])

# The ladder itself, called directly: a reopen that opens nothing hands the
# continuation back as None and commits nothing.
sc = scene(dense_box=True, reactors=())
declare(sc)
sc["charge"].begin_charge_move()
hits = spy_commits(sc)
calls = []


def reopen_nothing():
    calls.append(1)
    sc["movement"].cancel_move()  # leaves move_mode None


result, errors = ad._run_charge_attempts(sc["movement"], sc["charging"], sc["defender"],
                                         sc["charge"].max_distance, reopen=reopen_nothing,
                                         confirm=sc["charge"].confirm_charge_move)
c.eq("a retry whose reopen opens no move returns None", result, None)
c.eq("...after exactly one reopen", len(calls), 1)
c.true("...carrying the first approach's errors", bool(errors))
c.eq("...and committed nothing without a move", hits, [])

# ===================================== 5. the harness path is not affected
print("\n5) the bare-controller path (measure_reported_moves.py) still gets a bool")
sc = scene(dense_box=True, reactors=())
declare(sc)
mc, squad, target, roll = sc["movement"], sc["charging"], sc["defender"], sc["charge"].max_distance
sc["charge"].decline_charge_move()


def reopen_bare():
    mc.select(squad.models[0])
    if mc.selected_squad is not squad:
        mc.selected_squad = squad
    mc.start_charge_move(roll, [target])


reopen_bare()
result, errors = ad._run_charge_attempts(mc, squad, target, roll, reopen=reopen_bare, confirm=mc.confirm_move)
c.eq("every approach fails on the Dense box", result, False)
c.true("...with a real error to report", bool(errors))

# ==================================================== 6. guards at the source
print("\n6) guards at the source")
driver = io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read()
ladder = driver[driver.index("def _run_charge_attempts("):driver.index("def _log_charge_geometry(")]
c.true("the ladder checks the move right after every reopen()",
       "            reopen()\n            if movement_controller.move_mode != \"charge\":\n" in ladder)
c.true("...and hands the continuation back as None", "return None, last_errors" in ladder)
handler = driver[driver.index("def _handle_charge("):driver.index("def _handle_charge(") + 12000]
c.true("_handle_charge treats None as 'come back', not as a failed charge",
       "        if completed is None:\n" in handler
       and handler.index("if completed is None:") < handler.index("charge_controller.decline_charge_move()", handler.index("_run_charge_attempts(")))
# The resume branch opens the move only if a reaction's answer has not
# already done so - begin_charge_move() over an OPEN move runs the chain a
# second time for the same standing declaration (section 4's stub shows it).
resume = handler[:handler.index("_run_charge_attempts(")]
c.true("the resume branch opens the move only when it is not open yet",
       "        if movement_controller.move_mode != \"charge\":\n            # Open the move" in resume
       and resume.count("charge_controller.begin_charge_move()") == 1)

# MENGENDIFFERENZ: every reactor main.py hangs on the declaration chain keeps
# the memo. A behaviour test cannot see the FOURTH reactor, because it does
# not exist yet; this line can.
main_src = io.open("main.py", encoding="utf-8").read()
extend = main_src[main_src.index("charge_declaration_reactions.extend(["):]
extend = extend[:extend.index("])")]
names = re.findall(r"(\w+)\.maybe_offer", extend)
single = re.search(r"charge_controller\.on_charge_declared = (\w+)\.maybe_offer", main_src)
if single:
    names.append(single.group(1))
c.true("liveness: at least three reactors are registered", len(names) >= 3)
missing = []
for var in names:
    klass = re.search(rf"\b{var} = (?:proactive_stratagems\.add\()?(\w+)\(", main_src)
    module_src = None
    if klass:
        for fname in os.listdir("game"):
            if fname.endswith(".py"):
                text = io.open(os.path.join("game", fname), encoding="utf-8").read()
                if f"class {klass.group(1)}" in text:
                    module_src = text
                    break
    if module_src is None or "self._offered_key = key" not in module_src or "if key == self._offered_key" not in module_src:
        missing.append(var)
c.eq("every registered declaration reactor keeps the offered-key memo", missing, [])

c.finish()
