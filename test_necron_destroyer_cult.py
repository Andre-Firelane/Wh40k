"""Hexmark Destroyer, Ophydian Destroyers and Nekrosor Ammentar (Etappe 3).

THREE DATASHEETS AND EIGHT ABILITIES, and almost every one of them is a second
carrier of something that already existed - so this suite is mostly about
whether each landed on the seam its printed text names, and about the four
places where the new text differs from the text it resembles.

WHERE THIS MEASURES, AND WHY THERE
----------------------------------
  * INESCAPABLE DEATH is measured as THREE separate clauses, because only two
    of them share an entitlement. The 0CP and the 15.01 exemption are one
    sentence and one once-per-TURN allowance; the 2+ threshold opens with
    "each time" and is therefore NOT latched to the free use. Its near-twin,
    Protector of the Paths, says "while resolving THAT Stratagem" and IS
    latched - so the test drives a SECOND, fully paid Fire Overwatch and
    demands it still hits on 2+. A copied implementation passes every other
    line here and fails that one.

  * THE ONCE-PER-TURN WINDOW is measured across a TURN boundary and across a
    ROUND boundary separately. Every other cp_discount consumer prints "once
    per battle round", and a battle round holds both players' turns - so a
    test that only advanced the round would pass with the window left at its
    inherited value, and the card would be worth half what it prints.

  * INFECTIOUS MURDER-MADNESS is measured with the DESTROYER CULT half and the
    closest-target half SEPARATELY, and each with the other switched off.
    They are joined by "or", so a test that stages both at once passes with
    either one unimplemented. The MONSTER/TITANIC exclusion gets its own pair
    for the same reason.

  * NULLSTONE is measured against a MORTAL wound, a PSYCHIC one, and an
    ORDINARY one. "against mortal wounds and Psychic Attacks" is an OR over
    two kinds of wound and a limit on every other kind; only the third case
    separates "the aura works" from "the aura is unconditional".

  * PROTECTIVE DISCIPLES is measured beside a NON-DESTROYER-CULT friendly
    unit as well as beside a DESTROYER CULT one. Illuminor Szeras's identical
    sentence asks only for NECRONS, so the narrower keyword is the whole
    difference between the two and is the half a copy would lose.

  * THE PLASMACYTE is measured END TO END through a real FightController
    activation, not by calling use(). Its grant, its reset and its token count
    all shipped and worked; what was missing was that NOTHING EVER ASKED, and
    only driving the selection step can see that.

  * TUNNELLING HORRORS is measured on the ROUND GATE, in battle round 1. The
    withdrawal itself is Airborne Agility's and is already covered; what is
    new is that the unit may come back at all before round 2, which is what
    its printed parenthesis "(including in your first turn)" buys.
"""
import io

import testkit as tk
from testkit import Checks

from game import (conditional_lone_operative, feel_no_pain, inescapable_death,
                  ingress, multi_threat_eliminator, nekrosor_ammentar,
                  plasmacyte, sprites, status_effects, tunnelling_horrors)
from game.attached_units import model_has_datasheet_keyword
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.factions import necrons as nec
from game.factions.necrons_points import NECRONS_POINTS
from game.game_state import GameState
from game.stratagems import Stratagem, StratagemController
from game.turn import TurnTracker
from game.units import (HexmarkDestroyerProfile, NekrosorAmmentarProfile,
                        OphydianDestroyerProfile)
from game.weapons import (BladeTailAndWhipCoilsProfile,
                          EnmiticDisintegratorPistolsProfile,
                          EnmiticDisintegratorsProfile,
                          NecronCloseCombatWeaponA1Profile,
                          NecronCloseCombatWeaponA2Profile,
                          NecronCloseCombatWeaponA4S5Profile,
                          OphydianHyperphaseWeaponsProfile,
                          UnmakerGauntletProfile, WhipCoilsProfile)

checks = Checks("Necron Destroyer Cult")

D = nec.NECRONS.datasheets
HEXMARK = D["Hexmark Destroyer"]
OPHYDIAN = D["Ophydian Destroyers"]
NEKROSOR = D["Nekrosor Ammentar"]
SKORPEKH = D["Skorpekh Destroyers"]
WARRIORS = D["Necron Warriors"]
IMMORTALS = D["Immortals"]

SHEETS = [(HEXMARK, HexmarkDestroyerProfile),
          (OPHYDIAN, OphydianDestroyerProfile),
          (NEKROSOR, NekrosorAmmentarProfile)]


def build(sheet, owner="Player 2", n=1, **kw):
    """Named the way main.py names squads - see the sprite trap in
    game/sprites.py's _key_for_name()."""
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


def place(squad, x, y, spacing=1.4):
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + i * spacing, y
    return squad


class _Tokens(list):
    """all_tokens is a flat list of MODELS in this engine."""


def tokens(*squads):
    out = _Tokens()
    for s in squads:
        out.extend(s.models)
    return out


# =========================================================================
# 1. statlines
# =========================================================================
print("--- 1. statlines ---")

for sheet, profile in SHEETS:
    checks.true("%s: Reanimation Protocols" % sheet.name, profile.reanimation_protocols)

