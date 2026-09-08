"""'TARGET: One <X> unit from your army' - the player picks, on the board.

REPORTED: "cost of victory wird mir pauschal angeboten, aber ich habe 3 guardian
squads. ich kann nicht waehlen welchen squad zurueck in reserve schicken will.
es muss auf dem feld angeklickt werden."

ONE DEFECT, FOUR MODULES, so ONE file - the same reason
test_mortal_wound_drains.py and test_return_placement.py are single files
covering several abilities. Cost of Victory, Webway Tunnel, Skyborne Sanctuary
and Overflight each looped over the eligible units, raised a prompt about the
FIRST, and returned; a per-detachment suite would only ever have seen its own
half of that.

WHY NONE OF THE FOUR SUITES CAUGHT IT: every one of them stages exactly ONE
eligible squad, and with one candidate the broken shape and the correct shape
are indistinguishable. So the load-bearing check here is not "a prompt opened"
but "clicking the SECOND candidate resolves the SECOND" - a bare option COUNT
would pass against an offer that wired every option to the same unit.

Wall of Mirrors (Kauyon) is measured alongside as the REFERENCE: it prints the
same TARGET line and was already built this way, which is what made the four
legible as a defect rather than a design.
"""

import io

import testkit as tk
from game import (guardian_cost_of_victory as gcv, kauyon_wall_of_mirrors as kwm,
                  martial_grace, skyborne_sanctuary as sky, unit_choice_offer,
                  unit_pick, warhost_webway_tunnel as wwt,
                  windrider_overflight as wov)
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.factions import aeldari as ae
from game.stratagems import StratagemController
from game.turn import TurnTracker, PHASE_FIGHT, PHASE_SHOOTING

c = tk.Checks("One-unit-from-your-army offers")
D = ae.AELDARI.datasheets
HUMAN, AI = "Player 1", "Player 2"
settings_as = tk.settings_as


def sq(name, owner=HUMAN, suffix=1):
    return tk.build(D[name], owner, name="%s %s %d" % (owner[-1], name, suffix))


def strat(cp=20):
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=tk.Log())


class _State:
    """Enough GameState for withdraw_to_reserves() to really run."""

    def __init__(self, tokens=()):
        self.tokens = list(tokens)
        self.reserves = []
        self.embarked_squads = []
        self.objectives = []


def boundary_tracker(fought=AI, phase=PHASE_FIGHT):
    """A tracker parked on `phase` with `fought` as the turn owner.

    Returned BEFORE advance_phase(), so a caller can do what main.py does:
    capture mover_before, advance, reset, THEN offer."""
    tracker = TurnTracker(first_player=fought)
    while tracker.phase != phase:
        tracker.advance_phase()
    return tracker


def labels(decision_manager):
    if not decision_manager.is_pending:
        return []
    return [o["label"] for o in decision_manager.options]


def tagged(decision_manager):
    if not decision_manager.is_pending:
        return []
    return [o.get("squad") for o in decision_manager.options
            if o.get("squad") is not None]


def three_of(datasheet, owner=HUMAN, spread=12.0, y=20.0, x0=10.0):
    """Three separately-named squads of one datasheet, far apart."""
    squads = []
    for i in range(3):
        squad = sq(datasheet, owner, suffix=i + 1)
        tk.line_up(squad, x0 + i * spread, y, spacing=1.2)
        squads.append(squad)
    return squads


def models_of(squads):
    return [m for s in squads for m in s.models]


class _NoPick:
    """Stands in for a prompt that is NOT a board pick, so the checks below go
    RED instead of crashing.

    unit_pick.pending() returns None for an untagged prompt - which is exactly
    the pre-fix world every A/B probe here restores - and reading `.squads` off
    that aborts the whole suite instead of failing one line, hiding which check
    broke. This repo has paid for that lesson more than a dozen times."""

    squads = ()

    def is_eligible(self, squad):
        return False

    def pick(self, squad):
        return False


