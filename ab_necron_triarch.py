"""A/B probes for Etappe 4 - Triarch Praetorians, Triarch Stalker.

Each probe restores ONE printed clause to a pre-fix state AT THE SOURCE and
must make the suite that covers it go red. A probe that does not bite is a
finding about the TEST, not an all-clear.

A NOTE ON THE SHARED HEAD. game/cover_denial.py is an extraction at the second
consumer, and the Etappe 3 lesson says a probe on a shared base should be made
to fail against BOTH carriers' suites - otherwise the drift the extraction
exists to prevent is invisible from one side. That cannot be done here, and the
reason is a finding in itself: the Defiler's Barrage of Filth had NO
behavioural test anywhere in this repo before this stage. Three source-guard
lines in test_death_guard_datasheets.py pinned that it is BUILT, FED and
CLEARED, and nothing ever drove it. test_necron_triarch.py section 7 is now its
only behavioural coverage, and the probes below that break the shared base
therefore bite exactly one suite - stated rather than papered over.

Run these ALONE. A probe rewrites the file it probes and restores it in a
`finally`; a suite, measurement or commit started alongside one reads the
mutated tree (see the probe-runs-are-exclusive note, and commit 412dc4a).
"""
import io
import os
import re
import shutil
import subprocess
import sys

SUITE = "test_necron_triarch.py"
SHEETS = "test_necron_datasheets.py"