checks.eq("Hexmark: M8\" T5 Sv3+ W5 Ld6+ OC1 on 50 mm",
          (HexmarkDestroyerProfile.movement_in, HexmarkDestroyerProfile.toughness,
           HexmarkDestroyerProfile.armor_save, HexmarkDestroyerProfile.wounds,
           HexmarkDestroyerProfile.leadership, HexmarkDestroyerProfile.oc,
           round(HexmarkDestroyerProfile.base_radius_in, 3)),
          (8, 5, "3+", 5, "6+", 1, 0.984))
checks.eq("...WS3+ / BS2+, the two rows disagreeing on purpose",
          (HexmarkDestroyerProfile.weapon_skill, HexmarkDestroyerProfile.ballistic_skill),
          ("3+", "2+"))
checks.true("...CHARACTER with Deep Strike",
            HexmarkDestroyerProfile.character and HexmarkDestroyerProfile.deep_strike)
checks.eq("...LONE OPERATIVE is PRINTED, not conditional like his two cousins'",
          HexmarkDestroyerProfile.lone_operative, 12.0)

checks.eq("Ophydian: M10\" T5 Sv4+ W3 Ld7+ OC2 on 50 mm",
          (OphydianDestroyerProfile.movement_in, OphydianDestroyerProfile.toughness,
           OphydianDestroyerProfile.armor_save, OphydianDestroyerProfile.wounds,
           OphydianDestroyerProfile.leadership, OphydianDestroyerProfile.oc,
           round(OphydianDestroyerProfile.base_radius_in, 3)),
          (10, 5, "4+", 3, "7+", 2, 0.984))
checks.true("...Deep Strike, so Tunnelling Horrors grants none",
            OphydianDestroyerProfile.deep_strike)

checks.eq("Nekrosor: M10\" T8 Sv3+ W9 Ld6+ OC3, 4+ invulnerable",
          (NekrosorAmmentarProfile.movement_in, NekrosorAmmentarProfile.toughness,
           NekrosorAmmentarProfile.armor_save, NekrosorAmmentarProfile.wounds,
           NekrosorAmmentarProfile.leadership, NekrosorAmmentarProfile.oc,
           NekrosorAmmentarProfile.invulnerable_save),
          (10, 8, "3+", 9, "6+", 3, "4+"))
checks.true("...EPIC HERO with Fights First (24.13, not 11.04's grant)",
            NekrosorAmmentarProfile.epic_hero and NekrosorAmmentarProfile.fights_first)

# THE BASE SIZE IS A DECISION, so it is pinned with its reason. The standing
# instruction "alle Destroyer sollen die gleiche Groesse haben" put both Lords
# on 50 mm despite their printed 60, and the reason recorded with it is rule
# 19.01 - a Lord is MERGED into a Destroyer squad. Nekrosor Ammentar prints no
# LEADER line, so that reason cannot reach him.
checks.eq("Nekrosor keeps his printed 80 mm",
          round(NekrosorAmmentarProfile.base_radius_in, 3), 1.575)
checks.true("...and he can never be merged into a 50 mm squad - no LEADER line",
            not getattr(NekrosorAmmentarProfile, "leader", False)
            and NECRONS_POINTS["Nekrosor Ammentar"].leads == ()
            and NECRONS_POINTS["Nekrosor Ammentar"].supports == ())
checks.true("...while every sheet whose NAME says Destroyer is still 50 mm",
            all(round(p.base_radius_in, 3) == 0.984
                for s, p in ((HEXMARK, HexmarkDestroyerProfile),
                             (OPHYDIAN, OphydianDestroyerProfile))
                if "Destroyer" in s.name))


# =========================================================================
# 2. weapons, and the third "Close combat weapon"
# =========================================================================
print("--- 2. weapons ---")

cc4 = NecronCloseCombatWeaponA4S5Profile()
cc1, cc2 = NecronCloseCombatWeaponA1Profile(), NecronCloseCombatWeaponA2Profile()
checks.eq("Hexmark's Close combat weapon: A4 S5 AP0 D1",
          (cc4.attacks, cc4.strength, cc4.ap, cc4.damage), (4, 5, 0, 1))
# Pinned AGAINST the two that already exist rather than against literals: the
# assurance is that the three are DIFFERENT, which is what stops a fourth
# being folded into one of them.
checks.true("...one printed name, THREE sets of numbers, all distinct",
            len({(w.attacks, w.strength, w.ap, w.damage) for w in (cc1, cc2, cc4)}) == 3)
checks.true("...and all three really print the same name",
            cc1.name == cc2.name == cc4.name)

edp = EnmiticDisintegratorPistolsProfile()
checks.eq("Enmitic disintegrator pistols: 18\" A6 S6 AP-2 D1",
          (edp.range_in, edp.attacks, edp.strength, edp.ap, edp.damage),
          (18, 6, 6, -2, 1))
from game.weapons import printed_keywords  # noqa: E402
checks.eq("...its printed keyword column, exactly as the corpus prints it",
          printed_keywords(edp), ["IGNORES COVER", "PISTOL"])

ohw = OphydianHyperphaseWeaponsProfile()
checks.eq("Ophydian hyperphase weapons: A5 S4 AP-2 D2",
          (ohw.attacks, ohw.strength, ohw.ap, ohw.damage), (5, 4, -2, 2))

ed = EnmiticDisintegratorsProfile()
checks.eq("Enmitic disintegrators: 18\" A4 S6 AP-2 D1",
          (ed.range_in, ed.attacks, ed.strength, ed.ap, ed.damage), (18, 4, 6, -2, 1))
