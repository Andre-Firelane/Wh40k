"""The Skorpekh Lord - fourteenth Necron datasheet, and the fourth of the
DESTROYER CULT.

TWO ABILITIES, AND THEY FAIL IN DIFFERENT PLACES, so they are measured in
different places.

United In Destruction is a keyword GRANT, and the way a grant goes wrong here
is never the copying - it is the CONDITION. So it is driven through the real
attach() in both directions (led / not led / standing alone) AND through
FightController's own _adjusted_weapon() chain, because a grant module that
works while nothing calls it is exactly the "built but never fed" defect this
project has hit three times.

Crimson Harvest is a TRIGGER, and what goes wrong with a trigger is the moment.
Its D6 has THREE outcomes, not two (1 nothing / 2-5 D3 / 6 D3+3), so all three
are rolled rather than the pass and the fail; and the seam itself is driven
through the real ChargeController, since "each time this model ends a Charge
move" exists nowhere else and a confirmed charge is the only thing that is it -
a DECLINED one must not fire it.

THE BASE SIZE is pinned against the other three Destroyer datasheets rather
than against a literal. The printed size is 60 mm; the table size is the
Skorpekh 50 mm, on the user's standing instruction that all Destroyers share
one size. Three separate literals would drift apart the next time one is
touched, so the shared value IS the assurance.
"""

import pathlib

import testkit as tk
from testkit import Checks, GameState, build_squad, script
from game import attached_units, guardian_protocols, sprites, united_in_destruction
from game import mortal_wound_abilities as mw
from game.charge import ChargeController, DECLARING_TARGETS
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import necrons as nec
from game.factions.necrons_points import NECRONS_POINTS
from game.movement import MovementController
from game.squad import ENGAGEMENT_RANGE_IN
from game.turn import PHASE_CHARGE, TurnTracker
from game.units import (
    LokhustDestroyerProfile, LokhustHeavyDestroyerProfile,
    SkorpekhDestroyerProfile, SkorpekhLordProfile,
)
from game import weapons as w

c = Checks("Skorpekh Lord")


def build(sheet, owner="Player 2", name=None, **kw):
    kw.setdefault("name", name or f"{owner[-1]} {sheet.name} 1")
    return build_squad(sheet, owner, **kw)


def lord(name="2 Skorpekh Lord 1"):
    return build(nec.SKORPEKH_LORD, name=name)


def destroyers(name="2 Skorpekh Destroyers 1"):
    return build(nec.SKORPEKH_DESTROYERS, name=name)


# --- 1. statline -------------------------------------------------------------
print("--- 1. statline ---")

sq = lord()
c.eq("one model", len(sq.models), 1)
p = sq.models[0].profile
c.eq("M8 T7 Sv3+ W7 Ld6+ OC2",
     (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc),
     (8, 7, "3+", 7, "6+", 2))
c.eq("WS2+ / BS2+", (p.weapon_skill, p.ballistic_skill), ("2+", "2+"))
c.eq("4+ invulnerable save", p.invulnerable_save, "4+")
c.eq("INFANTRY CHARACTER, and a LEADER (24.22)",
     (p.infantry, p.character, p.leader), (True, True, True))
c.eq("Reanimation Protocols, like every NECRONS unit", p.reanimation_protocols, True)
c.eq("keywords transcribed in full", nec.SKORPEKH_LORD.keywords,
     ("INFANTRY", "CHARACTER", "DESTROYER CULT", "SKORPEKH LORD", "NECRONS"))

# NOT NOBLE, and this is the trap worth a line of its own: the Overlord is the
# roster's only NOBLE, and Guardian Protocols is gated on one LEADING the unit.
# A Lord wrongly marked noble would silently hand the Lychguard's defensive
# rule to a Destroyer squad.
c.eq("NOBLE is not among the printed keywords",
     "NOBLE" in nec.SKORPEKH_LORD.keywords, False)
c.eq("...and the profile does not claim it either", getattr(p, "noble", False), False)
_led_by_lord = attached_units.attach(lord("2 Skorpekh Lord 90"),
                                     destroyers("2 Skorpekh Destroyers 90"))
