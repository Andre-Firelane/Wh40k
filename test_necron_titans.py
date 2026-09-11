"""Stage 9 of the Necron datasheet backfill: the Monolith and The Silent King.

The last stage, and the two biggest single sheets in the faction. The Monolith
is the FIRST TITANIC and TOWERING model this engine has ever carried; The
Silent King is the first unit whose one datasheet prints TWO profiles with
different wounds, different bases and different keyword bars.

WHAT EACH SECTION IS FOR

  1. statlines, against the corpus - including the Monolith's base, which is a
     NEW table-size decision with no precedent either way, and Szarekh's and
     the Menhir's, which are plain transcriptions.
  2. weapons and the collision sweep. Eight names are new; the ninth is the
     Menhir's "Armoured bulk", the FORK stage 8 predicted BY NAME - pinned
     against the shared class rather than against literals.
  3. points (two tiers for the Monolith, one for a three-model unit), the
     composition, and the LEADER table: The Silent King prints no Leader
     section at all, which is measured through the real can_attach().
  4. Voice of the Triarch - the choice, its once-per-round window, and that it
     survives a save.
  5. the three Triarch auras through the seams that actually read them, at the
     6" boundary, and the MONSTER exclusion that the fourth aura does not
     print.
  6. The Silent King (+1 Ld) - the fourth aura, always on, no MONSTER
     exclusion, and the sign of an "improvement" on an N+ threshold.
  7. the two "Damaged:" tiers. The Monolith's OC half through the real
     effective_oc(); The Silent King's through both attack steps, including
     the half whose subject is the UNIT and not the model.
  8. Eternity Gate: the passenger rules, the withdrawal, the 6" placement, the
     "unengaged" band, the deployment-zone waiver and the charge lock.
  9. Triarchal Menhirs (linked destruction), and the extraction with its OTHER
     carrier still answering exactly as before.
 10. wiring, the AI negative space, sprites, dormancy.
"""

import ast
import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((100, 100))

import testkit as tk
from testkit import Checks, script
from game.factions import build_squad

from game import (attached_units, charge_reroll, coldstar, damaged_attacks,
                  eternity_gate, leadership, objective_control,
                  relentless_combatants, silent_king_leadership, sprites,
                  triarch_auras, triarchal_menhirs)
from game.decision import DecisionManager
from game.dice import DiceManager
from game.dice_notation import describe
from game.factions import necrons as nec
from game.factions.necrons_points import NECRONS_POINTS
from game.game_state import GameState
from game.weapons import MELEE
from game.units import (MonolithProfile, SzarekhProfile,
                        TriarchalMenhirProfile, UnitProfile)
from game.weapons import (AnnihilatorBeamProfile, ArmouredBulkProfile,
                          DeathRayProfile, GaussFluxArcProfile,
                          MenhirArmouredBulkProfile, ParticleWhipProfile,
                          PortalOfExileProfile, SceptreOfEternalGloryProfile,
                          StaffOfStarsProfile,
                          WeaponsOfTheFinalTriarchProfile)

c = Checks("Necron TITANS")

D = nec.NECRONS.datasheets
MONOLITH = D["Monolith"]
SILENT_KING = D["The Silent King"]
WARRIORS = D["Necron Warriors"]
IMMORTALS = D["Immortals"]
LYCHGUARD = D["Lychguard"]
OVERLORD = D["Overlord"]
PRAETORIANS = D["Triarch Praetorians"]
VOID_DRAGON = D["C'tan Shard of the Void Dragon"]

NEW = [MONOLITH, SILENT_KING]


def build(sheet, owner="Player 2", n=1, **kw):
    """Named the way main.py names squads - see the sprite trap in
    game/sprites.py's _key_for_name()."""
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


def place(squad, x, y, spacing=1.4):
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + i * spacing, y
    return squad


def corpus(name):
    return io.open(os.path.join("rules", "necrons", name + ".md"),
                   encoding="utf-8").read()


def between(text, first, second):
    """The slice between two anchors, or "" if either is gone.

    find() and not index(): a pin that CRASHES when its anchor moves takes the
    whole suite down instead of going red, and then says nothing about which
    assurance broke."""
    a = text.find(first)
    if a < 0:
        return ""
    b = text.find(second, a + len(first))
    return text[a:b] if b > a else ""


def living(squad):
    return sum(1 for m in squad.models if not m.is_dead())


def szarekh_of(squad):
    """type(...) is, not isinstance: stage 8 paid for that lesson when an
    identity pin passed against a SUBCLASS. Neither of these two profiles has
    one today, and the line below pins that rather than trusting it."""
    return [m for m in squad.models if type(m.profile) is SzarekhProfile][0]


def menhirs_of(squad):
    return [m for m in squad.models if type(m.profile) is TriarchalMenhirProfile]


# --- 1. statlines ------------------------------------------------------------
print("--- 1. statlines ---")

STATS = {
    # name: (M, T, Sv, W, Ld, OC, InSv, base_radius_in)
    # "-" is this engine's own sentinel for "no invulnerable save", not None.
    "Monolith": (8, 13, "2+", 22, "7+", 8, "-", 2.5),
    "Szarekh": (8, 10, "2+", 16, "6+", 6, "4+", 1.969),
    "Triarchal Menhir": (8, 10, "2+", 5, "6+", 1, "4+", 0.984),
}
PROFILES = {"Monolith": MonolithProfile, "Szarekh": SzarekhProfile,
            "Triarchal Menhir": TriarchalMenhirProfile}
for _name, _want in STATS.items():
    p = PROFILES[_name]
    c.eq("%s statline" % _name,
         (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership,
          p.oc, p.invulnerable_save, round(p.base_radius_in, 3)),
         _want)
    c.true("...and %s derives straight from UnitProfile" % _name,
           p.__bases__ == (UnitProfile,))

