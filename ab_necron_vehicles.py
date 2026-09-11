"""A/B probes for stage 8 of the Necron backfill - the three grav skimmers.

Each probe restores ONE clause of the pre-fix world AT THE SOURCE, runs the
suite that should notice, and puts it back. A probe that does NOT go red is a
finding about the TEST, so this file exits non-zero if any survives.

SIX SUITES, and the split is the point:

  * test_necron_vehicles.py     the new behaviour
  * test_wave_serpent.py        the OTHER carrier of game/strength_over_toughness.py
  * test_necron_abilities.py    the THIRD carrier of it (Guardian Protocols)
  * test_kill_rig.py            the datasheet the transport_requires fix affects
  * test_necron_ctan.py         the OTHER carrier of game/mortal_wound_sweep.py
  * test_event_chain_wiring.py  the source-level set differences
  * test_return_placement.py    section 7, the doors into reanimate()

The S>T extraction has THREE carriers, so its probes list three suites and are
counted three times. A break that only one of them notices is exactly the drift
the extraction exists to prevent - and that drift is not hypothetical here: for
two whole stages guardian_protocols.py's docstring CLAIMED the arithmetic was
shared while both files carried their own copy.

COUNTING RED, NOT GREEN: a probe that changes how many checks a guard runs
would make "fewer passed" meaningless.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)

SOT = os.path.join("game", "strength_over_toughness.py")
CARRIER = os.path.join("game", "carrier_wave.py")
OBJCTRL = os.path.join("game", "objective_control.py")
ARCING = os.path.join("game", "malevolent_arcing.py")
SWEEP = os.path.join("game", "mortal_wound_sweep.py")
REPAIR = os.path.join("game", "repair_barge.py")
ORB = os.path.join("game", "resurrection_orb.py")
TRANSPORT = os.path.join("game", "transport.py")
FORMATIONS = os.path.join("game", "formations.py")
UNITS = os.path.join("game", "units.py")
WEAPONS = os.path.join("game", "weapons.py")
SHOOTING = os.path.join("game", "shooting.py")
MAIN = "main.py"

VEH = "test_necron_vehicles.py"
SERPENT = "test_wave_serpent.py"
ABIL = "test_necron_abilities.py"
KILLRIG = "test_kill_rig.py"
CTAN = "test_necron_ctan.py"
WIRING = "test_event_chain_wiring.py"
RETPLACE = "test_return_placement.py"
SUITES = (VEH, SERPENT, ABIL, KILLRIG, CTAN, WIRING, RETPLACE)


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
# Anchor -> replacement: the anchor is what is there NOW, the replacement is
# the pre-fix (or plain wrong) world.

# --- the S>T extraction ---
_GT = "        return toughness is not None and strength > toughness"
_GT_OFF = "        return toughness is not None and strength >= toughness"

_SIGN = "    penalty = 1          # every printed line says \"subtract 1\""
_SIGN_OFF = "    penalty = -1         # every printed line says \"subtract 1\""

_MELEE = "        if melee and shield.ranged_only:"
_MELEE_OFF = "        if False and shield.ranged_only:"

_EXTRA = "        if not self.extra_condition(target_squad):"
_EXTRA_OFF = "        if False and not self.extra_condition(target_squad):"

_TOUGH = "        toughness = attached_unit_toughness(target_squad)"
_TOUGH_OFF = ("        toughness = getattr(target_squad.models[0].profile, "
              "'toughness', None) if target_squad.models else None")

_AQS_FLAG = '    flag = "advanced_quantum_shielding"'
_AQS_FLAG_OFF = '    flag = "no_such_flag_at_all"'

# --- Carrier Wave ---
_CW_ORDER = "    oc += carrier_wave.oc_bonus(model, all_tokens)"
_CW_ORDER_OFF = ""

_CW_WHOLE = ("        if any(edge_distance(m, bearer) <= CARRIER_WAVE_RANGE_IN"
             + NL + "               for m in squad.models if not m.is_dead()):")
_CW_WHOLE_OFF = ("        if all(edge_distance(m, bearer) <= CARRIER_WAVE_RANGE_IN"
                 + NL + "               for m in squad.models if not m.is_dead()):")

_CW_SELF = "    for bearer in bearers(all_tokens):"
_CW_SELF_OFF = ("    for bearer in bearers(all_tokens):"
                + NL + "        if bearer.squad is squad:"
                + NL + "            continue")

_CW_NECRONS = "    if not awakened_dynasty.is_necrons_unit(squad):"
_CW_NECRONS_OFF = ("    if not any(getattr(m.profile, 'reanimation_protocols', False)"
                   + NL + "               for m in squad.models):")

_CW_DEAD = ("    return [t for t in (all_tokens or ())"
            + NL + "            if getattr(t.profile, \"carrier_wave\", False) and not t.is_dead()]")
_CW_DEAD_OFF = ("    return [t for t in (all_tokens or ())"
                + NL + "            if getattr(t.profile, \"carrier_wave\", False)]")

# --- Malevolent Arcing ---
_ARC_FROZEN = "        armed.append((target_squad, self.arcing_candidates(attacking_squad, target_squad)))"
_ARC_FROZEN_OFF = "        armed.append((target_squad, None))"

_ARC_RANGE = "MALEVOLENT_ARCING_RANGE_IN = 3.0      # \"within 3\" of the target unit\""
_ARC_RANGE_OFF = "MALEVOLENT_ARCING_RANGE_IN = 24.0     # \"within 3\" of the target unit\""

_ARC_THRESH = "MALEVOLENT_ARCING_THRESHOLD = 5       # \"on a 5+\""
_ARC_THRESH_OFF = "MALEVOLENT_ARCING_THRESHOLD = 4       # \"on a 5+\""

_ARC_WEAPON = ("            if shooting is not None and not shooting.resolved_weapon_against("
               + NL + "                    MALEVOLENT_ARCING_WEAPON, target_squad):")
_ARC_WEAPON_OFF = ("            if False and not shooting.resolved_weapon_against("
                   + NL + "                    MALEVOLENT_ARCING_WEAPON, target_squad):")

_ARC_REACTIVE = "        if reactive:"
_ARC_REACTIVE_OFF = "        if False:"

_ARC_TARGET = "        out = [target_squad]"
_ARC_TARGET_OFF = "        out = []"

# --- the sweep's generalised queue ---
_QUEUE = "        self._bearer_queue = [(s, None) for s in eligible[1:]]"
_QUEUE_OFF = "        self._bearer_queue = []"

# --- Repair Barge ---
_RB_DELTA = "            if before is None or self._wound_total(squad) >= before:"
_RB_DELTA_OFF = "            if reanimation_protocols.recoverable_wounds(squad) <= 0:"

_RB_UNIT_LEDGER = "            if id(squad) in self._selected_this_turn:"
_RB_UNIT_LEDGER_OFF = "            if False:"

_RB_ARK_LEDGER = "            if id(ark) not in self._used_this_turn:"
_RB_ARK_LEDGER_OFF = "            if True:"

_RB_RANGE = "REPAIR_BARGE_RANGE_IN = 3.0"
_RB_RANGE_OFF = "REPAIR_BARGE_RANGE_IN = 60.0"

_RB_KEYWORD = "REPAIR_BARGE_KEYWORD = \"NECRON WARRIORS\""
_RB_KEYWORD_OFF = "REPAIR_BARGE_KEYWORD = \"NECRONS\""

_RB_PLACER = "    repair_barge_controller.placer = return_placement_controller"
_RB_PLACER_OFF = "    pass  # placer withheld"

# --- the orb ---
_ORB_BEARER = "        self._used_squads.add(id(squad))"
_ORB_BEARER_OFF = "        self._used_squads.add(id(target))"

_ORB_TARGETS = "            if any(edge_distance(a, b) <= self.range_in for a in mine for b in theirs):"
_ORB_TARGETS_OFF = "            if False:"

_ORB_PLACER = "    catacomb_orb_controller.placer = return_placement_controller"
_ORB_PLACER_OFF = "    pass  # catacomb placer withheld"

# --- the transport pools ---
_POOLS = ("    transport_pools = ((10, (\"NECRON WARRIORS\",)),"
          + NL + "                       (1, (\"NECRONS\", \"INFANTRY\", \"CHARACTER\")))")
_POOLS_OFF = "    transport_pools = ()"

_POOL_A = "    transport_pools = ((10, (\"NECRON WARRIORS\",)),"
_POOL_A_OFF = "    transport_pools = ((10, (\"NECRONS\",)),"

_POOL_EMBARKED = ("        if pools and not fits_pools(squad, pools, self.embarked_squads_in(transport_token)):")
_POOL_EMBARKED_OFF = "        if pools and not fits_pools(squad, pools):"

_POOL_1801 = ("    pools = getattr(transport_token.profile, \"transport_pools\", ())"
              + NL + "    if pools and not fits_pools(squad, pools, already_assigned):"
              + NL + "        errors.append(f\"{name} cannot transport {squad.name}.\")")
_POOL_1801_OFF = "    pass  # 18.01 never asked about pools"

# THE KILL RIG FIX - it must redden test_kill_rig.py, not only the new suite.
_REQUIRES_1801 = ("    required = getattr(transport_token.profile, \"transport_requires\", ())"
                  + NL + "    if required and not all(getattr(m.profile, kw, False)"
                  + NL + "                            for m in squad.models for kw in required):"
                  + NL + "        errors.append(f\"{name} cannot transport {squad.name}.\")")
_REQUIRES_1801_OFF = "    pass  # 18.01 never asked about transport_requires"

# --- weapons and profiles ---
_BLADE_SHARE = "                      with_weapons=[OverlordsBladeProfile],"
_BLADE_SHARE_OFF = "                      with_weapons=[type('ForkedBlade', (OverlordsBladeProfile,), {})],"

_STAFF_BS = ('against its base rather than against literals."""' + NL
             + '    ballistic_skill = "2+"')
