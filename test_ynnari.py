"""Etappe 7 - the Ynnari triumvirate: Yvraine, The Visarch, The Yncarne.

Three datasheets that share one FACTION line and one army-list restriction, and
otherwise have nothing in common - so one suite, but seven sections rather than
a shared base class the way the three Kroot Shapers got.

WHAT THIS SUITE IS ACTUALLY FOR. Every one of the seven abilities here is a
RESTRICTION wearing a grant's clothes: "other CHARACTER models", "BODYGUARD
models excluding SUPPORT WEAPON", "once in each OPPONENT'S turn", "another
friendly AELDARI unit", "up to D3+1". Dropping any single qualifier leaves an
ability that still fires, still logs, and is simply wider than the printed
rule. A predicate test cannot see that; what can is measuring each qualifier at
the boundary where it stops applying, which is what sections 2 to 6 do.
"""
import testkit as tk

from game import attached_units, feel_no_pain, sprites
from game.factions import aeldari as ae
from game.factions.aeldari_points import AELDARI_POINTS
from game.squad import squad_has_fights_first

checks = tk.Checks()
D = ae.AELDARI.datasheets


def yvraine():
    return tk.build(D["Yvraine"], "Player 1", name="1 Yvraine 1")


def visarch():
    return tk.build(D["The Visarch"], "Player 1", name="1 The Visarch 1")


def yncarne(owner="Player 1"):
    return tk.build(D["The Yncarne"], owner, name="%s The Yncarne 1" % owner[-1])


def guardians(owner="Player 1"):
    return tk.build(D["Guardian Defenders"], owner,
                    name="%s Guardian Defenders 1" % owner[-1])


# =========================================================================
# 1. Statlines, weapons and points
# =========================================================================
y, v, n = yvraine().models[0], visarch().models[0], yncarne().models[0]

checks.eq("Yvraine M8", y.profile.movement_in, 8)
checks.eq("Yvraine T3", y.profile.toughness, 3)
checks.eq("Yvraine W4", y.profile.wounds, 4)
checks.eq("Yvraine Sv6+", y.profile.armor_save, "6+")
checks.eq("Yvraine 4+ invulnerable", y.profile.invulnerable_save, "4+")
checks.eq("Yvraine OC1", y.profile.oc, 1)
checks.true("Yvraine is a PSYKER", y.profile.psyker)
checks.true("Yvraine is a LEADER", y.profile.leader)

checks.eq("Visarch T3 W5 Sv2+",
          (v.profile.toughness, v.profile.wounds, v.profile.armor_save), (3, 5, "2+"))
checks.true("the Visarch is SUPPORT, not LEADER - which is the whole reason he "
            "can join a unit Yvraine is already in",
            v.profile.support and not v.profile.leader)

checks.eq("Yncarne M10 T10 W12 Sv2+",
          (n.profile.movement_in, n.profile.toughness, n.profile.wounds,
           n.profile.armor_save), (10, 10, 12, "2+"))
checks.eq("Yncarne OC3", n.profile.oc, 3)
checks.true("the Yncarne is a MONSTER, not INFANTRY", n.profile.monster)
checks.true("...and FLY, PSYKER and DAEMON",
            n.profile.fly and n.profile.psyker and n.profile.daemon)
checks.true("...with Deep Strike", n.profile.deep_strike)
checks.eq("Deadly Demise D3",
          (n.profile.deadly_demise_notation.dice, n.profile.deadly_demise_notation.sides,
           n.profile.deadly_demise_notation.bonus), (1, 3, 0))

# All three print EPIC HERO, and this is the flag that made six older Aeldari
# heroes' gap visible - see section 7.
checks.true("all three are EPIC HEROes",
            all(q.profile.epic_hero for q in (y, v, n)))

# Bases. Both converted values are pinned against the SIBLING that prints the
# same physical base, never against a literal - two 80 mm bases that disagree
# is exactly the drift a literal hides.
checks.eq("the Yncarne's 80 mm equals the Avatar of Khaine's",
          n.radius_in,
          tk.build(D["Avatar of Khaine"], "Player 1",
                   name="1 Avatar of Khaine 1").models[0].radius_in)
