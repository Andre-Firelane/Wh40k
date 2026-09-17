"""Ork Kill Rig (2026-09 codex, stage E3e): the datasheet, its transport line and
its two psychic abilities, driven through the real controllers.

  1. the datasheet: keywords against the corpus, statline, CORE fields, points
     tiers, the Devilfish-sized base (a standing user decision)
  2. the six weapons as printed
  3. transport: "12 BEAST SNAGGAS INFANTRY models" at 18.01 AND 18.02
  4. the psychic roll: its three gates, the Unstable Energies spend, a 1
     battle-shocks through the one door
  5. Warpath through a real FightController: offered at "selected to fight",
     [LETHAL HITS] and [PSYCHIC] in the chain, [PSYCHIC] dropping the Kill Rig's
     own Damaged -1 on the real Hit roll
  6. Beastscent through a real TransportController/SetupController: offered when
     a passenger is selected to disembark, +1 to wound against MONSTER/VEHICLE in
     BOTH attack steps, the shared budget
  7. the AI: both verdicts, and _handle_fight() stopping while the psychic roll
     is on the table
  8. wiring at the source and the retirements

Run: python test_ork_kill_rig.py

Built on testkit.py (see its docstring for the headless-harness traps).
"""

import ast
import io
import math
import os
import re
from types import SimpleNamespace

import testkit as tk
from testkit import DecisionManager, GameState, TurnTracker, build, line_up, script

from ai import agent_driver
from ai.mock_agent import MockAgent
from game import battle_shock, beastscent, formations, maps, psychic_roll, unstable_energies, warpath
from game.factions import orks
from game.factions.tau_empire import DEVILFISH, STRIKE_TEAM
from game.movement import MovementController
from game.setup import PLACING, SetupController
from game.transport import COMBAT, TACTICAL, TransportController
from game.turn import PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, PHASES
from game.weapons import MELEE, RANGED

ROOT = os.path.dirname(os.path.abspath(__file__))
ORK, FOE = "Player 2", "Player 1"
MAP = maps.get("map2")
maps.apply_to_config(MAP)

c = tk.Checks("Ork Kill Rig (2026-09 codex)")


def read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8").read()


def corpus_keywords(sheet_name):
    text = read(os.path.join("rules", "orks", sheet_name + ".md"))
    match = re.search(r"^KEYWORDS: (.+)$", text, re.MULTILINE)
    return tuple(k.strip() for k in match.group(1).split(";")) if match else None


def tracker(phase, owner, battle_round=2):
    tt = TurnTracker()
    tt.started = True
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = owner
    tt.set_active(owner)
    tt.battle_round = battle_round
    return tt


def weapon(model, name):
    return next((w for w in model.weapons if w.name == name), None)


# ===========================================================================
print("\n1. the datasheet")
# ===========================================================================
rig_squad = build(orks.KILL_RIG, ORK, name="2 Kill Rig 1")
rig = rig_squad.models[0]
p = rig.profile
c.eq("KEYWORDS match the printed line", tuple(orks.KILL_RIG.keywords), corpus_keywords("Kill Rig"))
c.eq("M10 T10 Sv3+ W16 Ld7+ OC5, invulnerable 6+",
     (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc, p.invulnerable_save),
     (10, 10, "3+", 16, "7+", 5, "6+"))
c.eq("CORE: Damaged 6, Feel No Pain 5+", (p.damaged_threshold, p.feel_no_pain), (6, "5+"))
c.true("...Deadly Demise D6 is a real roll", p.deadly_demise_notation is not None)
c.eq("MONSTER, PSYKER, BEAST SNAGGA, TRANSPORT, Waaagh!",
     (p.monster, p.psyker, p.beast_snagga, p.transport, p.waaagh), (True, True, True, True, True))
c.eq("Wurrboy: psyker level 1", p.psyker_level, 1)
c.eq("...carrying Beastscent and Warpath", (p.beastscent, p.warpath), (True, True))
c.true("the pre-codex Spirit of Gork flag is gone", not hasattr(p, "spirit_of_gork"))
c.eq("points: 175 for the 1st and 2nd, 185 from the 3rd",
     [orks.KILL_RIG.points_for(unit_index=i) for i in (1, 2, 3, 4)], [175, 175, 185, 185])