checks.eq("...[SUSTAINED HITS 2]", ed.sustained_hits, 2)
checks.true("...and it is NOT the Hexmark's pistols - different name and numbers",
            ed.name != edp.name and ed.attacks != edp.attacks)

bt, wc = BladeTailAndWhipCoilsProfile(), WhipCoilsProfile()
checks.eq("Blade tail and whip coils: A6 S6 AP-1 D1 [EXTRA ATTACKS]",
          (bt.attacks, bt.strength, bt.ap, bt.damage, bt.extra_attacks),
          (6, 6, -1, 1, True))
# The Canoptek Wraiths' "Whip Coils" LOOKS like a shorter spelling of it.
checks.true("...and the Wraiths' Whip Coils is a different weapon entirely",
            bt.name != wc.name
            and (bt.attacks, bt.strength, bt.ap) != (wc.attacks, wc.strength, wc.ap))

ug = UnmakerGauntletProfile()
checks.eq("Unmaker Gauntlet: A6 S10 AP-3 D3",
          (ug.attacks, ug.strength, ug.ap, ug.damage), (6, 10, -3, 3))


# =========================================================================
# 3. composition, points and the Plasmacyte gear
# =========================================================================
print("--- 3. composition, points, gear ---")

hex_sq = build(HEXMARK)
checks.eq("Hexmark: 1 model, 75 pts", (len(hex_sq.models), hex_sq.points), (1, 75))
checks.eq("...both printed rows",
          sorted(w.name for w in hex_sq.models[0].weapons),
          ["Close Combat Weapon", "Enmitic disintegrator pistols"])

for ci, n, pts in ((0, 3, 80), (1, 6, 150)):
    sq = build(OPHYDIAN, composition_index=ci)
    checks.eq("Ophydian: %d models, %d pts (1st-2nd unit)" % (n, pts),
              (len(sq.models), sq.points), (n, pts))
_oph_tiers = NECRONS_POINTS["Ophydian Destroyers"].tiers
checks.eq("...3rd+ unit is 90/160", _oph_tiers[1].costs, {3: 90, 6: 160})
checks.eq("...and the 1st-2nd block really covers only those two",
          (_oph_tiers[0].from_unit, _oph_tiers[0].to_unit), (1, 2))

nek = build(NEKROSOR)
checks.eq("Nekrosor: 1 model, 185 pts", (len(nek.models), nek.points), (1, 185))
checks.eq("...three printed rows",
          sorted(w.name for w in nek.models[0].weapons),
          ["Blade tail and whip coils", "Enmitic disintegrators", "Unmaker Gauntlet"])

# The Plasmacyte is the SAME printed wargear the Skorpekh Destroyers carry, so
# it shares their equip callback - measured rather than assumed.
oph2 = build(OPHYDIAN, composition_index=1,
             gear={"Ophydian Destroyer": ["Plasmacyte", "Plasmacyte"]})
checks.eq("Ophydian may take two Plasmacytes (6 models)",
          plasmacyte.plasmacyte_count(oph2), 2)
checks.eq("...and they are FREE, like the Skorpekh's", oph2.points, 150)
checks.eq("...two uses, one per Plasmacyte", plasmacyte.remaining_uses(oph2), 2)


# =========================================================================
# 4. Inescapable Death - three clauses, two entitlements
# =========================================================================
print("--- 4. Inescapable Death ---")


def strat_scene():
    """A real StratagemController with a real CP account, plus the discount in
    BOTH lists exactly as main.py registers it."""
    tt = TurnTracker()
    tt.battle_round = 2
    tt.turn_owner = "Player 1"
    cp = CommandPointManager()
    cp.cp["Player 2"] = 5
    sc = StratagemController(command_points=cp)
    disc = inescapable_death.InescapableDeathDiscount(turn_tracker=tt)
    sc.cost_discounts.append(disc)
    sc.repeat_permissions.append(disc)
    return tt, cp, sc, disc


OVERWATCH = Stratagem(name="Fire Overwatch", cp_cost=1, effect=lambda *a: None)

tt, cp, sc, disc = strat_scene()
hexmark = build(HEXMARK)
other = build(IMMORTALS)

# Clause 1: for 0CP.
checks.eq("Fire Overwatch on the Hexmark costs 0 CP",
          sc._cost_for("Player 2", OVERWATCH, [hexmark], 0), 0)
checks.eq("...and on anything else it costs its printed 1",
          sc._cost_for("Player 2", OVERWATCH, [other], 0), 1)
# "FOR 0CP" IS NOT "-1CP", and on the shipped card the two readings COINCIDE:
# Fire Overwatch costs exactly 1, so a flat -1 also comes to nothing. That is
# the mistake game/free_stratagem_once_per_round.py's own docstring warns about
# ("would look right on every 1CP Stratagem"), and an A/B probe that installed
# it reported NO BITE against every line above. So the assurance is measured at
# a CONSTRUCTED higher cost - the same treatment this repo gives every
# mechanism whose live case cannot separate two readings.
_dear = Stratagem(name="Fire Overwatch", cp_cost=3, effect=lambda *a: None)
checks.eq("the discount is the WHOLE cost, not a flat 1",
          sc._cost_for("Player 2", _dear, [hexmark], 0), 0)

