"""Asurmen: datasheet data, Tactical Acumen, Hand of Asuryan.

Both abilities reuse machinery built for T'au stratagems (the post-shooting
Normal move, and the once-per-battle weapon grant), so the suite's job is to
show they are wired to THIS datasheet's own conditions - a 6" cap rather than
the model's M, a leadership requirement rather than a keyword, and a named
weapon rather than a chosen one - and that each effect is read back out of the
function the engine actually uses.
"""

import copy

import testkit as tk
from testkit import Checks, script

from game import hand_of_asuryan as hoa
from game import tactical_acumen as ta
from game.attached_units import attach, can_attach
from game.factions import aeldari as ae
from game.factions import tau_empire as tau
from game.sprites import _squad_key
from game.weapons import MELEE, RANGED

checks = Checks("Asurmen")


def asurmen(owner="Player 1", name="1 Asurmen 1"):
    return tk.build(ae.ASURMEN, owner, name=name)


def avengers(owner="Player 1", name="1 Dire Avengers 1"):
    return tk.build(ae.DIRE_AVENGERS, owner, name=name)


# --- 1. statline, keywords, points -----------------------------------------
print("--- 1. statline, keywords, points ---")

sq = asurmen()
p = sq.models[0].profile
checks.eq("one model", len(sq.models), 1)
checks.eq("135 points", sq.points, 135)
checks.eq("M7\"", p.movement_in, 7)
checks.eq("T3", p.toughness, 3)
checks.eq("Sv2+", p.armor_save, "2+")
checks.eq("W5", p.wounds, 5)
checks.eq("Ld6+", p.leadership, "6+")
checks.eq("OC1", p.oc, 1)
checks.eq("4+ invulnerable", p.invulnerable_save, "4+")
checks.eq("WS/BS 2+", (p.weapon_skill, p.ballistic_skill), ("2+", "2+"))
checks.eq("40 mm base", round(p.base_radius_in, 3), round(40 / 2 / 25.4, 3))
checks.true("INFANTRY", p.infantry)
checks.true("LEADER (24.22)", p.leader)
checks.true("Battle Focus", p.battle_focus)
checks.true("Tactical Acumen", p.tactical_acumen)
checks.true("Hand of Asuryan", p.hand_of_asuryan)
for kw in ("INFANTRY", "CHARACTER", "EPIC HERO", "PHOENIX LORD", "ASURMEN"):
    checks.true(f"keyword {kw}", kw in ae.ASURMEN.keywords)


# --- 2. weapons ------------------------------------------------------------
print("--- 2. weapons ---")

checks.eq("loadout", sorted(w.name for w in sq.models[0].weapons), ["Bloody Twins", "Sword of Asur"])
gun = next(w for w in sq.models[0].weapons if w.weapon_type == RANGED)
checks.eq("Bloody Twins 24\"/A6/S5/AP-1/D2",
          (gun.range_in, gun.attacks, gun.strength, gun.ap, gun.damage), (24, 6, 5, -1, 2))
# The keywords column printed empty and the NAME carried them - the rendering
# artefact this project has seen seven times now. Hand of Asuryan's own printed
# text calls the gun "its Bloody Twins weapon" without the suffix, which is the
# internal evidence that "assault pistol" is keywords rather than name.
checks.true("[ASSAULT]", gun.assault)
checks.true("[PISTOL]", gun.pistol)
checks.eq("...and the name is just 'Bloody Twins'", gun.name, hoa.HAND_OF_ASURYAN_WEAPON)

sword = next(w for w in sq.models[0].weapons if w.weapon_type == MELEE)
checks.eq("Sword of Asur A6/S6/AP-3/D3",
          (sword.attacks, sword.strength, sword.ap, sword.damage), (6, 6, -3, 3))
checks.true("[DEVASTATING WOUNDS]", sword.devastating_wounds)


# --- 3. Leader (19.01) -----------------------------------------------------
print("--- 3. Leader ---")

checks.eq("he can lead Dire Avengers", can_attach(asurmen(), avengers()), [])
checks.true("and only them",
            bool(can_attach(asurmen(), tk.build(ae.STRIKING_SCORPIONS, "Player 1",
                                                name="1 Striking Scorpions 1"))))


# --- 4. Tactical Acumen ----------------------------------------------------
print("--- 4. Tactical Acumen ---")


def led_unit():
    """A real attached unit (19.01), which is what "while this model is
    leading a unit" asks about."""
    body, lord = avengers(), asurmen()
    tk.line_up(body, x=20.0, y=20.0)
    tk.line_up(lord, x=20.0, y=18.5)
    attach(lord, body)
    return body