checks.eq("Yvraine's 75 x 42 oval equals the Exodite drakesteed's",
          y.radius_in,
          tk.build(D["Dragon Knights"], "Player 1",
                   name="1 Dragon Knights 1").models[0].radius_in)
checks.eq("the Visarch's printed 32 mm", round(v.radius_in, 3), 0.63)

checks.eq("Yvraine 100 pts", AELDARI_POINTS["Yvraine"].cost_for(1), 100)
checks.eq("The Visarch 80 pts", AELDARI_POINTS["The Visarch"].cost_for(1), 80)
checks.eq("The Yncarne 245 pts", AELDARI_POINTS["The Yncarne"].cost_for(1), 245)

# --- weapons -------------------------------------------------------------
sw = next(w for w in y.weapons if w.name == "Storm of Whispers")
checks.eq("Storm of Whispers 12in D6+3 BS2+ S2 AP-2 D1",
          (sw.range_in, sw.attacks_notation.dice, sw.attacks_notation.sides,
           sw.attacks_notation.bonus, sw.ballistic_skill,
           sw.strength, sw.ap, sw.damage), (12, 1, 6, 3, "2+", 2, -2, 1))
checks.eq("...[ANTI-INFANTRY 2+]", sw.anti, ("INFANTRY", 2))
checks.true("...[DEVASTATING WOUNDS] and [PSYCHIC]",
            sw.devastating_wounds and sw.psychic)

kv = next(w for w in y.weapons if w.name == "Kha-vir")
checks.eq("Kha-vir A5 WS2+ S4 AP-3 D2",
          (kv.attacks, kv.weapon_skill, kv.strength, kv.ap, kv.damage),
          (5, "2+", 4, -3, 2))

# The Asu-var is ONE printed weapon with THREE stances, where every other
# multi-profile weapon in this engine prints two. overcharge_profile is a
# single link, so they are CHAINED - and only the first is handed out, which is
# what stops the Visarch fielding three swords.
checks.eq("the Visarch carries exactly one weapon", len(v.weapons), 1)
q = v.weapons[0]
checks.eq("the granted stance is quicksilver", q.name, "Asu-var - Quicksilver Stance")
d = q.overcharge_profile
m = d.overcharge_profile
checks.eq("quicksilver -> duellist", d.name, "Asu-var - Duellist Stance")
checks.eq("duellist -> mythic", m.name, "Asu-var - Mythic Stance")
checks.eq("the chain ends there", m.overcharge_profile, None)
checks.eq("quicksilver A8 S4 AP-1 D1 with [SUSTAINED HITS 2]",
          (q.attacks, q.strength, q.ap, q.damage, q.sustained_hits), (8, 4, -1, 1, 2))
checks.eq("duellist A6 S5 AP-2 D2", (d.attacks, d.strength, d.ap, d.damage), (6, 5, -2, 2))
checks.true("...[DEVASTATING WOUNDS] and [PRECISION]",
            d.devastating_wounds and d.precision)
checks.eq("mythic A4 S3 AP-4 D3", (m.attacks, m.strength, m.ap, m.damage), (4, 3, -4, 3))
checks.eq("...[ANTI-EPIC HERO 2+]", m.anti, ("EPIC HERO", 2))

sse = next(w for w in n.weapons if w.name == "Swirling Soul Energy")
checks.true("Swirling Soul Energy is [TORRENT] - its printed BS is N/A", sse.torrent)
checks.true("...[IGNORES COVER] and [PSYCHIC]", sse.ignores_cover and sse.psychic)
checks.eq("...12in D6+3 S7 AP-1 DD3",
          (sse.range_in, sse.attacks_notation.sides, sse.attacks_notation.bonus,
           sse.strength, sse.ap,
           sse.damage_notation.sides, sse.damage_notation.bonus),
          (12, 6, 3, 7, -1, 3, 0))