_STAFF_BS_OFF = ('against its base rather than against literals."""' + NL
                 + '    pass')

_ANNI_WS = '    weapon_skill = "4+"             # armoured bulk, the row it shares with the Doomsday Ark and the Ghost Ark'
_ANNI_WS_OFF = '    weapon_skill = "3+"             # armoured bulk, the row it shares with the Doomsday Ark and the Ghost Ark'

_BASE = "    base_radius_in = 2.1            # printed 60 mm; the SAME hull as the Doomsday Ark, which carries this size already"
_BASE_OFF = "    base_radius_in = 1.181          # printed 60 mm; the SAME hull as the Doomsday Ark, which carries this size already"

# --- the new shooting seams ---
_ON_TARGET = ("        for listener in self.on_target_selected:"
              + NL + "            listener(self.active_squad, target_squad, reactive=self._reactive)")
_ON_TARGET_OFF = "        pass  # the attacker's own abilities are never told"

_RESOLVED = ("            for _model, _weapon in (pairs or ()):"
             + NL + "                self._resolved_weapon_names_this_activation.setdefault("
             + NL + "                    id(target_squad), set()).add(_weapon.name)")
_RESOLVED_OFF = "            pass  # nothing records which weapon fired at which target"


PROBES = [
    # ---- 1. the S>T extraction: every probe must redden ALL THREE carriers
    ("S>T compares with >= instead of >",
     [(SOT, _GT, _GT_OFF)], [VEH, SERPENT, ABIL]),
    ("the S>T penalty's sign is flipped",
     [(SOT, _SIGN, _SIGN_OFF)], [VEH, SERPENT, ABIL]),
    ("the ranged-only filter is dropped, so the shield reaches melee",
     [(SOT, _MELEE, _MELEE_OFF)], [VEH, SERPENT]),
    ("extra_condition() is ignored, so Guardian Protocols loses its NOBLE gate",
     [(SOT, _EXTRA, _EXTRA_OFF)], [ABIL]),
    ("Advanced Quantum Shielding reads a flag nothing sets",
     [(SOT, _AQS_FLAG, _AQS_FLAG_OFF)], [VEH]),

    # ---- 2. Carrier Wave
    ("Carrier Wave never reaches effective_oc()",
     [(OBJCTRL, _CW_ORDER, _CW_ORDER_OFF)], [VEH]),
    ("Carrier Wave needs the WHOLE unit within 6\", not one model",
     [(CARRIER, _CW_WHOLE, _CW_WHOLE_OFF)], [VEH]),
    ("Carrier Wave excludes the bearer's own unit ('another', which it does not say)",
     [(CARRIER, _CW_SELF, _CW_SELF_OFF)], [VEH]),
    ("'a friendly NECRONS unit' read off the per-model flag instead of the datasheet",
     [(CARRIER, _CW_NECRONS, _CW_NECRONS_OFF)], [VEH]),
    ("a DEAD Barge keeps radiating",
     [(CARRIER, _CW_DEAD, _CW_DEAD_OFF)], [VEH]),

    # ---- 3. Malevolent Arcing
    ("the candidates are re-derived at payment instead of frozen at selection",
     [(ARCING, _ARC_FROZEN, _ARC_FROZEN_OFF)], [VEH]),
    ("the 3\" is measured from the BEARER's range knob instead of the target",
     [(ARCING, _ARC_RANGE, _ARC_RANGE_OFF)], [VEH]),
    ("the gate is 4+ instead of 5+",
     [(ARCING, _ARC_THRESH, _ARC_THRESH_OFF)], [VEH]),
    ("'for this model's twin tesla destructor' is dropped",
     [(ARCING, _ARC_WEAPON, _ARC_WEAPON_OFF)], [VEH]),
    ("Fire Overwatch arms it - 'in YOUR Shooting phase' ignored",
     [(ARCING, _ARC_REACTIVE, _ARC_REACTIVE_OFF)], [VEH]),
    ("the TARGET unit is not itself a candidate",
     [(ARCING, _ARC_TARGET, _ARC_TARGET_OFF)], [VEH]),
    ("the sweep's queue loses its (squad, candidates) pairs",
     [(SWEEP, _QUEUE, _QUEUE_OFF)], [CTAN]),
    ("the select-targets listener list is never called",
     [(SHOOTING, _ON_TARGET, _ON_TARGET_OFF)], [VEH]),
    ("nothing records which weapon resolved against which target",
     [(SHOOTING, _RESOLVED, _RESOLVED_OFF)], [VEH]),

    # ---- 4. Repair Barge
    ("the delta trigger becomes 'has EVER lost wounds'",
     [(REPAIR, _RB_DELTA, _RB_DELTA_OFF)], [VEH]),
    ("the per-UNIT once-per-turn ledger is dropped",
     [(REPAIR, _RB_UNIT_LEDGER, _RB_UNIT_LEDGER_OFF)], [VEH]),
    ("the per-ARK once-per-turn ledger is dropped",
     [(REPAIR, _RB_ARK_LEDGER, _RB_ARK_LEDGER_OFF)], [VEH]),
    ("the 3\" becomes 60\"",
     [(REPAIR, _RB_RANGE, _RB_RANGE_OFF)], [VEH]),
    ("'NECRON WARRIORS units' widens to any NECRONS unit",
     [(REPAIR, _RB_KEYWORD, _RB_KEYWORD_OFF)], [VEH]),
    ("the fourth reanimate() door gets no placer",
     [(MAIN, _RB_PLACER, _RB_PLACER_OFF)], [VEH, RETPLACE]),

    # ---- 5. the orb
    ("the once-per-battle ledger keys the TARGET again, not the bearer",
     [(ORB, _ORB_BEARER, _ORB_BEARER_OFF)], [VEH]),
    ("the Barge's orb finds no targets at all",
     [(ORB, _ORB_TARGETS, _ORB_TARGETS_OFF)], [VEH]),
    ("the Barge's orb gets no placer of its own",
     [(MAIN, _ORB_PLACER, _ORB_PLACER_OFF)], [VEH]),

    # ---- 6. the transport pools, and the Kill Rig fix
    ("the Ghost Ark declares no sub-pools, so 10 Lychguard fit",
     [(UNITS, _POOLS, _POOLS_OFF)], [VEH]),
    ("pool A widens from NECRON WARRIORS to NECRONS",
     [(UNITS, _POOL_A, _POOL_A_OFF)], [VEH]),
    ("already-embarked loads stop counting against the pools",
     [(TRANSPORT, _POOL_EMBARKED, _POOL_EMBARKED_OFF)], [VEH]),
    ("18.01 stops asking about the pools",
     [(FORMATIONS, _POOL_1801, _POOL_1801_OFF)], [VEH]),
    ("18.01 stops asking about transport_requires - the Kill Rig bug restored",
     [(FORMATIONS, _REQUIRES_1801, _REQUIRES_1801_OFF)], [VEH, KILLRIG]),

    # ---- 7. weapons and the table size
    ("the Overlord's blade is FORKED for the Barge instead of shared",
     [(os.path.join("game", "factions", "necrons.py"), _BLADE_SHARE, _BLADE_SHARE_OFF)], [VEH]),
    ("the Barge's ranged staff loses its BS2+ override",
     [(WEAPONS, _STAFF_BS, _STAFF_BS_OFF)], [VEH]),
    ("the Annihilation Barge's profile WS stops matching the shared armoured bulk",
     [(UNITS, _ANNI_WS, _ANNI_WS_OFF)], [VEH]),
    ("the Ghost Ark goes back to its printed 60 mm",
     [(UNITS, _BASE, _BASE_OFF)], [VEH]),
]


