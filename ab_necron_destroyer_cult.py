"""A/B probes for Etappe 3 - Hexmark Destroyer, Ophydian Destroyers, Nekrosor
Ammentar.

Each probe restores ONE printed clause to a pre-fix state AT THE SOURCE and
must make the suite that covers it go red. A probe that does not bite is a
finding about the TEST, not an all-clear.

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

SUITE = "test_necron_destroyer_cult.py"
SHEETS = "test_necron_datasheets.py"
KROOT = "test_tau_kroot_and_vespid.py"
AELDARI = "test_aeldari_enhancements.py"

BS = chr(92)   # a real backslash, built rather than escaped - see error class 21

PROBES = [
    # --- Inescapable Death: three clauses, two entitlements -----------------
    # The two that share a sentence, each on its own.
    # "For 0CP" read as "-1CP" - the exact wrong reading
    # game/free_stratagem_once_per_round.py's docstring warns about, and one
    # that looks right on every 1CP Stratagem. Written as a card-specific
    # override rather than a change to the shared base, so it neutralises THIS
    # card and not its two Aeldari cousins.
    ("Inescapable Death makes Fire Overwatch CHEAPER rather than free",
     [("game/inescapable_death.py",
       "    def window_key(self):",
       "    def available_discount(self, player, stratagem=None, targets=()):\n"
       "        if not self.matches_stratagem(stratagem) or not self.available(player):\n"
       "            return 0\n"
       "        if not any(self.unit_has_ability(t) for t in targets or ()):\n"
       "            return 0\n"
       "        return 1\n"
       "\n"
       "    def window_key(self):")],
     [SUITE]),

    ("...and its 15.01 exemption is dropped",
     [("game/inescapable_death.py",
       "        return self.available_discount(player, stratagem, targets) > 0",
       "        return False")],
     [SUITE]),

    ("...the exemption is granted UNCONDITIONALLY instead",
     [("game/inescapable_death.py",
       "        return self.available_discount(player, stratagem, targets) > 0",
       "        return True")],
     [SUITE]),

    # THE WINDOW. Every other cp_discount consumer prints "once per battle
    # round"; inheriting that here halves the card, and a test that only
    # advanced the ROUND would never notice.
    ("the once-per-TURN window falls back to once per battle round",
     [("game/inescapable_death.py",
       "        return (getattr(self.turn_tracker, \"battle_round\", None),\n"
       "                getattr(self.turn_tracker, \"turn_owner\", None))",
       "        return getattr(self.turn_tracker, \"battle_round\", None)")],
     [SUITE]),

    # The third clause, which shares NO entitlement.
    ("the 2+ Snap Shooting threshold never reaches 15.09",
     [("game/shooting.py",
       "            hexmark = inescapable_death.snap_hit_threshold(self.active_squad)",
       "            hexmark = None")],
     [SUITE]),

    ("...or is LATCHED to the free use, the way Protector of the Paths is",
     [("game/inescapable_death.py",
       "    if not unit_has_bearer(squad):\n        return None\n"
       "    return INESCAPABLE_DEATH_HIT_THRESHOLD",
       "    if not unit_has_bearer(squad):\n        return None\n"
       "    if getattr(squad, \"_free_overwatch_spent\", True):\n        return None\n"
       "    return INESCAPABLE_DEATH_HIT_THRESHOLD")],
     [SUITE]),

    # --- Multi-threat Eliminator, and the shape it now shares ---------------
    ("Multi-threat Eliminator takes Kroot Packmates' 6\" instead of its 3\"",
     [("game/multi_threat_eliminator.py",
       "MULTI_THREAT_ELIMINATOR_RANGE_IN = 3.0",
       "MULTI_THREAT_ELIMINATOR_RANGE_IN = 6.0")],
     [SUITE]),

    ("...it protects any friendly unit rather than a NECRONS one",
     [("game/multi_threat_eliminator.py",
       "    return any(getattr(m.profile, \"reanimation_protocols\", False)\n"
       "               for m in getattr(squad, \"models\", ()) or () if not m.is_dead())",
       "    return True")],
     [SUITE]),

    ("...the \"must target only that enemy unit\" restriction is dropped",
     [("game/reactive_bodyguard_shooting.py",
       "        return self.shooting_controller.start_reactive_shooting(\n"
       "            reactor, restrict_to=attacker)",
       "        return self.shooting_controller.start_reactive_shooting(reactor)")],
     [SUITE]),

    ("...and it fires at the TRIGGER rather than after the attacker finishes",
     [("game/reactive_bodyguard_shooting.py",
       "        self._used_this_turn[reactor.owner] = self._turn_key()\n"
       "        self._owed = (reactor, attacking_squad)",
       "        self._used_this_turn[reactor.owner] = self._turn_key()\n"
       "        self._owed = None")],
     [SUITE]),

    # THE EXTRACTION ITSELF. A change to the shared base that only one of its
    # two carriers notices is exactly the drift it was made to prevent, so
    # this one has to make the KROOT suite red as well.
    ("the shared base stops declining MELEE attacks",
     [("game/reactive_bodyguard_shooting.py",
       "        if melee:\n            return False\n"
       "        return self.on_targets_selected(attacking_squad, [target_squad])",
       "        return self.on_targets_selected(attacking_squad, [target_squad])")],
     [SUITE, KROOT]),

    ("...and the once-per-turn ledger becomes per SQUAD rather than per army",
     [("game/reactive_bodyguard_shooting.py",
       "        return self._used_this_turn.get(player) != self._turn_key()",
       "        return True")],
     [KROOT]),

    # --- Protective Disciples ------------------------------------------------
    ("Protective Disciples widens to any friendly NECRONS unit (Szeras's text)",
     [("game/nekrosor_ammentar.py",
       "            if not _is_destroyer_cult_unit(other):\n                continue",
       "            if not _is_necron_unit(other):\n                continue")],
     [SUITE]),

    ("...and its 3\" stops being measured",
     [("game/nekrosor_ammentar.py",
       "            gap = _model_range_to_squad(model, other)\n"
       "            if gap is not None and gap <= PROTECTIVE_DISCIPLES_RANGE_IN:\n"
       "                return True",
       "            return True")],
     [SUITE]),

    ("...it is never registered in the shared conditional fold",
     [("game/conditional_lone_operative.py",
       "    (nekrosor_ammentar.grants_lone_operative,\n"
       "     nekrosor_ammentar.PROTECTIVE_DISCIPLES_LONE_OPERATIVE_RANGE_IN),\n",
       "")],
     [SUITE, AELDARI]),

    # --- Infectious Murder-madness -------------------------------------------
    # The two clauses are joined by "or", so each is neutralised on its own.
    ("the DESTROYER CULT half is dropped - only the closest target qualifies",
     [("game/nekrosor_ammentar.py",
       "    return model_has_datasheet_keyword(attacking_squad, attacking_model,\n"
       "                                       DESTROYER_CULT_KEYWORD)",
       "    return False")],
     [SUITE]),

    ("...the closest-target half is dropped",
     [("game/nekrosor_ammentar.py",
       "    if target_is_closest:\n        return True",
       "    pass")],
     [SUITE]),

    ("...the aura grants unconditionally, ignoring both clauses",
     [("game/nekrosor_ammentar.py",
       "    if target_is_closest:\n        return True\n"
       "    return model_has_datasheet_keyword(attacking_squad, attacking_model,\n"
       "                                       DESTROYER_CULT_KEYWORD)",
       "    return True")],
     [SUITE]),

    ("...the MONSTER exclusion is dropped",
     [("game/nekrosor_ammentar.py",
       "    if unit_has_keyword(squad, lambda m: getattr(m.profile, \"monster\", False)):\n"
       "        return True",
       "    pass")],
     [SUITE]),

    ("...the TITANIC exclusion is dropped",
     [("game/nekrosor_ammentar.py",
       "    return titanic.is_titanic_unit(squad)",
       "    return False")],
     [SUITE]),

    ("...the 6\" stops being measured",
     [("game/nekrosor_ammentar.py",
       "        gap = _model_range_to_squad(token, squad)\n"
       "        if gap is not None and gap <= MURDER_MADNESS_RANGE_IN:\n"
       "            return True\n"
       "    return False\n"
       "\n"
       "\n"
       "def murder_madness_applies",
       "        return True\n"
       "    return False\n"
       "\n"
       "\n"
       "def murder_madness_applies")],
     [SUITE]),

    ("...and the grant MUTATES the shared weapon instance instead of copying",
     [("game/nekrosor_ammentar.py",
       "    granted = copy.copy(weapon)\n"
       "    granted.sustained_hits = MURDER_MADNESS_SUSTAINED_HITS\n"
       "    return granted",
       "    weapon.sustained_hits = MURDER_MADNESS_SUSTAINED_HITS\n"
       "    return weapon")],
     [SUITE]),

    ("...and it OVERWRITES a printed [SUSTAINED HITS 2] with its own 1",
     [("game/nekrosor_ammentar.py",
       "    if getattr(weapon, \"sustained_hits\", 0) >= MURDER_MADNESS_SUSTAINED_HITS:\n"
       "        return weapon",
       "    pass")],
     [SUITE]),

    # --- Prophet of Destruction ----------------------------------------------
    ("Prophet of Destruction includes the killer's OWN unit",
     [("game/nekrosor_ammentar.py",
       "    for other in _friendly_squads(all_tokens, owner, exclude=killer_squad):\n"
       "        if not _is_destroyer_cult_unit(other):",
       "    for other in _friendly_squads(all_tokens, owner):\n"
       "        if not _is_destroyer_cult_unit(other):")],
     [SUITE]),

    ("...its 9\" stops being measured",
     [("game/nekrosor_ammentar.py",
       "        if gap is not None and gap <= PROPHET_RANGE_IN:\n"
       "            out.append(other)",
       "        out.append(other)")],
     [SUITE]),

    ("...it grants to any friendly unit, not just a DESTROYER CULT one",
     [("game/nekrosor_ammentar.py",
       "    for other in _friendly_squads(all_tokens, owner, exclude=killer_squad):\n"
       "        if not _is_destroyer_cult_unit(other):\n"
       "            continue",
       "    for other in _friendly_squads(all_tokens, owner, exclude=killer_squad):\n"
       "        pass\n"
       "    for other in _friendly_squads(all_tokens, owner, exclude=killer_squad):\n"
       "        if False:\n"
       "            continue")],
     [SUITE]),

    ("...and the grant survives the end of the phase",
     [("game/nekrosor_ammentar.py",
       "    for squad in squads or ():\n        squad.prophet_of_destruction = False",
       "    pass")],
     [SUITE]),

    # --- Nullstone Field Generator -------------------------------------------
    # "against mortal wounds and Psychic Attacks" - an OR over two kinds of
    # wound AND a limit on every other kind. Each half on its own.
    ("Nullstone covers ORDINARY wounds too",
     [("game/nekrosor_ammentar.py",
       "    if model is None or not (mortal or psychic):\n        return \"-\"",
       "    if model is None:\n        return \"-\"")],
     [SUITE]),

    ("...it stops covering PSYCHIC attacks",
     [("game/nekrosor_ammentar.py",
       "    if model is None or not (mortal or psychic):\n        return \"-\"",
       "    if model is None or not mortal:\n        return \"-\"")],
     [SUITE]),

    ("...its 6\" aura stops being measured",
     [("game/nekrosor_ammentar.py",
       "        gap = _model_range_to_squad(token, squad)\n"
       "        if gap is not None and gap <= NULLSTONE_RANGE_IN:\n"
       "            return True",
       "        return True")],
     [SUITE]),

    ("...and it never reaches the Feel No Pain fold at all",
     [("game/feel_no_pain.py",
       "    return _better_threshold(\n"
       "        best, nullstone_feel_no_pain(model, mortal=mortal, psychic=psychic))",
       "    return best")],
     [SUITE]),

    # --- Tunnelling Horrors ---------------------------------------------------
    # The withdrawal is Airborne Agility's and is covered elsewhere; what is
    # NEW is the round-gate override, so that is what these three attack.
    ("Tunnelling Horrors loses its round-gate override",
     [("game/ingress.py",
       "        if tunnelling_horrors.applies(squad):\n            return True",
       "        pass")],
     [SUITE]),

    ("...the obligation is never armed",
     [("game/tunnelling_horrors.py",
       "        squad.tunnelling_horrors_owed = True",
       "        squad.tunnelling_horrors_owed = False")],
     [SUITE]),

    ("...and the obligation survives the Movement phase it was owed in",
     [("game/tunnelling_horrors.py",
       "    for squad in squads or ():\n        squad.tunnelling_horrors_owed = False",
       "    pass")],
     [SUITE]),

    ("...an ENGAGED unit may tunnel",
     [("game/tunnelling_horrors.py",
       "                and not engagement.is_engaged(squad, tokens))",
       "                and True)")],
     [SUITE]),

    # --- the Plasmacyte, and the offer it never had --------------------------
    # THE HEADLINE FIND. Its grant, its reset and its token count all shipped
    # and worked; nothing ever asked. This probe restores exactly that world.
    ("nothing OFFERS the Plasmacyte - the shipped world",
     [("game/fight.py",
       "        if self.plasmacyte is not None:\n            self.plasmacyte.offer(squad)",
       "        pass")],
     [SUITE]),

    ("...main.py never hands the offer to FightController",
     [("main.py",
       "        plasmacyte=PlasmacyteController(\n"
       "            decision_manager=decision_manager, game_log=game_log,\n"
       "            auto_players=ai_players),",
       "        plasmacyte=None,")],
     [SUITE]),

    ("...and a human owner is answered for instead of asked",
     [("game/plasmacyte.py",
       "        if squad.owner in self.auto_players or self.decision_manager is None:\n"
       "            return self._use(squad)",
       "        return self._use(squad)")],
     [SUITE]),

    # --- the datasheets themselves -------------------------------------------
    ("the Hexmark's Close combat weapon is folded into the A2 one",
     [("game/weapons.py",
       "class NecronCloseCombatWeaponA4S5Profile(WeaponProfile):",
       "class NecronCloseCombatWeaponA4S5Profile(NecronCloseCombatWeaponA2Profile):\n"
       "    pass\n\n\nclass _UnusedA4S5(WeaponProfile):")],
     [SUITE]),

    ("Nekrosor Ammentar is shrunk to the Destroyer size",
     [("game/units.py",
       "    name = \"Nekrosor Ammentar\"\n    base_radius_in = 1.575          # 80 mm",
       "    name = \"Nekrosor Ammentar\"\n    base_radius_in = 0.984")],
     [SUITE]),

    ("...and he loses Fights First",
     [("game/units.py",
       "    fights_first = True             # rule 24.13 (CORE), not rule 11.04's post-charge grant",
       "    fights_first = False")],
     [SUITE]),
]


def clear_cache():
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