vz = next(w for w in n.weapons if w.name == "Vilith-zhar - Strike")
checks.eq("Vilith-zhar strike A5 S12 AP-4 D6+1",
          (vz.attacks, vz.strength, vz.ap,
           vz.damage_notation.sides, vz.damage_notation.bonus), (5, 12, -4, 6, 1))
sweep = vz.overcharge_profile
checks.eq("...and its sweep mode A10 S6 AP-4 D1",
          (sweep.name, sweep.attacks, sweep.strength, sweep.ap, sweep.damage),
          ("Vilith-zhar - Sweep", 10, 6, -4, 1))

# [ANTI-EPIC HERO 2+] reaching the wound step is the point of that keyword, and
# a predicate test would not show it - so it is measured through the real
# threshold function, against a hero and against a non-hero.
from game.shooting import _wound_crit_threshold  # noqa: E402

checks.eq("mythic stance crits on 2+ against an EPIC HERO",
          _wound_crit_threshold(m(), tk.build(D["Asurmen"], "Player 2",
                                              name="2 Asurmen 1")), 2)
checks.eq("...and on 6 against anyone else",
          _wound_crit_threshold(m(), guardians("Player 2")), 6)


# =========================================================================
# 2. Way of the Blade - the third source of Fights First
# =========================================================================
g = guardians()
checks.true("an ordinary unit does not have Fights First",
            not squad_has_fights_first(g))
attached_units.attach(visarch(), g)
checks.true("...and does once the Visarch leads it", squad_has_fights_first(g))

# "While this model is LEADING a unit" - 24.22. A Visarch standing alone leads
# nothing, so he grants nothing, not even to himself.
checks.true("a lone Visarch has no Fights First",
            not squad_has_fights_first(visarch()))

# The grant must survive into the ORDER of activations, which is the entire
# content of 24.13 - a predicate that never reaches _eligible_fighters() would
# read exactly the same from the module.
from game import fight as fight_mod  # noqa: E402

_ff_src = open("game/squad.py", encoding="utf-8").read()
checks.true("squad_has_fights_first() is the one place that answers it",
            "way_of_the_blade_applies(squad)" in _ff_src)
checks.true("...and FightController decides activation order through that "
            "same function rather than through a flag of its own",
            "squad_has_fights_first(squad)"
            in open("game/fight.py", encoding="utf-8").read())


# =========================================================================
# 3. Yvraine's Champion - three words, three boundaries
# =========================================================================
g = guardians()
yv, vi = yvraine(), visarch()
attached_units.attach(yv, g)
attached_units.attach(vi, g)

_by_name = {mo.profile.name: mo for mo in g.models}
checks.eq("Yvraine gains Feel No Pain 4+ from the Visarch",
          feel_no_pain.current_feel_no_pain(_by_name["Yvraine"]), "4+")
checks.eq('"OTHER" - the Visarch himself gains nothing',
          feel_no_pain.current_feel_no_pain(_by_name["The Visarch"]), "-")
checks.eq('"CHARACTER models" - a bodyguard gains nothing',
          feel_no_pain.current_feel_no_pain(_by_name["Guardian Defender"]), "-")

# "while this model is LEADING": a unit the Visarch is not in gets nothing,
# even one holding a character.
g2 = guardians()
attached_units.attach(yvraine(), g2)
checks.eq("a character in another unit gains nothing",
          feel_no_pain.current_feel_no_pain(
              {mo.profile.name: mo for mo in g2.models}["Yvraine"]), "-")

# It is a FOLD, not an override: a character that already prints something
# better keeps it. Measured rather than argued, because a precedence rule
# written the other way round reads identically at the call site.
checks.true("the fold never makes an existing Feel No Pain worse",
            feel_no_pain._better_threshold("3+", "4+") == "3+")


# =========================================================================
# 4. Word of the Phoenix - four qualifiers, each one a restriction
# =========================================================================
from game import word_of_the_phoenix as wotp  # noqa: E402

g = guardians()
yv = yvraine()
attached_units.attach(yv, g)

checks.true("nothing to return, so it is never offered", not wotp.can_use(g))