c.eq("base: the Devilfish's 2.1\" (user decision, not the 170x109mm oval)",
     (p.base_radius_in, build(DEVILFISH, name="DF").models[0].profile.base_radius_in), (2.1, 2.1))


# ===========================================================================
print("\n2. the six weapons")
# ===========================================================================
_rows = {
    "'Eavy Lobba": (RANGED, 48, 3, 6, 0, 2),
    "Stikka Kannon": (RANGED, 12, 1, 12, -2, 3),
    "Wurrtower": (RANGED, 24, 1, 12, -3, 6),
    "Butcha Boyz": (MELEE, 2, 4, 5, -1, 1),
    "Savage Horns and Hooves": (MELEE, 2, 4, 8, -1, 3),
    "Saw Blades": (MELEE, 2, 6, 10, -2, 2),
}
c.eq("carries exactly the six printed weapons", sorted(w.name for w in rig.weapons), sorted(_rows))
for _name, _row in _rows.items():
    _w = weapon(rig, _name)
    c.eq("%s: type/range/A/S/AP/D" % _name,
         (_w.weapon_type, _w.range_in, _w.attacks, _w.strength, _w.ap, _w.damage), _row)
_lobba, _wurr = weapon(rig, "'Eavy Lobba"), weapon(rig, "Wurrtower")
c.eq("'Eavy Lobba: flat A3 now, [BLAST 2], [INDIRECT FIRE]",
     (_lobba.attacks_notation, _lobba.blast, _lobba.indirect_fire), (None, 2, True))
c.eq("Wurrtower: flat A1 and D6, [HAZARDOUS] [PSYCHIC] [TORRENT]",
     (_wurr.attacks_notation, _wurr.damage_notation, _wurr.hazardous, _wurr.psychic, _wurr.torrent),
     (None, None, True, True, True))
c.eq("Stikka Kannon: [ANTI-MONSTER/VEHICLE 2+]", weapon(rig, "Stikka Kannon").anti,
     (("MONSTER", 2), ("VEHICLE", 2)))
c.eq("Saw Blades: [CLEAVE 1] and [EXTRA ATTACKS]",
     (weapon(rig, "Saw Blades").cleave, weapon(rig, "Saw Blades").extra_attacks), (1, True))
c.true("every melee weapon is [EXTRA ATTACKS] - rule 04.01 contests none",
       all(w.extra_attacks for w in rig.weapons if w.weapon_type == MELEE))
c.eq("Savage Horns and Hooves: WS4+ on the weapon, [LANCE]",
     (weapon(rig, "Savage Horns and Hooves").weapon_skill, weapon(rig, "Savage Horns and Hooves").lance),
     ("4+", True))


# ===========================================================================
print("\n3. transport: 12 BEAST SNAGGAS INFANTRY models")
# ===========================================================================
def fits(passenger_sheet, name, composition_index=0):
    """(18.01 errors, 18.02 answer) for `passenger` boarding a Kill Rig."""
    st = GameState()
    token = build(orks.KILL_RIG, ORK, name="2 Kill Rig T").models[0]
    token.x_in, token.y_in = 20.0, 20.0
    pax = build(passenger_sheet, ORK, name=name, composition_index=composition_index)
    spacing = 0.6
    line_up(pax, x=20.0 - (len(pax.models) - 1) * spacing / 2.0, y=23.0, spacing=spacing)
    st.add_token(token)
    for m in pax.models:
        st.add_token(m)
    mc = MovementController(all_tokens=st.tokens)
    mc.moved_squad_ids.add(pax)
    tc = TransportController(None, st, st.tokens, mc, None, None)
    return formations.embark_errors(pax, token), tc.can_embark(pax, token)


c.eq("capacity 12, INFANTRY and BEAST SNAGGA required",
     (p.transport_capacity, p.transport_requires_infantry, p.transport_requires), (12, True, ("beast_snagga",)))
