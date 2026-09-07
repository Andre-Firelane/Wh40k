"""Kauyon's Patient Hunter and Mont'ka's Killing Blow.

The two T'au detachments whose rule is the same mechanism twice - a battle
round window, an army-wide keyword grant on ranged weapons, and a second clause
that only applies while the attack is a Guided one. They are built and tested
together because what is worth guarding is mostly where they DIFFER:

  Kauyon   rounds 3-5   [SUSTAINED HITS 1]   + ignore hit modifiers (Guided)
  Mont'ka  rounds 1-3   [ASSAULT]            + [LETHAL HITS]        (Guided)

Round 3 is in BOTH windows, which is the kind of boundary a test that only
checks "round 4" and "round 1" would never see.

Sections:
  1. game/tau_detachments.py, the shared half.
  2. Kauyon's keyword grant, at its round boundaries.
  3. Kauyon's modifier clause, through the REAL ShootingController.
  4. Mont'ka's two grants.
  5. Both reach the real weapon chain.
  6. Source guards.
  7. A/B probes.
"""

import copy
import inspect
import io
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import testkit as tk  # noqa: E402
from game import (config, kauyon, montka, retaliation_cadre as rc,  # noqa: E402
                  shooting as shooting_module, tau_detachments as td)
from game.factions.orks import BOYZ  # noqa: E402
from game.factions.tau_empire import STRIKE_TEAM  # noqa: E402
from game.weapons import MELEE, RANGED  # noqa: E402

c = tk.Checks("T'au doctrines: Kauyon and Mont'ka")


# The one definition lives in testkit - eight suites had their own copy.
settings_as = tk.settings_as

class Turn:
    def __init__(self, battle_round):
        self.battle_round = battle_round


class Guided:
    """A GreaterGoodController stand-in that answers one question."""

    def __init__(self, guided=True):
        self.guided = guided

    def is_guided_attack(self, attacking_squad, target_squad):
        return self.guided