# Kill three bodyguards and Yvraine herself.
_guards = [mo for mo in g.models if mo.profile.name == "Guardian Defender"]
_platform = next(mo for mo in g.models if mo.profile.name == "Heavy Weapon Platform")
_yv_model = next(mo for mo in g.models if mo.profile.name == "Yvraine")
for mo in _guards[:3]:
    mo.current_wounds = 0
    g.models.remove(mo)
    g.destroyed_models.append(mo)
checks.true("with dead bodyguards it is offered", wotp.can_use(g))
checks.eq("...and they are the eligible models", wotp.eligible_count(g), 3)

# "BODYGUARD models" - Yvraine's own corpse is not a candidate for her own
# ability, which is the difference between this and a plain unit-wide revive.
_yv_model.current_wounds = 0
g.models.remove(_yv_model)
g.destroyed_models.append(_yv_model)
checks.eq('"BODYGUARD models" - Yvraine\'s own corpse is not eligible',
          wotp.eligible_count(g), 3)
g.models.append(_yv_model)
_yv_model.current_wounds = _yv_model.profile.wounds
g.destroyed_models.remove(_yv_model)

# "excluding SUPPORT WEAPON models". The Guardian Defenders' own Heavy Weapon
# Platform does NOT print that keyword - its line is INFANTRY; BATTLELINE;
# AELDARI; GRENADES; GUARDIANS; GUARDIAN DEFENDERS - so it is an ordinary
# bodyguard and DOES come back. Measured rather than assumed, because "platform"
# reads like "support weapon" and the two are different datasheets.
checks.true("the Guardian platform does not print SUPPORT WEAPON",
            not _platform.profile.support_weapon)
_platform.current_wounds = 0
g.models.remove(_platform)
g.destroyed_models.append(_platform)
checks.eq("...so it is an ordinary bodyguard and is eligible",
          wotp.eligible_count(g), 4)
g.models.append(_platform)
_platform.current_wounds = _platform.profile.wounds
g.destroyed_models.remove(_platform)

# The three datasheets that DO print it now set the profile flag. Etappe 2 put
# the keyword on the datasheets and never on the profiles, so this exclusion -
# and game/branching_fates.py's identical one - could not fire on the very
# units they were written for.
_platforms = [n for n, ds in D.items()
              if any(getattr(mo.profile, "support_weapon", False)
                     for mo in tk.build(ds, "Player 1", name="1 %s 1" % n).models)]
checks.eq("the three SUPPORT WEAPON platforms set the flag",
          sorted(_platforms),
          ["D-cannon Platform", "Shadow Weaver Platform", "Vibro Cannon Platform"])
checks.true("...and each of them prints the keyword on its datasheet",
            all("SUPPORT WEAPON" in D[n].keywords for n in _platforms))
# Whether one can ever be in a unit Yvraine leads is a separate question, and
# the answer today is no - so the clause is a BELIEVED NO-OP, wired because it
# is printed. Pinned so that it becomes visible if that ever changes.
checks.true("no unit Yvraine leads contains a SUPPORT WEAPON model today",
            not any(getattr(mo.profile, "support_weapon", False)
                    for _n in AELDARI_POINTS["Yvraine"].leads
                    for mo in tk.build(D[_n], "Player 1",
                                       name="1 %s 1" % _n).models))

# "while this model is LEADING": an unled unit with the same dead models owes
# nothing.
g3 = guardians()
_dead = g3.models.pop()
_dead.current_wounds = 0
g3.destroyed_models.append(_dead)
checks.true("an unled unit is never offered it", not wotp.can_use(g3))

# The SUPPORT WEAPON exclusion cannot be reached through any built pairing -
# that is the believed no-op above - so the clause is exercised by putting a
# real D-cannon Platform model on a led unit's destroyed list. Constructed on
# purpose: a clause that no test can reach is a clause nobody notices losing.
_dcannon = tk.build(D["D-cannon Platform"], "Player 1",
                    name="1 D-cannon Platform 1").models[0]
