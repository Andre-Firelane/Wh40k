"""A/B probes for stage 7 of the Necron backfill - the four leader characters.

Each probe restores ONE clause of the pre-fix world AT THE SOURCE, runs the
suite that should notice, and puts it back. A probe that does NOT go red is a
finding about the TEST, so this file exits non-zero if any survives.

FOUR SUITES, and the split is deliberate:

  * test_necron_leaders.py       the new behaviour
  * test_kroot_shapers.py        the OTHER carrier of game/end_battle_shock.py
  * test_eldrad_ulthran.py       the OTHER carrier of game/command_phase_cp.py
  * test_event_chain_wiring.py   the source-level set differences

Six of this stage's eight abilities are twins of something already shipped, so
several probes below are aimed at a SHARED base class and must make BOTH of its
carriers' suites red. A fix - or a break - that only one of them notices is
exactly the drift the extraction exists to prevent, which is why those probes
list two suites and are counted twice.

COUNTING RED, NOT GREEN. One probe here changes the number of checks a guard
runs, so "fewer passed than the baseline" can be false while checks are red.
"""

import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)

MOVE_EXC = os.path.join("game", "move_exceptions.py")
END_BS = os.path.join("game", "end_battle_shock.py")
ENGRAM = os.path.join("game", "engrammatic_logic.py")
SHROUD = os.path.join("game", "translocation_shroud.py")
MOVEMENT = os.path.join("game", "movement.py")
LOTS = os.path.join("game", "lord_of_the_storm.py")
CPCP = os.path.join("game", "command_phase_cp.py")
STRATEGIST = os.path.join("game", "grand_strategist.py")
COLLECTOR = os.path.join("game", "ancient_collector.py")
FIELDCRAFT = os.path.join("game", "fieldcraft.py")
WEAPONS = os.path.join("game", "weapons.py")
NECRONS = os.path.join("game", "factions", "necrons.py")
POINTS = os.path.join("game", "factions", "necrons_points.py")
SPRITES = os.path.join("game", "sprites.py")
MAIN = "main.py"

LEADERS = "test_necron_leaders.py"
KROOT = "test_kroot_shapers.py"
ELDRAD = "test_eldrad_ulthran.py"
WIRING = "test_event_chain_wiring.py"
SUITES = (LEADERS, KROOT, ELDRAD, WIRING)


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
# Written as (anchor -> replacement) pairs: the anchor is what is there NOW and
# the replacement is the pre-fix world.

# ---- Adaptive Strategy: the two halves, separately ------------------------
_SHOOT = ("            or squad_has_agile_combatant(squad)" + NL
          + "            or squad_has_adaptive_strategy(squad)")
_SHOOT_OFF = "            or squad_has_agile_combatant(squad)"

_CHARGE = ("            or squad_has_relentless_combatants(squad)" + NL
           + "            or squad_has_adaptive_strategy(squad)")
_CHARGE_OFF = "            or squad_has_relentless_combatants(squad)"

# ---- the shared end_battle_shock machine ----------------------------------
_BS_FILTER = "or not squad.battle_shocked"
_BS_FILTER_OFF = "or False"

_BS_USED = "        self._used.add(id(model))"
_BS_USED_OFF = "        pass  # probe: the once-per-battle ledger is never written"

_BS_RANGE = "BATTLE_SHOCK_RELIEF_RANGE_IN = 12.0"
_BS_RANGE_OFF = "BATTLE_SHOCK_RELIEF_RANGE_IN = 6.0"

_ENGRAM_TARGET = 'target_flag = "reanimation_protocols"'
_ENGRAM_TARGET_OFF = 'target_flag = "infantry"'

# ---- Translocation Shroud --------------------------------------------------
_MODES = "TRANSLOCATION_SHROUD_MOVE_MODES = (None, \"fall_back\")"
_MODES_OFF = "TRANSLOCATION_SHROUD_MOVE_MODES = (None, \"fall_back\", \"charge\", \"pile_in\", \"consolidate\")"

_GATE = ("    if move_mode not in TRANSLOCATION_SHROUD_MOVE_MODES:" + NL
         + "        return False")
_GATE_OFF = "    pass  # probe: the move mode is not consulted at all"

_ADVANCE = ("        elif translocation_shroud.skips_advance_roll(self.selected_squad):")
_ADVANCE_OFF = ("        elif False and translocation_shroud.skips_advance_roll(self.selected_squad):")

_CLAMP = "                or translocation_shroud.crosses_everything(self.move_mode, token)):"
_CLAMP_OFF = "                or False):"

# ---- Lord of the Storm -----------------------------------------------------
_BANDS = ("        if roll >= LORD_OF_THE_STORM_BIG_ROLL:" + NL
          + "            return D3(LORD_OF_THE_STORM_BIG_BONUS)")
_BANDS_OFF = "        if False:  # probe: one band only" + NL + "            return D3()"

_LOTS_RANGE = "LORD_OF_THE_STORM_RANGE_IN = 12.0"
_LOTS_RANGE_OFF = "LORD_OF_THE_STORM_RANGE_IN = 6.0"