# THE MONOLITH'S BASE IS A DECISION, and the two values it is NOT are pinned
# beside it so the reason survives. 160 mm is r=3.150"; the Defiler prints the
# SAME 160 mm and plays at 2.1", which is the value every large hull in this
# repo shares. Neither was taken - user: "2.5\", dazwischen".
c.true("the Monolith's printed base really is 160 mm",
       "160mm" in corpus("Monolith"))
c.eq("...and it plays at 2.5\", which is NEITHER the print nor the Defiler's",
     MonolithProfile.base_radius_in, 2.5)
c.true("...bigger than every other hull in the engine",
       MonolithProfile.base_radius_in > max(
           v.base_radius_in for k, v in vars(__import__("game.units", fromlist=["x"])).items()
           if isinstance(v, type) and issubclass(v, UnitProfile)
           and v is not MonolithProfile))
c.true("...and smaller than the printed 3.150\"",
       MonolithProfile.base_radius_in < 3.150)

# Szarekh and the Menhir are plain TRANSCRIPTIONS - 100 mm and 50 mm.
for _n, _mm in (("Szarekh", 100.0), ("Triarchal Menhir", 50.0)):
    c.true("%s's base is the printed %.0f mm, transcribed" % (_n, _mm),
           abs(PROFILES[_n].base_radius_in - _mm / 2.0 / 25.4) < 0.002)

c.eq("the Monolith's Deadly Demise is D6", describe(MonolithProfile.deadly_demise_notation), "D6")
c.eq("Szarekh's is D6+3", describe(SzarekhProfile.deadly_demise_notation), "D6+3")
c.eq("...and the Menhir has NONE - the line says (Szarekh model only)",
     TriarchalMenhirProfile.deadly_demise_notation, None)
c.true("...which the corpus prints that way",
       "Deadly Demise D6+3 (Szarekh model only)" in corpus("The Silent King"))

# The keyword bar is SPLIT on this datasheet, and that is the whole reason the
# Menhirs are not CHARACTERs: rule 05.03's allocation protection and
# [PRECISION] would otherwise reach two bodyguard obelisks.
c.true("Szarekh is a CHARACTER", SzarekhProfile.character)
c.true("...and the Menhir is NOT", not TriarchalMenhirProfile.character)
c.true("...but BOTH are EPIC HERO, which is the ALL MODELS half of the bar",
       SzarekhProfile.epic_hero and TriarchalMenhirProfile.epic_hero)
c.true("...and the corpus prints the split",
       "SZAREKH MODEL: CHARACTER" in corpus("The Silent King").replace("\n", ""))

c.true("the Monolith carries TITANIC on its DATASHEET, not on a profile flag",
       "TITANIC" in MONOLITH.keywords
       and not hasattr(MonolithProfile, "titanic"))
c.true("...and TOWERING with it", "TOWERING" in MONOLITH.keywords)


# --- 2. weapons --------------------------------------------------------------
print("--- 2. weapons ---")

WEAPONS = {
    # class: (name, A, BS/WS, S, AP, D, keywords)
    DeathRayProfile: ("Death Ray", "1", 12, -4, "D6+1", ["SUSTAINED HITS D3"]),
    GaussFluxArcProfile: ("Gauss Flux Arc", "3", 6, -1, "1", ["LETHAL HITS", "RAPID FIRE 3"]),
    ParticleWhipProfile: ("Particle Whip", "3D6", 8, -1, "2", ["BLAST", "DEVASTATING WOUNDS"]),
    PortalOfExileProfile: ("Portal of Exile", "6", 8, -2, "3", []),
    AnnihilatorBeamProfile: ("Annihilator Beam", "1", 14, -4, "6", []),
    SceptreOfEternalGloryProfile: ("Sceptre of Eternal Glory", "2", 10, -3, "3", ["DEVASTATING WOUNDS"]),
    StaffOfStarsProfile: ("Staff of Stars", "12", 6, -1, "1", ["INDIRECT FIRE"]),
    WeaponsOfTheFinalTriarchProfile: ("Weapons of the Final Triarch", "12", 8, -3, "2", ["LETHAL HITS"]),
    MenhirArmouredBulkProfile: ("Armoured Bulk", "1", 4, 0, "1", []),
}
from game import weapons as weapons_module  # noqa: E402
for _cls, (_name, _a, _s, _ap, _d, _kw) in WEAPONS.items():
    c.eq("%s row" % _name,
         (_cls.name,
          describe(_cls.attacks_notation) if _cls.attacks_notation else str(_cls.attacks),
          _cls.strength, _cls.ap,
          describe(_cls.damage_notation) if _cls.damage_notation else str(_cls.damage),
          list(weapons_module.printed_keywords(_cls))),
         (_name, _a, _s, _ap, _d, _kw))
# WHICH SIDE each weapon fights on was unmeasured until the A/B probe asked:
# turning the Staff of Stars into a MELEE weapon left every keyword and every
# number intact, so the whole table passed against a gun that cannot shoot.
RANGED_ROWS = {"Death Ray", "Gauss Flux Arc", "Particle Whip",
               "Annihilator Beam", "Sceptre of Eternal Glory", "Staff of Stars"}
for _cls, (_name, _a, _s, _ap, _d, _kw) in WEAPONS.items():
    c.eq("%s is on the printed side of the sheet" % _name,
         _cls.weapon_type, "ranged" if _name in RANGED_ROWS else MELEE)

# NO PER-WEAPON SKILL OVERRIDE IN THIS STAGE, pinned as a SET. The Catacomb
# Command Barge one stage earlier needed two, because its own rows contradicted
# each other; none of these three profiles does.
c.eq("no stage-9 weapon carries a skill override",
     sorted(w.name for w in WEAPONS
            if w.ballistic_skill is not None or w.weapon_skill is not None),
     [])

