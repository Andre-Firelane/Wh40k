"""Runtime proof that the SHIPPED Mecha Orks list (armies/orks.json) makes stages
G1-G5 reachable in a real game - nothing built, nothing staged.

Every other verify_*.py in this repo BUILDS the units it needs and SETS the
detachment config itself, because until now no list fielded those detachments.
This one does the opposite and that is its whole point: it runs selfplay.py's
real main() loop with the Orks as Player 1 and the Necrons as Player 2, and asks
main()'s live objects what the LIST alone produced.

  A. THE LIST ON THE TABLE: twelve units at 1990 points, the three detachments
     written into config by game/detachments.py, and the four Enhancements on
     the four units that bought them.
  B. THE WARLORD: Ghazghkull carries the flag on main()'s board (nothing else
     does), and main()'s own Da Boss controller pays his 1CP for a battle round.
  C. THE THREE TRANSPORTS the list declares: their passengers are aboard after
     the pre-game sequence, and main()'s GameState says so.
  D. THE ENHANCEMENTS REACH THEIR RULES on main()'s controllers: the Gunwagon
     ignores cover because the Big Mek it carries has Targetin' Gizmos; the
     Battlewagon draws Intimidating Motivation because a Warboss rides it with
     Boss Boomer aboard; the ten-Boy mob has a 4+ Save from 'Ardboyz; and the
     Bigboss swings with Ferocious Show-off's +2 Attacks in a mob this size.
  E. DA HUNT IS ON: a Beast Snagga unit's gun gains +1 AP against a Necron
     VEHICLE on main()'s ShootingController.

D and E are the list-level version of what test_ork_*.py already pin unit by
unit. What they add is that the ROSTER puts the right model in the right
transport: Targetin' Gizmos only does anything because this list seats the Big
Mek in the Gunwagon, and Boss Boomer only because it seats a Warboss in the
Battlewagon. Neither is a coincidence to leave unstated - both are written down
in armies/orks.json's own note.

STAGED, and it is deliberately almost nothing: the clock for D (the panel draws
in the Movement phase), CP top-ups, and one Necron VEHICLE built for E when the
Necron list happens to field none within reach. The army, its detachments, its
Enhancements, its Warlord and its transports all come from the file.

--neutralize takes away the one thing the list does that config cannot:
game/detachments.py's write of the three settings. Every gated rule then goes
dark while the same twelve units stand on the same board - which is the claim
this script makes, stated as its own A/B.

Usage:  python verify_mecha_orks_list.py [map2] [frames]
        python verify_mecha_orks_list.py map2 --neutralize
"""

import os
import runpy
import sys

import pygame

from game.decision import DecisionManager
from game import (config, detachments, enh_ardboyz,
                  enh_boss_boomer, enh_ferocious_show_off, enh_targetin_gizmos,
                  enhancements, save_characteristic)
from game.factions import build_squad
from game.factions.necrons import GHOST_ARK
from game.turn import PHASES, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker
from game.weapons import MELEE, RANGED

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")
    # The list still fields everything; only its detachments stop being declared.
    detachments.apply_to_config = lambda *a, **k: None

# THE ORKS ARE PLAYER 2 - the side selfplay's MockAgent plays, and the side
# this list is fielded on (`--army2 orks`, see test_player2_army.py). It matters
# for section C: the transports a list declares are a HINT that the deployment
# AI honours (ai/deployment_ai.py's _transport_affinity), and a human deploys by
# hand. With the Orks on Player 1 nothing ever embarked - which is a fact about
# who deploys, not about the list.
ORK, FOE = "Player 2", "Player 1"
STALE_FRAMES = 30
state = {"frames": 0, "tracker": None, "done": None, "declined": [],
         "stale": None, "stale_since": 0}


def _main_locals():
    frame = sys._getframe(1)
    while frame is not None and frame.f_code.co_name != "main":
        frame = frame.f_back
    return frame.f_locals if frame is not None else None


_real_tracker_init = TurnTracker.__init__


def tracker_init(self, *args, **kwargs):
    _real_tracker_init(self, *args, **kwargs)
    state["tracker"] = self


TurnTracker.__init__ = tracker_init


def _decline_stale_human_prompt(decisions):
    """Player 1 is the ORKS here and nobody answers for them - an offer left
    standing would keep _quiet() False for the whole run, which is exactly how
    the first version of this script measured nothing for 6000 frames."""
    if decisions is None or not decisions.is_pending or decisions.player != ORK:
        state["stale"] = None
        return
    key = (id(decisions._queue[0]), decisions.prompt or "")
    if state["stale"] != key:
        state["stale"], state["stale_since"] = key, state["frames"]
        return
    if state["frames"] - state["stale_since"] >= STALE_FRAMES:
        state["declined"].append((decisions.prompt or "")[:60])
        decisions.choose(len(decisions.options) - 1)
        state["stale"] = None


