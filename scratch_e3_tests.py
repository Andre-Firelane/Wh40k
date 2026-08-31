"""Appends section 3 (Etappe 3) to test_aeldari_enhancements.py."""
import io

SECTION = '''

# =========================================================================
# 3. Rolls and re-rolls
#    Mirage Field, Shimmerstone, Guiding Presence, Breath of Vaul,
#    Mantle of Wisdom.
# =========================================================================
print("\\n3. Rolls and re-rolls")

import game.fight as _f_mod  # noqa: E402
from game import enh_breath_of_vaul as ebv  # noqa: E402
from game import enh_guiding_presence as egp  # noqa: E402
from game import enh_mantle_of_wisdom as emw  # noqa: E402
from game import enh_mirage_field as emf  # noqa: E402
from game import enh_shimmerstone as esh  # noqa: E402
from game import path_of_the_warrior as potw  # noqa: E402
from game.factions import aeldari as aeldari_mod  # noqa: E402
from game.modifiers import apply_modifiers  # noqa: E402
from game.weapons import RANGED  # noqa: E402

_shoot_src = io.open("game/shooting.py", encoding="utf-8").read()


class _E3State:
    """The two fields the controllers here read off game_state."""

    def __init__(self, *squads):
        self.tokens = [m for s in squads for m in s.models]


def _ranged_gun(squad):
    return next(w for w in squad.models[0].weapons if w.weapon_type == RANGED)


def _group(scene, gun=None):
    """What _hit_modifiers()/_begin_resolution() actually take."""
    gun = gun if gun is not None else _ranged_gun(scene["attacker"])
    return {"pairs": [(m, gun) for m in scene["attacker"].models],
            "target_squad": scene["target"]}


def _led(leader_name, unit_name, owner=HUMAN):
    """A real 19.01 attached unit, built through the real attach()."""
    leader = sq(leader_name, owner)
    unit = sq(unit_name, owner)
    reasons = attached_units.can_attach(leader, unit)
    assert not reasons, (leader_name, unit_name, reasons)
    attached_units.attach(leader, unit)
    return unit


def _leader_model(unit, leader_name):
    """The merged-in leader model, for naming a bearer explicitly. Several of
    these cards are "ASURYANI model only", so every bodyguard qualifies too and
    grant() refuses to guess which one carries the upgrade."""
    return next(m for m in unit.models if m.profile.name == leader_name)


# --- 3a. Mirage Field: DEFENDER-side, and in BOTH chains ------------------
_mf_unit = sq("Windriders")
# Every Windrider is ASURYANI MOUNTED, so grant() refuses to guess which one
# carries a 25-point upgrade - the bearer is named, as army building would.
E.grant(_mf_unit, "Mirage Field", model=_mf_unit.models[0])

with only("WINDRIDER_HOST_PLAYERS"):
    c.true("attacks targeting the bearer's unit take the malus", emf.applies(_mf_unit))
with none_fielded():
    c.true("no detachment, no malus", not emf.applies(_mf_unit))

# "the bearer's UNIT" - one model carries it, every model is shielded. Under
# 19.01 that is what a joined character's Enhancement means, and it is the
# reason this is asked of the SQUAD.
c.eq("exactly one model carries it", len(E.bearer_models(_mf_unit, "Mirage Field")), 1)
c.true("...but the whole unit is protected",
       len(_mf_unit.models) > 1)

# THE SIGN. Positive = worse. Written the other way round this would be an
# army-wide bonus to everything shooting at the bearer.
c.true("it WORSENS the roll", emf.MIRAGE_FIELD_PENALTY > 0)

# ...end to end, through the REAL shooting hit step.
_mf_scene = tk.shooting_scene(D["Dire Avengers"], D["Windriders"], attacker_owner="Player 2")
tk.line_up(_mf_scene["attacker"], 20.0, 20.0, spacing=1.2)
tk.line_up(_mf_scene["target"], 20.0, 26.0, spacing=1.2)
_mf_shoot = _mf_scene["shooting"]
_mf_shoot.active_squad = _mf_scene["attacker"]
_mf_grp = _group(_mf_scene)
with none_fielded():
    _mf_without = [m.source for m in _mf_shoot._hit_modifiers(_mf_grp)]
E.grant(_mf_scene["target"], "Mirage Field", model=_mf_scene["target"].models[0])
with only("WINDRIDER_HOST_PLAYERS", players=("Player 1",)):
    _mf_with = _mf_shoot._hit_modifiers(_mf_grp)
c.true("the real RANGED hit step is clean without it",
       emf.MIRAGE_FIELD_LABEL not in _mf_without)
c.true("...and carries it with", emf.MIRAGE_FIELD_LABEL in [m.source for m in _mf_with])
c.eq("...as a +1 on the threshold, i.e. a HARDER roll",
     apply_modifiers(3, [m for m in _mf_with if m.source == emf.MIRAGE_FIELD_LABEL]), 4)

# ...and through the REAL melee hit step. "An attack", not "a ranged attack" -
# the one word that separates it from Shimmerstone, so this is measured and
# not assumed.
_mff = tk.fight_scene(D["Dire Avengers"], D["Windriders"], attacker_owner="Player 2")
tk.line_up(_mff["attacker"], 20.0, 20.0, spacing=1.2)
tk.line_up(_mff["target"], 20.0, 21.0, spacing=1.2)
_mff_fight = _mff["fight"]
_mff_fight.fighting_squad = _mff["attacker"]
_mff_model = _mff["attacker"].models[0]
with none_fielded():
    _mff_without = [m.source for m in _mff_fight._hit_modifiers(_mff_model, _mff["target"])]
E.grant(_mff["target"], "Mirage Field", model=_mff["target"].models[0])
with only("WINDRIDER_HOST_PLAYERS", players=("Player 1",)):
    _mff_with = [m.source for m in _mff_fight._hit_modifiers(_mff_model, _mff["target"])]
c.true("the real MELEE hit step is clean without it",
       emf.MIRAGE_FIELD_LABEL not in _mff_without)
c.true("...and carries it with - 'an attack' means both phases",
       emf.MIRAGE_FIELD_LABEL in _mff_with)


# --- 3b. Shimmerstone: three conditions, RANGED only ----------------------
_sh_unit = _led("Autarch", "Howling Banshees")
E.grant(_sh_unit, "Shimmerstone")

with only("ASPECT_HOST_PLAYERS"):
    c.true("a led ASPECT WARRIORS unit is protected", esh.applies(_sh_unit))

    # CONDITION 2, isolated: carried but NOT leading. Built by granting the
    # flag to a lone Autarch, which is a bearer with no unit to lead.
    _sh_alone = sq("Autarch")
    E.grant(_sh_alone, "Shimmerstone")
    c.true("...but a bearer leading nothing is not",
           not esh.applies(_sh_alone))

    # CONDITION 3, isolated: leading, but not ASPECT WARRIORS. Guardian
    # Defenders measured above as carrying neither keyword.
    _sh_wrong = _led("Farseer", "Guardian Defenders")
    setattr(_sh_wrong.models[0].profile, "shimmerstone", True)
    c.true("...and a led unit that is not ASPECT WARRIORS is not either",
           not esh.applies(_sh_wrong))
with none_fielded():
    c.true("no detachment, nothing", not esh.applies(_sh_unit))

c.true("it WORSENS the roll", esh.SHIMMERSTONE_PENALTY > 0)

# ...end to end through the REAL wound step.
_sh_scene = tk.shooting_scene(D["Dire Avengers"], D["Howling Banshees"], attacker_owner="Player 2")
tk.line_up(_sh_scene["attacker"], 20.0, 20.0, spacing=1.2)
tk.line_up(_sh_scene["target"], 20.0, 26.0, spacing=1.2)
_sh_shoot = _sh_scene["shooting"]
_sh_shoot.active_squad = _sh_scene["attacker"]
_sh_target = _sh_scene["target"]
attached_units.attach(sq("Autarch", "Player 1"), _sh_target)
E.grant(_sh_target, "Shimmerstone")
with none_fielded():
    _sh_without = [m.source for m in _sh_shoot._wound_modifiers(_sh_target)]
with only("ASPECT_HOST_PLAYERS", players=("Player 1",)):
    _sh_with = _sh_shoot._wound_modifiers(_sh_target)
c.true("the real wound step is clean without it",
       esh.SHIMMERSTONE_LABEL not in _sh_without)
c.true("...and carries it with", esh.SHIMMERSTONE_LABEL in [m.source for m in _sh_with])
c.eq("...as a +1 on the WOUND threshold",
     apply_modifiers(4, [m for m in _sh_with if m.source == esh.SHIMMERSTONE_LABEL]), 5)

# RANGED-ONLY, asserted at the SOURCE. A melee scene that happens to come out
# unchanged would not distinguish "not wired" from "wired and inapplicable".
c.true("Shimmerstone never reaches the Fight phase",
       "enh_shimmerstone" not in _fight_src)
c.true("...while Mirage Field does", "enh_mirage_field" in _fight_src)


# --- 3c. Guiding Presence: a mark on a FRIENDLY unit ----------------------
_gp_seer = sq("Farseer")
E.grant(_gp_seer, "Guiding Presence")
_gp_falcon = sq("Falcon")
_gp_enemy_falcon = sq("Falcon", "Player 2")
_gp_banshees = sq("Howling Banshees")

with only("ARMOURED_WARHOST_PLAYERS"):
    c.true("a friendly AELDARI VEHICLE unit is eligible",
           egp.is_eligible_target(_gp_falcon, HUMAN))
    # "FRIENDLY" - an enemy vehicle would be a 25-point gift.
    c.true("...an ENEMY vehicle is not",
           not egp.is_eligible_target(_gp_enemy_falcon, HUMAN))
    # "VEHICLE" - not just any Aeldari unit.
    c.true("...and a non-VEHICLE friendly unit is not",
           not egp.is_eligible_target(_gp_banshees, HUMAN))

c.true("+1 to hit is a BONUS, so a NEGATIVE threshold adjustment",
       egp.GUIDING_PRESENCE_BONUS < 0)

# The 6" boundary and the visibility clause, measured through the controller.
_gp_state = _E3State(_gp_seer, _gp_falcon, _gp_banshees, _gp_enemy_falcon)
_gp_ctrl = egp.GuidingPresenceController(game_state=_gp_state, auto_players=(HUMAN,))
with only("ARMOURED_WARHOST_PLAYERS"):
    tk.line_up(_gp_seer, 20.0, 20.0, spacing=1.2)
    tk.line_up(_gp_falcon, 20.0, 24.0, spacing=1.2)      # inside 6"
    c.true("a vehicle within 6\\" is a candidate",
           _gp_falcon in _gp_ctrl.candidates(HUMAN))
    tk.line_up(_gp_falcon, 20.0, 40.0, spacing=1.2)      # far outside
    c.true("...and one far away is not",
           _gp_falcon not in _gp_ctrl.candidates(HUMAN))
    # "VISIBLE" - the optional collaborator, refusing everything.
    tk.line_up(_gp_falcon, 20.0, 24.0, spacing=1.2)
    _gp_blind = egp.GuidingPresenceController(
        game_state=_gp_state, auto_players=(HUMAN,), visible=lambda a, b: False)
    c.eq("...and one in range but not VISIBLE is not either",
         _gp_blind.candidates(HUMAN), [])

    # The mark itself, and its lifetime.
    c.true("nothing is marked before the phase starts", not _gp_ctrl.applies(_gp_falcon))
    _gp_ctrl.offer_at_start_of_shooting_phase(HUMAN)
    c.true("...the chosen unit is marked", _gp_ctrl.applies(_gp_falcon))
    c.true("...and no other unit is", not _gp_ctrl.applies(_gp_banshees))
    _gp_ctrl.reset_phase()
    c.true("...and the mark is gone next phase", not _gp_ctrl.applies(_gp_falcon))

# ...end to end through the REAL hit step.
_gp_scene = tk.shooting_scene(D["Falcon"], D["Dire Avengers"], attacker_owner=HUMAN)
tk.line_up(_gp_scene["attacker"], 20.0, 20.0, spacing=1.2)
tk.line_up(_gp_scene["target"], 20.0, 26.0, spacing=1.2)
_gp_shoot = _gp_scene["shooting"]
_gp_shoot.active_squad = _gp_scene["attacker"]
_gp_grp = _group(_gp_scene)
_gp_live = egp.GuidingPresenceController(game_state=_gp_state)
_gp_shoot.guiding_presence = _gp_live
with only("ARMOURED_WARHOST_PLAYERS"):
    _gp_before = [m.source for m in _gp_shoot._hit_modifiers(_gp_grp)]
    _gp_live._choose(HUMAN, _gp_scene["attacker"])
    _gp_after = _gp_shoot._hit_modifiers(_gp_grp)
c.true("the real hit step is clean before the mark",
       egp.GUIDING_PRESENCE_LABEL not in _gp_before)
c.true("...and carries it after",
       egp.GUIDING_PRESENCE_LABEL in [m.source for m in _gp_after])
c.eq("...as a -1 on the threshold, i.e. an EASIER roll",
     apply_modifiers(3, [m for m in _gp_after
                         if m.source == egp.GUIDING_PRESENCE_LABEL]), 2)

# RANGED, so not in the Fight phase.
c.true("Guiding Presence never reaches the Fight phase",
       "enh_guiding_presence" not in _fight_src)

# WIRING - the class this repo has been bitten by seven times.
c.true("main.py builds the Guiding Presence controller",
       "guiding_presence_controller = GuidingPresenceController(" in _main_src2)
c.true("...hands it to the shooting controller",
       "shooting_controller.guiding_presence = guiding_presence_controller" in _main_src2)
c.true("...and drives it at the start of the Shooting phase",
       "guiding_presence_controller.offer_at_start_of_shooting_phase(" in _main_src2)
c.true("...clearing the previous mark first",
       before(_main_src2, "guiding_presence_controller.reset_phase()",
              "guiding_presence_controller.offer_at_start_of_shooting_phase("))


# --- 3d. Breath of Vaul: two re-rolls, two different rolls ----------------
# BUILT WITH THE TWO SPECIAL WEAPONS. The default Storm Guardian carries a
# shuriken pistol and nothing this card names, so a unit built plainly would
# exercise neither half - the checks below would pass while proving nothing.
_bv_leader = sq("Farseer")
_bv_unit = tk.build(D["Storm Guardians"], HUMAN, name="1 Storm Guardians 9", choices={
    "Storm Guardian": {aeldari_mod.STORM_GUARDIAN_PISTOL_TO_FLAMER: 1,
                       aeldari_mod.STORM_GUARDIAN_PISTOL_TO_FUSION: 1}})
attached_units.attach(_bv_leader, _bv_unit)
E.grant(_bv_unit, "Breath of Vaul", model=_leader_model(_bv_unit, "Farseer"))
_bv_flamer = next((w for m in _bv_unit.models for w in m.weapons
                   if ebv.is_flamer(w)), None)
_bv_fusion = next((w for m in _bv_unit.models for w in m.weapons
                   if ebv.is_fusion_gun(w)), None)
_bv_pistol = next(w for m in _bv_unit.models for w in m.weapons
                  if w.weapon_type == RANGED and not ebv.is_flamer(w)
                  and not ebv.is_fusion_gun(w))
c.true("the unit really carries a flamer", _bv_flamer is not None)
c.true("...and a fusion gun", _bv_fusion is not None)
# The flamer's Attacks characteristic IS a die - which is the whole reason the
# first half exists.
c.true("...whose Attacks characteristic is a die",
       _bv_flamer is not None and _bv_flamer.attacks_notation is not None)
c.true("...and the fusion gun's Damage is a die too",
       _bv_fusion is not None and _bv_fusion.damage_notation is not None)

with only("GUARDIAN_BATTLEHOST_PLAYERS"):
    c.true("the three shared conditions hold for a led STORM GUARDIANS unit",
           ebv.applies(_bv_unit))
    _bv_wrong = _led("Autarch", "Howling Banshees")
    setattr(_bv_wrong.models[0].profile, "breath_of_vaul", True)
    c.true("...and not for a led unit that is not STORM GUARDIANS",
           not ebv.applies(_bv_wrong))
with none_fielded():
    c.true("no detachment, nothing", not ebv.applies(_bv_unit))

# THE TWO HALVES ARE DIFFERENT WEAPONS. Reading one for the other would make
# the card fire on the wrong die.
with only("GUARDIAN_BATTLEHOST_PLAYERS"):
    c.true("the FLAMER gets the Attacks half", ebv.attacks_reroll_applies(_bv_unit, _bv_flamer))
    c.true("...and not the Damage half", not ebv.damage_reroll_applies(_bv_unit, _bv_flamer))
    c.true("the FUSION GUN gets the Damage half", ebv.damage_reroll_applies(_bv_unit, _bv_fusion))
    c.true("...and not the Attacks half", not ebv.attacks_reroll_applies(_bv_unit, _bv_fusion))
    c.true("a shuriken pistol gets neither half",
           not ebv.attacks_reroll_applies(_bv_unit, _bv_pistol)
           and not ebv.damage_reroll_applies(_bv_unit, _bv_pistol))
with none_fielded():
    c.true("...and without the detachment, the flamer gets nothing either",
           not ebv.attacks_reroll_applies(_bv_unit, _bv_flamer))

# The class match is EXACT, measured: neither profile has subclasses, so
# matching by class cannot quietly widen to another datasheet's flamer.
import inspect as _inspect  # noqa: E402
from game import weapons as _W  # noqa: E402
for _bv_name in ("AeldariFlamerProfile", "FusionGunProfile"):
    _bv_base = getattr(_W, _bv_name)
    c.eq("%s has no subclasses to widen into" % _bv_name,
         [k.__name__ for k in vars(_W).values()
          if _inspect.isclass(k) and k is not _bv_base and issubclass(k, _bv_base)], [])

# NOT a reroll_scope source. That module is the narrower "the 1s OR the whole
# roll" shape; listing these there would offer a failures-only subset the
# printed text never grants. Only visible as an absence.
c.true("Breath of Vaul is not a reroll_scope source",
       "breath_of_vaul" not in io.open("game/reroll_scope.py", encoding="utf-8").read())

# WIRING, both halves, at the call expression.
c.true("the ATTACKS half is offered in the real attacks step",
       "enh_breath_of_vaul.attacks_reroll_applies(self.active_squad, raw_weapon)" in _shoot_src)
c.true("the DAMAGE half joins the existing offer chain",
       "enh_breath_of_vaul.damage_reroll_applies(self.active_squad, weapon)" in _shoot_src)
# The re-roll has to be a REAL new visible roll, or the offer buys nothing.
c.true("...and an accepted Attacks re-roll throws a new visible roll",
       "is_reroll=True" in _shoot_src.split("def _after_attacks_reroll")[1].split("def _finish_attacks_roll")[0])

# THE EXTRACTION: one definition, two names.
from game import damage_reroll as _dr_shim  # noqa: E402
from game import notation_reroll as _nr  # noqa: E402
c.true("damage_reroll re-exports notation_reroll's class, not a copy",
       _dr_shim.DamageRerollOffer is _nr.DamageRerollOffer)
c.eq("...and the roll name defaults to Damage, so every old caller is unchanged",
     _nr.DamageRerollOffer("x").roll_name, "Damage")


# --- 3e. Mantle of Wisdom: it widens the RULE ------------------------------
_mw_unit = _led("Autarch", "Dire Avengers")
E.grant(_mw_unit, "Mantle of Wisdom")
_mw_ctrl = potw.PathOfTheWarriorController()

with only("ASPECT_HOST_PLAYERS"):
    c.true("the bearer's led ASPECT WARRIORS unit qualifies", emw.applies(_mw_unit))
    # BOTH abilities - the whole point of the card.
    c.true("it gains the HIT half", _mw_ctrl.hit_ones_apply(_mw_unit))
    c.true("...and the WOUND half at the same time",
           _mw_ctrl.wound_ones_apply(_mw_unit))
    # ...and therefore is never asked to choose. Offering a choice that
    # changes nothing would read as a limit that no longer exists.
    c.true("no choice is offered", not _mw_ctrl.offer(_mw_unit))

    # THE CONTRAST, on a unit without it: exactly one half, and it IS asked.
    _mw_plain = sq("Dire Avengers")
    c.true("a unit without it gets neither half until it chooses",
           not _mw_ctrl.hit_ones_apply(_mw_plain)
           and not _mw_ctrl.wound_ones_apply(_mw_plain))
    _mw_ctrl.choose(_mw_plain, potw.HIT)
    c.true("...and then exactly one",
           _mw_ctrl.hit_ones_apply(_mw_plain)
           and not _mw_ctrl.wound_ones_apply(_mw_plain))
with none_fielded():
    c.true("no detachment, nothing", not emw.applies(_mw_unit))

# READ AT THE RULE, not at the four consumers - so a widening cannot be
# applied to three of them.
_potw_src = io.open("game/path_of_the_warrior.py", encoding="utf-8").read()
c.eq("the rule itself reads Mantle of Wisdom, in both of its answers",
     _potw_src.count("enh_mantle_of_wisdom.applies(squad)"), 3)
for _mw_file in ("game/shooting.py", "game/fight.py"):
    c.true("%s never reads it directly" % _mw_file,
           "enh_mantle_of_wisdom" not in io.open(_mw_file, encoding="utf-8").read())
'''

p = "test_aeldari_enhancements.py"
s = io.open(p, encoding="utf-8").read()
old = "\n\nc.finish()"
assert s.count(old) == 1
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, SECTION + "\n\nc.finish()"))
print("appended")