c.eq("so leading a unit with him does NOT switch on Guardian Protocols",
     guardian_protocols.unit_has_guardian_protocols(_led_by_lord), False)


# --- 2. the base size, pinned against the other three Destroyers -------------
print("--- 2. base size ---")

c.eq("the Skorpekh Lord takes the Destroyer table size, not his printed 60 mm",
     SkorpekhLordProfile.base_radius_in, SkorpekhDestroyerProfile.base_radius_in)
c.eq("...which is the same one all four Destroyer datasheets share",
     {SkorpekhLordProfile.base_radius_in, SkorpekhDestroyerProfile.base_radius_in,
      LokhustDestroyerProfile.base_radius_in,
      LokhustHeavyDestroyerProfile.base_radius_in},
     {0.984})
# 50 mm -> radius in inches, recomputed rather than copied, so the number is
# derived from something and not from the line above it.
c.eq("...and 0.984in really is a 50 mm base",
     round((50.0 / 25.4) / 2.0, 3), 0.984)


# --- 3. the three weapons ----------------------------------------------------
print("--- 3. weapons ---")

names = [wp.name for wp in sq.models[0].weapons]
c.eq("all three printed weapons are carried - there are no wargear options",
     names, ["Enmitic Annihilator", "Flensing Claw", "Hyperphase Harvester"])
c.eq("...and the datasheet really has none, rather than none being chosen",
     list(nec.SKORPEKH_LORD.wargear_options or ()), [])

ann = w.EnmiticAnnihilatorProfile()
c.eq('Enmitic annihilator: 18" A2 BS2+ S6 AP-1 D1',
     (ann.range_in, ann.attacks, ann.ballistic_skill, ann.strength, ann.ap, ann.damage),
     (18, 2, None, 6, -1, 1))
c.eq("...with [RAPID FIRE 2], read off the NAME - the keyword column came back "
     "empty again (the ~16th time this artifact has appeared)",
     ann.rapid_fire, 2)
# Its near-namesake belongs to the Lokhust Heavy Destroyers and is a different
# gun entirely. Pinned as a DIFFERENCE, because a shared class would pass any
# test that only read one of them.
ext = w.EnmiticExterminatorProfile()
c.eq("the Enmitic EXTERMINATOR is a different weapon, not the same class",
     (ext.range_in, ext.attacks) != (ann.range_in, ann.attacks), True)

claw = w.FlensingClawProfile()
c.eq("Flensing claw: A8 WS2+ S6 AP-1 D1",
     (claw.attacks, claw.strength, claw.ap, claw.damage), (8, 6, -1, 1))
harv = w.HyperphaseHarvesterProfile()
c.eq("Hyperphase harvester: A4 WS2+ S10 AP-3 D3",
     (harv.attacks, harv.strength, harv.ap, harv.damage), (4, 10, -3, 3))

# THE POINT OF THE PAIR: neither is [EXTRA ATTACKS], so rule 04.01 makes them a
# real choice - eight light swings or four heavy ones - rather than a claw that
# comes free alongside the harvester. Checked rather than assumed, because a
# many-attacks claw usually IS [EXTRA ATTACKS].
c.eq("neither melee weapon is [EXTRA ATTACKS], so 04.01 makes them alternatives",
     (claw.extra_attacks, harv.extra_attacks), (False, False))
c.eq("...and neither carries any other keyword",
     (claw.lethal_hits, claw.devastating_wounds, claw.sustained_hits,
      harv.lethal_hits, harv.devastating_wounds, harv.sustained_hits),
     (False, False, 0, False, False, 0))
# Distinct from the two hyperphase weapons this faction already fields.
c.eq("the harvester is not the Lychguard's Hyperphase Sword",
     (harv.attacks, harv.strength) != (w.HyperphaseSwordProfile().attacks,
                                       w.HyperphaseSwordProfile().strength), True)
