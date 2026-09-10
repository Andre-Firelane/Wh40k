"""A/B probes for Etappe 5 - the CANOPTEK batch.

Each probe restores ONE printed clause to a pre-fix state AT THE SOURCE and
must make the suite that covers it go red. A probe that does not bite is a
finding about the TEST, not an all-clear.

THREE OF THESE PROBE A SHARED BASE, and the Etappe 3 lesson applies in full
this time: game/pinned.py, game/fnp_aura.py and game/retinue.py each have TWO
carriers with a suite apiece, so a probe on the shared half is aimed at BOTH -
a change that only one carrier's suite notices is exactly the drift the
extraction exists to prevent.

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

SUITE = "test_necron_canoptek.py"
RANK = "test_necron_rank_and_file.py"
AELDARI = "test_aeldari_gun_tanks.py"
NEKROSOR = "test_necron_destroyer_cult.py"
SHEETS = "test_necron_datasheets.py"

PROBES = [
    # --- 1. the collision sweep, in all THREE of its verdicts ---------------
    # THE FORK. "Particle beamer" is printed on two datasheets with different
    # Strength, so it needs two classes. Sharing one is the mistake in the
    # other direction from Etappe 4's, and only a line that compares the two
    # ROWS can see it - an identity line would pass with either.
    ("the two particle beamers are SHARED instead of forked",
     [("game/factions/necrons.py",
       "with_weapons=[ParticleBeamerS6Profile, ParticleBeamerS6Profile],",
       "with_weapons=[ParticleBeamerS5Profile, ParticleBeamerS5Profile],")],
     [SUITE]),

    # THE INHERIT. A twin gun written as a COPY passes every characteristic
    # line and stops tracking its parent the first time the parent moves.
    ("the twin gauss reaper is a COPY of its parent instead of a subclass",
     [("game/weapons.py",
       "class TwinGaussReaperProfile(GaussReaperProfile):\n",
       "class TwinGaussReaperProfile(WeaponProfile):\n"
       "    weapon_type = RANGED\n"
       "    range_in = GaussReaperProfile.range_in\n"
       "    attacks = GaussReaperProfile.attacks\n"
       "    strength = GaussReaperProfile.strength\n"
       "    ap = GaussReaperProfile.ap\n"
       "    damage = GaussReaperProfile.damage\n")],
     [SUITE]),

    # --- 2. Chittering Swarm: two clauses pointing opposite ways ------------
    ("the Scarabs' OC is never SET to 1 near a Cryptek",
     [("game/chittering_swarm.py",
       "    return CHITTERING_SWARM_OC\n\n\ndef worsen_enemy_oc",
       "    return printed\n\n\ndef worsen_enemy_oc")],
     [SUITE]),

    ("...and the enemy half never worsens anything",
     [("game/chittering_swarm.py",
       "            return max(CHITTERING_SWARM_OC, printed - CHITTERING_SWARM_ENEMY_PENALTY)",
       "            return printed")],
     [SUITE]),

    # The FLOOR read as a clamp rather than as a limit on worsening - the
    # reading Scabrous Soulrot already records, and the one that quietly
    # raises a printed OC 0 model.
    ("the OC floor is read as a clamp, so a printed 0 is raised to 1",
     [("game/chittering_swarm.py",
       "    if model is None or printed <= 0:\n        return printed",
       "    if model is None:\n        return printed")],
     [SUITE]),

    # --- 3. Self-destruction: the three bands -------------------------------
    ("a roll of 1 pays out as if it were the middle band",
     [("game/scarab_self_destruction.py",
       "SELF_DESTRUCTION_LOW_BAND = 2",
       "SELF_DESTRUCTION_LOW_BAND = 1")],
     [SUITE]),

    ("the +1 against a VEHICLE is dropped",
     [("game/scarab_self_destruction.py",
       "SELF_DESTRUCTION_VEHICLE_BONUS = 1",
       "SELF_DESTRUCTION_VEHICLE_BONUS = 0")],
     [SUITE]),

    # --- 4. the Spyders -----------------------------------------------------
    # THE VEHICLE HALF of the claw array. Widening it to any NECRONS unit
    # leaves every other line of section 6 passing.
    ("the Fabricator Claw Array covers any NECRONS unit, not just VEHICLES",
     [("game/spyder_wargear.py",
       "    unit_predicate=is_necron_vehicle_unit,",
       "    unit_predicate=is_necron_unit,")],
     [SUITE]),

    # THE MORTAL-ONLY HALF of the Gloom Prism - the clause that separates it
    # from its neighbour on the same model. Aimed at THIS suite alone, and
    # deliberately: it neutralises a knob on the Gloom Prism's own instance,
    # which the Nullstone field does not share. (The first version declared it
    # against both suites and reported NO BITE on the other - a finding about
    # the PROBE, and the reason the shared-base probe below exists.)
    ("the Gloom Prism covers ORDINARY wounds too",
     [("game/spyder_wargear.py",
       "    mortal_or_psychic_only=True,",
       "    mortal_or_psychic_only=False,")],
     [SUITE]),

    # THE SHARED BASE's half of the same clause: the knob READER, in
    # game/fnp_aura.py. Both carriers set it, so both suites must go red.
    ("the shared aura ignores mortal_or_psychic_only entirely",
     [("game/fnp_aura.py",
       "        if self.mortal_or_psychic_only and not (mortal or psychic):",
       "        if False:")],
     [SUITE, NEKROSOR]),

    # THE SHARED BASE, aimed at BOTH carriers: a dead bearer that keeps
    # projecting is the per-frame stamping bug this repo has paid for twice
    # (rule 12: remove_dead_models() runs once a frame).
    ("a dead aura bearer keeps projecting for one more frame",
     [("game/fnp_aura.py",
       "                and not t.is_dead()\n",
       "")],
     [SUITE, NEKROSOR]),

    ("the Canoptek Swarm returns ONE model however many Spyders there are",
     [("game/canoptek_swarm.py",
       "        wanted = min(len(spyder_models(spyders)), len(dead))",
       "        wanted = min(1, len(dead))")],
     [SUITE]),

    ("...and it offers a return to a unit at full strength",
     [("game/canoptek_swarm.py",
       "            if not getattr(squad, \"destroyed_models\", None):\n                continue",
       "            pass")],
     [SUITE]),

    # --- 5. Sentinel Construct ----------------------------------------------
    ("Sentinel Construct overwatches on the Hexmark's 2+",
     [("game/sentinel_construct.py",
       "SENTINEL_CONSTRUCT_HIT_THRESHOLD = 5",
       "SENTINEL_CONSTRUCT_HIT_THRESHOLD = 2")],
     [SUITE]),

    ("...and the shooting fold never asks it",
     [("game/shooting.py",
       "sentinel_construct.snap_hit_threshold(self.active_squad)",
       "None")],
     [SUITE]),

    # --- 6. the reanimation boosts ------------------------------------------
    ("the atomiser beam's 3\" is not measured",
     [("game/reanimation_boost.py",
       "NANOSCARAB_RANGE_IN = 3.0",
       "NANOSCARAB_RANGE_IN = 300.0")],
     [SUITE]),

    ("the projector fires more than once in a battle round",
     [("game/reanimation_boost.py",
       "                if self._used.get(id(t)) != this_round]",
       "                if True]")],
     [SUITE]),

    # --- 7. Harassment Swarm and Weapon Sentinels ---------------------------
    ("Harassment Swarm hits MONSTERS and VEHICLES too",
     [("game/harassment_swarm.py",
       "def is_exempt(squad):",
       "def is_exempt(squad):\n    return False\n\n\ndef _unreachable(squad):")],
     [SUITE]),

    ("...and its -1 never reaches the FIGHT step",
     [("game/fight.py",
       "harassment_swarm.hit_modifiers(self.fighting_squad)",
       "()")],
     [SUITE]),

    # THE NEW NOUN: the first ignore-modifier filter this engine has put on the
    # WOUND roll. Dropping it leaves the Hit half - and every predicate line -
    # passing.
    ("Weapon Sentinels filters the HIT roll only, not the WOUND roll",
     [("game/shooting.py",
       "weapon_sentinels.filtered(modifiers, self.active_squad, target_squad)",
       "modifiers")],
     [SUITE]),

    ("...and it drops the IMPROVING modifiers instead of the worsening ones",
     [("game/weapon_sentinels.py",
       "    return [m for m in modifiers if m.amount <= 0]",
       "    return [m for m in modifiers if m.amount >= 0]")],
     [SUITE]),

    ("...and its 12\" is not measured",
     [("game/weapon_sentinels.py",
       "WEAPON_SENTINELS_RANGE_IN = 12.0",
       "WEAPON_SENTINELS_RANGE_IN = 1200.0")],
     [SUITE]),

    # --- 8. the Geomancer ---------------------------------------------------
    # THE CLOCK. Both pins are pins; only the boundary tells them apart, and
    # getting it wrong halves or doubles the Geomancer's rule.
    ("the Geomancer's pin runs on the Night Spinner's TURN clock",
     [("game/tectonic_reverberations.py",
       "            target, owner, until=pinned_status.UNTIL_MOVEMENT,",
       "            target, owner, until=pinned_status.UNTIL_TURN,")],
     [SUITE]),

    # THE SHARED BASE again, and this probe must redden the AELDARI suite as
    # well - game/pinned.py's other carrier is the Night Spinner.
    ("a pinned unit takes no Move penalty",
     [("game/pinned.py",
       "PINNED_MOVE_PENALTY = 2",
       "PINNED_MOVE_PENALTY = 0")],
     [SUITE, AELDARI]),

    ("...and no Charge penalty",
     [("game/pinned.py",
       "PINNED_CHARGE_PENALTY = 2",
       "PINNED_CHARGE_PENALTY = 0")],
     [SUITE, AELDARI]),

    ("an ENSNARED unit can be pinned after all",
     [("game/pinned.py",
       "    if elemental_ensnarement.blocks_pinning(squad):",
       "    if False:")],
     [SUITE]),

    # OBELISK NODE CONTROL, both live conditions.
    ("Obelisk Node Control blocks from an objective the OPPONENT controls",
     [("game/obelisk_node_control.py",
       "        if getattr(objective, \"controlled_by\", None) != squad.owner:\n            continue",
       "        pass")],
     [SUITE]),

    ("...and it blocks the bearer's OWN reserves too",
     [("game/obelisk_node_control.py",
       "        if getattr(bearer.squad, \"owner\", None) == owner:\n            continue",
       "        pass")],
     [SUITE]),

    # THE MODEL, not the unit - the half that only shows once he is attached.
    ("...and it projects from the bearer's whole UNIT",
     [("game/obelisk_node_control.py",
       "        if not getattr(token.profile, \"obelisk_node_control\", False):\n            continue",
       "        if not any(getattr(m.profile, \"obelisk_node_control\", False)\n"
       "                   for m in getattr(squad, \"models\", ()) or ()):\n            continue")],
     [SUITE]),

    ("the ingress predicate never asks it",
     [("game/ingress.py",
       "obelisk_node_control.blocks_arrival(",
       "False and obelisk_node_control.blocks_arrival(")],
     [SUITE]),

    # VANGUARD PROTOCOLS is a measured no-op, so a probe that removes its
    # EFFECT cannot bite. What can go wrong is the QUALIFIER - granting it to
    # any host at all - and that is what this aims at.
    ("Vanguard Protocols applies to any host, not only CANOPTEK MACROCYTES",
     [("game/vanguard_protocols.py",
       "MACROCYTES_KEYWORD = \"MACROCYTES\"",
       "MACROCYTES_KEYWORD = \"NECRONS\"")],
     [SUITE]),

    # --- 9. the retinue extraction ------------------------------------------
    # THE SHARED BASE, third instance: both carriers' suites must notice.
    ("the Tomb Crawlers' host is required to be INFANTRY after all",
     [("game/retinue.py",
       "    (\"TOMB CRAWLERS\", \"Canoptek Retinue\", False),",
       "    (\"TOMB CRAWLERS\", \"Canoptek Retinue\", True),")],
     [SUITE]),

    ("the panel heading names the WRONG printed rule",
     [("game/formations.py",
       "    carrier = retinue.carrier_of(joiner)",
       "    carrier = None")],
     [SUITE]),

    # THE PRE-EXISTING BUG THIS STAGE FOUND. 19.01's one-per-role check read
    # leader_components(), which excludes the RETINUE role, so BOTH printed
    # parentheses went unenforced for two stages. It has to redden the
    # Cryptothralls suite too - that is where the false claim was made.
    ("19.01's one-per-role check cannot see a RETINUE component",
     [("game/attached_units.py",
       "        already = [c for c in components(bodyguard_squad) if c.role == role]",
       "        already = [c for c in leader_components(bodyguard_squad)\n"
       "                   if c.role == role]")],
     [SUITE, RANK]),
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
    # A probe aimed at more than one suite must redden EVERY one of them - the
    # whole point of a shared base is that its carriers cannot drift apart.
    bit = all(v == "BITES" for _s, v, _d in verdicts)
    detail = "  ".join("%s %s" % (v, d) for _s, v, d in verdicts)
    print("%-9s %-60s %s" % ("bites" if bit else "NO BITE", label[:60], detail))
    if not bit:
        bad.append(label)

clear_cache()
print("\nprobes: %d, all biting: %s" % (len(PROBES), not bad))
for b in bad:
    print("  !", b)
raise SystemExit(1 if bad else 0)