# THE FORK stage 8 predicted BY NAME. Pinned against the SHARED class rather
# than against literals: "identical except Attacks and Strength" is the real
# assurance, and two independent copies with the same numbers would satisfy a
# literal-by-literal test while quietly ceasing to track the shared row.
c.eq("the Menhir's bulk shares the printed NAME with the skimmers'",
     MenhirArmouredBulkProfile.name, ArmouredBulkProfile.name)
c.true("...and subclasses it rather than copying it",
       issubclass(MenhirArmouredBulkProfile, ArmouredBulkProfile))
c.eq("...differing in exactly Attacks and Strength",
     sorted(f for f in ("attacks", "strength", "weapon_skill", "ap", "damage", "range_in")
            if getattr(MenhirArmouredBulkProfile, f) != getattr(ArmouredBulkProfile, f)),
     ["attacks", "strength"])
c.eq("...and the shared row is still A3 S6 for the three skimmers",
     (ArmouredBulkProfile.attacks, ArmouredBulkProfile.strength), (3, 6))
c.true("stage 8's block predicted this fork by name",
       "stage 9 has to make it" in io.open(os.path.join("game", "weapons.py"),
                                           encoding="utf-8").read())

# EIGHT of the nine names appear nowhere else in the corpus - the sweep that
# decided there was nothing to share. Run over the corpus, with a liveness line
# so a sweep that stopped finding rows cannot read as a pass.
_rows, _seen = 0, {}
for _folder in sorted(os.listdir("rules")):
    _d = os.path.join("rules", _folder)
    if not os.path.isdir(_d) or _folder == ".cache":
        continue
    for _fn in sorted(os.listdir(_d)):
        if not _fn.endswith(".md"):
            continue
        for _line in io.open(os.path.join(_d, _fn), encoding="utf-8").read().splitlines():
            if not _line.startswith("| "):
                continue
            _rows += 1
            _cell = _line.split("|")[1].strip().lstrip("*").strip().split(" - ")[0].strip()
            _seen.setdefault(_cell.lower(), set()).add(_fn[:-3])
c.true("the corpus sweep really looked at the weapon tables", _rows > 2000)
for _cls in WEAPONS:
    _hits = _seen.get(_cls.name.lower(), set())
    if _cls is MenhirArmouredBulkProfile:
        c.true("Armoured bulk is printed by SIX sheets, which is why it forks",
               len(_hits) == 6)
    else:
        c.eq("%s is printed by exactly one sheet" % _cls.name, len(_hits), 1)


# --- 3. points, composition and the LEADER table -----------------------------
print("--- 3. points and composition ---")

c.eq("the Monolith's first unit costs 420",
     build(MONOLITH, n=1).points, 420)
c.eq("...and a second one 440",
     build_squad(MONOLITH, "Player 2", name="2 Monolith 2", unit_index=2).points, 440)
c.true("...both tiers printed", "420" in corpus("Monolith") and "440" in corpus("Monolith"))

_sk = build(SILENT_KING)
c.eq("The Silent King is 3 models for 420", (len(_sk.models), _sk.points), (3, 420))
c.eq("...one Szarekh", sum(1 for m in _sk.models if type(m.profile) is SzarekhProfile), 1)
c.eq("...and two Triarchal Menhirs", len(menhirs_of(_sk)), 2)
c.eq("Szarekh's loadout", [w.name for w in szarekh_of(_sk).weapons],
     ["Sceptre of Eternal Glory", "Staff of Stars", "Weapons of the Final Triarch"])
c.eq("a Menhir's loadout", [w.name for w in menhirs_of(_sk)[0].weapons],
     ["Annihilator Beam", "Armoured Bulk"])

_mono = build(MONOLITH)
c.eq("the Monolith fields FOUR gauss flux arcs",
     sum(1 for w in _mono.models[0].weapons if w.name == "Gauss Flux Arc"), 4)
_swapped = build_squad(MONOLITH, "Player 2", name="2 Monolith 3",
                       choices={"Monolith": {nec.MONOLITH_ARCS_TO_DEATH_RAYS: 1}})
c.eq("...and the option trades all FOUR for four death rays",
     (sum(1 for w in _swapped.models[0].weapons if w.name == "Gauss Flux Arc"),
      sum(1 for w in _swapped.models[0].weapons if w.name == "Death Ray")),
     (0, 4))
c.true("...which is what the corpus prints",
       "4 gauss flux arcs can be replaced with 4 death rays" in corpus("Monolith"))
c.eq("The Silent King prints NO wargear options at all",
     list(SILENT_KING.wargear_options), [])

# NEITHER leads NOR is led - measured through the REAL can_attach(), not
# inferred from an absent points-table entry.
for _sheet in NEW:
    c.eq("%s has no leads entry" % _sheet.name,
         NECRONS_POINTS[_sheet.name].leads, ())
    c.eq("...and no supports entry", NECRONS_POINTS[_sheet.name].supports, ())
for _body in (WARRIORS, IMMORTALS, LYCHGUARD):
    c.true("The Silent King cannot lead %s" % _body.name,
           attached_units.can_attach(build(SILENT_KING), build(_body)) != [])
    c.true("...nor can the Monolith",
           attached_units.can_attach(build(MONOLITH), build(_body)) != [])
c.true("...and the Overlord cannot lead THEM either",
       attached_units.can_attach(build(OVERLORD), build(SILENT_KING)) != [])
c.true("The Silent King really prints no Leader section",
       "## Leader" not in corpus("The Silent King"))


# --- 4. Voice of the Triarch -------------------------------------------------
print("--- 4. Voice of the Triarch ---")

c.eq("three Triarch abilities, in printed order",
     [k for k, _n in triarch_auras.TRIARCH_ABILITIES],
     [triarch_auras.PHAERON_OF_THE_STARS,
      triarch_auras.PHAERON_OF_THE_BLADES,
      triarch_auras.RELENTLESS_MARCH])