# Clause 2: even if already used this phase, and ONLY for the bearer.
sc.use("Player 2", OVERWATCH, [other])
checks.eq("...a second Fire Overwatch on a NON-bearer is refused by 15.01",
          sc.refusal("Player 2", OVERWATCH, [build(WARRIORS)], 0),
          "already used this phase (15.01)")
checks.true("...but the Hexmark may still be targeted this phase",
            sc.can_use("Player 2", OVERWATCH, [hexmark]))
checks.eq("...and that use is still free", cp.cp["Player 2"], 4)
sc.use("Player 2", OVERWATCH, [hexmark])
checks.eq("...paid nothing for it", cp.cp["Player 2"], 4)

# ...and the allowance is now spent, so 15.01 applies again.
checks.eq("...a THIRD Overwatch on the Hexmark is refused - the allowance is spent",
          sc.refusal("Player 2", OVERWATCH, [hexmark], 0),
          "already used this phase (15.01)")

# THE WINDOW: a turn, not a battle round.
tt2 = TurnTracker()
tt2.battle_round, tt2.turn_owner = 2, "Player 1"
d2 = inescapable_death.InescapableDeathDiscount(turn_tracker=tt2)
checks.true("the allowance starts available", d2.available("Player 2"))
d2.consume("Player 2", OVERWATCH, [hexmark])
checks.true("...spent", not d2.available("Player 2"))
tt2.turn_owner = "Player 2"          # the SAME battle round, the other turn
checks.true("...and it returns on the next TURN, inside the same battle round",
            d2.available("Player 2"))
d2.consume("Player 2", OVERWATCH, [hexmark])
tt2.battle_round = 3                 # a new round, same turn owner
checks.true("...and on a new battle round too", d2.available("Player 2"))

# Clause 3: the 2+, and it is NOT latched to the free use.
checks.eq("Snap Shooting by the Hexmark hits on 2+",
          inescapable_death.snap_hit_threshold(hexmark), 2)
checks.eq("...and by anything else, not at all (15.09's flat 6 stands)",
          inescapable_death.snap_hit_threshold(other), None)
# THE LINE A COPY OF PROTECTOR OF THE PATHS FAILS: that Enhancement's own
# clause 3 says "while resolving THAT Stratagem" and is latched to the free
# activation. This one says "each time you target this unit", so a second,
# fully PAID Overwatch still hits on 2+.
checks.eq("...even after the free use is spent - it is not latched",
          inescapable_death.snap_hit_threshold(hexmark), 2)
checks.true("...which is the printed difference from Protector of the Paths",
            "each time" in io.open("game/inescapable_death.py",
                                   encoding="utf-8").read().lower())


# =========================================================================
# 5. Multi-threat Eliminator, and the shape it now shares
# =========================================================================
print("--- 5. Multi-threat Eliminator ---")

mte = multi_threat_eliminator.MultiThreatEliminatorController()
checks.eq("range is the printed 3\", not Kroot Packmates' 6\"",
          mte.range_in, 3.0)
checks.true("it protects any friendly NECRONS unit",
            mte.protects(build(WARRIORS)) and mte.protects(build(IMMORTALS)))
from game.factions import tau_empire as tau  # noqa: E402
checks.true("...a T'au unit is not protected",
            not mte.protects(tk.build(tau.TAU_EMPIRE.datasheets["Strike Team"], "Player 2")))
checks.true("the Hexmark himself is a carrier",
            mte.carries(build(HEXMARK)) and not mte.carries(build(WARRIORS)))

# END TO END through the real trigger: an enemy shoots a nearby friendly, and
# the Hexmark owes a shot back at THAT unit.
state = GameState()
hexmark = place(build(HEXMARK, "Player 2"), 20, 20)
friend = place(build(WARRIORS, "Player 2", n=2), 22, 20)
enemy = place(build(IMMORTALS, "Player 1"), 40, 20)
state.tokens = list(hexmark.models) + list(friend.models) + list(enemy.models)
tt3 = TurnTracker()
tt3.battle_round, tt3.turn_owner = 2, "Player 1"


class _Shooting:
    def __init__(self):
        self.calls = []

    def start_reactive_shooting(self, squad, restrict_to=None, on_finished=None):
        self.calls.append((squad, restrict_to))
        return True


shoot = _Shooting()
mte = multi_threat_eliminator.MultiThreatEliminatorController(
    shooting_controller=shoot, game_state=state, turn_tracker=tt3,
    auto_players=("Player 2",))
checks.true("the Hexmark reacts when a friendly NECRONS unit 2\" away is shot",
            mte.maybe_offer(enemy, friend))
checks.eq("...nothing fires yet - the enemy has not finished", shoot.calls, [])
checks.true("...and it fires once that enemy has finished shooting",
            mte.on_squad_finished_shooting(enemy))
# getattr rather than r.name: with the restriction dropped, `restrict_to` is
# None and a bare attribute read ABORTS the suite instead of making it red -
# the twenty-first instance of that lesson in this repo. A probe has to produce
# a failing CHECK, because an aborted run does not say which assurance broke.
checks.eq("...at THAT enemy unit only",
          [(s.name, getattr(r, "name", None)) for s, r in shoot.calls],
          [(hexmark.name, enemy.name)])