c.eq("10 Beast Snagga Boyz fit, at 18.01 and 18.02", fits(orks.BEAST_SNAGGA_BOYZ, "2 BSB 1"), ([], True))
_errs, _ok = fits(orks.BOYZ, "2 Boyz 1")
c.true("plain Boyz are refused at both (INFANTRY, not BEAST SNAGGA)", bool(_errs) and not _ok)
_errs, _ok = fits(orks.BEAST_SNAGGA_BOYZ, "2 BSB 20", composition_index=1)
c.true("20 Beast Snagga Boyz are refused at both (20 > 12)", bool(_errs) and not _ok)
_saved = orks.KILL_RIG.model_lines[0].profile_cls.transport_requires
orks.KILL_RIG.model_lines[0].profile_cls.transport_requires = ()
c.eq("A/B: without the BEAST SNAGGA requirement, plain Boyz would fit",
     fits(orks.BOYZ, "2 Boyz 2"), ([], True))
orks.KILL_RIG.model_lines[0].profile_cls.transport_requires = _saved


# ===========================================================================
print("\n4. the psychic roll")
# ===========================================================================
def pr_scene(battle_round=2):
    dice = tk.RecordingDice()
    tt = tracker(PHASE_FIGHT, ORK, battle_round=battle_round)
    log = tk.Log()
    return SimpleNamespace(dice=dice, tt=tt, log=log,
                           ctrl=psychic_roll.PsychicRollController(dice, tt, log),
                           rig=build(orks.KILL_RIG, ORK, name="2 Kill Rig 1"))


_shocked = []
battle_shock.add_became_battle_shocked_listener(lambda sq, source: _shocked.append((sq.name, source)))
P = pr_scene()
c.true("a fresh Kill Rig may roll", P.ctrl.can_roll(P.rig))
script(1)
c.true("roll: spends the level and throws a visible D6", P.ctrl.roll(P.rig, "Warpath"))
c.eq("...one D6, the budget spent this round",
     (P.dice.is_pending, P.dice.sides, unstable_energies.spent_this_round(P.rig, 2)), (True, 6, 1))
c.eq("...and not yet shocked before the die is read", P.rig.battle_shocked, False)
c.true("a second ability is refused while the D6 is on the table",
       "another roll" in (P.ctrl.why_not(build(orks.KILL_RIG, ORK, name="2 Kill Rig 2")) or ""))
P.dice.acknowledge()
c.true("acknowledged", P.ctrl.on_dice_acknowledged())
c.eq("a 1 battle-shocks it, through the one door (listeners told)",
     (P.rig.battle_shocked, _shocked[-1:]), (True, [("2 Kill Rig 1", "a psychic roll (Warpath)")]))
c.true("...and the log says so", P.log.has("rolled a 1 for Warpath and is battle-shocked"))
c.true("a battle-shocked unit may not roll", "battle-shocked" in (P.ctrl.why_not(P.rig) or ""))

P = pr_scene()
script(1)
P.ctrl.roll(P.rig, "Warpath")
script(5)
P.dice.roll(count=1, sides=6, label="Hit Roll: something else")
P.dice.acknowledge()
P.ctrl.on_dice_acknowledged()
c.eq("a psychic roll REPLACED by another roll resolves on its own face (the 1), not the other die",
     (P.rig.battle_shocked, P.log.has("[psychic roll]")), (True, True))

P = pr_scene()
script(4)
P.ctrl.roll(P.rig, "Warpath")
P.dice.acknowledge()
P.ctrl.on_dice_acknowledged()
c.eq("a 4 leaves it unshocked", P.rig.battle_shocked, False)
c.true("the psyker level is spent for the battle round", "Unstable Energies" in (P.ctrl.why_not(P.rig) or ""))
P.tt.battle_round = 3
c.true("...and back the next battle round", P.ctrl.can_roll(P.rig))
c.true("a unit with no psyker level may never roll",
       not P.ctrl.can_roll(build(orks.BOYZ, ORK, name="2 Boyz 1")))