_LOTS_USED = "        self._used.add(id(model))"
_LOTS_USED_OFF = "        pass  # probe: the once-per-battle ledger is never written"

_LOTS_SIDE = "        for squad in sorted((s for s in squads if s.owner == player),"
_LOTS_SIDE_OFF = "        for squad in sorted((s for s in squads if True),"

# ---- the shared command_phase_cp machine -----------------------------------
_CP_DEAD = "        if token.is_dead() or not getattr(token.profile, flag, False):"
_CP_DEAD_OFF = "        if not getattr(token.profile, flag, False):"

_CP_CAP = "        return self.command_points.gain_cp("
_CP_CAP_OFF = ("        self.command_points.cp[player] = self.command_points.cp.get(player, 0) + self.amount" + NL
               + "        return self.amount" + NL
               + "        return self.command_points.gain_cp(")

_STRAT_FLAG = 'flag = "grand_strategist"'
_STRAT_FLAG_OFF = 'flag = "diviner_of_futures"'

# ---- Ancient Collector -----------------------------------------------------
_LEADING = 'return bool(attached_units.leader_ability(squad, "ancient_collector"))'
_LEADING_OFF = ('return any(getattr(m.profile, "ancient_collector", False)' + NL
                + "               for m in getattr(squad, \"models\", ()) or ())")

_SWEEP = "        if squad_has_fieldcraft(squad) or ancient_collector.applies(squad)"
_SWEEP_OFF = "        if squad_has_fieldcraft(squad)"

# ---- weapons ---------------------------------------------------------------
# The shared Close Combat Weapon with a skill written ON THE WEAPON - the
# mistake stage 4 caught once already, and the one a shared class invites.
_CCW = ('class NecronCloseCombatWeaponA4S5Profile(WeaponProfile):')
_CCW_OFF = ('class NecronCloseCombatWeaponA4S5Profile(WeaponProfile):' + NL
            + '    weapon_skill = "3+"  # probe: the skill on the weapon, not the wielder')

# Imotekh loses the melee half of the Staff - the firing-mode-pair reading.
_STAFF = "                            StaffOfTheDestroyerMeleeProfile],"
_STAFF_OFF = "                            ],"

# ---- the LEADER table ------------------------------------------------------
_WARDEN_LEADS = '{1: 50}, leads=("Immortals", "Necron Warriors")),'
_WARDEN_LEADS_OFF = '{1: 50}, leads=("Immortals", "Lychguard", "Necron Warriors")),'

# ---- sprites ---------------------------------------------------------------
_SPRITE = ('    "Overlord with translocation shroud": "Necron Overlord",' + NL
           + '    "Overlord": "Necron Overlord",')
_SPRITE_OFF = '    "Overlord": "Necron Overlord",'

_SPRITE_ORDER = ('    "Overlord with translocation shroud": "Necron Overlord",' + NL
                 + '    "Overlord": "Necron Overlord",')
_SPRITE_ORDER_OFF = ('    "Overlord": "Necron Overlord",' + NL
                     + '    "Overlord with translocation shroud": "Necron Overlord",')

# ---- main.py's seams -------------------------------------------------------
# The set-comprehension line alone appears three times in main.py, so the
# anchor has to carry the call it belongs to.
_SEAM = ("            lord_of_the_storm_controller.offer_at_end_of_command_phase(" + NL
         + "                {t.squad for t in state.tokens if t.squad is not None}, mover_before)")
_SEAM_OFF = ("            lord_of_the_storm_controller.offer_at_end_of_command_phase(" + NL
             + "                {t.squad for t in state.tokens if t.squad is not None},"
             + " turn_tracker.turn_owner)")

_CLICK = "                        lord_of_the_storm_controller.choose_damage_model(clicked)"
_CLICK_OFF = "                        pass  # probe: the allocation has no click branch"

_ACK = "                        lord_of_the_storm_controller.on_dice_acknowledged()"
_ACK_OFF = "                        pass  # probe: its dice are never acknowledged"

_OFFER = ("            lord_of_the_storm_controller.offer_at_end_of_command_phase(")
_OFFER_OFF = ("            False and lord_of_the_storm_controller.offer_at_end_of_command_phase(")