# ...but not for a friendly unit out of range: 3", not 6".
shoot.calls[:] = []
far = place(build(IMMORTALS, "Player 2", n=3), 27, 20)
state.tokens.extend(far.models)
mte2 = multi_threat_eliminator.MultiThreatEliminatorController(
    shooting_controller=shoot, game_state=state, turn_tracker=tt3,
    auto_players=("Player 2",))
checks.true("a friendly unit 6\" away is out of range - Kroot Packmates' number is not this one",
            not mte2.maybe_offer(enemy, far))
checks.true("...and a MELEE attack never triggers it", not mte2.maybe_offer(enemy, friend, melee=True))


# =========================================================================
# 6. Nekrosor Ammentar's four abilities
# =========================================================================
print("--- 6. Nekrosor Ammentar ---")

# --- Protective Disciples: the FIFTH conditional Lone Operative -----------
nek = place(build(NEKROSOR, "Player 2"), 20, 20)
cult = place(build(SKORPEKH, "Player 2", n=2), 22, 20)      # DESTROYER CULT, ~0.4" away
plain = place(build(WARRIORS, "Player 2", n=3), 22, 20)     # NECRONS, not the cult
# A cult unit OUT of the printed 3". Without it the range clause is not
# measured at all - the probe that deletes it reported NO BITE, which is a
# finding about this test rather than an all-clear.
far_cult = place(build(SKORPEKH, "Player 2", n=91), 34, 20)

checks.eq("alone, no Lone Operative",
          status_effects.lone_operative_range(nek, tokens(nek)), None)
checks.true("...and beside a NON-cult NECRONS unit, still none - the narrower keyword",
            status_effects.lone_operative_range(nek, tokens(nek, plain)) is None)
checks.eq("...beside a DESTROYER CULT unit, 12\"",
          status_effects.lone_operative_range(nek, tokens(nek, cult)), 12)
checks.true("...and a DESTROYER CULT unit 12\" away grants nothing - the 3\" is real",
            status_effects.lone_operative_range(nek, tokens(nek, far_cult)) is None)
# Illuminor Szeras's identical sentence would grant on the plain unit; this is
# the half a copy of his module loses.
checks.true("Szeras's version WOULD grant there - so the keyword is the difference",
            nekrosor_ammentar.grants_lone_operative(nek, tokens(nek, plain)) is False)
checks.true("...and it is registered in the shared fold, not read separately",
            any(f.__module__.endswith("nekrosor_ammentar")
                for f, _r in conditional_lone_operative.SOURCES))

# --- Infectious Murder-madness -------------------------------------------
nek = place(build(NEKROSOR, "Player 2"), 20, 20)
near_cult = place(build(SKORPEKH, "Player 2", n=4), 23, 20)   # DESTROYER CULT, 3" away
near_plain = place(build(WARRIORS, "Player 2", n=5), 23, 20)  # NECRONS, 3" away
far_cult = place(build(SKORPEKH, "Player 2", n=6), 40, 20)    # 20" away
tok = tokens(nek, near_cult, near_plain, far_cult)

checks.true("a DESTROYER CULT unit 3\" away is in the aura",
            nekrosor_ammentar.unit_in_murder_madness_aura(near_cult, tok))
checks.true("...so is a plain NECRONS unit",
            nekrosor_ammentar.unit_in_murder_madness_aura(near_plain, tok))
checks.true("...and a unit 20\" away is not",
            not nekrosor_ammentar.unit_in_murder_madness_aura(far_cult, tok))
checks.true("...the bearer's OWN unit is in it too - the text says 'a', not 'another'",
            nekrosor_ammentar.unit_in_murder_madness_aura(nek, tok))

# THE TWO CLAUSES, EACH WITH THE OTHER SWITCHED OFF. They are joined by "or",
# so staging both at once passes with either unimplemented.
cult_model = near_cult.models[0]
plain_model = near_plain.models[0]
checks.true("a DESTROYER CULT model gets it even when the target is NOT closest",
            nekrosor_ammentar.murder_madness_applies(
                near_cult, cult_model, target_is_closest=False, all_tokens=tok))
checks.true("a NON-cult model gets it only against the CLOSEST eligible target",
            nekrosor_ammentar.murder_madness_applies(
                near_plain, plain_model, target_is_closest=True, all_tokens=tok))
checks.true("...and not otherwise",
            not nekrosor_ammentar.murder_madness_applies(
                near_plain, plain_model, target_is_closest=False, all_tokens=tok))
checks.true("...and a unit outside the aura gets nothing either way",
            not nekrosor_ammentar.murder_madness_applies(
                far_cult, far_cult.models[0], target_is_closest=True, all_tokens=tok))

# The grant itself, with both no-downgrade guards.
w = OphydianHyperphaseWeaponsProfile()
granted = nekrosor_ammentar.adjusted_weapon(w, near_cult, cult_model, False, tok)
checks.eq("the grant is [SUSTAINED HITS 1]", granted.sustained_hits, 1)
checks.true("...on a COPY - the shared instance is never mutated",
            granted is not w and w.sustained_hits == 0)
better = EnmiticDisintegratorsProfile()                       # prints SUSTAINED HITS 2
checks.true("...and a weapon that already prints a better X keeps it",
            nekrosor_ammentar.adjusted_weapon(
                better, near_cult, cult_model, False, tok) is better)