def board_pick(decision_manager, tokens):
    """unit_pick.pending(), degraded to a no-op rather than None."""
    return unit_pick.pending(decision_manager, tokens) or _NoPick()


# =========================================================================
# 1. The reported case: Cost of Victory with three Guardian squads
# =========================================================================
print("\n1. Cost of Victory - the reported case")

GB_ON = dict(GUARDIAN_BATTLEHOST_PLAYERS=(HUMAN,))

with settings_as(**GB_ON):
    _cov_squads = three_of("Guardian Defenders")
    for _s in _cov_squads:                 # kill one each, so the return half runs
        _m = _s.models[0]
        _m.current_wounds = 0
        _s.models.remove(_m)
        _s.destroyed_models.append(_m)
    _cov_tokens = models_of(_cov_squads)
    _cov_state = _State(_cov_tokens)
    _cov_dec = DecisionManager()
    _cov_tt = boundary_tracker()
    _cov = gcv.CostOfVictoryController(
        strat(), game_state=_cov_state, turn_tracker=_cov_tt,
        all_tokens=_cov_tokens, decision_manager=_cov_dec, game_log=tk.Log())

    c.eq("three squads are eligible",
         sum(1 for s in _cov_squads if gcv.eligible_unit(s)), 3)

    # main.py's real order: capture mover_before, advance, reset, THEN offer.
    _mover_before = _cov_tt.turn_owner
    _cov_tt.advance_phase()
    _cov.reset_phase()
    _cov.offer_at_end_of_fight_phase(_cov_squads, _mover_before)

    c.true("the offer opens", _cov_dec.is_pending)
    c.eq("...to the side whose OPPONENT just fought", _cov_dec.player, HUMAN)
    c.eq("...naming every eligible unit", len(tagged(_cov_dec)), 3)
    c.eq("...plus a decline", len(labels(_cov_dec)), 4)
    c.true("...and the prompt no longer names one unit for the player",
           all(s.name not in _cov_dec.prompt for s in _cov_squads))

    c.true("it is answered by clicking the board",
           unit_pick.pending(_cov_dec, _cov_tokens) is not None)
    _pick = board_pick(_cov_dec, _cov_tokens)
    c.eq("...with all three ringed", len(_pick.squads), 3)
    c.eq("...and every model of all three clickable",
         len(unit_pick.target_models(_pick, _cov_tokens)), len(_cov_tokens))

    # THE LOAD-BEARING CHECK. Three options wired to the same unit would pass
    # every count above; only resolving a specific one tells them apart.
    _second = _cov_squads[1]
    c.true("clicking the SECOND squad resolves it", _pick.pick(_second))
    c.true("...and it is the SECOND that went into Strategic Reserves",
           _second in _cov_state.reserves)
    c.true("...while the other two are untouched",
           _cov_squads[0] not in _cov_state.reserves
           and _cov_squads[2] not in _cov_state.reserves)
    c.eq("...and its destroyed model came back", len(_second.destroyed_models), 0)
    c.true("...with the other two still carrying their dead",
           all(len(s.destroyed_models) == 1
               for s in (_cov_squads[0], _cov_squads[2])))

# --- 1b. the decline is still there, and still costs nothing --------------
with settings_as(**GB_ON):
    _d_squads = three_of("Guardian Defenders")
    _d_tokens = models_of(_d_squads)
    _d_state, _d_dec = _State(_d_tokens), DecisionManager()
    _d_tt = boundary_tracker()
    _d_pool = CommandPointManager()
    for _p in _d_pool.cp:
        _d_pool.cp[_p] = 20
    _d_ctrl = gcv.CostOfVictoryController(
        StratagemController(command_points=_d_pool, game_log=tk.Log()),
        game_state=_d_state, turn_tracker=_d_tt, all_tokens=_d_tokens,
        decision_manager=_d_dec, game_log=tk.Log())
    _mb = _d_tt.turn_owner
    _d_tt.advance_phase()
    _d_ctrl.reset_phase()
    _d_ctrl.offer_at_end_of_fight_phase(_d_squads, _mb)
    _cp_before = _d_pool.cp[HUMAN]
    if "Decline" in labels(_d_dec):
        _d_dec.choose(labels(_d_dec).index("Decline"))
    c.eq("declining spends no CP", _d_pool.cp[HUMAN], _cp_before)
    c.eq("...and withdraws nobody", _d_state.reserves, [])

