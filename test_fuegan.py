"""Fuegan: statline, weapons, Burning Lance, Unquenchable Resolve, sprite.

Two abilities, and each is checked where it actually bites rather than at its
own predicate.

Burning Lance changes a RANGE CHARACTERISTIC, so the interesting consequence is
not "can he reach further" but "does HALF range move too" - [MELTA X] and
[RAPID FIRE X] both measure half of it, and half of a characteristic that has
been added to is half of the new number. game/shooting.py used to read the
printed range at those two sites with a comment saying they would need the same
treatment if a weapon ever had both a range bonus and one of those keywords.
A Melta weapon under Fuegan is exactly that weapon, so both are checked.

Unquenchable Resolve puts a destroyed model BACK, which this engine has done
exactly once before (Grot Orderly). What matters is that all four halves of
"back" happen - in the token list, in its Squad, off the destroyed list, at full
wounds - because any one of them left out is a half-alive model, and only some
of those show up as an obvious failure.
"""

import math

import testkit as tk
from game import (
    attached_units, burning_lance, sprites, unquenchable_resolve, weapon_range,
)
from game.factions import aeldari as ae
from game.factions.aeldari_points import AELDARI_POINTS
from game.squad import ENGAGEMENT_RANGE_IN
from game.units import AsurmenProfile, BaharrothProfile, FueganProfile, JainZarProfile
from game.weapons import FireAxeProfile, SearsongBeamProfile, SearsongLanceProfile

checks = tk.Checks("Fuegan")


def fuegan(name="1 Fuegan 1", owner="Player 1"):
    return tk.build(ae.FUEGAN, owner, name=name)


def dragons(name="1 Fire Dragons 1", owner="Player 1"):
    return tk.build(ae.FIRE_DRAGONS, owner, name=name)


# --- 1. statline ------------------------------------------------------------
print("--- 1. statline ---")

lord = fuegan()
p = lord.models[0].profile

checks.eq("M7\"", p.movement_in, 7)
checks.eq("T3", p.toughness, 3)
checks.eq("Sv2+", p.armor_save, "2+")
checks.eq("W5", p.wounds, 5)
checks.eq("Ld6+", p.leadership, "6+")
checks.eq("OC1", p.oc, 1)
checks.eq("WS2+", p.weapon_skill, "2+")
checks.eq("BS2+", p.ballistic_skill, "2+")
checks.eq("Invulnerable Save 4+", p.invulnerable_save, "4+")

# T3 on a Phoenix Lord reads like a transcription slip, so it is pinned against
# the four already built rather than against a literal: they all print the same
# chassis, which is what makes it the edition's number and not a typo.
for other in (AsurmenProfile, JainZarProfile, BaharrothProfile):
    q = other()
    checks.eq("same Phoenix Lord chassis as %s (T/Sv/W/Ld/OC/inv)" % q.name,
              (p.toughness, p.armor_save, p.wounds, p.leadership, p.oc, p.invulnerable_save),
              (q.toughness, q.armor_save, q.wounds, q.leadership, q.oc, q.invulnerable_save))
checks.eq("40 mm base, like the other foot Phoenix Lords",
          p.base_radius_in, AsurmenProfile.base_radius_in)

for kw in ("INFANTRY", "CHARACTER", "EPIC HERO", "ASPECT WARRIOR", "PHOENIX LORD", "GRENADES"):
    checks.true("keyword %s" % kw, kw in ae.FUEGAN.keywords)
checks.eq("one model", len(lord.models), 1)
checks.true("LEADER (24.22)", p.leader)
checks.true("EPIC HERO", p.epic_hero)
checks.true("Battle Focus (army rule)", p.battle_focus)
checks.true("Burning Lance flag", p.burning_lance)
checks.true("Unquenchable Resolve flag", p.unquenchable_resolve)
checks.eq("no Deep Strike printed", getattr(p, "deep_strike", False), False)


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

checks.eq("equipped with Searsong and the Fire Axe - no wargear options at all",
          sorted(w.name for w in lord.models[0].weapons),
          ["Fire Axe", "Searsong - Beam"])
checks.eq("...and the datasheet prints none", len(ae.FUEGAN.wargear_options), 0)

beam, lance, axe = SearsongBeamProfile(), SearsongLanceProfile(), FireAxeProfile()

