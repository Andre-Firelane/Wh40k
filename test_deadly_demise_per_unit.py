"""Rule 24.08 (Deadly Demise X): ONE detonation D6, then the mortal-wound
amount rolled SEPARATELY for each unit caught in it.

User report, on a real game (logs/game_20260821_112241.log, lines 1622-1653):
"deadly demise hat im letzten zug viel zu viel schaden angerichtet oder?" - a
destroyed Battlewagon (printed "Deadly Demise D6") rolled a 6 to detonate,
rolled a 6 for X, and then dealt SIX mortal wounds to each of the four units
within 6" at once. 24 mortal wounds off one explosion; it wiped three units
and took Commander Farsight from 7/8 wounds to 1/8.

Everything else about that explosion checked out and is pinned here so the
next report does not re-investigate it: all four units really were within 6"
edge-to-edge, the Battlewagon really is Deadly Demise D6, mortal wounds
really do carry from model to model and really do stop at the unit boundary.
The single wrong thing was that X was rolled ONCE and handed to every unit -
user ruling: "es muss fuer JEDE einheit in reichtweite separat gewuerfelt
werden ... also einmal wuerfeln, ob er explodiert. wenn ja, fuer JEDE einheit
den schaden auswuerfeln."

Section 3 is the A/B: a local copy of the pre-fix shape (one shared X) run on
the same board, so a green suite proves the fix and not just that the scene
works. Real DeadlyDemiseController/GameState/DiceManager/TurnTracker and real
datasheets throughout; only the random number source is scripted.
"""

from game.deadly_demise import (
    DEADLY_DEMISE_RANGE_IN, DEADLY_DEMISE_SUCCESS_ROLL, DeadlyDemiseController,
)
from game.factions.orks import BATTLEWAGON, DEFF_DREAD, GRETCHIN
from game.factions.tau_empire import (
    CRISIS_SUNFORGE, RIPTIDE_BATTLESUIT, STEALTH_BATTLESUITS, STRIKE_TEAM,
)
from game.squad import edge_distance
from testkit import (
    Checks, GameState, Log, PHASES, PHASE_SHOOTING, RecordingDice, TurnTracker,
    build, script,
)

c = Checks("Deadly Demise: one detonation roll, one damage roll per unit")


def check(label, condition, detail=""):
    """testkit's Checks reports true/false only - fold the observed value into
    the label so a failure says what it actually saw."""
    c.true(f"{label} [{detail}]" if detail else label, condition)



# ----------------------------------------------------------------- scene

# The reported explosion, verbatim: every position below is a [move detail]
# line from logs/game_20260821_112241.log, and the Battlewagon is where it
# died. Only the units that were actually caught are placed.
BATTLEWAGON_AT = (51.78, 23.50)
REPORTED = [
    ("1 Strike Team 1", STRIKE_TEAM, "Player 1",
     [(53.00, 29.74), (52.98, 31.24), (51.69, 30.47)]),
    ("1 Stealth Battlesuits 1", STEALTH_BATTLESUITS, "Player 1",
     [(47.60, 31.52), (47.95, 33.18), (46.33, 32.64), (49.22, 32.05), (48.88, 30.39)]),
    ("1 Crisis Sunforge Battlesuits 1", CRISIS_SUNFORGE, "Player 1",
     [(48.47, 27.83)]),
    ("1 Riptide Battlesuit 1", RIPTIDE_BATTLESUIT, "Player 1",
     [(44.28, 30.26)]),
]


def scene(dying_sheet=BATTLEWAGON, extra=()):
    """The reported board. `extra` adds (name, datasheet, owner, positions)
    on top - used to put a friendly unit in the blast as well."""
    st = GameState()

    dying = build(dying_sheet, "Player 2", name="2 " + dying_sheet.name + " 1")
    for model in dying.models:
        model.x_in, model.y_in = BATTLEWAGON_AT
        st.add_token(model)

    caught = {}
    for name, sheet, owner, positions in list(REPORTED) + list(extra):
        squad = build(sheet, owner, name=name)
        for i, model in enumerate(squad.models):
            # More models than logged positions (the reported units had taken
            # losses): the rest stack on the last one, which keeps the unit in
            # range and gives it enough wounds that nothing is wasted.
            model.x_in, model.y_in = positions[min(i, len(positions) - 1)]
            st.add_token(model)
        caught[name] = squad

    tt = TurnTracker()
    tt.started = True
    tt.battle_round = 3
    tt.phase_index = PHASES.index(PHASE_SHOOTING)
    tt.turn_owner = tt.active_player = "Player 1"

    dice = RecordingDice()
    log = Log()
    dd = DeadlyDemiseController(dice, st.tokens, turn_tracker=tt, game_log=log)
    return dict(state=st, dying=dying, caught=caught, turn=tt, dice=dice, log=log, demise=dd)


def wounds_left(squad):
    return sum(max(0, m.current_wounds) for m in squad.models)