# --- 1c. the AI is unchanged: nothing is offered, and the window closes ---
with settings_as(GUARDIAN_BATTLEHOST_PLAYERS=(AI,)):
    _ai_squads = three_of("Guardian Defenders", owner=AI)
    _ai_tokens = models_of(_ai_squads)
    _ai_dec = DecisionManager()
    _ai_tt = boundary_tracker(fought=HUMAN)
    _ai_ctrl = gcv.CostOfVictoryController(
        strat(), game_state=_State(_ai_tokens), turn_tracker=_ai_tt,
        all_tokens=_ai_tokens, decision_manager=_ai_dec, game_log=tk.Log(),
        auto_players=(AI,))
    _mb = _ai_tt.turn_owner
    _ai_tt.advance_phase()
    _ai_ctrl.reset_phase()
    c.true("the AI is offered nothing",
           not _ai_ctrl.offer_at_end_of_fight_phase(_ai_squads, _mb))
    c.true("...no prompt is queued", not _ai_dec.is_pending)
    c.true("...and the window is closed again", not _ai_ctrl._window.is_open())


# =========================================================================
# 2. Webway Tunnel - the same printed TARGET, the same shape
# =========================================================================
print("\n2. Webway Tunnel")

WH_ON = dict(WARHOST_PLAYERS=(HUMAN,))

with settings_as(**WH_ON):
    # "wholly within 9" of one or more battlefield edges" - along the bottom.
    _wt_squads = three_of("Guardian Defenders", spread=14.0, y=4.0, x0=6.0)
    _wt_tokens = models_of(_wt_squads)
    _wt_state, _wt_dec = _State(_wt_tokens), DecisionManager()
    _wt_tt = boundary_tracker()
    _wt = wwt.WebwayTunnelController(
        strat(), game_state=_wt_state, turn_tracker=_wt_tt,
        all_tokens=_wt_tokens, board_width_in=60.0, board_height_in=44.0,
        decision_manager=_wt_dec, game_log=tk.Log())
    _mb = _wt_tt.turn_owner
    _wt_tt.advance_phase()
    _wt.reset_phase()
    _wt.offer_at_end_of_fight_phase(_wt_squads, _mb)

    c.true("the offer opens", _wt_dec.is_pending)
    c.eq("...naming every eligible unit", len(tagged(_wt_dec)), 3)
    c.true("...answered by clicking the board",
           unit_pick.pending(_wt_dec, _wt_tokens) is not None)
    _wt_pick = board_pick(_wt_dec, _wt_tokens)
    c.true("clicking the THIRD squad resolves it", _wt_pick.pick(_wt_squads[2]))
    c.true("...and it is the THIRD that withdrew",
           _wt_squads[2] in _wt_state.reserves
           and _wt_squads[0] not in _wt_state.reserves)


# =========================================================================
# 3. Overflight - "One ASURYANI MOUNTED unit ... that destroyed one or more"
# =========================================================================
print("\n3. Overflight")