# The MONSTER / TITANIC exclusion, each on its own.
monster = build(D["C'tan Shard of the Void Dragon"], "Player 2", n=7)
place(monster, 22, 20)
tok_m = tokens(nek, monster)
checks.true("a MONSTER unit is excluded from the aura",
            not nekrosor_ammentar.unit_in_murder_madness_aura(monster, tok_m))
# TITANIC has no built carrier yet, so it is staged the way the engine reads it
# - off the DATASHEET keyword line, which is what game/titanic.py answers.
titan = build(WARRIORS, "Player 2", n=8)
place(titan, 22, 20)
titan.datasheet = type("_Sheet", (), {"keywords": ("INFANTRY", "TITANIC", "NECRONS")})()
checks.true("...and so is a TITANIC one",
            not nekrosor_ammentar.unit_in_murder_madness_aura(titan, tokens(nek, titan)))

# The per-MODEL keyword question, and the measurement that makes the
# one-representative attack grouping exact.
checks.true("a Skorpekh model carries DESTROYER CULT",
            model_has_datasheet_keyword(near_cult, cult_model, "DESTROYER CULT"))
checks.true("...a Necron Warrior does not",
            not model_has_datasheet_keyword(near_plain, plain_model, "DESTROYER CULT"))
_mixed = []
for _sheet in D.values():
    _lead = NECRONS_POINTS.get(_sheet.name)
    for _target in (getattr(_lead, "leads", ()) or ()) + (getattr(_lead, "supports", ()) or ()):
        _a = "DESTROYER CULT" in _sheet.keywords
        _b = "DESTROYER CULT" in D[_target].keywords
        if _a != _b:
            _mixed.append((_sheet.name, _target))
checks.eq("NO buildable pairing mixes DESTROYER CULT with non-cult in one unit",
          _mixed, [])

# --- Prophet of Destruction ----------------------------------------------
nek = place(build(NEKROSOR, "Player 2"), 20, 20)
mate = place(build(SKORPEKH, "Player 2", n=9), 25, 20)        # cult, 5" away
stranger = place(build(WARRIORS, "Player 2", n=10), 25, 20)   # not cult
outside = place(build(SKORPEKH, "Player 2", n=11), 45, 20)    # cult, 25" away
victim = place(build(IMMORTALS, "Player 1", n=12), 22, 20)
tok_p = tokens(nek, mate, stranger, outside, victim)

cands = nekrosor_ammentar.prophet_candidates(nek, tok_p)
checks.eq("candidates are the OTHER DESTROYER CULT units within 9\"",
          [c.name for c in cands], [mate.name])

state_p = GameState()
state_p.tokens = list(tok_p)
prophet = nekrosor_ammentar.ProphetOfDestructionController(
    game_state=state_p, auto_players=("Player 2",))
checks.true("a kill grants the re-roll", prophet.notify_unit_destroyed(victim, nek))
checks.true("...to the chosen unit", nekrosor_ammentar.prophet_applies(mate))
checks.true("...and to nobody else",
            not nekrosor_ammentar.prophet_applies(stranger)
            and not nekrosor_ammentar.prophet_applies(outside)
            and not nekrosor_ammentar.prophet_applies(nek))
nekrosor_ammentar.prophet_reset_phase([mate])
checks.true("...and it lasts only to the end of the phase",
            not nekrosor_ammentar.prophet_applies(mate))
checks.true("a kill by somebody WITHOUT the ability grants nothing",
            not prophet.notify_unit_destroyed(victim, mate))

# --- Nullstone Field Generator -------------------------------------------
nek = place(build(NEKROSOR, "Player 2"), 20, 20)
close = place(build(WARRIORS, "Player 2", n=13), 23, 20)
distant = place(build(WARRIORS, "Player 2", n=14), 45, 20)
tok_n = tokens(nek, close, distant)
nekrosor_ammentar.refresh_nullstone(tok_n)

checks.true("a friendly NECRONS unit 3\" away is in the aura",
            close.nullstone_field_generator)
checks.true("...and one 25\" away is not", not distant.nullstone_field_generator)

m_close, m_far = close.models[0], distant.models[0]
checks.eq("in the aura: FNP 5+ against a MORTAL wound",
          feel_no_pain.current_feel_no_pain(m_close, mortal=True), "5+")
checks.eq("...and against a PSYCHIC attack",
          feel_no_pain.current_feel_no_pain(m_close, psychic=True), "5+")
# THE LINE THAT SEPARATES "the aura works" FROM "the aura is unconditional".
checks.eq("...and NOTHING against an ordinary wound",
          feel_no_pain.current_feel_no_pain(m_close), "-")
checks.eq("outside it: nothing, even against a mortal wound",
          feel_no_pain.current_feel_no_pain(m_far, mortal=True), "-")

# A BEARER THAT DIED THIS FRAME STOPS PROJECTING. remove_dead_models() runs
# once a frame, so the corpse is still in squad.models when the stamp is taken
# - error class 12, and the one thing about this aura that is NOT a property of
# the printed sentence. Added when Etappe 5's shared FeelNoPainAura probe found
# that only ONE of the extraction's two carriers measured it; a shared base
# whose carriers do not both notice a change is the drift the extraction is
# there to prevent.
for _m in nek.models:
    _m.current_wounds = 0