for _key, _name in triarch_auras.TRIARCH_ABILITIES:
    c.true("...and %s is printed under that name" % _name,
           _name in corpus("The Silent King"))


def voice_scene(auto=()):
    state = GameState()
    king = place(build(SILENT_KING), 20.0, 20.0)
    for m in king.models:
        state.add_token(m)
    dm = DecisionManager()
    ctrl = triarch_auras.VoiceOfTheTriarchController(
        decision_manager=dm, game_state=state, auto_players=auto)
    return state, king, dm, ctrl


_st, _king, _dm, _ctrl = voice_scene()
c.true("a human is asked at the start of the battle round",
       _ctrl.sync_battle_round(2))
c.eq("...with all three on offer", len(_dm.options), 3)
c.true("...and nothing is selected until an option is taken",
       triarch_auras.selected_ability(_king) is None)
_dm.choose(1)   # Phaeron of the Blades
c.eq("choosing stamps the squad",
     triarch_auras.selected_ability(_king), triarch_auras.PHAERON_OF_THE_BLADES)
c.true("...and the SAME round does not ask again",
       not _ctrl.sync_battle_round(2))
c.true("...but the next one does", _ctrl.sync_battle_round(3))

_st2, _king2, _dm2, _ctrl2 = voice_scene(auto=("Player 2",))
c.true("the AI answers for free - no prompt", not _ctrl2.sync_battle_round(2))
c.eq("...and takes Phaeron of the Stars",
     triarch_auras.selected_ability(_king2), triarch_auras.PHAERON_OF_THE_STARS)

# IT SURVIVES A SAVE. A choice with a battle-round lifetime, so losing it to an
# F9 would silently change which aura an army is under.
from game import activation_state  # noqa: E402
c.true("triarch_ability is in the SAVED flags",
       "triarch_ability" in activation_state.SQUAD_FLAGS)
c.true("...and the derived set is NOT",
       "triarch_auras_active" in activation_state.SQUAD_FLAGS_EXCLUDED)
c.true("...and a plain Squad really has both fields",
       hasattr(build(WARRIORS), "triarch_ability")
       and hasattr(build(WARRIORS), "triarch_auras_active"))


# --- 5. the three Triarch auras ----------------------------------------------
print("--- 5. the three auras ---")


def aura_scene(key, gap=3.0, body=WARRIORS, ci=0):
    state = GameState()
    king = place(build(SILENT_KING), 20.0, 20.0)
    king.triarch_ability = key
    unit = place(build(body, n=4, composition_index=ci), 20.0, 20.0 + gap, spacing=0.9)
    for s in (king, unit):
        for m in s.models:
            state.add_token(m)
    triarch_auras.refresh_active_auras(state.tokens)
    return state, king, unit


# THE 6" BOUNDARY IS WALKED, not pinned at one distance.
_near = aura_scene(triarch_auras.RELENTLESS_MARCH, gap=3.0)[2]
_far = aura_scene(triarch_auras.RELENTLESS_MARCH, gap=40.0)[2]
c.true("a unit within 6\" is under the selected aura",
       triarch_auras.is_active(_near, triarch_auras.RELENTLESS_MARCH))
c.true("...and one far away is not",
       not triarch_auras.is_active(_far, triarch_auras.RELENTLESS_MARCH))
c.true("...and only the SELECTED one is live",
       not triarch_auras.is_active(_near, triarch_auras.PHAERON_OF_THE_STARS))

# RELENTLESS MARCH reaches the movement fold, which is the seam with no board.
c.eq("Relentless March adds 2\" to the Move characteristic",
     coldstar.effective_movement_in(_near.models[0])
     - coldstar.effective_movement_in(_far.models[0]),
     2.0)

# PHAERON OF THE BLADES' strength half, through the real adjuster helper.
_blades = aura_scene(triarch_auras.PHAERON_OF_THE_BLADES, gap=3.0)[2]
_nob = aura_scene(triarch_auras.PHAERON_OF_THE_BLADES, gap=40.0)[2]
_melee = [w for w in _blades.models[0].weapons if w.weapon_type == MELEE][0]
c.eq("Phaeron of the Blades adds 1 to melee Strength",
     triarch_auras.blades_adjusted_weapon(_melee, _blades).strength,
     _melee.strength + 1)
c.eq("...and nothing outside 6\"",
     triarch_auras.blades_adjusted_weapon(_melee, _nob).strength, _melee.strength)
c.true("...and it does NOT mutate the model's own instance",
       _melee.strength == type(_melee).strength)
# THROUGH THE REAL ADJUSTER CHAIN, not just the helper. Calling
# blades_adjusted_weapon() directly proves the arithmetic and says nothing
# about whether fight.py ever asks - the probe that removed the call site
# reported NO BITE until this ran.
from game.fight import FightController  # noqa: E402
_fc = FightController(all_tokens=[], game_log=None)
_fc.fighting_squad = _blades
_pairs = [(_blades.models[0], _melee)]
c.eq("fight.py's own adjuster chain applies the +1 S",
     _fc._adjusted_weapon(_pairs).strength, _melee.strength + 1)
_fc.fighting_squad = _nob
c.eq("...and leaves a unit outside 6\" alone",
     _fc._adjusted_weapon([(_nob.models[0], _melee)]).strength, _melee.strength)
c.true("the SHOOTING side never reads it - the text says melee attack",
       "blades_adjusted_weapon" not in io.open(os.path.join("game", "shooting.py"),
                                               encoding="utf-8").read())

# THE MONSTER EXCLUSION IS REAL ON THIS ARMY: a C'tan is a NECRONS MONSTER.
_state_m, _king_m, _ = aura_scene(triarch_auras.RELENTLESS_MARCH, gap=3.0)
_ctan = place(build(VOID_DRAGON), 20.0, 22.0)
for m in _ctan.models:
    _state_m.add_token(m)