checks.eq("Searsong beam 12\"/A3/BS2+/S8/AP-3/D2",
          (beam.range_in, beam.attacks, beam.ballistic_skill, beam.strength, beam.ap, beam.damage),
          (12, 3, "2+", 8, -3, 2))
checks.true("...[ASSAULT]", beam.assault)
checks.eq("...[MELTA 1]", beam.melta, 1)
checks.eq("...[SUSTAINED HITS 2]", beam.sustained_hits, 2)

checks.eq("Searsong lance 18\"/A1/BS2+/S14/AP-4",
          (lance.range_in, lance.attacks, lance.ballistic_skill, lance.strength, lance.ap),
          (18, 1, "2+", 14, -4))
checks.eq("...damage D6, rolled for real", lance.damage_notation.sides, 6)
checks.true("...[ASSAULT]", lance.assault)
checks.eq("...[MELTA 6]", lance.melta, 6)

# ONE datasheet entry with two firing profiles, so only the beam is granted -
# granting both would give him two guns.
checks.eq("the lance is the beam's alternate FIRING MODE, not a second weapon",
          SearsongBeamProfile.overcharge_profile, SearsongLanceProfile)
checks.true("...so only one Searsong is in the loadout",
            sum(1 for w in lord.models[0].weapons if w.name.startswith("Searsong")) == 1)

# The reading this datasheet forced: "Searsong - lance" puts "lance" exactly
# where "beam" sits (and where "sunburst"/"starshot" sit on the missile
# launcher), so it is the PROFILE NAME, not the [LANCE] weapon ability. Pinned
# so that correcting it, if it is ever confirmed the other way, is a visible
# one-line change rather than a silent one.
checks.eq("\"lance\" is the profile NAME, not the [LANCE] ability",
          getattr(lance, "lance", False), False)

checks.eq("Fire Axe Melee/A6/WS2+/S5/AP-4/D3",
          (axe.attacks, axe.weapon_skill, axe.strength, axe.ap, axe.damage),
          (6, "2+", 5, -4, 3))
checks.eq("...and no keywords at all",
          (axe.melta, axe.sustained_hits, axe.lethal_hits, axe.devastating_wounds),
          (0, 0, False, False))


# --- 3. points and the LEADER pairing ---------------------------------------
print("--- 3. points / leader ---")

entry = AELDARI_POINTS["Fuegan"]
checks.eq("130 pts", entry.cost_for(1, 1), 130)
checks.eq("no copy tiers - an EPIC HERO is unique anyway", entry.cost_for(1, 4), 130)
checks.eq("built squad carries the price", lord.points, 130)

checks.eq("he can lead Fire Dragons", attached_units.can_attach(fuegan(), dragons()), [])
checks.true("...and nothing else",
            bool(attached_units.can_attach(
                fuegan(), tk.build(ae.DIRE_AVENGERS, "Player 1", name="1 Dire Avengers 1"))))


# --- 4. Burning Lance -------------------------------------------------------
print("--- 4. Burning Lance ---")

unled = dragons()
gun = next(w for w in unled.models[1].weapons if w.melta)
checks.eq("a Dragon Fusion Gun prints 12\"", gun.range_in, 12)
checks.eq("unled: effective range is the printed one",
          weapon_range.effective_range_in(unled.models[1], gun), 12.0)
checks.eq("...and half range is 6\"",
          weapon_range.half_range_in(unled.models[1], gun), 6.0)

led = dragons()
attached_units.attach(fuegan(), led)
checks.eq("19.01 merged him in: 5 Dragons + Fuegan", len(led.models), 6)

trooper = next(m for m in led.models if m.profile.name == "Fire Dragon")
led_gun = next(w for w in trooper.weapons if w.melta)
checks.eq("led: +6\" to the Range characteristic",
          weapon_range.effective_range_in(trooper, led_gun), 18.0)
# The consequence that actually matters, and the one shooting.py's own comment
# predicted: half of a characteristic that has been added to is half of the NEW
# number, so the melta bonus reaches 9" instead of 6".
checks.eq("...so half range moves with it: 9\", not 6\"",
          weapon_range.half_range_in(trooper, led_gun), 9.0)

# "models in that unit" includes him: his own Searsong is [MELTA] on both modes.
fu_model = next(m for m in led.models if m.profile.name == "Fuegan")
own = next(w for w in fu_model.weapons if w.melta)
checks.eq("his own Searsong grows too - he is a model in that unit",
          weapon_range.effective_range_in(fu_model, own), 18.0)

