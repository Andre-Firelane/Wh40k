"""A/B probes for stage 9 of the Necron backfill - Monolith, The Silent King.

Each probe restores ONE clause of the pre-fix world AT THE SOURCE, runs the
suite that should notice, and puts it back. A probe that does NOT go red is a
finding about the TEST, so this file exits non-zero if any survives.

FOUR SUITES, and the split is the point:

  * test_necron_titans.py     the new behaviour
  * test_necron_triarch.py    the OTHER carrier of game/charge_reroll.py
  * test_death_guard_datasheets.py  the two cross-faction sweeps stage 9 moved
  * test_necron_datasheets.py the faction-wide counts

A probe on a SHARED module lists more than one suite and is counted once per
run. A break only one of them notices is exactly the drift an extraction
exists to prevent - and this stage has a live example of it, since the Death
Guard suite is the only place that measures "the toughest model in the engine".

COUNTING RED, NOT GREEN: a probe that changes how many checks a guard runs
would make "fewer passed" meaningless.

NEVER PIPE THIS THROUGH `tail`. Stage 8 did, and the reported exit code was
tail's - "exit 0" printed beside "14 probe run(s) did not bite". Redirect to a
file instead (error class 18).
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
AURAS = os.path.join("game", "triarch_auras.py")
SKLEAD = os.path.join("game", "silent_king_leadership.py")
MENHIRS = os.path.join("game", "triarchal_menhirs.py")
GATE = os.path.join("game", "eternity_gate.py")
DAMAGED = os.path.join("game", "damaged_attacks.py")
CREROLL = os.path.join("game", "charge_reroll.py")
RELENT = os.path.join("game", "relentless_combatants.py")
OBJCTRL = os.path.join("game", "objective_control.py")
LEADER = os.path.join("game", "leadership.py")
COLDSTAR = os.path.join("game", "coldstar.py")
INGRESS = os.path.join("game", "ingress.py")
SHEETS_SRC = os.path.join("game", "factions", "necrons.py")
ACTIVATION = os.path.join("game", "activation_state.py")

TITANS = "test_necron_titans.py"
TRIARCH = "test_necron_triarch.py"
DG = "test_death_guard_datasheets.py"
SHEETS = "test_necron_datasheets.py"
SUITES = (TITANS, TRIARCH, DG, SHEETS)


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

# --- bases: the decision, and the two values it is not ---
_BASE_DEFILER = '    base_radius_in = 2.5            # printed 160 mm (r=3.150"); a NEW table-size decision'
_BASE_DEFILER_OFF = '    base_radius_in = 2.1            # printed 160 mm (r=3.150"); a NEW table-size decision'
_BASE_PRINTED_OFF = '    base_radius_in = 3.150          # printed 160 mm (r=3.150"); a NEW table-size decision'

_MENHIR_BASE = '    base_radius_in = 0.984          # printed 50 mm'
_MENHIR_BASE_OFF = '    base_radius_in = 1.969          # printed 50 mm'

# --- weapons ---
_FORK = "class MenhirArmouredBulkProfile(ArmouredBulkProfile):"
_FORK_OFF = "class MenhirArmouredBulkProfile(WeaponProfile):"

# Anchored on the docstring line above, because "attacks = 1" alone occurs
# sixteen times in weapons.py.
# chr(34)*3 and not a literal triple quote: "...row." + '''"""''' written
# inline parses as a string followed by an EMPTY string, which silently drops
# the three characters the anchor needs.
_DOC_END = "    quietly ceasing to track the shared row." + chr(34) * 3
_FORK_A = _DOC_END + NL + "    attacks = 1" + NL + "    strength = 4"
_FORK_A_OFF = _DOC_END + NL + "    attacks = 3" + NL + "    strength = 6"

_DEATHRAY = "    damage_notation = D6(1)         # printed \"D6+1\""
_DEATHRAY_OFF = "    damage_notation = None          # printed \"D6+1\""

_WHIP = "    attacks_notation = D6(dice=3)   # printed \"3D6\""
_WHIP_OFF = "    attacks_notation = D6()         # printed \"3D6\""

# Anchored on the line above it - "indirect_fire = True" occurs thirteen
# times, one per weapon that prints the keyword.
_INDIRECT = '    name = "Staff of Stars"' + NL + "    weapon_type = RANGED"
_INDIRECT_OFF = '    name = "Staff of Stars"' + NL + "    weapon_type = MELEE"

# --- profiles ---
_MENHIR_DD = "    triarchal_menhir = True             # see game/triarchal_menhirs.py"
_MENHIR_DD_OFF = ("    deadly_demise_notation = D6(3)      # WRONG: the line says Szarekh only" + NL +
                  "    triarchal_menhir = True             # see game/triarchal_menhirs.py")

_MENHIR_CHAR = "    epic_hero = True" + NL + "    reanimation_protocols = True" + NL + "    triarchal_menhir = True"
_MENHIR_CHAR_OFF = ("    epic_hero = True" + NL + "    character = True" + NL +
                    "    reanimation_protocols = True" + NL + "    triarchal_menhir = True")

# --- Voice of the Triarch ---
_STAMP = "        squad.triarch_ability = key"
_STAMP_OFF = "        pass  # nothing is stamped"

_ONCE = "            if self._chosen_round.get(id(squad)) == battle_round:" + NL + "                continue"
_ONCE_OFF = "            if False:" + NL + "                continue"

_AI_SILENT = ("            self._choose(squad, PHAERON_OF_THE_STARS, battle_round)" + NL +
              "            # False, not the _choose() result")
_AI_SILENT_OFF = ("            return self._choose(squad, PHAERON_OF_THE_STARS, battle_round)" + NL +
                  "            # False, not the _choose() result")

_SAVED = '    "triarch_ability",'
_SAVED_OFF = '    # "triarch_ability",'

# --- the three auras ---
_FROM_SZAREKH = "        for szarekh in szarekh_models(bearer):"
_FROM_SZAREKH_OFF = "        for szarekh in _alive(bearer):"

_NOT_ANOTHER = "    for bearer in bearer_squads(all_tokens):"
_NOT_ANOTHER_OFF = ("    for bearer in bearer_squads(all_tokens):" + NL +
                    "        if bearer is squad:" + NL +
                    "            continue")

_MONSTER = "    if is_monster_unit(squad):" + NL + "        return False"
_MONSTER_OFF = "    if False:" + NL + "        return False"

_AURA_RANGE = "TRIARCH_AURA_RANGE_IN = 6.0"
_AURA_RANGE_OFF = "TRIARCH_AURA_RANGE_IN = 40.0"

_MARCH_FOLD = "        total += triarch_auras.RELENTLESS_MARCH_BONUS_IN"
_MARCH_FOLD_OFF = "        pass  # the movement fold never hears about it"

_BLADES_COPY = "    boosted = copy.copy(weapon)"
_BLADES_COPY_OFF = "    boosted = weapon"

_BLADES_GRANT = "        weapon = triarch_auras.blades_adjusted_weapon(weapon, self.fighting_squad)"
_BLADES_GRANT_OFF = "        pass  # the melee Strength half is never granted"

# --- the Leadership aura ---
_LD_SIGN = "            - silent_king_leadership.leadership_bonus(squad, all_tokens or ()))"
_LD_SIGN_OFF = "            + silent_king_leadership.leadership_bonus(squad, all_tokens or ()))"

_LD_MONSTER = "    if squad is None or not awakened_dynasty.is_necrons_unit(squad):"
_LD_MONSTER_OFF = ("    from game.triarch_auras import is_monster_unit" + NL +
                   "    if squad is None or not awakened_dynasty.is_necrons_unit(squad) or is_monster_unit(squad):")

# --- Damaged ---
_OC_PENALTY = "        oc = max(0, oc - damaged_penalty)"
_OC_PENALTY_OFF = "        pass  # the OC half of the tier is dropped"

_ROUND_UP = "    return (attacks + 1) // 2"
_ROUND_UP_OFF = "    return attacks // 2"

_UNITWIDE = "    if damaged_attacks.covers_model(model):"
_UNITWIDE_OFF = "    if False and damaged_attacks.covers_model(model):"

# --- Eternity Gate ---
_FIRST_ROUND = "        if self._battle_round() < FIRST_ALLOWED_BATTLE_ROUND:"
_FIRST_ROUND_OFF = "        if False:"

_UNENGAGED = "ETERNITY_GATE_MIN_ENEMY_DISTANCE_IN = ENGAGEMENT_RANGE_IN"
_UNENGAGED_OFF = "ETERNITY_GATE_MIN_ENEMY_DISTANCE_IN = 8.0"

_CHARGE_LOCK = "        passenger.charge_locked_until_end_of_turn = True"
_CHARGE_LOCK_OFF = "        pass  # the charge lock is never set"

_INFANTRY_ALL = '    return bool(models) and all(getattr(m.profile, "infantry", False) for m in models)'
_INFANTRY_ALL_OFF = '    return bool(models) and any(getattr(m.profile, "infantry", False) for m in models)'

_GATE_AI = '            self._log("%s (%s): the AI leaves its units where they stand - see "'
_GATE_AI_OFF = '            return self._offer_to_human(monolith_squad, candidates) or self._log("%s (%s): the AI leaves its units where they stand - see "'

_DZ_WAIVER = "        if self.eternity_gate_squad is squad:" + NL + '            # "even if that is within your opponent\'s deployment zone" -'
_DZ_WAIVER_OFF = "        if False:" + NL + '            # "even if that is within your opponent\'s deployment zone" -'

_GATE_CHECK = "        if self.eternity_gate_squad is squad:" + NL + "            return self._eternity_gate_extra_check(squad)"
_GATE_CHECK_OFF = "        if False:" + NL + "            return self._eternity_gate_extra_check(squad)"

# --- Triarchal Menhirs ---
_REVERSE = "    ever = [m for m in list(squad.models) + list(getattr(squad, \"destroyed_models\", ()) or ())"
_REVERSE_OFF = "    ever = [m for m in list(squad.models)"

_MENHIR_PICK = '    return [m for m in squad.models' + NL + '            if getattr(m.profile, "triarchal_menhir", False) and not m.is_dead()]'
_MENHIR_PICK_OFF = '    return [m for m in squad.models' + NL + '            if not m.is_dead()]'

# --- the extraction ---
_LABEL_GUARD = "        if not self.LABEL:" + NL + "            raise TypeError"
_LABEL_GUARD_OFF = "        if False:" + NL + "            raise TypeError"

_SUBCLASS = "class RelentlessCombatantsController(ChargeRerollController):"
_SUBCLASS_OFF = "class RelentlessCombatantsController(object):"

_CLAIM = "        if not self.dice_manager.claim_reroll_offer(self.LABEL):"
_CLAIM_OFF = "        if False:"

# --- cross-faction ---
_MONO_T = "    toughness = 13"
_MONO_T_OFF = "    toughness = 12"


PROBES = [
    # ---- 1. the base decision
    ("the Monolith goes back to the Defiler's 2.1\"",
     [(UNITS, _BASE_DEFILER, _BASE_DEFILER_OFF)], [TITANS]),
    ("...or to its printed 3.150\"",
     [(UNITS, _BASE_DEFILER, _BASE_PRINTED_OFF)], [TITANS]),
    ("the Menhir's base is transcribed wrong",
     [(UNITS, _MENHIR_BASE, _MENHIR_BASE_OFF)], [TITANS]),

    # ---- 2. weapons
    ("the Menhir's bulk is an independent copy instead of a fork",
     [(WEAPONS, _FORK, _FORK_OFF)], [TITANS]),
    ("...or shares the skimmers' A3 S6 outright",
     [(WEAPONS, _FORK_A, _FORK_A_OFF)], [TITANS]),
    ("the Death Ray's D6+1 becomes a flat value",
     [(WEAPONS, _DEATHRAY, _DEATHRAY_OFF)], [TITANS]),
    ("the Particle Whip rolls one D6 instead of three",
     [(WEAPONS, _WHIP, _WHIP_OFF)], [TITANS]),
    ("the Staff of Stars becomes a MELEE weapon, so [INDIRECT FIRE] cannot apply",
     [(WEAPONS, _INDIRECT, _INDIRECT_OFF)], [TITANS]),

    # ---- 3. profiles
    ("the Menhirs get Szarekh's Deadly Demise too",
     [(UNITS, _MENHIR_DD, _MENHIR_DD_OFF)], [TITANS]),
    ("the Menhirs become CHARACTERs",
     [(UNITS, _MENHIR_CHAR, _MENHIR_CHAR_OFF)], [TITANS]),

    # ---- 4. Voice of the Triarch
    ("the selection is never stamped on the squad",
     [(AURAS, _STAMP, _STAMP_OFF)], [TITANS]),
    ("it asks again in the SAME battle round",
     [(AURAS, _ONCE, _ONCE_OFF)], [TITANS]),
    ("the AI branch reports a prompt it never opened",
     [(AURAS, _AI_SILENT, _AI_SILENT_OFF)], [TITANS]),
    ("the selection stops being saved",
     [(ACTIVATION, _SAVED, _SAVED_OFF)], [TITANS]),

    # ---- 5. the three auras
    ("the aura is measured from the UNIT, not the Szarekh model",
     [(AURAS, _FROM_SZAREKH, _FROM_SZAREKH_OFF)], [TITANS]),
    ("the bearer's own unit is excluded ('another', which it does not say)",
     [(AURAS, _NOT_ANOTHER, _NOT_ANOTHER_OFF)], [TITANS]),
    ("the MONSTER exclusion is dropped",
     [(AURAS, _MONSTER, _MONSTER_OFF)], [TITANS]),
    ("the 6\" becomes 40\"",
     [(AURAS, _AURA_RANGE, _AURA_RANGE_OFF)], [TITANS]),
    ("Relentless March never reaches the movement fold",
     [(COLDSTAR, _MARCH_FOLD, _MARCH_FOLD_OFF)], [TITANS]),
    ("Phaeron of the Blades MUTATES the model's own weapon instance",
     [(AURAS, _BLADES_COPY, _BLADES_COPY_OFF)], [TITANS]),
    ("...or never reaches the melee adjuster chain at all",
     [(os.path.join("game", "fight.py"), _BLADES_GRANT, _BLADES_GRANT_OFF)], [TITANS]),

    # ---- 6. the Leadership aura
    ("'improve Leadership by 1' ADDS to the threshold instead of subtracting",
     [(LEADER, _LD_SIGN, _LD_SIGN_OFF)], [TITANS]),
    ("the Leadership aura gains a MONSTER exclusion it does not print",
     [(SKLEAD, _LD_MONSTER, _LD_MONSTER_OFF)], [TITANS]),

    # ---- 7. Damaged
    ("the Monolith's damaged OC penalty is dropped",
     [(OBJCTRL, _OC_PENALTY, _OC_PENALTY_OFF)], [TITANS]),
    ("halving rounds DOWN, deleting a 1-attack weapon",
     [(DAMAGED, _ROUND_UP, _ROUND_UP_OFF)], [TITANS]),
    ("the UNIT-wide half of the tier never reaches the Menhirs",
     [(os.path.join("game", "shooting.py"), _UNITWIDE, _UNITWIDE_OFF)], [TITANS]),

    # ---- 8. Eternity Gate
    ("the gate opens in the first battle round",
     [(GATE, _FIRST_ROUND, _FIRST_ROUND_OFF)], [TITANS]),
    ("'unengaged' becomes a fourth 8\" literal",
     [(GATE, _UNENGAGED, _UNENGAGED_OFF)], [TITANS]),
    ("the passenger keeps its charge",
     [(GATE, _CHARGE_LOCK, _CHARGE_LOCK_OFF)], [TITANS]),
    ("'NECRONS INFANTRY' is pooled with any() instead of all()",
     [(GATE, _INFANTRY_ALL, _INFANTRY_ALL_OFF)], [TITANS]),
    ("the deployment-zone waiver is dropped",
     [(INGRESS, _DZ_WAIVER, _DZ_WAIVER_OFF)], [TITANS]),
    ("the gated placement check is never reached",
     [(INGRESS, _GATE_CHECK, _GATE_CHECK_OFF)], [TITANS]),

    # ---- 9. Triarchal Menhirs and the extraction
    ("a swept-off Szarekh stops counting as down",
     [(MENHIRS, _REVERSE, _REVERSE_OFF)], [TITANS]),
    ("the shared base stops refusing a carrier with no LABEL",
     [(CREROLL, _LABEL_GUARD, _LABEL_GUARD_OFF)], [TITANS]),
    ("the first carrier stops using the shared base",
     [(RELENT, _SUBCLASS, _SUBCLASS_OFF)], [TITANS, TRIARCH]),
    ("the once-per-roll claim is dropped from the shared base",
     [(CREROLL, _CLAIM, _CLAIM_OFF)], [TRIARCH]),

    # ---- 10. the cross-faction sweeps
    ("the Monolith drops to T12, so nothing in the engine is above it",
     [(UNITS, _MONO_T, _MONO_T_OFF)], [TITANS, DG]),
]


# DECLARED NON-BITER. A probe that cannot go red is normally a finding about
# the TEST - this one is a finding about the DATA, and it is measured rather
# than assumed: the rule only fires once Szarekh is DOWN, and once he is down
# every remaining LIVING model of the unit is a Triarchal Menhir. So
# "take the Menhirs" and "take whatever is still standing" return the same
# list on every board this engine can build, and no behaviour test could
# separate them. Listed here, with the measurement pinned in
# test_necron_titans.py section 9, instead of being quietly dropped.
#
#   ("the rule takes every model, not just the Menhirs",
#    [(MENHIRS, _MENHIR_PICK, _MENHIR_PICK_OFF)], [TITANS])
#
# The filter stays in game/triarchal_menhirs.py because the printed sentence
# names the Menhirs, not because a board today can tell the two apart.


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
    print("baseline %-34s %s/%s (%d red)" % (_suite, got, total, total - got))
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