# ===========================================================================
print("\n5. Warpath through a real FightController")
# ===========================================================================
def wp_scene(auto=(), verdict=None, wounds=None, target_sheet=None):
    scene = tk.fight_scene(orks.KILL_RIG, target_sheet or orks.BOYZ, attacker_owner=ORK)
    fc = scene["fight"]
    scene["turn"].battle_round = 2
    pr = psychic_roll.PsychicRollController(scene["dice"], scene["turn"], scene["log"])
    fc.warpath = warpath.WarpathController(pr, decision_manager=scene["decision"], game_log=scene["log"],
                                           auto_players=auto, verdict=verdict)
    if wounds is not None:
        scene["attacker"].models[0].current_wounds = wounds
    return SimpleNamespace(scene=scene, fc=fc, pr=pr, rig=scene["attacker"], target=scene["target"],
                           dice=scene["dice"], dm=scene["decision"], log=scene["log"])


W = wp_scene()
W.fc.select_to_fight(W.rig)
c.eq("selected to fight: the human is asked, Roll or Decline",
     (W.dm.player, tk.options_of(W.dm)), (ORK, [warpath.ROLL_LABEL, warpath.DECLINE_LABEL]))
c.true("...no die yet", not W.dice.is_pending)
script(5)
tk.pick_option(W.dm, "Make the psychic roll")
c.eq("yes: the grant is up and the psychic D6 is on the table",
     (warpath.is_active(W.rig), W.dice.is_pending, "Psychic roll: Warpath" in (W.dice.label or "")),
     (True, True, True))
_saw = weapon(W.rig.models[0], "Saw Blades")
_adj = W.fc._adjusted_weapon([(W.rig.models[0], _saw)], W.target)
c.eq("the chain gives its melee weapons [LETHAL HITS] and [PSYCHIC]", (_adj.lethal_hits, _adj.psychic), (True, True))
c.eq("...on a copy - the carried weapon is untouched", (_saw.lethal_hits, _saw.psychic), (False, False))
_lobba_adj = warpath.adjusted_weapon(weapon(W.rig.models[0], "'Eavy Lobba"), W.rig)
c.true("...and a ranged weapon gets nothing", not getattr(_lobba_adj, "lethal_hits", False))
W.dice.acknowledge()
W.pr.on_dice_acknowledged()
c.eq("a 5: not shocked, grant kept", (W.rig.battle_shocked, warpath.is_active(W.rig)), (False, True))


def hit_threshold(with_warpath):
    """The Saw Blades' real Hit roll for a Kill Rig on 5 wounds (Damaged 6: -1
    to hit): its threshold and label, and how many of an all-3s roll the hit
    STEP counted as hits - the step computes its own threshold, so both ends
    have to be asked."""
    S = wp_scene(auto=(ORK,), verdict=lambda squad: with_warpath, wounds=5)
    script(6)
    S.fc.select_to_fight(S.rig)
    if S.dice.is_pending:
        S.dice.acknowledge()
        S.pr.on_dice_acknowledged()
    if S.fc.target_squad is None:
        S.fc.choose_target_squad(S.target)
    key = next(k for k, label, *_rest in S.fc.weapon_eligibility() if "Saw Blades" in str(label))
    script(*([3] * 12))
    S.fc.choose_weapon(key)
    threshold, label = S.dice.success_threshold, S.dice.label
    S.dice.acknowledge()
    S.fc.on_dice_acknowledged()
    line = S.log.find("hit roll") or ""
    match = re.search(r": (\d+) hit\(s\)", line)
    return threshold, label, int(match.group(1)) if match else None