# A non-[MELTA] weapon in the same unit is untouched - the rule names a keyword.
axe_in_unit = next(w for w in fu_model.weapons if not w.melta)
checks.eq("a non-Melta weapon in the same unit is untouched",
          weapon_range.effective_range_in(fu_model, axe_in_unit), float(axe_in_unit.range_in))

# "While this model is LEADING a unit" - a Character standing alone leads
# nothing, which is 24.22's own condition and the reason this reads
# leader_ability() rather than unit_wide_ability().
alone = fuegan()
alone_beam = next(w for w in alone.models[0].weapons if w.melta)
checks.eq("standing alone he is not leading, so no bonus",
          weapon_range.effective_range_in(alone.models[0], alone_beam), 12.0)
checks.eq("...and the predicate agrees",
          burning_lance.unit_has_burning_lance(alone), False)
checks.eq("a Fire Dragons unit with no Fuegan gets nothing",
          burning_lance.unit_has_burning_lance(unled), False)
checks.eq("...but the led one does", burning_lance.unit_has_burning_lance(led), True)

# A/B: neutralise the ability at its source and the SAME call falls back to the
# printed range - otherwise the numbers above would prove nothing about it.
_bonus = burning_lance.bonus_for
try:
    burning_lance.bonus_for = lambda model, weapon: 0.0
    checks.eq("A/B: neutralised, the led Dragon is back to 12\"",
              weapon_range.effective_range_in(trooper, led_gun), 12.0)
    checks.eq("...and half range back to 6\"",
              weapon_range.half_range_in(trooper, led_gun), 6.0)
finally:
    burning_lance.bonus_for = _bonus
checks.eq("...restored", weapon_range.effective_range_in(trooper, led_gun), 18.0)

# End to end: [MELTA X]'s damage bonus is the site that reads half range, so a
# target sitting between the old and the new half range is the whole difference.
from game.shooting import melta_adjusted_weapon  # noqa: E402

probe = dragons("1 Fire Dragons 9")
tk.line_up(probe, y=20.0)
enemy = tk.build(ae.RANGERS, "Player 2", name="2 Rangers 1")
tk.line_up(enemy, y=20.0 + 7.5)   # between 6" and 9" of the shooter
shooter = probe.models[1]
probe_gun = next(w for w in shooter.weapons if w.melta)
plain = melta_adjusted_weapon(probe_gun, [(shooter, probe_gun)], enemy)
checks.eq("unled, a target 7.5\" away is OUTSIDE half range - no melta bonus",
          plain.damage, probe_gun.damage)

attached_units.attach(fuegan("1 Fuegan 9"), probe)
boosted = melta_adjusted_weapon(probe_gun, [(shooter, probe_gun)], enemy)
checks.eq("led, the same target is INSIDE the new half range - melta bonus lands",
          boosted.damage, probe_gun.damage + probe_gun.melta)


# --- 5. Unquenchable Resolve -----------------------------------------------
print("--- 5. Unquenchable Resolve ---")


class _Dice:
    """A dice manager that returns exactly what the test queued."""

    def __init__(self, *values):
        self.queued = list(values)
        self.labels = []

    def roll(self, count, sides=6, **kwargs):
        self.labels.append(kwargs.get("label"))
        return [self.queued.pop(0) if self.queued else 6]


def death_scene(roll, enemy_at=None, name="1 Fuegan 5"):
    """Fuegan alone on an empty board, killed, with the roll scripted."""
    state = tk.GameState()
    lord_squad = fuegan(name)
    model = lord_squad.models[0]
    model.x_in, model.y_in = 20.0, 20.0
    state.add_token(model)
    enemies = None
    if enemy_at is not None:
        enemies = tk.build(ae.RANGERS, "Player 2", name="2 Rangers 5")
        for i, m in enumerate(enemies.models):
            m.x_in, m.y_in = enemy_at[0] + i * 1.2, enemy_at[1]
            state.add_token(m)
    dice = _Dice(roll)
    log = tk.Log()
    ctrl = unquenchable_resolve.UnquenchableResolveController(
        dice_manager=dice, game_state=state, game_log=log,
    )
    model.current_wounds = 0
    swept = state.remove_dead_models()
    ctrl.notify_destroyed(swept)
    return dict(state=state, squad=lord_squad, model=model, ctrl=ctrl,
                dice=dice, log=log, enemies=enemies)