c.eq("...nor the Skorpekh Destroyers' own hyperphase weapons",
     (harv.strength, harv.ap, harv.damage)
     != (w.SkorpekhHyperphaseWeaponsProfile().strength,
         w.SkorpekhHyperphaseWeaponsProfile().ap,
         w.SkorpekhHyperphaseWeaponsProfile().damage), True)


# --- 4. points and the LEADER pairing ---------------------------------------
print("--- 4. points and pairing ---")

pts = NECRONS_POINTS["Skorpekh Lord"]
c.eq("90 points for the first two units", pts.cost_for(1, unit_index=1), 90)
c.eq("...and 100 from the third onward", pts.cost_for(1, unit_index=3), 100)
c.eq("he leads Skorpekh Destroyers and nothing else", tuple(pts.leads),
     ("Skorpekh Destroyers",))
c.eq("attaching to Skorpekh Destroyers is legal",
     attached_units.can_attach(lord("2 Skorpekh Lord 4"),
                               destroyers("2 Skorpekh Destroyers 4")), [])
c.true("...and to Lychguard is not",
       bool(attached_units.can_attach(lord("2 Skorpekh Lord 5"),
                                      build(nec.LYCHGUARD, name="2 Lychguard 5"))))


# --- 5. the sprite -----------------------------------------------------------
print("--- 5. sprite ---")

# Checked at the MODEL, not in the table: a key that resolves to no file on
# disk is exactly the error a glance at the mapping cannot see.
art = sprites.sprite_for(lord("2 Skorpekh Lord 6").models[0])
c.true("the Skorpekh Lord resolves to a real image file",
       art is not None and pathlib.Path(art).exists())
c.true("...to its own art, not the Destroyers'", "Skorpekh Lord" in str(art))
# The only Necron file without the "Necron " prefix the other thirteen carry -
# the folder wins, as it does everywhere else in that table.
c.eq("the mapped key is the file's own name", sprites.SQUAD_SPRITE_KEYS["Skorpekh Lord"],
     "Skorpekh Lord")
# The pair that could actually shadow each other, checked rather than assumed:
# _key_for_name() returns on the FIRST substring hit.
c.true("the Lord and his bodyguards get DIFFERENT art",
       sprites.sprite_for(lord("2 Skorpekh Lord 7").models[0])
       != sprites.sprite_for(destroyers("2 Skorpekh Destroyers 7").models[0]))
c.eq('"Overlord" is not a substring of "Skorpekh Lord", so the Overlord entry '
     "cannot swallow it", "Overlord" in "2 Skorpekh Lord 7", False)


# --- 6. United In Destruction ------------------------------------------------
print("--- 6. United In Destruction ---")

alone = lord("2 Skorpekh Lord 10")
c.eq("a Lord standing on his own is not LEADING anything (24.22), so nothing "
     "is granted", united_in_destruction.unit_has_united_in_destruction(alone), False)

plain = destroyers("2 Skorpekh Destroyers 11")
c.eq("an unled Skorpekh squad has no [LETHAL HITS] either",
     united_in_destruction.adjusted_weapon(
         w.SkorpekhHyperphaseWeaponsProfile(), plain).lethal_hits, False)

led = attached_units.attach(lord("2 Skorpekh Lord 12"),
                            destroyers("2 Skorpekh Destroyers 12"))
c.eq("once he leads them, the ability is live",
     united_in_destruction.unit_has_united_in_destruction(led), True)
granted = united_in_destruction.adjusted_weapon(w.SkorpekhHyperphaseWeaponsProfile(), led)
c.eq("...and their melee weapons gain [LETHAL HITS]", granted.lethal_hits, True)

base = w.SkorpekhHyperphaseWeaponsProfile()
c.eq("a COPY is returned, never the shared instance",
     united_in_destruction.adjusted_weapon(base, led) is not base, True)
c.eq("...and the shared instance is left alone", base.lethal_hits, False)
already = w.SkorpekhHyperphaseWeaponsProfile()
already.lethal_hits = True
c.eq("a weapon that already has it is passed straight through",
     united_in_destruction.adjusted_weapon(already, led) is already, True)