_plain_threshold, _plain_label, _plain_hits = hit_threshold(False)
_wp_threshold, _wp_label, _wp_hits = hit_threshold(True)
c.eq("(live) a damaged Kill Rig hits on 4+ with its WS3+ Saw Blades (Damaged 6: -1)", _plain_threshold, 4)
c.eq("[PSYCHIC] from Warpath drops that worsening modifier: 3+ on the REAL Hit roll", _wp_threshold, 3)
c.true("...the Hit roll label no longer names Damaged", "Damaged" in _plain_label and "Damaged" not in _wp_label)
c.eq("...and the hit STEP agrees: all-3s miss without it and hit with it", (_plain_hits, _wp_hits > 0), (0, True))
_D = wp_scene(auto=(ORK,), verdict=lambda squad: True, wounds=5)
_D.fc.select_to_fight(_D.rig)
c.true("(live) the grant is up for the direct _hit_modifiers() checks", warpath.is_active(_D.rig))
c.true("_hit_modifiers() without a weapon drops nothing (every caller hands the adjusted one)",
       any(m.amount > 0 for m in _D.fc._hit_modifiers(_D.rig.models[0], _D.target)))
c.true("...with the adjusted Saw Blades it drops the Damaged -1",
       not any(m.amount > 0 for m in _D.fc._hit_modifiers(
           _D.rig.models[0], _D.target,
           _D.fc._adjusted_weapon([(_D.rig.models[0], weapon(_D.rig.models[0], "Saw Blades"))], _D.target))))

W = wp_scene(auto=(ORK,), verdict=lambda squad: True)
script(3)
W.fc.select_to_fight(W.rig)
c.eq("AI: a yes rolls with no prompt", (W.dm.is_pending, W.dice.is_pending, warpath.is_active(W.rig)),
     (False, True, True))
W = wp_scene(auto=(ORK,), verdict=lambda squad: False)
W.fc.select_to_fight(W.rig)
c.eq("AI: a no rolls nothing", (W.dice.is_pending, warpath.is_active(W.rig)), (False, False))
W = wp_scene()
W.rig.battle_shocked = True
W.fc.select_to_fight(W.rig)
c.true("not offered to a battle-shocked Kill Rig", not W.dm.is_pending)
W = wp_scene()
unstable_energies.spend(W.rig, 1, 2)
W.fc.select_to_fight(W.rig)
c.true("not offered once its psyker level is spent this round", not W.dm.is_pending)
W = wp_scene()
W.fc.warpath.offer(W.scene["target"])
c.true("not offered to a unit without the ability", not W.dm.is_pending)
W = wp_scene(auto=(ORK,), verdict=lambda squad: True)
W.fc.select_to_fight(W.rig)
warpath.reset_phase([W.rig])
c.true("reset_phase ends the grant", not warpath.is_active(W.rig))


# ===========================================================================
print("\n6. Beastscent through a real TransportController")
# ===========================================================================
def bs_scene(phase=PHASE_MOVEMENT, turn_owner=ORK, auto=(), verdict=None, transport_sheet=None):
    st = GameState()
    tt = tracker(phase, turn_owner)
    carrier = build(transport_sheet or orks.KILL_RIG, ORK, name="2 %s 1" % (transport_sheet or orks.KILL_RIG).name)
    token = carrier.models[0]
    token.x_in, token.y_in = 30.0, 22.0
    st.add_token(token)
    bsb = build(orks.BEAST_SNAGGA_BOYZ, ORK, name="2 Beast Snagga Boyz 1")
    bsb.embarked_in = token
    st.embarked_squads.append(bsb)
    setup = SetupController(st, obstacles=[], all_tokens=st.tokens,
                            board_width_in=MAP.width_in, board_height_in=MAP.height_in)
    mc = MovementController([], tk.Log(), turn_owner, tk.DiceManager(), tt, st.tokens)
    dice = tk.RecordingDice()
    tc = TransportController(setup, st, st.tokens, mc, None, dice, turn_tracker=tt,
                             board_width_in=MAP.width_in, board_height_in=MAP.height_in)
    dm, log = DecisionManager(), tk.Log()
    pr = psychic_roll.PsychicRollController(dice, tt, log)
    ctrl = beastscent.BeastscentController(pr, turn_tracker=tt, decision_manager=dm, game_log=log,
                                           auto_players=auto, verdict=verdict)
    tc.on_disembark_started.append(ctrl.on_disembark_started)
    return SimpleNamespace(st=st, tt=tt, carrier=carrier, token=token, bsb=bsb, setup=setup, tc=tc,
                           dice=dice, dm=dm, log=log, pr=pr, ctrl=ctrl)