triarch_auras.refresh_active_auras(_state_m.tokens)
c.true("staging: the C'tan really is a MONSTER and really is in range",
       triarch_auras.is_monster_unit(_ctan))
c.true("a NECRONS MONSTER unit gets NONE of the three",
       not triarch_auras.is_active(_ctan, triarch_auras.RELENTLESS_MARCH))

# THE SILENT KING'S OWN UNIT IS COVERED BY ITS OWN AURA - "a", not "another".
_state_s, _king_s, _ = aura_scene(triarch_auras.RELENTLESS_MARCH, gap=3.0)
c.true("the bearer's own unit is under its own aura",
       triarch_auras.is_active(_king_s, triarch_auras.RELENTLESS_MARCH))

# AN ENEMY NECRONS UNIT IS NOT - "a FRIENDLY NECRONS unit".
_state_e = GameState()
_king_e = place(build(SILENT_KING), 20.0, 20.0)
_king_e.triarch_ability = triarch_auras.RELENTLESS_MARCH
_foe = place(build(WARRIORS, owner="Player 1", n=9), 20.0, 22.0, spacing=0.9)
for s in (_king_e, _foe):
    for m in s.models:
        _state_e.add_token(m)
triarch_auras.refresh_active_auras(_state_e.tokens)
c.true("an ENEMY Necrons unit in range gets nothing",
       not triarch_auras.is_active(_foe, triarch_auras.RELENTLESS_MARCH))

# MEASURED FROM THE SZAREKH MODEL, not from the unit. A Menhir dragged far out
# of the way must not carry the aura with it.
_state_z, _king_z, _unit_z = aura_scene(triarch_auras.RELENTLESS_MARCH, gap=40.0)
menhirs_of(_king_z)[0].x_in, menhirs_of(_king_z)[0].y_in = _unit_z.models[0].x_in, _unit_z.models[0].y_in
triarch_auras.refresh_active_auras(_state_z.tokens)
c.true("a MENHIR standing beside a unit does not project the aura",
       not triarch_auras.is_active(_unit_z, triarch_auras.RELENTLESS_MARCH))


# --- 6. The Silent King (+1 Ld) ----------------------------------------------
print("--- 6. the Leadership aura ---")

_state_l = GameState()
_king_l = place(build(SILENT_KING), 20.0, 20.0)
_near_l = place(build(WARRIORS, n=6), 20.0, 23.0, spacing=0.9)
_far_l = place(build(WARRIORS, n=7), 20.0, 60.0, spacing=0.9)
for s in (_king_l, _near_l, _far_l):
    for m in s.models:
        _state_l.add_token(m)

_base = leadership.leadership_threshold(_far_l, _state_l.tokens)
_boosted = leadership.leadership_threshold(_near_l, _state_l.tokens)
c.eq("an improvement to Ld SUBTRACTS from the N+ threshold", _boosted, _base - 1)
c.true("...and the aura says so", silent_king_leadership.applies(_near_l, _state_l.tokens))
c.true("...while the far unit is untouched",
       not silent_king_leadership.applies(_far_l, _state_l.tokens))

# THE FOURTH AURA PRINTS NO MONSTER EXCLUSION, and that is one printed word.
_ctan_l = place(build(VOID_DRAGON), 20.0, 22.0)
for m in _ctan_l.models:
    _state_l.add_token(m)
triarch_auras.refresh_active_auras(_state_l.tokens)
c.true("a C'tan DOES get the Leadership aura - it prints no MONSTER exclusion",
       silent_king_leadership.applies(_ctan_l, _state_l.tokens))
c.true("...while the three Triarch auras still exclude it",
       not triarch_auras.is_active(_ctan_l, triarch_auras.RELENTLESS_MARCH))
_sk_text = corpus("The Silent King")
c.true("the corpus prints the exclusion on the three and not on the fourth",
       _sk_text.count("excluding MONSTER units") == 3)

# IT IS NOT ONE OF THE THREE SWAPPABLE ABILITIES, so it is always on.
c.true("the Leadership aura is not a Voice of the Triarch option",
       "The Silent King" not in [n for _k, n in triarch_auras.TRIARCH_ABILITIES])
c.true("...and needs no selection at all",
       triarch_auras.selected_ability(_king_l) is None
       and silent_king_leadership.applies(_near_l, _state_l.tokens))


# --- 7. the two Damaged tiers ------------------------------------------------
print("--- 7. Damaged ---")

# THE MONOLITH: -1 Hit (the generic field) and -4 OC (the new one).
_state_d = GameState()
_mono_d = place(build(MONOLITH), 20.0, 20.0)
for m in _mono_d.models:
    _state_d.add_token(m)
_mm = _mono_d.models[0]
c.eq("a healthy Monolith has OC 8", objective_control.effective_oc(_mm, _state_d.tokens), 8)
_mm.current_wounds = 7
c.eq("...and OC 4 at 7 wounds remaining",
     objective_control.effective_oc(_mm, _state_d.tokens), 4)
_mm.current_wounds = 8
c.eq("...but 8 again at 8 wounds - the boundary is walked",
     objective_control.effective_oc(_mm, _state_d.tokens), 8)
c.eq("the OC penalty is the printed 4", MonolithProfile.damaged_oc_penalty, 4)
c.eq("...and the threshold the printed 7", MonolithProfile.damaged_threshold, 7)
c.true("...both printed on the sheet",
       "1-7 Wounds Remaining" in corpus("Monolith")
       and "subtract 4 from its Objective Control" in corpus("Monolith"))

