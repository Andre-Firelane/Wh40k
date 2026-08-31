"""A/B probes for Etappe 5 (CP and resource economy)."""
import io, os, shutil, subprocess, sys

BASE = 406
PROBES = [
    # --- the shared "for 0CP" sentence -------------------------------------
    ("free stratagem: it is a flat -1 instead of the whole cost",
     "game/free_stratagem_once_per_round.py",
     '        return max(0, getattr(stratagem, "cp_cost", 0))',
     "        return 1"),
    ("free stratagem: it stops keying on WHICH Stratagem",
     "game/free_stratagem_once_per_round.py",
     "        if not self.matches_stratagem(stratagem):\n            return 0",
     "        pass"),
    ("free stratagem: asking the price spends the entitlement",
     "game/free_stratagem_once_per_round.py",
     "    def available_discount(self, player, stratagem=None, targets=()):",
     "    def available_discount(self, player, stratagem=None, targets=()):\n        self._used_in_round[player] = self._round()"),
    ("free stratagem: the detachment gate is dropped",
     "game/free_stratagem_once_per_round.py",
     "        return enhancements.is_active(squad, self.enhancement_name)",
     "        return super().unit_has_ability(squad)"),
    # --- Protector of the Paths -------------------------------------------
    ("Protector: the threshold ignores the latch, so a PAID Overwatch gets it",
     "game/enh_protector_of_the_paths.py",
     "    if not discount.is_free_activation(squad):\n        return None",
     "    pass"),
    ("Protector: the latch is never released",
     "game/overwatch.py",
     "            self.protector_of_the_paths.clear_activation()",
     "            pass"),
    ("Protector: the 5+ slips to 6",
     "game/enh_protector_of_the_paths.py",
     "PROTECTOR_HIT_THRESHOLD = 5",
     "PROTECTOR_HIT_THRESHOLD = 6"),
    ("Protector: any objective improves it, not only a CONTROLLED one",
     "game/enh_protector_of_the_paths.py",
     '    controlled = [o for o in objectives or ()\n                  if getattr(o, "controlled_by", None) == owner]',
     "    controlled = list(objectives or ())"),
    ("Protector: the LEADING clause is dropped",
     "game/enh_protector_of_the_paths.py",
     "    if not attached_units.leader_ability(squad, FLAG_ATTR):\n        return False",
     "    pass"),
    ("Protector: the DIRE AVENGERS / GUARDIANS keywords are dropped",
     "game/enh_protector_of_the_paths.py",
     "    return any(attached_units.unit_has_datasheet_keyword(squad, k)\n               for k in PROTECTOR_KEYWORDS)",
     "    return True"),
    ("Protector: the discount half stops asking the same three questions",
     "game/enh_protector_of_the_paths.py",
     "        return unit_has_bearer(squad)",
     "        return super().unit_has_ability(squad)"),
    ("Protector: it never reaches 15.09's branch",
     "game/shooting.py",
     "            return override if override is not None else 6",
     "            return 6"),
    # --- Torc of Morai-Heg -------------------------------------------------
    ("Torc: the surcharge never reaches the cost",
     "game/stratagems.py",
     "        for surcharge in self.cost_surcharges:\n            cost += surcharge.available_surcharge(player, stratagem, targets)",
     "        pass"),
    ("Torc: the clamp moves AFTER the surcharge, so any discount cancels it",
     "game/stratagems.py",
     "        cost = max(0, cost)\n        for surcharge in self.cost_surcharges:",
     "        for surcharge in self.cost_surcharges:"),
    ("Torc: the FAQ clause is dropped - a priced-out Stratagem can be retried",
     "game/stratagems.py",
     "                self.used_this_phase.add((player, stratagem.name))\n                if self.game_log is not None:",
     "                if self.game_log is not None:"),
    ("Torc: 'unaffordable anyway' is recorded as used too",
     "game/stratagems.py",
     "        return have < cost and have >= cost - surcharge",
     "        return have < cost"),
    ("Torc: it taxes its OWN side's Stratagems as well",
     "game/enh_torc_of_morai_heg.py",
     "        return [(s, m) for s in self._squads() if s.owner != user",
     "        return [(s, m) for s in self._squads() if True"),
    ("Torc: the 12\" is dropped",
     "game/enh_torc_of_morai_heg.py",
     "            if edge_distance(bearer_model, other) <= TORC_RANGE_IN:\n                return True",
     "            return True"),
    ("Torc: the once-per-turn window is dropped",
     "game/enh_torc_of_morai_heg.py",
     "            if not self.available(squad.owner):\n                continue\n            if any(self._in_range(model, t) for t in targets or ()):\n                return TORC_SURCHARGE_CP",
     "            if any(self._in_range(model, t) for t in targets or ()):\n                return TORC_SURCHARGE_CP"),
    # --- Echoes of Ulthanesh ----------------------------------------------
    ("Echoes: the two bonuses do NOT stack",
     "game/enh_echoes_of_ulthanesh.py",
     "    if enemy_zone is not None and enemy_zone.contains_point(model.x_in, model.y_in):\n        bonus += 1",
     "    if enemy_zone is not None and enemy_zone.contains_point(model.x_in, model.y_in):\n        bonus = 1"),
    ("Echoes: the own-zone clause is inverted",
     "game/enh_echoes_of_ulthanesh.py",
     "    if own_zone is not None and not own_zone.contains_point(model.x_in, model.y_in):",
     "    if own_zone is not None and own_zone.contains_point(model.x_in, model.y_in):"),
    ("Echoes: it rolls even when the CP cannot be paid",
     "game/enh_echoes_of_ulthanesh.py",
     "        if self._headroom(player) <= 0:",
     "        if False:"),
    ("Echoes: the 5+ slips to 4+",
     "game/enh_echoes_of_ulthanesh.py",
     "ECHOES_THRESHOLD = 5",
     "ECHOES_THRESHOLD = 4"),
    # --- Timeless Strategist ----------------------------------------------
    ("Timeless Strategist: the embarked clause is dropped",
     "game/enh_timeless_strategist.py",
     "    return squad in embarked_squads",
     "    return False"),
    ("Timeless Strategist: the OWNER filter is dropped",
     "game/enh_timeless_strategist.py",
     "        if squad.owner != player:\n            continue",
     "        pass"),
    ("Timeless Strategist: the detachment gate is dropped",
     "game/enh_timeless_strategist.py",
     "    if not enhancements.is_active(squad, TIMELESS_STRATEGIST):\n        return []",
     "    pass"),
    ("Timeless Strategist: it never reaches the token grant",
     "game/battle_focus.py",
     "                + enh_timeless_strategist.extra_tokens_for(\n                    player, self._board_squads(), self._embarked_squads()))",
     "                + 0)"),
    # --- Lucid Eye ---------------------------------------------------------
    ("Lucid Eye: it can push a die past a real face",
     "game/enh_lucid_eye.py",
     "            if new in legal and (value, new) not in out:",
     "            if (value, new) not in out:"),
    ("Lucid Eye: it only adds, never subtracts",
     "game/enh_lucid_eye.py",
     "LUCID_EYE_STEPS = (1, -1)",
     "LUCID_EYE_STEPS = (1,)"),
    ("Lucid Eye: applying a change edits nothing",
     "game/enh_lucid_eye.py",
     "    faces[faces.index(from_value)] = to_value\n    return True",
     "    return True"),
    # The membership guard is targeted at its RETURN VALUE: removing the guard
    # outright makes faces.index() raise, which is a crash rather than a clean
    # red and tells the reader less.
    ("Lucid Eye: it reports success for a die the pool does not hold",
     "game/enh_lucid_eye.py",
     "    if faces is None or from_value not in faces:\n        return False",
     "    if faces is None or from_value not in faces:\n        return True"),
]

SUITE = "test_aeldari_enhancements.py"


def run():
    for root, dirs, _ in os.walk("."):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True)
    for line in (out.stdout + out.stderr).splitlines():
        if "checks passed" in line:
            return int(line.split("/")[0].strip())
    return -1


bad = []
for label, path, old, new in PROBES:
    src = io.open(path, encoding="utf-8").read()
    if src.count(old) != 1:
        print("NO ANCHOR  %-4s %s" % (src.count(old), label))
        bad.append(label)
        continue
    io.open(path, "w", encoding="utf-8", newline="\n").write(src.replace(old, new, 1))
    try:
        got = run()
    finally:
        io.open(path, "w", encoding="utf-8", newline="\n").write(src)
    bites = -1 < got < BASE
    tag = "bites" if bites else ("CRASH" if got == -1 else "NO BITE")
    print("%-9s %d/%d  %s" % (tag, got, BASE, label))
    if not bites:
        bad.append(label)

print("\nprobes: %d, all biting: %s" % (len(PROBES), not bad))
for b in bad:
    print("  !", b)
