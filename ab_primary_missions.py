"""A/B probes for the Force Disposition Primary Missions.

Each probe restores ONE pre-fix world AT THE SOURCE, runs the suites, and
must turn exactly its own checks red. A probe that does NOT bite is a finding
about the TEST, not proof that the code is fine - this repo has recorded that
lesson enough times to make it the point of the exercise.

Run:  python ab_primary_missions.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))

# (label, file, needle, replacement)
PROBES = [
    # --- the boxes ---------------------------------------------------------
    ("Battlefield Dominance: a tie counts as 'more'",
     "game/primary_missions.py",
     "return BATTLEFIELD_DOMINANCE_MORE_VP if mine > theirs else 0",
     "return BATTLEFIELD_DOMINANCE_MORE_VP if mine >= theirs else 0"),
    ("Battlefield Dominance: the cumulative home bonus counts the home too",
     "game/primary_missions.py",
     "    forward = len(controlled_non_home_objectives(ctx))",
     "    forward = len(controlled_objectives(ctx))"),
    ("Battlefield Dominance: the home bonus is not gated on holding the home",
     "game/primary_missions.py",
     "    if home is None or home.controlled_by != ctx.player:\n        return base",
     "    if home is None:\n        return base"),
    ("Reconnaissance Sweep: the two spread tiers ADD instead of being alternatives",
     "game/primary_missions.py",
     "    if quarters >= 4:\n        return RECON_FOUR_QUARTERS_VP",
     "    if quarters >= 4:\n        return RECON_FOUR_QUARTERS_VP + RECON_THREE_QUARTERS_VP"),
    ("Reconnaissance Sweep: kills are a yes/no rather than a count",
     "game/primary_missions.py",
     "    return len(enemy_units_destroyed_this_turn(ctx)) * RECON_PER_KILL_VP",
     "    return RECON_PER_KILL_VP if enemy_units_destroyed_this_turn(ctx) else 0"),
    ("Reconnaissance Sweep: my own losses count as kills",
     "game/primary_missions.py",
     "    return [sq for sq in ctx.destroyed_squads_this_turn if sq.owner != ctx.player]",
     "    return list(ctx.destroyed_squads_this_turn)"),
    ("the home objective is not excluded anywhere",
     "game/primary_missions.py",
     "    return [o for o in _non_home_objectives(ctx) if o.controlled_by == ctx.player]",
     "    return [o for o in ctx.objectives if o.controlled_by == ctx.player]"),
    ("Unstoppable Force: kills are counted rather than a yes/no",
     "game/primary_missions.py",
     "    return UNSTOPPABLE_KILL_VP if enemy_units_destroyed_this_turn(ctx) else 0",
     "    return UNSTOPPABLE_KILL_VP * len(enemy_units_destroyed_this_turn(ctx))"),
    ("Unstoppable Force: 'gained' reads the board instead of the turn-start snapshot",
     "game/primary_missions.py",
     "            if any(id(o) not in ctx.objectives_controlled_at_turn_start\n"
     "                   for o in controlled_non_home_objectives(ctx))",
     "            if controlled_non_home_objectives(ctx)"),
    ("Unstoppable Force: final scoring accepts ANY objective, not a central one",
     "game/primary_missions.py",
     "            if any(o.controlled_by == ctx.player for o in central_objectives(ctx))",
     "            if any(o.controlled_by == ctx.player for o in ctx.objectives)"),
    ("Secure Asset: the kill clause ignores the turn-start snapshot",
     "game/primary_missions.py",
     "            if any(id(sq) in marked for sq in enemy_units_destroyed_this_turn(ctx))",
     "            if enemy_units_destroyed_this_turn(ctx)"),
    ("Secure Asset: the 'three or more' row excludes the home objective too",
     "game/primary_missions.py",
     "            if len(controlled_objectives(ctx)) >= SECURE_ASSET_THREE_NEEDED else 0",
     "            if len(controlled_non_home_objectives(ctx)) >= SECURE_ASSET_THREE_NEEDED else 0"),
    ("Death Trap: the objective-area bonus is dropped",
     "game/primary_missions.py",
     "        if area_is_an_objective(ctx, area):\n            total += DEATH_TRAP_OBJECTIVE_AREA_BONUS_VP",
     "        if False:\n            total += DEATH_TRAP_OBJECTIVE_AREA_BONUS_VP"),
    ("Death Trap: the kill clause ignores whether the area is trapped",
     "game/primary_missions.py",
     "            if area_id in trapped:\n                return DEATH_TRAP_KILL_VP",
     "            if True:\n                return DEATH_TRAP_KILL_VP"),
    ("Death Trap: an area can be trapped again every turn",
     "game/primary_missions.py",
     "        if id(area) in seen or area_is_trapped(ctx, area):",
     "        if id(area) in seen:"),
    ("Death Trap: 'trapped' does not outlive the turn",
     "game/primary_missions.py",
     "        self.card_state.pop(DEATH_TRAP_SLOT, None)",
     "        self.card_state.pop(DEATH_TRAP_SLOT, None)\n"
     "        self.card_state.pop(DEATH_TRAP_ALL_SLOT, None)"),
    ("Death Trap: the area is identified by geometry rather than identity",
     "game/primary_missions.py",
     "    return any(o.terrain_area is area for o in ctx.objectives)",
     "    return False"),

    # --- the controller and its instants -----------------------------------
    ("the round bands are ignored",
     "game/primary_missions.py",
     "        if battle_round is None:\n            return True",
     "        return True\n        if battle_round is None:\n            return True"),
    ("end-of-turn boxes score at BOTH players' turn ends",
     "game/primary_missions.py",
     "        if ending_player == self.player:\n            ctx = self._context(ending_player=ending_player, battle_round=battle_round)",
     "        if True:\n            ctx = self._context(ending_player=ending_player, battle_round=battle_round)"),
    ("the Command-phase box scores for whoever's phase it was",
     "game/primary_missions.py",
     "        if not self.plays_card or phase_owner != self.player:\n            return 0\n        ctx = self._context(battle_round=battle_round)",
     "        if not self.plays_card:\n            return 0\n        ctx = self._context(battle_round=battle_round)"),
    ("final scoring pays every frame instead of once",
     "game/primary_missions.py",
     "        if not self.plays_card or self._battle_scored:\n            return 0\n        self._battle_scored = True",
     "        if not self.plays_card:\n            return 0\n        self._battle_scored = True"),
    ("a destroyed squad can be counted twice",
     "game/primary_missions.py",
     "        if id(squad) in self._destroyed_squad_ids:\n            return\n        self._destroyed_squad_ids.add(id(squad))",
     "        self._destroyed_squad_ids.add(id(squad))"),
    ("the per-player gate is gone: everyone plays a Primary card",
     "game/primary_missions.py",
     "        return self.player in card_players()",
     "        return True"),
    ("Hold the Line is NOT replaced for the card player",
     "game/missions.py",
     "        if self.plays_primary_mission_card(player):\n            return 0",
     "        if False:\n            return 0"),

    # --- rule 16.01 --------------------------------------------------------
    ("Secure Asset's use limit is per unit rather than per turn",
     "game/primary_missions.py",
     '    return not any(s.definition.key == "secure_asset" for s in started)',
     '    return not any(s.definition.key == "secure_asset" and s.squad is squad\n'
     '                   for s in started)'),
    ("resolve_end_of_turn() is no longer idempotent, so effects fire twice",
     "game/actions.py",
     "        if self._resolved_for == player:\n            return self.completed_this_turn\n        self._resolved_for = player",
     "        pass"),
    ("the action's result slot is a hard-coded guess again",
     "game/secondary_missions.py",
     "            slot = card.action.result_slot",
     '            slot = ("plundered_this_turn" if card.action.key == "plunder"\n'
     '                    else "cleansed_this_turn")'),

    # --- geometry ----------------------------------------------------------
    ("central objectives: ties are broken instead of shared",
     "game/mission_context.py",
     "    return [o for o in candidates\n            if distance(o) <= nearest + CENTRAL_OBJECTIVE_TIE_IN]",
     "    return [min(candidates, key=distance)]"),
    ("central objectives: home objectives are candidates too",
     "game/mission_context.py",
     "    candidates = no_mans_land_objectives(ctx)",
     "    candidates = list(ctx.objectives)"),
    ("central objectives: read by NAME, the way map3 breaks",
     "game/mission_context.py",
     "    candidates = no_mans_land_objectives(ctx)",
     '    return [o for o in ctx.objectives if "Central" in o.name]\n'
     "    candidates = no_mans_land_objectives(ctx)"),

    # --- the list / detachment declaration ---------------------------------
    ("a list may declare a disposition none of its detachments permits",
     "game/detachments.py",
     "        if declared not in granted:",
     "        if False:"),
    ("the T'au list stops declaring Reconnaissance",
     "game/army_lists.py",
     "             force_disposition=force_dispositions.RECONNAISSANCE),    # Advanced Acquisition Cadre",
     "             force_disposition=force_dispositions.DISRUPTION),"),
    ("the corpus stops carrying the Force Disposition",
     "fetch_datasheet_rules.py",
     '        line += " - Force Disposition: %s" % detachment["force_disposition"]',
     "        pass"),
]

SUITES = ["test_primary_missions.py", "test_force_dispositions.py",
          "test_secondary_missions.py", "test_actions.py", "test_detachments.py",
          "test_datasheet_rules.py"]


def run_suites():
    """(passed, total) summed over every suite, plus the failing suite names."""
    passed = total = 0
    failed = []
    for suite in SUITES:
        if not os.path.exists(os.path.join(ROOT, suite)):
            continue
        proc = subprocess.run([sys.executable, suite], cwd=ROOT,
                              capture_output=True, text=True)
        for line in proc.stdout.split("\n"):
            if "checks passed" in line:
                got, want = line.split()[0].split("/")
                passed += int(got)
                total += int(want)
        if proc.returncode != 0:
            failed.append(suite)
    return passed, total, failed


def clear_cache():
    """__pycache__ between runs. These probes rewrite and restore a file inside
    the same second, which is exactly the stale-bytecode race this repo records
    as error class 19 - and which once sent an investigation down a blind alley
    because the wrong failure reproduced deterministically."""
    for dirpath, dirnames, _files in os.walk(ROOT):
        for name in list(dirnames):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, name), ignore_errors=True)
                dirnames.remove(name)


def main():
    clear_cache()
    base_passed, base_total, base_failed = run_suites()
    print(f"BASELINE: {base_passed}/{base_total}"
          + (f"  (failing: {base_failed})" if base_failed else ""))
    if base_failed:
        print("  refusing to probe against a red baseline")
        return 1

    inert = []
    for label, path, needle, replacement in PROBES:
        full = os.path.join(ROOT, path)
        original = open(full, encoding="utf-8").read()
        if needle not in original:
            print(f"  !! NEEDLE MISSING  {label}  ({path})")
            inert.append(label)
            continue
        try:
            open(full, "w", encoding="utf-8", newline="").write(
                original.replace(needle, replacement, 1))
            clear_cache()
            passed, total, failed = run_suites()
        finally:
            open(full, "w", encoding="utf-8", newline="").write(original)
            clear_cache()
        broke = base_passed - passed
        crashed = " CRASHED:" + ",".join(failed) if failed and broke <= 0 else ""
        mark = "ok  " if (broke > 0 or crashed) else "INERT"
        print(f"  {mark} -{broke:<4} {label}{crashed}")
        if broke <= 0 and not crashed:
            inert.append(label)

    print()
    if inert:
        print(f"{len(inert)} INERT probe(s) - each is a finding about the TEST:")
        for label in inert:
            print("   ", label)
        return 1
    print(f"all {len(PROBES)} probes bite")
    return 0


if __name__ == "__main__":
    sys.exit(main())