def _alive(squad):
    return [m for m in squad.models if not m.is_dead()]


def _named(squads, needle):
    """The one unit whose name ENDS with `needle` (after the owner prefix) or
    starts with it after the prefix - never a substring match: "Boyz 2" is a
    substring of "Beast Snagga Boyz 2 + Beastboss + Weirdboy", and the first
    version of this script measured that unit and reported 'Ardboyz as dead."""
    for squad in squads:
        rest = squad.name.split(" ", 1)[1] if " " in squad.name else squad.name
        if rest == needle or rest.startswith(needle + " "):
            return squad
    return None


def _ready(L):
    """The first frame after the pre-game sequence has handed over - the army is
    on the table exactly as the LIST asked for it, and nobody has played a turn.

    NOT "the first quiet frame": measuring later measures the AI's play, not the
    list. The transports are the case that makes the difference - all three load
    during Declare Battle Formations (rule 18.01), and the AI then unloads two of
    them in its first Movement phase, which is its decision to make."""
    pregame_controller = L.get("pregame_controller")
    return (L["setup_controller"].state != "placing"
            and pregame_controller is not None and not pregame_controller.is_active)


def _set_phase(phase, owner=ORK):
    tracker = state["tracker"]
    tracker.phase_index = PHASES.index(phase)
    tracker.turn_owner = owner
    tracker.set_active(owner)


def measure(L):
    st = L["state"]
    squads = [s for s in st.all_squads() if s.owner == ORK and _alive(s)]
    out = {"units": sorted(s.name for s in squads),
           "points": sum(s.points or 0 for s in squads)}

    # --- A. the list on the table ------------------------------------------
    out["settings"] = sorted(s for s in detachments.all_settings() if ORK in (getattr(config, s) or ()))
    wagon = _named(squads, "Battlewagon")
    gun = _named(squads, "Gunwagon")
    mob20 = _named(squads, "Boyz 1")
    mob10 = _named(squads, "Boyz 2")
    bsb_plain = _named(squads, "Beast Snagga Boyz 1")
    mega = _named(squads, "Meganobz 1")
    out["measured"] = {"wagon": getattr(wagon, "name", None), "gunwagon": getattr(gun, "name", None),
                       "mob20": getattr(mob20, "name", None), "mob10": getattr(mob10, "name", None),
                       "bsb": getattr(bsb_plain, "name", None), "foil": None}
    out["enhancements"] = {
        "Boss Boomer": bool(wagon is not None and enhancements.is_active(wagon, enh_boss_boomer.BOSS_BOOMER)),
        "Targetin' Gizmos": bool(gun is not None and enhancements.is_active(
            gun, enh_targetin_gizmos.TARGETIN_GIZMOS)),
        "'Ardboyz": bool(mob10 is not None and enhancements.is_active(mob10, enh_ardboyz.ARDBOYZ)),
        "Ferocious Show-off": bool(mob20 is not None and enhancements.is_active(
            mob20, enh_ferocious_show_off.FEROCIOUS_SHOW_OFF)),
    }

    # --- B. the Warlord -----------------------------------------------------
    warlords = [s.name for s in squads if any(getattr(m, "warlord", False) for m in _alive(s))]
    out["warlords"] = warlords
    cp_before = L["command_points"].cp[ORK]
    L["da_boss_rule_controller"].sync_battle_round(99)   # a round nobody has been paid for
    out["da_boss_cp"] = L["command_points"].cp[ORK] - cp_before

    # --- C. the transports the list declares --------------------------------
    out["reserves"] = sorted(getattr(sq, "name", "?") for sq in getattr(st, "reserves", []) or [])
    out["embarked"] = sorted(
        "%s -> %s" % (passenger.name, getattr(carrier, "squad", carrier).name)
        for carrier, riders in _carriers(st) for passenger in riders)

    # --- D. the Enhancements reach their rules ------------------------------
    sc = L["shooting_controller"]
    foes = [s for s in st.all_squads() if s.owner == FOE and _alive(s)]
    target = next((s for s in foes
                   if not any(m.profile.vehicle or m.profile.monster for m in _alive(s))), None)
    out["measured"]["foil"] = getattr(target, "name", None)
    if gun is not None and target is not None:
        model = _alive(gun)[0]
        weapon = next((w for w in model.weapons if w.weapon_type == RANGED), None)
        saved, real = sc.active_squad, sc._has_benefit_of_cover
        try:
            sc.active_squad = gun
            sc._has_benefit_of_cover = lambda shooter_model, target_squad: True
            out["gizmos_ignores_cover"] = bool(sc._adjusted_weapon([(model, weapon)], target).ignores_cover)
            out["gizmos_cover_modifiers"] = [
                m.source for m in sc._hit_modifiers({"pairs": [(model, weapon)], "target_squad": target})
                if m.source == "Benefit of Cover"]
        finally:
            sc.active_squad, sc._has_benefit_of_cover = saved, real
    _set_phase(PHASE_MOVEMENT, ORK)
    out["boomer_bearers"] = [
        m.profile.name for m in L["intimidating_motivation_controller"].bearer_models(wagon)
    ] if wagon is not None else []
    if mob10 is not None:
        out["ardboyz_save"] = save_characteristic.armour_save(_alive(mob10)[0])
    if mob20 is not None:
        bigboss = next((m for m in _alive(mob20) if m.profile.name == "Bigboss"), None)
        boy = next((m for m in _alive(mob20) if m.profile.name == "Boy"), None)
        fc = L["fight_controller"]
        if bigboss is not None and boy is not None:
            printed = next((w.attacks for w in bigboss.weapons if w.weapon_type == MELEE), None)
            out["show_off"] = (printed, _attacks(fc, mob20, bigboss, target),
                               _attacks(fc, mob20, boy, target), len(_alive(mob20)))

    # --- E. Da Hunt is On ---------------------------------------------------
    vehicle = next((s for s in st.all_squads() if s.owner == FOE and _alive(s)
                    and any(m.profile.vehicle or m.profile.monster for m in _alive(s))), None)
    if vehicle is None:
        vehicle = build_squad(GHOST_ARK, FOE, name="2 Ghost Ark (probe)")
    if bsb_plain is not None:
        model = next((m for m in _alive(bsb_plain) if any(w.weapon_type == RANGED for w in m.weapons)), None)
        weapon = next((w for w in model.weapons if w.weapon_type == RANGED), None)
        saved = sc.active_squad
        try:
            sc.active_squad = bsb_plain
            _set_phase(PHASE_SHOOTING, ORK)
            out["da_hunt"] = (weapon.ap, sc._adjusted_weapon([(model, weapon)], vehicle).ap,
                              sc._adjusted_weapon([(model, weapon)], target).ap)
        finally:
            sc.active_squad = saved
    return out