PROBES = [
    # --- the collision sweep -----------------------------------------------
    # THE MISTAKE THIS STAGE EXISTS TO AVOID, in its exact shape: a printed
    # name that already had a class gets a twin instead of being shared. Every
    # characteristic line in section 2 passes against the twin; only the
    # identity line and the per-wielder BS line fail, which is why both are
    # written.
    ("the particle caster is FORKED instead of shared with the Wraiths",
     [("game/weapons.py",
       "class TransdimensionalBeamerProfile(WeaponProfile):",
       "class TriarchParticleCasterProfile(WeaponProfile):\n"
       "    name = \"Particle Caster\"\n"
       "    weapon_type = RANGED\n"
       "    range_in = 12\n"
       "    attacks = 3\n"
       "    strength = 5\n"
       "    ap = 0\n"
       "    damage = 1\n"
       "    devastating_wounds = True\n"
       "    pistol = True\n"
       "\n"
       "\n"
       "class TransdimensionalBeamerProfile(WeaponProfile):"),
      ("game/factions/necrons.py",
       "                      with_weapons=[ParticleCasterProfile, VoidbladeProfile],",
       "                      with_weapons=[TriarchParticleCasterProfile, VoidbladeProfile],"),
      ("game/factions/necrons.py",
       "    RodOfCovenantRangedProfile,",
       "    RodOfCovenantRangedProfile,\n    TriarchParticleCasterProfile,")],
     [SUITE]),

    # ...and its mirror: a per-weapon BS override that is NOT printed would
    # make the fork look necessary. The shredder's 2+ is the only printed one.
    ("the particle shredder loses its printed BS 2+ override",
     [("game/weapons.py",
       '    ballistic_skill = "2+"          # printed on the weapon, BETTER than the '
       "Stalker's own 3+",
       "    # ballistic_skill deliberately dropped by the probe")],
     [SUITE]),

    # The heat ray read as TWO GUNS rather than one entry with two modes -
    # which would let the Stalker fire both in the same activation (04.01).
    ("the heat ray's two modes become two separate guns",
     [("game/weapons.py",
       "    overcharge_profile = HeatRayFocusedProfile",
       "    # overcharge_profile deliberately dropped by the probe"),
      # The probe has to import what it adds, or the datasheet module raises a
      # NameError and the suite ABORTS instead of going red - a probe that
      # crashes says nothing about which assurance broke.
      ("game/factions/necrons.py",
       "    HeatRayDispersedProfile,",
       "    HeatRayDispersedProfile,\n    HeatRayFocusedProfile,"),
      ("game/factions/necrons.py",
       "                           [HeatRayDispersedProfile, StalkersForelimbsProfile],",
       "                           [HeatRayDispersedProfile, HeatRayFocusedProfile,\n"
       "                            StalkersForelimbsProfile],")],
     [SUITE]),

    # --- Relentless Combatants, clause 1: the Charge re-roll ---------------
    ("Relentless Combatants never offers a Charge re-roll at all",
     [("game/relentless_combatants.py",
       "        squad = self.charging_squad() if squad is None else squad",
       "        return False\n"
       "        squad = self.charging_squad() if squad is None else squad")],
     [SUITE]),

    # THE DECISION BOUNDARY, both directions. Each half of the AI rule is
    # neutralised on its own, because a probe that removes the whole verdict
    # cannot tell which half was load-bearing.
    ("...the AI re-rolls even a charge that already REACHED something",
     [("game/relentless_combatants.py",
       "        if self.charge_controller.targets_reachable_with(rolled):\n"
       "            if squad.owner in self.auto_players or self.decision_manager is None:\n"
       "                return False",
       "        if False:\n"
       "            pass")],
     [SUITE]),

    ("...or never re-rolls a failed one",
     [("game/relentless_combatants.py",
       "        if squad.owner in self.auto_players or self.decision_manager is None:\n"
       "            return bool(self._reroll(squad, rolled))",
       "        if squad.owner in self.auto_players or self.decision_manager is None:\n"
       "            return False")],
     [SUITE]),

    # NEVER OFFER WHAT CANNOT BUY ANYTHING - here it is also the honest
    # answer, since the charge is already lost on any roll.
    ("...a hopeless charge is offered a re-roll anyway",
     [("game/relentless_combatants.py",
       "        elif not self.charge_controller.targets_reachable_with(MAX_CHARGE_ROLL_TOTAL):",
       "        elif False:")],
     [SUITE]),

    # THE REPORTED INFINITE LOOP. Declining leaves exactly the board that
    # produced the question, so without the claim the next click asks again.
    ("...the offer is not claimed once per roll, so declining asks again",
     [("game/relentless_combatants.py",
       "        if not self.dice_manager.claim_reroll_offer(RELENTLESS_COMBATANTS_LABEL):\n"
       "            return False",
       "        # claim deliberately dropped by the probe")],
     [SUITE]),

    # "MUST BE RE-ROLLED IN FULL" (15.02's own wording for a Charge roll).
    ("...only one die of the Charge roll is re-rolled",
     [("game/relentless_combatants.py",
       "        if not self.dice_manager.reroll_all():",
       "        if not self.dice_manager.reroll_die(0):")],
     [SUITE]),

    # THE ONE-INSTANT WINDOW: acknowledge() clears pending_values and
    # reroll_all() then refuses, so an offer one line later cannot be taken.
    ("...the offer is made AFTER the roll is acknowledged",
     [("main.py",
       "                        if dice_manager.roll_kind == CHARGE_ROLL:\n"
       "                            relentless_combatants_controller.maybe_offer_charge_reroll()\n"
       "                            if decision_manager.is_pending:\n"
       "                                continue\n"
       "                        dice_manager.acknowledge()",
       "                        dice_manager.acknowledge()\n"
       "                        relentless_combatants_controller.maybe_offer_charge_reroll()")],
     [SUITE]),

    # --- Relentless Combatants, clause 2: charging after a Fall Back -------
    ("the Fall Back exemption is not registered in move_exceptions",
     [("game/move_exceptions.py",
       "            or squad_has_relentless_combatants(squad)\n",
       "")],
     [SUITE]),

    # THE WRONG HALF of rule 09.07. The printed text says "declare a charge",
    # not "shoot" - that difference is the whole reason move_exceptions keeps
    # three separate lists.
    ("...it lifts the SHOOTING ban instead of the charge one",
     [("game/move_exceptions.py",
       "            or squad_has_relentless_combatants(squad)\n"
       "            or any(_flag(squad, name) for name in CHARGE_AFTER_FALL_BACK_FLAGS))",
       "            or any(_flag(squad, name) for name in CHARGE_AFTER_FALL_BACK_FLAGS))"),
      ("game/move_exceptions.py",
       "            or squad_has_agile_combatant(squad)",
       "            or squad_has_agile_combatant(squad)\n"
       "            or squad_has_relentless_combatants(squad)")],
     [SUITE]),

    # --- Targeting Relay ----------------------------------------------------
    # THE MARK NEVER REACHES THE COVER TEST - the "built but never fed" shape,
    # and the reason section 6 measures through the real ShootingController
    # rather than at the controller.
    ("Targeting Relay's mark never reaches the cover test",
     [("game/shooting.py",
       "        if cover_denial.denied(target_squad, (self.barrage_of_filth, self.targeting_relay)):",
       "        if cover_denial.denied(target_squad, (self.barrage_of_filth,)):")],
     [SUITE]),

    # ONE READER for the denial: a fold that stops at the first source is the
    # same bug wearing a different hat.
    ("...denied() folds only the first source",
     [("game/cover_denial.py",
       "    return any(s is not None and s.denies_cover(squad) for s in sources or ())",
       "    first = (sources or (None,))[0]\n"
       "    return first is not None and first.denies_cover(squad)")],
     [SUITE]),

    # "UNTIL THE END OF THE PHASE" - one clock, and it is the shorter one.
    ("...the mark is never cleared, so it lasts the whole battle",
     [("game/cover_denial.py",
       "        self._stripped.clear()",
       "        pass")],
     [SUITE]),

    # The options must be TAGGED with their unit, or the choice cannot be
    # answered on the board.
    ("...the prompt's options carry no unit, so no board pick is possible",
     [("game/cover_denial.py",
       "        options = [(\"%s: %s\" % (self.label, t.name),\n"
       "                    (lambda target=t: self._use(shooter_squad, target)), t)\n"
       "                   for t in candidates]",
       "        options = [(\"%s: %s\" % (self.label, t.name),\n"
       "                    (lambda target=t: self._use(shooter_squad, target)))\n"
       "                   for t in candidates]")],
     [SUITE]),

    # "SELECT ONE ENEMY UNIT" - a friendly unit is never a candidate.
    ("...a friendly unit becomes a candidate",
     [("game/cover_denial.py",
       "        candidates = [s for s in target_squads or ()\n"
       "                      if s is not None and s.owner != shooter_squad.owner]",
       "        candidates = [s for s in target_squads or () if s is not None]")],
     [SUITE]),

    ("...main.py never feeds it from the shooting hook",
     [("main.py",
       "    shooting_controller.on_squad_finished_shooting.append(\n"
       "        targeting_relay_controller.on_squad_finished_shooting)",
       "    pass")],
     [SUITE]),

    ("...and never clears it at the phase boundary",
     [("main.py",
       "        targeting_relay_controller.reset_phase()\n",
       "")],
     [SUITE]),

    # --- the shared head ----------------------------------------------------
    # A subclass that forgets a knob must fail LOUDLY at construction rather
    # than offering an unnamed choice.
    ("a subclass missing its knobs fails silently instead of loudly",
     [("game/cover_denial.py",
       "        assert self.flag and self.label, (\n"
       "            \"a %s subclass must set both `flag` and `label`\" % type(self).__name__)",
       "        pass")],
     [SUITE]),

    # BEHAVIOUR-NEUTRALITY of the extraction, from the Defiler's side: its
    # prompt and log strings are the ones it always produced.
    ("the Defiler's ability logs under the wrong name after the extraction",
     [("game/barrage_of_filth.py",
       '    label = "Barrage of Filth"',
       '    label = "Cover Denial"')],
     [SUITE]),

    # --- datasheet-level -----------------------------------------------------
    ("the Stalker takes the big tracked-hull base instead of its own",
     [("game/units.py",
       "    base_radius_in = 1.575          # 80 mm - a table size, see above",
       "    base_radius_in = 2.1            # probe: the big tracked-hull size")],
     [SUITE]),

    ("a Triarch sprite key goes missing",
     [("game/sprites.py",
       '    "Triarch Stalker": "Triarch Stalker",\n',
       "")],
     [SUITE, SHEETS]),

    ("the Praetorians' wargear swap keeps the rod of covenant",
     [("game/factions/necrons.py",
       "                      replaces=(RodOfCovenantRangedProfile, RodOfCovenantMeleeProfile),",
       "                      replaces=RodOfCovenantRangedProfile,")],
     [SUITE]),
]


