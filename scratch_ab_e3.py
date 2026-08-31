"""A/B probes for Etappe 3 (rolls and re-rolls).

Each entry neutralises ONE printed clause at the SOURCE and must make the
suite go red. A probe that does not bite is a finding about the TEST.
"""
import io, os, shutil, subprocess, sys

BASE = 292
PROBES = [
    # --- Mirage Field ------------------------------------------------------
    ("Mirage Field: the sign is flipped, so it HELPS the attacker",
     "game/enh_mirage_field.py",
     "MIRAGE_FIELD_PENALTY = 1",
     "MIRAGE_FIELD_PENALTY = -1"),
    ("Mirage Field: it never reaches the ranged hit step",
     "game/shooting.py",
     "        if enh_mirage_field.applies(target_squad):",
     "        if False:"),
    ("Mirage Field: it never reaches the MELEE hit step",
     "game/fight.py",
     "        if enh_mirage_field.applies(target_squad):",
     "        if False:"),
    ("Mirage Field: it asks the ATTACKER instead of the target",
     "game/enh_mirage_field.py",
     "    return enhancements.is_active(target_squad, MIRAGE_FIELD)",
     "    return False"),
    # --- Shimmerstone ------------------------------------------------------
    ("Shimmerstone: the sign is flipped",
     "game/enh_shimmerstone.py",
     "SHIMMERSTONE_PENALTY = 1",
     "SHIMMERSTONE_PENALTY = -1"),
    ("Shimmerstone: the LEADING condition is dropped",
     "game/enh_shimmerstone.py",
     '    if not attached_units.leader_ability(target_squad, "shimmerstone"):\n        return False',
     "    pass"),
    ("Shimmerstone: the ASPECT WARRIORS keyword is dropped",
     "game/enh_shimmerstone.py",
     "    return attached_units.unit_has_datasheet_keyword(target_squad, SHIMMERSTONE_KEYWORD)",
     "    return True"),
    ("Shimmerstone: it never reaches the wound step",
     "game/shooting.py",
     "        if enh_shimmerstone.applies(target_squad):",
     "        if False:"),
    ("Shimmerstone: it leaks into the MELEE chain, which its card excludes",
     "game/fight.py",
     "from game import enh_mirage_field",
     "from game import enh_mirage_field\nfrom game import enh_shimmerstone  # noqa: F401"),
    # --- Guiding Presence --------------------------------------------------
    ("Guiding Presence: the sign is flipped, so a bonus becomes a malus",
     "game/enh_guiding_presence.py",
     "GUIDING_PRESENCE_BONUS = -1",
     "GUIDING_PRESENCE_BONUS = 1"),
    ("Guiding Presence: the 6\" range is dropped",
     "game/enh_guiding_presence.py",
     "            if edge_distance(bearer_model, other) > GUIDING_PRESENCE_RANGE_IN:\n                continue",
     "            pass"),
    ("Guiding Presence: the VISIBLE clause is dropped",
     "game/enh_guiding_presence.py",
     "            if self.visible is None or self.visible(bearer_model, other):\n                return True",
     "            return True"),
    ("Guiding Presence: 'friendly' is dropped, so an enemy vehicle qualifies",
     "game/enh_guiding_presence.py",
     "    if squad is None or squad.owner != owner:",
     "    if squad is None or False:"),
    ("Guiding Presence: the VEHICLE keyword is dropped",
     "game/enh_guiding_presence.py",
     '    return attached_units.unit_has_keyword(\n        squad, lambda m: getattr(m.profile, "vehicle", False))',
     "    return True"),
    ("Guiding Presence: the mark outlives its phase",
     "game/enh_guiding_presence.py",
     "        self._marked.clear()",
     "        pass"),
    ("Guiding Presence: it never reaches the hit step",
     "game/shooting.py",
     "        if (self.guiding_presence is not None\n                and self.guiding_presence.applies(self.active_squad)):",
     "        if False:"),
    ("Guiding Presence: main.py stops driving it",
     "main.py",
     "            guiding_presence_controller.offer_at_start_of_shooting_phase(turn_tracker.turn_owner)",
     "            pass"),
    ("Guiding Presence: main.py sets the mark before clearing the old one",
     "main.py",
     "            guiding_presence_controller.reset_phase()\n            guiding_presence_controller.offer_at_start_of_shooting_phase(turn_tracker.turn_owner)",
     "            guiding_presence_controller.offer_at_start_of_shooting_phase(turn_tracker.turn_owner)\n            guiding_presence_controller.reset_phase()"),
    # --- Breath of Vaul ----------------------------------------------------
    ("Breath of Vaul: the STORM GUARDIANS keyword is dropped",
     "game/enh_breath_of_vaul.py",
     "    return attached_units.unit_has_datasheet_keyword(squad, BREATH_OF_VAUL_KEYWORD)",
     "    return True"),
    ("Breath of Vaul: the LEADING condition is dropped",
     "game/enh_breath_of_vaul.py",
     '    if not attached_units.leader_ability(squad, "breath_of_vaul"):\n        return False',
     "    pass"),
    ("Breath of Vaul: the two weapons are swapped",
     "game/enh_breath_of_vaul.py",
     "    return is_flamer(weapon) and applies(squad)",
     "    return is_fusion_gun(weapon) and applies(squad)"),
    ("Breath of Vaul: the ATTACKS half never reaches the attacks step",
     "game/shooting.py",
     "            if enh_breath_of_vaul.attacks_reroll_applies(self.active_squad, raw_weapon):",
     "            if False:"),
    ("Breath of Vaul: the DAMAGE half never joins the offer chain",
     "game/shooting.py",
     "            elif enh_breath_of_vaul.damage_reroll_applies(self.active_squad, weapon):",
     "            elif False:"),
    ("Breath of Vaul: the accepted re-roll is silent instead of a real roll",
     "game/shooting.py",
     "                roll_kind=ATTACKS_ROLL, log=self._log, is_reroll=True,",
     "                roll_kind=ATTACKS_ROLL, log=self._log,"),
    ("Breath of Vaul: it is listed as a reroll_scope source",
     "game/reroll_scope.py",
     "def is_ones_or_whole(reason):",
     "def is_ones_or_whole(reason):  # breath_of_vaul"),
    # --- the extraction ----------------------------------------------------
    ("extraction: damage_reroll stops re-exporting and becomes a copy",
     "game/damage_reroll.py",
     "from game.notation_reroll import DamageRerollOffer  # noqa: F401",
     "class DamageRerollOffer:  # noqa\n    roll_name = 'Damage'"),
    ("extraction: the roll name stops defaulting to Damage",
     "game/notation_reroll.py",
     'notation=None, roll_name="Damage"):',
     'notation=None, roll_name="Attacks"):'),
    # --- Mantle of Wisdom --------------------------------------------------
    ("Mantle of Wisdom: the ASPECT WARRIORS keyword is dropped",
     "game/enh_mantle_of_wisdom.py",
     "    return attached_units.unit_has_datasheet_keyword(squad, MANTLE_OF_WISDOM_KEYWORD)",
     "    return True"),
    ("Mantle of Wisdom: the LEADING condition is dropped",
     "game/enh_mantle_of_wisdom.py",
     '    if not attached_units.leader_ability(squad, "mantle_of_wisdom"):\n        return False',
     "    pass"),
    ("Mantle of Wisdom: only the HIT half is granted",
     "game/path_of_the_warrior.py",
     "    def wound_ones_apply(self, squad):\n        if enh_mantle_of_wisdom.applies(squad):\n            return True",
     "    def wound_ones_apply(self, squad):\n        if False:\n            return True"),
    ("Mantle of Wisdom: only the WOUND half is granted",
     "game/path_of_the_warrior.py",
     "    def hit_ones_apply(self, squad):\n        if enh_mantle_of_wisdom.applies(squad):\n            return True",
     "    def hit_ones_apply(self, squad):\n        if False:\n            return True"),
    ("Mantle of Wisdom: the pointless choice is still offered",
     "game/path_of_the_warrior.py",
     "        if enh_mantle_of_wisdom.applies(squad):\n            return False",
     "        if False:\n            return False"),
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