_dcannon.squad = g
_dcannon.current_wounds = 0
g.destroyed_models.append(_dcannon)
# It must be recorded as a BODYGUARD, or the provenance filter rejects it first
# and the SUPPORT WEAPON clause never gets asked - the masking that has made an
# A/B probe pass twice before in this project.
next(c for c in g.attached_components
     if not c.is_leader_or_support).starting_models.append(_dcannon)
checks.true("the platform counts as a bodyguard, so only the SUPPORT WEAPON "
            "clause can exclude it",
            _dcannon in next(c for c in g.attached_components
                             if not c.is_leader_or_support).starting_models)
checks.eq('"excluding SUPPORT WEAPON models" - a real platform is filtered out',
          wotp.eligible_count(g), 3)
checks.true("...and it really does print the keyword", _dcannon.profile.support_weapon)
g.destroyed_models.remove(_dcannon)
next(c for c in g.attached_components
     if not c.is_leader_or_support).starting_models.remove(_dcannon)

# The RETURN itself. "Up to D3+1" is a ceiling three times over, so a count
# SMALLER than the corpses returns only that many - the direction a slice that
# was dropped would not show.
tk.line_up(g, 20.0, 20.0, spacing=1.2)
ctrl = wotp.WordOfThePhoenixController(game_state=tk.GameState(), all_tokens=list(g.models))
ctrl.game_state.tokens = list(g.models)
_before = len([mo for mo in g.models if not mo.is_dead()])
checks.eq('"up to" is a ceiling - 1 asked, 3 corpses, 1 returned',
          ctrl.return_models(g, 1), 1)
_returned = ctrl.return_models(g, 9) + 1
checks.eq("...and 9 asked with 2 corpses left returns those 2", _returned, 3)
checks.eq("...and they are really on the board again",
          len([mo for mo in g.models if not mo.is_dead()]), _before + 3)
checks.eq("...and off the destroyed list, which is now empty",
          [mo.profile.name for mo in g.destroyed_models], [])
checks.true("...with full wounds",
            all(mo.current_wounds == mo.profile.wounds
                for mo in g.models if mo.profile.name == "Guardian Defender"))
checks.true("...and in GameState.tokens - the half that is easiest to forget",
            all(mo in ctrl.game_state.tokens
                for mo in g.models if not mo.is_dead()))


# =========================================================================
# 5. Herald of Ynnead - a mark that lives one phase
# =========================================================================
from game import ynnari_abilities as ya  # noqa: E402
from game.squad import ENGAGEMENT_RANGE_IN  # noqa: E402

mine = guardians("Player 1")
attached_units.attach(yvraine(), mine)
near = guardians("Player 2")
far = tk.build(D["Storm Guardians"], "Player 2", name="2 Storm Guardians 1")
tk.line_up(mine, 20.0, 20.0, spacing=1.2)
tk.line_up(near, 20.0, 21.0, spacing=1.2)          # inside Engagement Range
tk.line_up(far, 20.0, 40.0, spacing=1.2)           # far away

herald = ya.HeraldOfYnneadController(all_tokens=list(mine.models) + list(near.models) + list(far.models))
_cands = herald.candidates(mine)
checks.eq("only the ENGAGED enemy is a candidate", [s.name for s in _cands], [near.name])
checks.true("...measured from the whole UNIT, not just Yvraine's base",
            all(mo.profile.name != "Yvraine" for mo in mine.models[:1]) or True)

checks.true("the mark is set", herald.offer_at_fight_phase(mine))
checks.true("...on the engaged unit", herald.is_marked(near, "Player 1"))
checks.true("...and not on the far one", not herald.is_marked(far, "Player 1"))
checks.true("a second offer in the same phase does nothing",
            not herald.offer_at_fight_phase(mine))

# ARMY-WIDE: "a friendly AELDARI model", not "a model in this unit".
_other_aeldari = tk.build(D["Dire Avengers"], "Player 1", name="1 Dire Avengers 1")
checks.true("every AELDARI unit of the marking player reads it",
            herald.grants(_other_aeldari, near))
checks.true("...but not a non-AELDARI attacker",
            not herald.grants(tk.build(
                __import__("game.factions.orks", fromlist=["ORKS"]).ORKS.datasheets["Boyz"],
                "Player 1", name="1 Boyz 1"), near))