nekrosor_ammentar.refresh_nullstone(tok_n)
checks.eq("a bearer killed THIS frame stops projecting at once",
          (close.nullstone_field_generator,
           feel_no_pain.current_feel_no_pain(m_close, mortal=True)),
          (False, "-"))


# =========================================================================
# 7. Tunnelling Horrors - the round gate is the new half
# =========================================================================
print("--- 7. Tunnelling Horrors ---")

state_t = GameState()
oph = place(build(OPHYDIAN, "Player 2"), 20, 20)
enemy_t = place(build(IMMORTALS, "Player 1", n=20), 60, 20)
state_t.tokens = list(oph.models) + list(enemy_t.models)
th = tunnelling_horrors.TunnellingHorrorsController(
    game_state=state_t, auto_players=())

checks.true("an unengaged Ophydian unit may tunnel", th.can_use(oph))
checks.true("...and it really leaves the board", th.use(oph))
checks.true("...into Strategic Reserves", oph in state_t.reserves)
checks.true("...owing an ingress move", tunnelling_horrors.applies(oph))

# THE HALF THAT IS NEW: rule 20.03 forbids arriving before battle round 2, and
# the printed parenthesis "(including in your first turn)" overrides it.
tt_t = TurnTracker()
tt_t.battle_round = 1


class _Setup:
    def start_setup(self, *a, **kw):
        pass


ing = ingress.IngressController(_Setup(), state_t, state_t.tokens, turn_tracker=tt_t)
checks.true("it may ingress in battle round 1 - the printed parenthesis",
            ing.can_ingress(oph))
tunnelling_horrors.reset_movement_phase([oph])
checks.true("...and once that Movement phase ends, 20.03 applies again",
            not ing.can_ingress(oph))
checks.true("...the unit simply stays in reserves - 'must' is not a compulsion",
            oph in state_t.reserves)

# An ENGAGED unit cannot use it, which is the printed condition.
state_t2 = GameState()
oph2 = place(build(OPHYDIAN, "Player 2", n=21), 20, 20)
close_enemy = place(build(IMMORTALS, "Player 1", n=22), 21.0, 20)
state_t2.tokens = list(oph2.models) + list(close_enemy.models)
th2 = tunnelling_horrors.TunnellingHorrorsController(game_state=state_t2)
checks.true("an ENGAGED unit may not tunnel", not th2.can_use(oph2))


# =========================================================================
# 8. the Plasmacyte, offered at last
# =========================================================================
print("--- 8. the Plasmacyte offer ---")

# THE FIND: use()/can_use() had no caller anywhere. Pinned at the SOURCE as
# well as end to end, because the behaviour test below would pass against a
# controller nothing constructs.
_main = io.open("main.py", encoding="utf-8").read()
checks.true("main.py hands FightController a Plasmacyte offer",
            "plasmacyte=PlasmacyteController(" in _main)
_fight_src = io.open("game/fight.py", encoding="utf-8").read()
checks.true("...and _start_fighting() calls it",
            "self.plasmacyte.offer(squad)" in _fight_src)

# Driven through the REAL controller: the offer happens when the unit is
# SELECTED TO FIGHT, which is the step that was never reaching the ability.
from game.fight import FightController  # noqa: E402
from game.dice import DiceManager  # noqa: E402

atk = place(build(OPHYDIAN, "Player 2", composition_index=1,
                  gear={"Ophydian Destroyer": ["Plasmacyte"]}), 20, 20)
tgt = place(build(IMMORTALS, "Player 1", n=31), 20.9, 20)
all_tok = tokens(atk, tgt)
tt_f = TurnTracker()
tt_f.phase_index = 4
tt_f.turn_owner = "Player 2"
fc = FightController(dice_manager=DiceManager(), turn_tracker=tt_f, all_tokens=all_tok,
                     plasmacyte=plasmacyte.PlasmacyteController(auto_players=("Player 2",)))
checks.eq("before the activation, no grant", plasmacyte.remaining_uses(atk), 1)
fc.fighting_squad = None
fc._start_fighting(atk)
checks.true("selecting the unit to fight OFFERS the Plasmacyte",
            getattr(atk, "plasmacyte_active", False))
checks.eq("...and spends one", plasmacyte.remaining_uses(atk), 0)
w = OphydianHyperphaseWeaponsProfile()
checks.true("...so its melee weapons have [DEVASTATING WOUNDS]",
            plasmacyte.adjusted_weapon(w, atk).devastating_wounds)
checks.true("...on a copy", not w.devastating_wounds)
# A human is ASKED rather than answered for - it is a per-BATTLE ledger, so
# saving one is a real decision.
dm = DecisionManager()
atk2 = place(build(OPHYDIAN, "Player 1", n=32, composition_index=1,
                   gear={"Ophydian Destroyer": ["Plasmacyte"]}), 20, 20)
plasmacyte.PlasmacyteController(decision_manager=dm, auto_players=("Player 2",)).offer(atk2)
checks.true("a human owner is asked", dm.is_pending)
checks.true("...and nothing is spent until the answer",
            plasmacyte.remaining_uses(atk2) == 1)


# =========================================================================
# 9. wiring, the AI negative space, and sprites
# =========================================================================
print("--- 9. wiring, AI, sprites ---")