led = led_unit()
checks.true("a led unit has the ability", ta.unit_has_asurmen(led))
checks.eq("a plain Dire Avenger squad does not", ta.unit_has_asurmen(avengers()), False)
# A lone Asurmen leads nobody, so the ability grants nothing - which is what
# attached_units.leader_ability() is for, and why unit_wide_ability() would be
# the wrong lookup (no Dire Avenger prints this).
checks.eq("a lone Asurmen leads nobody", ta.unit_has_asurmen(asurmen()), False)

from game.decision import DecisionManager  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.turn import PHASE_SHOOTING  # noqa: E402


def move_scene():
    state = GameState()
    unit = led_unit()
    for model in unit.models:
        state.add_token(model)
    tracker = tk._tracker(PHASE_SHOOTING, "Player 1")
    log, dm = tk.Log(), DecisionManager()
    mover = MovementController(obstacles=[], game_log=log, player_name="Player 1",
                               turn_tracker=tracker, all_tokens=state.tokens)
    ctrl = ta.TacticalAcumenController(movement_controller=mover, decision_manager=dm, game_log=log)
    return dict(state=state, unit=unit, move=mover, decision=dm, log=log, ctrl=ctrl)


sc = move_scene()
sc["ctrl"].offer_after_shooting(sc["unit"], set())
checks.true("after shooting, the move is offered", sc["decision"].is_pending)
checks.eq("...as a real choice", sorted(o["label"] for o in sc["decision"].options),
          ["Make the move", "Stay put"])
tk.pick_option(sc["decision"], "Make the move")
checks.eq("the move is a Normal move of up to 6\", not the unit's M7\"",
          sc["move"].remaining_range[sc["unit"].models[0].id], ta.TACTICAL_ACUMEN_MOVE_IN)
checks.eq("...under its own move mode", sc["move"].move_mode, "tactical_acumen")
checks.eq("no charge lock yet - 'if it does' means once the move is made",
          sc["unit"].charge_locked_until_end_of_turn, False)
sc["ctrl"].confirm_move()
checks.true("...and now there is", sc["unit"].charge_locked_until_end_of_turn)
checks.eq("the move is finished", sc["move"].move_mode, None)

# Declining costs nothing.
sc2 = move_scene()
sc2["ctrl"].offer_after_shooting(sc2["unit"], set())
tk.pick_option(sc2["decision"], "Stay put")
checks.eq("declining starts no move", sc2["move"].move_mode, None)
checks.eq("...and locks no charge", sc2["unit"].charge_locked_until_end_of_turn, False)

# Cancelling a started move likewise: the lock is conditional on the move.
sc3 = move_scene()
sc3["ctrl"].offer_after_shooting(sc3["unit"], set())
tk.pick_option(sc3["decision"], "Make the move")
sc3["ctrl"].cancel_move()
checks.eq("cancelling locks no charge", sc3["unit"].charge_locked_until_end_of_turn, False)
checks.eq("...and leaves no move open", sc3["move"].move_mode, None)

# Not offered to a unit he is not leading.
sc4 = move_scene()
plain = avengers(name="1 Dire Avengers 2")
sc4["ctrl"].offer_after_shooting(plain, set())
checks.eq("an unled unit is not offered it", sc4["decision"].is_pending, False)

# The move is NOT booked as the unit's Movement-phase move - it happens in the
# Shooting phase, which is over for movement purposes.
checks.eq("it does not count as the Movement-phase move",
          sc["unit"] in sc["move"].moved_squad_ids, False)


# --- 5. Hand of Asuryan ----------------------------------------------------
print("--- 5. Hand of Asuryan ---")

lord = asurmen()
checks.true("available at the start", hoa.can_use(lord))
model = hoa.use(lord)
checks.true("using it returns the bearer", model is lord.models[0])
checks.eq("once per battle - not available again", hoa.can_use(lord), False)

granted = hoa.hand_of_asuryan_adjusted_weapon(
    next(w for w in lord.models[0].weapons if w.weapon_type == RANGED),
    [(lord.models[0], None)],
)
checks.eq("Damage becomes 3", granted.damage, hoa.HAND_OF_ASURYAN_DAMAGE)
checks.true("[DEVASTATING WOUNDS] is granted", granted.devastating_wounds)
checks.eq("[ANTI-INFANTRY 5+] is granted", granted.anti, hoa.HAND_OF_ASURYAN_ANTI)
# The shared class-level profile must never be mutated.
from game.weapons import BloodyTwinsProfile  # noqa: E402
checks.eq("the printed weapon is untouched",
          (BloodyTwinsProfile.damage, BloodyTwinsProfile.devastating_wounds, BloodyTwinsProfile.anti),
          (2, False, None))

# The grant is named to ONE weapon, so the sword is not affected.
sword_after = hoa.hand_of_asuryan_adjusted_weapon(
    next(w for w in lord.models[0].weapons if w.weapon_type == MELEE),
    [(lord.models[0], None)],
)
checks.eq("the Sword of Asur is untouched - the rule names Bloody Twins",
          sword_after.damage, 3)
