"""A/B probes for stage 6 of the Necron backfill - the other three C'tan.

Each probe restores ONE printed clause, or one half of one extraction, to a
pre-fix state AT THE SOURCE, runs the suite that should notice, and puts it
back. A probe that does NOT go red is a finding about the TEST, not an
all-clear, so this file exits non-zero if any survives.

RUN IT ALONE. It rewrites modules in the working tree and restores them in a
finally - a suite run, an edit or a commit alongside it will see a half-broken
tree, which is how a probe run once got committed into this repo.

THREE SUITES, and the split is deliberate:

  * test_necron_ctan.py is this stage's behaviour.
  * test_tau_enhancements.py is the EXTRACTION's other carrier. A probe on the
    shared half of game/post_deployment_redeploy.py is aimed at BOTH, because
    an extraction that only its new carrier notices is exactly the drift the
    extraction was supposed to prevent.
  * test_event_chain_wiring.py is the source-level set difference. No
    behaviour test can see a missing click branch or a missing highlight: it
    drives the controller directly, so the controller answers.

FAILURES ARE COUNTED, NOT PASSES. A probe can ADD checks (a loop that runs one
more time), and then "fewer passed than the baseline" is false while checks are
red - the older green-count driver reported NO BITE for a guard that was
working exactly as intended.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)

UNITS = os.path.join("game", "units.py")
WEAPONS = os.path.join("game", "weapons.py")
POINTS = os.path.join("game", "factions", "necrons_points.py")
DRAIN = os.path.join("game", "drain_life.py")
SWEEP = os.path.join("game", "mortal_wound_sweep.py")
ILLUSION = os.path.join("game", "grand_illusion.py")
REDEPLOY = os.path.join("game", "post_deployment_redeploy.py")
DISPLACE = os.path.join("game", "transdimensional_displacement.py")
MOVEMENT = os.path.join("game", "movement.py")
SQUAD = os.path.join("game", "squad.py")
MAIN = "main.py"

CTAN = "test_necron_ctan.py"
TAU = "test_tau_enhancements.py"
WIRING = "test_event_chain_wiring.py"
SUITES = (CTAN, TAU, WIRING)


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite):
    # The probes rewrite modules within the same second - the documented
    # __pycache__ race that has produced phantom failures in this repo.
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


# --------------------------------------------------------------- the edits
# Written as (anchor -> pre-fix) pairs: the anchor is what is there NOW.

PROBES = [
    # --- 1. the shared chassis ---------------------------------------------
    # The whole reason CtanShardProfile exists. A subclass that redefines one
    # of the shared names still LOOKS right - every characteristic reads
    # correctly - so only the "overrides nothing it shares" line can see it.
    ("the Deceiver drifts off the shared chassis (its own Toughness)",
     [(UNITS, '''    name = "C'tan Shard of the Deceiver"
    base_radius_in = CtanShardOfTheVoidDragonProfile.base_radius_in''',
       '''    name = "C'tan Shard of the Deceiver"
    toughness = 11
    base_radius_in = CtanShardOfTheVoidDragonProfile.base_radius_in''')], CTAN),

    # The Void Dragon was REPARENTED by this stage. If that dropped one of its
    # values, the corpus sweep in section 1 is what says so.
    ("the shared chassis loses a characteristic (Feel No Pain)",
     [(UNITS, '''    invulnerable_save = "4+"
    feel_no_pain = "5+"
    monster = True
    character = True
    fly = True
    deep_strike = True
    reanimation_protocols = True
    damage_reduction = 1            # "Necrodermis"''',
       '''    invulnerable_save = "4+"
    monster = True
    character = True
    fly = True
    deep_strike = True
    reanimation_protocols = True
    damage_reduction = 1            # "Necrodermis"''')], CTAN),

    # --- 2. weapons ---------------------------------------------------------
    # Two melee profiles printed as ONE datasheet entry. Split into two
    # weapons, every characteristic is still correct and rule 04.01 is simply
    # broken - a silent failure only the pairing assertion catches.
    ("the Scythe's two modes become two separate weapons",
     [(WEAPONS, "    overcharge_profile = ScytheOfTheNightbringerSweepProfile",
       "    # overcharge_profile removed by probe")], CTAN),

    ("the Gaze of Death loses its D6+3 damage notation",
     [(WEAPONS, '''    damage = 9            # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D6(3)''',
       "    damage = 9")], CTAN),

    ("Cosmic Insanity loses [PRECISION]",
     [(WEAPONS, '''    anti = ("CHARACTER", 4)
    devastating_wounds = True
    precision = True''',
       '''    anti = ("CHARACTER", 4)
    devastating_wounds = True''')], CTAN),

    # --- 3. the base-size decision -----------------------------------------
    # Undo it: transcribe the printed 40 mm. The test reads the corpus itself,
    # so it knows the printed number and still refuses this.
    ("the Deceiver is transcribed onto its printed 40 mm",
     [(UNITS, "    base_radius_in = CtanShardOfTheVoidDragonProfile.base_radius_in  # printed 40 mm; see above",
       "    base_radius_in = 0.787          # 40 mm printed base")], CTAN),

    ("the Transcendent C'tan loses its second-unit tier",
     [(POINTS, '''    "Transcendent C'tan": UnitPoints([
        PointsTier({1: 340}, to_unit=1),
        PointsTier({1: 360}, from_unit=2),
    ]),''',
       '''    "Transcendent C'tan": flat_points({1: 340}),''')], CTAN),

    # --- 4. Drain Life ------------------------------------------------------
    ("Drain Life triggers on a 2+ instead of a 4+",
     [(DRAIN, "DRAIN_LIFE_THRESHOLD = 4      # \"on a 4+\"",
       "DRAIN_LIFE_THRESHOLD = 2")], CTAN),

    ("Drain Life reaches 12\" instead of 6\"",
     [(DRAIN, "DRAIN_LIFE_RANGE_IN = 6.0", "DRAIN_LIFE_RANGE_IN = 12.0")], CTAN),

    # THE ONE THIS ENGINE HAS SHIPPED WRONG TWICE. The dice are rolled, the log
    # says N mortal wounds, and against a multi-model unit not one of them is
    # ever applied. Only a check that counts MODELS LOST can see it.
    ("the wounds are rolled and never land (no allocation drain)",
     [(SWEEP, '''        self._inflict(target, wounds)
        self._check_session_done()''',
       "        self._inflict(target, wounds)")], CTAN),

    # One die for the whole sweep instead of one per unit - the printed text is
    # "roll one D6 for EACH enemy unit".
    ("the gate rolls a single die rather than one per unit",
     [(SWEEP, '''        self.dice_manager.roll(
            len(targets), 6, label=self.label,''',
       '''        self.dice_manager.roll(
            1, 6, label=self.label,''')], CTAN),

    # is_busy is what main.py's phase gate reads. Forgetting the queue lets the
    # phase advance out from under the rest of the sweep.
    ("is_busy forgets the units still queued behind the current one",
     [(SWEEP, '''        return (self._pending is not None
                or bool(self._queue)
                or self._wound_roll is not None
                or self.mortal_wound_session is not None)''',
       '''        return self._pending is not None''')], CTAN),

    # --- 5. Grand Illusion --------------------------------------------------
    # THE CLAUSE A COPY OF THE T'AU TWIN WOULD LOSE. "If your army INCLUDES
    # this model" read as "if it is on the battlefield" - which is what the
    # OTHER redeploy ability in this engine really says.
    ("Grand Illusion is gated on the board instead of the army list",
     [(ILLUSION, '''        getter = getattr(state, "all_squads", None)
        if callable(getter):
            return list(getter())
        return self._squads()''',
       "        return self._squads()")], CTAN),

    ("Grand Illusion redeploys any unit, not just NECRONS ones",
     [(ILLUSION, "        return awakened_dynasty.is_necrons_unit(squad)",
       "        return True")], CTAN),

    # --- 6. Transdimensional Displacement -----------------------------------
    ("the displacement gets an ordinary Advance's budget",
     [(MOVEMENT, "        budget = (config.BOARD_WIDTH_IN ** 2 + config.BOARD_HEIGHT_IN ** 2) ** 0.5",
       "        budget = 6.0")], CTAN),

    ("the through-models bypass is never reached",
     [(MOVEMENT, '''                    or (self.displacing_this_move
                        and transdimensional_displacement.model_has_ability(token))):''',
       '''                    or (False
                        and transdimensional_displacement.model_has_ability(token))):''')], CTAN),

    ("the 8\" clearance is not checked after the move",
     [(MOVEMENT, "        if self.displacing_this_move:", "        if False:")], CTAN),

    # The generalisation itself: if the clearance still reported "a Scout move"
    # the rule would be enforced and the message would name the wrong ability.
    ("the clearance reports a Scout move rather than the ability",
     [(MOVEMENT, '''            errors += self.selected_squad.check_min_enemy_distance(
                self.all_tokens,
                transdimensional_displacement.TRANSDIMENSIONAL_MIN_ENEMY_DISTANCE_IN,
                "a Transdimensional Displacement",
                transdimensional_displacement.TRANSDIMENSIONAL_DISPLACEMENT_NAME)''',
       "            errors += self.selected_squad.check_scout_move_clearance(self.all_tokens)")], CTAN),

    # --- 7. the extractions -------------------------------------------------
    # THE SHARED HALF, AIMED AT THE OTHER CARRIER. An extraction whose T'au
    # carrier stops working is not an extraction, and no Necron suite can see
    # it - which is the whole reason this file runs two suites.
    ("the shared redeploy step stops offering anything",
     [(REDEPLOY, "        if not self.grants(player):", "        if True:")], TAU),

    # AIMED AT THIS STAGE'S SUITE, not the T'au one: measured, that suite never
    # reads remaining() at all, so it cannot see the printed maximum change.
    # A probe pointed at a suite that does not cover the clause reports NO BITE
    # for code that is perfectly correct.
    ("the shared redeploy step ignores the printed maximum of three",
     [(REDEPLOY, "        return self.max_units - len(self.chosen.get(player, []))",
       "        return 99")], CTAN),

    # Squad.check_min_enemy_distance was parameterised at its second consumer.
    # The Scout wrapper must still answer EXACTLY as it did.
    ("the Scout wrapper passes the wrong distance",
     [(SQUAD, "            all_tokens, SCOUT_MOVE_MIN_ENEMY_DISTANCE_IN, \"a Scout move\", \"rule 24.32\")",
       "            all_tokens, 1.0, \"a Scout move\", \"rule 24.32\")")], CTAN),

    # --- 8. the wiring ------------------------------------------------------
    # None of these can be seen by a behaviour test: it drives the controller
    # directly, so the controller answers. Only the source knows whether
    # main.py ever asks.
    ("main.py never fires Drain Life at the end of the Fight phase",
     [(MAIN, '''            drain_life_controller.resolve_end_of_fight_phase(
                {t.squad for t in state.tokens if t.squad is not None})''',
       "            pass  # drain life hook removed by probe")], CTAN),

    ("main.py never acknowledges Drain Life's dice",
     [(MAIN, "                        drain_life_controller.on_dice_acknowledged()",
       "                        pass  # dice ack removed by probe")], CTAN),

    # THE CALL, not the branch around it. Section 6 is a set difference over
    # the SOURCE - every controller main.py asks for pending_damage_choice must
    # also have a choose_damage_model call and a highlight - so hiding the
    # branch behind `elif False:` leaves the guard perfectly satisfied. What it
    # can see is the call going missing.
    ("Drain Life's allocation is never answered",
     [(MAIN, "                        drain_life_controller.choose_damage_model(clicked)",
       "                        pass  # click branch removed by probe")], WIRING),

    ("Grand Illusion is built but never joins the redeploy chain",
     [(MAIN, "            _solid_image_step, prince_of_corsairs_step, grand_illusion_step)",
       "            _solid_image_step, prince_of_corsairs_step)")], CTAN),

    ("the panel never offers Transdimensional Displacement",
     [(os.path.join("game", "ui", "action_panel.py"),
       "            if movement_controller.can_transdimensional_displacement():",
       "            if False:")], CTAN),
]


BASE = {}
for _suite in SUITES:
    got, total, text = run(_suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:%s%s" % (_suite, NL, text[-2000:]))
        raise SystemExit(2)
    BASE[_suite] = total - got
    print("baseline %-34s %s/%s (%d red)" % (_suite, got, total, total - got))
print()

bad = 0
for label, edits, suite in PROBES:
    originals = {path: read(path) for path, _, _ in edits}
    ok = True
    for path, new, old in edits:
        src = read(path)
        if src.count(new) != 1:
            print("  SKIP     %s: anchor not unique in %s (%d)"
                  % (label, path, src.count(new)))
            ok = False
            break
        write(path, src.replace(new, old))
    try:
        if not ok:
            bad += 1
            continue
        got, tot, out = run(suite)
        red = None if got is None else tot - got
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif red > BASE[suite]:
            verdict, detail = "BITES", "%s/%s (%d red)" % (got, tot, red)
        else:
            verdict, detail = "NO BITE", "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
            bad += 1
        print("  %-8s %s [%s]: %s" % (verdict, label, suite, detail))
        if red is not None and red > BASE[suite]:
            for line in out.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:104])
                    break
    finally:
        for path, text in originals.items():
            write(path, text)

print()
print("%d probe(s) did not bite" % bad if bad else "every probe bit")
raise SystemExit(1 if bad else 0)