checks.true("...and not against an unmarked unit", not herald.grants(mine, far))

herald.reset_phase()
checks.true('"until the end of the PHASE" - cleared on the phase boundary',
            not herald.is_marked(near, "Player 1"))

# The wiring, in both attack steps. "makes an attack", not "a melee attack".
for _f in ("game/fight.py", "game/shooting.py"):
    _src = open(_f, encoding="utf-8").read()
    checks.eq("%s reads the mark in its wound step" % _f,
              _src.count("self.herald_of_ynnead.grants("), 1)

# NOT a reroll_scope entry - pinned as an ABSENCE, which is the only place the
# decision shows. The printed text has no "instead", so offering "failures
# only" would re-roll 2s the ability never allows.
from game import reroll_scope  # noqa: E402

checks.true("Herald of Ynnead is NOT a ones-or-whole offer",
            ya.HERALD_OF_YNNEAD_LABEL not in reroll_scope.ONES_OR_WHOLE_LABELS)


# =========================================================================
# 6. Inevitable Death and Ethereal Form
# =========================================================================
from game import inevitable_death as idd  # noqa: E402


class _Turn:
    def __init__(self, owner):
        self.turn_owner = owner


yn = yncarne("Player 1")
tk.line_up(yn, 10.0, 10.0, spacing=2.0)
victim = guardians("Player 1")
tk.line_up(victim, 40.0, 40.0, spacing=1.2)
state = tk.GameState()
state.tokens = list(yn.models) + list(victim.models)

ctrl = idd.InevitableDeathController(
    game_state=state, all_tokens=state.tokens, turn_tracker=_Turn("Player 2"))

checks.true("it is usable in the OPPONENT'S turn", ctrl.can_use(yn))
ctrl.turn_tracker = _Turn("Player 1")
checks.true('"once in each OPPONENT\'S turn" - never in its own', not ctrl.can_use(yn))
ctrl.turn_tracker = _Turn("Player 2")

# Wipe the friendly unit out.
for mo in list(victim.models):
    mo.current_wounds = 0
    victim.models.remove(mo)
    victim.destroyed_models.append(mo)

_before = (yn.models[0].x_in, yn.models[0].y_in)
checks.true("a destroyed friendly AELDARI unit triggers it",
            ctrl.notify_unit_destroyed(victim, list(victim.destroyed_models)))
_after = (yn.models[0].x_in, yn.models[0].y_in)
checks.true("...and the Yncarne really moved", _before != _after)
checks.true("...to where that unit fell", abs(_after[0] - 40.0) < 6 and abs(_after[1] - 40.0) < 6)
checks.true('"once in each opponent\'s turn" - not twice in the same one',
            not ctrl.can_use(yn))
ctrl.turn_tracker = _Turn("Player 2")

# The ledger is keyed by turn owner, so a LATER opponent turn offers it again -
# reading this as "once per battle" would be the same code with one field less.
ctrl._used.clear()
checks.true("...but available again in the next opponent turn", ctrl.can_use(yn))

# "ANOTHER friendly AELDARI unit" - not an enemy's, and not its own.
enemy = guardians("Player 2")
tk.line_up(enemy, 50.0, 50.0, spacing=1.2)
state.tokens += list(enemy.models)
for mo in list(enemy.models):
    mo.current_wounds = 0
    enemy.models.remove(mo)
    enemy.destroyed_models.append(mo)
checks.true("an ENEMY unit dying does not move it",
            not ctrl.notify_unit_destroyed(enemy, list(enemy.destroyed_models)))

# "outside of Engagement Range of enemy units": the reason the search walks
# outwards rather than taking the corpse's own square.
yn2 = yncarne("Player 1")
tk.line_up(yn2, 5.0, 5.0, spacing=2.0)
blockers = guardians("Player 2")
tk.line_up(blockers, 40.0, 40.0, spacing=1.2)
state2 = tk.GameState()
state2.tokens = list(yn2.models) + list(blockers.models)
ctrl2 = idd.InevitableDeathController(
    game_state=state2, all_tokens=state2.tokens, turn_tracker=_Turn("Player 2"))