B = bs_scene()
B.tc.start_disembark(B.bsb)
c.eq("(live) the disembark placement is open", (B.setup.state, B.tc.is_disembarking(B.bsb)), (PLACING, True))
c.eq("a passenger selected to disembark in YOUR Movement phase: the Kill Rig's owner is asked",
     (B.dm.player, tk.options_of(B.dm)), (ORK, [beastscent.ROLL_LABEL, beastscent.DECLINE_LABEL]))
script(2)
tk.pick_option(B.dm, "Make the psychic roll")
c.eq("yes: the PASSENGER has the grant, the KILL RIG made the roll and spent its level",
     (beastscent.is_active(B.bsb), B.dice.is_pending, unstable_energies.spent_this_round(B.carrier, 2),
      unstable_energies.spent_this_round(B.bsb, 2)), (True, True, 1, 0))
B.dice.acknowledge()
B.pr.on_dice_acknowledged()
c.eq("a 2: nobody shocked", (B.carrier.battle_shocked, B.bsb.battle_shocked), (False, False))
c.eq("...and the placement still stands for the human", B.setup.state, PLACING)

B = bs_scene()
B.tc.start_disembark(B.bsb)
script(1)
tk.pick_option(B.dm, "Make the psychic roll")
B.dice.acknowledge()
B.pr.on_dice_acknowledged()
c.eq("a 1 battle-shocks the KILL RIG, not the passenger", (B.carrier.battle_shocked, B.bsb.battle_shocked),
     (True, False))

B = bs_scene()
B.tc.start_disembark(B.bsb)
tk.pick_option(B.dm, "Decline")
c.eq("Decline: no grant, no roll, no spend",
     (beastscent.is_active(B.bsb), B.dice.is_pending, unstable_energies.spent_this_round(B.carrier, 2)),
     (False, False, 0))

B = bs_scene(turn_owner=FOE)
B.tc.start_disembark(B.bsb)
c.true("not in the OPPONENT's Movement phase", not B.dm.is_pending)
B = bs_scene(phase=PHASE_SHOOTING)
B.tc.start_disembark(B.bsb)
c.true("not outside the Movement phase", not B.dm.is_pending)
B = bs_scene()
B.carrier.battle_shocked = True
B.tc.start_disembark(B.bsb)
c.true("not while the Kill Rig is battle-shocked", not B.dm.is_pending)
B = bs_scene()
unstable_energies.spend(B.carrier, 1, 2)
B.tc.start_disembark(B.bsb)
c.true("not once Warpath has spent the level this round (one shared budget)", not B.dm.is_pending)
B = bs_scene(transport_sheet=orks.BATTLEWAGON)
# A PSYKER transport, or the psychic roll's own psyker-level gate refuses first and
# the ability check is never the one that holds. A subclass on THIS token only -
# UnitProfile is a class attribute shared by every Battlewagon.
B.token.profile = type("PsykerWagon", (type(B.token.profile),), {"psyker_level": 1})()
c.true("(live) that Battlewagon could make a psychic roll", B.pr.can_roll(B.carrier))
B.tc.start_disembark(B.bsb)
c.true("a PSYKER TRANSPORT without Beastscent asks nothing", not B.dm.is_pending)
B = bs_scene(auto=(ORK,), verdict=lambda t, p: True)
script(6)
B.tc.start_disembark(B.bsb)
c.eq("AI: a yes rolls with no prompt", (B.dm.is_pending, B.dice.is_pending, beastscent.is_active(B.bsb)),
     (False, True, True))
B = bs_scene(auto=(ORK,), verdict=lambda t, p: False)
B.tc.start_disembark(B.bsb)
c.eq("AI: a no does nothing", (B.dice.is_pending, beastscent.is_active(B.bsb)), (False, False))

# The same budget, the other way round: a Kill Rig that used Beastscent is not
# offered Warpath in its Fight phase of that battle round.
W = wp_scene()
unstable_energies.spend(W.rig, beastscent.BEASTSCENT_PSYCHIC_LEVEL, 2)
W.fc.select_to_fight(W.rig)
c.true("Beastscent spent: Warpath is not offered that round", not W.dm.is_pending)

