"""A/B probes for Etappe 6 (pre-game, movement, return)."""
import io, os, shutil, subprocess, sys

BASE = 496
PROBES = [
    # --- Firstdrawn Blade --------------------------------------------------
    ("Firstdrawn Blade: the 9\" slips to 6\"",
     "game/enh_firstdrawn_blade.py",
     "FIRSTDRAWN_BLADE_SCOUTS_IN = 9.0",
     "FIRSTDRAWN_BLADE_SCOUTS_IN = 6.0"),
    ("Firstdrawn Blade: it OVERWRITES a longer printed Scouts range",
     "game/enh_firstdrawn_blade.py",
     "        printed = getattr(model.profile, \"scouts\", None) or 0.0\n        model.profile.scouts = max(printed, FIRSTDRAWN_BLADE_SCOUTS_IN)",
     "        model.profile.scouts = FIRSTDRAWN_BLADE_SCOUTS_IN"),
    ("Firstdrawn Blade: the detachment gate is dropped",
     "game/enh_firstdrawn_blade.py",
     "    return enhancements.is_active(squad, FIRSTDRAWN_BLADE)",
     "    return True"),
    ("Firstdrawn Blade: its step is registered AFTER the Scouts step",
     "main.py",
     "        pregame_controller.prebattle_steps.insert(0, FirstdrawnBladeStep(",
     "        pregame_controller.prebattle_steps.append(FirstdrawnBladeStep("),
    # --- Ethereal Pathway --------------------------------------------------
    ("Ethereal Pathway: it marks only the first model, not every one",
     "game/enh_ethereal_pathway.py",
     "    for model in squad.models:\n        model.profile.infiltrators = True",
     "    squad.models[0].profile.infiltrators = True"),
    ("Ethereal Pathway: the GUARDIANS keyword is dropped",
     "game/enh_ethereal_pathway.py",
     "    if not attached_units.unit_has_datasheet_keyword(squad, ETHEREAL_PATHWAY_KEYWORD):\n        return False",
     "    pass"),
    ("Ethereal Pathway: it offers a unit that already has Infiltrators",
     "game/enh_ethereal_pathway.py",
     "    return not squad_has_infiltrators(squad)",
     "    return True"),
    ("Ethereal Pathway: 'from YOUR army' is dropped",
     "game/enh_ethereal_pathway.py",
     "    if squad is None or squad.owner != owner:",
     "    if squad is None or False:"),
    ("Ethereal Pathway: its step runs AFTER the deployment order is set",
     "game/pregame.py",
     "        for step in self.deploy_armies_steps:\n            step.start(self)\n        self.state = DEPLOYING",
     "        self.state = DEPLOYING\n        for step in self.deploy_armies_steps:\n            step.start(self)"),
    ("Ethereal Pathway: it is registered as an ordinary pre-battle step",
     "main.py",
     "        pregame_controller.deploy_armies_steps.append(EtherealPathwayStep(",
     "        pregame_controller.prebattle_steps.append(EtherealPathwayStep("),
    # --- Higher Duty -------------------------------------------------------
    ("Higher Duty: the mode is NOT registered as reactive",
     "game/movement.py",
     '"raid_and_run", "overflight", "higher_duty"',
     '"raid_and_run", "overflight"'),
    ("Higher Duty: the 8\" trigger slips to 3\"",
     "game/enh_higher_duty.py",
     "HIGHER_DUTY_TRIGGER_RANGE_IN = 8.0",
     "HIGHER_DUTY_TRIGGER_RANGE_IN = 3.0"),
    ("Higher Duty: the move slips to 3\"",
     "game/enh_higher_duty.py",
     "HIGHER_DUTY_MOVE_IN = 6.0",
     "HIGHER_DUTY_MOVE_IN = 3.0"),
    ("Higher Duty: the Engagement Range clause is read off the MOVER",
     "game/enh_higher_duty.py",
     "        return not squad.is_engaged(self._tokens())",
     "        return not mover.is_engaged(self._tokens())"),
    ("Higher Duty: it reacts to a FRIENDLY unit's move too",
     "game/enh_higher_duty.py",
     "        if squad is None or mover is None or squad.owner == mover.owner:",
     "        if squad is None or mover is None:"),
    ("Higher Duty: the trigger distance is not checked",
     "game/enh_higher_duty.py",
     "        if not self._within(squad, mover, HIGHER_DUTY_TRIGGER_RANGE_IN):\n            return False",
     "        pass"),
    ("Higher Duty: the detachment gate is dropped",
     "game/enh_higher_duty.py",
     "        if not has_bearer(squad):\n            return False",
     "        pass"),
    ("Higher Duty: active_player is never handed back",
     "game/enh_higher_duty.py",
     "            self.turn_tracker.set_active(self._restore_active)",
     "            pass"),
    ("Higher Duty: the panel stops routing Confirm to it",
     "game/ui/action_panel.py",
     "                confirm_callback = higher_duty_controller.confirm_move",
     "                pass"),
    ("Higher Duty: an open move no longer blocks the phase change",
     "main.py",
     "            or higher_duty_controller.is_busy",
     "            or False"),
    ("Higher Duty: main.py stops feeding it",
     "main.py",
     "    movement_controller.on_move_finished.append(higher_duty_controller.on_move_finished)",
     "    pass"),
    # --- Phoenix Gem -------------------------------------------------------
    # The bug the suite found: is_active() filters the dead, so the ONE state
    # this ability ever sees would answer False.
    ("Phoenix Gem: the gate uses is_active(), which is False for a dead bearer",
     "game/enh_phoenix_gem.py",
     "        if not is_bearer(model) or not detachment_active(squad):",
     "        if not is_bearer(model) or not enhancements.is_active(squad, PHOENIX_GEM):"),
    ("Phoenix Gem: 'the FIRST time' is dropped, so it returns every death",
     "game/enh_phoenix_gem.py",
     "        if id(model) in self._used:\n            return False              # \"the FIRST time\" - once per battle",
     "        pass"),
    ("Phoenix Gem: the 2+ slips to 4+",
     "game/enh_phoenix_gem.py",
     "PHOENIX_GEM_THRESHOLD = 2",
     "PHOENIX_GEM_THRESHOLD = 4"),
    ("Phoenix Gem: it returns on a 1 as well",
     "game/enh_phoenix_gem.py",
     "        if roll < PHOENIX_GEM_THRESHOLD:",
     "        if False:"),
    ("Phoenix Gem: the Engagement Range clause is dropped",
     "game/enh_phoenix_gem.py",
     "            if not model_return.clear_of_engagement(model, x_in, y_in, enemies):\n                continue",
     "            pass"),
    ("Phoenix Gem: main.py stops noting the death",
     "main.py",
     "            phoenix_gem_controller.notify_model_destroyed(",
     "            _unused_phoenix = (lambda *a, **k: None)("),
    ("Phoenix Gem: main.py stops rolling at the end of the phase",
     "main.py",
     "        phoenix_gem_controller.resolve_end_of_phase()",
     "        pass"),
    # --- the SpiritMarkController repair -----------------------------------
    ("Spirit Mark: the offer's answer is dropped again",
     "game/spiritseer.py",
     "    def on_move_started(self, squad):\n        return self.offer(squad)",
     "    def on_move_started(self, squad):\n        self.offer(squad)"),
    ("Spirit Mark: main.py stops feeding it at the start of a move",
     "main.py",
     "    movement_controller.on_move_started.append(spirit_mark_controller.on_move_started)",
     "    pass"),
    ("Spirit Mark: its own reset point is not driven",
     "main.py",
     "            spirit_mark_controller.start_of_movement_phase(turn_tracker.turn_owner)",
     "            pass"),
    ("Spirit Mark: 'once per turn' is dropped",
     "game/spiritseer.py",
     "                and bearer_squad.owner not in self._used_this_turn)",
     "                and True)"),
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