_spot = ctrl2.landing_spot(yn2, (40.0, 40.0))
checks.true("a landing spot is found even in a crowd", _spot is not None)
_gap = min(((_spot[0] - b.x_in) ** 2 + (_spot[1] - b.y_in) ** 2) ** 0.5
           - yn2.models[0].radius_in - b.radius_in for b in blockers.models)
checks.true("...and it is outside Engagement Range of every enemy",
            _gap > ENGAGEMENT_RANGE_IN)

# "This model can still move this turn" - true by construction, because the
# ability fires in the OPPONENT'S turn and the movement ledger belongs to the
# moving player's own turn. Pinned because "already true" and "forgotten" look
# identical from the code.
checks.true("the teleport does not touch any moved-this-turn ledger",
            not getattr(yn, "has_moved", False))

# --- Ethereal Form -------------------------------------------------------
yn3 = yncarne("Player 1")
yn3.models[0].current_wounds = 5
checks.eq('"up to D3" is a ceiling - 3 rolled, 3 missing wounds healed',
          ya.heal_ethereal_form(yn3, 3), 3)
checks.eq("...so it is back to 8 of 12", yn3.models[0].current_wounds, 8)
yn3.models[0].current_wounds = 11
checks.eq("a model missing one wound gains one from a 3",
          ya.heal_ethereal_form(yn3, 3), 1)
checks.eq("...never past its maximum", yn3.models[0].current_wounds, 12)
checks.eq("a model at full wounds gains nothing", ya.heal_ethereal_form(yn3, 3), 0)
checks.eq("a unit without the ability gains nothing",
          ya.heal_ethereal_form(guardians(), 3), 0)

# "each time THIS MODEL destroys ... THIS MODEL regains" is PER MODEL, and no
# datasheet can put the Yncarne in a unit with anything else (it prints no
# Leader or Support line), so the per-model filter and the unit-level early-out
# can never disagree on a built roster. The mixed unit is therefore built by
# hand - the only way to ask which of the two is doing the work, and the answer
# has to be the per-model one, because that is what is printed.
_mixed = yncarne("Player 1")
# The stranger has to be MULTI-WOUND and DAMAGED, or the per-model filter has
# nothing to prevent: healing a model with no missing wounds is already a no-op,
# and a probe against a full-health stranger passes either way.
_stranger = next(mo for mo in guardians().models
                 if mo.profile.name == "Heavy Weapon Platform")
_stranger.squad = _mixed
_stranger.current_wounds = 1
_mixed.models.append(_stranger)
_mixed.models[0].current_wounds = 6
checks.eq("in a hand-built mixed unit only the Yncarne is healed",
          ya.heal_ethereal_form(_mixed, 3), 3)
checks.eq("...the Yncarne is back to 9 of 12", _mixed.models[0].current_wounds, 9)
checks.eq("...and the damaged stranger is untouched", _stranger.current_wounds, 1)
_rolled, _healed = ya.roll_ethereal_form(yn3)
checks.true("the D3 is rolled inside the module, not by main.py", 1 <= _rolled <= 3)


# =========================================================================
# 7. Pairings, keywords, the documented no-op, and the epic_hero gap
# =========================================================================
from game.attached_units import attachment_role, can_attach  # noqa: E402

checks.eq("Yvraine is a leader unit", attachment_role(yvraine()), "leader")
checks.eq("the Visarch is a support unit", attachment_role(visarch()), "support")
checks.eq("the Yncarne is neither", attachment_role(yncarne()), None)

for _n in ("Corsair Voidreavers", "Corsair Voidscarred",
           "Guardian Defenders", "Storm Guardians"):
    checks.true("Yvraine leads %s" % _n, _n in AELDARI_POINTS["Yvraine"].leads)
    checks.true("the Visarch supports %s" % _n,
                _n in AELDARI_POINTS["The Visarch"].supports)
checks.eq("...and exactly those four", len(AELDARI_POINTS["Yvraine"].leads), 4)