def _attacks(fc, squad, model, target):
    weapon = next((w for w in model.weapons if w.weapon_type == MELEE), None)
    fc.fighting_squad = squad
    return fc._adjusted_weapon([(model, weapon)], target).attacks


def _carriers(st):
    """(carrier token, passengers) for every transport that is carrying."""
    out = []
    for squad in st.all_squads():
        for model in squad.models:
            riders = [p for p in st.all_squads() if getattr(p, "embarked_in", None) is model]
            if riders:
                out.append((model, riders))
    return out


def flip(*args, **kwargs):
    state["frames"] += 1
    tracker = state["tracker"]
    if state["done"] is None and tracker is not None and getattr(tracker, "started", False):
        L = _main_locals()
        if L is not None and "fight_controller" in L and "proactive_stratagems" in L:
            _decline_stale_human_prompt(L.get("decision_manager"))
        if (L is not None and "fight_controller" in L and "proactive_stratagems" in L
                and _ready(L)):
            L["command_points"].cp[ORK] = max(L["command_points"].cp.get(ORK, 0), 3)
            state["done"] = measure(L)
            raise SystemExit(0)
    return _real_flip(*args, **kwargs)


_real_flip = pygame.display.flip
pygame.display.flip = flip

_argv = sys.argv[1:] or ["map2", "6000"]
sys.argv = ["selfplay.py"] + _argv
config.PLAYER1_ARMY = "necrons"
config.PLAYER2_ARMY = "orks"
config.ARMY_SELECT = False

try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass

r = state["done"] or {}
print()
print("--- Mecha Orks, the shipped list, live" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                 : %d" % state["frames"])
print("  A. %d units, %d pts; settings %s" % (len(r.get("units") or []), r.get("points", 0),
                                              r.get("settings")))
print("     units               : %s" % (r.get("units"),))
print("     measured            : %s" % (r.get("measured"),))
print("     enhancements        : %s" % (r.get("enhancements"),))
print("  B. warlord %s, Da Boss paid %s CP" % (r.get("warlords"), r.get("da_boss_cp")))
print("  C. embarked            : %s" % (r.get("embarked"),))
print("     in reserve          : %s" % (r.get("reserves"),))
print("  D. Gizmos: ignores cover %s, cover modifiers %s; Boomer lends %s; "
      "'Ardboyz Save %s; Show-off (bigboss, boy, models) %s"
      % (r.get("gizmos_ignores_cover"), r.get("gizmos_cover_modifiers"), r.get("boomer_bearers"),
         r.get("ardboyz_save"), r.get("show_off")))
print("  E. Da Hunt is On (printed, vs VEHICLE, vs other): %s" % (r.get("da_hunt"),))
print("  stale Player 1 prompts declined: %s" % (state["declined"] or "none"))

if not r:
    print("  INCONCLUSIVE - the run never reached a quiet frame")
    raise SystemExit(2)

if not NEUTRALIZE:
    checks = (
        ("the shipped list puts twelve units and 1990 points on the board",
         len(r["units"]) == 12 and r["points"] == 1990),
        ("...and declares its three detachments through game/detachments.py",
         r["settings"] == ["BLITZ_BRIGADE_PLAYERS", "DA_BIG_HUNT_PLAYERS", "GREEN_TIDE_PLAYERS"]),
        ("...with all four Enhancements live on the units that bought them",
         all(r["enhancements"].values())),
        ("Ghazghkull is the one Warlord, and main()'s Da Boss pays his 1CP",
         r["warlords"] == ["%s Ghazghkull Thraka 1" % ORK[-1]] and r["da_boss_cp"] == 1),
        ("the three declared transports are carrying after the pre-game", len(r["embarked"]) == 3),
        ("Targetin' Gizmos: the Gunwagon ignores cover because it carries the Big Mek",
         r.get("gizmos_ignores_cover") is True and r.get("gizmos_cover_modifiers") == []),
        ("Boss Boomer: the Battlewagon lends its Warboss's Intimidating Motivation",
         bool(r.get("boomer_bearers"))),
        ("'Ardboyz: the ten-Boy mob has a 4+ Save", r.get("ardboyz_save") == "4+"),
        ("Ferocious Show-off: the Bigboss swings at his printed A +2 in a mob of 11+, "
         "and the Boyz beside him are untouched",
         r.get("show_off") and r["show_off"][1] == r["show_off"][0] + 2 and r["show_off"][3] >= 11),
        ("Da Hunt is On: +1 AP against a VEHICLE and nothing against the rest",
         r.get("da_hunt") and r["da_hunt"][1] == r["da_hunt"][0] - 1 and r["da_hunt"][2] == r["da_hunt"][0]),
    )
else:
    checks = (
        ("the same twelve units and points are on the board",
         len(r["units"]) == 12 and r["points"] == 1990),
        # NOT "no setting at all": game/config.py still ships WAR_HORDE_PLAYERS
        # and AWAKENED_DYNASTY_PLAYERS as ("Player 2",) from before lists wrote
        # these, and clearing them is part of what apply_to_config() does. With
        # its write stubbed out those two stale defaults stand - which is worth
        # printing rather than hiding, and none of them is a detachment THIS
        # list declares.
        ("...but not one of the list's three detachments is declared",
         not ({"BLITZ_BRIGADE_PLAYERS", "DA_BIG_HUNT_PLAYERS", "GREEN_TIDE_PLAYERS"}
              & set(r["settings"]))),
        ("...so not one Enhancement is live", not any(r["enhancements"].values())),
        ("Targetin' Gizmos does nothing: the cover modifier stands",
         r.get("gizmos_ignores_cover") is False and r.get("gizmos_cover_modifiers") == ["Benefit of Cover"]),
        ("Boss Boomer lends nothing", not r.get("boomer_bearers")),
        ("'Ardboyz does nothing: the mob keeps its printed Save", r.get("ardboyz_save") != "4+"),
        ("Ferocious Show-off does nothing: the Bigboss swings at his printed A",
         r.get("show_off") and r["show_off"][1] == r["show_off"][0]),
        ("Da Hunt is On does nothing: the printed AP stands against a VEHICLE",
         r.get("da_hunt") and r["da_hunt"][1] == r["da_hunt"][0]),
        # The Warlord is NOT gated on a detachment - he is named by the list, and
        # Da Boss is an army rule. Both must survive the neutralize, or this
        # script would be proving something wider than it claims.
        ("the Warlord and his CP are untouched - they are the LIST's, not a detachment's",
         r["warlords"] == ["%s Ghazghkull Thraka 1" % ORK[-1]] and r["da_boss_cp"] == 1),
        ("...and the three transports still carry", len(r["embarked"]) == 3),
    )
failed = 0
for label, ok in checks:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    failed += 0 if ok else 1
print("  %d/%d" % (len(checks) - failed, len(checks)))
raise SystemExit(1 if failed else 0)