# "melee weapons equipped by models in THAT unit" - his own harvester and claw
# are weapons of models in the unit, so they gain it too.
c.eq("his own melee weapons are covered as well",
     united_in_destruction.adjusted_weapon(w.HyperphaseHarvesterProfile(), led).lethal_hits,
     True)

# The bodyguards' own datasheet must not claim the ability - it is a LEADER
# ability, and a unit_wide_ability()-shaped predicate would be False for every
# unit that really has it (game/attached_units.py documents that trap).
c.eq("the ability is printed on the LORD, not on the Destroyers",
     (SkorpekhLordProfile.united_in_destruction,
      getattr(SkorpekhDestroyerProfile, "united_in_destruction", False)),
     (True, False))


# --- 6b. ...through FightController's own chain ------------------------------
print("--- 6b. the chain in fight.py ---")

scene = tk.fight_scene(nec.SKORPEKH_DESTROYERS, nec.NECRON_WARRIORS)
attacker = scene["attacker"]
before = scene["fight"]._adjusted_weapon(
    [(attacker.models[0], w.SkorpekhHyperphaseWeaponsProfile())], scene["target"])
c.eq("an unled squad's weapon comes out of the real chain WITHOUT [LETHAL HITS]",
     before.lethal_hits, False)

# Attach a Lord into that same live scene and ask the same chain again.
lord_sq = lord("2 Skorpekh Lord 13")
lord_sq.models[0].x_in, lord_sq.models[0].y_in = attacker.models[0].x_in, attacker.models[0].y_in
scene["state"].add_token(lord_sq.models[0])
attached_units.attach(lord_sq, attacker, game_state=scene["state"])
scene["fight"].fighting_squad = attacker
after = scene["fight"]._adjusted_weapon(
    [(attacker.models[0], w.SkorpekhHyperphaseWeaponsProfile())], scene["target"])
c.eq("with the Lord leading it, the SAME chain returns [LETHAL HITS]",
     after.lethal_hits, True)

# A/B at the source: neutralise the ability and the same call falls back.
_real = united_in_destruction.unit_has_united_in_destruction
try:
    united_in_destruction.unit_has_united_in_destruction = lambda squad: False
    probe = scene["fight"]._adjusted_weapon(
        [(attacker.models[0], w.SkorpekhHyperphaseWeaponsProfile())], scene["target"])
    c.eq("A/B: with the ability neutralised at its source the keyword is gone",
         probe.lethal_hits, False)
finally:
    united_in_destruction.unit_has_united_in_destruction = _real


# --- 7. Crimson Harvest: who can be selected ---------------------------------
print("--- 7. Crimson Harvest targets ---")

state = GameState()
harvester_unit = lord("2 Skorpekh Lord 20")
near = build(nec.NECRON_WARRIORS, owner="Player 1", composition_index=0,
             name="1 Necron Warriors 20")
far = build(nec.IMMORTALS, owner="Player 1", composition_index=0, name="1 Immortals 20")
tk.line_up(harvester_unit, x=20.0, y=20.0)
tk.line_up(near, x=20.0, y=21.0)
tk.line_up(far, x=20.0, y=40.0)
state.tokens = list(harvester_unit.models) + list(near.models) + list(far.models)

c.eq("the ability is on the datasheet", mw.has_crimson_harvest(harvester_unit), True)
c.eq("only the unit within Engagement Range can be selected",
     [s.name for s in mw.crimson_harvest_targets(harvester_unit, state.tokens)],
     ["1 Necron Warriors 20"])
c.eq("Engagement Range is the printed measure, not a range in inches",
     ENGAGEMENT_RANGE_IN, 2.0)
# A charge that fell short leaves nothing in range, and that is the whole
# "did it connect" test - no separate success flag is needed or wanted.
for model in near.models:
    model.y_in += 6.0
c.eq("out of Engagement Range, there is nothing to select at all",
     mw.crimson_harvest_targets(harvester_unit, state.tokens), [])
for model in near.models:
    model.y_in -= 6.0