tau = tk.build(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
tk.line_up(tau, 10, 10)
orks = tk.build(BOYZ, "Player 2", name="2 Boyz 1")
tk.line_up(orks, 10, 20)
GUN = next(w for w in tau.models[0].weapons if w.weapon_type == RANGED)
BLADE = next((w for w in tau.models[0].weapons if w.weapon_type == MELEE), None)


# --- 1. The shared half ---------------------------------------------------
print("\n1. game/tau_detachments.py")

c.true("a T'au squad is recognised", td.is_tau_unit(tau))
c.true("an Ork squad is not", not td.is_tau_unit(orks))
c.true("None is not", not td.is_tau_unit(None))

with settings_as(KAUYON_PLAYERS=("Player 1",)):
    c.true("has_detachment reads the named setting", td.has_detachment("Player 1", "KAUYON_PLAYERS"))
    c.true("...and only for that player", not td.has_detachment("Player 2", "KAUYON_PLAYERS"))
    c.true("...and only that setting", not td.has_detachment("Player 1", "MONTKA_PLAYERS"))
c.true("a None player has no detachment", not td.has_detachment(None, "KAUYON_PLAYERS"))

c.true("battle_round_in finds a round in the window", td.battle_round_in(Turn(4), (3, 4, 5)))
c.true("...and misses one outside", not td.battle_round_in(Turn(2), (3, 4, 5)))
# A missing tracker reads as OUT, which withholds a bonus rather than
# inventing one - the safe direction for a rule that is otherwise army-wide.
c.true("no turn tracker reads as out of the window",
       not td.battle_round_in(None, (3, 4, 5)))

c.true("is_guided_attack degrades to False without a controller",
       not td.is_guided_attack(None, tau, orks))
c.true("...and asks the controller when there is one",
       td.is_guided_attack(Guided(True), tau, orks))

# is_tau_unit is ONE definition, shared - it moved out of the detachment module
# because "is this unit T'au" is a faction question, not a Retaliation Cadre one.
c.true("retaliation_cadre shares the faction predicate rather than copying it",
       rc.is_tau_unit is td.is_tau_unit)


# --- 2. Kauyon's keyword grant --------------------------------------------
print("\n2. Kauyon: [SUSTAINED HITS 1], rounds 3-5")


def kauyon_at(rnd, weapon=None, squad=None):
    return kauyon.adjusted_weapon(weapon or GUN, squad or tau, Turn(rnd))


with settings_as(KAUYON_PLAYERS=("Player 1",)):
    for rnd in (3, 4, 5):
        c.eq("round %d grants it" % rnd, kauyon_at(rnd).sustained_hits, 1)
    for rnd in (1, 2, 6):
        c.eq("round %d does not" % rnd, getattr(kauyon_at(rnd), "sustained_hits", 0), 0)
    c.true("a melee weapon never gets it",
           BLADE is None or getattr(kauyon_at(4, weapon=BLADE), "sustained_hits", 0) == 0)
    c.true("an Ork unit never gets it",
           getattr(kauyon.adjusted_weapon(GUN, orks, Turn(4)), "sustained_hits", 0) == 0)

    # "have the [SUSTAINED HITS 1] ability" GRANTS it; it does not SET the
    # value. A weapon already printing 2 must not be dragged down to 1.
    strong = copy.copy(GUN)
    strong.sustained_hits = 2
    c.eq("a printed [SUSTAINED HITS 2] is not downgraded",
         kauyon_at(4, weapon=strong).sustained_hits, 2)
    dice_x = copy.copy(GUN)
    dice_x.sustained_hits_notation = "D3"
    c.true("a printed dice X is left alone too",
           kauyon_at(4, weapon=dice_x) is dice_x)

with settings_as(KAUYON_PLAYERS=()):
    c.eq("without the detachment, nothing is granted",
         getattr(kauyon_at(4), "sustained_hits", 0), 0)
with settings_as(KAUYON_PLAYERS=("Player 2",)):
    c.eq("the other player having it does not help this one",
         getattr(kauyon_at(4), "sustained_hits", 0), 0)

c.eq("the shared WeaponProfile was never mutated", getattr(GUN, "sustained_hits", 0), 0)


# --- 3. Kauyon's modifier clause, through the real controller -------------
print("\n3. Kauyon: ignoring hit modifiers, end to end")


class Suppressed:
    """Any source of a WORSENING hit modifier - this is the Strike Team's own
    Suppression Volley, which _hit_modifiers checks against the SHOOTER."""

    def is_suppressed(self, squad):
        return True


class FullGreaterGood(Guided):
    def is_observer(self, squad):
        return False

    def marked_by_markerlight(self, squad):
        return False

    def is_spotted(self, squad):
        return True


scene = tk.shooting_scene(STRIKE_TEAM, BOYZ, attacker_owner="Player 1")
sc, attacker, target = scene["shooting"], scene["attacker"], scene["target"]
sc.suppression = Suppressed()
# _hit_modifiers reads self.active_squad; leaving it None would make every gate
# below answer False for a reason that has nothing to do with the rule.
sc.active_squad = attacker
scene_gun = next(w for w in attacker.models[0].weapons if w.weapon_type == RANGED)
group = {"pairs": [(attacker.models[0], scene_gun)], "target_squad": target}


def worsening(battle_round, players, greater_good):
    scene["turn"].battle_round = battle_round
    sc.greater_good = greater_good
    with settings_as(KAUYON_PLAYERS=players):
        return [m for m in sc._hit_modifiers(group) if m.amount > 0]


c.true("a worsening modifier is there to begin with",
       bool(worsening(4, (), None)))
c.true("Kauyon + Guided in round 4 drops it",
       not worsening(4, ("Player 1",), FullGreaterGood(True)))
c.true("out of the round window it stays",
       bool(worsening(2, ("Player 1",), FullGreaterGood(True))))
c.true("without the detachment it stays",
       bool(worsening(4, (), FullGreaterGood(True))))
c.true("not Guided, it stays",
       bool(worsening(4, ("Player 1",), FullGreaterGood(False))))

# The clause drops WORSENING modifiers only - an improving one is kept, which
# is the whole reason "you can ignore any or all" needs no prompt.
scene["turn"].battle_round = 4
sc.greater_good = FullGreaterGood(True)
with settings_as(KAUYON_PLAYERS=("Player 1",)):
    kept = sc._hit_modifiers(group)
c.true("an improving modifier survives", any(m.amount < 0 for m in kept))
c.true("...and no worsening one does", not any(m.amount > 0 for m in kept))


# --- 4. Mont'ka -----------------------------------------------------------
print("\n4. Mont'ka: [ASSAULT] rounds 1-3, [LETHAL HITS] while Guided")


def montka_at(rnd, guided=None, weapon=None, squad=None):
    return montka.adjusted_weapon(
        weapon or GUN, squad or tau, Turn(rnd),
        target_squad=orks, greater_good=(Guided(guided) if guided is not None else None))


with settings_as(MONTKA_PLAYERS=("Player 1",)):
    for rnd in (1, 2, 3):
        c.true("round %d grants [ASSAULT]" % rnd, montka_at(rnd).assault)
    for rnd in (4, 5):
        c.true("round %d does not" % rnd, not montka_at(rnd).assault)

    c.true("[LETHAL HITS] needs the attack to be Guided",
           not montka_at(2, guided=False).lethal_hits)
    c.true("...and is granted when it is", montka_at(2, guided=True).lethal_hits)
    c.true("...but never outside the round window",
           not montka_at(4, guided=True).lethal_hits)
    c.true("no Greater Good controller means no [LETHAL HITS]",
           not montka_at(2).lethal_hits)
    c.true("[ASSAULT] does not need Guided", montka_at(2).assault)
    c.true("a melee weapon gets neither",
           BLADE is None or not montka_at(2, weapon=BLADE).assault)
    c.true("an Ork unit gets neither",
           not montka.adjusted_weapon(GUN, orks, Turn(2)).assault)

with settings_as(MONTKA_PLAYERS=()):
    c.true("without the detachment, nothing is granted", not montka_at(2).assault)

c.true("the shared WeaponProfile was never mutated",
       not GUN.assault and not GUN.lethal_hits)


# --- 4b. Mont'ka reaches the rule-10.05 Advance gate ----------------------
print("\n4b. Mont'ka: [ASSAULT] at the Advance gate, not only in the chain")

# THE DEFECT THIS PINS. [ASSAULT] is read in two unrelated places, and section
# 4 above only ever exercised one of them:
#   * montka.adjusted_weapon() - the damage maths, which section 4 measures.
#   * coldstar.weapon_has_assault(), reached from
#     shooting.available_shooting_types(), and the ONLY thing that decides
#     whether a unit that Advanced may shoot at all (rule 10.05). That is the
#     entire reason [ASSAULT] is granted.
# Killing Blow reached the first and not the second, because its condition is a
# battle round and weapon_has_assault() is handed only (weapon, squad). It was
# recorded as a known gap justified by "no shipped army list fields Mont'ka" -
# which stopped being true when the tau_montka roster was added. Measured on
# that roster before the fix: 102 of its 151 ranged weapons refused.
#
# The condition arrives as Squad.montka_killing_blow, stamped by
# refresh_killing_blow(). So there are three things to hold apart, and a test
# that checks only the first would pass with the flag never fed:
#   1. the reader honours the flag,
#   2. the stamper sets it from the real round window,
#   3. main.py actually calls the stamper.
from game import coldstar, shooting  # noqa: E402

with settings_as(MONTKA_PLAYERS=("Player 1",)):
    # 1. THE READER. Set by hand, so this measures weapon_has_assault() and
    # nothing else.
    tau.montka_killing_blow = True
    c.true("the Advance gate sees Killing Blow's [ASSAULT]",
           coldstar.weapon_has_assault(GUN, tau))
    tau.montka_killing_blow = False
    c.true("...and without the flag it does not (the reported gap)",
           not coldstar.weapon_has_assault(GUN, tau))
    c.true("a melee weapon is never granted it",
           BLADE is None or not coldstar.weapon_has_assault(BLADE, tau))

    # 2. THE STAMPER, across the whole window and both its edges. Driven
    # through refresh_killing_blow() rather than by assignment, so the round
    # question is answered by the same is_active() the adjuster chain uses -
    # a literal (1, 2, 3) here would be a second copy of a window
    # game/tau_detachments.py owns, and would silently drop the Exemplar of the
    # Mont'ka's fourth round at this gate only.
    for rnd in (1, 2, 3):
        montka.refresh_killing_blow([tau], Turn(rnd))
        c.true("round %d stamps the flag" % rnd, tau.montka_killing_blow)
        c.true("...so the Advance gate grants [ASSAULT] in round %d" % rnd,
               coldstar.weapon_has_assault(GUN, tau))
    for rnd in (4, 5):
        montka.refresh_killing_blow([tau], Turn(rnd))
        c.true("round %d does not" % rnd, not tau.montka_killing_blow)
        c.true("...and the Advance gate refuses in round %d" % rnd,
               not coldstar.weapon_has_assault(GUN, tau))

    # The stamp is a REFRESH, not a latch: a unit stamped inside the window
    # must lose it when the window closes. Without this the flag would be
    # write-once and Killing Blow would run for the rest of the battle.
    montka.refresh_killing_blow([tau], Turn(2))
    montka.refresh_killing_blow([tau], Turn(5))
    c.true("the stamp is re-derived each time, not latched",
           not tau.montka_killing_blow)

    # END TO END through the real rule-10.05 gate: a unit that Advanced is
    # offered Assault Shooting only because this grant reaches it.
    class _Advanced:
        def __init__(self, squad):
            self.advanced_squad_ids = {squad}

    _tokens = list(tau.models) + list(orks.models)
    montka.refresh_killing_blow([tau], Turn(2))
    _with = shooting.available_shooting_types(tau, _tokens, _Advanced(tau))
    montka.refresh_killing_blow([tau], Turn(5))
    _without = shooting.available_shooting_types(tau, _tokens, _Advanced(tau))
    c.true("an Advanced unit is offered Assault Shooting inside the window",
           "Assault" in _with)
    c.true("...and is offered none outside it (the reported behaviour)",
           "Assault" not in _without)

with settings_as(MONTKA_PLAYERS=()):
    montka.refresh_killing_blow([tau], Turn(2))
    c.true("without the detachment the flag is never stamped",
           not tau.montka_killing_blow)

# An Ork unit is never stamped, whoever else fields Mont'ka.
with settings_as(MONTKA_PLAYERS=("Player 2",)):
    montka.refresh_killing_blow([orks], Turn(2))
    c.true("a non-T'au unit is never stamped", not orks.montka_killing_blow)

# 3. THE FEED. Sections 1 and 2 pass with a flag nothing ever sets - "gebaut,
# aber nie GEFUETTERT", the class this repo has been caught by six times. Only
# the source can answer it, and it is asked as the guarded CALL rather than as
# a mention, so a line in a docstring or a commented-out call cannot satisfy it.
_MAIN_SRC = io.open("main.py", encoding="utf-8").read()
c.true("main.py imports the module that owns the stamp",
       "from game import montka" in _MAIN_SRC
       or "from game import montka," in _MAIN_SRC)
c.true("main.py stamps the flag on every phase change",
       "montka.refresh_killing_blow(_detachment_squads, turn_tracker)" in _MAIN_SRC)
# ...and it is stamped BEFORE anything in that block could read it, next to the
# other Mont'ka per-phase work rather than in some later branch.
c.true("...in the per-phase reset block, beside the other Mont'ka resets",
       _MAIN_SRC.find("montka.refresh_killing_blow(")
       < _MAIN_SRC.find("aggressive_mobility_controller.reset_phase("))

# --- 5. The two together --------------------------------------------------
print("\n5. The mirror")

# Round 3 sits in BOTH windows. Pinned because a test that only tried round 1
# and round 4 would pass with either window written one round wrong.
c.true("round 3 is inside Kauyon's window", 3 in kauyon.PATIENT_HUNTER_ROUNDS)
c.true("round 3 is inside Mont'ka's window", 3 in montka.KILLING_BLOW_ROUNDS)
c.eq("Kauyon's window is rounds 3-5", kauyon.PATIENT_HUNTER_ROUNDS, (3, 4, 5))
c.eq("Mont'ka's window is rounds 1-3", montka.KILLING_BLOW_ROUNDS, (1, 2, 3))
c.eq("the two windows overlap in exactly one round",
     sorted(set(kauyon.PATIENT_HUNTER_ROUNDS) & set(montka.KILLING_BLOW_ROUNDS)), [3])

# Each gates on its OWN setting, so holding one does not confer the other.
with settings_as(KAUYON_PLAYERS=("Player 1",), MONTKA_PLAYERS=()):
    c.eq("Kauyon grants its keyword", kauyon_at(3).sustained_hits, 1)
    c.true("...and Mont'ka's is absent", not montka_at(3).assault)
with settings_as(KAUYON_PLAYERS=(), MONTKA_PLAYERS=("Player 1",)):
    c.true("Mont'ka grants its keyword", montka_at(3).assault)
    c.eq("...and Kauyon's is absent", getattr(kauyon_at(3), "sustained_hits", 0), 0)

c.eq("each reads its own config setting", (kauyon.SETTING, montka.SETTING),
     ("KAUYON_PLAYERS", "MONTKA_PLAYERS"))
# The settings really are the ones game/detachments.py writes - a rule reading a
# constant nobody writes would be inert and look fine from here.
from game import detachments  # noqa: E402
for setting in (kauyon.SETTING, montka.SETTING):
    c.true("%s is written by game/detachments.py" % setting,
           setting in detachments.all_settings())


# --- 6. Source guards -----------------------------------------------------
print("\n6. Source guards")

chain = inspect.getsource(shooting_module.ShootingController._adjusted_weapon)
c.true("Kauyon is in the weapon chain", "kauyon.adjusted_weapon(" in chain)
c.true("Mont'ka is in the weapon chain", "montka.adjusted_weapon(" in chain)
# Both grant crit-relevant keywords, so they must be applied BEFORE the hit
# step reads them - being in this chain at all is what guarantees that, and
# _crit_note() is the reason the chain exists.
c.true("Mont'ka is handed the target and the army rule",
       "target_squad=target_squad" in chain and "greater_good=self.greater_good" in chain)

mods_src = inspect.getsource(shooting_module.ShootingController._hit_modifiers)
c.true("Kauyon's second half is in the hit-modifier step",
       "kauyon.hit_modifiers_ignored(" in mods_src)
c.true("...and drops only the worsening modifiers",
       "m.amount <= 0" in mods_src)
c.true("Mont'ka has nothing in the hit-modifier step - it grants keywords",
       "montka" not in mods_src)

# Neither belongs in the Fight phase: both rules say "ranged weapons".
fight_src = io.open("game/fight.py", encoding="utf-8").read()
# Matched as "<module>." rather than as a bare name: these two are the
# detachment RULES, and their Stratagem modules (kauyon_*, montka_*) legitimately
# DO reach the Fight phase - Pinpoint Counter-Offensive says "an attack". A bare
# substring test conflated the rule with its Stratagems the moment those existed.
c.true("Kauyon's RULE is not wired into the Fight phase", "kauyon." not in fight_src)
c.true("Mont'ka's RULE is not wired into the Fight phase", "montka." not in fight_src)
c.true("...though a Mont'ka STRATAGEM is, and should be",
       "montka_pinpoint_counter_offensive" in fight_src)

# No AI path, per the standing instruction for T'au.
driver = io.open("ai/agent_driver.py", encoding="utf-8").read()
for name in ("kauyon", "montka"):
    c.true("nothing in ai/ mentions %s - by design" % name, name not in driver.lower())


# --- 7. A/B probes --------------------------------------------------------
print("\n7. A/B probes")

# Probe 1: a window written as "3 or later" instead of the printed three rounds.
_real_rounds = kauyon.PATIENT_HUNTER_ROUNDS
try:
    kauyon.PATIENT_HUNTER_ROUNDS = (3, 4, 5, 6, 7)
    with settings_as(KAUYON_PLAYERS=("Player 1",)):
        c.eq("A/B: a looser window grants it in round 6 too",
             kauyon_at(6).sustained_hits, 1)
finally:
    kauyon.PATIENT_HUNTER_ROUNDS = _real_rounds
with settings_as(KAUYON_PLAYERS=("Player 1",)):
    c.eq("A/B restored", getattr(kauyon_at(6), "sustained_hits", 0), 0)

# Probe 2: the no-downgrade guard removed - the failure it prevents.
_real_grant = kauyon.SUSTAINED_HITS_GRANTED
try:
    kauyon.SUSTAINED_HITS_GRANTED = 3
    with settings_as(KAUYON_PLAYERS=("Player 1",)):
        strong2 = copy.copy(GUN)
        strong2.sustained_hits = 2
        c.eq("A/B: granting a HIGHER value would overwrite the printed one",
             kauyon_at(4, weapon=strong2).sustained_hits, 3)
finally:
    kauyon.SUSTAINED_HITS_GRANTED = _real_grant

# Probe 3: Mont'ka's second clause read as a property of the UNIT rather than
# of the ATTACK - the plausible misreading its docstring warns about.
with settings_as(MONTKA_PLAYERS=("Player 1",)):
    c.true("A/B: read as unit-level, an unspotted target would get [LETHAL HITS]",
           montka_at(2, guided=True).lethal_hits and not montka_at(2, guided=False).lethal_hits)

c.finish()