# DECLARED NON-BITERS. A probe that cannot go red is normally a finding about
# the TEST - but this one is a finding about the DATA, and it is measured
# rather than assumed: over every buildable unit in all five factions, merged
# and unmerged, models[0].profile.toughness and attached_unit_toughness() give
# the SAME answer. There is no board on which the two readings differ, so no
# behaviour test could tell them apart. Listed here, with the measurement
# pinned in test_wave_serpent.py, instead of being quietly dropped.
#
#   ("Toughness read off the model instead of attached_unit_toughness()",
#    [(SOT, _TOUGH, _TOUGH_OFF)], [VEH, SERPENT, ABIL])
#
# game/guardian_protocols.py used to claim the opposite ("Here it genuinely
# matters"); its Lychguard and Overlord are both T5, so it never did.


# ------------------------------------------------------------------ driver
# FAILURES, not passes: a probe that changes how many checks a guard runs makes
# "fewer passed" meaningless.
BASE = {}
for _suite in SUITES:
    got, total, text = run(_suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:%s%s" % (_suite, NL, text[-2000:]))
        raise SystemExit(2)
    BASE[_suite] = total - got
    print("baseline %-30s %s/%s (%d red)" % (_suite, got, total, total - got))
print()

bad = 0
for label, edits, suites in PROBES:
    originals = {path: read(path) for path, _, _ in edits}
    ok = True
    for path, anchor, replacement in edits:
        src = read(path)
        if src.count(anchor) != 1:
            print("  SKIP     %s: anchor not unique in %s (%d)"
                  % (label, path, src.count(anchor)))
            ok = False
            break
        write(path, src.replace(anchor, replacement))
    try:
        if not ok:
            bad += 1
            continue
        for suite in suites:
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
print("%d probe run(s) did not bite" % bad if bad else "every probe bit")
raise SystemExit(1 if bad else 0)