# --- 8. Crimson Harvest: all THREE outcomes of the D6 ------------------------
print("--- 8. the three outcomes ---")


def harvest(gate, amount):
    """Roll the gate, then (if it passed) the amount. Returns the controller."""
    ctrl = mw.CrimsonHarvestController(
        dice_manager=DiceManager(), game_state=state, auto_players=("Player 2",))
    script(gate, amount, default=1)
    ctrl.on_charge_move_finished(harvester_unit)
    ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()   # the gate
    if ctrl.is_busy:
        ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()  # the amount
    return ctrl


def inflicted(ctrl):
    s = ctrl.mortal_wound_session
    return None if s is None else s.inflicted + s.remaining


one = harvest(1, 3)
c.eq("a 1 does nothing at all - not even a second roll",
     (one.mortal_wound_session, one.is_busy), (None, False))

mid = harvest(2, 3)
c.eq("a 2 is the bottom of the 2-5 band and inflicts a plain D3", inflicted(mid), 3)
five = harvest(5, 2)
c.eq("a 5 is the top of that band and still a plain D3", inflicted(five), 2)

six = harvest(6, 2)
c.eq("a 6 inflicts D3+3 - the bonus is what the gate value decides",
     inflicted(six), 5)
c.eq("...so a 6 with the SAME D3 beats a 5 by exactly 3",
     inflicted(harvest(6, 2)) - inflicted(harvest(5, 2)), 3)

# The middle band is the one that gets lost: a test that only rolls a 1 and a 6
# passes just as well with the threshold written as 6+.
c.eq("the gate threshold is 2, not 6", mw.CRIMSON_HARVEST_THRESHOLD, 2)
c.eq("...and the big-roll bonus is +3 on a 6",
     (mw.CRIMSON_HARVEST_BIG_ROLL, mw.CRIMSON_HARVEST_BIG_BONUS), (6, 3))

# Not optional: "select", not "you can". With one candidate there is nothing
# to ask, so no prompt is raised even with a human decision manager wired.
dec = DecisionManager()
ctrl = mw.CrimsonHarvestController(dice_manager=DiceManager(), decision_manager=dec,
                                   game_state=state, auto_players=())
script(4, 2, default=1)
ctrl.on_charge_move_finished(harvester_unit)
c.eq("with a single candidate the ability just happens - it is not a 'you can'",
     (dec.is_pending, ctrl.is_busy), (False, True))


# --- 9. the seam: a CONFIRMED charge, and only that -------------------------
print("--- 9. the charge seam ---")


def charge_scene():
    """A real charge, driven the way the engine drives one: declare, begin the
    move, commit a segment, confirm. A single-model target so the Lord has
    somewhere legal to land - a 20-model line leaves no gap that is inside
    Engagement Range and outside base overlap."""
    st = GameState()
    lord_unit = lord("2 Skorpekh Lord 30")
    prey = build(nec.OVERLORD, owner="Player 1", name="1 Overlord 30")
    tk.line_up(lord_unit, x=20.0, y=20.0)
    tk.line_up(prey, x=20.0, y=24.0)
    st.tokens = list(lord_unit.models) + list(prey.models)
    mc = MovementController(all_tokens=st.tokens)
    tt = TurnTracker()
    while tt.phase != PHASE_CHARGE:
        tt.advance_phase()
    cc = ChargeController(dice_manager=DiceManager(), turn_tracker=tt,
                          all_tokens=st.tokens, movement_controller=mc, game_log=tk.Log())
    ctrl = mw.CrimsonHarvestController(dice_manager=DiceManager(), game_state=st,
                                       auto_players=("Player 2",))
    cc.on_charge_move_finished.append(ctrl.on_charge_move_finished)
    cc.active_squad = lord_unit
    cc.charge_targets = [prey]
    cc.max_distance = 8
    cc.state = DECLARING_TARGETS
    mc.selected_squad = lord_unit
    cc.begin_charge_move()
    return st, lord_unit, prey, mc, cc, ctrl