checks.eq("...and it is the same object, not a copy",
          sword_after is next(w for w in lord.models[0].weapons if w.weapon_type == MELEE), True)

# Two lifetimes: the GRANT expires at end of phase, the SPEND does not.
hoa.reset_phase([lord])
after = hoa.hand_of_asuryan_adjusted_weapon(
    next(w for w in lord.models[0].weapons if w.weapon_type == RANGED),
    [(lord.models[0], None)],
)
checks.eq("the grant is gone at end of phase", after.damage, 2)
checks.eq("but the once-per-battle spend stays spent", hoa.can_use(lord), False)

# End to end through the real controller and the real shooting activation.
scene = tk.shooting_scene(ae.ASURMEN, tau.STRIKE_TEAM, attacker_owner="Player 1", gap=6.0)
ctrl = hoa.HandOfAsuryanController(decision_manager=scene["decision"], game_log=scene["log"])
scene["shooting"].hand_of_asuryan = ctrl
scene["shooting"].start_shooting(scene["attacker"])
checks.true("start_shooting() raises the offer", scene["decision"].is_pending)
checks.true("...naming the ability", "Hand of Asuryan" in scene["decision"].prompt)
tk.pick_option(scene["decision"], "Use Hand of Asuryan")
scene["shooting"].choose_target_squad(scene["target"])
key = next(r[0] for r in scene["shooting"].weapon_eligibility())
# 6 hits, then every wound die a 5. Against T3 an S5 shot wounds on 3+ either
# way - what changes is that 5 is a CRITICAL wound only under the granted
# [ANTI-INFANTRY 5+], and a critical wound is only special because
# [DEVASTATING WOUNDS] was granted too. So mortal wounds in the log are proof
# that BOTH halves of the grant reached the real resolution.
script(*([4] * 6 + [5] * 6), default=4)
scene["shooting"].choose_weapon(key)
for _ in range(8):
    if scene["decision"].is_pending:
        tk.pick_option(scene["decision"], scene["decision"].options[-1]["label"])
    elif scene["dice"].is_pending:
        scene["dice"].acknowledge()
        scene["shooting"].on_dice_acknowledged()
    elif scene["shooting"].pending_damage_choice:
        scene["shooting"].choose_damage_model(scene["shooting"].pending_damage_choice[0])
    else:
        break
log = " ".join(scene["log"].lines)
checks.true("the log records the use", "Hand of Asuryan" in log)
checks.true("a wound roll of 5 became CRITICAL, which only [ANTI-INFANTRY 5+] does",
            "6 critical" in log or "of which 6 critical" in log)
checks.true("...and those criticals became mortal wounds, which only "
            "[DEVASTATING WOUNDS] does", "DEVASTATING WOUNDS" in log)

# A unit without the ability is never offered it.
plain_scene = tk.shooting_scene(ae.DIRE_AVENGERS, tau.STRIKE_TEAM, attacker_owner="Player 1", gap=6.0)
plain_scene["shooting"].hand_of_asuryan = hoa.HandOfAsuryanController(
    decision_manager=plain_scene["decision"], game_log=plain_scene["log"])
plain_scene["shooting"].start_shooting(plain_scene["attacker"])
checks.eq("a unit without the ability is not offered it", plain_scene["decision"].is_pending, False)


# --- 6. sprite -------------------------------------------------------------
print("--- 6. sprite ---")

checks.eq("Asurmen art", _squad_key(sq.models[0]), "Asurmen")


# --- 7. A/B probes ---------------------------------------------------------
print("--- 7. A/B probes ---")

original = ta.unit_has_asurmen
ta.unit_has_asurmen = lambda squad: False
probe = move_scene()
probe["ctrl"].offer_after_shooting(probe["unit"], set())
checks.eq("A/B: without the leader lookup the move is never offered",
          probe["decision"].is_pending, False)
ta.unit_has_asurmen = original
probe2 = move_scene()
probe2["ctrl"].offer_after_shooting(probe2["unit"], set())
checks.true("A/B: restored", probe2["decision"].is_pending)

lord2 = asurmen()
hoa.use(lord2)
saved = hoa.HAND_OF_ASURYAN_DAMAGE
hoa.HAND_OF_ASURYAN_DAMAGE = 0
checks.eq("A/B: with the grant neutralised the Damage stays printed",
          hoa.hand_of_asuryan_adjusted_weapon(
              next(w for w in lord2.models[0].weapons if w.weapon_type == RANGED),
              [(lord2.models[0], None)]).damage, 2)
hoa.HAND_OF_ASURYAN_DAMAGE = saved
checks.eq("A/B: restored",
          hoa.hand_of_asuryan_adjusted_weapon(
              next(w for w in lord2.models[0].weapons if w.weapon_type == RANGED),
              [(lord2.models[0], None)]).damage, 3)

checks.finish()