# +1 to wound against MONSTER/VEHICLE, in BOTH attack steps.
_S = tk.shooting_scene(orks.BEAST_SNAGGA_BOYZ, DEVILFISH, attacker_owner=ORK, gap=8.0)
_SC = _S["shooting"]
_SC.active_squad = _S["attacker"]


def beastscent_mods(mods):
    return [m.amount for m in mods if m.source == beastscent.BEASTSCENT_NAME]


c.eq("(live) shooting: no grant, no bonus", beastscent_mods(_SC._wound_modifiers(_S["target"])), [])
_S["attacker"].beastscent_active = True
c.eq("shooting at a VEHICLE: +1 to wound (-1 on the threshold)",
     beastscent_mods(_SC._wound_modifiers(_S["target"])), [-1])
c.eq("...not at an INFANTRY unit", beastscent_mods(_SC._wound_modifiers(build(STRIKE_TEAM, FOE, name="1 ST 1"))), [])
_F = tk.fight_scene(orks.BEAST_SNAGGA_BOYZ, orks.KILL_RIG, attacker_owner=ORK)
_FC = _F["fight"]
_FC.fighting_squad = _F["attacker"]
_choppa = next(w for w in _F["attacker"].models[1].weapons if w.weapon_type == MELEE)
c.eq("(live) fight: no grant, no bonus", beastscent_mods(_FC._wound_modifiers(_choppa, _F["target"])), [])
_F["attacker"].beastscent_active = True
c.eq("fight against a MONSTER: +1 to wound too", beastscent_mods(_FC._wound_modifiers(_choppa, _F["target"])), [-1])
beastscent.clear_turn([_F["attacker"]])
c.true("clear_turn ends it", not beastscent.is_active(_F["attacker"]))


# ===========================================================================
print("\n7. the AI")
# ===========================================================================
class _Area:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def distance_to_model(self, model):
        return max(0.0, math.hypot(model.x_in - self.x, model.y_in - self.y) - model.radius_in)


_ai_state = GameState()
_ai_rig = build(orks.KILL_RIG, ORK, name="2 Kill Rig 1")
_ai_rig.models[0].x_in, _ai_rig.models[0].y_in = 30.0, 22.0
_ai_state.add_token(_ai_rig.models[0])
_ai_pax = build(orks.BEAST_SNAGGA_BOYZ, ORK, name="2 BSB 1")
c.true("Warpath: rolls with no objective at stake", agent_driver.warpath_verdict(_ai_state, _ai_rig))
_ai_state.objectives = [SimpleNamespace(terrain_area=_Area(31.0, 22.0), name="obj")]
c.true("...but not on an objective (a 1 makes its OC 0)", not agent_driver.warpath_verdict(_ai_state, _ai_rig))
c.true("Beastscent: not on an objective either",
       not agent_driver.beastscent_verdict(_ai_state, _ai_rig.models[0], _ai_pax, TACTICAL))
_ai_state.objectives = []
c.true("Beastscent: nothing MONSTER/VEHICLE in reach - keep the level",
       not agent_driver.beastscent_verdict(_ai_state, _ai_rig.models[0], _ai_pax, TACTICAL))
_ai_foe = build(STRIKE_TEAM, FOE, name="1 ST 1")
line_up(_ai_foe, x=30.0, y=30.0)
for _m in _ai_foe.models:
    _ai_state.add_token(_m)
c.true("...an INFANTRY unit in reach changes nothing",
       not agent_driver.beastscent_verdict(_ai_state, _ai_rig.models[0], _ai_pax, TACTICAL))
_ai_df = build(DEVILFISH, FOE, name="1 Devilfish 1")
_ai_df.models[0].x_in, _ai_df.models[0].y_in = 30.0, 34.0
_ai_state.add_token(_ai_df.models[0])
c.true("a VEHICLE within 15\": roll", agent_driver.beastscent_verdict(_ai_state, _ai_rig.models[0], _ai_pax, TACTICAL))
c.true("...never for a Combat disembark (its hazard roll would replace the psychic one)",
       not agent_driver.beastscent_verdict(_ai_state, _ai_rig.models[0], _ai_pax, COMBAT))