c.eq("ChargeController exposes the hook as a LIST, so a second listener is a "
     "line and not a refactor",
     isinstance(ChargeController(all_tokens=[]).on_charge_move_finished, list), True)

st, lord_unit, prey, mc, cc, ctrl = charge_scene()
moved = lord_unit.models[0]
moved.y_in = 22.2                      # into Engagement Range of the Overlord
c.eq("the segment commits - this really is a legal charge move",
     mc.try_commit_segment(moved)[0], True)
script(3, 2, default=1)
cc.confirm_charge_move()
c.eq("the move was accepted", mc.errors, [])
c.eq("confirming a charge move fires Crimson Harvest", ctrl.is_busy, True)
ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()   # the 3 -> D3 band
ctrl.dice_manager.acknowledge(); ctrl.on_dice_acknowledged()   # the D3
c.eq("...end to end, through the real ChargeController: 2 mortal wounds",
     inflicted(ctrl), 2)

# ...and a DECLINED charge does not. This is why the hook is in
# confirm_charge_move() and not in _finish_charge(), which both paths reach.
st2, lord2, prey2, mc2, cc2, ctrl2 = charge_scene()
lord2.models[0].y_in = 22.2
mc2.try_commit_segment(lord2.models[0])
cc2.decline_charge_move()
c.eq("a DECLINED charge fires nothing - it did not end a Charge move, even "
     "though it reached _finish_charge() just as the confirmed one did",
     (ctrl2.is_busy, ctrl2.mortal_wound_session), (False, None))

# ...measured at the SEAM and not at the ability, because the ability alone is
# not evidence: decline_charge_move() calls cancel_move() first, so the models
# are back out of Engagement Range by then and Crimson Harvest would find no
# target for the WRONG reason. Recording listeners say which path really fired.
fired_ok, fired_declined = [], []
st3, lord3, prey3, mc3, cc3, _c3 = charge_scene()
cc3.on_charge_move_finished.append(lambda sq: fired_ok.append(sq.name))
lord3.models[0].y_in = 22.2
mc3.try_commit_segment(lord3.models[0])
cc3.confirm_charge_move()

st4, lord4, prey4, mc4, cc4, _c4 = charge_scene()
cc4.on_charge_move_finished.append(lambda sq: fired_declined.append(sq.name))
lord4.models[0].y_in = 22.2
mc4.try_commit_segment(lord4.models[0])
cc4.decline_charge_move()

c.eq("the seam itself fires on a confirmed charge", fired_ok, ["2 Skorpekh Lord 30"])
c.eq("...and NOT on a declined one - which is why it lives in "
     "confirm_charge_move() and not in _finish_charge()", fired_declined, [])
c.true("the hook is NOT in _finish_charge(), which the declined path also runs",
       "on_charge_move_finished" not in
       pathlib.Path("game/charge.py").read_text(encoding="utf-8")
       .split("def _finish_charge")[1].split("def _finish_reactive")[0])


# --- 10. wiring: does any of this reach main.py? ----------------------------
print("--- 10. wiring ---")

_main = pathlib.Path("main.py").read_text(encoding="utf-8")
c.true("the controller is built", "crimson_harvest_controller = CrimsonHarvestController(" in _main)
c.true("...and actually FED from the charge hook",
       "charge_controller.on_charge_move_finished.append(" in _main
       and "crimson_harvest_controller.on_charge_move_finished)" in _main)
c.true("...and its dice are acknowledged",
       "crimson_harvest_controller.on_dice_acknowledged()" in _main)

_fight = pathlib.Path("game/fight.py").read_text(encoding="utf-8")
c.true("United In Destruction is in FightController's adjuster chain",
       "united_in_destruction.adjusted_weapon(weapon, self.fighting_squad)" in _fight)
# Melee-only, pinned at the source rather than by building a shooting scene:
# the assurance is that game/shooting.py never reads this module at all.
c.eq("...and the ranged side never reads it - the ability is melee-only",
     "united_in_destruction" in
     pathlib.Path("game/shooting.py").read_text(encoding="utf-8"), False)

c.finish()