with settings_as(WINDRIDER_HOST_PLAYERS=(HUMAN,)):
    _ov_squads = three_of("Windriders", spread=14.0)
    _ov_tokens = models_of(_ov_squads)
    _ov_dec = DecisionManager()
    _ov_tt = boundary_tracker(fought=HUMAN, phase=PHASE_SHOOTING)
    _ov = wov.OverflightController(
        strat(), turn_tracker=_ov_tt, decision_manager=_ov_dec,
        game_log=tk.Log())
    # All three killed something this phase, so all three qualify.
    for _s in _ov_squads:
        _ov.notify_unit_destroyed(sq("Guardian Defenders", AI), _s)
    _mb = _ov_tt.turn_owner
    _phase_before = _ov_tt.phase
    _ov_tt.advance_phase()
    _ov.reset_phase()
    _ov.offer_at_end_of_phase(_ov_squads, _phase_before, _mb)

    c.true("the offer opens", _ov_dec.is_pending)
    c.eq("...naming every unit that killed this phase", len(tagged(_ov_dec)), 3)
    c.true("...answered by clicking the board",
           unit_pick.pending(_ov_dec, _ov_tokens) is not None)
    _ov_pick = board_pick(_ov_dec, _ov_tokens)
    c.true("...and only the units that killed are ringed",
           set(_ov_pick.squads) == set(_ov_squads))


# =========================================================================
# 4. Skyborne Sanctuary - the printed TARGET names TWO things
# =========================================================================
print("\n4. Skyborne Sanctuary - unit on the board, then transport")


class _FightStub:
    def is_eligible_to_fight(self, squad):
        return True


class _EmbarkStub:
    """Says yes only for the squads named as TRANSPORTS.

    A stub that accepts every friendly token makes the other two candidate
    squads look like transports, and step two would then be asked about them -
    which is the shape of the very bug under test, arriving from the test's own
    scaffolding."""

    def __init__(self, transports=()):
        self.transports = set(id(s) for s in transports)
        self.embarked = []

    def can_embark(self, squad, token, require_move=True, range_in=None):
        return id(getattr(token, "squad", None)) in self.transports

    def embark(self, squad, token, require_move=True, range_in=None):
        self.embarked.append((squad, token))
        return True


with settings_as(**WH_ON):
    _sk_squads = three_of("Dire Avengers", spread=14.0)
    _serpent = sq("Wave Serpent")
    tk.line_up(_serpent, 40.0, 30.0, spacing=1.2)
    _sk_tokens = models_of(_sk_squads) + list(_serpent.models)
    _sk_dec, _sk_emb = DecisionManager(), _EmbarkStub([_serpent])
    _sk_tt = boundary_tracker()
    _sk = sky.SkyborneSanctuaryController(
        strat(), martial_grace.SETTING, transport_controller=_sk_emb,
        fight_controller=_FightStub(), all_tokens=_sk_tokens,
        turn_tracker=_sk_tt, decision_manager=_sk_dec, game_log=tk.Log())
    _sk_tt.advance_phase()
    _sk.reset_phase()
    _sk.offer_at_end_of_fight_phase(_sk_squads)

    c.true("the offer opens", _sk_dec.is_pending)
    c.eq("...naming every eligible unit", len(tagged(_sk_dec)), 3)
    c.true("...answered by clicking the board",
           unit_pick.pending(_sk_dec, _sk_tokens) is not None)
    _sk_pick = board_pick(_sk_dec, _sk_tokens)
    c.true("clicking the SECOND squad resolves it", _sk_pick.pick(_sk_squads[1]))
    # ONE legal transport, so step two is not a question and is not asked.
    c.true("...one transport in range needs no second prompt",
           not _sk_dec.is_pending)
    c.eq("...and the SECOND squad is the one that embarked",
         [s for s, _ in _sk_emb.embarked], [_sk_squads[1]])