# THE SILENT KING: halving is "that MODEL's weapons", the Hit penalty is "this
# UNIT" - two different subjects, and the Menhir is the case that tells them
# apart.
_sk_d = build(SILENT_KING)
_sz = szarekh_of(_sk_d)
_mh = menhirs_of(_sk_d)[0]
c.true("a healthy Szarekh halves nothing", not damaged_attacks.halves_attacks_for(_sz))
_sz.current_wounds = 6
c.true("...and a damaged one does", damaged_attacks.halves_attacks_for(_sz))
_final = [w for w in _sz.weapons if w.name == "Weapons of the Final Triarch"][0]
c.eq("A12 halves to 6", damaged_attacks.attacks_for(_sz, _final), 6)
c.true("...and the MENHIR keeps its own Attacks",
       damaged_attacks.attacks_for(_mh, _mh.weapons[0]) == _mh.weapons[0].attacks)
c.true("...but DOES take the unit-wide Hit penalty",
       damaged_attacks.covers_model(_mh))
# THROUGH THE REAL _damaged_modifier(), which is what both attack steps
# actually read. covers_model() alone proves the predicate and nothing about
# whether the hit step asks it - the probe said so.
from game.shooting import _damaged_modifier  # noqa: E402
c.eq("the hit step gives the MENHIR a -1 from Szarekh's wounds",
     [m.amount for m in _damaged_modifier(_mh)], [1])
c.eq("...and Szarekh ONE -1, not two",
     [m.amount for m in _damaged_modifier(_sz)], [1])
c.true("...which the per-model field could never answer for it",
       TriarchalMenhirProfile.damaged_threshold is None)
c.eq("halving rounds UP - a 1-attack weapon is not deleted",
     damaged_attacks.halved(1), 1)
c.eq("...and 3 becomes 2", damaged_attacks.halved(3), 2)
_sz.current_wounds = 7
c.true("at 7 wounds nothing is halved", not damaged_attacks.halves_attacks_for(_sz))
c.true("...and the unit-wide penalty is off too", not damaged_attacks.covers_model(_mh))


# --- 8. Eternity Gate --------------------------------------------------------
print("--- 8. Eternity Gate ---")

c.eq("the gate's band is rule 03.04's, not a fourth literal",
     eternity_gate.ETERNITY_GATE_MIN_ENEMY_DISTANCE_IN,
     __import__("game.squad", fromlist=["x"]).ENGAGEMENT_RANGE_IN)
c.eq("...and its reach the printed 6\"", eternity_gate.ETERNITY_GATE_RANGE_IN, 6.0)
c.true("...both printed", "wholly within 6" in corpus("Monolith")
       and "unengaged" in corpus("Monolith"))

for _sheet, _want in ((WARRIORS, True), (IMMORTALS, True),
                      (MONOLITH, False), (VOID_DRAGON, False)):
    c.eq("%s is an eligible passenger: %s" % (_sheet.name, _want),
         eternity_gate.is_eligible_passenger(build(_sheet)), _want)
# A MIXED UNIT IS CONSTRUCTED, because no datasheet here builds one and the
# any()/all() reading is invisible without it - the probe that swapped them
# reported NO BITE. "NECRONS INFANTRY unit" is every model, not any: pooling
# it with any() would let one infantry component drag a vehicle through.
_mixed = build(WARRIORS, n=14)
_mixed.models[0].profile = MonolithProfile()
c.true("staging: the mixed unit really has one non-INFANTRY model",
       any(not m.profile.infantry for m in _mixed.models)
       and any(m.profile.infantry for m in _mixed.models))
c.true("a unit that is only PARTLY infantry cannot use the gate",
       not eternity_gate.is_eligible_passenger(_mixed))


def gate_scene(battle_round=2, auto=()):
    state = GameState()
    mono = place(build(MONOLITH), 20.0, 20.0)
    rider = place(build(WARRIORS, n=11), 30.0, 30.0, spacing=0.9)
    for s in (mono, rider):
        for m in s.models:
            state.add_token(m)

    class _Ing:
        eternity_gate_squad = None
        eternity_gate_bearer = None

    class _Turn:
        pass
    turn = _Turn()
    turn.battle_round = battle_round
    dm = DecisionManager()
    ctrl = eternity_gate.EternityGateController(
        decision_manager=dm, game_state=state, ingress_controller=_Ing(),
        turn_tracker=turn, auto_players=auto)
    return state, mono, rider, dm, ctrl


_s8, _mono8, _rider8, _dm8, _g8 = gate_scene(battle_round=1)
c.true("the gate is shut in the first battle round", not _g8.can_use(_mono8))
_s8b, _mono8b, _rider8b, _dm8b, _g8b = gate_scene(battle_round=2)
c.true("...and open from the second", _g8b.can_use(_mono8b))
c.true("a human is asked which unit", _g8b.offer(_mono8b))
c.eq("...with the passenger and a decline", len(_dm8b.options), 2)
_dm8b.choose(0)
c.true("the passenger leaves the battlefield",
       _rider8b.models[0] not in _s8b.tokens)
c.eq("...and is handed to the ingress controller as the gated arrival",
     _g8b.ingress_controller.eternity_gate_squad, _rider8b)
c.eq("...naming the Monolith to measure from",
     _g8b.ingress_controller.eternity_gate_bearer, _mono8b)
c.true("...and it cannot charge this turn",
       _rider8b.charge_locked_until_end_of_turn)
c.true("...and the Monolith is spent for the turn", not _g8b.can_use(_mono8b))

_s8c, _mono8c, _rider8c, _dm8c, _g8c = gate_scene(battle_round=2, auto=("Player 2",))
c.true("the AI declines - a named decision, not a missing path",
       not _g8c.offer(_mono8c))
c.true("...and nothing was withdrawn", _rider8c.models[0] in _s8c.tokens)