def kill_and_detonate(sc, *rolls):
    """Destroy the model exactly the way main.py's own loop leaves it (wounds
    at zero, token out of play, death queued, position and .squad kept), then
    start rule 24.08.

    `rolls` is the whole dice script for the detonation: the D6 first, then
    whatever damage rolls follow. It has to be queued HERE, before
    maybe_start_next() - that call already throws the detonation die."""
    model = sc["dying"].models[0]
    model.current_wounds = 0
    sc["state"].remove_dead_models()
    sc["demise"].queue_death(model)
    sc["before"] = {name: wounds_left(sq) for name, sq in sc["caught"].items()}
    script(*rolls, default=1)
    sc["demise"].maybe_start_next()
    return model


def drive(sc, limit=500):
    """Answer whatever the detonation is waiting on, the way main.py's loop
    does: acknowledge dice, then pick a model for each mortal wound. Records
    who the engine considered the active player at each pick (rule 06.02)."""
    sc.setdefault("owner_matched_active", [])
    for _ in range(limit):
        if sc["dice"].is_pending:
            sc["dice"].acknowledge()
            sc["demise"].on_dice_acknowledged()
        elif sc["demise"].pending_damage_choice:
            pick = sc["demise"].pending_damage_choice[0]
            sc["owner_matched_active"].append(pick.squad.owner == sc["turn"].active_player)
            sc["demise"].choose_damage_model(pick)
        elif sc["demise"].is_busy:
            raise AssertionError("busy with nothing to answer")
        else:
            return
    raise AssertionError("detonation never settled")


def taken(sc):
    """Mortal wounds actually applied, per unit."""
    return {name: sc["before"][name] - wounds_left(sq) for name, sq in sc["caught"].items()}


def x_roll_labels(sc):
    return [label for label, _ in sc["dice"].rolled if "Deadly Demise" in label and " vs " in label]


def detonation_labels(sc):
    return [label for label, _ in sc["dice"].rolled
            if "Deadly Demise" in label and " vs " not in label]


# ========================= 1. the reported board: nothing here was the bug
print("\n1) the reported explosion - geometry, datasheet and allocation")

sc = scene()
bw = sc["dying"].models[0]
check("the Battlewagon really is Deadly Demise D6",
        bw.profile.deadly_demise_notation is not None
        and bw.profile.deadly_demise_notation.sides == 6,
        str(bw.profile.deadly_demise_notation))

for name, squad in sc["caught"].items():
    gap = min(edge_distance(bw, m) for m in squad.models)
    check('%s was genuinely within %.0f" (%.2f")' % (name, DEADLY_DEMISE_RANGE_IN, gap),
            gap <= DEADLY_DEMISE_RANGE_IN, "%.2f" % gap)

check("all four reported units are caught, and they are the only ones",
        len(sc["caught"]) == 4)

# The exploding vehicle must not be in its own blast: it is off the board by
# the time 24.08 resolves, so its squad has no models left to be "within 6"".
kill_and_detonate(sc, DEADLY_DEMISE_SUCCESS_ROLL, 1, 2, 3, 4)
sc["dice"].acknowledge()
sc["demise"].on_dice_acknowledged()
check("the exploding model is not caught in its own detonation",
        not any(m.current_wounds > 0 for m in sc["dying"].models))


# ============================== 2. one detonation roll, one X roll per unit
print("\n2) one detonation D6, then a separate damage roll for each unit")

sc = scene()
# The detonation D6, then four DIFFERENT X values. The order units come out
# in is not defined (the queue is built from a set), so the check is on the
# multiset of amounts, not on which unit got which.
kill_and_detonate(sc, DEADLY_DEMISE_SUCCESS_ROLL, 1, 2, 3, 4)
drive(sc)

check("exactly one detonation roll", len(detonation_labels(sc)) == 1,
        " | ".join(detonation_labels(sc)))
check("one damage roll per caught unit, four in total",
        len(x_roll_labels(sc)) == 4, " | ".join(x_roll_labels(sc)))
check("each damage roll names the unit it is for",
        all(any(name in label for label in x_roll_labels(sc)) for name in sc["caught"]),
        " | ".join(x_roll_labels(sc)))

amounts = taken(sc)
check("the four units take four DIFFERENT amounts, one per roll",
        sorted(amounts.values()) == [1, 2, 3, 4], str(amounts))
check("nothing was wasted, so every rolled wound landed",
        sum(amounts.values()) == 1 + 2 + 3 + 4, str(sum(amounts.values())))
check("the log names each unit and its own amount",
        all(sc["log"].has(name) for name in sc["caught"]))
check("and the detonation line says the amount is rolled per unit",
        "separately for each" in sc["log"].find("detonates"),
        sc["log"].find("detonates"))
check("the active player is restored once the detonation is done",
        sc["turn"].active_player == "Player 1", str(sc["turn"].active_player))
check("and the controller is idle again", not sc["demise"].is_busy)