# --- 4b. TWO transports really is a question, and it gets asked ----------
with settings_as(**WH_ON):
    _sk2_squads = three_of("Dire Avengers", spread=14.0)
    _serpent_a, _serpent_b = sq("Wave Serpent"), sq("Falcon")
    tk.line_up(_serpent_a, 40.0, 30.0, spacing=1.2)
    tk.line_up(_serpent_b, 44.0, 30.0, spacing=1.2)
    _sk2_tokens = (models_of(_sk2_squads) + list(_serpent_a.models)
                   + list(_serpent_b.models))
    _sk2_dec, _sk2_emb = DecisionManager(), _EmbarkStub(
        [_serpent_a, _serpent_b])
    _sk2_tt = boundary_tracker()
    _sk2 = sky.SkyborneSanctuaryController(
        strat(), martial_grace.SETTING, transport_controller=_sk2_emb,
        fight_controller=_FightStub(), all_tokens=_sk2_tokens,
        turn_tracker=_sk2_tt, decision_manager=_sk2_dec, game_log=tk.Log())
    _sk2_tt.advance_phase()
    _sk2.reset_phase()
    _sk2.offer_at_end_of_fight_phase(_sk2_squads)
    c.true("the unit is still the board pick",
           unit_pick.pending(_sk2_dec, _sk2_tokens) is not None)
    _sk2_pick = board_pick(_sk2_dec, _sk2_tokens)
    _sk2_pick.pick(_sk2_squads[0])
    c.true("...and TWO transports raise the second question", _sk2_dec.is_pending)
    c.true("...naming both by name",
           {_serpent_a.name, _serpent_b.name} <= set(labels(_sk2_dec)))
    c.true("...as an ordinary list, not a second board pick",
           unit_pick.pending(_sk2_dec, _sk2_tokens) is None)
    if _serpent_b.name in labels(_sk2_dec):
        _sk2_dec.choose(labels(_sk2_dec).index(_serpent_b.name))
    c.eq("...and the transport that was named is the one embarked in",
         [t.squad for _, t in _sk2_emb.embarked], [_serpent_b])


# =========================================================================
# 5. Wall of Mirrors - the reference, unchanged
# =========================================================================
print("\n5. Wall of Mirrors (Kauyon) - the shape the four now share")

with settings_as(KAUYON_PLAYERS=(HUMAN,)):
    from game.factions import tau_empire as te      # noqa: E402
    _tau = te.TAU_EMPIRE.datasheets
    _wm_squads = []
    for _i in range(2):
        _s = tk.build(_tau["Stealth Battlesuits"], HUMAN,
                      name="1 Stealth Battlesuits %d" % (_i + 1))
        tk.line_up(_s, 12.0 + _i * 14.0, 20.0, spacing=1.2)
        _wm_squads.append(_s)
    _wm_tokens = models_of(_wm_squads)
    _wm_dec = DecisionManager()
    _wm_tt = boundary_tracker()
    _wm = kwm.WallOfMirrorsController(
        strat(), game_state=_State(_wm_tokens), turn_tracker=_wm_tt,
        all_tokens=_wm_tokens, decision_manager=_wm_dec, game_log=tk.Log())
    _mb = _wm_tt.turn_owner
    _wm_tt.advance_phase()
    _wm.reset_phase()
    _wm.offer_at_end_of_fight_phase(_mb)
    c.true("it opens one prompt naming both units", _wm_dec.is_pending)
    c.eq("...tagged", len(tagged(_wm_dec)), 2)
    c.true("...and is a board pick",
           unit_pick.pending(_wm_dec, _wm_tokens) is not None)


# =========================================================================
# 6. The shared helper, and the four really go through it
# =========================================================================
print("\n6. game/unit_choice_offer.py")

_UCO = io.open("game/unit_choice_offer.py", encoding="utf-8").read()
c.true("it records the report it was built for",
       "cost of victory wird mir pauschal angeboten" in _UCO)
c.true("...and says how it differs from per_unit_offer", "per_unit_offer" in _UCO)

for _name in ("guardian_cost_of_victory", "warhost_webway_tunnel",
              "skyborne_sanctuary", "windrider_overflight"):
    _src = io.open("game/%s.py" % _name, encoding="utf-8").read()
    c.true("%s offers through the shared helper" % _name,
           "unit_choice_offer.offer_one_of(" in _src)
    # The old shape, byte for byte: a request built INSIDE the per-squad loop.
    c.true("%s no longer raises its own single-unit request" % _name,
           "self.decision_manager.request(\n                squad.owner," not in _src)