# THE THREE INGRESS SEAMS, MEASURED rather than grepped. Source pins on this
# file passed against a gate whose every branch had been turned off, because
# the strings they matched still appear - the probes for the deployment-zone
# waiver and for the placement check both reported NO BITE until this ran.
from game.ingress import IngressController  # noqa: E402
from game.deployment import DeploymentZone  # noqa: E402


class _Round:
    def __init__(self, n):
        self.battle_round = n


_s_ing = GameState()
_mono_i = place(build(MONOLITH), 20.0, 20.0)
_rider_i = place(build(WARRIORS, n=12), 20.0, 22.0, spacing=0.9)
_foe_i = place(build(WARRIORS, owner="Player 1", n=13), 50.0, 20.0, spacing=0.9)
for _s in (_mono_i, _foe_i):
    for _m in _s.models:
        _s_ing.add_token(_m)
_s_ing.deployment_zones = [DeploymentZone("Player 1", [(40.0, 0.0, 20.0, 44.0)])]
_ing = IngressController(None, _s_ing, _s_ing.tokens, turn_tracker=_Round(2))

# (a) the deployment-zone waiver. Rule 20.04 bans the opponent's zone before
#     round 3; the gate prints its own exemption, and the PASSENGER has no
#     Deep Strike of its own to inherit one from.
c.true("staging: a plain Warriors unit has no Deep Strike",
       not any(getattr(m.profile, "deep_strike", False) for m in _rider_i.models))
c.true("without the gate, the opponent's zone is refused",
       _ing._in_enemy_deployment_zone(_rider_i, 45.0, 20.0))
_ing.eternity_gate_squad = _rider_i
_ing.eternity_gate_bearer = _mono_i
c.true("...and WITH it the zone is allowed - the waiver is printed on the gate",
       not _ing._in_enemy_deployment_zone(_rider_i, 45.0, 20.0))

# (b) the 6" placement replaces the board edge, and (c) "unengaged" replaces
#     the 8" band. Both through the real _extra_check().
for _m in _rider_i.models:
    _m.x_in, _m.y_in = 20.0, 22.0
c.eq("a gated arrival beside the Monolith is legal", _ing._extra_check(_rider_i), [])
for _m in _rider_i.models:
    _m.x_in, _m.y_in = 20.0, 40.0
_far_errs = _ing._extra_check(_rider_i)
c.true("...and one 20\" away is not", _far_errs != [])
c.true("...naming the 6\" and the Monolith",
       any("6" in e and _mono_i.name in e for e in _far_errs))
for _m in _rider_i.models:
    _m.x_in, _m.y_in = 50.0, 20.0     # right on top of the enemy unit
c.true("a gated arrival inside Engagement Range is refused",
       any("unengaged" in e for e in _ing._extra_check(_rider_i)))
for _m in _rider_i.models:
    _m.x_in, _m.y_in = 20.0, 22.0
c.eq("...and it is rule 03.04's band that decides, not an 8\" literal",
     eternity_gate.ETERNITY_GATE_MIN_ENEMY_DISTANCE_IN, 2.0)

_ing_src = io.open(os.path.join("game", "ingress.py"), encoding="utf-8").read()
for _seam in ("_eternity_gate_extra_check",
              "self.eternity_gate_squad is squad",
              "eternity_gate.ETERNITY_GATE_MIN_ENEMY_DISTANCE_IN",
              "eternity_gate.ETERNITY_GATE_RANGE_IN"):
    c.true("ingress carries the gated arrival: %s" % _seam, _seam in _ing_src)
c.eq("...and clears it on BOTH outcomes",
     _ing_src.count("self.eternity_gate_squad = None"), 3)   # __init__ + confirm + cancel


# --- 9. Triarchal Menhirs, and the extraction --------------------------------
print("--- 9. linked destruction ---")

_sk9 = build(SILENT_KING)
c.true("nothing happens while Szarekh lives", not triarchal_menhirs.szarekh_is_down(_sk9))
c.eq("...and no Menhir is taken", triarchal_menhirs.menhirs_to_destroy(_sk9), [])
menhirs_of(_sk9)[0].current_wounds = 0
c.true("a dead MENHIR does not fire it in reverse",
       not triarchal_menhirs.szarekh_is_down(_sk9))
c.eq("...and Szarekh lives on", living(_sk9), 2)

_sk9b = build(SILENT_KING)
szarekh_of(_sk9b).current_wounds = 0
c.eq("Szarekh down takes BOTH remaining Menhirs",
     len(triarchal_menhirs.apply(_sk9b)), 2)
# THE `triarchal_menhir` FILTER CANNOT BE TOLD APART on this datasheet, and
# that is a fact about the DATA rather than a gap in the test: the rule only
# fires once Szarekh is down, and once he is down every remaining LIVING
# model of the unit IS a Menhir. So "take the Menhirs" and "take whatever is
# still standing" return the same list on every board this engine can build.
# Measured here rather than left to luck; the filter stays because the rule
# names the Menhirs, and ab_necron_titans.py carries the probe as a declared
# non-biter.
_sk9d = build(SILENT_KING)
szarekh_of(_sk9d).current_wounds = 0
c.eq("every model still standing when Szarekh falls IS a Menhir",
     [m for m in _sk9d.models if not m.is_dead()], menhirs_of(_sk9d))
c.eq("...leaving nothing standing", living(_sk9b), 0)

# THE PRE-SWEEP WINDOW IS WHAT IT WANTS, and the post-sweep one must not spare
# them - Squad has no starting_models, only a COUNT.
_sk9c = build(SILENT_KING)
_sz9c = szarekh_of(_sk9c)
_sz9c.current_wounds = 0
_sk9c.models.remove(_sz9c)
_sk9c.destroyed_models.append(_sz9c)
c.true("a Szarekh already swept off still counts as down",
       triarchal_menhirs.szarekh_is_down(_sk9c))