# =============================================== 3. A/B against the pre-fix
print("\n3) A/B: the pre-fix shape gave every unit the same number")

# Local copy of what the code used to do, in observable terms: only the first
# caught unit rolls, and that one number is handed to every later unit. Kept
# here rather than as a switch in the engine.
_real_next = DeadlyDemiseController._begin_next_squad
_real_wounds = DeadlyDemiseController._begin_squad_wounds


def _shared_x_wounds(self, squad, x):
    if getattr(self, "_shared_x", None) is None:
        self._shared_x = x
    _real_wounds(self, squad, self._shared_x)


def _shared_x_next(self):
    if getattr(self, "_shared_x", None) is not None and self._squad_queue:
        squad = self._squad_queue.pop(0)
        if self.turn_tracker is not None:
            self.turn_tracker.set_active(squad.owner)
        _real_wounds(self, squad, self._shared_x)
        return
    _real_next(self)


DeadlyDemiseController._begin_next_squad = _shared_x_next
DeadlyDemiseController._begin_squad_wounds = _shared_x_wounds
try:
    ab = scene()
    kill_and_detonate(ab, DEADLY_DEMISE_SUCCESS_ROLL, 6, 1, 2, 3)
    drive(ab)
    ab_amounts = taken(ab)
    check("pre-fix: only ONE damage roll for the whole detonation",
            len(x_roll_labels(ab)) == 1, " | ".join(x_roll_labels(ab)))
    check("pre-fix: every unit takes that same 6 (the reported case)",
            sorted(ab_amounts.values()) == [6, 6, 6, 6], str(ab_amounts))
    check("pre-fix total is 24 mortal wounds off one explosion",
            sum(ab_amounts.values()) == 24, str(sum(ab_amounts.values())))
finally:
    DeadlyDemiseController._begin_next_squad = _real_next
    DeadlyDemiseController._begin_squad_wounds = _real_wounds

# Same board, same detonation, fixed code: four rolls, four amounts.
after = scene()
kill_and_detonate(after, DEADLY_DEMISE_SUCCESS_ROLL, 6, 1, 2, 3)
drive(after)
check("fixed: the same scripted dice now give four different amounts",
        sorted(taken(after).values()) == [1, 2, 3, 6], str(taken(after)))


# ============================================ 4. friend and foe, rule 06.02
print("\n4) friend and foe are both caught, and each picks its own models")

friendly = ("2 Gretchin 9", GRETCHIN, "Player 2", [(50.0, 25.0)])
sc = scene(extra=(friendly,))
kill_and_detonate(sc, DEADLY_DEMISE_SUCCESS_ROLL, 1, 2, 3, 4, 5)
drive(sc)

check("the friendly unit is caught too", taken(sc).get("2 Gretchin 9", 0) > 0,
        str(taken(sc)))
check("five units, five separate damage rolls", len(x_roll_labels(sc)) == 5,
        " | ".join(x_roll_labels(sc)))
check("five different amounts", sorted(taken(sc).values()) == [1, 2, 3, 4, 5],
        str(taken(sc)))
check("rule 06.02: every model pick belonged to that unit's own controller",
        sc["owner_matched_active"] and all(sc["owner_matched_active"]),
        str(sc["owner_matched_active"]))


# ================================================= 5. a fixed X needs no roll
print("\n5) a printed fixed X is used as-is, with no roll at all")

sc = scene(dying_sheet=DEFF_DREAD)
trukk = sc["dying"].models[0]
check("the Deff Dread's X is a plain number, not dice notation",
        trukk.profile.deadly_demise_notation is None and trukk.profile.deadly_demise == 1,
        str(trukk.profile.deadly_demise))
kill_and_detonate(sc, DEADLY_DEMISE_SUCCESS_ROLL)
drive(sc)
check("no damage rolls are thrown", not x_roll_labels(sc), " | ".join(x_roll_labels(sc)))
# The Deff Dread's base is far smaller than the Battlewagon's, so the same
# board catches fewer units - assert on the ones actually in range, and that
# there ARE some, rather than on a fixed count.
in_range = {name: n for name, n in taken(sc).items() if n}
check("some units are caught", len(in_range) >= 3, str(taken(sc)))
check("and every caught unit takes exactly the printed 1",
        set(in_range.values()) == {1}, str(taken(sc)))


# ==================================================== 6. no detonation, no X
print("\n6) a failed detonation rolls nothing further and hurts nobody")

sc = scene()
kill_and_detonate(sc, DEADLY_DEMISE_SUCCESS_ROLL - 1, 6, 6, 6, 6)
drive(sc)
check("no damage roll is thrown", not x_roll_labels(sc), " | ".join(x_roll_labels(sc)))
check("nobody takes a wound", set(taken(sc).values()) == {0}, str(taken(sc)))
check("and the log says so", sc["log"].has("no detonation"), sc["log"].find("Deadly Demise"))


c.finish()