PROBES = [
    # ---- 1. Adaptive Strategy, one half at a time --------------------------
    # A copy of the Triarch Praetorians' Relentless Combatants loses exactly
    # the first of these two and keeps the second.
    ("Adaptive Strategy does not lift the SHOOTING ban",
     [(MOVE_EXC, _SHOOT, _SHOOT_OFF)], [LEADERS]),
    ("Adaptive Strategy does not lift the CHARGE ban",
     [(MOVE_EXC, _CHARGE, _CHARGE_OFF)], [LEADERS]),

    # ---- 2. the shared end_battle_shock machine ----------------------------
    # Each of these must redden BOTH carriers' suites.
    ("end_battle_shock offers a unit that is not Battle-shocked",
     [(END_BS, _BS_FILTER, _BS_FILTER_OFF)], [LEADERS, KROOT]),
    ("end_battle_shock never spends its once-per-battle use",
     [(END_BS, _BS_USED, _BS_USED_OFF)], [LEADERS, KROOT]),
    ("end_battle_shock's range is 6\" instead of 12\"",
     [(END_BS, _BS_RANGE, _BS_RANGE_OFF)], [LEADERS, KROOT]),
    ("Engrammatic Logic reads a keyword every model has",
     [(ENGRAM, _ENGRAM_TARGET, _ENGRAM_TARGET_OFF)], [LEADERS]),

    # ---- 3. Translocation Shroud -------------------------------------------
    ("the shroud's bypass is not gated on the move mode (the list)",
     [(SHROUD, _MODES, _MODES_OFF)], [LEADERS]),
    ("...nor by the predicate itself",
     [(SHROUD, _GATE, _GATE_OFF)], [LEADERS]),
    ("the shroud does not replace the Advance roll",
     [(MOVEMENT, _ADVANCE, _ADVANCE_OFF)], [LEADERS]),
    ("clamp_move never asks the shroud whether this model crosses everything",
     [(MOVEMENT, _CLAMP, _CLAMP_OFF)], [LEADERS]),

    # ---- 4. Lord of the Storm ----------------------------------------------
    ("Lord of the Storm has one band instead of two",
     [(LOTS, _BANDS, _BANDS_OFF)], [LEADERS]),
    ("...and a 6\" sweep instead of 12\"",
     [(LOTS, _LOTS_RANGE, _LOTS_RANGE_OFF)], [LEADERS]),
    ("...and never spends its once-per-battle use",
     [(LOTS, _LOTS_USED, _LOTS_USED_OFF)], [LEADERS]),
    ("...and is offered in the opponent's Command phase too",
     [(LOTS, _LOTS_SIDE, _LOTS_SIDE_OFF)], [LEADERS]),

    # ---- 5. the shared command_phase_cp machine ----------------------------
    ("command_phase_cp counts a dead bearer as on the battlefield",
     [(CPCP, _CP_DEAD, _CP_DEAD_OFF)], [LEADERS, ELDRAD]),
    ("command_phase_cp bypasses the shared one-bonus-CP-per-round cap",
     [(CPCP, _CP_CAP, _CP_CAP_OFF)], [LEADERS]),
    ("Grand Strategist reads the Aeldari flag instead of its own",
     [(STRATEGIST, _STRAT_FLAG, _STRAT_FLAG_OFF)], [LEADERS]),

    # ---- 6. Ancient Collector ----------------------------------------------
    ("Ancient Collector drops \"while this model is LEADING a unit\"",
     [(COLLECTOR, _LEADING, _LEADING_OFF)], [LEADERS]),
    ("the Fieldcraft sweep never asks about Ancient Collector",
     [(FIELDCRAFT, _SWEEP, _SWEEP_OFF)], [LEADERS]),

    # ---- 7. weapons ---------------------------------------------------------
    ("the shared Close Combat Weapon carries a skill of its own",
     [(WEAPONS, _CCW, _CCW_OFF)], [LEADERS]),
    ("Imotekh carries only one Staff of the Destroyer",
     [(NECRONS, _STAFF, _STAFF_OFF)], [LEADERS]),

    # ---- 8. the LEADER table -------------------------------------------------
    ("the Royal Warden may lead Lychguard after all",
     [(POINTS, _WARDEN_LEADS, _WARDEN_LEADS_OFF)], [LEADERS]),

    # ---- 9. sprites ----------------------------------------------------------
    ("the shroud Overlord has no entry of his own",
     [(SPRITES, _SPRITE, _SPRITE_OFF)], [LEADERS]),
    ("...or has one, but BELOW the shorter key that swallows him",
     [(SPRITES, _SPRITE_ORDER, _SPRITE_ORDER_OFF)], [LEADERS]),

    # ---- 10. main.py's seams -------------------------------------------------
    # The wiring guard sees these; the behaviour suite drives the controller
    # directly and cannot.
    ("main.py offers Lord of the Storm to the FLIPPED turn owner",
     [(MAIN, _SEAM, _SEAM_OFF)], [LEADERS]),
    ("main.py has no click branch for Lord of the Storm's allocation",
     [(MAIN, _CLICK, _CLICK_OFF)], [LEADERS, WIRING]),
    ("main.py never acknowledges Lord of the Storm's dice",
     [(MAIN, _ACK, _ACK_OFF)], [LEADERS, WIRING]),
    ("main.py never offers Lord of the Storm at all",
     [(MAIN, _OFFER, _OFFER_OFF)], [LEADERS]),

    # ---- 11. the whole pre-fix world ----------------------------------------
    ("the whole pre-fix world - both Adaptive Strategy halves and both shrouds",
     [(MOVE_EXC, _SHOOT, _SHOOT_OFF),
      (MOVE_EXC, _CHARGE, _CHARGE_OFF),
      (SHROUD, _GATE, _GATE_OFF),
      (MOVEMENT, _ADVANCE, _ADVANCE_OFF)], [LEADERS]),
]


# FAILURES, not passes: one probe changes how many checks a guard runs, so
# "fewer passed" is not a comparison that survives a changing total.
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