# -- the roll
s = death_scene(roll=1)
checks.eq("a destroyed Fuegan is off the board", s["model"] in s["state"].tokens, False)
checks.eq("...and recorded as destroyed", s["model"] in s["squad"].destroyed_models, True)
checks.eq("the ability is owed a roll", s["ctrl"].is_pending(), True)
returned = s["ctrl"].resolve_end_of_phase()
checks.eq("rolled a 1: he stays dead", returned, [])
checks.eq("...still off the board", s["model"] in s["state"].tokens, False)
checks.true("...and the log says so", s["log"].has("Unquenchable Resolve"))
checks.eq("...the roll is labelled for the dice panel",
          s["dice"].labels, ["Unquenchable Resolve"])

s = death_scene(roll=2)
returned = s["ctrl"].resolve_end_of_phase()
checks.eq("rolled a 2: he rises (the printed threshold is 2+)", len(returned), 1)
checks.eq("...back in the token list", s["model"] in s["state"].tokens, True)
checks.eq("...back in his Squad", s["model"] in s["squad"].models, True)
checks.eq("...off the destroyed list", s["model"] in s["squad"].destroyed_models, False)
checks.eq("...\"with its full wounds remaining\"",
          s["model"].current_wounds, s["model"].profile.wounds)
checks.eq("...and nothing is left pending", s["ctrl"].is_pending(), False)

# -- "as close as possible to where it was destroyed"
s = death_scene(roll=6)
s["ctrl"].resolve_end_of_phase()
moved = math.hypot(s["model"].x_in - 20.0, s["model"].y_in - 20.0)
checks.true("on empty ground he comes back exactly where he fell", moved < 0.01)

# -- "not within Engagement Range of one or more enemy units"
s = death_scene(roll=6, enemy_at=(20.0, 20.0))
s["ctrl"].resolve_end_of_phase()
checks.eq("with enemies standing on the spot he still returns", s["model"] in s["state"].tokens, True)
gaps = [math.hypot(s["model"].x_in - e.x_in, s["model"].y_in - e.y_in)
        - s["model"].radius_in - e.radius_in for e in s["enemies"].models]
checks.true("...but pushed clear of Engagement Range of every enemy",
            min(gaps) > ENGAGEMENT_RANGE_IN)
checks.true("...and no further than it had to be", min(gaps) < ENGAGEMENT_RANGE_IN + 4.0)

# -- "the FIRST time this model is destroyed"
s = death_scene(roll=6)
s["ctrl"].resolve_end_of_phase()
checks.eq("first death: back up", s["model"] in s["state"].tokens, True)
s["model"].current_wounds = 0
s["ctrl"].notify_destroyed(s["state"].remove_dead_models())
checks.eq("a SECOND death is not owed a roll", s["ctrl"].is_pending(), False)
s["dice"].queued = [6]
checks.eq("...and resolving does nothing", s["ctrl"].resolve_end_of_phase(), [])
checks.eq("...he stays dead this time", s["model"] in s["state"].tokens, False)

# -- only this model has it
plain_squad = dragons("1 Fire Dragons 5")
checks.eq("a Fire Dragon does not have the ability",
          unquenchable_resolve.has_unquenchable_resolve(plain_squad.models[0]), False)
checks.eq("...Fuegan does",
          unquenchable_resolve.has_unquenchable_resolve(lord.models[0]), True)
ctrl = unquenchable_resolve.UnquenchableResolveController(game_log=tk.Log())
ctrl.notify_destroyed(plain_squad.models)
checks.eq("...so a dead Fire Dragon is owed nothing", ctrl.is_pending(), False)

# -- A/B: with the flag off, the same death is owed nothing
off = fuegan("1 Fuegan 8")
off.models[0].profile = type("NoResolve", (FueganProfile,), {"unquenchable_resolve": False})()
ctrl = unquenchable_resolve.UnquenchableResolveController(game_log=tk.Log())
ctrl.notify_destroyed(off.models)
checks.eq("A/B: without the flag, no roll is owed", ctrl.is_pending(), False)


# --- 6. sprite --------------------------------------------------------------
print("--- 6. sprite ---")

checks.true("Fuegan resolves a sprite", sprites.sprite_for(lord.models[0]))
checks.true("...and it is the file that had been sitting unused",
            "Fuegan" in (sprites.sprite_for(lord.models[0]) or ""))


checks.finish()