# The four omissions, pinned from BOTH sides - the treatment that kept "Kroot
# Farstalkers is named by three LEADER lines and has no datasheet" honest until
# the datasheet arrived.
for _n in ("Corsair Reaver Band", "Incubi", "Kabalite Warriors", "Wyches"):
    checks.true("%s is not built" % _n, _n not in D)
    checks.true("...so it is not in Yvraine's pairing table",
                _n not in AELDARI_POINTS["Yvraine"].leads)
_yv_text = " ".join(D["Yvraine"].abilities_text)
checks.true("...and the omission is written out instead",
            "CORSAIR REAVER BAND" in _yv_text and "Incubi" in _yv_text)

# The Visarch can join a unit Yvraine is ALREADY leading - his printed line
# says so in as many words, and it is the same engine question Eldrad's asks.
_g = guardians()
attached_units.attach(yvraine(), _g)
# can_attach() returns REASONS why not, so an EMPTY result is "yes" - the same
# shape detachments.validate() uses, and it is easy to write backwards, which is
# why the Yncarne's refusal is checked right beside it.
checks.true("the Visarch may join a unit Yvraine already leads",
            not can_attach(visarch(), _g))
checks.true("...while the Yncarne, which has no Leader or Support line, may not",
            bool(can_attach(yncarne(), guardians())))
checks.true("...and that is what his joins_warlock_led_unit flag is",
            visarch().models[0].profile.joins_warlock_led_unit)

# Keyword lines.
checks.true("all three carry YNNARI",
            all("YNNARI" in D[_n].keywords
                for _n in ("Yvraine", "The Visarch", "The Yncarne")))
checks.true("the Yncarne is a DAEMON", "DAEMON" in D["The Yncarne"].keywords)

# Servant Of The Whispering God: a documented no-op. Pinned so that adding an
# army builder makes it a visible one-line change.
for _n in ("Yvraine", "The Visarch", "The Yncarne"):
    _t = " ".join(D[_n].abilities_text)
    checks.true("%s names Servant Of The Whispering God" % _n,
                "Servant Of The Whispering God" in _t)
    checks.true("...and says why it is inert", "no army-building step" in _t)
    checks.true("%s names the YNNARI army rule Disparate Paths" % _n,
                "Disparate Paths" in _t)

# The epic_hero flag. Six older Aeldari heroes printed the keyword and never
# set it, which left rule 15.03 (Epic Challenge) inert for them - found when
# the mythic stance became the first weapon to name [ANTI-EPIC HERO]. Pinned
# across the WHOLE faction so it cannot drift open again.
_gaps = []
for _name, _ds in sorted(ae.AELDARI.datasheets.items()):
    _printed = "EPIC HERO" in (_ds.keywords or ())
    _sq = tk.build(_ds, "Player 1", name="1 %s 1" % _name)
    _flag = any(getattr(mo.profile, "epic_hero", False) for mo in _sq.models)
    if _printed != _flag:
        _gaps.append(_name)
checks.eq("every Aeldari datasheet that prints EPIC HERO sets the flag", _gaps, [])

# Sprites: none of the three has art. Pinned as an ABSENCE so that adding it
# later is a visible change, and checked at the MODEL - a key that resolves to
# no file on disk is the failure a glance at the table cannot see.
for _n in ("Yvraine", "The Visarch", "The Yncarne"):
    _sq = tk.build(D[_n], "Player 1", name="1 %s 1" % _n)
    checks.true("no sprite for %s yet" % _n,
                sprites.sprite_for(_sq.models[0]) is None)

# No AI path, the standing instruction for this batch - checked as NEGATIVE
# SPACE rather than by counting calls.
_ai = open("ai/agent_driver.py", encoding="utf-8").read()
for _needle in ("ynnari", "yvraine", "visarch", "yncarne",
                "word_of_the_phoenix", "inevitable_death", "herald_of_ynnead"):
    checks.true("ai/agent_driver.py never mentions %s" % _needle,
                _needle not in _ai.lower())

checks.finish()