# THE AI IS UNCHANGED, for all four - and this is what test_ai_mode.py's
# "no class takes auto_players and ignores it" now leans on. The four no longer
# READ self.auto_players; they forward it to the shared helper, so the guard
# there accepts a token and the real assurance has to be measured here.
with settings_as(WARHOST_PLAYERS=(AI,)):
    _n_squads = three_of("Guardian Defenders", owner=AI, spread=14.0, y=4.0, x0=6.0)
    _n_tokens = models_of(_n_squads)
    _n_dec = DecisionManager()
    _n_tt = boundary_tracker(fought=HUMAN)
    _n_ctrl = wwt.WebwayTunnelController(
        strat(), game_state=_State(_n_tokens), turn_tracker=_n_tt,
        all_tokens=_n_tokens, board_width_in=60.0, board_height_in=44.0,
        decision_manager=_n_dec, game_log=tk.Log(), auto_players=(AI,))
    _n_mb = _n_tt.turn_owner
    _n_tt.advance_phase()
    _n_ctrl.reset_phase()
    c.true("Webway Tunnel offers the AI nothing",
           not _n_ctrl.offer_at_end_of_fight_phase(_n_squads, _n_mb))
    c.true("...and queues no prompt for it", not _n_dec.is_pending)
    c.true("...and closes its window again", not _n_ctrl._window.is_open())

with settings_as(WINDRIDER_HOST_PLAYERS=(AI,)):
    _no_squads = three_of("Windriders", owner=AI, spread=14.0)
    _no_dec = DecisionManager()
    _no_tt = boundary_tracker(fought=AI, phase=PHASE_SHOOTING)
    _no_ov = wov.OverflightController(
        strat(), turn_tracker=_no_tt, decision_manager=_no_dec,
        game_log=tk.Log(), auto_players=(AI,))
    for _s in _no_squads:
        _no_ov.notify_unit_destroyed(sq("Guardian Defenders", HUMAN), _s)
    _no_mb, _no_phase = _no_tt.turn_owner, _no_tt.phase
    _no_tt.advance_phase()
    _no_ov.reset_phase()
    c.true("Overflight offers the AI nothing",
           not _no_ov.offer_at_end_of_phase(_no_squads, _no_phase, _no_mb))
    c.true("...and queues no prompt for it", not _no_dec.is_pending)
    c.true("...and closes its window again", not _no_ov._window.is_open())

with settings_as(WARHOST_PLAYERS=(AI,)):
    _ns_squads = three_of("Dire Avengers", owner=AI, spread=14.0)
    _ns_serpent = sq("Wave Serpent", owner=AI)
    tk.line_up(_ns_serpent, 40.0, 30.0, spacing=1.2)
    _ns_tokens = models_of(_ns_squads) + list(_ns_serpent.models)
    _ns_dec = DecisionManager()
    _ns_tt = boundary_tracker()
    _ns = sky.SkyborneSanctuaryController(
        strat(), martial_grace.SETTING, transport_controller=_EmbarkStub([_ns_serpent]),
        fight_controller=_FightStub(), all_tokens=_ns_tokens,
        turn_tracker=_ns_tt, decision_manager=_ns_dec, game_log=tk.Log(),
        auto_players=(AI,))
    _ns_tt.advance_phase()
    _ns.reset_phase()
    c.true("Skyborne Sanctuary offers the AI nothing",
           not _ns.offer_at_end_of_fight_phase(_ns_squads))
    c.true("...and queues no prompt for it", not _ns_dec.is_pending)
    c.true("...and closes its window again", not _ns._window.is_open())


# An empty candidate list must not raise a prompt - the callers rely on the
# False to close their window.
_empty_dec = DecisionManager()
c.true("no candidates, no prompt",
       not unit_choice_offer.offer_one_of(_empty_dec, HUMAN, [], "?",
                                          lambda s: None))
c.true("...and nothing is queued", not _empty_dec.is_pending)
c.true("no decision manager, no prompt",
       not unit_choice_offer.offer_one_of(None, HUMAN, [1], "?", lambda s: None))

c.finish()
