"""Appends section 5 (Etappe 5) to test_aeldari_enhancements.py."""
import io

SECTION = '''

# =========================================================================
# 5. CP and resource economy
#    Protector of the Paths, Gift of Foresight, Echoes of Ulthanesh,
#    Torc of Morai-Heg, Timeless Strategist, Lucid Eye.
# =========================================================================
print("\\n5. CP and resource economy")

from game import enh_echoes_of_ulthanesh as eeu  # noqa: E402
from game import enh_gift_of_foresight as egf  # noqa: E402
from game import enh_lucid_eye as ele  # noqa: E402
from game import enh_protector_of_the_paths as epp  # noqa: E402
from game import enh_timeless_strategist as ets  # noqa: E402
from game import enh_torc_of_morai_heg as etm  # noqa: E402
from game import free_stratagem_once_per_round as fsopr  # noqa: E402
from game import cp_discount  # noqa: E402
from game.command_points import CommandPointManager  # noqa: E402
from game.stratagems import Stratagem, StratagemController  # noqa: E402

_strat_src = io.open("game/stratagems.py", encoding="utf-8").read()


class _E5Objective:
    """The two things Protector of the Paths asks of an objective."""

    def __init__(self, x_in, y_in, controlled_by):
        self.controlled_by = controlled_by
        self.terrain_area = _E5Area(x_in, y_in)


class _E5Area:
    def __init__(self, x_in, y_in):
        self.x_in, self.y_in = x_in, y_in

    def distance_to_model(self, model):
        return ((model.x_in - self.x_in) ** 2 + (model.y_in - self.y_in) ** 2) ** 0.5


class _E5Zone:
    """A rectangular stand-in for a DeploymentZone - only contains_point is
    read, and the real shapes are exercised by test_deployment_shapes.py."""

    def __init__(self, x_in, y_in, w_in, h_in):
        self.x_in, self.y_in, self.w_in, self.h_in = x_in, y_in, w_in, h_in

    def contains_point(self, x_in, y_in):
        return (self.x_in <= x_in <= self.x_in + self.w_in
                and self.y_in <= y_in <= self.y_in + self.h_in)


class _Turn5:
    def __init__(self, battle_round=1, turn_owner=HUMAN):
        self.battle_round = battle_round
        self.turn_owner = turn_owner


def _cp(**start):
    m = CommandPointManager()
    for player, amount in start.items():
        m.cp[player.replace("_", " ")] = amount
    return m


# --- 5a. the shared "for 0CP" sentence ------------------------------------
# FREE, NOT CHEAPER: the discount is whatever the Stratagem costs, so a 2CP
# use is as free as a 1CP one. A flat -1 would look right on every 1CP
# Stratagem and quietly charge for the rest.
_f_unit = _led("Farseer", "Guardian Defenders")
E.grant(_f_unit, "Gift of Foresight", model=_leader_model(_f_unit, "Farseer"))
_f_disc = egf.GiftOfForesightDiscount(turn_tracker=_Turn5())
_cheap = Stratagem(name="Command Re-roll", cp_cost=1, effect=lambda *a: None)
_dear = Stratagem(name="Command Re-roll", cp_cost=2, effect=lambda *a: None)
_other = Stratagem(name="Fire Overwatch", cp_cost=1, effect=lambda *a: None)
with only("WARHOST_PLAYERS"):
    c.eq("a 1CP use is free", _f_disc.available_discount(HUMAN, _cheap, [_f_unit]), 1)
    c.eq("...and so is a 2CP one, entirely", _f_disc.available_discount(HUMAN, _dear, [_f_unit]), 2)
    # KEYED ON THE STRATAGEM, which is what separates these from the four flat
    # CP discounts: another Stratagem on the same unit gets nothing.
    c.eq("a DIFFERENT Stratagem gets nothing",
         _f_disc.available_discount(HUMAN, _other, [_f_unit]), 0)
    # PURE QUERY: asking the price must never burn the once-per-round use.
    _f_disc.available_discount(HUMAN, _cheap, [_f_unit])
    _f_disc.available_discount(HUMAN, _cheap, [_f_unit])
    c.true("asking twice does not spend it", _f_disc.available(HUMAN))
    _f_disc.consume(HUMAN, _cheap, [_f_unit])
    c.true("...and consuming does", not _f_disc.available(HUMAN))
    c.eq("...so the second use in the round costs full price",
         _f_disc.available_discount(HUMAN, _cheap, [_f_unit]), 0)
with none_fielded():
    c.eq("no detachment, no discount",
         egf.GiftOfForesightDiscount(turn_tracker=_Turn5())
         .available_discount(HUMAN, _cheap, [_f_unit]), 0)

# It is a SUBCLASS of the plain CP discount, so the once-per-round ledger has
# exactly one definition.
c.true("it inherits the shared once-per-round machinery",
       issubclass(fsopr.FreeNamedStratagemOncePerRound, cp_discount.OncePerRoundCpDiscount))


# --- 5b. Protector of the Paths: the Snap Shooting override ---------------
_pp_unit = _led("Farseer", "Guardian Defenders")
E.grant(_pp_unit, "Protector of the Paths", model=_leader_model(_pp_unit, "Farseer"))
_pp_disc = epp.ProtectorOfThePathsDiscount(turn_tracker=_Turn5())
_ow = Stratagem(name="Fire Overwatch", cp_cost=1, effect=lambda *a: None)

with only("GUARDIAN_BATTLEHOST_PLAYERS"):
    # THE LATCH, not merely the bearer. Fire Overwatch is once per PHASE, the
    # discount once per battle ROUND - so a second, PAID Overwatch in the same
    # round is an ordinary one and hits on 6s.
    c.eq("before the free use, nothing overrides 15.09's 6",
         epp.snap_hit_threshold(_pp_disc, _pp_unit, []), None)
    _pp_disc.consume(HUMAN, _ow, [_pp_unit])
    c.eq("the free Overwatch hits on 5+",
         epp.snap_hit_threshold(_pp_disc, _pp_unit, []), 5)
    _pp_disc.clear_activation()
    c.eq("...and once that activation ends, 6s again",
         epp.snap_hit_threshold(_pp_disc, _pp_unit, []), None)

    # THE 4+ NEEDS A CONTROLLED OBJECTIVE - both halves.
    _pp_disc2 = epp.ProtectorOfThePathsDiscount(turn_tracker=_Turn5())
    _pp_disc2.consume(HUMAN, _ow, [_pp_unit])
    tk.line_up(_pp_unit, 20.0, 20.0, spacing=1.2)
    _pp_mine = _E5Objective(20.0, 20.0, HUMAN)
    _pp_theirs = _E5Objective(20.0, 20.0, "Player 2")
    c.eq("an objective the OPPONENT controls does not improve it",
         epp.snap_hit_threshold(_pp_disc2, _pp_unit, [_pp_theirs]), 5)
    c.eq("...one I control does", epp.snap_hit_threshold(_pp_disc2, _pp_unit, [_pp_mine]), 4)
    _pp_far = _E5Objective(20.0, 60.0, HUMAN)
    c.eq("...and one I control but am nowhere near does not",
         epp.snap_hit_threshold(_pp_disc2, _pp_unit, [_pp_far]), 5)

    # "WHILE THE BEARER IS LEADING A DIRE AVENGERS OR GUARDIANS UNIT" - EITHER
    # keyword, and neither is decoration. Guardian Defenders above carries
    # GUARDIANS; a led unit carrying neither gets nothing at all.
    c.true("Guardian Defenders carry one of the two named keywords",
           attached_units.unit_has_datasheet_keyword(_pp_unit, "GUARDIANS"))
    _pp_wrong = _led("Eldrad Ulthran", "Storm Guardians")
    setattr(_leader_model(_pp_wrong, "Eldrad Ulthran").profile,
            epp.FLAG_ATTR, True)
    c.true("...and Storm Guardians carry GUARDIANS too, so they qualify",
           epp.unit_has_bearer(_pp_wrong))
    # A bearer LEADING NOTHING fails on the 24.22 clause alone.
    _pp_alone = sq("Farseer")
    setattr(_pp_alone.models[0].profile, epp.FLAG_ATTR, True)
    c.true("a bearer leading nothing does not qualify",
           not epp.unit_has_bearer(_pp_alone))
    # BOTH HALVES OF THE CARD ask the same three questions - granting the free
    # Overwatch where the threshold half refuses would be one sentence
    # disagreeing with itself.
    c.eq("the discount half refuses there too",
         _pp_disc2.available_discount(HUMAN, _ow, [_pp_alone]), 0)

# AN OVERRIDE, NOT A MODIFIER: 15.09 says modifiers are ignored, so a Modifier
# would be thrown away by the very rule this is meant to beat.
c.true("the shooting step overrides the base threshold rather than modifying it",
       "override = enh_protector_of_the_paths.snap_hit_threshold(" in _shoot_src)
c.true("...at 15.09's own branch",
       "override if override is not None else 6" in _shoot_src)
# ...and the latch is released when the activation ends.
_ow_src = io.open("game/overwatch.py", encoding="utf-8").read()
c.true("the Overwatch controller releases the latch",
       "self.protector_of_the_paths.clear_activation()" in _ow_src)


# --- 5c. Torc of Morai-Heg: the first SURCHARGE ---------------------------
_tm_unit = _led("Farseer", "Guardian Defenders")
E.grant(_tm_unit, "Torc of Morai-Heg", model=_leader_model(_tm_unit, "Farseer"))
_tm_enemy = sq("Dire Avengers", "Player 2")
tk.line_up(_tm_unit, 20.0, 20.0, spacing=1.2)
_tm_bearer = _leader_model(_tm_unit, "Farseer")
tk.line_up(_tm_enemy, _tm_bearer.x_in, _tm_bearer.y_in + 6.0, spacing=1.2)
_tm_state = _E3State(_tm_unit, _tm_enemy)

with only("SEER_COUNCIL_PLAYERS"):
    _tm = etm.TorcOfMoraiHegSurcharge(game_state=_tm_state, turn_tracker=_Turn5())
    _tm_strat = Stratagem(name="Some Ploy", cp_cost=1, effect=lambda *a: None)
    c.eq("an enemy Stratagem on a unit within 12\\" costs 1CP more",
         _tm.available_surcharge("Player 2", _tm_strat, [_tm_enemy]), 1)
    # "YOUR OPPONENT targets" - it never taxes its own side.
    c.eq("...and the bearer's own Stratagems are untouched",
         _tm.available_surcharge(HUMAN, _tm_strat, [_tm_unit]), 0)
    # PURE QUERY again.
    _tm.available_surcharge("Player 2", _tm_strat, [_tm_enemy])
    c.true("asking does not spend it", _tm.available(HUMAN))
    # OUT OF RANGE.
    tk.line_up(_tm_enemy, _tm_bearer.x_in, _tm_bearer.y_in + 40.0, spacing=1.2)
    c.eq("a target out of 12\\" is not taxed",
         _tm.available_surcharge("Player 2", _tm_strat, [_tm_enemy]), 0)
    tk.line_up(_tm_enemy, _tm_bearer.x_in, _tm_bearer.y_in + 6.0, spacing=1.2)
    # ONCE PER TURN.
    _tm.consume("Player 2", _tm_strat, [_tm_enemy])
    c.eq("...and only once per turn",
         _tm.available_surcharge("Player 2", _tm_strat, [_tm_enemy]), 0)

# THE ORDER: discount, clamp, THEN surcharge. The two orders differ exactly
# when a discount exceeds the cost - and the other one would let any discount
# at all cancel the tax.
c.true("the cost is clamped before the surcharge is added",
       before(_strat_src, "cost = max(0, cost)", "for surcharge in self.cost_surcharges:"))

# ...end to end, through the REAL StratagemController.
with only("SEER_COUNCIL_PLAYERS"):
    _sc = StratagemController(command_points=_cp(Player_2=1))
    _sc.cost_surcharges.append(
        etm.TorcOfMoraiHegSurcharge(game_state=_tm_state, turn_tracker=_Turn5()))
    _tax_strat = Stratagem(name="Taxed Ploy", cp_cost=1, effect=lambda *a: None)
    c.eq("a 1CP Stratagem costs 2CP under the Torc",
         _sc._cost_for("Player 2", _tax_strat, [_tm_enemy], 0), 2)
    # THE FAQ CLAUSE: priced out, it still counts as used this phase.
    c.true("...so with only 1CP it cannot be used",
           not _sc.can_use("Player 2", _tax_strat, [_tm_enemy]))
    c.true("...and using it fails", not _sc.use("Player 2", _tax_strat, [_tm_enemy]))
    c.true("...but it COUNTS AS USED this phase",
           ("Player 2", "Taxed Ploy") in _sc.used_this_phase)
    c.eq("...with no CP spent", _sc.command_points.cp["Player 2"], 1)

    # THE CONTRAST: unaffordable ANYWAY records nothing, which is the old
    # behaviour and must not change.
    _sc2 = StratagemController(command_points=_cp(Player_2=0))
    _sc2.cost_surcharges.append(
        etm.TorcOfMoraiHegSurcharge(game_state=_tm_state, turn_tracker=_Turn5()))
    _poor = Stratagem(name="Unaffordable Ploy", cp_cost=1, effect=lambda *a: None)
    c.true("a Stratagem nobody could afford anyway fails",
           not _sc2.use("Player 2", _poor, [_tm_enemy]))
    c.true("...and is NOT recorded as used",
           ("Player 2", "Unaffordable Ploy") not in _sc2.used_this_phase)


# --- 5d. Echoes of Ulthanesh: the two bonuses STACK -----------------------
_eu_unit = sq("Windriders")
E.grant(_eu_unit, "Echoes of Ulthanesh", model=_eu_unit.models[0])
_eu_model = _eu_unit.models[0]
_eu_own = _E5Zone(0.0, 0.0, 40.0, 12.0)
_eu_enemy = _E5Zone(0.0, 40.0, 40.0, 12.0)

_eu_model.x_in, _eu_model.y_in = 20.0, 6.0            # inside its own zone
c.eq("in your own zone: no bonus", eeu.roll_bonus(_eu_model, _eu_own, _eu_enemy), 0)
_eu_model.x_in, _eu_model.y_in = 20.0, 25.0           # no man's land
c.eq("outside it: +1", eeu.roll_bonus(_eu_model, _eu_own, _eu_enemy), 1)
_eu_model.x_in, _eu_model.y_in = 20.0, 45.0           # in the enemy zone
# THE STACK: a bearer in the opponent's zone is by definition not in its own,
# so it gets BOTH - a 3+ rather than a 5+. Read as either/or the card caps at
# +1 and the aggressive play it rewards buys nothing extra.
c.eq("in the ENEMY zone: +2, because both clauses apply",
     eeu.roll_bonus(_eu_model, _eu_own, _eu_enemy), 2)
c.eq("...which turns the printed 5+ into a 3+",
     eeu.ECHOES_THRESHOLD - 2, 3)

# NO ROLL WHEN THE CP CANNOT BE PAID.
with only("WINDRIDER_HOST_PLAYERS"):
    _eu_cp = _cp(Player_1=0)
    _eu_ctrl = eeu.EchoesOfUlthaneshController(
        game_state=_E3State(_eu_unit), command_points=_eu_cp,
        turn_tracker=_Turn5(), zones={HUMAN: (_eu_own, _eu_enemy)})
    tk.script(6)
    c.true("with headroom, it rolls", _eu_ctrl.begin_command_phase(HUMAN))
    c.eq("...and a 6 gains the CP", _eu_cp.cp.get(HUMAN, 0), 1)
    tk.script(6)
    c.true("...and with the round's bonus cap already spent, it does not roll",
           not _eu_ctrl.begin_command_phase(HUMAN))
    tk.script()


# --- 5e. Timeless Strategist: two ways to be present ----------------------
_ts_unit = _led("Farseer", "Guardian Defenders")
E.grant(_ts_unit, "Timeless Strategist", model=_leader_model(_ts_unit, "Farseer"))
with only("WARHOST_PLAYERS"):
    c.eq("a bearer on the battlefield grants a token",
         ets.extra_tokens_for(HUMAN, [_ts_unit], []), 1)
    # THE CLAUSE THAT IS EASY TO DROP: embarked in a transport that IS on the
    # battlefield still counts, and its models are off the token list.
    c.eq("...and so does one embarked in a transport that is",
         ets.extra_tokens_for(HUMAN, [], [_ts_unit]), 1)
    # ...while a unit in neither collection - Strategic Reserves - does not.
    c.eq("a bearer in Reserves grants nothing",
         ets.extra_tokens_for(HUMAN, [], []), 0)
    c.eq("...and the other player gets nothing either",
         ets.extra_tokens_for("Player 2", [_ts_unit], []), 0)
with none_fielded():
    c.eq("no detachment, nothing", ets.extra_tokens_for(HUMAN, [_ts_unit], []), 0)

# It is a SECOND term beside Martial Grace's, not a replacement.
_bf_src = io.open("game/battle_focus.py", encoding="utf-8").read()
c.true("the grant adds Martial Grace's term",
       "martial_grace.extra_tokens_for(player)" in _bf_src)
c.true("...and this one as well",
       "enh_timeless_strategist.extra_tokens_for(" in _bf_src)


# --- 5f. Lucid Eye: a SWAP, not a bonus -----------------------------------
_le_unit = _led("Farseer", "Guardian Defenders")
E.grant(_le_unit, "Lucid Eye", model=_leader_model(_le_unit, "Farseer"))

# A Fate die's FACE is which Stratagem it pays for, and consume() removes by
# VALUE - so +-1 must REPLACE an entry. Modelled as a bonus the pool would
# still hold the old value and nothing would change.
_le_faces = [3, 3, 5]
c.true("a 3 can become a 4", (3, 4) in ele.adjustments(_le_faces))
c.true("...and a 2", (3, 2) in ele.adjustments(_le_faces))
# DEDUPLICATED ON THE PAIR: two 3s offer one "3 -> 4", not two identical
# choices.
c.eq("two identical dice offer one change each way",
     len([p for p in ele.adjustments(_le_faces) if p[0] == 3]), 2)
# CLAMPED TO A REAL FACE: a 6 cannot become a 7, or the pool holds a die that
# can never be spent.
c.true("a 6 cannot go above the highest real face",
       not any(b > max(ele.legal_values()) for _a, b in ele.adjustments([6])))
c.true("...and a 1 cannot go below the lowest",
       not any(b < min(ele.legal_values()) for _a, b in ele.adjustments([1])))

# THE SWAP ITSELF, in place.
_le_pool_faces = [3, 3, 5]
c.true("applying a change edits the pool", ele.apply_adjustment(_le_pool_faces, 3, 4))
c.eq("...replacing exactly one die", sorted(_le_pool_faces), [3, 4, 5])
c.true("...and a value that is not held changes nothing",
       not ele.apply_adjustment(_le_pool_faces, 6, 5))
'''

p = "test_aeldari_enhancements.py"
s = io.open(p, encoding="utf-8").read()
old = "\n\nc.finish()"
assert s.count(old) == 1
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, SECTION + "\n\nc.finish()"))
print("appended")