_ai_df.models[0].y_in = 60.0
c.true("...and not when the VEHICLE is out of reach",
       not agent_driver.beastscent_verdict(_ai_state, _ai_rig.models[0], _ai_pax, TACTICAL))

# _handle_fight() must stop after select_to_fight() while the psychic roll is on
# the table - its next step throws the Hit roll into the same one-roll slot.
W = wp_scene(auto=(ORK,), verdict=lambda squad: True)
script(4)
agent_driver._handle_fight(MockAgent(), agent_driver.AIMemory(), ORK, W.scene["state"].tokens, W.fc,
                           None, None, None)
c.eq("AI fight: selected, and the psychic roll is still the pending roll (no Hit roll thrown over it)",
     (W.fc.fighting_squad is W.rig, W.dice.is_pending, "Psychic roll" in (W.dice.label or "")), (True, True, True))


# ===========================================================================
print("\n8. wiring and retirements")
# ===========================================================================
MAIN = read("main.py")
TREE = ast.parse(MAIN)


def calls(tree, text):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n) == text]


c.eq("main.py routes the psychic roll's acknowledgement",
     len(calls(TREE, "psychic_roll_controller.on_dice_acknowledged()")), 1)
c.eq("...hands FightController a WarpathController",
     sum(1 for n in ast.walk(TREE) if isinstance(n, ast.keyword) and n.arg == "warpath"
         and isinstance(n.value, ast.Call) and ast.unparse(n.value.func) == "WarpathController"), 1)
c.eq("...clears Warpath with the per-phase grants",
     len(calls(TREE, "warpath.reset_phase({t.squad for t in state.tokens if t.squad is not None})")), 1)
c.eq("...listens for a disembark being started",
     len(calls(TREE, "transport_controller.on_disembark_started.append(beastscent_controller.on_disembark_started)")), 1)
c.true("...and injects both AI verdicts", "warpath_verdict(state, squad)" in MAIN and "beastscent_verdict(" in MAIN)
_sweeps = [n for n in ast.walk(TREE) if isinstance(n, ast.For) and ast.unparse(n.iter) == "state.all_squads()"
           and any(isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "squad.charge_locked_until_end_of_turn"
                   for s in n.body)]
c.true("Beastscent ends with the turn, swept over every unit",
       bool(_sweeps) and any(ast.unparse(s) == "squad.beastscent_active = False" for s in _sweeps[0].body))
_fight = read(os.path.join("game", "fight.py"))
c.true("FightController offers Warpath at selection", "self.warpath.offer(squad)" in _fight)
c.true("...has Warpath in its adjuster chain", "warpath.adjusted_weapon(weapon, self.fighting_squad)" in _fight)
c.true("...and reads Beastscent in its wound modifiers",
       "beastscent.wound_modifiers(self.fighting_squad, target_squad)" in _fight)
c.true("ShootingController reads Beastscent in its wound modifiers",
       "beastscent.wound_modifiers(self.active_squad, target_squad)" in read(os.path.join("game", "shooting.py")))
c.true("start_disembark() fires on_disembark_started",
       "for listener in list(self.on_disembark_started or ()):" in read(os.path.join("game", "transport.py")))
from game import activation_state  # noqa: E402
c.true("both grants survive a save (SQUAD_FLAGS)",
       {"warpath_active", "beastscent_active"} <= set(activation_state.SQUAD_FLAGS))
c.true("game/spirit_of_gork.py is gone", not os.path.exists(os.path.join(ROOT, "game", "spirit_of_gork.py")))
c.true("...and no Squad field or flag of it remains",
       "spirit_of_gork" not in read(os.path.join("game", "squad.py"))
       and not any("spirit_of_gork" in f for f in activation_state.SQUAD_FLAGS))
c.true("Unstable Energies is no longer dormant", "DORMANT" not in read(os.path.join("game", "unstable_energies.py")))

c.finish()
