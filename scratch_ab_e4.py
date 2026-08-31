"""A/B probes for Etappe 4 (defence and concealment)."""
import io, os, shutil, subprocess, sys

BASE = 344
PROBES = [
    # --- Runes of Warding --------------------------------------------------
    ("Runes of Warding: the three conditions are read as a CONJUNCTION",
     "game/enh_runes_of_warding.py",
     "    if model is None or not (mortal or psychic or devastating):",
     "    if model is None or not (mortal and psychic and devastating):"),
    ("Runes of Warding: it applies to an ORDINARY wound too",
     "game/enh_runes_of_warding.py",
     "    if model is None or not (mortal or psychic or devastating):\n        return False",
     "    if model is None:\n        return False"),
    ("Runes of Warding: the threshold slips to 5+",
     "game/enh_runes_of_warding.py",
     'RUNES_OF_WARDING_THRESHOLD = "4+"',
     'RUNES_OF_WARDING_THRESHOLD = "5+"'),
    ("Runes of Warding: it returns None instead of '-', collapsing the fold",
     "game/enh_runes_of_warding.py",
     '        return "-"\n    return RUNES_OF_WARDING_THRESHOLD',
     "        return None\n    return RUNES_OF_WARDING_THRESHOLD"),
    ("Runes of Warding: it never reaches the fold",
     "game/feel_no_pain.py",
     "        best, enh_runes_of_warding.feel_no_pain(",
     "        best, (lambda *a, **k: \"-\")("),
    ("Runes of Warding: the damage session stops reporting PSYCHIC",
     "game/damage_resolution.py",
     '                             psychic=bool(getattr(self.weapon, "psychic", False)))\n        if fnp.is_pending:\n            self.pending_fnp = fnp\n            self._fnp_model = model\n            self._fnp_roll_value = roll\n            if resumed:',
     "                             )\n        if fnp.is_pending:\n            self.pending_fnp = fnp\n            self._fnp_model = model\n            self._fnp_roll_value = roll\n            if resumed:"),
    ("Runes of Warding: the devastating session stops reporting itself",
     "game/damage_resolution.py",
     "                             waaagh=self.waaagh, devastating=True)",
     "                             waaagh=self.waaagh)"),
    # --- Rune of Mists -----------------------------------------------------
    ("Rune of Mists: the range test is NOT inverted",
     "game/enh_rune_of_mists.py",
     "    return not _within(shooter_model, target_squad, RUNE_OF_MISTS_MIN_ATTACKER_RANGE_IN)",
     "    return _within(shooter_model, target_squad, RUNE_OF_MISTS_MIN_ATTACKER_RANGE_IN)"),
    ("Rune of Mists: the 18\" slips to 6\"",
     "game/enh_rune_of_mists.py",
     "RUNE_OF_MISTS_MIN_ATTACKER_RANGE_IN = 18.0",
     "RUNE_OF_MISTS_MIN_ATTACKER_RANGE_IN = 6.0"),
    ("Rune of Mists: the mark is ignored, so it always grants cover",
     "game/enh_rune_of_mists.py",
     "    if shooter_model is None or not is_marked(target_squad):",
     "    if shooter_model is None:"),
    ("Rune of Mists: it inherits Stave of Kurnous's TITANIC exclusion",
     "game/enh_rune_of_mists.py",
     "    return wraith_construct.is_wraith_construct_unit(squad)",
     "    return wraith_construct.is_non_titanic_wraith_construct(squad)"),
    ("Rune of Mists: it never reaches the cover computation",
     "game/shooting.py",
     "        if enh_rune_of_mists.grants_cover(shooter_model, target_squad):",
     "        if False:"),
    ("Rune of Mists: main.py stops driving its Command phase",
     "main.py",
     "            rune_of_mists_controller.begin_command_phase(turn_tracker.turn_owner)",
     "            pass"),
    # --- Camouflaged Snipers ----------------------------------------------
    ("Camouflaged Snipers: it never joins the shared question",
     "game/hidden_after_shooting.py",
     "    if enh_camouflaged_snipers.applies(squad):\n        return True",
     "    pass"),
    ("Camouflaged Snipers: the detachment gate is dropped",
     "game/enh_camouflaged_snipers.py",
     "    return enhancements.is_active(squad, CAMOUFLAGED_SNIPERS)",
     "    return True"),
    # --- Spirit Stone of Raelyth ------------------------------------------
    ("Raelyth: it is not registered as a lone-operative source",
     "game/conditional_lone_operative.py",
     "    (enh_spirit_stone_of_raelyth.grants_lone_operative,\n     enh_spirit_stone_of_raelyth.SPIRIT_STONE_RANGE_IN),",
     ""),
    ("Raelyth: the 3\" slips to 12\"",
     "game/enh_spirit_stone_of_raelyth.py",
     "SPIRIT_STONE_RANGE_IN = 3.0",
     "SPIRIT_STONE_RANGE_IN = 12.0"),
    ("Raelyth: the VEHICLE keyword is dropped",
     "game/enh_spirit_stone_of_raelyth.py",
     '    return attached_units.unit_has_keyword(\n        squad, lambda m: getattr(m.profile, "vehicle", False))',
     "    return True"),
    ("Raelyth: an undamaged vehicle is offered a heal that does nothing",
     "game/enh_spirit_stone_of_raelyth.py",
     "            if m.current_wounds < m.profile.wounds]",
     "            ]"),
    ("Raelyth: the heal overshoots the printed wounds",
     "game/enh_spirit_stone_of_raelyth.py",
     "        model.current_wounds = min(model.profile.wounds, before + healed)",
     "        model.current_wounds = before + healed"),
    ("Raelyth: the once-per-move ledger is never set, so it heals twice",
     "game/enh_spirit_stone_of_raelyth.py",
     "        self._used_this_move[id(squad)] = True",
     "        pass"),
    ("Raelyth: DECLINING spends the ability, closing the second moment",
     "game/enh_spirit_stone_of_raelyth.py",
     '        options.append(("Do not heal", lambda: False))',
     '        options.append(("Do not heal",\n                        lambda: self._used_this_move.__setitem__(id(squad), True)))'),
    ("Raelyth: the START moment is dropped",
     "game/enh_spirit_stone_of_raelyth.py",
     "        if squad is not None:\n            self._used_this_move.pop(id(squad), None)\n        self.offer(squad)",
     "        if squad is not None:\n            self._used_this_move.pop(id(squad), None)"),
    # --- the new hook ------------------------------------------------------
    ("hook: on_move_started is never fired",
     "game/movement.py",
     "        for listener in (self.on_move_started or ()):\n            listener(self.selected_squad)",
     "        pass"),
    ("hook: main.py listens only on the END of a move",
     "main.py",
     "    movement_controller.on_move_started.append(spirit_stone_controller.on_move_started)",
     "    pass"),
    ("hook: main.py listens only on the START of a move",
     "main.py",
     "    movement_controller.on_move_finished.append(spirit_stone_controller.on_move_finished)\n    movement_controller.on_move_finished.append(wraith_form_controller.on_move_finished)",
     "    movement_controller.on_move_finished.append(wraith_form_controller.on_move_finished)"),
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