def clear_cache():
    """The documented __pycache__ race: a probe writes and restores inside one
    second, so a stale .pyc makes the NEXT run report the previous world."""
    for root, dirs, _files in os.walk("."):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)


def run(suite):
    if not os.path.exists(suite):
        return None, None
    clear_cache()
    out = subprocess.run([sys.executable, suite], capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    m = re.search(r"(\d+)/(\d+) checks passed", out.stdout + out.stderr)
    if not m:
        return None, None          # crashed - counts as red
    return int(m.group(1)), int(m.group(2))


baselines = {}
for _, _, suites in PROBES:
    for s in suites:
        if s not in baselines:
            baselines[s] = run(s)
print("baselines:")
for s, (g, t) in baselines.items():
    print("   %-40s %s" % (s, "MISSING" if g is None else "%d/%d" % (g, t)))
print()

bad = []
for label, edits, suites in PROBES:
    originals = {}
    ok = True
    for path, old, new in edits:
        src = io.open(path, encoding="utf-8").read()
        if src.count(old) != 1:
            print("NO ANCHOR (%d)  %s" % (src.count(old), label))
            ok = False
            break
        if path not in originals:
            originals[path] = src
        io.open(path, "w", encoding="utf-8", newline="\n").write(src.replace(old, new, 1))
    if not ok:
        for p, s in originals.items():
            io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        bad.append(label)
        continue
    try:
        verdicts = []
        for s in suites:
            base = baselines.get(s, (None, None))[0]
            got, tot = run(s)
            if base is None:
                verdicts.append((s, "NO SUITE", ""))
            elif got is None:
                verdicts.append((s, "BITES", "(crashed - counts as red)"))
            elif got < base:
                verdicts.append((s, "BITES", "%d/%d" % (got, tot)))
            else:
                verdicts.append((s, "NO BITE", "%d/%d" % (got, tot)))
    finally:
        for p, s in originals.items():
            io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    bit = any(v == "BITES" for _, v, _ in verdicts)
    detail = "  ".join("%s %s" % (v, d) for _s, v, d in verdicts)
    print("%-9s %-62s %s" % ("bites" if bit else "NO BITE", label[:62], detail))
    if not bit:
        bad.append(label)

clear_cache()
print("\nprobes: %d, all biting: %s" % (len(PROBES), not bad))
for b in bad:
    print("  !", b)
raise SystemExit(1 if bad else 0)