c.eq("...and the Menhirs still go", len(triarchal_menhirs.apply(_sk9c)), 2)

# THE EXTRACTION, with its OTHER carrier answering exactly as before.
c.true("charge_reroll is the shared base",
       issubclass(relentless_combatants.RelentlessCombatantsController,
                  charge_reroll.ChargeRerollController))
from game.phaeron_of_the_blades import PhaeronOfTheBladesController  # noqa: E402
c.true("...and so is the second carrier",
       issubclass(PhaeronOfTheBladesController, charge_reroll.ChargeRerollController))
c.eq("the two carriers claim under DIFFERENT labels",
     len({relentless_combatants.RELENTLESS_COMBATANTS_LABEL,
          PhaeronOfTheBladesController.LABEL}), 2)
try:
    charge_reroll.ChargeRerollController()
    _label_guard = False
except TypeError:
    _label_guard = True
c.true("a subclass that forgets its LABEL fails loudly at construction",
       _label_guard)
c.eq("relentless_combatants re-exports the constant, so no caller moved",
     relentless_combatants.MAX_CHARGE_ROLL_TOTAL, charge_reroll.MAX_CHARGE_ROLL_TOTAL)

# NO UNIT CAN HOLD BOTH, so the shared claim ledger never has to arbitrate.
_prae = build(PRAETORIANS)
c.true("the Praetorians have their own ability",
       relentless_combatants.squad_has_relentless_combatants(_prae))
c.true("...and are not under the aura",
       not triarch_auras.is_active(_prae, triarch_auras.PHAERON_OF_THE_BLADES))


# --- 10. wiring, AI, sprites, dormancy ---------------------------------------
print("--- 10. wiring ---")

MAIN_SRC = io.open("main.py", encoding="utf-8").read()
MAIN_AST = ast.parse(MAIN_SRC)
CALLS = set()
for _node in ast.walk(MAIN_AST):
    if isinstance(_node, ast.Call):
        _seg = ast.get_source_segment(MAIN_SRC, _node) or ""
        CALLS.add(" ".join(_seg.split()))


def called(fragment):
    return any(fragment in call for call in CALLS)


for _frag in ("voice_of_the_triarch_controller.sync_battle_round(",
              "eternity_gate_controller.offer(",
              "eternity_gate_controller.reset_turn(",
              "triarch_auras.refresh_active_auras(",
              "triarchal_menhirs.apply(",
              "phaeron_blades_controller.maybe_offer_charge_reroll("):
    c.true("main.py really calls %s" % _frag, called(_frag))

c.true("the aura stamp runs beside the other per-frame refreshes",
       "triarch_auras.refresh_active_auras(state.tokens)" in MAIN_SRC)
c.true("the Menhir sweep runs BEFORE remove_dead_models()",
       MAIN_SRC.find("triarchal_menhirs.apply(") <
       MAIN_SRC.find("_swept = state.remove_dead_models()"))

# THE AI NEGATIVE SPACE. Full datasheet names, because "Monolith" and "King"
# could appear in prose - the trap stages 5 and 6 both had to sidestep.
AI_SRC = io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read()
for _name in ("Monolith", "The Silent King", "Szarekh", "Triarchal Menhir",
              "Voice of the Triarch", "Eternity Gate", "Phaeron of the"):
    c.true("no AI judgement for %s" % _name, _name not in AI_SRC)
# THE MODULE SWEEP MATCHES AN IMPORT OR AN ATTRIBUTE ACCESS, never the bare
# word. "charge_reroll" is a substring of _charge_reroll_verdict(), a
# PRE-EXISTING function in that file for the CP-paying Command Re-roll - the
# same false-positive trap stages 5 and 6 hit with "Canoptek" and "C'tan".
for _mod in ("triarch_auras", "eternity_gate", "triarchal_menhirs",
             "silent_king_leadership", "damaged_attacks", "charge_reroll",
             "phaeron_of_the_blades"):
    c.true("...and ai/agent_driver.py neither imports nor calls %s" % _mod,
           ("import %s" % _mod) not in AI_SRC and ("%s." % _mod) not in AI_SRC)

# SPRITES - both have art, at exactly matching filenames.
for _sheet in NEW:
    _sq = build(_sheet)
    for _m in _sq.models:
        c.true("%s draws its own art" % _m.profile.name,
               sprites.sprite_for(_m) is not None)
c.eq("the Monolith's key shadows nothing and is shadowed by nothing",
     [k for k in sprites.SQUAD_SPRITE_KEYS if k in "2 Monolith 1"], ["Monolith"])
c.eq("...and The Silent King's likewise",
     [k for k in sprites.SQUAD_SPRITE_KEYS if k in "2 The Silent King 1"],
     ["The Silent King"])

# DORMANT BY ROSTER - armies/necrons.json fields neither.
ROSTER = io.open(os.path.join("armies", "necrons.json"), encoding="utf-8").read()
for _sheet in NEW:
    c.true("%s is dormant by roster" % _sheet.name, _sheet.name not in ROSTER)

# THE SCOPE RECORD IS EMPTY OF BUILD TARGETS - this was the last stage.
FETCH_SRC = io.open("fetch_datasheet_rules.py", encoding="utf-8").read()
_missing = between(FETCH_SRC, "MISSING_NECRONS = ", "]")
for _name in ("Monolith", "The Silent King"):
    c.true("%s is no longer on the missing list" % _name,
           '"%s"' % _name not in _missing)
c.true("...and the out-of-scope tail is still snapshotted",
       '"Doom Scythe", "Night Scythe", "Convergence Of Dominion"' in FETCH_SRC)
c.true("both corpus files are still on disk",
       os.path.exists(os.path.join("rules", "necrons", "Monolith.md"))
       and os.path.exists(os.path.join("rules", "necrons", "The Silent King.md")))

c.finish()