for _name, _needle in (
        ("Multi-threat Eliminator is in the shooting target_reactions tuple",
         "multi_threat_eliminator_controller,"),
        ("...and fires once the attacker has finished",
         "multi_threat_eliminator_controller.on_squad_finished_shooting)"),
        ("...and its owed reaction is cleared at end of turn",
         "multi_threat_eliminator_controller.reset_turn()"),
        ("Tunnelling Horrors is offered at end of turn",
         "tunnelling_horrors_controller.offer_at_end_of_turn("),
        ("...and its obligation is cleared at end of the Movement phase",
         "tunnelling_horrors.reset_movement_phase("),
        ("Inescapable Death is a cost discount",
         "stratagem_controller.cost_discounts.append(inescapable_death_discount)"),
        ("...and a repeat permission - the SAME object",
         "stratagem_controller.repeat_permissions.append(inescapable_death_discount)"),
        ("Prophet of Destruction is fed by the death sweep",
         "prophet_of_destruction_controller.notify_unit_destroyed("),
        ("...and expires at the phase boundary",
         "nekrosor_ammentar.prophet_reset_phase("),
        ("the Nullstone aura is refreshed once per frame",
         "nekrosor_ammentar.refresh_nullstone(state.tokens)")):
    checks.true(_name, _needle in _main)

# The 2+ override reaches Snap Shooting's own threshold, not a modifier list.
_shoot_src = io.open("game/shooting.py", encoding="utf-8").read()
checks.true("the 2+ is an OVERRIDE inside _base_hit_threshold()",
            "inescapable_death.snap_hit_threshold(self.active_squad)" in _shoot_src)

# KEIN KI-PFAD (standing instruction for this backfill): auto_players in every
# new controller, and NO agent_driver verdicts - none of these eight choices is
# army-wide.
_driver = io.open("ai/agent_driver.py", encoding="utf-8").read()
for _n in ("inescapable_death", "multi_threat_eliminator", "tunnelling_horrors",
           "nekrosor_ammentar", "prophet_of_destruction", "plasmacyte"):
    checks.true("no agent_driver path for %s" % _n, _n not in _driver)

# ...and every new controller really HAS the gate, measured on the object
# rather than grepped for the word: MultiThreatEliminatorController inherits
# it from game/reactive_bodyguard_shooting.py and its own file never mentions
# it, so a source sweep answers False for a controller that is gated perfectly.
for _label, _ctrl in (
        ("Multi-threat Eliminator",
         multi_threat_eliminator.MultiThreatEliminatorController(auto_players=("Player 2",))),
        ("Tunnelling Horrors",
         tunnelling_horrors.TunnellingHorrorsController(auto_players=("Player 2",))),
        ("Prophet of Destruction",
         nekrosor_ammentar.ProphetOfDestructionController(auto_players=("Player 2",))),
        ("the Plasmacyte", plasmacyte.PlasmacyteController(auto_players=("Player 2",)))):
    checks.true("%s gates on auto_players" % _label,
                "Player 2" in _ctrl.auto_players and "Player 1" not in _ctrl.auto_players)

# THE GATE IS A WEICHE, not a shortcut: the human is ASKED where the AI is
# answered for. Measured on the two that open a prompt in an ordinary turn.
_dm = DecisionManager()
_st = GameState()
_hx = place(build(HEXMARK, "Player 1", n=50), 20, 20)
_fr = place(build(WARRIORS, "Player 1", n=51), 22, 20)
_en = place(build(IMMORTALS, "Player 2", n=52), 40, 20)
_st.tokens = list(_hx.models) + list(_fr.models) + list(_en.models)
_tt = TurnTracker()
_tt.battle_round, _tt.turn_owner = 2, "Player 2"
_mte_h = multi_threat_eliminator.MultiThreatEliminatorController(
    shooting_controller=_Shooting(), decision_manager=_dm, game_state=_st,
    turn_tracker=_tt, auto_players=("Player 2",))
checks.true("a HUMAN Hexmark owner is asked, not answered for",
            _mte_h.maybe_offer(_en, _fr) and _dm.is_pending)

# DORMANT BY ROSTER, pinned so fielding one is a visible change.
_roster = io.open("armies/necrons.json", encoding="utf-8").read()
for _n in ("Hexmark Destroyer", "Ophydian Destroyers", "Nekrosor Ammentar"):
    checks.true("%s is dormant by roster" % _n, _n not in _roster)

WITHOUT_ART = {"Nekrosor Ammentar"}
for sheet, _p in SHEETS:
    art = sprites.sprite_for(build(sheet, n=40).models[0])
    if sheet.name in WITHOUT_ART:
        checks.eq("%s has no art yet - pinned so adding one is visible" % sheet.name,
                  art, None)
    else:
        checks.true("%s draws its own art" % sheet.name, art is not None)

# SPRITE SHADOWING is measured, not hoped: _key_for_name() returns the FIRST
# key that is a substring of the squad name, so a new key can be swallowed or
# can swallow an older one.
_keys = list(sprites.SQUAD_SPRITE_KEYS)
for _new in ("Hexmark Destroyer", "Ophydian Destroyers"):
    _swallowers = [k for k in _keys if k != _new and k in _new]
    checks.eq("no existing key swallows %r" % _new, _swallowers, [])
    _victims = [k for k in _keys if k != _new and _new in k]
    checks.eq("...and it swallows none" , _victims, [])

checks.finish()
